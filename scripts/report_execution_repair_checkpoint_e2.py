#!/usr/bin/env python3
"""E2 checkpoint persistence report for execution repair (2026-10-02).

Runs one bounded toy neural fit that saves initial/final state, epoch history
and selection identity, verifies reload probability identity and interrupted-
write recovery, and preserves scientific NOT_AUTHORIZED / B_NULL labels.
Not a research pilot.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.execution_repair_checkpoint import (  # noqa: E402
    CheckpointPersistenceError,
    atomic_save_checkpoint,
    checkpoint_path_for_fit_id,
    fit_neural_with_checkpoint,
    load_checkpoint,
    recover_interrupted_tmp,
    reload_probabilities_from_checkpoint,
)
from p22.eval.masked_atac_adapter import build_toy_mixed_label_fold  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.s7_ledger import sha256_file  # noqa: E402

DEFAULT_OUT_JSON = ROOT / "tasks" / "checkpoint_persistence_e2.json"
DEFAULT_OUT_MD = ROOT / "tasks" / "CHECKPOINT_PERSISTENCE_E2.md"


def build_checkpoint_report(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    toy = build_toy_mixed_label_fold()
    proto = MultiomeProtocol(
        max_epochs=3,
        patience=2,
        batch_size=4,
        n_repeats=1,
        feature_budget=8,
        model_seed=7,
    )
    checks: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="e2_ckpt_") as tmp:
        ckpt_dir = Path(tmp) / "checkpoints"
        fitted = fit_neural_with_checkpoint(
            arm="token_concat",
            views=toy["views"],
            labels=toy["labels"],
            donors=toy["donors"],
            train_idx=toy["train_idx"],
            val_idx=toy["val_idx"],
            test_idx=toy["test_idx"],
            fit_id="toy|token_concat|fold0",
            checkpoint_dir=ckpt_dir,
            protocol=proto,
            stage="toy",
            fold=0,
        )
        path = Path(fitted["checkpoint_path"])
        loaded = load_checkpoint(path)
        reloaded = reload_probabilities_from_checkpoint(
            loaded, toy["views"], toy["test_idx"]
        )
        reload_ok = bool(
            np.allclose(reloaded, fitted["probabilities"], rtol=0.0, atol=1e-6)
        )
        overwrite_refused = False
        try:
            atomic_save_checkpoint(path, {"schema": "should_not_write"})
        except CheckpointPersistenceError:
            overwrite_refused = True
        # Interrupted write: leave only .tmp and recover without promotion.
        interrupted = checkpoint_path_for_fit_id(ckpt_dir, "toy|interrupted|fold0")
        tmp_path = interrupted.with_name(interrupted.name + ".tmp")
        torch.save({"incomplete": True}, tmp_path)
        interrupted_load_refused = False
        try:
            load_checkpoint(interrupted)
        except CheckpointPersistenceError:
            interrupted_load_refused = True
        recovered = recover_interrupted_tmp(interrupted)
        checks = {
            "checkpoint_saved": path.is_file(),
            "checkpoint_bytes": int(path.stat().st_size),
            "checkpoint_sha256_file": sha256_file(path),
            "has_initial_state": "initial_state" in loaded,
            "has_final_state": "final_state" in loaded,
            "epoch_history_len": len(loaded["epoch_history"]),
            "selection_identity_present": bool(loaded.get("selection_identity")),
            "reload_probability_identity": reload_ok,
            "overwrite_refused": overwrite_refused,
            "interrupted_tmp_load_refused": interrupted_load_refused,
            "interrupted_tmp_discarded": recovered.get("status")
            == "interrupted_tmp_discarded",
            "interrupted_not_promoted": recovered.get("promoted") is False,
            "initial_state_sha256": fitted["initial_state_sha256"],
            "checkpoint_sha256": fitted["checkpoint_sha256"],
            "pilot_checkpoints_dir_empty_historical": not any(
                (
                    workspace
                    / "reports/generated/nn_masked_atac_pilot_20261001/checkpoints"
                ).glob("*.pt")
            ),
        }
    required = (
        "checkpoint_saved",
        "has_initial_state",
        "has_final_state",
        "reload_probability_identity",
        "overwrite_refused",
        "interrupted_tmp_load_refused",
        "interrupted_tmp_discarded",
        "interrupted_not_promoted",
    )
    all_pass = all(bool(checks[k]) for k in required) and int(
        checks["epoch_history_len"]
    ) >= 1
    return {
        "disposition": (
            "CHECKPOINT_PERSISTENCE_PASS" if all_pass else "CHECKPOINT_PERSISTENCE_FAIL"
        ),
        "stage": "E2",
        "date": "2026-10-02",
        "research_fits": 0,
        "bounded_toy_only": True,
        "checks": checks,
        "required_checks_pass": all_pass,
        "scientific_status_unchanged": {
            "masked_atac_m9": "NOT_AUTHORIZED",
            "primary": "B_NULL",
            "prior_S10_S9_S7": "INVALID",
            "prior_S8": "NO FIT",
        },
        "artifacts": {
            "helper": "src/p22/eval/execution_repair_checkpoint.py",
            "pilot_wiring": "src/p22/eval/masked_atac_pilot.py",
            "focused_tests": "tests/test_execution_repair_checkpoint_e2.py",
        },
        "notes": [
            "Historical M9 checkpoints/ directory remains empty (pre-repair gap).",
            "Prediction sidecars already carried epoch history metadata; E2 adds "
            "reloadable initial/final state artifacts.",
            "M8 locked adapter/execute digests unchanged; helpers live outside lock.",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        "# E2 checkpoint persistence — 2026-10-02",
        "",
        f"**Disposition:** `{report['disposition']}`",
        "",
        "Bounded toy neural job saves initial/final state, per-epoch history and",
        "selection identity before completion. Reload reproduces saved probabilities.",
        "Resume refuses overwrite; interrupted `.pt.tmp` is discarded, never promoted.",
        "Not a research pilot.",
        "",
        "## Checks",
        "",
        f"- Checkpoint saved: `{checks['checkpoint_saved']}`",
        f"- Checkpoint bytes: `{checks['checkpoint_bytes']}`",
        f"- Epoch history length: `{checks['epoch_history_len']}`",
        f"- Selection identity present: `{checks['selection_identity_present']}`",
        f"- Reload probability identity: `{checks['reload_probability_identity']}`",
        f"- Overwrite refused: `{checks['overwrite_refused']}`",
        f"- Interrupted tmp load refused: `{checks['interrupted_tmp_load_refused']}`",
        f"- Interrupted tmp discarded (not promoted): "
        f"`{checks['interrupted_tmp_discarded']}`",
        f"- Historical pilot checkpoints empty: "
        f"`{checks['pilot_checkpoints_dir_empty_historical']}`",
        f"- Research fits this stage: `{report['research_fits']}`",
        "",
        "## Scientific labels preserved",
        "",
        f"- `masked_atac_m9`: **{report['scientific_status_unchanged']['masked_atac_m9']}**",
        f"- `primary`: **{report['scientific_status_unchanged']['primary']}**",
        f"- `prior_S10_S9_S7`: **{report['scientific_status_unchanged']['prior_S10_S9_S7']}**",
        f"- `prior_S8`: **{report['scientific_status_unchanged']['prior_S8']}**",
        "",
        "## Evidence",
        "",
        f"- `{report['artifacts']['helper']}`",
        f"- `{report['artifacts']['pilot_wiring']}` → `fit_one_job(..., checkpoint_dir=...)`",
        f"- Focused tests: `{report['artifacts']['focused_tests']}`",
        "",
        "No research fits. Next: E3 full-executor authorization binding.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args(argv)
    report = build_checkpoint_report(args.workspace)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(report["disposition"])
    return 0 if report["disposition"] == "CHECKPOINT_PERSISTENCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
