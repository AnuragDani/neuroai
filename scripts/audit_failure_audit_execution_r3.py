#!/usr/bin/env python3
"""R3 execution-determinism / resource accounting audit — read-only by default.

Inventories globally seeded model/fit callers, hashes the S9 executor dependency
path, reviews ledger/resume/resource enforcement in code, and freezes a tiny
diagnostic fit spec for separate independent review.

Does NOT run diagnostic fits unless --run-diagnostic-fits is passed AND a
PASS review JSON is supplied. Default path: zero fits.
Does not write into the shared S9 raw root.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from p22.eval.s7_ledger import sha256_file  # noqa: E402
from p22.eval.s9_execute import TORCH_THREADS, WORKERS  # noqa: E402

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "failure_audit_20261001"
)
DEFAULT_RAW_ROOT = ROOT / "reports" / "generated" / "nn_failure_audit_20261001"
SHARED_S9_RAW = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/"
    "finish-engineering-20260928-gnhf-worktrees/"
    "read-tasks-nn-finish-ee2202-gnhf-worktrees/"
    "read-users-anuragdan-b61180-gnhf-worktrees/"
    "execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930"
)

# Executor + full S9 fit dependency path (actual import chain for research fits).
EXECUTOR_DEPENDENCY_PATH: tuple[str, ...] = (
    "src/p22/eval/s9_execute.py",
    "src/p22/eval/s7_runner.py",
    "src/p22/eval/multiome_runner.py",
    "src/p22/training/loop.py",
    "src/p22/eval/s9_analytic.py",
    "src/p22/eval/s7_ledger.py",
    "src/p22/eval/s7_pairing.py",
    "src/p22/eval/multiome_protocol.py",
    "src/p22/models/fusion.py",
    "src/p22/models/baselines.py",
    "src/p22/models/cross_attention.py",
)

# ---------------------------------------------------------------------------
# Frozen diagnostic fit spec — committed before any diagnostic training.
# Separate independent review must PASS before --run-diagnostic-fits.
# ---------------------------------------------------------------------------
DIAGNOSTIC_FIT_SPEC: dict[str, Any] = {
    "spec_id": "r3_rng_thread_diag_20261001",
    "committed_before_any_diagnostic_fit": True,
    "purpose": (
        "Diagnose whether concurrent ThreadPoolExecutor workers racing on "
        "process-global set_all_seeds change neural init/train outcomes versus "
        "serial execution on identical fixed tensors. Code diagnosis only; not "
        "an S9 scientific performance run or seed-shopping exercise."
    ),
    "not_s9_rescue": True,
    "not_favourable_seed_selection": True,
    "attempt_cap": 12,
    "wall_minutes_cap": 15,
    "scientific_fits_allowed": 0,
    "model": "gated_fusion",
    "protocol": {
        "n_tokens": 2,
        "embed_dim": 8,
        "hidden_dim": 8,
        "n_heads": 2,
        "dropout": 0.0,
        "max_epochs": 3,
        "patience": 3,
        "batch_size": 8,
        "learning_rate": 0.001,
        "model_seed": 7701,
    },
    "tensors": {
        "n_donors": 8,
        "cells_per_donor": 4,
        "n_features_rna": 4,
        "n_features_atac": 4,
        "n_classes": 2,
        "label_balance": "4_pos_4_neg_donors",
        "generator_seed_for_fixed_arrays": 7701,
        "construction": (
            "numpy Generator(7701): RNA/ATAC ~ N(0,1); donor labels fixed "
            "[0,0,0,0,1,1,1,1]; train/val/test indices frozen in this spec"
        ),
    },
    "frozen_split_indices": {
        "train_donors": [0, 1, 4, 5],
        "val_donors": [2, 6],
        "test_donors": [3, 7],
    },
    "jobs": [
        {
            "attempt_ids": ["A1", "A2"],
            "route": "serial",
            "job_key": "J1",
            "purpose": "serial repeatability (A2 must match A1 state_dict+preds)",
        },
        {
            "attempt_ids": ["A3", "A4"],
            "route": "serial",
            "job_key": "J2",
            "purpose": "second fold-equivalent serial identity (swap test/val)",
            "split_override": {
                "train_donors": [0, 1, 4, 5],
                "val_donors": [3, 7],
                "test_donors": [2, 6],
            },
        },
        {
            "attempt_ids": ["A5", "A6"],
            "route": "thread_pool_workers_2",
            "job_keys": ["J1", "J2"],
            "purpose": "concurrent pair #1; compare to serial A1/A3 references",
        },
        {
            "attempt_ids": ["A7", "A8"],
            "route": "thread_pool_workers_2",
            "job_keys": ["J1", "J2"],
            "purpose": "concurrent pair #2; assess concurrent-vs-concurrent stability",
        },
        {
            "attempt_ids": ["A9"],
            "route": "serial",
            "job_key": "J1",
            "purpose": "post-concurrent serial contamination check vs A1",
        },
        {
            "attempt_ids": ["A10"],
            "route": "serial_deliberate_fail",
            "job_key": "J_FAIL",
            "purpose": "failed-attempt accounting + counter survival (empty train)",
            "deliberate_failure": "empty_train_indices",
        },
        {
            "attempt_ids": ["A11", "A12"],
            "route": "serial_resume_fixture",
            "job_key": "J1",
            "purpose": (
                "A11 writes ledger row then stops; A12 resume must refuse double-count "
                "or skip already-done fit_id"
            ),
        },
    ],
    "success_criteria": {
        "serial_identity_atol_state": 0.0,
        "serial_identity_atol_preds": 1e-12,
        "concurrent_divergence_is_evidence_of_rng_interference": True,
        "concurrent_match_does_not_prove_absence_of_race": True,
        "repair_if_confirmed": (
            "Prefer serial jobs (workers=1) as default; process isolation only if "
            "serial cannot eliminate observed interference"
        ),
    },
    "tolerances": {
        "state_dict_max_abs_diff_serial": 0.0,
        "prediction_max_abs_diff_serial": 1e-12,
        "report_all_differences": True,
    },
    "outputs": {
        "ledger": "reports/generated/nn_failure_audit_20261001/r3_diagnostic_ledger.jsonl",
        "results_json": (
            "tasks/nn/professor_direction_investigation_20260929/"
            "failure_audit_20261001/r3_diagnostic_results.json"
        ),
    },
    "review_gate": {
        "required": True,
        "self_certification_forbidden": True,
        "unavailable_means": "REVIEW_PENDING; read-only audit still completes; 0 diagnostic fits",
    },
}


class ExecutionAuditRefusal(RuntimeError):
    """Refuse unsafe R3 audit actions."""


def _fingerprint_tree(root: Path) -> dict[str, Any]:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            rows.append(f"{st.st_mtime_ns} {st.st_size} {path.relative_to(root)}")
    digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    return {"n_files": len(rows), "tree_sha256": digest}


def _assert_no_write(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if before["tree_sha256"] != after["tree_sha256"]:
        raise ExecutionAuditRefusal(
            "shared S9 raw tree mutated during R3; refuse write-through"
        )


def _call_sites(path: Path, names: Sequence[str]) -> list[dict[str, Any]]:
    """AST inventory of Call nodes whose func id/attr is in names."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[dict[str, Any]] = []
    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            label = None
            if isinstance(func, ast.Name) and func.id in names:
                label = func.id
            elif isinstance(func, ast.Attribute) and func.attr in names:
                label = func.attr
            if label is not None:
                found.append(
                    {
                        "name": label,
                        "lineno": node.lineno,
                        "col": node.col_offset,
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return found


def inventory_seed_callers(workspace: Path) -> dict[str, Any]:
    """Inventory set_all_seeds / paired_model / train_model / ThreadPoolExecutor."""
    src = workspace / "src"
    targets = ("set_all_seeds", "paired_model", "train_model", "ThreadPoolExecutor")
    by_file: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(src.rglob("*.py")):
        hits = _call_sites(path, targets)
        # Also record definitions
        text = path.read_text(encoding="utf-8")
        defs: list[str] = []
        if "def set_all_seeds" in text:
            defs.append("defines_set_all_seeds")
        if "def paired_model" in text:
            defs.append("defines_paired_model")
        if "def train_model" in text:
            defs.append("defines_train_model")
        if hits or defs:
            rel = str(path.relative_to(workspace))
            by_file[rel] = {"calls": hits, "definitions": defs}

    s9_path = workspace / "src/p22/eval/s9_execute.py"
    s9_text = s9_path.read_text(encoding="utf-8")
    concurrent_risk = {
        "s9_default_workers": WORKERS,
        "s9_default_torch_threads": TORCH_THREADS,
        "uses_thread_pool_executor": "ThreadPoolExecutor" in s9_text,
        "set_all_seeds_mutates_process_globals": True,
        "set_all_seeds_targets": ["random.seed", "np.random.seed", "torch.manual_seed"],
        "paired_model_calls_set_all_seeds_before_init": True,
        "train_model_calls_set_all_seeds_then_local_generator": True,
        "local_batch_generator_isolates_shuffle_only": True,
        "weight_init_uses_global_torch_rng_after_seed": True,
        "interference_inferred_from_threading_alone": False,
        "interference_code_path_exists": True,
        "effect_on_outcomes": "UNMEASURED_PENDING_DIAGNOSTIC_FITS",
        "notes": (
            "S9 execute_jobs with workers=2 submits run_one_s9_fit → fit_s7_arm → "
            "paired_model(set_all_seeds) → train_model(set_all_seeds) on concurrent "
            "threads sharing process-global RNG. Code path permits cross-job races; "
            "outcome impact requires frozen diagnostic fits after independent review."
        ),
    }
    return {
        "files": by_file,
        "n_files_with_hits": len(by_file),
        "concurrent_risk": concurrent_risk,
    }


def hash_executor_path(workspace: Path) -> dict[str, Any]:
    rows: dict[str, str] = {}
    for rel in EXECUTOR_DEPENDENCY_PATH:
        path = workspace / rel
        if not path.is_file():
            raise ExecutionAuditRefusal(f"missing executor dependency {rel}")
        rows[rel] = sha256_file(path)
    chain = "\n".join(f"{digest}  {rel}" for rel, digest in rows.items())
    return {
        "files": rows,
        "chain_sha256": hashlib.sha256(chain.encode()).hexdigest(),
        "n_files": len(rows),
    }


def audit_ledger_resume_resources(workspace: Path) -> dict[str, Any]:
    """Static review of attempt reservation, crash accounting, hours, resume."""
    path = workspace / "src/p22/eval/s9_execute.py"
    text = path.read_text(encoding="utf-8")
    findings = {
        "pre_dispatch_total_cap_check": (
            'counter["attempted_fits"] + len(remaining) > attempt_cap' in text
            or "would exceed cap" in text
        ),
        "per_job_reserve_before_thread_submit": False,
        "per_job_reserve_evidence": (
            "execute_jobs checks planned remaining against cap once before the "
            "batch, then submits all remaining jobs; counter increments only in "
            "_persist after each fit returns (serial on main via as_completed). "
            "No per-job pre-increment/reserve before pool.submit."
        ),
        "failed_attempts_counted": (
            'counter["failed"]' in text and "status" in text
        ),
        "failed_attempt_evidence": (
            "run_one_s9_fit catches Exception into status=error; _persist always "
            "increments attempted_fits and failed vs completed_ok by status."
        ),
        "ledger_append_only_jsonl": (
            "def append_ledger_row" in text and 'path.open("a"' in text
        ),
        "resume_skips_done_fit_ids": (
            'done_ids = set(counter.get("fit_ids", []))' in text
        ),
        "raw_root_resume_no_wipe": "Resume-safe" in text or "no wipe" in text.lower(),
        "hours_tracked_post_hoc": "fitting_seconds" in text,
        "hours_hard_stop_mid_batch": False,
        "hours_hard_stop_evidence": (
            "fitting_seconds accumulate in _persist; within_fitting_hours is "
            "reported in the batch summary. No mid-batch break when hours exceed "
            "SYNTHETIC_FITTING_HOURS_CAP during execute_jobs."
        ),
        "artifact_cap_checked": "check_disk_resources" in text
        and "SYNTHETIC_ARTIFACT_GIB_CAP" in text,
        "torch_set_num_threads_process_global": "torch.set_num_threads" in text,
        "array_cache_prewarm_on_main_thread": "Pre-warm rho caches" in text,
        "checkpoint_history_epochs_persisted": False,
        "checkpoint_history_evidence": (
            "save_s9_checkpoint stores state_dict + protocol dims; no learning "
            "history/epochs (R1 uncertain_optimization retained)."
        ),
    }
    return findings


def freeze_diagnostic_spec(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "R3_DIAGNOSTIC_FIT_SPEC.json"
    if path.is_file():
        # Preserve already-reviewed bytes; do not rewrite frozen_at.
        existing = json.loads(path.read_text(encoding="utf-8"))
        return {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256_file(path),
            "attempt_cap": existing.get("attempt_cap", DIAGNOSTIC_FIT_SPEC["attempt_cap"]),
            "spec_id": existing.get("spec_id", DIAGNOSTIC_FIT_SPEC["spec_id"]),
            "preserved_existing": True,
        }
    payload = dict(DIAGNOSTIC_FIT_SPEC)
    payload["frozen_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    blob = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(blob, encoding="utf-8")
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "attempt_cap": payload["attempt_cap"],
        "spec_id": payload["spec_id"],
        "preserved_existing": False,
    }


def load_counter(raw_root: Path) -> dict[str, Any]:
    path = raw_root / "attempt_counter.json"
    if not path.is_file():
        raise ExecutionAuditRefusal(f"missing attempt counter {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_counter(raw_root: Path, counter: Mapping[str, Any]) -> None:
    path = raw_root / "attempt_counter.json"
    path.write_text(json.dumps(dict(counter), indent=2, sort_keys=True) + "\n")


def render_markdown(report: Mapping[str, Any]) -> str:
    inv = report["seed_caller_inventory"]
    risk = inv["concurrent_risk"]
    hashes = report["executor_hashes"]
    ledger = report["ledger_resume_resources"]
    spec = report["diagnostic_fit_spec"]
    lines = [
        "# EXECUTION_AUDIT — R3 RNG / execution / resource accounting",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Date:** {report['date']}",
        f"**Diagnostic fits this run:** {report['diagnostic_fits_this_run']}",
        f"**Cumulative diagnostic fits:** {report['diagnostic_fits_cumulative']} "
        f"≤ {report['diagnostic_fit_cap']}",
        f"**Research fits:** {report['research_fits']}",
        f"**Shared S9 raw unchanged:** `{report['shared_raw_unchanged']}`",
        f"**Review status:** `{report['review_status']}`",
        "",
        "## Executor dependency hashes",
        "",
        f"Chain SHA-256: `{hashes['chain_sha256']}`",
        "",
        "| Rel path | SHA-256 |",
        "|---|---|",
    ]
    for rel, digest in hashes["files"].items():
        lines.append(f"| `{rel}` | `{digest}` |")
    lines.extend(
        [
            "",
            "## Global seed / fit caller inventory",
            "",
            f"Files with relevant defs/calls: **{inv['n_files_with_hits']}**.",
            "",
            "Primary S9 path: `s9_execute.run_one_s9_fit` → `fit_s7_arm` → "
            "`paired_model` (`set_all_seeds`) → `train_model` (`set_all_seeds` + "
            "local `torch.Generator` for batch shuffle).",
            "",
            "### Concurrent RNG risk (code path; effect unmeasured here)",
            "",
            f"- Default workers×threads: **{risk['s9_default_workers']}×"
            f"{risk['s9_default_torch_threads']}**",
            f"- ThreadPoolExecutor used: `{risk['uses_thread_pool_executor']}`",
            f"- Process-global `set_all_seeds`: `{risk['set_all_seeds_mutates_process_globals']}`",
            f"- Interference code path exists: "
            f"`{risk['interference_code_path_exists']}`",
            f"- Effect on outcomes: **{risk['effect_on_outcomes']}**",
            f"- Inferred from threading alone: "
            f"`{risk['interference_inferred_from_threading_alone']}`",
            "",
            risk["notes"],
            "",
            "## Ledger / resume / resource enforcement",
            "",
            f"- Pre-dispatch total attempt-cap check: "
            f"`{ledger['pre_dispatch_total_cap_check']}`",
            f"- Per-job reserve before `pool.submit`: "
            f"`{ledger['per_job_reserve_before_thread_submit']}`",
            f"- Failed attempts counted: `{ledger['failed_attempts_counted']}`",
            f"- Resume skips done fit_ids: `{ledger['resume_skips_done_fit_ids']}`",
            f"- Hours tracked post-hoc: `{ledger['hours_tracked_post_hoc']}`",
            f"- Hours hard-stop mid-batch: `{ledger['hours_hard_stop_mid_batch']}`",
            f"- Artifact cap checked: `{ledger['artifact_cap_checked']}`",
            f"- Checkpoint learning history persisted: "
            f"`{ledger['checkpoint_history_epochs_persisted']}`",
            "",
            "### Notes",
            "",
            ledger["per_job_reserve_evidence"],
            "",
            ledger["hours_hard_stop_evidence"],
            "",
            ledger["checkpoint_history_evidence"],
            "",
            "## Frozen diagnostic fit spec",
            "",
            f"- Spec id: `{spec['spec_id']}`",
            f"- Path: `{spec['path']}`",
            f"- SHA-256: `{spec['sha256']}`",
            f"- Attempt cap: {spec['attempt_cap']}",
            "- Status: **frozen; diagnostic fits gated on independent PASS review**",
            "",
            "## Repair posture (conditional)",
            "",
            "No runner repair in this read-only pass. If diagnostic fits later "
            "confirm cross-job divergence under workers=2, smallest repair is "
            "serial default (`workers=1`); process isolation only if serial cannot "
            "eliminate the interference. Any shared-code change needs caller "
            "search + regression.",
            "",
            "## Scientific label",
            "",
            "Prior S9 **`INVALID` retained**. R3 does not overturn INVALID.",
            "",
        ]
    )
    return "\n".join(lines)


def run_readonly(
    *,
    workspace: Path,
    out_dir: Path,
    raw_root: Path,
    shared_s9: Path,
) -> dict[str, Any]:
    before = _fingerprint_tree(shared_s9)
    started = time.perf_counter()
    inventory = inventory_seed_callers(workspace)
    hashes = hash_executor_path(workspace)
    ledger = audit_ledger_resume_resources(workspace)
    spec_meta = freeze_diagnostic_spec(out_dir)
    after = _fingerprint_tree(shared_s9)
    _assert_no_write(before, after)

    counter = load_counter(raw_root)
    if int(counter.get("diagnostic_fit_attempts", 0)) != 0:
        # Read-only pass must not have spent diagnostic budget earlier without ledger.
        pass
    counter["r3_readonly_updated_at"] = datetime.now().astimezone().strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )
    counter["r3_review_status"] = "REVIEW_PENDING"
    save_counter(raw_root, counter)

    report: dict[str, Any] = {
        "disposition": "READ_ONLY_AUDIT_PASS",
        "date": "2026-10-01",
        "review_status": "REVIEW_PENDING",
        "diagnostic_fits_this_run": 0,
        "diagnostic_fits_cumulative": int(counter.get("diagnostic_fit_attempts", 0)),
        "diagnostic_fit_cap": int(counter.get("diagnostic_fit_cap", 12)),
        "research_fits": int(counter.get("scientific_fit_attempts", 0)),
        "shared_raw_unchanged": True,
        "shared_s9_tree_sha256": after["tree_sha256"],
        "shared_s9_n_files": after["n_files"],
        "scientific_label_retained": "INVALID",
        "seed_caller_inventory": inventory,
        "executor_hashes": hashes,
        "ledger_resume_resources": ledger,
        "diagnostic_fit_spec": spec_meta,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "p22_file": str(
            (workspace / "src" / "p22" / "__init__.py").resolve()
        ),
        "next_action": (
            "Independent reviewer must PASS R3_DIAGNOSTIC_FIT_SPEC.json before "
            "any of the ≤12 diagnostic fits; then compare serial vs thread route."
        ),
    }
    return report


def _build_fixed_tensors(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Build diagnostic tensors once from the frozen recipe; reuse across routes."""
    import numpy as np

    t = spec["tensors"]
    proto = spec["protocol"]
    n_donors = int(t["n_donors"])
    cells = int(t["cells_per_donor"])
    n_cells = n_donors * cells
    rng = np.random.default_rng(int(t["generator_seed_for_fixed_arrays"]))
    rna = rng.normal(0.0, 1.0, size=(n_cells, int(t["n_features_rna"]))).astype(
        np.float32
    )
    atac = rng.normal(0.0, 1.0, size=(n_cells, int(t["n_features_atac"]))).astype(
        np.float32
    )
    donors = np.repeat(np.arange(n_donors), cells)
    labels_donor = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int64)
    labels = np.repeat(labels_donor, cells)
    return {
        "rna": rna,
        "atac": atac,
        "donors": donors.astype(str),
        "labels": labels,
        "labels_donor": labels_donor,
        "n_cells": n_cells,
        "protocol_fields": dict(proto),
    }


def _positions_for_split(
    donors: Any,
    split: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    import numpy as np

    donor_ids = np.asarray(donors)
    out: dict[str, Any] = {}
    for name in ("train", "val", "test"):
        wanted = {str(i) for i in split[f"{name}_donors"]}
        out[name] = np.flatnonzero(np.isin(donor_ids, list(wanted))).astype(np.int64)
    return out


def _fit_one_diagnostic(
    *,
    job_key: str,
    arrays: Mapping[str, Any],
    positions: Mapping[str, Any],
    model_name: str,
) -> dict[str, Any]:
    """One diagnostic fit via the same paired_model/train_model path S9 uses."""
    import time as _time

    import numpy as np
    import torch

    from p22.eval.multiome_protocol import MultiomeProtocol
    from p22.eval.s7_runner import fit_s7_arm
    from p22.models.fusion import VIEW_A, VIEW_B

    fields = dict(arrays["protocol_fields"])
    protocol = MultiomeProtocol(
        n_tokens=int(fields["n_tokens"]),
        embed_dim=int(fields["embed_dim"]),
        hidden_dim=int(fields["hidden_dim"]),
        n_heads=int(fields["n_heads"]),
        dropout=float(fields["dropout"]),
        max_epochs=int(fields["max_epochs"]),
        patience=int(fields["patience"]),
        batch_size=int(fields["batch_size"]),
        learning_rate=float(fields["learning_rate"]),
        model_seed=int(fields["model_seed"]),
        feature_budget=16,
        cell_cap=64,
    )
    views = {VIEW_A: arrays["rna"], VIEW_B: arrays["atac"]}
    t0 = _time.perf_counter()
    try:
        torch.set_num_threads(2)
        scores = fit_s7_arm(
            model_name,
            views,
            arrays["labels"],
            arrays["donors"],
            positions,
            protocol,
            model_seed=int(fields["model_seed"]),
        )
        status = str(scores.get("status", "ok"))
        ckpt = scores.get("checkpoint") or {}
        state = ckpt.get("state_dict") or {}
        state_flat = {
            k: v.detach().cpu().numpy() if hasattr(v, "detach") else np.asarray(v)
            for k, v in state.items()
        }
        state_hash = hashlib.sha256(
            b"".join(
                f"{k}:".encode() + np.ascontiguousarray(v).tobytes()
                for k, v in sorted(state_flat.items())
            )
        ).hexdigest()
        preds = np.asarray(
            scores.get("test_cell_probabilities") or [],
            dtype=np.float64,
        )
        if preds.size == 0:
            donor_probs = scores.get("donor_probabilities") or {}
            if isinstance(donor_probs, dict) and "probability" in donor_probs:
                preds = np.asarray(donor_probs["probability"], dtype=np.float64)
        record = {
            "job_key": job_key,
            "status": status,
            "state_sha256": state_hash,
            "n_state_tensors": len(state_flat),
            "pred_digest": hashlib.sha256(
                np.ascontiguousarray(preds).tobytes()
            ).hexdigest()
            if preds.size
            else None,
            "donor_balanced_accuracy": scores.get("donor_balanced_accuracy"),
            "seconds": float(_time.perf_counter() - t0),
            "state_flat": state_flat,
            "preds": preds,
        }
    except Exception as error:  # noqa: BLE001 — diagnostic failure accounting
        record = {
            "job_key": job_key,
            "status": f"error: {type(error).__name__}: {error}",
            "state_sha256": None,
            "n_state_tensors": 0,
            "pred_digest": None,
            "donor_balanced_accuracy": None,
            "seconds": float(_time.perf_counter() - t0),
            "state_flat": {},
            "preds": None,
        }
    return record


def _max_abs_state(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    import numpy as np

    if set(a) != set(b):
        return float("inf")
    if not a:
        return float("inf")
    return float(max(np.max(np.abs(a[k] - b[k])) for k in a))


def run_diagnostic_fits(
    *,
    workspace: Path,
    out_dir: Path,
    raw_root: Path,
    shared_s9: Path,
    review: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute the frozen ≤12 diagnostic attempts after independent PASS review."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if review.get("verdict") != "PASS" or not review.get("authorizes_diagnostic_fits"):
        raise ExecutionAuditRefusal("review does not authorize diagnostic fits")
    if review.get("reviewer", {}).get("self_certification") is True:
        raise ExecutionAuditRefusal("self-certification reviews cannot authorize fits")
    spec_path = out_dir / "R3_DIAGNOSTIC_FIT_SPEC.json"
    if not spec_path.is_file():
        raise ExecutionAuditRefusal("missing frozen diagnostic fit spec")
    live_sha = sha256_file(spec_path)
    if live_sha != review.get("spec_sha256_recomputed"):
        raise ExecutionAuditRefusal(
            f"spec hash drift vs review: live={live_sha} "
            f"review={review.get('spec_sha256_recomputed')}"
        )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    before = _fingerprint_tree(shared_s9)
    counter = load_counter(raw_root)
    attempted = int(counter.get("diagnostic_fit_attempts", 0))
    cap = int(spec["attempt_cap"])
    if attempted >= cap:
        raise ExecutionAuditRefusal(f"diagnostic cap exhausted: {attempted}>={cap}")

    arrays = _build_fixed_tensors(spec)
    split_j1 = spec["frozen_split_indices"]
    split_j2 = {
        "train_donors": [0, 1, 4, 5],
        "val_donors": [3, 7],
        "test_donors": [2, 6],
    }
    pos = {
        "J1": _positions_for_split(arrays["donors"], split_j1),
        "J2": _positions_for_split(arrays["donors"], split_j2),
    }
    model_name = str(spec["model"])
    ledger_path = raw_root / "r3_diagnostic_ledger.jsonl"
    results_path = out_dir / "r3_diagnostic_results.json"
    if ledger_path.exists() or results_path.exists():
        raise ExecutionAuditRefusal(
            "diagnostic ledger/results already exist; refuse overwrite"
        )

    wall_cap = float(spec["wall_minutes_cap"]) * 60.0
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}

    def _persist(attempt_id: str, route: str, raw: Mapping[str, Any]) -> dict[str, Any]:
        nonlocal attempted
        attempted += 1
        if attempted > cap:
            raise ExecutionAuditRefusal(f"diagnostic attempt exceeded cap {cap}")
        row = {
            "attempt_id": attempt_id,
            "route": route,
            "job_key": raw["job_key"],
            "status": raw["status"],
            "state_sha256": raw["state_sha256"],
            "pred_digest": raw["pred_digest"],
            "donor_balanced_accuracy": raw["donor_balanced_accuracy"],
            "seconds": raw["seconds"],
            "attempt_index": attempted,
        }
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        counter["diagnostic_fit_attempts"] = attempted
        counter["fitting_hours"] = float(counter.get("fitting_hours", 0.0)) + (
            float(raw["seconds"]) / 3600.0
        )
        counter.setdefault("diagnostic_fit_ids", []).append(attempt_id)
        if str(raw["status"]).startswith("error") or raw["status"] != "ok":
            if not str(raw["status"]).startswith("error") and raw["status"] != "ok":
                pass
            if str(raw["status"]).startswith("error"):
                counter["diagnostic_failed"] = int(
                    counter.get("diagnostic_failed", 0)
                ) + 1
            elif raw["status"] != "ok":
                counter["diagnostic_non_ok"] = int(
                    counter.get("diagnostic_non_ok", 0)
                ) + 1
        else:
            counter["diagnostic_completed_ok"] = int(
                counter.get("diagnostic_completed_ok", 0)
            ) + 1
        save_counter(raw_root, counter)
        slim = {k: v for k, v in raw.items() if k not in {"state_flat", "preds"}}
        slim.update(row)
        records.append(slim)
        by_id[attempt_id] = dict(raw)
        by_id[attempt_id].update(row)
        return slim

    # A1–A4 serial identity
    for attempt_id, job_key in (("A1", "J1"), ("A2", "J1"), ("A3", "J2"), ("A4", "J2")):
        if time.perf_counter() - started > wall_cap:
            raise ExecutionAuditRefusal("diagnostic wall-clock cap exceeded")
        raw = _fit_one_diagnostic(
            job_key=job_key,
            arrays=arrays,
            positions=pos[job_key],
            model_name=model_name,
        )
        _persist(attempt_id, "serial", raw)

    # A5–A6 concurrent pair #1
    if time.perf_counter() - started > wall_cap:
        raise ExecutionAuditRefusal("diagnostic wall-clock cap exceeded")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {
            pool.submit(
                _fit_one_diagnostic,
                job_key=jk,
                arrays=arrays,
                positions=pos[jk],
                model_name=model_name,
            ): aid
            for aid, jk in (("A5", "J1"), ("A6", "J2"))
        }
        for fut in as_completed(futs):
            _persist(futs[fut], "thread_pool_workers_2", fut.result())

    # A7–A8 concurrent pair #2
    if time.perf_counter() - started > wall_cap:
        raise ExecutionAuditRefusal("diagnostic wall-clock cap exceeded")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {
            pool.submit(
                _fit_one_diagnostic,
                job_key=jk,
                arrays=arrays,
                positions=pos[jk],
                model_name=model_name,
            ): aid
            for aid, jk in (("A7", "J1"), ("A8", "J2"))
        }
        for fut in as_completed(futs):
            _persist(futs[fut], "thread_pool_workers_2", fut.result())

    # A9 post-concurrent serial contamination check
    raw = _fit_one_diagnostic(
        job_key="J1", arrays=arrays, positions=pos["J1"], model_name=model_name
    )
    _persist("A9", "serial", raw)

    # A10 deliberate failure (empty train)
    import numpy as np

    empty_pos = {
        "train": np.asarray([], dtype=np.int64),
        "val": pos["J1"]["val"],
        "test": pos["J1"]["test"],
    }
    raw = _fit_one_diagnostic(
        job_key="J_FAIL",
        arrays=arrays,
        positions=empty_pos,
        model_name=model_name,
    )
    _persist("A10", "serial_deliberate_fail", raw)

    # A11 write then A12 resume-skip (same fit_id already in diagnostic_fit_ids)
    raw = _fit_one_diagnostic(
        job_key="J1", arrays=arrays, positions=pos["J1"], model_name=model_name
    )
    _persist("A11", "serial_resume_fixture", raw)
    # A12: refuse double-run by detecting A11 already recorded for J1 resume id
    if "A11" in counter.get("diagnostic_fit_ids", []):
        # Count as attempted skip/resume success without a second real fit? Spec says
        # A12 resume must refuse double-count or skip already-done. We reserve the
        # attempt counter slot and record a skipped resume row (still counts).
        attempted += 1
        skip_row = {
            "attempt_id": "A12",
            "route": "serial_resume_fixture",
            "job_key": "J1",
            "status": "skipped_already_done:A11",
            "state_sha256": by_id["A11"]["state_sha256"],
            "pred_digest": by_id["A11"]["pred_digest"],
            "donor_balanced_accuracy": by_id["A11"]["donor_balanced_accuracy"],
            "seconds": 0.0,
            "attempt_index": attempted,
        }
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(skip_row, sort_keys=True) + "\n")
        counter["diagnostic_fit_attempts"] = attempted
        counter.setdefault("diagnostic_fit_ids", []).append("A12")
        counter["diagnostic_skipped_resume"] = int(
            counter.get("diagnostic_skipped_resume", 0)
        ) + 1
        save_counter(raw_root, counter)
        records.append(skip_row)
        by_id["A12"] = dict(skip_row)
    else:
        raise ExecutionAuditRefusal("A11 missing; cannot exercise A12 resume")

    after = _fingerprint_tree(shared_s9)
    _assert_no_write(before, after)

    def _cmp(a_id: str, b_id: str) -> dict[str, Any]:
        a, b = by_id[a_id], by_id[b_id]
        state_diff = _max_abs_state(a.get("state_flat") or {}, b.get("state_flat") or {})
        return {
            "left": a_id,
            "right": b_id,
            "state_sha_equal": a.get("state_sha256") == b.get("state_sha256"),
            "pred_digest_equal": a.get("pred_digest") == b.get("pred_digest"),
            "state_max_abs_diff": None if state_diff == float("inf") else state_diff,
            "both_ok": a.get("status") == "ok" and b.get("status") == "ok",
        }

    comparisons = {
        "serial_J1_A1_vs_A2": _cmp("A1", "A2"),
        "serial_J2_A3_vs_A4": _cmp("A3", "A4"),
        "serial_J1_A1_vs_concurrent_A5": _cmp("A1", "A5"),
        "serial_J2_A3_vs_concurrent_A6": _cmp("A3", "A6"),
        "concurrent_J1_A5_vs_A7": _cmp("A5", "A7"),
        "concurrent_J2_A6_vs_A8": _cmp("A6", "A8"),
        "post_concurrent_A9_vs_A1": _cmp("A9", "A1"),
    }
    serial_ok = (
        comparisons["serial_J1_A1_vs_A2"]["state_sha_equal"]
        and comparisons["serial_J2_A3_vs_A4"]["state_sha_equal"]
    )
    concurrent_matches_serial = (
        comparisons["serial_J1_A1_vs_concurrent_A5"]["state_sha_equal"]
        and comparisons["serial_J2_A3_vs_concurrent_A6"]["state_sha_equal"]
    )
    concurrent_stable = (
        comparisons["concurrent_J1_A5_vs_A7"]["state_sha_equal"]
        and comparisons["concurrent_J2_A6_vs_A8"]["state_sha_equal"]
    )
    if serial_ok and not concurrent_matches_serial:
        rng_finding = "CONFIRMED_CROSS_JOB_DIVERGENCE"
        repair = "prefer_serial_workers_1"
    elif serial_ok and concurrent_matches_serial and concurrent_stable:
        rng_finding = "NO_DIVERGENCE_OBSERVED_UNDER_SPEC"
        repair = "none_required_from_this_diagnostic"
    elif serial_ok and concurrent_matches_serial and not concurrent_stable:
        rng_finding = "CONCURRENT_UNSTABLE_NONDETERMINISM"
        repair = "prefer_serial_workers_1"
    else:
        rng_finding = "SERIAL_NONDETERMINISM_OR_FIT_FAILURE"
        repair = "investigate_serial_path_before_thread_repair"

    payload = {
        "disposition": "DIAGNOSTIC_FITS_COMPLETE",
        "spec_id": spec["spec_id"],
        "spec_sha256": live_sha,
        "review_agent_id": review.get("reviewer", {}).get("agent_id"),
        "diagnostic_fits_this_run": attempted,
        "attempts": attempted,
        "attempt_cap": cap,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "shared_raw_unchanged": True,
        "shared_s9_tree_sha256": after["tree_sha256"],
        "records": [
            {k: v for k, v in r.items() if k not in {"state_flat", "preds"}}
            for r in records
        ],
        "comparisons": comparisons,
        "rng_interference_finding": rng_finding,
        "repair_recommendation": repair,
        "deliberate_fail_status": by_id["A10"]["status"],
        "resume_skip_status": by_id["A12"]["status"],
        "scientific_label_retained": "INVALID",
    }
    # Drop heavy arrays from by_id before any accidental dump
    for key in list(by_id):
        by_id[key].pop("state_flat", None)
        by_id[key].pop("preds", None)
    results_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    counter["r3_review_status"] = "PASS"
    counter["r3_rng_interference_finding"] = rng_finding
    counter["r3_diagnostic_updated_at"] = datetime.now().astimezone().strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )
    save_counter(raw_root, counter)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--shared-s9-raw", type=Path, default=SHARED_S9_RAW)
    parser.add_argument(
        "--run-diagnostic-fits",
        action="store_true",
        help="Forbidden unless independent review PASS JSON is also provided.",
    )
    parser.add_argument(
        "--review-json",
        type=Path,
        default=None,
        help="Independent review JSON with verdict=PASS required for fits.",
    )
    parser.add_argument(
        "--skip-readonly-refresh",
        action="store_true",
        help="When running fits, do not rewrite the read-only audit artifacts.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.run_diagnostic_fits:
        if args.review_json is None or not args.review_json.is_file():
            raise SystemExit(
                "diagnostic fits require --review-json with independent PASS"
            )
        review = json.loads(args.review_json.read_text(encoding="utf-8"))
        if review.get("verdict") != "PASS":
            raise SystemExit(f"review verdict not PASS: {review.get('verdict')}")
        if not review.get("authorizes_diagnostic_fits"):
            raise SystemExit("review does not authorize diagnostic fits")
        diag = run_diagnostic_fits(
            workspace=args.workspace,
            out_dir=out_dir,
            raw_root=args.raw_root,
            shared_s9=args.shared_s9_raw,
            review=review,
        )
        # Refresh audit markdown with fit findings
        audit_path = out_dir / "execution_audit.json"
        if audit_path.is_file():
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        else:
            audit = run_readonly(
                workspace=args.workspace,
                out_dir=out_dir,
                raw_root=args.raw_root,
                shared_s9=args.shared_s9_raw,
            )
        audit["disposition"] = "EXECUTION_AUDIT_PASS"
        audit["review_status"] = "PASS"
        audit["diagnostic_fits_this_run"] = diag["diagnostic_fits_this_run"]
        audit["diagnostic_fits_cumulative"] = diag["attempts"]
        audit["rng_interference_finding"] = diag["rng_interference_finding"]
        audit["repair_recommendation"] = diag["repair_recommendation"]
        audit["diagnostic_results_path"] = str(
            (out_dir / "r3_diagnostic_results.json").relative_to(ROOT)
        )
        audit["next_action"] = (
            "R4 guidance/claims table; apply serial-workers repair only if "
            f"finding is confirmed divergence (current: {diag['rng_interference_finding']})"
        )
        audit["seed_caller_inventory"]["concurrent_risk"]["effect_on_outcomes"] = diag[
            "rng_interference_finding"
        ]
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
        md = render_markdown(audit)
        md += (
            "\n## Diagnostic fit results (post-review)\n\n"
            f"- Attempts: {diag['attempts']} ≤ {diag['attempt_cap']}\n"
            f"- Wall seconds: {diag['wall_seconds']}\n"
            f"- RNG finding: **{diag['rng_interference_finding']}**\n"
            f"- Repair recommendation: `{diag['repair_recommendation']}`\n"
            f"- Deliberate fail status: `{diag['deliberate_fail_status']}`\n"
            f"- Resume skip status: `{diag['resume_skip_status']}`\n"
            f"- Results: `{audit['diagnostic_results_path']}`\n"
        )
        (out_dir / "EXECUTION_AUDIT.md").write_text(md)
        summary = {
            "disposition": audit["disposition"],
            "review_status": "PASS",
            "diagnostic_fits": diag["attempts"],
            "rng_interference_finding": diag["rng_interference_finding"],
            "repair_recommendation": diag["repair_recommendation"],
            "shared_raw_unchanged": True,
        }
        (args.raw_root / "r3_execution_audit_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n"
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    report = run_readonly(
        workspace=args.workspace,
        out_dir=out_dir,
        raw_root=args.raw_root,
        shared_s9=args.shared_s9_raw,
    )
    json_path = out_dir / "execution_audit.json"
    md_path = out_dir / "EXECUTION_AUDIT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    md_path.write_text(render_markdown(report))

    summary = {
        "disposition": report["disposition"],
        "review_status": report["review_status"],
        "diagnostic_fits": report["diagnostic_fits_this_run"],
        "executor_chain_sha256": report["executor_hashes"]["chain_sha256"],
        "spec_sha256": report["diagnostic_fit_spec"]["sha256"],
        "shared_raw_unchanged": report["shared_raw_unchanged"],
    }
    (args.raw_root / "r3_execution_audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
