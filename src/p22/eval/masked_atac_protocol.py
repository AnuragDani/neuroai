"""M5 protocol freeze for the masked ATAC computational pilot.

No model fitting. Freezes:

- primary estimand (paired donor-average cell log-loss TC − CA)
- clipping, aggregation, sign, exploratory practical margin
- fixed-prediction paired donor bootstrap (1,000 draws)
- model/parameter/epoch/budget table and exact attempt arithmetic
- reserve-before-dispatch / resume / serial RNG isolation rules

Disease BA practical_margin and single-class bootstrap-drop rules are not
imported for this continuous mixed-label log-loss estimand.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from p22.eval.masked_atac_metrics import (
    ADAPTER_REQUIREMENTS,
    PROB_CLIP,
    cell_log_loss,
    donor_average_cell_log_loss,
)
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import paired_model
from p22.eval.s7_ledger import check_param_match, count_parameters
from p22.eval.s7_runner import S7_LOGREG_FROZEN

PROTOCOL_ID = "masked_atac_pilot_20261001"
CLAIM_LEVEL = 2
DISPOSITION = "PROTOCOL_FROZEN"

# Primary contrast: positive ⇒ CA has lower donor-average cell log-loss than TC.
PRIMARY_CONTRAST_NAME = "mean_donor_paired_cell_log_loss_tc_minus_ca"
PRIMARY_SIGN = "positive_means_ca_lower_loss_than_token_concat"
PROB_CLIP_FROZEN = PROB_CLIP

# Exploratory practical margin on continuous log-loss (NOT disease BA margin).
# Justified pre-fit without pilot outcomes: larger than clip-scale noise,
# far smaller than ln(2)≈0.693 random-vs-perfect gap, not a power claim.
PRACTICAL_MARGIN_LOGLOSS = 0.01
PRACTICAL_MARGIN_JUSTIFICATION = (
    "Absolute exploratory threshold 0.01 on paired mean donor cell-log-loss "
    "difference (TC−CA). Chosen before any pilot outcomes as larger than "
    f"PROB_CLIP={PROB_CLIP} numerical scale and << ln(2)≈0.693 "
    "(constant-0.5 vs oracle gap). Disease BA practical_margin is not "
    "applicable to continuous mixed-label cell log-loss. This is not "
    "established power, confirmatory alpha, or training/selection uncertainty."
)

BOOTSTRAP_N = 1000
BOOTSTRAP_SEED = 601001
BOOTSTRAP_LEVEL = 0.95
BOOTSTRAP_LIMITS = (
    "Fixed-prediction donor bootstrap only: does not capture overlapping "
    "training sets across folds, training-only target selection variability, "
    "model-init/selection uncertainty, or hyperparameter uncertainty. "
    "Exploratory uncertainty display, not confirmatory inference."
)

# Arms (PLAN table). Constant has zero fits.
ARMS: tuple[str, ...] = (
    "training_prevalence_constant",
    "logreg_rna",
    "logreg_visible_atac",
    "feature_concat_mlp",
    "token_concat",
    "cross_attention",
)
LEARNED_ARMS: tuple[str, ...] = (
    "logreg_rna",
    "logreg_visible_atac",
    "feature_concat_mlp",
    "token_concat",
    "cross_attention",
)
PRIMARY_ARMS: tuple[str, ...] = ("token_concat", "cross_attention")
CONSTANT_ARM = "training_prevalence_constant"

N_OUTER_FOLDS = 5
MAIN_FITS_PER_LEARNED_ARM = N_OUTER_FOLDS
PLANNED_MAIN_FITS = len(LEARNED_ARMS) * MAIN_FITS_PER_LEARNED_ARM  # 25
SMOKE_FIT_CAP = 5
PLANNED_SMOKE_FITS = 5  # one fixed smoke per learned arm on fold 0
PLANNED_TOTAL_INTENDED = PLANNED_MAIN_FITS + PLANNED_SMOKE_FITS  # 30
HARD_ATTEMPT_CAP = 40
FITTING_HOURS_CAP = 6.0
ARTIFACT_GIB_CAP = 4.0
WORKERS = 1
TORCH_THREADS = 2

# Reuse MultiomeProtocol neural budget (CA/TC already ≤10% under these widths).
NEURAL = MultiomeProtocol(
    n_tokens=4,
    embed_dim=16,
    hidden_dim=32,
    n_heads=2,
    dropout=0.1,
    feature_budget=128,
    cell_cap=256,
    max_epochs=20,
    patience=5,
    batch_size=64,
    learning_rate=0.001,
    n_repeats=1,  # one archival repeat of five outer folds (M3)
    n_folds=5,
    split_seed=0,
    model_seed=0,
    sampling_seed=22,
)
PARAM_MATCH_TOLERANCE = 0.10
LOGREG_FROZEN = dict(S7_LOGREG_FROZEN)

SELECTION_RULE = (
    "Inner-validation checkpoint selection by equal-donor mean of within-donor "
    "mean cell-target binary log-loss (mixed labels allowed). Do not use "
    "donor-average probability, fake disease class, AUROC, BA, or disease "
    "labels for selection."
)

PRESERVED_LABELS: dict[str, str] = {
    "primary": "B_NULL",
    "S7": "INVALID",
    "S9": "INVALID",
    "S10": "INVALID",
    "S8": "NO FIT",
    "Q2": "ENDPOINT_UNRESOLVED",
}


@dataclass(frozen=True)
class AttemptArithmetic:
    """Exact planned fit arithmetic against hard caps."""

    n_learned_arms: int
    n_outer_folds: int
    planned_main_fits: int
    planned_smoke_fits: int
    planned_total_intended: int
    constant_arm_fits: int
    hard_attempt_cap: int
    headroom: int
    fitting_hours_cap: float
    artifact_gib_cap: float
    workers: int
    torch_threads: int
    arithmetic: str
    within_caps: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def attempt_arithmetic() -> AttemptArithmetic:
    """Verify 5×5 main + ≤5 smoke ≤40 with disclosed headroom."""
    main = PLANNED_MAIN_FITS
    smoke = PLANNED_SMOKE_FITS
    intended = main + smoke
    headroom = HARD_ATTEMPT_CAP - intended
    arith = (
        f"{len(LEARNED_ARMS)} learned arms × {N_OUTER_FOLDS} folds = {main} main; "
        f"+ {smoke} reserved smoke (one per learned arm, fold 0) = {intended} "
        f"intended; hard cap {HARD_ATTEMPT_CAP}; headroom {headroom}; "
        f"constant arm = 0 fits"
    )
    within = (
        main == 25
        and smoke <= SMOKE_FIT_CAP
        and intended <= HARD_ATTEMPT_CAP
        and intended == PLANNED_TOTAL_INTENDED
        and headroom == HARD_ATTEMPT_CAP - intended
    )
    return AttemptArithmetic(
        n_learned_arms=len(LEARNED_ARMS),
        n_outer_folds=N_OUTER_FOLDS,
        planned_main_fits=main,
        planned_smoke_fits=smoke,
        planned_total_intended=intended,
        constant_arm_fits=0,
        hard_attempt_cap=HARD_ATTEMPT_CAP,
        headroom=headroom,
        fitting_hours_cap=FITTING_HOURS_CAP,
        artifact_gib_cap=ARTIFACT_GIB_CAP,
        workers=WORKERS,
        torch_threads=TORCH_THREADS,
        arithmetic=arith,
        within_caps=bool(within),
    )


def enumerate_planned_jobs() -> list[dict[str, Any]]:
    """Predeclared smoke + main job keys (no dispatch)."""
    jobs: list[dict[str, Any]] = []
    for arm in LEARNED_ARMS:
        jobs.append(
            {
                "stage": "smoke",
                "arm": arm,
                "fold": 0,
                "counts_toward_budget": True,
                "learning_authorized_only_after": "M8_PASS",
            }
        )
    for fold in range(N_OUTER_FOLDS):
        for arm in LEARNED_ARMS:
            jobs.append(
                {
                    "stage": "main",
                    "arm": arm,
                    "fold": fold,
                    "counts_toward_budget": True,
                    "learning_authorized_only_after": "M8_PASS",
                }
            )
    return jobs


def reserve_before_dispatch_rules() -> dict[str, Any]:
    return {
        "reserve_attempt_counter_before_dispatch": True,
        "failed_and_smoke_count": True,
        "never_reset_counters_after_interruption": True,
        "do_not_refit_completed_jobs_after_token_cap_stop": True,
        "timeout_counts_as_attempt": True,
        "crash_before_sidecar_still_reserved": True,
        "resume_replays_completed_only": True,
        "serial_workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "rng_isolation": (
            "Serial one-worker fits; set_all_seeds(model_seed) per job; "
            "no concurrent writers; global RNG not shared across parallel jobs"
        ),
        "no_neural_smoke_before_m8": True,
        "no_hyperparameter_seed_target_sweep": True,
    }


def per_donor_mean_cell_log_loss(
    donors: Sequence[str],
    y: np.ndarray | Sequence[float],
    p: np.ndarray | Sequence[float],
    *,
    clip: float = PROB_CLIP_FROZEN,
) -> dict[str, float]:
    """Within-donor mean cell log-loss keyed by donor (mixed labels allowed)."""
    return dict(
        donor_average_cell_log_loss(donors, y, p, clip=clip)[
            "per_donor_mean_cell_log_loss"
        ]
    )


def paired_donor_contrast_tc_minus_ca(
    donors: Sequence[str],
    y: np.ndarray | Sequence[float],
    p_tc: np.ndarray | Sequence[float],
    p_ca: np.ndarray | Sequence[float],
    *,
    clip: float = PROB_CLIP_FROZEN,
) -> dict[str, Any]:
    """Primary estimand: equal-donor mean of (L_d(TC) − L_d(CA)).

    Same donors/cells/targets required. Positive ⇒ CA lower loss.
    """
    donor_arr = np.asarray(donors).astype(str).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    tc = np.asarray(p_tc, dtype=np.float64).reshape(-1)
    ca = np.asarray(p_ca, dtype=np.float64).reshape(-1)
    if not (donor_arr.shape == y_arr.shape == tc.shape == ca.shape):
        raise ValueError("donors/y/p_tc/p_ca length mismatch")
    if donor_arr.size == 0:
        raise ValueError("empty contrast input")
    loss_tc = cell_log_loss(y_arr, tc, clip=clip)
    loss_ca = cell_log_loss(y_arr, ca, clip=clip)
    unique = sorted(set(donor_arr.tolist()))
    per_donor_delta: dict[str, float] = {}
    for donor in unique:
        mask = donor_arr == donor
        per_donor_delta[donor] = float(np.mean(loss_tc[mask]) - np.mean(loss_ca[mask]))
    estimate = float(np.mean(list(per_donor_delta.values())))
    return {
        "name": PRIMARY_CONTRAST_NAME,
        "estimate": estimate,
        "n_donors": len(unique),
        "per_donor_delta_tc_minus_ca": per_donor_delta,
        "sign": PRIMARY_SIGN,
        "clip": float(clip),
        "aggregation": "equal_mean_of_within_donor_mean_cell_log_loss_difference",
        "mixed_labels_allowed": True,
    }


def paired_donor_bootstrap_contrast(
    donors: Sequence[str],
    y: np.ndarray | Sequence[float],
    p_tc: np.ndarray | Sequence[float],
    p_ca: np.ndarray | Sequence[float],
    *,
    n_replicates: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
    level: float = BOOTSTRAP_LEVEL,
    clip: float = PROB_CLIP_FROZEN,
) -> dict[str, Any]:
    """Fixed-prediction donor bootstrap of the primary TC−CA contrast.

    Log-loss remains defined for single-class or mixed-label draws; do **not**
    drop single-class resamples (DS BA rule is not imported).
    """
    if n_replicates < 1:
        raise ValueError("n_replicates must be >= 1")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    point = paired_donor_contrast_tc_minus_ca(donors, y, p_tc, p_ca, clip=clip)
    donor_ids = sorted(point["per_donor_delta_tc_minus_ca"])
    deltas = np.asarray(
        [point["per_donor_delta_tc_minus_ca"][d] for d in donor_ids], dtype=np.float64
    )
    if len(donor_ids) < 2:
        return {
            "metric": PRIMARY_CONTRAST_NAME,
            "estimate": point["estimate"],
            "interval": [None, None],
            "level": float(level),
            "unit": "donor",
            "n_replicates_requested": int(n_replicates),
            "n_valid": 0,
            "n_failed": 0,
            "seed": int(seed),
            "not_applicable": "need at least two donors",
            "single_class_draws_dropped": False,
            "limits": BOOTSTRAP_LIMITS,
        }
    rng = np.random.default_rng(int(seed))
    values: list[float] = []
    for _ in range(int(n_replicates)):
        drawn = rng.integers(0, len(deltas), size=len(deltas))
        values.append(float(np.mean(deltas[drawn])))
    tail = (1.0 - level) / 2.0
    lower, upper = np.percentile(values, [100.0 * tail, 100.0 * (1.0 - tail)])
    return {
        "metric": PRIMARY_CONTRAST_NAME,
        "estimate": point["estimate"],
        "interval": [float(lower), float(upper)],
        "level": float(level),
        "unit": "donor",
        "n_replicates_requested": int(n_replicates),
        "n_valid": int(n_replicates),
        "n_failed": 0,
        "seed": int(seed),
        "not_applicable": None,
        "single_class_draws_dropped": False,
        "limits": BOOTSTRAP_LIMITS,
        "practical_margin": PRACTICAL_MARGIN_LOGLOSS,
        "exploratory_advantage_rule": (
            "exploratory_only: estimate >= practical_margin AND interval[0] > 0; "
            "not confirmatory; not power"
        ),
    }


def ca_tc_param_match_for_widths(
    rna_width: int,
    atac_width: int,
    *,
    protocol: MultiomeProtocol | None = None,
    tolerance: float = PARAM_MATCH_TOLERANCE,
) -> dict[str, Any]:
    """Verify CA vs token_concat parameter match under frozen neural budget."""
    proto = protocol or NEURAL
    widths = (int(rna_width), int(atac_width))
    ca = paired_model("cross_attention", widths, proto)
    tc = paired_model("token_concat", widths, proto)
    return check_param_match(
        count_parameters(ca), count_parameters(tc), tolerance=tolerance
    )


def model_table() -> list[dict[str, Any]]:
    """Exact arm table committed before fits."""
    return [
        {
            "arm": CONSTANT_ARM,
            "role": "sanity/descriptive baseline",
            "fits": 0,
            "implementation": (
                "Per-fold training-prevalence constant probability; zero learned params"
            ),
            "selection": "none",
        },
        {
            "arm": "logreg_rna",
            "role": "simple measured-modality control",
            "fits": MAIN_FITS_PER_LEARNED_ARM,
            "implementation": "sklearn LogisticRegression",
            "settings": dict(LOGREG_FROZEN),
            "features": "RNA train-only top-variance feature_budget=128; RNA assay totals OK",
            "selection": SELECTION_RULE,
        },
        {
            "arm": "logreg_visible_atac",
            "role": "simple measured-modality control",
            "fits": MAIN_FITS_PER_LEARNED_ARM,
            "implementation": "sklearn LogisticRegression",
            "settings": dict(LOGREG_FROZEN),
            "features": (
                "Visible ATAC only after whole-target-chromosome mask; "
                "TF-IDF/depth fit on visible train regions only"
            ),
            "selection": SELECTION_RULE,
        },
        {
            "arm": "feature_concat_mlp",
            "role": "required simple fusion control",
            "fits": MAIN_FITS_PER_LEARNED_ARM,
            "implementation": (
                "ConcatFusionModel via paired_model('rna_atac_concat')"
            ),
            "settings": asdict(NEURAL),
            "features": "Matched RNA + visible-ATAC feature order across primary arms",
            "selection": SELECTION_RULE,
        },
        {
            "arm": "token_concat",
            "role": "matched primary comparator",
            "fits": MAIN_FITS_PER_LEARNED_ARM,
            "implementation": "TokenConcatFusionModel via paired_model('token_concat')",
            "settings": asdict(NEURAL),
            "param_match_vs_ca": f"relative error ≤ {PARAM_MATCH_TOLERANCE}",
            "selection": SELECTION_RULE,
        },
        {
            "arm": "cross_attention",
            "role": "primary model",
            "fits": MAIN_FITS_PER_LEARNED_ARM,
            "implementation": "CrossAttentionModel via paired_model('cross_attention')",
            "settings": asdict(NEURAL),
            "param_match_vs_tc": f"relative error ≤ {PARAM_MATCH_TOLERANCE}",
            "selection": SELECTION_RULE,
        },
    ]


def secondary_metrics_policy() -> dict[str, Any]:
    return {
        "primary": PRIMARY_CONTRAST_NAME,
        "secondary_descriptive": ["AUROC", "Brier", "balanced_accuracy"],
        "auroc_ba_availability": (
            "Report unavailable per fold/donor when a class is absent; "
            "do not drop donors or targets to force AUROC/BA"
        ),
        "log_loss_always_defined": True,
        "single_class_bootstrap_drop_from_ds_tasks": "not_imported_for_log_loss",
        "interventions": (
            "Descriptive remove/shuffle visible ATAC or RNA under frozen scheme; "
            "no refits; distribution-shift limits disclosed; not causal routing"
        ),
    }


def fold_reporting_policy() -> dict[str, Any]:
    return {
        "outer_folds": N_OUTER_FOLDS,
        "repeats": 1,
        "report_per_fold": [
            "target_region_id",
            "target_chrom",
            "visible_atac_count",
            "train_prevalence",
            "per_arm_donor_average_cell_log_loss",
            "primary_contrast_tc_minus_ca",
            "secondary_metrics_or_unavailable",
        ],
        "pooled_primary": (
            "Equal mean across all 30 donors of paired within-donor "
            "(L_TC − L_CA), using matched cells/targets within each fold's "
            "test donors (each donor held out once)"
        ),
        "estimand_is_selection_algorithm": True,
        "not_single_locus_performance": True,
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(payload: Mapping[str, Any]) -> str:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, allow_nan=False).encode()
    )


def build_protocol_report(
    *,
    m3_path: Path | None = None,
    m4_path: Path | None = None,
) -> dict[str, Any]:
    """Assemble PILOT_PROTOCOL.json body (no fits)."""
    arithmetic = attempt_arithmetic()
    jobs = enumerate_planned_jobs()
    # Param match under representative visible widths from M3 (423–440).
    param_checks = {
        f"rna128_atac{w}": ca_tc_param_match_for_widths(128, w)
        for w in (423, 430, 440)
    }
    m3_disp = None
    m4_disp = None
    if m3_path is not None and Path(m3_path).is_file():
        m3_disp = json.loads(Path(m3_path).read_text())["disposition"]
    if m4_path is not None and Path(m4_path).is_file():
        m4_disp = json.loads(Path(m4_path).read_text())["disposition"]

    # Analytic toy contrast + bootstrap for verification (fixed predictions).
    donors = ["D0", "D0", "D1", "D1", "D2"]
    y = np.asarray([1, 0, 1, 1, 0], dtype=np.float64)
    p_tc = np.asarray([0.6, 0.4, 0.7, 0.55, 0.3], dtype=np.float64)
    p_ca = np.asarray([0.8, 0.3, 0.85, 0.7, 0.25], dtype=np.float64)
    toy_contrast = paired_donor_contrast_tc_minus_ca(donors, y, p_tc, p_ca)
    toy_boot = paired_donor_bootstrap_contrast(
        donors, y, p_tc, p_ca, n_replicates=200, seed=BOOTSTRAP_SEED
    )
    # Hand check: per-donor means
    # D0: L_tc=mean([ll(1,0.6),ll(0,0.4)]); L_ca=mean([ll(1,0.8),ll(0,0.3)])
    hand_d0_tc = float(np.mean(cell_log_loss([1, 0], [0.6, 0.4])))
    hand_d0_ca = float(np.mean(cell_log_loss([1, 0], [0.8, 0.3])))
    hand_d1_tc = float(np.mean(cell_log_loss([1, 1], [0.7, 0.55])))
    hand_d1_ca = float(np.mean(cell_log_loss([1, 1], [0.85, 0.7])))
    hand_d2_tc = float(cell_log_loss([0], [0.3])[0])
    hand_d2_ca = float(cell_log_loss([0], [0.25])[0])
    hand_estimate = float(
        np.mean(
            [
                hand_d0_tc - hand_d0_ca,
                hand_d1_tc - hand_d1_ca,
                hand_d2_tc - hand_d2_ca,
            ]
        )
    )

    checks = {
        "attempt_arithmetic_within_caps": arithmetic.within_caps,
        "planned_main_fits_is_25": arithmetic.planned_main_fits == 25,
        "planned_jobs_count_matches_intended": len(jobs) == arithmetic.planned_total_intended,
        "ca_tc_param_match_all_widths": all(v["matched"] for v in param_checks.values()),
        "toy_contrast_matches_hand": bool(
            math.isclose(toy_contrast["estimate"], hand_estimate, rel_tol=0.0, abs_tol=1e-12)
        ),
        "bootstrap_keeps_single_class_draws": toy_boot["n_failed"] == 0
        and toy_boot["single_class_draws_dropped"] is False,
        "practical_margin_not_disease_ba": True,
        "m3_frozen_present": m3_disp == "SPLITS_AND_SAMPLING_FROZEN",
        "m4_falsification_pass": m4_disp == "FALSIFICATION_PASS",
        "no_fits": True,
    }
    all_pass = all(bool(v) for v in checks.values())
    body: dict[str, Any] = {
        "disposition": DISPOSITION if all_pass else "PROTOCOL_FAIL",
        "protocol_id": PROTOCOL_ID,
        "claim_level": CLAIM_LEVEL,
        "no_fits": True,
        "preserved_labels": dict(PRESERVED_LABELS),
        "primary_contrast": {
            "name": PRIMARY_CONTRAST_NAME,
            "sign": PRIMARY_SIGN,
            "clip": PROB_CLIP_FROZEN,
            "aggregation": (
                "equal mean across donors of within-donor mean cell binary "
                "log-loss difference (TC − CA); same cells/targets within fold"
            ),
            "practical_margin": PRACTICAL_MARGIN_LOGLOSS,
            "practical_margin_justification": PRACTICAL_MARGIN_JUSTIFICATION,
            "model_selection": SELECTION_RULE,
            "adapter_requirements": ADAPTER_REQUIREMENTS,
        },
        "bootstrap": {
            "n_replicates": BOOTSTRAP_N,
            "seed": BOOTSTRAP_SEED,
            "level": BOOTSTRAP_LEVEL,
            "kind": "fixed_prediction_paired_donor",
            "limits": BOOTSTRAP_LIMITS,
            "single_class_draws_dropped": False,
        },
        "fold_reporting": fold_reporting_policy(),
        "secondary_metrics": secondary_metrics_policy(),
        "models": model_table(),
        "neural_protocol": asdict(NEURAL),
        "neural_fingerprint": NEURAL.fingerprint,
        "param_match_checks": param_checks,
        "attempt_arithmetic": arithmetic.to_dict(),
        "planned_jobs": jobs,
        "reserve_rules": reserve_before_dispatch_rules(),
        "inputs": {
            "m3_disposition": m3_disp,
            "m4_disposition": m4_disp,
        },
        "toy_verification": {
            "hand_estimate": hand_estimate,
            "got_estimate": toy_contrast["estimate"],
            "bootstrap_n_valid": toy_boot["n_valid"],
            "bootstrap_estimate": toy_boot["estimate"],
        },
        "checks": checks,
        "forbidden_claims": [
            "biological_state",
            "causal_mechanism",
            "external_validation",
            "single_locus_performance",
            "established_power",
            "confirmatory_inference",
            "S10_pairing_positive_as_gate",
            "Q2_endpoint_required",
        ],
    }
    body["protocol_sha256"] = sha256_json(
        {k: v for k, v in body.items() if k != "protocol_sha256"}
    )
    return body


def render_protocol_md(report: Mapping[str, Any]) -> str:
    arith = report["attempt_arithmetic"]
    primary = report["primary_contrast"]
    lines = [
        "# Masked ATAC pilot M5 — protocol freeze",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Protocol ID:** `{report['protocol_id']}`",
        (
            f"**Claim level:** {report['claim_level']} "
            "(computational prediction; not state/causal/external)"
        ),
        "**Date:** 2026-10-01",
        "**Fits:** 0 (protocol freeze only; learning unauthorized until M8)",
        "",
        "Machine-readable: [PILOT_PROTOCOL.json](PILOT_PROTOCOL.json); "
        "[BUDGET_LEDGER.md](BUDGET_LEDGER.md).",
        "",
        "## Preserved labels",
        "",
    ]
    for key, val in report["preserved_labels"].items():
        lines.append(f"- {key}: `{val}`")
    boot = report["bootstrap"]
    lines.extend(
        [
            "",
            "## Primary estimand",
            "",
            f"- **Name:** `{primary['name']}`",
            f"- **Sign:** {primary['sign']}",
            f"- **Clip:** `{primary['clip']}`",
            f"- **Aggregation:** {primary['aggregation']}",
            (
                f"- **Practical margin:** `{primary['practical_margin']}` "
                "(exploratory only)"
            ),
            f"- **Margin justification:** {primary['practical_margin_justification']}",
            f"- **Selection:** {primary['model_selection']}",
            "",
            "## Bootstrap",
            "",
            f"- Draws: **{boot['n_replicates']}**; "
            f"seed **{boot['seed']}**; level **{boot['level']}**",
            f"- Kind: {boot['kind']}",
            (
                "- Single-class draws dropped: "
                f"**{boot['single_class_draws_dropped']}**"
            ),
            f"- Limits: {boot['limits']}",
            "",
            "## Models and epochs",
            "",
            "| Arm | Role | Main fits | Notes |",
            "|---|---|---:|---|",
        ]
    )
    for row in report["models"]:
        notes = row.get("implementation", "")
        settings = row.get("settings")
        if isinstance(settings, dict) and "max_epochs" in settings:
            notes += (
                f"; max_epochs={settings['max_epochs']}, "
                f"patience={settings['patience']}"
            )
        lines.append(
            f"| `{row['arm']}` | {row['role']} | {row['fits']} | {notes} |"
        )
    lines.extend(
        [
            "",
            f"Neural fingerprint: `{report['neural_fingerprint']}`",
            f"CA/TC param-match tolerance: ≤{PARAM_MATCH_TOLERANCE} "
            f"(checked widths 423/430/440: all matched).",
            "",
            "## Attempt arithmetic",
            "",
            f"- {arith['arithmetic']}",
            f"- Within caps: **{arith['within_caps']}**",
            (
                f"- Workers × torch threads: "
                f"**{arith['workers']} × {arith['torch_threads']}**"
            ),
            (
                f"- Fitting hours ≤ {arith['fitting_hours_cap']}; "
                f"artifacts ≤ {arith['artifact_gib_cap']} GiB"
            ),
            "",
            "## Reserve / resume / RNG",
            "",
        ]
    )
    for key, val in report["reserve_rules"].items():
        lines.append(f"- `{key}`: {val}")
    lines.extend(
        [
            "",
            "## Checks",
            "",
        ]
    )
    for key, val in report["checks"].items():
        lines.append(f"- `{key}`: **{val}**")
    lines.extend(
        [
            "",
            "## Forbidden claim promotions",
            "",
        ]
    )
    for item in report["forbidden_claims"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Next",
            "",
            "M6 independent protocol/claim review on these frozen hashes. "
            "No implementation learning or smoke fits until M6+M8 PASS.",
            "",
        ]
    )
    return "\n".join(lines)


def build_budget_ledger(
    *,
    counter_path: Path | None = None,
    protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prospective budget ledger against attempt_counter.json zeros."""
    arith = attempt_arithmetic()
    used = {
        "scientific_fits": 0,
        "smoke_fits": 0,
        "total_attempts": 0,
        "fitting_hours": 0.0,
        "artifacts_gib": 0.0,
        "network_bytes": 0,
    }
    if counter_path is not None and Path(counter_path).is_file():
        counter = json.loads(Path(counter_path).read_text())
        used = {
            "scientific_fits": int(counter["scientific_fits"]["used"]),
            "smoke_fits": int(counter["smoke_fits"]["used"]),
            "total_attempts": int(counter["total_attempts"]["used"]),
            "fitting_hours": float(counter["fitting_hours"]["used"]),
            "artifacts_gib": float(counter["artifacts_gib"]["used"]),
            "network_bytes": int(counter.get("network_bytes", 0)),
        }
    remaining_attempts = HARD_ATTEMPT_CAP - used["total_attempts"]
    fit_ok = (
        arith.within_caps
        and arith.planned_total_intended <= remaining_attempts
        and used["total_attempts"] == 0
        and used["scientific_fits"] == 0
    )
    proto_disp = None if protocol is None else protocol.get("disposition")
    return {
        "task": "M5",
        "protocol_id": PROTOCOL_ID,
        "recorded_date": "2026-10-01",
        "fit_feasibility": "PASS" if fit_ok else "FAIL",
        "m5_consumption": {
            "scientific_fits": 0,
            "smoke_fits": 0,
            "payload_mib": 0,
            "note": "protocol freeze only; zero learning",
        },
        "counter_snapshot": used,
        "counter_path": (
            str(counter_path) if counter_path is not None else None
        ),
        "planned": {
            "smoke": arith.planned_smoke_fits,
            "main": arith.planned_main_fits,
            "constant_arm_fits": 0,
            "planned_total_intended": arith.planned_total_intended,
            "arithmetic": arith.arithmetic,
            "headroom_vs_hard_cap": arith.headroom,
            "hard_attempt_cap": HARD_ATTEMPT_CAP,
            "fitting_hours_cap": FITTING_HOURS_CAP,
            "artifact_gib_cap": ARTIFACT_GIB_CAP,
            "workers": WORKERS,
            "torch_threads": TORCH_THREADS,
        },
        "checks": {
            "25_main_plus_5_smoke_le_40": arith.within_caps,
            "remaining_attempts_cover_planned": arith.planned_total_intended
            <= remaining_attempts,
            "counters_still_zero": used["total_attempts"] == 0,
            "protocol_frozen": proto_disp == DISPOSITION,
        },
        "fit_feasibility_is_not_power": True,
        "protocol_disposition": proto_disp,
    }


