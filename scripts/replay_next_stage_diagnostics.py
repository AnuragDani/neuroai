#!/usr/bin/env python3
"""Q1 bounded replay of next_stage_20260930 saved diagnostics.

Reproduces DATA_DIAGNOSTIC, MEASUREMENT_AUDIT and TARGETED_SAMPLING_FEASIBILITY
from shared read-only inputs using existing loaders/sampler. Writes fresh JSON
under a new raw root; refuses overwrite, missing columns, hash/order mismatches
and expected-golden drift. No fits, RNA dense-atlas load or downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.data.nn_sampling import sample_donor_stratified_cells  # noqa: E402

DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_SAMPLING = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/docs/nn_v2/sampling_cap1000_seed22.json"
)
DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8/reports/generated/"
    "atac_tiebreak_measured_20260921/counts/counts.npz"
)
DEFAULT_LADDER_VERIFICATION = ROOT / "docs" / "nn_v2" / "ladder_verification.json"
DEFAULT_EXPECTED = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
OBS_COLUMNS = (
    "donor_id",
    "disease",
    "author_cell_type",
    "library",
    "dev_PCW",
    "nCount_RNA",
    "nCount_ATAC",
)
CELL_TYPE_ORDER = (
    "AST",
    "IPC",
    "IPC_prol",
    "MIC",
    "NEU_CALB2",
    "NEU_CUX2",
    "NEU_RELN",
    "NEU_RORB",
    "NEU_SST",
    "NEU_TLE4",
    "NEU_low",
    "OPC",
    "RG",
    "RG_prol",
    "VASC",
)
SUPPORT_CUTOFF = 20
TARGETED_CAP = 64
TARGETED_SEED = 22


class DiagnosticReplayError(RuntimeError):
    """Nonzero-exit diagnostic failure with a useful message."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def donor_class(donor_id: str) -> str:
    if "_CON_" in donor_id:
        return "CON"
    if "_DS_" in donor_id:
        return "DS"
    raise DiagnosticReplayError(f"cannot parse class from donor_id={donor_id!r}")


def donor_age(donor_id: str) -> str:
    match = re.match(r"PCW(\d+)_", donor_id)
    if not match:
        raise DiagnosticReplayError(f"cannot parse age from donor_id={donor_id!r}")
    return match.group(1)


def require_columns(obs: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in obs.columns]
    if missing:
        raise DiagnosticReplayError(f"missing required columns: {missing}")


def load_obs(h5ad_path: Path, columns: tuple[str, ...] = OBS_COLUMNS) -> pd.DataFrame:
    import anndata as ad

    if not h5ad_path.is_file():
        raise DiagnosticReplayError(f"h5ad not found: {h5ad_path}")
    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        require_columns(backed.obs, columns)
        obs = backed.obs[list(columns)].copy()
        obs.index = obs.index.astype(str)
    finally:
        backed.file.close()
    for column in ("donor_id", "disease", "author_cell_type", "library", "dev_PCW"):
        if column in obs.columns:
            obs[column] = obs[column].astype(str)
    for column in ("nCount_RNA", "nCount_ATAC"):
        if column in obs.columns:
            obs[column] = pd.to_numeric(obs[column], errors="coerce")
    return obs


def ordered_cell_ids(h5ad_path: Path) -> list[str]:
    import anndata as ad

    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        return [str(cell_id) for cell_id in backed.obs.index.tolist()]
    finally:
        backed.file.close()


def age_counts_from_donors(donor_ids: list[str]) -> dict[str, dict[str, int]]:
    ages: dict[str, dict[str, int]] = {}
    for donor in donor_ids:
        age = donor_age(donor)
        cls = donor_class(donor)
        ages.setdefault(age, {})
        ages[age][cls] = ages[age].get(cls, 0) + 1
    return {age: ages[age] for age in sorted(ages, key=int)}


