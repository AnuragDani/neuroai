"""R2 failure-audit null exchangeability diagnosis: orthogonality, chance BA, no fits."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
AUDIT_JSON = OUT / "null_audit.json"
AUDIT_MD = OUT / "NULL_AUDIT.md"
SCHEDULE = OUT / "R2_SEED_SCHEDULE.json"
SCRIPT = ROOT / "scripts" / "diagnose_failure_audit_null_r2.py"
PRIOR_NULL = OUT / "NULL_INVARIANCE_DIAGNOSTIC.json"
COUNTER = (
    ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
)
S9_RAW = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/"
    "finish-engineering-20260928-gnhf-worktrees/"
    "read-tasks-nn-finish-ee2202-gnhf-worktrees/"
    "read-users-anuragdan-b61180-gnhf-worktrees/"
    "execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "diagnose_failure_audit_null_r2", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert AUDIT_JSON.is_file(), f"missing {AUDIT_JSON}; run R2 diagnostic first"
    return json.loads(AUDIT_JSON.read_text())


def test_audit_files_disposition_and_zero_fits(report: dict) -> None:
    assert AUDIT_MD.is_file()
    assert SCHEDULE.is_file()
    text = AUDIT_MD.read_text()
    assert "exchangeability" in text.lower() or "Exchangeability" in text
    assert "INVALID" in text
    assert report["disposition"] == "NULL_AUDIT_PASS"
    assert report["scientific_label_retained"] == "INVALID"
    assert report["research_fits"] == 0
    assert report["diagnostic_fits"] == 0
    assert report["shared_raw_unchanged"] is True
    assert 0 < report["generator_draws_this_run"] <= 256
    assert report["generator_draws_cumulative"] <= 256


def test_orthogonality_matches_prior_diagnostic(report: dict) -> None:
    prior = json.loads(PRIOR_NULL.read_text())
    repro = report["orthogonality_reproduction"]
    assert all(repro["matches_prior_diagnostic"].values())
    assert repro["original_max_abs_donor_channel_product_mean"] == pytest.approx(
        prior["original_max_abs_donor_channel_product_mean"], abs=1e-30
    )
    assert repro["shuffled_mean_abs_donor_channel_product_mean"] == pytest.approx(
        prior["shuffled_mean_abs_donor_channel_product_mean"], rel=1e-12
    )


def test_exchangeability_and_candidate_null(report: dict) -> None:
    exch = report["exchangeability"]
    assert "cell-pair" in exch["pairing_statistic_tests"]["primary_object"].lower() or (
        "pairing" in exch["pairing_statistic_tests"]["primary_object"].lower()
    )
    assert report["orthogonal_panel"]["all_original_near_machine_zero"] is True
    assert report["orthogonal_panel"]["all_shuffled_far_from_zero"] is True
    indep = report["independent_gaussian_panel"]
    assert indep["not_s9_replacement"] is True
    assert indep["ratio_near_one"] is True
    cand = report["candidate_null"]
    assert cand["status"] == "CANDIDATE_DIAGNOSTIC_NULL"
    assert "not a successful replacement" in cand["role"].lower() or (
        "not a" in cand["role"].lower() and "replacement" in cand["role"].lower()
    )


def test_marginal_chance_vs_bootstrap_distinction(report: dict) -> None:
    marg = report["marginal_uncertainty"]
    assert marg["arms"]["logreg_rna"]["pooled_ba"] == pytest.approx(0.75)
    assert marg["arms"]["logreg_atac"]["pooled_ba"] == pytest.approx(
        0.7083333333333334
    )
    chance = marg["chance_independent_draw_reference"]
    # Finite-sample: BA≥0.75 has non-negligible chance probability for n=24.
    assert chance["P_BA_ge"]["P_BA_ge_0.75"] > 0.01
    assert chance["P_BA_ge"]["P_BA_ge_0.6"] > 0.1
    assert "independent_donor_draws" in marg["distinction"]
    assert "repeated_resampling_of_24" in marg["distinction"]
    rna_boot = marg["arms"]["logreg_rna"]["donor_bootstrap"]
    assert rna_boot["n_valid"] >= 1000
    assert rna_boot["ci95"] is not None


def test_seed_schedule_committed_and_counter(report: dict) -> None:
    schedule = json.loads(SCHEDULE.read_text())
    assert schedule["committed_before_simulation"] is True
    assert schedule["fit_attempts_allowed"] == 0
    assert len(schedule["independent_gaussian_generator_seeds"]) == 64
    assert len(schedule["orthogonal_rho0_generator_seeds"]) == 16
    counter = json.loads(COUNTER.read_text())
    assert counter["scientific_fit_attempts"] == 0
    assert counter["diagnostic_fit_attempts"] == 0
    assert counter["generator_only_draws"] == report["generator_draws_cumulative"]
    assert counter["generator_only_draws"] <= counter["generator_only_cap"]


def test_helper_refuses_shared_raw_mutation(tmp_path: Path, report: dict) -> None:
    mod = _load_script()
    before = {"tree_sha256": "aaa", "rows": ["a"]}
    after = {"tree_sha256": "bbb", "rows": ["a", "b"]}
    with pytest.raises(mod.NullAuditRefusal):
        mod._assert_no_write(before, after)
    # Shared S9 tree still present and unchanged relative to report fingerprint.
    assert S9_RAW.is_dir()
    live = mod._fingerprint_tree(S9_RAW)
    assert live["tree_sha256"] == report["shared_raw_tree_sha256"]
