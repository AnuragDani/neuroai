"""M10 saved-prediction replay (no fitting).

Independently recomputes donor-average cell log-loss and the frozen TC−CA
primary contrast from prediction sidecars. Preserves counters; does not
modify M8 locks; does not promote scientific PASS when the prospective
executor-review gate failed.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from p22.eval.masked_atac_execute import ALLOWED_RAW_ROOT, COUNTER_NAME
from p22.eval.masked_atac_metrics import donor_average_cell_log_loss
from p22.eval.masked_atac_protocol import (
    BOOTSTRAP_LEVEL,
    BOOTSTRAP_LIMITS,
    BOOTSTRAP_N,
    BOOTSTRAP_SEED,
    CLAIM_LEVEL,
    LEARNED_ARMS,
    PRACTICAL_MARGIN_JUSTIFICATION,
    PRACTICAL_MARGIN_LOGLOSS,
    PRIMARY_CONTRAST_NAME,
    PRIMARY_SIGN,
    PROTOCOL_ID,
    paired_donor_bootstrap_contrast,
    paired_donor_contrast_tc_minus_ca,
)
from p22.eval.s7_ledger import sha256_file

PRESERVED_LABELS = {
    "primary": "B_NULL",
    "S7": "INVALID",
    "S9": "INVALID",
    "S10": "INVALID",
    "S8": "NO FIT",
    "Q2": "ENDPOINT_UNRESOLVED",
}

MAIN_ARMS: tuple[str, ...] = LEARNED_ARMS
SMOKE_ARMS: tuple[str, ...] = LEARNED_ARMS
N_FOLDS = 5
RTOL = 1e-12
ATOL = 1e-12


class MaskedAtacM10ReplayError(RuntimeError):
    """Replay integrity failure."""


def _task_dir(workspace: Path) -> Path:
    return (
        Path(workspace)
        / "tasks/nn/professor_direction_investigation_20260929"
        / "masked_atac_pilot_20261001"
    )


def _raw_root(workspace: Path) -> Path:
    return Path(workspace) / ALLOWED_RAW_ROOT


def _sidecar_name(stage: str, arm: str, fold: int) -> str:
    return f"{stage}__{arm}__fold{fold}.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _approx_equal(a: float, b: float) -> bool:
    return bool(np.isclose(float(a), float(b), rtol=RTOL, atol=ATOL))


def measure_artifact_bytes(raw_root: Path) -> dict[str, Any]:
    """Filesystem ``du -sk``; counter artifacts_gib.used is not this measurement."""
    completed = subprocess.run(
        ["du", "-sk", str(raw_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    kib = int(completed.stdout.split()[0])
    return {
        "du_kib": kib,
        "du_gib": kib / (1024.0 * 1024.0),
        "note": (
            "live du -sk; counter artifacts_gib.used=0.0 is not filesystem measurement"
        ),
    }


def verify_pre_replay_pins(
    workspace: Path,
    *,
    pins_path: Path | None = None,
) -> dict[str, Any]:
    """Rematch M10_PRE_REPLAY_PINS against live sidecars/ledger/counter."""
    workspace = Path(workspace)
    task = _task_dir(workspace)
    pins_path = pins_path or (task / "M10_PRE_REPLAY_PINS.json")
    pins = _load_json(pins_path)
    raw = _raw_root(workspace)
    mismatches: list[str] = []

    for rel, expected in pins["ledger_pins"].items():
        got = sha256_file(workspace / rel)
        if got != expected:
            mismatches.append(f"{rel}: expected {expected} got {got}")

    pred_dir = raw / "predictions"
    sidecar_hashes = pins["prediction_sidecar_sha256"]
    if len(sidecar_hashes) != int(pins["n_prediction_sidecars"]):
        mismatches.append("pin n_prediction_sidecars mismatch")
    live_names = sorted(p.name for p in pred_dir.glob("*.json"))
    if live_names != sorted(sidecar_hashes):
        mismatches.append(
            f"sidecar inventory mismatch: live={live_names!r} pinned={sorted(sidecar_hashes)!r}"
        )
    for name, expected in sorted(sidecar_hashes.items()):
        got = sha256_file(pred_dir / name)
        if got != expected:
            mismatches.append(f"predictions/{name}: expected {expected} got {got}")

    for rel, expected in pins.get("post_m8_path_hashes", {}).items():
        got = sha256_file(workspace / rel)
        if got != expected:
            mismatches.append(f"{rel}: expected {expected} got {got}")

    return {
        "pins_path": str(pins_path),
        "pins_sha256": sha256_file(pins_path),
        "n_checked": (
            len(pins["ledger_pins"])
            + len(sidecar_hashes)
            + len(pins.get("post_m8_path_hashes", {}))
        ),
        "all_match": len(mismatches) == 0,
        "mismatches": mismatches,
    }


def _load_sidecar(path: Path) -> dict[str, Any]:
    blob = _load_json(path)
    if blob.get("status") != "ok":
        raise MaskedAtacM10ReplayError(f"{path.name}: status != ok")
    record = blob["record"]
    required = (
        "test_probabilities",
        "test_labels",
        "test_donors",
        "test_cell_ids",
        "test_donor_average_cell_log_loss",
        "target_label",
        "target_index",
        "cell_ids_sha256",
        "labels_sha256",
    )
    missing = [k for k in required if k not in record]
    if missing:
        raise MaskedAtacM10ReplayError(f"{path.name}: missing {missing}")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "fit_id": blob.get("fit_id"),
        "stage": blob["stage"],
        "arm": blob["arm"],
        "fold": int(blob["fold"]),
        "seconds": float(blob.get("seconds", 0.0)),
        "record": record,
    }


def _recompute_loss(record: Mapping[str, Any]) -> dict[str, Any]:
    donors = np.asarray(record["test_donors"], dtype=str)
    y = np.asarray(record["test_labels"], dtype=np.float64)
    p = np.asarray(record["test_probabilities"], dtype=np.float64)
    got = donor_average_cell_log_loss(donors, y, p)
    stored = float(record["test_donor_average_cell_log_loss"])
    match = _approx_equal(got["value"], stored)
    return {
        "recomputed": float(got["value"]),
        "stored": stored,
        "match": match,
        "n_donors": int(got["n_donors"]),
        "n_cells": int(donors.size),
        "per_donor_mean_cell_log_loss": got["per_donor_mean_cell_log_loss"],
    }


def _equality_pins(arms: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Require identical test cells/labels/donors/target across arms in a fold."""
    first = next(iter(arms.values()))["record"]
    cell_ids = list(first["test_cell_ids"])
    donors = list(first["test_donors"])
    labels = list(first["test_labels"])
    target_label = first["target_label"]
    target_index = int(first["target_index"])
    cell_sha = first["cell_ids_sha256"]
    label_sha = first["labels_sha256"]
    ok = True
    details: dict[str, bool] = {}
    for arm, payload in arms.items():
        rec = payload["record"]
        arm_ok = (
            list(rec["test_cell_ids"]) == cell_ids
            and list(rec["test_donors"]) == donors
            and list(rec["test_labels"]) == labels
            and rec["target_label"] == target_label
            and int(rec["target_index"]) == target_index
            and rec["cell_ids_sha256"] == cell_sha
            and rec["labels_sha256"] == label_sha
        )
        details[arm] = arm_ok
        ok = ok and arm_ok
    return {
        "arms_equal_cells_labels_donors_target": ok,
        "per_arm": details,
        "n_test_cells": len(cell_ids),
        "n_test_donors": len(sorted(set(donors))),
        "target_label": target_label,
        "target_index": target_index,
        "cell_ids_sha256": cell_sha,
        "labels_sha256": label_sha,
        "test_cell_ids": cell_ids,
        "test_donors": donors,
        "test_labels": labels,
    }


