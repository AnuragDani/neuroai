"""S10 corrected-null pairing-use generator and dry-run helpers.

Protocol ``S10_corrected_null_pairing_use_20261001`` reuses S9 arms/splits/
oracle scoring but replaces exact ρ=0 orthogonalization with independent
centre-scaled Gaussians so within-donor ATAC shuffle remains exchangeable.
Does not modify immutable ``s9_analytic`` or historical S9 INVALID.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_ledger import make_fit_id, sha256_file
from p22.eval.s9_analytic import (
    ARMS,
    CELLS_PER_DONOR,
    LOGREG_ARMS,
    N_ARMS,
    N_DONORS,
    N_FEATURES,
    N_FOLDS,
    N_PLANTED_CHANNELS,
    NEURAL_ARMS,
    ORACLE_BA_CHANCE_MAX,
    ORACLE_BA_RHO1_MIN,
    PAIRING_SHUFFLE_SEEDS,
    SCREEN_FITS,
    SMOKE_FITS,
    allocate_s9_folds,
    assert_donor_isolation,
    assign_donor_labels,
    build_param_match_record,
    check_finite_gradients,
    check_state_dict_reload_equality,
    donor_ids,
    fold_row_indices,
    oracle_balanced_accuracy,
    oracle_donor_scores,
    permute_atac_within_donor,
    s9_protocol_from_frozen,
)
from p22.eval.s9_analytic import (
    _centre_scale as _centre_scale,
)
from p22.eval.s9_analytic import (
    _stable_rng as _stable_rng,
)
from p22.models.fusion import VIEW_A, VIEW_B

PROTOCOL_ID = "S10_corrected_null_pairing_use_20261001"
PROTOCOL_KIND = "corrected_software_null_reproducibility_test"
NULL_CANDIDATE_ID = "independent_gaussian_rho0_within_donor_shuffle_20261001"
CLAIM_LEVEL = 1

# Prospective decision seeds — disjoint from S9 decision/headroom and R2
# diagnostic generator panels. Not selected from S9/diagnostic outcomes.
DECISION_GENERATOR_SEED = 9301
DECISION_SPLIT_SEED = 17
DECISION_MODEL_SEED = 9301
HEADROOM_GENERATOR_SEEDS = (9401, 9402, 9403)
# Preregistered R7 generator-only exchangeability panel (≤64; within remaining).
R7_EXCHANGEABILITY_SEEDS = tuple(range(5301, 5317))  # 16

TOTAL_FITS = SMOKE_FITS + SCREEN_FITS  # 49
SCIENTIFIC_ATTEMPT_CAP = 90
SYNTHETIC_FITTING_HOURS_CAP = 6.0
SYNTHETIC_ARTIFACT_GIB_CAP = 4.0
WORKERS = 1
TORCH_THREADS = 2

ALLOWED_RAW_ROOT = (
    "reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/"
)
REFUSED_RAW_ROOT_MARKERS = (
    "nn_s7_covariance_20260929",
    "nn_s7_covariance_split_v2_20260929",
    "nn_s8_",
    "nn_s9_analytic_pairing_20260930",
)

_VAR_EPS = 1e-12
# Panel gate uses mean ratio (R2 reported ≈1.003); single-seed ratios have
# finite-sample noise wider than the mean band.
_EXCHANGEABILITY_MEAN_LO = 0.95
_EXCHANGEABILITY_MEAN_HI = 1.05
_EXCHANGEABILITY_SEED_LO = 0.75
_EXCHANGEABILITY_SEED_HI = 1.30
_EXCHANGEABILITY_ORIG_ABS_MIN = 0.05


class S10Refusal(ValueError):
    """Explicit refusal for mismatched S10 protocol/output/identity contracts."""


def _digest(*parts: object) -> str:
    return hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def generate_corrected_arrays(
    labels: dict[str, int],
    *,
    rho: float,
    generator_seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Independent-Gaussian planted channels without exact orthogonalization.

    ATAC planted = sign(y)*rho*z + sqrt(1-rho^2)*w where z,w are independently
    centre-scaled Gaussians (no w⊥z projection). At rho=0 this yields an
    exchangeable within-donor ATAC shuffle null (R2 candidate).
    """
    rho = float(rho)
    if not (-1.0 <= rho <= 1.0):
        raise ValueError(f"rho must be in [-1, 1], got {rho}")
    sign_scale = math.sqrt(max(0.0, 1.0 - rho * rho))
    n_cells = N_DONORS * CELLS_PER_DONOR
    rna = np.zeros((n_cells, N_FEATURES), dtype=np.float64)
    atac = np.zeros((n_cells, N_FEATURES), dtype=np.float64)
    donor_col = np.empty(n_cells, dtype=object)
    label_col = np.empty(n_cells, dtype=np.int64)
    cell_ids = np.empty(n_cells, dtype=object)
    row = 0
    for donor in donor_ids():
        y_d = int(labels[donor])
        sign = 2 * y_d - 1
        for c in range(CELLS_PER_DONOR):
            donor_col[row] = donor
            label_col[row] = y_d
            cell_ids[row] = f"{donor}__cell_{c:02d}"
            row += 1
        rows = np.flatnonzero(donor_col == donor)
        for channel in range(N_PLANTED_CHANNELS):
            z = _centre_scale(
                _stable_rng(generator_seed, donor, channel, "z_s10").normal(
                    size=CELLS_PER_DONOR
                )
            )
            # Corrected null: independent centre-scaled w — NO orthogonalize.
            w = _centre_scale(
                _stable_rng(generator_seed, donor, channel, "w_s10").normal(
                    size=CELLS_PER_DONOR
                )
            )
            rna[rows, channel] = z
            atac[rows, channel] = sign * rho * z + sign_scale * w
        donor_shift = _stable_rng(generator_seed, donor, "nuisance_shift_s10").normal(
            size=N_FEATURES - N_PLANTED_CHANNELS
        )
        for j, channel in enumerate(range(N_PLANTED_CHANNELS, N_FEATURES)):
            rna[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "rna_n_s10").normal(
                    size=CELLS_PER_DONOR
                )
                + 0.5 * donor_shift[j]
            )
            atac[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "atac_n_s10").normal(
                    size=CELLS_PER_DONOR
                )
                + 0.5 * donor_shift[j]
            )
    return rna, atac, donor_col, label_col, cell_ids


