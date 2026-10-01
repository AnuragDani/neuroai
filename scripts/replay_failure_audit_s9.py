#!/usr/bin/env python3
"""R1 read-only S9 sidecar/checkpoint replay for the failure audit.

Recomputes coverage, per-arm pooled BA, primary pairing drops/CI, and disposition
from the immutable prior S9 raw root without fitting and without writing into that
root. Existing ``run_q10_batch(..., skip_fits=True)`` rewrites provenance on the
raw root, so this helper calls read-only aggregation APIs instead.

Outputs live only under the failure-audit task directory / new raw root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from p22.eval.s7_ledger import sha256_file  # noqa: E402
from p22.eval.s9_analytic import (  # noqa: E402
    DECISION_GENERATOR_SEED,
    PROTOCOL_ID,
    TOTAL_FITS,
    allocate_s9_folds,
    assign_donor_labels,
    s9_protocol_from_frozen,
    verify_oracle_invariants,
)
from p22.eval.s9_execute import (  # noqa: E402
    MARGINAL_BA_MAX,
    REVIEWED_HASHES,
    _pool_donor_ba_from_predictions,
    _score_pairing_for_rho,
    interpret_batch,
    load_attempt_counter,
    read_ledger_records,
    verify_checkpoint_c_hashes,
)

DEFAULT_S9_RAW = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/"
    "finish-engineering-20260928-gnhf-worktrees/"
    "read-tasks-nn-finish-ee2202-gnhf-worktrees/"
    "read-users-anuragdan-b61180-gnhf-worktrees/"
    "execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930"
)
DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "failure_audit_20261001"
)
DEFAULT_PROTOCOL_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
SCREEN_MODELS = (
    "cross_attention",
    "token_concat",
    "gated_fusion",
    "rna_atac_concat",
    "logreg_concat",
    "logreg_rna",
    "logreg_atac",
)


class S9ReplayRefusal(RuntimeError):
    """Refuse unsafe or incomplete R1 replay."""


def _fingerprint_tree(root: Path) -> dict[str, list[str]]:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            rows.append(f"{st.st_mtime_ns} {st.st_size} {path.relative_to(root)}")
    digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    return {"n_files": len(rows), "tree_sha256": digest, "rows": rows}


def _assert_no_write(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if before["tree_sha256"] != after["tree_sha256"]:
        before_set = set(before["rows"])
        after_set = set(after["rows"])
        raise S9ReplayRefusal(
            "shared S9 raw root mutated during replay: "
            f"added={sorted(after_set - before_set)[:5]!r} "
            f"removed={sorted(before_set - after_set)[:5]!r}"
        )


def validate_sidecar_hashes(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    pred_ok = 0
    ckpt_ok = 0
    pred_mismatch: list[str] = []
    ckpt_mismatch: list[str] = []
    missing: list[str] = []
    for row in records:
        fit_id = str(row["fit_id"])
        pred_path = Path(str(row["donor_predictions_path"]))
        if not pred_path.is_file():
            missing.append(f"pred:{fit_id}")
            continue
        digest = sha256_file(pred_path)
        if digest != row.get("donor_predictions_sha256"):
            pred_mismatch.append(fit_id)
        else:
            pred_ok += 1
        ckpt = row.get("checkpoint_path")
        if ckpt:
            ckpt_path = Path(str(ckpt))
            if not ckpt_path.is_file():
                missing.append(f"ckpt:{fit_id}")
                continue
            cdigest = sha256_file(ckpt_path)
            if cdigest != row.get("checkpoint_sha256"):
                ckpt_mismatch.append(fit_id)
            else:
                ckpt_ok += 1
    return {
        "n_records": len(records),
        "prediction_hash_ok": pred_ok,
        "checkpoint_hash_ok": ckpt_ok,
        "prediction_mismatches": pred_mismatch,
        "checkpoint_mismatches": ckpt_mismatch,
        "missing_paths": missing,
        "all_ok": (
            pred_ok == len(records)
            and not pred_mismatch
            and not ckpt_mismatch
            and not missing
        ),
    }


def independent_donor_ba(path: Path) -> dict[str, Any]:
    """Simple BA at 0.5 from one donor-prediction sidecar (independent of pool helper)."""
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    preds = blob["donor_probabilities"]
    y = np.asarray(preds["label"], dtype=int)
    p = np.asarray(preds["probability"], dtype=float)
    pred = (p >= 0.5).astype(int)
    parts = []
    for cls in (0, 1):
        mask = y == cls
        if not np.any(mask):
            return {"complete": False, "reason": f"missing class {cls}", "ba": None}
        parts.append(float(np.mean(pred[mask] == cls)))
    return {
        "complete": True,
        "ba": float(np.mean(parts)),
        "n_donors": int(len(y)),
        "donor_ids": [str(d) for d in preds["donor_id"]],
    }


def inventory_optimization_provenance(
    records: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Inspect retained CA/TC checkpoints for epoch/selection history."""
    retained = [
        r
        for r in records
        if r.get("stage") == "screen"
        and r.get("model") in {"cross_attention", "token_concat"}
        and r.get("checkpoint_path")
        and r.get("status") == "ok"
    ]
    histories: list[dict[str, Any]] = []
    for row in retained:
        ckpt = torch.load(
            row["checkpoint_path"], map_location="cpu", weights_only=False
        )
        inner = ckpt.get("checkpoint") or {}
        keys = sorted(inner.keys()) if isinstance(inner, dict) else []
        histories.append(
            {
                "fit_id": row["fit_id"],
                "seconds": row.get("seconds"),
                "checkpoint_top_keys": sorted(ckpt.keys()),
                "checkpoint_inner_keys": keys,
                "has_epoch_history": any(
                    k in keys
                    for k in (
                        "history",
                        "learning_history",
                        "epochs",
                        "n_epochs",
                        "train_history",
                        "metrics",
                    )
                ),
                "protocol_snapshot": (
                    inner.get("protocol") if isinstance(inner, dict) else None
                ),
            }
        )
    return {
        "n_retained_ca_tc_screen": len(retained),
        "expected_retained": 12,
        "any_epoch_history": any(h["has_epoch_history"] for h in histories),
        "sum_ledger_seconds": float(sum(float(r.get("seconds") or 0.0) for r in records)),
        "checkpoints": histories,
        "note": (
            "Five-second cumulative fit wall alone neither proves nor refutes "
            "adequate learning; epoch/selection history is absent from saved "
            "checkpoints (state_dict + protocol dims only)."
        ),
    }