def replay_main_fold(
    workspace: Path,
    fold: int,
    *,
    constant_arm: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Independently replay all main learned arms for one outer fold."""
    pred_dir = _raw_root(workspace) / "predictions"
    arms: dict[str, dict[str, Any]] = {}
    loss_checks: dict[str, dict[str, Any]] = {}
    for arm in MAIN_ARMS:
        path = pred_dir / _sidecar_name("main", arm, fold)
        if not path.is_file():
            raise MaskedAtacM10ReplayError(f"missing sidecar {path.name}")
        loaded = _load_sidecar(path)
        arms[arm] = loaded
        loss_checks[arm] = _recompute_loss(loaded["record"])

    eq = _equality_pins(arms)
    if not eq["arms_equal_cells_labels_donors_target"]:
        raise MaskedAtacM10ReplayError(f"fold {fold}: arm equality failed")

    donors = np.asarray(eq["test_donors"], dtype=str)
    y = np.asarray(eq["test_labels"], dtype=np.float64)
    p_tc = np.asarray(arms["token_concat"]["record"]["test_probabilities"], dtype=np.float64)
    p_ca = np.asarray(
        arms["cross_attention"]["record"]["test_probabilities"], dtype=np.float64
    )
    contrast = paired_donor_contrast_tc_minus_ca(donors, y, p_tc, p_ca)
    boot = paired_donor_bootstrap_contrast(
        donors,
        y,
        p_tc,
        p_ca,
        n_replicates=BOOTSTRAP_N,
        seed=BOOTSTRAP_SEED,
        level=BOOTSTRAP_LEVEL,
    )

    donor_avg: dict[str, float] = {
        arm: float(loss_checks[arm]["recomputed"]) for arm in MAIN_ARMS
    }
    if constant_arm is not None:
        donor_avg["training_prevalence_constant"] = float(
            constant_arm["test_donor_average_cell_log_loss"]
        )

    all_loss_match = all(v["match"] for v in loss_checks.values())
    return {
        "fold": fold,
        "target_label": eq["target_label"],
        "target_index": eq["target_index"],
        "n_test_cells": eq["n_test_cells"],
        "n_test_donors": eq["n_test_donors"],
        "cell_ids_sha256": eq["cell_ids_sha256"],
        "labels_sha256": eq["labels_sha256"],
        "arms_equal_cells_labels_donors_target": eq[
            "arms_equal_cells_labels_donors_target"
        ],
        "stored_vs_recomputed_loss_match": all_loss_match,
        "donor_average_cell_log_loss": donor_avg,
        "loss_checks": {
            arm: {
                "recomputed": v["recomputed"],
                "stored": v["stored"],
                "match": v["match"],
                "sidecar_sha256": arms[arm]["sha256"],
            }
            for arm, v in loss_checks.items()
        },
        "primary_contrast_tc_minus_ca": {
            "estimate": contrast["estimate"],
            "n_donors": contrast["n_donors"],
            "per_donor_delta_tc_minus_ca": contrast["per_donor_delta_tc_minus_ca"],
        },
        "bootstrap_fold": {
            "estimate": boot["estimate"],
            "interval": boot["interval"],
            "n_valid": boot["n_valid"],
            "seed": boot["seed"],
            "level": boot["level"],
        },
    }


def replay_smoke(workspace: Path) -> dict[str, Any]:
    """Verify five smoke sidecars separately (coverage + recomputed loss)."""
    pred_dir = _raw_root(workspace) / "predictions"
    arms: dict[str, dict[str, Any]] = {}
    loss_checks: dict[str, dict[str, Any]] = {}
    for arm in SMOKE_ARMS:
        path = pred_dir / _sidecar_name("smoke", arm, 0)
        if not path.is_file():
            raise MaskedAtacM10ReplayError(f"missing smoke sidecar {path.name}")
        loaded = _load_sidecar(path)
        arms[arm] = loaded
        loss_checks[arm] = _recompute_loss(loaded["record"])
    eq = _equality_pins(arms)
    return {
        "n_smoke_ok": len(arms),
        "expected": 5,
        "fold": 0,
        "arms_equal_cells_labels_donors_target": eq[
            "arms_equal_cells_labels_donors_target"
        ],
        "stored_vs_recomputed_loss_match": all(v["match"] for v in loss_checks.values()),
        "donor_average_cell_log_loss": {
            arm: float(loss_checks[arm]["recomputed"]) for arm in SMOKE_ARMS
        },
        "sidecar_sha256": {arm: arms[arm]["sha256"] for arm in SMOKE_ARMS},
        "loss_checks": {
            arm: {
                "recomputed": v["recomputed"],
                "stored": v["stored"],
                "match": v["match"],
            }
            for arm, v in loss_checks.items()
        },
    }


def _pool_primary(per_fold: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Pool per-donor TC−CA deltas across folds (each donor held out once)."""
    pooled: dict[str, float] = {}
    for fold_key in sorted(per_fold, key=int):
        deltas = per_fold[fold_key]["primary_contrast_tc_minus_ca"][
            "per_donor_delta_tc_minus_ca"
        ]
        for donor, value in deltas.items():
            if donor in pooled:
                raise MaskedAtacM10ReplayError(
                    f"donor {donor} appears in multiple outer folds"
                )
            pooled[donor] = float(value)
    donors = sorted(pooled)
    estimate = float(np.mean([pooled[d] for d in donors]))
    # Bootstrap on pooled donor deltas with frozen seed (same as protocol helper
    # after per-donor deltas are formed).
    deltas_arr = np.asarray([pooled[d] for d in donors], dtype=np.float64)
    rng = np.random.default_rng(int(BOOTSTRAP_SEED))
    values: list[float] = []
    for _ in range(int(BOOTSTRAP_N)):
        drawn = rng.integers(0, len(deltas_arr), size=len(deltas_arr))
        values.append(float(np.mean(deltas_arr[drawn])))
    tail = (1.0 - BOOTSTRAP_LEVEL) / 2.0
    lower, upper = np.percentile(values, [100.0 * tail, 100.0 * (1.0 - tail)])
    interval = [float(lower), float(upper)]
    exploratory = bool(
        estimate >= PRACTICAL_MARGIN_LOGLOSS and interval[0] > 0.0
    )
    return {
        "name": PRIMARY_CONTRAST_NAME,
        "sign": PRIMARY_SIGN,
        "pooled_estimate": estimate,
        "n_donors_pooled": len(donors),
        "per_donor_delta_tc_minus_ca": {d: pooled[d] for d in donors},
        "practical_margin": PRACTICAL_MARGIN_LOGLOSS,
        "practical_margin_justification": PRACTICAL_MARGIN_JUSTIFICATION,
        "exploratory_advantage_observed": exploratory,
        "exploratory_advantage_rule": (
            "exploratory_only: estimate >= practical_margin AND bootstrap "
            "interval[0] > 0; not confirmatory; not power; not biological state"
        ),
        "bootstrap": {
            "estimate": estimate,
            "interval": interval,
            "level": BOOTSTRAP_LEVEL,
            "n_replicates": BOOTSTRAP_N,
            "n_valid": BOOTSTRAP_N,
            "seed": BOOTSTRAP_SEED,
            "limits": BOOTSTRAP_LIMITS,
            "single_class_draws_dropped": False,
        },
        "per_fold_estimates": {
            k: float(v["primary_contrast_tc_minus_ca"]["estimate"])
            for k, v in per_fold.items()
        },
    }


def _compare_to_execute(
    replay_primary: Mapping[str, Any],
    execute_path: Path,
) -> dict[str, Any]:
    if not execute_path.is_file():
        return {"execute_present": False, "primary_match": False}
    execute = _load_json(execute_path)
    ep = execute["primary_contrast"]
    checks = {
        "pooled_estimate": _approx_equal(
            replay_primary["pooled_estimate"], ep["pooled_estimate"]
        ),
        "n_donors_pooled": replay_primary["n_donors_pooled"] == ep["n_donors_pooled"],
        "bootstrap_interval_lo": _approx_equal(
            replay_primary["bootstrap"]["interval"][0], ep["bootstrap"]["interval"][0]
        ),
        "bootstrap_interval_hi": _approx_equal(
            replay_primary["bootstrap"]["interval"][1], ep["bootstrap"]["interval"][1]
        ),
        "exploratory_advantage_observed": (
            replay_primary["exploratory_advantage_observed"]
            == ep["exploratory_advantage_observed"]
        ),
        "per_donor_deltas": all(
            _approx_equal(
                replay_primary["per_donor_delta_tc_minus_ca"][d],
                ep["per_donor_delta_tc_minus_ca"][d],
            )
            for d in replay_primary["per_donor_delta_tc_minus_ca"]
        ),
    }
    return {
        "execute_present": True,
        "execute_sha256": sha256_file(execute_path),
        "checks": checks,
        "primary_match": all(checks.values()),
    }


def load_coverage_gate(workspace: Path) -> dict[str, Any]:
    path = _task_dir(workspace) / "M10_COVERAGE_REVIEW.json"
    blob = _load_json(path)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "prospective_executor_review_gate": blob["prospective_executor_review_gate"],
        "retrospective_path_inspection": blob["retrospective_path_inspection"],
        "scientific_acceptance_of_M9": blob["scientific_acceptance_of_M9"],
        "reviewer_agent_id": blob["reviewer_agent_id"],
        "self_certification": blob["self_certification"],
        "review_duration_minutes": blob["review_duration_minutes"],
    }


