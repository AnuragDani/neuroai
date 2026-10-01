"""R8 failure-audit independent review and Checkpoint C authorization tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from p22.eval.s10_analytic import S10Refusal, refuse_unreviewed_scientific_fits
from p22.eval.s10_execute import (
    DEFAULT_REVIEW_LOCK,
    REQUIRED_LOCK_KEYS,
    execution_defaults,
    load_reviewed_hashes,
    review_lock_path,
    reviewed_hashes_complete,
    run_scientific_batch,
    verify_reviewed_hashes,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
LOCK = OUT / "R8_REVIEWED_HASHES.json"
REVIEW = OUT / "INDEPENDENT_REVIEW_R8.md"
REVIEW_JSON = OUT / "NO_FIT_REVIEW_R8.json"
CHECKPOINT_C = OUT / "CHECKPOINT_C.md"
PROTOCOL = OUT / "S10_PROTOCOL.json"
SPLIT = OUT / "S10_SPLIT_MANIFEST.json"
SEED = OUT / "S10_SEED_SCHEDULE.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_r8_review_pass_and_lock_present() -> None:
    assert REVIEW.is_file()
    assert REVIEW_JSON.is_file()
    assert LOCK.is_file()
    assert CHECKPOINT_C.is_file()
    text = REVIEW.read_text()
    assert "**PASS**" in text or "Overall verdict\n\n**PASS**" in text
    assert "fd860419-c20a-4e11-8c6f-f56ddc15fdec" in text
    assert "self-assertion" in text.lower() or "self_certification" in text.lower()
    blob = json.loads(REVIEW_JSON.read_text())
    assert blob["verdict"] == "PASS"
    assert blob["disposition"] == "PASS"
    assert blob["self_certification"] is False
    assert blob["reviewer"]["agent_id"] == "fd860419-c20a-4e11-8c6f-f56ddc15fdec"
    assert blob["checkpoint_c"]["authorized_by_review"] is True
    assert blob["correction_cycle"] == 0
    assert blob["critical_findings"] == []
    assert "PASS" in CHECKPOINT_C.read_text()


def test_external_lock_matches_live_files() -> None:
    assert reviewed_hashes_complete(LOCK) is True
    lock = json.loads(LOCK.read_text())
    hashes = lock["reviewed_hashes"]
    assert set(hashes) == set(REQUIRED_LOCK_KEYS)
    paths = {
        "S10_PROTOCOL.json": PROTOCOL,
        "S10_SPLIT_MANIFEST.json": SPLIT,
        "S10_SEED_SCHEDULE.json": SEED,
        "src/p22/eval/s10_analytic.py": ROOT / "src/p22/eval/s10_analytic.py",
        "src/p22/eval/s10_execute.py": ROOT / "src/p22/eval/s10_execute.py",
    }
    for key, path in paths.items():
        assert _sha(path) == hashes[key]
    live = verify_reviewed_hashes(
        workspace=ROOT,
        protocol_path=PROTOCOL,
        split_path=SPLIT,
        seed_path=SEED,
        lock_path=LOCK,
    )
    assert live == hashes
    # Executor digests are not self-embedded in the module.
    execute_src = (ROOT / "src/p22/eval/s10_execute.py").read_text()
    assert hashes["src/p22/eval/s10_execute.py"] not in execute_src
    assert str(DEFAULT_REVIEW_LOCK).endswith("R8_REVIEWED_HASHES.json")
    assert review_lock_path(ROOT) == LOCK


def test_serial_defaults_and_reserve_flag() -> None:
    defaults = execution_defaults()
    assert defaults["workers"] == 1
    assert defaults["parallel_dispatch"] is False
    assert defaults["thread_pool_executor"] is False
    assert defaults["reserve_attempts_before_dispatch"] is True
    assert defaults["planned_fits"] == 49
    assert defaults["scientific_cap"] == 90
    assert defaults["reviewed_hashes_complete"] is True


def test_unreviewed_dry_run_still_refused_without_auth_args() -> None:
    with pytest.raises(S10Refusal, match="R8"):
        refuse_unreviewed_scientific_fits()
    with pytest.raises(S10Refusal, match="R8"):
        run_scientific_batch()


def test_review_json_invariants_and_dependency_hash() -> None:
    blob = json.loads(REVIEW_JSON.read_text())
    inv = blob["scientific_invariants"]
    assert inv["s9"] == "INVALID"
    assert inv["s9_immutable"] is True
    assert inv["primary"] == "B_NULL"
    assert inv["q2_endpoint"] == "ENDPOINT_UNRESOLVED"
    assert inv["claim_level"] == 1
    dep = blob["dependency_hashes"]["src/p22/eval/s7_runner.py"]
    assert len(dep) == 64
    assert _sha(ROOT / "src/p22/eval/s7_runner.py") == dep
    assert blob["checkpoint_c"]["workers"] == 1
    assert blob["checkpoint_c"]["planned_fits"] == 49
    loaded = load_reviewed_hashes(LOCK)
    assert all(len(v) == 64 for v in loaded.values())


def test_checkpoint_c_blocks_biology_upgrade() -> None:
    text = CHECKPOINT_C.read_text()
    assert "claim level 1" in text.lower() or "Claim level 1" in text
    assert "INVALID" in text
    assert "ENDPOINT_UNRESOLVED" in text
    assert "B_NULL" in text
    assert "R9" in text
