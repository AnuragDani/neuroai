"""S10 corrected-null serial executor (fits gated on R8 external hash lock).

Reuses S7 fit/pairing helpers and the S10 corrected generator. Scientific
dispatch is refused until ``R8_REVIEWED_HASHES.json`` is written by independent
R8 review PASS. Default workers=1 (serial); no ThreadPoolExecutor path.
Per-job attempt reservation happens before each fit (R3 finding repair).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from p22.data.group_splits import aggregate_donor_probabilities
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_confirm_exec import save_donor_predictions
from p22.eval.s7_ledger import make_fit_id, sha256_file
from p22.eval.s7_pairing import (
    S7_BOOTSTRAP_DRAWS,
    S7_BOOTSTRAP_SEED,
    S7_IDENTITY_ATOL,
    S7_MIN_VALID_DRAWS,
    evaluate_pairing_pc,
    identity_check,
)
from p22.eval.s7_runner import (
    S7_LOGREG_FROZEN,
    check_disk_resources,
    fit_s7_arm,
    ledger_payload,
    reload_checkpoint_predictions,
)
from p22.eval.s9_execute import (
    _pool_donor_ba_from_predictions,
    interpret_batch,
)
from p22.eval.s10_analytic import (
    ALLOWED_RAW_ROOT,
    DECISION_GENERATOR_SEED,
    DECISION_MODEL_SEED,
    N_FOLDS,
    PAIRING_SHUFFLE_SEEDS,
    PROTOCOL_ID,
    SCIENTIFIC_ATTEMPT_CAP,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TORCH_THREADS,
    TOTAL_FITS,
    WORKERS,
    allocate_s10_folds,
    assert_donor_isolation,
    assign_donor_labels,
    enumerate_s10_jobs,
    fold_row_indices,
    generate_corrected_arrays,
    permute_atac_within_donor,
    refuse_if_not_allowed_raw_root,
    refuse_mismatched_protocol_hash,
    refuse_unreviewed_scientific_fits,
    s10_protocol_from_frozen,
    verify_oracle_invariants,
)
from p22.models.fusion import VIEW_A, VIEW_B

# External lock written only after independent R8 PASS. Embedding digests in
# this module would make the executor's own hash self-referential (S9 gap).
DEFAULT_REVIEW_LOCK = Path(
    "tasks/nn/professor_direction_investigation_20260929/"
    "failure_audit_20261001/R8_REVIEWED_HASHES.json"
)

REQUIRED_LOCK_KEYS = (
    "S10_PROTOCOL.json",
    "S10_SPLIT_MANIFEST.json",
    "S10_SEED_SCHEDULE.json",
    "src/p22/eval/s10_analytic.py",
    "src/p22/eval/s10_execute.py",
)

LEDGER_NAME = "attempt_ledger.jsonl"
PROVENANCE_NAME = "provenance.json"
COUNTER_NAME = "attempt_counter.json"
CHECKPOINT_MODELS = frozenset({"cross_attention", "token_concat"})
MARGINAL_BA_MAX = 0.60


class S10ExecuteRefusal(ValueError):
    """Refuse unauthorized or unsafe S10 execution."""


def review_lock_path(workspace: Path | None = None) -> Path:
    if workspace is None:
        return DEFAULT_REVIEW_LOCK
    return Path(workspace) / DEFAULT_REVIEW_LOCK


def load_reviewed_hashes(lock_path: Path | None = None) -> dict[str, str]:
    path = Path(lock_path) if lock_path is not None else DEFAULT_REVIEW_LOCK
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
    protocol_path: Path,
    split_path: Path,
    seed_path: Path | None = None,
    lock_path: Path | None = None,
) -> dict[str, str]:
    """Require exact R8-reviewed hashes before any research fit."""
    lock = Path(lock_path) if lock_path is not None else review_lock_path(workspace)
    if not reviewed_hashes_complete(lock):
        raise S10ExecuteRefusal(
            "R8_REVIEWED_HASHES incomplete; independent review PASS required "
            "before scientific fits"
        )
    expected = load_reviewed_hashes(lock)
    seed = (
        Path(seed_path)
        if seed_path is not None
        else Path(workspace)
        / "tasks/nn/professor_direction_investigation_20260929"
        / "failure_audit_20261001"
        / "S10_SEED_SCHEDULE.json"
    )
    paths = {
        "S10_PROTOCOL.json": Path(protocol_path),
        "S10_SPLIT_MANIFEST.json": Path(split_path),
        "S10_SEED_SCHEDULE.json": seed,
        "src/p22/eval/s10_analytic.py": Path(workspace) / "src/p22/eval/s10_analytic.py",
        "src/p22/eval/s10_execute.py": Path(workspace) / "src/p22/eval/s10_execute.py",
    }
    live: dict[str, str] = {}
    for key, path in paths.items():
        if not path.is_file():
            raise S10ExecuteRefusal(f"missing reviewed artifact {key}: {path}")
        digest = sha256_file(path)
        live[key] = digest
        refuse_mismatched_protocol_hash(expected[key], digest, label=key)
    return live


def prepare_raw_root(raw_root: Path | str) -> Path:
    """Create authorized S10 raw root; refuse S7/S8/S9 and symlink write-through."""
    root = Path(raw_root)
    refuse_if_not_allowed_raw_root(root)
    if root.exists():
        if root.is_symlink():
            raise S10ExecuteRefusal(f"raw root must not be a symlink: {root}")
    else:
        root.mkdir(parents=True, exist_ok=False)
    (root / "checkpoints").mkdir(exist_ok=True)
    (root / "donor_predictions").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    return root


def load_attempt_counter(raw_root: Path) -> dict[str, Any]:
    path = raw_root / COUNTER_NAME
    if not path.is_file():
        return {
            "attempted_fits": 0,
            "completed_ok": 0,
            "failed": 0,
            "fit_ids": [],
            "reserved_fit_ids": [],
            "fitting_seconds": 0.0,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_attempt_counter(raw_root: Path, counter: Mapping[str, Any]) -> Path:
    path = raw_root / COUNTER_NAME
    path.write_text(json.dumps(dict(counter), indent=2, sort_keys=True) + "\n")
    return path


def append_ledger_row(raw_root: Path, row: Mapping[str, Any]) -> None:
    path = raw_root / LEDGER_NAME
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def read_ledger_records(raw_root: Path) -> list[dict[str, Any]]:
    path = raw_root / LEDGER_NAME
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def execution_defaults() -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "parallel_dispatch": False,
        "thread_pool_executor": False,
        "planned_fits": TOTAL_FITS,
        "scientific_cap": SCIENTIFIC_ATTEMPT_CAP,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "allowed_raw_root": ALLOWED_RAW_ROOT,
        "decision_generator_seed": DECISION_GENERATOR_SEED,
        "decision_model_seed": DECISION_MODEL_SEED,
        "reserve_attempts_before_dispatch": True,
        "reviewed_hashes_complete": reviewed_hashes_complete(),
        "review_lock": str(DEFAULT_REVIEW_LOCK),
        "marginal_ba_max": MARGINAL_BA_MAX,
        "checkpoint_models": sorted(CHECKPOINT_MODELS),
        "note": (
            "Serial neural worker default. Scientific fits require external "
            "R8_REVIEWED_HASHES.json written by independent review PASS."
        ),
    }


def should_retain_s10_checkpoint(job: Mapping[str, Any]) -> bool:
    return str(job["model"]) in CHECKPOINT_MODELS and str(job["stage"]) == "screen"


def save_s10_checkpoint(record: Mapping[str, Any], checkpoint_dir: Path) -> Path | None:
    if not should_retain_s10_checkpoint(record):
        return None
    payload = record.get("checkpoint")
    if payload is None:
        raise S10ExecuteRefusal(f"missing checkpoint for retainable {record['fit_id']}")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    fit_id = str(record["fit_id"]).replace("|", "__")
    path = checkpoint_dir / f"{fit_id}.pt"
    torch.save(
        {
            "fit_id": record["fit_id"],
            "stage": record["stage"],
            "rho": record["rho"],
            "generator_seed": record["generator_seed"],
            "fold": record["fold"],
            "model": record["model"],
            "model_seed": record.get("model_seed"),
            "initial_state_sha256": record.get("initial_state_sha256"),
            "epochs_run": record.get("epochs_run"),
            "learning_history": record.get("learning_history"),
            "checkpoint": payload,
        },
        path,
    )
    return path


def _arrays_for_rho(
    labels: dict[str, int],
    rho: float,
    *,
    cache: dict[float, tuple[np.ndarray, ...]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    key = float(rho)
    if key not in cache:
        rna, atac, donor, lab, cells = generate_corrected_arrays(
            labels, rho=key, generator_seed=DECISION_GENERATOR_SEED
        )
        cache[key] = (
            rna.astype(np.float32),
            atac.astype(np.float32),
            donor,
            lab.astype(np.int64),
            cells,
        )
    return cache[key]


def run_one_s10_fit(
    job: Mapping[str, Any],
    *,
    labels: dict[str, int],
    splits: Mapping[str, Any],
    protocol: MultiomeProtocol,
    array_cache: dict[float, tuple[np.ndarray, ...]],
) -> dict[str, Any]:
    """Fit one predeclared S10 job; return ledger-ready record with history."""
    rho = float(job["rho"])
    fold_idx = int(job["fold"])
    model = str(job["model"])
    stage = str(job["stage"])
    fit_id = str(job["fit_id"])
    rna, atac, donor, lab, _cells = _arrays_for_rho(labels, rho, cache=array_cache)
    fold = splits["folds"][str(fold_idx)]
    positions = fold_row_indices(donor, fold)
    assert_donor_isolation(positions, donor)
    views = {VIEW_A: rna, VIEW_B: atac}
    t0 = time.perf_counter()
    try:
        scores = fit_s7_arm(
            model,
            views,
            lab,
            donor,
            positions,
            protocol,
            model_seed=DECISION_MODEL_SEED,
        )
        status = str(scores["status"])
        checkpoint = scores.get("checkpoint")
        initial_state = None
        history = None
        epochs_run = None
        if isinstance(checkpoint, dict) and checkpoint.get("kind") == "neural":
            history = checkpoint.get("history")
            epochs_run = checkpoint.get("epochs_run")
            initial_state = checkpoint.get("initial_state_sha256")
        record: dict[str, Any] = {
            "fit_id": fit_id,
            "stage": stage,
            "rho": rho,
            "generator_seed": DECISION_GENERATOR_SEED,
            "fold": fold_idx,
            "model": model,
            "status": status,
            "donor_balanced_accuracy": scores.get("donor_balanced_accuracy"),
            "donor_auroc": scores.get("donor_auroc"),
            "donor_log_loss": scores.get("donor_log_loss"),
            "n_test_donors": scores.get("n_test_donors"),
            "model_seed": scores.get("model_seed"),
            "checkpoint": checkpoint,
            "test_cell_probabilities": scores.get("test_cell_probabilities"),
            "donor_probabilities": scores.get("donor_probabilities"),
            "initial_state_sha256": initial_state,
            "learning_history": history,
            "epochs_run": epochs_run,
            "seconds": float(time.perf_counter() - t0),
            "logreg_frozen": dict(S7_LOGREG_FROZEN) if model.startswith("logreg") else None,
        }
    except Exception as error:  # noqa: BLE001 — record failed attempt
        record = {
            "fit_id": fit_id,
            "stage": stage,
            "rho": rho,
            "generator_seed": DECISION_GENERATOR_SEED,
            "fold": fold_idx,
            "model": model,
            "status": f"error: {type(error).__name__}: {error}",
            "seconds": float(time.perf_counter() - t0),
        }
    return record


def execute_jobs_serial(
    jobs: list[dict[str, Any]],
    *,
    raw_root: Path,
    labels: dict[str, int],
    splits: Mapping[str, Any],
    protocol: MultiomeProtocol,
    torch_threads: int = TORCH_THREADS,
    attempt_cap: int = SCIENTIFIC_ATTEMPT_CAP,
    fitting_hours_cap: float = SYNTHETIC_FITTING_HOURS_CAP,
) -> dict[str, Any]:
    """Serial execution with per-job reserve before dispatch (R3 repair)."""
    if WORKERS != 1:
        raise S10ExecuteRefusal("S10 requires WORKERS=1 serial execution")
    counter = load_attempt_counter(raw_root)
    done_ids = set(counter.get("fit_ids", []))
    remaining = [j for j in jobs if j["fit_id"] not in done_ids]
    if int(counter.get("attempted_fits", 0)) > attempt_cap:
        raise S10ExecuteRefusal(
            f"attempt counter {counter['attempted_fits']} already exceeds cap {attempt_cap}"
        )
    if int(counter.get("attempted_fits", 0)) + len(remaining) > attempt_cap:
        raise S10ExecuteRefusal(
            f"planned remaining {len(remaining)} would exceed cap "
            f"({counter['attempted_fits']} + {len(remaining)} > {attempt_cap})"
        )

    torch.set_num_threads(int(torch_threads))
    os.environ["OMP_NUM_THREADS"] = str(int(torch_threads))
    array_cache: dict[float, tuple[np.ndarray, ...]] = {}
    for rho in sorted({float(j["rho"]) for j in remaining}):
        _arrays_for_rho(labels, rho, cache=array_cache)
    ckpt_dir = raw_root / "checkpoints"
    pred_dir = raw_root / "donor_predictions"
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    for job in remaining:
        # Reserve before dispatch so crash mid-fit still consumes budget.
        reserved = list(counter.get("reserved_fit_ids", []))
        if job["fit_id"] not in reserved:
            reserved.append(job["fit_id"])
        counter["reserved_fit_ids"] = reserved
        counter["attempted_fits"] = int(counter.get("attempted_fits", 0)) + 1
        save_attempt_counter(raw_root, counter)

        hours_used = float(counter.get("fitting_seconds", 0.0)) / 3600.0
        if hours_used >= float(fitting_hours_cap):
            raise S10ExecuteRefusal(
                f"fitting hours cap {fitting_hours_cap} already reached "
                f"({hours_used:.6f} h); refusing further dispatch"
            )

        record = run_one_s10_fit(
            job,
            labels=labels,
            splits=splits,
            protocol=protocol,
            array_cache=array_cache,
        )
        ckpt_path = save_s10_checkpoint(record, ckpt_dir)
        pred_path = save_donor_predictions(record, pred_dir)
        payload = ledger_payload(record)
        payload["seconds"] = record.get("seconds")
        payload["initial_state_sha256"] = record.get("initial_state_sha256")
        payload["epochs_run"] = record.get("epochs_run")
        if ckpt_path is not None:
            payload["checkpoint_path"] = str(ckpt_path)
            payload["checkpoint_sha256"] = sha256_file(ckpt_path)
        if pred_path is not None:
            payload["donor_predictions_path"] = str(pred_path)
            payload["donor_predictions_sha256"] = sha256_file(pred_path)
        append_ledger_row(raw_root, payload)
        counter["fitting_seconds"] = float(counter.get("fitting_seconds", 0.0)) + float(
            record.get("seconds") or 0.0
        )
        counter.setdefault("fit_ids", []).append(record["fit_id"])
        if str(record.get("status")) == "ok":
            counter["completed_ok"] = int(counter.get("completed_ok", 0)) + 1
        else:
            counter["failed"] = int(counter.get("failed", 0)) + 1
        save_attempt_counter(raw_root, counter)
        results.append(payload)

        hours_used = float(counter.get("fitting_seconds", 0.0)) / 3600.0
        if hours_used > float(fitting_hours_cap):
            raise S10ExecuteRefusal(
                f"fitting hours exceeded cap after fit {record['fit_id']}: "
                f"{hours_used:.6f} > {fitting_hours_cap}"
            )

    wall = float(time.perf_counter() - started)
    return {
        "n_executed_this_call": len(results),
        "n_skipped_already_done": len(jobs) - len(remaining),
        "wall_seconds": wall,
        "counter": dict(counter),
        "records": results,
        "workers": 1,
        "parallel_dispatch": False,
    }


def score_pairing_for_rho(
    *,
    records: list[Mapping[str, Any]],
    labels: dict[str, int],
    splits: Mapping[str, Any],
    protocol: MultiomeProtocol,
    rho: float,
    model: str = "cross_attention",
) -> dict[str, Any]:
    """Reload screen checkpoints; within-donor ATAC shuffle; pooled pairing gate."""
    selected = [
        r
        for r in records
        if r.get("stage") == "screen"
        and abs(float(r.get("rho", -1)) - float(rho)) < 1e-12
        and r.get("model") == model
        and r.get("status") == "ok"
        and r.get("checkpoint_path")
    ]
    if len(selected) != N_FOLDS:
        return {
            "complete": False,
            "reason": (
                f"expected {N_FOLDS} {model} rho={rho} screen checkpoints; "
                f"got {len(selected)}"
            ),
            "missing": [
                make_fit_id("screen", rho, DECISION_GENERATOR_SEED, f, model)
                for f in range(N_FOLDS)
            ],
        }

    rna, atac, donor, lab, _cells = generate_corrected_arrays(
        labels, rho=float(rho), generator_seed=DECISION_GENERATOR_SEED
    )
    views_base = {
        VIEW_A: rna.astype(np.float32),
        VIEW_B: atac.astype(np.float32),
    }

    all_donor_ids: list[str] = []
    all_y: list[float] = []
    all_p0: list[float] = []
    all_reload: list[float] = []
    shuffled_pool: dict[int, list[float]] = {int(s): [] for s in PAIRING_SHUFFLE_SEEDS}

    for row in sorted(selected, key=lambda r: int(r["fold"])):
        fold_idx = int(row["fold"])
        fold = splits["folds"][str(fold_idx)]
        positions = fold_row_indices(donor, fold)
        test = np.asarray(positions["test"], dtype=np.int64)
        ckpt = row["checkpoint_path"]
        p_orig = reload_checkpoint_predictions(ckpt, views_base, test, protocol)
        p_reload = reload_checkpoint_predictions(ckpt, views_base, test, protocol)
        id_check = identity_check(p_orig, p_reload, atol=S7_IDENTITY_ATOL)
        if not id_check["passed"]:
            return {
                "complete": False,
                "reason": f"identity fail fold {fold_idx}",
                "identity": id_check,
            }
        frame0 = aggregate_donor_probabilities(p_orig, donor[test])
        truth = pd.Series(lab[test], index=donor[test]).groupby(level=0).first()
        frame0["label"] = frame0.donor_id.map(truth).astype(float)
        order = [str(d) for d in frame0["donor_id"].tolist()]
        by_p = {
            str(d): float(p)
            for d, p in zip(frame0["donor_id"], frame0["probability"], strict=True)
        }
        by_y = {str(d): float(y) for d, y in zip(frame0["donor_id"], frame0["label"], strict=True)}
        all_donor_ids.extend(order)
        all_y.extend([by_y[d] for d in order])
        all_p0.extend([by_p[d] for d in order])
        frame_r = aggregate_donor_probabilities(p_reload, donor[test])
        by_r = {
            str(d): float(p)
            for d, p in zip(frame_r["donor_id"], frame_r["probability"], strict=True)
        }
        all_reload.extend([by_r[d] for d in order])

        for seed in PAIRING_SHUFFLE_SEEDS:
            atac_s = permute_atac_within_donor(atac, donor, seed=int(seed))
            test_donors = donor[test]
            for name in sorted(set(test_donors.tolist()), key=str):
                idx_all = np.flatnonzero(donor == name)
                orig_sorted = np.sort(atac[idx_all], axis=0)
                shuf_sorted = np.sort(atac_s[idx_all], axis=0)
                if not np.allclose(orig_sorted, shuf_sorted):
                    raise S10ExecuteRefusal(
                        f"shuffle marginal fail donor={name} seed={seed}"
                    )
            views_s = {
                VIEW_A: rna.astype(np.float32),
                VIEW_B: atac_s.astype(np.float32),
            }
            p_s = reload_checkpoint_predictions(ckpt, views_s, test, protocol)
            frame_s = aggregate_donor_probabilities(p_s, donor[test])
            by_s = {
                str(d): float(p)
                for d, p in zip(frame_s["donor_id"], frame_s["probability"], strict=True)
            }
            shuffled_pool[int(seed)].extend([by_s[d] for d in order])

    if len(set(all_donor_ids)) != len(all_donor_ids):
        return {"complete": False, "reason": "duplicate donors in pooled pairing"}

    gate = evaluate_pairing_pc(
        donor_ids=all_donor_ids,
        y_true=all_y,
        p_original=all_p0,
        p_shuffled_by_seed=shuffled_pool,
        p_reload=all_reload,
        required_seeds=PAIRING_SHUFFLE_SEEDS,
        n_draws=S7_BOOTSTRAP_DRAWS,
        bootstrap_seed=S7_BOOTSTRAP_SEED,
        min_valid=S7_MIN_VALID_DRAWS,
        atol=S7_IDENTITY_ATOL,
    )
    pc = gate["pc_label"]
    if pc == "PC_PASS":
        pairing_label = "PAIRING_POSITIVE"
    elif pc == "PC_FAIL":
        pairing_label = "PAIRING_NEGATIVE"
    elif pc == "PC_IDENTITY_FAIL":
        pairing_label = "INVALID"
    else:
        pairing_label = "INCOMPLETE"
    return {
        "complete": pairing_label not in {"INCOMPLETE", "INVALID"} or pc == "PC_FAIL",
        "rho": float(rho),
        "model": model,
        "n_donors": len(all_donor_ids),
        "n_shuffle_seeds": len(PAIRING_SHUFFLE_SEEDS),
        "pairing_label": pairing_label,
        "pc_label_raw": pc,
        "gate": gate,
    }


def preflight_no_fit(
    *,
    workspace: Path,
    protocol_path: Path,
    split_path: Path,
    raw_root: Path | str,
) -> dict[str, Any]:
    """Hash/oracle/job/raw-root checks without scientific fits."""
    refuse_if_not_allowed_raw_root(raw_root)
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise S10ExecuteRefusal(f"oracle gate FAIL: {oracle}")
    splits = allocate_s10_folds(labels)
    frozen_split = json.loads(Path(split_path).read_text(encoding="utf-8"))
    if frozen_split["donor_labels"] != splits["donor_labels"]:
        raise S10ExecuteRefusal("split manifest diverges from live allocator")
    jobs = enumerate_s10_jobs()
    if len(jobs) != TOTAL_FITS:
        raise S10ExecuteRefusal(f"job count {len(jobs)} != {TOTAL_FITS}")
    _rna, _atac, _donor, _lab, _cells = generate_corrected_arrays(
        labels, rho=0.0, generator_seed=DECISION_GENERATOR_SEED
    )
    del _rna, _atac, _donor, _lab, _cells
    proto = s10_protocol_from_frozen()
    return {
        "protocol_id": PROTOCOL_ID,
        "oracle_gate": oracle["oracle_gate"],
        "n_jobs": len(jobs),
        "raw_root": str(raw_root),
        "protocol_sha256": sha256_file(protocol_path),
        "split_sha256": sha256_file(split_path),
        "analytic_sha256": sha256_file(
            Path(workspace) / "src/p22/eval/s10_analytic.py"
        ),
        "execute_sha256": sha256_file(
            Path(workspace) / "src/p22/eval/s10_execute.py"
        ),
        "execution_defaults": execution_defaults(),
        "protocol_fingerprint": proto.fingerprint,
        "scientific_fits_authorized": reviewed_hashes_complete(
            review_lock_path(workspace)
        ),
    }


def run_scientific_batch(
    *,
    workspace: Path | None = None,
    protocol_path: Path | None = None,
    split_path: Path | None = None,
    review_path: Path | None = None,
    raw_root: Path | str | None = None,
    skip_fits: bool = False,
    **_kwargs: Any,
) -> Mapping[str, Any]:
    """Authorize via external R8 lock, then optionally execute serial S10 batch."""
    if workspace is None:
        # Preserve R7 refusal behaviour when called with no authorization args.
        refuse_unreviewed_scientific_fits()
        raise AssertionError("unreachable")  # pragma: no cover

    workspace = Path(workspace)
    stage_dir = (
        workspace
        / "tasks/nn/professor_direction_investigation_20260929"
        / "failure_audit_20261001"
    )
    protocol_path = Path(protocol_path or stage_dir / "S10_PROTOCOL.json")
    split_path = Path(split_path or stage_dir / "S10_SPLIT_MANIFEST.json")
    seed_path = stage_dir / "S10_SEED_SCHEDULE.json"
    lock_path = review_lock_path(workspace)
    review_path = Path(review_path or stage_dir / "NO_FIT_REVIEW_R8.json")

    live_hashes = verify_reviewed_hashes(
        workspace=workspace,
        protocol_path=protocol_path,
        split_path=split_path,
        seed_path=seed_path,
        lock_path=lock_path,
    )
    if not review_path.is_file():
        raise S10ExecuteRefusal(f"missing R8 review record: {review_path}")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review.get("verdict") != "PASS" or review.get("disposition") != "PASS":
        raise S10ExecuteRefusal("R8 independent review must be PASS before fits")
    if not review.get("checkpoint_c", {}).get("authorized_by_review", False):
        raise S10ExecuteRefusal("Checkpoint C authorization missing in R8 review")

    root = prepare_raw_root(raw_root or (workspace / ALLOWED_RAW_ROOT))
    try:
        disk = check_disk_resources(
            output_root=root,
            min_free_gib=1.0,
            max_artifacts_gib=SYNTHETIC_ARTIFACT_GIB_CAP,
        )
    except RuntimeError as err:
        raise S10ExecuteRefusal(str(err)) from err

    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    splits = allocate_s10_folds(labels)
    split_manifest = json.loads(split_path.read_text(encoding="utf-8"))
    if splits["donor_labels"] != split_manifest["donor_labels"]:
        raise S10ExecuteRefusal("live split labels diverge from S10_SPLIT_MANIFEST")
    for fk, fold in split_manifest["folds"].items():
        if splits["folds"][fk] != fold:
            raise S10ExecuteRefusal(f"live split fold {fk} diverges from manifest")

    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise S10ExecuteRefusal(f"oracle gate FAIL before fits: {oracle}")

    proto = s10_protocol_from_frozen()
    jobs = enumerate_s10_jobs()
    if len(jobs) != TOTAL_FITS:
        raise S10ExecuteRefusal(f"job count {len(jobs)} != {TOTAL_FITS}")

    provenance = {
        "protocol_id": PROTOCOL_ID,
        "task": "R9",
        "reviewed_hashes": live_hashes,
        "review_verdict": review.get("verdict"),
        "reviewer_agent_id": review.get("reviewer", {}).get("agent_id"),
        "raw_root": str(root),
        "attempt_cap": SCIENTIFIC_ATTEMPT_CAP,
        "planned_fits": TOTAL_FITS,
        "workers": 1,
        "torch_threads": TORCH_THREADS,
        "parallel_dispatch": False,
        "disk": disk,
    }
    (root / PROVENANCE_NAME).write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )

    if skip_fits:
        exec_summary: dict[str, Any] = {
            "n_executed_this_call": 0,
            "n_skipped_already_done": 0,
            "wall_seconds": 0.0,
            "counter": load_attempt_counter(root),
            "records": [],
            "skipped": True,
        }
    else:
        exec_summary = execute_jobs_serial(
            jobs,
            raw_root=root,
            labels=labels,
            splits=splits,
            protocol=proto,
        )

    records = read_ledger_records(root)
    counter = load_attempt_counter(root)
    coverage = {
        "planned": TOTAL_FITS,
        "attempted": int(counter.get("attempted_fits", 0)),
        "completed_ok": int(counter.get("completed_ok", 0)),
        "failed": int(counter.get("failed", 0)),
        "unique_fit_ids": len(set(counter.get("fit_ids", []))),
        "complete": (
            int(counter.get("attempted_fits", 0)) >= TOTAL_FITS
            and int(counter.get("completed_ok", 0)) + int(counter.get("failed", 0))
            >= TOTAL_FITS
        ),
    }
    marginal = {
        "logreg_rna": _pool_donor_ba_from_predictions(
            records, stage="screen", rho=1.0, model="logreg_rna"
        ),
        "logreg_atac": _pool_donor_ba_from_predictions(
            records, stage="screen", rho=1.0, model="logreg_atac"
        ),
    }
    rna_ba = marginal["logreg_rna"].get("ba")
    atac_ba = marginal["logreg_atac"].get("ba")
    marginal["pass"] = (
        marginal["logreg_rna"].get("complete")
        and marginal["logreg_atac"].get("complete")
        and rna_ba is not None
        and atac_ba is not None
        and float(rna_ba) <= MARGINAL_BA_MAX
        and float(atac_ba) <= MARGINAL_BA_MAX
    )
    pairing_rho1 = score_pairing_for_rho(
        records=records,
        labels=labels,
        splits=splits,
        protocol=proto,
        rho=1.0,
    )
    pairing_rho0 = score_pairing_for_rho(
        records=records,
        labels=labels,
        splits=splits,
        protocol=proto,
        rho=0.0,
    )
    interpretation = interpret_batch(
        records=records,
        pairing_rho1=pairing_rho1,
        pairing_rho0=pairing_rho0,
        marginal=marginal,
        coverage=coverage,
    )
    return {
        "protocol_id": PROTOCOL_ID,
        "reviewed_hashes": live_hashes,
        "raw_root": str(root),
        "exec_summary": exec_summary,
        "coverage": coverage,
        "marginal": marginal,
        "pairing_rho1": pairing_rho1,
        "pairing_rho0": pairing_rho0,
        "interpretation": interpretation,
        "skip_fits": skip_fits,
        "workers": 1,
    }
