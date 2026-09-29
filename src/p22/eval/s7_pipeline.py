"""S7 stage orchestrator: smoke → screen → pairing-PC → confirmation → handoff.

Wires the frozen evaluators and single-fit runner under runbook stage gates.
Does not search scenarios, seeds or hyperparameters. Confirmation fits run only
when screen is ``CA_FAVOURED_SCREEN`` and pairing-PC is ``PC_PASS``. Scientific
negatives and incompletes are complete handoffs; biological primary stays
``B_NULL``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_confirmation import (
    CONFIRM_SKIPPED,
    enumerate_confirmation_jobs,
    evaluate_confirmation,
)
from p22.eval.s7_handoff import (
    build_s7_result_payload,
    finalize_scientific_label,
    write_s7_result,
)
from p22.eval.s7_ledger import (
    S7FitLedger,
    enumerate_screen_jobs,
)
from p22.eval.s7_pairing import PC_PASS
from p22.eval.s7_runner import (
    S7_PROTOCOL,
    check_disk_resources,
    enumerate_smoke_jobs,
    plant_and_fit_job,
    record_completed_fit,
    remaining_fit_budget,
    write_resource_snapshot,
)
from p22.eval.s7_screen import SCREEN_CA_FAVOURED, evaluate_screen

ACTION_RUN_SMOKE = "run_smoke"
ACTION_RUN_SCREEN = "run_screen"
ACTION_RUN_PAIRING_PC = "run_pairing_pc"
ACTION_RUN_CONFIRMATION = "run_confirmation"
ACTION_WRITE_HANDOFF = "write_handoff"
ACTION_STOP_HARD = "stop_hard"

ALLOWED_ACTIONS = frozenset(
    {
        ACTION_RUN_SMOKE,
        ACTION_RUN_SCREEN,
        ACTION_RUN_PAIRING_PC,
        ACTION_RUN_CONFIRMATION,
        ACTION_WRITE_HANDOFF,
        ACTION_STOP_HARD,
    }
)


def decide_next_action(
    *,
    smoke_complete: bool,
    screen_label: str | None,
    pc_label: str | None,
    confirm_label: str | None,
    run_invalid: bool = False,
) -> dict[str, Any]:
    """Pure stage policy: one next action under frozen runbook gates.

    Confirmation is required only after ``CA_FAVOURED_SCREEN`` + ``PC_PASS``.
    Screen/PC failures still allow a complete handoff with confirmation skipped.
    Pairing-PC may run after a non-favourable screen as a retained-checkpoint
    diagnostic (no new confirmation fits).
    """
    if run_invalid:
        if confirm_label is None:
            return {
                "action": ACTION_WRITE_HANDOFF,
                "reason": "run invalid; write handoff without further fits",
                "confirmation_eligible": False,
            }
        return {
            "action": ACTION_WRITE_HANDOFF,
            "reason": "run invalid; handoff already stage-labeled",
            "confirmation_eligible": False,
        }

    if not smoke_complete:
        return {
            "action": ACTION_RUN_SMOKE,
            "reason": "smoke fits not complete",
            "confirmation_eligible": False,
        }

    if screen_label is None:
        return {
            "action": ACTION_RUN_SCREEN,
            "reason": "screen not evaluated",
            "confirmation_eligible": False,
        }

    if pc_label is None:
        return {
            "action": ACTION_RUN_PAIRING_PC,
            "reason": "pairing-PC not evaluated (diagnostic allowed after any complete screen)",
            "confirmation_eligible": False,
        }

    confirmation_eligible = (
        screen_label == SCREEN_CA_FAVOURED and pc_label == PC_PASS
    )

    if confirmation_eligible and confirm_label is None:
        return {
            "action": ACTION_RUN_CONFIRMATION,
            "reason": "screen+PC eligible; confirmation required",
            "confirmation_eligible": True,
        }

    if not confirmation_eligible and confirm_label is None:
        return {
            "action": ACTION_WRITE_HANDOFF,
            "reason": "screen/PC not eligible; skip confirmation and write handoff",
            "confirmation_eligible": False,
        }

    return {
        "action": ACTION_WRITE_HANDOFF,
        "reason": "all required stages resolved; write handoff",
        "confirmation_eligible": confirmation_eligible,
    }


def pending_jobs(
    jobs: Sequence[Mapping[str, Any]],
    ledger: S7FitLedger,
) -> list[dict[str, Any]]:
    """Return predeclared jobs whose fit_id is not yet in the immutable ledger."""
    done = ledger.completed_ids
    return [dict(job) for job in jobs if str(job["fit_id"]) not in done]


def smoke_is_complete(ledger: S7FitLedger) -> bool:
    """True when every predeclared smoke fit_id is present (any status)."""
    expected = {job["fit_id"] for job in enumerate_smoke_jobs()}
    return expected.issubset(ledger.completed_ids)


def skipped_confirmation_result() -> dict[str, Any]:
    """Confirmation payload when screen/PC do not authorize new fits."""
    return evaluate_confirmation([], eligible=False)


def run_fit_jobs(
    jobs: Sequence[Mapping[str, Any]],
    *,
    folds_by_index: Mapping[int, FoldArrays],
    positions_by_fold: Mapping[int, Mapping[str, np.ndarray]],
    ledger: S7FitLedger,
    checkpoint_dir: Path | str,
    output_root: Path | str,
    cell_ids_by_fold: Mapping[int, np.ndarray] | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    feature_seed: int | None = None,
    check_disk: bool = True,
    fit_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute pending jobs one-at-a-time; record into ledger; respect caps.

    Skips fit_ids already present. Refuses to start when disk/artifact gates
    fail. Does not retune on errors — records status and continues so coverage
    evaluation can label incomplete/invalid honestly.
    """
    root = Path(output_root)
    ckpt = Path(checkpoint_dir)
    resources: dict[str, Any] | None = None
    if check_disk:
        resources = check_disk_resources(output_root=root)
        write_resource_snapshot(root / "resources_pre_fit.json", resources)

    todo = pending_jobs(jobs, ledger)
    recorded: list[dict[str, Any]] = []
    skipped = len(jobs) - len(todo)
    worker = fit_fn or plant_and_fit_job

    for job in todo:
        if ledger.remaining_budget() <= 0:
            break
        fold_idx = int(job["fold"])
        if fold_idx not in folds_by_index:
            raise KeyError(f"missing fold arrays for fold {fold_idx}")
        if fold_idx not in positions_by_fold:
            raise KeyError(f"missing positions for fold {fold_idx}")
        cell_ids = None
        if cell_ids_by_fold is not None:
            cell_ids = cell_ids_by_fold.get(fold_idx)
        record = worker(
            folds_by_index[fold_idx],
            job,
            positions_by_fold[fold_idx],
            cell_ids=cell_ids,
            protocol=protocol,
            feature_seed=feature_seed,
        )
        written = record_completed_fit(ledger, record, checkpoint_dir=ckpt)
        recorded.append(written)

    if check_disk:
        post = check_disk_resources(output_root=root)
        write_resource_snapshot(root / "resources_post_fit.json", post)
        resources = post

    return {
        "n_requested": len(jobs),
        "n_pending": len(todo),
        "n_skipped_completed": skipped,
        "n_recorded": len(recorded),
        "n_remaining_pending": len(pending_jobs(jobs, ledger)),
        "budget": remaining_fit_budget(ledger),
        "resources": resources,
        "records": recorded,
    }


