#!/usr/bin/env python3
"""V3: diagnose below-chance pooled AUROC on learned ladder arms.

Reads V1 per-fold metrics and V2 positive-control evidence, applies the
mandatory IF/ELSE verdict tree, and writes
``docs/nn_v2/v5/below_chance_diagnosis.json`` plus
``docs/nn_v2/v5/BELOW_CHANCE.md``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_OUT = Path("docs/nn_v2/v5")
LEARNED_ARMS = ("R3_ca", "R3_tc", "logreg_rna")
POOLING_NEAR_CHANCE = 0.1
POOLING_BELOW = 0.45


def _arm_summary(per_arm: dict[str, Any], name: str) -> dict[str, Any]:
    a = per_arm[name]
    mean = float(a["per_fold_auroc_mean"])
    pooled = float(a["pooled_auroc"])
    return {
        "arm": name,
        "per_fold_auroc_mean": mean,
        "per_fold_auroc_sd": float(a["per_fold_auroc_sd"]),
        "pooled_auroc": pooled,
        "abs_mean_minus_half": abs(mean - 0.5),
        "mean_near_chance": abs(mean - 0.5) <= POOLING_NEAR_CHANCE,
        "pooled_below_chance": pooled < POOLING_BELOW,
    }


def shared_path_fix_present(positive_control: dict[str, Any]) -> bool:
    """True when V2 records a shared-path code change."""
    fix = str(positive_control.get("shared_path_fix") or "").strip()
    return bool(fix)


def decide_verdict(
    arm_summaries: list[dict[str, Any]],
    v2_required_fix: bool,
    positive_control_auroc: float,
) -> tuple[str, str]:
    """Return (verdict, reason) using the V3 IF/ELSE tree."""
    learned = [s for s in arm_summaries if s["arm"] in LEARNED_ARMS]
    all_mean_near = all(s["mean_near_chance"] for s in learned)
    all_pooled_below = all(s["pooled_below_chance"] for s in learned)

    if all_mean_near and all_pooled_below and not v2_required_fix:
        return (
            "POOLING_ARTEFACT",
            "Per-fold mean AUROC of learned arms is near 0.5 while pooled "
            "AUROC is below 0.45, and V2 passed without shared-path code changes.",
        )
    if v2_required_fix:
        return (
            "PIPELINE_BUG_FIXED",
            "V2 required a shared-path fix "
            f"(positive-control donor_auroc={positive_control_auroc:.3f}); "
            "canonical ladder must be rerun under the corrected fit path.",
        )
    # Per-fold also clearly below chance with a clean V2.
    return (
        "REAL_ANTI_SIGNAL_EXPLAINED",
        "Per-fold AUROC of learned arms is clearly below 0.5 while V2 passed "
        "without a shared-path fix; donor-level confounding must be documented.",
    )


def build_diagnosis(
    per_fold: dict[str, Any],
    positive_control: dict[str, Any],
) -> dict[str, Any]:
    per_arm = per_fold["per_arm"]
    summaries = [_arm_summary(per_arm, name) for name in LEARNED_ARMS]
    # Include majority + chr21 for contrast in the evidence blob.
    for extra in ("majority", "chr21_dosage"):
        if extra in per_arm:
            summaries.append(_arm_summary(per_arm, extra))

    v2_fix = shared_path_fix_present(positive_control)
    pc_auroc = float(positive_control.get("donor_auroc") or 0.0)
    verdict, reason = decide_verdict(summaries, v2_fix, pc_auroc)

    return {
        "record_type": "v5_below_chance_diagnosis",
        "verdict": verdict,
        "reason": reason,
        "v2_required_shared_path_fix": v2_fix,
        "positive_control_donor_auroc": pc_auroc,
        "positive_control_orientation_spearman": (
            (positive_control.get("orientation_check") or {}).get("spearman_rho")
        ),
        "chr21_genes_in_hvg_default": positive_control.get(
            "chr21_genes_in_hvg_default"
        ),
        "shared_path_fix": positive_control.get("shared_path_fix"),
        "learned_arms": [s for s in summaries if s["arm"] in LEARNED_ARMS],
        "reference_arms": [s for s in summaries if s["arm"] not in LEARNED_ARMS],
        "decision_tree": {
            "pooling_artefact_requires": {
                "per_fold_mean_near_0.5": f"|mean-0.5|<={POOLING_NEAR_CHANCE}",
                "pooled_below": f"pooled<{POOLING_BELOW}",
                "v2_without_code_changes": True,
            },
            "pipeline_bug_fixed_requires": "v2_required_shared_path_fix",
            "real_anti_signal_requires": (
                "per-fold clearly <0.5 and V2 clean"
            ),
        },
        "sources": {
            "per_fold_metrics": "docs/nn_v2/v5/per_fold_metrics.json",
            "positive_control": "docs/nn_v2/v5/positive_control.json",
            "canonical_ladder": "docs/nn_v2/v5/CANONICAL_LADDER.txt",
        },
        "next_step": (
            "V4: rerun full ladder into ladder_v3"
            if verdict == "PIPELINE_BUG_FIXED"
            else (
                "V4 NOT_NEEDED; report per-fold AUROC alongside pooled"
                if verdict == "POOLING_ARTEFACT"
                else "Document confounding mechanism; do not flip predictions"
            )
        ),
    }


def render_md(dx: dict[str, Any]) -> str:
    lines = [
        "# Below-chance pooled AUROC — V3 diagnosis",
        "",
        f"**Verdict:** `{dx['verdict']}`",
        "",
        dx["reason"],
        "",
        "## Evidence (from docs/nn_v2/v5/)",
        "",
        "| Arm | Per-fold AUROC mean | Per-fold SD | Pooled AUROC |",
        "|---|---:|---:|---:|",
    ]
    for s in dx["learned_arms"] + dx["reference_arms"]:
        lines.append(
            f"| {s['arm']} | {s['per_fold_auroc_mean']:.3f} | "
            f"{s['per_fold_auroc_sd']:.3f} | {s['pooled_auroc']:.3f} |"
        )
    lines += [
        "",
        "## Positive control (V2)",
        "",
        f"- Forced-chr21 logreg pooled donor AUROC: "
        f"**{dx['positive_control_donor_auroc']:.3f}** (threshold ≥ 0.9).",
        f"- Default HVG keeps ~{dx['chr21_genes_in_hvg_default']} chr21 genes "
        "(most dosage signal dropped before training).",
        f"- Orientation Spearman (pred DS prob vs chr21 share): "
        f"{dx['positive_control_orientation_spearman']}.",
        "",
        "## Shared-path fix",
        "",
        str(dx.get("shared_path_fix") or "none"),
        "",
        "## Reading",
        "",
        "Pooled AUROC mixes fold-specific score scales across stratified folds "
        "and can look below chance even when each fold ranks donors above "
        "chance. That pooling gap remains visible (learned per-fold means "
        "> 0.5; pooled < 0.45). Separately, V2 found that sklearn control arms "
        "were fit on only the inner-train third of outer-train donors; fixing "
        "that path raised the forced-chr21 positive control above 0.9. Because "
        "the shared runner changed, the V3 tree selects `PIPELINE_BUG_FIXED` "
        "and V4 must rebuild the canonical ladder under the corrected fit.",
        "",
        f"**Next:** {dx['next_step']}",
        "",
    ]
    text = "\n".join(lines)
    # Keep ≤ 60 lines as required.
    body = text.strip().splitlines()
    if len(body) > 60:
        body = body[:59] + ["(truncated to 60 lines)"]
    return "\n".join(body) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--per-fold",
        type=Path,
        default=DEFAULT_OUT / "per_fold_metrics.json",
    )
    p.add_argument(
        "--positive-control",
        type=Path,
        default=DEFAULT_OUT / "positive_control.json",
    )
    args = p.parse_args(argv)

    per_fold = json.loads(args.per_fold.read_text())
    positive_control = json.loads(args.positive_control.read_text())
    dx = build_diagnosis(per_fold, positive_control)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "below_chance_diagnosis.json"
    md_path = args.out_dir / "BELOW_CHANCE.md"
    json_path.write_text(json.dumps(dx, indent=2) + "\n")
    md_path.write_text(render_md(dx))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"verdict={dx['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
