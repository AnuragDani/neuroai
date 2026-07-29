"""Runtime and path safety checks for the one-notebook workflow (G0)."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeReport:
    """Machine and path facts needed before any scientific gate."""

    status: str
    python_version: str
    platform: str
    project_root: str
    data_root: str
    output_root: str
    source_notebook: str
    executed_copy_root: str
    disk_free_gb: float | None
    cpu_count: int | None
    ram_total_gb: float | None
    device: str
    blocking_problems: tuple[str, ...]
    open_questions: tuple[str, ...]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "python_version": self.python_version,
            "platform": self.platform,
            "project_root": self.project_root,
            "data_root": self.data_root,
            "output_root": self.output_root,
            "source_notebook": self.source_notebook,
            "executed_copy_root": self.executed_copy_root,
            "disk_free_gb": self.disk_free_gb,
            "cpu_count": self.cpu_count,
            "ram_total_gb": self.ram_total_gb,
            "device": self.device,
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "generated_at": self.generated_at,
        }


def _ram_total_gb() -> float | None:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        return round((page_size * phys_pages) / 1e9, 3)
    except (AttributeError, OSError, ValueError):
        return None


def _device_name() -> str:
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def resolve_project_root(cwd: str | Path | None = None) -> Path:
    """Locate the repository root from cwd or parents containing pyproject.toml."""
    start = Path(cwd or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "p22").is_dir():
            return candidate
    return start


def assert_output_does_not_overwrite_source(
    source_notebook: Path,
    output_root: Path,
) -> list[str]:
    """Return blocking problems if output paths collide with the source notebook."""
    problems: list[str] = []
    source = source_notebook.resolve()
    output = output_root.resolve()
    if output == source or output == source.parent:
        problems.append("output_root collides with source notebook path")
    if "reports/generated" not in str(output).replace("\\", "/"):
        problems.append("output_root should live under reports/generated/")
    return problems


def collect_runtime_report(
    project_root: str | Path | None = None,
    data_root: str | Path | None = None,
    output_root: str | Path | None = None,
    source_notebook: str | Path | None = None,
    min_disk_gb: float = 5.0,
) -> RuntimeReport:
    """Collect G0 runtime facts and return PASS/INCONCLUSIVE/BLOCKED."""
    root = resolve_project_root(project_root)
    data = Path(data_root or root / "data" / "real")
    output = Path(output_root or root / "reports" / "generated" / "verification" / "down_syndrome")
    source = Path(source_notebook or root / "P22_down_syndrome_all_in_one.ipynb")
    executed_root = root / "reports" / "generated" / "notebooks"

    blocking: list[str] = []
    unknowns: list[str] = []

    data.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    executed_root.mkdir(parents=True, exist_ok=True)

    blocking.extend(assert_output_does_not_overwrite_source(source, output))
    if not source.is_file():
        blocking.append(f"source notebook missing: {source}")

    disk_free_gb: float | None
    try:
        usage = shutil.disk_usage(output)
        disk_free_gb = round(usage.free / 1e9, 3)
        if disk_free_gb < min_disk_gb:
            blocking.append(f"free disk {disk_free_gb} GB is below minimum {min_disk_gb} GB")
    except OSError as error:
        disk_free_gb = None
        unknowns.append(f"disk usage unavailable: {error}")

    probe = output / "g0_write_probe.txt"
    try:
        probe.write_text("ok\n", encoding="utf-8")
    except OSError as error:
        blocking.append(f"cannot write under output_root: {error}")

    if sys.version_info[:2] != (3, 11):
        unknowns.append(f"expected Python 3.11 kernel, got {sys.version.split()[0]}")

    status = "BLOCKED" if blocking else ("INCONCLUSIVE" if unknowns else "PASS")
    return RuntimeReport(
        status=status,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        project_root=str(root),
        data_root=str(data),
        output_root=str(output),
        source_notebook=str(source),
        executed_copy_root=str(executed_root),
        disk_free_gb=disk_free_gb,
        cpu_count=os.cpu_count(),
        ram_total_gb=_ram_total_gb(),
        device=_device_name(),
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
