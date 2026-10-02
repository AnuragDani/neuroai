#!/usr/bin/env python3
"""M2 training-only masked ATAC target feasibility report.

Freezes candidate ranking/eligibility on provisional inner-train donors from
archival repeat-0 outer folds, selects one binary presence target per fold or
records NO_TARGET_SUPPORT, and never reads outer-test target outcomes for
selection. No fits, downloads, or densification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import anndata as ad
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.masked_atac_target import (  # noqa: E402
    INNER_VAL_SALT,
    TARGET_RANK_SALT,
    RegionRecord,
    TargetEligibilityCriteria,
    select_targets_for_repeat0_folds,
    visible_regions_chromosome_mask,
)

DEFAULT_H5AD = ROOT / "data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
DEFAULT_ATAC = (
    ROOT
    / "reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz"
)
DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_REGION_SETS = ROOT / "configs" / "atac_tiebreak_region_sets_2026-09-21.json"
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


class TargetFeasibilityError(RuntimeError):
    """Nonzero-exit target-feasibility failure."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text_lines(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def parse_bed_regions(path: Path) -> list[RegionRecord]:
    regions: list[RegionRecord] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            raise TargetFeasibilityError(f"malformed BED row: {line!r}")
        chrom, start_s, end_s = fields[0], fields[1], fields[2]
        start, end = int(start_s), int(end_s)
        if end <= start:
            raise TargetFeasibilityError(f"non-positive half-open interval: {line!r}")
        label = f"{chrom}:{start}-{end}"
        regions.append(
            RegionRecord(
                index=len(regions),
                chrom=chrom,
                start=start,
                end=end,
                label=label,
            )
        )
    return regions


