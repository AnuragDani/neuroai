"""Visible notebook run modes for the one-notebook workflow.

Three modes only. Safe default is simulation, so sharing the notebook never
triggers a multi-gigabyte download. Real analysis is opt-in and must be selected
explicitly together with the data flag.

Approval is an attestation supplied outside this repository. ``plan/approvals.json``
stays at its recorded state and is reported, not rewritten, and no approval date
is invented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODE_SIMULATION = "simulation"
MODE_METADATA_CENSUS = "metadata_census"
MODE_REAL_ANALYSIS = "real_analysis"

# Earlier runs named the real mode ``approved_real_analysis``. The name is kept as
# an accepted alias so an old command or saved notebook still resolves.
MODE_APPROVED_REAL = MODE_REAL_ANALYSIS
LEGACY_MODE_NAMES = {"approved_real_analysis": MODE_REAL_ANALYSIS}

VISIBLE_MODES = (MODE_SIMULATION, MODE_METADATA_CENSUS, MODE_REAL_ANALYSIS)

MODE_DESCRIPTIONS = {
    MODE_SIMULATION: (
        "Synthetic wiring only. Tests splits, baselines, and interventions. Never disease evidence."
    ),
    MODE_METADATA_CENSUS: (
        "Live public catalog metadata plus planned full-cohort census contract. "
        "No H5AD download. Not a model result."
    ),
    MODE_REAL_ANALYSIS: (
        "Full public H5AD: schema audit, QC census, resource gate, ATAC branch, "
        "donor-held-out baselines and models, interventions, and validation status."
    ),
}


@dataclass(frozen=True)
class ModeSelection:
    """User-visible mode choice and whether real matrix work may proceed."""

    mode: str
    professor_approved: bool
    allow_h5ad_download: bool
    allow_model_fit: bool
    description: str
    blocking_problems: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "professor_approved": self.professor_approved,
            "allow_h5ad_download": self.allow_h5ad_download,
            "allow_model_fit": self.allow_model_fit,
            "description": self.description,
            "blocking_problems": list(self.blocking_problems),
        }


def detect_colab() -> bool:
    """Return True when running inside Google Colab."""
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


def normalize_mode(requested_mode: str) -> str:
    """Map a legacy mode name onto its current name.

    Raises:
        ValueError: if ``requested_mode`` is not a visible or legacy mode.
    """
    resolved = LEGACY_MODE_NAMES.get(requested_mode, requested_mode)
    if resolved not in VISIBLE_MODES:
        raise ValueError(f"unknown mode {requested_mode!r}; expected one of {VISIBLE_MODES}")
    return resolved


def resolve_mode(
    requested_mode: str,
    *,
    professor_approved: bool,
    run_real_data: bool = False,
    run_model: bool = False,
) -> ModeSelection:
    """Resolve visible mode against the approval attestation and flags.

    Raises:
        ValueError: if ``requested_mode`` is unknown.
    """
    mode = normalize_mode(requested_mode)

    blocking: list[str] = []
    allow_download = False
    allow_model = False

    if mode == MODE_REAL_ANALYSIS:
        if not run_real_data:
            blocking.append("set P22_RUN_REAL_DATA=1 or notebook RUN_REAL_DATA=True for real data")
        else:
            allow_download = True
            allow_model = bool(run_model) and professor_approved
            if run_model and not professor_approved:
                blocking.append("approval attestation absent; model fitting blocked")
            elif run_model is False:
                blocking.append("model fitting off; census/resource path may still run")

    return ModeSelection(
        mode=mode,
        professor_approved=professor_approved,
        allow_h5ad_download=allow_download,
        allow_model_fit=allow_model and allow_download,
        description=MODE_DESCRIPTIONS[mode],
        blocking_problems=tuple(blocking),
    )
