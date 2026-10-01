#!/usr/bin/env python3
"""R2 null-exchangeability / marginal diagnosis — generator-only, zero fits.

Preregistered seed schedule is frozen in SEED_SCHEDULE before any simulation.
Reproduces the initial orthogonality/shuffle diagnostic, derives exchangeability
requirements analytically, quantifies finite-sample marginal BA uncertainty from
saved S9 sidecars, and states a candidate null or NULL_DESIGN_UNRESOLVED.

Does not write into the shared S9 raw root. Does not fit models.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from p22.eval.s7_ledger import sha256_file  # noqa: E402
from p22.eval.s9_analytic import (  # noqa: E402
    CELLS_PER_DONOR,
    DECISION_GENERATOR_SEED,
    N_DONORS,
    N_PLANTED_CHANNELS,
    PAIRING_SHUFFLE_SEEDS,
    assign_donor_labels,
    generate_analytic_arrays,
    permute_atac_within_donor,
)
from p22.eval.s9_execute import (  # noqa: E402
    MARGINAL_BA_MAX,
    _pool_donor_ba_from_predictions,
    read_ledger_records,
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
DEFAULT_RAW_ROOT = ROOT / "reports" / "generated" / "nn_failure_audit_20261001"
PRIOR_NULL_DIAG = DEFAULT_OUT_DIR / "NULL_INVARIANCE_DIAGNOSTIC.json"

# ---------------------------------------------------------------------------
# Preregistered seed schedule — committed before any draw below.
# Total generator-array draws (generate_analytic_arrays calls) ≤ 256.
# ---------------------------------------------------------------------------
SEED_SCHEDULE: dict[str, Any] = {
    "committed_before_simulation": True,
    "decision_generator_seed": DECISION_GENERATOR_SEED,
    "shuffle_seeds_reproduce_prior": list(PAIRING_SHUFFLE_SEEDS),  # 4001–4016
    # Independent non-orthogonal Gaussian reference (diagnostic alternative draws).
    "independent_gaussian_generator_seeds": list(range(5101, 5165)),  # 64
    # Extra orthogonal ρ=0 draws to characterize product-mean sampling under
    # the frozen construction across generator seeds (not seed shopping).
    "orthogonal_rho0_generator_seeds": list(range(5201, 5217)),  # 16
    "max_generator_array_draws": 256,
    "fit_attempts_allowed": 0,
}


class NullAuditRefusal(RuntimeError):
    """Refuse unsafe R2 diagnosis."""


def _fingerprint_tree(root: Path) -> dict[str, Any]:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            rows.append(f"{st.st_mtime_ns} {st.st_size} {path.relative_to(root)}")
    digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    return {"n_files": len(rows), "tree_sha256": digest, "rows": rows}


def _assert_no_write(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    if before["tree_sha256"] != after["tree_sha256"]:
        raise NullAuditRefusal(
            "shared S9 raw tree mutated during R2; refuse write-through"
        )


def _donor_channel_product_means(
    rna: np.ndarray, atac: np.ndarray, donor: np.ndarray
) -> np.ndarray:
    """Per-donor mean of planted-channel products (shape: n_donors × n_planted)."""
    means: list[np.ndarray] = []
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        prod = rna[idx, :N_PLANTED_CHANNELS] * atac[idx, :N_PLANTED_CHANNELS]
        means.append(prod.mean(axis=0))
    return np.asarray(means, dtype=np.float64)


def _centre_scale(vector: np.ndarray) -> np.ndarray:
    centred = vector - float(vector.mean())
    variance = float(np.mean(centred * centred))
    if variance <= 1e-12:
        raise ValueError("degenerate vector")
    return centred / math.sqrt(variance)


def _stable_rng(*parts: object) -> np.random.Generator:
    digest = hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).digest()
    words = np.frombuffer(digest, dtype=np.uint32)
    return np.random.default_rng(np.random.SeedSequence(words.tolist()))


def generate_independent_gaussian_arrays(
    labels: dict[str, int],
    *,
    generator_seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Diagnostic alternative: independent centre-scaled Gaussians, no orthogonalize.

    At intended ρ=0 this preserves E[product]=0 in population while allowing
    finite-sample products comparable to within-donor ATAC shuffle of the same
    draws. Labelled diagnostic alternative — not a frozen S9 replacement.
    """
    from p22.eval.s9_analytic import N_FEATURES, donor_ids

    n_cells = N_DONORS * CELLS_PER_DONOR
    rna = np.zeros((n_cells, N_FEATURES), dtype=np.float64)
    atac = np.zeros((n_cells, N_FEATURES), dtype=np.float64)
    donor_col = np.empty(n_cells, dtype=object)
    row = 0
    for donor in donor_ids():
        for _c in range(CELLS_PER_DONOR):
            donor_col[row] = donor
            row += 1
        rows = np.flatnonzero(donor_col == donor)
        for channel in range(N_PLANTED_CHANNELS):
            z = _centre_scale(
                _stable_rng(generator_seed, donor, channel, "z_indep").normal(
                    size=CELLS_PER_DONOR
                )
            )
            w = _centre_scale(
                _stable_rng(generator_seed, donor, channel, "w_indep").normal(
                    size=CELLS_PER_DONOR
                )
            )
            # No orthogonalization; no ρ·z term (ρ=0 plant). Labels unused here.
            _ = labels[donor]
            rna[rows, channel] = z
            atac[rows, channel] = w
        donor_shift = _stable_rng(
            generator_seed, donor, "nuisance_shift_indep"
        ).normal(size=N_FEATURES - N_PLANTED_CHANNELS)
        for j, channel in enumerate(range(N_PLANTED_CHANNELS, N_FEATURES)):
            rna[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "rna_n_indep").normal(
                    size=CELLS_PER_DONOR
                )
                + 0.5 * donor_shift[j]
            )
            atac[rows, channel] = (
                _stable_rng(generator_seed, donor, channel, "atac_n_indep").normal(
                    size=CELLS_PER_DONOR
                )
                + 0.5 * donor_shift[j]
            )
    return rna, atac, donor_col


