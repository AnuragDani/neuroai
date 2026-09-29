#!/usr/bin/env python3
"""X4: detectability of CA−TC donor-BA contrast at 30 donors (S4 planted).

For effect sizes δ ∈ {0.1, 0.25, 0.5, 0.75, 1.0} of an S4-type context
interaction, fit cross-attention vs token-concat on the same 30-donor 5×5
design used by the planted benchmark. Per δ and per repeat, pool the five
outer-fold test donors, compute the paired CA−TC donor balanced-accuracy
contrast with a 1,000-draw donor-cluster bootstrap (seed 22), and ask whether
the 95% CI excludes 0. Detection fraction is the share of repeats with a
non-null CI excluding 0. ``min_detectable_delta`` is the smallest δ with
fraction ≥ 0.8, else null with the statement that the contrast is not
detectable up to δ = 1.0.

Null results are valid; this does not retune the primary endpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_nn_planted_benchmark as bench  # noqa: E402
from p22.data.group_splits import aggregate_donor_probabilities  # noqa: E402
from p22.data.nn_inputs import (  # noqa: E402
    LABEL_DISEASE,
    load_nn_inputs,
    prepare_nn_fold,
    region_indices,
)
from p22.eval.planted_signal import fake_donor_labels, plant  # noqa: E402
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.training.loop import predict, train_model  # noqa: E402
from run_real_paired_comparison import _fold_map, _indices  # noqa: E402

CONFIG = ROOT / "configs" / "nn_inputs_2026-09-23.json"
OUT_RUN = ROOT / "reports/generated/nn_20260923/detectability_s4"
OUT_JSON = ROOT / "docs/nn_v2/v6/detectability.json"
OUT_MD = ROOT / "docs/nn_v2/v6/DETECTABILITY.md"
DELTAS = (0.1, 0.25, 0.5, 0.75, 1.0)
SCENARIO = "S4"
CA_MODEL = "cross_attention"
TC_MODEL = "token_concat"
MODELS = (CA_MODEL, TC_MODEL)
DETECTION_FRACTION = 0.8
BOOT_SEED = 22
N_BOOT = 1000
PLANT_SEED = 0
DEFAULT_REPEATS = 5


def detectability_protocol(n_repeats: int = DEFAULT_REPEATS):
    """N4 multiome protocol with the requested outer-repeat count."""
    return replace(bench.N4_PROTOCOL, n_repeats=int(n_repeats))


def _donor_frame(labels: np.ndarray, probabilities: np.ndarray, donors: np.ndarray) -> pd.DataFrame:
    """One row per test donor with label and mean predicted probability."""
    frame = aggregate_donor_probabilities(probabilities, donors)
    truth = pd.Series(labels, index=donors).groupby(level=0).first()
    frame["label"] = frame.donor_id.map(truth).astype(int)
    return frame[["donor_id", "label", "probability"]].reset_index(drop=True)


def _fit_donor_frame(name: str, views: dict, labels_all: np.ndarray, donors: np.ndarray,
                     positions: dict, protocol) -> pd.DataFrame:
    widths = [views[VIEW_A].shape[1], views[VIEW_B].shape[1]]
    model = bench.paired_model(name, widths, protocol)
    selected = bench.model_inputs(name, views)
    trained = train_model(
        model,
        {key: value[positions["train"]] for key, value in selected.items()},
        labels_all[positions["train"]],
        {key: value[positions["val"]] for key, value in selected.items()},
        labels_all[positions["val"]],
        max_epochs=protocol.max_epochs,
        patience=protocol.patience,
        batch_size=protocol.batch_size,
        learning_rate=protocol.learning_rate,
        seed=protocol.model_seed,
        train_donor_ids=donors[positions["train"]],
        val_donor_ids=donors[positions["val"]],
    )
    _, probability = predict(
        trained.model, {key: value[positions["test"]] for key, value in selected.items()}
    )
    return _donor_frame(labels_all[positions["test"]], probability[:, 1], donors[positions["test"]])


def ci_excludes_zero(interval: list | tuple) -> bool:
    """True when both bounds are finite and the interval does not contain 0."""
    if interval is None or len(interval) != 2:
        return False
    lo, hi = interval
    if lo is None or hi is None:
        return False
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return False
    return bool(hi < 0.0 or lo > 0.0)


def summarize_repeat_contrast(
    ca_frame: pd.DataFrame,
    tc_frame: pd.DataFrame,
    *,
    n_replicates: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> dict:
    """Paired CA−TC donor-BA contrast + CI for one repeat's pooled donors."""
    from p22.eval.metrics import MetricValue, balanced_accuracy
    from p22.eval.statistics import donor_bootstrap

    left = ca_frame.sort_values("donor_id").reset_index(drop=True)
    right = tc_frame.sort_values("donor_id").reset_index(drop=True)
    if not left["donor_id"].equals(right["donor_id"]):
        raise ValueError("CA/TC donor sets must match")
    if not np.array_equal(left["label"].to_numpy(), right["label"].to_numpy()):
        raise ValueError("CA/TC labels must match")
    labels = left["label"].to_numpy(dtype=int)
    a = (left["probability"].to_numpy() >= 0.5).astype(int)
    b = (right["probability"].to_numpy() >= 0.5).astype(int)

    def delta(truth, indices):
        first = balanced_accuracy(truth, a[indices])
        second = balanced_accuracy(truth, b[indices])
        return MetricValue(
            "paired_donor_balanced_accuracy_delta",
            first.value - second.value if first.applicable else None,
            not_applicable=first.not_applicable,
        )

    boot = donor_bootstrap(
        delta,
        labels,
        np.arange(len(labels)),
        left["donor_id"],
        n_replicates=n_replicates,
        seed=seed,
    ).to_dict()
    interval = list(boot["interval"])
    return {
        "estimate": None if boot["estimate"] is None else float(boot["estimate"]),
        "ci": [None if v is None else float(v) for v in interval],
        "ci_excludes_zero": ci_excludes_zero(interval),
        "n_donors": int(len(left)),
        "n_valid": int(boot.get("n_valid") or 0),
        "n_failed": int(boot.get("n_failed") or 0),
    }


