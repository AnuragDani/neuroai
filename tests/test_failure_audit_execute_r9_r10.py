"""R9/R10 failure-audit closeout: skip-fits replay, INVALID disposition, handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from p22.eval.s10_execute import run_scientific_batch

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
RAW = (
    ROOT
    / "reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001"
)
STAGE_COUNTER = ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
EXECUTE = OUT / "EXECUTE.md"
EXECUTE_JSON = OUT / "execute.json"
HANDOFF = OUT / "HANDOFF.md"
VERIFICATION = OUT / "VERIFICATION.json"
LOCK = OUT / "R8_REVIEWED_HASHES.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def execute_report() -> dict:
    assert EXECUTE_JSON.is_file()
    return json.loads(EXECUTE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verification() -> dict:
    assert VERIFICATION.is_file()
    return json.loads(VERIFICATION.read_text(encoding="utf-8"))


def test_r9_execute_disposition_invalid(execute_report: dict) -> None:
    assert EXECUTE.is_file()
    assert execute_report["task"] == "R9"
    assert execute_report["disposition"] == "INVALID"
    assert execute_report["protocol_id"] == "S10_corrected_null_pairing_use_20261001"
    assert execute_report["coverage"]["complete"] is True
    assert execute_report["coverage"]["attempted"] == 49
    assert execute_report["coverage"]["completed_ok"] == 49
    assert execute_report["coverage"]["failed"] == 0
    assert execute_report["execution"]["skip_fits"] is True
    assert execute_report["execution"]["mode"] == "replay_saved_sidecars"
    assert execute_report["marginal_check"]["pass"] is False
    assert execute_report["marginal_check"]["logreg_atac_ba"] == pytest.approx(0.625)
    assert execute_report["pairing_rho0"]["pairing_label"] == "PAIRING_NEGATIVE"
    assert execute_report["pairing_rho1"]["pairing_label"] == "PAIRING_NEGATIVE"
    text = EXECUTE.read_text(encoding="utf-8")
    assert "`INVALID`" in text
    assert "PAIRING_NEGATIVE" in text
    assert "skip_fits" in text


def test_r9_raw_artifacts_complete() -> None:
    assert RAW.is_dir()
    preds = list((RAW / "donor_predictions").glob("*.donors.json"))
    ckpts = list((RAW / "checkpoints").glob("*.pt"))
    assert len(preds) == 49
    assert len(ckpts) == 12
    ledger = (RAW / "attempt_ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(ledger) == 49
    counter = json.loads((RAW / "attempt_counter.json").read_text(encoding="utf-8"))
    assert counter["attempted_fits"] == 49
    assert counter["completed_ok"] == 49
    assert counter["failed"] == 0


def test_skip_fits_replay_preserves_attempt_counters() -> None:
    before_stage = STAGE_COUNTER.read_bytes()
    before_s10 = (RAW / "attempt_counter.json").read_bytes()
    batch = run_scientific_batch(
        workspace=ROOT,
        protocol_path=OUT / "S10_PROTOCOL.json",
        split_path=OUT / "S10_SPLIT_MANIFEST.json",
        review_path=OUT / "NO_FIT_REVIEW_R8.json",
        raw_root=RAW,
        skip_fits=True,
    )
    assert batch["skip_fits"] is True
    assert batch["exec_summary"].get("n_executed_this_call") == 0
    assert batch["coverage"]["attempted"] == 49
    assert batch["interpretation"]["disposition"] == "INVALID"
    assert STAGE_COUNTER.read_bytes() == before_stage
    assert (RAW / "attempt_counter.json").read_bytes() == before_s10


def test_reviewed_hashes_still_match_lock(execute_report: dict) -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))["reviewed_hashes"]
    assert execute_report["reviewed_hashes"] == lock
    paths = {
        "S10_PROTOCOL.json": OUT / "S10_PROTOCOL.json",
        "S10_SPLIT_MANIFEST.json": OUT / "S10_SPLIT_MANIFEST.json",
        "S10_SEED_SCHEDULE.json": OUT / "S10_SEED_SCHEDULE.json",
        "src/p22/eval/s10_analytic.py": ROOT / "src/p22/eval/s10_analytic.py",
        "src/p22/eval/s10_execute.py": ROOT / "src/p22/eval/s10_execute.py",
    }
    for key, path in paths.items():
        assert _sha(path) == lock[key]


def test_r10_handoff_and_verification(verification: dict) -> None:
    assert HANDOFF.is_file()
    text = HANDOFF.read_text(encoding="utf-8")
    assert "`INVALID`" in text
    assert "One smallest next action" in text
    assert "do not continue searching for a positive" in text.lower()
    assert verification["task"] == "R10"
    assert verification["disposition"] == "DONE"
    assert verification["scientific_result"] == "INVALID"
    assert verification["task_dispositions"]["R9"]["label"] == "INVALID"
    assert verification["task_dispositions"]["R9"]["fits"] == 49
    assert verification["task_dispositions"]["R9"]["refits"] == 0
    assert verification["task_dispositions"]["Checkpoint_D"]["stop_condition_met"] is True
    assert verification["stop_condition"]["met"] is True
    assert verification["resources"]["scientific_fit_attempts"] == 49
    assert verification["resources"]["diagnostic_fit_attempts"] == 12
    assert verification["r9_gates"]["pairing_rho0"] == "PAIRING_NEGATIVE"
    assert verification["forbidden_actions_observed"]["new_fits_during_closeout"] is False
    assert "ENDPOINT_UNRESOLVED" in text or "ENDPOINT_UNRESOLVED" in json.dumps(
        verification
    )


def test_scientific_invariants_retained(verification: dict, execute_report: dict) -> None:
    for blob in (verification["scientific_invariants"], execute_report["scientific_invariants"]):
        assert blob["primary"] == "B_NULL"
        assert (
            blob.get("s9") == "INVALID"
            or blob.get("s9_selected_experiment") == "INVALID"
        )
        assert blob["prior_s8"] == "NO FIT"
        assert blob["q2_endpoint"] == "ENDPOINT_UNRESOLVED"
    assert verification["scientific_invariants"]["s9_immutable"] is True
    assert verification["scientific_invariants"]["s10_selected_experiment"] == "INVALID"
