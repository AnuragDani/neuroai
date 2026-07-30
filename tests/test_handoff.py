"""Tests for the human-readable run summary and executed-notebook copy."""

from __future__ import annotations

import json

from p22.reports.handoff import SUMMARY_NAME, copy_executed_notebook, write_human_summary


def _manifest() -> dict[str, object]:
    return {
        "run_id": "20260101T000000Z",
        "mode": {"mode": "real_analysis"},
        "dataset_id": "f16c25da-15bd-46a4-9a3f-17093f27a2f1",
        "commit": "abc1234",
        "data_layer_label": "full cohort pseudobulk plus 256-cell capped layer",
        "atac_branch_label": "B2b RNA-only",
        "headline": ["chr21 dosage separates donors", "gated fusion NOT_APPLICABLE"],
        "gates": {"status_map": {"G0": "PASS", "G6": "NOT_APPLICABLE"}},
        "data_size_stages": {"status_map": {"R1": "PASS", "R5": "BLOCKED"}},
        "metric_rows": [
            {
                "model": "chr21_dosage",
                "layer": "full_cohort",
                "status": "measured",
                "donor_balanced_accuracy": 1.0,
                "bootstrap_lower": 0.9,
                "bootstrap_upper": 1.0,
                "not_applicable": None,
            },
            {
                "model": "gated_fusion",
                "layer": "capped",
                "status": "NOT_APPLICABLE",
                "not_applicable": "ATAC branch B2b",
            },
        ],
        "evidence_buckets": {
            "verified_real": ["donor census"],
            "metadata_only": ["GSE280175 listed in GEO"],
            "synthetic": ["fusion wiring test"],
            "blocked_or_unknown": ["external validation UNKNOWN"],
        },
        "limitations": ["no ATAC peak matrix"],
        "next_decision_owner": "researcher",
        "decision": "reframe as RNA-only",
        "next_decision": "fund fragment build or drop multimodal claim?",
        "exact_command": "P22_MODE=real_analysis make notebook-real",
    }


def test_summary_records_gates_metrics_and_evidence(tmp_path):
    target = write_human_summary(tmp_path, _manifest())
    assert target.name == SUMMARY_NAME
    text = target.read_text(encoding="utf-8")
    assert "real_analysis" in text
    assert "B2b RNA-only" in text
    assert "chr21_dosage" in text
    assert "NOT_APPLICABLE" in text
    assert "external validation UNKNOWN" in text
    assert "P22_MODE=real_analysis make notebook-real" in text


def test_summary_handles_a_run_with_no_model_rows(tmp_path):
    manifest = _manifest() | {"metric_rows": []}
    text = write_human_summary(tmp_path, manifest).read_text(encoding="utf-8")
    assert "No model rows in this run." in text


def test_executed_notebook_is_copied_without_touching_source(tmp_path):
    source = tmp_path / "executed.ipynb"
    payload = {"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    source.write_text(json.dumps(payload), encoding="utf-8")
    run_dir = tmp_path / "run"
    copied = copy_executed_notebook(source, run_dir)
    assert copied is not None
    assert copied.parent == run_dir
    assert json.loads(copied.read_text(encoding="utf-8")) == payload
    assert source.is_file()


def test_missing_executed_notebook_is_reported_as_none(tmp_path):
    assert copy_executed_notebook(tmp_path / "absent.ipynb", tmp_path / "run") is None