def reproduce_prior_orthogonality(
    labels: dict[str, int],
) -> tuple[dict[str, Any], int]:
    """Reproduce NULL_INVARIANCE_DIAGNOSTIC.json; count 1 generator draw."""
    rna, atac, donor, _, _ = generate_analytic_arrays(
        labels, rho=0.0, generator_seed=DECISION_GENERATOR_SEED
    )
    draws = 1
    orig_means = _donor_channel_product_means(rna, atac, donor)
    orig_max_abs = float(np.max(np.abs(orig_means)))

    shuffled_abs_means: list[float] = []
    shuffled_max_abs = 0.0
    for seed in PAIRING_SHUFFLE_SEEDS:
        shuf = permute_atac_within_donor(atac, donor, seed=int(seed))
        means = _donor_channel_product_means(rna, shuf, donor)
        abs_mean = float(np.mean(np.abs(means)))
        shuffled_abs_means.append(abs_mean)
        shuffled_max_abs = max(shuffled_max_abs, float(np.max(np.abs(means))))

    prior = json.loads(PRIOR_NULL_DIAG.read_text())
    result = {
        "original_max_abs_donor_channel_product_mean": orig_max_abs,
        "shuffled_mean_abs_donor_channel_product_mean": float(
            np.mean(shuffled_abs_means)
        ),
        "shuffled_max_abs_donor_channel_product_mean": shuffled_max_abs,
        "shuffled_per_seed_mean_abs": shuffled_abs_means,
        "matches_prior_diagnostic": {
            "original_max_abs": math.isclose(
                orig_max_abs,
                float(prior["original_max_abs_donor_channel_product_mean"]),
                rel_tol=0.0,
                abs_tol=1e-30,
            ),
            "shuffled_mean_abs": math.isclose(
                float(np.mean(shuffled_abs_means)),
                float(prior["shuffled_mean_abs_donor_channel_product_mean"]),
                rel_tol=1e-12,
                abs_tol=1e-15,
            ),
            "shuffled_max_abs": math.isclose(
                shuffled_max_abs,
                float(prior["shuffled_max_abs_donor_channel_product_mean"]),
                rel_tol=1e-12,
                abs_tol=1e-15,
            ),
        },
        "prior_sha256": sha256_file(PRIOR_NULL_DIAG),
    }
    return result, draws