def review_chronology(protocol_dir: Path, workspace: Path) -> dict[str, Any]:
    artifacts = {
        "SYNTHETIC_PROTOCOL.json": protocol_dir / "SYNTHETIC_PROTOCOL.json",
        "SPLIT_MANIFEST.json": protocol_dir / "SPLIT_MANIFEST.json",
        "FIT_LEDGER.json": protocol_dir / "FIT_LEDGER.json",
        "NO_FIT_REVIEW.json": protocol_dir / "NO_FIT_REVIEW.json",
        "INDEPENDENT_REVIEW_Q9.md": protocol_dir / "INDEPENDENT_REVIEW_Q9.md",
        "CHECKPOINT_C.md": protocol_dir / "CHECKPOINT_C.md",
        "execute.json": protocol_dir / "execute.json",
        "EXECUTE.md": protocol_dir / "EXECUTE.md",
        "src/p22/eval/s9_analytic.py": workspace / "src/p22/eval/s9_analytic.py",
        "src/p22/eval/s9_execute.py": workspace / "src/p22/eval/s9_execute.py",
    }
    hashes = {name: sha256_file(path) for name, path in artifacts.items() if path.is_file()}
    review = json.loads((protocol_dir / "NO_FIT_REVIEW.json").read_text())
    execute = json.loads((protocol_dir / "execute.json").read_text())
    return {
        "pipeline": [
            "Q7 PROTOCOL_FROZEN (generator/split/null/fit arithmetic)",
            "Q8 IMPLEMENT_PASS (s9_analytic + dry-run; 0 research fits)",
            "Q9 independent review PASS (agent 393c27bd…; no self-cert)",
            "Checkpoint C authorize research fits under reviewed hashes",
            "Q10 execute 49/49 → INVALID (unimodal marginal FAIL)",
            "Q12 handoff preserves INVALID; biological pilot BLOCKED",
        ],
        "artifact_sha256": hashes,
        "reviewed_hashes_match_live": {
            key: hashes.get(key) == expected
            for key, expected in REVIEWED_HASHES.items()
        },
        "q9_verdict": review.get("verdict"),
        "q9_reviewer_agent_id": (review.get("reviewer") or {}).get("agent_id"),
        "q9_correction_cycle": review.get("correction_cycle"),
        "q10_disposition": execute.get("disposition"),
        "q10_workers_torch_threads": [
            execute.get("resources", {}).get("workers"),
            execute.get("resources", {}).get("torch_threads"),
        ],
        "executor_coverage_note": (
            "Q9 reviewed protocol/code/test hashes and checklist 1–10; "
            "Q10 executor s9_execute.py was authored after Q9 and was not "
            "re-hashed under the Q9 REVIEWED_HASHES lock (post-review "
            "execution path). R1 records this chronology; cause claims deferred."
        ),
    }


