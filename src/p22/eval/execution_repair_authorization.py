"""E3 full-executor authorization binding for execution repair (2026-10-02).

Kept outside M8 ``REQUIRED_LOCK_KEYS`` so locked adapter/executor modules remain
byte-stable while authorization covers the real runner, preprocessing/fit module,
repair helpers and transitive dependencies. Mutable attempt counters stay outside
immutable source digests. Scientific M9 acceptance remains NOT_AUTHORIZED.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from p22.eval.s7_ledger import sha256_file

LOCK_REL = "configs/execution_repair_full_executor_lock_2026-10-02.json"
LOCK_SCHEMA = "execution_repair_full_executor_lock_v1"
ARTIFACT_GIB_CAP = 4.0

# Immutable source/path digests (no mutable counters).
FULL_EXECUTOR_IMMUTABLE_KEYS: tuple[str, ...] = (
    "scripts/run_masked_atac_m9.py",
    "src/p22/eval/masked_atac_pilot.py",
    "src/p22/eval/execution_repair_authorization.py",
    "src/p22/eval/execution_repair_provenance.py",
    "src/p22/eval/execution_repair_runtime_mask.py",
    "src/p22/eval/execution_repair_checkpoint.py",
    "src/p22/eval/masked_atac_execute.py",
    "src/p22/eval/masked_atac_adapter.py",
    "src/p22/eval/masked_atac_protocol.py",
    "src/p22/eval/masked_atac_metrics.py",
    "src/p22/eval/masked_atac_splits.py",
    "src/p22/eval/masked_atac_target.py",
    "src/p22/eval/multiome_runner.py",
    "src/p22/eval/s7_runner.py",
    "src/p22/training/loop.py",
    "src/p22/training/mil_loop.py",
    "src/p22/data/transforms.py",
)

MUTABLE_COUNTER_KEY = (
    "reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json"
)
ALLOWED_RAW_ROOT = "reports/generated/nn_masked_atac_pilot_20261001"


class AuthorizationBindingError(ValueError):
    """Refuse learning when the full-executor lock does not rematch."""


def resolve_executor_artifact_path(workspace: Path, key: str) -> Path:
    return Path(workspace) / key


def lock_path(workspace: Path | None = None) -> Path:
    if workspace is None:
        return Path(LOCK_REL)
    return Path(workspace) / LOCK_REL


def live_immutable_hashes(workspace: Path) -> dict[str, str]:
    workspace = Path(workspace)
    out: dict[str, str] = {}
    for key in FULL_EXECUTOR_IMMUTABLE_KEYS:
        path = resolve_executor_artifact_path(workspace, key)
        if not path.is_file():
            raise AuthorizationBindingError(f"missing executor artifact {key}: {path}")
        out[key] = sha256_file(path)
    return out


def live_mutable_counter_digest(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    path = resolve_executor_artifact_path(workspace, MUTABLE_COUNTER_KEY)
    if not path.is_file():
        raise AuthorizationBindingError(f"missing mutable counter: {path}")
    blob = json.loads(path.read_text(encoding="utf-8"))
    return {
        "key": MUTABLE_COUNTER_KEY,
        "sha256": sha256_file(path),
        "total_attempts_used": int(blob["total_attempts"]["used"]),
        "smoke_fits_used": int(blob["smoke_fits"]["used"]),
        "scientific_fits_used": int(blob["scientific_fits"]["used"]),
        "note": "mutable; excluded from immutable source lock rematch",
    }


def measure_artifact_bytes(raw_root: Path | str) -> dict[str, Any]:
    """Filesystem byte measurement; counter artifacts_gib.used is not this."""
    root = Path(raw_root)
    if not root.is_dir():
        raise AuthorizationBindingError(f"raw root missing for artifact measure: {root}")
    completed = subprocess.run(
        ["du", "-sk", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    kib = int(completed.stdout.split()[0])
    gib = kib / (1024.0 * 1024.0)
    # Also sum regular-file sizes for an independent check (tmp fixtures).
    walk_bytes = 0
    n_files = 0
    for path in root.rglob("*"):
        if path.is_file():
            walk_bytes += int(path.stat().st_size)
            n_files += 1
    return {
        "raw_root": str(root),
        "du_kib": kib,
        "du_bytes": kib * 1024,
        "du_gib": gib,
        "walk_file_bytes": walk_bytes,
        "n_files": n_files,
        "within_cap": gib <= ARTIFACT_GIB_CAP,
        "artifact_gib_cap": ARTIFACT_GIB_CAP,
        "note": (
            "live filesystem measure; counter artifacts_gib.used is not this value"
        ),
    }


def load_full_executor_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AuthorizationBindingError(f"missing full-executor lock: {path}")
    blob = json.loads(path.read_text(encoding="utf-8"))
    if blob.get("schema") != LOCK_SCHEMA:
        raise AuthorizationBindingError(
            f"unexpected lock schema {blob.get('schema')!r}; want {LOCK_SCHEMA}"
        )
    return blob


def verify_full_executor_lock(
    *,
    workspace: Path,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    """Rematch immutable executor digests; leave mutable counter separate."""
    workspace = Path(workspace)
    lock = Path(lock_file) if lock_file is not None else lock_path(workspace)
    blob = load_full_executor_lock(lock)
    expected = blob.get("immutable_reviewed_hashes") or {}
    if set(expected) != set(FULL_EXECUTOR_IMMUTABLE_KEYS):
        missing = sorted(set(FULL_EXECUTOR_IMMUTABLE_KEYS) - set(expected))
        extra = sorted(set(expected) - set(FULL_EXECUTOR_IMMUTABLE_KEYS))
        raise AuthorizationBindingError(
            f"lock key set mismatch; missing={missing} extra={extra}"
        )
    live = live_immutable_hashes(workspace)
    mismatches: list[str] = []
    for key in FULL_EXECUTOR_IMMUTABLE_KEYS:
        want = str(expected[key])
        got = live[key]
        if want != got:
            mismatches.append(f"{key}: expected {want} got {got}")
    if mismatches:
        raise AuthorizationBindingError(
            "full-executor hash mismatch (changed source refuses learning): "
            + "; ".join(mismatches[:3])
            + (f" (+{len(mismatches) - 3} more)" if len(mismatches) > 3 else "")
        )
    if MUTABLE_COUNTER_KEY in expected:
        raise AuthorizationBindingError(
            "mutable counter must not appear in immutable_reviewed_hashes"
        )
    counter = live_mutable_counter_digest(workspace)
    return {
        "ok": True,
        "lock_path": str(lock),
        "immutable_reviewed_hashes": live,
        "mutable_counter": counter,
        "scientific_fits_authorized": bool(blob.get("scientific_fits_authorized", False)),
        "scientific_status": blob.get("scientific_status_unchanged", {}),
        "n_immutable_keys": len(live),
    }


def refuse_changed_source_learning(
    *,
    workspace: Path,
    lock_file: Path | None = None,
) -> dict[str, Any]:
    """Require full-executor rematch before any learning authorization path."""
    verified = verify_full_executor_lock(workspace=workspace, lock_file=lock_file)
    # E3 binds the path; it does not flip scientific NOT_AUTHORIZED.
    if verified.get("scientific_fits_authorized"):
        raise AuthorizationBindingError(
            "E3 lock must keep scientific_fits_authorized=false; "
            "independent E4 review is required before any new scientific authorization"
        )
    return verified


def build_lock_payload(
    *,
    workspace: Path,
    date: str = "2026-10-02",
) -> dict[str, Any]:
    """Assemble lock JSON from live immutable digests (does not write)."""
    workspace = Path(workspace)
    hashes = live_immutable_hashes(workspace)
    counter = live_mutable_counter_digest(workspace)
    raw = workspace / ALLOWED_RAW_ROOT
    artifacts = measure_artifact_bytes(raw) if raw.is_dir() else None
    return {
        "schema": LOCK_SCHEMA,
        "record_type": "execution_repair_full_executor_lock",
        "stage": "E3",
        "date": date,
        "note": (
            "External lock of the complete real-data execution path for repair "
            "authorization binding. Does NOT include hash of this file. Mutable "
            "attempt_counter is recorded separately and excluded from rematch. "
            "scientific_fits_authorized remains false (NOT_AUTHORIZED)."
        ),
        "immutable_reviewed_hashes": hashes,
        "mutable_counter_separate": counter,
        "artifact_bytes_at_lock_build": artifacts,
        "scientific_fits_authorized": False,
        "smoke_learning_authorized": False,
        "scientific_status_unchanged": {
            "masked_atac_m9": "NOT_AUTHORIZED",
            "primary": "B_NULL",
            "prior_S10_S9_S7": "INVALID",
            "prior_S8": "NO FIT",
        },
        "authorized_raw_root": ALLOWED_RAW_ROOT + "/",
    }


def write_full_executor_lock(
    *,
    workspace: Path,
    out_path: Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace)
    payload = build_lock_payload(workspace=workspace)
    dest = Path(out_path) if out_path is not None else lock_path(workspace)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def mutate_and_refuse(
    *,
    workspace: Path,
    key: str,
    lock_blob: Mapping[str, Any],
    tmp_root: Path,
) -> dict[str, Any]:
    """Copy one locked artifact, corrupt it, and require refusal."""
    workspace = Path(workspace)
    src = resolve_executor_artifact_path(workspace, key)
    if not src.is_file():
        raise AuthorizationBindingError(f"cannot mutate missing {key}")
    fixture = Path(tmp_root)
    # Mirror relative layout under tmp_root as workspace.
    dest = fixture / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    # Seed all other immutable keys as copies so only one is mutated.
    for other in FULL_EXECUTOR_IMMUTABLE_KEYS:
        if other == key:
            continue
        other_src = resolve_executor_artifact_path(workspace, other)
        other_dest = fixture / other
        other_dest.parent.mkdir(parents=True, exist_ok=True)
        if not other_dest.exists():
            shutil.copy2(other_src, other_dest)
    # Counter required for verify side reports; copy live counter.
    counter_src = resolve_executor_artifact_path(workspace, MUTABLE_COUNTER_KEY)
    counter_dest = fixture / MUTABLE_COUNTER_KEY
    counter_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(counter_src, counter_dest)
    # Corrupt target.
    dest.write_bytes(dest.read_bytes() + b"\n# e3_mutated\n")
    lock_path_tmp = fixture / "e3_lock_fixture.json"
    lock_path_tmp.write_text(json.dumps(dict(lock_blob), indent=2) + "\n")
    refused = False
    message = ""
    try:
        verify_full_executor_lock(workspace=fixture, lock_file=lock_path_tmp)
    except AuthorizationBindingError as exc:
        refused = True
        message = str(exc)
    return {
        "key": key,
        "refused": refused,
        "message": message,
        "mutated_sha256": sha256_file(dest),
    }


def resume_skips_completed_jobs(
    *,
    jobs: Sequence[Mapping[str, Any]],
    raw_root: Path,
    counter_path: Path,
    fit_fn: Callable[[Mapping[str, Any]], dict[str, Any]],
    execute_jobs_serial: Callable[..., dict[str, Any]],
    job_fit_id: Callable[[Mapping[str, Any]], str],
    load_attempt_counter: Callable[[Path], dict[str, Any]],
    save_attempt_counter: Callable[[Path, Mapping[str, Any]], Any],
) -> dict[str, Any]:
    """Toy resume: completed fit_ids are skipped; counter used preserved for them."""
    raw_root = Path(raw_root)
    counter_path = Path(counter_path)
    raw_root.mkdir(parents=True, exist_ok=True)
    before = load_attempt_counter(counter_path)
    used_before = int(before["total_attempts"]["used"])
    completed_before = list(before.get("completed_fit_ids", []))
    summary = execute_jobs_serial(
        list(jobs),
        raw_root=raw_root,
        counter_path=counter_path,
        fit_fn=fit_fn,
    )
    after = load_attempt_counter(counter_path)
    return {
        "used_before": used_before,
        "used_after": int(after["total_attempts"]["used"]),
        "completed_before": completed_before,
        "completed_after": list(after.get("completed_fit_ids", [])),
        "n_skipped_already_done": int(summary["n_skipped_already_done"]),
        "n_executed_this_call": int(summary["n_executed_this_call"]),
        "counter_preserved_for_skipped": (
            int(summary["n_skipped_already_done"]) >= 1
            and int(summary["n_executed_this_call"]) == 0
            and int(after["total_attempts"]["used"]) == used_before
            and list(after.get("completed_fit_ids", [])) == completed_before
        ),
    }
