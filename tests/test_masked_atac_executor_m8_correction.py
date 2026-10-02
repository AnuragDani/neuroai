"""M8 correction-cycle tests: live hash gate, reserve, skip-fits (no research fits)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from p22.eval.masked_atac_execute import (
    ALLOWED_RAW_ROOT,
    MaskedAtacExecuteRefusal,
    execute_jobs_serial,
    job_fit_id,
    refuse_unreviewed_learning,
    reserve_attempt_before_dispatch,
    run_authorized_pilot,
    save_attempt_counter,
    verify_reviewed_hashes,
)
from p22.eval.masked_atac_protocol import enumerate_planned_jobs
from p22.eval.s7_ledger import sha256_file

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
)
M8_LOCK = TASK_DIR / "M8_REVIEWED_HASHES.json"
COUNTER = ROOT / "reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json"


def test_fail_lock_and_empty_pass_lock_refuse_learning() -> None:
    # Live M8 PASS lock must authorize (correction cycle 1).
    refuse_unreviewed_learning(m8_lock_path=M8_LOCK, workspace=ROOT)
    fake_fail = TASK_DIR / "_tmp_fake_m8_fail_lock_for_test.json"
    fake_partial = TASK_DIR / "_tmp_fake_m8_partial_lock_for_test.json"
    try:
        fake_fail.write_text(
            json.dumps(
                {
                    "verdict": "FAIL",
                    "fits_authorized": False,
                    "reviewed_hashes": {},
                }
            )
        )
        with pytest.raises(MaskedAtacExecuteRefusal, match="fits_authorized"):
            refuse_unreviewed_learning(m8_lock_path=fake_fail, workspace=ROOT)
        # Synthetic PASS without complete reviewed_hashes must refuse (M8-C1).
        fake_partial.write_text(
            json.dumps(
                {
                    "verdict": "PASS",
                    "fits_authorized": True,
                    "reviewed_hashes": {"PILOT_PROTOCOL.json": "0" * 64},
                }
            )
        )
        with pytest.raises(MaskedAtacExecuteRefusal):
            refuse_unreviewed_learning(m8_lock_path=fake_partial, workspace=ROOT)
    finally:
        for path in (fake_fail, fake_partial):
            if path.exists():
                path.unlink()


def test_reserve_before_dispatch_is_durable(tmp_path: Path) -> None:
    counter_path = tmp_path / "attempt_counter.json"
    save_attempt_counter(
        counter_path,
        {
            "stage": "masked_atac_pilot_20261001",
            "scientific_fits": {"used": 0, "cap": 40},
            "smoke_fits": {"used": 0, "cap": 5},
            "total_attempts": {"used": 0, "hard_cap": 40},
            "fitting_hours": {"used": 0.0, "cap": 6.0},
            "artifacts_gib": {"used": 0.0, "cap": 4.0},
            "reserved_fit_ids": [],
            "completed_fit_ids": [],
            "failed_fit_ids": [],
        },
    )
    c1 = reserve_attempt_before_dispatch(
        counter_path=counter_path, fit_id="smoke|token_concat|fold0", stage="smoke"
    )
    assert c1["total_attempts"]["used"] == 1
    assert c1["smoke_fits"]["used"] == 1
    assert "smoke|token_concat|fold0" in c1["reserved_fit_ids"]
    # Re-read from disk — reserve survived process boundary.
    disk = json.loads(counter_path.read_text())
    assert disk["total_attempts"]["used"] == 1
    assert disk["reserved_fit_ids"] == ["smoke|token_concat|fold0"]
    # Owned production counter must remain untouched.
    prod = json.loads(COUNTER.read_text())
    assert prod["total_attempts"]["used"] == 0


def test_serial_skip_completed_and_skip_fits_path(tmp_path: Path) -> None:
    raw = tmp_path / "reports/generated/nn_masked_atac_pilot_20261001"
    raw.mkdir(parents=True)
    counter_path = raw / "attempt_counter.json"
    save_attempt_counter(
        counter_path,
        {
            "stage": "masked_atac_pilot_20261001",
            "scientific_fits": {"used": 0, "cap": 40},
            "smoke_fits": {"used": 0, "cap": 5},
            "total_attempts": {"used": 0, "hard_cap": 40},
            "fitting_hours": {"used": 0.0, "cap": 6.0},
            "artifacts_gib": {"used": 0.0, "cap": 4.0},
            "reserved_fit_ids": [],
            "completed_fit_ids": [],
            "failed_fit_ids": [],
        },
    )
    jobs = enumerate_planned_jobs()[:2]
    calls: list[str] = []

    def fit_fn(job: dict) -> dict:
        calls.append(job_fit_id(job))
        return {"ok": True, "fit_id": job_fit_id(job)}

    first = execute_jobs_serial(
        jobs, raw_root=raw, counter_path=counter_path, fit_fn=fit_fn
    )
    assert first["n_executed_this_call"] == 2
    assert len(calls) == 2
    second = execute_jobs_serial(
        jobs, raw_root=raw, counter_path=counter_path, fit_fn=fit_fn
    )
    assert second["n_executed_this_call"] == 0
    assert second["n_skipped_already_done"] == 2
    assert len(calls) == 2  # no refit

    # skip_fits under synthetic FAIL lock must refuse authorization.
    fake_fail = TASK_DIR / "_tmp_fake_m8_fail_lock_skip_fits.json"
    try:
        fake_fail.write_text(
            json.dumps(
                {
                    "verdict": "FAIL",
                    "fits_authorized": False,
                    "reviewed_hashes": {},
                }
            )
        )
        with pytest.raises(MaskedAtacExecuteRefusal):
            run_authorized_pilot(
                workspace=ROOT,
                raw_root=raw,
                m8_lock_path=fake_fail,
                skip_fits=True,
            )
    finally:
        if fake_fail.exists():
            fake_fail.unlink()

    # Live PASS + skip_fits must authorize without dispatching learning or
    # mutating the owned production counter.
    prod_before = json.loads(COUNTER.read_text())
    replay = run_authorized_pilot(
        workspace=ROOT,
        raw_root=raw,
        m8_lock_path=M8_LOCK,
        skip_fits=True,
    )
    assert replay.get("learning") is False or replay.get("n_executed_this_call", 0) == 0
    prod_after = json.loads(COUNTER.read_text())
    assert prod_after["total_attempts"]["used"] == prod_before["total_attempts"]["used"] == 0


def test_verify_reviewed_hashes_rejects_fail_lock() -> None:
    live = verify_reviewed_hashes(workspace=ROOT, lock_path=M8_LOCK)
    assert len(live) >= 10
    fake_fail = TASK_DIR / "_tmp_fake_m8_fail_lock_verify.json"
    try:
        fake_fail.write_text(
            json.dumps(
                {
                    "verdict": "FAIL",
                    "fits_authorized": False,
                    "reviewed_hashes": {},
                }
            )
        )
        with pytest.raises(MaskedAtacExecuteRefusal):
            verify_reviewed_hashes(workspace=ROOT, lock_path=fake_fail)
    finally:
        if fake_fail.exists():
            fake_fail.unlink()
    # Production counter and ALLOWED_RAW_ROOT contract still present.
    assert COUNTER.is_file()
    assert "nn_masked_atac_pilot_20261001" in ALLOWED_RAW_ROOT
    assert sha256_file(COUNTER)
