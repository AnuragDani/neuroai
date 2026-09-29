#!/usr/bin/env python3
"""X3: per-fold R3_ca − R3_tc donor AUROC/BA contrast (prespecified sensitivity).

For each of the 25 folds, compute donor AUROC and BA for R3_ca and R3_tc, then
their difference. The estimate is the mean over folds. The 95% CI uses a
1,000-draw donor-cluster bootstrap that preserves fold membership within each
repeat (seed 22): resample the 30 donors with replacement, recompute each fold
metric on the resampled donors that fall in that fold, and average valid fold
contrasts.

Writes ``docs/nn_v2/v6/per_fold_contrast.json`` for the canonical ladder_v3 and,
when present, also summarises ``ladder_v4_chr21forced``.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from sklearn.metrics import balanced_accuracy_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "reports/generated/nn_20260923/ladder_v3"
DEFAULT_RUN_V4 = ROOT / "reports/generated/nn_20260923/ladder_v4_chr21forced"
DEFAULT_OUT = ROOT / "docs/nn_v2/v6/per_fold_contrast.json"
CA_ARM = "R3_ca"
TC_ARM = "R3_tc"
N_BOOT = 1000
BOOT_SEED = 22


def _donor_auroc(labels: list[int], probs: list[float]) -> float | None:
    if len(set(labels)) < 2:
        return None
    return float(roc_auc_score(labels, probs))


def _donor_ba(labels: list[int], probs: list[float]) -> float | None:
    if len(set(labels)) < 2:
        return None
    pred = [1 if p >= 0.5 else 0 for p in probs]
    return float(balanced_accuracy_score(labels, pred))


def _metric(labels: list[int], probs: list[float], name: str) -> float | None:
    if name == "donor_ba":
        return _donor_ba(labels, probs)
    if name == "donor_auroc":
        return _donor_auroc(labels, probs)
    raise ValueError(f"unknown metric {name!r}")


def load_paired_folds(
    run_dir: Path,
    *,
    ca_arm: str = CA_ARM,
    tc_arm: str = TC_ARM,
) -> list[dict[str, Any]]:
    """Load paired CA/TC fold records sorted by (repeat, fold)."""
    folds_dir = run_dir / "folds"
    if not folds_dir.is_dir():
        raise FileNotFoundError(f"missing folds directory under {run_dir}")

    by_key: dict[tuple[int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for path in sorted(folds_dir.glob("*.json")):
        rec = json.loads(path.read_text())
        arm = rec.get("arm")
        if arm not in (ca_arm, tc_arm):
            continue
        key = (int(rec["repeat"]), int(rec["fold"]))
        by_key[key][arm] = rec

    paired: list[dict[str, Any]] = []
    for (repeat, fold), arms in sorted(by_key.items()):
        if ca_arm not in arms or tc_arm not in arms:
            raise ValueError(f"incomplete CA/TC pair at repeat={repeat} fold={fold}")
        ca, tc = arms[ca_arm], arms[tc_arm]
        if list(ca["donor_ids"]) != list(tc["donor_ids"]):
            raise ValueError(f"donor_ids mismatch at repeat={repeat} fold={fold}")
        if list(ca["donor_labels"]) != list(tc["donor_labels"]):
            raise ValueError(f"donor_labels mismatch at repeat={repeat} fold={fold}")
        labels = [int(y) for y in ca["donor_labels"]]
        ca_probs = [float(p) for p in ca["donor_probabilities"]]
        tc_probs = [float(p) for p in tc["donor_probabilities"]]
        donor_ids = [str(d) for d in ca["donor_ids"]]
        auroc_ca = _donor_auroc(labels, ca_probs)
        auroc_tc = _donor_auroc(labels, tc_probs)
        ba_ca = _donor_ba(labels, ca_probs)
        ba_tc = _donor_ba(labels, tc_probs)
        paired.append(
            {
                "repeat": repeat,
                "fold": fold,
                "donor_ids": donor_ids,
                "donor_labels": labels,
                "ca_probs": ca_probs,
                "tc_probs": tc_probs,
                "donor_auroc_ca": auroc_ca,
                "donor_auroc_tc": auroc_tc,
                "donor_auroc_delta": (
                    None if auroc_ca is None or auroc_tc is None else auroc_ca - auroc_tc
                ),
                "donor_ba_ca": ba_ca,
                "donor_ba_tc": ba_tc,
                "donor_ba_delta": None if ba_ca is None or ba_tc is None else ba_ca - ba_tc,
            }
        )
    if len(paired) != 25:
        raise ValueError(f"expected 25 paired folds, got {len(paired)} under {run_dir}")
    return paired


def _per_fold_public(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "repeat": r["repeat"],
            "fold": r["fold"],
            "donor_auroc_ca": r["donor_auroc_ca"],
            "donor_auroc_tc": r["donor_auroc_tc"],
            "donor_auroc_delta": r["donor_auroc_delta"],
            "donor_ba_ca": r["donor_ba_ca"],
            "donor_ba_tc": r["donor_ba_tc"],
            "donor_ba_delta": r["donor_ba_delta"],
        }
        for r in rows
    ]


def _mean_delta(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r[key] for r in rows if r[key] is not None]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _build_repeat_maps(
    rows: list[dict[str, Any]],
) -> tuple[list[str], dict[int, dict[str, tuple[int, int, float, float]]]]:
    """donor list + per-repeat map: donor -> (label, fold, p_ca, p_tc)."""
    by_repeat: dict[int, dict[str, tuple[int, int, float, float]]] = defaultdict(dict)
    for r in rows:
        rep = int(r["repeat"])
        fold = int(r["fold"])
        for donor, y, pca, ptc in zip(
            r["donor_ids"], r["donor_labels"], r["ca_probs"], r["tc_probs"], strict=True
        ):
            by_repeat[rep][str(donor)] = (int(y), fold, float(pca), float(ptc))
    donors = sorted(next(iter(by_repeat.values())))
    for rep, mp in by_repeat.items():
        if sorted(mp) != donors:
            raise ValueError(f"donor set mismatch at repeat={rep}")
        if len(mp) != 30:
            raise ValueError(f"expected 30 donors in repeat={rep}, got {len(mp)}")
    return donors, dict(by_repeat)


def _fold_contrast_from_sample(
    sample: list[str],
    donor_map: dict[str, tuple[int, int, float, float]],
    metric: str,
) -> list[float]:
    """Compute per-fold CA−TC contrasts for one repeat on a donor sample."""
    by_fold: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
    for donor in sample:
        if donor not in donor_map:
            continue
        y, fold, pca, ptc = donor_map[donor]
        by_fold[fold].append((y, pca, ptc))
    contrasts: list[float] = []
    for fold in sorted(by_fold):
        trips = by_fold[fold]
        labels = [t[0] for t in trips]
        ca_probs = [t[1] for t in trips]
        tc_probs = [t[2] for t in trips]
        ca_m = _metric(labels, ca_probs, metric)
        tc_m = _metric(labels, tc_probs, metric)
        if ca_m is None or tc_m is None:
            continue
        contrasts.append(ca_m - tc_m)
    return contrasts


def donor_cluster_bootstrap_ci(
    rows: list[dict[str, Any]],
    *,
    metric: str,
    n_draws: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> tuple[list[float], int]:
    """95% CI via donor-cluster bootstrap over folds within repeats."""
    donors, by_repeat = _build_repeat_maps(rows)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(n_draws):
        sample = [rng.choice(donors) for _ in donors]
        fold_contrasts: list[float] = []
        for rep in sorted(by_repeat):
            fold_contrasts.extend(
                _fold_contrast_from_sample(sample, by_repeat[rep], metric)
            )
        if fold_contrasts:
            draws.append(float(sum(fold_contrasts) / len(fold_contrasts)))
    if not draws:
        raise RuntimeError("donor-cluster bootstrap produced no valid draws")
    draws.sort()
    lo = draws[int(0.025 * len(draws))]
    hi = draws[int(0.975 * len(draws)) - 1]
    return [float(lo), float(hi)], len(draws)


def summarize_run(
    run_dir: Path,
    *,
    metric: str = "donor_ba",
    n_draws: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Per-fold contrast summary for one ladder run directory."""
    rows = load_paired_folds(run_dir)
    delta_key = "donor_ba_delta" if metric == "donor_ba" else "donor_auroc_delta"
    estimate = _mean_delta(rows, delta_key)
    if estimate is None:
        raise RuntimeError(f"no valid per-fold {metric} contrasts under {run_dir}")
    ci, n_valid = donor_cluster_bootstrap_ci(
        rows, metric=metric, n_draws=n_draws, seed=seed
    )
    auroc_est = _mean_delta(rows, "donor_auroc_delta")
    auroc_ci, auroc_valid = donor_cluster_bootstrap_ci(
        rows, metric="donor_auroc", n_draws=n_draws, seed=seed
    )
    return {
        "run": str(run_dir).replace("\\", "/"),
        "metric": metric,
        "estimate": estimate,
        "ci": ci,
        "n_folds": len(rows),
        "bootstrap_draws": n_draws,
        "bootstrap_seed": seed,
        "valid_draws": n_valid,
        "per_fold": _per_fold_public(rows),
        "donor_auroc": {
            "estimate": auroc_est,
            "ci": auroc_ci,
            "valid_draws": auroc_valid,
        },
    }


