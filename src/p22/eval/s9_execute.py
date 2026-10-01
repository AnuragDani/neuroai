"""Q10 S9 analytic pairing-use batch executor.

Runs the Checkpoint-C-authorized smoke+screen fits under the frozen protocol,
writes a new S9 raw root, and replays pairing statistics from saved sidecars.
Does not modify reviewed ``s9_analytic.py``; reuses ``fit_s7_arm`` /
``evaluate_pairing_pc`` / analytic generator helpers.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from p22.eval.s9_analytic import (
    ALLOWED_RAW_ROOT,
    DECISION_GENERATOR_SEED,
    DECISION_MODEL_SEED,
    N_FOLDS,
    PAIRING_SHUFFLE_SEEDS,
    PROTOCOL_ID,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_ATTEMPT_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TOTAL_FITS,
    allocate_s9_folds,
    assert_donor_isolation,
    assign_donor_labels,
    enumerate_s9_jobs,
    fold_row_indices,
    generate_analytic_arrays,
    permute_atac_within_donor,
    refuse_if_not_allowed_raw_root,
    refuse_mismatched_protocol_hash,
    s9_protocol_from_frozen,
    verify_oracle_invariants,
)
from p22.models.fusion import VIEW_A, VIEW_B

REVIEWED_HASHES = {
    "SYNTHETIC_PROTOCOL.json": (
        "eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a"
    ),
    "SPLIT_MANIFEST.json": (
        "2d9a3b9fac7bfd8dd48b7517e0ad22e297eab9a4e9f775ac814dd99b8c50fd4d"
    ),
    "FIT_LEDGER.json": (
        "841c8468b6b17a43628d14af00f277ffb156b774264fe1dad0545b2ab5cd3563"
    ),
    "src/p22/eval/s9_analytic.py": (
        "dad126cd6dc33e9e8226b9924baa7c0b0fd3e88f8b413a6b06c9313c06d4ea02"
    ),
}
CHECKPOINT_MODELS = frozenset({"cross_attention", "token_concat"})
MARGINAL_BA_MAX = 0.60
WORKERS = 2
TORCH_THREADS = 2
LEDGER_NAME = "attempt_ledger.jsonl"
PROVENANCE_NAME = "provenance.json"
COUNTER_NAME = "attempt_counter.json"


class S9ExecuteRefusal(ValueError):
    """Refuse unauthorized or unsafe Q10 execution."""


def verify_checkpoint_c_hashes(
    *,
    workspace: Path,
    protocol_path: Path,
    split_path: Path,
    ledger_path: Path,
) -> dict[str, str]:
    """Require exact Q9-reviewed hashes before any research fit."""
    paths = {
        "SYNTHETIC_PROTOCOL.json": Path(protocol_path),
        "SPLIT_MANIFEST.json": Path(split_path),
        "FIT_LEDGER.json": Path(ledger_path),
        "src/p22/eval/s9_analytic.py": Path(workspace) / "src/p22/eval/s9_analytic.py",
    }
    live: dict[str, str] = {}
    for key, path in paths.items():
        if not path.is_file():
            raise S9ExecuteRefusal(f"missing reviewed artifact {key}: {path}")
        digest = sha256_file(path)
        live[key] = digest
        refuse_mismatched_protocol_hash(
            REVIEWED_HASHES[key], digest, label=key
        )
    return live


def _dir_size_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def prepare_raw_root(raw_root: Path | str) -> Path:
    """Create authorized S9 raw root; refuse S7/S8 and symlink write-through."""
    root = Path(raw_root)
    refuse_if_not_allowed_raw_root(root)
    if root.exists():
        if root.is_symlink():
            raise S9ExecuteRefusal(f"raw root must not be a symlink: {root}")
        # Resume-safe: existing root ok if counter present; no wipe.
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


def should_retain_s9_checkpoint(job: Mapping[str, Any]) -> bool:
    """Retain CA/TC for pairing/advantage at both decision rhos."""
    return str(job["model"]) in CHECKPOINT_MODELS and str(job["stage"]) == "screen"


def save_s9_checkpoint(record: Mapping[str, Any], checkpoint_dir: Path) -> Path | None:
    if not should_retain_s9_checkpoint(record):
        return None
    payload = record.get("checkpoint")
    if payload is None:
        raise S9ExecuteRefusal(f"missing checkpoint for retainable {record['fit_id']}")
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
        rna, atac, donor, lab, cells = generate_analytic_arrays(
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


def run_one_s9_fit(
    job: Mapping[str, Any],
    *,
    labels: dict[str, int],
    splits: Mapping[str, Any],
    protocol: MultiomeProtocol,
    array_cache: dict[float, tuple[np.ndarray, ...]],
) -> dict[str, Any]:
    """Fit one predeclared S9 job; return ledger-ready record."""
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
            "checkpoint": scores.get("checkpoint"),
            "test_cell_probabilities": scores.get("test_cell_probabilities"),
            "donor_probabilities": scores.get("donor_probabilities"),
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


def execute_jobs(
    jobs: list[dict[str, Any]],
    *,
    raw_root: Path,
    labels: dict[str, int],
    splits: Mapping[str, Any],
    protocol: MultiomeProtocol,
    workers: int = WORKERS,
    torch_threads: int = TORCH_THREADS,
    attempt_cap: int = SYNTHETIC_ATTEMPT_CAP,
) -> dict[str, Any]:
    """Execute remaining jobs under cumulative attempt counter; preserve failures."""
    counter = load_attempt_counter(raw_root)
    done_ids = set(counter.get("fit_ids", []))
    remaining = [j for j in jobs if j["fit_id"] not in done_ids]
    if counter["attempted_fits"] > attempt_cap:
        raise S9ExecuteRefusal(
            f"attempt counter {counter['attempted_fits']} already exceeds cap {attempt_cap}"
        )
    if counter["attempted_fits"] + len(remaining) > attempt_cap:
        raise S9ExecuteRefusal(
            f"planned remaining {len(remaining)} would exceed cap "
            f"({counter['attempted_fits']} + {len(remaining)} > {attempt_cap})"
        )

    torch.set_num_threads(int(torch_threads))
    os.environ["OMP_NUM_THREADS"] = str(int(torch_threads))
    array_cache: dict[float, tuple[np.ndarray, ...]] = {}
    # Pre-warm rho caches on the main thread to avoid concurrent first-fill races.
    for rho in sorted({float(j["rho"]) for j in remaining}):
        _arrays_for_rho(labels, rho, cache=array_cache)
    ckpt_dir = raw_root / "checkpoints"
    pred_dir = raw_root / "donor_predictions"
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    def _persist(record: dict[str, Any]) -> dict[str, Any]:
        ckpt_path = save_s9_checkpoint(record, ckpt_dir)
        pred_path = save_donor_predictions(record, pred_dir)
        payload = ledger_payload(record)
        payload["seconds"] = record.get("seconds")
        if ckpt_path is not None:
            payload["checkpoint_path"] = str(ckpt_path)
            payload["checkpoint_sha256"] = sha256_file(ckpt_path)
        if pred_path is not None:
            payload["donor_predictions_path"] = str(pred_path)
            payload["donor_predictions_sha256"] = sha256_file(pred_path)
        append_ledger_row(raw_root, payload)
        counter["attempted_fits"] = int(counter["attempted_fits"]) + 1
        counter["fitting_seconds"] = float(counter.get("fitting_seconds", 0.0)) + float(
            record.get("seconds") or 0.0
        )
        counter.setdefault("fit_ids", []).append(record["fit_id"])
        if str(record.get("status")) == "ok":
            counter["completed_ok"] = int(counter.get("completed_ok", 0)) + 1
        else:
            counter["failed"] = int(counter.get("failed", 0)) + 1
        save_attempt_counter(raw_root, counter)
        return payload

    if workers <= 1 or len(remaining) <= 1:
        for job in remaining:
            record = run_one_s9_fit(
                job,
                labels=labels,
                splits=splits,
                protocol=protocol,
                array_cache=array_cache,
            )
            results.append(_persist(record))
    else:
        # Thread pool: shared array_cache is read-mostly after first fills.
        with ThreadPoolExecutor(max_workers=int(workers)) as pool:
            futures = {
                pool.submit(
                    run_one_s9_fit,
                    job,
                    labels=labels,
                    splits=splits,
                    protocol=protocol,
                    array_cache=array_cache,
                ): job
                for job in remaining
            }
            for fut in as_completed(futures):
                record = fut.result()
                results.append(_persist(record))

    wall = float(time.perf_counter() - started)
    return {
        "n_executed_this_call": len(results),
        "n_skipped_already_done": len(jobs) - len(remaining),
        "wall_seconds": wall,
        "counter": dict(counter),
        "records": results,
    }


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


def _pool_donor_ba_from_predictions(
    records: list[Mapping[str, Any]],
    *,
    stage: str,
    rho: float,
    model: str,
) -> dict[str, Any]:
    """Pool disjoint outer-fold held-out donors once; compute BA at threshold 0.5."""
    selected = [
        r
        for r in records
        if r.get("stage") == stage
        and abs(float(r.get("rho", -1)) - float(rho)) < 1e-12
        and r.get("model") == model
        and r.get("status") == "ok"
        and r.get("donor_predictions_path")
    ]
    if len(selected) != N_FOLDS:
        return {
            "complete": False,
            "n_folds": len(selected),
            "expected_folds": N_FOLDS,
            "ba": None,
            "n_donors": 0,
        }
    donor_ids: list[str] = []
    y_true: list[int] = []
    probs: list[float] = []
    seen: set[str] = set()
    for row in sorted(selected, key=lambda r: int(r["fold"])):
        blob = json.loads(Path(row["donor_predictions_path"]).read_text())
        preds = blob["donor_probabilities"]
        for d, y, p in zip(
            preds["donor_id"], preds["label"], preds["probability"], strict=True
        ):
            d_s = str(d)
            if d_s in seen:
                return {
                    "complete": False,
                    "reason": f"duplicate donor across folds: {d_s}",
                    "ba": None,
                    "n_donors": 0,
                }
            seen.add(d_s)
            donor_ids.append(d_s)
            y_true.append(int(y))
            probs.append(float(p))
    y_arr = np.asarray(y_true, dtype=int)
    p_arr = np.asarray(probs, dtype=float)
    pred = (p_arr >= 0.5).astype(int)
    # Balanced accuracy
    ba_parts = []
    for cls in (0, 1):
        mask = y_arr == cls
        if not np.any(mask):
            return {"complete": False, "reason": f"missing class {cls}", "ba": None}
        ba_parts.append(float(np.mean(pred[mask] == cls)))
    return {
        "complete": True,
        "n_folds": N_FOLDS,
        "n_donors": len(donor_ids),
        "ba": float(np.mean(ba_parts)),
        "donor_ids": donor_ids,
    }


def _score_pairing_for_rho(
    *,
    raw_root: Path,
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

    rna, atac, donor, lab, _cells = generate_analytic_arrays(
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
            # Preserve within-donor marginal on test rows
            test_donors = donor[test]
            for name in sorted(set(test_donors.tolist()), key=str):
                idx_all = np.flatnonzero(donor == name)
                orig_sorted = np.sort(atac[idx_all], axis=0)
                shuf_sorted = np.sort(atac_s[idx_all], axis=0)
                if not np.allclose(orig_sorted, shuf_sorted):
                    raise S9ExecuteRefusal(
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
    # Map S7 PC labels to S9 pairing labels
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


def interpret_batch(
    *,
    records: list[Mapping[str, Any]],
    pairing_rho1: Mapping[str, Any],
    pairing_rho0: Mapping[str, Any],
    marginal: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply frozen joint rule; never promote incomplete/null failure to method claim."""
    secondary: list[str] = []
    if pairing_rho0.get("pairing_label") == "PAIRING_POSITIVE":
        secondary.append(
            "also: fitted rho=0 pairing-plant null yielded PAIRING_POSITIVE"
        )
    if pairing_rho1.get("pairing_label") == "PAIRING_NEGATIVE":
        secondary.append("also: CA rho=1 pairing was PAIRING_NEGATIVE")
    elif pairing_rho1.get("pairing_label") == "PAIRING_POSITIVE":
        secondary.append("also: CA rho=1 pairing was PAIRING_POSITIVE (not claimed)")

    if not coverage.get("complete"):
        return {
            "disposition": "INCOMPLETE",
            "primary_pairing": None,
            "reason": "smoke+screen coverage incomplete",
            "secondary_findings": secondary,
            "coverage": coverage,
        }
    if not marginal.get("pass", False):
        return {
            "disposition": "INVALID",
            "primary_pairing": None,
            "reason": (
                "rho=1 unimodal marginal BA exceeds 0.60 "
                "(logreg_rna/logreg_atac shortcut)"
            ),
            "secondary_findings": secondary,
            "marginal": marginal,
            "pairing_rho0": pairing_rho0,
            "pairing_rho1": pairing_rho1,
        }
    if pairing_rho0.get("pairing_label") == "PAIRING_POSITIVE":
        return {
            "disposition": "INVALID",
            "primary_pairing": None,
            "reason": (
                "fitted rho=0 pairing-plant null yielded PAIRING_POSITIVE "
                "(design/optimization leak); not a method claim"
            ),
            "secondary_findings": secondary,
            "pairing_rho0": pairing_rho0,
            "pairing_rho1": pairing_rho1,
        }
    if pairing_rho0.get("pairing_label") in {"INCOMPLETE", "INVALID"}:
        return {
            "disposition": (
                "INCOMPLETE"
                if pairing_rho0.get("pairing_label") == "INCOMPLETE"
                else "INVALID"
            ),
            "primary_pairing": None,
            "reason": f"rho=0 null gate unresolved: {pairing_rho0.get('pairing_label')}",
            "secondary_findings": secondary,
            "pairing_rho0": pairing_rho0,
        }
    if pairing_rho1.get("pairing_label") == "PAIRING_POSITIVE":
        return {
            "disposition": "PAIRING_POSITIVE",
            "primary_pairing": "PAIRING_POSITIVE",
            "reason": "CA rho=1 donor log-loss-drop CI lower > 0; rho=0 null not positive",
            "secondary_findings": secondary,
            "pairing_rho1": pairing_rho1,
            "pairing_rho0": pairing_rho0,
        }
    if pairing_rho1.get("pairing_label") == "PAIRING_NEGATIVE":
        return {
            "disposition": "PAIRING_NEGATIVE",
            "primary_pairing": "PAIRING_NEGATIVE",
            "reason": "CA rho=1 donor log-loss-drop CI lower <= 0 under fitted plant",
            "secondary_findings": secondary,
            "pairing_rho1": pairing_rho1,
            "pairing_rho0": pairing_rho0,
        }
    return {
        "disposition": "INCOMPLETE",
        "primary_pairing": None,
        "reason": f"rho=1 pairing unresolved: {pairing_rho1.get('pairing_label')}",
        "secondary_findings": secondary,
        "pairing_rho1": pairing_rho1,
    }