def build_report(
    *,
    h5ad: Path,
    atac_npz: Path,
    union_bed: Path,
    region_sets_path: Path,
) -> dict[str, Any]:
    for path in (h5ad, atac_npz, union_bed, region_sets_path):
        if not path.is_file():
            raise TargetFeasibilityError(f"missing required input: {path}")

    matrix_sha = sha256_file(atac_npz)
    bed_sha = sha256_file(union_bed)
    region_sets_sha = sha256_file(region_sets_path)
    region_sets = json.loads(region_sets_path.read_text())
    regions = parse_bed_regions(union_bed)
    if len(regions) != 465:
        raise TargetFeasibilityError(f"expected 465 BED regions; got {len(regions)}")

    adata = ad.read_h5ad(h5ad, backed="r")
    donors = adata.obs["donor_id"].astype(str).to_numpy()
    cell_ids = adata.obs_names.astype(str).to_numpy()
    ordered_cells_sha = sha256_text_lines(cell_ids.tolist())
    mat = sparse.load_npz(atac_npz)
    if mat.shape != (465, 248998):
        raise TargetFeasibilityError(f"unexpected matrix shape {mat.shape}")

    hash_ok = {
        "matrix_sha256_match": matrix_sha == EXPECTED_MATRIX_SHA256,
        "bed_sha256_match": bed_sha == EXPECTED_BED_SHA256,
        "region_sets_sha256_match": region_sets_sha == EXPECTED_REGION_SETS_SHA256,
        "ordered_cells_sha256_match": ordered_cells_sha
        == EXPECTED_ORDERED_CELLS_SHA256,
    }
    if not all(hash_ok.values()):
        raise TargetFeasibilityError(f"input hash contract failed: {hash_ok}")

    criteria = TargetEligibilityCriteria()
    selection = select_targets_for_repeat0_folds(
        regions,
        mat,
        donors.tolist(),
        region_sets["per_fold"],
        criteria=criteria,
        inner_val_salt=INNER_VAL_SALT,
        rank_salt=TARGET_RANK_SALT,
    )

    # Chromosome exclusivity and no outer-test contamination checks
    chrom_ok = True
    for fold in selection["folds"]:
        selected = fold["selection"]["selected"]
        if selected is None:
            chrom_ok = False
            continue
        visible = visible_regions_chromosome_mask(regions, selected["chrom"])
        if any(v.chrom == selected["chrom"] for v in visible):
            chrom_ok = False
        if set(fold["inner_train_donors"]) & set(fold["outer_test_donors"]):
            raise TargetFeasibilityError("inner-train overlaps outer-test")
        if int(selected["n_visible_atac_regions"]) != len(visible):
            raise TargetFeasibilityError("visible count mismatch")

    fold_summaries = []
    for fold in selection["folds"]:
        sel = fold["selection"]["selected"]
        fold_summaries.append(
            {
                "fold": fold["fold"],
                "disposition": fold["selection"]["disposition"],
                "target_label": None if sel is None else sel["region_label"],
                "target_chrom": None if sel is None else sel["chrom"],
                "target_index": None if sel is None else sel["region_index"],
                "inner_train_prevalence": None if sel is None else sel["prevalence"],
                "n_pos_cells": None if sel is None else sel["n_pos_cells"],
                "n_neg_cells": None if sel is None else sel["n_neg_cells"],
                "n_both_class_donors": None
                if sel is None
                else sel["n_both_class_donors"],
                "n_visible_atac_regions": None
                if sel is None
                else sel["n_visible_atac_regions"],
                "n_eligible": fold["selection"]["n_eligible"],
                "n_inner_train_cells": fold["selection"]["n_inner_train_cells"],
                "n_inner_train_donors": len(fold["inner_train_donors"]),
                "n_inner_val_donors": len(fold["inner_val_donors"]),
                "n_outer_test_donors": len(fold["outer_test_donors"]),
            }
        )

    report: dict[str, Any] = {
        "record_type": "masked_atac_pilot_m2_target_feasibility",
        "date": "2026-10-01",
        "disposition": selection["disposition"],
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
        "binary_target_rationale": {
            "definition": selection["binary_target_definition"],
            "why_useful": (
                "Binary presence reuses two-class heads, stays a measured "
                "computational estimand under chromosome masking, and supports "
                "a fair CA-vs-token-concat comparison without claiming "
                "regulatory function or reconstructing count magnitude."
            ),
            "imbalance_note": (
                "Union-region accessibility is sparse (typical inner-train "
                "prevalence well below 0.5); eligibility requires both classes "
                "at cell and donor support minima; ranking prefers closest to "
                "balanced prevalence among eligible regions."
            ),
            "not_a_fixed_locus_claim": True,
            "selection_algorithm_is_the_estimand_unit": True,
        },
        "inputs": {
            "h5ad": str(h5ad),
            "atac_counts": str(atac_npz),
            "union_bed": str(union_bed),
            "region_sets": str(region_sets_path),
            "matrix_sha256": matrix_sha,
            "bed_sha256": bed_sha,
            "region_sets_sha256": region_sets_sha,
            "ordered_cells_sha256": ordered_cells_sha,
            **hash_ok,
            "n_regions": 465,
            "n_cells": 248998,
            "n_donors": 30,
        },
        "panel_provenance": {
            "candidate_space": "exact 465-region measured ATAC union",
            "historical_256_panels": (
                "disclosed outer-training-library prevalence selections; not "
                "used as the M2 candidate filter; not claimed as strict "
                "inner-train-only provenance"
            ),
            "outer_folds": "archival region_sets repeat=0 / five folds / split_seed=0",
            "inner_split": selection["inner_val_rule"],
            "inner_split_status": (
                "provisional for M2 feasibility; M3 freezes the pilot "
                "inner-validation partition. If M3 adopts the same salt/rule, "
                "targets remain; if M3 changes the carve, re-run this frozen "
                "algorithm before fits (no outcome-driven redesign)."
            ),
            "disease_labels_as_features": False,
            "disease_labels_in_target_ranking": False,
            "archival_outer_splits_disease_stratified_disclosed": True,
        },
        "eligibility_and_ranking": {
            "criteria": selection["criteria"],
            "ranking_rule": (
                "minimize |inner_train_prevalence - 0.5|; then maximize "
                "count_depth_sum; then "
                f"sha256('{TARGET_RANK_SALT}' + '\\n' + region_label); "
                "then region_label"
            ),
            "salts": {
                "inner_val": INNER_VAL_SALT,
                "target_rank": TARGET_RANK_SALT,
            },
            "forbidden_selection_signals": [
                "outer-test target labels or prevalence",
                "CA / model performance",
                "disease separation",
                "author_cell_type as a feature or eligibility filter",
            ],
        },
        "selection_summary": {
            "n_folds": selection["n_folds"],
            "n_folds_with_target": selection["n_folds_with_target"],
            "unique_selected_targets": selection["unique_selected_targets"],
            "n_unique_selected_targets": selection["n_unique_selected_targets"],
            "fold_to_fold_target_varies": selection["fold_to_fold_target_varies"],
            "folds": fold_summaries,
        },
        "fold_details": selection["folds"],
        "claim_limits": selection["claim_limits"],
        "checks": {
            "input_hashes_pass": all(hash_ok.values()),
            "chromosome_mask_exclusivity_for_selected": chrom_ok,
            "outer_test_excluded_from_inner_train": True,
            "no_disease_in_ranking": True,
            "all_five_folds_selected": selection["disposition"]
            == "TARGET_FEASIBILITY_PASS",
        },
        "what_this_authorizes": {
            "allowed_next": [
                "M3 freeze of donor/inner-val/cell/feature manifests using "
                "these targets if the same inner carve is adopted",
                "Continue independent safe feasibility without fits",
            ],
            "not_authorized": [
                "Model fitting or neural smoke learning",
                "Single-locus performance claims",
                "Relabeling Q2/S9/S10/primary B_NULL",
                "Using outer-test prevalence to drop targets",
                "Strict inner-train-only historical 256-panel provenance",
            ],
        },
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    ss = report["selection_summary"]
    lines = [
        "# Masked ATAC pilot M2 — target feasibility",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Date:** {report['date']}",
        f"**Claim level:** {report['claim_level']} "
        f"({report['claim_level_meaning']})",
        "",
        "## Preserved labels",
        "",
        f"- Primary: `{report['preserved_labels']['primary']}`",
        f"- S7/S9/S10: `{report['preserved_labels']['S7']}` / "
        f"`{report['preserved_labels']['S9']}` / "
        f"`{report['preserved_labels']['S10']}`",
        f"- S8: `{report['preserved_labels']['S8']}`",
        f"- Q2: `{report['preserved_labels']['Q2']}`",
        "",
        "## Binary target rationale",
        "",
        f"- Definition: {report['binary_target_rationale']['definition']}",
        f"- Why useful: {report['binary_target_rationale']['why_useful']}",
        f"- Imbalance: {report['binary_target_rationale']['imbalance_note']}",
        "- Estimand unit is the **training-only selection algorithm**, not one "
        "fixed genomic locus.",
        "",
        "## Eligibility and ranking (frozen before outer-test labels)",
        "",
        f"- Criteria: `{json.dumps(report['eligibility_and_ranking']['criteria'])}`",
        f"- Ranking: {report['eligibility_and_ranking']['ranking_rule']}",
        f"- Inner split: {report['panel_provenance']['inner_split']}",
        f"- Inner-split status: {report['panel_provenance']['inner_split_status']}",
        "- Forbidden: outer-test labels/prevalence, CA performance, disease "
        "separation, author_cell_type features.",
        "",
        "## Per-fold selection",
        "",
        f"- Folds with target: **{ss['n_folds_with_target']}/{ss['n_folds']}**",
        f"- Unique targets: **{ss['n_unique_selected_targets']}** "
        f"(`fold_to_fold_target_varies={ss['fold_to_fold_target_varies']}`)",
        f"- Selected labels: {', '.join(ss['unique_selected_targets']) or '(none)'}",
        "",
        "| Fold | Target | Chrom | Inner-train prevalence | "
        "Pos/Neg cells | Both-class donors | Visible ATAC | Eligible |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for fold in ss["folds"]:
        lines.append(
            f"| {fold['fold']} | `{fold['target_label']}` | "
            f"{fold['target_chrom']} | "
            f"{fold['inner_train_prevalence']:.4f} | "
            f"{fold['n_pos_cells']}/{fold['n_neg_cells']} | "
            f"{fold['n_both_class_donors']} | "
            f"{fold['n_visible_atac_regions']} | {fold['n_eligible']} |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"- Input hashes: **{report['checks']['input_hashes_pass']}**",
            f"- Chromosome-mask exclusivity: "
            f"**{report['checks']['chromosome_mask_exclusivity_for_selected']}**",
            f"- Outer-test excluded from inner-train: "
            f"**{report['checks']['outer_test_excluded_from_inner_train']}**",
            f"- Disease absent from ranking: "
            f"**{report['checks']['no_disease_in_ranking']}**",
            "",
            "## What this does / does not authorize",
            "",
            "Allowed next: " + "; ".join(report["what_this_authorizes"]["allowed_next"]),
            "",
            "Not authorized: "
            + "; ".join(report["what_this_authorizes"]["not_authorized"]),
            "",
            "No fits were run.",
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
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    report = build_report(
        h5ad=args.h5ad,
        atac_npz=args.atac_npz,
        union_bed=args.union_bed,
        region_sets_path=args.region_sets,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "target_feasibility.json"
    out_md = args.out_dir / "TARGET_FEASIBILITY.md"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    out_md.write_text(render_markdown(report))
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(f"disposition={report['disposition']}")
    return 0 if report["disposition"] == "TARGET_FEASIBILITY_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
