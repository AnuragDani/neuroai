"""Data-size defense stages R1-R6.

Separate from G0-G9. These stages prove full-cohort accounting before any capped
model result is called real evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from p22.eval.gates import (
    ALLOWED_STATUSES,
    STATUS_BLOCKED,
    STATUS_INCONCLUSIVE,
    STATUS_PASS,
)

R_IDS = tuple(f"R{index}" for index in range(1, 7))

R_QUESTIONS: dict[str, str] = {
    "R1": "Was the immutable full-cohort acquisition recorded before filtering?",
    "R2": "Was a backed full-cohort census produced before any model cap?",
    "R3": "Do post-QC retained donors/cells meet adequacy thresholds?",
    "R4": "Are full-cohort and capped cell-level layers reported separately?",
    "R5": "Is donor-limited inferential scale and second-cohort status explicit?",
    "R6": "Does the evidence package include numeric data-scale accounting?",
}


@dataclass(frozen=True)
class ScaleRecord:
    """One R-stage outcome."""

    stage_id: str
    question: str
    status: str
    evidence: dict[str, Any] = field(default_factory=dict)
    unknowns: tuple[str, ...] = ()
    next_owner: str = "researcher"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.stage_id not in R_IDS:
            raise ValueError(f"unknown stage_id {self.stage_id!r}; expected one of {R_IDS}")
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"unknown status {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "question": self.question,
            "status": self.status,
            "evidence": dict(self.evidence),
            "unknowns": list(self.unknowns),
            "next_owner": self.next_owner,
            "notes": self.notes,
        }


@dataclass
class ScaleBoard:
    """Mutable R1-R6 board."""

    records: dict[str, ScaleRecord] = field(default_factory=dict)

    def set(self, record: ScaleRecord) -> ScaleRecord:
        self.records[record.stage_id] = record
        return record

    def status_map(self) -> dict[str, str]:
        return {
            stage_id: self.records[stage_id].status
            for stage_id in R_IDS
            if stage_id in self.records
        }

    def as_rows(self) -> list[dict[str, Any]]:
        rows = []
        for stage_id in R_IDS:
            record = self.records.get(stage_id)
            if record is None:
                rows.append(
                    {
                        "stage": stage_id,
                        "question": R_QUESTIONS[stage_id],
                        "status": "PENDING",
                        "notes": "not evaluated yet",
                    }
                )
            else:
                rows.append(
                    {
                        "stage": record.stage_id,
                        "question": record.question,
                        "status": record.status,
                        "notes": record.notes,
                    }
                )
        return rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": {
                stage_id: self.records[stage_id].to_dict()
                for stage_id in R_IDS
                if stage_id in self.records
            },
            "status_map": self.status_map(),
        }


def make_scale(
    stage_id: str,
    status: str,
    evidence: Mapping[str, Any] | None = None,
    unknowns: tuple[str, ...] | list[str] = (),
    next_owner: str = "researcher",
    notes: str = "",
) -> ScaleRecord:
    return ScaleRecord(
        stage_id=stage_id,
        question=R_QUESTIONS[stage_id],
        status=status,
        evidence=dict(evidence or {}),
        unknowns=tuple(unknowns),
        next_owner=next_owner,
        notes=notes,
    )


def empty_scale_board() -> ScaleBoard:
    return ScaleBoard()


def blocked_without_h5ad(stage_id: str, reason: str) -> ScaleRecord:
    return make_scale(
        stage_id,
        STATUS_BLOCKED,
        evidence={"h5ad_loaded": False},
        unknowns=(reason,),
        next_owner="Professor Fang",
        notes=reason,
    )


# Re-export statuses for callers.
__all__ = [
    "R_IDS",
    "R_QUESTIONS",
    "STATUS_BLOCKED",
    "STATUS_INCONCLUSIVE",
    "STATUS_PASS",
    "ScaleBoard",
    "ScaleRecord",
    "blocked_without_h5ad",
    "empty_scale_board",
    "make_scale",
]