def cell_type_support_ge20(primary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell_type in CELL_TYPE_ORDER:
        row: dict[str, Any] = {"cell_type": cell_type}
        for cls in ("CON", "DS"):
            available = 0
            selected = 0
            for donor, info in primary["donors"].items():
                if donor_class(donor) != cls:
                    continue
                if int(info["cell_type_available"].get(cell_type, 0)) >= SUPPORT_CUTOFF:
                    available += 1
                if int(info["cell_type_selected"].get(cell_type, 0)) >= SUPPORT_CUTOFF:
                    selected += 1
            row[cls] = {
                "cell_type_available_donors_ge20": available,
                "cell_type_selected_donors_ge20": selected,
            }
        rows.append(row)
    return rows


def crosscheck_h5ad_metadata(obs: pd.DataFrame, sampling_primary: dict[str, Any]) -> dict:
    problems: list[str] = []
    if int(len(obs)) != int(sampling_primary["n_cells_available"]):
        problems.append(
            "cell count mismatch: "
            f"h5ad={len(obs)} sampling={sampling_primary['n_cells_available']}"
        )
    donors = sorted(obs["donor_id"].astype(str).unique().tolist())
    if donors != sorted(sampling_primary["donors"]):
        problems.append("donor id set mismatch versus sampling record")
    for donor, group in obs.groupby("donor_id", observed=True):
        donor = str(donor)
        expected = int(sampling_primary["donors"][donor]["available"])
        if int(len(group)) != expected:
            problems.append(f"donor available count mismatch for {donor}")
        avail = group["author_cell_type"].value_counts().to_dict()
        for cell_type, count in sampling_primary["donors"][donor]["cell_type_available"].items():
            if int(avail.get(cell_type, 0)) != int(count):
                problems.append(
                    f"donor/cell-type available mismatch {donor}/{cell_type}"
                )
        meta_ages = {str(int(float(value))) for value in group["dev_PCW"].unique()}
        parsed = donor_age(donor)
        if meta_ages != {parsed}:
            problems.append(f"age metadata disagrees with donor id for {donor}")
    if problems:
        raise DiagnosticReplayError(
            "fresh_h5ad_metadata_crosscheck FAIL: " + "; ".join(problems[:8])
        )
    return {
        "status": "PASS",
        "cells": int(len(obs)),
        "donors": int(obs["donor_id"].nunique()),
        "checks": [
            "all donor counts",
            "all donor/cell-type available counts",
            "age metadata agrees with donor ID",
        ],
        "scope": (
            "obs metadata only; expression/ATAC values not read; "
            "whole-file checksum not recomputed"
        ),
    }


def build_data_diagnostic(
    *,
    sampling_path: Path,
    obs: pd.DataFrame,
    ladder_verification: dict[str, Any],
    date: str = "2026-09-30",
) -> dict[str, Any]:
    if not sampling_path.is_file():
        raise DiagnosticReplayError(f"sampling record not found: {sampling_path}")
    source_sha = sha256_file(sampling_path)
    sampling = json.loads(sampling_path.read_text())
    primary = sampling["primary"]
    classes = {"CON": 0, "DS": 0}
    for donor in primary["donors"]:
        classes[donor_class(donor)] += 1
    primary_contrast = ladder_verification.get("primary_recomputed")
    if not isinstance(primary_contrast, dict):
        raise DiagnosticReplayError("ladder verification missing primary_recomputed")
    return {
        "record_type": "saved_record_dataset_diagnostic",
        "date": date,
        "source": str(sampling_path),
        "source_sha256": source_sha,
        "donors": int(primary["n_donors"]),
        "classes": classes,
        "available_cells": int(primary["n_cells_available"]),
        "selected_cells": int(primary["n_cells_selected"]),
        "age_counts_from_donor_ids": age_counts_from_donors(list(primary["donors"])),
        "cell_type_support": cell_type_support_ge20(primary),
        "support_cutoff_note": (
            "20 cells/donor is descriptive screening only; "
            "not an accepted inference or power gate"
        ),
        "primary": {
            "estimate": primary_contrast["estimate"],
            "ci": list(primary_contrast["ci"]),
            "valid_draws": primary_contrast["valid_draws"],
            "margin": primary_contrast["margin"],
            "advantage": primary_contrast["advantage"],
        },
        "diagnostic_limits": [
            "Saved sampling records, not fresh H5AD QC replay.",
            "Age parsed from donor IDs, requires metadata check before adjustment.",
            "More cells do not add independent donors.",
            "Cannot attribute null to dataset or model from these counts.",
        ],
        "fresh_h5ad_metadata_crosscheck": crosscheck_h5ad_metadata(obs, primary),
    }


def build_targeted_sampling(obs: pd.DataFrame) -> dict[str, Any]:
    require_columns(obs, ("donor_id", "author_cell_type", "library"))
    selected: dict[str, list[str]] = {}
    for cell_type in CELL_TYPE_ORDER:
        sub = obs[obs["author_cell_type"].astype(str) == cell_type]
        if sub.empty:
            raise DiagnosticReplayError(f"no cells for cell_type={cell_type}")
        rows = sample_donor_stratified_cells(sub, cap=TARGETED_CAP, seed=TARGETED_SEED)
        selected[cell_type] = [str(cell_id) for cell_id in sub.index.to_numpy()[rows]]
    return {
        "scope": "descriptive, no fits",
        "cap_per_donor_per_type": TARGETED_CAP,
        "seed": TARGETED_SEED,
        "sampler": "p22.data.nn_sampling.sample_donor_stratified_cells",
        "selected_cell_ids_by_type": selected,
    }


def build_measurement_audit(
    *,
    obs: pd.DataFrame,
    h5ad_path: Path,
    atac_npz: Path,
    union_bed: Path,
    date: str = "2026-09-30",
    require_matrix_sha256: str | None = None,
    require_ordered_cells_sha256: str | None = None,
    require_bed_sha256: str | None = None,
) -> dict[str, Any]:
    require_columns(
        obs,
        ("donor_id", "author_cell_type", "library", "nCount_RNA", "nCount_ATAC"),
    )
    if not atac_npz.is_file():
        raise DiagnosticReplayError(f"ATAC counts not found: {atac_npz}")
    if not union_bed.is_file():
        raise DiagnosticReplayError(f"union BED not found: {union_bed}")

    matrix_sha = sha256_file(atac_npz)
    bed_sha = sha256_file(union_bed)
    cells = ordered_cell_ids(h5ad_path)
    ordered_sha = sha256_text(cells)
    if len(cells) != len(obs):
        raise DiagnosticReplayError("ordered cell count does not match loaded obs")

    sidecar_path = atac_npz.with_name("counts.json")
    if sidecar_path.is_file():
        sidecar = json.loads(sidecar_path.read_text())
        sidecar_cells = sidecar.get("cells_sha256")
        if sidecar_cells and sidecar_cells != ordered_sha:
            raise DiagnosticReplayError(
                "ordered-cell hash differs from ATAC sidecar cells_sha256 "
                f"(got {ordered_sha}, expected {sidecar_cells})"
            )
        if list(sidecar.get("shape", [])) and list(sidecar["shape"])[1] != len(cells):
            raise DiagnosticReplayError("sidecar cell axis length mismatch")

    if require_matrix_sha256 and matrix_sha != require_matrix_sha256:
        raise DiagnosticReplayError(
            f"matrix sha256 mismatch: got {matrix_sha}, "
            f"required {require_matrix_sha256}"
        )
    if require_ordered_cells_sha256 and ordered_sha != require_ordered_cells_sha256:
        raise DiagnosticReplayError(
            f"ordered-cell sha256 mismatch: got {ordered_sha}, "
            f"required {require_ordered_cells_sha256}"
        )
    if require_bed_sha256 and bed_sha != require_bed_sha256:
        raise DiagnosticReplayError(
            f"BED sha256 mismatch: got {bed_sha}, required {require_bed_sha256}"
        )

    matrix = sparse.load_npz(atac_npz).tocsc()
    if matrix.shape[1] != len(cells):
        raise DiagnosticReplayError(
            f"ATAC cell axis {matrix.shape[1]} != h5ad cells {len(cells)}"
        )
    nnz_per_cell = np.diff(matrix.indptr)
    col_sums = np.asarray(matrix.sum(axis=0)).ravel()
    panel_zero = float((nnz_per_cell == 0).mean())

    per_type: list[dict[str, Any]] = []
    for cell_type in CELL_TYPE_ORDER:
        mask = obs["author_cell_type"].to_numpy() == cell_type
        idx = np.flatnonzero(mask)
        sub = obs.iloc[idx]
        nnz = nnz_per_cell[idx]
        sums = col_sums[idx]
        rows = sample_donor_stratified_cells(sub, cap=TARGETED_CAP, seed=TARGETED_SEED)
        ge20 = {"CON": 0, "DS": 0}
        for donor, group in sub.groupby("donor_id", observed=True):
            if len(group) >= SUPPORT_CUTOFF:
                ge20[donor_class(str(donor))] += 1
        per_type.append(
            {
                "cell_type": cell_type,
                "available_cells": int(len(sub)),
                "panel_zero_cell_fraction": float((nnz == 0).mean()),
                "median_panel_nonzero_regions": float(np.median(nnz)),
                "median_panel_fragment_overlaps": float(np.median(sums)),
                "median_full_atac_depth_obs": float(
                    np.median(sub["nCount_ATAC"].to_numpy())
                ),
                "median_rna_depth_obs": float(np.median(sub["nCount_RNA"].to_numpy())),
                "targeted_cap64_selected_cells": int(len(rows)),
                "targeted_ge20_donors": ge20,
            }
        )

    return {
        "date": date,
        "status": "STRUCTURAL_AND_DESCRIPTIVE_CHECKS_PASS",
        "matrix_sha256": matrix_sha,
        "ordered_cells_sha256": ordered_sha,
        "bed_sha256": bed_sha,
        "shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "count_unit": "unique_fragment_overlap",
        "panel_zero_cell_fraction": panel_zero,
        "per_type": per_type,
        "limits": [
            "No biological effect/prediction analysis.",
            "Panel overlap counts are not full-genome ATAC depth.",
            "465 union regions; fold panels use 256. No regulatory-coverage adequacy inferred.",
            "Cap64 and >=20 are descriptive feasibility settings, not a frozen fit protocol.",
            "Independent cell-state outcome not yet established.",
        ],
    }


def compare_records(name: str, fresh: Any, expected: Any, path: str = "") -> list[str]:
    problems: list[str] = []
    here = path or name
    if type(fresh) is not type(expected) and not (
        isinstance(fresh, (int, float)) and isinstance(expected, (int, float))
    ):
        return [f"{here}: type {type(fresh).__name__} != {type(expected).__name__}"]
    if isinstance(expected, dict):
        fresh_keys = set(fresh)
        expected_keys = set(expected)
        for key in sorted(expected_keys - fresh_keys):
            problems.append(f"{here}: missing key {key}")
        for key in sorted(fresh_keys - expected_keys):
            problems.append(f"{here}: unexpected key {key}")
        for key in sorted(expected_keys & fresh_keys):
            problems.extend(
                compare_records(name, fresh[key], expected[key], f"{here}.{key}")
            )
        return problems
    if isinstance(expected, list):
        if len(fresh) != len(expected):
            return [f"{here}: length {len(fresh)} != {len(expected)}"]
        for index, (left, right) in enumerate(zip(fresh, expected, strict=True)):
            problems.extend(compare_records(name, left, right, f"{here}[{index}]"))
        return problems
    if isinstance(expected, float) or isinstance(fresh, float):
        if not np.isclose(float(fresh), float(expected), rtol=0.0, atol=0.0, equal_nan=True):
            # exact bit compare preferred; fall back only when both are true floats
            if fresh != expected:
                problems.append(f"{here}: {fresh!r} != {expected!r}")
        return problems
    if fresh != expected:
        problems.append(f"{here}: {fresh!r} != {expected!r}")
    return problems


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def prepare_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        raise DiagnosticReplayError(
            f"refusing to overwrite an existing output directory: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=False)


def run_replay(args: argparse.Namespace) -> dict[str, Any]:
    # Build fully in memory first so a failed replay never leaves a half-written
    # output root that later blocks a clean retry via the overwrite guard.
    ladder = json.loads(Path(args.ladder_verification).read_text())
    obs = load_obs(Path(args.h5ad))

    data = build_data_diagnostic(
        sampling_path=Path(args.sampling),
        obs=obs,
        ladder_verification=ladder,
    )
    targeted = build_targeted_sampling(obs)
    measurement = build_measurement_audit(
        obs=obs,
        h5ad_path=Path(args.h5ad),
        atac_npz=Path(args.atac_npz),
        union_bed=Path(args.union_bed),
        require_matrix_sha256=args.require_matrix_sha256,
        require_ordered_cells_sha256=args.require_ordered_cells_sha256,
        require_bed_sha256=args.require_bed_sha256,
    )

    paths = {
        "DATA_DIAGNOSTIC.json": data,
        "TARGETED_SAMPLING_FEASIBILITY.json": targeted,
        "MEASUREMENT_AUDIT.json": measurement,
    }

    comparison: dict[str, Any] = {
        "status": "PASS",
        "output_dir": str(args.output_dir),
        "files": {},
        "problems": [],
    }
    expected_dir = Path(args.expected_dir) if args.expected_dir else None
    if expected_dir is not None:
        for name, payload in paths.items():
            expected_path = expected_dir / name
            if not expected_path.is_file():
                comparison["problems"].append(f"missing expected golden {expected_path}")
                continue
            expected = json.loads(expected_path.read_text())
            problems = compare_records(name, payload, expected)
            comparison["files"][name] = {
                "exact_match": not problems,
                "n_problems": len(problems),
                "problems_head": problems[:20],
            }
            comparison["problems"].extend(problems)
        if comparison["problems"]:
            comparison["status"] = "FAIL"
            raise DiagnosticReplayError(
                "fresh diagnostics differ from immutable expected copies: "
                + "; ".join(comparison["problems"][:12])
            )

    prepare_output_dir(args.output_dir)
    for name, payload in paths.items():
        write_json(args.output_dir / name, payload)
        if name in comparison["files"]:
            comparison["files"][name]["fresh_sha256"] = sha256_file(args.output_dir / name)
            expected_path = Path(args.expected_dir) / name
            comparison["files"][name]["expected_sha256"] = sha256_file(expected_path)
    write_json(args.output_dir / "REPLAY_COMPARISON.json", comparison)
    return comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument("--sampling", type=Path, default=DEFAULT_SAMPLING)
    parser.add_argument("--atac-npz", type=Path, default=DEFAULT_ATAC)
    parser.add_argument("--union-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument(
        "--ladder-verification", type=Path, default=DEFAULT_LADDER_VERIFICATION
    )
    parser.add_argument("--expected-dir", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--require-matrix-sha256", default=None)
    parser.add_argument("--require-ordered-cells-sha256", default=None)
    parser.add_argument("--require-bed-sha256", default=None)
    parser.add_argument(
        "--no-compare-expected",
        action="store_true",
        help="Write fresh JSON only; skip golden exact compare.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.no_compare_expected:
        args.expected_dir = None
    try:
        comparison = run_replay(args)
    except DiagnosticReplayError as error:
        print(f"DIAGNOSTIC_REPLAY_FAIL: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": comparison["status"], "output_dir": comparison["output_dir"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
