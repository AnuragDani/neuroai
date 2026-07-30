"""Tests for held-out interventions on the real-data RNA-only path."""

from __future__ import annotations

import numpy as np

from p22.eval.real_interventions import (
    RNA_ZERO,
    ROUTING_INTERVENTIONS_REQUIRING_TWO_VIEWS,
    intervention_rows,
    routing_not_applicable,
    run_rna_only_interventions,
)


def _split(seed: int = 0, separation: float = 2.5):
    rng = np.random.default_rng(seed)
    train_donors = [f"TR_{index:02d}" for index in range(12)]
    test_donors = [f"TE_{index:02d}" for index in range(8)]
    cells = 20
    train_labels = np.repeat(np.array([0, 1] * 6), cells)
    test_labels = np.repeat(np.array([0, 1] * 4), cells)
    train_matrix = rng.normal(size=(train_labels.size, 12))
    train_matrix[:, 0] += train_labels * separation
    test_matrix = rng.normal(size=(test_labels.size, 12))
    test_matrix[:, 0] += test_labels * separation
    test_cell_donors = np.repeat(np.asarray(test_donors, dtype=object), cells)
    return train_matrix, train_labels, test_matrix, test_labels, test_cell_donors, train_donors


def test_rna_only_interventions_measure_input_dependence():
    train_x, train_y, test_x, test_y, test_donors, _ = _split()
    effects = run_rna_only_interventions(
        train_x, train_y, test_x, test_y, test_donors, branch_reason="ATAC branch B2b"
    )
    measured = [effect for effect in effects if effect.status == "measured"]
    assert len(measured) == 3
    for effect in measured:
        assert effect.target == "rna"
        assert effect.n_donors == 8
        assert effect.n_cells == test_y.size
        assert effect.donor_metric_before is not None
        assert effect.donor_metric_after is not None
        assert 0.0 <= effect.cell_flip_rate <= 1.0

    ablation = next(effect for effect in measured if effect.name == RNA_ZERO)
    assert ablation.donor_metric_drop is not None
    assert ablation.donor_metric_drop > 0.0


def test_interventions_are_reported_not_silently_skipped():
    train_x, train_y, test_x, test_y, test_donors, _ = _split()
    effects = run_rna_only_interventions(
        train_x, train_y, test_x, test_y, test_donors, branch_reason="ATAC branch B2b"
    )
    names = {effect.name for effect in effects}
    assert set(ROUTING_INTERVENTIONS_REQUIRING_TWO_VIEWS).issubset(names)
    blocked = [effect for effect in effects if effect.status == "NOT_APPLICABLE"]
    assert all(effect.not_applicable == "ATAC branch B2b" for effect in blocked)


def test_routing_not_applicable_lists_every_gate_intervention():
    effects = routing_not_applicable("no second modality")
    assert len(effects) == len(ROUTING_INTERVENTIONS_REQUIRING_TWO_VIEWS)
    assert all(effect.status == "NOT_APPLICABLE" for effect in effects)
    assert all(effect.cell_flip_rate is None for effect in effects)


def test_intervention_rows_declare_evidence_scope():
    rows = intervention_rows(routing_not_applicable("no second modality"))
    assert rows
    for row in rows:
        assert "not an explanation" in row["evidence"]
        assert row["status"] == "NOT_APPLICABLE"