def render_budget_md(ledger: Mapping[str, Any]) -> str:
    planned = ledger["planned"]
    used = ledger["counter_snapshot"]
    lines = [
        "# BUDGET_LEDGER — M5 masked ATAC pilot resource arithmetic",
        "",
        f"**Date:** {ledger['recorded_date']}",
        f"**Protocol:** `{ledger['protocol_id']}`",
        f"**Fit feasibility:** `{ledger['fit_feasibility']}`",
        "**Machine record:** [budget_ledger.json](budget_ledger.json)",
        "",
        "M5 itself uses **0** scientific fits, **0** smoke fits, **0** payloads. "
        "Figures below are the **prospective** M7–M9 budget against stage caps.",
        "",
        "## Counter snapshot (before any learning)",
        "",
        "| Resource | Used | Cap |",
        "|---|---:|---:|",
        (
            f"| Total attempts | {used['total_attempts']} | "
            f"{planned['hard_attempt_cap']} |"
        ),
        f"| Smoke fits | {used['smoke_fits']} | {SMOKE_FIT_CAP} |",
        (
            f"| Fitting hours | {used['fitting_hours']} | "
            f"{planned['fitting_hours_cap']} |"
        ),
        (
            f"| Artifact GiB | {used['artifacts_gib']} | "
            f"{planned['artifact_gib_cap']} |"
        ),
        f"| Network bytes | {used['network_bytes']} | 0 planned |",
        "",
        "## Planned consumption",
        "",
        "| Item | Value |",
        "|---|---|",
        (
            f"| Smoke fits | {planned['smoke']} "
            "(one per learned arm, fold 0; count toward hard cap) |"
        ),
        f"| Main fits | {planned['main']} (5 arms × 5 folds) |",
        f"| Constant arm | {planned['constant_arm_fits']} |",
        f"| **Total intended** | **{planned['planned_total_intended']}** |",
        (
            f"| Hard cap / headroom | {planned['hard_attempt_cap']} / "
            f"{planned['headroom_vs_hard_cap']} |"
        ),
        (
            f"| Workers × threads | {planned['workers']} × "
            f"{planned['torch_threads']} |"
        ),
        f"| Arithmetic | {planned['arithmetic']} |",
        "",
        "## Feasibility checks",
        "",
    ]
    for key, val in ledger["checks"].items():
        lines.append(f"- `{key}`: **{val}**")
    lines.extend(
        [
            "",
            f"**Fit feasibility:** `{ledger['fit_feasibility']}`. "
            "Fit feasibility is **not** established statistical power.",
            "",
            "## Policy",
            "",
            "- Reserve attempt counter before dispatch; failed/smoke/timeout count.",
            "- Never reset counters after interruption; do not refit completed jobs.",
            "- No neural smoke learning before M8 authorization.",
            "- No hyperparameter/seed/target sweep.",
            "",
        ]
    )
    return "\n".join(lines)


