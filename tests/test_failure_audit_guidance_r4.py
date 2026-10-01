"""R4 failure-audit guidance and claim hierarchy checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
MD = OUT / "GUIDANCE_AND_CLAIMS.md"
JS = OUT / "guidance_and_claims.json"
PREFLIGHT = OUT / "PREFLIGHT.md"
ATTESTATION = ROOT / "plan/real_data_attestation_2026-09-08.json"
ENDPOINTS = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/ENDPOINTS.md"
)
JUL2 = Path(
    "/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/"
    "MOM/2026-07-02/MOM_07-02-2026_Transcript_and_Meeting_Notes.md"
)
JUL21 = Path(
    "/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/"
    "MOM/2026-07-21/MOM_07-21-2026_Transcript_and_Meeting_Notes.md"
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def report() -> dict:
    assert JS.is_file(), f"missing {JS}"
    assert MD.is_file(), f"missing {MD}"
    return json.loads(JS.read_text())


def test_disposition_and_no_fits(report: dict) -> None:
    assert report["disposition"] == "GUIDANCE_CLAIMS_PASS"
    assert report["research_fits"] == 0
    assert report["diagnostic_fits"] == 0
    assert report["downloads"] == 0
    labels = report["scientific_labels_retained"]
    assert labels["s9"] == "INVALID"
    assert labels["q2_endpoint"] == "ENDPOINT_UNRESOLVED"
    assert labels["primary"] == "B_NULL"
    text = MD.read_text()
    assert "ENDPOINT_UNRESOLVED" in text
    assert "not silently relabeled PASS" in text or "not** silently relabeled PASS" in text
    assert "GUIDANCE_CLAIMS_PASS" in text


def test_mom_hashes_match_preflight_and_disk(report: dict) -> None:
    assert JUL2.is_file() and JUL21.is_file()
    live2 = _sha256(JUL2)
    live21 = _sha256(JUL21)
    assert report["mom_hashes"]["july_2"] == live2
    assert report["mom_hashes"]["july_21"] == live21
    pre = PREFLIGHT.read_text()
    assert live2 in pre
    assert live21 in pre


def test_guidance_table_separates_professor_and_worker(report: dict) -> None:
    rows = report["guidance_rows"]
    assert len(rows) >= 10
    ids = {r["id"] for r in rows}
    assert {"G1", "G4", "G7", "G9"}.issubset(ids)
    for r in rows:
        assert r["professor"]
        assert r["worker"]
        assert r["professor"] != r["worker"]
    text = MD.read_text()
    assert "Professor request" in text
    assert "Worker restriction" in text
    assert "[00:36]" in text or "Jul 2 [00:36]" in text
    assert "[19:30]" in text
    assert "[14:02]" in text or "14:02" in text
    assert "wet lab" in text.lower() or "wet-lab" in text.lower()


def test_claim_hierarchy_gate_mapping(report: dict) -> None:
    levels = {c["level"]: c for c in report["claim_hierarchy_gates"]}
    assert set(levels) == {1, 2, 3, 4}
    assert levels[1]["q2_blocks"] is False
    assert levels[2]["q2_blocks"] is False
    assert levels[3]["q2_blocks"] is False
    assert levels[4]["q2_blocks"] is True
    assert levels[1]["proceed_with_current_inputs"] is True
    assert levels[2]["proceed_with_current_inputs"] is True
    assert levels[4]["proceed_with_current_inputs"] is False
    assert levels[3].get("limited") is True
    paths = report["current_data_paths"]
    assert paths["claim4_biological_cell_state"] == "blocked"
    assert paths["dataset_change_from_null_alone"] == "forbidden"
    assert paths["nemo_external_test_role"] == "preserved"


def test_prospective_amendment_does_not_unlock_biology(report: dict) -> None:
    amd = report["prospective_amendment"]
    assert amd["q2_relabeled_pass"] is False
    assert amd["authorizes_new_biological_claim"] is False
    assert amd["authorizes_experiment_by_itself"] is False
    assert "level 4" in amd["summary"] or "claim level 4" in amd["summary"]
    assert ENDPOINTS.is_file()
    ep = ENDPOINTS.read_text()
    assert "ENDPOINT_UNRESOLVED" in ep
    assert "Disposition:** `ENDPOINT_UNRESOLVED`" in ep or "`ENDPOINT_UNRESOLVED`" in ep


def test_attestation_and_objective_approval_bounds(report: dict) -> None:
    assert ATTESTATION.is_file()
    att = json.loads(ATTESTATION.read_text())
    assert att["professor_approval_date"] is None
    assert att["independently_verified"] is False
    live = _sha256(ATTESTATION)
    assert report["attestation"]["sha256"] == live
    oa = report["objective_approval"]
    assert oa["dated_independent_fang_approval_for_changed_disease_objective"] is False
    assert oa["may_claim_professor_endorsed_changed_disease_task"] is False
    assert oa["user_attestation_existing_public_plans"] is True
