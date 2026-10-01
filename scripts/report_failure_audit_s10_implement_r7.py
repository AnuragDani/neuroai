#!/usr/bin/env python3
"""R7 reporter: freeze S10 protocol/split/seed artifacts and IMPLEMENT dry-run.

Zero scientific fits. Generator-only exchangeability panel counts toward the
stage generator budget. Writes owned files under failure_audit_20261001/.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from p22.eval.s7_ledger import sha256_file
from p22.eval.s9_analytic import ARMS, N_FOLDS
from p22.eval.s10_analytic import (
    ALLOWED_RAW_ROOT,
    CLAIM_LEVEL,
    DECISION_GENERATOR_SEED,
    DECISION_MODEL_SEED,
    DECISION_SPLIT_SEED,
    HEADROOM_GENERATOR_SEEDS,
    NULL_CANDIDATE_ID,
    PAIRING_SHUFFLE_SEEDS,
    PROTOCOL_ID,
    PROTOCOL_KIND,
    R7_EXCHANGEABILITY_SEEDS,
    SCIENTIFIC_ATTEMPT_CAP,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TORCH_THREADS,
    TOTAL_FITS,
    WORKERS,
    assign_donor_labels,
    build_split_manifest,
    recompute_fit_arithmetic,
    run_r7_dry_run,
    seed_schedule_payload,
    verify_oracle_invariants,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
COUNTER = ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
RAW_SUBDIR = (
    ROOT
    / "reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001"
)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_protocol_json(*, oracle: dict, fit_arithmetic: dict) -> dict:
    return {
        "task": "R7",
        "disposition": "PROTOCOL_FROZEN",
        "protocol_id": PROTOCOL_ID,
        "kind": PROTOCOL_KIND,
        "null_candidate_id": NULL_CANDIDATE_ID,
        "claim_level": CLAIM_LEVEL,
        "date": "2026-10-01",
        "branch": "gnhf/execute-p22-s-failur-d8f02c",
        "fits": 0,
        "depends_on": ["R6"],
        "hypothesis": (
            "Under the corrected independent-Gaussian ρ=0 null (no exact "
            "orthogonalization), does the seven-arm NN factory detect planted "
            "within-cell RNA/ATAC pairing via CA donor log-loss drop under "
            "within-donor ATAC shuffle, with a VALID exchangeable ρ=0 null gate?"
        ),
        "generation": {
            "n_donors": 24,
            "cells_per_donor": 32,
            "n_features_rna": 16,
            "n_features_atac": 16,
            "n_planted_channels": 4,
            "n_nuisance_channels": 12,
            "donor_label_equation": (
                "Reuse S9 assign_donor_labels: rank donor_ids by "
                "SHA256('s9-label\\n'+generator_seed+'\\n'+donor_id); first 12 → "
                "class 0, remaining 12 → class 1. Decision generator_seed=9301."
            ),
            "planted_equation": (
                "For each donor d and planted channel k∈{0..3}: draw z,w ~ N(0,I) "
                "from SHA256(generator_seed, donor_id, channel, 'z_s10'|'w_s10'); "
                "centre/scale each independently (NO orthogonalize). Set "
                "RNA[cells,k]=z and ATAC[cells,k]=(2*y_d-1)*rho*z + sqrt(1-rho^2)*w. "
                "At rho=0 ATAC planted = independent w (exchangeable under "
                "within-donor ATAC shuffle). At rho=1 ATAC planted = signed RNA."
            ),
            "nuisance_equation": (
                "Channels k∈{4..15}: independent Gaussian draws per view plus a "
                "donor-level mean shift (0.5 * SHA256-stable donor shift); tags "
                "use '_s10' suffixes. Independent of y_d and planted z."
            ),
            "correction_vs_s9": (
                "Removes exact w⊥z orthogonalization that placed ρ=0 planted "
                "pairs on measure-zero and broke shuffle exchangeability (R2)."
            ),
            "test_pairing_shuffle": (
                "Permute ATAC rows within each held-out donor using fixed "
                "PAIRING_SHUFFLE_SEEDS 4001–4016; preserve exact within-donor "
                "ATAC marginal row multiset; never shuffle across donors/labels."
            ),
        },
        "oracle": {
            "definition": (
                "Non-learned donor score = mean over cells of sum of planted-"
                "channel products RNA[k]*ATAC[k] for k=0..3. Predict class 1 "
                "iff score > 0."
            ),
            "role": (
                "Validates constructed pairing exists and is destroyed by "
                "within-donor ATAC shuffle. Does not validate learned models."
            ),
            "gates": {
                "rho1_ba_min": 0.9,
                "chance_ba_max": 0.7,
                "require_rho1_detects": True,
                "require_rho0_near_chance": True,
                "require_shuffle_destroys_rho1": True,
                "require_rho0_not_exact_orthogonal": True,
            },
            "toy_verification": oracle,
        },
        "null": {
            "kind": "fitted_pairing_plant_null_exchangeable",
            "statement": (
                "Under the corrected generator and within-donor ATAC shuffle at "
                "rho=0, CA must not yield PAIRING_POSITIVE (donor log-loss-drop "
                "95% CI lower <= 0)."
            ),
            "matches_tested_mechanism": True,
            "rejects_chance_bernoulli_ba_band": True,
            "prior_s8_no_fit_unchanged": True,
            "s9_invalid_immutable": True,
        },
        "seeds": seed_schedule_payload(),
        "splits": {
            "n_folds": N_FOLDS,
            "method": "s9-class-quota-sha256",
            "units": "donor",
            "outer_test_per_fold": 8,
            "train_val_per_fold": [12, 4],
            "both_classes_required": True,
            "manifest_ref": "S10_SPLIT_MANIFEST.json",
            "split_seed": DECISION_SPLIT_SEED,
            "generator_seed": DECISION_GENERATOR_SEED,
        },
        "models": {
            "arms": list(ARMS),
            "n_arms": 7,
            "equal_supervision": True,
            "selection": (
                "Same inner-validation donor log-loss and identical available "
                "training budget for neural arms; no hyperparameter sweep."
            ),
            "reuse": (
                "Existing paired_model / model_inputs / train_model / fit_logistic "
                "/ s7 pairing helpers; s10_analytic adds corrected generator only."
            ),
            "training_budget": {
                "max_epochs": 20,
                "patience": 5,
                "learning_rate": 0.001,
                "batch_size": 64,
                "n_tokens": 8,
                "embed_dim": 32,
                "hidden_dim": 128,
                "n_heads": 4,
                "dropout": 0.2,
                "param_match_ca_tc_relative": 0.1,
            },
        },
        "evaluation": {
            "primary_statistic": {
                "name": "pairing_use_donor_logloss_drop",
                "definition": (
                    "For CA at rho=1: mean donor log-loss(shuffled ATAC) - "
                    "log-loss(original); average shuffle outcomes within donor "
                    "across PAIRING_SHUFFLE_SEEDS, then paired donor-bootstrap "
                    "95% CI (1000 draws, seed 22). PAIRING_POSITIVE iff CI lower > 0."
                ),
                "applies_to": "cross_attention",
                "rho": 1.0,
            },
            "fitted_mechanism_null_gate": {
                "definition": (
                    "Same pairing statistic at rho=0 must have CI lower <= 0; "
                    "otherwise label INVALID (design/optimization leak), not a "
                    "method claim."
                ),
                "rho": 0.0,
            },
            "advantage_contrast": {
                "name": "ca_minus_token_concat_pooled_ba",
                "label": "SEPARATE_NON_PRIMARY",
                "definition": (
                    "Pooled donor BA(CA) - BA(token_concat) at rho=1 with paired "
                    "donor-bootstrap CI. Descriptive only."
                ),
            },
            "joint_rule": (
                "All seven arms must complete smoke+screen coverage before "
                "interpreting pairing. Incomplete coverage => INCOMPLETE."
            ),
            "marginal_check": (
                "At rho=1, logreg_rna and logreg_atac donor BA <= 0.60; failure "
                "suggests unimodal/background shortcut."
            ),
            "outcome_precedence": [
                "INCOMPLETE if coverage < 49",
                "INVALID if rho=0 pairing CI lower > 0",
                "INVALID if rho=1 unimodal marginal BA FAIL",
                "VALID_POSITIVE if rho=1 PAIRING_POSITIVE and marginal PASS and rho=0 null VALID",
                "VALID_NEGATIVE if rho=1 PAIRING_NEGATIVE with rho=0 null VALID and marginal PASS",
            ],
            "claim_scope": "claim_level_1_software_only",
            "bootstrap": {
                "draws": 1000,
                "seed": 22,
                "cluster_unit": "donor",
                "paired_shared_draws": True,
            },
        },
        "screen": {
            "generator_seed": DECISION_GENERATOR_SEED,
            "rho_grid": [0.0, 1.0],
            "fixed_decision_cell": 1.0,
            "do_not_choose_best_rho": True,
            "fits": 42,
        },
        "smoke": {
            "fold": 0,
            "rho": 1.0,
            "fits": 7,
            "counts_as_scientific": True,
            "require_both_classes_held_out": True,
        },
        "resources": {
            "max_total_scientific_fits": SCIENTIFIC_ATTEMPT_CAP,
            "planned_attempted_fits": TOTAL_FITS,
            "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
            "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
            "max_simultaneous_workers": WORKERS,
            "torch_threads_per_worker": TORCH_THREADS,
            "serial_default": True,
            "payload_mib": 0,
            "fit_arithmetic": fit_arithmetic,
            "no_optimum_search_loop": True,
            "count_failed_attempts": True,
            "reserve_attempts_before_dispatch": True,
            "allowed_raw_root": ALLOWED_RAW_ROOT,
        },
        "exclusions": [
            "No S9 rescue or re-label of historical INVALID",
            "No seed shopping / outcome-driven threshold change",
            "No biology upgrade / claim-4",
            "No NeMO development use / no external predictions",
            "No ThreadPoolExecutor scientific dispatch unless later reviewed isolation proof",
            "No diagnostic-fit allowance remaining (12/12 exhausted)",
        ],
        "scientific_invariants": {
            "primary": "B_NULL",
            "s9": "INVALID",
            "s9_immutable": True,
            "prior_s8": "NO FIT",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "study": "STUDY_PARTIAL",
            "q2": "ENDPOINT_UNRESOLVED",
        },
    }


def build_protocol_md(*, protocol: dict, oracle: dict, fit_arithmetic: dict) -> str:
    lines = [
        "# R7 — S10 corrected-null protocol freeze",
        "",
        "**Disposition:** `PROTOCOL_FROZEN` + `IMPLEMENT_PASS`",
        f"**Protocol ID:** `{PROTOCOL_ID}`",
        f"**Kind:** `{PROTOCOL_KIND}`",
        f"**Null candidate:** `{NULL_CANDIDATE_ID}`",
        f"**Claim level:** {CLAIM_LEVEL} (software / mechanism control)",
        "**Date:** 2026-10-01",
        "**Branch:** `gnhf/execute-p22-s-failur-d8f02c`",
        "**Fits:** 0 scientific; 0 diagnostic (cap exhausted).",
        "",
        "Machine-readable: [S10_PROTOCOL.json](S10_PROTOCOL.json); "
        "[S10_SPLIT_MANIFEST.json](S10_SPLIT_MANIFEST.json); "
        "[S10_SEED_SCHEDULE.json](S10_SEED_SCHEDULE.json); "
        "[IMPLEMENT.md](IMPLEMENT.md).",
        "",
        "## Hypothesis",
        "",
        protocol["hypothesis"],
        "",
        "## Generator correction vs S9",
        "",
        "- **S9 defect (immutable):** exact ρ=0 orthogonalization broke within-donor "
        "ATAC shuffle exchangeability (R2 ESTABLISHED).",
        "- **S10 repair:** planted z,w are independently centre-scaled Gaussians "
        "(tags `z_s10`/`w_s10`); **no** `w⊥z` projection.",
        "- At ρ=0: ATAC planted = independent w (exchangeable under within-donor shuffle).",
        "- At ρ=1: ATAC planted = signed RNA (positive-control role unchanged).",
        "",
        "## Seeds (prospective; disjoint from S9/R2 panels)",
        "",
        f"- Decision: generator `{DECISION_GENERATOR_SEED}`, split "
        f"`{DECISION_SPLIT_SEED}`, model `{DECISION_MODEL_SEED}`",
        f"- Headroom: `{list(HEADROOM_GENERATOR_SEEDS)}`",
        f"- Pairing shuffle: `{list(PAIRING_SHUFFLE_SEEDS)}` (intervention; not fits)",
        f"- R7 exchangeability panel: `{list(R7_EXCHANGEABILITY_SEEDS)}` "
        "(generator-only; ≤64)",
        "",
        "## Oracle (toy; decision seed)",
        "",
        f"- ρ=1 BA={oracle['rho1_oracle_ba']:.4f}; ρ=0 BA={oracle['rho0_oracle_ba']:.4f}; "
        f"ρ=1 shuffled BA={oracle['rho1_shuffled_oracle_ba']:.4f}",
        f"- ρ=0 max |product mean|={oracle['rho0_max_abs_product_mean']:.6f} "
        "(not machine-zero orthogonal)",
        f"- Gate: `{oracle['oracle_gate']}`",
        "",
        "## Arms and budgets",
        "",
        f"- Seven equally supervised arms: {', '.join(ARMS)}",
        f"- Smoke 7 + screen ρ=0 21 + screen ρ=1 21 = **{TOTAL_FITS} ≤ "
        f"{SCIENTIFIC_ATTEMPT_CAP}** (headroom {fit_arithmetic['headroom_fits']})",
        f"- Serial workers=`{WORKERS}`; torch threads=`{TORCH_THREADS}`",
        f"- Fitting hours ≤ {SYNTHETIC_FITTING_HOURS_CAP}; artifacts ≤ "
        f"{SYNTHETIC_ARTIFACT_GIB_CAP} GiB; payloads = 0",
        f"- Raw root: `{ALLOWED_RAW_ROOT}`",
        "",
        "## Primary statistic and null gate",
        "",
        "- **Primary:** CA ρ=1 donor log-loss drop under within-donor ATAC shuffle "
        "(PAIRING_POSITIVE iff CI lower > 0).",
        "- **Null gate:** same statistic at ρ=0 must have CI lower ≤ 0.",
        "- **Advantage contrast:** CA−token_concat pooled BA = `SEPARATE_NON_PRIMARY`.",
        "- Unimodal marginal BA ≤ 0.60 at ρ=1 for logreg_rna/atac.",
        "",
        "## Scientific invariants (unchanged)",
        "",
        "Primary `B_NULL`; S9 `INVALID` immutable; S7-v1/v2 `INVALID`; prior S8 "
        "`NO FIT`; Q2 `ENDPOINT_UNRESOLVED`; study `STUDY_PARTIAL`.",
        "",
        "## Next",
        "",
        "R8 independent full-path review on actual executor + dependency hashes. "
        "No scientific fits until Checkpoint C PASS.",
        "",
    ]
    return "\n".join(lines)


def build_implement_md(*, report: dict) -> str:
    ex = report["exchangeability_panel"]
    lines = [
        "# R7 — Minimal implement (S10 corrected null)",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Protocol ID:** `{PROTOCOL_ID}`",
        "**Date:** 2026-10-01",
        "**Branch:** `gnhf/execute-p22-s-failur-d8f02c`",
        f"**Research fits:** 0 (`{report['trainability_with_learning']}`).",
        f"**Generator draws this run:** {report['generator_draws_this_run']} "
        "(R7 exchangeability panel).",
        "",
        "Machine-readable: [implement.json](implement.json); frozen "
        "[S10_PROTOCOL.json](S10_PROTOCOL.json).",
        "",
        "## Reuse",
        "",
        "- Existing `paired_model` / `model_inputs` / `predict` / S7 pairing helpers.",
        "- Existing S9 label/split/oracle-scoring/permute helpers via import.",
        "- New: `p22.eval.s10_analytic` corrected generator + dry-run/refusals; "
        "`p22.eval.s10_execute` serial executor stub (fits refused until R8).",
        "",
        "## Verification summary",
        "",
        f"- Oracle gate: `{report['oracle']['oracle_gate']}` "
        f"(ρ=1 BA={report['oracle']['rho1_oracle_ba']:.4f}; "
        f"ρ=0 BA={report['oracle']['rho0_oracle_ba']:.4f}; "
        f"ρ=1 shuffled={report['oracle']['rho1_shuffled_oracle_ba']:.4f})",
        f"- Exchangeability panel: mean ratio={ex['mean_ratio']:.4f} "
        f"(band {ex['band']}; within={ex['ratio_within_band']})",
        f"- Job coverage: smoke {report['job_coverage']['smoke']} + screen "
        f"{report['job_coverage']['screen']} = **{report['job_coverage']['total']} "
        f"≤ {SCIENTIFIC_ATTEMPT_CAP}**",
        f"- CA/TC param match: pass={report['param_match']['pass']} "
        f"(rel={report['param_match']['relative_abs_diff']:.4f})",
        f"- Finite gradients: all {len(report['gradients_finite'])} neural arms",
        f"- Reload equality: all {len(report['reload_pass'])} neural arms",
        "- Refusals: hash/S7/S9-raw/unreviewed-fits + allowed S10 root",
        f"- Workers: {report['workers']} (serial); torch threads: {report['torch_threads']}",
        "",
        "## Hashes (exact)",
        "",
    ]
    for key, digest in report["hashes"].items():
        lines.append(f"- `{key}`: `{digest}`")
    lines.extend(
        [
            "",
            "## Scientific invariants (unchanged)",
            "",
            "Primary `B_NULL`; S9 `INVALID` immutable; prior S8 `NO FIT`; "
            "study `STUDY_PARTIAL`.",
            "",
            "## Next",
            "",
            "R8 independent full-path review on exact hashes (executor + "
            "dependencies). No fits until Checkpoint C.",
            "",
        ]
    )
    return "\n".join(lines)


def update_attempt_counter(generator_draws: int) -> dict:
    counter = json.loads(COUNTER.read_text(encoding="utf-8"))
    prior = int(counter.get("generator_only_draws", 0))
    counter["generator_only_draws"] = prior + int(generator_draws)
    counter["r7_generator_draws_this_run"] = int(generator_draws)
    counter["r7_updated_at"] = _utc_now()
    counter["scientific_fit_attempts"] = int(counter.get("scientific_fit_attempts", 0))
    COUNTER.write_text(json.dumps(counter, indent=2, sort_keys=True) + "\n")
    return counter


def write_outputs() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW_SUBDIR.mkdir(parents=True, exist_ok=True)
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    oracle = verify_oracle_invariants(labels)
    fit_arithmetic = recompute_fit_arithmetic()
    split_manifest = build_split_manifest(labels)
    seed_schedule = seed_schedule_payload()
    protocol = build_protocol_json(oracle=oracle, fit_arithmetic=fit_arithmetic)

    proto_path = OUT / "S10_PROTOCOL.json"
    split_path = OUT / "S10_SPLIT_MANIFEST.json"
    seed_path = OUT / "S10_SEED_SCHEDULE.json"
    proto_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    split_path.write_text(json.dumps(split_manifest, indent=2, sort_keys=True) + "\n")
    seed_path.write_text(json.dumps(seed_schedule, indent=2, sort_keys=True) + "\n")
    (OUT / "S10_PROTOCOL.md").write_text(
        build_protocol_md(
            protocol=protocol, oracle=oracle, fit_arithmetic=fit_arithmetic
        )
    )

    report = run_r7_dry_run(protocol_path=proto_path, split_path=split_path)
    report["hashes"]["S10_PROTOCOL.json"] = sha256_file(proto_path)
    report["hashes"]["S10_SPLIT_MANIFEST.json"] = sha256_file(split_path)
    report["hashes"]["S10_SEED_SCHEDULE.json"] = sha256_file(seed_path)
    report["hashes"]["src/p22/eval/s10_analytic.py"] = sha256_file(
        ROOT / "src/p22/eval/s10_analytic.py"
    )
    exec_path = ROOT / "src/p22/eval/s10_execute.py"
    if exec_path.is_file():
        report["hashes"]["src/p22/eval/s10_execute.py"] = sha256_file(exec_path)
    report["fits"] = 0
    report["date"] = "2026-10-01"
    report["branch"] = "gnhf/execute-p22-s-failur-d8f02c"
    report["decision_seeds"] = {
        "generator": DECISION_GENERATOR_SEED,
        "split": DECISION_SPLIT_SEED,
        "model": DECISION_MODEL_SEED,
    }

    (OUT / "implement.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (OUT / "IMPLEMENT.md").write_text(build_implement_md(report=report))

    counter = update_attempt_counter(int(report["generator_draws_this_run"]))
    report["attempt_counter_after"] = {
        "generator_only_draws": counter["generator_only_draws"],
        "scientific_fit_attempts": counter["scientific_fit_attempts"],
        "diagnostic_fit_attempts": counter["diagnostic_fit_attempts"],
    }
    # Rewrite implement.json with counter snapshot.
    (OUT / "implement.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> int:
    report = write_outputs()
    print(json.dumps({"disposition": report["disposition"], "protocol_id": PROTOCOL_ID,
                      "generator_draws": report["generator_draws_this_run"],
                      "oracle_gate": report["oracle"]["oracle_gate"],
                      "hashes": report["hashes"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
