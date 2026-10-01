#!/usr/bin/env python3
"""Q6 research decision: rank bottlenecks, choose one experiment, fit ledger.

Cross-checks Q2–Q5 dispositions and corrects the prior S8 chance-band numerical
illustration using exact (not rounded) Bernoulli quantiles and exact pooled
donor BAs from saved S7-v2 sidecars. No fits, downloads, or package installs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
DEFAULT_DONOR_PREDS = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
    "nn_s7_covariance_split_v2_20260929/donor_predictions"
)
DEFAULT_Q_REPORTS = {
    "q2": DEFAULT_OUT_DIR / "endpoint_inventory.json",
    "q3": DEFAULT_OUT_DIR / "regulatory_coverage.json",
    "q4": DEFAULT_OUT_DIR / "sampling_feasibility.json",
    "q5": DEFAULT_OUT_DIR / "external_feasibility.json",
}
ARMS = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
    "logreg_concat",
    "logreg_rna",
    "logreg_atac",
)
SYNTHETIC_ATTEMPT_CAP = 60
SYNTHETIC_FITTING_HOURS_CAP = 4
SYNTHETIC_ARTIFACT_GIB_CAP = 2


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def pooled_rho0_bas(donor_pred_dir: Path) -> dict[str, float]:
    """Exact pooled donor BA at rho=0 from saved S7-v2 screen sidecars."""
    out: dict[str, float] = {}
    labels_ref: list[int] | None = None
    for arm in ARMS:
        labels: list[int] = []
        preds: list[int] = []
        donors: list[str] = []
        for fold in range(5):
            path = donor_pred_dir / f"screen__0__1001__{fold}__{arm}.donors.json"
            block = _load_json(path)["donor_probabilities"]
            donors.extend(block["donor_id"])
            labels.extend(int(x) for x in block["label"])
            preds.extend(int(x) for x in block["prediction"])
        if len(donors) != 30 or len(set(donors)) != 30:
            raise RuntimeError(f"{arm}: expected 30 unique held-out donors, got {len(set(donors))}")
        if labels_ref is None:
            labels_ref = labels
        elif labels != labels_ref:
            raise RuntimeError(f"{arm}: donor label order mismatch vs first arm")
        out[arm] = float(balanced_accuracy_score(np.asarray(labels), np.asarray(preds)))
    return out


def bernoulli_central_95(
    labels: np.ndarray, *, seed: int = 0, draws: int = 10_000
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    bas = np.empty(draws, dtype=float)
    n = len(labels)
    for i in range(draws):
        bas[i] = balanced_accuracy_score(labels, rng.integers(0, 2, size=n))
    lo, hi = np.quantile(bas, [0.025, 0.975])
    return float(lo), float(hi)


def s8_numerical_correction(donor_pred_dir: Path) -> dict[str, Any]:
    """Correct rounded-band S8 illustration; keep mechanism-mismatch intact."""
    exact_bas = pooled_rho0_bas(donor_pred_dir)
    # Actual pooled labels are 16/14 (same composition as DECISION illustration).
    y = np.array([0] * 16 + [1] * 14, dtype=int)
    lo_exact, hi_exact = bernoulli_central_95(y, seed=0, draws=10_000)
    rounded_lo, rounded_hi = round(lo_exact, 3), round(hi_exact, 3)
    gated = exact_bas["gated_fusion"]
    token = exact_bas["token_concat"]
    rows = []
    for arm, ba in exact_bas.items():
        rows.append(
            {
                "arm": arm,
                "exact_pooled_ba": ba,
                "inside_exact_band": bool(lo_exact <= ba <= hi_exact),
                "inside_rounded_band_3dp": bool(rounded_lo <= ba <= rounded_hi),
                "delta_vs_exact_lo": ba - lo_exact,
            }
        )
    return {
        "source_donor_predictions": str(donor_pred_dir),
        "label_vector": {"n0": 16, "n1": 14, "n": 30},
        "bernoulli_mc": {
            "predictor": "Bernoulli-0.5 hard labels",
            "draws": 10_000,
            "seed": 0,
            "exact_central_95": [lo_exact, hi_exact],
            "rounded_3dp_central_95": [rounded_lo, rounded_hi],
        },
        "exact_pooled_rho0_bas": exact_bas,
        "boundary_case": {
            "arm": "gated_fusion",
            "exact_pooled_ba": gated,
            "reported_6dp_in_prior_review": 0.325893,
            "equals_exact_lo": bool(gated == lo_exact),
            "inside_exact_band": bool(lo_exact <= gated <= hi_exact),
            "inside_rounded_band_3dp": bool(rounded_lo <= gated <= rounded_hi),
            "correction": (
                "Rounded endpoints [0.326, 0.674] incorrectly exclude gated_fusion "
                f"exact BA {gated}, which sits exactly on the Bernoulli 2.5% quantile "
                f"{lo_exact}. Exact band classification must be used."
            ),
        },
        "token_concat": {
            "exact_pooled_ba": token,
            "inside_exact_band": bool(lo_exact <= token <= hi_exact),
            "inside_rounded_band_3dp": bool(rounded_lo <= token <= rounded_hi),
        },
        "illustrative_claim_with_exact_values": {
            "all_seven_arms_inside_exact_chance_band": all(
                r["inside_exact_band"] for r in rows
            ),
            "arms": rows,
            "retained_conclusion": (
                "Under the exact Bernoulli central 95% band, every S7-v2 rho=0 pooled "
                "BA (including token_concat and gated_fusion) falls inside. Adopting "
                "that chance band after seeing the frozen [0.35,0.65] failures remains "
                "an outcome-guided relaxation. Mechanism mismatch alone still rejects "
                "chance predictors as a fitted-model null."
            ),
        },
        "mechanism_mismatch_retained": True,
        "unsupported_rounded_argument_removed": True,
        "prior_s8_no_fit_unchanged": True,
    }


def rank_bottlenecks(q_reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    q2, q3, q4, q5 = (q_reports["q2"], q_reports["q3"], q_reports["q4"], q_reports["q5"])
    return [
        {
            "id": "task_endpoint",
            "rank_label": "established",
            "summary": "No independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs.",
            "supporting_evidence": [
                f"Q2 disposition {q2.get('disposition')}",
                "H5AD lacks continuous pseudotime/maturation fields",
                "author_cell_type/SCT clusters are RNA-derived from the same Gene Expression modality",
            ],
            "contradicting_evidence": [
                "Specimen disease/group remains a valid non-state primary endpoint (already used; B_NULL)",
            ],
            "blocks": ["biological_cell_state_pilot", "Q11_real_pilot_unless_new_endpoint"],
        },
        {
            "id": "implementation_optimization_control",
            "rank_label": "established",
            "summary": (
                "S7-v1/v2 INVALID and prior S8 NO FIT leave pairing-use / fitted-null "
                "software control unresolved; July 21 discriminating multimodal "
                "benchmark vs concat remains open."
            ),
            "supporting_evidence": [
                "S7-v2 rho-0 pooled null FAIL; pairing-PC PC_FAIL",
                "Prior S8 chance-null rejected for mechanism mismatch (exact-band correction below)",
                "PLAN D3 / July 21 MOM 14:02–17:39 request a discriminating benchmark with concat baseline",
            ],
            "contradicting_evidence": [
                "Primary ladder_v3 verifier PASS with B_NULL does not by itself prove software failure",
            ],
            "blocks": [],
        },
        {
            "id": "sampling_support",
            "rank_label": "plausible_resolved_for_support",
            "summary": "Targeted sampling restores rare-type support; eligibility frozen; not every-fold feasible for MIC/OPC.",
            "supporting_evidence": [
                f"Q4 disposition {q4.get('disposition')}; eligibility {q4.get('eligibility_status')}",
                "MIC/OPC/VASC selected ≥20 restored to available counts under cap64/seed22",
            ],
            "contradicting_evidence": [
                "Restored support ≠ biological signal; power POWER_UNESTABLISHED",
                "MIC/OPC remain non-split-feasible under frozen 5×5 both-class-every-fold rule",
            ],
            "blocks": [],
        },
        {
            "id": "atac_regulatory_coverage",
            "rank_label": "plausible_structural_unknown_regulatory",
            "summary": "Structural 25-panel coverage PASS; regulatory adequacy unresolved without element catalog.",
            "supporting_evidence": [
                (
                    "Q3 structural "
                    f"{(q3.get('structural_adequacy') or {}).get('label')} / "
                    f"regulatory {q3.get('disposition')}"
                ),
                "Exact counted 465-region union present; fold-0/repeat-0 replay matched",
            ],
            "contradicting_evidence": [
                "Gene-body/flank overlaps are descriptive only",
                "Cannot authorize biological regulatory-feature claims",
            ],
            "blocks": ["biological_regulatory_feature_claim"],
        },
        {
            "id": "donor_count_power",
            "rank_label": "established_limit_unknown_cause",
            "summary": "30 donors / 15+15 limits replication; cell count ≠ donor count; power unestablished.",
            "supporting_evidence": [
                "DATA_DIAGNOSTIC / Q4: 30 donors; practical_margin 0.07 at 15+15",
                "detectability min_detectable_delta=null; POWER_UNESTABLISHED",
            ],
            "contradicting_evidence": [
                "Null result alone does not prove donor-count is the binding cause",
            ],
            "blocks": ["equivalence_or_power_claim"],
        },
        {
            "id": "external_confirmatory",
            "rank_label": "unknown_unresolved",
            "summary": "NeMO confirmatory evaluation unresolved (QC/specimen/feature); role preserved.",
            "supporting_evidence": [
                f"Q5 disposition {q5.get('disposition')}; confirmatory {q5.get('overall_confirmatory_status')}",
                "Age conventions + source declaration ACCEPTED; 0 new network bytes",
            ],
            "contradicting_evidence": [
                "Empty donor-ID overlap is not certified specimen independence",
            ],
            "blocks": ["external_predictive_evaluation", "payload_download_this_run"],
        },
    ]


def fit_ledger() -> dict[str, Any]:
    """Enumerate fit/resource arithmetic before protocol freeze."""
    candidates = [
        {
            "id": "rejected_s8_chance_null_relaunch",
            "status": "REJECT",
            "attempted_fits": 119,
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "fits_within_cap": False,
            "null_valid": False,
            "reason": (
                "Prior S8 draft smoke14+screen105=119>60; chance/Bernoulli BA band is "
                "mechanism-mismatched for fitted seven-arm pooled BA (exact-band "
                "correction does not rehabilitate it)."
            ),
        },
        {
            "id": "s7_shaped_5fold_3rho_7arm",
            "status": "REJECT",
            "attempted_fits": 119,
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "fits_within_cap": False,
            "null_valid": "unspecified",
            "reason": "Smoke14+screen105 exceeds synthetic cap 60 before any new calibration.",
        },
        {
            "id": "decision_5fold_2rho_7arm_plus_smoke",
            "status": "REJECT",
            "attempted_fits": 77,
            "breakdown": {"smoke": 7, "screen": 70, "pairing": 0},
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "fits_within_cap": False,
            "reason": "7 arms × 5 folds × 2 rho = 70 plus smoke 7 = 77 > 60.",
        },
        {
            "id": "fitted_ba_montecarlo_joint_calibration",
            "status": "DESIGN_UNRESOLVED",
            "attempted_fits_lower_bound": 20 * 7 * 2,
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "fits_within_cap": False,
            "null_valid": "would_be_if_budgeted",
            "reason": (
                "R≥20 independent complete-pipeline null replicates for a joint "
                "seven-arm fitted BA critical value at even 2 folds is ≥280 fits, "
                "far above 60. Do not shrink joint calibration or relax thresholds "
                "to unlock fits."
            ),
        },
        {
            "id": "selected_pairing_use_fitted_plant_null",
            "status": "SELECT",
            "attempted_fits": 49,
            "breakdown": {
                "smoke_fold0_rho1": 7,
                "screen_rho0": 21,
                "screen_rho1": 21,
                "pairing_interventions": 0,
                "total": 49,
            },
            "design": {
                "arms": list(ARMS),
                "n_arms": 7,
                "n_folds": 3,
                "rhos": [0.0, 1.0],
                "primary_statistic": (
                    "donor log-loss drop under within-donor ATAC shuffle at rho=1 "
                    "(CA); 95% CI lower > 0 for PAIRING_POSITIVE"
                ),
                "fitted_mechanism_null": (
                    "same fitted pipeline and pairing intervention at rho=0 must not "
                    "yield PAIRING_POSITIVE (CI lower <= 0)"
                ),
                "joint_rule": (
                    "all seven arms must complete smoke+screen coverage before "
                    "interpreting pairing; advantage contrast CA−concat is separately "
                    "labelled and non-primary; no chance/Bernoulli BA band"
                ),
                "fold_rationale": (
                    "Prospective F=3 for analytic synthetic software/mechanism "
                    "detectability of a planted pairing signal — not biological power "
                    "and not a post-hoc shrink of a frozen 5-fold disease protocol"
                ),
                "oracle": "analytic / non-learned target confirming planted pairing exists and shuffle destroys it",
                "calibration_decision": (
                    "rho plants and seeds fixed before results; no outcome-guided "
                    "band shopping; disjoint from any optional robustness seed in headroom"
                ),
            },
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
            "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
            "fits_within_cap": True,
            "headroom_fits": 11,
            "null_valid": "prospective_pairing_plant_null_not_chance_ba",
            "reason": (
                "49 ≤ 60 attempts with seven equally supervised arms, fitted rho=0 "
                "pairing null matching the tested pairing mechanism, and no "
                "chance-predictor BA calibration."
            ),
        },
    ]
    selected = next(c for c in candidates if c["status"] == "SELECT")
    unresolved = [c for c in candidates if c["status"] == "DESIGN_UNRESOLVED"]
    return {
        "synthetic_attempt_cap": SYNTHETIC_ATTEMPT_CAP,
        "synthetic_fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "synthetic_artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "workers": 2,
        "torch_threads_per_worker": 2,
        "candidates": candidates,
        "selected_candidate_id": selected["id"],
        "selected_attempted_fits": selected["attempted_fits"],
        "fit_feasibility": "PASS",
        "design_unresolved_paths": [c["id"] for c in unresolved],
        "note": (
            "Fitted BA Monte Carlo joint calibration remains DESIGN_UNRESOLVED under "
            "the cap and is not selected. Selected path uses pairing-plant null instead."
        ),
    }


def build_report(
    *,
    donor_pred_dir: Path,
    q_paths: dict[str, Path],
) -> dict[str, Any]:
    q_reports = {k: _load_json(p) for k, p in q_paths.items()}
    s8 = s8_numerical_correction(donor_pred_dir)
    bottlenecks = rank_bottlenecks(q_reports)
    ledger = fit_ledger()
    chosen = {
        "experiment_id": "S9_analytic_pairing_use_synthetic_20260930",
        "kind": "analytic_synthetic_pairing_use_software_control",
        "plan_ref": "PLAN D3 / Q6–Q7",
        "professor_ref": "July 21 MOM 14:02–17:39 discriminating multimodal benchmark + concat baseline; 03:40 stratified/donor sampling already audited in Q4",
        "what_result_would_change": (
            "PAIRING_POSITIVE under valid rho=0 null + oracle PASS would support that "
            "the CA implementation can use planted within-cell pairing on this "
            "generator/budget; PAIRING_NEGATIVE / oracle-fail / INVALID would direct "
            "repair of representation/optimization before new disease data or pilots."
        ),
        "what_remains_unidentified": [
            "Biological cell-state endpoint (Q2 ENDPOINT_UNRESOLVED)",
            "Regulatory-element adequacy (Q3 REGULATORY_ADEQUACY_UNRESOLVED)",
            "NeMO confirmatory QC/specimen/feature (Q5 UNRESOLVED)",
            "Biological power / min_detectable_delta (POWER_UNESTABLISHED)",
        ],
        "fit_candidate_id": ledger["selected_candidate_id"],
        "attempted_fits": ledger["selected_attempted_fits"],
    }
    rejected = [
        {
            "id": "biological_cell_state_pilot",
            "reason": "Q2 ENDPOINT_UNRESOLVED; Checkpoint A forbids unlocking biological cell-state fits",
        },
        {
            "id": "targeted_sampling_full_ladder_rerun",
            "reason": "Q4 repaired support but endpoint/power gates fail; PLAN forbids full-ladder rerun merely for more cells",
        },
        {
            "id": "atac_regulatory_representation_pilot",
            "reason": "Q3 regulatory adequacy unresolved; structural coverage PASS does not authorize a biological regulatory claim; endpoint still unresolved",
        },
        {
            "id": "external_nemo_acquisition_or_predictive_eval",
            "reason": "Q5 confirmatory UNRESOLVED; payload ~1.54 GiB out of budget; NeMO evaluation role PRESERVED",
        },
        {
            "id": "relaunch_rejected_s8_chance_null",
            "reason": "Prior NO FIT preserved; chance-null mechanism mismatch retained after exact-band correction; budget 119>60",
        },
        {
            "id": "new_real_label_ca_advantage_same_30_donors",
            "reason": "Primary already B_NULL; POWER_UNESTABLISHED; between-model gap small vs practical_margin",
        },
        {
            "id": "paper_only_closeout_as_this_experiments_destination",
            "reason": "Bounded null paper remains valid later writing path but is not the predetermined destination of Q0–Q12",
        },
    ]
    return {
        "task": "Q6",
        "disposition": "EXPERIMENT_SELECTED",
        "fit_feasibility": ledger["fit_feasibility"],
        "date": "2026-09-30",
        "branch": "gnhf/execute-the-p22-data-146414",
        "fits": 0,
        "predictions": None,
        "network_bytes": 0,
        "bottlenecks": bottlenecks,
        "s8_numerical_correction": s8,
        "chosen_experiment": chosen,
        "rejected_alternatives": rejected,
        "fit_ledger": ledger,
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
        ],
        "q_report_dispositions": {
            "q2": q_reports["q2"].get("disposition"),
            "q3": q_reports["q3"].get("disposition"),
            "q3_structural": (q_reports["q3"].get("structural_adequacy") or {}).get("label"),
            "q4": q_reports["q4"].get("disposition"),
            "q4_eligibility": q_reports["q4"].get("eligibility_status"),
            "q5": q_reports["q5"].get("disposition"),
            "q5_confirmatory": q_reports["q5"].get("overall_confirmatory_status"),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    s8 = report["s8_numerical_correction"]
    band = s8["bernoulli_mc"]["exact_central_95"]
    rounded = s8["bernoulli_mc"]["rounded_3dp_central_95"]
    gf = s8["boundary_case"]
    chosen = report["chosen_experiment"]
    ledger = report["fit_ledger"]
    bot_rows = "\n".join(
        f"| `{b['id']}` | `{b['rank_label']}` | {b['summary']} |"
        for b in report["bottlenecks"]
    )
    rej = "\n".join(f"- **{r['id']}**: {r['reason']}" for r in report["rejected_alternatives"])
    cand_rows = "\n".join(
        f"| `{c['id']}` | `{c['status']}` | {c.get('attempted_fits', c.get('attempted_fits_lower_bound'))} | {c['reason']} |"
        for c in ledger["candidates"]
    )
    ba_rows = "\n".join(
        f"| `{a['arm']}` | {a['exact_pooled_ba']:.12f} | {a['inside_exact_band']} | {a['inside_rounded_band_3dp']} |"
        for a in s8["illustrative_claim_with_exact_values"]["arms"]
    )
    return f"""# Q6 — Research decision (one discriminating experiment)

