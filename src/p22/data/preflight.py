"""Metadata preflight: what is inspectable before any training decision.

Nothing here trains, and nothing here reaches the network. It answers the five
questions the meeting asked about a candidate dataset: are donors present, are
labels present, are the two views paired, what is missing, and what shape is each
modality. Anything the files cannot answer is reported as ``unknown``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from p22 import __version__
from p22.data.schema import (
    CELL_ID,
    DEFAULT_SCHEMA,
    DONOR_ID,
    LABEL,
    PAIRING_PAIRED,
    PAIRING_PARTIAL,
    PAIRING_UNKNOWN,
    PAIRING_UNPAIRED,
    STATUS_BLOCKED,
    STATUS_INCONCLUSIVE,
    STATUS_PASS,
    UNKNOWN,
    MetadataSchema,
)


@dataclass(frozen=True)
class PreflightReport:
    """Inspectable facts about a candidate dataset.

    Attributes:
        status: ``PASS``, ``INCONCLUSIVE``, or ``BLOCKED``.
        blocking_problems: reasons the dataset cannot be used as supplied.
        open_questions: facts that are unknown rather than wrong.
        sections: the recorded findings, one key per question.
    """

    status: str
    blocking_problems: tuple[str, ...]
    open_questions: tuple[str, ...]
    sections: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            **self.sections,
        }

    def summary_lines(self) -> list[str]:
        rows = self.sections.get("rows", {})
        donors = self.sections.get("donors", {})
        labels = self.sections.get("labels", {})
        lines = [
            f"status: {self.status}",
            f"rows: {rows.get('n_rows', UNKNOWN)}",
            f"donors: {donors.get('n_donors', UNKNOWN)}",
            f"labels: {labels.get('n_classes', UNKNOWN)}",
            f"pairing: {self.sections.get('pairing', {}).get('status', UNKNOWN)}",
        ]
        lines += [f"blocking: {problem}" for problem in self.blocking_problems]
        lines += [f"unknown: {question}" for question in self.open_questions]
        return lines


def _missingness(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    n_rows = max(int(frame.shape[0]), 1)
    for column in frame.columns:
        column_values = frame[column]
        blank = column_values.isna()
        if column_values.dtype == object:
            blank = blank | column_values.map(
                lambda value: isinstance(value, str) and not value.strip()
            ).fillna(False)
        count = int(blank.sum())
        report[str(column)] = {
            "missing": count,
            "fraction": round(count / n_rows, 6),
        }
    return report


def _donor_section(frame: pd.DataFrame) -> dict[str, Any]:
    if DONOR_ID not in frame.columns:
        return {"n_donors": UNKNOWN, "reason": f"{DONOR_ID} column absent"}
    donors = frame[DONOR_ID].astype(str)
    counts = donors.value_counts()
    return {
        "n_donors": int(counts.size),
        "cells_per_donor": {
            "min": int(counts.min()),
            "median": float(counts.median()),
            "max": int(counts.max()),
        },
        "donors_with_one_cell": int((counts == 1).sum()),
        "split_unit_available": "donor",
    }


def _label_section(frame: pd.DataFrame) -> dict[str, Any]:
    if LABEL not in frame.columns:
        return {"n_classes": UNKNOWN, "reason": f"{LABEL} column absent"}
    labels = frame[LABEL]
    counts = labels.value_counts(dropna=False).sort_index()
    smallest = int(counts.min()) if counts.size else 0
    return {
        "n_classes": int(counts.size),
        "class_counts": {str(key): int(value) for key, value in counts.items()},
        "smallest_class_cells": smallest,
        "class_balance_note": "balance is reported, never enforced",
    }


def _per_donor_class_counts(frame: pd.DataFrame) -> dict[str, Any]:
    if DONOR_ID not in frame.columns or LABEL not in frame.columns:
        return {"available": False, "reason": "donor or label column absent"}
    table = pd.crosstab(frame[DONOR_ID].astype(str), frame[LABEL].astype(str))
    return {
        "available": True,
        "donors": int(table.shape[0]),
        "classes": int(table.shape[1]),
        "donors_missing_at_least_one_class": int((table == 0).any(axis=1).sum()),
        "counts": {donor: row.to_dict() for donor, row in table.iterrows()},
    }


def _duplicate_section(frame: pd.DataFrame) -> dict[str, Any]:
    if CELL_ID not in frame.columns:
        return {"duplicate_cell_ids": UNKNOWN, "reason": f"{CELL_ID} column absent"}
    ids = frame[CELL_ID].astype(str)
    duplicated = ids[ids.duplicated(keep=False)]
    examples = sorted(set(duplicated))[:5]
    return {
        "duplicate_cell_ids": int(duplicated.nunique()),
        "duplicate_rows": int(duplicated.size),
        "examples": examples,
    }


def _modality_section(
    view_shapes: Mapping[str, Sequence[int]] | None, n_rows: int
) -> dict[str, Any]:
    if not view_shapes:
        return {"available": False, "reason": "no modality shapes supplied", "views": {}}
    views: dict[str, Any] = {}
    for name, shape in view_shapes.items():
        rows, features = int(shape[0]), int(shape[1])
        views[str(name)] = {
            "rows": rows,
            "features": features,
            "rows_match_metadata": rows == n_rows,
        }
    return {"available": True, "views": views}


def _pairing_section(
    view_cell_ids: Mapping[str, Sequence[Any]] | None, metadata_ids: Sequence[Any] | None
) -> dict[str, Any]:
    if not view_cell_ids or len(view_cell_ids) < 2:
        return {
            "status": PAIRING_UNKNOWN,
            "reason": "cell identifiers for two views were not supplied",
        }
    id_sets = {name: {str(value) for value in ids} for name, ids in view_cell_ids.items()}
    names = list(id_sets)
    shared = set.intersection(*id_sets.values())
    union = set.union(*id_sets.values())
    if not shared:
        status = PAIRING_UNPAIRED
    elif shared == union:
        status = PAIRING_PAIRED
    else:
        status = PAIRING_PARTIAL
    section = {
        "status": status,
        "views": names,
        "cells_per_view": {name: len(values) for name, values in id_sets.items()},
        "cells_in_all_views": len(shared),
        "cells_in_any_view": len(union),
    }
    if metadata_ids is not None:
        metadata_set = {str(value) for value in metadata_ids}
        section["cells_in_metadata_and_all_views"] = len(shared & metadata_set)
        section["metadata_cells_missing_from_a_view"] = len(metadata_set - shared)
    return section


def inspect_metadata(
    metadata: pd.DataFrame,
    view_shapes: Mapping[str, Sequence[int]] | None = None,
    view_cell_ids: Mapping[str, Sequence[Any]] | None = None,
    access_facts: Mapping[str, Any] | None = None,
    data_mode: str = "synthetic",
    source: str = "in-memory table",
    schema: MetadataSchema = DEFAULT_SCHEMA,
) -> PreflightReport:
    """Inspect a per-cell metadata table and report feasibility facts.

    Args:
        metadata: per-cell table.
        view_shapes: optional ``{view name: (rows, features)}``.
        view_cell_ids: optional ``{view name: cell identifiers}`` for pairing.
        access_facts: recorded licence and access facts; anything absent is
            reported as unknown.
        data_mode: declared data mode of the inspected source.
        source: human-readable origin of the table.
        schema: column contract to check against.

    Returns:
        A :class:`PreflightReport`. Status is ``BLOCKED`` when a required column
        is absent, cell identifiers repeat, or a modality row count disagrees with
        the table; ``INCONCLUSIVE`` while pairing or access facts are unknown;
        otherwise ``PASS``.

    Raises:
        TypeError: if ``metadata`` is not a pandas DataFrame.
        ValueError: if ``metadata`` has no rows.
    """
    if not isinstance(metadata, pd.DataFrame):
        raise TypeError(f"metadata must be a pandas DataFrame, got {type(metadata).__name__}")
    if metadata.shape[0] == 0:
        raise ValueError("metadata has no rows")

    n_rows = int(metadata.shape[0])
    missing_required = schema.missing_required(metadata)
    duplicates = _duplicate_section(metadata)
    modality = _modality_section(view_shapes, n_rows)
    pairing = _pairing_section(
        view_cell_ids,
        metadata[CELL_ID] if CELL_ID in metadata.columns else None,
    )
    unknown_facts = schema.unknown_access_facts(dict(access_facts or {}))

    blocking: list[str] = []
    for column in missing_required:
        blocking.append(f"required column absent: {column}")
    if isinstance(duplicates.get("duplicate_cell_ids"), int) and duplicates["duplicate_cell_ids"]:
        blocking.append(
            f"{duplicates['duplicate_cell_ids']} cell identifiers repeat, "
            f"examples: {duplicates['examples']}"
        )
    for name, view in modality.get("views", {}).items():
        if not view["rows_match_metadata"]:
            blocking.append(f"view {name} has {view['rows']} rows but metadata has {n_rows}")
    if pairing["status"] == PAIRING_UNPAIRED:
        blocking.append("no cell identifier is shared between the supplied views")

    open_questions: list[str] = []
    if pairing["status"] == PAIRING_UNKNOWN:
        open_questions.append("pairing between the two views is unknown: " + pairing["reason"])
    if pairing["status"] == PAIRING_PARTIAL:
        open_questions.append(
            "views overlap only partially; the usable paired subset must be decided by a human"
        )
    for fact in unknown_facts:
        open_questions.append(f"{fact} is unknown and must be recorded by a human")
    if not modality.get("available"):
        open_questions.append("modality shapes were not supplied")
    missingness = _missingness(metadata)
    for column in schema.required:
        if column in missingness and missingness[column]["missing"]:
            blocking.append(
                f"required column {column} has {missingness[column]['missing']} missing values"
            )

    if blocking:
        status = STATUS_BLOCKED
    elif open_questions:
        status = STATUS_INCONCLUSIVE
    else:
        status = STATUS_PASS

    sections: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "p22_version": __version__,
        "data_mode": data_mode,
        "source": source,
        "network_access": "none",
        "rows": {
            "n_rows": n_rows,
            "n_columns": int(metadata.shape[1]),
            "columns": [str(column) for column in metadata.columns],
            "missing_required_columns": missing_required,
            "unexpected_columns": schema.unexpected(metadata),
        },
        "donors": _donor_section(metadata),
        "labels": _label_section(metadata),
        "per_donor_class_counts": _per_donor_class_counts(metadata),
        "missingness": missingness,
        "duplicates": duplicates,
        "modalities": modality,
        "pairing": pairing,
        "access_facts": {
            fact: (access_facts or {}).get(fact, UNKNOWN) or UNKNOWN for fact in schema.access_facts
        },
        "unknown_access_facts": unknown_facts,
        "schema_notes": list(schema.notes),
    }
    return PreflightReport(
        status=status,
        blocking_problems=tuple(blocking),
        open_questions=tuple(open_questions),
        sections=sections,
    )


def inspect_h5ad(
    path: str | Path,
    label_column: str = LABEL,
    donor_column: str = DONOR_ID,
    access_facts: Mapping[str, Any] | None = None,
    data_mode: str = "synthetic",
) -> PreflightReport:
    """Inspect a small local ``.h5ad`` file without downloading anything.

    Args:
        path: local file path. No remote location is accepted.
        label_column: column in ``obs`` holding the label.
        donor_column: column in ``obs`` holding the donor identifier.
        access_facts: recorded licence and access facts.
        data_mode: declared data mode of the file.

    Returns:
        A :class:`PreflightReport` for the file's ``obs`` table and matrix shape.

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if the path is not a local ``.h5ad`` file.
    """
    import anndata

    if str(path).startswith(("http://", "https://", "ftp://", "s3://", "gs://")):
        raise ValueError("inspect_h5ad accepts local paths only")
    target = Path(path)
    if target.suffix != ".h5ad":
        raise ValueError(f"expected a .h5ad file, got {target.name}")
    if not target.is_file():
        raise FileNotFoundError(f"no such file: {target}")

    adata = anndata.read_h5ad(target)
    frame = adata.obs.reset_index()
    first_column = frame.columns[0]
    if CELL_ID not in frame.columns:
        frame = frame.rename(columns={first_column: CELL_ID})
    renames = {}
    if donor_column != DONOR_ID and donor_column in frame.columns:
        renames[donor_column] = DONOR_ID
    if label_column != LABEL and label_column in frame.columns:
        renames[label_column] = LABEL
    frame = frame.rename(columns=renames)
    for column in frame.columns:
        if isinstance(frame[column].dtype, pd.CategoricalDtype):
            frame[column] = frame[column].astype(str)

    return inspect_metadata(
        frame,
        view_shapes={"view_a": (int(adata.n_obs), int(adata.n_vars))},
        access_facts=access_facts,
        data_mode=data_mode,
        source=f"local file {target.name}",
    )


def write_preflight_report(
    report: PreflightReport,
    path: str | Path,
) -> Path:
    """Write a preflight report as JSON and return the written path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    target.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    return target


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)
