"""Tests for frozen marker panels and honest validation status."""

from __future__ import annotations

import numpy as np
import pandas as pd

from p22.eval.marker_validation import (
    CHR21_DOSAGE_PANEL,
    CHR21_DOSAGE_PANEL_NAME,
    CONTROL_PANEL,
    CONTROL_PANEL_NAME,
    evaluate_panel,
)
from p22.eval.validation import build_validation_report, default_validation_resources

N_PER_CLASS = 8


def test_registry_names_rna_and_multiome_candidates_without_claiming_acceptance():
    resources = {item.accession: item for item in default_validation_resources()}
    assert (resources["GSE280175"].n_control, resources["GSE280175"].n_case) == (5, 5)
    candidate = resources["nemo:col-umstjg0"]
    assert (candidate.n_control, candidate.n_case) == (13, 13)
    assert candidate.available is None
    assert "pending" in candidate.notes
    assert resources["GSE305153"].role == "scale_pool_candidate_not_independent"


def _panel_frame(dosage_effect: float, control_effect: float = 0.0, seed: int = 0):
    rng = np.random.default_rng(seed)
    symbols = list(CHR21_DOSAGE_PANEL) + list(CONTROL_PANEL) + ["FILLER1", "FILLER2"]
    donors = tuple(
        [f"CON_{index}" for index in range(N_PER_CLASS)]
        + [f"DS_{index}" for index in range(N_PER_CLASS)]
    )
    labels = np.array([0] * N_PER_CLASS + [1] * N_PER_CLASS)
    matrix = rng.normal(loc=4.0, scale=0.1, size=(len(donors), len(symbols)))
    for index, symbol in enumerate(symbols):
        if symbol in CHR21_DOSAGE_PANEL:
            matrix[:, index] += labels * dosage_effect
        elif symbol in CONTROL_PANEL:
            matrix[:, index] += labels * control_effect
    return matrix, pd.Series(symbols), labels, donors, set(donors)


def test_marker_panel_detects_declared_direction():
    matrix, symbols, labels, donors, held_out = _panel_frame(dosage_effect=0.6)
    result = evaluate_panel(
        CHR21_DOSAGE_PANEL_NAME,
        CHR21_DOSAGE_PANEL,
        "higher in trisomy 21",
        matrix,
        symbols,
        labels,
        donors,
        held_out,
    )
    assert result.status == "measured"
    assert result.n_genes_found == len(CHR21_DOSAGE_PANEL)
    assert result.median_log2_fold_change is not None
    assert result.median_log2_fold_change > 0
    assert result.fraction_up_in_ds == 1.0
    assert result.to_row()["evidence_scope"].startswith("internal held-out")


def test_control_panel_stays_flat_when_only_chr21_moves():
    matrix, symbols, labels, donors, held_out = _panel_frame(dosage_effect=0.6)
    control = evaluate_panel(
        CONTROL_PANEL_NAME,
        CONTROL_PANEL,
        "no systematic shift",
        matrix,
        symbols,
        labels,
        donors,
        held_out,
    )
    assert control.status == "measured"
    assert control.median_log2_fold_change is not None
    assert abs(control.median_log2_fold_change) < 0.2


def test_marker_panel_reports_missing_genes():
    matrix, symbols, labels, donors, held_out = _panel_frame(dosage_effect=0.3)
    result = evaluate_panel(
        "panel with absent genes",
        ("APP", "NOT_A_REAL_GENE_XYZ"),
        "higher in trisomy 21",
        matrix,
        symbols,
        labels,
        donors,
        held_out,
    )
    assert result.n_genes_found == 1
    assert result.genes_missing == ("NOT_A_REAL_GENE_XYZ",)


def test_marker_panel_not_applicable_with_too_few_donors():
    matrix, symbols, labels, donors, _ = _panel_frame(dosage_effect=0.6)
    result = evaluate_panel(
        CHR21_DOSAGE_PANEL_NAME,
        CHR21_DOSAGE_PANEL,
        "higher in trisomy 21",
        matrix,
        symbols,
        labels,
        donors,
        {donors[0], donors[-1]},
    )
    assert result.status == "NOT_APPLICABLE"
    assert result.not_applicable is not None


def test_validation_inconclusive_without_external_matrix():
    report = build_validation_report(
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        findings_available=True,
        approval_present=True,
        external_matrix_ingested=False,
        internal_holdout_measured=True,
    )
    assert report.status == "INCONCLUSIVE"
    assert any("external validation is UNKNOWN" in item for item in report.open_questions)
    assert any("not independent validation" in item for item in report.open_questions)


def test_validation_never_passes_on_internal_evidence_alone():
    report = build_validation_report(
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        findings_available=False,
        approval_present=True,
        external_matrix_ingested=False,
        internal_holdout_measured=True,
    )
    assert report.status == "BLOCKED"