def summarize_delta(records: list[dict], delta: float, n_repeats: int) -> dict:
    """Detection fraction and mean contrast for one δ across repeats."""
    per_repeat = []
    for repeat in range(n_repeats):
        rows = [r for r in records if r["delta"] == delta and r["repeat"] == repeat]
        if not rows:
            per_repeat.append({
                "repeat": repeat,
                "status": "missing",
                "estimate": None,
                "ci": [None, None],
                "ci_excludes_zero": False,
            })
            continue
        ca_parts, tc_parts = [], []
        status = "ok"
        for row in rows:
            if row.get("status") != "ok":
                status = row.get("status", "error")
                break
            ca_parts.append(pd.DataFrame(row["ca_donors"]))
            tc_parts.append(pd.DataFrame(row["tc_donors"]))
        if status != "ok":
            per_repeat.append({
                "repeat": repeat,
                "status": status,
                "estimate": None,
                "ci": [None, None],
                "ci_excludes_zero": False,
            })
            continue
        ca = pd.concat(ca_parts, ignore_index=True)
        tc = pd.concat(tc_parts, ignore_index=True)
        if ca["donor_id"].duplicated().any() or tc["donor_id"].duplicated().any():
            raise ValueError(f"duplicate test donors in repeat={repeat} delta={delta}")
        summary = summarize_repeat_contrast(ca, tc)
        per_repeat.append({"repeat": repeat, "status": "ok", **summary})

    ok = [r for r in per_repeat if r["status"] == "ok" and r["estimate"] is not None]
    detected = [r for r in ok if r["ci_excludes_zero"]]
    mean_contrast = (
        float(np.mean([r["estimate"] for r in ok])) if ok else None
    )
    fraction = (len(detected) / len(ok)) if ok else 0.0
    return {
        "delta": float(delta),
        "n_repeats": int(n_repeats),
        "n_repeats_ok": len(ok),
        "n_repeats_detected": len(detected),
        "detection_fraction": float(fraction),
        "mean_contrast": mean_contrast,
        "per_repeat": per_repeat,
    }


def min_detectable_delta(per_delta: list[dict], threshold: float = DETECTION_FRACTION):
    """Smallest δ with detection_fraction ≥ threshold, else None."""
    for row in sorted(per_delta, key=lambda r: r["delta"]):
        if row["detection_fraction"] >= threshold and row["n_repeats_ok"] > 0:
            return float(row["delta"])
    return None


