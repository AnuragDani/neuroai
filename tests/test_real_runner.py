"""Tests for donor-held-out scoring of real-data baselines and models."""

from __future__ import annotations

import numpy as np

from p22.data.group_splits import build_repeated_group_split_report
from p22.eval.real_runner import (
    ModelRun,
    not_applicable_run,
    paired_donor_delta,
    run_cell_level_model,
    run_donor_level_model,
    run_majority_baseline,
)

N_PER_CLASS = 15


def _donor_setup(separation: float = 3.0, seed: int = 0):
    rng = np.random.default_rng(seed)
    donors = [f"CON_{index:02d}" for index in range(N_PER_CLASS)]
    donors += [f"DS_{index:02d}" for index in range(N_PER_CLASS)]
    labels = np.array([0] * N_PER_CLASS + [1] * N_PER_CLASS)
    features = rng.normal(size=(len(donors), 6))
    features[:, 0] += labels * separation
    report = build_repeated_group_split_report(
        np.asarray(donors, dtype=object), labels, n_repeats=3, n_folds=5, base_seed=0
    )
    return donors, labels, features, report.folds


def test_donor_level_model_scores_every_donor_once_per_repeat():
    donors, labels, features, folds = _donor_setup()
    run = run_donor_level_model("pseudobulk_rna_logistic", features, labels, donors, folds)
    assert run.status == "measured"
    assert run.n_donors == 2 * N_PER_CLASS
    assert len(run.per_repeat_balanced_accuracy) == 3
    assert run.balanced_accuracy is not None and run.balanced_accuracy > 0.8
    assert max(run.donor_overlap_per_fold) == 0
    row = run.to_row()
    assert row["bootstrap_lower"] is not None
    assert row["split_repeats_std"] is not None


def test_donor_level_model_on_noise_is_near_chance():
    donors, labels, features, folds = _donor_setup(separation=0.0, seed=7)
    run = run_donor_level_model("noise", features, labels, donors, folds)
    assert run.balanced_accuracy is not None
    assert run.balanced_accuracy < 0.8


def test_majority_baseline_is_chance_on_balanced_donors():
    donors, labels, _features, folds = _donor_setup()
    run = run_majority_baseline(labels, donors, folds)
    assert run.balanced_accuracy == 0.5
    assert run.n_donors == 2 * N_PER_CLASS


def test_cell_level_model_aggregates_to_donor_probability():
    rng = np.random.default_rng(1)
    donors, labels, _features, folds = _donor_setup()
    cells_per_donor = 12
    cell_donors = np.repeat(np.asarray(donors, dtype=object), cells_per_donor)
    cell_labels = np.repeat(labels, cells_per_donor)
    matrix = rng.normal(size=(cell_donors.size, 20))
    matrix[:, 0] += cell_labels * 2.0
    run = run_cell_level_model("rna_only", matrix, cell_labels, cell_donors, folds, n_features=10)
    assert run.status == "measured"
    assert run.n_cells == cell_donors.size
    assert run.balanced_accuracy is not None and run.balanced_accuracy > 0.8
    assert max(run.donor_overlap_per_fold) == 0


def test_cell_level_model_accepts_sparse_input():
    from scipy import sparse

    rng = np.random.default_rng(2)
    donors, labels, _features, folds = _donor_setup()
    cell_donors = np.repeat(np.asarray(donors, dtype=object), 8)
    cell_labels = np.repeat(labels, 8)
    dense = np.abs(rng.normal(size=(cell_donors.size, 15)))
    dense[:, 0] += cell_labels * 2.0
    run = run_cell_level_model(
        "rna_only_sparse",
        sparse.csr_matrix(dense),
        cell_labels,
        cell_donors,
        folds,
        n_features=8,
    )
    assert run.status == "measured"
    assert run.balanced_accuracy is not None


def test_paired_delta_reports_verdict_and_margin():
    donors, labels, features, folds = _donor_setup()
    strong = run_donor_level_model("strong", features, labels, donors, folds)
    majority = run_majority_baseline(labels, donors, folds)
    delta = paired_donor_delta(strong, majority, margin=0.07)
    assert delta.delta is not None and delta.delta > 0
    assert delta.verdict in {"success", "inconclusive"}
    assert delta.margin == 0.07
    same = paired_donor_delta(strong, strong, margin=0.07)
    assert same.delta == 0.0
    assert same.verdict == "inconclusive"


def test_paired_delta_not_applicable_against_unscored_model():
    donors, labels, features, folds = _donor_setup()
    strong = run_donor_level_model("strong", features, labels, donors, folds)
    blocked = not_applicable_run("gated_fusion", "ATAC branch B2b")
    delta = paired_donor_delta(strong, blocked, margin=0.07)
    assert delta.verdict == "not_applicable"
    assert delta.delta is None


def test_paired_delta_reports_when_reference_is_better():
    donors = tuple(f"D{index:02d}" for index in range(20))
    labels = np.asarray([0] * 10 + [1] * 10, dtype=int)
    weak = ModelRun(
        name="weak",
        layer="donor_level",
        status="measured",
        donor_ids=donors,
        labels=labels,
        donor_prediction=1 - labels,
    )
    strong = ModelRun(
        name="strong",
        layer="donor_level",
        status="measured",
        donor_ids=donors,
        labels=labels,
        donor_prediction=labels,
    )

    delta = paired_donor_delta(weak, strong, margin=0.07)

    assert delta.delta == -1.0
    assert delta.meets_margin is True
    assert delta.interval_excludes_zero is True
    assert delta.verdict == "success"
    assert delta.to_dict()["comparison_result"] == "reference_better"


def test_not_applicable_run_carries_reason():
    run = not_applicable_run("gated_fusion", "ATAC branch B2b")
    assert run.status == "NOT_APPLICABLE"
    assert run.to_row()["not_applicable"] == "ATAC branch B2b"
    assert run.balanced_accuracy is None
