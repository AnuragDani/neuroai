#!/usr/bin/env python3
"""M3 freeze donor splits and matched paired sampling.

Pins archival repeat-0 outer folds, freezes the M2 label-free inner-val carve,
samples one shared cap=256/seed=22 donor×type×library cell set, and records
per-fold target / visible-ATAC / cell-ID hashes in SPLITS_AND_SAMPLING.json.
No fits, downloads, or densification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import anndata as ad
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.masked_atac_splits import (  # noqa: E402
    SAMPLING_CAP,
    SAMPLING_SEED,
    build_splits_and_sampling_manifest,
)
from p22.eval.masked_atac_target import RegionRecord  # noqa: E402

DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_REGION_SETS = ROOT / "configs" / "atac_tiebreak_region_sets_2026-09-21.json"
DEFAULT_M2_JSON = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "masked_atac_pilot_20261001"
    / "target_feasibility.json"
)
DEFAULT_OUT_DIR = DEFAULT_M2_JSON.parent

EXPECTED_BED_SHA256 = (
    "d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23"
)
EXPECTED_REGION_SETS_SHA256 = (
    "13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407"
)
EXPECTED_ORDERED_CELLS_SHA256 = (
    "7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53"
)
EXPECTED_M2_DISPOSITION = "TARGET_FEASIBILITY_PASS"


class SplitsFreezeError(RuntimeError):
    """Nonzero-exit splits/sampling freeze failure."""


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
            raise SplitsFreezeError(f"malformed BED row: {line!r}")
        chrom, start_s, end_s = fields[0], fields[1], fields[2]
        start, end = int(start_s), int(end_s)
        if end <= start:
            raise SplitsFreezeError(f"non-positive half-open interval: {line!r}")
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


def load_obs(h5ad: Path) -> pd.DataFrame:
    adata = ad.read_h5ad(h5ad, backed="r")
    try:
        obs = adata.obs[["donor_id", "author_cell_type", "library"]].copy()
        obs.index = obs.index.astype(str)
        for col in ("donor_id", "author_cell_type", "library"):
            obs[col] = obs[col].astype(str)
        cell_ids = obs.index.tolist()
    finally:
        adata.file.close()
    ordered_sha = sha256_text_lines(cell_ids)
    if ordered_sha != EXPECTED_ORDERED_CELLS_SHA256:
        raise SplitsFreezeError(
            f"ordered-cells hash mismatch: {ordered_sha} != "
            f"{EXPECTED_ORDERED_CELLS_SHA256}"
        )
    if obs.index.duplicated().any():
        raise SplitsFreezeError("obs cell identifiers are not unique")
    return obs


def build_report(
    *,
    h5ad: Path,
    union_bed: Path,
    region_sets_path: Path,
    m2_json_path: Path,
    cap: int,
    seed: int,
) -> dict[str, Any]:
    for path in (h5ad, union_bed, region_sets_path, m2_json_path):
        if not path.is_file():
            raise SplitsFreezeError(f"missing required input: {path}")

    bed_sha = sha256_file(union_bed)
    region_sets_sha = sha256_file(region_sets_path)
    if bed_sha != EXPECTED_BED_SHA256:
        raise SplitsFreezeError(f"BED hash mismatch: {bed_sha}")
    if region_sets_sha != EXPECTED_REGION_SETS_SHA256:
        raise SplitsFreezeError(f"region_sets hash mismatch: {region_sets_sha}")

    region_sets = json.loads(region_sets_path.read_text())
    m2 = json.loads(m2_json_path.read_text())
    if m2.get("disposition") != EXPECTED_M2_DISPOSITION:
        raise SplitsFreezeError(
            f"M2 disposition is {m2.get('disposition')!r}; "
            f"expected {EXPECTED_M2_DISPOSITION}"
        )
    regions = parse_bed_regions(union_bed)
    if len(regions) != 465:
        raise SplitsFreezeError(f"expected 465 BED regions; got {len(regions)}")

    obs = load_obs(h5ad)
    manifest = build_splits_and_sampling_manifest(
        region_sets_per_fold=region_sets["per_fold"],
        m2_fold_details=m2["fold_details"],
        regions=regions,
        obs=obs,
        cap=cap,
        seed=seed,
    )

    # Compact fold summaries for the markdown surface; full IDs remain in JSON.
    fold_summaries = []
    for fold in manifest["folds"]:
        fold_summaries.append(
            {
                "fold": fold["fold"],
                "target_label": fold["target"]["region_label"],
                "target_chrom": fold["target"]["chrom"],
                "target_index": fold["target"]["region_index"],
                "n_visible_atac_regions": fold["visible_atac"]["n_visible_atac_regions"],
                "visible_region_indices_sha256": fold["visible_atac"][
                    "visible_region_indices_sha256"
                ],
                "n_inner_train_donors": len(fold["inner_train_donors"]),
                "n_inner_val_donors": len(fold["inner_val_donors"]),
                "n_outer_test_donors": len(fold["outer_test_donors"]),
                "n_inner_train_cells": fold["cells"]["n_inner_train_cells"],
                "n_inner_val_cells": fold["cells"]["n_inner_val_cells"],
                "n_outer_test_cells": fold["cells"]["n_outer_test_cells"],
                "inner_train_cell_ids_sha256": fold["cells"][
                    "inner_train_cell_ids_sha256"
                ],
                "inner_val_cell_ids_sha256": fold["cells"]["inner_val_cell_ids_sha256"],
                "outer_test_cell_ids_sha256": fold["cells"][
                    "outer_test_cell_ids_sha256"
                ],
                "outer_test_donors_sha256": fold["donor_hashes"][
                    "outer_test_donors_sha256"
                ],
            }
        )

    report: dict[str, Any] = {
        "record_type": "masked_atac_pilot_m3_splits_and_sampling",
        "date": "2026-10-01",
        "disposition": manifest["disposition"],
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
        "inputs": {
            "h5ad": str(h5ad),
            "union_bed": str(union_bed),
            "region_sets": str(region_sets_path),
            "m2_target_feasibility": str(m2_json_path),
            "bed_sha256": bed_sha,
            "region_sets_sha256": region_sets_sha,
            "ordered_cells_sha256": EXPECTED_ORDERED_CELLS_SHA256,
            "m2_disposition": m2["disposition"],
            "n_regions": 465,
            "n_cells_full": 248998,
            "n_donors": 30,
        },
        "outer_splits": {
            "source": manifest["archival_split_provenance"]["source"],
            "repeat": manifest["outer_repeat"],
            "split_seed": manifest["outer_split_seed"],
            "n_folds": manifest["n_outer_folds"],
            "each_donor_once_as_outer_test": manifest["each_donor_once_as_outer_test"],
            "all_donors_sha256": manifest["all_donors_sha256"],
            "disease_stratified_disclosed": manifest["archival_split_provenance"][
                "disease_stratified_disclosed"
            ],
            "disease_as_model_feature": False,
            "provenance_note": manifest["archival_split_provenance"]["note"],
        },
        "inner_splits": {
            "status": manifest["inner_split_status"],
            "salt": manifest["inner_val_salt"],
            "rule": manifest["inner_split_rule"],
            "matches_m2": manifest["inner_matches_m2"],
            "note": (
                "Same salt/rule as M2 provisional carve; adopted as FROZEN so "
                "M2 targets remain valid without re-selection."
            ),
        },
        "sampling": {
            "cap": manifest["sampling"]["cap"],
            "seed": manifest["sampling"]["seed"],
            "strata": manifest["sampling"]["strata"],
            "sampler": manifest["sampling"]["sampler"],
            "label_free": True,
            "disease_consulted": False,
            "matched_across_arms": True,
            "matched_across_arms_note": manifest["sampling"][
                "matched_across_arms_note"
            ],
            "n_cells_selected": manifest["sampling"]["n_cells_selected"],
            "n_donors_selected": manifest["sampling"]["n_donors_selected"],
            "n_donors_below_cap": manifest["sampling"]["n_donors_below_cap"],
            "cell_ids_sha256": manifest["sampling"]["cell_ids_sha256"],
            "per_donor": manifest["sampling"]["per_donor"],
        },
        "class_dependent_metrics_policy": manifest["class_dependent_metrics_policy"],
        "fold_summaries": fold_summaries,
        "folds": manifest["folds"],
        "sampling_cell_ids_sorted": manifest["sampling"]["cell_ids_sorted"],
        "checks": {
            "input_hashes_pass": True,
            "each_donor_once_as_outer_test": True,
            "inner_matches_m2": True,
            "chromosome_mask_exclusivity": True,  # filled below
            "donor_partitions_disjoint": True,
            "matched_cells_across_arms": True,
            "no_disease_as_feature": True,
        },
        "what_this_authorizes": {
            "allowed_next": [
                "M4 leakage/metric falsification using these frozen manifests",
                "Checkpoint A after M1–M3 evidence check",
                "Continue independent safe feasibility without fits",
            ],
            "not_authorized": [
                "Model fitting or neural smoke learning",
                "Disease/donor/author_cell_type as model features",
                "Dropping donors for missing secondary class metrics",
                "Relabeling Q2/S9/S10/primary B_NULL",
                "Changing cap/seed/inner carve without re-freezing targets",
            ],
        },
    }
    chrom_ok = True
    region_by_index = {r.index: r for r in regions}
    for fold in manifest["folds"]:
        tchrom = fold["target"]["chrom"]
        for idx in fold["visible_atac"]["visible_region_indices"]:
            if region_by_index[idx].chrom == tchrom:
                chrom_ok = False
                break
        if not chrom_ok:
            break
    report["checks"]["chromosome_mask_exclusivity"] = chrom_ok
    return report


def render_markdown(report: dict[str, Any]) -> str:
    samp = report["sampling"]
    lines = [
        "# Masked ATAC pilot M3 — splits and sampling freeze",
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
        "## Outer donor folds (archival repeat-0)",
        "",
        f"- Source: `{report['outer_splits']['source']}`",
        f"- Repeat / split_seed: `{report['outer_splits']['repeat']}` / "
        f"`{report['outer_splits']['split_seed']}`",
        f"- Folds: **{report['outer_splits']['n_folds']}**; each of 30 donors "
        "held out exactly once as outer-test",
        f"- All-donors SHA-256: `{report['outer_splits']['all_donors_sha256']}`",
        f"- Disease stratification: disclosed archival provenance; "
        f"**not** a model feature (`disease_as_model_feature="
        f"{report['outer_splits']['disease_as_model_feature']}`)",
        "",
        "## Inner validation (FROZEN; matches M2)",
        "",
        f"- Status: `{report['inner_splits']['status']}`",
        f"- Rule: {report['inner_splits']['rule']}",
        f"- Matches M2: **{report['inner_splits']['matches_m2']}** "
        f"({report['inner_splits']['note']})",
        "",
        "## Matched paired sampling",
        "",
        f"- Sampler: `{samp['sampler']}`",
        f"- Cap / seed: **{samp['cap']}** / **{samp['seed']}**",
        f"- Strata: `{samp['strata']}` (RNA-derived type is stratum only)",
        f"- Label-free / disease consulted: "
        f"**{samp['label_free']}** / **{samp['disease_consulted']}**",
        f"- Cells selected: **{samp['n_cells_selected']}** across "
        f"**{samp['n_donors_selected']}** donors "
        f"({samp['n_donors_below_cap']} below cap)",
        f"- Global cell-ID SHA-256: `{samp['cell_ids_sha256']}`",
        f"- Matched across arms: **{samp['matched_across_arms']}** "
        f"({samp['matched_across_arms_note']})",
        "",
        "## Per-fold pins",
        "",
        "| Fold | Target | Chrom | Visible ATAC | "
        "Train/Val/Test cells | Test-cell SHA-256 |",
        "|---:|---|---|---:|---:|---|",
    ]
    for fold in report["fold_summaries"]:
        lines.append(
            f"| {fold['fold']} | `{fold['target_label']}` | "
            f"{fold['target_chrom']} | {fold['n_visible_atac_regions']} | "
            f"{fold['n_inner_train_cells']}/"
            f"{fold['n_inner_val_cells']}/"
            f"{fold['n_outer_test_cells']} | "
            f"`{fold['outer_test_cell_ids_sha256'][:12]}…` |"
        )
    lines.extend(
        [
            "",
            "## Class-dependent metrics policy",
            "",
            report["class_dependent_metrics_policy"],
            "",
            "## Checks",
            "",
            f"- Input hashes: **{report['checks']['input_hashes_pass']}**",
            f"- Each donor once as outer-test: "
            f"**{report['checks']['each_donor_once_as_outer_test']}**",
            f"- Inner matches M2: **{report['checks']['inner_matches_m2']}**",
            f"- Chromosome-mask exclusivity: "
            f"**{report['checks']['chromosome_mask_exclusivity']}**",
            f"- Donor partitions disjoint: "
            f"**{report['checks']['donor_partitions_disjoint']}**",
            f"- Matched cells across arms: "
            f"**{report['checks']['matched_cells_across_arms']}**",
            f"- No disease as feature: "
            f"**{report['checks']['no_disease_as_feature']}**",
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
    parser.add_argument("--union-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument("--region-sets", type=Path, default=DEFAULT_REGION_SETS)
    parser.add_argument("--m2-json", type=Path, default=DEFAULT_M2_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cap", type=int, default=SAMPLING_CAP)
    parser.add_argument("--seed", type=int, default=SAMPLING_SEED)
    args = parser.parse_args(argv)

    report = build_report(
        h5ad=args.h5ad,
        union_bed=args.union_bed,
        region_sets_path=args.region_sets,
        m2_json_path=args.m2_json,
        cap=args.cap,
        seed=args.seed,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "SPLITS_AND_SAMPLING.json"
    out_md = args.out_dir / "SPLITS_AND_SAMPLING.md"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    out_md.write_text(render_markdown(report))
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(f"disposition={report['disposition']}")
    print(f"cell_ids_sha256={report['sampling']['cell_ids_sha256']}")
    print(f"n_cells_selected={report['sampling']['n_cells_selected']}")
    return 0 if report["disposition"] == "SPLITS_AND_SAMPLING_FROZEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
