#!/usr/bin/env python3
"""Build and verify the manifest for the legacy Tasic proxy-view experiment.

The legacy experiment is read-only evidence. This script never writes into
``experiments/``; it records byte size, SHA-256, generator, and evidence label so
that later work cannot silently reinterpret or overwrite those outputs.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "legacy" / "tasic_proxy_view" / "manifest.json"

GENERATOR_SCRIPT = "experiments/run_tasic2018_pipeline.py"

EXPECTED_FILES: tuple[dict[str, str], ...] = (
    {
        "relative_path": GENERATOR_SCRIPT,
        "generator": "human-authored legacy script",
        "evidence_label": "verified",
        "description": (
            "Legacy pipeline that builds two views from one RNA count matrix and trains "
            "single-view, concatenation, and attention-fusion classifiers."
        ),
    },
    {
        "relative_path": "experiments/tasic2018_summary.json",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": (
            "Dataset counts, per-model metrics with cell-level intervals, paired test, "
            "mutual information."
        ),
    },
    {
        "relative_path": "experiments/tasic2018_broadtype_metrics.csv",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": "Four-class task metrics per model; accuracy saturates at or near 1.0.",
    },
    {
        "relative_path": "experiments/tasic2018_finegrained_metrics.csv",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": "130-class task metrics per model, single seed.",
    },
    {
        "relative_path": "experiments/tasic2018_attn_broadtype.csv",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": "Per-class mean attention weight over the two views, four-class task.",
    },
    {
        "relative_path": "experiments/tasic2018_attn_finegrained.csv",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": "Per-class mean attention weight over the two views, 130-class task.",
    },
    {
        "relative_path": "experiments/tasic2018_mcnemar.json",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": (
            "Paired test comparing attention fusion with concatenation fusion, 130-class task."
        ),
    },
    {
        "relative_path": "experiments/tasic2018_mutual_information.json",
        "generator": GENERATOR_SCRIPT,
        "evidence_label": "experimental result",
        "description": (
            "Mutual information between each view and the label, and between paired features."
        ),
    },
)

BOUNDARY = (
    "Both views are derived from one RNA count matrix: view one is highly variable gene "
    "expression, view two is a principal component projection of the same matrix.",
    "This is an architecture proof of concept, not independent two-modality validation.",
    "This is not condition-specific evidence and contains no clinical cohort.",
    "Attention weights are routing signals; no intervention test supports treating them as "
    "explanations.",
    "The projection for view two was fitted on all cells before splitting, so leakage cannot be "
    "ruled out.",
    "Splits were stratified over cells with one seed; no donor grouping and no seed variability "
    "estimate.",
    "Reported intervals were resampled over test cells, not over donors.",
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(131072), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_files(repo: Path = REPO_ROOT) -> list[dict[str, object]]:
    """Return manifest records for every expected legacy file.

    Raises:
        FileNotFoundError: if an expected legacy file is missing.
    """
    records: list[dict[str, object]] = []
    for expected in EXPECTED_FILES:
        target = repo / str(expected["relative_path"])
        if not target.is_file():
            raise FileNotFoundError(f"expected legacy file is missing: {expected['relative_path']}")
        records.append(
            {
                "relative_path": expected["relative_path"],
                "bytes": target.stat().st_size,
                "sha256": sha256_of(target),
                "generator": expected["generator"],
                "evidence_label": expected["evidence_label"],
                "description": expected["description"],
            }
        )
    return records


def build_manifest(repo: Path = REPO_ROOT) -> dict[str, object]:
    return {
        "manifest_version": "1",
        "recorded_for_step": "C02",
        "data_mode": "legacy read-only",
        "source_dataset": {
            "reference": "Tasic et al. 2018 mouse cortex SMART-seq",
            "accession": "GSE115746",
            "matrix_tracked_in_repository": False,
            "donor_identifiers_available_in_outputs": "unknown",
        },
        "boundary": list(BOUNDARY),
        "files": collect_files(repo),
    }


def verify_manifest(manifest: dict[str, object], repo: Path = REPO_ROOT) -> list[str]:
    """Return one problem string per drift between the manifest and disk."""
    problems: list[str] = []
    recorded = {str(entry["relative_path"]): entry for entry in manifest.get("files", [])}
    expected_paths = [str(entry["relative_path"]) for entry in EXPECTED_FILES]

    for path in expected_paths:
        if path not in recorded:
            problems.append(f"manifest is missing expected file: {path}")
    for path in recorded:
        if path not in expected_paths:
            problems.append(f"manifest records an unexpected file: {path}")

    for path, entry in sorted(recorded.items()):
        target = repo / path
        if not target.is_file():
            problems.append(f"manifested file disappeared: {path}")
            continue
        size = target.stat().st_size
        if size != entry.get("bytes"):
            problems.append(f"byte size changed for {path}: {entry.get('bytes')} -> {size}")
        digest = sha256_of(target)
        if digest != entry.get("sha256"):
            problems.append(f"checksum changed for {path}")
    return problems


def write_manifest(repo: Path = REPO_ROOT) -> Path:
    manifest = build_manifest(repo)
    path = repo / "legacy" / "tasic_proxy_view" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args(argv)

    if args.command == "build":
        path = write_manifest()
        print(f"wrote {path.relative_to(REPO_ROOT)} with {len(EXPECTED_FILES)} files")
        return 0

    problems = verify_manifest(load_manifest())
    for problem in problems:
        print(f"FAIL: {problem}")
    print("PASS: legacy manifest matches disk" if not problems else "FAIL: legacy manifest drifted")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
