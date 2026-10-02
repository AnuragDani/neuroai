#!/usr/bin/env python3
"""M4 leakage and metric falsification for the masked ATAC pilot.

Runs no-fit metric/leakage suite against tiny deterministic arrays, verifies
M3 frozen fold chromosome-mask exclusivity, and records adapter requirements
for mixed cell-target labels. Writes FALSIFICATION.md/json. No model fitting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.masked_atac_metrics import (  # noqa: E402
    ADAPTER_REQUIREMENTS,
    FORBIDDEN_FEATURE_FIELDS,
    assert_chromosome_mask_exclusivity,
    run_falsification_suite,
)
from p22.eval.masked_atac_target import RegionRecord  # noqa: E402

DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_M3_JSON = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "masked_atac_pilot_20261001"
    / "SPLITS_AND_SAMPLING.json"
)
DEFAULT_OUT_DIR = DEFAULT_M3_JSON.parent
EXPECTED_M3_DISPOSITION = "SPLITS_AND_SAMPLING_FROZEN"


class FalsificationError(RuntimeError):
    """Nonzero-exit M4 falsification failure."""


def parse_bed_regions(path: Path) -> list[RegionRecord]:
    regions: list[RegionRecord] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            raise FalsificationError(f"malformed BED row: {line!r}")
        chrom, start_s, end_s = fields[0], fields[1], fields[2]
        start, end = int(start_s), int(end_s)
        if end <= start:
            raise FalsificationError(f"non-positive half-open interval: {line!r}")
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


def verify_m3_chromosome_masks(
    m3: dict[str, Any],
    regions: list[RegionRecord],
) -> dict[str, Any]:
    chroms = [r.chrom for r in regions]
    fold_ok: list[dict[str, Any]] = []
    for fold in m3["folds"]:
        target_chrom = fold["target"]["chrom"]
        visible = fold["visible_atac"]["visible_region_indices"]
        assert_chromosome_mask_exclusivity(chroms, visible, target_chrom)
        # Also ensure target region index is not in visible list.
        tidx = int(fold["target"]["region_index"])
        if tidx in set(int(i) for i in visible):
            raise FalsificationError(
                f"fold {fold['fold']}: target index {tidx} in visible features"
            )
        fold_ok.append(
            {
                "fold": int(fold["fold"]),
                "target_chrom": target_chrom,
                "target_index": tidx,
                "n_visible": len(visible),
                "chromosome_mask_exclusive": True,
                "target_not_in_visible": True,
            }
        )
    return {
        "m3_disposition": m3["disposition"],
        "n_folds_checked": len(fold_ok),
        "all_folds_exclusive": True,
        "folds": fold_ok,
    }


def build_report(*, m3_json_path: Path, union_bed: Path) -> dict[str, Any]:
    if not m3_json_path.is_file():
        raise FalsificationError(f"missing M3 manifest: {m3_json_path}")
    if not union_bed.is_file():
        raise FalsificationError(f"missing BED: {union_bed}")

    m3 = json.loads(m3_json_path.read_text())
    if m3.get("disposition") != EXPECTED_M3_DISPOSITION:
        raise FalsificationError(
            f"M3 disposition is {m3.get('disposition')!r}; "
            f"expected {EXPECTED_M3_DISPOSITION}"
        )
    regions = parse_bed_regions(union_bed)
    if len(regions) != 465:
        raise FalsificationError(f"expected 465 BED regions; got {len(regions)}")

    suite = run_falsification_suite()
    m3_mask = verify_m3_chromosome_masks(m3, regions)

    checks = dict(suite["checks"])
    checks["m3_chromosome_mask_exclusivity"] = bool(m3_mask["all_folds_exclusive"])
    checks["m3_disposition_frozen"] = m3["disposition"] == EXPECTED_M3_DISPOSITION
    all_pass = all(bool(v) for v in checks.values())

    return {
        "record_type": "masked_atac_pilot_m4_falsification",
        "date": "2026-10-01",
        "disposition": "FALSIFICATION_PASS" if all_pass else "FALSIFICATION_FAIL",
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
            "m3_splits_and_sampling": str(m3_json_path),
            "m3_disposition": m3["disposition"],
            "union_bed": str(union_bed),
            "n_regions": 465,
        },
        "metric_contract": {
            "binary_target": "1 if exact-region unique_fragment_overlap count > 0 else 0",
            "primary_aggregation": (
                "equal mean across donors of within-donor mean cell binary log-loss"
            ),
            "probability_clip": 1e-15,
            "mixed_cell_labels_allowed": True,
            "donor_average_probability_forbidden_as_primary": True,
            "fake_disease_class_forbidden": True,
            "hand_calculated_example": suite["metric_example"],
            "oracle_constant_direction": suite["direction"],
        },
        "leakage_contract": {
            "mask": "whole target chromosome excluded from ATAC input",
            "fit_statistics": (
                "ATAC TF/IDF/panel depth fit on visible regions and train rows only"
            ),
            "target_perturbation_leaves_inputs_unchanged": suite["leakage"][
                "target_perturbation"
            ]["passed"],
            "target_inclusive_depth_refused": suite["leakage"]["target_inclusive_depth"][
                "refused_path"
            ],
            "target_inclusive_depth_demonstration": suite["leakage"][
                "target_inclusive_depth"
            ],
            "forbidden_feature_fields": list(FORBIDDEN_FEATURE_FIELDS),
            "rna_is_separate_measured_assay_allowed": True,
            "disease_donor_author_cell_type_as_features": False,
        },
        "adapter_requirements": {
            **ADAPTER_REQUIREMENTS,
            "live_mil_mixed_label_check": suite["adapter"],
        },
        "guards": {
            "feature_order_hash": suite["feature_order"],
            "prediction_reload": suite["reload"],
            "output_overwrite_refusal_verified": suite["overwrite_refusal_verified"],
        },
        "m3_mask_verification": m3_mask,
        "checks": checks,
        "what_this_authorizes": {
            "allowed_next": [
                "Checkpoint B after leakage/metric fixtures pass",
                "M5 estimand/statistical/resource protocol freeze",
                "Continue independent safe feasibility without fits",
            ],
            "not_authorized": [
                "Model fitting or neural smoke learning",
                "Reusing mil_loop donor-label bags for mixed cell targets without adapter",
                "Donor-average probability or fake disease class as primary estimand",
                "Target-inclusive ATAC depth/QC/IDF/latent inputs",
                "Relabeling Q2/S9/S10/primary B_NULL",
            ],
        },
        "no_fits": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    m = report["metric_contract"]
    ex = m["hand_calculated_example"]
    checks = report["checks"]
    lines = [
        "# Masked ATAC pilot M4 — leakage and metric falsification",
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
        "## Metric contract (no fits)",
        "",
        f"- Binary target: {m['binary_target']}",
        f"- Primary aggregation: {m['primary_aggregation']}",
        f"- Probability clip: `{m['probability_clip']}`",
        "- Mixed cell labels within donor: **allowed**",
        "- Donor-average probability as primary: **forbidden**",
        "- Fake donor disease class: **forbidden**",
        "",
        "### Hand-calculated mixed-label example",
        "",
        "- Unequal cells (A=3, B=1); donor A mixed labels",
        f"- Expected donor-average cell log-loss: "
        f"`{ex['expected_donor_average']:.12f}`",
        f"- Got: `{ex['got_donor_average']:.12f}`",
        f"- Wrong log-loss(donor-mode-y, donor-mean-p): "
        f"`{ex['wrong_donor_avg_prob_value']:.12f}` "
        f"(differs from correct `{ex['correct_donor_avg_cell_loss']:.12f}`)",
        "",
        "### Oracle / constant direction",
        "",
        f"- Oracle near-zero: **{m['oracle_constant_direction']['oracle_near_zero']}** "
        f"(value `{m['oracle_constant_direction']['oracle_value']:.6g}`)",
        f"- Constant p=0.5 equals ln(2): "
        f"**{m['oracle_constant_direction']['constant_equals_ln2']}**",
        f"- Oracle better than constant: "
        f"**{m['oracle_constant_direction']['oracle_better_than_constant']}**",
        "",
        "## Leakage contract",
        "",
        f"- Mask: {report['leakage_contract']['mask']}",
        f"- Fit statistics: {report['leakage_contract']['fit_statistics']}",
        "- Target-count perturbation leaves RNA + visible ATAC fit stats "
        f"unchanged: "
        f"**{report['leakage_contract']['target_perturbation_leaves_inputs_unchanged']}**",
        f"- Target-inclusive panel depth path refused: "
        f"`{report['leakage_contract']['target_inclusive_depth_refused']}` "
        "(toy demo shows visible TF changes under that wrong path)",
        "- Forbidden feature fields: "
        + ", ".join(
            f"`{x}`"
            for x in report["leakage_contract"]["forbidden_feature_fields"]
        ),
        "",
        "## Adapter requirements",
        "",
        f"- Existing MIL assumption: "
        f"{report['adapter_requirements']['existing_mil_loop_assumption']}",
        f"- Required adapter: {report['adapter_requirements']['required_adapter']}",
        f"- Live mixed-label refusal: "
        f"**{report['adapter_requirements']['live_mil_mixed_label_check']['mixed_refused']}** "
        f"(`{report['adapter_requirements']['live_mil_mixed_label_check']['message']}`)",
        f"- Preserve classification API: "
        f"**{report['adapter_requirements']['preserve_classification_api']}**",
        "",
        "## M3 frozen-fold mask recheck",
        "",
        f"- M3 disposition: `{report['m3_mask_verification']['m3_disposition']}`",
        f"- Folds checked: **{report['m3_mask_verification']['n_folds_checked']}**; "
        f"all chromosome-exclusive: "
        f"**{report['m3_mask_verification']['all_folds_exclusive']}**",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- `{key}`: **{value}**")
    lines.extend(
        [
            "",
            "## Guards",
            "",
            f"- Feature-order hash sensitive to permutation: "
            f"**{checks['feature_order_hash_sensitive']}**",
            f"- Prediction reload identity: "
            f"**{checks['prediction_reload_identity']}**",
            f"- Output overwrite refused: "
            f"**{checks['output_overwrite_refused']}**",
            "",
            "## What this does / does not authorize",
            "",
            "Allowed next: "
            + "; ".join(report["what_this_authorizes"]["allowed_next"]),
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
    parser.add_argument("--m3-json", type=Path, default=DEFAULT_M3_JSON)
    parser.add_argument("--union-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    report = build_report(m3_json_path=args.m3_json, union_bed=args.union_bed)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "FALSIFICATION.json"
    out_md = args.out_dir / "FALSIFICATION.md"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    out_md.write_text(render_markdown(report))
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(f"disposition={report['disposition']}")
    return 0 if report["disposition"] == "FALSIFICATION_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
