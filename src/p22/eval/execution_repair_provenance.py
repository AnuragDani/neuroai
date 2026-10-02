"""E0 portable provenance helpers for execution repair (2026-10-02).

Resolves measured ATAC pilot inputs under the primary checkout and verifies
archive / digest contracts without requiring removed worktrees.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from p22.eval.s7_ledger import sha256_file

PORTABLE_INPUTS_REL = "configs/execution_repair_portable_inputs_2026-10-02.json"
DEFAULT_H5AD_REL = "data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
DEFAULT_ATAC_REL = (
    "reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz"
)
EXPECTED_MATRIX_SHA256 = (
    "5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969"
)
EXPECTED_ORDERED_CELLS_SHA256 = (
    "7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53"
)
EXPECTED_UNION_BED_SHA256 = (
    "d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23"
)
EXPECTED_REGION_SETS_SHA256 = (
    "13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407"
)


class PortableProvenanceError(ValueError):
    """Refuse when portable inputs or archive digests fail."""


def load_portable_inputs(workspace: Path) -> dict[str, Any]:
    path = Path(workspace) / PORTABLE_INPUTS_REL
    if not path.is_file():
        raise PortableProvenanceError(f"missing portable inputs contract: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_portable_path(workspace: Path, key: str) -> Path:
    contract = load_portable_inputs(workspace)
    try:
        rel = contract["paths"][key]
    except KeyError as exc:
        raise PortableProvenanceError(f"unknown portable path key: {key}") from exc
    return (Path(workspace) / rel).resolve()


def default_h5ad_path(workspace: Path) -> Path:
    return (Path(workspace) / DEFAULT_H5AD_REL).resolve()


def default_atac_path(workspace: Path) -> Path:
    return (Path(workspace) / DEFAULT_ATAC_REL).resolve()


def _check_file_sha(path: Path, expected: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "match": False,
        }
    got = sha256_file(path)
    return {
        "path": str(path),
        "exists": True,
        "sha256": got,
        "expected_sha256": expected,
        "match": got == expected,
    }


def verify_measured_inputs(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    contract = load_portable_inputs(workspace)
    expected = contract["expected_sha256"]
    atac = resolve_portable_path(workspace, "atac_counts_npz")
    bed = resolve_portable_path(workspace, "union_bed")
    regions = resolve_portable_path(workspace, "region_sets")
    counts_json = resolve_portable_path(workspace, "atac_counts_json")
    h5ad = resolve_portable_path(workspace, "h5ad")

    matrix = _check_file_sha(atac, expected["atac_counts_npz"])
    bed_check = _check_file_sha(bed, expected["union_bed"])
    region_check = _check_file_sha(regions, expected["region_sets"])

    cells_match = False
    cells_sha = None
    if counts_json.is_file():
        meta = json.loads(counts_json.read_text(encoding="utf-8"))
        cells_sha = meta.get("cells_sha256")
        cells_match = cells_sha == expected["ordered_cells"]

    former_atac = Path(
        contract["historical_absolute_paths"]["former_atac_counts_npz"]
    )
    return {
        "matrix": matrix,
        "union_bed": bed_check,
        "region_sets": region_check,
        "ordered_cells_from_counts_json": {
            "path": str(counts_json),
            "exists": counts_json.is_file(),
            "sha256": cells_sha,
            "expected_sha256": expected["ordered_cells"],
            "match": cells_match,
        },
        "h5ad": {
            "path": str(h5ad),
            "exists": h5ad.is_file(),
            "bytes": h5ad.stat().st_size if h5ad.is_file() else None,
        },
        "former_worktree_atac_resolves": former_atac.is_file(),
        "portable_defaults": {
            "h5ad_rel": DEFAULT_H5AD_REL,
            "atac_rel": DEFAULT_ATAC_REL,
            "h5ad_resolved": str(default_h5ad_path(workspace)),
            "atac_resolved": str(default_atac_path(workspace)),
        },
        "all_required_digests_match": all(
            [
                matrix["match"],
                bed_check["match"],
                region_check["match"],
                cells_match,
                h5ad.is_file(),
                not former_atac.is_file(),
            ]
        ),
    }


def verify_archives(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    inventory_path = resolve_portable_path(workspace, "consolidation_inventory")
    manifest_path = resolve_portable_path(workspace, "archive_manifest")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if inventory != manifest:
        raise PortableProvenanceError(
            "docs/CONSOLIDATION_2026-10-02.json != archive_manifest.json"
        )

    archive_checks: list[dict[str, Any]] = []
    live_missing: list[str] = []
    for entry in inventory:
        archive = workspace / entry["archive"]
        live = Path(entry["path"])
        if not live.exists():
            live_missing.append(entry["path"])
        if not archive.is_file():
            archive_checks.append(
                {
                    "archive": entry["archive"],
                    "exists": False,
                    "match": False,
                }
            )
            continue
        got = sha256_file(archive)
        archive_checks.append(
            {
                "archive": entry["archive"],
                "exists": True,
                "sha256": got,
                "expected_sha256": entry["sha256"],
                "bytes": archive.stat().st_size,
                "expected_bytes": entry["archive_bytes"],
                "match": got == entry["sha256"]
                and archive.stat().st_size == entry["archive_bytes"],
                "live_path_exists": live.exists(),
            }
        )

    n_ok = sum(1 for row in archive_checks if row["match"])
    return {
        "n_archives": len(inventory),
        "n_archives_hash_ok": n_ok,
        "all_archives_match": n_ok == len(inventory),
        "n_live_worktrees_missing": len(live_missing),
        "all_live_worktrees_absent": len(live_missing) == len(inventory),
        "live_worktrees_missing_sample": live_missing[:3],
        "archives": archive_checks,
    }


def verify_pilot_sidecars(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    pins_path = resolve_portable_path(workspace, "m10_pre_replay_pins")
    pins = json.loads(pins_path.read_text(encoding="utf-8"))
    pred_dir = resolve_portable_path(workspace, "pilot_predictions")
    expected = pins["prediction_sidecar_sha256"]
    rows: list[dict[str, Any]] = []
    for name, want in sorted(expected.items()):
        path = pred_dir / name
        if not path.is_file():
            rows.append({"name": name, "exists": False, "match": False})
            continue
        got = sha256_file(path)
        rows.append(
            {
                "name": name,
                "exists": True,
                "sha256": got,
                "expected_sha256": want,
                "match": got == want,
            }
        )

    ledger_rows: list[dict[str, Any]] = []
    for rel, want in pins["ledger_pins"].items():
        path = workspace / rel
        if not path.is_file():
            ledger_rows.append({"path": rel, "exists": False, "match": False})
            continue
        got = sha256_file(path)
        ledger_rows.append(
            {
                "path": rel,
                "exists": True,
                "sha256": got,
                "expected_sha256": want,
                "match": got == want,
            }
        )

    n_ok = sum(1 for row in rows if row["match"])
    n_ledger_ok = sum(1 for row in ledger_rows if row["match"])
    return {
        "n_sidecars_expected": len(expected),
        "n_sidecars_match": n_ok,
        "all_sidecars_match": n_ok == len(expected),
        "n_ledger_pins_match": n_ledger_ok,
        "all_ledger_pins_match": n_ledger_ok == len(pins["ledger_pins"]),
        "sidecars": rows,
        "ledger_pins": ledger_rows,
    }


def build_provenance_report(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    contract = load_portable_inputs(workspace)
    measured = verify_measured_inputs(workspace)
    archives = verify_archives(workspace)
    sidecars = verify_pilot_sidecars(workspace)
    disposition = (
        "PORTABLE_PROVENANCE_PASS"
        if (
            measured["all_required_digests_match"]
            and archives["all_archives_match"]
            and archives["all_live_worktrees_absent"]
            and sidecars["all_sidecars_match"]
            and sidecars["all_ledger_pins_match"]
        )
        else "PORTABLE_PROVENANCE_FAIL"
    )
    return {
        "disposition": disposition,
        "stage": "E0",
        "contract": PORTABLE_INPUTS_REL,
        "scientific_status_unchanged": contract["scientific_status_unchanged"],
        "measured_inputs": measured,
        "archives": {
            "n_archives": archives["n_archives"],
            "n_archives_hash_ok": archives["n_archives_hash_ok"],
            "all_archives_match": archives["all_archives_match"],
            "n_live_worktrees_missing": archives["n_live_worktrees_missing"],
            "all_live_worktrees_absent": archives["all_live_worktrees_absent"],
            "live_worktrees_missing_sample": archives["live_worktrees_missing_sample"],
        },
        "pilot_sidecars": {
            "n_sidecars_expected": sidecars["n_sidecars_expected"],
            "n_sidecars_match": sidecars["n_sidecars_match"],
            "all_sidecars_match": sidecars["all_sidecars_match"],
            "n_ledger_pins_match": sidecars["n_ledger_pins_match"],
            "all_ledger_pins_match": sidecars["all_ledger_pins_match"],
        },
        "missing_older_dependencies": contract["missing_live_dependencies"],
        "historical_absolute_paths": contract["historical_absolute_paths"],
        "checks": {
            "canonical_paths_resolve_without_worktrees": measured[
                "all_required_digests_match"
            ]
            and not measured["former_worktree_atac_resolves"],
            "archives_immutable_hashes_ok": archives["all_archives_match"],
            "pilot_sidecars_retain_exact_hashes": sidecars["all_sidecars_match"]
            and sidecars["all_ledger_pins_match"],
            "zero_research_fits": True,
        },
    }
