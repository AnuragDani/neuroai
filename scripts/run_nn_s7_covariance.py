"""Bounded S7 prospective synthetic-control driver.

Loads frozen NN inputs, freezes provenance, prepares five donor folds under the
screen generator tag, then advances the immutable stage pipeline
(smoke → screen → pairing-PC → conditional confirmation → handoff).

No real-disease-label fits, retuning, downloads, package installs, push or merge.
Scientific negatives and incompletes are complete results; biological primary
stays B_NULL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import torch  # noqa: E402

from p22.eval.s7_ledger import S7FitLedger  # noqa: E402
from p22.eval.s7_pipeline import (  # noqa: E402
    execute_next_stage,
    load_stage_state,
    run_until_handoff,
)
from p22.eval.s7_runner import (  # noqa: E402
    S7_PROTOCOL,
    check_disk_resources,
    write_resource_snapshot,
)
from p22.eval.s7_setup import (  # noqa: E402
    S7_CAP,
    FoldPackCache,
    build_provenance,
    load_region_panels,
    load_s7_inputs,
    prepare_s7_folds,
    preflight_param_match,
    resolve_s7_paths,
    write_preflight_record,
    write_split_log,
)


def _configure_threads(n_threads: int = 2) -> None:
    torch.set_num_threads(int(n_threads))
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # Already set in this process; ignore.
        pass


def run_preflight(
    *,
    repo_root: Path,
    cap: int = S7_CAP,
    check_disk: bool = True,
) -> dict:
    """Hash freeze, disk gate, param match, fold prep; return pipeline kwargs."""
    paths = resolve_s7_paths(repo_root)
    paths["durable_root"].mkdir(parents=True, exist_ok=True)
    paths["ledger_root"].mkdir(parents=True, exist_ok=True)
    paths["checkpoint_dir"].mkdir(parents=True, exist_ok=True)
    paths["result_dir"].mkdir(parents=True, exist_ok=True)
    paths["worktree_reports"].mkdir(parents=True, exist_ok=True)

    resources = None
    if check_disk:
        resources = check_disk_resources(output_root=paths["durable_root"])
        write_resource_snapshot(paths["durable_root"] / "resources_preflight.json", resources)

    param_match = preflight_param_match(S7_PROTOCOL)
    provenance = build_provenance(repo_root)
    inputs = load_s7_inputs(repo_root=repo_root, cap=cap, protocol=S7_PROTOCOL)
    panels = load_region_panels(paths["config"])
    folds = prepare_s7_folds(
        inputs,
        panels,
        generator_seed=1001,
        protocol=S7_PROTOCOL,
    )

    preflight = {
        "protocol_id": provenance.protocol_id,
        "paths": {key: str(value) for key, value in paths.items()},
        "param_match": param_match,
        "resources": resources,
        "donor_inventory": folds["donor_inventory"],
        "fake_label_tag": folds["fake_label_tag"],
        "split_log": folds["split_log"],
        "provenance": provenance.to_dict(),
        "cap": int(cap),
        "n_folds": len(folds["folds_by_index"]),
        "screen_generator_seed": int(folds["generator_seed"]),
    }
    write_preflight_record(paths["durable_root"] / "preflight.json", preflight)
    write_split_log(
        paths["durable_root"] / "split_logs" / f"split_log_seed_{folds['generator_seed']}.json",
        folds,
    )
    # Mirror a short pointer under the worktree reports tree.
    write_preflight_record(
        paths["worktree_reports"] / "preflight_pointer.json",
        {
            "durable_root": str(paths["durable_root"]),
            "ledger_root": str(paths["ledger_root"]),
            "checkpoint_dir": str(paths["checkpoint_dir"]),
            "result_dir": str(paths["result_dir"]),
            "preflight": str(paths["durable_root"] / "preflight.json"),
        },
    )

    ledger = S7FitLedger(paths["ledger_root"])
    ledger.load()
    if ledger.provenance_path.exists():
        ledger.assert_resume_hashes(provenance)
    else:
        ledger.freeze(provenance)

    fold_cache = FoldPackCache(
        inputs,
        panels,
        protocol=S7_PROTOCOL,
        split_log_dir=paths["durable_root"] / "split_logs",
        initial={int(folds["generator_seed"]): folds},
    )

    return {
        "paths": paths,
        "ledger": ledger,
        "provenance": provenance,
        "folds_by_index": folds["folds_by_index"],
        "positions_by_fold": folds["positions_by_fold"],
        "cell_ids_by_fold": folds["cell_ids_by_fold"],
        "fold_pack_resolver": fold_cache.resolver(),
        "fold_cache": fold_cache,
        "preflight": preflight,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository root containing the frozen S7 spec/config",
    )
    parser.add_argument("--cap", type=int, default=S7_CAP)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Advance exactly one pipeline stage then exit",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Freeze provenance and prepare folds; do not fit",
    )
    parser.add_argument(
        "--skip-disk-check",
        action="store_true",
        help="Skip free-disk gate (tests only; not for result fits)",
    )
    parser.add_argument("--torch-threads", type=int, default=2)
    args = parser.parse_args(argv)

    _configure_threads(args.torch_threads)
    bundle = run_preflight(
        repo_root=args.repo_root.resolve(),
        cap=args.cap,
        check_disk=not args.skip_disk_check,
    )
    if args.preflight_only:
        print(json.dumps({"action": "preflight_only", "preflight": bundle["preflight"]}, indent=2))
        return 0

    common = dict(
        ledger=bundle["ledger"],
        folds_by_index=bundle["folds_by_index"],
        positions_by_fold=bundle["positions_by_fold"],
        checkpoint_dir=bundle["paths"]["checkpoint_dir"],
        output_root=bundle["paths"]["stage_output_root"],
        result_dir=bundle["paths"]["result_dir"],
        cell_ids_by_fold=bundle["cell_ids_by_fold"],
        protocol=S7_PROTOCOL,
        feature_seed=1001,
        provenance=bundle["provenance"].to_dict(),
        check_disk=not args.skip_disk_check,
        fold_pack_resolver=bundle["fold_pack_resolver"],
    )

    if args.once:
        state = load_stage_state(bundle["paths"]["stage_output_root"])
        step = execute_next_stage(state=state, **common)
        print(
            json.dumps(
                {
                    "action": step["action"],
                    "done": step["done"],
                    "reason": step["state"].get("last_reason"),
                    "handoff_paths": step["state"].get("handoff_paths"),
                },
                indent=2,
            )
        )
        return 0

    out = run_until_handoff(**common)
    print(
        json.dumps(
            {
                "done": out["done"],
                "n_steps": out["n_steps"],
                "steps": out["steps"],
                "final_action": out.get("final_action"),
                "handoff_paths": (out.get("state") or {}).get("handoff_paths"),
                "reason": out.get("reason"),
            },
            indent=2,
        )
    )
    return 0 if out.get("done") else 2


if __name__ == "__main__":
    raise SystemExit(main())
