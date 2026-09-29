"""Focused checks for S7 confirmation trial-contrast builder.

Synthetic donor tables only — no H5AD, no model fits. One sidecar round-trip.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from p22.eval.s7_confirm_exec import (
    build_one_trial_contrasts,
    build_trial_contrasts,
    donor_table_from_payload,
    load_donor_predictions,
    paired_ba_contrast,
    pool_trial_model_tables,
    run_confirmation_evaluation,
    save_donor_predictions,
    shared_bootstrap_indices,
)
from p22.eval.s7_confirmation import (
    CONFIRM_INCOMPLETE,
    CONFIRM_NEGATIVE,
    CONFIRM_RELIABLE,
    CONFIRM_SKIPPED,
    S7_CONFIRM_SEEDS,
    enumerate_confirmation_jobs,
)
from p22.eval.s7_screen import S7_NON_ATTENTION


def _donor_payload(
    donors: list[str],
    labels: list[float],
    probs: list[float],
) -> dict:
    return {
        "donor_id": donors,
        "label": labels,
        "probability": probs,
        "prediction": [int(p >= 0.5) for p in probs],
    }


def _record(
    *,
    seed: int,
    fold: int,
    model: str,
    donors: list[str],
    labels: list[float],
    probs: list[float],
    ba: float = 0.8,
) -> dict:
    return {
        "fit_id": f"confirm|{seed}|{fold}|{model}",
        "stage": "confirm",
        "rho": 1.0,
        "generator_seed": seed,
        "fold": fold,
        "model": model,
        "status": "ok",
        "donor_balanced_accuracy": ba,
        "donor_probabilities": _donor_payload(donors, labels, probs),
    }


def _perfect_ca_records(seed: int = 2001, n_folds: int = 5) -> list[dict]:
    """CA perfectly separates; baselines at chance — large positive contrasts."""
    records: list[dict] = []
    for fold in range(n_folds):
        d0, d1 = f"s{seed}f{fold}c0", f"s{seed}f{fold}c1"
        donors = [d0, d1]
        labels = [0.0, 1.0]
        records.append(
            _record(
                seed=seed,
                fold=fold,
                model="cross_attention",
                donors=donors,
                labels=labels,
                probs=[0.05, 0.95],
                ba=1.0,
            )
        )
        for model in S7_NON_ATTENTION:
            records.append(
                _record(
                    seed=seed,
                    fold=fold,
                    model=model,
                    donors=donors,
                    labels=labels,
                    probs=[0.51, 0.49],
                    ba=0.5,
                )
            )
        # Single-view arms exist in job enum but are not confirmation baselines.
        for model in ("logreg_rna", "logreg_atac"):
            records.append(
                _record(
                    seed=seed,
                    fold=fold,
                    model=model,
                    donors=donors,
                    labels=labels,
                    probs=[0.5, 0.5],
                    ba=0.5,
                )
            )
    return records


def _null_ca_records(seed: int = 2001, n_folds: int = 5) -> list[dict]:
    """CA and baselines identical chance predictions — contrasts near zero."""
    records: list[dict] = []
    for fold in range(n_folds):
        d0, d1 = f"s{seed}f{fold}c0", f"s{seed}f{fold}c1"
        donors = [d0, d1]
        labels = [0.0, 1.0]
        chance = [0.51, 0.49]
        for model in (
            "cross_attention",
            *S7_NON_ATTENTION,
            "logreg_rna",
            "logreg_atac",
        ):
            records.append(
                _record(
                    seed=seed,
                    fold=fold,
                    model=model,
                    donors=donors,
                    labels=labels,
                    probs=list(chance),
                    ba=0.5,
                )
            )
    return records


def test_donor_table_sorts_and_rejects_duplicates() -> None:
    table = donor_table_from_payload(
        _donor_payload(["b", "a"], [1.0, 0.0], [0.9, 0.1])
    )
    assert table["donor_ids"] == ["a", "b"]
    assert table["y_true"] == [0.0, 1.0]
    assert table["p"] == [0.1, 0.9]
    with pytest.raises(ValueError, match="duplicate"):
        donor_table_from_payload(
            _donor_payload(["a", "a"], [0.0, 1.0], [0.1, 0.9])
        )


def test_shared_bootstrap_indices_are_deterministic() -> None:
    a = shared_bootstrap_indices(4, n_draws=10, seed=22)
    b = shared_bootstrap_indices(4, n_draws=10, seed=22)
    c = shared_bootstrap_indices(4, n_draws=10, seed=23)
    assert a.shape == (10, 4)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_paired_ba_contrast_uses_shared_draws_and_detects_gap() -> None:
    y = [0.0, 0.0, 1.0, 1.0]
    p_ca = [0.1, 0.1, 0.9, 0.9]
    p_base = [0.6, 0.6, 0.4, 0.4]
    draws = shared_bootstrap_indices(4, n_draws=200, seed=22)
    row = paired_ba_contrast(y, p_ca, p_base, draw_indices=draws, min_valid=150)
    assert row["incomplete"] is False
    assert row["estimate"] is not None and row["estimate"] >= 0.07
    assert row["lower"] is not None and row["lower"] > 0.0


def test_pool_trial_requires_all_models_and_disjoint_donors() -> None:
    records = _perfect_ca_records(seed=2001)
    pooled = pool_trial_model_tables(
        records,
        generator_seed=2001,
        models=("cross_attention", *S7_NON_ATTENTION),
    )
    assert pooled["complete"] is True
    assert pooled["n_donors"] == 10  # 5 folds × 2 donors

    missing = [r for r in records if r["model"] != "token_concat"]
    bad = pool_trial_model_tables(
        missing,
        generator_seed=2001,
        models=("cross_attention", *S7_NON_ATTENTION),
    )
    assert bad["complete"] is False
    assert "token_concat" in str(bad["reason"])


def test_build_one_trial_contrasts_passing_and_failing() -> None:
    passing = build_one_trial_contrasts(
        _perfect_ca_records(2001),
        generator_seed=2001,
        n_draws=200,
        min_valid=150,
    )
    assert passing["complete"] is True
    assert set(passing["contrasts"]) == set(S7_NON_ATTENTION)
    assert all(
        c["estimate"] is not None and c["estimate"] >= 0.07 and c["lower"] > 0
        for c in passing["contrasts"].values()
    )
    assert passing["mean_fold_donor_ba"]["cross_attention"] == 1.0

    failing = build_one_trial_contrasts(
        _null_ca_records(2001),
        generator_seed=2001,
        n_draws=200,
        min_valid=150,
    )
    assert failing["complete"] is True
    assert all(
        (c["estimate"] is not None and c["estimate"] < 0.07) or (c["lower"] is not None and c["lower"] <= 0)
        for c in failing["contrasts"].values()
    )


def test_run_confirmation_skip_incomplete_negative_reliable(tmp_path: Path) -> None:
    skipped = run_confirmation_evaluation([], eligible=False)
    assert skipped["confirm_label"] == CONFIRM_SKIPPED

    # Coverage incomplete when only one seed of records is present.
    partial = _perfect_ca_records(2001)
    incomplete = run_confirmation_evaluation(
        partial, eligible=True, n_draws=50, min_valid=40
    )
    assert incomplete["confirm_label"] == CONFIRM_INCOMPLETE

    # Build full 10-seed null coverage → CONFIRM_NEGATIVE.
    null_all: list[dict] = []
    for seed in S7_CONFIRM_SEEDS:
        null_all.extend(_null_ca_records(seed))
    # Pad fit_id uniqueness to match enumerate for coverage check.
    jobs = {
        (j["generator_seed"], j["fold"], j["model"]): j
        for j in enumerate_confirmation_jobs()
    }
    for row in null_all:
        key = (row["generator_seed"], row["fold"], row["model"])
        row["fit_id"] = jobs[key]["fit_id"]

    negative = run_confirmation_evaluation(
        null_all, eligible=True, n_draws=100, min_valid=80
    )
    assert negative["confirm_label"] == CONFIRM_NEGATIVE
    assert negative["ca_tc_successes"] == 0

    # Full 10-seed perfect CA → CONFIRM_RELIABLE.
    perfect_all: list[dict] = []
    for seed in S7_CONFIRM_SEEDS:
        perfect_all.extend(_perfect_ca_records(seed))
    for row in perfect_all:
        key = (row["generator_seed"], row["fold"], row["model"])
        row["fit_id"] = jobs[key]["fit_id"]

    reliable = run_confirmation_evaluation(
        perfect_all, eligible=True, n_draws=100, min_valid=80
    )
    assert reliable["confirm_label"] == CONFIRM_RELIABLE
    assert reliable["ca_tc_successes"] == 10
    assert reliable["all_baseline_successes"] == 10

    # Sidecar round-trip: strip inline probs, load from path.
    row0 = perfect_all[0]
    path = save_donor_predictions(row0, tmp_path)
    assert path is not None and path.exists()
    stripped = {k: v for k, v in row0.items() if k != "donor_probabilities"}
    stripped["donor_predictions_path"] = str(path)
    loaded = load_donor_predictions(stripped)
    assert loaded is not None
    assert loaded["donor_ids"] == donor_table_from_payload(row0["donor_probabilities"])["donor_ids"]


def test_confirm_stage_retention_alias_in_runner() -> None:
    from p22.eval.s7_runner import should_retain_checkpoint

    job = {
        "model": "cross_attention",
        "rho": 1.0,
        "stage": "confirm",
    }
    assert should_retain_checkpoint(job) is True
    assert (
        should_retain_checkpoint({**job, "stage": "confirmation"}) is False
    )


def test_build_trial_contrasts_covers_all_seeds() -> None:
    records: list[dict] = []
    jobs = {
        (j["generator_seed"], j["fold"], j["model"]): j
        for j in enumerate_confirmation_jobs()
    }
    for seed in S7_CONFIRM_SEEDS:
        for row in _null_ca_records(seed):
            key = (row["generator_seed"], row["fold"], row["model"])
            row["fit_id"] = jobs[key]["fit_id"]
            records.append(row)
    trials = build_trial_contrasts(records, n_draws=50, min_valid=40)
    assert len(trials) == 10
    assert [t["generator_seed"] for t in trials] == list(S7_CONFIRM_SEEDS)
    assert all(t["complete"] for t in trials)