**Disposition:** `{report['disposition']}`  
**Fit feasibility:** `{report['fit_feasibility']}`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependencies:** Q2–Q5 complete; Checkpoint B accepted. No fits, downloads, or package installs.

Machine-readable: [research_decision.json](research_decision.json); [FIT_LEDGER.json](FIT_LEDGER.json).

## Bottleneck ranking

| Bottleneck | Rank | Summary |
|---|---|---|
{bot_rows}

Unresolved flags retained for later stages: {", ".join(f"`{x}`" for x in report["unresolved_flags_retained"])}.

## S8 numerical correction (exact vs rounded)

Prior continuation DECISION illustrated a Bernoulli-0.5 central 95% BA band as ≈`[0.326, 0.674]`. Exact recomputation (10k draws, seed 0, 16/14 labels) yields:

| Quantity | Value |
|---|---|
| Exact central 95% | `[{band[0]:.16f}, {band[1]:.16f}]` |
| Rounded to 3 d.p. | `[{rounded[0]}, {rounded[1]}]` |
| `gated_fusion` exact pooled BA | `{gf['exact_pooled_ba']:.16f}` |
| Equals exact lower quantile? | **{gf['equals_exact_lo']}** |
| Inside exact band? | **{gf['inside_exact_band']}** |
| Inside rounded 3 d.p. band? | **{gf['inside_rounded_band_3dp']}** |

