"""Tests for measured resource accounting and the ATAC fragment-build gate."""

from __future__ import annotations

import time

from p22.data.resources import (
    ATAC_BRANCH_B2A,
    ATAC_BRANCH_B2B,
    PRIMARY_CAP,
    assess_fragment_build,
    build_resource_report,
    decide_atac_branch,
    environment_record,
    measure_stage,
    peak_rss_gb,
)


def test_fragment_build_refused_when_disk_is_short():
    verdict = assess_fragment_build(fragment_bytes=25_500_000_000, free_gb=12.6)
    assert verdict.feasible is False
    assert verdict.required_gb == 51.0
    assert "only 12.6 GB is free" in verdict.reason


def test_fragment_build_allowed_with_headroom():
    verdict = assess_fragment_build(fragment_bytes=5_000_000_000, free_gb=400.0)
    assert verdict.feasible is True
    assert verdict.required_gb == 10.0


def test_fragment_build_refused_when_size_unknown():
    verdict = assess_fragment_build(fragment_bytes=None, free_gb=900.0)
    assert verdict.feasible is False
    assert "size unknown" in verdict.reason


def test_branch_is_b2b_when_fragment_build_is_infeasible():
    verdict = assess_fragment_build(fragment_bytes=25_500_000_000, free_gb=12.6)
    decision = decide_atac_branch(
        peak_block_present=False,
        fragment_asset_present=True,
        fragment_build_approved=True,
        resource_budget_ok=verdict.feasible,
    )
    assert decision.branch == ATAC_BRANCH_B2B
    assert decision.multimodal_claim_allowed is False
    assert set(decision.not_applicable_models) == {"atac_only", "rna_atac_concat", "gated_fusion"}


def test_branch_is_b2a_only_with_budget_and_approval():
    decision = decide_atac_branch(
        peak_block_present=False,
        fragment_asset_present=True,
        fragment_build_approved=True,
        resource_budget_ok=True,
    )
    assert decision.branch == ATAC_BRANCH_B2A
    assert decision.multimodal_claim_allowed is True


def test_measure_stage_records_time_and_memory(tmp_path):
    def work() -> int:
        time.sleep(0.01)
        return 7

    result, measurement = measure_stage(
        "cap_256",
        work,
        cells_per_donor_cap=PRIMARY_CAP,
        disk_path=tmp_path,
        notes="unit test",
    )
    assert result == 7
    assert measurement.elapsed_seconds is not None and measurement.elapsed_seconds >= 0.01
    assert measurement.peak_rss_gb == peak_rss_gb()
    assert measurement.disk_free_gb is not None
    assert measurement.cells_per_donor_cap == PRIMARY_CAP


def test_environment_record_names_python_and_packages():
    record = environment_record()
    assert record["python"]
    assert "numpy" in record["packages"]
    assert "pandas" in record["packages"]


def test_resource_report_blocks_dense_full_matrix_conversion(tmp_path):
    _result, measurement = measure_stage(
        "cap_256", lambda: None, cells_per_donor_cap=PRIMARY_CAP, disk_path=tmp_path
    )
    report = build_resource_report(
        measurements=[measurement],
        atac_branch=decide_atac_branch(False, True),
        h5ad_available=True,
        approval_present=True,
        environment=environment_record(),
        storage={"dense_full_matrix_conversion": True},
    )
    assert report.status == "BLOCKED"
    assert any("dense full-matrix" in problem for problem in report.blocking_problems)


def test_resource_report_carries_environment_and_feasibility(tmp_path):
    _result, measurement = measure_stage(
        "cap_256", lambda: None, cells_per_donor_cap=PRIMARY_CAP, disk_path=tmp_path
    )
    report = build_resource_report(
        measurements=[measurement],
        atac_branch=decide_atac_branch(False, True),
        h5ad_available=True,
        approval_present=True,
        environment=environment_record(),
        fragment_feasibility=assess_fragment_build(25_500_000_000, 12.6),
        storage={"dense_full_matrix_conversion": False, "backed_read": True},
    )
    payload = report.to_dict()
    assert payload["environment"]["packages"]
    assert payload["fragment_feasibility"]["feasible"] is False
    assert payload["storage"]["backed_read"] is True
    assert report.status in {"PASS", "INCONCLUSIVE"}
