"""Frozen S7 pairing positive-control gates (no fitting).

Evaluates within-donor ATAC shuffle sensitivity on retained rho=1 CA
predictions. Pass requires donor-bootstrap CI lower bound of mean
log-loss(shuffled)-original > 0. Identity/reload must match within atol.
Does not assign the final runbook label ``CA_FAVOURED_CONTROL`` (needs
confirmation if eligible). No new fits happen here.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

# Mirrors tasks/nn/finish_20260928/BENCHMARK_SPEC.json pairing_pc + evaluation.bootstrap.
S7_PAIRING_SEEDS: tuple[int, ...] = tuple(range(3001, 3033))
S7_PAIRING_N = 32
S7_IDENTITY_ATOL = 1e-6
S7_BOOTSTRAP_DRAWS = 1000
S7_BOOTSTRAP_SEED = 22
S7_BOOTSTRAP_LEVEL = 0.95
S7_MIN_VALID_DRAWS = 950

PC_PASS = "PC_PASS"
PC_FAIL = "PC_FAIL"
PC_INCOMPLETE = "PC_INCOMPLETE"
PC_IDENTITY_FAIL = "PC_IDENTITY_FAIL"

assert len(S7_PAIRING_SEEDS) == S7_PAIRING_N


def binary_log_loss(y: float | np.ndarray, p: float | np.ndarray) -> float:
    """Mean binary cross-entropy; clips probabilities away from {0,1}."""
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    p_arr = np.clip(np.asarray(p, dtype=np.float64).reshape(-1), 1e-15, 1.0 - 1e-15)
    if y_arr.shape != p_arr.shape:
        raise ValueError(f"y shape {y_arr.shape} != p shape {p_arr.shape}")
    if y_arr.size == 0:
        raise ValueError("empty log-loss input")
    return float(-np.mean(y_arr * np.log(p_arr) + (1.0 - y_arr) * np.log(1.0 - p_arr)))


def identity_check(
    probs_a: Sequence[float] | np.ndarray,
    probs_b: Sequence[float] | np.ndarray,
    *,
    atol: float = S7_IDENTITY_ATOL,
) -> dict[str, Any]:
    """Reload/repeat must reproduce predictions within ``atol`` (spec identity)."""
    a = np.asarray(probs_a, dtype=np.float64).reshape(-1)
    b = np.asarray(probs_b, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        return {
            "passed": False,
            "atol": float(atol),
            "max_abs_diff": None,
            "reason": f"shape mismatch {a.shape} vs {b.shape}",
        }
    if a.size == 0:
        return {
            "passed": False,
            "atol": float(atol),
            "max_abs_diff": None,
            "reason": "empty probability vectors",
        }
    max_diff = float(np.max(np.abs(a - b)))
    return {
        "passed": bool(max_diff <= float(atol)),
        "atol": float(atol),
        "max_abs_diff": max_diff,
        "reason": None if max_diff <= float(atol) else "predictions differ beyond atol",
    }


def _align_arrays(
    donor_ids: Sequence[Any],
    y_true: Sequence[float] | np.ndarray,
    p_original: Sequence[float] | np.ndarray,
    p_shuffled_by_seed: Mapping[int, Sequence[float] | np.ndarray],
    *,
    required_seeds: tuple[int, ...] = S7_PAIRING_SEEDS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, np.ndarray], list[str]]:
    """Validate alignment and return arrays; collect incompleteness reasons."""
    donors = np.asarray(donor_ids, dtype=object).reshape(-1)
    y = np.asarray(y_true, dtype=np.float64).reshape(-1)
    p0 = np.asarray(p_original, dtype=np.float64).reshape(-1)
    reasons: list[str] = []
    if donors.size == 0:
        reasons.append("no donors")
    if not (donors.size == y.size == p0.size):
        reasons.append(
            f"length mismatch donors={donors.size} y={y.size} p_original={p0.size}"
        )
    if len(set(str(d) for d in donors)) != donors.size:
        reasons.append("duplicate donor_ids")

    missing = [int(s) for s in required_seeds if int(s) not in p_shuffled_by_seed]
    if missing:
        reasons.append(f"missing shuffle seeds: {missing}")

    shuffled: dict[int, np.ndarray] = {}
    for seed in required_seeds:
        if int(seed) not in p_shuffled_by_seed:
            continue
        arr = np.asarray(p_shuffled_by_seed[int(seed)], dtype=np.float64).reshape(-1)
        if arr.size != donors.size:
            reasons.append(f"seed {int(seed)} length {arr.size} != n_donors {donors.size}")
            continue
        shuffled[int(seed)] = arr
    return donors, y, p0, shuffled, reasons


def per_donor_mean_drops(
    donor_ids: Sequence[Any],
    y_true: Sequence[float] | np.ndarray,
    p_original: Sequence[float] | np.ndarray,
    p_shuffled_by_seed: Mapping[int, Sequence[float] | np.ndarray],
    *,
    required_seeds: tuple[int, ...] = S7_PAIRING_SEEDS,
) -> dict[str, Any]:
    """Average shuffle log-loss and BA drops within each donor.

    Primary drop is ``ll(shuffled) - ll(original)`` (positive when shuffle hurts).
    BA drop is secondary: ``1[correct_orig] - 1[correct_shuf]`` averaged over seeds.
    """
    donors, y, p0, shuffled, reasons = _align_arrays(
        donor_ids,
        y_true,
        p_original,
        p_shuffled_by_seed,
        required_seeds=required_seeds,
    )
    if reasons:
        return {
            "complete": False,
            "reasons": reasons,
            "donor_ids": [],
            "mean_ll_drop": [],
            "mean_ba_drop": [],
            "n_seeds": 0,
        }
    seed_list = [int(s) for s in required_seeds]
    ll_drops: list[float] = []
    ba_drops: list[float] = []
    for i in range(donors.size):
        y_i = float(y[i])
        p_i = float(p0[i])
        ll0 = binary_log_loss(y_i, p_i)
        pred0 = 1 if p_i >= 0.5 else 0
        correct0 = 1.0 if pred0 == int(y_i) else 0.0
        seed_ll: list[float] = []
        seed_ba: list[float] = []
        for seed in seed_list:
            p_s = float(shuffled[seed][i])
            seed_ll.append(binary_log_loss(y_i, p_s) - ll0)
            pred_s = 1 if p_s >= 0.5 else 0
            correct_s = 1.0 if pred_s == int(y_i) else 0.0
            seed_ba.append(correct0 - correct_s)
        ll_drops.append(float(np.mean(seed_ll)))
        ba_drops.append(float(np.mean(seed_ba)))
    return {
        "complete": True,
        "reasons": [],
        "donor_ids": [str(d) for d in donors],
        "mean_ll_drop": ll_drops,
        "mean_ba_drop": ba_drops,
        "n_seeds": len(seed_list),
    }


def paired_donor_bootstrap_mean(
    values: Sequence[float] | np.ndarray,
    *,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    seed: int = S7_BOOTSTRAP_SEED,
    level: float = S7_BOOTSTRAP_LEVEL,
    min_valid: int = S7_MIN_VALID_DRAWS,
) -> dict[str, Any]:
    """Percentile CI for the mean of per-donor values via donor resampling.

    Spec: average shuffle outcomes within donor first, then paired donor-bootstrap.
    Insufficient valid draws (< ``min_valid``) => incomplete (not a pass).
    """
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    n = int(arr.size)
    if n < 2:
        return {
            "estimate": None if n == 0 else float(arr.mean()),
            "lower": None,
            "upper": None,
            "level": float(level),
            "n_donors": n,
            "n_draws_requested": int(n_draws),
            "n_valid": 0,
            "incomplete": True,
            "reason": f"donor bootstrap needs at least two donors, got {n}",
        }
    if int(n_draws) < 1:
        raise ValueError(f"n_draws must be >= 1, got {n_draws}")
    if not 0.0 < float(level) < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")

    rng = np.random.default_rng(int(seed))
    replicates: list[float] = []
    for _ in range(int(n_draws)):
        idx = rng.integers(0, n, size=n)
        replicates.append(float(arr[idx].mean()))
    reps = np.asarray(replicates, dtype=np.float64)
    # Finite means only; NaN would indicate upstream corruption.
    valid = reps[np.isfinite(reps)]
    n_valid = int(valid.size)
    incomplete = n_valid < int(min_valid)
    if n_valid == 0:
        return {
            "estimate": float(arr.mean()),
            "lower": None,
            "upper": None,
            "level": float(level),
            "n_donors": n,
            "n_draws_requested": int(n_draws),
            "n_valid": 0,
            "incomplete": True,
            "reason": "every bootstrap draw failed",
        }
    tail = (1.0 - float(level)) / 2.0
    lower, upper = np.percentile(valid, [100.0 * tail, 100.0 * (1.0 - tail)])
    return {
        "estimate": float(arr.mean()),
        "lower": float(lower),
        "upper": float(upper),
        "level": float(level),
        "n_donors": n,
        "n_draws_requested": int(n_draws),
        "n_valid": n_valid,
        "incomplete": incomplete,
        "reason": (
            None
            if not incomplete
            else f"insufficient valid draws: {n_valid} < {int(min_valid)}"
        ),
    }


def evaluate_pairing_pc(
    *,
    donor_ids: Sequence[Any],
    y_true: Sequence[float] | np.ndarray,
    p_original: Sequence[float] | np.ndarray,
    p_shuffled_by_seed: Mapping[int, Sequence[float] | np.ndarray],
    p_reload: Sequence[float] | np.ndarray | None = None,
    required_seeds: tuple[int, ...] = S7_PAIRING_SEEDS,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    bootstrap_seed: int = S7_BOOTSTRAP_SEED,
    min_valid: int = S7_MIN_VALID_DRAWS,
    atol: float = S7_IDENTITY_ATOL,
) -> dict[str, Any]:
    """Combine identity + 32-seed within-donor shuffle drop into a PC label.

    ``PC_PASS`` is eligible for confirmation. Identity failure and incomplete
    coverage never pass. BA drop is reported but never chosen as the gate.
    """
    identity = (
        identity_check(p_original, p_reload, atol=atol)
        if p_reload is not None
        else {"passed": True, "atol": float(atol), "max_abs_diff": 0.0, "reason": None}
    )
    if not identity["passed"]:
        return {
            "pc_label": PC_IDENTITY_FAIL,
            "eligible_for_confirmation": False,
            "identity": identity,
            "drops": None,
            "ll_drop_bootstrap": None,
            "ba_drop_bootstrap": None,
        }

    drops = per_donor_mean_drops(
        donor_ids,
        y_true,
        p_original,
        p_shuffled_by_seed,
        required_seeds=required_seeds,
    )
    if not drops["complete"]:
        return {
            "pc_label": PC_INCOMPLETE,
            "eligible_for_confirmation": False,
            "identity": identity,
            "drops": drops,
            "ll_drop_bootstrap": None,
            "ba_drop_bootstrap": None,
        }

    ll_boot = paired_donor_bootstrap_mean(
        drops["mean_ll_drop"],
        n_draws=n_draws,
        seed=bootstrap_seed,
        min_valid=min_valid,
    )
    ba_boot = paired_donor_bootstrap_mean(
        drops["mean_ba_drop"],
        n_draws=n_draws,
        seed=bootstrap_seed,
        min_valid=min_valid,
    )

    if ll_boot["incomplete"] or ll_boot["lower"] is None:
        label = PC_INCOMPLETE
        eligible = False
    elif float(ll_boot["lower"]) > 0.0:
        label = PC_PASS
        eligible = True
    else:
        label = PC_FAIL
        eligible = False

    return {
        "pc_label": label,
        "eligible_for_confirmation": eligible,
        "identity": identity,
        "drops": {
            "n_donors": len(drops["donor_ids"]),
            "n_seeds": drops["n_seeds"],
            "mean_ll_drop_estimate": ll_boot["estimate"],
            "mean_ba_drop_estimate": ba_boot["estimate"],
        },
        "ll_drop_bootstrap": ll_boot,
        "ba_drop_bootstrap": ba_boot,
    }