def analytic_exchangeability_notes() -> dict[str, Any]:
    """Derive what the ρ=0 construction and shuffle preserve or break."""
    return {
        "intended_claim": (
            "Software/mechanism control: detect planted within-cell RNA↔ATAC "
            "pairing via donor log-loss drop under within-donor ATAC shuffle."
        ),
        "pairing_statistic_tests": {
            "primary_object": (
                "Whether fitted predictions depend on within-donor cell pairing "
                "of RNA and ATAC rows (cell-pair exchangeability under the "
                "intervention)."
            ),
            "not_primarily": (
                "Label relevance of unimodal features; that is gated separately "
                "by the unimodal marginal BA ≤ 0.60 check."
            ),
            "mixture_caveat": (
                "If the generative null is not exchangeable under the same "
                "shuffle, a PAIRING_POSITIVE at ρ=0 can reflect broken "
                "exchangeability (exact orthogonality) rather than planted "
                "pairing or label leak."
            ),
        },
        "rho0_construction": {
            "planted": (
                "ATAC_k = w with w forced exactly orthogonal to RNA_k=z "
                "(after centre/scale). Sample mean product per donor×channel "
                "is machine-zero (~1e-16), stronger than population "
                "independence E[z·w]=0."
            ),
            "nuisance": (
                "Independent RNA/ATAC nuisance channels plus a shared "
                "donor_shift; donor_shift is label-blind (RNG keyed by donor "
                "id, not y)."
            ),
            "label_term": (
                "The (2y−1)·ρ·z term vanishes at ρ=0, so planted channels "
                "carry no designed label signal."
            ),
        },
        "within_donor_atac_shuffle": {
            "preserves": [
                "Within-donor ATAC row multiset (exact marginals)",
                "Donor identity and labels",
                "RNA matrix unchanged",
                "Cross-donor isolation",
            ],
            "breaks": [
                "Exact planted-channel orthogonality (z ⊥ w cell pairing)",
                "Any learned dependence on the original cell alignment",
            ],
            "exchangeability": (
                "Under true conditional independence of RNA/ATAC given donor, "
                "within-donor ATAC permutation leaves the joint law invariant. "
                "The frozen ρ=0 construction places (z,w) on the measure-zero "
                "set {w⊥z}, which permutation leaves; therefore original and "
                "shuffled joints are not exchangeable under this generator."
            ),
        },
        "implication_for_fitted_null": (
            "Observed ρ=0 PAIRING_POSITIVE is consistent with a broken "
            "exchangeability null (models can exploit exact orthogonality that "
            "shuffle destroys). It does not by itself prove a neural leak of "
            "label information, nor does one positive 95% CI prove systematic "
            "error without a valid exchangeable reference."
        ),
    }


def orthogonal_seed_panel(
    labels: dict[str, int], seeds: Sequence[int]
) -> tuple[dict[str, Any], int]:
    """Characterize product means under frozen orthogonal ρ=0 across seeds."""
    draws = 0
    orig_max_abs: list[float] = []
    shuf_mean_abs: list[float] = []
    for gseed in seeds:
        rna, atac, donor, _, _ = generate_analytic_arrays(
            labels, rho=0.0, generator_seed=int(gseed)
        )
        draws += 1
        means = _donor_channel_product_means(rna, atac, donor)
        orig_max_abs.append(float(np.max(np.abs(means))))
        # One fixed shuffle seed per draw (not expanding shuffle×seed).
        shuf = permute_atac_within_donor(atac, donor, seed=int(PAIRING_SHUFFLE_SEEDS[0]))
        shuf_means = _donor_channel_product_means(rna, shuf, donor)
        shuf_mean_abs.append(float(np.mean(np.abs(shuf_means))))
    return {
        "n_seeds": len(seeds),
        "original_max_abs_max": float(np.max(orig_max_abs)),
        "original_max_abs_median": float(np.median(orig_max_abs)),
        "shuffled_mean_abs_mean": float(np.mean(shuf_mean_abs)),
        "shuffled_mean_abs_min": float(np.min(shuf_mean_abs)),
        "shuffled_mean_abs_max": float(np.max(shuf_mean_abs)),
        "all_original_near_machine_zero": bool(np.max(orig_max_abs) < 1e-12),
        "all_shuffled_far_from_zero": bool(np.min(shuf_mean_abs) > 1e-3),
    }, draws