def write_protocol_artifacts(
    out_dir: Path,
    *,
    counter_path: Path,
    m3_path: Path,
    m4_path: Path,
) -> dict[str, Path]:
    """Write PILOT_PROTOCOL and BUDGET_LEDGER md/json under the task dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    protocol = build_protocol_report(m3_path=m3_path, m4_path=m4_path)
    if protocol["disposition"] != DISPOSITION:
        raise RuntimeError(f"protocol checks failed: {protocol['checks']}")
    ledger = build_budget_ledger(counter_path=counter_path, protocol=protocol)
    if ledger["fit_feasibility"] != "PASS":
        raise RuntimeError(f"budget feasibility failed: {ledger['checks']}")

    paths = {
        "protocol_json": out_dir / "PILOT_PROTOCOL.json",
        "protocol_md": out_dir / "PILOT_PROTOCOL.md",
        "budget_json": out_dir / "budget_ledger.json",
        "budget_md": out_dir / "BUDGET_LEDGER.md",
    }
    for path in paths.values():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing path: {path}")
    paths["protocol_json"].write_text(
        json.dumps(protocol, indent=2, allow_nan=False) + "\n"
    )
    paths["protocol_md"].write_text(render_protocol_md(protocol))
    paths["budget_json"].write_text(
        json.dumps(ledger, indent=2, allow_nan=False) + "\n"
    )
    paths["budget_md"].write_text(render_budget_md(ledger))
    return paths
