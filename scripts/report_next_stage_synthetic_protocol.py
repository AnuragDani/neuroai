#!/usr/bin/env python3
"""Q7 freeze analytic synthetic protocol for S9 pairing-use software control.

Writes SYNTHETIC_PROTOCOL.json/.md and SPLIT_MANIFEST.json. Recomputes fit
arithmetic, builds the tiny F=3 class-quota split, and verifies analytic
oracle/shuffle invariants on an in-memory toy realization. No model fits,
downloads, or package installs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
DEFAULT_FIT_LEDGER = DEFAULT_OUT_DIR / "FIT_LEDGER.json"

PROTOCOL_ID = "S9_analytic_pairing_use_synthetic_20260930"
PROTOCOL_KIND = "analytic_synthetic_pairing_use_software_control"
ARMS = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
    "logreg_concat",
    "logreg_rna",
    "logreg_atac",
)
N_ARMS = 7
N_FOLDS = 3
N_DONORS = 24
N_CLASS0 = 12
N_CLASS1 = 12
CELLS_PER_DONOR = 32
N_FEATURES = 16
N_PLANTED_CHANNELS = 4
OUTER_QUOTAS_CLASS0 = (4, 4, 4)
OUTER_QUOTAS_CLASS1 = (4, 4, 4)
INNER_VAL_PER_CLASS = 2
DECISION_GENERATOR_SEED = 9001
DECISION_SPLIT_SEED = 0
DECISION_MODEL_SEED = 9001
HEADROOM_GENERATOR_SEEDS = (9101, 9102, 9103)
PAIRING_SHUFFLE_SEEDS = tuple(range(4001, 4017))
SMOKE_FITS = 7  # fold-0 × rho=1 × 7 arms
SCREEN_FITS = N_FOLDS * N_ARMS * 2  # 3 × 7 × {0,1} = 42
TOTAL_FITS = SMOKE_FITS + SCREEN_FITS  # 49
SYNTHETIC_ATTEMPT_CAP = 60
SYNTHETIC_FITTING_HOURS_CAP = 4
SYNTHETIC_ARTIFACT_GIB_CAP = 2
ORACLE_BA_RHO1_MIN = 0.90
ORACLE_BA_CHANCE_MAX = 0.70
_VAR_EPS = 1e-12


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _digest(*parts: object) -> str:
    return hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def _stable_rng(*parts: object) -> np.random.Generator:
    digest = hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).digest()
    words = np.frombuffer(digest, dtype=np.uint32)
    return np.random.default_rng(np.random.SeedSequence(words.tolist()))


def _centre_scale(vector: np.ndarray) -> np.ndarray:
    centred = vector - float(vector.mean())
    variance = float(np.mean(centred * centred))
    if variance <= _VAR_EPS:
        raise ValueError("degenerate planted vector (near-zero variance)")
    return centred / np.sqrt(variance)


def _orthogonalize_against(w: np.ndarray, z: np.ndarray) -> np.ndarray:
    projection = float(np.dot(w, z) / np.dot(z, z))
    residual = w - projection * z
    return _centre_scale(residual)


def donor_ids() -> list[str]:
    return [f"s9_donor_{i:02d}" for i in range(N_DONORS)]


def assign_donor_labels(generator_seed: int) -> dict[str, int]:
    """Rank donors by SHA256; first 12 → class 0, remaining → class 1."""
    ranked = sorted(
        donor_ids(),
        key=lambda d: (_digest("s9-label", generator_seed, d), d),
    )
    labels = {d: 0 for d in ranked[:N_CLASS0]}
    labels.update({d: 1 for d in ranked[N_CLASS0:]})
    if sum(1 for v in labels.values() if v == 0) != N_CLASS0:
        raise RuntimeError("label assignment class-0 count mismatch")
    if sum(1 for v in labels.values() if v == 1) != N_CLASS1:
        raise RuntimeError("label assignment class-1 count mismatch")
    return labels


def s9_split_digest(
    *,
    split_seed: int,
    generator_seed: int,
    stage: str,
    label: int,
    donor_id: str,
) -> str:
    return _digest("s9-split-v1", split_seed, generator_seed, stage, label, donor_id)


def rank_donors(
    ids: list[str],
    *,
    split_seed: int,
    generator_seed: int,
    stage: str,
    label: int,
) -> list[str]:
    unique = sorted(set(ids))
    return sorted(
        unique,
        key=lambda d: (
            s9_split_digest(
                split_seed=split_seed,
                generator_seed=generator_seed,
                stage=stage,
                label=label,
                donor_id=d,
            ),
            d,
        ),
    )


def allocate_s9_folds(
    labels: dict[str, int],
    *,
    split_seed: int = DECISION_SPLIT_SEED,
    generator_seed: int = DECISION_GENERATOR_SEED,
) -> dict[str, Any]:
    """Class-quota F=3 outer/inner allocation; feature-blind."""
    if sum(OUTER_QUOTAS_CLASS0) != N_CLASS0:
        raise ValueError("class-0 outer quotas must sum to 12")
    if sum(OUTER_QUOTAS_CLASS1) != N_CLASS1:
        raise ValueError("class-1 outer quotas must sum to 12")
    ranked0 = rank_donors(
        [d for d, lab in labels.items() if lab == 0],
        split_seed=split_seed,
        generator_seed=generator_seed,
        stage="outer",
        label=0,
    )
    ranked1 = rank_donors(
        [d for d, lab in labels.items() if lab == 1],
        split_seed=split_seed,
        generator_seed=generator_seed,
        stage="outer",
        label=1,
    )
    folds: dict[str, Any] = {}
    seen_test: list[str] = []
    cursor0 = cursor1 = 0
    for fold_idx in range(N_FOLDS):
        n0 = OUTER_QUOTAS_CLASS0[fold_idx]
        n1 = OUTER_QUOTAS_CLASS1[fold_idx]
        test0 = ranked0[cursor0 : cursor0 + n0]
        test1 = ranked1[cursor1 : cursor1 + n1]
        cursor0 += n0
        cursor1 += n1
        test_donors = sorted(test0 + test1)
        if len(test_donors) != 8 or len(set(test_donors)) != 8:
            raise ValueError(f"fold {fold_idx}: expected 8 unique test donors")
        overlap = set(test_donors) & set(seen_test)
        if overlap:
            raise ValueError(f"outer-test donor reuse refused: {sorted(overlap)}")
        seen_test.extend(test_donors)

        remaining = sorted(set(labels) - set(test_donors))
        rem0 = [d for d in remaining if labels[d] == 0]
        rem1 = [d for d in remaining if labels[d] == 1]
        inner_stage = f"inner:{fold_idx}"
        ranked_rem0 = rank_donors(
            rem0,
            split_seed=split_seed,
            generator_seed=generator_seed,
            stage=inner_stage,
            label=0,
        )
        ranked_rem1 = rank_donors(
            rem1,
            split_seed=split_seed,
            generator_seed=generator_seed,
            stage=inner_stage,
            label=1,
        )
        val_donors = sorted(
            ranked_rem0[:INNER_VAL_PER_CLASS] + ranked_rem1[:INNER_VAL_PER_CLASS]
        )
        train_donors = sorted(
            ranked_rem0[INNER_VAL_PER_CLASS:] + ranked_rem1[INNER_VAL_PER_CLASS:]
        )
        if len(val_donors) != 4 or len(train_donors) != 12:
            raise ValueError(
                f"fold {fold_idx}: expected train/val 12/4; "
                f"got {len(train_donors)}/{len(val_donors)}"
            )
        parts = (set(train_donors), set(val_donors), set(test_donors))
        if len(parts[0] | parts[1] | parts[2]) != N_DONORS:
            raise ValueError(f"fold {fold_idx}: partitions miss donors")
        if parts[0] & parts[1] or parts[0] & parts[2] or parts[1] & parts[2]:
            raise ValueError(f"fold {fold_idx}: overlapping partitions")
        class_counts = {}
        for part_name, part in (
            ("train", train_donors),
            ("val", val_donors),
            ("test", test_donors),
        ):
            c0 = sum(1 for d in part if labels[d] == 0)
            c1 = sum(1 for d in part if labels[d] == 1)
            if c0 < 1 or c1 < 1:
                raise ValueError(
                    f"fold {fold_idx} {part_name} single-class refused: "
                    f"{{0:{c0},1:{c1}}}"
                )
            class_counts[part_name] = {"0": c0, "1": c1}
        folds[str(fold_idx)] = {
            "train_donors": train_donors,
            "val_donors": val_donors,
            "test_donors": test_donors,
            "class_counts": class_counts,
        }
    if len(seen_test) != N_DONORS or len(set(seen_test)) != N_DONORS:
        raise ValueError("outer tests must cover each donor exactly once")
    return {
        "protocol_id": PROTOCOL_ID,
        "split_method": "s9-class-quota-sha256",
        "split_seed": int(split_seed),
        "generator_seed": int(generator_seed),
        "n_folds": N_FOLDS,
        "n_donors": N_DONORS,
        "class_balance": {"0": N_CLASS0, "1": N_CLASS1},
        "outer_quotas": {
            "class_0": list(OUTER_QUOTAS_CLASS0),
            "class_1": list(OUTER_QUOTAS_CLASS1),
        },
        "inner_val_per_class": INNER_VAL_PER_CLASS,
        "donor_labels": {d: int(labels[d]) for d in sorted(labels)},
        "folds": folds,
        "validation": {
            "both_classes_every_partition": True,
            "outer_test_exactly_once": True,
            "train_val_test_disjoint": True,
        },
    }


def generate_analytic_arrays(
    labels: dict[str, int],
    *,
    rho: float,
    generator_seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Independent analytic RNA/ATAC with planted pairing channels + nuisance."""
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
        # Planted channels: label-dependent within-cell covariance at rho.
        for channel in range(N_PLANTED_CHANNELS):
            z = _centre_scale(
                _stable_rng(generator_seed, donor, channel, "z").normal(size=CELLS_PER_DONOR)
            )
            w = _orthogonalize_against(
                _stable_rng(generator_seed, donor, channel, "w").normal(size=CELLS_PER_DONOR),
                z,
            )
            rna[rows, channel] = z
            atac[rows, channel] = sign * rho * z + sign_scale * w
        # Nuisance channels: independent of label and of planted z; donor mean shift.
        donor_shift = _stable_rng(generator_seed, donor, "nuisance_shift").normal(
            size=N_FEATURES - N_PLANTED_CHANNELS
        )
        for j, channel in enumerate(range(N_PLANTED_CHANNELS, N_FEATURES)):
            rna[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "rna_n").normal(size=CELLS_PER_DONOR)
                + 0.5 * donor_shift[j]
            )
            atac[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "atac_n").normal(size=CELLS_PER_DONOR)
                + 0.5 * donor_shift[j]
            )
    return rna, atac, donor_col, label_col, cell_ids