def independent_gaussian_panel(
    labels: dict[str, int], seeds: Sequence[int]
) -> tuple[dict[str, Any], int]:
    """Independent-Gaussian diagnostic alternative vs its own shuffle."""
    draws = 0
    orig_mean_abs: list[float] = []
    shuf_mean_abs: list[float] = []
    ratio: list[float] = []
    for gseed in seeds:
        rna, atac, donor = generate_independent_gaussian_arrays(
            labels, generator_seed=int(gseed)
        )
        draws += 1  # counts as generator-only diagnostic draw
        means = _donor_channel_product_means(rna, atac, donor)
        o = float(np.mean(np.abs(means)))
        shuf = permute_atac_within_donor(atac, donor, seed=int(PAIRING_SHUFFLE_SEEDS[0]))
        s = float(np.mean(np.abs(_donor_channel_product_means(rna, shuf, donor))))
        orig_mean_abs.append(o)
        shuf_mean_abs.append(s)
        ratio.append(s / o if o > 1e-15 else float("inf"))
    return {
        "kind": "diagnostic_alternative_independent_gaussian_rho0",
        "not_s9_replacement": True,
        "n_seeds": len(seeds),
        "original_mean_abs_mean": float(np.mean(orig_mean_abs)),
        "original_mean_abs_std": float(np.std(orig_mean_abs)),
        "shuffled_mean_abs_mean": float(np.mean(shuf_mean_abs)),
        "shuffled_mean_abs_std": float(np.std(shuf_mean_abs)),
        "mean_shuffle_over_original_ratio": float(np.mean(ratio)),
        "exchangeability_approx": (
            "Under independent Gaussians, original and shuffled mean-|product| "
            "are the same order; ratio near 1 supports approximate "
            "exchangeability of this statistic (unlike exact orthogonalization)."
        ),
        "ratio_near_one": bool(0.5 <= float(np.mean(ratio)) <= 2.0),
    }, draws


def chance_ba_reference(*, n_donors: int = 24, n_class: int = 12) -> dict[str, Any]:
    """Exact finite-sample chance BA for balanced binary labels, threshold rule.

    Under pure chance prediction that assigns exactly n_class positives by
    randomly choosing n_class of n_donors (or equivalently random scores with
    balanced predicted classes), balanced accuracy equals ordinary accuracy for
    balanced labels: BA = (TP/n_class + TN/n_class) / 2 with TP+FP = n_class.
    Enumerate Hypergeometric: k ~ Hypergeometric(N=24, K=12, n=12) correct
    positives among predicted class-1; BA = k/12.
    """
    # P(K=k) for k=0..12; BA = k/12 when predicting exactly 12 positives.
    from math import comb

    total = comb(n_donors, n_class)
    probs: dict[str, float] = {}
    cdf_ge: dict[str, float] = {}
    for k in range(0, n_class + 1):
        # predicted-1 set of size 12 overlaps true-1 in k → BA = k/12
        # Hypergeometric: draw 12 from 24 with 12 success states
        p = comb(n_class, k) * comb(n_donors - n_class, n_class - k) / total
        ba = k / n_class
        key = f"{ba:.6f}"
        probs[key] = probs.get(key, 0.0) + p
    # P(BA >= t) for observed thresholds
    thresholds = [0.50, 0.60, MARGINAL_BA_MAX, 0.7083333333333334, 0.75]
    for t in thresholds:
        cdf_ge[f"P_BA_ge_{t}"] = float(
            sum(p for ba_s, p in probs.items() if float(ba_s) + 1e-15 >= t)
        )
    return {
        "model": (
            "Hypergeometric overlap of a size-12 predicted-positive set with "
            "12 true class-1 donors (balanced chance classifier)."
        ),
        "n_donors": n_donors,
        "n_per_class": n_class,
        "note": (
            "This is an independent-draw chance reference for a single balanced "
            "prediction vector. It is not the same as donor-cluster bootstrap "
            "of one fixed prediction vector (which resamples the same 24 donors)."
        ),
        "P_BA_ge": cdf_ge,
        "P_BA_eq_0.75": float(probs.get("0.750000", 0.0)),
        "P_BA_eq_0.666667_approx": float(
            sum(p for ba_s, p in probs.items() if abs(float(ba_s) - 2 / 3) < 1e-6)
        ),
    }