def run_m10_replay(workspace: Path) -> dict[str, Any]:
    """Full M10 no-fit replay + pin/hash/coverage report (compact; no per-cell dump)."""
    workspace = Path(workspace)
    raw = _raw_root(workspace)
    task = _task_dir(workspace)
    counter_path = raw / COUNTER_NAME
    counter_sha_before = sha256_file(counter_path)
    counter_before = _load_json(counter_path)

    pin_check = verify_pre_replay_pins(workspace)
    if not pin_check["all_match"]:
        raise MaskedAtacM10ReplayError(
            f"pre-replay pin mismatch: {pin_check['mismatches']}"
        )

    constant_path = raw / "constant_arm_descriptive.json"
    constants = _load_json(constant_path) if constant_path.is_file() else {}

    per_fold: dict[str, dict[str, Any]] = {}
    for fold in range(N_FOLDS):
        const = constants.get(str(fold))
        per_fold[str(fold)] = replay_main_fold(
            workspace, fold, constant_arm=const
        )

    smoke = replay_smoke(workspace)
    primary = _pool_primary(per_fold)
    execute_cmp = _compare_to_execute(primary, task / "EXECUTE.json")
    coverage = load_coverage_gate(workspace)
    artifacts = measure_artifact_bytes(raw)

    counter_sha_after = sha256_file(counter_path)
    counter_after = _load_json(counter_path)
    counters_preserved = (
        counter_sha_before == counter_sha_after and counter_before == counter_after
    )
    if not counters_preserved:
        raise MaskedAtacM10ReplayError("attempt_counter mutated during replay")

    main_ok = all(
        fold["arms_equal_cells_labels_donors_target"]
        and fold["stored_vs_recomputed_loss_match"]
        for fold in per_fold.values()
    )
    smoke_ok = (
        smoke["n_smoke_ok"] == 5
        and smoke["arms_equal_cells_labels_donors_target"]
        and smoke["stored_vs_recomputed_loss_match"]
    )
    diagnostic_replay_pass = bool(
        pin_check["all_match"]
        and main_ok
        and smoke_ok
        and counters_preserved
        and execute_cmp.get("primary_match", False)
    )

    # Compact per-fold: drop per-donor lists from top-level report size control
    # but keep them inside primary pool (30 donors) and fold contrast estimates.
    compact_folds: dict[str, Any] = {}
    for key, fold in per_fold.items():
        compact_folds[key] = {
            "fold": fold["fold"],
            "target_label": fold["target_label"],
            "target_index": fold["target_index"],
            "n_test_cells": fold["n_test_cells"],
            "n_test_donors": fold["n_test_donors"],
            "cell_ids_sha256": fold["cell_ids_sha256"],
            "labels_sha256": fold["labels_sha256"],
            "arms_equal_cells_labels_donors_target": fold[
                "arms_equal_cells_labels_donors_target"
            ],
            "stored_vs_recomputed_loss_match": fold["stored_vs_recomputed_loss_match"],
            "donor_average_cell_log_loss": fold["donor_average_cell_log_loss"],
            "primary_contrast_tc_minus_ca": {
                "estimate": fold["primary_contrast_tc_minus_ca"]["estimate"],
                "n_donors": fold["primary_contrast_tc_minus_ca"]["n_donors"],
            },
            "bootstrap_fold": fold["bootstrap_fold"],
            "loss_checks": fold["loss_checks"],
        }

    secondary_means: dict[str, float] = {}
    arm_keys = list(MAIN_ARMS) + ["training_prevalence_constant"]
    for arm in arm_keys:
        vals = []
        for fold in per_fold.values():
            if arm in fold["donor_average_cell_log_loss"]:
                vals.append(fold["donor_average_cell_log_loss"][arm])
        if vals:
            secondary_means[arm] = float(np.mean(vals))

    disposition = "REPLAY_PASS_DIAGNOSTIC_ONLY"
    if not diagnostic_replay_pass:
        disposition = "REPLAY_FAIL"

    return {
        "task": "M10_REPLAY",
        "protocol_id": PROTOCOL_ID,
        "disposition": disposition,
        "claim_level": CLAIM_LEVEL,
        "preserved_labels": dict(PRESERVED_LABELS),
        "fits_run": 0,
        "counters_modified": False,
        "m8_locks_modified": False,
        "prospective_executor_review_gate": coverage[
            "prospective_executor_review_gate"
        ],
        "scientific_acceptance_of_M9": coverage["scientific_acceptance_of_M9"],
        "scientific_acceptance_note": (
            "Diagnostic numerical replay only. Prospective executor-review gate "
            "FAIL (unlocked masked_atac_pilot.py / run_masked_atac_m9.py) blocks "
            "scientific acceptance of M9; retrospective inspection cannot satisfy it."
        ),
        "coverage_review": coverage,
        "pre_replay_pins": pin_check,
        "post_replay_counter": {
            "sha256_before": counter_sha_before,
            "sha256_after": counter_sha_after,
            "preserved": counters_preserved,
            "total_attempts_used": counter_after["total_attempts"]["used"],
            "hard_cap": counter_after["total_attempts"]["hard_cap"],
            "smoke_fits_used": counter_after["smoke_fits"]["used"],
            "scientific_fits_used": counter_after["scientific_fits"]["used"],
            "failed": len(counter_after.get("failed_fit_ids", [])),
            "fitting_hours_used": counter_after["fitting_hours"]["used"],
            "artifacts_gib_used_counter_field": counter_after["artifacts_gib"]["used"],
            "workers": counter_after.get("workers", 1),
            "torch_threads": counter_after.get("torch_threads", 2),
        },
        "artifact_bytes": artifacts,
        "smoke": {
            "n_smoke_ok": smoke["n_smoke_ok"],
            "expected": smoke["expected"],
            "arms_equal_cells_labels_donors_target": smoke[
                "arms_equal_cells_labels_donors_target"
            ],
            "stored_vs_recomputed_loss_match": smoke[
                "stored_vs_recomputed_loss_match"
            ],
            "donor_average_cell_log_loss": smoke["donor_average_cell_log_loss"],
            "sidecar_sha256": smoke["sidecar_sha256"],
        },
        "main_coverage": {
            "n_folds": N_FOLDS,
            "n_learned_arms": len(MAIN_ARMS),
            "n_main_sidecars": N_FOLDS * len(MAIN_ARMS),
            "all_folds_equality_and_loss_match": main_ok,
        },
        "equality_across_arms": {
            "per_fold_cell_label_donor_identity": main_ok,
            "sampling_cell_ids_sha256": next(iter(per_fold.values()))[
                "cell_ids_sha256"
            ],
            "all_folds_share_sampling_hash": len(
                {f["cell_ids_sha256"] for f in per_fold.values()}
            )
            == 1,
        },
        "primary_contrast": primary,
        "secondary_descriptive": {
            "role": "model_sensitivity_not_causal_routing",
            "mean_across_folds_donor_average_cell_log_loss": secondary_means,
            "limitations": (
                "Arm-wise mean test cell log-loss is descriptive only. Does not "
                "establish causal modality routing, biological mechanism, or "
                "independent external validation. Diagnostic under prospective "
                "gate FAIL."
            ),
        },
        "per_fold": compact_folds,
        "execute_comparison": execute_cmp,
        "diagnostic_replay_pass": diagnostic_replay_pass,
        "raw_root": str(raw),
    }


