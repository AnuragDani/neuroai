"""Frozen S7 screen evaluation gates (no fitting).

Decides coverage, rho=0 null, rho=1 marginal leakage, and the N4
``CA_FAVOURED`` regime on the fixed rho=1 decision cell. Does not select a
best rho. Pairing-PC and confirmation remain separate stages.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from p22.eval.s7_ledger import S7_MODELS, S7_N_FOLDS, S7_RHO_GRID

# N4 decision-tree non-attention arms (single-view logregs are marginal checks).
S7_NON_ATTENTION: tuple[str, ...] = (
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
    "logreg_concat",
)
S7_SINGLE_VIEW: tuple[str, ...] = ("logreg_rna", "logreg_atac")
S7_DECISION_RHO = 1.0
S7_NULL_RHO = 0.0
S7_NULL_BA_RANGE = (0.35, 0.65)
S7_MARGINAL_BA_MAX = 0.60
S7_CA_MARGIN = 0.07
S7_LINEAR_TIE = 0.03

SCREEN_INCOMPLETE = "INCOMPLETE"
SCREEN_INVALID = "INVALID"
SCREEN_NEGATIVE = "CONTROL_NEGATIVE"
SCREEN_CA_FAVOURED = "CA_FAVOURED_SCREEN"


def fold_cell_ids(
    metadata_index: Sequence[Any] | np.ndarray,
    train_rows: np.ndarray,
    val_rows: np.ndarray,
    test_rows: np.ndarray,
) -> np.ndarray:
    """Map stable ``NNInputs.metadata.index`` through fold row order.

    ``prepare_nn_fold`` builds tensors as ``[train; val; test]``. FoldArrays has
    no cell_id field, so callers must pass this vector into
    ``plant_covariance(..., cell_ids=...)``.
    """
    index = np.asarray(metadata_index)
    source = np.concatenate(
        [
            np.asarray(train_rows, dtype=np.int64),
            np.asarray(val_rows, dtype=np.int64),
            np.asarray(test_rows, dtype=np.int64),
        ]
    )
    if source.size == 0:
        raise ValueError("fold row order is empty")
    if int(source.min()) < 0 or int(source.max()) >= index.shape[0]:
        raise ValueError("fold row indices out of range for metadata.index")
    return index[source]


def _ok_frame(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in records:
        if raw.get("status") != "ok":
            continue
        row = dict(raw)
        row["rho"] = float(row["rho"])
        row["fold"] = int(row["fold"])
        row["model"] = str(row["model"])
        row["donor_balanced_accuracy"] = float(row["donor_balanced_accuracy"])
        out.append(row)
    return out


def screen_coverage(
    records: Sequence[Mapping[str, Any]],
    *,
    rho_grid: tuple[float, ...] = S7_RHO_GRID,
    n_folds: int = S7_N_FOLDS,
    models: tuple[str, ...] = S7_MODELS,
) -> dict[str, Any]:
    """Require every predeclared (rho, fold, model) cell to complete successfully."""
    ok = _ok_frame(records)
    present = {(r["rho"], r["fold"], r["model"]) for r in ok}
    expected = [
        (float(rho), fold, model)
        for rho in rho_grid
        for fold in range(int(n_folds))
        for model in models
    ]
    missing = [
        {"rho": rho, "fold": fold, "model": model}
        for rho, fold, model in expected
        if (rho, fold, model) not in present
    ]
    return {
        "complete": len(missing) == 0,
        "n_expected": len(expected),
        "n_ok": len(present),
        "missing": missing,
    }


def _mean_ba_by_model(ok: Sequence[Mapping[str, Any]], rho: float) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for row in ok:
        if float(row["rho"]) != float(rho):
            continue
        buckets.setdefault(str(row["model"]), []).append(float(row["donor_balanced_accuracy"]))
    return {model: float(np.mean(vals)) for model, vals in buckets.items()}


def null_check(
    records: Sequence[Mapping[str, Any]],
    *,
    rho: float = S7_NULL_RHO,
    ba_range: tuple[float, float] = S7_NULL_BA_RANGE,
    models: tuple[str, ...] = S7_MODELS,
) -> dict[str, Any]:
    """Rho=0: every complete arm's mean-fold donor BA must lie in [0.35, 0.65]."""
    means = _mean_ba_by_model(_ok_frame(records), rho)
    low, high = float(ba_range[0]), float(ba_range[1])
    per_model: dict[str, Any] = {}
    failures: list[str] = []
    for model in models:
        if model not in means:
            per_model[model] = None
            failures.append(model)
            continue
        value = means[model]
        ok = low <= value <= high
        per_model[model] = round(value, 6)
        if not ok:
            failures.append(model)
    return {
        "rho": float(rho),
        "range": [low, high],
        "mean_fold_donor_ba": per_model,
        "passed": len(failures) == 0,
        "failures": failures,
    }


