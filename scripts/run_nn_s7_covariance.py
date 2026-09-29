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
    S7_V2_DECLARED_SEEDS,
    FoldPackCache,
    S7V2PreflightError,
    assert_s7_v2_paths_disjoint,
    build_provenance,
    build_s7_v2_label_rows_by_seed,
    collect_s7_v2_donor_labels,
    load_region_panels,
    load_s7_inputs,
    prepare_s7_folds,
    preflight_param_match,
    resolve_s7_paths,
    run_s7_v2_all_seed_nofit_preflight,
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
    split_method: str = "v1",
    all_seed_preflight: bool = False,
) -> dict:
    """Hash freeze, disk gate, param match, fold prep; return pipeline kwargs.

    When ``split_method='v2'`` or ``all_seed_preflight=True``, validate all 11
    declared generator seeds (55 train/val/test triplets) before ledger freeze
    or any fit. Failure raises ``S7V2PreflightError`` (INVALID_PREFLIGHT).
    V2 writes only under the versioned durable/result roots and never aliases v1.
    """
    protocol_version = "v2" if split_method == "v2" else "v1"
    paths = resolve_s7_paths(repo_root, protocol_version=protocol_version)
    path_audit = None
    if protocol_version == "v2":
        path_audit = assert_s7_v2_paths_disjoint(repo_root)
        if not check_disk:
            raise ValueError(
                "S7-v2 live runs refuse --skip-disk-check; disk headroom is required"
            )
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
    inputs = load_s7_inputs(repo_root=repo_root, cap=cap, protocol=S7_PROTOCOL)
    panels = load_region_panels(paths["config"])

    split_manifest = None
    if all_seed_preflight or split_method == "v2":
        label_rows = build_s7_v2_label_rows_by_seed(inputs, seeds=S7_V2_DECLARED_SEEDS)
        planted_unique = {
            int(seed): collect_s7_v2_donor_labels(donors, labels)
            for seed, (donors, labels) in label_rows.items()
        }
        try:
            split_manifest = run_s7_v2_all_seed_nofit_preflight(
                label_rows_by_seed=label_rows,
                split_seed=int(S7_PROTOCOL.split_seed),
                planted_labels_by_seed=planted_unique,
                manifest_path=paths["durable_root"] / "split_manifest_v2.json",
            )
        except S7V2PreflightError:
            # Do not freeze ledger or prepare fits after INVALID_PREFLIGHT.
            raise

    provenance = build_provenance(
        repo_root,
        protocol_version=protocol_version,
        split_manifest_sha256=(
            None
            if split_manifest is None
            else split_manifest.get("split_manifest_sha256")
        ),
    )

    folds = prepare_s7_folds(
        inputs,
        panels,
        generator_seed=1001,
        protocol=S7_PROTOCOL,
        split_method=split_method,
    )

    preflight = {
        "protocol_id": provenance.protocol_id,
        "protocol_version": protocol_version,
        "paths": {key: str(value) for key, value in paths.items()},
        "path_audit": path_audit,
        "param_match": param_match,
        "resources": resources,
        "donor_inventory": folds["donor_inventory"],
        "fake_label_tag": folds["fake_label_tag"],
        "split_log": folds["split_log"],
        "provenance": provenance.to_dict(),
        "cap": int(cap),
        "n_folds": len(folds["folds_by_index"]),
        "screen_generator_seed": int(folds["generator_seed"]),
        "split_method": split_method,
        "all_seed_preflight": bool(all_seed_preflight or split_method == "v2"),
        "split_manifest_ok": None if split_manifest is None else bool(split_manifest.get("ok")),
        "split_manifest_sha256": None
        if split_manifest is None
        else split_manifest.get("split_manifest_sha256"),
        "n_declared_seeds": None if split_manifest is None else split_manifest.get("n_seeds"),
        "n_triplets": None if split_manifest is None else split_manifest.get("n_triplets"),
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
            "protocol_id": provenance.protocol_id,
            "protocol_version": protocol_version,
            "durable_root": str(paths["durable_root"]),
            "ledger_root": str(paths["ledger_root"]),
            "checkpoint_dir": str(paths["checkpoint_dir"]),
            "result_dir": str(paths["result_dir"]),
            "old_run_read_only": str(paths["old_run_read_only"]),
            "preflight": str(paths["durable_root"] / "preflight.json"),
            "split_manifest_v2": str(paths["durable_root"] / "split_manifest_v2.json")
            if split_manifest is not None
            else None,
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
        split_method=split_method,
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
        "split_manifest": split_manifest,
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
        "--split-v2",
        action="store_true",
        help="Use S7-v2 donor-quota splitter and all-seed no-fit preflight",
    )
    parser.add_argument(
        "--all-seed-preflight",
        action="store_true",
        help="Validate all 11 declared seeds before ledger freeze (implies no fits yet)",
    )
    parser.add_argument(
        "--skip-disk-check",
        action="store_true",
        help="Skip free-disk gate (tests only; not for result fits)",
    )
    parser.add_argument("--torch-threads", type=int, default=2)
    args = parser.parse_args(argv)

    _configure_threads(args.torch_threads)
    split_method = "v2" if args.split_v2 else "v1"
    if args.split_v2 and args.skip_disk_check:
        print(
            json.dumps(
                {
                    "action": "invalid_preflight",
                    "error": "S7-v2 refuses --skip-disk-check for live runs",
                },
                indent=2,
            )
        )
        return 3
    try:
        bundle = run_preflight(
            repo_root=args.repo_root.resolve(),
            cap=args.cap,
            check_disk=not args.skip_disk_check,
            split_method=split_method,
            all_seed_preflight=bool(args.all_seed_preflight or args.split_v2),
        )
    except S7V2PreflightError as exc:
        print(json.dumps({"action": "invalid_preflight", "error": str(exc)}, indent=2))
        return 3
    except ValueError as exc:
        if args.split_v2:
            print(json.dumps({"action": "invalid_preflight", "error": str(exc)}, indent=2))
            return 3
        raise
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