def write_replay_reports(
    workspace: Path,
    *,
    report: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Write compact REPLAY.json + REPLAY.md under the task directory."""
    workspace = Path(workspace)
    task = _task_dir(workspace)
    report = dict(report or run_m10_replay(workspace))
    json_path = task / "REPLAY.json"
    md_path = task / "REPLAY.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    primary = report["primary_contrast"]
    boot = primary["bootstrap"]
    cov = report["coverage_review"]
    lines = [
        "# M10 — Saved-prediction replay (diagnostic only)",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Prospective executor-review gate:** `{report['prospective_executor_review_gate']}` "
        f"(reviewer `{cov['reviewer_agent_id']}`)",
        f"**Scientific acceptance of M9:** `{report['scientific_acceptance_of_M9']}`",
        f"**Fits run this step:** `{report['fits_run']}` (counters preserved: "
        f"`{report['post_replay_counter']['preserved']}`)",
        "",
        "## Scope",
        "",
        "Independent recomputation of donor-average cell log-loss and frozen "
        "TC−CA contrast from the 25 main + 5 smoke prediction sidecars. No "
        "fitting, no counter reset, no M8 lock mutation. Numerical agreement "
        "with EXECUTE.json is **diagnostic only** under prospective gate FAIL.",
        "",
        "## Coverage and pins",
        "",
        f"- Pre-replay pins rematch: `{report['pre_replay_pins']['all_match']}` "
        f"({report['pre_replay_pins']['n_checked']} digests)",
        f"- Main 25/25 equality+loss rematch: "
        f"`{report['main_coverage']['all_folds_equality_and_loss_match']}`",
        f"- Smoke 5/5 equality+loss rematch: "
        f"`{report['smoke']['stored_vs_recomputed_loss_match']}`",
        f"- EXECUTE primary rematch: `{report['execute_comparison']['primary_match']}`",
        f"- Counter SHA before/after: `{report['post_replay_counter']['sha256_before']}`",
        "",
        "## Primary contrast (diagnostic)",
        "",
        f"- Pooled TC−CA: `{primary['pooled_estimate']:.6g}` "
        f"(n_donors={primary['n_donors_pooled']})",
        f"- Bootstrap 95% CI (seed {boot['seed']}): "
        f"`[{boot['interval'][0]:.6g}, {boot['interval'][1]:.6g}]`",
        f"- Practical margin: `{primary['practical_margin']}`",
        f"- Exploratory advantage observed: `{primary['exploratory_advantage_observed']}`",
        f"- Per-fold estimates: `{primary['per_fold_estimates']}`",
        "",
        "## Resources",
        "",
        f"- Attempts: `{report['post_replay_counter']['total_attempts_used']}/"
        f"{report['post_replay_counter']['hard_cap']}` "
        f"(smoke {report['post_replay_counter']['smoke_fits_used']}; "
        f"scientific {report['post_replay_counter']['scientific_fits_used']}; "
        f"failed {report['post_replay_counter']['failed']})",
        f"- Fitting hours (ledger): `{report['post_replay_counter']['fitting_hours_used']}`",
        f"- Artifact bytes (live du): `{report['artifact_bytes']['du_gib']:.6f}` GiB "
        f"({report['artifact_bytes']['du_kib']} KiB); "
        f"counter field `{report['post_replay_counter']['artifacts_gib_used_counter_field']}`",
        "",
        "## Claim limits",
        "",
        "- Claim level 2 computational prediction only.",
        "- Does **not** authorize scientific PASS of M9.",
        "- Does **not** promote biological state, causal mechanism, or external validation.",
        "- Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, Q2 "
        "`ENDPOINT_UNRESOLVED` unchanged.",
        "",
        "Machine-readable: [REPLAY.json](REPLAY.json). Coverage: "
        "[M10_COVERAGE_REVIEW.json](M10_COVERAGE_REVIEW.json).",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "REPLAY.json": str(json_path),
        "REPLAY.md": str(md_path),
        "REPLAY.json.sha256": sha256_file(json_path),
        "REPLAY.md.sha256": sha256_file(md_path),
    }
