"""Q6 research decision: bottleneck ranking, S8 exact-band correction, fit ledger."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
DECISION_JSON = OUT / "research_decision.json"
DECISION_MD = OUT / "RESEARCH_DECISION.md"
LEDGER_JSON = OUT / "FIT_LEDGER.json"
SCRIPT = ROOT / "scripts" / "report_next_stage_research_decision.py"
DONOR_PREDS = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
    "nn_s7_covariance_split_v2_20260929/donor_predictions"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_research_decision", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert DECISION_JSON.is_file(), f"missing {DECISION_JSON}; run Q6 reporter first"
    return json.loads(DECISION_JSON.read_text())


def test_markdown_disposition_and_invariants(report: dict) -> None:
    assert DECISION_MD.is_file()
    text = DECISION_MD.read_text()
    assert "EXPERIMENT_SELECTED" in text
    assert "S9_analytic_pairing_use_synthetic_20260930" in text
    assert "mechanism mismatch" in text.lower() or "Mechanism mismatch" in text
    assert report["disposition"] == "EXPERIMENT_SELECTED"
    assert report["fit_feasibility"] == "PASS"
    assert report["fits"] == 0
    assert report["scientific_invariants"]["primary"] == "B_NULL"
    assert report["scientific_invariants"]["prior_s8"] == "NO FIT"
    assert report["scientific_invariants"]["s7_v2"] == "INVALID"


def test_s8_exact_vs_rounded_boundary(report: dict) -> None:
    s8 = report["s8_numerical_correction"]
    lo, hi = s8["bernoulli_mc"]["exact_central_95"]
    rlo, rhi = s8["bernoulli_mc"]["rounded_3dp_central_95"]
    assert rlo == 0.326
    assert rhi == 0.674
    gated = s8["boundary_case"]["exact_pooled_ba"]
    assert gated == pytest.approx(lo)
    assert s8["boundary_case"]["equals_exact_lo"] is True
    assert s8["boundary_case"]["inside_exact_band"] is True
    assert s8["boundary_case"]["inside_rounded_band_3dp"] is False
    assert s8["mechanism_mismatch_retained"] is True
    assert s8["prior_s8_no_fit_unchanged"] is True
    assert s8["illustrative_claim_with_exact_values"][
        "all_seven_arms_inside_exact_chance_band"
    ]


def test_live_sidecar_bas_match_report(report: dict) -> None:
    mod = _load_script()
    live = mod.pooled_rho0_bas(DONOR_PREDS)
    for arm, ba in report["s8_numerical_correction"]["exact_pooled_rho0_bas"].items():
        assert live[arm] == pytest.approx(ba)
    assert live["token_concat"] == pytest.approx(0.330357142857)
    assert live["gated_fusion"] == pytest.approx(0.325892857143)


def test_chosen_experiment_and_rejections(report: dict) -> None:
    chosen = report["chosen_experiment"]
    assert chosen["experiment_id"] == "S9_analytic_pairing_use_synthetic_20260930"
    assert chosen["attempted_fits"] == 49
    rejected_ids = {r["id"] for r in report["rejected_alternatives"]}
    assert "biological_cell_state_pilot" in rejected_ids
    assert "relaunch_rejected_s8_chance_null" in rejected_ids
    assert "external_nemo_acquisition_or_predictive_eval" in rejected_ids
    assert "ENDPOINT_UNRESOLVED" in report["unresolved_flags_retained"]


def test_fit_ledger_cap_and_design_unresolved_path(report: dict) -> None:
    assert LEDGER_JSON.is_file()
    ledger = json.loads(LEDGER_JSON.read_text())
    assert ledger["synthetic_attempt_cap"] == 60
    assert ledger["fit_feasibility"] == "PASS"
    assert ledger["selected_attempted_fits"] == 49
    assert ledger["selected_attempted_fits"] <= ledger["synthetic_attempt_cap"]
    by_id = {c["id"]: c for c in ledger["candidates"]}
    assert by_id["rejected_s8_chance_null_relaunch"]["status"] == "REJECT"
    assert by_id["fitted_ba_montecarlo_joint_calibration"]["status"] == (
        "DESIGN_UNRESOLVED"
    )
    assert by_id["selected_pairing_use_fitted_plant_null"]["status"] == "SELECT"
    assert by_id["selected_pairing_use_fitted_plant_null"]["breakdown"]["total"] == 49
    # Joint BA Monte Carlo lower bound exceeds cap.
    assert by_id["fitted_ba_montecarlo_joint_calibration"][
        "attempted_fits_lower_bound"
    ] > 60


def test_bernoulli_helper_matches_boundary(report: dict) -> None:
    mod = _load_script()
    y = np.array([0] * 16 + [1] * 14, dtype=int)
    lo, hi = mod.bernoulli_central_95(y, seed=0, draws=10_000)
    assert lo == pytest.approx(
        report["s8_numerical_correction"]["bernoulli_mc"]["exact_central_95"][0]
    )
    assert hi == pytest.approx(
        report["s8_numerical_correction"]["bernoulli_mc"]["exact_central_95"][1]
    )
