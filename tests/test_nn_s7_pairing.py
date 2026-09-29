"""Focused checks for S7 pairing-PC identity, coverage and log-loss drop gate.

Synthetic donor probabilities only — no H5AD, no model fits.
"""

from __future__ import annotations

import numpy as np
import pytest

from p22.eval.s7_pairing import (
    PC_FAIL,
    PC_IDENTITY_FAIL,
    PC_INCOMPLETE,
    PC_PASS,
    S7_PAIRING_N,
    S7_PAIRING_SEEDS,
    binary_log_loss,
    evaluate_pairing_pc,
    identity_check,
    paired_donor_bootstrap_mean,
    per_donor_mean_drops,
)


def _sensitive_case(n_donors: int = 10) -> dict:
    """Original probs track labels; every shuffle collapses toward 0.5."""
    rng = np.random.default_rng(0)
    y = np.asarray([0, 1] * (n_donors // 2) + ([0] if n_donors % 2 else []), dtype=np.float64)
    # Strong original predictions.
    p0 = np.where(y == 1, 0.92, 0.08).astype(np.float64)
    shuffled = {
        int(seed): np.clip(0.5 + rng.normal(0.0, 0.02, size=n_donors), 0.05, 0.95)
        for seed in S7_PAIRING_SEEDS
    }
    donors = [f"d{i}" for i in range(n_donors)]
    return {
        "donor_ids": donors,
        "y_true": y,
        "p_original": p0,
        "p_shuffled_by_seed": shuffled,
        "p_reload": p0.copy(),
    }


def _insensitive_case(n_donors: int = 10) -> dict:
    """Shuffle leaves predictions essentially unchanged."""
    y = np.asarray([0, 1] * (n_donors // 2), dtype=np.float64)
    p0 = np.where(y == 1, 0.80, 0.20).astype(np.float64)
    shuffled = {int(seed): p0.copy() for seed in S7_PAIRING_SEEDS}
    donors = [f"d{i}" for i in range(n_donors)]
    return {
        "donor_ids": donors,
        "y_true": y,
        "p_original": p0,
        "p_shuffled_by_seed": shuffled,
        "p_reload": p0.copy(),
    }


def test_pairing_seed_table_is_frozen_32() -> None:
    assert len(S7_PAIRING_SEEDS) == S7_PAIRING_N == 32
    assert S7_PAIRING_SEEDS[0] == 3001
    assert S7_PAIRING_SEEDS[-1] == 3032
    assert list(S7_PAIRING_SEEDS) == list(range(3001, 3033))


def test_identity_check_atol() -> None:
    a = np.asarray([0.1, 0.9, 0.4], dtype=np.float64)
    assert identity_check(a, a)["passed"] is True
    assert identity_check(a, a + 1e-7)["passed"] is True
    bad = identity_check(a, a + 1e-5)
    assert bad["passed"] is False
    assert bad["max_abs_diff"] == pytest.approx(1e-5)


def test_binary_log_loss_perfect_and_wrong() -> None:
    assert binary_log_loss(1.0, 0.999) < 0.01
    assert binary_log_loss(1.0, 0.001) > 5.0
    with pytest.raises(ValueError, match="empty"):
        binary_log_loss([], [])


def test_per_donor_drops_require_all_32_seeds() -> None:
    case = _sensitive_case()
    incomplete = dict(case["p_shuffled_by_seed"])
    del incomplete[3001]
    drops = per_donor_mean_drops(
        case["donor_ids"],
        case["y_true"],
        case["p_original"],
        incomplete,
    )
    assert drops["complete"] is False
    assert any("missing shuffle seeds" in r for r in drops["reasons"])


def test_sensitive_shuffle_yields_positive_ll_drop() -> None:
    case = _sensitive_case()
    drops = per_donor_mean_drops(
        case["donor_ids"],
        case["y_true"],
        case["p_original"],
        case["p_shuffled_by_seed"],
    )
    assert drops["complete"] is True
    assert drops["n_seeds"] == 32
    assert float(np.mean(drops["mean_ll_drop"])) > 0.5


def test_bootstrap_incomplete_when_too_few_valid() -> None:
    values = np.asarray([0.1, 0.2, 0.15, 0.12], dtype=np.float64)
    boot = paired_donor_bootstrap_mean(values, n_draws=10, min_valid=950)
    assert boot["incomplete"] is True
    assert boot["n_valid"] == 10
    assert "insufficient valid draws" in str(boot["reason"])


def test_evaluate_pairing_pc_pass_fail_identity_incomplete() -> None:
    sensitive = _sensitive_case()
    passed = evaluate_pairing_pc(**sensitive)
    assert passed["pc_label"] == PC_PASS
    assert passed["eligible_for_confirmation"] is True
    assert passed["ll_drop_bootstrap"]["lower"] > 0.0
    assert passed["ba_drop_bootstrap"] is not None  # reported, not gating

    insensitive = _insensitive_case()
    failed = evaluate_pairing_pc(**insensitive)
    assert failed["pc_label"] == PC_FAIL
    assert failed["eligible_for_confirmation"] is False
    assert failed["ll_drop_bootstrap"]["lower"] <= 0.0

    id_fail = dict(sensitive)
    id_fail["p_reload"] = sensitive["p_original"] + 0.01
    assert evaluate_pairing_pc(**id_fail)["pc_label"] == PC_IDENTITY_FAIL

    missing = dict(sensitive)
    missing["p_shuffled_by_seed"] = {
        k: v for k, v in sensitive["p_shuffled_by_seed"].items() if k != 3032
    }
    assert evaluate_pairing_pc(**missing)["pc_label"] == PC_INCOMPLETE
