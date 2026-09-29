"""N4 planted-signal benchmark: five fusion heads on injected synthetic signal.

Pure planted-signal sanity check, not a biological claim. For each of five
predeclared outer donor folds and each scenario x delta cell, a label-free
signal is planted *after* train-only fold preprocessing, and five models are
fit: ``logreg_concat`` (donor-weighted logistic regression) and the four neural
fusion families (``rna_atac_concat``, ``gated_fusion``, ``token_concat``,
``cross_attention``). Donor-level balanced accuracy, AUROC and log-loss are
recorded.

P2 / D3 adds helpers ``gene_aligned_delta_grid`` / ``gene_aligned_regime_labels``
and ``GA_MODELS`` for the S6 gene-matched RNA×ATAC interaction regime; the
runner is ``scripts/nn_v5_planted_gene_aligned.py``.

Outer and inner folds are stratified by the *fake* planted label (grouped by
donor), not the true disease label: the fake label alternates within each true
group, so a true-stratified split can leave a single fake class in a test or
validation split and break balanced accuracy. Fake labels are hash-identical
across scenarios, so the folds are identical across scenario x delta cells and
the cells stay comparable. Test donors never enter any fit or selection step.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import log_loss, roc_auc_score  # noqa: E402

from p22.data.group_splits import aggregate_donor_probabilities  # noqa: E402
from p22.data.nn_inputs import (  # noqa: E402
    LABEL_DISEASE,
    load_nn_inputs,
    prepare_nn_fold,
    region_indices,
)
from p22.eval.metrics import balanced_accuracy  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.multiome_runner import model_inputs, paired_model  # noqa: E402
from p22.eval.planted_signal import (  # noqa: E402
    GENE_ALIGNED_SCENARIO,
    SCENARIOS,
    fake_donor_labels,
    plant,
)
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.training.loop import predict, train_model  # noqa: E402
from run_real_paired_comparison import _fold_map, _indices  # noqa: E402
from run_real_paired_linear_controls import donor_cell_weights, fit_logistic  # noqa: E402

CONFIG = ROOT / "configs" / "nn_inputs_2026-09-23.json"
N_RNA_VIEW, N_ATAC_VIEW = 2000, 256
DELTAS = (0.25, 0.5, 1.0)
GENE_ALIGNED_DELTAS = (0.5, 1.0)
NEURAL_MODELS = ("rna_atac_concat", "gated_fusion", "token_concat", "cross_attention")
MODELS = ("logreg_concat", *NEURAL_MODELS)
# P2 / D3: gene-aligned CA vs matched token-concat vs MLP on S6.
GA_MODELS = ("gene_aligned_ca", "gene_aligned_tc", "rna_atac_concat")
PLANT_SEED = 0
N4_PROTOCOL = MultiomeProtocol(
    n_tokens=8, embed_dim=32, hidden_dim=128, n_heads=4, dropout=0.2,
    n_repeats=1, n_folds=5, split_seed=0, model_seed=0, sampling_seed=22,
)


def delta_grid() -> list[tuple[str, float]]:
    """The 16 scenario x delta cells: S0 null plus S1-S5 at three deltas."""
    cells = [(SCENARIOS[0], 0.0)]
    for scenario in SCENARIOS[1:]:
        cells.extend((scenario, delta) for delta in DELTAS)
    return cells


def gene_aligned_delta_grid() -> list[tuple[str, float]]:
    """P2 S6 gene-matched interaction cells at δ ∈ {0.5, 1.0}."""
    return [(GENE_ALIGNED_SCENARIO, delta) for delta in GENE_ALIGNED_DELTAS]


def gene_aligned_regime_labels(records: list[dict]) -> dict:
    """N4 CA_FAVOURED rule on gene-aligned CA vs non-attention (tc + MLP)."""
    frame = pd.DataFrame([r for r in records if r["status"] == "ok"])
    out = {}
    if frame.empty:
        return out
    for (scenario, delta), group in frame.groupby(["scenario", "delta"]):
        means = group.groupby("model")["donor_balanced_accuracy"].mean()
        present = [m for m in GA_MODELS if m in means.index]
        best = float(means[present].max()) if present else float("nan")
        non_attn = [m for m in ("gene_aligned_tc", "rna_atac_concat") if m in means.index]
        best_non = float(means[non_attn].max()) if non_attn else float("nan")
        cross = (
            float(means["gene_aligned_ca"]) if "gene_aligned_ca" in means.index
            else float("nan")
        )
        if "rna_atac_concat" in means.index and float(means["rna_atac_concat"]) >= best - 0.03:
            label = "LINEAR_SUFFICIENT"
        elif non_attn and np.isfinite(cross) and cross - best_non >= 0.07:
            label = "CA_FAVOURED"
        elif "gene_aligned_tc" in means.index and float(means["gene_aligned_tc"]) >= best - 0.03:
            label = "MLP_FAVOURED"
        else:
            label = "NONE_DETECT"
        out[f"{scenario}@{delta}"] = {
            "regime": label,
            "n_models_scored": len(present),
            "mean_balanced_accuracy": {k: round(float(v), 4) for k, v in means.items()},
            "cross_attention_minus_best_non_attention": round(cross - best_non, 4),
        }
    return out



def fold_positions(train_rows: np.ndarray, val_rows: np.ndarray, test_rows: np.ndarray) -> dict:
    """Map split rows into ``prepare_nn_fold`` row order [train, val, test]."""
    holdout = np.concatenate([val_rows, test_rows])
    train = np.arange(train_rows.size)
    val = train_rows.size + np.arange(val_rows.size)
    test = train_rows.size + val_rows.size + np.arange(test_rows.size)
    return {"train": train, "val": val, "test": test, "holdout_rows": holdout}


def donor_scores(labels: np.ndarray, probabilities: np.ndarray, donors: np.ndarray) -> dict:
    """Aggregate cell probabilities per donor and score donor-level metrics."""
    frame = aggregate_donor_probabilities(probabilities, donors)
    truth = pd.Series(labels, index=donors).groupby(level=0).first()
    frame["label"] = frame.donor_id.map(truth).astype(int)
    y = frame["label"].to_numpy(dtype=int)
    p = frame["probability"].to_numpy(dtype=float)
    if set(np.unique(y)) != {0, 1}:
        return {"donor_balanced_accuracy": None, "donor_auroc": None,
                "donor_log_loss": None, "n_test_donors": int(len(y)), "status": "single_class"}
    return {
        "donor_balanced_accuracy": balanced_accuracy(frame.label, frame.prediction).value,
        "donor_auroc": float(roc_auc_score(y, p)),
        "donor_log_loss": float(log_loss(y, p, labels=[0, 1])),
        "n_test_donors": int(len(y)),
        "status": "ok",
    }


def regime_labels(records: list[dict]) -> dict:
    """Classify each cell by the predeclared decision-tree rules.

    Only models whose fit succeeded (``status == "ok"``) enter a cell. If a
    model is missing from a cell the rule falls through to the remaining
    families rather than raising, so a partial run still produces a summary.
    """
    frame = pd.DataFrame([r for r in records if r["status"] == "ok"])
    out = {}
    if frame.empty:
        return out
    for (scenario, delta), group in frame.groupby(["scenario", "delta"]):
        means = group.groupby("model")["donor_balanced_accuracy"].mean()

        def has(*names, _idx=means.index):
            return [m for m in names if m in _idx]

        present = has(*MODELS)
        best = float(means[present].max()) if present else float("nan")
        non_attention = has("logreg_concat", *NEURAL_MODELS[:-1])
        best_non = float(means[non_attention].max()) if non_attention else float("nan")
        cross = (
            float(means["cross_attention"]) if "cross_attention" in means.index
            else float("nan")
        )
        mlp_family = has("rna_atac_concat", "gated_fusion")

        if "logreg_concat" in means.index and float(means["logreg_concat"]) >= best - 0.03:
            label = "LINEAR_SUFFICIENT"
        elif non_attention and np.isfinite(cross) and cross - best_non >= 0.07:
            label = "CA_FAVOURED"
        elif mlp_family and float(means[mlp_family].max()) >= best - 0.03:
            label = "MLP_FAVOURED"
        else:
            label = "NONE_DETECT"
        out[f"{scenario}@{delta}"] = {
            "regime": label,
            "n_models_scored": len(present),
            "mean_balanced_accuracy": {k: round(float(v), 4) for k, v in means.items()},
            "cross_attention_minus_best_non_attention": round(cross - best_non, 4),
        }
    return out


def acceptance_checks(records: list[dict]) -> dict:
    """S0 leak check, S1 sanity at delta 1.0, S5 near-chance at delta 1.0."""
    frame = pd.DataFrame([r for r in records if r["status"] == "ok"])
    means = frame.groupby(["scenario", "delta", "model"])["donor_balanced_accuracy"].mean()

    def at(scenario, delta):
        key = (scenario, delta)
        if key not in means.index.droplevel("model").unique():
            return None
        return means.xs(key, level=["scenario", "delta"])

    s0, s1, s5 = at("S0", 0.0), at("S1", 1.0), at("S5", 1.0)
    checks = {}
    checks["s0_null_within_0p35_0p65"] = (
        None if s0 is None else bool(float(s0.min()) >= 0.35 and float(s0.max()) <= 0.65)
    )
    checks["s0_range"] = None if s0 is None else [
        round(float(s0.min()), 4), round(float(s0.max()), 4)
    ]
    checks["s1_delta1_all_models_at_least_0p9"] = (
        None if s1 is None else bool(s1.min() >= 0.9)
    )
    checks["s1_delta1_min"] = None if s1 is None else round(float(s1.min()), 4)
    checks["s5_delta1_within_0p05_of_chance"] = (
        None if s5 is None else bool((s5 - 0.5).abs().max() <= 0.05)
    )
    checks["s5_delta1_max_deviation"] = (
        None if s5 is None else round(float((s5 - 0.5).abs().max()), 4)
    )
    return checks


def _load_job_inputs(job: dict):
    inputs = load_nn_inputs(
        job["h5ad"], job["atac_npz"], cap=job["cap"], seed=N4_PROTOCOL.sampling_seed,
        union_bed=job["union_bed"],
    )
    return inputs


def _fit_and_score(name: str, views: dict, labels_all: np.ndarray, donors: np.ndarray,
                   positions: dict, protocol: MultiomeProtocol) -> dict:
    if name == "logreg_concat":
        matrix = np.hstack([views[VIEW_A], views[VIEW_B]])
        weights = donor_cell_weights(donors[positions["train"]])
        estimator, _ = fit_logistic(
            matrix[positions["train"]], labels_all[positions["train"]], weights
        )
        probability = estimator.predict_proba(matrix[positions["test"]])[:, 1]
    else:
        widths = [views[VIEW_A].shape[1], views[VIEW_B].shape[1]]
        model = paired_model(name, widths, protocol)
        selected = model_inputs(name, views)
        trained = train_model(
            model,
            {key: value[positions["train"]] for key, value in selected.items()},
            labels_all[positions["train"]],
            {key: value[positions["val"]] for key, value in selected.items()},
            labels_all[positions["val"]],
            max_epochs=protocol.max_epochs, patience=protocol.patience,
            batch_size=protocol.batch_size, learning_rate=protocol.learning_rate,
            seed=protocol.model_seed,
            train_donor_ids=donors[positions["train"]],
            val_donor_ids=donors[positions["val"]],
        )
        _, probability = predict(
            trained.model, {key: value[positions["test"]] for key, value in selected.items()}
        )
        probability = probability[:, 1]
    return donor_scores(labels_all[positions["test"]], probability, donors[positions["test"]])


def run_fold(job: dict) -> dict:
    """Worker: one outer fold, all 16 cells x 5 models, in-process."""
    import torch

    torch.set_num_threads(2)
    inputs = _load_job_inputs(job)
    donor = inputs.metadata["donor_id"].astype(str).to_numpy()
    truth = (inputs.metadata["disease"].astype(str) == LABEL_DISEASE).to_numpy(dtype=np.int64)
    table = pd.DataFrame({"donor_id": donor, "label": fake_donor_labels(donor, truth)})
    folds = _fold_map(table, N4_PROTOCOL)
    outer = folds[(0, job["fold"])]
    split = _indices(table, outer)
    panel = job["regions"]
    region_rows = region_indices(inputs, panel)
    positions = fold_positions(split["train"], split["val"], split["test"])
    base = prepare_nn_fold(inputs, split["train"], positions["holdout_rows"], region_rows)
    if base.rna.shape[1] != N_RNA_VIEW or base.atac.shape[1] != N_ATAC_VIEW:
        raise ValueError(f"unexpected view widths {base.rna.shape[1]}, {base.atac.shape[1]}")

    records: list[dict] = []
    for scenario, delta in delta_grid():
        planted, fake = plant(base, scenario, delta, PLANT_SEED)
        views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
        for name in MODELS:
            common = {"scenario": scenario, "delta": delta, "fold": job["fold"], "model": name}
            try:
                score = _fit_and_score(name, views, fake, donor, positions, N4_PROTOCOL)
                records.append({**common, **score})
            except Exception as error:  # noqa: BLE001 - record and continue
                records.append({**common, "status": f"error: {type(error).__name__}: {error}"})
    return {"fold": job["fold"], "n_train_donors": int(len(set(donor[positions["train"]]))),
            "n_test_donors": int(len(set(donor[positions["test"]]))), "records": records}


def write_results(records: list[dict], summary: dict, out_dir: Path, docs_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(records).sort_values(["scenario", "delta", "fold", "model"])
    frame.to_csv(out_dir / "results.csv.gz", index=False, compression="gzip")
    summary["n_records"] = int(len(frame))
    (docs_dir / "planted_benchmark.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    ok = frame[frame["status"] == "ok"]
    lines = ["# Planted-signal benchmark (N4)", "", summary["reading"], ""]
    for scenario in SCENARIOS:
        lines += [f"## {scenario}", "",
                  "| delta | model | donor BA (mean +/- SD) | AUROC | log-loss |",
                  "| --- | --- | --- | --- | --- |"]
        for delta in ([0.0] if scenario == SCENARIOS[0] else list(DELTAS)):
            block = ok[(ok.scenario == scenario) & (ok.delta == delta)]
            for name in MODELS:
                rows = block[block.model == name]
                if rows.empty:
                    lines.append(f"| {delta} | {name} | -- | -- | -- |")
                    continue
                ba_mean = rows.donor_balanced_accuracy.mean()
                ba_sd = rows.donor_balanced_accuracy.std()
                lines.append(
                    f"| {delta} | {name} | {ba_mean:.3f} +/- {ba_sd:.3f} | "
                    f"{rows.donor_auroc.mean():.3f} | {rows.donor_log_loss.mean():.3f} |"
                )
        lines.append("")
    (docs_dir / "PLANTED_BENCHMARK.md").write_text("\n".join(lines))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=1000)
    parser.add_argument("--out", type=Path, default=ROOT / "reports/generated/nn_20260923/planted")
    parser.add_argument("--docs-dir", type=Path, default=ROOT / "docs/nn_v2")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--only-fold", type=int, default=None)
    args = parser.parse_args(argv)

    config = json.loads(CONFIG.read_text())["inputs"]
    region_sets = json.loads(Path(config["region_sets_sha256_json"]["path"]).read_text())
    panels = {e["fold"]: e["regions"] for e in region_sets["per_fold"] if e["repeat"] == 0}
    folds = [args.only_fold] if args.only_fold is not None else sorted(panels)
    jobs = [{
        "fold": fold, "cap": args.cap, "regions": panels[fold],
        "h5ad": config["h5ad"]["path"], "atac_npz": config["atac_tiebreak_counts"]["path"],
        "union_bed": config["tracked_union_bed"]["path"],
    } for fold in folds]

    records: list[dict] = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(jobs))) as pool:
        futures = {pool.submit(run_fold, job): job["fold"] for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            records.extend(result["records"])
            print(f"fold {result['fold']} done: {len(result['records'])} records "
                  f"({result['n_train_donors']} train / {result['n_test_donors']} test donors)")

    raw = pd.DataFrame(records).sort_values(["scenario", "delta", "fold", "model"])
    args.out.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out / "results.csv.gz", index=False, compression="gzip")
    bad = raw[raw["status"] != "ok"]
    print(f"status: {len(raw) - len(bad)} ok / {len(bad)} non-ok of {len(raw)}")
    for status, count in bad["status"].value_counts().items():
        print(f"  {count}x {status}")

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "task": "N4 planted-signal benchmark",
        "cap": args.cap,
        "plant_seed": PLANT_SEED,
        "protocol": {"n_tokens": N4_PROTOCOL.n_tokens, "embed_dim": N4_PROTOCOL.embed_dim,
                     "hidden_dim": N4_PROTOCOL.hidden_dim, "n_heads": N4_PROTOCOL.n_heads,
                     "dropout": N4_PROTOCOL.dropout, "n_repeats": N4_PROTOCOL.n_repeats,
                     "n_folds": N4_PROTOCOL.n_folds},
        "protocol_sha256": N4_PROTOCOL.fingerprint,
        "delta_grid": [f"{s}@{d}" for s, d in delta_grid()],
        "regime_labels": regime_labels(records),
        "acceptance_checks": acceptance_checks(records),
        "reading": "Planted synthetic signal only; no biological or clinical claim.",
    }
    write_results(records, summary, args.out, args.docs_dir)
    print(f"wrote {args.out / 'results.csv.gz'} and {args.docs_dir / 'PLANTED_BENCHMARK.md'}")
    print(json.dumps(summary["acceptance_checks"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())