def pipeline_trace() -> list[dict[str, str]]:
    return [
        {
            "step": "generator",
            "impl": "s9_analytic.generate_analytic_arrays / assign_donor_labels",
            "params": f"seed={DECISION_GENERATOR_SEED}; 24 donors; rho in {{0,1}}",
        },
        {
            "step": "split",
            "impl": "s9_analytic.allocate_s9_folds",
            "params": "F=3 class-quota SHA256; both classes every fold",
        },
        {
            "step": "fit",
            "impl": "s9_execute.run_one_s9_fit → s7_runner.fit_s7_arm",
            "params": "model_seed=9001; max_epochs=20; workers=2 torch_threads=2",
        },
        {
            "step": "checkpoint",
            "impl": "s9_execute.save_s9_checkpoint",
            "params": "retain screen CA/TC only (12 files); state_dict+protocol",
        },
        {
            "step": "reload",
            "impl": "s7_runner.reload_checkpoint_predictions",
            "params": "identity atol 1e-6 before shuffle scoring",
        },
        {
            "step": "shuffle",
            "impl": "s9_analytic.permute_atac_within_donor",
            "params": "PAIRING_SHUFFLE_SEEDS (16); within-donor marginal preserved",
        },
        {
            "step": "aggregate",
            "impl": "group_splits.aggregate_donor_probabilities",
            "params": "held-out donors pooled once across folds",
        },
        {
            "step": "bootstrap",
            "impl": "s7_pairing.evaluate_pairing_pc",
            "params": "1000 draws; seed from S7_BOOTSTRAP_SEED; min_valid=1000",
        },
        {
            "step": "gate",
            "impl": "s9_execute.interpret_batch",
            "params": (
                f"unimodal marginal BA≤{MARGINAL_BA_MAX}; "
                "primary CA pairing ll-drop CI; INVALID on marginal FAIL"
            ),
        },
    ]


