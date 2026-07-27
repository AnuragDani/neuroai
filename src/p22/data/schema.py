"""Metadata schema for preflight inspection.

The schema states what must exist before any training decision, and it names the
facts that cannot be derived from a matrix at all: licence, access level, consent,
and redistribution terms. Those are reported as ``unknown`` until a human records
them. A guess is worse than an unknown here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

CELL_ID = "cell_id"
DONOR_ID = "donor_id"
LABEL = "label"
REQUIRED_COLUMNS: tuple[str, ...] = (CELL_ID, DONOR_ID, LABEL)
OPTIONAL_COLUMNS: tuple[str, ...] = ("label_name", "capture_batch", "modality")

UNKNOWN = "unknown"
ACCESS_FACTS: tuple[str, ...] = (
    "licence",
    "access_level",
    "consent_terms",
    "redistribution_allowed",
    "controlled_access_approval",
)

STATUS_PASS = "PASS"
STATUS_INCONCLUSIVE = "INCONCLUSIVE"
STATUS_BLOCKED = "BLOCKED"
STATUSES: tuple[str, ...] = (STATUS_PASS, STATUS_INCONCLUSIVE, STATUS_BLOCKED)

PAIRING_PAIRED = "paired"
PAIRING_PARTIAL = "partially paired"
PAIRING_UNPAIRED = "unpaired"
PAIRING_UNKNOWN = UNKNOWN


@dataclass(frozen=True)
class MetadataSchema:
    """Column contract for a per-cell metadata table."""

    required: tuple[str, ...] = REQUIRED_COLUMNS
    optional: tuple[str, ...] = OPTIONAL_COLUMNS
    access_facts: tuple[str, ...] = ACCESS_FACTS
    notes: tuple[str, ...] = field(
        default=(
            "donor_id is required because donor-held-out evaluation is the only "
            "split this project accepts when donors exist",
            "licence, access level, consent, redistribution, and controlled-access "
            "approval cannot be inferred from a matrix and stay unknown until recorded",
        )
    )

    def missing_required(self, frame: pd.DataFrame) -> list[str]:
        return [column for column in self.required if column not in frame.columns]

    def unexpected(self, frame: pd.DataFrame) -> list[str]:
        known = set(self.required) | set(self.optional)
        return [column for column in frame.columns if column not in known]

    def unknown_access_facts(self, recorded: dict[str, object] | None) -> list[str]:
        provided = recorded or {}
        return [fact for fact in self.access_facts if provided.get(fact) in (None, "", UNKNOWN)]


DEFAULT_SCHEMA = MetadataSchema()
