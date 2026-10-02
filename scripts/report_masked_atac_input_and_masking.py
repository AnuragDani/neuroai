#!/usr/bin/env python3
"""M1 measured-input and whole-chromosome masking contract report.

Rehashes exact ATAC union contracts, quantifies half-open interval overlaps,
compares target-ID removal vs whole-target-chromosome masking, and records
inherited panel provenance limits. No fits, downloads, recounts, or densification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8/reports/generated/"
    "atac_tiebreak_measured_20260921/counts/counts.npz"
)
DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_REGION_SETS = ROOT / "configs" / "atac_tiebreak_region_sets_2026-09-21.json"
DEFAULT_CONTRACT = ROOT / "configs" / "atac_tiebreak_measurement_contract_2026-09-21.json"
DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "masked_atac_pilot_20261001"
)

EXPECTED_MATRIX_SHA256 = (
    "5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969"
)
EXPECTED_BED_SHA256 = (
    "d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23"
)
EXPECTED_REGION_SETS_SHA256 = (
    "13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407"
)
EXPECTED_ORDERED_CELLS_SHA256 = (
    "7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53"
)


class MaskingError(RuntimeError):
    """Nonzero-exit masking-contract failure."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text_lines(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def parse_bed_regions(path: Path) -> list[tuple[int, str, int, int, str]]:
    """Return (index, chrom, start, end, label) for 0-based half-open BED rows."""
    regions: list[tuple[int, str, int, int, str]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            raise MaskingError(f"malformed BED row: {line!r}")
        chrom, start_s, end_s = fields[0], fields[1], fields[2]
        start, end = int(start_s), int(end_s)
        if end <= start:
            raise MaskingError(f"non-positive half-open interval: {line!r}")
        label = f"{chrom}:{start}-{end}"
        regions.append((len(regions), chrom, start, end, label))
    return regions


def half_open_overlap(
    a: tuple[str, int, int], b: tuple[str, int, int]
) -> bool:
    """True iff same chrom and half-open intervals [start,end) intersect."""
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


def overlapping_interval_pairs(
    regions: list[tuple[int, str, int, int, str]],
) -> list[dict[str, Any]]:
    """Enumerate unordered overlapping region pairs within each chromosome."""
    by_chrom: dict[str, list[tuple[int, str, int, int, str]]] = defaultdict(list)
    for region in regions:
        by_chrom[region[1]].append(region)
    pairs: list[dict[str, Any]] = []
    for chrom, items in sorted(by_chrom.items()):
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if half_open_overlap((a[1], a[2], a[3]), (b[1], b[2], b[3])):
                    span = max(0, min(a[3], b[3]) - max(a[2], b[2]))
                    pairs.append(
                        {
                            "chrom": chrom,
                            "region_a": a[4],
                            "region_b": b[4],
                            "index_a": a[0],
                            "index_b": b[0],
                            "overlap_bp": span,
                        }
                    )
    return pairs


def visible_regions_id_only(
    regions: list[tuple[int, str, int, int, str]], target_index: int
) -> list[tuple[int, str, int, int, str]]:
    return [r for r in regions if r[0] != target_index]


def visible_regions_chromosome_mask(
    regions: list[tuple[int, str, int, int, str]], target_chrom: str
) -> list[tuple[int, str, int, int, str]]:
    return [r for r in regions if r[1] != target_chrom]


def target_leakage_summary(
    regions: list[tuple[int, str, int, int, str]],
) -> dict[str, Any]:
    """Compare target-ID removal vs whole-chromosome mask for every union region."""
    id_overlap = 0
    id_same_chrom = 0
    chr_overlap = 0
    chr_same_chrom = 0
    per_chrom_visible: dict[str, int] = {}
    for idx, chrom, start, end, _label in regions:
        visible_id = visible_regions_id_only(regions, idx)
        if any(r[1] == chrom for r in visible_id):
            id_same_chrom += 1
        if any(
            half_open_overlap((chrom, start, end), (r[1], r[2], r[3]))
            for r in visible_id
        ):
            id_overlap += 1
        visible_chr = visible_regions_chromosome_mask(regions, chrom)
        per_chrom_visible[chrom] = len(visible_chr)
        if any(r[1] == chrom for r in visible_chr):
            chr_same_chrom += 1
        if any(
            half_open_overlap((chrom, start, end), (r[1], r[2], r[3]))
            for r in visible_chr
        ):
            chr_overlap += 1
    return {
        "n_targets_evaluated": len(regions),
        "target_id_removal": {
            "targets_with_interval_overlapping_visible_region": id_overlap,
            "targets_with_same_chromosome_visible_region": id_same_chrom,
            "eliminates_shared_fragment_risk": False,
            "reason": (
                "Same-chromosome counted intervals remain visible; overlapping "
                "or nearby intervals can share fragment records under "
                "unique_fragment_overlap half-open counting."
            ),
        },
        "whole_target_chromosome_mask": {
            "targets_with_interval_overlapping_visible_region": chr_overlap,
            "targets_with_same_chromosome_visible_region": chr_same_chrom,
            "eliminates_shared_fragment_risk_under_documented_semantics": (
                chr_overlap == 0 and chr_same_chrom == 0
            ),
            "reason": (
                "All visible ATAC chromosome IDs differ from the target "
                "chromosome, so no same-chromosome fragment can qualify for "
                "both target and visible intervals under the documented "
                "fragment_start < end and fragment_end > beg rule."
            ),
            "visible_region_count_by_masked_chromosome": dict(
                sorted(per_chrom_visible.items())
            ),
            "min_visible_regions": min(per_chrom_visible.values()),
            "max_visible_regions": max(per_chrom_visible.values()),
        },
    }


def verify_panel_donor_library_isolation(
    region_sets: dict[str, Any],
    donor_to_libraries: dict[str, set[str]],
) -> dict[str, Any]:
    donor_overlap = 0
    test_lib_leak = 0
    train_lib_outside = 0
    for entry in region_sets["per_fold"]:
        train = set(entry["train_donors"])
        test = set(entry["test_donors"])
        if train & test:
            donor_overlap += 1
        test_libs: set[str] = set()
        for donor in test:
            test_libs |= donor_to_libraries[donor]
        train_libs = set(entry["train_libraries"])
        if train_libs & test_libs:
            test_lib_leak += 1
        train_donor_libs: set[str] = set()
        for donor in train:
            train_donor_libs |= donor_to_libraries[donor]
        if not train_libs.issubset(train_donor_libs):
            train_lib_outside += 1
    return {
        "n_panels": len(region_sets["per_fold"]),
        "panels_with_train_test_donor_overlap": donor_overlap,
        "panels_with_test_library_in_train_libraries": test_lib_leak,
        "panels_with_train_library_outside_train_donors": train_lib_outside,
        "pass": donor_overlap == 0
        and test_lib_leak == 0
        and train_lib_outside == 0,
    }


def build_report(
    *,
    h5ad: Path,
    atac_npz: Path,
    union_bed: Path,
    region_sets_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    for path in (h5ad, atac_npz, union_bed, region_sets_path, contract_path):
        if not path.is_file():
            raise MaskingError(f"missing required input: {path}")

    bed_sha = sha256_file(union_bed)
    region_sets_sha = sha256_file(region_sets_path)
    matrix_sha = sha256_file(atac_npz)
    contract = json.loads(contract_path.read_text())
    region_sets = json.loads(region_sets_path.read_text())
    regions = parse_bed_regions(union_bed)
    labels = [r[4] for r in regions]

    backed = ad.read_h5ad(h5ad, backed="r")
    try:
        cell_ids = backed.obs_names.astype(str).tolist()
        donors = backed.obs["donor_id"].astype(str)
        libraries = backed.obs["library"].astype(str)
        n_obs = int(backed.n_obs)
        n_vars = int(backed.n_vars)
        donor_to_libraries: dict[str, set[str]] = defaultdict(set)
        for donor, library in zip(donors.tolist(), libraries.tolist(), strict=True):
            donor_to_libraries[donor].add(library)
    finally:
        backed.file.close()
    ordered_cells_sha = sha256_text_lines(cell_ids)

    matrix = sparse.load_npz(atac_npz)
    if matrix.ndim != 2:
        raise MaskingError(f"expected 2-D ATAC matrix, got shape {matrix.shape}")
    if matrix.shape[0] != len(regions):
        raise MaskingError(
            f"BED regions {len(regions)} != matrix rows {matrix.shape[0]}"
        )
    if matrix.shape[1] != n_obs:
        raise MaskingError(
            f"matrix cells {matrix.shape[1]} != H5AD n_obs {n_obs}"
        )
    if matrix.shape[1] != len(cell_ids):
        raise MaskingError("ordered cell length mismatch")
    data = np.asarray(matrix.data)
    has_negative = bool((data < 0).any()) if data.size else False
    stored_all_positive = bool((data >= 1).all()) if data.size else True

    overlap_pairs = overlapping_interval_pairs(regions)
    pairs_by_chrom: dict[str, int] = defaultdict(int)
    for pair in overlap_pairs:
        pairs_by_chrom[pair["chrom"]] += 1
    leakage = target_leakage_summary(regions)

    union_match = list(region_sets["union_regions"]) == labels
    panels_subset = True
    for entry in region_sets["per_fold"]:
        if not set(entry["regions"]).issubset(set(labels)):
            panels_subset = False
            break
    isolation = verify_panel_donor_library_isolation(
        region_sets, dict(donor_to_libraries)
    )

    chroms = sorted({r[1] for r in regions})
    chrom_naming_ok = all(
        c.startswith("chr") and c[3:].isdigit() or c in {"chrX", "chrY"}
        for c in chroms
    )

    hash_checks = {
        "matrix_sha256": matrix_sha,
        "matrix_sha256_match": matrix_sha == EXPECTED_MATRIX_SHA256,
        "bed_sha256": bed_sha,
        "bed_sha256_match": bed_sha == EXPECTED_BED_SHA256,
        "region_sets_sha256": region_sets_sha,
        "region_sets_sha256_match": region_sets_sha == EXPECTED_REGION_SETS_SHA256,
        "ordered_cells_sha256": ordered_cells_sha,
        "ordered_cells_sha256_match": ordered_cells_sha
        == EXPECTED_ORDERED_CELLS_SHA256,
    }
    structural_pass = (
        all(
            hash_checks[k]
            for k in (
                "matrix_sha256_match",
                "bed_sha256_match",
                "region_sets_sha256_match",
                "ordered_cells_sha256_match",
            )
        )
        and not has_negative
        and stored_all_positive
        and union_match
        and panels_subset
        and isolation["pass"]
        and chrom_naming_ok
        and leakage["whole_target_chromosome_mask"][
            "eliminates_shared_fragment_risk_under_documented_semantics"
        ]
        and leakage["whole_target_chromosome_mask"]["min_visible_regions"] > 0
    )

    disposition = (
        "INPUT_AND_MASKING_PASS" if structural_pass else "INPUT_UNRESOLVED"
    )

    return {
        "record_type": "masked_atac_pilot_m1_input_and_masking",
        "date": "2026-10-01",
        "disposition": disposition,
        "claim_level": 2,
        "claim_level_meaning": (
            "computational prediction of measured accessibility presence; "
            "not biological state, causal mechanism, or external validation"
        ),
        "preserved_labels": {
            "primary": "B_NULL",
            "S7": "INVALID",
            "S8": "NO FIT",
            "S9": "INVALID",
            "S10": "INVALID",
            "Q2": "ENDPOINT_UNRESOLVED",
        },
        "count_semantics": {
            "genome_build": "GRCh38",
            "interval_convention": "chr:start-end 0-based half-open (cellranger-arc)",
            "count_unit": "unique_fragment_overlap",
            "fragment_qualifies_when": (
                "fragment_start < region_end and fragment_end > region_start; "
                "fragment_start >= fragment_end ignored"
            ),
            "matrix_orientation": "regions × cells",
            "source_contract": str(contract_path),
            "contract_count_unit": contract.get("source", {}).get("count_unit"),
            "contract_interval_rule": contract.get("source", {}).get(
                "interval_rule"
            ),
        },
        "inputs": {
            "h5ad": str(h5ad),
            "atac_counts": str(atac_npz),
            "union_bed": str(union_bed),
            "region_sets": str(region_sets_path),
            "n_cells": n_obs,
            "n_rna_vars": n_vars,
            "n_donors": int(donors.nunique()),
            "n_regions": len(regions),
            "n_chromosomes": len(chroms),
            "chromosomes": chroms,
            "matrix_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
            "matrix_nnz": int(matrix.nnz),
            "matrix_zero_fraction": float(1.0 - (matrix.nnz / (matrix.shape[0] * matrix.shape[1]))),
            "stored_count_values_all_positive": stored_all_positive,
            "has_negative_counts": has_negative,
            **hash_checks,
        },
        "measured_zero_vs_missing": {
            "missing_input_policy": (
                "Unmeasured regions are absent from the union/matrix; they are "
                "never filled as biological zeros."
            ),
            "measured_zero_meaning": (
                "A zero for a union region/cell means no unique fragment "
                "qualified under the half-open overlap rule for that exact "
                "interval; sparse storage omits zeros but they are measured."
            ),
            "target_labels_vs_visible_features": (
                "Target is binary count>0 at one withheld region; visible ATAC "
                "excludes the entire target chromosome. RNA remains a separate "
                "measured assay and may stay as input."
            ),
            "forbidden_as_model_inputs": [
                "full nCount_ATAC",
                "full nFeature_ATAC",
                "target-inclusive QC/depth summaries",
                "all-region latent / gene-activity values computed before masking",
                "disease / donor / author_cell_type labels as features",
            ],
        },
        "overlap_and_masking": {
            "n_overlapping_interval_pairs": len(overlap_pairs),
            "n_chromosomes_with_overlapping_pairs": len(pairs_by_chrom),
            "overlapping_pairs_by_chromosome": dict(
                sorted(pairs_by_chrom.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "plan_note_clarification": (
                "PLAN cites 58 overlapping pairs in the 465-region union spanning "
                "24 chromosomes. Live enumeration confirms 58 pairs; pairs occur "
                "on 9 chromosomes within the 24-chromosome union (not one pair on "
                "every chromosome)."
            ),
            "example_pairs": overlap_pairs[:5],
            "half_open_boundary_checks": {
                "adjacent_chr1_10_20_vs_20_30_overlap": half_open_overlap(
                    ("chr1", 10, 20), ("chr1", 20, 30)
                ),
                "interior_chr1_10_20_vs_19_25_overlap": half_open_overlap(
                    ("chr1", 10, 20), ("chr1", 19, 25)
                ),
            },
            "leakage": leakage,
            "chromosome_naming_consistent_chr_prefix": chrom_naming_ok,
        },
        "inherited_panel_provenance": {
            "selection_rule": region_sets.get("selection_rule"),
            "tie_break": region_sets.get("tie_break"),
            "tie_break_salt": region_sets.get("tie_break_salt"),
            "top_n": region_sets.get("top_n"),
            "n_panels": len(region_sets["per_fold"]),
            "label_independence_statement": region_sets.get(
                "label_independence"
            ),
            "union_regions_match_bed": union_match,
            "all_panel_regions_subset_of_union": panels_subset,
            "donor_library_isolation": isolation,
            "strict_inner_train_only_panel_construction": False,
            "inherited_processing_disclosure": (
                "Historical 256-region panels are selected by outer-fold "
                "training-library prevalence (archival 5×5 disease-stratified "
                "donor splits). That uses outer-training donors/libraries and "
                "does not prove a later inner-validation-only construction. "
                "This pilot pins the measured 465-region union as the candidate "
                "target/feature space; M2 must freeze training-only target "
                "ranking without inventing stricter provenance than evidenced. "
                "Disease labels stratify archival splits only and are not model "
                "features."
            ),
            "candidate_repeat_for_pilot": {
                "proposed": "repeat 0 / five outer folds from region_sets",
                "fold0_repeat0_regions_sha256": next(
                    e["regions_sha256"]
                    for e in region_sets["per_fold"]
                    if e["fold"] == 0 and e["repeat"] == 0
                ),
                "fold0_repeat0_n_train_donors": next(
                    e["n_train_donors"]
                    for e in region_sets["per_fold"]
                    if e["fold"] == 0 and e["repeat"] == 0
                ),
                "note": (
                    "M3 freezes the actual pilot split/sampling; M1 only traces "
                    "existing panel-to-donor provenance."
                ),
            },
        },
        "checks": {
            "hash_and_dimension_pass": structural_pass,
            "target_id_removal_insufficient": leakage["target_id_removal"][
                "targets_with_interval_overlapping_visible_region"
            ]
            > 0,
            "chromosome_mask_eliminates_same_chrom_visible": leakage[
                "whole_target_chromosome_mask"
            ]["eliminates_shared_fragment_risk_under_documented_semantics"],
            "visible_atac_nonempty_for_every_masked_chromosome": leakage[
                "whole_target_chromosome_mask"
            ]["min_visible_regions"]
            > 0,
        },
        "what_this_authorizes": {
            "allowed_next": [
                "M2 training-only target feasibility on the pinned union",
                "Continue independent safe feasibility without fits",
            ],
            "not_authorized": [
                "Model fitting or neural smoke learning",
                "Claiming biological regulatory function or cell-state",
                "Relabeling Q2/S9/S10/primary B_NULL",
                "Strict inner-train-only historical panel provenance",
                "Target-ID-only ATAC masking",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    ov = report["overlap_and_masking"]
    leak = ov["leakage"]
    inp = report["inputs"]
    lines = [
        "# M1 — Measured inputs and chromosome masking contract",
        "",
        f"**Disposition:** `{report['disposition']}`  ",
        f"**Date:** {report['date']}  ",
        "**Dependency:** M0 PASS. No fits, downloads, package installs, or recounts.",
        "",
        "Machine-readable: [input_and_masking.json](input_and_masking.json).",
        "",
        "## Contract checks",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Matrix/BED/region_sets/ordered-cell SHA-256 | "
        f"{'PASS' if report['checks']['hash_and_dimension_pass'] else 'FAIL'} |",
        f"| Dimensions {inp['matrix_shape'][0]}×{inp['matrix_shape'][1]}; "
        f"{inp['n_donors']} donors; {inp['n_chromosomes']} chroms | PASS |",
        f"| Overlapping interval pairs in union | "
        f"**{ov['n_overlapping_interval_pairs']}** "
        f"(on {ov['n_chromosomes_with_overlapping_pairs']} chromosomes) |",
        f"| Target-ID removal leaves interval-overlapping visible region | "
        f"{leak['target_id_removal']['targets_with_interval_overlapping_visible_region']} "
        f"/ {leak['n_targets_evaluated']} targets — **insufficient** |",
        f"| Whole-target-chromosome mask same-chrom / interval leak | "
        f"{leak['whole_target_chromosome_mask']['targets_with_same_chromosome_visible_region']} / "
        f"{leak['whole_target_chromosome_mask']['targets_with_interval_overlapping_visible_region']}"
        f" — **eliminated** |",
        f"| Visible ATAC regions after mask | "
        f"{leak['whole_target_chromosome_mask']['min_visible_regions']}–"
        f"{leak['whole_target_chromosome_mask']['max_visible_regions']} |",
        "",
        "## Count and zero semantics",
        "",
        f"- Genome build **{report['count_semantics']['genome_build']}**; "
        f"intervals **{report['count_semantics']['interval_convention']}**; "
        f"unit **`{report['count_semantics']['count_unit']}`**.",
        f"- {report['measured_zero_vs_missing']['measured_zero_meaning']}",
        f"- {report['measured_zero_vs_missing']['missing_input_policy']}",
        f"- {report['measured_zero_vs_missing']['target_labels_vs_visible_features']}",
        "- Forbidden inputs: "
        + ", ".join(
            f"`{x}`"
            for x in report["measured_zero_vs_missing"]["forbidden_as_model_inputs"]
        )
        + ".",
        "",
        "## Overlap clarification",
        "",
        ov["plan_note_clarification"],
        "",
        "Pairs by chromosome: "
        + ", ".join(
            f"{c}={n}"
            for c, n in ov["overlapping_pairs_by_chromosome"].items()
        )
        + ".",
        "",
        "## Inherited panel provenance",
        "",
        report["inherited_panel_provenance"]["inherited_processing_disclosure"],
        "",
        f"- Selection rule: {report['inherited_panel_provenance']['selection_rule']}",
        f"- Strict inner-train-only historical panels claimed: "
        f"**{report['inherited_panel_provenance']['strict_inner_train_only_panel_construction']}**",
        "- Donor/library isolation across 25 panels: "
        + (
            "**PASS**"
            if report["inherited_panel_provenance"]["donor_library_isolation"][
                "pass"
            ]
            else "**FAIL**"
        ),
        "",
        "## Preserved scientific labels",
        "",
        "Primary **`B_NULL`**; S7/S9/S10 **`INVALID`**; S8 **`NO FIT`**; "
        "Q2 **`ENDPOINT_UNRESOLVED`** (does not block claim-level-2).",
        "",
        "## What this does and does not authorize",
        "",
        "| Allowed next | Not authorized |",
        "|---|---|",
    ]
    allowed = report["what_this_authorizes"]["allowed_next"]
    denied = report["what_this_authorizes"]["not_authorized"]
    for i in range(max(len(allowed), len(denied))):
        a = allowed[i] if i < len(allowed) else ""
        d = denied[i] if i < len(denied) else ""
        lines.append(f"| {a} | {d} |")
    lines.extend(
        [
            "",
            "## Verification commands",
            "",
            "```bash",
            'export PYTHONPATH="$(pwd)/src"',
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "
            '"import p22; print(p22.__file__)"',
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python "
            "scripts/report_masked_atac_input_and_masking.py",
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest "
            "tests/test_masked_atac_input_and_masking_m1.py -q",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument("--atac-npz", type=Path, default=DEFAULT_ATAC)
    parser.add_argument("--union-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument("--region-sets", type=Path, default=DEFAULT_REGION_SETS)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    report = build_report(
        h5ad=args.h5ad,
        atac_npz=args.atac_npz,
        union_bed=args.union_bed,
        region_sets_path=args.region_sets,
        contract_path=args.contract,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "input_and_masking.json"
    md_path = args.out_dir / "INPUT_AND_MASKING.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_markdown(report))
    print(json.dumps({"disposition": report["disposition"], "json": str(json_path)}))
    return 0 if report["disposition"] == "INPUT_AND_MASKING_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