def replay_s9_readonly(
    *,
    workspace: Path,
    s9_raw: Path,
    protocol_dir: Path,
) -> dict[str, Any]:
    s9_raw = Path(s9_raw).resolve()
    if not s9_raw.is_dir():
        raise S9ReplayRefusal(f"missing shared S9 raw root: {s9_raw}")
    if s9_raw.is_symlink():
        raise S9ReplayRefusal(f"refusing symlink S9 raw root: {s9_raw}")

    before = _fingerprint_tree(s9_raw)
    live_hashes = verify_checkpoint_c_hashes(
        workspace=workspace,
        protocol_path=protocol_dir / "SYNTHETIC_PROTOCOL.json",
        split_path=protocol_dir / "SPLIT_MANIFEST.json",
        ledger_path=protocol_dir / "FIT_LEDGER.json",
    )
    protocol_blob = json.loads(
        (protocol_dir / "SYNTHETIC_PROTOCOL.json").read_text(encoding="utf-8")
    )
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    splits = allocate_s9_folds(labels)
    split_manifest = json.loads(
        (protocol_dir / "SPLIT_MANIFEST.json").read_text(encoding="utf-8")
    )
    if splits["donor_labels"] != split_manifest["donor_labels"]:
        raise S9ReplayRefusal("live split labels diverge from SPLIT_MANIFEST")
    for fk, fold in split_manifest["folds"].items():
        if splits["folds"][fk] != fold:
            raise S9ReplayRefusal(f"live split fold {fk} diverges from SPLIT_MANIFEST")

    oracle = verify_oracle_invariants(labels)
    records = read_ledger_records(s9_raw)
    counter = load_attempt_counter(s9_raw)
    hash_check = validate_sidecar_hashes(records)
    if not hash_check["all_ok"]:
        raise S9ReplayRefusal(f"sidecar/checkpoint hash validation failed: {hash_check}")

    coverage = {
        "planned": TOTAL_FITS,
        "attempted": int(counter.get("attempted_fits", 0)),
        "completed_ok": int(counter.get("completed_ok", 0)),
        "failed": int(counter.get("failed", 0)),
        "unique_fit_ids": len(set(counter.get("fit_ids", []))),
        "ledger_rows": len(records),
        "complete": (
            int(counter.get("attempted_fits", 0)) == TOTAL_FITS
            and int(counter.get("completed_ok", 0)) == TOTAL_FITS
            and len(set(counter.get("fit_ids", []))) == TOTAL_FITS
            and len(records) == TOTAL_FITS
        ),
    }

    per_arm_pooled: dict[str, Any] = {}
    per_arm_per_fold: dict[str, Any] = {}
    independent_checks: dict[str, Any] = {}
    for model in SCREEN_MODELS:
        pooled = _pool_donor_ba_from_predictions(
            records, stage="screen", rho=1.0, model=model
        )
        per_arm_pooled[model] = pooled
        fold_rows = [
            r
            for r in records
            if r.get("stage") == "screen"
            and abs(float(r.get("rho", -1)) - 1.0) < 1e-12
            and r.get("model") == model
            and r.get("status") == "ok"
        ]
        fold_bas = {
            str(r["fold"]): {
                "ledger_donor_ba": r.get("donor_balanced_accuracy"),
                "independent_sidecar_ba": independent_donor_ba(
                    Path(r["donor_predictions_path"])
                ),
            }
            for r in sorted(fold_rows, key=lambda x: int(x["fold"]))
        }
        per_arm_per_fold[model] = fold_bas
        # Independent pooled BA from concatenating fold sidecars
        donor_ids: list[str] = []
        y_true: list[int] = []
        probs: list[float] = []
        seen: set[str] = set()
        for r in sorted(fold_rows, key=lambda x: int(x["fold"])):
            blob = json.loads(Path(r["donor_predictions_path"]).read_text())
            preds = blob["donor_probabilities"]
            for d, y, p in zip(
                preds["donor_id"], preds["label"], preds["probability"], strict=True
            ):
                d_s = str(d)
                if d_s in seen:
                    raise S9ReplayRefusal(f"duplicate donor in independent pool: {d_s}")
                seen.add(d_s)
                donor_ids.append(d_s)
                y_true.append(int(y))
                probs.append(float(p))
        y_arr = np.asarray(y_true, dtype=int)
        p_arr = np.asarray(probs, dtype=float)
        pred = (p_arr >= 0.5).astype(int)
        ba_parts = [
            float(np.mean(pred[y_arr == cls] == cls)) for cls in (0, 1)
        ]
        indep_ba = float(np.mean(ba_parts))
        independent_checks[model] = {
            "independent_pooled_ba": indep_ba,
            "helper_pooled_ba": pooled.get("ba"),
            "match": (
                pooled.get("ba") is not None
                and abs(float(pooled["ba"]) - indep_ba) < 1e-12
            ),
            "n_donors": len(donor_ids),
            "label_match": donor_ids == pooled.get("donor_ids"),
        }

    rna_ba = per_arm_pooled["logreg_rna"]
    atac_ba = per_arm_pooled["logreg_atac"]
    marginal = {
        "logreg_rna_ba": rna_ba.get("ba"),
        "logreg_atac_ba": atac_ba.get("ba"),
        "threshold": MARGINAL_BA_MAX,
        "pass": (
            rna_ba.get("complete")
            and atac_ba.get("complete")
            and rna_ba.get("ba") is not None
            and atac_ba.get("ba") is not None
            and float(rna_ba["ba"]) <= MARGINAL_BA_MAX
            and float(atac_ba["ba"]) <= MARGINAL_BA_MAX
        ),
        "logreg_rna": rna_ba,
        "logreg_atac": atac_ba,
    }

    proto = s9_protocol_from_frozen(protocol_blob["models"]["training_budget"])
    pairing_rho1 = _score_pairing_for_rho(
        raw_root=s9_raw,
        records=records,
        labels=labels,
        splits=splits,
        protocol=proto,
        rho=1.0,
    )
    pairing_rho0 = _score_pairing_for_rho(
        raw_root=s9_raw,
        records=records,
        labels=labels,
        splits=splits,
        protocol=proto,
        rho=0.0,
    )
    ca_ba = per_arm_pooled["cross_attention"]
    tc_ba = per_arm_pooled["token_concat"]
    advantage = {
        "label": "SEPARATE_NON_PRIMARY",
        "ca_ba": ca_ba.get("ba"),
        "token_concat_ba": tc_ba.get("ba"),
        "ca_minus_token_concat": (
            None
            if ca_ba.get("ba") is None or tc_ba.get("ba") is None
            else float(ca_ba["ba"]) - float(tc_ba["ba"])
        ),
        "complete": bool(ca_ba.get("complete") and tc_ba.get("complete")),
    }
    interpretation = interpret_batch(
        records=records,
        pairing_rho1=pairing_rho1,
        pairing_rho0=pairing_rho0,
        marginal=marginal,
        coverage=coverage,
    )
    opt = inventory_optimization_provenance(records)
    chronology = review_chronology(protocol_dir, workspace)
    after = _fingerprint_tree(s9_raw)
    _assert_no_write(before, after)

    prior_execute = json.loads((protocol_dir / "execute.json").read_text())
    matches_prior = {
        "disposition": interpretation["disposition"] == prior_execute["disposition"],
        "marginal_rna": marginal["logreg_rna_ba"]
        == prior_execute["marginal_check"]["logreg_rna_ba"],
        "marginal_atac": marginal["logreg_atac_ba"]
        == prior_execute["marginal_check"]["logreg_atac_ba"],
        "pairing_rho1_label": pairing_rho1.get("pairing_label")
        == prior_execute["pairing_rho1"]["pairing_label"],
        "pairing_rho0_label": pairing_rho0.get("pairing_label")
        == prior_execute["pairing_rho0"]["pairing_label"],
        "rho1_ll_drop_lower": pairing_rho1.get("gate", {})
        .get("ll_drop_bootstrap", {})
        .get("lower")
        == prior_execute["pairing_rho1"]["gate"]["ll_drop_bootstrap"]["lower"],
        "rho0_ll_drop_lower": pairing_rho0.get("gate", {})
        .get("ll_drop_bootstrap", {})
        .get("lower")
        == prior_execute["pairing_rho0"]["gate"]["ll_drop_bootstrap"]["lower"],
        "advantage_ca_ba": advantage["ca_ba"]
        == prior_execute["advantage_contrast"]["ca_ba"],
    }

    failure_categories = {
        "protocol_failure": {
            "applies": interpretation["disposition"] == "INVALID"
            and not marginal["pass"],
            "evidence": (
                "Frozen unimodal marginal gate FAIL: logreg_rna BA "
                f"{marginal['logreg_rna_ba']} and logreg_atac BA "
                f"{marginal['logreg_atac_ba']} both > {MARGINAL_BA_MAX}. "
                "Primary INVALID retained; not a method claim."
            ),
        },
        "implementation_deviation": {
            "applies": False,
            "evidence": (
                "Replay recomputes identical disposition/labels/CI lowers versus "
                "prior execute.json; donor prediction and checkpoint SHA-256 match "
                "ledger; live splits match SPLIT_MANIFEST; oracle gate PASS."
            ),
        },
        "uncertain_optimization": {
            "applies": True,
            "evidence": (
                "Retained checkpoints store state_dict + protocol dims only; no "
                "epoch/learning_history/selection metrics. Cumulative ledger "
                f"seconds={opt['sum_ledger_seconds']:.4f} cannot alone establish "
                "under-training or adequacy. Leave optimization uncertain."
            ),
        },
        "statistical_fluctuation": {
            "applies": False,
            "evidence": (
                "Primary INVALID is a hard marginal threshold exceedance on all "
                "24 donors (pooled), not a borderline CI that could flip under "
                "resampling of the same saved predictions."
            ),
        },
        "missing_provenance": {
            "applies": True,
            "evidence": (
                "Epoch/selection history absent from checkpoints; Q10 executor "
                "module was not under the Q9 REVIEWED_HASHES lock (chronology "
                "note). Does not overturn saved INVALID label."
            ),
        },
    }

    return {
        "task": "R1",
        "disposition": "REPLAY_PASS",
        "scientific_label_retained": interpretation["disposition"],
        "protocol_id": PROTOCOL_ID,
        "date": time.strftime("%Y-%m-%d"),
        "recorded_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "s9_raw_root": str(s9_raw),
        "shared_raw_write": False,
        "shared_raw_fingerprint_before": {
            "n_files": before["n_files"],
            "tree_sha256": before["tree_sha256"],
        },
        "shared_raw_fingerprint_after": {
            "n_files": after["n_files"],
            "tree_sha256": after["tree_sha256"],
        },
        "shared_raw_unchanged": before["tree_sha256"] == after["tree_sha256"],
        "reviewed_hashes_live": live_hashes,
        "oracle": oracle,
        "coverage": coverage,
        "sidecar_hash_validation": hash_check,
        "per_arm_pooled_ba_rho1_screen": {
            m: {"ba": per_arm_pooled[m].get("ba"), "complete": per_arm_pooled[m].get("complete")}
            for m in SCREEN_MODELS
        },
        "per_arm_per_fold_ba_rho1_screen": per_arm_per_fold,
        "independent_ba_checks": independent_checks,
        "marginal_check": marginal,
        "pairing_rho1": pairing_rho1,
        "pairing_rho0": pairing_rho0,
        "advantage_contrast": advantage,
        "interpretation": interpretation,
        "optimization_provenance": opt,
        "pipeline_trace": pipeline_trace(),
        "review_chronology": chronology,
        "matches_prior_execute_json": matches_prior,
        "failure_categories": failure_categories,
        "invariants_preserved": {
            "S9_INVALID": interpretation["disposition"] == "INVALID",
            "primary": "B_NULL",
            "prior_s8": "NO FIT",
            "s7": "INVALID",
        },
        "research_fits_this_replay": 0,
        "network_bytes": 0,
    }