def permute_atac_within_donor(
    atac: np.ndarray, donor: np.ndarray, seed: int
) -> np.ndarray:
    """Permute ATAC rows within each donor; preserve exact marginal multiset."""
    out = np.array(atac, copy=True)
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        rng = np.random.default_rng(
            int(_digest("s9-shuffle", seed, name)[:8], 16)
        )
        perm = rng.permutation(idx.size)
        out[idx] = atac[idx][perm]
    return out


def oracle_donor_scores(
    rna: np.ndarray, atac: np.ndarray, donor: np.ndarray
) -> dict[str, float]:
    """Non-learned pairing product on planted channels, mean per donor."""
    product = (rna[:, :N_PLANTED_CHANNELS] * atac[:, :N_PLANTED_CHANNELS]).sum(axis=1)
    scores: dict[str, float] = {}
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        scores[str(name)] = float(np.mean(product[idx]))
    return scores


def oracle_balanced_accuracy(
    scores: dict[str, float], labels: dict[str, int]
) -> float:
    """Classify donor by sign(score); report balanced accuracy."""
    y_true = [labels[d] for d in sorted(scores)]
    y_pred = [1 if scores[d] > 0.0 else 0 for d in sorted(scores)]
    return float(balanced_accuracy_score(y_true, y_pred))


