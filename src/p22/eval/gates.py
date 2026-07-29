"""Human-readable gate statuses for the professor recommendation workflow.

Gate numbering is canonical: only G0 through G9 exist. Each gate answers one
question and reports PASS, INCONCLUSIVE, or BLOCKED with observed evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

STATUS_PASS = "PASS"
STATUS_INCONCLUSIVE = "INCONCLUSIVE"
STATUS_BLOCKED = "BLOCKED"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
ALLOWED_STATUSES = (
    STATUS_PASS,
    STATUS_INCONCLUSIVE,
    STATUS_BLOCKED,
    STATUS_NOT_APPLICABLE,
)

GATE_IDS = tuple(f"G{index}" for index in range(10))

GATE_QUESTIONS: dict[str, str] = {
    "G0": "Can researcher run notebook locally and save outputs?",
    "G1": "Are we using the intended public dataset?",
    "G2": "Is dataset large enough at donor level, not merely cell level?",
    "G3": "Can local machine process real data within declared limits?",
    "G4": "Is comparison defined before final training?",
    "G5": "Can model be evaluated on unseen donors without train contamination?",
    "G6": "Does multimodal routing add stable value over simpler models?",
    "G7": "Does prediction depend on routed modalities?",
    "G8": "Are findings supported outside training data?",
    "G9": "Can another researcher rerun and audit the result?",
}

ONE_NOTEBOOK_CONTRACT = (
    "P22_down_syndrome_all_in_one.ipynb is the only final professor-facing, "
    "local-Jupyter and Google-Colab-compatible notebook. Synthetic wiring may "
    "test code paths; it is never disease evidence. Real matrix work requires a "
    "dated Professor Fang approval record and passing G1-G4."
)


@dataclass(frozen=True)
class GateRecord:
    """One gate outcome with evidence and next owner."""

    gate_id: str
    question: str
    status: str
    evidence: dict[str, Any] = field(default_factory=dict)
    unknowns: tuple[str, ...] = ()
    next_owner: str = "researcher"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.gate_id not in GATE_IDS:
            raise ValueError(f"unknown gate_id {self.gate_id!r}; expected one of {GATE_IDS}")
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"unknown status {self.status!r}; expected one of {ALLOWED_STATUSES}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "question": self.question,
            "status": self.status,
            "evidence": dict(self.evidence),
            "unknowns": list(self.unknowns),
            "next_owner": self.next_owner,
            "notes": self.notes,
        }


@dataclass
class GateBoard:
    """Mutable collection of G0-G9 records."""

    records: dict[str, GateRecord] = field(default_factory=dict)

    def set(self, record: GateRecord) -> GateRecord:
        self.records[record.gate_id] = record
        return record

    def get(self, gate_id: str) -> GateRecord | None:
        return self.records.get(gate_id)

    def status_map(self) -> dict[str, str]:
        return {
            gate_id: self.records[gate_id].status for gate_id in GATE_IDS if gate_id in self.records
        }

    def as_rows(self) -> list[dict[str, Any]]:
        rows = []
        for gate_id in GATE_IDS:
            record = self.records.get(gate_id)
            if record is None:
                rows.append(
                    {
                        "gate": gate_id,
                        "question": GATE_QUESTIONS[gate_id],
                        "status": "PENDING",
                        "next_owner": "researcher",
                        "notes": "not evaluated yet",
                    }
                )
            else:
                rows.append(
                    {
                        "gate": record.gate_id,
                        "question": record.question,
                        "status": record.status,
                        "next_owner": record.next_owner,
                        "notes": record.notes,
                    }
                )
        return rows

    def to_dict(self) -> dict[str, Any]:
        gates = {
            gate_id: self.records[gate_id].to_dict()
            for gate_id in GATE_IDS
            if gate_id in self.records
        }
        return {
            "contract": ONE_NOTEBOOK_CONTRACT,
            "gates": gates,
            "status_map": self.status_map(),
        }


def make_gate(
    gate_id: str,
    status: str,
    evidence: Mapping[str, Any] | None = None,
    unknowns: Sequence[str] = (),
    next_owner: str = "researcher",
    notes: str = "",
) -> GateRecord:
    """Build a gate record using the canonical question text."""
    return GateRecord(
        gate_id=gate_id,
        question=GATE_QUESTIONS[gate_id],
        status=status,
        evidence=dict(evidence or {}),
        unknowns=tuple(unknowns),
        next_owner=next_owner,
        notes=notes,
    )


def empty_board() -> GateBoard:
    """Return an empty G0-G9 board."""
    return GateBoard()
