"""Q4 sampling feasibility: support repair, eligibility freeze, label-free IDs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
    / "sampling_feasibility.json"
)
FEASIBILITY_MD = FEASIBILITY_JSON.with_name("SAMPLING_FEASIBILITY.md")
GOLDEN_TARGETED = FEASIBILITY_JSON.with_name("TARGETED_SAMPLING_FEASIBILITY.json")
SCRIPT = ROOT / "scripts" / "report_next_stage_sampling_feasibility.py"
H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
EXPECTED_GOLDEN_SHA256 = (
    "5c0fbd58d6c33db43c005e1c34fb6f82990efbe4d0fbe4c8ab2a0599a662b8d9"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_sampling_feasibility", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert FEASIBILITY_JSON.is_file(), f"missing {FEASIBILITY_JSON}; run Q4 reporter first"
    return json.loads(FEASIBILITY_JSON.read_text())


def test_markdown_and_disposition(report: dict) -> None:
    assert FEASIBILITY_MD.is_file()
    text = FEASIBILITY_MD.read_text()
    assert "SUPPORT_REPAIR_PASS" in text
    assert "ELIGIBILITY_FROZEN" in text
    assert report["disposition"] == "SUPPORT_REPAIR_PASS"
    assert report["eligibility_status"] == "ELIGIBILITY_FROZEN"
    assert report["eligibility_freeze"]["biological_cell_state_pilot_eligibility"][
        "status"
    ] == "BLOCKED"
    assert report["eligibility_freeze"]["power_status"] == "POWER_UNESTABLISHED"


def test_mic_opc_repair_and_anchors(report: dict) -> None:
    by_type = {
        row["cell_type"]: row for row in report["measured_support_repair"]["types"]
    }
    assert "MIC" in by_type
    assert by_type["MIC"]["global_selected_ge20"] == {"CON": 0, "DS": 0}
    assert by_type["MIC"]["targeted_selected_ge20"] == {"CON": 9, "DS": 10}
    assert "OPC" in by_type
    assert by_type["OPC"]["global_selected_ge20"] == {"CON": 0, "DS": 0}
    assert by_type["OPC"]["targeted_selected_ge20"] == {"CON": 12, "DS": 13}
    # Anchors retain full support under targeted sampling
    t = report["targeted_support_by_type"]
    assert t["RG"]["CON"]["selected_donors_ge20"] == 15
    assert t["RG"]["DS"]["selected_donors_ge20"] == 15
    assert t["NEU_CUX2"]["CON"]["selected_donors_ge20"] == 15
    assert t["NEU_CUX2"]["DS"]["selected_donors_ge20"] == 15


def test_age_one_class_and_eligibility_rules(report: dict) -> None:
    one = report["age_sex_library_support"]["one_class_ages"]
    assert one["10"] == {"CON": 1}
    assert one["14"] == {"CON": 1}
    assert one["15"] == {"DS": 1}
    rules = report["eligibility_freeze"]["rules"]
    assert rules["min_cells_per_donor_support_floor"] == 20
    assert rules["targeted_cap_per_donor_per_type"] == 64
    assert rules["sampling_seed"] == 22
    assert rules["age_covariate_rules"]["age_is_not_cell_state_endpoint"] is True
    assert set(rules["age_covariate_rules"]["one_class_ages_excluded_from_age_matched_claims"]) == {
        "10",
        "14",
        "15",
    }
    # Split-feasible types must include well-supported anchors
    feasible = report["eligibility_freeze"][
        "candidate_types_split_feasible_under_frozen_5x5"
    ]
    assert "RG" in feasible
    assert "NEU_CUX2" in feasible
    assert "MIC" not in feasible  # support repaired but not every-fold both-class


def test_practical_margin_toy_cases(report: dict) -> None:
    mod = _load_script()
    # Hand cases from estimand contract: 15+15 → 0.07; 8+8 → 0.13
    assert mod.practical_margin(15, 15) == 0.07
    assert mod.score_resolution(15, 15) == pytest.approx(1.0 / 30.0)
    assert mod.practical_margin(8, 8) == 0.13
    assert report["cohort_uncertainty_full_15_plus_15"]["practical_margin"] == 0.07
    assert report["cohort_uncertainty_full_15_plus_15"]["power_status"] == (
        "POWER_UNESTABLISHED"
    )


@pytest.mark.skipif(not H5AD.is_file(), reason="shared H5AD not available")
def test_live_targeted_ids_match_golden_and_label_free(report: dict) -> None:
    mod = _load_script()
    assert GOLDEN_TARGETED.is_file()
    assert mod.sha256_file(GOLDEN_TARGETED) == EXPECTED_GOLDEN_SHA256
    assert report["sampling"]["golden_targeted_ids_exact_match"] is True
    assert report["sampling"]["label_free_check"]["label_free"] is True

    obs = mod.load_obs(H5AD)
    _, ids, hashes = mod.sample_targeted(obs)
    golden = json.loads(GOLDEN_TARGETED.read_text())["selected_cell_ids_by_type"]
    for cell_type in mod.CELL_TYPE_ORDER:
        assert ids[cell_type] == golden[cell_type]
        assert hashes[cell_type] == report["sampling"][
            "targeted_selected_ids_sha256_by_type"
        ][cell_type]
    assert mod.verify_label_free(obs)["label_free"] is True
