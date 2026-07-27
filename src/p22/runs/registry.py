"""Run records that carry enough context to replay and audit a result.

A record is only accepted when it can answer the questions a reviewer will ask: which
commit, which configuration, which data, which mode, which approval state, which seeds,
how many donors and cells, what was fitted on train, what was measured, and what the
result does not support. Missing provenance or an empty limitations list is refused.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

import p22

RUNS_ROOT = p22.REPO_ROOT / "reports" / "generated" / "runs"
SPLIT_NAMES = ("train", "val", "test")
REQUIRED_METRIC_KEYS = ("value", "not_applicable")


def current_git_commit(repo_root: str | Path | None = None) -> str:
    """Return the current commit hash.

    Args:
        repo_root: repository to inspect; defaults to the package repository root.

    Returns:
        The forty-character commit hash.

    Raises:
        RuntimeError: if the commit cannot be read, since a record without a commit
            cannot be replayed.
    """
    root = Path(repo_root) if repo_root is not None else p22.REPO_ROOT
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"could not read the git commit at {root}: {error}") from error
    return completed.stdout.strip()


def data_fingerprint(
    views: Mapping[str, np.ndarray],
    labels: Sequence[Any] | np.ndarray,
    donor_ids: Sequence[Any] | np.ndarray,
    decimals: int = 6,
) -> dict[str, Any]:
    """Summarise the exact arrays a run consumed.

    Args:
        views: mapping of view name to a two-dimensional feature matrix.
        labels: label per cell.
        donor_ids: donor identifier per cell.
        decimals: rounding applied before hashing, so trivial float noise does not
            change the fingerprint.

    Returns:
        A dictionary with a content hash, per-view shapes, cell and donor counts, and
        label counts.

    Raises:
        ValueError: if no view is given, a view is not two-dimensional, or the row
            counts disagree.
    """
    if not views:
        raise ValueError("data_fingerprint needs at least one view")
    label_array = np.asarray(labels)
    donor_array = np.asarray([str(value) for value in np.asarray(donor_ids)], dtype=object)
    if label_array.size != donor_array.size:
        raise ValueError(
            f"labels cover {label_array.size} cells but donor_ids cover {donor_array.size}"
        )

    digest = hashlib.sha256()
    shapes: dict[str, list[int]] = {}
    for name in sorted(views):
        matrix = np.asarray(views[name], dtype=np.float64)
        if matrix.ndim != 2:
            raise ValueError(f"view {name!r} must be two-dimensional, got shape {matrix.shape}")
        if matrix.shape[0] != label_array.size:
            raise ValueError(
                f"view {name!r} has {matrix.shape[0]} rows but labels cover "
                f"{label_array.size} cells"
            )
        shapes[name] = list(matrix.shape)
        digest.update(name.encode("utf-8"))
        digest.update(np.ascontiguousarray(np.round(matrix, decimals)).tobytes())
    digest.update(np.ascontiguousarray(label_array.astype(str)).tobytes())
    digest.update("|".join(donor_array.tolist()).encode("utf-8"))

    unique_labels, counts = np.unique(label_array, return_counts=True)
    return {
        "sha256": digest.hexdigest(),
        "views": shapes,
        "n_cells": int(label_array.size),
        "n_donors": int(np.unique(donor_array).size),
        "label_counts": {
            str(label): int(count) for label, count in zip(unique_labels, counts, strict=True)
        },
        "rounded_decimals": int(decimals),
    }


@dataclass(frozen=True)
class RunRecord:
    """Everything needed to replay one run and to judge what it supports."""

    run_id: str
    created_at: str
    git_commit: str
    config_hash: str
    config: dict[str, Any]
    data_fingerprint: dict[str, Any]
    data_mode: str
    approval_state: str
    seeds: tuple[int, ...]
    donor_counts: dict[str, int]
    cell_counts: dict[str, int]
    transform_metadata: dict[str, Any]
    model: str
    metrics: dict[str, dict[str, Any]]
    evidence_labels: tuple[str, ...]
    limitations: tuple[str, ...]
    routing_signals: dict[str, Any] = field(default_factory=dict)
    intervention_evidence: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_text("run_id", self.run_id)
        _check_text("created_at", self.created_at)
        _check_hex("git_commit", self.git_commit, 40)
        _check_hex("config_hash", self.config_hash, 64)
        if not self.config:
            raise ValueError("config must not be empty; a record without its config cannot replay")
        if not self.data_fingerprint.get("sha256"):
            raise ValueError("data_fingerprint must carry a sha256 of the arrays used")
        if self.data_mode not in p22.DATA_MODES:
            raise ValueError(f"unknown data_mode {self.data_mode!r}")
        p22.require_allowed_data_mode(self.data_mode)
        declared = self.config.get("data_mode")
        if declared is not None and declared != self.data_mode:
            raise ValueError(
                f"record data_mode {self.data_mode!r} disagrees with config data_mode {declared!r}"
            )
        _check_text("approval_state", self.approval_state)
        if not self.seeds:
            raise ValueError("seeds must record at least one seed")
        _check_counts("donor_counts", self.donor_counts)
        _check_counts("cell_counts", self.cell_counts)
        if not self.transform_metadata:
            raise ValueError("transform_metadata must record what was fitted and on which cells")
        if "fit_scope" not in self.transform_metadata:
            raise ValueError(
                "transform_metadata must state its fit_scope, for example 'train cells only'"
            )
        _check_text("model", self.model)
        _check_metrics(self.metrics)
        if not self.evidence_labels:
            raise ValueError("evidence_labels must not be empty")
        unknown = [label for label in self.evidence_labels if label not in p22.EVIDENCE_LABELS]
        if unknown:
            raise ValueError(f"unknown evidence label(s) {unknown}; expected {p22.EVIDENCE_LABELS}")
        if not self.limitations or any(not str(item).strip() for item in self.limitations):
            raise ValueError(
                "limitations must list at least one non-empty statement; an unqualified result "
                "is not reportable"
            )

    @classmethod
    def create(
        cls,
        config: Any,
        model: str,
        seeds: Sequence[int],
        data_fingerprint: Mapping[str, Any],
        donor_counts: Mapping[str, int],
        cell_counts: Mapping[str, int],
        transform_metadata: Mapping[str, Any],
        metrics: Mapping[str, Mapping[str, Any]],
        evidence_labels: Sequence[str],
        limitations: Sequence[str] | None = None,
        routing_signals: Mapping[str, Any] | None = None,
        intervention_evidence: Mapping[str, Any] | None = None,
        notes: Sequence[str] = (),
        git_commit: str | None = None,
        created_at: str | None = None,
        run_id: str | None = None,
    ) -> RunRecord:
        """Assemble a record, filling commit, timestamp, and run identifier.

        Args:
            config: a ``RunConfig``.
            model: the model name this record describes.
            seeds: seeds actually executed.
            data_fingerprint: output of :func:`data_fingerprint`.
            donor_counts: donors per split.
            cell_counts: cells per split.
            transform_metadata: metadata from the fitted, frozen transform.
            metrics: metric name to a mapping with ``value`` and ``not_applicable``.
            evidence_labels: labels describing how the numbers should be read.
            limitations: statements the run does not support; defaults to the
                configuration's own limitations.
            routing_signals: routing summaries, kept apart from performance.
            intervention_evidence: intervention summaries, kept apart from performance.
            notes: free-text notes.
            git_commit: override the commit lookup.
            created_at: override the timestamp.
            run_id: override the generated identifier.

        Returns:
            A validated :class:`RunRecord`.
        """
        commit = git_commit if git_commit is not None else current_git_commit()
        stamp = created_at if created_at is not None else datetime.now(UTC).isoformat()
        config_hash = config.config_hash
        seed_tuple = tuple(int(seed) for seed in seeds)
        identifier = run_id or "-".join(
            [
                str(config.name),
                str(model),
                "seeds" + "_".join(str(seed) for seed in seed_tuple),
                config_hash[:8],
                commit[:8],
            ]
        )
        stated = tuple(limitations) if limitations is not None else tuple(config.limitations)
        return cls(
            run_id=identifier,
            created_at=stamp,
            git_commit=commit,
            config_hash=config_hash,
            config=config.to_dict(),
            data_fingerprint=dict(data_fingerprint),
            data_mode=config.data_mode,
            approval_state="blocked" if p22.approval_blocked() else "approved",
            seeds=seed_tuple,
            donor_counts={key: int(value) for key, value in donor_counts.items()},
            cell_counts={key: int(value) for key, value in cell_counts.items()},
            transform_metadata=dict(transform_metadata),
            model=str(model),
            metrics={name: dict(entry) for name, entry in metrics.items()},
            evidence_labels=tuple(evidence_labels),
            limitations=stated,
            routing_signals=dict(routing_signals or {}),
            intervention_evidence=dict(intervention_evidence or {}),
            notes=tuple(notes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "git_commit": self.git_commit,
            "config_hash": self.config_hash,
            "config": self.config,
            "data_fingerprint": self.data_fingerprint,
            "data_mode": self.data_mode,
            "approval_state": self.approval_state,
            "seeds": list(self.seeds),
            "donor_counts": self.donor_counts,
            "cell_counts": self.cell_counts,
            "transform_metadata": self.transform_metadata,
            "model": self.model,
            "metrics": self.metrics,
            "evidence_labels": list(self.evidence_labels),
            "limitations": list(self.limitations),
            "routing_signals": self.routing_signals,
            "intervention_evidence": self.intervention_evidence,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RunRecord:
        """Rebuild a record from its serialised form, revalidating as it goes."""
        return cls(
            run_id=str(payload["run_id"]),
            created_at=str(payload["created_at"]),
            git_commit=str(payload["git_commit"]),
            config_hash=str(payload["config_hash"]),
            config=dict(payload["config"]),
            data_fingerprint=dict(payload["data_fingerprint"]),
            data_mode=str(payload["data_mode"]),
            approval_state=str(payload["approval_state"]),
            seeds=tuple(int(seed) for seed in payload["seeds"]),
            donor_counts={key: int(value) for key, value in payload["donor_counts"].items()},
            cell_counts={key: int(value) for key, value in payload["cell_counts"].items()},
            transform_metadata=dict(payload["transform_metadata"]),
            model=str(payload["model"]),
            metrics={name: dict(entry) for name, entry in payload["metrics"].items()},
            evidence_labels=tuple(payload["evidence_labels"]),
            limitations=tuple(payload["limitations"]),
            routing_signals=dict(payload.get("routing_signals", {})),
            intervention_evidence=dict(payload.get("intervention_evidence", {})),
            notes=tuple(payload.get("notes", ())),
        )


class RunRegistry:
    """Stores run records as JSON under an ignored generated directory."""

    def __init__(self, root: str | Path = RUNS_ROOT) -> None:
        self.root = Path(root)

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def write(self, record: RunRecord) -> Path:
        """Write a record to disk and return its path.

        Raises:
            FileExistsError: if a record with the same identifier is already stored,
                so a result is never silently replaced.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path_for(record.run_id)
        if target.exists():
            raise FileExistsError(f"run record already exists: {target}")
        target.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n")
        return target

    def load(self, run_id: str) -> RunRecord:
        target = self.path_for(run_id)
        if not target.is_file():
            raise FileNotFoundError(f"run record not found: {target}")
        return RunRecord.from_dict(json.loads(target.read_text()))

    def run_ids(self) -> tuple[str, ...]:
        if not self.root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))

    def load_all(self) -> tuple[RunRecord, ...]:
        return tuple(self.load(run_id) for run_id in self.run_ids())


