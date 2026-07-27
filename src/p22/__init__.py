"""P22 research package.

Synthetic-only scaffold. Approval state lives in ``plan/approvals.json`` and is
read at runtime so that configs and run records cannot silently claim a data
mode that has not been approved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
APPROVALS_PATH = REPO_ROOT / "plan" / "approvals.json"

SYNTHETIC = "synthetic"
LEGACY_READ_ONLY = "legacy read-only"
APPROVED_REAL_DATA = "approved real data"
DATA_MODES = (SYNTHETIC, LEGACY_READ_ONLY, APPROVED_REAL_DATA)

EVIDENCE_LABELS = (
    "verified",
    "experimental result",
    "proposed",
    "inference",
    "unknown",
)


def load_approvals(path: Path | None = None) -> dict[str, Any]:
    """Return the approval record."""
    target = path or APPROVALS_PATH
    with Path(target).open(encoding="utf-8") as handle:
        return json.load(handle)


def approval_blocked(approvals: dict[str, Any] | None = None) -> bool:
    """Return True while condition-specific work is not approved."""
    record = approvals if approvals is not None else load_approvals()
    return record.get("approval_state") != "approved"


def allowed_data_modes(approvals: dict[str, Any] | None = None) -> tuple[str, ...]:
    record = approvals if approvals is not None else load_approvals()
    return tuple(record.get("allowed_data_modes", (SYNTHETIC,)))


def require_allowed_data_mode(data_mode: str, approvals: dict[str, Any] | None = None) -> str:
    """Validate a data mode against the current approval record.

    Raises:
        ValueError: if the mode is unknown or not currently allowed.
    """
    if data_mode not in DATA_MODES:
        raise ValueError(f"unknown data_mode {data_mode!r}; expected one of {DATA_MODES}")
    permitted = allowed_data_modes(approvals)
    if data_mode not in permitted:
        raise ValueError(
            f"data_mode {data_mode!r} is not permitted while approval is blocked; "
            f"allowed modes: {permitted}"
        )
    return data_mode


__all__ = [
    "APPROVALS_PATH",
    "APPROVED_REAL_DATA",
    "DATA_MODES",
    "EVIDENCE_LABELS",
    "LEGACY_READ_ONLY",
    "REPO_ROOT",
    "SYNTHETIC",
    "__version__",
    "allowed_data_modes",
    "approval_blocked",
    "load_approvals",
    "require_allowed_data_mode",
]
