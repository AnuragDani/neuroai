"""R6 failure-audit decision and budget ledger checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
MD = OUT / "DECISION.md"
JS = OUT / "decision.json"
BUDGET_MD = OUT / "BUDGET_LEDGER.md"
BUDGET_JS = OUT / "budget_ledger.json"
COUNTER = ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
NULL_JS = OUT / "null_audit.json"
TASK_JS = OUT / "task_data_options.json"


@pytest.fixture(scope="module")
def report() -> dict:
    assert JS.is_file(), f"missing {JS}"
    assert MD.is_file(), f"missing {MD}"
    return json.loads(JS.read_text())


@pytest.fixture(scope="module")
def budget() -> dict:
    assert BUDGET_JS.is_file(), f"missing {BUDGET_JS}"
    assert BUDGET_MD.is_file(), f"missing {BUDGET_MD}"
    return json.loads(BUDGET_JS.read_text())


def test_disposition_one_experiment_no_fits(report: dict) -> None:
    assert report["disposition"] == "EXPERIMENT_SELECTED"
    assert report["fit_feasibility"] == "PASS"
    assert report["research_fits"] == 0
    assert report["diagnostic_fits"] == 0
    assert report["payload_downloads"] == 0
    labels = report["scientific_labels_retained"]
    assert labels["s9"] == "INVALID"
    assert labels["s9_immutable"] is True
    assert labels["primary"] == "B_NULL"
    chosen = report["chosen_experiment"]
    assert chosen["experiment_id"] == "S10_corrected_null_pairing_use_20261001"
    assert chosen["claim_level"] == 1
    assert chosen["route"] == "corrected_software_null_reproducibility_test"
    text = MD.read_text()
    assert "EXPERIMENT_SELECTED" in text
    assert "S10_corrected_null_pairing_use_20261001" in text
    assert "Null invalidity" in text or "null_invalidity" in text


def test_cause_ranking_partitions_null_model_dataset(report: dict) -> None:
    ranking = report["cause_ranking"]
    assert len(ranking) >= 3
    assert ranking[0]["rank"] == 1
    assert ranking[0]["cause_class"] == "null_invalidity"
    assert ranking[0]["strength"] == "ESTABLISHED"
    partitions = {c["partition"] for c in ranking}
    assert "null_invalidity" in partitions
    assert any("learned_model" in p for p in partitions)
    assert any("dataset_task" in p for p in partitions)
    null_audit = json.loads(NULL_JS.read_text())
    assert (
        report["chosen_experiment"]["null_candidate_id"]
        == null_audit["candidate_null"]["id"]
    )


def test_coverage_arithmetic_within_scientific_cap(report: dict, budget: dict) -> None:
    cov = report["chosen_experiment"]["coverage"]
    assert cov["smoke"] + cov["screen_rho0"] + cov["screen_rho1"] == 49
    assert cov["planned_scientific_fits"] == 49
    assert cov["planned_scientific_fits"] <= cov["scientific_fit_cap"]
    assert cov["headroom"] == cov["scientific_fit_cap"] - 49
    assert report["chosen_experiment"]["n_arms"] == 7
    assert len(report["chosen_experiment"]["arms"]) == 7
    assert budget["planned_selected_experiment"]["planned_scientific_fits"] == 49
    assert budget["fit_feasibility"] == "PASS"
    assert budget["checks"]["scientific_49_le_90"] is True
    assert budget["checks"]["power_established"] is False
    assert budget["r6_consumption"]["scientific_fits"] == 0


def test_counter_consistency_and_serial_default(report: dict, budget: dict) -> None:
    counter = json.loads(COUNTER.read_text())
    stage = budget["stage_cumulative_before_r7"]
    assert stage["diagnostic_fit_attempts"] == counter["diagnostic_fit_attempts"]
    assert stage["scientific_fit_attempts"] == counter["scientific_fit_attempts"]
    # Ledger freezes pre-R7 generator draws; counter may grow in R7+.
    assert stage["generator_only_draws"] == 81
    assert counter["generator_only_draws"] >= stage["generator_only_draws"]
    assert stage["diagnostic_remaining"] == 0
    assert report["chosen_experiment"]["execution"]["workers"] == 1
    assert report["chosen_experiment"]["execution"]["parallel_scientific_dispatch"] is False
    assert report["chosen_experiment"]["acquisition_mib"] == 0
    assert budget["planned_selected_experiment"]["payload_mib"] == 0
    assert budget["planned_selected_experiment"]["planned_diagnostic_fits"] == 0


def test_rejected_alternatives_and_constraints(report: dict) -> None:
    rejected = {r["id"] for r in report["rejected_alternatives"]}
    assert "current_paired_masked_atac_from_rna_20261001" in rejected
    assert "bounded_new_dataset_ingestion" in rejected
    assert "biological_cell_state_pilot" in rejected
    assert "s9_relaunch_or_gate_widen" in rejected
    assert "paper_only_closeout" in rejected
    task = json.loads(TASK_JS.read_text())
    assert task["constraints_for_r6"]["dataset_change_from_null_alone"] == "forbidden"
    assert task["constraints_for_r6"]["nemo_external_test_role"] == "preserved"
    text = MD.read_text()
    assert "do not choose paper-only" in text.lower() or "paper-only" in text.lower()
    assert "Deferred" in text or "deferred" in text


def test_smallest_useful_result_and_inference_limits(report: dict) -> None:
    chosen = report["chosen_experiment"]
    assert len(chosen["smallest_useful_result"]) >= 1
    assert any("rho=0" in s or "ρ=0" in s for s in chosen["smallest_useful_result"])
    limits = set(chosen["inference_limitations"])
    assert "claim_level_1_software_only" in limits
    assert "does_not_overturn_historical_s9_INVALID" in limits
    assert "fit_feasibility_is_not_established_power" in limits
    assert chosen["effect_assumptions_before_outcomes"]
    assert "s9_rescue" in chosen["forbidden"]
    assert "seed_shopping" in chosen["forbidden"]
    text = BUDGET_MD.read_text()
    assert "49" in text
    assert "PASS" in text