def _check_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")


def _check_hex(name: str, value: Any, length: int) -> None:
    _check_text(name, value)
    if len(value) != length or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"{name} must be {length} hexadecimal characters, got {value!r}")


def _check_counts(name: str, counts: Mapping[str, int]) -> None:
    missing = [split for split in SPLIT_NAMES if split not in counts]
    if missing:
        raise ValueError(f"{name} is missing split(s) {missing}")
    unexpected = [split for split in counts if split not in SPLIT_NAMES]
    if unexpected:
        raise ValueError(f"{name} has unexpected split(s) {sorted(unexpected)}")
    for split, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name}[{split!r}] must be a positive int, got {value!r}")


def _check_metrics(metrics: Mapping[str, Mapping[str, Any]]) -> None:
    if not metrics:
        raise ValueError("metrics must not be empty")
    for name, entry in metrics.items():
        if not isinstance(entry, Mapping):
            raise ValueError(f"metric {name!r} must map to a mapping, got {type(entry).__name__}")
        missing = [key for key in REQUIRED_METRIC_KEYS if key not in entry]
        if missing:
            raise ValueError(f"metric {name!r} is missing key(s) {missing}")
        value = entry["value"]
        if value is None:
            if not str(entry["not_applicable"] or "").strip():
                raise ValueError(f"metric {name!r} has no value and no reason")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"metric {name!r} value must be a number or None, got {value!r}")
        if not np.isfinite(value):
            raise ValueError(
                f"metric {name!r} value is {value!r}; record an explicit not_applicable reason "
                "instead of a non-finite number"
            )
