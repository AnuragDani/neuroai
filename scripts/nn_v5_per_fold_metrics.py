#!/usr/bin/env python3
"""V1: per-fold donor metrics (no pooling) for the canonical NN ladder.

Reads every fold JSON under ``<run>/folds``, computes donor AUROC, BA@0.5,
log-loss and class counts per fold, then mean/SD across folds plus pooled
metrics for comparison. Writes ``docs/nn_v2/v5/per_fold_metrics.json`` and
``docs/nn_v2/v5/CANONICAL_LADDER.txt``.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    log_loss,
    roc_auc_score,
)

DEFAULT_RUN = "reports/generated/nn_20260923/ladder_v3"
DEFAULT_OUT = Path("docs/nn_v2/v5")
CANONICAL_POINTER = DEFAULT_OUT / "CANONICAL_LADDER.txt"


def fold_metrics(
    labels: list[int] | np.ndarray,
    probabilities: list[float] | np.ndarray,
) -> dict[str, Any]:
    """Donor-level metrics for one fold's hold-out set."""
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if y.shape != p.shape:
        raise ValueError(f"label/prob length mismatch: {y.shape} vs {p.shape}")
    if y.size == 0:
        raise ValueError("empty fold")

    n0 = int((y == 0).sum())
    n1 = int((y == 1).sum())
    pred = (p >= 0.5).astype(int)

    auroc: float | None
    if n0 == 0 or n1 == 0:
        auroc = None
    else:
        auroc = float(roc_auc_score(y, p))

    ba: float | None
    if n0 == 0 or n1 == 0:
        ba = None
    else:
        ba = float(balanced_accuracy_score(y, pred))

    # Clip extremes so constant 0/1 majority preds stay finite.
    p_clip = np.clip(p, 1e-15, 1.0 - 1e-15)
    ll = float(log_loss(y, p_clip, labels=[0, 1]))

    return {
        "donor_auroc": auroc,
        "donor_ba": ba,
        "log_loss": ll,
        "n_donors_class_0": n0,
        "n_donors_class_1": n1,
        "n_donors": int(y.size),
    }


def _mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=0)) if arr.size > 1 else 0.0
    return mean, sd


def pooled_metrics(
    labels: list[int],
    probabilities: list[float],
) -> dict[str, float | None]:
    """Single pooled metric over all donors from all folds (artefact-prone)."""
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    n0 = int((y == 0).sum())
    n1 = int((y == 1).sum())
    pred = (p >= 0.5).astype(int)
    auroc = float(roc_auc_score(y, p)) if n0 and n1 else None
    ba = float(balanced_accuracy_score(y, pred)) if n0 and n1 else None
    p_clip = np.clip(p, 1e-15, 1.0 - 1e-15)
    ll = float(log_loss(y, p_clip, labels=[0, 1]))
    return {"pooled_auroc": auroc, "pooled_ba": ba, "pooled_log_loss": ll}


def collect_fold_records(folds_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load every fold JSON, keyed by arm name from the record."""
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    paths = sorted(folds_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no fold JSON under {folds_dir}")
    for path in paths:
        rec = json.loads(path.read_text())
        arm = rec["arm"]
        metrics = fold_metrics(rec["donor_labels"], rec["donor_probabilities"])
        by_arm[arm].append(
            {
                "repeat": int(rec["repeat"]),
                "fold": int(rec["fold"]),
                "path": str(path),
                "donor_ids": list(rec["donor_ids"]),
                "donor_labels": list(rec["donor_labels"]),
                "donor_probabilities": list(rec["donor_probabilities"]),
                **metrics,
            }
        )
    for arm in by_arm:
        by_arm[arm].sort(key=lambda r: (r["repeat"], r["fold"]))
    return dict(by_arm)


def summarize_arm(fold_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean/SD over folds plus pooled metrics for one arm."""
    aurocs = [r["donor_auroc"] for r in fold_rows if r["donor_auroc"] is not None]
    bas = [r["donor_ba"] for r in fold_rows if r["donor_ba"] is not None]
    lls = [r["log_loss"] for r in fold_rows if r["log_loss"] is not None and math.isfinite(r["log_loss"])]

    auroc_mean, auroc_sd = _mean_sd(aurocs)
    ba_mean, ba_sd = _mean_sd(bas)
    ll_mean, ll_sd = _mean_sd(lls)

    all_labels: list[int] = []
    all_probs: list[float] = []
    for r in fold_rows:
        all_labels.extend(r["donor_labels"])
        all_probs.extend(r["donor_probabilities"])
    pooled = pooled_metrics(all_labels, all_probs)

    per_fold = [
        {
            "repeat": r["repeat"],
            "fold": r["fold"],
            "donor_auroc": r["donor_auroc"],
            "donor_ba": r["donor_ba"],
            "log_loss": r["log_loss"],
            "n_donors_class_0": r["n_donors_class_0"],
            "n_donors_class_1": r["n_donors_class_1"],
            "n_donors": r["n_donors"],
        }
        for r in fold_rows
    ]

    return {
        "n_folds": len(fold_rows),
        "per_fold_auroc_mean": auroc_mean,
        "per_fold_auroc_sd": auroc_sd,
        "per_fold_ba_mean": ba_mean,
        "per_fold_ba_sd": ba_sd,
        "per_fold_log_loss_mean": ll_mean,
        "per_fold_log_loss_sd": ll_sd,
        "pooled_auroc": pooled["pooled_auroc"],
        "pooled_ba": pooled["pooled_ba"],
        "pooled_log_loss": pooled["pooled_log_loss"],
        "per_fold": per_fold,
    }


def compute_per_fold_metrics(run_dir: Path) -> dict[str, Any]:
    """Full per-arm summary for a ladder run directory."""
    folds_dir = run_dir / "folds"
    by_arm = collect_fold_records(folds_dir)
    per_arm = {arm: summarize_arm(rows) for arm, rows in sorted(by_arm.items())}
    return {
        "run": str(run_dir).replace("\\", "/"),
        "n_arms": len(per_arm),
        "per_arm": per_arm,
    }


def write_outputs(
    run_dir: Path,
    out_dir: Path,
    *,
    canonical_text: str | None = None,
) -> dict[str, Any]:
    """Compute metrics and write JSON + CANONICAL_LADDER.txt."""
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = compute_per_fold_metrics(run_dir)
    (out_dir / "per_fold_metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    text = canonical_text if canonical_text is not None else str(run_dir).replace("\\", "/")
    (out_dir / "CANONICAL_LADDER.txt").write_text(text.rstrip("\n") + "\n")
    return summary


def resolve_run_dir(explicit: Path | None = None) -> Path:
    """Prefer --run, else CANONICAL_LADDER.txt, else DEFAULT_RUN."""
    if explicit is not None:
        return explicit
    if CANONICAL_POINTER.is_file():
        text = CANONICAL_POINTER.read_text().strip()
        if text:
            return Path(text)
    return Path(DEFAULT_RUN)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    run_dir = resolve_run_dir(args.run)
    if not (run_dir / "folds").is_dir():
        raise SystemExit(f"missing folds directory under {run_dir}")
    canonical = str(run_dir).replace("\\", "/")
    summary = write_outputs(run_dir, args.out, canonical_text=canonical)
    print(f"wrote {args.out / 'per_fold_metrics.json'} ({summary['n_arms']} arms)")
    print(f"wrote {args.out / 'CANONICAL_LADDER.txt'} -> {canonical}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