def donor_bootstrap_ba(
    labels: list[int],
    preds: list[int],
    *,
    n_draws: int = 2000,
    seed: int = 22,
) -> dict[str, Any]:
    """Resample the fixed 24-donor prediction vector (not independent redraws)."""
    y = np.asarray(labels, dtype=np.int64)
    p = np.asarray(preds, dtype=np.int64)
    n = y.size
    rng = np.random.default_rng(seed)
    bas: list[float] = []
    invalid = 0
    for _ in range(n_draws):
        idx = rng.integers(0, n, size=n)
        ys = y[idx]
        ps = p[idx]
        if len(set(ys.tolist())) < 2:
            invalid += 1
            continue
        bas.append(float(balanced_accuracy_score(ys, ps)))
    arr = np.asarray(bas, dtype=np.float64)
    return {
        "n_draws_requested": n_draws,
        "n_valid": int(arr.size),
        "n_invalid_single_class": invalid,
        "mean": float(arr.mean()) if arr.size else None,
        "ci95": (
            [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))]
            if arr.size
            else None
        ),
        "fraction_ba_gt_0_60": (
            float(np.mean(arr > MARGINAL_BA_MAX)) if arr.size else None
        ),
        "interpretation": (
            "Donor-cluster bootstrap of one saved prediction vector estimates "
            "uncertainty from resampling the same 24 donors; it does not "
            "simulate independent new donor draws from a chance classifier."
        ),
    }


def marginal_from_saved_predictions(s9_raw: Path) -> dict[str, Any]:
    """Quantify unimodal BA using saved ρ=1 screen sidecars (no refit)."""
    records = read_ledger_records(s9_raw)
    out: dict[str, Any] = {"rho": 1.0, "arms": {}}
    for model in ("logreg_rna", "logreg_atac"):
        pooled = _pool_donor_ba_from_predictions(
            records, stage="screen", rho=1.0, model=model
        )
        # Filenames: screen__{rho_int}__{generator_seed}__{fold}__{model}.donors.json
        donor_labels: list[int] = []
        donor_preds: list[int] = []
        for fold in range(3):
            path = (
                s9_raw
                / "donor_predictions"
                / f"screen__1__{DECISION_GENERATOR_SEED}__{fold}__{model}.donors.json"
            )
            if not path.is_file():
                raise NullAuditRefusal(
                    f"missing rho=1 sidecar for {model} fold {fold}: {path}"
                )
            payload = json.loads(path.read_text())
            if abs(float(payload.get("rho", -1)) - 1.0) >= 1e-12:
                raise NullAuditRefusal(f"expected rho=1 in {path}")
            dp = payload["donor_probabilities"]
            donor_labels.extend(int(x) for x in dp["label"])
            donor_preds.extend(int(x) for x in dp["prediction"])
        if len(donor_labels) != N_DONORS:
            raise NullAuditRefusal(
                f"{model}: expected {N_DONORS} donors, got {len(donor_labels)}"
            )
        boot = donor_bootstrap_ba(donor_labels, donor_preds, n_draws=2000, seed=22)
        out["arms"][model] = {
            "pooled_ba": pooled.get("ba"),
            "complete": pooled.get("complete"),
            "exceeds_marginal_max": (
                pooled.get("ba") is not None
                and float(pooled["ba"]) > MARGINAL_BA_MAX
            ),
            "donor_bootstrap": boot,
            "n_correct": int(
                sum(int(a == b) for a, b in zip(donor_labels, donor_preds, strict=True))
            ),
        }
    out["chance_independent_draw_reference"] = chance_ba_reference()
    out["distinction"] = {
        "independent_donor_draws": (
            "Chance hypergeometric reference: new random balanced predictions "
            "each time; P(BA≥0.75) and P(BA≥0.60) under pure chance."
        ),
        "repeated_resampling_of_24": (
            "Donor bootstrap: resamples the fixed observed prediction vector; "
            "CI reflects instability of that vector under donor resampling, "
            "not a new generative chance experiment."
        ),
        "marginal_failure_reading": (
            "Observed RNA BA=0.75 / ATAC≈0.708 can occur under chance for n=24 "
            "balanced donors with non-negligible probability; finite-sample "
            "nuisance association is plausible. This does not overturn INVALID "
            "(gate failed), nor prove a structural unimodal leak without a "
            "prospective chance-calibrated marginal rule."
        ),
    }
    return out


