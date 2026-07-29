"""Visible notebook run modes for the one-notebook workflow.

Three modes only. Safe default is simulation. Real matrix work stays behind
dated approval plus an explicit user-selected mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODE_SIMULATION = "simulation"
MODE_METADATA_CENSUS = "metadata_census"
MODE_APPROVED_REAL = "approved_real_analysis"

VISIBLE_MODES = (MODE_SIMULATION, MODE_METADATA_CENSUS, MODE_APPROVED_REAL)

MODE_DESCRIPTIONS = {
    MODE_SIMULATION: (
        "Synthetic wiring only. Tests splits, baselines, and interventions. Never disease evidence."
    ),
    MODE_METADATA_CENSUS: (
        "Live public catalog metadata plus planned full-cohort census contract. "
        "No H5AD download. Not a model result."
    ),
    MODE_APPROVED_REAL: (
        "Download and analyze the full public H5AD after dated Professor Fang "
        "approval. Full-cohort census first; capped cell-level models second."
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


def resolve_mode(
    requested_mode: str,
    *,
    professor_approved: bool,
    run_real_data: bool = False,
    run_model: bool = False,
) -> ModeSelection:
    """Resolve visible mode against approval and flags.

    Raises:
        ValueError: if ``requested_mode`` is unknown.
    """
    if requested_mode not in VISIBLE_MODES:
        raise ValueError(f"unknown mode {requested_mode!r}; expected one of {VISIBLE_MODES}")

    blocking: list[str] = []
    allow_download = False
    allow_model = False

    if requested_mode == MODE_APPROVED_REAL:
        if not professor_approved:
            blocking.append(
                "dated Professor Fang approval absent; approved_real_analysis cannot download H5AD"
            )
        elif not run_real_data:
            blocking.append("set P22_RUN_REAL_DATA=1 or notebook RUN_REAL_DATA=True after approval")
        else:
            allow_download = True
            allow_model = bool(run_model)
            if run_model is False:
                blocking.append("model fitting off; census/resource path may still run")

    return ModeSelection(
        mode=requested_mode,
        professor_approved=professor_approved,
        allow_h5ad_download=allow_download,
        allow_model_fit=allow_model and allow_download,
        description=MODE_DESCRIPTIONS[requested_mode],
        blocking_problems=tuple(blocking),
    )
