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
)
from p22.testing.cohort_fixture import write_synthetic_cohort_h5ad


@pytest.fixture(scope="module")
def fixture_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("pipeline")
    record = write_synthetic_cohort_h5ad(root / "cohort.h5ad")
    return Path(record["path"])


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
    assert all(row["status"] in {"measured", "NOT_APPLICABLE"} for row in state.metrics_rows)
    assert state.split["donor_level_overlap"] == 0

    run_real_interventions(fixture_path, state, primary_cap=32, n_features=16)
    assert any(row["status"] == "measured" for row in state.intervention_rows)
    assert any(row["status"] == "NOT_APPLICABLE" for row in state.intervention_rows)

    run_real_validation(fixture_path, state)
    assert state.validation["status"] in {"INCONCLUSIVE", "BLOCKED", "PASS"}
    assert state.panel_rows
