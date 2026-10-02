#!/usr/bin/env python3
"""Dispatch M9 smoke or main jobs under the locked M8 authorization path.

Does not mutate M8 REQUIRED_LOCK_KEYS source files. New module
``masked_atac_pilot`` provides real-data fit_fn + durable resume auth.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from p22.eval.masked_atac_pilot import run_m9_jobs
from p22.eval.s7_ledger import sha256_file

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929"
    / "masked_atac_pilot_20261001"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stages",
        nargs="+",
        default=["smoke"],
        choices=["smoke", "main"],
        help="Job stages to dispatch (default: smoke only)",
    )
    parser.add_argument(
        "--allow-progressed-counter",
        action="store_true",
        help="Resume after attempt_counter has left the locked zero digest",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional summary JSON path under the task dir",
    )
    args = parser.parse_args()

    summary = run_m9_jobs(
        workspace=ROOT,
        stages=tuple(args.stages),
        allow_progressed_counter=bool(args.allow_progressed_counter),
    )
    out = args.out_json
    if out is None:
        tag = "_".join(args.stages)
        out = TASK_DIR / f"EXECUTE_{tag.upper()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=2, default=str) + "\n"
    if out.exists():
        # Allow overwrite of our own stage summary only if content differs and
        # prior run was incomplete — still refuse silently replacing sidecars.
        # Summaries are re-writable stage reports; prediction sidecars stay refuse.
        out.write_text(text, encoding="utf-8")
    else:
        out.write_text(text, encoding="utf-8")
    print(json.dumps({
        "out_json": str(out),
        "out_sha256": sha256_file(out),
        "stages": summary["stages"],
        "n_executed": summary["execution"]["n_executed_this_call"],
        "n_skipped": summary["execution"]["n_skipped_already_done"],
        "counter_total_used": summary["counter"]["total_attempts"]["used"],
        "counter_smoke_used": summary["counter"]["smoke_fits"]["used"],
        "authorization_mode": summary["authorization"]["mode"],
        "wall_seconds": summary["execution"]["wall_seconds"],
    }, indent=2))
    failed = [
        r for r in summary["execution"]["records"] if r.get("status") != "ok"
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