{gf['correction']}

| Arm | Exact pooled ρ=0 BA | Inside exact band | Inside rounded 3 d.p. |
|---|---:|---|---|
{ba_rows}

**Retained:** chance/Bernoulli predictors remain an invalid fitted-model null (mechanism mismatch). Prior S8 **`NO FIT`** unchanged. Primary **`B_NULL`**; S7-v1/v2 **`INVALID`** unchanged.

**Illustrative claim with exact values:** {s8['illustrative_claim_with_exact_values']['retained_conclusion']}

## Chosen experiment

- **ID:** `{chosen['experiment_id']}`
- **Kind:** `{chosen['kind']}`
- **Plan / professor refs:** {chosen['plan_ref']}; {chosen['professor_ref']}
- **Fit candidate:** `{chosen['fit_candidate_id']}` at **{chosen['attempted_fits']}** attempted fits (cap {ledger['synthetic_attempt_cap']})
- **Result that would change direction:** {chosen['what_result_would_change']}
- **Still unidentified:** {"; ".join(chosen['what_remains_unidentified'])}

## Rejected alternatives

{rej}

## Fit / resource ledger

| Candidate | Status | Attempts | Reason |
|---|---|---:|---|
{cand_rows}

Selected design uses F=3 × 7 arms × ρ∈{{0,1}} (smoke 7 + screen 42 = 49 ≤ 60). Fitted-mechanism null is the **ρ=0 pairing plant** under the same training pipeline — not a chance BA band. Fitted BA Monte Carlo joint calibration remains `{ledger['design_unresolved_paths'][0]}` and is not selected.

