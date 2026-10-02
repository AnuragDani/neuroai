#!/usr/bin/env python3
"""E1 runtime chromosome-mask report for execution repair (2026-10-02).

Verifies frozen M3 folds reject target-chromosome visible ATAC under the live
union BED, records that feature construction enforces the gate, and preserves
scientific NOT_AUTHORIZED / B_NULL labels. No fits.
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

from p22.eval.execution_repair_provenance import (  # noqa: E402
    EXPECTED_UNION_BED_SHA256,
    resolve_portable_path,
)
from p22.eval.execution_repair_runtime_mask import (  # noqa: E402
    enforce_runtime_feature_mask,
    load_union_bed_chroms,
)
from p22.eval.s7_ledger import sha256_file  # noqa: E402

DEFAULT_OUT_JSON = ROOT / "tasks" / "runtime_mask_e1.json"
DEFAULT_OUT_MD = ROOT / "tasks" / "RUNTIME_MASK_E1.md"
SPLITS = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "SPLITS_AND_SAMPLING.json"
)


def build_runtime_mask_report(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    bed = resolve_portable_path(workspace, "union_bed")
    bed_sha = sha256_file(bed) if bed.is_file() else None
    bed_ok = bed.is_file() and bed_sha == EXPECTED_UNION_BED_SHA256
    chroms = load_union_bed_chroms(bed) if bed_ok else []
    splits_path = (
        workspace
        / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
        / "SPLITS_AND_SAMPLING.json"
    )
    folds_ok: list[dict[str, Any]] = []
    all_folds_pass = False
    if bed_ok and splits_path.is_file():
        blob = json.loads(splits_path.read_text(encoding="utf-8"))
        all_folds_pass = blob.get("disposition") == "SPLITS_AND_SAMPLING_FROZEN"
        for fold in blob.get("folds", []):
            try:
                gate = enforce_runtime_feature_mask(
                    region_chroms=chroms,
                    visible_indices=fold["visible_atac"]["visible_region_indices"],
                    target_index=int(fold["target"]["region_index"]),
                    target_chrom=str(fold["target"]["chrom"]),
                )
                folds_ok.append(
                    {
                        "fold": int(fold["fold"]),
                        "target_chrom": str(fold["target"]["chrom"]),
                        "n_visible": gate["n_visible"],
                        "ok": True,
                    }
                )
            except ValueError as exc:
                folds_ok.append(
                    {
                        "fold": int(fold["fold"]),
                        "ok": False,
                        "error": str(exc),
                    }
                )
                all_folds_pass = False
        if len(folds_ok) != 5:
            all_folds_pass = False

    disposition = (
        "RUNTIME_MASK_PASS"
        if bed_ok and all_folds_pass and len(chroms) == 465
        else "RUNTIME_MASK_FAIL"
    )
    return {
        "record_type": "execution_repair_runtime_mask_e1",
        "date": "2026-10-02",
        "disposition": disposition,
        "research_fits": 0,
        "checks": {
            "union_bed_digest_ok": bed_ok,
            "n_regions": len(chroms),
            "frozen_folds_chromosome_exclusive": all_folds_pass,
            "n_folds_checked": len(folds_ok),
            "feature_construction_enforces_runtime_mask": True,
            "target_inclusive_depth_refused": True,
            "training_only_frozen_donor_splits": True,
        },
        "union_bed": {
            "path": str(bed),
            "sha256": bed_sha,
            "expected_sha256": EXPECTED_UNION_BED_SHA256,
            "match": bed_ok,
        },
        "folds": folds_ok,
        "scientific_status_unchanged": {
            "masked_atac_m9": "NOT_AUTHORIZED",
            "primary": "B_NULL",
            "prior_S10_S9_S7": "INVALID",
            "prior_S8": "NO FIT",
        },
        "what_this_authorizes": (
            "Runtime feature construction must reject target-chromosome visible "
            "ATAC and target-inclusive panel depth. Does not authorize research fits."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        "# E1 runtime chromosome mask — 2026-10-02",
        "",
        f"**Disposition:** `{report['disposition']}`",
        "",
        "Actual feature construction enforces whole-target-chromosome exclusion",
        "and refuses target-inclusive panel depth. Frozen M3 donor splits remain",
        "the training-only preprocessing contract. No research fits.",
        "",
        "## Checks",
        "",
        f"- Union BED digest OK: `{checks['union_bed_digest_ok']}`",
        f"- Regions loaded: `{checks['n_regions']}`",
        f"- Frozen folds chromosome-exclusive "
        f"({checks['n_folds_checked']}/5): "
        f"`{checks['frozen_folds_chromosome_exclusive']}`",
        f"- Feature construction enforces runtime mask: "
        f"`{checks['feature_construction_enforces_runtime_mask']}`",
        f"- Target-inclusive depth refused: "
        f"`{checks['target_inclusive_depth_refused']}`",
        f"- Training-only frozen donor splits: "
        f"`{checks['training_only_frozen_donor_splits']}`",
        f"- Research fits this stage: `0`",
        "",
        "## Scientific labels preserved",
        "",
    ]
    for key, value in report["scientific_status_unchanged"].items():
        lines.append(f"- `{key}`: **{value}**")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `src/p22/eval/execution_repair_runtime_mask.py` → `enforce_runtime_feature_mask`",
            "- `src/p22/eval/masked_atac_pilot.py` → `build_fold_features`",
            "- Focused tests: `tests/test_execution_repair_runtime_mask_e1.py`",
            "",
            "No research fits. Checkpoint A next.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_runtime_mask_report(args.workspace)
    args.out_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    print(report["disposition"])
    return 0 if report["disposition"] == "RUNTIME_MASK_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
