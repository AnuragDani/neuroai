"""Tests for the shared corrected-measurement reader used by the notebook."""

from __future__ import annotations

import json
from pathlib import Path

from p22.eval.measurement_correction import (
    CORRECTED_ARTIFACT_ABSENT,
    CORRECTED_RESULT_PRESENT,
    summarize_measurement_correction,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_checkout_reports_corrected_result_and_contract():
    summary = summarize_measurement_correction(ROOT)
    assert summary["status"] == CORRECTED_RESULT_PRESENT

    declared = summary["declared_contract"]
    assert declared["rna_matrix_key"] == "raw/X"
    assert declared["rna_axis_key"] == "raw/var"
    assert declared["atac_count_unit"] == "unique_fragment_overlap"
    assert declared["atac_count_mode"] == "fragment"
    assert declared["unknown_policy"] == "error"

    corrected = summary["corrected_result"]
    assert corrected["model"] == "cross_attention"
    assert corrected["reference"] == "token_concat"
    assert abs(corrected["estimate"] - 0.006666666666666665) < 1e-12
    assert corrected["interval"] == [-0.025, 0.035007352941176476]
    assert corrected["practical_margin"] == 0.07
    assert corrected["advantage_demonstrated"] is False

    assert summary["acceptance"]["status"] == "ACCEPTED"
    assert summary["acceptance"]["scientific_claim_allowed"] is True
    assert summary["acceptance"]["manifest_present"] is True
    assert not summary["acceptance"]["blocking_checks"]

    historical = summary["historical_result"]
    assert abs(historical["estimate"] - 0.033333333333333326) < 1e-12
    assert historical["practical_margin"] == 0.07


def test_absent_checkout_returns_declared_contract_without_raising(tmp_path):
    summary = summarize_measurement_correction(tmp_path)
    assert summary["status"] == CORRECTED_ARTIFACT_ABSENT
    assert summary["corrected_result"] is None
    assert summary["historical_result"] is None
    assert summary["acceptance"]["status"] is None
    assert summary["acceptance"]["manifest_present"] is False
    assert summary["declared_contract"]["atac_count_unit"] == "unique_fragment_overlap"
    assert summary["paths"]["corrected_record_present"] is False


def test_contract_record_overrides_declared_defaults(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/atac_measurement_contract_2026-09-21.json").write_text(
        json.dumps(
            {
                "record_type": "corrected_atac_measurement_contract",
                "count_unit": "custom_unit",
                "count_rule": "custom rule",
                "interval_rule": "custom interval",
            }
        )
    )
    summary = summarize_measurement_correction(tmp_path)
    assert summary["declared_contract"]["atac_count_unit"] == "custom_unit"
    assert summary["declared_contract"]["count_rule"] == "custom rule"
    assert summary["declared_contract"]["interval_rule"] == "custom interval"
    assert summary["status"] == CORRECTED_ARTIFACT_ABSENT


def test_run_wrapped_record_is_parsed(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/repeated_internal_comparison_corrected_2026-09-21.json").write_text(
        json.dumps(
            {
                "record_type": "corrected_internal_paired_comparison",
                "run": {
                    "primary_comparison": {
                        "model": "cross_attention",
                        "reference": "token_concat",
                        "estimate": 0.5,
                        "interval": [0.4, 0.6],
                        "practical_margin": 0.07,
                        "advantage_demonstrated": True,
                    },
                    "acceptance": {"status": "ACCEPTED", "scientific_claim_allowed": True},
                },
            }
        )
    )
    summary = summarize_measurement_correction(tmp_path)
    assert summary["status"] == CORRECTED_RESULT_PRESENT
    assert summary["corrected_result"]["estimate"] == 0.5
    assert summary["acceptance"]["status"] == "ACCEPTED"
