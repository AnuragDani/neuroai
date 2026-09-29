"""Focused checks for S7 confirmation joint-success, Wilson CI and coverage.

Synthetic contrast summaries only — no H5AD, no model fits.
"""

from __future__ import annotations

import pytest

from p22.eval.s7_confirmation import (
    CONFIRM_INCOMPLETE,
    CONFIRM_NEGATIVE,
    CONFIRM_RELIABLE,
    CONFIRM_SKIPPED,
    S7_CONFIRM_FITS,
    S7_CONFIRM_N,
    S7_CONFIRM_SEEDS,
    confirmation_coverage,
    enumerate_confirmation_jobs,
    evaluate_confirmation,
    joint_success,
    trial_all_baseline_success,
    wilson_interval,
)
from p22.eval.s7_ledger import S7_MODELS, S7_N_FOLDS
from p22.eval.s7_screen import S7_NON_ATTENTION


def _passing_contrasts() -> dict[str, dict[str, float]]:
    return {
        name: {"estimate": 0.12, "lower": 0.03, "upper": 0.20}
        for name in S7_NON_ATTENTION
    }


def _failing_contrasts() -> dict[str, dict[str, float]]:
    return {
        name: {"estimate": 0.08, "lower": -0.01, "upper": 0.15}
        for name in S7_NON_ATTENTION
    }


def _complete_fit_records() -> list[dict]:
    return [
        {**job, "status": "ok", "donor_balanced_accuracy": 0.7}
        for job in enumerate_confirmation_jobs()
    ]


def test_confirmation_seed_table_is_frozen_10() -> None:
    assert len(S7_CONFIRM_SEEDS) == S7_CONFIRM_N == 10
    assert S7_CONFIRM_SEEDS[0] == 2001
    assert S7_CONFIRM_SEEDS[-1] == 2010
    assert list(S7_CONFIRM_SEEDS) == list(range(2001, 2011))


def test_enumerate_confirmation_jobs_is_350() -> None:
    jobs = enumerate_confirmation_jobs()
    assert len(jobs) == S7_CONFIRM_FITS == 350
    assert len({j["fit_id"] for j in jobs}) == 350
    assert {j["generator_seed"] for j in jobs} == set(S7_CONFIRM_SEEDS)
    assert all(j["rho"] == 1.0 for j in jobs)
    assert all(j["stage"] == "confirm" for j in jobs)
    assert len(S7_MODELS) * S7_N_FOLDS * S7_CONFIRM_N == 350


def test_joint_success_requires_margin_and_positive_lower() -> None:
    assert joint_success(0.07, 0.01) is True
    assert joint_success(0.12, 0.0) is False  # lower must be > 0
    assert joint_success(0.06, 0.02) is False  # estimate below margin
    assert joint_success(None, 0.02) is False
    assert joint_success(0.10, None) is False


def test_wilson_interval_bounds_and_midpoint() -> None:
    mid = wilson_interval(5, 10)
    assert mid["rate"] == 0.5
    assert 0.0 < mid["lower"] < 0.5 < mid["upper"] < 1.0

    perfect = wilson_interval(10, 10)
    assert perfect["rate"] == 1.0
    assert perfect["lower"] > 0.6
    assert perfect["upper"] == 1.0

    with pytest.raises(ValueError, match="n must"):
        wilson_interval(0, 0)


def test_trial_intersection_union_requires_every_baseline() -> None:
    contrasts = _passing_contrasts()
    ok = trial_all_baseline_success(contrasts)
    assert ok["ca_tc_success"] is True
    assert ok["all_baseline_success"] is True

    contrasts["gated_fusion"] = {"estimate": 0.12, "lower": -0.02}
    mixed = trial_all_baseline_success(contrasts)
    assert mixed["ca_tc_success"] is True  # token_concat still passes
    assert mixed["all_baseline_success"] is False
    assert mixed["per_baseline"]["gated_fusion"] is False


def test_confirmation_coverage_refuses_partial() -> None:
    records = _complete_fit_records()
    assert confirmation_coverage(records)["complete"] is True

    partial = [r for r in records if r["fit_id"] != records[0]["fit_id"]]
    cov = confirmation_coverage(partial)
    assert cov["complete"] is False
    assert cov["n_present"] == 349
    assert records[0]["fit_id"] in cov["missing_fit_ids"]


def test_evaluate_confirmation_skip_incomplete_negative_reliable() -> None:
    skipped = evaluate_confirmation([], eligible=False)
    assert skipped["confirm_label"] == CONFIRM_SKIPPED
    assert skipped["ca_tc_wilson"] is None

    incomplete = evaluate_confirmation(
        [
            {"generator_seed": 2001, "contrasts": _passing_contrasts()},
        ],
        eligible=True,
    )
    assert incomplete["confirm_label"] == CONFIRM_INCOMPLETE

    trials_neg = [
        {"generator_seed": s, "contrasts": _failing_contrasts()}
        for s in S7_CONFIRM_SEEDS
    ]
    negative = evaluate_confirmation(
        trials_neg,
        eligible=True,
        fit_records=_complete_fit_records(),
    )
    assert negative["confirm_label"] == CONFIRM_NEGATIVE
    assert negative["ca_tc_successes"] == 0
    assert negative["all_baseline_successes"] == 0
    assert negative["ca_tc_wilson"]["rate"] == 0.0
    assert negative["biological_power"] == "POWER_UNESTABLISHED"

    trials_ok = [
        {"generator_seed": s, "contrasts": _passing_contrasts()}
        for s in S7_CONFIRM_SEEDS
    ]
    reliable = evaluate_confirmation(
        trials_ok,
        eligible=True,
        fit_records=_complete_fit_records(),
    )
    assert reliable["confirm_label"] == CONFIRM_RELIABLE
    assert reliable["ca_tc_successes"] == 10
    assert reliable["all_baseline_successes"] == 10
    assert reliable["exploratory_reliable"] is True
    assert reliable["ca_tc_wilson"]["lower"] > 0.6
