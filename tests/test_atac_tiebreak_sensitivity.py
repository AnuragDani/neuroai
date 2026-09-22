"""Tests for the shared ATAC tie-break sensitivity / cell-state reader."""

from __future__ import annotations

import json
from pathlib import Path

from p22.eval.atac_tiebreak_sensitivity import (
    TIEBREAK_ARTIFACT_ABSENT,
    TIEBREAK_RESULT_PRESENT,
    summarize_atac_tiebreak_sensitivity,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_checkout_reports_tiebreak_and_cellstate():
    summary = summarize_atac_tiebreak_sensitivity(ROOT)
    assert summary["status"] == TIEBREAK_RESULT_PRESENT

    declared = summary["declared_sensitivity"]
    assert declared["salt"] == "p22-atac-tiebreak-v1"
    assert declared["region_budget"] == 256
    assert declared["practical_margin"] == 0.07
    assert declared["sampling_seed"] == 22

    historical = summary["comparison"]["historical_corrected"]["primary"]
    assert abs(historical["estimate"] - 0.006666666666666665) < 1e-12
    assert historical["advantage_demonstrated"] is False
    tiebreak = summary["comparison"]["tiebreak"]["primary"]
    assert abs(tiebreak["estimate"] + 0.02) < 1e-12
    assert tiebreak["interval"] == [-0.05333333333333332, 0.01131649310441878]
    assert tiebreak["advantage_demonstrated"] is False

    assert summary["representation"]["historical"]["n_union_regions"] == 480
    assert summary["representation"]["sha256"]["n_union_regions"] == 465
    per_fold = summary["representation"]["per_fold_chrom1"]
    assert per_fold["historical_max"] > per_fold["sha256_max"]

    five_seed = summary["five_seed"]
    assert list(five_seed["estimates"]) == ["0", "1", "2", "3", "4"]
    assert five_seed["any_advantage_demonstrated"] is False
    assert abs(five_seed["spread"] - 0.06) < 1e-9

    controls = summary["linear_controls"]
    assert controls["historical_corrected"]["all_converged"] is True
    assert controls["tiebreak"]["all_converged"] is True
    assert controls["tiebreak"]["n_extension_used"] == 0

    cellstate = summary["cellstate"]
    assert cellstate["model_fitted"] is False
    assert cellstate["outcome_used_for_selection"] is False
    assert cellstate["n_accepted_cells"] == 248998
    assert cellstate["n_donors"] == 30
    assert cellstate["donor_invariance"]["batch_seq"]["donor_invariant"] is False
    assert cellstate["donor_invariance"]["batch_seq"]["n_varying_donors"] == 7
    assert cellstate["donor_invariance"]["dev_PCW"]["donor_invariant"] is True
    assert cellstate["proposal_name"] == "donor_aware_celltype_stratified_v1"
    for condition in ("historical_corrected", "sha256_tiebreak"):
        assert cellstate["program_coverage"][condition]["n_program_genes"] == 13
        assert cellstate["program_coverage"][condition]["genes_with_any_overlapping_region"] == 1
    assert cellstate["next_study"]["status"] == "PROPOSED_NOT_EXECUTED"


def test_absent_checkout_returns_declared_sensitivity_without_raising(tmp_path):
    summary = summarize_atac_tiebreak_sensitivity(tmp_path)
    assert summary["status"] == TIEBREAK_ARTIFACT_ABSENT
    assert summary["comparison"]["tiebreak"]["primary"] is None
    assert summary["linear_controls"] is None
    assert summary["cellstate"] is None
    assert summary["declared_sensitivity"]["salt"] == "p22-atac-tiebreak-v1"
    assert summary["paths"]["tiebreak_record_present"] is False
    assert summary["paths"]["cellstate_record_present"] is False


def test_amendment_record_overrides_declared_defaults(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/atac_tiebreak_sensitivity_2026-09-21.json").write_text(
        json.dumps(
            {
                "record_type": "prospective_atac_representation_sensitivity",
                "salt": "custom-salt",
                "ranking": "custom ranking",
                "question": "custom question",
                "region_budget": 128,
                "primary_contrast": "custom contrast",
            }
        )
    )
    summary = summarize_atac_tiebreak_sensitivity(tmp_path)
    declared = summary["declared_sensitivity"]
    assert declared["salt"] == "custom-salt"
    assert declared["ranking"] == "custom ranking"
    assert declared["question"] == "custom question"
    assert declared["region_budget"] == 128
    assert summary["status"] == TIEBREAK_ARTIFACT_ABSENT
    assert summary["paths"]["protocol_amendment_present"] is True


def test_cellstate_record_parsed_even_when_tiebreak_absent(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/cellstate_feasibility_2026-09-21.json").write_text(
        json.dumps(
            {
                "record_type": "cellstate_feasibility_assessment",
                "n_accepted_cells": 100,
                "n_capped_cells": 50,
                "n_donors": 4,
                "model_fitted": False,
                "outcome_used_for_selection": False,
                "donor_invariance": {
                    "batch_seq": {"donor_invariant": False, "n_varying_donors": 1},
                },
                "atac_panels": {"historical_corrected": {"n_regions": 10, "panel_zero_regions": 0}},
                "program_feature_coverage": {
                    "panels": {
                        "historical_corrected": {
                            "n_regions": 10,
                            "genes": {"RORB": {"rna_feature_present": True}},
                            "genes_with_any_overlapping_region": 0,
                        }
                    }
                },
                "proposal": {
                    "historical_corrected": {"name": "donor_aware_celltype_stratified_v1"}
                },
            }
        )
    )
    summary = summarize_atac_tiebreak_sensitivity(tmp_path)
    assert summary["status"] == TIEBREAK_ARTIFACT_ABSENT
    cellstate = summary["cellstate"]
    assert cellstate["n_accepted_cells"] == 100
    assert cellstate["program_coverage"]["historical_corrected"]["n_program_genes"] == 1
    assert cellstate["proposal_name"] == "donor_aware_celltype_stratified_v1"
