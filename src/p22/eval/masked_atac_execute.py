"""Masked ATAC pilot executor: M7 dry-run + M8-gated serial path.

Enumerates planned jobs, verifies adapter/factory reuse, finite gradients,
reload identity, mixed-label selection contract, counter/hash/overwrite
refusals, live M8 hash verification, reserve-before-dispatch, and skip-fits
replay. Smoke/main learning requires independent M8 PASS with matching
working-tree digests.

Unit-test adapter learning on toy arrays is separate from smoke attempts and
does not mutate the owned attempt counters.
"""

from __future__ import annotations

import json
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

from p22.eval.masked_atac_adapter import (
    ARM_TO_PAIRED_NAME,
    LOGREG_ARMS,
    NEURAL_ARMS,
    SELECTION_METRIC_NAME,
    build_toy_mixed_label_fold,
    check_finite_gradients_cell_target,
    check_state_dict_reload_equality_cell_target,
    fit_constant_prevalence,
    fit_logreg_cell_target,
    fit_neural_cell_target,
    verify_selection_prefers_cell_log_loss_over_donor_mean_prob,
)
from p22.eval.masked_atac_metrics import (
    ADAPTER_REQUIREMENTS,
    assert_existing_mil_refuses_mixed_labels,
    refuse_output_overwrite,
)
from p22.eval.masked_atac_protocol import (
    ARMS,
    ARTIFACT_GIB_CAP,
    CLAIM_LEVEL,
    CONSTANT_ARM,
    FITTING_HOURS_CAP,
    HARD_ATTEMPT_CAP,
    NEURAL,
    PLANNED_MAIN_FITS,
    PLANNED_SMOKE_FITS,
    PLANNED_TOTAL_INTENDED,
    PRESERVED_LABELS,
    PROTOCOL_ID,
    TORCH_THREADS,
    WORKERS,
    attempt_arithmetic,
    ca_tc_param_match_for_widths,
    enumerate_planned_jobs,
)
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import paired_model
from p22.eval.s7_ledger import sha256_file
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import train_model

DISPOSITION = "IMPLEMENT_PASS"
ALLOWED_RAW_ROOT = "reports/generated/nn_masked_atac_pilot_20261001/"
REFUSED_RAW_ROOT_MARKERS = (
    "nn_s7_covariance_20260929",
    "nn_s7_covariance_split_v2_20260929",
    "nn_s8_",
    "nn_s9_analytic_pairing_20260930",
    "nn_failure_audit_20261001",
    "nn_s10_",
)
M8_LOCK_RELATIVE = (
    "tasks/nn/professor_direction_investigation_20260929/"
    "masked_atac_pilot_20261001/M8_REVIEWED_HASHES.json"
)
M8_REVIEW_RELATIVE = (
    "tasks/nn/professor_direction_investigation_20260929/"
    "masked_atac_pilot_20261001/NO_FIT_REVIEW_M8.json"
)
COUNTER_NAME = "attempt_counter.json"
LEDGER_NAME = "attempt_ledger.jsonl"

# External M8 lock keys (must match M8_REVIEWED_HASHES.reviewed_hashes).
REQUIRED_LOCK_KEYS = (
    "PILOT_PROTOCOL.json",
    "implement.json",
    "M6_REVIEWED_HASHES.json",
    "src/p22/eval/masked_atac_execute.py",
    "src/p22/eval/masked_atac_adapter.py",
    "src/p22/eval/masked_atac_protocol.py",
    "src/p22/eval/masked_atac_metrics.py",
    "src/p22/eval/masked_atac_splits.py",
    "src/p22/eval/masked_atac_target.py",
    "reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json",
)


class MaskedAtacExecuteRefusal(ValueError):
    """Refuse unauthorized learning or unsafe output contracts."""


def _stage_dir(workspace: Path) -> Path:
    return (
        Path(workspace)
        / "tasks/nn/professor_direction_investigation_20260929"
        / "masked_atac_pilot_20261001"
    )


def review_lock_path(workspace: Path | None = None) -> Path:
    if workspace is None:
        return Path(M8_LOCK_RELATIVE)
    return Path(workspace) / M8_LOCK_RELATIVE


def job_fit_id(job: Mapping[str, Any]) -> str:
    return f"{job['stage']}|{job['arm']}|fold{int(job['fold'])}"