def marginal_check(
    records: Sequence[Mapping[str, Any]],
    *,
    rho: float = S7_DECISION_RHO,
    ba_max: float = S7_MARGINAL_BA_MAX,
    models: tuple[str, ...] = S7_SINGLE_VIEW,
) -> dict[str, Any]:
    """Rho=1: single-view logreg donor BA must be ≤0.60 (no marginal shortcut)."""
    means = _mean_ba_by_model(_ok_frame(records), rho)
    per_model: dict[str, Any] = {}
    failures: list[str] = []
    for model in models:
        if model not in means:
            per_model[model] = None
            failures.append(model)
            continue
        value = means[model]
        per_model[model] = round(value, 6)
        if value > float(ba_max):
            failures.append(model)
    return {
        "rho": float(rho),
        "ba_max": float(ba_max),
        "mean_fold_donor_ba": per_model,
        "passed": len(failures) == 0,
        "failures": failures,
    }


def rho1_regime(
    records: Sequence[Mapping[str, Any]],
    *,
    rho: float = S7_DECISION_RHO,
    margin: float = S7_CA_MARGIN,
    linear_tie: float = S7_LINEAR_TIE,
    non_attention: tuple[str, ...] = S7_NON_ATTENTION,
) -> dict[str, Any]:
    """Apply the existing N4 ``CA_FAVOURED`` decision tree at fixed rho=1."""
    means = _mean_ba_by_model(_ok_frame(records), rho)
    present = [m for m in S7_MODELS if m in means]
    best = float(max(means[m] for m in present)) if present else float("nan")
    non = [m for m in non_attention if m in means]
    best_non = float(max(means[m] for m in non)) if non else float("nan")
    cross = float(means["cross_attention"]) if "cross_attention" in means else float("nan")
    mlp = [m for m in ("rna_atac_concat", "gated_fusion") if m in means]

    if "logreg_concat" in means and float(means["logreg_concat"]) >= best - float(linear_tie):
        label = "LINEAR_SUFFICIENT"
    elif non and np.isfinite(cross) and cross - best_non >= float(margin):
        label = "CA_FAVOURED"
    elif mlp and float(max(means[m] for m in mlp)) >= best - float(linear_tie):
        label = "MLP_FAVOURED"
    else:
        label = "NONE_DETECT"

    gap = (
        round(cross - best_non, 6)
        if np.isfinite(cross) and np.isfinite(best_non)
        else None
    )
    return {
        "rho": float(rho),
        "regime": label,
        "ca_favoured": label == "CA_FAVOURED",
        "mean_fold_donor_ba": {k: round(float(v), 6) for k, v in means.items()},
        "cross_attention_minus_best_non_attention": gap,
        "best_non_attention": None if not non else max(non, key=lambda m: means[m]),
        "n_models_scored": len(present),
    }


def evaluate_screen(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Combine coverage + controls + rho=1 regime into a screen-stage label.

    ``CA_FAVOURED_SCREEN`` means the screen cell is eligible for pairing-PC; the
    final runbook label ``CA_FAVOURED_CONTROL`` still requires PC (and is not
    assigned here). Null/marginal failure is ``INVALID`` (design failure), not a
    favourable method claim. Incomplete coverage never passes.
    """
    coverage = screen_coverage(records)
    if not coverage["complete"]:
        return {
            "screen_label": SCREEN_INCOMPLETE,
            "eligible_for_pairing_pc": False,
            "coverage": coverage,
            "null_check": None,
            "marginal_check": None,
            "rho1_regime": None,
        }

    null = null_check(records)
    marginal = marginal_check(records)
    regime = rho1_regime(records)

    if not null["passed"] or not marginal["passed"]:
        label = SCREEN_INVALID
        eligible = False
    elif regime["ca_favoured"]:
        label = SCREEN_CA_FAVOURED
        eligible = True
    else:
        label = SCREEN_NEGATIVE
        eligible = False

    return {
        "screen_label": label,
        "eligible_for_pairing_pc": eligible,
        "coverage": coverage,
        "null_check": null,
        "marginal_check": marginal,
        "rho1_regime": regime,
    }