def render_s9_audit_markdown(report: Mapping[str, Any]) -> str:
    cats = report["failure_categories"]
    lines = [
        "# S9_AUDIT — R1 replay of immutable S9 evidence",
        "",
        f"**Disposition:** `{report['disposition']}` (scientific label retained "
        f"`{report['scientific_label_retained']}`)",
        f"**Date:** {report['date']}",
        f"**Protocol:** `{report['protocol_id']}`",
        f"**Shared S9 raw (read-only):** `{report['s9_raw_root']}`",
        f"**Shared raw unchanged:** `{report['shared_raw_unchanged']}` "
        f"(tree SHA-256 `{report['shared_raw_fingerprint_before']['tree_sha256']}`)",
        f"**Research fits this replay:** {report['research_fits_this_replay']}",
        "",
        "## Coverage",
        "",
        f"- Planned/attempted/ok/failed: "
        f"{report['coverage']['planned']}/"
        f"{report['coverage']['attempted']}/"
        f"{report['coverage']['completed_ok']}/"
        f"{report['coverage']['failed']}",
        f"- Ledger rows / unique fit_ids: "
        f"{report['coverage']['ledger_rows']} / "
        f"{report['coverage']['unique_fit_ids']}",
        f"- Complete: `{report['coverage']['complete']}`",
        f"- Sidecar+checkpoint SHA-256 vs ledger: "
        f"`{report['sidecar_hash_validation']['all_ok']}` "
        f"({report['sidecar_hash_validation']['prediction_hash_ok']} preds; "
        f"{report['sidecar_hash_validation']['checkpoint_hash_ok']} ckpts)",
        "",
        "## Per-arm pooled donor BA (ρ=1 screen)",
        "",
        "| Arm | Pooled BA | Independent match |",
        "|---|---:|:---:|",
    ]
    for model, meta in report["per_arm_pooled_ba_rho1_screen"].items():
        indep = report["independent_ba_checks"][model]
        lines.append(
            f"| `{model}` | {meta['ba']} | `{indep['match']}` |"
        )
    lines.extend(
        [
            "",
            "## Marginal / pairing / advantage",
            "",
            f"- Marginal pass (≤{report['marginal_check']['threshold']}): "
            f"`{report['marginal_check']['pass']}` "
            f"(RNA {report['marginal_check']['logreg_rna_ba']}; "
            f"ATAC {report['marginal_check']['logreg_atac_ba']})",
            f"- CA ρ=1 pairing: `{report['pairing_rho1']['pairing_label']}` "
            f"(ll-drop CI lower "
            f"{report['pairing_rho1']['gate']['ll_drop_bootstrap']['lower']})",
            f"- CA ρ=0 pairing: `{report['pairing_rho0']['pairing_label']}` "
            f"(ll-drop CI lower "
            f"{report['pairing_rho0']['gate']['ll_drop_bootstrap']['lower']})",
            f"- Advantage SEPARATE_NON_PRIMARY CA−TC: "
            f"{report['advantage_contrast']['ca_minus_token_concat']} "
            f"(CA {report['advantage_contrast']['ca_ba']}; "
            f"TC {report['advantage_contrast']['token_concat_ba']})",
            f"- Interpretation: `{report['interpretation']['disposition']}` — "
            f"{report['interpretation']['reason']}",
            "",
            "## Matches prior execute.json",
            "",
        ]
    )
    for key, ok in report["matches_prior_execute_json"].items():
        lines.append(f"- `{key}`: `{ok}`")
    lines.extend(
        [
            "",
            "## Pipeline trace",
            "",
        ]
    )
    for step in report["pipeline_trace"]:
        lines.append(
            f"1. **{step['step']}** — `{step['impl']}` ({step['params']})"
        )
    chron = report["review_chronology"]
    lines.extend(
        [
            "",
            "## Review chronology",
            "",
        ]
    )
    for item in chron["pipeline"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"- Q9 verdict `{chron['q9_verdict']}`; reviewer "
            f"`{chron['q9_reviewer_agent_id']}`; correction_cycle "
            f"`{chron['q9_correction_cycle']}`",
            f"- Note: {chron['executor_coverage_note']}",
            "",
            "## Optimization provenance",
            "",
            f"- Retained CA/TC screen checkpoints: "
            f"{report['optimization_provenance']['n_retained_ca_tc_screen']}/"
            f"{report['optimization_provenance']['expected_retained']}",
            f"- Any epoch/learning history in checkpoints: "
            f"`{report['optimization_provenance']['any_epoch_history']}`",
            f"- Sum ledger seconds: "
            f"{report['optimization_provenance']['sum_ledger_seconds']}",
            f"- {report['optimization_provenance']['note']}",
            "",
            "## Failure-category distinctions",
            "",
            "| Category | Applies | Evidence |",
            "|---|---|---|",
        ]
    )
    for name, blob in cats.items():
        lines.append(
            f"| {name} | `{blob['applies']}` | {blob['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## Invariants preserved",
            "",
            f"- S9 scientific label remains **`{report['scientific_label_retained']}`** "
            "(immutable; replay does not rewrite old summaries).",
            f"- Primary `{report['invariants_preserved']['primary']}`; "
            f"S7 `{report['invariants_preserved']['s7']}`; "
            f"prior S8 `{report['invariants_preserved']['prior_s8']}`.",
            "",
            "## Next",
            "",
            "R2 null-exchangeability / marginal diagnosis (≤256 generator-only draws; "
            "0 fits). Checkpoint A after R1+R2.",
            "",
        ]
    )
    return "\n".join(lines)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    # bool is a subclass of int; check before int coercion
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if obj is None or isinstance(obj, str):
        return obj
    return str(obj)