def _donor_channel_product_means(
    rna: np.ndarray, atac: np.ndarray, donor: np.ndarray
) -> np.ndarray:
    means: list[float] = []
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        for channel in range(N_PLANTED_CHANNELS):
            means.append(
                float(np.mean(rna[idx, channel] * atac[idx, channel]))
            )
    return np.asarray(means, dtype=np.float64)


def exchangeability_ratio_for_seed(
    labels: dict[str, int],
    *,
    generator_seed: int,
    shuffle_seeds: Sequence[int] = PAIRING_SHUFFLE_SEEDS,
) -> dict[str, float]:
    """Mean-|product| shuffle/original ratio under corrected ρ=0 generator."""
    rna, atac, donor, _, _ = generate_corrected_arrays(
        labels, rho=0.0, generator_seed=int(generator_seed)
    )
    orig = _donor_channel_product_means(rna, atac, donor)
    orig_mean_abs = float(np.mean(np.abs(orig)))
    shuffled_abs: list[float] = []
    for seed in shuffle_seeds:
        shuf = permute_atac_within_donor(atac, donor, seed=int(seed))
        means = _donor_channel_product_means(rna, shuf, donor)
        shuffled_abs.append(float(np.mean(np.abs(means))))
    shuf_mean_abs = float(np.mean(shuffled_abs))
    ratio = shuf_mean_abs / orig_mean_abs if orig_mean_abs > _VAR_EPS else float("inf")
    return {
        "generator_seed": float(generator_seed),
        "original_mean_abs": orig_mean_abs,
        "shuffled_mean_abs": shuf_mean_abs,
        "ratio": ratio,
    }