## Scientific invariants (unchanged)

Primary `{report['scientific_invariants']['primary']}`; S7-v1/v2 `{report['scientific_invariants']['s7_v1']}`; prior S8 `{report['scientific_invariants']['prior_s8']}`; power `{report['scientific_invariants']['power']}`; study `{report['scientific_invariants']['study']}`.

## Next

Q7 may freeze `SYNTHETIC_PROTOCOL` for `{chosen['experiment_id']}` with exact seeds, generator equations, oracle, and the pairing-plant null above. No fits until Checkpoint C.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--donor-predictions", type=Path, default=DEFAULT_DONOR_PREDS)
    parser.add_argument("--q2-json", type=Path, default=DEFAULT_Q_REPORTS["q2"])
    parser.add_argument("--q3-json", type=Path, default=DEFAULT_Q_REPORTS["q3"])
    parser.add_argument("--q4-json", type=Path, default=DEFAULT_Q_REPORTS["q4"])
    parser.add_argument("--q5-json", type=Path, default=DEFAULT_Q_REPORTS["q5"])
    args = parser.parse_args()

    report = build_report(
        donor_pred_dir=args.donor_predictions,
        q_paths={
            "q2": args.q2_json,
            "q3": args.q3_json,
            "q4": args.q4_json,
            "q5": args.q5_json,
        },
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    decision_json = args.out_dir / "research_decision.json"
    decision_md = args.out_dir / "RESEARCH_DECISION.md"
    ledger_json = args.out_dir / "FIT_LEDGER.json"
    decision_json.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    decision_md.write_text(render_markdown(report))
    ledger_json.write_text(json.dumps(report["fit_ledger"], indent=2, allow_nan=False) + "\n")
    print(report["disposition"], report["fit_feasibility"], report["chosen_experiment"]["experiment_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
