#!/usr/bin/env python
"""Run the synthetic toy pilot: every configured model, every configured seed.

Writes one run record and one report per model and seed under ``reports/generated``, then
prints an across-seed summary. Synthetic data only; the runner refuses anything else.

    python scripts/run_toy_pilot.py --config configs/toy_pilot.json
    python scripts/run_toy_pilot.py --seeds 0 1 --quick
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import p22  # noqa: E402
from p22.reports.render import write_run_report  # noqa: E402
from p22.runs.config import load_run_config  # noqa: E402
from p22.runs.registry import RunRegistry  # noqa: E402
from p22.training.seed_runner import (  # noqa: E402
    build_record,
    run_all_seeds,
    summarize_across_seeds,
)

DEFAULT_CONFIG = REPO_ROOT / "configs" / "toy_pilot.json"
GENERATED = REPO_ROOT / "reports" / "generated"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="run configuration JSON"
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=None, help="override the configured seeds"
    )
    parser.add_argument(
        "--replicates", type=int, default=None, help="override the bootstrap replicate count"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="small run for a smoke check: two seeds and 50 bootstrap replicates",
    )
    parser.add_argument(
        "--out", type=Path, default=GENERATED, help="output root; must be a generated directory"
    )
    parser.add_argument("--metric", default="accuracy", help="metric shown in the printed summary")
    return parser.parse_args(argv)


def _display(path: Path) -> str:
    """Show a repository-relative path when possible, absolute otherwise."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    config = load_run_config(arguments.config)
    seeds = arguments.seeds if arguments.seeds is not None else list(config.seeds)
    replicates = arguments.replicates
    if arguments.quick:
        seeds = seeds[:2]
        replicates = replicates or 50

    print(f"config: {config.name} ({config.config_hash[:12]})")
    print(f"data mode: {config.data_mode} | approval blocked: {p22.approval_blocked()}")
    print(f"seeds: {seeds}")
    print(f"models: {[model.name for model in config.models]}")
    print()

    registry = RunRegistry(arguments.out / "runs")
    runs = []
    for seed in seeds:
        print(f"seed {seed} ...", flush=True)
        run = run_all_seeds(config, seeds=[seed], n_replicates=replicates)[0]
        runs.append(run)
        for outcome in run.outcomes.values():
            record = build_record(config, run, outcome)
            registry.write(record)
            write_run_report(record, arguments.out / "reports")
            value = outcome.metrics[arguments.metric]["value"]
            shown = "not applicable" if value is None else f"{value:.4f}"
            print(f"  {outcome.model_name:<28} {arguments.metric}={shown}")

    summary = summarize_across_seeds(runs, metrics=[arguments.metric])
    print()
    print(f"across-seed summary for {arguments.metric} ({len(runs)} seed(s)):")
    for model_name, metrics in summary.items():
        entry = metrics[arguments.metric]
        if entry["mean"] is None:
            print(f"  {model_name:<28} not applicable: {entry['not_applicable']}")
            continue
        spread = "sd=n/a" if entry["std"] is None else f"sd={entry['std']:.4f}"
        interval = entry["interval"]
        span = (
            f"no across-seed interval: {entry['not_applicable']}"
            if interval[0] is None
            else f"[{interval[0]:.4f}, {interval[1]:.4f}]"
        )
        print(f"  {model_name:<28} mean={entry['mean']:.4f} {spread} {span}")

    summary_path = arguments.out / "reports" / f"{config.name}_across_seeds.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summarize_across_seeds(runs), indent=2) + "\n")
    print()
    print(f"records: {_display(registry.root)}")
    print(f"summary: {_display(summary_path)}")
    print(
        "Overlapping across-seed intervals do not establish a difference between models, "
        "and none of these numbers transfer to real data."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