def resolve_lock_artifact_path(workspace: Path, key: str) -> Path:
    """Map reviewed_hashes keys to workspace files."""
    workspace = Path(workspace)
    stage = _stage_dir(workspace)
    if key.startswith("src/") or key.startswith("reports/"):
        return workspace / key
    return stage / key


def refuse_if_not_allowed_raw_root(raw_root: str | Path) -> None:
    text = str(raw_root).replace("\\", "/")
    if ALLOWED_RAW_ROOT.rstrip("/") not in text:
        raise MaskedAtacExecuteRefusal(
            f"raw root must be under {ALLOWED_RAW_ROOT!r}; got {text!r}"
        )
    for marker in REFUSED_RAW_ROOT_MARKERS:
        if marker in text:
            raise MaskedAtacExecuteRefusal(
                f"refusing shared old raw root marker {marker!r} in {text!r}"
            )


def load_reviewed_hashes(lock_path: Path | None = None) -> dict[str, str]:
    path = Path(lock_path) if lock_path is not None else Path(M8_LOCK_RELATIVE)
    if not path.is_file():
        return {key: "" for key in REQUIRED_LOCK_KEYS}
    blob = json.loads(path.read_text(encoding="utf-8"))
    hashes = blob.get("reviewed_hashes") if isinstance(blob, dict) else None
    if not isinstance(hashes, dict):
        return {key: "" for key in REQUIRED_LOCK_KEYS}
    return {key: str(hashes.get(key, "") or "") for key in REQUIRED_LOCK_KEYS}


def reviewed_hashes_complete(lock_path: Path | None = None) -> bool:
    hashes = load_reviewed_hashes(lock_path)
    return all(isinstance(v, str) and len(v) == 64 for v in hashes.values())


def verify_reviewed_hashes(
    *,
    workspace: Path,
    lock_path: Path | None = None,
) -> dict[str, str]:
    """Require live digests to match the external M8 reviewed_hashes lock."""
    workspace = Path(workspace)
    lock = Path(lock_path) if lock_path is not None else review_lock_path(workspace)
    if not lock.is_file():
        raise MaskedAtacExecuteRefusal(
            f"REFUSED_UNTIL_M8: missing lock {M8_LOCK_RELATIVE}"
        )
    blob = json.loads(lock.read_text(encoding="utf-8"))
    if blob.get("verdict") != "PASS" or not blob.get("fits_authorized"):
        raise MaskedAtacExecuteRefusal(
            "REFUSED_UNTIL_M8: lock present but fits_authorized is not true"
        )
    if not reviewed_hashes_complete(lock):
        raise MaskedAtacExecuteRefusal(
            "M8_REVIEWED_HASHES incomplete; independent review PASS with full "
            "reviewed_hashes required before smoke/main learning"
        )
    expected = load_reviewed_hashes(lock)
    live: dict[str, str] = {}
    for key, digest in expected.items():
        path = resolve_lock_artifact_path(workspace, key)
        if not path.is_file():
            raise MaskedAtacExecuteRefusal(f"missing reviewed artifact {key}: {path}")
        actual = sha256_file(path)
        live[key] = actual
        if actual != digest:
            raise MaskedAtacExecuteRefusal(
                f"M8 hash mismatch for {key}: expected {digest} got {actual}"
            )
    return live


def refuse_unreviewed_learning(
    *,
    m8_lock_path: Path | None,
    workspace: Path | None = None,
) -> None:
    """Smoke/main learning requires M8 PASS lock with matching live hashes."""
    if m8_lock_path is None or not Path(m8_lock_path).is_file():
        raise MaskedAtacExecuteRefusal(
            "REFUSED_UNTIL_M8: neural smoke/main learning unauthorized; "
            f"missing lock {M8_LOCK_RELATIVE}"
        )
    lock = Path(m8_lock_path)
    blob = json.loads(lock.read_text(encoding="utf-8"))
    if blob.get("verdict") != "PASS" or not blob.get("fits_authorized"):
        raise MaskedAtacExecuteRefusal(
            "REFUSED_UNTIL_M8: lock present but fits_authorized is not true"
        )
    # Live hash match is mandatory (M8-C1); workspace defaults from lock path.
    if workspace is None:
        # .../tasks/nn/.../masked_atac_pilot_20261001/M8_REVIEWED_HASHES.json
        # parents[4] == workspace root under the standard layout.
        workspace = lock.resolve().parents[4]
    verify_reviewed_hashes(workspace=Path(workspace), lock_path=lock)


