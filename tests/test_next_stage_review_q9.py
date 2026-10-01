"""Q9 independent review: exact hashes, no self-certification, Checkpoint C gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
REVIEW_JSON = OUT / "NO_FIT_REVIEW.json"
REVIEW_MD = OUT / "INDEPENDENT_REVIEW_Q9.md"
CHECKPOINT_C = OUT / "CHECKPOINT_C.md"

REQUIRED_ARTIFACTS = {
    "SYNTHETIC_PROTOCOL.json": OUT / "SYNTHETIC_PROTOCOL.json",
    "SPLIT_MANIFEST.json": OUT / "SPLIT_MANIFEST.json",
    "FIT_LEDGER.json": OUT / "FIT_LEDGER.json",
    "src/p22/eval/s9_analytic.py": ROOT / "src/p22/eval/s9_analytic.py",
    "tests/test_next_stage_s9_implement_q8.py": ROOT
    / "tests/test_next_stage_s9_implement_q8.py",
    "tests/test_next_stage_synthetic_protocol_q7.py": ROOT
    / "tests/test_next_stage_synthetic_protocol_q7.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def review() -> dict:
    assert REVIEW_JSON.is_file(), f"missing {REVIEW_JSON}"
    return json.loads(REVIEW_JSON.read_text())


def test_independent_reviewer_not_self_certified(review: dict) -> None:
    assert REVIEW_MD.is_file()
    assert review["disposition"] == "PASS"
    assert review["verdict"] == "PASS"
    assert review["reviewer"]["self_certification"] is False
    identity = review["reviewer"]["identity"]
    assert "independent" in identity.lower()
    assert "Task" in identity or "agent" in identity.lower()
    assert review["reviewer"]["agent_id"]
    assert review["critical_findings"] == []
    assert review["fits"] == 0
    assert review["research_fits_executed"] == 0
    text = REVIEW_MD.read_text()
    assert "PASS" in text
    assert "Worker self-assertion was not used" in text
    assert "independent of Q7/Q8 authoring session" in text
    assert review["reviewer"]["review_file"] == "INDEPENDENT_REVIEW_Q9.md"


def test_reviewed_hashes_match_live_files(review: dict) -> None:
    assert review["hashes_match"] is True
    recorded = review["reviewed_hashes"]
    assert set(recorded) == set(REQUIRED_ARTIFACTS)
    for key, path in REQUIRED_ARTIFACTS.items():
        assert path.is_file(), key
        assert recorded[key] == _sha256(path), f"hash drift: {key}"


def test_checklist_all_pass(review: dict) -> None:
    checklist = review["checklist"]
    assert len(checklist) == 10
    assert all(v == "PASS" for v in checklist.values())
    assert review["correction_cycle"] == 0
    assert review["max_correction_cycles"] == 2


def test_scientific_invariants_retained(review: dict) -> None:
    inv = review["scientific_invariants"]
    assert inv["primary"] == "B_NULL"
    assert inv["s7_v2"] == "INVALID"
    assert inv["prior_s8"] == "NO FIT"
    assert inv["power"] == "POWER_UNESTABLISHED"
    assert inv["q2_endpoint"] == "ENDPOINT_UNRESOLVED"
    assert "UNRESOLVED" in inv["q3_regulatory"]
    assert "UNRESOLVED" in inv["q5_external"]


def test_checkpoint_c_authorized_with_budget(review: dict) -> None:
    assert CHECKPOINT_C.is_file()
    text = CHECKPOINT_C.read_text()
    assert "Disposition:** `PASS`" in text or "Disposition: `PASS`" in text
    assert "authorized" in text.lower()
    cc = review["checkpoint_c"]
    assert cc["authorized_by_review"] is True
    assert cc["resource_headroom_established"] is True
    assert cc["planned_fits"] == 49
    assert cc["cap"] == 60
    assert cc["headroom_fits"] == 11
    assert cc["planned_fits"] <= cc["cap"]
    recompute = review["independent_recompute"]
    assert recompute["smoke_plus_screen_jobs"] == 49
    assert recompute["seeds_disjoint"] is True
    assert recompute["decision_seed"] == 9001
    assert 9001 not in recompute["headroom_seeds"]