def write_per_fold_contrast(
    out_path: Path,
    *,
    run_v3: Path = DEFAULT_RUN,
    run_v4: Path | None = DEFAULT_RUN_V4,
    metric: str = "donor_ba",
    n_draws: int = N_BOOT,
    seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Write the X3 JSON for ladder_v3 and optionally ladder_v4_chr21forced."""
    payload = summarize_run(run_v3, metric=metric, n_draws=n_draws, seed=seed)
    payload["record_type"] = "nn_v6_per_fold_contrast"
    payload["prespecified_sensitivity"] = True
    payload["primary_endpoint_unchanged"] = True
    if run_v4 is not None and (run_v4 / "folds").is_dir():
        payload["ladder_v4_chr21forced"] = summarize_run(
            run_v4, metric=metric, n_draws=n_draws, seed=seed
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--run-v4", type=Path, default=DEFAULT_RUN_V4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--metric", choices=("donor_ba", "donor_auroc"), default="donor_ba")
    parser.add_argument("--bootstrap-draws", type=int, default=N_BOOT)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOT_SEED)
    parser.add_argument("--skip-v4", action="store_true")
    args = parser.parse_args(argv)
    run_v4 = None if args.skip_v4 else args.run_v4
    payload = write_per_fold_contrast(
        args.out,
        run_v3=args.run,
        run_v4=run_v4,
        metric=args.metric,
        n_draws=args.bootstrap_draws,
        seed=args.bootstrap_seed,
    )
    print(
        json.dumps(
            {
                "out": str(args.out),
                "estimate": payload["estimate"],
                "ci": payload["ci"],
                "metric": payload["metric"],
                "has_v4": "ladder_v4_chr21forced" in payload,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
