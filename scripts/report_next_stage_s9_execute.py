#!/usr/bin/env python3
"""Q10 bounded S9 analytic pairing-use synthetic batch executor.

Verifies Checkpoint C / Q9 exact hashes, runs smoke+screen fits under the
authorized S9 raw root, replays pairing from saved sidecars (no refit), and
writes execute.json / EXECUTE.md. Does not unlock a biological pilot.
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

from p22.eval.s9_analytic import ALLOWED_RAW_ROOT  # noqa: E402
from p22.eval.s9_execute import (  # noqa: E402
    render_execute_markdown,
    run_q10_batch,
)

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)


def write_outputs(
    out_dir: Path,
    *,
    workers: int,
    torch_threads: int,
    skip_fits: bool,
    raw_root: Path | None,
) -> dict:
    out_dir = Path(out_dir)
    report = run_q10_batch(
        workspace=ROOT,
        protocol_path=out_dir / "SYNTHETIC_PROTOCOL.json",
        split_path=out_dir / "SPLIT_MANIFEST.json",
        ledger_path=out_dir / "FIT_LEDGER.json",
        review_path=out_dir / "NO_FIT_REVIEW.json",
        raw_root=raw_root or (ROOT / ALLOWED_RAW_ROOT),
        workers=workers,
        torch_threads=torch_threads,
        skip_fits=skip_fits,
    )
    json_path = out_dir / "execute.json"
    md_path = out_dir / "EXECUTE.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_execute_markdown(report))
    return {
        "disposition": report["disposition"],
        "protocol_id": report["protocol_id"],
        "research_fits_executed": report["research_fits_executed"],
        "coverage_complete": report["coverage"]["complete"],
        "raw_root": report["raw_root"],
        "resources": report["resources"],
        "paths": {"execute_json": str(json_path), "execute_md": str(md_path)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--torch-threads", type=int, default=2)
    parser.add_argument(
        "--skip-fits",
        action="store_true",
        help="Replay/summarize only from existing ledger (no new fits).",
    )
    args = parser.parse_args(argv)
    summary = write_outputs(
        args.out_dir,
        workers=args.workers,
        torch_threads=args.torch_threads,
        skip_fits=args.skip_fits,
        raw_root=args.raw_root,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