def verify_exchangeability_panel(
    labels: dict[str, int],
    *,
    seeds: Sequence[int] = R7_EXCHANGEABILITY_SEEDS,
) -> dict[str, Any]:
    """Preregistered generator-only panel; counts toward stage generator budget."""
    rows = [
        exchangeability_ratio_for_seed(labels, generator_seed=int(s)) for s in seeds
    ]
    ratios = [float(r["ratio"]) for r in rows]
    orig_abs = [float(r["original_mean_abs"]) for r in rows]
    mean_ratio = float(np.mean(ratios))
    mean_orig_abs = float(np.mean(orig_abs))
    seeds_in_band = all(
        _EXCHANGEABILITY_SEED_LO <= r <= _EXCHANGEABILITY_SEED_HI for r in ratios
    )
    mean_in_band = _EXCHANGEABILITY_MEAN_LO <= mean_ratio <= _EXCHANGEABILITY_MEAN_HI
    not_machine_zero = mean_orig_abs >= _EXCHANGEABILITY_ORIG_ABS_MIN
    return {
        "n_seeds": len(seeds),
        "seeds": list(int(s) for s in seeds),
        "mean_ratio": mean_ratio,
        "min_ratio": float(min(ratios)),
        "max_ratio": float(max(ratios)),
        "mean_original_mean_abs": mean_orig_abs,
        "ratio_within_band": mean_in_band and seeds_in_band and not_machine_zero,
        "mean_band": [_EXCHANGEABILITY_MEAN_LO, _EXCHANGEABILITY_MEAN_HI],
        "seed_band": [_EXCHANGEABILITY_SEED_LO, _EXCHANGEABILITY_SEED_HI],
        "band": [_EXCHANGEABILITY_MEAN_LO, _EXCHANGEABILITY_MEAN_HI],
        "per_seed": rows,
        "generator_draws": len(seeds),
    }


def verify_oracle_invariants(
    labels: dict[str, int], *, generator_seed: int = DECISION_GENERATOR_SEED
) -> dict[str, Any]:
    """Analytic oracle PASS/FAIL under corrected generator (0 learned fits)."""
    rna1, atac1, donor, _lab, _cells = generate_corrected_arrays(
        labels, rho=1.0, generator_seed=generator_seed
    )
    rna0, atac0, donor0, _, _ = generate_corrected_arrays(
        labels, rho=0.0, generator_seed=generator_seed
    )
    if not np.array_equal(donor, donor0):
        raise RuntimeError("donor column mismatch across rho")
    if not np.allclose(rna1[:, :N_PLANTED_CHANNELS], rna0[:, :N_PLANTED_CHANNELS]):
        raise RuntimeError("planted RNA must be rho-invariant")
    scores_rho1 = oracle_donor_scores(rna1, atac1, donor)
    scores_rho0 = oracle_donor_scores(rna0, atac0, donor)
    ba_rho1 = oracle_balanced_accuracy(scores_rho1, labels)
    ba_rho0 = oracle_balanced_accuracy(scores_rho0, labels)
    shuffled = permute_atac_within_donor(atac1, donor, seed=PAIRING_SHUFFLE_SEEDS[0])
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        orig = np.sort(atac1[idx], axis=0)
        shuf = np.sort(shuffled[idx], axis=0)
        if not np.allclose(orig, shuf):
            raise RuntimeError(f"shuffle failed marginal preservation for {name}")
    ba_rho1_shuffled = oracle_balanced_accuracy(
        oracle_donor_scores(rna1, shuffled, donor), labels
    )
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        sign = 2 * labels[str(name)] - 1
        if not np.allclose(
            atac1[idx, :N_PLANTED_CHANNELS],
            sign * rna1[idx, :N_PLANTED_CHANNELS],
        ):
            raise RuntimeError(f"rho=1 ATAC != signed RNA for {name}")
    # Corrected null must NOT force exact orthogonality at rho=0.
    products0 = _donor_channel_product_means(rna0, atac0, donor)
    max_abs_rho0 = float(np.max(np.abs(products0)))
    checks = {
        "rho1_oracle_ba": ba_rho1,
        "rho0_oracle_ba": ba_rho0,
        "rho1_shuffled_oracle_ba": ba_rho1_shuffled,
        "rho1_oracle_detects_pairing": ba_rho1 >= ORACLE_BA_RHO1_MIN,
        "rho0_oracle_near_chance": ba_rho0 <= ORACLE_BA_CHANCE_MAX,
        "shuffle_destroys_rho1_oracle": ba_rho1_shuffled <= ORACLE_BA_CHANCE_MAX,
        "planted_rna_rho_invariant": True,
        "shuffle_preserves_within_donor_marginals": True,
        "rho1_atac_equals_signed_rna": True,
        "rho0_not_exact_orthogonal": max_abs_rho0 > 1e-6,
        "rho0_max_abs_product_mean": max_abs_rho0,
    }
    checks["oracle_gate"] = (
        "PASS"
        if (
            checks["rho1_oracle_detects_pairing"]
            and checks["rho0_oracle_near_chance"]
            and checks["shuffle_destroys_rho1_oracle"]
            and checks["rho0_not_exact_orthogonal"]
        )
        else "FAIL"
    )
    return checks


