"""P2: planted gene-matched RNA×ATAC interaction (S6) for gene-aligned CA vs TC vs MLP.

Uses the same fold prep / fake-label stratification helpers as N4
(``run_nn_planted_benchmark``) and the gene-activity matched-gene view path
from N21. Writes ``docs/nn_v2/v5/planted_gene_aligned.json``. Null is valid.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_nn_planted_benchmark as bench  # noqa: E402
import run_nn_v2_gene_activity as ga  # noqa: E402
from p22.data.nn_fold import _atac_tfidf, _rna_lognorm  # noqa: E402
from p22.data.nn_inputs import LABEL_DISEASE, FoldArrays, load_nn_inputs  # noqa: E402
from p22.eval.planted_signal import GENE_ALIGNED_SCENARIO, fake_donor_labels, plant  # noqa: E402
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.models.gene_aligned import (  # noqa: E402
    GeneAlignedCrossAttention,
    GeneAlignedTokenConcat,
    build_genomic_attention_mask,
)
from p22.training.loop import predict, set_all_seeds, train_model  # noqa: E402
from run_real_paired_comparison import _fold_map, _indices  # noqa: E402

CONFIG = ROOT / "configs/nn_inputs_2026-09-23.json"
GA_ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/"
    "gene_activity/counts/counts.npz"
)
GA_BED = ROOT / "configs/nn_gene_activity_2026-09-23.bed"
GA_CFG = ROOT / "configs/nn_gene_activity_2026-09-23.json"
OUT_JSON = ROOT / "docs/nn_v2/v5/planted_gene_aligned.json"
OUT_RUN = ROOT / "reports/generated/nn_20260923/planted_gene_aligned"
GA_TOKEN_CAP = 64
PLANT_SEED = 0


def select_matched_genes(gene_cfg: Path, cap: int = GA_TOKEN_CAP) -> dict:
    """Top-`cap` GA panel genes by label-free dispersion_z (stable)."""
    return ga.select_ga_genes(gene_cfg, cap)


def matched_gene_fold(
    inputs, train_rows, holdout_rows, selected: dict, bed_path: Path
) -> FoldArrays:
    """Build equal-width RNA/ATAC gene views with train-only scaler/IDF."""
    names = selected["names"]
    name_to_rna = {str(n): i for i, n in enumerate(inputs.gene_names.tolist())}
    rna_cols = [name_to_rna[n] for n in names]
    name_to_region = ga._panel_name_to_region_index(bed_path)
    atac_cols = [name_to_region[n] for n in names]
    all_rows = np.concatenate([train_rows, holdout_rows])
    train_pos = np.arange(train_rows.size)
    rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, rna_cols]
    rna_dense = np.asarray(rna_norm[all_rows].todense(), dtype=np.float32)
    scaler = StandardScaler().fit(rna_dense[train_pos])
    rna = scaler.transform(rna_dense).astype(np.float32)
    atac_raw = inputs.atac[all_rows][:, atac_cols]
    atac_tfidf, _ = _atac_tfidf(atac_raw, train_pos)
    atac = np.asarray(atac_tfidf.todense(), dtype=np.float32)
    meta = inputs.metadata.iloc[all_rows]
    label = (meta["disease"].astype(str) == LABEL_DISEASE).to_numpy(dtype=np.int64)
    donor = meta["donor_id"].astype(str).to_numpy()
    train_mask = np.zeros(all_rows.size, dtype=bool)
    train_mask[: train_rows.size] = True
    return FoldArrays(
        rna=rna, atac=atac, qc=np.zeros((all_rows.size, 5), dtype=np.float32),
        label=label, donor=donor, nuisance_codes={}, train_position=train_mask,
        gene_ids=np.asarray(selected["names"], dtype=object),
        region_ids=tuple(selected["names"]),
        evidence={"ga_n_genes": len(names), "scenario": GENE_ALIGNED_SCENARIO},
    )


def _build_model(name: str, n_genes: int, protocol, chroms, starts):
    set_all_seeds(protocol.model_seed)
    if name == "gene_aligned_ca":
        mask = build_genomic_attention_mask(chroms, starts, k=5)
        return GeneAlignedCrossAttention(
            num_genes=n_genes, dim=protocol.embed_dim, heads=protocol.n_heads,
            dropout=protocol.dropout, attn_mask=mask,
        )
    if name == "gene_aligned_tc":
        return GeneAlignedTokenConcat(
            num_genes=n_genes, dim=protocol.embed_dim, dropout=protocol.dropout,
        )
    return bench.paired_model("rna_atac_concat", [n_genes, n_genes], protocol)


def _fit_score(name, views, labels, donors, positions, protocol, chroms, starts):
    n_genes = views[VIEW_A].shape[1]
    model = _build_model(name, n_genes, protocol, chroms, starts)
    selected = {VIEW_A: views[VIEW_A], VIEW_B: views[VIEW_B]}
    trained = train_model(
        model,
        {k: v[positions["train"]] for k, v in selected.items()},
        labels[positions["train"]],
        {k: v[positions["val"]] for k, v in selected.items()},
        labels[positions["val"]],
        max_epochs=protocol.max_epochs, patience=protocol.patience,
        batch_size=protocol.batch_size, learning_rate=protocol.learning_rate,
        seed=protocol.model_seed,
        train_donor_ids=donors[positions["train"]],
        val_donor_ids=donors[positions["val"]],
    )
    _, probability = predict(
        trained.model, {k: v[positions["test"]] for k, v in selected.items()}
    )
    return bench.donor_scores(
        labels[positions["test"]], probability[:, 1], donors[positions["test"]]
    )


def run_fold(job: dict) -> dict:
    import pandas as pd
    import torch

    torch.set_num_threads(1)
    inputs = load_nn_inputs(
        job["h5ad"], job["atac"], cap=job["cap"], seed=bench.N4_PROTOCOL.sampling_seed,
        union_bed=job["bed"],
    )
    donor_all = inputs.metadata["donor_id"].astype(str).to_numpy()
    truth = (inputs.metadata["disease"].astype(str) == LABEL_DISEASE).to_numpy(dtype=np.int64)
    table = pd.DataFrame({"donor_id": donor_all, "label": fake_donor_labels(donor_all, truth)})
    folds = _fold_map(table, bench.N4_PROTOCOL)
    outer = folds[(0, job["fold"])]
    split = _indices(table, outer)
    positions = bench.fold_positions(split["train"], split["val"], split["test"])
    selected = job["selected"]
    base = matched_gene_fold(
        inputs, split["train"], positions["holdout_rows"], selected, Path(job["bed"])
    )
    records = []
    for scenario, delta in bench.gene_aligned_delta_grid():
        planted, fake = plant(base, scenario, delta, PLANT_SEED)
        views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
        for name in bench.GA_MODELS:
            common = {"scenario": scenario, "delta": delta, "fold": job["fold"], "model": name}
            try:
                score = _fit_score(
                    name, views, fake, planted.donor, positions, bench.N4_PROTOCOL,
                    selected["chromosomes"], selected["starts"],
                )
                records.append({**common, **score})
            except Exception as err:  # noqa: BLE001
                records.append({**common, "status": f"error: {type(err).__name__}: {err}"})
    return {"fold": job["fold"], "records": records}


def summarize(records: list[dict], selected: dict, cap: int) -> dict:
    regimes = bench.gene_aligned_regime_labels(records)
    any_ca = any(v["regime"] == "CA_FAVOURED" for v in regimes.values())
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "task": "P2 planted gene-aligned S6",
        "scenario": GENE_ALIGNED_SCENARIO,
        "cap": cap,
        "ga_token_cap": selected["ga_n_genes"],
        "deltas": list(bench.GENE_ALIGNED_DELTAS),
        "models": list(bench.GA_MODELS),
        "n_records": len(records),
        "n_ok": sum(1 for r in records if r.get("status") == "ok"),
        "regime_labels": regimes,
        "any_ca_favoured": any_ca,
        "finding": (
            "CA_FAVOURED in ≥1 S6 δ cell" if any_ca
            else "no CA_FAVOURED regime on gene-matched S6 (null acceptable)"
        ),
        "reading": "Planted synthetic gene-matched interaction only; no biological claim.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--only-fold", type=int, default=None)
    parser.add_argument("--out", type=Path, default=OUT_RUN)
    parser.add_argument("--docs-json", type=Path, default=OUT_JSON)
    parser.add_argument("--ga-token-cap", type=int, default=GA_TOKEN_CAP)
    args = parser.parse_args(argv)

    config = json.loads(CONFIG.read_text())["inputs"]
    selected = select_matched_genes(GA_CFG, args.ga_token_cap)
    folds = [args.only_fold] if args.only_fold is not None else list(range(5))
    jobs = [{
        "fold": fold, "cap": args.cap, "selected": selected,
        "h5ad": config["h5ad"]["path"], "atac": str(GA_ATAC), "bed": str(GA_BED),
    } for fold in folds]

    records: list[dict] = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        futures = {pool.submit(run_fold, job): job["fold"] for job in jobs}
        for fut in as_completed(futures):
            result = fut.result()
            records.extend(result["records"])
            print(f"fold {result['fold']} done: {len(result['records'])} records")

    args.out.mkdir(parents=True, exist_ok=True)
    import pandas as pd

    frame = pd.DataFrame(records).sort_values(["scenario", "delta", "fold", "model"])
    frame.to_csv(args.out / "results.csv.gz", index=False, compression="gzip")
    summary = summarize(records, selected, args.cap)
    args.docs_json.parent.mkdir(parents=True, exist_ok=True)
    args.docs_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"any_ca_favoured": summary["any_ca_favoured"],
                      "regimes": {k: v["regime"] for k, v in summary["regime_labels"].items()},
                      "n_ok": summary["n_ok"]}, indent=2))
    print(f"wrote {args.docs_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
