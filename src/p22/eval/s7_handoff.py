"""S7 exit handoff: final scientific label and S7_RESULT.md writer.

Combines screen / pairing-PC / confirmation stage outcomes into the runbook
labels without fitting models or editing canonical gates. Confirmation is
required when screen+PC make it eligible; skipped confirmation after a failed
screen/PC is a complete negative, not incomplete. Biological power stays
POWER_UNESTABLISHED; finished primary remains B_NULL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from p22.eval.s7_confirmation import (
    CONFIRM_INCOMPLETE,
    CONFIRM_NEGATIVE,
    CONFIRM_RELIABLE,
    CONFIRM_SKIPPED,
)
from p22.eval.s7_pairing import (
    PC_FAIL,
    PC_IDENTITY_FAIL,
    PC_INCOMPLETE,
    PC_PASS,
)
from p22.eval.s7_screen import (
    SCREEN_CA_FAVOURED,
    SCREEN_INCOMPLETE,
    SCREEN_INVALID,
    SCREEN_NEGATIVE,
)

# Runbook exit labels (EXECUTION_RUNBOOK.md Exit and handoff).
LABEL_CA_FAVOURED_CONTROL = "CA_FAVOURED_CONTROL"
LABEL_CONTROL_NEGATIVE = "CONTROL_NEGATIVE"
LABEL_INVALID = "INVALID"
LABEL_INCOMPLETE = "INCOMPLETE"

BIOLOGICAL_POWER = "POWER_UNESTABLISHED"
FINISHED_PRIMARY = "B_NULL"
STUDY_STATUS = "STUDY_PARTIAL"

ALLOWED_LABELS = frozenset(
    {
        LABEL_CA_FAVOURED_CONTROL,
        LABEL_CONTROL_NEGATIVE,
        LABEL_INVALID,
        LABEL_INCOMPLETE,
    }
)


def finalize_scientific_label(
    *,
    screen_label: str | None,
    pc_label: str | None,
    confirm_label: str | None,
    run_invalid: bool = False,
    run_invalid_reason: str | None = None,
) -> dict[str, Any]:
    """Map stage labels to one runbook scientific label.

    ``CA_FAVOURED_CONTROL`` requires screen ``CA_FAVOURED_SCREEN``, ``PC_PASS``,
    and ``CONFIRM_RELIABLE``. Eligible confirmation that was not run or is
    incomplete is ``INCOMPLETE``. Screen/PC failures with confirmation
    ``CONFIRM_SKIPPED`` are complete negatives (or invalid design), never
    favourable.
    """
    if run_invalid:
        return {
            "scientific_label": LABEL_INVALID,
            "reason": run_invalid_reason or "run marked invalid",
            "eligible_for_confirmation": False,
            "confirmation_required": False,
            "biological_power": BIOLOGICAL_POWER,
            "finished_primary": FINISHED_PRIMARY,
            "study": STUDY_STATUS,
            "stages": {
                "screen": screen_label,
                "pairing_pc": pc_label,
                "confirmation": confirm_label,
            },
        }

    screen = screen_label
    pc = pc_label
    confirm = confirm_label

    if screen is None or screen == SCREEN_INCOMPLETE:
        return _pack(
            LABEL_INCOMPLETE,
            "screen incomplete or missing",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=False,
            confirm_required=False,
        )

    if screen == SCREEN_INVALID:
        return _pack(
            LABEL_INVALID,
            "null/marginal control design failure",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=False,
            confirm_required=False,
        )

    if screen == SCREEN_NEGATIVE:
        # Retained-checkpoint PC diagnostics may finish without new fits.
        if pc == PC_INCOMPLETE:
            return _pack(
                LABEL_INCOMPLETE,
                "pairing-PC diagnostic incomplete after screen negative",
                screen=screen,
                pc=pc,
                confirm=confirm,
                eligible=False,
                confirm_required=False,
            )
        return _pack(
            LABEL_CONTROL_NEGATIVE,
            "screen not CA_FAVOURED at fixed rho=1",
            screen=screen,
            pc=pc,
            confirm=confirm or CONFIRM_SKIPPED,
            eligible=False,
            confirm_required=False,
        )

    if screen != SCREEN_CA_FAVOURED:
        return _pack(
            LABEL_INVALID,
            f"unrecognised screen_label {screen!r}",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=False,
            confirm_required=False,
        )

    # Screen favoured: pairing-PC required before confirmation.
    if pc is None or pc == PC_INCOMPLETE:
        return _pack(
            LABEL_INCOMPLETE,
            "pairing-PC incomplete or missing after CA_FAVOURED_SCREEN",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=False,
            confirm_required=True,
        )

    if pc in {PC_FAIL, PC_IDENTITY_FAIL}:
        return _pack(
            LABEL_CONTROL_NEGATIVE,
            "pairing-PC failed after CA_FAVOURED_SCREEN",
            screen=screen,
            pc=pc,
            confirm=confirm or CONFIRM_SKIPPED,
            eligible=False,
            confirm_required=False,
        )

    if pc != PC_PASS:
        return _pack(
            LABEL_INVALID,
            f"unrecognised pc_label {pc!r}",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=False,
            confirm_required=False,
        )

    # PC_PASS: confirmation is required (eligible).
    if confirm is None or confirm == CONFIRM_INCOMPLETE:
        return _pack(
            LABEL_INCOMPLETE,
            "confirmation incomplete or missing after PC_PASS",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=True,
            confirm_required=True,
        )

    if confirm == CONFIRM_SKIPPED:
        return _pack(
            LABEL_INCOMPLETE,
            "confirmation skipped despite PC_PASS eligibility",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=True,
            confirm_required=True,
        )

    if confirm == CONFIRM_NEGATIVE:
        return _pack(
            LABEL_CONTROL_NEGATIVE,
            "confirmation reliability below exploratory threshold",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=True,
            confirm_required=True,
        )

    if confirm == CONFIRM_RELIABLE:
        return _pack(
            LABEL_CA_FAVOURED_CONTROL,
            "screen CA_FAVOURED + PC_PASS + CONFIRM_RELIABLE",
            screen=screen,
            pc=pc,
            confirm=confirm,
            eligible=True,
            confirm_required=True,
        )

    return _pack(
        LABEL_INVALID,
        f"unrecognised confirm_label {confirm!r}",
        screen=screen,
        pc=pc,
        confirm=confirm,
        eligible=True,
        confirm_required=True,
    )


def _pack(
    label: str,
    reason: str,
    *,
    screen: str | None,
    pc: str | None,
    confirm: str | None,
    eligible: bool,
    confirm_required: bool,
) -> dict[str, Any]:
    if label not in ALLOWED_LABELS:
        raise ValueError(f"internal label error: {label!r}")
    return {
        "scientific_label": label,
        "reason": reason,
        "eligible_for_confirmation": bool(eligible),
        "confirmation_required": bool(confirm_required),
        "biological_power": BIOLOGICAL_POWER,
        "finished_primary": FINISHED_PRIMARY,
        "study": STUDY_STATUS,
        "stages": {
            "screen": screen,
            "pairing_pc": pc,
            "confirmation": confirm,
        },
    }


def build_s7_result_payload(
    *,
    finalize: Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
    screen: Mapping[str, Any] | None = None,
    pairing_pc: Mapping[str, Any] | None = None,
    confirmation: Mapping[str, Any] | None = None,
    resources: Mapping[str, Any] | None = None,
    ledger_path: str | None = None,
    checkpoint_root: str | None = None,
    protocol_id: str = "S7_covariance_20260929",
) -> dict[str, Any]:
    """Assemble the structured handoff payload used for markdown + JSON."""
    label = str(finalize["scientific_label"])
    if label not in ALLOWED_LABELS:
        raise ValueError(f"scientific_label must be one of {sorted(ALLOWED_LABELS)}")
    return {
        "protocol_id": protocol_id,
        "scientific_label": label,
        "reason": finalize.get("reason"),
        "biological_power": BIOLOGICAL_POWER,
        "finished_primary": FINISHED_PRIMARY,
        "study": STUDY_STATUS,
        "provenance": dict(provenance) if provenance else {},
        "screen": dict(screen) if screen else {},
        "pairing_pc": dict(pairing_pc) if pairing_pc else {},
        "confirmation": dict(confirmation) if confirmation else {},
        "resources": dict(resources) if resources else {},
        "ledger_path": ledger_path,
        "checkpoint_root": checkpoint_root,
        "finalize": dict(finalize),
        "claims": {
            "biological_advantage": False,
            "edits_canonical_gates": False,
            "real_disease_label_fits": False,
        },
    }


def render_s7_result_md(payload: Mapping[str, Any]) -> str:
    """Render worktree-local ``docs/nn_v2/s7/S7_RESULT.md`` body."""
    label = str(payload["scientific_label"])
    prov = payload.get("provenance") or {}
    resources = payload.get("resources") or {}
    screen = payload.get("screen") or {}
    pairing = payload.get("pairing_pc") or {}
    confirm = payload.get("confirmation") or {}
    finalize = payload.get("finalize") or {}
    stages = finalize.get("stages") or {}

    lines = [
        "# S7 prospective synthetic control — result",
        "",
        f"**Scientific label:** `{label}`",
        f"**Reason:** {payload.get('reason')}",
        f"**Biological power:** `{payload.get('biological_power', BIOLOGICAL_POWER)}`",
        f"**Finished primary:** `{payload.get('finished_primary', FINISHED_PRIMARY)}`",
        f"**Study:** `{payload.get('study', STUDY_STATUS)}`",
        "",
        "This batch is a prospective semisynthetic control only. It does not "
        "change the finished biological primary (`B_NULL`) and does not "
        "establish biological power or transportability.",
        "",
        "## Protocol and provenance",
        "",
        f"- Protocol ID: `{payload.get('protocol_id', 'S7_covariance_20260929')}`",
        f"- Spec SHA256: `{prov.get('spec_sha256', 'n/a')}`",
        f"- Provenance fingerprint: `{prov.get('fingerprint', 'n/a')}`",
        f"- Source hashes: `{json.dumps(prov.get('source_sha256', {}), sort_keys=True)}`",
        f"- Input hashes: `{json.dumps(prov.get('input_sha256', {}), sort_keys=True)}`",
        "",
        "## Stage outcomes",
        "",
        f"- Screen: `{stages.get('screen') or screen.get('screen_label')}`",
        f"- Pairing PC: `{stages.get('pairing_pc') or pairing.get('pc_label')}`",
        f"- Confirmation: `{stages.get('confirmation') or confirm.get('confirm_label')}`",
        "",
        "### Screen",
        "",
        "```json",
        json.dumps(screen, indent=2, sort_keys=True),
        "```",
        "",
        "### Pairing PC",
        "",
        "```json",
        json.dumps(pairing, indent=2, sort_keys=True),
        "```",
        "",
        "### Confirmation",
        "",
        "```json",
        json.dumps(confirm, indent=2, sort_keys=True),
        "```",
        "",
        "## Resources",
        "",
        "```json",
        json.dumps(resources, indent=2, sort_keys=True),
        "```",
        "",
        "## Artifact paths",
        "",
        f"- Ledger: `{payload.get('ledger_path')}`",
        f"- Checkpoints: `{payload.get('checkpoint_root')}`",
        "",
        "## Claims boundary",
        "",
        "- Biological advantage claimed: no",
        "- Canonical scientific JSON/gates edited: no",
        "- Real-disease-label fits: no",
        "",
    ]
    return "\n".join(lines)


def write_s7_result(
    path: Path | str,
    payload: Mapping[str, Any],
    *,
    also_json: bool = True,
) -> dict[str, Path]:
    """Write ``S7_RESULT.md`` (and optional sidecar JSON) under the given path.

    ``path`` may be the markdown file or its parent directory
    (``.../docs/nn_v2/s7``).
    """
    target = Path(path)
    if target.suffix.lower() == ".md":
        md_path = target
        root = md_path.parent
    else:
        root = target
        md_path = root / "S7_RESULT.md"
    root.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_s7_result_md(payload), encoding="utf-8")
    out: dict[str, Path] = {"markdown": md_path}
    if also_json:
        json_path = root / "S7_RESULT.json"
        json_path.write_text(
            json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        out["json"] = json_path
    return out