def allocate_s10_folds(
    labels: dict[str, int],
    *,
    split_seed: int = DECISION_SPLIT_SEED,
    generator_seed: int = DECISION_GENERATOR_SEED,
) -> dict[str, Any]:
    """Reuse S9 class-quota allocator with S10 prospective seeds."""
    return allocate_s9_folds(
        labels, split_seed=split_seed, generator_seed=generator_seed
    )


def s10_protocol_from_frozen(
    training: Mapping[str, Any] | None = None,
) -> MultiomeProtocol:
    """Build MultiomeProtocol from frozen S10 training budget."""
    proto = s9_protocol_from_frozen(training)
    # Override seeds to S10 prospective decision seeds.
    return MultiomeProtocol(
        n_tokens=proto.n_tokens,
        embed_dim=proto.embed_dim,
        hidden_dim=proto.hidden_dim,
        n_heads=proto.n_heads,
        dropout=proto.dropout,
        feature_budget=proto.feature_budget,
        cell_cap=proto.cell_cap,
        max_epochs=proto.max_epochs,
        patience=proto.patience,
        batch_size=proto.batch_size,
        learning_rate=proto.learning_rate,
        n_repeats=proto.n_repeats,
        n_folds=N_FOLDS,
        split_seed=DECISION_SPLIT_SEED,
        model_seed=DECISION_MODEL_SEED,
        sampling_seed=proto.sampling_seed,
    )


def enumerate_s10_jobs() -> list[dict[str, Any]]:
    """Predeclared smoke (7) + screen (42) jobs; no execution."""
    jobs: list[dict[str, Any]] = []
    for model in ARMS:
        fit_id = make_fit_id(
            "smoke", 1.0, DECISION_GENERATOR_SEED, 0, model
        )
        jobs.append(
            {
                "fit_id": fit_id,
                "stage": "smoke",
                "rho": 1.0,
                "generator_seed": DECISION_GENERATOR_SEED,
                "fold": 0,
                "model": model,
            }
        )
    for rho in (0.0, 1.0):
        for fold in range(N_FOLDS):
            for model in ARMS:
                fit_id = make_fit_id(
                    "screen", rho, DECISION_GENERATOR_SEED, fold, model
                )
                jobs.append(
                    {
                        "fit_id": fit_id,
                        "stage": "screen",
                        "rho": float(rho),
                        "generator_seed": DECISION_GENERATOR_SEED,
                        "fold": int(fold),
                        "model": model,
                    }
                )
    return jobs


