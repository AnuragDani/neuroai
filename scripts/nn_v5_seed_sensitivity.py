#!/usr/bin/env python3
"""P1/N12: fixed-protocol seed sensitivity against the canonical ladder (seeds_v3)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from p22.eval.repeated_comparison import repeated_primary_contrast

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_SEEDS_ROOT = ROOT / "reports/generated/nn_20260923/seeds_v3"
PROTOCOL = ROOT / "configs/nn_protocol_v2_2026-09-23.json"
OUT_JSON = ROOT / "docs/nn_v2/seed_sensitivity.json"
ROBUSTNESS = ROOT / "docs/nn_v2/ROBUSTNESS.md"
LADDER_SUMMARY = ROOT / "docs/nn_v2/ladder_summary.json"
EXPECTED_R3_CA = 384250
EXPECTED_R3_TC = 380026
RUNS = [(m, 22) for m in range(5)] + [(0, 23), (0, 24)]
PY = Path("/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python")
RUNNER = ROOT / "scripts/run_nn_v2_comparison.py"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def reuse_ladder_as_m0_s22(ladder_dir: Path, dest: Path) -> None:
    src_folds = ladder_dir / "folds"
    dest_folds = dest / "folds"
    dest_folds.mkdir(parents=True, exist_ok=True)
    n = 0
    for arm in ("R3_ca", "R3_tc"):
        for src in sorted(src_folds.glob(f"*_{arm}.json")):
            shutil.copy2(src, dest_folds / src.name)
            n += 1
    if n != 50:
        raise RuntimeError(f"expected 50 R3_ca/R3_tc folds from {ladder_dir}, got {n}")
    (dest / "run.json").write_text(
        json.dumps(
            {
                "folds_expected": 50,
                "folds_done": 50,
                "failures": [],
                "source": str(ladder_dir.resolve()),
                "reused_arms": ["R3_ca", "R3_tc"],
                "model_seed": 0,
                "sampling_seed": 22,
            },
            indent=2,
        )
        + "\n"
    )


def assert_seed_fold_protocol(folds_dir: Path) -> dict:
    counts = {"R3_ca": [], "R3_tc": []}
    for path in folds_dir.glob("*.json"):
        rec = json.loads(path.read_text())
        arm = rec["arm"]
        if arm in counts:
            counts[arm].append(int(rec["parameter_count"]))
    for arm, expected in (("R3_ca", EXPECTED_R3_CA), ("R3_tc", EXPECTED_R3_TC)):
        if len(counts[arm]) != 25:
            raise RuntimeError(f"{folds_dir}: expected 25 {arm} folds, got {len(counts[arm])}")
        bad = [c for c in counts[arm] if c != expected]
        if bad:
            raise RuntimeError(
                f"{folds_dir}: {arm} parameter_count {bad[0]} != expected {expected}"
            )
    return {
        "R3_ca_parameter_count": EXPECTED_R3_CA,
        "R3_tc_parameter_count": EXPECTED_R3_TC,
        "n_folds": 50,
    }


def load_repeats_seed(folds_dir: Path):
    per_repeat: dict = {}
    for path in Path(folds_dir).glob("*.json"):
        rec = json.loads(path.read_text())
        if rec["arm"] not in ("R3_ca", "R3_tc"):
            continue
        per_repeat.setdefault(rec["repeat"], {}).setdefault(rec["arm"], []).append(
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
    return repeats


def decide_labels(outcome: str, model_estimates: list[float], sampling_spread: float) -> list[str]:
    labels: list[str] = []
    if outcome.startswith("A_"):
        n_above = sum(1 for e in model_estimates if e >= 0.07)
        labels.append("A_ROBUST_INIT" if n_above >= 4 else "A_FRAGILE")
    else:
        labels.append("SPREAD_ONLY")
    if sampling_spread > 0.07:
        labels.append("SAMPLING_SENSITIVE")
    return labels


def summarize(ladder_dir: Path, seeds_root: Path, protocol: Path) -> dict:
    model_ests: list[float] = []
    sampling_ests: list[float] = []
    results = {
        "record_type": "nn_v5_seed_sensitivity",
        "protocol_source": str(protocol.resolve()),
        "ladder_source": str(ladder_dir.resolve()),
        "seeds_root": str(seeds_root.resolve()),
        "rejected_buggy_seeds_root": str(
            Path("/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/seeds")
        ),
        "expected_parameter_counts": {"R3_ca": EXPECTED_R3_CA, "R3_tc": EXPECTED_R3_TC},
        "runs": {},
    }
    for m, s in RUNS:
        key = f"m_{m}_s_{s}"
        folds_dir = seeds_root / key / "folds"
        protocol_info = assert_seed_fold_protocol(folds_dir)
        repeats = load_repeats_seed(folds_dir)
        diff = repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")
        est = float(diff["estimate"])
        ci = [float(diff["interval"][0]), float(diff["interval"][1])]
        entry = {
            "estimate": est,
            "ci": ci,
            "model_seed": m,
            "sampling_seed": s,
            **protocol_info,
            "source": "ladder_reuse" if (m == 0 and s == 22) else str(seeds_root / key),
        }
        results["runs"][key] = entry
        results[key] = {"estimate": est, "ci": ci}
        if s == 22:
            model_ests.append(est)
        if m == 0:
            sampling_ests.append(est)
    model_spread = max(model_ests) - min(model_ests)
    sampling_spread = max(sampling_ests) - min(sampling_ests)
    results["model_seed_spread"] = float(model_spread)
    results["sampling_seed_spread"] = float(sampling_spread)
    outcome = json.loads(LADDER_SUMMARY.read_text()).get("outcome", "")
    results["ladder_outcome"] = outcome
    results["labels"] = decide_labels(outcome, model_ests, sampling_spread)
    return results


def run_seed_jobs(ladder_dir: Path, seeds_root: Path, protocol: Path, workers: int) -> None:
    seeds_root.mkdir(parents=True, exist_ok=True)
    py = str(PY if PY.exists() else sys.executable)
    for m, s in RUNS:
        out_dir = seeds_root / f"m_{m}_s_{s}"
        if m == 0 and s == 22:
            logging.info("Reusing %s R3_ca/R3_tc as m_0_s_22", ladder_dir)
            reuse_ladder_as_m0_s22(ladder_dir, out_dir)
            assert_seed_fold_protocol(out_dir / "folds")
            continue
        cmd = [
            py,
            str(RUNNER),
            "--protocol",
            str(protocol),
            "--out",
            str(out_dir),
            "--arms",
            "R3_ca",
            "R3_tc",
            "--model-seed",
            str(m),
            "--sampling-seed",
            str(s),
            "--resume",
            "--workers",
            str(workers),
        ]
        logging.info("Running seed m=%s s=%s -> %s", m, s, out_dir)
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": "src:scripts",
                "PYTHONDONTWRITEBYTECODE": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "TORCH_NUM_THREADS": "1",
            }
        )
        subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
        assert_seed_fold_protocol(out_dir / "folds")


def write_robustness(payload: dict) -> None:
    old = ROBUSTNESS.read_text() if ROBUSTNESS.exists() else ""
    marker = "## Init-seed and sampling-seed sensitivity (N12)"
    head = old.split(marker)[0].rstrip() if marker in old else old.rstrip()
    head_lines = [ln for ln in head.splitlines() if "N12 seed rerun for ladder_v3 is pending" not in ln]
    if not any("seeds_v3" in ln for ln in head_lines):
        out_lines, inserted = [], False
        for ln in head_lines:
            out_lines.append(ln)
            if "chr21_excluded_v3" in ln and not inserted:
                out_lines.append(
                    f"- N12 seeds: `{payload['seeds_root']}` "
                    f"(m_0_s_22 reuses `{payload['ladder_source']}`)."
                )
                inserted = True
        head_lines = out_lines if inserted else head_lines
    rows = []
    for key, entry in payload["runs"].items():
        tag = " (ladder reuse)" if entry.get("source") == "ladder_reuse" else ""
        rows.append(
            f"| {key}{tag} | {entry['estimate']:.4f} | "
            f"[{entry['ci'][0]:.4f}, {entry['ci'][1]:.4f}] |"
        )
    body = [
        marker, "",
        f"Accepted against `{payload['ladder_source']}` frozen widths (`seeds_v3`). "
        "Primary contrast (R3_ca−R3_tc) across model seeds 0–4 at sampling seed 22 "
        "and sampling seeds {22,23,24} at model seed 0:",
        "", "| run | estimate | CI |", "|---|---:|---|", *rows, "",
        f"Model-seed spread = {payload['model_seed_spread']:.3f}; "
        f"sampling-seed spread = {payload['sampling_seed_spread']:.3f}. "
        f"Ladder outcome is `{payload['ladder_outcome']}`, so decision-tree N12 reports "
        f"`{'` / `'.join(payload['labels'])}`. Evidence: `docs/nn_v2/seed_sensitivity.json`.",
        "",
    ]
    ROBUSTNESS.write_text("\n".join(head_lines + [""] + body))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--seeds-root", type=Path, default=DEFAULT_SEEDS_ROOT)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--workers", type=int, default=14)
    parser.add_argument("--run", action="store_true", help="Launch missing seed jobs")
    parser.add_argument("--write-robustness", action="store_true")
    args = parser.parse_args(argv)
    ladder = args.ladder or resolve_canonical_ladder()
    if args.run:
        run_seed_jobs(ladder, args.seeds_root, args.protocol, args.workers)
    payload = summarize(ladder, args.seeds_root, args.protocol)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n")
    if args.write_robustness:
        write_robustness(payload)
    print(
        json.dumps(
            {
                "labels": payload["labels"],
                "model_seed_spread": payload["model_seed_spread"],
                "sampling_seed_spread": payload["sampling_seed_spread"],
                "seeds_root": payload["seeds_root"],
                "out": str(args.out_json),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
