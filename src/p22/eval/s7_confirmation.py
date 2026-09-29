"""Frozen S7 confirmation gates (no fitting).

Ten predeclared rho=1 generator seeds. Per-trial joint success requires
estimate >= margin AND 95% CI lower > 0 for CA−TC and for CA versus every
non-attention baseline (intersection-union). Incomplete coverage never
passes as favourable. >=8/10 is exploratory synthetic reliability only —
not biological power.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from p22.eval.s7_ledger import S7_MODELS, S7_N_FOLDS, make_fit_id
from p22.eval.s7_screen import S7_NON_ATTENTION

# Mirrors tasks/nn/finish_20260928/BENCHMARK_SPEC.json confirmation + evaluation.
S7_CONFIRM_SEEDS: tuple[int, ...] = tuple(range(2001, 2011))
S7_CONFIRM_N = 10
S7_CONFIRM_RHO = 1.0
S7_CONFIRM_FITS = 350  # 10 seeds × 5 folds × 7 models
S7_CA_MARGIN = 0.07
S7_RELIABILITY_MIN = 8
S7_WILSON_Z = 1.959963984540054  # ~N(0,1) 97.5th percentile

CONFIRM_SKIPPED = "CONFIRM_SKIPPED"
CONFIRM_INCOMPLETE = "CONFIRM_INCOMPLETE"
CONFIRM_NEGATIVE = "CONFIRM_NEGATIVE"
CONFIRM_RELIABLE = "CONFIRM_RELIABLE"

assert len(S7_CONFIRM_SEEDS) == S7_CONFIRM_N
assert S7_CONFIRM_N * S7_N_FOLDS * len(S7_MODELS) == S7_CONFIRM_FITS


def enumerate_confirmation_jobs(
    *,
    seeds: tuple[int, ...] = S7_CONFIRM_SEEDS,
    rho: float = S7_CONFIRM_RHO,
    n_folds: int = S7_N_FOLDS,
    models: tuple[str, ...] = S7_MODELS,
) -> list[dict[str, Any]]:
    """Predeclared confirmation jobs: |seeds| × folds × models (350 frozen)."""
    jobs: list[dict[str, Any]] = []
    for seed in seeds:
        for fold in range(int(n_folds)):
            for model in models:
                fit_id = make_fit_id("confirm", rho, int(seed), fold, model)
                jobs.append(
                    {
                        "fit_id": fit_id,
                        "stage": "confirm",
                        "rho": float(rho),
                        "generator_seed": int(seed),
                        "fold": int(fold),
                        "model": model,
                    }
                )
    return jobs


def joint_success(
    estimate: float | None,
    ci_lower: float | None,
    *,
    margin: float = S7_CA_MARGIN,
) -> bool:
    """Spec joint success: estimate >= margin AND CI lower > 0.

    Negative or zero lower bounds never count, even if estimate clears margin.
    Missing values never succeed.
    """
    if estimate is None or ci_lower is None:
        return False
    return float(estimate) >= float(margin) and float(ci_lower) > 0.0


def wilson_interval(
    successes: int,
    n: int,
    *,
    z: float = S7_WILSON_Z,
) -> dict[str, Any]:
    """Wilson score 95% interval for a binomial proportion."""
    k = int(successes)
    total = int(n)
    if total < 1:
        raise ValueError(f"n must be >= 1, got {total}")
    if k < 0 or k > total:
        raise ValueError(f"successes must be in [0, n], got {k} of {total}")
    z2 = float(z) * float(z)
    phat = k / total
    denom = 1.0 + z2 / total
    center = (phat + z2 / (2.0 * total)) / denom
    half = (
        float(z)
        * float(np.sqrt((phat * (1.0 - phat) + z2 / (4.0 * total)) / total))
        / denom
    )
    lower = float(max(0.0, center - half))
    upper = float(min(1.0, center + half))
    # Guard float drift so k==n / k==0 clamp exactly to the unit interval.
    if k == 0:
        lower = 0.0
    if k == total:
        upper = 1.0
    return {
        "successes": k,
        "n": total,
        "rate": float(phat),
        "lower": lower,
        "upper": upper,
        "z": float(z),
    }


def confirmation_coverage(
    records: Sequence[Mapping[str, Any]],
    *,
    seeds: tuple[int, ...] = S7_CONFIRM_SEEDS,
    rho: float = S7_CONFIRM_RHO,
    n_folds: int = S7_N_FOLDS,
    models: tuple[str, ...] = S7_MODELS,
) -> dict[str, Any]:
    """Require every predeclared confirm fit_id with status ok."""
    expected = {
        job["fit_id"]
        for job in enumerate_confirmation_jobs(
            seeds=seeds, rho=rho, n_folds=n_folds, models=models
        )
    }
    present: set[str] = set()
    for raw in records:
        if raw.get("status") != "ok":
            continue
        fit_id = raw.get("fit_id")
        if fit_id is None:
            fit_id = make_fit_id(
                "confirm",
                float(raw["rho"]),
                int(raw["generator_seed"]),
                int(raw["fold"]),
                str(raw["model"]),
            )
        present.add(str(fit_id))
    missing = sorted(expected - present)
    return {
        "complete": len(missing) == 0,
        "n_expected": len(expected),
        "n_present": len(present & expected),
        "missing_fit_ids": missing,
    }


def trial_all_baseline_success(
    contrasts: Mapping[str, Mapping[str, Any]],
    *,
    primary: str = "token_concat",
    baselines: tuple[str, ...] = S7_NON_ATTENTION,
    margin: float = S7_CA_MARGIN,
) -> dict[str, Any]:
    """Intersection-union: joint success vs primary and every baseline.

    ``contrasts`` maps comparator name -> {estimate, lower} for CA − comparator.
    """
    per: dict[str, bool] = {}
    for name in baselines:
        row = contrasts.get(name)
        if row is None:
            per[name] = False
            continue
        per[name] = joint_success(
            row.get("estimate"),
            row.get("lower"),
            margin=margin,
        )
    ca_tc = bool(per.get(primary, False))
    all_baselines = all(per[name] for name in baselines) if baselines else False
    return {
        "ca_tc_success": ca_tc,
        "all_baseline_success": all_baselines,
        "per_baseline": per,
    }


def evaluate_confirmation(
    trial_contrasts: Sequence[Mapping[str, Any]],
    *,
    eligible: bool,
    seeds: tuple[int, ...] = S7_CONFIRM_SEEDS,
    baselines: tuple[str, ...] = S7_NON_ATTENTION,
    margin: float = S7_CA_MARGIN,
    reliability_min: int = S7_RELIABILITY_MIN,
    fit_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine eligibility, coverage and 10-trial Wilson rates into a label.

    ``trial_contrasts`` one entry per seed with ``generator_seed`` and
    ``contrasts`` mapping baseline -> {estimate, lower}. Fit coverage is
    checked when ``fit_records`` is provided; otherwise trial seed coverage
    alone is required.
    """
    if not eligible:
        return {
            "confirm_label": CONFIRM_SKIPPED,
            "reason": "screen/pairing not eligible; confirmation not run",
            "ca_tc_successes": None,
            "all_baseline_successes": None,
            "ca_tc_wilson": None,
            "all_baseline_wilson": None,
            "trials": [],
        }

    expected_seeds = [int(s) for s in seeds]
    by_seed: dict[int, Mapping[str, Any]] = {}
    for row in trial_contrasts:
        by_seed[int(row["generator_seed"])] = row

    missing_seeds = [s for s in expected_seeds if s not in by_seed]
    coverage = (
        confirmation_coverage(fit_records, seeds=seeds)
        if fit_records is not None
        else {
            "complete": len(missing_seeds) == 0,
            "n_expected": len(expected_seeds),
            "n_present": len(expected_seeds) - len(missing_seeds),
            "missing_fit_ids": [f"seed:{s}" for s in missing_seeds],
        }
    )
    if missing_seeds or not coverage["complete"]:
        return {
            "confirm_label": CONFIRM_INCOMPLETE,
            "reason": "incomplete confirmation coverage",
            "coverage": coverage,
            "missing_seeds": missing_seeds,
            "ca_tc_successes": None,
            "all_baseline_successes": None,
            "ca_tc_wilson": None,
            "all_baseline_wilson": None,
            "trials": [],
        }

    trials: list[dict[str, Any]] = []
    ca_tc_n = 0
    all_n = 0
    for seed in expected_seeds:
        row = by_seed[seed]
        judged = trial_all_baseline_success(
            row.get("contrasts", {}),
            baselines=baselines,
            margin=margin,
        )
        if judged["ca_tc_success"]:
            ca_tc_n += 1
        if judged["all_baseline_success"]:
            all_n += 1
        trials.append(
            {
                "generator_seed": seed,
                **judged,
            }
        )

    ca_tc_wilson = wilson_interval(ca_tc_n, len(expected_seeds))
    all_wilson = wilson_interval(all_n, len(expected_seeds))
    reliable = ca_tc_n >= int(reliability_min) and all_n >= int(reliability_min)
    label = CONFIRM_RELIABLE if reliable else CONFIRM_NEGATIVE

    return {
        "confirm_label": label,
        "reason": None,
        "coverage": coverage,
        "missing_seeds": [],
        "ca_tc_successes": ca_tc_n,
        "all_baseline_successes": all_n,
        "n_trials": len(expected_seeds),
        "reliability_min": int(reliability_min),
        "exploratory_reliable": reliable,
        "ca_tc_wilson": ca_tc_wilson,
        "all_baseline_wilson": all_wilson,
        "trials": trials,
        "biological_power": "POWER_UNESTABLISHED",
    }