def recompute_fit_arithmetic() -> dict[str, Any]:
    smoke = SMOKE_FITS
    screen0 = N_FOLDS * N_ARMS
    screen1 = N_FOLDS * N_ARMS
    total = smoke + screen0 + screen1
    if total != TOTAL_FITS:
        raise RuntimeError(f"fit total mismatch: {total} vs {TOTAL_FITS}")
    if total > SCIENTIFIC_ATTEMPT_CAP:
        raise RuntimeError(f"fits {total} exceed cap {SCIENTIFIC_ATTEMPT_CAP}")
    if DECISION_GENERATOR_SEED in HEADROOM_GENERATOR_SEEDS:
        raise RuntimeError("headroom seeds must be disjoint from decision seed")
    forbidden = {
        9001,
        9101,
        9102,
        9103,
        *range(5101, 5165),
        *range(5201, 5217),
    }
    if DECISION_GENERATOR_SEED in forbidden:
        raise RuntimeError("decision seed collides with S9/R2 reserved set")
    return {
        "smoke_fold0_rho1": smoke,
        "screen_rho0": screen0,
        "screen_rho1": screen1,
        "pairing_interventions_as_fits": 0,
        "total_attempted_fits": total,
        "cap": SCIENTIFIC_ATTEMPT_CAP,
        "fits_within_cap": total <= SCIENTIFIC_ATTEMPT_CAP,
        "headroom_fits": SCIENTIFIC_ATTEMPT_CAP - total,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "decision_generator_seed": DECISION_GENERATOR_SEED,
        "decision_split_seed": DECISION_SPLIT_SEED,
        "decision_model_seed": DECISION_MODEL_SEED,
        "headroom_generator_seeds_disjoint": list(HEADROOM_GENERATOR_SEEDS),
        "pairing_shuffle_seeds_not_counted_as_fits": list(PAIRING_SHUFFLE_SEEDS),
        "r7_exchangeability_seeds": list(R7_EXCHANGEABILITY_SEEDS),
        "note": (
            "Smoke counts as scientific (diagnostic allowance exhausted). "
            "Pairing shuffle interventions are not fits. Serial workers=1 default."
        ),
    }


