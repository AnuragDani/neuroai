#!/usr/bin/env python3
"""M10 no-fit saved-prediction replay for the masked ATAC pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from p22.eval.masked_atac_m10_replay import run_m10_replay, write_replay_reports

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=ROOT,
        help="Worktree root (default: repo containing this script)",
    )
    args = parser.parse_args()
    report = run_m10_replay(args.workspace)
    paths = write_replay_reports(args.workspace, report=report)
    summary = {
        "disposition": report["disposition"],
        "diagnostic_replay_pass": report["diagnostic_replay_pass"],
        "prospective_executor_review_gate": report[
            "prospective_executor_review_gate"
        ],
        "scientific_acceptance_of_M9": report["scientific_acceptance_of_M9"],
        "pooled_tc_minus_ca": report["primary_contrast"]["pooled_estimate"],
        "bootstrap_interval": report["primary_contrast"]["bootstrap"]["interval"],
        "exploratory_advantage_observed": report["primary_contrast"][
            "exploratory_advantage_observed"
        ],
        "counters_preserved": report["post_replay_counter"]["preserved"],
        "fits_run": report["fits_run"],
        "artifact_du_gib": report["artifact_bytes"]["du_gib"],
        "replay_json": paths["REPLAY.json"],
        "replay_json_sha256": paths["REPLAY.json.sha256"],
        "counter_sha256": report["post_replay_counter"]["sha256_after"],
    }
    print(json.dumps(summary, indent=2))
    return 0 if report["diagnostic_replay_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
