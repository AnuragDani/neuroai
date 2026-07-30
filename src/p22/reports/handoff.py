"""Human-readable run summary for the evidence package (G9).

The manifest is for machines. This file is what a reader opens first, so it
leads with what was measured on real cells, what was blocked, and what decision
is owed next.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

SUMMARY_NAME = "SUMMARY.md"


def _table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join("" if value is None else str(value) for value in row) + " |")
    return "\n".join(lines)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def write_human_summary(run_dir: str | Path, manifest: dict[str, Any]) -> Path:
    """Write ``SUMMARY.md`` next to the manifest and CSVs."""
    root = Path(run_dir)
    root.mkdir(parents=True, exist_ok=True)
    gates = (manifest.get("gates") or {}).get("status_map") or {}
    stages = (manifest.get("data_size_stages") or {}).get("status_map") or {}
    buckets = manifest.get("evidence_buckets") or {}
    metrics = manifest.get("metric_rows") or []

    metric_rows = [
        (
            row.get("model"),
            row.get("layer"),
            row.get("status"),
            row.get("donor_balanced_accuracy"),
            row.get("bootstrap_lower"),
            row.get("bootstrap_upper"),
            row.get("not_applicable") or "",
        )
        for row in metrics
    ]

    sections = [
        f"# P22 run summary — `{manifest.get('run_id', 'unknown')}`",
        "",
        f"**Mode:** {(manifest.get('mode') or {}).get('mode', 'unknown')}  ",
        f"**Dataset:** `{manifest.get('dataset_id')}`  ",
        f"**Commit:** `{manifest.get('commit')}`  ",
        f"**Data layer:** {manifest.get('data_layer_label', 'unknown')}  ",
        f"**ATAC branch:** {manifest.get('atac_branch_label', 'unknown')}",
        "",
        "## Headline",
        "",
        _bullets(list(manifest.get("headline") or [])),
        "",
        "## Gate board",
        "",
        _table(
            ("gate", "status"),
            [(gate, status) for gate, status in sorted(gates.items())],
        ),
        "",
        "## Data-scale stages",
        "",
        _table(
            ("stage", "status"),
            [(stage, status) for stage, status in sorted(stages.items())],
        ),
        "",
        "## Donor-held-out model comparison",
        "",
        _table(
            (
                "model",
                "layer",
                "status",
                "donor balanced accuracy",
                "CI lower",
                "CI upper",
                "not applicable",
            ),
            metric_rows,
        )
        if metric_rows
        else "No model rows in this run.",
        "",
        "## Evidence separation",
        "",
        "### Verified on real cells",
        "",
        _bullets(list(buckets.get("verified_real") or [])),
        "",
        "### Metadata only",
        "",
        _bullets(list(buckets.get("metadata_only") or [])),
        "",
        "### Synthetic wiring (never disease evidence)",
        "",
        _bullets(list(buckets.get("synthetic") or [])),
        "",
        "### Blocked, unknown, or not applicable",
        "",
        _bullets(list(buckets.get("blocked_or_unknown") or [])),
        "",
        "## Limitations",
        "",
        _bullets(list(manifest.get("limitations") or [])),
        "",
        "## Next decision",
        "",
        f"**Owner:** {manifest.get('next_decision_owner', 'researcher')}  ",
        f"**Decision:** {manifest.get('decision', 'unknown')}  ",
        f"**Question:** {manifest.get('next_decision', 'unknown')}",
        "",
        "## Exact command",
        "",
        "```bash",
        str(manifest.get("exact_command", "unknown")),
        "```",
        "",
    ]
    target = root / SUMMARY_NAME
    target.write_text("\n".join(sections), encoding="utf-8")
    return target


def copy_executed_notebook(executed: str | Path, run_dir: str | Path) -> Path | None:
    """Place the executed notebook copy inside the run directory."""
    source = Path(executed)
    if not source.is_file():
        return None
    destination = Path(run_dir) / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination
