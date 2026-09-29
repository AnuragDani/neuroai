"""S7 stage orchestrator: smoke → screen → pairing-PC → confirmation → handoff.

Wires the frozen evaluators and single-fit runner under runbook stage gates.
Does not search scenarios, seeds or hyperparameters. Confirmation fits run only
when screen is ``CA_FAVOURED_SCREEN`` and pairing-PC is ``PC_PASS``. Scientific
negatives and incompletes are complete handoffs; biological primary stays
``B_NULL``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_confirm_exec import run_confirmation_evaluation
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
from p22.eval.s7_pairing_exec import run_pairing_pc_diagnostic
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

STAGE_STATE_NAME = "stage_state.json"

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


def empty_stage_state() -> dict[str, Any]:
    """Fresh persisted stage labels/payloads (no evaluation yet)."""
    return {
        "smoke_complete": False,
        "screen_label": None,
        "pc_label": None,
        "confirm_label": None,
        "screen": None,
        "pairing_pc": None,
        "confirmation": None,
        "confirmation_eligible": False,
        "handoff_paths": None,
        "last_action": None,
        "last_reason": None,
    }


def stage_state_path(output_root: Path | str) -> Path:
    return Path(output_root) / STAGE_STATE_NAME


def load_stage_state(output_root: Path | str) -> dict[str, Any]:
    """Load ``stage_state.json`` or return an empty state."""
    path = stage_state_path(output_root)
    if not path.exists():
        return empty_stage_state()
    raw = json.loads(path.read_text(encoding="utf-8"))
    state = empty_stage_state()
    state.update(raw)
    return state


def save_stage_state(output_root: Path | str, state: Mapping[str, Any]) -> Path:
    """Persist stage labels so resume does not re-fit completed stages."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    path = stage_state_path(root)
    path.write_text(
        json.dumps(dict(state), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def sync_smoke_complete(state: Mapping[str, Any], ledger: S7FitLedger) -> dict[str, Any]:
    """Refresh smoke_complete from the immutable ledger (source of truth)."""
    out = dict(state)
    out["smoke_complete"] = smoke_is_complete(ledger)
    return out


def execute_next_stage(
    *,
    ledger: S7FitLedger,
    folds_by_index: Mapping[int, FoldArrays],
    positions_by_fold: Mapping[int, Mapping[str, np.ndarray]],
    checkpoint_dir: Path | str,
    output_root: Path | str,
    result_dir: Path | str,
    cell_ids_by_fold: Mapping[int, np.ndarray] | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    feature_seed: int | None = None,
    provenance: Mapping[str, Any] | None = None,
    check_disk: bool = True,
    fit_fn: Callable[..., dict[str, Any]] | None = None,
    pairing_fn: Callable[..., dict[str, Any]] | None = None,
    confirmation_eval_fn: Callable[..., dict[str, Any]] | None = None,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Advance exactly one runbook stage under ``decide_next_action``.

    Fit stages call ``run_fit_jobs``; pairing-PC and confirmation evaluation use
    the frozen executors (injectable for tests). Writes ``stage_state.json`` and,
    on handoff, ``S7_RESULT.md``. Never retunes or searches settings.
    """
    root = Path(output_root)
    ckpt = Path(checkpoint_dir)
    current = sync_smoke_complete(
        empty_stage_state() if state is None else dict(state),
        ledger,
    )
    decision = decide_next_action(
        smoke_complete=bool(current["smoke_complete"]),
        screen_label=current.get("screen_label"),
        pc_label=current.get("pc_label"),
        confirm_label=current.get("confirm_label"),
        run_invalid=ledger.is_invalid,
    )
    action = str(decision["action"])
    detail: dict[str, Any] = {"decision": decision}

    if action == ACTION_STOP_HARD:
        current["last_action"] = action
        current["last_reason"] = decision.get("reason")
        save_stage_state(root, current)
        return {
            "action": action,
            "state": current,
            "detail": detail,
            "done": True,
        }

    if action == ACTION_RUN_SMOKE:
        detail["fit"] = run_fit_jobs(
            planned_stage_jobs("smoke"),
            folds_by_index=folds_by_index,
            positions_by_fold=positions_by_fold,
            ledger=ledger,
            checkpoint_dir=ckpt,
            output_root=root,
            cell_ids_by_fold=cell_ids_by_fold,
            protocol=protocol,
            feature_seed=feature_seed,
            check_disk=check_disk,
            fit_fn=fit_fn,
        )
        current["smoke_complete"] = smoke_is_complete(ledger)

    elif action == ACTION_RUN_SCREEN:
        detail["fit"] = run_fit_jobs(
            planned_stage_jobs("screen"),
            folds_by_index=folds_by_index,
            positions_by_fold=positions_by_fold,
            ledger=ledger,
            checkpoint_dir=ckpt,
            output_root=root,
            cell_ids_by_fold=cell_ids_by_fold,
            protocol=protocol,
            feature_seed=feature_seed,
            check_disk=check_disk,
            fit_fn=fit_fn,
        )
        screen = evaluate_screen(ledger_records_for_stage(ledger, "screen"))
        current["screen"] = screen
        current["screen_label"] = screen.get("screen_label")

    elif action == ACTION_RUN_PAIRING_PC:
        worker = pairing_fn or run_pairing_pc_diagnostic
        pairing = worker(
            folds_by_index=folds_by_index,
            positions_by_fold=positions_by_fold,
            ledger_records=list(ledger.records.values()),
            cell_ids_by_fold=cell_ids_by_fold,
            feature_seed=feature_seed,
            protocol=protocol,
        )
        detail["pairing_pc"] = pairing
        current["pairing_pc"] = pairing
        current["pc_label"] = pairing.get("pc_label")

    elif action == ACTION_RUN_CONFIRMATION:
        detail["fit"] = run_fit_jobs(
            planned_stage_jobs("confirm"),
            folds_by_index=folds_by_index,
            positions_by_fold=positions_by_fold,
            ledger=ledger,
            checkpoint_dir=ckpt,
            output_root=root,
            cell_ids_by_fold=cell_ids_by_fold,
            protocol=protocol,
            feature_seed=feature_seed,
            check_disk=check_disk,
            fit_fn=fit_fn,
        )
        eval_fn = confirmation_eval_fn or run_confirmation_evaluation
        confirmation = eval_fn(
            ledger_records_for_stage(ledger, "confirm"),
            eligible=True,
        )
        detail["confirmation"] = confirmation
        current["confirmation"] = confirmation
        current["confirm_label"] = confirmation.get("confirm_label")
        current["confirmation_eligible"] = True

    elif action == ACTION_WRITE_HANDOFF:
        stages = assemble_stage_results(
            screen_records=ledger_records_for_stage(ledger, "screen"),
            pairing_pc=current.get("pairing_pc"),
            confirmation=current.get("confirmation"),
            confirmation_eligible=decision.get("confirmation_eligible"),
        )
        # Prefer freshly assembled labels; keep prior payloads if assemble rebuilds.
        current["screen"] = stages.get("screen")
        current["screen_label"] = stages.get("screen_label")
        current["pairing_pc"] = stages.get("pairing_pc")
        current["pc_label"] = stages.get("pc_label")
        current["confirmation"] = stages.get("confirmation")
        current["confirm_label"] = stages.get("confirm_label")
        current["confirmation_eligible"] = stages.get("confirmation_eligible")
        resources = None
        post_path = root / "resources_post_fit.json"
        if post_path.exists():
            resources = json.loads(post_path.read_text(encoding="utf-8"))
        handoff = write_pipeline_handoff(
            result_dir=result_dir,
            stages=stages,
            provenance=provenance,
            resources=resources,
            ledger_path=ledger.ledger_path,
            checkpoint_root=ckpt,
            run_invalid=ledger.is_invalid,
            run_invalid_reason=ledger.invalid_reason,
        )
        detail["handoff"] = handoff
        current["handoff_paths"] = handoff.get("paths")
    else:
        raise ValueError(f"unknown pipeline action {action!r}")

    current["last_action"] = action
    current["last_reason"] = decision.get("reason")
    save_stage_state(root, current)
    return {
        "action": action,
        "state": current,
        "detail": detail,
        "done": action in {ACTION_WRITE_HANDOFF, ACTION_STOP_HARD},
    }


def run_until_handoff(
    *,
    ledger: S7FitLedger,
    folds_by_index: Mapping[int, FoldArrays],
    positions_by_fold: Mapping[int, Mapping[str, np.ndarray]],
    checkpoint_dir: Path | str,
    output_root: Path | str,
    result_dir: Path | str,
    cell_ids_by_fold: Mapping[int, np.ndarray] | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    feature_seed: int | None = None,
    provenance: Mapping[str, Any] | None = None,
    check_disk: bool = True,
    fit_fn: Callable[..., dict[str, Any]] | None = None,
    pairing_fn: Callable[..., dict[str, Any]] | None = None,
    confirmation_eval_fn: Callable[..., dict[str, Any]] | None = None,
    max_steps: int = 8,
) -> dict[str, Any]:
    """Drive ``execute_next_stage`` until handoff or ``max_steps`` (safety cap).

    ``max_steps`` defaults to 8 (> smoke/screen/PC/confirm/handoff) so a stuck
    loop cannot spin forever; incomplete coverage is still an honest handoff.
    """
    state = load_stage_state(output_root)
    steps: list[dict[str, Any]] = []
    for _ in range(int(max_steps)):
        step = execute_next_stage(
            ledger=ledger,
            folds_by_index=folds_by_index,
            positions_by_fold=positions_by_fold,
            checkpoint_dir=checkpoint_dir,
            output_root=output_root,
            result_dir=result_dir,
            cell_ids_by_fold=cell_ids_by_fold,
            protocol=protocol,
            feature_seed=feature_seed,
            provenance=provenance,
            check_disk=check_disk,
            fit_fn=fit_fn,
            pairing_fn=pairing_fn,
            confirmation_eval_fn=confirmation_eval_fn,
            state=state,
        )
        steps.append(
            {
                "action": step["action"],
                "done": step["done"],
                "reason": step["state"].get("last_reason"),
            }
        )
        state = step["state"]
        if step["done"]:
            return {
                "done": True,
                "n_steps": len(steps),
                "steps": steps,
                "state": state,
                "final_action": step["action"],
            }
    return {
        "done": False,
        "n_steps": len(steps),
        "steps": steps,
        "state": state,
        "final_action": None if not steps else steps[-1]["action"],
        "reason": f"max_steps={max_steps} reached without handoff",
    }
