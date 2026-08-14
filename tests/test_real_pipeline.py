"""Smoke test for the real-analysis orchestrator on a tiny fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from p22.eval.real_pipeline import (
    RealAnalysisState,
    freeze_real_estimand,
    run_real_interventions,
    run_real_model_comparison,
    run_real_validation,
    run_resource_and_atac,
    run_schema_qc_census,
    summarize_same_cap_results,
)
from p22.testing.cohort_fixture import write_synthetic_cohort_h5ad


@pytest.fixture(scope="module")
def fixture_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("pipeline")
    record = write_synthetic_cohort_h5ad(root / "cohort.h5ad")
    return Path(record["path"])


def _metric_rows(scores_by_cap: dict[int, dict[str, float]]) -> list[dict[str, object]]:
    return [
        {
            "model": model,
            "cap": cap,
            "status": "measured",
            "donor_balanced_accuracy": score,
        }
        for cap, scores in scores_by_cap.items()
        for model, score in scores.items()
    ]


def _delta(
    cap: int,
    reference: str,
    value: float,
    lower: float,
    upper: float,
    verdict: str,
) -> dict[str, object]:
    return {
        "cap": cap,
        "model": "rna_only",
        "reference": reference,
        "donor_balanced_accuracy_delta": value,
        "bootstrap_lower": lower,
        "bootstrap_upper": upper,
        "practical_margin": 0.07,
        "verdict": verdict,
    }


def test_same_cap_summary_is_inconclusive_when_rank_changes() -> None:
    rows = _metric_rows(
        {
            64: {"chr21_dosage": 0.9, "pseudobulk_rna_logistic": 0.7, "rna_only": 0.8},
            128: {"chr21_dosage": 0.8, "pseudobulk_rna_logistic": 0.7, "rna_only": 0.9},
            256: {"chr21_dosage": 0.85, "pseudobulk_rna_logistic": 0.7, "rna_only": 0.9},
        }
    )

    summary = summarize_same_cap_results(rows, [], primary_cap=256)

    assert summary["status"] == "INCONCLUSIVE"
    assert summary["stable_point_winner"] is None
    assert "changes across cell caps" in summary["conclusion"]


def test_same_cap_summary_supports_rna_only_only_with_both_paired_results() -> None:
    rows = _metric_rows(
        {
            cap: {"chr21_dosage": 0.75, "pseudobulk_rna_logistic": 0.7, "rna_only": 0.9}
            for cap in (64, 128, 256)
        }
    )
    deltas = [
        _delta(256, "chr21_dosage", 0.15, 0.08, 0.22, "success"),
        _delta(256, "pseudobulk_rna_logistic", 0.2, 0.1, 0.3, "success"),
    ]

    summary = summarize_same_cap_results(rows, deltas, primary_cap=256)

    assert summary["status"] == "SUPPORTED"
    assert summary["stable_point_winner"] == "rna_only"
    assert "exceeds both capped baselines" in summary["conclusion"]


def test_same_cap_summary_keeps_point_winner_inconclusive_when_interval_crosses_zero() -> None:
    rows = _metric_rows(
        {
            cap: {"chr21_dosage": 0.95, "pseudobulk_rna_logistic": 0.7, "rna_only": 0.85}
            for cap in (64, 128, 256)
        }
    )
    deltas = [_delta(256, "chr21_dosage", -0.1, -0.2, 0.02, "inconclusive")]

    summary = summarize_same_cap_results(rows, deltas, primary_cap=256)

    assert summary["status"] == "INCONCLUSIVE"
    assert summary["stable_point_winner"] == "chr21_dosage"
    assert "does not support superiority" in summary["conclusion"]


def test_real_pipeline_stages(fixture_path: Path) -> None:
    state = RealAnalysisState()
    run_schema_qc_census(fixture_path, state)
    assert state.qc["n_donors_post_qc"] == 30
    assert state.keep_mask is not None

    run_resource_and_atac(
        fixture_path,
        state,
        fragment_asset={"present": True, "file_size": None},
        fragment_build_approved=False,
    )
    assert state.atac_branch["branch"] == "B2b"
    assert state.resource["measurements"]

    freeze_real_estimand(state)
    assert state.estimand["status"] == "PASS"
    assert state.split["donor_overlap_count"] == 0

    run_real_model_comparison(
        fixture_path,
        state,
        primary_cap=32,
        sensitivity_caps=(8, 16),
        n_features=64,
    )
    context_rows = [row for row in state.metrics_rows if row.get("cap") is None]
    assert [row["model"] for row in context_rows[:4]] == [
        "majority_class",
        "chr21_dosage",
        "qc_covariate_logistic",
        "pseudobulk_rna_logistic",
    ]

    capped_rows = [row for row in state.metrics_rows if row.get("cap") is not None]
    assert len(capped_rows) == 9
    for cap in (8, 16, 32):
        rows = [row for row in capped_rows if row["cap"] == cap]
        assert {row["model"] for row in rows} == {
            "chr21_dosage",
            "pseudobulk_rna_logistic",
            "rna_only",
        }
        assert len({row["sample_row_sha256"] for row in rows}) == 1
        assert {row["n_donors"] for row in rows} == {30}
        assert {row["sample_seed"] for row in rows} == {0}

    assert len(state.paired_deltas) == 6
    assert {row["cap"] for row in state.paired_deltas} == {8, 16, 32}
    assert state.same_cap_summary["primary_cap"] == 32
    assert state.same_cap_summary["status"] in {"SUPPORTED", "INCONCLUSIVE"}
    assert state.same_cap_summary["conclusion"] in state.headline
    assert all(row["status"] in {"measured", "NOT_APPLICABLE"} for row in state.metrics_rows)
    assert state.split["donor_level_overlap"] == 0

    run_real_interventions(fixture_path, state, primary_cap=32, n_features=16)
    assert any(row["status"] == "measured" for row in state.intervention_rows)
    assert any(row["status"] == "NOT_APPLICABLE" for row in state.intervention_rows)

    run_real_validation(fixture_path, state)
    assert state.validation["status"] in {"INCONCLUSIVE", "BLOCKED", "PASS"}
    assert state.panel_rows