def ledger_records_for_stage(
    ledger: S7FitLedger,
    stage: str,
) -> list[dict[str, Any]]:
    """Collect ledger rows for one stage name (smoke/screen/confirm)."""
    return [
        dict(row)
        for row in ledger.records.values()
        if str(row.get("stage")) == stage
    ]


def assemble_stage_results(
    *,
    screen_records: Sequence[Mapping[str, Any]],
    pairing_pc: Mapping[str, Any] | None,
    confirmation: Mapping[str, Any] | None,
    confirmation_eligible: bool | None = None,
) -> dict[str, Any]:
    """Evaluate screen and attach pairing/confirmation payloads for handoff.

    When confirmation is omitted and not eligible, inserts CONFIRM_SKIPPED.
    When eligible but confirmation is missing, leaves confirm_label None so
    finalize maps to INCOMPLETE.
    """
    screen = evaluate_screen(screen_records)
    pc = dict(pairing_pc) if pairing_pc is not None else None
    eligible = (
        bool(confirmation_eligible)
        if confirmation_eligible is not None
        else (
            screen.get("screen_label") == SCREEN_CA_FAVOURED
            and pc is not None
            and pc.get("pc_label") == PC_PASS
        )
    )
    if confirmation is not None:
        confirm = dict(confirmation)
    elif not eligible:
        confirm = skipped_confirmation_result()
    else:
        confirm = None

    return {
        "screen": screen,
        "pairing_pc": pc,
        "confirmation": confirm,
        "confirmation_eligible": eligible,
        "screen_label": screen.get("screen_label"),
        "pc_label": None if pc is None else pc.get("pc_label"),
        "confirm_label": None if confirm is None else confirm.get("confirm_label"),
    }


def write_pipeline_handoff(
    *,
    result_dir: Path | str,
    stages: Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    ledger_path: str | Path | None = None,
    checkpoint_root: str | Path | None = None,
    run_invalid: bool = False,
    run_invalid_reason: str | None = None,
) -> dict[str, Any]:
    """Finalize scientific label and write ``S7_RESULT.md`` (+ JSON sidecar)."""
    finalize = finalize_scientific_label(
        screen_label=stages.get("screen_label"),
        pc_label=stages.get("pc_label"),
        confirm_label=stages.get("confirm_label"),
        run_invalid=run_invalid,
        run_invalid_reason=run_invalid_reason,
    )
    payload = build_s7_result_payload(
        finalize=finalize,
        provenance=provenance,
        screen=stages.get("screen"),
        pairing_pc=stages.get("pairing_pc"),
        confirmation=stages.get("confirmation"),
        resources=resources,
        ledger_path=None if ledger_path is None else str(ledger_path),
        checkpoint_root=None if checkpoint_root is None else str(checkpoint_root),
    )
    paths = write_s7_result(result_dir, payload)
    return {
        "finalize": finalize,
        "payload": payload,
        "paths": {key: str(value) for key, value in paths.items()},
    }


def planned_stage_jobs(stage: str) -> list[dict[str, Any]]:
    """Enumerate the frozen job list for a fit stage."""
    if stage == "smoke":
        return enumerate_smoke_jobs()
    if stage == "screen":
        return enumerate_screen_jobs()
    if stage == "confirm":
        return enumerate_confirmation_jobs()
    raise ValueError(f"unknown fit stage {stage!r}; expected smoke/screen/confirm")
