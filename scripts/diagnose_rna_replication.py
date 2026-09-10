#!/usr/bin/env python3
"""One owned CPU process with a wall deadline and conservative sampled-RSS stop."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3


def _rss_bytes(pid: int) -> int:
    result = subprocess.run(
        ["/bin/ps", "-o", "rss=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=True,
        timeout=1,
    )
    value = int(result.stdout.strip()) * 1024
    if value <= 0:
        raise ValueError("RSS monitor returned no resident memory")
    return value


def supervise(
    command: list[str],
    output_dir: Path,
    *,
    timeout_seconds: float = 1800,
    stop_rss_bytes: int = 5 * GIB,
    poll_seconds: float = 0.1,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    started, process = time.monotonic(), None
    report = {
        "status": "MONITOR_ERROR",
        "pid": None,
        "exit_code": None,
        "peak_sampled_rss_bytes": 0,
        "stop_rss_bytes": stop_rss_bytes,
        "timeout_seconds": timeout_seconds,
        "poll_seconds": poll_seconds,
        "budget_bytes": 6 * GIB,
        "enforcement": "sampled RSS early stop; not a kernel hard memory ceiling",
    }
    try:
        _rss_bytes(os.getpid())  # Refuse BEFORE launch if the monitor is unavailable.
        with (
            (output_dir / "stdout.log").open("x") as stdout,
            (output_dir / "stderr.log").open("x") as stderr,
        ):
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
            report["pid"] = process.pid
            while process.poll() is None:
                if time.monotonic() - started >= timeout_seconds:
                    report["status"] = "TIMEOUT"
                    break
                try:
                    rss = _rss_bytes(process.pid)
                except (OSError, ValueError, subprocess.SubprocessError):
                    if process.poll() is not None:
                        break  # Normal exit raced the OS query.
                    raise
                report["peak_sampled_rss_bytes"] = max(report["peak_sampled_rss_bytes"], rss)
                if rss >= stop_rss_bytes:
                    report["status"] = "MEMORY_LIMIT"
                    break
                time.sleep(
                    min(poll_seconds, max(0, timeout_seconds - (time.monotonic() - started)))
                )
            if report["status"] not in {"TIMEOUT", "MEMORY_LIMIT"} and process.poll() is not None:
                report["status"] = "COMPLETED" if process.returncode == 0 else "CHILD_FAILED"
                if time.monotonic() - started >= timeout_seconds:
                    report["status"] = "TIMEOUT"
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report["reason"] = str(exc)
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            report["exit_code"] = process.wait()
        report["elapsed_seconds"] = time.monotonic() - started
        report["peak_sampled_rss_gib"] = report["peak_sampled_rss_bytes"] / GIB
        with (output_dir / "resources.json").open("x") as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rna_donor_influence.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    from p22.eval.rna_donor_influence import load_config

    load_config(args.config)
    if os.environ.get("P22_PROFESSOR_APPROVED") != "1":
        parser.error("existing P22_PROFESSOR_APPROVED=1 per-run attestation required")
    # The diagnostic never launches further workers or GPU kernels.
    os.environ.update(
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
        MPLBACKEND="Agg",
    )
    child = (
        "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]+'/src'); "
        "from p22.eval.rna_donor_influence import run_analysis; "
        "run_analysis(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))"
    )
    result = supervise(
        [
            sys.executable,
            "-c",
            child,
            str(ROOT),
            str(args.config.resolve()),
            str(args.output_dir.resolve()),
        ],
        args.output_dir,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
