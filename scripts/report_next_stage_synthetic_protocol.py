#!/usr/bin/env python3
"""Q7 freeze analytic synthetic protocol for S9 pairing-use software control.

Writes SYNTHETIC_PROTOCOL.json/.md and SPLIT_MANIFEST.json. Generator/oracle/
split helpers live in ``p22.eval.s9_analytic`` (shared with Q8). No model fits,
downloads, or package installs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.s9_analytic import (  # noqa: E402
    ARMS,
    DECISION_GENERATOR_SEED,
    DECISION_MODEL_SEED,
    DECISION_SPLIT_SEED,
    HEADROOM_GENERATOR_SEEDS,
    N_ARMS,
    N_DONORS,
    N_FEATURES,
    N_FOLDS,
    N_PLANTED_CHANNELS,
    ORACLE_BA_CHANCE_MAX,
    ORACLE_BA_RHO1_MIN,
    PAIRING_SHUFFLE_SEEDS,
    PROTOCOL_ID,
    PROTOCOL_KIND,
    SCREEN_FITS,
    SMOKE_FITS,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_ATTEMPT_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TOTAL_FITS,
    allocate_s9_folds,
    assign_donor_labels,
    recompute_fit_arithmetic,
    verify_oracle_invariants,
)

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
DEFAULT_FIT_LEDGER = DEFAULT_OUT_DIR / "FIT_LEDGER.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def build_protocol(
    *,
    split_manifest: dict[str, Any],
    fit_arithmetic: dict[str, Any],
    oracle: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task": "Q7",
        "disposition": "PROTOCOL_FROZEN",
        "protocol_id": PROTOCOL_ID,
        "kind": PROTOCOL_KIND,
        "date": "2026-09-30",
        "branch": "gnhf/execute-the-p22-data-146414",
        "fits": 0,
        "predictions": None,
        "network_bytes": 0,
        "depends_on": ["Q6"],
        "hypothesis": (
            "Can the existing seven-arm NN factory, under equal supervision and "
            "the frozen analytic generator, detect planted within-cell RNA/ATAC "
            "pairing via donor log-loss drop under within-donor ATAC shuffle?"
        ),
        "generation": {
            "n_donors": N_DONORS,
            "cells_per_donor": 32,
            "n_features_rna": N_FEATURES,
            "n_features_atac": N_FEATURES,
            "n_planted_channels": N_PLANTED_CHANNELS,
            "n_nuisance_channels": N_FEATURES - N_PLANTED_CHANNELS,
            "donor_label_equation": (
                "Rank donor_ids by SHA256('s9-label\\n'+generator_seed+'\\n'+donor_id); "
                "first 12 → class 0, remaining 12 → class 1. Labels are analytic and "
                "independent of any biological disease label."
            ),
            "planted_equation": (
                "For each donor d and planted channel k∈{0..3}: draw z,w ~ N(0,I) from "
                "SHA256(generator_seed, donor_id, channel, 'z'|'w') SeedSequence; "
                "centre/scale z to mean 0 variance 1; orthogonalize w against z then "
                "centre/scale. Set RNA[cells,k]=z and "
                "ATAC[cells,k]=(2*y_d-1)*rho*z + sqrt(1-rho^2)*w. "
                "Latent draws do not depend on fold index."
            ),
            "nuisance_equation": (
                "For channels k∈{4..15}: independent Gaussian draws per view plus a "
                "donor-level mean shift (0.5 * SHA256-stable donor shift vector). "
                "Nuisance is independent of y_d and of planted z."
            ),
            "interpretation": (
                "At all rho, planted channels have mean 0 and variance 1 per donor. "
                "rho controls signed within-cell cross-view covariance. At rho=0 there "
                "is no planted pairing; at rho=1 ATAC planted equals signed RNA planted. "
                "Unimodal marginals of planted channels carry no label signal."
            ),
            "row_identity": (
                "Generate in stable donor_id × cell_id order "
                "(s9_donor_XX__cell_YY); restore to fold tensor order at fit time."
            ),
            "test_pairing_shuffle": (
                "Permute ATAC rows within each held-out donor using fixed "
                "PAIRING_SHUFFLE_SEEDS; preserve exact within-donor ATAC marginal "
                "row multiset; never shuffle across donors or labels."
            ),
        },
        "oracle": {
            "definition": (
                "Non-learned donor score = mean over cells of sum of planted-channel "
                "products RNA[k]*ATAC[k] for k=0..3. Predict class 1 iff score > 0."
            ),
            "role": (
                "Validates that the constructed pairing signal exists and is destroyed "
                "by the intended within-donor ATAC shuffle. Does not validate learned models."
            ),
            "gates": {
                "rho1_ba_min": ORACLE_BA_RHO1_MIN,
                "chance_ba_max": ORACLE_BA_CHANCE_MAX,
                "require_rho1_detects": True,
                "require_rho0_near_chance": True,
                "require_shuffle_destroys_rho1": True,
            },
            "toy_verification": oracle,
        },
        "null": {
            "kind": "fitted_pairing_plant_null",
            "statement": (
                "Under the same fitted pipeline and within-donor ATAC shuffle "
                "intervention at rho=0, CA must not yield PAIRING_POSITIVE "
                "(donor log-loss-drop 95% CI lower <= 0)."
            ),
            "matches_tested_mechanism": True,
            "rejects_chance_bernoulli_ba_band": True,
            "prior_s8_no_fit_unchanged": True,
            "multiplicity": (
                "Joint coverage rule requires all seven arms to complete smoke+screen "
                "before interpreting pairing; the primary pairing estimand is CA-only. "
                "No joint seven-arm fitted-BA critical value is used (that path remains "
                "DESIGN_UNRESOLVED under the cap)."
            ),
        },
        "seeds": {
            "decision_generator_seed": DECISION_GENERATOR_SEED,
            "decision_split_seed": DECISION_SPLIT_SEED,
            "decision_model_seed": DECISION_MODEL_SEED,
            "pairing_shuffle_seeds": list(PAIRING_SHUFFLE_SEEDS),
            "headroom_generator_seeds": list(HEADROOM_GENERATOR_SEEDS),
            "calibration_decision_disjoint": True,
            "disjoint_rule": (
                "Decision seeds (9001 / split 0 / model 9001) are frozen before any "
                "result. Headroom seeds 9101+ are disjoint and may only be used within "
                "remaining fit headroom after review; they cannot retune the frozen "
                "null threshold, oracle gates, or primary statistic."
            ),
        },
        "splits": {
            "n_folds": N_FOLDS,
            "method": "s9-class-quota-sha256",
            "units": "donor",
            "outer_test_per_fold": 8,
            "train_val_per_fold": [12, 4],
            "both_classes_required": True,
            "manifest_ref": "SPLIT_MANIFEST.json",
            "fold_rationale": (
                "Prospective F=3 for analytic synthetic software/mechanism "
                "detectability of a planted pairing signal — not biological power "
                "and not a post-hoc shrink of the frozen S7 5-fold disease protocol."
            ),
        },
        "models": {
            "arms": list(ARMS),
            "n_arms": N_ARMS,
            "equal_supervision": True,
            "selection": (
                "Same inner-validation donor log-loss and identical available training "
                "budget for neural arms; no hyperparameter sweep."
            ),
            "reuse": (
                "Existing paired_model / model_inputs / train_model / fit_logistic / "
                "donor_cell_weights / nn_factory; Q8 adds only generator/statistic/runner "
                "pieces demonstrably missing."
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
                "param_match_ca_tc_relative": 0.10,
            },
        },
        "evaluation": {
            "primary_statistic": {
                "name": "pairing_use_donor_logloss_drop",
                "definition": (
                    "For CA at rho=1: mean donor log-loss(shuffled ATAC) - log-loss(original); "
                    "average shuffle outcomes within donor across PAIRING_SHUFFLE_SEEDS, "
                    "then paired donor-bootstrap 95% CI (1000 draws, seed 22). "
                    "PAIRING_POSITIVE iff CI lower > 0."
                ),
                "applies_to": "cross_attention",
                "rho": 1.0,
            },
            "fitted_mechanism_null_gate": {
                "definition": (
                    "Same pairing statistic at rho=0 must have CI lower <= 0; "
                    "otherwise label INVALID (design/optimization leak), not a method claim."
                ),
                "rho": 0.0,
            },
            "advantage_contrast": {
                "name": "ca_minus_token_concat_pooled_ba",
                "label": "SEPARATE_NON_PRIMARY",
                "definition": (
                    "Pooled donor BA(CA) - BA(token_concat) at rho=1 with paired "
                    "donor-bootstrap CI. Reported for description only; does not define "
                    "PAIRING_POSITIVE and is not required for a valid pairing-use control."
                ),
            },
            "joint_rule": (
                "All seven arms must complete smoke+screen coverage before interpreting "
                "pairing. Incomplete coverage => INCOMPLETE, not a partial positive."
            ),
            "marginal_check": (
                "At rho=1, logreg_rna and logreg_atac donor BA <= 0.60; failure suggests "
                "unimodal/background shortcut and refuses pairing-only interpretation."
            ),
            "donor_prediction": (
                "Mean held-out cell probability; threshold fixed 0.5; three disjoint "
                "outer folds pooled once per rho for descriptive BA only."
            ),
            "bootstrap": {
                "draws": 1000,
                "seed": 22,
                "cluster_unit": "donor",
                "paired_shared_draws": True,
                "invalid_draws": (
                    "Count/report single-class draws; never silently redraw; "
                    "insufficient valid draws (<950) => incomplete"
                ),
            },
        },
        "screen": {
            "generator_seed": DECISION_GENERATOR_SEED,
            "rho_grid": [0.0, 1.0],
            "fixed_decision_cell": 1.0,
            "do_not_choose_best_rho": True,
            "fits": SCREEN_FITS,
        },
        "smoke": {
            "fold": 0,
            "rho": 1.0,
            "fits": SMOKE_FITS,
            "require_both_classes_held_out": True,
        },
        "resources": {
            "max_total_fits": SYNTHETIC_ATTEMPT_CAP,
            "planned_attempted_fits": TOTAL_FITS,
            "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
            "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
            "max_simultaneous_workers": 2,
            "torch_threads_per_worker": 2,
            "fit_arithmetic": fit_arithmetic,
            "no_optimum_search_loop": True,
            "count_failed_attempts": True,
        },
        "output_roots": {
            "new_raw_root": "reports/generated/nn_s9_analytic_pairing_20260930/",
            "refuse_roots": [
                "reports/generated/nn_s7_covariance_20260929/",
                "reports/generated/nn_s7_covariance_split_v2_20260929/",
                "reports/generated/nn_s8_*",
            ],
            "no_write_through_shared_symlink": True,
        },
        "scientific_invariants": {
            "primary": "B_NULL",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "prior_s8": "NO FIT",
            "power": "POWER_UNESTABLISHED",
            "study": "STUDY_PARTIAL",
        },
        "unresolved_flags_retained": [
            "ENDPOINT_UNRESOLVED",
            "REGULATORY_ADEQUACY_UNRESOLVED",
            "EXTERNAL_FEASIBILITY_BOUNDED/confirmatory UNRESOLVED",
            "POWER_UNESTABLISHED",
            "fitted_ba_montecarlo_joint_calibration DESIGN_UNRESOLVED",
        ],
        "split_manifest_summary": {
            "n_folds": split_manifest["n_folds"],
            "n_donors": split_manifest["n_donors"],
            "class_balance": split_manifest["class_balance"],
            "validation": split_manifest["validation"],
        },
        "no_fits_until": "Checkpoint C (Q7+Q8+Q9 PASS on exact hashes)",
    }


def render_markdown(protocol: dict[str, Any], oracle: dict[str, Any]) -> str:
    fa = protocol["resources"]["fit_arithmetic"]
    lines = [
        "# Q7 — Synthetic protocol freeze (S9 analytic pairing-use)",
        "",
        f"**Disposition:** `{protocol['disposition']}`  ",
        f"**Protocol ID:** `{protocol['protocol_id']}`  ",
        f"**Kind:** `{protocol['kind']}`  ",
        f"**Date:** {protocol['date']}  ",
        f"**Branch:** `{protocol['branch']}`  ",
        "**Fits:** 0 (protocol freeze only; Checkpoint C required before any research fit).",
        "",
        "Machine-readable: [SYNTHETIC_PROTOCOL.json](SYNTHETIC_PROTOCOL.json); "
        "[SPLIT_MANIFEST.json](SPLIT_MANIFEST.json); [FIT_LEDGER.json](FIT_LEDGER.json).",
        "",
        "## Hypothesis",
        "",
        protocol["hypothesis"],
        "",
        "## Generator equations",
        "",
        f"- **Donor labels:** {protocol['generation']['donor_label_equation']}",
        f"- **Planted pairing:** {protocol['generation']['planted_equation']}",
        f"- **Nuisance:** {protocol['generation']['nuisance_equation']}",
        f"- **Interpretation:** {protocol['generation']['interpretation']}",
        "",
        "## Oracle",
        "",
        f"- Definition: {protocol['oracle']['definition']}",
        f"- Role: {protocol['oracle']['role']}",
        f"- Toy gate: `{oracle['oracle_gate']}` "
        f"(ρ=1 BA={oracle['rho1_oracle_ba']:.4f}; "
        f"ρ=0 BA={oracle['rho0_oracle_ba']:.4f}; "
        f"ρ=1 shuffled BA={oracle['rho1_shuffled_oracle_ba']:.4f})",
        "",
        "## Fitted-mechanism null",
        "",
        protocol["null"]["statement"],
        "",
        "Chance/Bernoulli BA bands remain rejected (prior S8 `NO FIT` unchanged).",
        "",
        "## Seeds (decision vs headroom disjoint)",
        "",
        f"- Decision: generator `{protocol['seeds']['decision_generator_seed']}`, "
        f"split `{protocol['seeds']['decision_split_seed']}`, "
        f"model `{protocol['seeds']['decision_model_seed']}`",
        f"- Pairing shuffle seeds (not fits): `{protocol['seeds']['pairing_shuffle_seeds'][0]}`"
        f"–`{protocol['seeds']['pairing_shuffle_seeds'][-1]}`",
        f"- Headroom (disjoint): `{protocol['seeds']['headroom_generator_seeds']}`",
        f"- Rule: {protocol['seeds']['disjoint_rule']}",
        "",
        "## Splits",
        "",
        f"- F={protocol['splits']['n_folds']} donor-level class-quota SHA256; "
        f"{protocol['splits']['outer_test_per_fold']} test / "
        f"{protocol['splits']['train_val_per_fold'][0]} train / "
        f"{protocol['splits']['train_val_per_fold'][1]} val per fold; both classes required.",
        f"- Rationale: {protocol['splits']['fold_rationale']}",
        "",
        "## Arms and budgets",
        "",
        f"- Seven equally supervised arms: {', '.join(protocol['models']['arms'])}",
        f"- Smoke {fa['smoke_fold0_rho1']} + screen ρ=0 {fa['screen_rho0']} + "
        f"screen ρ=1 {fa['screen_rho1']} = **{fa['total_attempted_fits']} ≤ {fa['cap']}** "
        f"(headroom {fa['headroom_fits']})",
        f"- Fitting hours ≤ {fa['fitting_hours_cap']}; artifacts ≤ {fa['artifact_gib_cap']} GiB; "
        "2 workers × 2 torch threads",
        "",
        "## Primary statistic vs advantage contrast",
        "",
        f"- **Primary (pairing-use):** {protocol['evaluation']['primary_statistic']['definition']}",
        f"- **Null gate:** {protocol['evaluation']['fitted_mechanism_null_gate']['definition']}",
        f"- **Advantage contrast (`SEPARATE_NON_PRIMARY`):** "
        f"{protocol['evaluation']['advantage_contrast']['definition']}",
        f"- **Joint rule:** {protocol['evaluation']['joint_rule']}",
        "",
        "## Scientific invariants (unchanged)",
        "",
        "Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; "
        "power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.",
        "",
        "Unresolved flags retained: "
        + "; ".join(protocol["unresolved_flags_retained"])
        + ".",
        "",
        "## Next",
        "",
        "Q8 implements minimal generator/runner reuse and focused falsification tests. "
        "No fits until Checkpoint C.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(out_dir: Path, ledger_path: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = _load_json(ledger_path)
    if ledger.get("selected_candidate_id") != "selected_pairing_use_fitted_plant_null":
        raise RuntimeError("FIT_LEDGER selected candidate mismatch vs Q6")
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    split_manifest = allocate_s9_folds(labels)
    fit_arithmetic = recompute_fit_arithmetic(ledger)
    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise RuntimeError(f"oracle gate FAIL: {oracle}")
    protocol = build_protocol(
        split_manifest=split_manifest,
        fit_arithmetic=fit_arithmetic,
        oracle=oracle,
    )
    proto_path = out_dir / "SYNTHETIC_PROTOCOL.json"
    md_path = out_dir / "SYNTHETIC_PROTOCOL.md"
    split_path = out_dir / "SPLIT_MANIFEST.json"
    proto_path.write_text(json.dumps(protocol, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_markdown(protocol, oracle))
    split_path.write_text(json.dumps(split_manifest, indent=2, sort_keys=False) + "\n")
    return {
        "disposition": protocol["disposition"],
        "protocol_id": PROTOCOL_ID,
        "oracle_gate": oracle["oracle_gate"],
        "total_attempted_fits": fit_arithmetic["total_attempted_fits"],
        "paths": {
            "protocol_json": str(proto_path),
            "protocol_md": str(md_path),
            "split_manifest": str(split_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--fit-ledger", type=Path, default=DEFAULT_FIT_LEDGER)
    args = parser.parse_args(argv)
    summary = write_outputs(args.out_dir, args.fit_ledger)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