def verify_oracle_invariants(
    labels: dict[str, int], *, generator_seed: int = DECISION_GENERATOR_SEED
) -> dict[str, Any]:
    """Analytic oracle PASS/FAIL checks without learned models."""
    rna1, atac1, donor, _lab, _cells = generate_analytic_arrays(
        labels, rho=1.0, generator_seed=generator_seed
    )
    rna0, atac0, donor0, _, _ = generate_analytic_arrays(
        labels, rho=0.0, generator_seed=generator_seed
    )
    if not np.array_equal(donor, donor0):
        raise RuntimeError("donor column mismatch across rho")
    # Planted RNA identical across rho (z draw independent of rho).
    if not np.allclose(rna1[:, :N_PLANTED_CHANNELS], rna0[:, :N_PLANTED_CHANNELS]):
        raise RuntimeError("planted RNA must be rho-invariant")
    scores_rho1 = oracle_donor_scores(rna1, atac1, donor)
    scores_rho0 = oracle_donor_scores(rna0, atac0, donor)
    ba_rho1 = oracle_balanced_accuracy(scores_rho1, labels)
    ba_rho0 = oracle_balanced_accuracy(scores_rho0, labels)
    shuffled = permute_atac_within_donor(atac1, donor, seed=PAIRING_SHUFFLE_SEEDS[0])
    # Exact marginal preservation within donor.
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        orig = np.sort(atac1[idx], axis=0)
        shuf = np.sort(shuffled[idx], axis=0)
        if not np.allclose(orig, shuf):
            raise RuntimeError(f"shuffle failed marginal preservation for {name}")
    ba_rho1_shuffled = oracle_balanced_accuracy(
        oracle_donor_scores(rna1, shuffled, donor), labels
    )
    # At rho=1, planted ATAC equals signed RNA on planted channels (no noise).
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        sign = 2 * labels[str(name)] - 1
        if not np.allclose(
            atac1[idx, :N_PLANTED_CHANNELS],
            sign * rna1[idx, :N_PLANTED_CHANNELS],
        ):
            raise RuntimeError(f"rho=1 ATAC != signed RNA for {name}")
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
    }
    checks["oracle_gate"] = (
        "PASS"
        if (
            checks["rho1_oracle_detects_pairing"]
            and checks["rho0_oracle_near_chance"]
            and checks["shuffle_destroys_rho1_oracle"]
        )
        else "FAIL"
    )
    return checks


