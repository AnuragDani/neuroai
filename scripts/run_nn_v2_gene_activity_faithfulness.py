#!/usr/bin/env python3
"""N21 secondary faithfulness: I1/I3/I4 on gene-activity GA_ca fold models.

Reuses held-out intervention helpers from run_nn_v2_faithfulness.py and the
500-gene GA view construction from run_nn_v2_gene_activity.py. Results are
secondary only and are merged into docs/nn_v2/gene_activity_results.json.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import torch

import run_nn_v2_faithfulness as faith
import run_nn_v2_gene_activity as ga
from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import _atac_tfidf, _rna_lognorm, prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs
from p22.eval import nn_factory
from p22.models.fusion import VIEW_A, VIEW_B
from p22.models.gene_aligned import build_genomic_attention_mask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/gene_activity_v2"
)


def _align_ga_fold(inputs, fold_arrays, selected_names, bed_path: Path):
    name_to_rna = {str(n): i for i, n in enumerate(inputs.gene_names.tolist())}
    rna_cols = [name_to_rna[n] for n in selected_names]
    name_to_region = ga._panel_name_to_region_index(bed_path)
    atac_cols = [name_to_region[n] for n in selected_names]

    rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, rna_cols]
    rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    scaler.fit(rna_dense[fold_arrays.train_position])
    fold_arrays.rna = scaler.transform(rna_dense).astype(np.float32)

    atac_raw = inputs.atac[:, atac_cols]
    atac_tfidf, _ = _atac_tfidf(atac_raw, fold_arrays.train_position)
    fold_arrays.atac = np.asarray(atac_tfidf.todense(), dtype=np.float32)
    return fold_arrays


def evaluate_ga_ca_fold(
    *,
    run_dir: Path,
    repeat: int,
    fold: int,
    inputs,
    train_rows,
    holdout_rows,
    protocol,
    selection,
    bed_path: Path,
    i3_draws: int,
):
    arm = "GA_ca"
    evidence_path = run_dir / "models" / arm / f"r{repeat}_f{fold}.json"
    state_path = run_dir / "models" / arm / f"r{repeat}_f{fold}.pt"
    fold_path = run_dir / "folds" / f"r{repeat}_f{fold}_{arm}.json"
    saved_evidence = json.loads(evidence_path.read_text())
    fold_rec = json.loads(fold_path.read_text())

    region_rows = np.arange(len(inputs.regions), dtype=np.int64)
    fold_arrays = prepare_nn_fold(
        inputs,
        train_rows,
        holdout_rows,
        region_rows,
        n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
        exclude_chr21=False,
    )
    if fold_arrays.evidence["idf_sha256"] != saved_evidence["idf_sha256"]:
        raise RuntimeError(
            f"idf_sha256 mismatch GA_ca r{repeat}_f{fold}: "
            f"{fold_arrays.evidence['idf_sha256']} != {saved_evidence['idf_sha256']}"
        )
    fold_arrays = _align_ga_fold(
        inputs, fold_arrays, selection["names"], bed_path
    )

    ga._ATTN_MASK = build_genomic_attention_mask(
        selection["chromosomes"], selection["starts"], k=5
    )

    train_pos = fold_arrays.train_position
    test_pos = ~train_pos
    train_views = {VIEW_A: fold_arrays.rna[train_pos], VIEW_B: fold_arrays.atac[train_pos]}
    test_views = {VIEW_A: fold_arrays.rna[test_pos], VIEW_B: fold_arrays.atac[test_pos]}
    test_donors = fold_arrays.donor[test_pos]
    test_labels = fold_arrays.label[test_pos]
    test_cell_types = inputs.metadata["author_cell_type"].to_numpy()[holdout_rows]

    widths = {
        "n_features_a": int(fold_arrays.rna.shape[1]),
        "n_features_b": int(fold_arrays.atac.shape[1]),
        "n_library": 37,
        "n_batch": 12,
        "k_rna": 16,
        "k_atac": 8,
        "n_classes": 2,
    }
    # Load via module attribute so GA-patched nn_factory.build_arm is used
    # (faith._load_fold_model binds the unpatched name at import time).
    cfg = dict(fold_rec["best_grid_point"])
    cfg["cell_meta"] = faith._dummy_cell_meta()
    model, _aux, _trainer = nn_factory.build_arm(arm, widths, cfg)
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    missing, unexpected = model.load_state_dict(state, strict=True)
    if missing or unexpected:
        raise RuntimeError(
            f"state_dict mismatch for {state_path}: missing={missing} unexpected={unexpected}"
        )
    model.eval()

    donor_ids, prob_donor, logits = faith._donor_probs(model, test_views, test_donors)
    saved_ids = list(fold_rec["donor_ids"])
    order = {d: i for i, d in enumerate(donor_ids)}
    if set(saved_ids) != set(order):
        raise RuntimeError(f"donor set mismatch GA_ca r{repeat}_f{fold}")
    prob_donor = np.array([prob_donor[order[d]] for d in saved_ids])
    donor_truth = np.array(
        [int(test_labels[test_donors == d][0]) for d in saved_ids]
    )
    baseline_cell_pred = (logits >= 0).astype(int)
    baseline_donor_ids = np.asarray(saved_ids)

    rows = []
    for name in ("I1", "I3", "I4", "NC"):
        result = faith.run_intervention(
            name,
            model,
            test_views,
            test_donors,
            test_cell_types,
            train_views,
            seed=22 + 1000 * repeat + fold,
            baseline_cell_pred=baseline_cell_pred,
            donor_truth=donor_truth,
            baseline_donor_ids=baseline_donor_ids,
            baseline_prob_donor=prob_donor,
            i3_draws=i3_draws if name == "I3" else 1,
        )
        if result is None:
            continue
        if name == "NC":
            if not np.allclose(result["prob_donor"], prob_donor):
                raise RuntimeError(f"NC Δ ≠ 0 for GA_ca r{repeat}_f{fold}")
            if result["flip_rate"] != 0.0:
                raise RuntimeError(f"NC flip_rate ≠ 0 for GA_ca r{repeat}_f{fold}")
        rows.append(
            {
                "intervention": name,
                "arm": arm,
                "repeat": repeat,
                "fold": fold,
                "donors": baseline_donor_ids,
                "y": donor_truth,
                "p_before": prob_donor,
                "p_after": result["prob_donor"],
                "flip_rate": result["flip_rate"],
            }
        )
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "configs/nn_protocol_v2_2026-09-23.json",
    )
    parser.add_argument(
        "--inputs-manifest",
        type=Path,
        default=ROOT / "configs/nn_inputs_2026-09-23.json",
    )
    parser.add_argument("--atac-matrix", type=Path, default=ga.DEFAULT_ATAC)
    parser.add_argument("--atac-bed", type=Path, default=ga.DEFAULT_BED)
    parser.add_argument("--gene-config", type=Path, default=ga.DEFAULT_GENE_CFG)
    parser.add_argument(
        "--results-json",
        type=Path,
        default=ROOT / "docs/nn_v2/gene_activity_results.json",
    )
    parser.add_argument("--i3-draws", type=int, default=5)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=22)
    args = parser.parse_args(argv)
    ga.install_ga_factory_patches()

    selection = ga.select_ga_genes(args.gene_config, ga.GA_TOKEN_CAP)
    protocol = json.loads(args.protocol.read_text())
    manifest = json.loads(args.inputs_manifest.read_text())
    h5ad = manifest["inputs"]["h5ad"]["path"]

    logging.info("Loading gene-activity inputs for GA_ca faithfulness…")
    inputs = load_nn_inputs(
        h5ad,
        str(args.atac_matrix),
        protocol["sampling"]["cap_per_donor"],
        22,
        union_bed=str(args.atac_bed),
    )
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = list(
        iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=5,
            n_folds=5,
            base_seed=protocol["splits"]["split_seed"],
        )
    )

    all_rows = []
    for split in splits:
        rows = evaluate_ga_ca_fold(
            run_dir=args.run,
            repeat=split.repeat,
            fold=split.fold,
            inputs=inputs,
            train_rows=split.train_index,
            holdout_rows=split.test_index,
            protocol=protocol,
            selection=selection,
            bed_path=args.atac_bed,
            i3_draws=args.i3_draws,
        )
        all_rows.extend(rows)
        logging.info("GA_ca faithfulness r%s_f%s (%d rows)", split.repeat, split.fold, len(rows))

    summary_rows = faith._aggregate(all_rows, args.bootstrap_draws, args.bootstrap_seed)
    by = {(r["intervention"], r["arm"]): r for r in summary_rows}

    def _ci_excludes_zero(key):
        row = by.get(key)
        if row is None:
            return False
        lo, hi = row["ll_drop_ci"]
        return lo is not None and hi is not None and (lo > 0 or hi < 0)

    tags = []
    if _ci_excludes_zero(("I1", "GA_ca")):
        tags.append("GA_ATAC_USED")
    else:
        tags.append("GA_ATAC_UNUSED_OR_NULL")
    if _ci_excludes_zero(("I3", "GA_ca")):
        tags.append("GA_CA_USES_PAIRING")
    else:
        tags.append("GA_CA_PAIRING_UNUSED")
    if _ci_excludes_zero(("I4", "GA_ca")):
        tags.append("GA_ATTENTION_USED")
    else:
        tags.append("GA_ATTENTION_NOT_SHOWN_USED")

    faith_block = {
        "arm": "GA_ca",
        "n_folds": 25,
        "interventions": ["I1", "I3", "I4", "NC"],
        "nc_exact_zero": True,
        "summary": summary_rows,
        "tags": tags,
        "secondary_only": True,
        "source_run": str(args.run),
    }

    results = json.loads(args.results_json.read_text())
    results["faithfulness_ga"] = faith_block
    args.results_json.write_text(json.dumps(results, indent=2, default=str) + "\n")

    md = ROOT / "docs/nn_v2/GENE_ACTIVITY.md"
    extra = [
        "",
        "## Faithfulness on GA_ca (I1/I3/I4)",
        "",
        f"Tags: {', '.join(tags)}. NC exact zero on all 25 folds.",
        "Secondary only; does not alter primary N13 tags.",
        "",
    ]
    for key in (("I1", "GA_ca"), ("I3", "GA_ca"), ("I4", "GA_ca")):
        row = by.get(key)
        if row is None:
            continue
        lo, hi = row["ll_drop_ci"]
        extra.append(
            f"- {key[0]} Δlogloss={row['ll_drop']:.4f} "
            f"CI [{lo:.4f}, {hi:.4f}]"
        )
    extra.append("")
    text = md.read_text() if md.exists() else ""
    if "## Faithfulness on GA_ca" in text:
        head = text.split("## Faithfulness on GA_ca", 1)[0].rstrip()
        text = head + "\n" + "\n".join(extra)
    else:
        text = text.rstrip() + "\n" + "\n".join(extra)
    md.write_text(text + "\n")
    logging.info("Wrote faithfulness_ga tags=%s", tags)
    return 0


if __name__ == "__main__":
    sys.exit(main())