def build_summary(records: list[dict], *, n_repeats: int, cap: int, protocol) -> dict:
    """Assemble detectability.json payload from fold records."""
    per_delta = [summarize_delta(records, delta, n_repeats) for delta in DELTAS]
    mdd = min_detectable_delta(per_delta)
    statement = (
        None
        if mdd is not None
        else "not detectable up to δ = 1.0"
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "task": "X4 detectability S4 CA−TC at 30 donors",
        "scenario": SCENARIO,
        "models": list(MODELS),
        "deltas": [float(d) for d in DELTAS],
        "n_repeats": int(n_repeats),
        "n_folds": int(protocol.n_folds),
        "n_donors": 30,
        "cap": int(cap),
        "plant_seed": PLANT_SEED,
        "bootstrap": {"n_replicates": N_BOOT, "seed": BOOT_SEED},
        "detection_threshold": DETECTION_FRACTION,
        "protocol": {
            "n_tokens": protocol.n_tokens,
            "embed_dim": protocol.embed_dim,
            "hidden_dim": protocol.hidden_dim,
            "n_heads": protocol.n_heads,
            "dropout": protocol.dropout,
            "n_repeats": protocol.n_repeats,
            "n_folds": protocol.n_folds,
            "max_epochs": protocol.max_epochs,
        },
        "protocol_sha256": protocol.fingerprint,
        "per_delta": {f"{row['delta']}": row for row in per_delta},
        "min_detectable_delta": mdd,
        "statement": statement,
        "reading": (
            "Planted S4 context-interaction only; reports when CA−TC donor-BA "
            "CI excludes 0 across repeats. No biological claim."
        ),
        "n_records": len(records),
        "n_ok": sum(1 for r in records if r.get("status") == "ok"),
    }