def recompute_fit_arithmetic(ledger: dict[str, Any]) -> dict[str, Any]:
    selected = next(
        c for c in ledger["candidates"] if c["id"] == ledger["selected_candidate_id"]
    )
    smoke = int(selected["breakdown"]["smoke_fold0_rho1"])
    screen0 = int(selected["breakdown"]["screen_rho0"])
    screen1 = int(selected["breakdown"]["screen_rho1"])
    total = smoke + screen0 + screen1
    expected_screen = N_FOLDS * N_ARMS  # per rho
    if smoke != N_ARMS:
        raise RuntimeError(f"smoke must be {N_ARMS}, got {smoke}")
    if screen0 != expected_screen or screen1 != expected_screen:
        raise RuntimeError(
            f"screen per-rho must be {expected_screen}; got rho0={screen0} rho1={screen1}"
        )
    if total != TOTAL_FITS or total != int(selected["attempted_fits"]):
        raise RuntimeError(f"fit total mismatch: {total} vs {selected['attempted_fits']}")
    if total > SYNTHETIC_ATTEMPT_CAP:
        raise RuntimeError(f"fits {total} exceed cap {SYNTHETIC_ATTEMPT_CAP}")
    headroom = SYNTHETIC_ATTEMPT_CAP - total
    # Headroom seeds are disjoint from decision seed 9001.
    if DECISION_GENERATOR_SEED in HEADROOM_GENERATOR_SEEDS:
        raise RuntimeError("headroom seeds must be disjoint from decision seed")
    return {
        "smoke_fold0_rho1": smoke,
        "screen_rho0": screen0,
        "screen_rho1": screen1,
        "pairing_interventions_as_fits": 0,
        "total_attempted_fits": total,
        "cap": SYNTHETIC_ATTEMPT_CAP,
        "fits_within_cap": total <= SYNTHETIC_ATTEMPT_CAP,
        "headroom_fits": headroom,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "decision_generator_seed": DECISION_GENERATOR_SEED,
        "headroom_generator_seeds_disjoint": list(HEADROOM_GENERATOR_SEEDS),
        "pairing_shuffle_seeds_not_counted_as_fits": list(PAIRING_SHUFFLE_SEEDS),
        "note": (
            "Pairing shuffle interventions evaluate saved checkpoints and do not "
            "consume fit attempts. Headroom seeds cannot retune the frozen "
            "decision rule or null threshold."
        ),
    }


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
            "cells_per_donor": CELLS_PER_DONOR,
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
