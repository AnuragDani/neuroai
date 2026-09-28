"""N15 out-of-fold per-cell score export against accepted ladder_v2 models.

Reloads saved fold state_dicts from the main-checkout ladder_v2 run (not copied
here), rebuilds matching fold inputs, and writes per-cell logits / MIL attention
averaged across the five outer-test repeats. Every sampled cell must appear
exactly five times per arm before averaging (decision_tree N15).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs, region_indices
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.mil_loop import predict_mil

_LADDER_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2"
)
_CHR21_EXCLUDED_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/chr21_excluded"
)
_DEFAULT_SPECTRUM = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/spectrum"
)
_DEFAULT_ARMS = ("R1_ca", "R3_ca", "R3_tc", "R4_ca")
_N_LIBRARY = 37
_N_BATCH = 12


def _dummy_cell_meta(n: int = 8) -> dict[str, np.ndarray]:
    return {
        "labels": np.zeros(n, dtype=np.int64),
        "library": np.zeros(n, dtype=np.int64),
        "batch": np.zeros(n, dtype=np.int64),
        "qc": np.zeros((n, 5), dtype=np.float32),
    }


def _load_fold_model(
    arm: str,
    widths: Mapping[str, Any],
    grid: Mapping[str, Any],
    state_path: Path,
) -> nn.Module:
    cfg = dict(grid)
    cfg["cell_meta"] = _dummy_cell_meta()
    model, _aux, _trainer = build_arm(arm, widths, cfg)
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    missing, unexpected = model.load_state_dict(state, strict=True)
    if missing or unexpected:
        raise RuntimeError(
            f"state_dict mismatch for {state_path}: missing={missing} unexpected={unexpected}"
        )
    model.eval()
    return model


def _apply_r4_programs(
    inputs,
    fold_arrays,
    region_rows: np.ndarray,
    model_seed: int,
):
    from p22.data.nn_fold import _atac_tfidf, _rna_lognorm
    from p22.models.program_tokens import fit_programs, program_activities

    id_to_idx = {gid: i for i, gid in enumerate(inputs.gene_ids)}
    selected_cols = [id_to_idx[gid] for gid in fold_arrays.gene_ids]
    rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, selected_cols]
    rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
    atac_raw = inputs.atac[:, region_rows]
    atac_tfidf, _ = _atac_tfidf(atac_raw, fold_arrays.train_position)
    atac_dense = np.asarray(atac_tfidf.todense(), dtype=np.float32)
    rna_nmf = fit_programs(rna_dense[fold_arrays.train_position], k=16, seed=model_seed)
    atac_nmf = fit_programs(atac_dense[fold_arrays.train_position], k=8, seed=model_seed)
    fold_arrays.rna = program_activities(rna_nmf, rna_dense).numpy()
    fold_arrays.atac = program_activities(atac_nmf, atac_dense).numpy()
    return fold_arrays


def _chr21_dosage_for_test(inputs, fold_arrays) -> np.ndarray:
    """Mean scaled RNA of chr21 genes present in the fold HVG set (test rows)."""
    test_pos = ~fold_arrays.train_position
    chr21_mask = inputs.chr21_gene_mask()
    gene_id_to_global = {gid: i for i, gid in enumerate(inputs.gene_ids)}
    hvg_cols = [
        j
        for j, gid in enumerate(fold_arrays.gene_ids)
        if chr21_mask[gene_id_to_global[gid]]
    ]
    if not hvg_cols:
        return np.zeros(int(test_pos.sum()), dtype=np.float32)
    return np.asarray(fold_arrays.rna[test_pos][:, hvg_cols].mean(axis=1), dtype=np.float32)


def assert_five_appearances(
    cell_scores: Mapping[str, Mapping[Any, Mapping[str, list]]],
) -> None:
    """Decision-tree N15: each cell must appear exactly 5 times per arm."""
    for arm, arm_scores in cell_scores.items():
        for cell_id, metrics in arm_scores.items():
            n = len(metrics["s"])
            if n != 5:
                raise AssertionError(
                    f"export bug: cell {cell_id!r} in arm {arm} appeared {n} times "
                    "(expected 5); do not average partial repeats"
                )


def export_run(
    *,
    run_dir: Path,
    arms: Sequence[str],
    inputs,
    splits: Sequence[Any],
    protocol: Mapping[str, Any],
    out_cells: Path,
    out_compact: Path,
    exclude_chr21: bool,
    smoke: bool = False,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    metadata = inputs.metadata
    cell_scores: dict[str, dict[Any, dict[str, list]]] = {
        arm: defaultdict(lambda: {"s": [], "a": [], "chr21": []}) for arm in arms
    }
    cell_metadata_cache: dict[Any, dict[str, Any]] = {}
    folds_used = 0
    parameter_counts: dict[str, int] = {}

    with open(protocol["representation"]["atac"]["region_set_config"]) as handle:
        atac_regions = json.load(handle)
    region_by_split = {
        (item["repeat"], item["fold"]): item["regions"]
        for item in atac_regions["per_fold"]
    }

    for arm_name in arms:
        print(f"Processing arm {arm_name}...", flush=True)
        for split in splits:
            if smoke and not (split.repeat == 0 and split.fold == 0):
                continue
            region_list = region_by_split.get((split.repeat, split.fold))
            if region_list is None:
                raise ValueError(f"missing region set for r{split.repeat}_f{split.fold}")
            region_rows = region_indices(inputs, region_list)

            state_path = run_dir / "models" / arm_name / f"r{split.repeat}_f{split.fold}.pt"
            evidence_path = (
                run_dir / "models" / arm_name / f"r{split.repeat}_f{split.fold}.json"
            )
            fold_path = (
                run_dir / "folds" / f"r{split.repeat}_f{split.fold}_{arm_name}.json"
            )
            if not state_path.exists():
                raise FileNotFoundError(state_path)
            saved_evidence = json.loads(evidence_path.read_text())
            fold_rec = json.loads(fold_path.read_text())
            parameter_counts[arm_name] = int(fold_rec["parameter_count"])

            fold_arrays = prepare_nn_fold(
                inputs,
                split.train_index,
                split.test_index,
                region_rows,
                n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
                exclude_chr21=exclude_chr21,
            )
            if fold_arrays.evidence["idf_sha256"] != saved_evidence["idf_sha256"]:
                raise RuntimeError(
                    f"idf_sha256 mismatch for {arm_name} r{split.repeat}_f{split.fold}: "
                    f"{fold_arrays.evidence['idf_sha256']} != {saved_evidence['idf_sha256']}"
                )

            # Chr21 dosage uses HVG RNA columns; compute before R4 program replace.
            chr21_dosage = _chr21_dosage_for_test(inputs, fold_arrays)

            model_seed = int(fold_rec["best_grid_point"].get("model_seed", 0))
            if arm_name.startswith("R4_"):
                fold_arrays = _apply_r4_programs(
                    inputs, fold_arrays, region_rows, model_seed
                )

            test_pos = ~fold_arrays.train_position
            views = {
                VIEW_A: fold_arrays.rna[test_pos],
                VIEW_B: fold_arrays.atac[test_pos],
            }
            widths = {
                "n_features_a": int(fold_arrays.rna.shape[1]),
                "n_features_b": int(fold_arrays.atac.shape[1]),
                "n_library": _N_LIBRARY,
                "n_batch": _N_BATCH,
                "k_rna": 16,
                "k_atac": 8,
                "n_classes": 2,
            }
            model = _load_fold_model(
                arm_name, widths, fold_rec["best_grid_point"], state_path
            )
            test_donors = fold_arrays.donor[test_pos]
            preds = predict_mil(model, views, test_donors)
            cell_logits = np.asarray(preds["cell_logits"], dtype=np.float64)
            attention = np.asarray(preds["attention"], dtype=np.float64)

            test_cell_ids = metadata.index[split.test_index].to_numpy()
            if len(test_cell_ids) != len(cell_logits):
                raise RuntimeError(
                    f"row mismatch {arm_name} r{split.repeat}_f{split.fold}: "
                    f"{len(test_cell_ids)} cells vs {len(cell_logits)} logits"
                )

            for i, cell_id in enumerate(test_cell_ids):
                cell_scores[arm_name][cell_id]["s"].append(float(cell_logits[i]))
                cell_scores[arm_name][cell_id]["a"].append(float(attention[i]))
                cell_scores[arm_name][cell_id]["chr21"].append(float(chr21_dosage[i]))
                if cell_id not in cell_metadata_cache:
                    row = metadata.iloc[int(split.test_index[i])]
                    cell_metadata_cache[cell_id] = {
                        "cell_id": cell_id,
                        "donor": row["donor_id"],
                        "label": int(row["disease"] == "complete trisomy 21"),
                        "author_cell_type": row["author_cell_type"],
                        "cell_class": row["cell_class"],
                        "dev_PCW": row["dev_PCW"],
                        "log1p_nCount_RNA": float(np.log1p(row["nCount_RNA"])),
                        "log1p_nCount_ATAC": float(np.log1p(row["nCount_ATAC"])),
                    }
            folds_used += 1
            print(
                f"  done {arm_name} r{split.repeat}_f{split.fold} "
                f"n_test={len(test_cell_ids)}",
                flush=True,
            )

    if not smoke:
        assert_five_appearances(cell_scores)

    out_rows: list[dict[str, Any]] = []
    for arm_name in arms:
        for cell_id, metrics in cell_scores[arm_name].items():
            if smoke and len(metrics["s"]) == 0:
                continue
            s_arr = np.asarray(metrics["s"], dtype=np.float64)
            a_arr = np.asarray(metrics["a"], dtype=np.float64)
            c_arr = np.asarray(metrics["chr21"], dtype=np.float64)
            meta = cell_metadata_cache[cell_id]
            out_rows.append(
                {
                    "cell_id": meta["cell_id"],
                    "donor": meta["donor"],
                    "label": meta["label"],
                    "author_cell_type": meta["author_cell_type"],
                    "cell_class": meta["cell_class"],
                    "dev_PCW": meta["dev_PCW"],
                    "arm": arm_name,
                    "s_mean": float(s_arr.mean()),
                    "s_sd": float(s_arr.std(ddof=1)) if s_arr.size > 1 else float("nan"),
                    "a_mean": float(a_arr.mean()),
                    "chr21_dosage": float(c_arr.mean()),
                    "log1p_nCount_RNA": meta["log1p_nCount_RNA"],
                    "log1p_nCount_ATAC": meta["log1p_nCount_ATAC"],
                    "n_repeats": int(s_arr.size),
                }
            )

    df = pd.DataFrame(out_rows)
    out_cells.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_cells, index=False, compression="gzip")

    compact = (
        df.groupby(["arm", "donor", "author_cell_type"], observed=True)
        .agg(
            label=("label", "first"),
            cell_class=("cell_class", "first"),
            dev_PCW=("dev_PCW", "first"),
            s_mean=("s_mean", "mean"),
            a_mean=("a_mean", "mean"),
            chr21_dosage=("chr21_dosage", "mean"),
            log1p_nCount_RNA=("log1p_nCount_RNA", "mean"),
            log1p_nCount_ATAC=("log1p_nCount_ATAC", "mean"),
            n_cells=("cell_id", "count"),
        )
        .reset_index()
    )
    out_compact.parent.mkdir(parents=True, exist_ok=True)
    compact.to_csv(out_compact, index=False, compression="gzip")

    counts_by_arm = {
        arm: int((df["arm"] == arm).sum()) for arm in arms if arm in set(df["arm"])
    }
    summary = {
        "source_run": str(run_dir),
        "exclude_chr21": exclude_chr21,
        "smoke": smoke,
        "arms": list(arms),
        "folds_used": folds_used,
        "n_cell_arm_rows": int(len(df)),
        "n_donor_celltype_rows": int(len(compact)),
        "rows_per_arm": counts_by_arm,
        "parameter_counts": parameter_counts,
        "cell_scores_path": str(out_cells),
        "donor_celltype_scores_path": str(out_compact),
        "five_appearances_asserted": (not smoke),
        "n_library": _N_LIBRARY,
        "n_batch": _N_BATCH,
    }
    print(
        f"Exported {len(df)} cell-arm rows -> {out_cells}; "
        f"{len(compact)} donor×cell-type rows -> {out_compact}",
        flush=True,
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=_LADDER_V2_ROOT)
    parser.add_argument("--spectrum-dir", type=Path, default=_DEFAULT_SPECTRUM)
    parser.add_argument("--out-docs", type=Path, default=Path("docs/nn_v2"))
    parser.add_argument("--protocol", default="configs/nn_protocol_v2_2026-09-23.json")
    parser.add_argument("--inputs-config", default="configs/nn_inputs_2026-09-23.json")
    parser.add_argument("--arms", default=",".join(_DEFAULT_ARMS))
    parser.add_argument(
        "--include-chr21-excluded",
        action="store_true",
        help="Also export R3_ca/R3_tc from chr21_excluded models if present",
    )
    parser.add_argument("--smoke", action="store_true", help="Only repeat 0 fold 0")
    args = parser.parse_args(argv)

    protocol = json.loads(Path(args.protocol).read_text())
    input_manifest = json.loads(Path(args.inputs_config).read_text())
    inputs = load_nn_inputs(
        input_manifest["inputs"]["h5ad"]["path"],
        input_manifest["inputs"]["atac_tiebreak_counts"]["path"],
        protocol["sampling"]["cap_per_donor"],
        protocol["sampling"]["seed"],
        union_bed=input_manifest["inputs"]["tracked_union_bed"]["path"],
    )
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = list(
        iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=protocol["splits"]["n_repeats"],
            n_folds=protocol["splits"]["n_folds"],
            base_seed=protocol["splits"]["split_seed"],
        )
    )
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    spectrum_dir = args.spectrum_dir
    out_docs = args.out_docs

    main_summary = export_run(
        run_dir=args.run.resolve(),
        arms=arms,
        inputs=inputs,
        splits=splits,
        protocol=protocol,
        out_cells=spectrum_dir
        / ("cell_scores_smoke.csv.gz" if args.smoke else "cell_scores.csv.gz"),
        out_compact=out_docs
        / (
            "donor_celltype_scores_smoke.csv.gz"
            if args.smoke
            else "donor_celltype_scores.csv.gz"
        ),
        exclude_chr21=False,
        smoke=args.smoke,
    )

    evidence: dict[str, Any] = {
        "ladder_v2_export": main_summary,
        "chr21_excluded_export": None,
    }

    if args.include_chr21_excluded:
        chr21_models = _CHR21_EXCLUDED_ROOT / "models"
        if (chr21_models / "R3_ca").exists() and (chr21_models / "R3_tc").exists():
            evidence["chr21_excluded_export"] = export_run(
                run_dir=_CHR21_EXCLUDED_ROOT,
                arms=("R3_ca", "R3_tc"),
                inputs=inputs,
                splits=splits,
                protocol=protocol,
                out_cells=spectrum_dir
                / (
                    "cell_scores_chr21_excluded_smoke.csv.gz"
                    if args.smoke
                    else "cell_scores_chr21_excluded.csv.gz"
                ),
                out_compact=out_docs
                / (
                    "donor_celltype_scores_chr21_excluded_smoke.csv.gz"
                    if args.smoke
                    else "donor_celltype_scores_chr21_excluded.csv.gz"
                ),
                exclude_chr21=True,
                smoke=args.smoke,
            )
        else:
            evidence["chr21_excluded_export"] = {
                "status": "NOT_NEEDED",
                "reason": f"models missing under {chr21_models}",
            }
    else:
        evidence["chr21_excluded_export"] = {
            "status": "DEFERRED",
            "reason": "pass --include-chr21-excluded to export no-chr21 R3 scores",
        }

    evidence_path = out_docs / (
        "cell_scores_export_smoke.json" if args.smoke else "cell_scores_export.json"
    )
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"Wrote evidence {evidence_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
