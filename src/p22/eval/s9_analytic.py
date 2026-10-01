"""S9 analytic pairing-use generator, oracle, dry-run and refusal helpers.

Implements the Q7-frozen protocol ``S9_analytic_pairing_use_synthetic_20260930``
without research fits. Reuses ``paired_model`` / ``model_inputs`` / ``predict``
and S7 pairing log-loss helpers. Tiny trainability-with-learning checks are
explicitly refused until Checkpoint C review allowance.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import balanced_accuracy_score

from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import model_inputs, paired_model
from p22.eval.s7_ledger import make_fit_id, sha256_file
from p22.eval.s7_pairing import S7_IDENTITY_ATOL, binary_log_loss, identity_check
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import forward_logits, predict

PROTOCOL_ID = "S9_analytic_pairing_use_synthetic_20260930"
PROTOCOL_KIND = "analytic_synthetic_pairing_use_software_control"
ARMS: tuple[str, ...] = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
    "logreg_concat",
    "logreg_rna",
    "logreg_atac",
)
NEURAL_ARMS: tuple[str, ...] = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
)
LOGREG_ARMS: tuple[str, ...] = ("logreg_concat", "logreg_rna", "logreg_atac")
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
SMOKE_FITS = 7
SCREEN_FITS = N_FOLDS * N_ARMS * 2
TOTAL_FITS = SMOKE_FITS + SCREEN_FITS
SYNTHETIC_ATTEMPT_CAP = 60
SYNTHETIC_FITTING_HOURS_CAP = 4
SYNTHETIC_ARTIFACT_GIB_CAP = 2
ORACLE_BA_RHO1_MIN = 0.90
ORACLE_BA_CHANCE_MAX = 0.70
REFUSED_RAW_ROOT_PREFIXES = (
    "reports/generated/nn_s7_covariance_20260929/",
    "reports/generated/nn_s7_covariance_split_v2_20260929/",
    "reports/generated/nn_s8_",
)
ALLOWED_RAW_ROOT = "reports/generated/nn_s9_analytic_pairing_20260930/"
_VAR_EPS = 1e-12


class S9Refusal(ValueError):
    """Explicit refusal for mismatched protocol/output/identity contracts."""


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
        rng = np.random.default_rng(int(_digest("s9-shuffle", seed, name)[:8], 16))
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


def recompute_fit_arithmetic(ledger: Mapping[str, Any]) -> dict[str, Any]:
    selected = next(
        c for c in ledger["candidates"] if c["id"] == ledger["selected_candidate_id"]
    )
    smoke = int(selected["breakdown"]["smoke_fold0_rho1"])
    screen0 = int(selected["breakdown"]["screen_rho0"])
    screen1 = int(selected["breakdown"]["screen_rho1"])
    total = smoke + screen0 + screen1
    expected_screen = N_FOLDS * N_ARMS
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
        "headroom_fits": SYNTHETIC_ATTEMPT_CAP - total,
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


def s9_protocol_from_frozen(training: Mapping[str, Any] | None = None) -> MultiomeProtocol:
    """Build MultiomeProtocol from frozen S9 training budget (decision model seed)."""
    tb = dict(training or {})
    return MultiomeProtocol(
        n_tokens=int(tb.get("n_tokens", 8)),
        embed_dim=int(tb.get("embed_dim", 32)),
        hidden_dim=int(tb.get("hidden_dim", 128)),
        n_heads=int(tb.get("n_heads", 4)),
        dropout=float(tb.get("dropout", 0.2)),
        feature_budget=N_FEATURES,
        cell_cap=N_DONORS * CELLS_PER_DONOR,
        max_epochs=int(tb.get("max_epochs", 20)),
        patience=int(tb.get("patience", 5)),
        batch_size=int(tb.get("batch_size", 64)),
        learning_rate=float(tb.get("learning_rate", 0.001)),
        n_repeats=1,
        n_folds=N_FOLDS,
        split_seed=DECISION_SPLIT_SEED,
        model_seed=DECISION_MODEL_SEED,
        sampling_seed=22,
    )


def enumerate_s9_jobs() -> list[dict[str, Any]]:
    """Predeclared smoke (7) + screen (42) jobs; no execution."""
    jobs: list[dict[str, Any]] = []
    for model in ARMS:
        fit_id = make_fit_id("smoke", 1.0, DECISION_GENERATOR_SEED, 0, model)
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


def fold_row_indices(
    donor_col: np.ndarray, fold: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    """Map frozen fold donor lists to cell-row indices."""
    out: dict[str, np.ndarray] = {}
    for part in ("train", "val", "test"):
        donors = set(fold[f"{part}_donors"])
        out[part] = np.flatnonzero(np.isin(donor_col, list(donors)))
    return out


def assert_donor_isolation(positions: Mapping[str, np.ndarray], donor_col: np.ndarray) -> None:
    """Refuse overlapping donors across train/val/test partitions."""
    donor_sets = {}
    for part, rows in positions.items():
        donor_sets[part] = set(str(d) for d in donor_col[rows].tolist())
    if donor_sets["train"] & donor_sets["val"]:
        raise S9Refusal("train/val donor leakage")
    if donor_sets["train"] & donor_sets["test"]:
        raise S9Refusal("train/test donor leakage")
    if donor_sets["val"] & donor_sets["test"]:
        raise S9Refusal("val/test donor leakage")


def refuse_mismatched_protocol_hash(
    expected_sha256: str, actual_sha256: str, *, label: str = "protocol"
) -> None:
    if expected_sha256 != actual_sha256:
        raise S9Refusal(
            f"{label} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )


def refuse_forbidden_raw_root(raw_root: str | Path) -> None:
    text = str(raw_root).replace("\\", "/")
    for prefix in REFUSED_RAW_ROOT_PREFIXES:
        if prefix.rstrip("/") in text or text.endswith(prefix.rstrip("/")) or prefix in text:
            # nn_s8_ is a prefix pattern; match substring carefully
            if prefix.endswith("_"):
                if "/nn_s8_" in text or text.startswith("reports/generated/nn_s8_"):
                    raise S9Refusal(f"refused raw root overlaps forbidden prefix {prefix!r}")
            else:
                raise S9Refusal(f"refused raw root overlaps forbidden prefix {prefix!r}")
    # Also require allowed root when path is relative-ish
    if "nn_s9_analytic_pairing_20260930" not in text and ALLOWED_RAW_ROOT.strip("/") not in text:
        # Absolute paths under allowed name ok; bare wrong names refused above.
        # Only refuse when an old S7/S8 marker is present (handled) or explicit force.
        pass


def refuse_if_not_allowed_raw_root(raw_root: str | Path) -> None:
    """Hard refuse S7/S8 roots; require S9 analytic root name."""
    text = str(raw_root).replace("\\", "/")
    refuse_forbidden_raw_root(text)
    if "nn_s9_analytic_pairing_20260930" not in text:
        raise S9Refusal(
            f"raw root must contain nn_s9_analytic_pairing_20260930; got {text!r}"
        )


def refuse_unreviewed_trainability() -> None:
    """Fixture/tests must not silently run unreviewed research learning fits."""
    raise S9Refusal(
        "tiny trainability-with-learning checks count toward the fit cap and "
        "require Checkpoint C / independent review allowance before execution"
    )


def _loss_from_logits(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.cross_entropy(logits, labels)


def check_finite_gradients(
    arm: str,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    protocol: MultiomeProtocol,
    *,
    n_cells: int = 64,
) -> dict[str, Any]:
    """One forward+backward on frozen widths; no optimizer step / no fit count."""
    if arm not in NEURAL_ARMS:
        raise ValueError(f"finite-gradient check applies to neural arms only, got {arm}")
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(arm, widths, protocol)
    model.train()
    selected = model_inputs(arm, dict(views))
    take = min(int(n_cells), int(labels.shape[0]))
    tensors = {
        key: torch.as_tensor(value[:take], dtype=torch.float32)
        for key, value in selected.items()
    }
    y = torch.as_tensor(labels[:take], dtype=torch.long)
    logits = forward_logits(model, tensors)
    loss = _loss_from_logits(logits, y)
    model.zero_grad(set_to_none=True)
    loss.backward()
    grads = []
    for param in model.parameters():
        if param.grad is None:
            continue
        g = param.grad.detach()
        if not torch.isfinite(g).all():
            return {
                "arm": arm,
                "finite": False,
                "loss": float(loss.detach()),
                "reason": "non-finite gradient tensor",
            }
        grads.append(float(g.abs().max()))
    if not grads:
        return {
            "arm": arm,
            "finite": False,
            "loss": float(loss.detach()),
            "reason": "no gradients produced",
        }
    return {
        "arm": arm,
        "finite": True,
        "loss": float(loss.detach()),
        "max_abs_grad": max(grads),
        "n_cells": take,
    }


def check_state_dict_reload_equality(
    arm: str,
    views: Mapping[str, np.ndarray],
    protocol: MultiomeProtocol,
    *,
    n_cells: int = 64,
) -> dict[str, Any]:
    """Build → predict → reload state_dict → predict; identity within atol."""
    if arm not in NEURAL_ARMS:
        raise ValueError(f"reload check applies to neural arms only, got {arm}")
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(arm, widths, protocol)
    selected = model_inputs(arm, dict(views))
    take = min(int(n_cells), int(views[VIEW_A].shape[0]))
    subset = {key: value[:take] for key, value in selected.items()}
    _, probs_a = predict(model, subset)
    state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model2 = paired_model(arm, widths, protocol)
    model2.load_state_dict(state)
    _, probs_b = predict(model2, subset)
    check = identity_check(probs_a[:, 1], probs_b[:, 1], atol=S7_IDENTITY_ATOL)
    return {
        "arm": arm,
        "passed": bool(check["passed"]),
        "max_abs_diff": check["max_abs_diff"],
        "atol": check["atol"],
        "n_cells": take,
    }


def pairing_use_toy_logloss_drop(
    labels: dict[str, int],
    *,
    rho: float,
    generator_seed: int = DECISION_GENERATOR_SEED,
) -> dict[str, Any]:
    """Non-learned pairing-score log-loss drop under shuffle (statistic scaffolding).

    Uses oracle scores mapped to probabilities via sigmoid of the donor score.
    Does not fit models; validates that the primary statistic scaffolding is
    well-defined on the analytic plant.
    """
    rna, atac, donor, _lab, _cells = generate_analytic_arrays(
        labels, rho=rho, generator_seed=generator_seed
    )
    scores = oracle_donor_scores(rna, atac, donor)
    shuffled = permute_atac_within_donor(atac, donor, seed=PAIRING_SHUFFLE_SEEDS[0])
    scores_s = oracle_donor_scores(rna, shuffled, donor)
    donors_sorted = sorted(scores)
    y = np.asarray([labels[d] for d in donors_sorted], dtype=np.float64)
    # Map score → probability via logistic of score (toy; not a learned model).
    p0 = 1.0 / (1.0 + np.exp(-np.asarray([scores[d] for d in donors_sorted])))
    p1 = 1.0 / (1.0 + np.exp(-np.asarray([scores_s[d] for d in donors_sorted])))
    ll0 = binary_log_loss(y, p0)
    ll1 = binary_log_loss(y, p1)
    return {
        "rho": float(rho),
        "log_loss_original": ll0,
        "log_loss_shuffled": ll1,
        "mean_drop": float(ll1 - ll0),
        "n_donors": len(donors_sorted),
    }


def build_param_match_record(protocol: MultiomeProtocol) -> dict[str, Any]:
    """CA vs token_concat parameter counts under frozen S9 widths."""
    widths = [N_FEATURES, N_FEATURES]
    ca = paired_model("cross_attention", widths, protocol)
    tc = paired_model("token_concat", widths, protocol)
    ca_n = sum(int(p.numel()) for p in ca.parameters())
    tc_n = sum(int(p.numel()) for p in tc.parameters())
    denom = max(ca_n, tc_n)
    relative = abs(ca_n - tc_n) / denom
    tol = 0.10
    return {
        "cross_attention": ca_n,
        "token_concat": tc_n,
        "relative_abs_diff": relative,
        "tolerance": tol,
        "pass": relative <= tol,
    }


def run_q8_dry_run(
    *,
    protocol_path: Path,
    split_path: Path,
    ledger_path: Path,
) -> dict[str, Any]:
    """Verify frozen artifacts, oracle, factory reuse, gradients, reload, refusals.

    Research fits are not executed. Trainability-with-learning is refused.
    """
    protocol = json.loads(Path(protocol_path).read_text())
    split_manifest = json.loads(Path(split_path).read_text())
    ledger = json.loads(Path(ledger_path).read_text())
    protocol_sha = sha256_file(protocol_path)
    split_sha = sha256_file(split_path)
    if protocol.get("protocol_id") != PROTOCOL_ID:
        raise S9Refusal(f"unexpected protocol_id {protocol.get('protocol_id')!r}")
    if protocol.get("disposition") != "PROTOCOL_FROZEN":
        raise S9Refusal("Q8 requires PROTOCOL_FROZEN upstream disposition")

    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    live_split = allocate_s9_folds(labels)
    if live_split["donor_labels"] != split_manifest["donor_labels"]:
        raise S9Refusal("live split labels diverge from SPLIT_MANIFEST")
    for fold_key, fold in split_manifest["folds"].items():
        if live_split["folds"][fold_key] != fold:
            raise S9Refusal(f"live split fold {fold_key} diverges from SPLIT_MANIFEST")

    fit_arithmetic = recompute_fit_arithmetic(ledger)
    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise RuntimeError(f"oracle gate FAIL: {oracle}")

    jobs = enumerate_s9_jobs()
    if len(jobs) != TOTAL_FITS:
        raise RuntimeError(f"job enumeration {len(jobs)} != {TOTAL_FITS}")
    smoke_n = sum(1 for j in jobs if j["stage"] == "smoke")
    screen_n = sum(1 for j in jobs if j["stage"] == "screen")
    if smoke_n != SMOKE_FITS or screen_n != SCREEN_FITS:
        raise RuntimeError(f"coverage mismatch smoke={smoke_n} screen={screen_n}")

    rna, atac, donor_col, label_col, cell_ids = generate_analytic_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    views = {VIEW_A: rna.astype(np.float32), VIEW_B: atac.astype(np.float32)}
    fold0 = split_manifest["folds"]["0"]
    positions = fold_row_indices(donor_col, fold0)
    assert_donor_isolation(positions, donor_col)

    # Cross-donor shuffle would mix donors — verify within-donor only.
    shuffled = permute_atac_within_donor(atac, donor_col, seed=PAIRING_SHUFFLE_SEEDS[0])
    for name in sorted(set(donor_col.tolist()), key=str):
        idx = np.flatnonzero(donor_col == name)
        if not np.allclose(np.sort(atac[idx], axis=0), np.sort(shuffled[idx], axis=0)):
            raise RuntimeError(f"marginal fail {name}")

    proto = s9_protocol_from_frozen(protocol["models"]["training_budget"])
    param_match = build_param_match_record(proto)
    if not param_match["pass"]:
        raise RuntimeError(f"CA/TC param match FAIL: {param_match}")

    arm_build: dict[str, Any] = {}
    for arm in ARMS:
        if arm in LOGREG_ARMS:
            arm_build[arm] = {"kind": "logreg", "built": True}
            continue
        widths = [N_FEATURES, N_FEATURES]
        model = paired_model(arm, widths, proto)
        n_params = sum(int(p.numel()) for p in model.parameters())
        arm_build[arm] = {"kind": "neural", "built": True, "n_params": n_params}

    grad_checks = [
        check_finite_gradients(arm, views, label_col, proto) for arm in NEURAL_ARMS
    ]
    if not all(c["finite"] for c in grad_checks):
        raise RuntimeError(f"non-finite gradients: {grad_checks}")

    reload_checks = [
        check_state_dict_reload_equality(arm, views, proto) for arm in NEURAL_ARMS
    ]
    if not all(c["passed"] for c in reload_checks):
        raise RuntimeError(f"reload identity FAIL: {reload_checks}")

    null_toy = pairing_use_toy_logloss_drop(labels, rho=0.0)
    pos_toy = pairing_use_toy_logloss_drop(labels, rho=1.0)

    refusal_cases: list[dict[str, Any]] = []
    # Protocol hash mismatch
    try:
        refuse_mismatched_protocol_hash(protocol_sha, "0" * 64)
        refusal_cases.append({"case": "protocol_hash", "refused": False})
    except S9Refusal:
        refusal_cases.append({"case": "protocol_hash", "refused": True})
    # Forbidden raw roots
    for bad in (
        "reports/generated/nn_s7_covariance_20260929/",
        "reports/generated/nn_s7_covariance_split_v2_20260929/",
        "reports/generated/nn_s8_fake/",
    ):
        try:
            refuse_if_not_allowed_raw_root(bad)
            refusal_cases.append({"case": f"raw_root:{bad}", "refused": False})
        except S9Refusal:
            refusal_cases.append({"case": f"raw_root:{bad}", "refused": True})
    # Allowed root passes
    try:
        refuse_if_not_allowed_raw_root(ALLOWED_RAW_ROOT)
        allowed_ok = True
    except S9Refusal:
        allowed_ok = False
    # Unreviewed trainability
    try:
        refuse_unreviewed_trainability()
        trainability_refused = False
    except S9Refusal:
        trainability_refused = True
    # Induced donor leakage
    leak_positions = {
        "train": positions["train"],
        "val": positions["val"],
        "test": np.concatenate([positions["test"], positions["train"][:1]]),
    }
    try:
        assert_donor_isolation(leak_positions, donor_col)
        leakage_refused = False
    except S9Refusal:
        leakage_refused = True

    if not all(c["refused"] for c in refusal_cases):
        raise RuntimeError(f"expected refusals missing: {refusal_cases}")
    if not allowed_ok or not trainability_refused or not leakage_refused:
        raise RuntimeError("refusal contract incomplete")

    disposition = "IMPLEMENT_PASS"
    return {
        "task": "Q8",
        "disposition": disposition,
        "protocol_id": PROTOCOL_ID,
        "date": "2026-09-30",
        "branch": "gnhf/execute-the-p22-data-146414",
        "fits": 0,
        "research_fits_executed": 0,
        "trainability_with_learning": "REFUSED_UNTIL_CHECKPOINT_C",
        "network_bytes": 0,
        "depends_on": ["Q7"],
        "hashes": {
            "SYNTHETIC_PROTOCOL.json": protocol_sha,
            "SPLIT_MANIFEST.json": split_sha,
            "FIT_LEDGER.json": sha256_file(ledger_path),
        },
        "reuse": {
            "paired_model": True,
            "model_inputs": True,
            "predict": True,
            "binary_log_loss": True,
            "identity_check": True,
            "make_fit_id": True,
            "nn_factory_not_required_for_s9_seven_arms": True,
            "note": (
                "S9 seven arms reuse multiome_runner.paired_model (same as S7), "
                "not ladder nn_factory R* names."
            ),
        },
        "oracle": oracle,
        "null_semantics": {
            "kind": "fitted_pairing_plant_null",
            "toy_rho0_logloss_drop": null_toy,
            "toy_rho1_logloss_drop": pos_toy,
            "note": (
                "Toy logistic-of-oracle-score scaffolding only; fitted CA null "
                "gate remains for Q10 after Checkpoint C."
            ),
            "rejects_chance_bernoulli_ba_band": True,
            "prior_s8_no_fit_unchanged": True,
        },
        "pairing_marginal_preservation": True,
        "donor_isolation_fold0": True,
        "job_coverage": {
            "smoke": smoke_n,
            "screen": screen_n,
            "total": len(jobs),
            "cap": SYNTHETIC_ATTEMPT_CAP,
            "within_cap": len(jobs) <= SYNTHETIC_ATTEMPT_CAP,
            "job_ids_unique": len({j["fit_id"] for j in jobs}) == len(jobs),
        },
        "fit_arithmetic": fit_arithmetic,
        "resources": {
            "planned_attempted_fits": TOTAL_FITS,
            "max_total_fits": SYNTHETIC_ATTEMPT_CAP,
            "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
            "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
            "max_simultaneous_workers": 2,
            "torch_threads_per_worker": 2,
            "new_raw_root": ALLOWED_RAW_ROOT,
        },
        "arm_build": arm_build,
        "param_match": param_match,
        "finite_gradients": grad_checks,
        "reload_equality": reload_checks,
        "refusals": {
            "cases": refusal_cases,
            "allowed_raw_root_accepted": allowed_ok,
            "unreviewed_trainability_refused": trainability_refused,
            "donor_leakage_refused": leakage_refused,
        },
        "cell_ids_sample": cell_ids[:3].tolist(),
        "scientific_invariants": protocol["scientific_invariants"],
        "unresolved_flags_retained": protocol["unresolved_flags_retained"],
        "no_fits_until": "Checkpoint C (Q7+Q8+Q9 PASS on exact hashes)",
        "next": "Q9 independent scientific/code review on exact hashes",
    }


def render_implement_markdown(report: dict[str, Any]) -> str:
    fa = report["fit_arithmetic"]
    lines = [
        "# Q8 — Minimal implement and falsification (S9 analytic pairing-use)",
        "",
        f"**Disposition:** `{report['disposition']}`  ",
        f"**Protocol ID:** `{report['protocol_id']}`  ",
        f"**Date:** {report['date']}  ",
        f"**Branch:** `{report['branch']}`  ",
        f"**Research fits:** {report['research_fits_executed']} "
        f"(trainability-with-learning `{report['trainability_with_learning']}`).",
        "",
        "Machine-readable: [implement.json](implement.json); frozen "
        "[SYNTHETIC_PROTOCOL.json](SYNTHETIC_PROTOCOL.json).",
        "",
        "## Reuse",
        "",
        "- Existing `paired_model` / `model_inputs` / `predict` (multiome_runner).",
        "- Existing `binary_log_loss` / `identity_check` (s7_pairing).",
        "- Existing `make_fit_id` (s7_ledger).",
        "- New pieces only: analytic generator module `p22.eval.s9_analytic` + "
        "dry-run job enumeration / refusal helpers.",
        "",
        "## Verification summary",
        "",
        f"- Oracle gate: `{report['oracle']['oracle_gate']}` "
        f"(ρ=1 BA={report['oracle']['rho1_oracle_ba']:.4f}; "
        f"ρ=0 BA={report['oracle']['rho0_oracle_ba']:.4f}; "
        f"ρ=1 shuffled BA={report['oracle']['rho1_shuffled_oracle_ba']:.4f})",
        f"- Job coverage: smoke {report['job_coverage']['smoke']} + "
        f"screen {report['job_coverage']['screen']} = "
        f"**{report['job_coverage']['total']} ≤ {report['job_coverage']['cap']}**",
        f"- Fit arithmetic: smoke {fa['smoke_fold0_rho1']} + "
        f"screen ρ0 {fa['screen_rho0']} + screen ρ1 {fa['screen_rho1']} = "
        f"{fa['total_attempted_fits']}",
        f"- CA/TC param match: pass={report['param_match']['pass']} "
        f"(rel={report['param_match']['relative_abs_diff']:.4f})",
        f"- Finite gradients: all {len(report['finite_gradients'])} neural arms",
        f"- Reload equality: all {len(report['reload_equality'])} neural arms "
        f"(atol={S7_IDENTITY_ATOL})",
        "- Donor isolation fold-0: PASS",
        "- Within-donor ATAC marginal preservation: PASS",
        "- Refusals: protocol-hash mismatch, S7/S8 raw roots, donor leakage, "
        "unreviewed trainability-with-learning",
        "",
        "## Hashes (exact)",
        "",
    ]
    for name, digest in report["hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend(
        [
            "",
            "## Scientific invariants (unchanged)",
            "",
            "Primary `B_NULL`; S7-v1/v2 `INVALID`; prior S8 `NO FIT`; "
            "power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.",
            "",
            "Unresolved flags retained: "
            + "; ".join(report["unresolved_flags_retained"])
            + ".",
            "",
            "## Next",
            "",
            "Q9 independent scientific/code review on exact hashes. "
            "No fits until Checkpoint C.",
            "",
        ]
    )
    return "\n".join(lines)