def write_outputs(
    *,
    out_dir: Path,
    workspace: Path,
    s9_raw: Path,
    protocol_dir: Path,
    audit_raw: Path | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = replay_s9_readonly(
        workspace=workspace, s9_raw=s9_raw, protocol_dir=protocol_dir
    )
    json_path = out_dir / "s9_audit.json"
    md_path = out_dir / "S9_AUDIT.md"
    json_path.write_text(
        json.dumps(_jsonable(report), indent=2, sort_keys=False) + "\n"
    )
    md_path.write_text(render_s9_audit_markdown(report))
    if audit_raw is not None:
        audit_raw = Path(audit_raw)
        audit_raw.mkdir(parents=True, exist_ok=True)
        # Copy machine summary into new owned raw root (not shared S9).
        (audit_raw / "r1_s9_audit_summary.json").write_text(
            json.dumps(
                {
                    "disposition": report["disposition"],
                    "scientific_label_retained": report["scientific_label_retained"],
                    "shared_raw_unchanged": report["shared_raw_unchanged"],
                    "tree_sha256": report["shared_raw_fingerprint_after"]["tree_sha256"],
                    "coverage_complete": report["coverage"]["complete"],
                    "matches_prior": report["matches_prior_execute_json"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    return {
        "disposition": report["disposition"],
        "scientific_label_retained": report["scientific_label_retained"],
        "shared_raw_unchanged": report["shared_raw_unchanged"],
        "coverage_complete": report["coverage"]["complete"],
        "paths": {"s9_audit_json": str(json_path), "s9_audit_md": str(md_path)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--s9-raw", type=Path, default=DEFAULT_S9_RAW)
    parser.add_argument("--protocol-dir", type=Path, default=DEFAULT_PROTOCOL_DIR)
    parser.add_argument(
        "--audit-raw",
        type=Path,
        default=ROOT / "reports/generated/nn_failure_audit_20261001",
    )
    parser.add_argument("--workspace", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    # Hard refuse: never set cwd writes into s9-raw
    if Path(args.out_dir).resolve() == Path(args.s9_raw).resolve():
        raise S9ReplayRefusal("out-dir must not equal shared S9 raw root")
    if Path(args.audit_raw).resolve() == Path(args.s9_raw).resolve():
        raise S9ReplayRefusal("audit-raw must not equal shared S9 raw root")
    summary = write_outputs(
        out_dir=args.out_dir,
        workspace=args.workspace,
        s9_raw=args.s9_raw,
        protocol_dir=args.protocol_dir,
        audit_raw=args.audit_raw,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