def candidate_null_decision(indep_panel: Mapping[str, Any]) -> dict[str, Any]:
    """Analytically justified candidate or NULL_DESIGN_UNRESOLVED."""
    if indep_panel.get("ratio_near_one"):
        return {
            "status": "CANDIDATE_DIAGNOSTIC_NULL",
            "id": "independent_gaussian_rho0_within_donor_shuffle_20261001",
            "statement": (
                "For a future software pairing-use control, generate planted "
                "channels as independent centre-scaled Gaussians at ρ_plant=0 "
                "(no exact orthogonalization). The fitted-mechanism null remains: "
                "within-donor ATAC shuffle must not yield PAIRING_POSITIVE for CA. "
                "Under this generator the product-mean statistic is approximately "
                "exchangeable under the same shuffle (ratio near 1 in the "
                "preregistered panel)."
            ),
            "role": (
                "Diagnostic alternative generator for exchangeability — not a "
                "successful replacement of frozen S9 and not authorization to "
                "rerun S9."
            ),
            "what_would_change_conclusion": [
                "Demonstration that independent-Gaussian ρ=0 still yields "
                "systematic PAIRING_POSITIVE under serial deterministic fits "
                "(would point past exchangeability to optimization/RNG).",
                "Analytic proof that another intervention (e.g. label-blind "
                "feature scramble) better matches the estimand.",
            ],
            "explicitly_not": [
                "No constant/Bernoulli BA band calibration from S9 outcomes",
                "No threshold chosen from observed S9 CI lowers",
                "No claim that this fixes unimodal marginal BA",
            ],
        }
    return {
        "status": "NULL_DESIGN_UNRESOLVED",
        "reason": (
            "Independent-Gaussian panel did not show approximate exchangeability "
            "of the product-mean statistic under shuffle; further analytic work "
            "required before proposing a candidate null."
        ),
    }


