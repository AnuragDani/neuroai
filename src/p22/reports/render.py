"""Markdown reports that keep different kinds of evidence apart.

A report has fixed sections: provenance, predictive performance, routing signals,
intervention evidence, limitations, and approval. Sections that were not measured say so
rather than disappearing, so a reader can tell the difference between a null result and a
missing experiment. Routing and intervention evidence never share a table with accuracy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import p22
from p22.runs.registry import RunRecord

REPORTS_ROOT = p22.REPO_ROOT / "reports" / "generated" / "reports"
NOT_MEASURED = "Not measured in this run."

SECTION_TITLES = (
    "Provenance",
    "Predictive performance",
    "Routing signals",
    "Intervention evidence",
    "Limitations",
    "Approval and next step",
)


def _format_number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.{digits}f}"
    return str(value)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _provenance_section(record: RunRecord) -> str:
    config = record.config
    fingerprint = record.data_fingerprint
    rows = [
        ["run id", f"`{record.run_id}`"],
        ["created at", record.created_at],
        ["git commit", f"`{record.git_commit}`"],
        ["config name", str(config.get("name", "-"))],
        ["config hash", f"`{record.config_hash}`"],
        ["data mode", record.data_mode],
        ["approval state", record.approval_state],
        ["data fingerprint", f"`{fingerprint.get('sha256', '-')}`"],
        [
            "views",
            ", ".join(
                f"{name} {tuple(shape)}"
                for name, shape in sorted(fingerprint.get("views", {}).items())
            )
            or "-",
        ],
        ["cells (total)", str(fingerprint.get("n_cells", "-"))],
        ["donors (total)", str(fingerprint.get("n_donors", "-"))],
        [
            "donors per split",
            ", ".join(f"{split} {count}" for split, count in record.donor_counts.items()),
        ],
        [
            "cells per split",
            ", ".join(f"{split} {count}" for split, count in record.cell_counts.items()),
        ],
        ["seeds", ", ".join(str(seed) for seed in record.seeds)],
        ["model", record.model],
        ["split unit", "donor"],
        ["transform", str(record.transform_metadata.get("kind", "-"))],
        ["transform fit scope", str(record.transform_metadata.get("fit_scope", "-"))],
        [
            "transform fingerprint",
            f"`{record.transform_metadata.get('parameter_fingerprint', '-')}`",
        ],
        ["evidence labels", ", ".join(record.evidence_labels)],
    ]
    return _markdown_table(["field", "value"], rows)


def _performance_section(record: RunRecord) -> str:
    if not record.metrics:
        return NOT_MEASURED
    rows = []
    for name in sorted(record.metrics):
        entry = record.metrics[name]
        interval = entry.get("interval")
        if isinstance(interval, Sequence) and not isinstance(interval, str) and len(interval) == 2:
            interval_text = f"[{_format_number(interval[0])}, {_format_number(interval[1])}]"
        else:
            interval_text = "-"
        valid = entry.get("n_valid")
        failed = entry.get("n_failed")
        replicates = "-" if valid is None and failed is None else f"{valid} valid / {failed} failed"
        reason = entry.get("not_applicable")
        rows.append(
            [
                name,
                _format_number(entry.get("value")),
                interval_text,
                str(entry.get("unit", "-")),
                replicates,
                "measured" if entry.get("value") is not None else f"not applicable: {reason}",
            ]
        )
    return _markdown_table(
        ["metric", "estimate", "interval", "resampling unit", "replicates", "status"], rows
    )


def _routing_section(record: RunRecord) -> str:
    if not record.routing_signals:
        return NOT_MEASURED
    rows = [[key, _readable(value)] for key, value in sorted(record.routing_signals.items())]
    return (
        "Routing weights describe how much each view contributed to the fused representation. "
        "They are reported apart from accuracy and do not by themselves show that a prediction "
        "depended on a view.\n\n" + _markdown_table(["signal", "value"], rows)
    )


def _intervention_section(record: RunRecord) -> str:
    if not record.intervention_evidence:
        return NOT_MEASURED
    rows = [[key, _readable(value)] for key, value in sorted(record.intervention_evidence.items())]
    return (
        "Interventions modify a view on held-out cells and record the change in the metric. "
        "Effects are associations under the stated intervention, measured on synthetic data.\n\n"
        + _markdown_table(["intervention", "effect"], rows)
    )


def _limitations_section(record: RunRecord) -> str:
    return "\n".join(f"- {item}" for item in record.limitations)


def _approval_section(record: RunRecord) -> str:
    lines = [
        f"- Approval state recorded with this run: **{record.approval_state}**.",
        f"- Data mode: **{record.data_mode}**.",
    ]
    if record.approval_state == "blocked":
        lines.append(
            "- No real dataset may be added, and no result here transfers to real data. "
            "Written approval is required before changing the data mode."
        )
    if record.notes:
        lines.extend(f"- {note}" for note in record.notes)
    return "\n".join(lines)


def _readable(value: Any) -> str:
    if isinstance(value, Mapping):
        return ", ".join(f"{key}: {_readable(inner)}" for key, inner in sorted(value.items()))
    if isinstance(value, (list, tuple)):
        return ", ".join(_readable(item) for item in value)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return _format_number(value)
    return str(value)


def render_run_report(record: RunRecord) -> str:
    """Render one run record as Markdown.

    Args:
        record: the run record to render.

    Returns:
        Markdown text with all six sections present, in a fixed order.
    """
    bodies = {
        "Provenance": _provenance_section(record),
        "Predictive performance": _performance_section(record),
        "Routing signals": _routing_section(record),
        "Intervention evidence": _intervention_section(record),
        "Limitations": _limitations_section(record),
        "Approval and next step": _approval_section(record),
    }
    parts = [f"# Run report: {record.run_id}", ""]
    for title in SECTION_TITLES:
        parts.extend([f"## {title}", "", bodies[title], ""])
    return "\n".join(parts).rstrip() + "\n"


def render_comparison_table(records: Sequence[RunRecord], metric: str = "accuracy") -> str:
    """Render one metric across several runs, without ranking or recommending.

    Args:
        records: run records to compare.
        metric: metric name to read from each record.

    Returns:
        Markdown text with one row per record.

    Raises:
        ValueError: if no records are given.
    """
    if not records:
        raise ValueError("render_comparison_table needs at least one record")
    rows = []
    for record in records:
        entry = record.metrics.get(metric, {})
        interval = entry.get("interval")
        if isinstance(interval, Sequence) and not isinstance(interval, str) and len(interval) == 2:
            interval_text = f"[{_format_number(interval[0])}, {_format_number(interval[1])}]"
        else:
            interval_text = "-"
        rows.append(
            [
                record.model,
                _format_number(entry.get("value")),
                interval_text,
                ", ".join(str(seed) for seed in record.seeds),
                entry.get("not_applicable") or "-",
            ]
        )
    header = (
        f"Metric: `{metric}`. Intervals come from resampling donors. Overlapping intervals "
        "do not establish a difference, and this table makes no claim that any model is better.\n\n"
    )
    return header + _markdown_table(
        ["model", "estimate", "interval", "seeds", "not applicable"], rows
    )


def write_run_report(record: RunRecord, root: str | Path = REPORTS_ROOT) -> Path:
    """Write a rendered report under the ignored generated tree.

    Args:
        record: the run record to render.
        root: output directory; defaults to ``reports/generated/reports``.

    Returns:
        The path written.

    Raises:
        ValueError: if the target is outside a ``reports/generated`` tree, since
            generated files must not land in the source tree.
    """
    target_root = Path(root)
    if "generated" not in target_root.parts:
        raise ValueError(f"reports must be written under a generated directory, got {target_root}")
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / f"{record.run_id}.md"
    target.write_text(render_run_report(record))
    return target
