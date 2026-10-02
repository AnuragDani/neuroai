"""E3 full-executor authorization binding: mutation refusal + resume skip (toy)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from p22.eval.execution_repair_authorization import (
    FULL_EXECUTOR_IMMUTABLE_KEYS,
    MUTABLE_COUNTER_KEY,
    lock_path,
    measure_artifact_bytes,
    mutate_and_refuse,
    refuse_changed_source_learning,
    resume_skips_completed_jobs,
)
from p22.eval.masked_atac_execute import (
    execute_jobs_serial,
    job_fit_id,
    load_attempt_counter,
    save_attempt_counter,
)
from p22.eval.masked_atac_pilot import authorize_immutable_lock

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "tasks" / "authorization_e3.json"
OUT_MD = ROOT / "tasks" / "AUTHORIZATION_E3.md"
LOCK = ROOT / "configs" / "execution_repair_full_executor_lock_2026-10-02.json"


def test_live_full_executor_lock_rematch() -> None:
    verified = refuse_changed_source_learning(workspace=ROOT)
    assert verified["ok"] is True
    assert verified["n_immutable_keys"] == len(FULL_EXECUTOR_IMMUTABLE_KEYS)
    assert verified["scientific_fits_authorized"] is False
    assert verified["scientific_status"]["masked_atac_m9"] == "NOT_AUTHORIZED"
    assert verified["mutable_counter"]["key"] == MUTABLE_COUNTER_KEY
    assert MUTABLE_COUNTER_KEY not in verified["immutable_reviewed_hashes"]
    assert LOCK.is_file()
    assert lock_path(ROOT) == LOCK


def test_mutate_each_immutable_key_refuses(tmp_path: Path) -> None:
    lock_blob = json.loads(LOCK.read_text(encoding="utf-8"))
    for key in FULL_EXECUTOR_IMMUTABLE_KEYS:
        result = mutate_and_refuse(
            workspace=ROOT,
            key=key,
            lock_blob=lock_blob,
            tmp_root=tmp_path / key.replace("/", "__"),
        )
        assert result["refused"] is True, key
        assert "hash mismatch" in result["message"]


def test_artifact_bytes_measured_from_filesystem() -> None:
    raw = ROOT / "reports/generated/nn_masked_atac_pilot_20261001"
    measured = measure_artifact_bytes(raw)
    assert measured["du_kib"] > 0
    assert measured["n_files"] >= 30
    assert measured["within_cap"] is True
    counter = json.loads((raw / "attempt_counter.json").read_text(encoding="utf-8"))
    # Counter field is not the filesystem measurement (historical gap).
    assert float(counter["artifacts_gib"]["used"]) == 0.0
    assert measured["du_gib"] > float(counter["artifacts_gib"]["used"])


def test_resume_fixture_preserves_counters_and_skips(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "predictions").mkdir()
    (raw / "checkpoints").mkdir()
    (raw / "logs").mkdir()
    counter_path = raw / "attempt_counter.json"
    jobs = [
        {"stage": "toy", "arm": "token_concat", "fold": 0},
        {"stage": "toy", "arm": "cross_attention", "fold": 0},
    ]
    fit_ids = [job_fit_id(j) for j in jobs]
    counter = {
        "stage": "toy_e3_resume",
        "scientific_fits": {"used": 1, "cap": 40},
        "smoke_fits": {"used": 0, "cap": 5},
        "total_attempts": {"used": 1, "hard_cap": 40},
        "fitting_hours": {"used": 0.0, "cap": 6.0},
        "artifacts_gib": {"used": 0.0, "cap": 4.0},
        "network_bytes": 0,
        "workers": 1,
        "torch_threads": 2,
        "reserved_fit_ids": [fit_ids[0]],
        "completed_fit_ids": [fit_ids[0]],
        "failed_fit_ids": [],
    }
    save_attempt_counter(counter_path, counter)
    calls: list[str] = []

    def fit_fn(job: dict) -> dict:
        fid = job_fit_id(job)
        calls.append(fid)
        return {"fit_id": fid, "status": "ok"}

    # First call: one remaining job executes.
    first = resume_skips_completed_jobs(
        jobs=jobs,
        raw_root=raw,
        counter_path=counter_path,
        fit_fn=fit_fn,
        execute_jobs_serial=execute_jobs_serial,
        job_fit_id=job_fit_id,
        load_attempt_counter=load_attempt_counter,
        save_attempt_counter=save_attempt_counter,
    )
    assert first["n_skipped_already_done"] == 1
    assert first["n_executed_this_call"] == 1
    assert first["used_after"] == 2
    assert calls == [fit_ids[1]]

    # Second call: both completed → skip all; used preserved.
    second = resume_skips_completed_jobs(
        jobs=jobs,
        raw_root=raw,
        counter_path=counter_path,
        fit_fn=fit_fn,
        execute_jobs_serial=execute_jobs_serial,
        job_fit_id=job_fit_id,
        load_attempt_counter=load_attempt_counter,
        save_attempt_counter=save_attempt_counter,
    )
    assert second["counter_preserved_for_skipped"] is True
    assert second["n_skipped_already_done"] == 2
    assert second["n_executed_this_call"] == 0
    assert second["used_after"] == 2
    assert calls == [fit_ids[1]]  # no new fits


def test_authorize_immutable_lock_requires_e3(tmp_path: Path) -> None:
    # Live path rematches E3.
    auth = authorize_immutable_lock(workspace=ROOT, allow_progressed_counter=True)
    assert auth["full_executor"]["ok"] is True
    assert auth["full_executor"]["scientific_fits_authorized"] is False
    # Broken lock refuses.
    bad = tmp_path / "bad_lock.json"
    blob = json.loads(LOCK.read_text(encoding="utf-8"))
    first_key = FULL_EXECUTOR_IMMUTABLE_KEYS[0]
    blob["immutable_reviewed_hashes"][first_key] = "0" * 64
    bad.write_text(json.dumps(blob) + "\n")
    with pytest.raises(Exception, match="hash mismatch|full-executor"):
        authorize_immutable_lock(
            workspace=ROOT,
            allow_progressed_counter=True,
            e3_lock_path=bad,
        )


def test_evidence_report_present() -> None:
    assert OUT_JSON.is_file(), "run scripts/report_execution_repair_authorization_e3.py"
    assert OUT_MD.is_file()
    report = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert report["disposition"] == "FULL_EXECUTOR_AUTHORIZATION_PASS"
    assert report["scientific_status_unchanged"]["masked_atac_m9"] == "NOT_AUTHORIZED"
    assert report["scientific_status_unchanged"]["primary"] == "B_NULL"
    assert report["research_fits"] == 0
    assert report["checks"]["all_mutations_refused"] is True
    assert report["checks"]["mutable_counter_excluded"] is True
    assert "FULL_EXECUTOR_AUTHORIZATION_PASS" in OUT_MD.read_text(encoding="utf-8")