def refuse_mismatched_protocol_hash(
    expected_sha256: str, actual_sha256: str, *, label: str = "protocol"
) -> None:
    if expected_sha256 != actual_sha256:
        raise S10Refusal(
            f"{label} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )


def refuse_if_not_allowed_raw_root(raw_root: str | Path) -> None:
    text = str(raw_root).replace("\\", "/")
    for marker in REFUSED_RAW_ROOT_MARKERS:
        if marker in text:
            raise S10Refusal(
                f"refused raw root overlaps forbidden marker {marker!r}: {text!r}"
            )
    if "s10_corrected_null_pairing_20261001" not in text:
        raise S10Refusal(
            "raw root must contain s10_corrected_null_pairing_20261001; "
            f"got {text!r}"
        )


def refuse_unreviewed_scientific_fits() -> None:
    raise S10Refusal(
        "scientific fits require R8 independent full-path review PASS "
        "(Checkpoint C) before dispatch; self-certification is not sufficient"
    )


def refuse_s9_orthogonal_generator() -> None:
    """Guard: S10 must not call the frozen orthogonal S9 rho=0 path for null."""
    raise S10Refusal(
        "S10 corrected null forbids S9 exact-orthogonal rho=0 generator; "
        "use generate_corrected_arrays"
    )


def build_split_manifest(
    labels: dict[str, int] | None = None,
) -> dict[str, Any]:
    labels = labels or assign_donor_labels(DECISION_GENERATOR_SEED)
    split = allocate_s10_folds(labels)
    return {
        "protocol_id": PROTOCOL_ID,
        "split_method": "s9-class-quota-sha256",
        "split_seed": DECISION_SPLIT_SEED,
        "generator_seed": DECISION_GENERATOR_SEED,
        "n_folds": N_FOLDS,
        "n_donors": N_DONORS,
        "class_balance": {"0": 12, "1": 12},
        "outer_quotas": {"class_0": [4, 4, 4], "class_1": [4, 4, 4]},
        "inner_val_per_class": 2,
        "donor_labels": split["donor_labels"],
        "folds": split["folds"],
        "note": (
            "Prospective S10 seeds; allocator reused from s9_analytic.allocate_s9_folds. "
            "Not selected from S9 or R2 diagnostic outcomes."
        ),
    }


def run_r7_dry_run(
    *,
    protocol_path: Path | None = None,
    split_path: Path | None = None,
) -> dict[str, Any]:
    """Verify corrected generator, oracle, exchangeability, factory, refusals.

    Research fits are not executed. Trainability-with-learning is refused.
    """
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    split_manifest = build_split_manifest(labels)
    if split_path is not None and Path(split_path).is_file():
        frozen = json.loads(Path(split_path).read_text(encoding="utf-8"))
        if frozen["donor_labels"] != split_manifest["donor_labels"]:
            raise S10Refusal("live split labels diverge from S10_SPLIT_MANIFEST")
        for fold_key, fold in frozen["folds"].items():
            if split_manifest["folds"][fold_key] != fold:
                raise S10Refusal(
                    f"live split fold {fold_key} diverges from S10_SPLIT_MANIFEST"
                )
        split_sha = sha256_file(split_path)
    else:
        split_sha = None

    protocol_sha = sha256_file(protocol_path) if protocol_path else None
    if protocol_path is not None:
        protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
        if protocol.get("protocol_id") != PROTOCOL_ID:
            raise S10Refusal(f"unexpected protocol_id {protocol.get('protocol_id')!r}")

    fit_arithmetic = recompute_fit_arithmetic()
    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise RuntimeError(f"oracle gate FAIL: {oracle}")

    exchange = verify_exchangeability_panel(labels)
    if not exchange["ratio_within_band"]:
        raise RuntimeError(f"exchangeability panel FAIL: {exchange}")

    jobs = enumerate_s10_jobs()
    if len(jobs) != TOTAL_FITS:
        raise RuntimeError(f"job enumeration {len(jobs)} != {TOTAL_FITS}")
    if len({j["fit_id"] for j in jobs}) != TOTAL_FITS:
        raise RuntimeError("duplicate fit_ids in enumeration")

    rna, atac, donor_col, label_col, _cells = generate_corrected_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    views = {VIEW_A: rna.astype(np.float32), VIEW_B: atac.astype(np.float32)}
    fold0 = split_manifest["folds"]["0"]
    positions = fold_row_indices(donor_col, fold0)
    assert_donor_isolation(positions, donor_col)

    shuffled = permute_atac_within_donor(atac, donor_col, seed=PAIRING_SHUFFLE_SEEDS[0])
    for name in sorted(set(donor_col.tolist()), key=str):
        idx = np.flatnonzero(donor_col == name)
        if not np.allclose(np.sort(atac[idx], axis=0), np.sort(shuffled[idx], axis=0)):
            raise RuntimeError(f"marginal fail {name}")

    proto = s10_protocol_from_frozen()
    param_match = build_param_match_record(proto)
    if not param_match["pass"]:
        raise RuntimeError(f"CA/TC param match FAIL: {param_match}")

    gradients: dict[str, Any] = {}
    reloads: dict[str, Any] = {}
    for arm in NEURAL_ARMS:
        gradients[arm] = check_finite_gradients(arm, views, label_col, proto)
        if not gradients[arm]["finite"]:
            raise RuntimeError(f"non-finite gradients for {arm}")
        reloads[arm] = check_state_dict_reload_equality(arm, views, proto)
        if not reloads[arm]["passed"]:
            raise RuntimeError(f"reload mismatch for {arm}")

    refusals = {
        "hash_mismatch": False,
        "forbidden_s9_raw": False,
        "forbidden_s7_raw": False,
        "unreviewed_fits": False,
        "allowed_raw_ok": False,
    }
    try:
        refuse_mismatched_protocol_hash("a" * 64, "b" * 64)
    except S10Refusal:
        refusals["hash_mismatch"] = True
    try:
        refuse_if_not_allowed_raw_root(
            "reports/generated/nn_s9_analytic_pairing_20260930/"
        )
    except S10Refusal:
        refusals["forbidden_s9_raw"] = True
    try:
        refuse_if_not_allowed_raw_root(
            "reports/generated/nn_s7_covariance_20260929/"
        )
    except S10Refusal:
        refusals["forbidden_s7_raw"] = True
    try:
        refuse_unreviewed_scientific_fits()
    except S10Refusal:
        refusals["unreviewed_fits"] = True
    refuse_if_not_allowed_raw_root(ALLOWED_RAW_ROOT)
    refusals["allowed_raw_ok"] = True

    return {
        "disposition": "IMPLEMENT_PASS",
        "protocol_id": PROTOCOL_ID,
        "null_candidate_id": NULL_CANDIDATE_ID,
        "claim_level": CLAIM_LEVEL,
        "research_fits_executed": 0,
        "diagnostic_fits_executed": 0,
        "generator_draws_this_run": int(exchange["generator_draws"]),
        "oracle": oracle,
        "exchangeability_panel": {
            "n_seeds": exchange["n_seeds"],
            "mean_ratio": exchange["mean_ratio"],
            "min_ratio": exchange["min_ratio"],
            "max_ratio": exchange["max_ratio"],
            "ratio_within_band": exchange["ratio_within_band"],
            "band": exchange["band"],
            "seeds": exchange["seeds"],
        },
        "fit_arithmetic": fit_arithmetic,
        "job_coverage": {
            "smoke": sum(1 for j in jobs if j["stage"] == "smoke"),
            "screen": sum(1 for j in jobs if j["stage"] == "screen"),
            "total": len(jobs),
            "within_cap": len(jobs) <= SCIENTIFIC_ATTEMPT_CAP,
            "job_ids_unique": True,
        },
        "param_match": param_match,
        "gradients_finite": {a: gradients[a]["finite"] for a in NEURAL_ARMS},
        "reload_pass": {a: reloads[a]["passed"] for a in NEURAL_ARMS},
        "refusals": refusals,
        "hashes": {
            "S10_PROTOCOL.json": protocol_sha,
            "S10_SPLIT_MANIFEST.json": split_sha,
        },
        "allowed_raw_root": ALLOWED_RAW_ROOT,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "scientific_invariants": {
            "primary": "B_NULL",
            "s9": "INVALID",
            "s9_immutable": True,
            "prior_s8": "NO FIT",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "study": "STUDY_PARTIAL",
        },
        "trainability_with_learning": "REFUSED_UNTIL_CHECKPOINT_C",
        "arms": list(ARMS),
        "neural_arms": list(NEURAL_ARMS),
        "logreg_arms": list(LOGREG_ARMS),
    }


def seed_schedule_payload() -> dict[str, Any]:
    return {
        "committed_before_simulation": True,
        "protocol_id": PROTOCOL_ID,
        "decision_generator_seed": DECISION_GENERATOR_SEED,
        "decision_split_seed": DECISION_SPLIT_SEED,
        "decision_model_seed": DECISION_MODEL_SEED,
        "headroom_generator_seeds": list(HEADROOM_GENERATOR_SEEDS),
        "pairing_shuffle_seeds": list(PAIRING_SHUFFLE_SEEDS),
        "r7_exchangeability_generator_seeds": list(R7_EXCHANGEABILITY_SEEDS),
        "disjoint_from": {
            "s9_decision_generator": 9001,
            "s9_headroom": [9101, 9102, 9103],
            "r2_independent_gaussian_panel": list(range(5101, 5165)),
            "r2_orthogonal_panel": list(range(5201, 5217)),
        },
        "selection_rule": (
            "Prospective freeze before scientific outcomes; not chosen by S9 "
            "INVALID metrics or R2 diagnostic performance."
        ),
    }
