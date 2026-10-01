"""R5 failure-audit task/data candidate checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
MD = OUT / "TASK_DATA_OPTIONS.md"
JS = OUT / "task_data_options.json"
CPB = OUT / "CHECKPOINT_B.md"
LEDGER = (
    ROOT
    / "reports/generated/nn_failure_audit_20261001/r5_network_ledger.jsonl"
)
GUIDANCE = OUT / "guidance_and_claims.json"


@pytest.fixture(scope="module")
def report() -> dict:
    assert JS.is_file(), f"missing {JS}"
    assert MD.is_file(), f"missing {MD}"
    return json.loads(JS.read_text())


def test_disposition_no_fits_no_payloads(report: dict) -> None:
    assert report["disposition"] == "TASK_DATA_OPTIONS_BOUNDED"
    assert report["research_fits"] == 0
    assert report["diagnostic_fits"] == 0
    assert report["payload_downloads"] == 0
    labels = report["scientific_labels_retained"]
    assert labels["s9"] == "INVALID"
    assert labels["primary"] == "B_NULL"
    assert labels["q2_endpoint"] == "ENDPOINT_UNRESOLVED"
    text = MD.read_text()
    assert "TASK_DATA_OPTIONS_BOUNDED" in text
    assert "current_paired_masked_atac_from_rna_20261001" in text


def test_network_budget_and_ledger(report: dict) -> None:
    net = report["network"]
    assert net["new_requests"] <= 20
    assert net["aggregate_new_download_bytes"] <= 32 * 1024 * 1024
    assert LEDGER.is_file()
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
    assert len(rows) == net["new_requests"]
    assert sum(r["body_bytes"] for r in rows) == net["aggregate_new_download_bytes"]
    purposes = {r["purpose"] for r in rows}
    assert "nemo_atac_counts_listing" in purposes
    assert "alt1_geo_text_brief" in purposes
    assert "alt2_geo_text_brief" in purposes


def test_masked_task_is_claim_level_2(report: dict) -> None:
    task = report["masked_measurement_task"]
    assert task["claim_level"] == 2
    assert task["status"] == "FEASIBLE_CANDIDATE"
    assert task["paired_assays"] is True
    assert task["independent_donors"] is True
    estimand = task["estimand"].lower()
    assert "not biological" in estimand
    guidance = json.loads(GUIDANCE.read_text())
    paths = guidance["current_data_paths"]
    assert paths["claim2_masked_measurement_or_pairing"] == "eligible_candidate_R5_R6"
    assert guidance["claim_hierarchy_gates"][1]["proceed_with_current_inputs"] is True


def test_three_public_candidates_nemo_preserved(report: dict) -> None:
    cands = report["public_candidates"]
    assert len(cands) == 3
    ids = {c["id"] for c in cands}
    assert "NeMO_Vuong_delaTorre_DS_snMultiome" in ids
    assert "GSE280175" in ids
    assert "GSE204684" in ids
    nemo = next(c for c in cands if c["id"].startswith("NeMO"))
    assert nemo["nemo_evaluation_role"] == "PRESERVED"
    assert nemo["nemo_switched_to_development"] is False
    assert nemo["metadata_payload_sizes"]["exceeds_256mib_ceiling"] is True
    g280 = next(c for c in cands if c["id"] == "GSE280175")
    assert g280["paired_assays"] is False
    assert g280["status"] == "EXPLORATORY_ONLY"
    g204 = next(c for c in cands if c["id"] == "GSE204684")
    assert g204["paired_assays"] is True
    validity = g204["objective_target_validity"]
    assert "no_DS" in validity


def test_constraints_forbid_dataset_change_from_null(report: dict) -> None:
    c = report["constraints_for_r6"]
    assert c["dataset_change_from_null_alone"] == "forbidden"
    assert c["nemo_external_test_role"] == "preserved"
    assert c["experiment_selected_in_r5"] is False
    assert c["public_candidate_ready_for_256mib_predictive_ingestion"] is False
    assert c["claim4_biology_current_inputs"] == "blocked"
    assert report["current_data_repair"]["dataset_defect_from_ds_null"] == "FORBIDDEN"
    text = MD.read_text()
    assert "Dataset change is **not** recommended" in text


def test_checkpoint_b_records_r3_r5(report: dict) -> None:
    assert CPB.is_file()
    text = CPB.read_text()
    assert "CHECKPOINT B" in text or "Checkpoint B" in text
    assert "EXECUTION_AUDIT_PASS" in text
    assert "GUIDANCE_CLAIMS_PASS" in text
    assert "TASK_DATA_OPTIONS_BOUNDED" in text
    assert "No new biological claim" in text or "no new biological claim" in text.lower()
    assert report["disposition"] == "TASK_DATA_OPTIONS_BOUNDED"