def write_reading(summary: dict, path: Path) -> None:
    """Write ≤30-line DETECTABILITY.md from the summary JSON."""
    lines = [
        "# Detectability (X4): S4 CA−TC at 30 donors",
        "",
        f"Scenario `{summary['scenario']}`; models "
        f"`{summary['models'][0]}` vs `{summary['models'][1]}`; "
        f"{summary['n_repeats']}×{summary['n_folds']} on 30 donors; "
        f"cap {summary['cap']}.",
        "",
        "Per δ: fraction of repeats whose donor-bootstrap CA−TC BA CI excludes 0 "
        f"(threshold {summary['detection_threshold']:.0%}).",
        "",
        "| δ | detection fraction | mean contrast | n detected / ok |",
        "| --- | --- | --- | --- |",
    ]
    for key in sorted(summary["per_delta"], key=float):
        row = summary["per_delta"][key]
        mean = row["mean_contrast"]
        mean_s = "n/a" if mean is None else f"{mean:+.4f}"
        lines.append(
            f"| {row['delta']} | {row['detection_fraction']:.2f} | {mean_s} | "
            f"{row['n_repeats_detected']}/{row['n_repeats_ok']} |"
        )
    mdd = summary["min_detectable_delta"]
    lines += [
        "",
        (
            f"**min_detectable_delta** = {mdd}"
            if mdd is not None
            else f"**min_detectable_delta** = null ({summary['statement']})"
        ),
        "",
        "Primary real-data endpoint unchanged. Planted synthetic signal only.",
        "",
    ]
    text = "\n".join(lines)
    if text.count("\n") > 30:
        raise ValueError(f"DETECTABILITY.md exceeds 30 lines ({text.count(chr(10))})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run_job(job: dict) -> dict:
    """Worker: one (repeat, fold); all deltas × CA/TC donor frames."""
    import torch

    torch.set_num_threads(1)
    protocol = detectability_protocol(job["n_repeats"])
    inputs = load_nn_inputs(
        job["h5ad"], job["atac_npz"], cap=job["cap"], seed=protocol.sampling_seed,
        union_bed=job["union_bed"],
    )
    donor = inputs.metadata["donor_id"].astype(str).to_numpy()
    truth = (inputs.metadata["disease"].astype(str) == LABEL_DISEASE).to_numpy(dtype=np.int64)
    table = pd.DataFrame({"donor_id": donor, "label": fake_donor_labels(donor, truth)})
    folds = _fold_map(table, protocol)
    outer = folds[(job["repeat"], job["fold"])]
    split = _indices(table, outer)
    positions = bench.fold_positions(split["train"], split["val"], split["test"])
    region_rows = region_indices(inputs, job["regions"])
    base = prepare_nn_fold(inputs, split["train"], positions["holdout_rows"], region_rows)
    if base.rna.shape[1] != bench.N_RNA_VIEW or base.atac.shape[1] != bench.N_ATAC_VIEW:
        raise ValueError(f"unexpected view widths {base.rna.shape[1]}, {base.atac.shape[1]}")

    records: list[dict] = []
    for delta in job["deltas"]:
        planted, fake = plant(base, SCENARIO, float(delta), PLANT_SEED)
        views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
        common = {
            "scenario": SCENARIO,
            "delta": float(delta),
            "repeat": int(job["repeat"]),
            "fold": int(job["fold"]),
        }
        try:
            from p22.eval.metrics import balanced_accuracy as _ba

            fold_donors = planted.donor  # fold-local order; not the original metadata index
            ca = _fit_donor_frame(CA_MODEL, views, fake, fold_donors, positions, protocol)
            tc = _fit_donor_frame(TC_MODEL, views, fake, fold_donors, positions, protocol)
            if list(ca["donor_id"]) != list(tc["donor_id"]):
                raise ValueError("CA/TC donor_id mismatch")
            if not np.array_equal(ca["label"].to_numpy(), tc["label"].to_numpy()):
                raise ValueError("CA/TC label mismatch")
            ca_pred = (ca["probability"].to_numpy() >= 0.5).astype(int)
            tc_pred = (tc["probability"].to_numpy() >= 0.5).astype(int)
            ca_ba = float(_ba(ca["label"].to_numpy(), ca_pred).value)
            tc_ba = float(_ba(tc["label"].to_numpy(), tc_pred).value)
            records.append({
                **common,
                "status": "ok",
                "ca_donors": ca.to_dict(orient="records"),
                "tc_donors": tc.to_dict(orient="records"),
                "ca_ba": ca_ba,
                "tc_ba": tc_ba,
                "ba_delta": ca_ba - tc_ba,
            })
        except Exception as error:  # noqa: BLE001 - record and continue
            records.append({
                **common,
                "status": f"error: {type(error).__name__}: {error}",
            })
    return {
        "repeat": job["repeat"],
        "fold": job["fold"],
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cap", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--n-repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--only-repeat", type=int, default=None)
    parser.add_argument("--only-fold", type=int, default=None)
    parser.add_argument("--out", type=Path, default=OUT_RUN)
    parser.add_argument("--docs-json", type=Path, default=OUT_JSON)
    parser.add_argument("--docs-md", type=Path, default=OUT_MD)
    parser.add_argument(
        "--from-records",
        type=Path,
        default=None,
        help="Skip fitting; summarise an existing records.json.gz",
    )
    args = parser.parse_args(argv)

    if args.n_repeats < 1 or args.n_repeats > 5:
        raise SystemExit("--n-repeats must be in 1..5")
    if args.workers > 14:
        raise SystemExit("--workers must be ≤ 14")

    protocol = detectability_protocol(args.n_repeats)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.from_records is not None:
        records = json.loads(
            Path(args.from_records).read_text()
            if args.from_records.suffix != ".gz"
            else __import__("gzip").open(args.from_records, "rt").read()
        )
        if isinstance(records, dict) and "records" in records:
            records = records["records"]
    else:
        config = json.loads(CONFIG.read_text())["inputs"]
        region_sets = json.loads(Path(config["region_sets_sha256_json"]["path"]).read_text())
        panels = {
            (int(e["repeat"]), int(e["fold"])): e["regions"] for e in region_sets["per_fold"]
        }
        repeats = (
            [args.only_repeat] if args.only_repeat is not None else list(range(args.n_repeats))
        )
        folds = [args.only_fold] if args.only_fold is not None else list(range(protocol.n_folds))
        jobs = []
        for repeat in repeats:
            for fold in folds:
                key = (repeat, fold)
                if key not in panels:
                    raise KeyError(f"missing region panel for repeat={repeat} fold={fold}")
                jobs.append({
                    "repeat": repeat,
                    "fold": fold,
                    "cap": args.cap,
                    "regions": panels[key],
                    "h5ad": config["h5ad"]["path"],
                    "atac_npz": config["atac_tiebreak_counts"]["path"],
                    "union_bed": config["tracked_union_bed"]["path"],
                    "n_repeats": args.n_repeats,
                    "deltas": list(DELTAS),
                })

        records = []
        workers = min(args.workers, len(jobs))
        print(
            f"detectability: {len(jobs)} jobs × {len(DELTAS)} deltas × "
            f"{len(MODELS)} models; workers={workers}"
        )
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_job, job): (job["repeat"], job["fold"]) for job in jobs}
            for future in as_completed(futures):
                repeat, fold = futures[future]
                result = future.result()
                records.extend(result["records"])
                n_ok = sum(1 for r in result["records"] if r.get("status") == "ok")
                print(
                    f"repeat {repeat} fold {fold} done: "
                    f"{n_ok}/{len(result['records'])} ok",
                    flush=True,
                )

        raw_path = args.out / "records.json.gz"
        import gzip

        with gzip.open(raw_path, "wt") as handle:
            json.dump(records, handle)
        print(f"wrote {raw_path} ({len(records)} records)")

    summary = build_summary(records, n_repeats=args.n_repeats, cap=args.cap, protocol=protocol)
    args.docs_json.parent.mkdir(parents=True, exist_ok=True)
    args.docs_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_reading(summary, args.docs_md)
    (args.out / "detectability.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote {args.docs_json} and {args.docs_md}")
    print(
        json.dumps(
            {
                "min_detectable_delta": summary["min_detectable_delta"],
                "statement": summary["statement"],
                "per_delta": {
                    k: {
                        "detection_fraction": v["detection_fraction"],
                        "mean_contrast": v["mean_contrast"],
                    }
                    for k, v in summary["per_delta"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