def update_attempt_counter(raw_root: Path, generator_draws: int) -> dict[str, Any]:
    path = raw_root / "attempt_counter.json"
    counter = json.loads(path.read_text())
    used = int(counter.get("generator_only_draws", 0)) + int(generator_draws)
    cap = int(counter.get("generator_only_cap", 256))
    if used > cap:
        raise NullAuditRefusal(f"generator draws {used} exceed cap {cap}")
    if int(counter.get("scientific_fit_attempts", 0)) != 0:
        raise NullAuditRefusal("scientific fits must remain 0 in R2")
    if int(counter.get("diagnostic_fit_attempts", 0)) != 0:
        raise NullAuditRefusal("diagnostic fits must remain 0 in R2")
    counter["generator_only_draws"] = used
    counter["r2_generator_draws_this_run"] = int(generator_draws)
    counter["r2_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    path.write_text(json.dumps(counter, indent=2) + "\n")
    return counter


def render_md(report: Mapping[str, Any]) -> str:
    repro = report["orthogonality_reproduction"]
    exch = report["exchangeability"]
    marg = report["marginal_uncertainty"]
    cand = report["candidate_null"]
    lines = [
        "# NULL_AUDIT — R2 null exchangeability and marginal diagnosis",
        "",
        f"**Disposition:** `{report['disposition']}`",
        f"**Date:** {report['date']}",
        f"**Generator-only draws this run:** {report['generator_draws_this_run']} "
        f"(cumulative {report['generator_draws_cumulative']} ≤ 256)",
        "**Research / diagnostic fits:** 0 / 0",
        f"**Shared S9 raw unchanged:** `{report['shared_raw_unchanged']}`",
        "",
        "## Seed schedule (committed before simulation)",
        "",
        "```json",
        json.dumps(SEED_SCHEDULE, indent=2),
        "```",
        "",
        "## 1. Reproduce exact-orthogonality / shuffle finding",
        "",
        f"- Original max |donor×channel product mean|: "
        f"`{repro['original_max_abs_donor_channel_product_mean']}`",
        f"- Shuffled mean |product mean| (seeds 4001–4016): "
        f"`{repro['shuffled_mean_abs_donor_channel_product_mean']}`",
        f"- Shuffled max |product mean|: "
        f"`{repro['shuffled_max_abs_donor_channel_product_mean']}`",
        f"- Matches prior NULL_INVARIANCE_DIAGNOSTIC: "
        f"`{all(repro['matches_prior_diagnostic'].values())}`",
        "",
        "## 2. Exchangeability: what is preserved vs broken",
        "",
        f"**Pairing statistic tests:** {exch['pairing_statistic_tests']['primary_object']}",
        "",
        f"**Mixture caveat:** {exch['pairing_statistic_tests']['mixture_caveat']}",
        "",
        "### Preserved under within-donor ATAC shuffle",
        "",
    ]
    for item in exch["within_donor_atac_shuffle"]["preserves"]:
        lines.append(f"- {item}")
    lines.extend(["", "### Broken", ""])
    for item in exch["within_donor_atac_shuffle"]["breaks"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"**Exchangeability verdict:** {exch['within_donor_atac_shuffle']['exchangeability']}",
            "",
            f"**Implication:** {exch['implication_for_fitted_null']}",
            "",
            "## 3. Orthogonal vs independent-Gaussian panels",
            "",
            f"- Orthogonal ρ=0 panel ({report['orthogonal_panel']['n_seeds']} seeds): "
            f"all original near machine zero = "
            f"`{report['orthogonal_panel']['all_original_near_machine_zero']}`; "
            f"all shuffled far from zero = "
            f"`{report['orthogonal_panel']['all_shuffled_far_from_zero']}`",
            f"- Independent-Gaussian diagnostic panel "
            f"({report['independent_gaussian_panel']['n_seeds']} seeds): "
            f"mean |product| original="
            f"`{report['independent_gaussian_panel']['original_mean_abs_mean']:.6f}` "
            f"shuffled="
            f"`{report['independent_gaussian_panel']['shuffled_mean_abs_mean']:.6f}` "
            f"ratio="
            f"`{report['independent_gaussian_panel']['mean_shuffle_over_original_ratio']:.4f}` "
            f"(near one = "
            f"`{report['independent_gaussian_panel']['ratio_near_one']}`)",
            "",
            "## 4. Marginal BA uncertainty (saved ρ=1 predictions; no refit)",
            "",
            f"- logreg_rna pooled BA: `{marg['arms']['logreg_rna']['pooled_ba']}`",
            f"- logreg_atac pooled BA: `{marg['arms']['logreg_atac']['pooled_ba']}`",
            f"- Gate threshold: `{MARGINAL_BA_MAX}` (INVALID retained; not overturned)",
            "",
            "### Independent-draw chance reference (Hypergeometric, n=24 balanced)",
            "",
        ]
    )
    for k, v in marg["chance_independent_draw_reference"]["P_BA_ge"].items():
        lines.append(f"- `{k}` = `{v:.6f}`")
    lines.extend(
        [
            "",
            "### Donor-cluster bootstrap of the fixed saved prediction vectors",
            "",
            f"- RNA BA bootstrap mean / 95% CI: "
            f"`{marg['arms']['logreg_rna']['donor_bootstrap']['mean']}` / "
            f"`{marg['arms']['logreg_rna']['donor_bootstrap']['ci95']}`",
            f"- ATAC BA bootstrap mean / 95% CI: "
            f"`{marg['arms']['logreg_atac']['donor_bootstrap']['mean']}` / "
            f"`{marg['arms']['logreg_atac']['donor_bootstrap']['ci95']}`",
            "",
            f"**Distinction:** {marg['distinction']['marginal_failure_reading']}",
            "",
            "## 5. Candidate null",
            "",
            f"**Status:** `{cand['status']}`",
            "",
        ]
    )
    if cand["status"] == "CANDIDATE_DIAGNOSTIC_NULL":
        lines.extend(
            [
                f"- ID: `{cand['id']}`",
                f"- Statement: {cand['statement']}",
                f"- Role: {cand['role']}",
                "",
                "Not authorized: S9 replacement, threshold retune, or research fits.",
            ]
        )
    else:
        lines.append(f"- Reason: {cand.get('reason')}")
    lines.extend(
        [
            "",
            "## Invariants",
            "",
            "- Frozen S9 scientific label remains **`INVALID`**.",
            "- Primary `B_NULL`; S7 `INVALID`; prior S8 `NO FIT`.",
            "- Zero model fits in R2; no writes through shared S9 raw.",
            "",
            "## Next",
            "",
            "Checkpoint A (R1+R2); then independent R3/R4/R5 as scheduled.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def run(*, s9_raw: Path, out_dir: Path, raw_root: Path) -> dict[str, Any]:
    if not s9_raw.is_dir():
        raise NullAuditRefusal(f"S9 raw missing: {s9_raw}")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)

    before = _fingerprint_tree(s9_raw)
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    total_draws = 0

    # Persist seed schedule hash before draws (schedule already module-constant).
    schedule_path = out_dir / "R2_SEED_SCHEDULE.json"
    schedule_path.write_text(json.dumps(SEED_SCHEDULE, indent=2) + "\n")
    schedule_sha = sha256_file(schedule_path)

    repro, d1 = reproduce_prior_orthogonality(labels)
    total_draws += d1
    if not all(repro["matches_prior_diagnostic"].values()):
        raise NullAuditRefusal(
            f"failed to reproduce prior null diagnostic: {repro['matches_prior_diagnostic']}"
        )

    exch = analytic_exchangeability_notes()

    ortho_panel, d2 = orthogonal_seed_panel(
        labels, SEED_SCHEDULE["orthogonal_rho0_generator_seeds"]
    )
    total_draws += d2

    indep_panel, d3 = independent_gaussian_panel(
        labels, SEED_SCHEDULE["independent_gaussian_generator_seeds"]
    )
    total_draws += d3

    if total_draws > int(SEED_SCHEDULE["max_generator_array_draws"]):
        raise NullAuditRefusal(
            f"draw budget exceeded: {total_draws} > "
            f"{SEED_SCHEDULE['max_generator_array_draws']}"
        )

    marginal = marginal_from_saved_predictions(s9_raw)
    candidate = candidate_null_decision(indep_panel)

    after = _fingerprint_tree(s9_raw)
    _assert_no_write(before, after)

    counter = update_attempt_counter(raw_root, total_draws)

    report: dict[str, Any] = {
        "disposition": "NULL_AUDIT_PASS",
        "date": "2026-10-01",
        "kind": "r2_null_exchangeability_marginal_diagnosis",
        "research_fits": 0,
        "diagnostic_fits": 0,
        "generator_draws_this_run": total_draws,
        "generator_draws_cumulative": counter["generator_only_draws"],
        "generator_draw_cap": counter["generator_only_cap"],
        "seed_schedule_sha256": schedule_sha,
        "seed_schedule": SEED_SCHEDULE,
        "orthogonality_reproduction": repro,
        "exchangeability": exch,
        "orthogonal_panel": ortho_panel,
        "independent_gaussian_panel": indep_panel,
        "marginal_uncertainty": marginal,
        "candidate_null": candidate,
        "shared_s9_raw": str(s9_raw),
        "shared_raw_unchanged": True,
        "shared_raw_tree_sha256": before["tree_sha256"],
        "scientific_label_retained": "INVALID",
        "limits": [
            "Zero model fits; no S9 replacement claimed.",
            "Independent-Gaussian null is a diagnostic alternative only.",
            "Finite-sample chance BA reference does not overturn INVALID gate.",
            "Does not establish the neural outcome's unique cause.",
        ],
    }

    json_path = out_dir / "null_audit.json"
    md_path = out_dir / "NULL_AUDIT.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_md(report))

    raw_summary = raw_root / "r2_null_audit_summary.json"
    raw_summary.write_text(
        json.dumps(
            {
                "disposition": report["disposition"],
                "generator_draws_this_run": total_draws,
                "candidate_null_status": candidate["status"],
                "null_audit_json_sha256": sha256_file(json_path),
                "null_audit_md_sha256": sha256_file(md_path),
                "seed_schedule_sha256": schedule_sha,
                "shared_raw_tree_sha256": before["tree_sha256"],
            },
            indent=2,
        )
        + "\n"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s9-raw", type=Path, default=DEFAULT_S9_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    args = parser.parse_args(argv)
    report = run(s9_raw=args.s9_raw, out_dir=args.out_dir, raw_root=args.raw_root)
    print(
        json.dumps(
            {
                "disposition": report["disposition"],
                "generator_draws": report["generator_draws_this_run"],
                "candidate_null": report["candidate_null"]["status"],
                "shared_raw_unchanged": report["shared_raw_unchanged"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
