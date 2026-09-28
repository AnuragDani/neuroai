#!/usr/bin/env python3
"""P1/N11: summarize chr21-excluded_v3 vs the canonical ladder (CANONICAL_LADDER)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from p22.eval.repeated_comparison import repeated_model_accuracy, repeated_primary_contrast

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_EXCLUDED = ROOT / "reports/generated/nn_20260923/chr21_excluded_v3"
ARMS = ("R3_ca", "R3_tc", "logreg_rna", "logreg_concat")
OUT_JSON = ROOT / "docs/nn_v2/chr21_excluded.json"
ROBUSTNESS = ROOT / "docs/nn_v2/ROBUSTNESS.md"


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def load_repeats(folds_dir: Path):
    per_repeat: dict = {}
    arms: set[str] = set()
    for path in sorted(folds_dir.glob("*.json")):
        rec = json.loads(path.read_text())
        rep = int(rec["repeat"])
        arm = rec["arm"]
        arms.add(arm)
        per_repeat.setdefault(rep, {}).setdefault(arm, []).append(
            pd.DataFrame(
                {
                    "donor_id": rec["donor_ids"],
                    "label": rec["donor_labels"],
                    "probability": rec["donor_probabilities"],
                }
            )
        )
    repeats = []
    for rep in sorted(per_repeat):
        entry = {"repeat": rep}
        for arm, frames in per_repeat[rep].items():
            entry[arm] = pd.concat(frames, ignore_index=True)
        repeats.append(entry)
    return repeats, arms


def decide_label(results: dict) -> str:
    bas = [results[a]["ba_without_chr21"] for a in ARMS if a in results]
    if bas and all(ba <= 0.55 for ba in bas):
        return "DOSAGE_DOMINATED"
    for arm in ARMS:
        if arm in results and results[arm]["ba_without_chr21"] >= 0.60:
            return f"BEYOND_DOSAGE ({arm})"
    return "PARTIAL_DOSAGE"


def summarize(ladder_dir: Path, excluded_dir: Path) -> dict:
    ladder_repeats, ladder_arms = load_repeats(ladder_dir / "folds")
    excluded_repeats, excluded_arms = load_repeats(excluded_dir / "folds")
    results: dict = {}
    for arm in ARMS:
        if arm not in excluded_arms or arm not in ladder_arms:
            continue
        acc_ladder = repeated_model_accuracy(ladder_repeats, model=arm)
        acc_excluded = repeated_model_accuracy(excluded_repeats, model=arm)
        joint = []
        for l_rep, e_rep in zip(ladder_repeats, excluded_repeats):
            row = {"repeat": l_rep["repeat"]}
            row[f"{arm}_with"] = l_rep.get(arm, pd.DataFrame())
            row[f"{arm}_without"] = e_rep.get(arm, pd.DataFrame())
            if not row[f"{arm}_with"].empty and not row[f"{arm}_without"].empty:
                joint.append(row)
        diff = repeated_primary_contrast(
            joint, model=f"{arm}_with", reference=f"{arm}_without"
        )
        results[arm] = {
            "ba_with_chr21": acc_ladder.get("mean", 0.0),
            "ba_without_chr21": acc_excluded.get("mean", 0.0),
            "paired_difference": diff.get("estimate", 0.0),
            "ci": list(diff.get("interval", [0.0, 0.0])),
        }
    label = decide_label(results)
    payload = {
        "record_type": "nn_v5_chr21_excluded",
        "ladder_source": str(ladder_dir.resolve()),
        "excluded_source": str(excluded_dir.resolve()),
        "n_excluded_folds": len(list((excluded_dir / "folds").glob("*.json"))),
        "label": label,
        **results,
    }
    return payload


def write_robustness(payload: dict) -> None:
    lines = [
        "# NN-v2 robustness (D13, D9) — tasks N11, N12",
        "",
        "## Source binding",
        "",
        f"- Accepted with-chr21 ladder: `{payload['ladder_source']}` (canonical; P1 N11 vs ladder_v3).",
        f"- N11 no-chr21 folds: `{payload['excluded_source']}` "
        f"(`n_folds={payload['n_excluded_folds']}`; arms R3_ca, R3_tc, logreg_rna, logreg_concat).",
        "- Prior ladder_v2 / chr21_excluded paths retained on disk; docs now bind to `_v3`.",
        "- N12 seed rerun for ladder_v3 is pending under P1 (`seeds_v3`).",
        "",
        "## chr21-excluded sensitivity (N11)",
        "",
    ]
    bits = []
    for arm in ARMS:
        if arm in payload:
            bits.append(f"{arm} {payload[arm]['ba_without_chr21']:.3f}")
    lines.append(
        f"Rebuilt `docs/nn_v2/chr21_excluded.json` against the canonical ladder. "
        f"Decision-tree N11 label **{payload['label']}**. "
        f"Per-arm no-chr21 BA: {', '.join(bits)}. "
        "Interpretation limited to this internal 30-donor cohort."
    )
    lines.append("")
    # Keep N12 section from prior file if present.
    old = ROBUSTNESS.read_text() if ROBUSTNESS.exists() else ""
    marker = "## Init-seed and sampling-seed sensitivity (N12)"
    if marker in old:
        lines.append(old[old.index(marker) :].rstrip())
        lines.append("")
    ROBUSTNESS.write_text("\n".join(lines) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--excluded", type=Path, default=DEFAULT_EXCLUDED)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--write-robustness", action="store_true")
    args = parser.parse_args(argv)
    ladder = args.ladder or resolve_canonical_ladder()
    if not (ladder / "folds").is_dir():
        raise SystemExit(f"missing ladder folds: {ladder / 'folds'}")
    if not (args.excluded / "folds").is_dir():
        raise SystemExit(f"missing excluded folds: {args.excluded / 'folds'}")
    payload = summarize(ladder, args.excluded)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n")
    if args.write_robustness:
        write_robustness(payload)
    print(json.dumps({"label": payload["label"], "n_arms": sum(1 for a in ARMS if a in payload),
                      "out": str(args.out_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