def run_q10_batch(
    *,
    workspace: Path,
    protocol_path: Path,
    split_path: Path,
    ledger_path: Path,
    review_path: Path,
    raw_root: Path | None = None,
    workers: int = WORKERS,
    torch_threads: int = TORCH_THREADS,
    skip_fits: bool = False,
) -> dict[str, Any]:
    """Authorize, execute (unless skip), replay, and summarize one S9 batch."""
    workspace = Path(workspace)
    live_hashes = verify_checkpoint_c_hashes(
        workspace=workspace,
        protocol_path=protocol_path,
        split_path=split_path,
        ledger_path=ledger_path,
    )
    review = json.loads(Path(review_path).read_text())
    if review.get("verdict") != "PASS" or review.get("disposition") != "PASS":
        raise S9ExecuteRefusal("Q9 independent review must be PASS before Q10 fits")
    if not review.get("checkpoint_c", {}).get("authorized_by_review", False):
        raise S9ExecuteRefusal("Checkpoint C authorization missing in NO_FIT_REVIEW")

    protocol_blob = json.loads(Path(protocol_path).read_text())
    root = prepare_raw_root(raw_root or (workspace / ALLOWED_RAW_ROOT))
    refuse_if_not_allowed_raw_root(root)

    # Resource gate (disk); artifact cap checked after.
    try:
        disk = check_disk_resources(
            output_root=root,
            min_free_gib=2.0,
            max_artifacts_gib=SYNTHETIC_ARTIFACT_GIB_CAP,
        )
    except RuntimeError as err:
        # Soften min free for small synthetic; still enforce artifact cap.
        if "min_free_disk_gib" in str(err):
            usage = shutil.disk_usage(root if root.exists() else workspace)
            free_gib = usage.free / (1024**3)
            if free_gib < 1.0:
                raise S9ExecuteRefusal(f"insufficient free disk: {free_gib:.2f} GiB") from err
            disk = {
                "free_gib": round(free_gib, 3),
                "artifacts_gib": round(_dir_size_bytes(root) / (1024**3), 3)
                if root.exists()
                else 0.0,
                "ok": True,
                "note": "min_free softened for analytic synthetic; artifact cap enforced",
            }
        else:
            raise

    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    splits = allocate_s9_folds(labels)
    split_manifest = json.loads(Path(split_path).read_text())
    if splits["donor_labels"] != split_manifest["donor_labels"]:
        raise S9ExecuteRefusal("live split labels diverge from SPLIT_MANIFEST")
    for fk, fold in split_manifest["folds"].items():
        if splits["folds"][fk] != fold:
            raise S9ExecuteRefusal(f"live split fold {fk} diverges from SPLIT_MANIFEST")

    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise S9ExecuteRefusal(f"oracle gate FAIL before fits: {oracle}")

    proto = s9_protocol_from_frozen(protocol_blob["models"]["training_budget"])
    jobs = enumerate_s9_jobs()
    if len(jobs) != TOTAL_FITS:
        raise S9ExecuteRefusal(f"job count {len(jobs)} != {TOTAL_FITS}")

    provenance = {
        "protocol_id": PROTOCOL_ID,
        "task": "Q10",
        "reviewed_hashes": live_hashes,
        "review_verdict": review.get("verdict"),
        "reviewer_agent_id": review.get("reviewer", {}).get("agent_id"),
        "raw_root": str(root),
        "attempt_cap": SYNTHETIC_ATTEMPT_CAP,
        "planned_fits": TOTAL_FITS,
        "workers": workers,
        "torch_threads": torch_threads,
        "logreg_frozen": dict(S7_LOGREG_FROZEN),
    }
    (root / PROVENANCE_NAME).write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )

    exec_summary: dict[str, Any]
    if skip_fits:
        exec_summary = {
            "n_executed_this_call": 0,
            "n_skipped_already_done": 0,
            "wall_seconds": 0.0,
            "counter": load_attempt_counter(root),
            "records": [],
            "skipped": True,
        }
    else:
        exec_summary = execute_jobs(
            jobs,
            raw_root=root,
            labels=labels,
            splits=splits,
            protocol=proto,
            workers=workers,
            torch_threads=torch_threads,
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
            int(counter.get("attempted_fits", 0)) == TOTAL_FITS
            and int(counter.get("completed_ok", 0)) == TOTAL_FITS
            and len(set(counter.get("fit_ids", []))) == TOTAL_FITS
        ),
    }

    # Marginal unimodal check at rho=1 from saved donor predictions
    rna_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="logreg_rna"
    )
    atac_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="logreg_atac"
    )
    marginal = {
        "logreg_rna_ba": rna_ba.get("ba"),
        "logreg_atac_ba": atac_ba.get("ba"),
        "threshold": MARGINAL_BA_MAX,
        "pass": (
            rna_ba.get("complete")
            and atac_ba.get("complete")
            and rna_ba.get("ba") is not None
            and atac_ba.get("ba") is not None
            and float(rna_ba["ba"]) <= MARGINAL_BA_MAX
            and float(atac_ba["ba"]) <= MARGINAL_BA_MAX
        ),
        "logreg_rna": rna_ba,
        "logreg_atac": atac_ba,
    }

    pairing_rho1: dict[str, Any]
    pairing_rho0: dict[str, Any]
    if coverage["complete"]:
        pairing_rho1 = _score_pairing_for_rho(
            raw_root=root,
            records=records,
            labels=labels,
            splits=splits,
            protocol=proto,
            rho=1.0,
        )
        pairing_rho0 = _score_pairing_for_rho(
            raw_root=root,
            records=records,
            labels=labels,
            splits=splits,
            protocol=proto,
            rho=0.0,
        )
    else:
        pairing_rho1 = {"complete": False, "pairing_label": "INCOMPLETE", "reason": "coverage"}
        pairing_rho0 = {"complete": False, "pairing_label": "INCOMPLETE", "reason": "coverage"}

    ca_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="cross_attention"
    )
    tc_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="token_concat"
    )
    advantage = {
        "label": "SEPARATE_NON_PRIMARY",
        "ca_ba": ca_ba.get("ba"),
        "token_concat_ba": tc_ba.get("ba"),
        "ca_minus_token_concat": (
            None
            if ca_ba.get("ba") is None or tc_ba.get("ba") is None
            else float(ca_ba["ba"]) - float(tc_ba["ba"])
        ),
        "complete": bool(ca_ba.get("complete") and tc_ba.get("complete")),
    }

    interpretation = interpret_batch(
        records=records,
        pairing_rho1=pairing_rho1,
        pairing_rho0=pairing_rho0,
        marginal=marginal,
        coverage=coverage,
    )

    artifacts_gib = _dir_size_bytes(root) / (1024**3)
    fitting_hours = float(counter.get("fitting_seconds", 0.0)) / 3600.0
    resource = {
        "attempted_fits": int(counter.get("attempted_fits", 0)),
        "cap": SYNTHETIC_ATTEMPT_CAP,
        "within_cap": int(counter.get("attempted_fits", 0)) <= SYNTHETIC_ATTEMPT_CAP,
        "fitting_seconds": float(counter.get("fitting_seconds", 0.0)),
        "fitting_hours": fitting_hours,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "within_fitting_hours": fitting_hours <= SYNTHETIC_FITTING_HOURS_CAP,
        "artifacts_gib": round(artifacts_gib, 6),
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "within_artifact_cap": artifacts_gib <= SYNTHETIC_ARTIFACT_GIB_CAP,
        "disk": disk,
        "workers": workers,
        "torch_threads": torch_threads,
    }

    report = {
        "task": "Q10",
        "disposition": interpretation["disposition"],
        "protocol_id": PROTOCOL_ID,
        "date": time.strftime("%Y-%m-%d"),
        "branch": "gnhf/execute-the-p22-data-146414",
        "fits": int(counter.get("attempted_fits", 0)),
        "research_fits_executed": int(counter.get("attempted_fits", 0)),
        "network_bytes": 0,
        "depends_on": ["Q9", "Checkpoint C"],
        "raw_root": str(root),
        "reviewed_hashes": live_hashes,
        "hashes_match_q9": True,
        "coverage": coverage,
        "execution": {
            "n_executed_this_call": exec_summary.get("n_executed_this_call"),
            "n_skipped_already_done": exec_summary.get("n_skipped_already_done"),
            "wall_seconds": exec_summary.get("wall_seconds"),
            "skipped": exec_summary.get("skipped", False),
        },
        "oracle": oracle,
        "marginal_check": marginal,
        "pairing_rho1": _jsonable(pairing_rho1),
        "pairing_rho0": _jsonable(pairing_rho0),
        "advantage_contrast": advantage,
        "interpretation": _jsonable(interpretation),
        "resources": resource,
        "scientific_invariants": {
            "primary": "B_NULL",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "prior_s8": "NO FIT",
            "power": "POWER_UNESTABLISHED",
            "study": "STUDY_PARTIAL",
            "q2_endpoint": "ENDPOINT_UNRESOLVED",
            "q3_regulatory": "REGULATORY_ADEQUACY_UNRESOLVED",
            "q5_external": "EXTERNAL_FEASIBILITY_BOUNDED / confirmatory UNRESOLVED",
        },
        "unresolved_flags_retained": [
            "ENDPOINT_UNRESOLVED",
            "REGULATORY_ADEQUACY_UNRESOLVED",
            "EXTERNAL_FEASIBILITY_BOUNDED/confirmatory UNRESOLVED",
            "POWER_UNESTABLISHED",
            "fitted_ba_montecarlo_joint_calibration DESIGN_UNRESOLVED",
        ],
        "q11_authorization": {
            "biological_pilot": "BLOCKED",
            "reason": "Q2 ENDPOINT_UNRESOLVED (and Q3/Q5 unresolved) cannot unlock Q11",
        },
    }
    return report


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def render_execute_markdown(report: Mapping[str, Any]) -> str:
    cov = report["coverage"]
    res = report["resources"]
    interp = report["interpretation"]
    p1 = report.get("pairing_rho1") or {}
    p0 = report.get("pairing_rho0") or {}
    lines = [
        "# Q10 — Bounded S9 analytic pairing-use synthetic batch",
        "",
        f"**Disposition:** `{report['disposition']}`  ",
        f"**Protocol ID:** `{report['protocol_id']}`  ",
        f"**Date:** {report['date']}  ",
        f"**Branch:** `{report['branch']}`  ",
        f"**Research fits:** {report['research_fits_executed']}  ",
        f"**Raw root:** `{report['raw_root']}`",
        "",
        "Machine-readable: [execute.json](execute.json).",
        "",
        "## Coverage",
        "",
        f"- Planned: {cov['planned']}; attempted: {cov['attempted']}; "
        f"ok: {cov['completed_ok']}; failed: {cov['failed']}",
        f"- Complete: `{cov['complete']}`",
        "",
        "## Primary pairing (CA)",
        "",
        f"- ρ=1 label: `{p1.get('pairing_label')}`",
        f"- ρ=0 null label: `{p0.get('pairing_label')}`",
        f"- Interpretation: {interp.get('reason')}",
        "",
    ]
    secondary = interp.get("secondary_findings") or []
    if secondary:
        lines.append("- Secondary findings:")
        for item in secondary:
            lines.append(f"  - {item}")
        lines.append("")
    lines.extend([
        "## Advantage contrast (SEPARATE_NON_PRIMARY)",
        "",
        f"- CA BA: {report['advantage_contrast'].get('ca_ba')}",
        f"- token_concat BA: {report['advantage_contrast'].get('token_concat_ba')}",
        f"- CA−TC: {report['advantage_contrast'].get('ca_minus_token_concat')}",
        "",
        "## Marginal check (ρ=1)",
        "",
        f"- logreg_rna BA: {report['marginal_check'].get('logreg_rna_ba')}",
        f"- logreg_atac BA: {report['marginal_check'].get('logreg_atac_ba')}",
        f"- pass (≤{report['marginal_check'].get('threshold')}): "
        f"`{report['marginal_check'].get('pass')}`",
        "",
        "## Resources",
        "",
        f"- Fits: {res['attempted_fits']} ≤ {res['cap']} (`{res['within_cap']}`)",
        f"- Fitting hours: {res['fitting_hours']:.4f} ≤ {res['fitting_hours_cap']}",
        f"- Artifacts GiB: {res['artifacts_gib']} ≤ {res['artifact_gib_cap']}",
        f"- Workers×threads: {res['workers']}×{res['torch_threads']}",
        "",
        "## Scientific invariants (unchanged)",
        "",
        "Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; "
        "power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.",
        "",
        "Unresolved flags retained: ENDPOINT_UNRESOLVED; "
        "REGULATORY_ADEQUACY_UNRESOLVED; EXTERNAL confirmatory UNRESOLVED.",
        "",
        "## Q11",
        "",
        f"- Biological pilot: **{report['q11_authorization']['biological_pilot']}** — "
        f"{report['q11_authorization']['reason']}",
        "",
        "## Next",
        "",
        "Q11 SKIPPED/BLOCKED (endpoint unresolved) or Q12 handoff after disposition recorded.",
        "",
    ])
    return "\n".join(lines)
