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

    run_real_model_comparison(fixture_path, state, primary_cap=32, n_features=64)
    names = [row["model"] for row in state.metrics_rows]
    assert names[:5] == [
        "majority_class",
        "chr21_dosage",
        "qc_covariate_logistic",
        "pseudobulk_rna_logistic",
        "rna_only",
    ]
    assert all(row["status"] in {"measured", "NOT_APPLICABLE"} for row in state.metrics_rows)
    assert state.split["donor_level_overlap"] == 0

    run_real_interventions(fixture_path, state, primary_cap=32, n_features=16)
    assert any(row["status"] == "measured" for row in state.intervention_rows)
    assert any(row["status"] == "NOT_APPLICABLE" for row in state.intervention_rows)

    run_real_validation(fixture_path, state)
    assert state.validation["status"] in {"INCONCLUSIVE", "BLOCKED", "PASS"}
    assert state.panel_rows
