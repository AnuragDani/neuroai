"""Compact reproducible evidence package writer (G9)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_FILES = (
    "manifest.json",
    "metrics.csv",
    "interventions.csv",
    "validation.csv",
)


@dataclass
class EvidencePackage:
    """One compact run directory for professor review."""

    run_dir: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    metrics_rows: list[dict[str, Any]] = field(default_factory=list)
    intervention_rows: list[dict[str, Any]] = field(default_factory=list)
    validation_rows: list[dict[str, Any]] = field(default_factory=list)

    def write(self) -> dict[str, str]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        figures = self.run_dir / "figures"
        figures.mkdir(parents=True, exist_ok=True)
        manifest_path = self.run_dir / "manifest.json"
        metrics_path = self.run_dir / "metrics.csv"
        interventions_path = self.run_dir / "interventions.csv"
        validation_path = self.run_dir / "validation.csv"

        payload = dict(self.manifest)
        payload.setdefault("generated_at", datetime.now(UTC).isoformat(timespec="seconds"))
        payload.setdefault("package_files", list(REQUIRED_FILES) + ["figures/"])
        text = json.dumps(payload, indent=2, default=str) + "\n"
        manifest_path.write_text(text, encoding="utf-8")

        pd.DataFrame(self.metrics_rows).to_csv(metrics_path, index=False)
        pd.DataFrame(self.intervention_rows).to_csv(interventions_path, index=False)
        pd.DataFrame(self.validation_rows).to_csv(validation_path, index=False)

        return {
            "run_dir": str(self.run_dir),
            "manifest": str(manifest_path),
            "metrics": str(metrics_path),
            "interventions": str(interventions_path),
            "validation": str(validation_path),
            "figures": str(figures),
        }


def package_is_complete(run_dir: str | Path) -> tuple[bool, list[str]]:
    """Check that the lean G9 package files exist."""
    root = Path(run_dir)
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if not (root / "figures").is_dir():
        missing.append("figures/")
    return (not missing, missing)
