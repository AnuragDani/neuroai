#!/usr/bin/env python3
"""Q8 dry-run implement + falsification for S9 analytic pairing-use.

Verifies frozen protocol hashes, oracle/null scaffolding, job coverage,
paired_model reuse, finite gradients, reload equality, and refusal contracts.
Does not execute research fits or trainability-with-learning.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.s9_analytic import (  # noqa: E402
    render_implement_markdown,
    run_q8_dry_run,
)

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)


def write_outputs(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    report = run_q8_dry_run(
        protocol_path=out_dir / "SYNTHETIC_PROTOCOL.json",
        split_path=out_dir / "SPLIT_MANIFEST.json",
        ledger_path=out_dir / "FIT_LEDGER.json",
    )
    json_path = out_dir / "implement.json"
    md_path = out_dir / "IMPLEMENT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_implement_markdown(report))
    return {
        "disposition": report["disposition"],
        "protocol_id": report["protocol_id"],
        "research_fits_executed": report["research_fits_executed"],
        "job_total": report["job_coverage"]["total"],
        "oracle_gate": report["oracle"]["oracle_gate"],
        "paths": {"implement_json": str(json_path), "implement_md": str(md_path)},
        "hashes": report["hashes"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    summary = write_outputs(args.out_dir)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