def refuse_mismatched_protocol_hash(expected: str, actual: str) -> None:
    if expected != actual:
        raise MaskedAtacExecuteRefusal(
            f"protocol hash mismatch: expected {expected} got {actual}"
        )


def load_attempt_counter(counter_path: Path) -> dict[str, Any]:
    path = Path(counter_path)
    if not path.is_file():
        return {
            "stage": PROTOCOL_ID,
            "scientific_fits": {"used": 0, "cap": HARD_ATTEMPT_CAP},
            "smoke_fits": {"used": 0, "cap": PLANNED_SMOKE_FITS},
            "total_attempts": {"used": 0, "hard_cap": HARD_ATTEMPT_CAP},
            "fitting_hours": {"used": 0.0, "cap": FITTING_HOURS_CAP},
            "artifacts_gib": {"used": 0.0, "cap": ARTIFACT_GIB_CAP},
            "network_bytes": 0,
            "workers": WORKERS,
            "torch_threads": TORCH_THREADS,
            "reserved_fit_ids": [],
            "completed_fit_ids": [],
            "failed_fit_ids": [],
        }
    counter = json.loads(path.read_text(encoding="utf-8"))
    counter.setdefault("reserved_fit_ids", [])
    counter.setdefault("completed_fit_ids", [])
    counter.setdefault("failed_fit_ids", [])
    return counter


def save_attempt_counter(counter_path: Path, counter: Mapping[str, Any]) -> Path:
    path = Path(counter_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(counter), indent=2, sort_keys=True) + "\n")
    return path


def reserve_attempt_before_dispatch(
    *,
    counter_path: Path,
    fit_id: str,
    stage: str,
) -> dict[str, Any]:
    """Crash-safe reserve: increment counters and record fit_id before learning."""
    counter = load_attempt_counter(counter_path)
    hard_cap = int(counter["total_attempts"]["hard_cap"])
    used = int(counter["total_attempts"]["used"])
    if used >= hard_cap:
        raise MaskedAtacExecuteRefusal(
            f"hard attempt cap {hard_cap} already reached ({used})"
        )
    reserved = list(counter.get("reserved_fit_ids", []))
    if fit_id not in reserved:
        reserved.append(fit_id)
    counter["reserved_fit_ids"] = reserved
    counter["total_attempts"]["used"] = used + 1
    if stage == "smoke":
        smoke_used = int(counter["smoke_fits"]["used"])
        smoke_cap = int(counter["smoke_fits"]["cap"])
        if smoke_used >= smoke_cap:
            raise MaskedAtacExecuteRefusal(
                f"smoke cap {smoke_cap} already reached ({smoke_used})"
            )
        counter["smoke_fits"]["used"] = smoke_used + 1
    else:
        sci_used = int(counter["scientific_fits"]["used"])
        sci_cap = int(counter["scientific_fits"]["cap"])
        if sci_used >= sci_cap:
            raise MaskedAtacExecuteRefusal(
                f"scientific cap {sci_cap} already reached ({sci_used})"
            )
        counter["scientific_fits"]["used"] = sci_used + 1
    hours_used = float(counter["fitting_hours"]["used"])
    if hours_used >= float(counter["fitting_hours"]["cap"]):
        raise MaskedAtacExecuteRefusal(
            f"fitting hours cap already reached ({hours_used})"
        )
    save_attempt_counter(counter_path, counter)
    return counter


def append_ledger_row(raw_root: Path, row: Mapping[str, Any]) -> None:
    path = Path(raw_root) / LEDGER_NAME
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def prepare_raw_root(raw_root: Path | str) -> Path:
    root = Path(raw_root)
    refuse_if_not_allowed_raw_root(root)
    if root.exists() and root.is_symlink():
        raise MaskedAtacExecuteRefusal(f"raw root must not be a symlink: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "checkpoints").mkdir(exist_ok=True)
    (root / "predictions").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    return root


def execute_jobs_serial(
    jobs: list[Mapping[str, Any]],
    *,
    raw_root: Path,
    counter_path: Path,
    fit_fn: Callable[[Mapping[str, Any]], dict[str, Any]],
    attempt_cap: int = HARD_ATTEMPT_CAP,
) -> dict[str, Any]:
    """Serial one-worker loop with per-job reserve before dispatch."""
    if WORKERS != 1:
        raise MaskedAtacExecuteRefusal("masked ATAC pilot requires WORKERS=1")
    counter = load_attempt_counter(counter_path)
    done_ids = set(counter.get("completed_fit_ids", []))
    remaining = [j for j in jobs if job_fit_id(j) not in done_ids]
    used = int(counter["total_attempts"]["used"])
    if used > attempt_cap:
        raise MaskedAtacExecuteRefusal(
            f"attempt counter {used} already exceeds cap {attempt_cap}"
        )
    if used + len(remaining) > attempt_cap:
        raise MaskedAtacExecuteRefusal(
            f"planned remaining {len(remaining)} would exceed cap "
            f"({used} + {len(remaining)} > {attempt_cap})"
        )
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    for job in remaining:
        fit_id = job_fit_id(job)
        counter = reserve_attempt_before_dispatch(
            counter_path=counter_path,
            fit_id=fit_id,
            stage=str(job["stage"]),
        )
        job_started = time.perf_counter()
        try:
            record = fit_fn(job)
            status = "ok"
            completed = list(counter.get("completed_fit_ids", []))
            if fit_id not in completed:
                completed.append(fit_id)
            counter["completed_fit_ids"] = completed
        except Exception as exc:  # noqa: BLE001 — ledger must retain failures
            record = {"fit_id": fit_id, "error": f"{type(exc).__name__}: {exc}"}
            status = "failed"
            failed = list(counter.get("failed_fit_ids", []))
            if fit_id not in failed:
                failed.append(fit_id)
            counter["failed_fit_ids"] = failed
        seconds = float(time.perf_counter() - job_started)
        counter["fitting_hours"]["used"] = float(
            counter["fitting_hours"]["used"]
        ) + seconds / 3600.0
        save_attempt_counter(counter_path, counter)
        payload = {
            "fit_id": fit_id,
            "stage": job["stage"],
            "arm": job["arm"],
            "fold": int(job["fold"]),
            "status": status,
            "seconds": seconds,
            "record": record,
        }
        append_ledger_row(raw_root, payload)
        pred_dir = Path(raw_root) / "predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        pred_path = pred_dir / f"{fit_id.replace('|', '__')}.json"
        if not pred_path.exists():
            pred_path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
        results.append(payload)
        if float(counter["fitting_hours"]["used"]) > float(
            counter["fitting_hours"]["cap"]
        ):
            raise MaskedAtacExecuteRefusal(
                f"fitting hours exceeded cap after {fit_id}"
            )
    return {
        "n_executed_this_call": len(results),
        "n_skipped_already_done": len(jobs) - len(remaining),
        "wall_seconds": float(time.perf_counter() - started),
        "counter": dict(load_attempt_counter(counter_path)),
        "records": results,
        "workers": 1,
        "parallel_dispatch": False,
    }


def run_authorized_pilot(
    *,
    workspace: Path,
    raw_root: Path | str | None = None,
    m8_lock_path: Path | None = None,
    review_path: Path | None = None,
    skip_fits: bool = False,
    fit_fn: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Authorize via external M8 lock; optionally run serial jobs or skip-fits replay."""
    workspace = Path(workspace)
    lock = Path(m8_lock_path) if m8_lock_path is not None else review_lock_path(workspace)
    review = (
        Path(review_path)
        if review_path is not None
        else workspace / M8_REVIEW_RELATIVE
    )
    live_hashes = verify_reviewed_hashes(workspace=workspace, lock_path=lock)
    if not review.is_file():
        raise MaskedAtacExecuteRefusal(f"missing M8 review record: {review}")
    review_blob = json.loads(review.read_text(encoding="utf-8"))
    if review_blob.get("verdict") != "PASS":
        raise MaskedAtacExecuteRefusal("M8 independent review must be PASS before fits")
    if not review_blob.get("fits_authorized", False):
        raise MaskedAtacExecuteRefusal("M8 review fits_authorized must be true")

    root = prepare_raw_root(raw_root or (workspace / ALLOWED_RAW_ROOT))
    counter_path = root / COUNTER_NAME
    jobs = enumerate_planned_jobs()
    if skip_fits:
        counter = load_attempt_counter(counter_path)
        return {
            "skip_fits": True,
            "n_executed_this_call": 0,
            "n_skipped_already_done": 0,
            "reviewed_hashes": live_hashes,
            "counter": counter,
            "planned_jobs": len(jobs),
            "workers": WORKERS,
            "torch_threads": TORCH_THREADS,
            "raw_root": str(root),
            "learning": False,
        }
    if fit_fn is None:
        raise MaskedAtacExecuteRefusal(
            "fit_fn required when skip_fits is False; refuse implicit learning"
        )
    exec_summary = execute_jobs_serial(
        jobs,
        raw_root=root,
        counter_path=counter_path,
        fit_fn=fit_fn,
    )
    return {
        "skip_fits": False,
        "reviewed_hashes": live_hashes,
        "raw_root": str(root),
        "learning": True,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        **exec_summary,
    }


def counter_still_zero(counter_path: Path) -> dict[str, Any]:
    counter = json.loads(Path(counter_path).read_text())
    used = int(counter["total_attempts"]["used"])
    smoke = int(counter["smoke_fits"]["used"])
    scientific = int(counter["scientific_fits"]["used"])
    ok = used == 0 and smoke == 0 and scientific == 0
    return {
        "ok": ok,
        "total_attempts_used": used,
        "smoke_fits_used": smoke,
        "scientific_fits_used": scientific,
        "hard_cap": int(counter["total_attempts"]["hard_cap"]),
        "path": str(counter_path),
    }


def run_m7_dry_run(
    *,
    workspace: Path,
    protocol_json: Path,
    m6_lock: Path,
    counter_path: Path,
    m8_lock: Path | None = None,
) -> dict[str, Any]:
    """Assemble IMPLEMENT report without smoke/main learning or counter mutation."""
    workspace = Path(workspace)
    protocol = json.loads(Path(protocol_json).read_text())
    if protocol.get("protocol_id") != PROTOCOL_ID:
        raise MaskedAtacExecuteRefusal(
            f"unexpected protocol_id {protocol.get('protocol_id')!r}"
        )
    if protocol.get("disposition") != "PROTOCOL_FROZEN":
        raise MaskedAtacExecuteRefusal("M7 requires PROTOCOL_FROZEN upstream")
    m6 = json.loads(Path(m6_lock).read_text())
    if m6.get("verdict") != "PASS" or not m6.get("m7_may_implement"):
        raise MaskedAtacExecuteRefusal("M6 PASS with m7_may_implement required")

    protocol_sha = sha256_file(protocol_json)
    m6_sha = sha256_file(m6_lock)
    arithmetic = attempt_arithmetic()
    jobs = enumerate_planned_jobs()
    if len(jobs) != PLANNED_TOTAL_INTENDED:
        raise RuntimeError(f"job count {len(jobs)} != {PLANNED_TOTAL_INTENDED}")

    counter = counter_still_zero(counter_path)
    if not counter["ok"]:
        raise MaskedAtacExecuteRefusal(f"attempt counters not zero: {counter}")

    # Classification API preserved: mil still refuses mixed; train_model donor-mode too.
    mil = assert_existing_mil_refuses_mixed_labels()
    disease_api_intact = bool(mil["mixed_refused"] and mil["uniform_accepted"])

    toy = build_toy_mixed_label_fold()
    views = toy["views"]
    labels = toy["labels"]
    donors = toy["donors"]
    train_idx = toy["train_idx"]
    val_idx = toy["val_idx"]
    test_idx = toy["test_idx"]

    # Existing donor-mode trainer must still refuse mixed labels (do not weaken API).
    train_model_refused = False
    try:
        widths = [views[VIEW_A].shape[1], views[VIEW_B].shape[1]]
        model = paired_model("token_concat", widths, NEURAL)
        train_model(
            model,
            {VIEW_A: views[VIEW_A][train_idx], VIEW_B: views[VIEW_B][train_idx]},
            labels[train_idx],
            {VIEW_A: views[VIEW_A][val_idx], VIEW_B: views[VIEW_B][val_idx]},
            labels[val_idx],
            max_epochs=1,
            patience=1,
            batch_size=4,
            seed=0,
            train_donor_ids=donors[train_idx],
            val_donor_ids=donors[val_idx],
        )
    except ValueError:
        train_model_refused = True

    selection_check = verify_selection_prefers_cell_log_loss_over_donor_mean_prob()

    # Tiny adapter fit on toy arrays only (unit verification; not smoke/counter).
    short_proto = MultiomeProtocol(
        n_tokens=NEURAL.n_tokens,
        embed_dim=NEURAL.embed_dim,
        hidden_dim=NEURAL.hidden_dim,
        n_heads=NEURAL.n_heads,
        dropout=NEURAL.dropout,
        feature_budget=NEURAL.feature_budget,
        cell_cap=NEURAL.cell_cap,
        max_epochs=3,
        patience=2,
        batch_size=4,
        learning_rate=NEURAL.learning_rate,
        n_repeats=1,
        n_folds=5,
        split_seed=NEURAL.split_seed,
        model_seed=NEURAL.model_seed,
        sampling_seed=NEURAL.sampling_seed,
    )
    neural_fit = fit_neural_cell_target(
        "token_concat",
        views,
        labels,
        donors,
        train_idx,
        val_idx,
        test_idx,
        protocol=short_proto,
    )
    adapter_ok = (
        neural_fit["result"]["selection_metric"] == SELECTION_METRIC_NAME
        and neural_fit["result"]["training"]["training_weighting"]
        == "inverse_donor_cell_count"
        and neural_fit["result"]["training"]["epochs_run"] >= 1
        and np.isfinite(neural_fit["probabilities"]).all()
    )

    const = fit_constant_prevalence(labels[train_idx], n_predict=len(test_idx))
    logreg = fit_logreg_cell_target(
        views[VIEW_A],
        labels,
        donors,
        train_idx,
        test_idx,
    )

    grad_checks = [
        check_finite_gradients_cell_target(arm, views, labels) for arm in NEURAL_ARMS
    ]
    reload_checks = [
        check_state_dict_reload_equality_cell_target(arm, views) for arm in NEURAL_ARMS
    ]
    param_match = ca_tc_param_match_for_widths(128, 430)

    # Refusals
    refusals: list[dict[str, Any]] = []
    try:
        refuse_mismatched_protocol_hash(protocol_sha, "0" * 64)
        refusals.append({"case": "protocol_hash", "refused": False})
    except MaskedAtacExecuteRefusal:
        refusals.append({"case": "protocol_hash", "refused": True})

    for bad in (
        "reports/generated/nn_s7_covariance_20260929/",
        "reports/generated/nn_s9_analytic_pairing_20260930/",
        "reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/",
    ):
        try:
            refuse_if_not_allowed_raw_root(bad)
            refusals.append({"case": f"raw_root:{bad}", "refused": False})
        except MaskedAtacExecuteRefusal:
            refusals.append({"case": f"raw_root:{bad}", "refused": True})
    try:
        refuse_if_not_allowed_raw_root(workspace / ALLOWED_RAW_ROOT)
        refusals.append({"case": "allowed_raw_root", "refused": False, "allowed": True})
    except MaskedAtacExecuteRefusal:
        refusals.append({"case": "allowed_raw_root", "refused": True, "allowed": False})

    overwrite_refused = False
    try:
        refuse_output_overwrite(protocol_json)
    except FileExistsError:
        overwrite_refused = True
    refusals.append({"case": "overwrite", "refused": overwrite_refused})

    learning_refused = False
    lock_path = m8_lock if m8_lock is not None else workspace / M8_LOCK_RELATIVE
    try:
        refuse_unreviewed_learning(m8_lock_path=lock_path, workspace=workspace)
    except MaskedAtacExecuteRefusal:
        learning_refused = True
    refusals.append(
        {
            "case": "unreviewed_smoke_main_learning",
            "refused": learning_refused,
            "lock_present": Path(lock_path).is_file(),
        }
    )

    # M8-C1: PASS + fits_authorized without live hash match must still refuse.
    empty_hash_lock_refused = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "M8_REVIEWED_HASHES.json"
            fake.write_text(
                json.dumps(
                    {
                        "verdict": "PASS",
                        "fits_authorized": True,
                        "reviewed_hashes": {},
                    }
                )
            )
            refuse_unreviewed_learning(m8_lock_path=fake, workspace=workspace)
    except MaskedAtacExecuteRefusal:
        empty_hash_lock_refused = True
    refusals.append(
        {
            "case": "empty_reviewed_hashes_pass_lock",
            "refused": empty_hash_lock_refused,
        }
    )

    checks = {
        "m6_pass_authorizes_implement": True,
        "attempt_arithmetic_within_caps": arithmetic.within_caps,
        "planned_jobs_30": len(jobs) == 30,
        "planned_main_25": PLANNED_MAIN_FITS == 25,
        "planned_smoke_5": PLANNED_SMOKE_FITS == 5,
        "counters_still_zero": counter["ok"],
        "mil_mixed_refused": disease_api_intact,
        "train_model_donor_mode_refuses_mixed": train_model_refused,
        "adapter_mixed_label_train_ok": bool(adapter_ok),
        "selection_prefers_cell_log_loss": bool(
            selection_check["cell_log_loss_prefers_good"]
        ),
        "constant_arm_zero_params": const["n_parameters"] == 0,
        "logreg_probabilities_finite": bool(np.isfinite(logreg["probabilities"]).all()),
        "finite_gradients_all_neural": all(c["finite"] for c in grad_checks),
        "reload_identity_all_neural": all(c["passed"] for c in reload_checks),
        "ca_tc_param_match_toy_widths": bool(param_match["matched"]),
        "protocol_hash_mismatch_refused": all(
            r["refused"] for r in refusals if r["case"] == "protocol_hash"
        ),
        "forbidden_raw_roots_refused": all(
            r["refused"] for r in refusals if r["case"].startswith("raw_root:")
        ),
        "allowed_raw_root_accepted": any(
            r.get("allowed") for r in refusals if r["case"] == "allowed_raw_root"
        ),
        "overwrite_refused": overwrite_refused,
        "learning_refused_until_m8": learning_refused,
        "empty_hash_pass_lock_refused": empty_hash_lock_refused,
        "no_smoke_main_fits": True,
        "claim_level_2": CLAIM_LEVEL == 2,
        "executor_has_verify_reviewed_hashes": True,
        "executor_has_reserve_before_dispatch": True,
        "executor_has_skip_fits": True,
    }
    all_pass = all(bool(v) for v in checks.values())
    body: dict[str, Any] = {
        "disposition": DISPOSITION if all_pass else "IMPLEMENT_FAIL",
        "task": "M7",
        "protocol_id": PROTOCOL_ID,
        "claim_level": CLAIM_LEVEL,
        "no_fits": True,
        "trainability_with_learning": "REFUSED_UNTIL_M8",
        "preserved_labels": dict(PRESERVED_LABELS),
        "reuse": {
            "paired_model": True,
            "model_inputs": True,
            "predict": True,
            "donor_cell_weights": True,
            "visible_atac_tfidf_fit": "available_via_masked_atac_metrics",
            "classification_apis_unmodified": True,
        },
        "adapter": {
            "module": "p22.eval.masked_atac_adapter",
            "selection_metric": SELECTION_METRIC_NAME,
            "requirements": ADAPTER_REQUIREMENTS,
            "arms": {
                "constant": CONSTANT_ARM,
                "logreg": list(LOGREG_ARMS),
                "neural": list(NEURAL_ARMS),
                "paired_name_map": dict(ARM_TO_PAIRED_NAME),
                "all_protocol_arms": list(ARMS),
            },
            "toy_mixed_label_fit": {
                "arm": neural_fit["arm"],
                "epochs_run": neural_fit["result"]["training"]["epochs_run"],
                "best_epoch": neural_fit["result"]["training"]["best_epoch"],
                "initial_state_sha256": neural_fit["result"]["initial_state_sha256"],
                "checkpoint_sha256": neural_fit["result"]["checkpoint_sha256"],
                "val_donor_average_cell_log_loss": neural_fit["result"][
                    "val_donor_average_cell_log_loss"
                ],
                "note": (
                    "Toy-array unit verification only; does not reserve attempt "
                    "counters and is not a smoke/main research fit"
                ),
            },
        },
        "attempt_arithmetic": arithmetic.to_dict(),
        "planned_jobs": jobs,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "fitting_hours_cap": FITTING_HOURS_CAP,
        "artifact_gib_cap": ARTIFACT_GIB_CAP,
        "allowed_raw_root": ALLOWED_RAW_ROOT,
        "counter_snapshot": counter,
        "param_match_toy": param_match,
        "gradient_checks": grad_checks,
        "reload_checks": reload_checks,
        "selection_check": selection_check,
        "refusals": refusals,
        "hashes": {
            "PILOT_PROTOCOL.json": protocol_sha,
            "M6_REVIEWED_HASHES.json": m6_sha,
        },
        "m6_lock": {
            "verdict": m6.get("verdict"),
            "m7_may_implement": m6.get("m7_may_implement"),
            "m8_still_required": m6.get("m8_still_required"),
            "fits_authorized": m6.get("fits_authorized"),
            "reviewer_agent_id": m6.get("reviewer_agent_id"),
        },
        "checks": checks,
        "next": "M8 independent full executor/dependency hash review before any learning",
    }
    return body


def render_implement_md(report: Mapping[str, Any]) -> str:
    lines = [
        "# M7 — Minimal measured-target adapter (masked ATAC pilot)",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Protocol ID:** `{report['protocol_id']}`",
        f"**Claim level:** {report['claim_level']} (computational prediction)",
        "**Date:** 2026-10-01",
        (
            f"**Research fits:** 0 "
            f"(trainability-with-learning `{report['trainability_with_learning']}`)."
        ),
        "",
        "Machine-readable: [implement.json](implement.json); frozen "
        "[PILOT_PROTOCOL.json](PILOT_PROTOCOL.json); "
        "[M6_REVIEWED_HASHES.json](M6_REVIEWED_HASHES.json).",
        "",
        "## Reuse",
        "",
        "- Existing `paired_model` / `model_inputs` / `predict` (multiome_runner).",
        "- Existing `donor_cell_weights` (s7_runner) for equal-donor cell weighting.",
        "- Existing `visible_atac_tfidf_fit` (masked_atac_metrics) for visible-only ATAC.",
        "- New: `p22.eval.masked_atac_adapter` (mixed-label cell-loss train/select) + "
        "`p22.eval.masked_atac_execute` (dry-run / M8 gate / refusals).",
        "- Disease classification APIs (`mil_loop`, `train_model` donor-mode) unchanged "
        "and still refuse mixed cell labels.",
        "",
        "## Adapter contract",
        "",
        f"- Selection metric: `{report['adapter']['selection_metric']}` "
        "(minimize; mixed labels allowed).",
        f"- Requirements: {report['adapter']['requirements']['required_adapter']}",
        "- Forbidden: donor-average probability / fake disease class as primary.",
        "",
        "## Verification summary",
        "",
    ]
    for key, val in report["checks"].items():
        lines.append(f"- `{key}`: **{val}**")
    toy = report["adapter"]["toy_mixed_label_fit"]
    arith = report["attempt_arithmetic"]
    lines.extend(
        [
            "",
            "## Toy adapter fit (unit verification only)",
            "",
            f"- Arm: `{toy['arm']}`; epochs_run={toy['epochs_run']}; "
            f"best_epoch={toy['best_epoch']}",
            f"- initial_state_sha256: `{toy['initial_state_sha256']}`",
            f"- checkpoint_sha256: `{toy['checkpoint_sha256']}`",
            f"- Note: {toy['note']}",
            "",
            "## Attempt arithmetic (unchanged)",
            "",
            f"- {arith['arithmetic']}",
            f"- Within caps: **{arith['within_caps']}**",
            f"- Workers × threads: **{report['workers']} × {report['torch_threads']}**",
            "",
            "## Hashes",
            "",
        ]
    )
    for key, val in report["hashes"].items():
        lines.append(f"- `{key}`: `{val}`")
    lines.extend(
        [
            "",
            "## Scientific invariants (unchanged)",
            "",
        ]
    )
    for key, val in report["preserved_labels"].items():
        lines.append(f"- {key}: `{val}`")
    lines.extend(
        [
            "",
            "## Next",
            "",
            report["next"] + ".",
            "",
        ]
    )
    return "\n".join(lines)


def write_implement_artifacts(
    out_dir: Path,
    report: Mapping[str, Any],
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": out_dir / "implement.json",
        "md": out_dir / "IMPLEMENT.md",
    }
    for path in paths.values():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing path: {path}")
    paths["json"].write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    paths["md"].write_text(render_implement_md(report))
    return paths
