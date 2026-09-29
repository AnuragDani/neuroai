"""S7 confirmation trial-contrast builder (no new fits).

Pools five disjoint outer-fold held-out donor predictions once per generator
seed, then forms paired CA−baseline donor balanced-accuracy contrasts under
shared bootstrap draws. Feeds :func:`evaluate_confirmation`. Does not search
seeds or retune. Insufficient valid draws map to ``CONFIRM_INCOMPLETE``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from p22.eval.metrics import balanced_accuracy
from p22.eval.s7_confirmation import (
    CONFIRM_INCOMPLETE,
    CONFIRM_SKIPPED,
    S7_CONFIRM_SEEDS,
    confirmation_coverage,
    enumerate_confirmation_jobs,
    evaluate_confirmation,
)
from p22.eval.s7_pairing import (
    S7_BOOTSTRAP_DRAWS,
    S7_BOOTSTRAP_LEVEL,
    S7_BOOTSTRAP_SEED,
    S7_MIN_VALID_DRAWS,
)
from p22.eval.s7_screen import S7_NON_ATTENTION

S7_CONFIRM_CA = "cross_attention"
S7_CONFIRM_THRESHOLD = 0.5
S7_CONFIRM_STAGE = "confirm"


def donor_table_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise a donor_probabilities dict-of-lists into aligned arrays."""
    if not {"donor_id", "probability"}.issubset(payload):
        raise ValueError("donor payload needs donor_id and probability")
    donors = [str(d) for d in payload["donor_id"]]
    probs = [float(p) for p in payload["probability"]]
    if "label" in payload:
        labels = [float(y) for y in payload["label"]]
    elif "y_true" in payload:
        labels = [float(y) for y in payload["y_true"]]
    else:
        raise ValueError("donor payload needs label or y_true")
    if not (len(donors) == len(probs) == len(labels)):
        raise ValueError(
            f"donor payload length mismatch donors={len(donors)} "
            f"probs={len(probs)} labels={len(labels)}"
        )
    if len(donors) != len(set(donors)):
        raise ValueError("donor payload has duplicate donor_id")
    order = sorted(range(len(donors)), key=lambda i: donors[i])
    return {
        "donor_ids": [donors[i] for i in order],
        "y_true": [labels[i] for i in order],
        "p": [probs[i] for i in order],
    }


def load_donor_predictions(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return donor table from inline payload or ``donor_predictions_path``."""
    inline = record.get("donor_probabilities")
    if inline is not None:
        return donor_table_from_payload(inline)
    path = record.get("donor_predictions_path")
    if not path:
        return None
    blob = json.loads(Path(path).read_text(encoding="utf-8"))
    if "donor_probabilities" in blob:
        return donor_table_from_payload(blob["donor_probabilities"])
    return donor_table_from_payload(blob)


def save_donor_predictions(
    record: Mapping[str, Any],
    prediction_dir: Path | str,
) -> Path | None:
    """Persist donor probabilities for later confirmation contrasts."""
    preds = record.get("donor_probabilities")
    if preds is None:
        return None
    root = Path(prediction_dir)
    root.mkdir(parents=True, exist_ok=True)
    fit_id = str(record["fit_id"]).replace("|", "__")
    path = root / f"{fit_id}.donors.json"
    payload = {
        "fit_id": record["fit_id"],
        "stage": record.get("stage"),
        "rho": record.get("rho"),
        "generator_seed": record.get("generator_seed"),
        "fold": record.get("fold"),
        "model": record.get("model"),
        "donor_probabilities": preds,
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def pool_trial_model_tables(
    records: Sequence[Mapping[str, Any]],
    *,
    generator_seed: int,
    models: Sequence[str],
) -> dict[str, Any]:
    """Pool disjoint-fold held-out donors once per model for one trial seed.

    Missing models or duplicate donors across folds refuse with incomplete.
    """
    by_model: dict[str, list[Mapping[str, Any]]] = {m: [] for m in models}
    for raw in records:
        if int(raw.get("generator_seed", -1)) != int(generator_seed):
            continue
        if raw.get("status") != "ok":
            continue
        model = str(raw["model"])
        if model not in by_model:
            continue
        table = load_donor_predictions(raw)
        if table is None:
            return {
                "complete": False,
                "reason": f"missing donor predictions for {raw.get('fit_id')}",
                "tables": {},
                "n_donors": 0,
            }
        by_model[model].append(table)

    tables: dict[str, dict[str, Any]] = {}
    n_donors: int | None = None
    reference_donors: list[str] | None = None
    reference_labels: list[float] | None = None
    for model in models:
        chunks = by_model[model]
        if not chunks:
            return {
                "complete": False,
                "reason": f"no ok records for model {model} seed {generator_seed}",
                "tables": {},
                "n_donors": 0,
            }
        donor_ids: list[str] = []
        y_true: list[float] = []
        p: list[float] = []
        for chunk in chunks:
            donor_ids.extend(chunk["donor_ids"])
            y_true.extend(chunk["y_true"])
            p.extend(chunk["p"])
        if len(donor_ids) != len(set(donor_ids)):
            return {
                "complete": False,
                "reason": f"duplicate donors across folds for {model} seed {generator_seed}",
                "tables": {},
                "n_donors": 0,
            }
        order = sorted(range(len(donor_ids)), key=lambda i: donor_ids[i])
        sorted_donors = [donor_ids[i] for i in order]
        sorted_y = [y_true[i] for i in order]
        sorted_p = [p[i] for i in order]
        if reference_donors is None:
            reference_donors = sorted_donors
            reference_labels = sorted_y
            n_donors = len(sorted_donors)
        else:
            if sorted_donors != reference_donors:
                return {
                    "complete": False,
                    "reason": f"donor set mismatch for {model} vs CA pool",
                    "tables": {},
                    "n_donors": 0,
                }
            if sorted_y != reference_labels:
                return {
                    "complete": False,
                    "reason": f"label mismatch for {model} vs CA pool",
                    "tables": {},
                    "n_donors": 0,
                }
        tables[model] = {
            "donor_ids": sorted_donors,
            "y_true": sorted_y,
            "p": sorted_p,
        }

    return {
        "complete": True,
        "reason": None,
        "tables": tables,
        "n_donors": int(n_donors or 0),
        "donor_ids": list(reference_donors or []),
        "y_true": list(reference_labels or []),
    }


def mean_fold_donor_ba(
    records: Sequence[Mapping[str, Any]],
    *,
    generator_seed: int,
    models: Sequence[str],
) -> dict[str, float | None]:
    """Descriptive mean of per-fold donor BA (not the pooled estimand)."""
    buckets: dict[str, list[float]] = {m: [] for m in models}
    for raw in records:
        if int(raw.get("generator_seed", -1)) != int(generator_seed):
            continue
        if raw.get("status") != "ok":
            continue
        model = str(raw["model"])
        if model not in buckets:
            continue
        value = raw.get("donor_balanced_accuracy")
        if value is None:
            continue
        buckets[model].append(float(value))
    return {
        model: (None if not vals else float(np.mean(vals)))
        for model, vals in buckets.items()
    }


def _ba_from_probs(
    y_true: np.ndarray,
    probs: np.ndarray,
    index: np.ndarray | None = None,
    *,
    threshold: float = S7_CONFIRM_THRESHOLD,
) -> float | None:
    truth = y_true if index is None else y_true[index]
    p = probs if index is None else probs[index]
    pred = (p >= float(threshold)).astype(int)
    metric = balanced_accuracy(truth, pred)
    return None if not metric.applicable else float(metric.value)


def paired_ba_contrast(
    y_true: Sequence[float] | np.ndarray,
    p_ca: Sequence[float] | np.ndarray,
    p_base: Sequence[float] | np.ndarray,
    *,
    draw_indices: np.ndarray,
    min_valid: int = S7_MIN_VALID_DRAWS,
    level: float = S7_BOOTSTRAP_LEVEL,
    threshold: float = S7_CONFIRM_THRESHOLD,
) -> dict[str, Any]:
    """CA − baseline donor BA contrast under predeclared shared draw indices.

    Single-class draws are counted as failed and never redrawn. Fewer than
    ``min_valid`` finite draws => incomplete (not a success).
    """
    y = np.asarray(y_true, dtype=np.float64).reshape(-1)
    ca = np.asarray(p_ca, dtype=np.float64).reshape(-1)
    base = np.asarray(p_base, dtype=np.float64).reshape(-1)
    if not (y.size == ca.size == base.size):
        raise ValueError(
            f"length mismatch y={y.size} ca={ca.size} base={base.size}"
        )
    n = int(y.size)
    if draw_indices.ndim != 2 or draw_indices.shape[1] != n:
        raise ValueError(
            f"draw_indices shape {draw_indices.shape} incompatible with n={n}"
        )
    estimate_full = None
    ca_ba = _ba_from_probs(y, ca, threshold=threshold)
    base_ba = _ba_from_probs(y, base, threshold=threshold)
    if ca_ba is not None and base_ba is not None:
        estimate_full = float(ca_ba - base_ba)

    replicates: list[float] = []
    n_failed = 0
    for row in draw_indices:
        idx = np.asarray(row, dtype=np.int64)
        left = _ba_from_probs(y, ca, idx, threshold=threshold)
        right = _ba_from_probs(y, base, idx, threshold=threshold)
        if left is None or right is None:
            n_failed += 1
            continue
        replicates.append(float(left - right))

    n_valid = len(replicates)
    incomplete = n_valid < int(min_valid) or estimate_full is None
    if n_valid == 0 or estimate_full is None:
        return {
            "estimate": estimate_full,
            "lower": None,
            "upper": None,
            "level": float(level),
            "n_donors": n,
            "n_draws_requested": int(draw_indices.shape[0]),
            "n_valid": n_valid,
            "n_failed": n_failed,
            "incomplete": True,
            "reason": (
                "full-sample BA not applicable"
                if estimate_full is None
                else "every bootstrap draw failed"
            ),
        }
    arr = np.asarray(replicates, dtype=np.float64)
    tail = (1.0 - float(level)) / 2.0
    lower, upper = np.percentile(arr, [100.0 * tail, 100.0 * (1.0 - tail)])
    return {
        "estimate": float(estimate_full),
        "lower": float(lower),
        "upper": float(upper),
        "level": float(level),
        "n_donors": n,
        "n_draws_requested": int(draw_indices.shape[0]),
        "n_valid": n_valid,
        "n_failed": n_failed,
        "incomplete": incomplete,
        "reason": (
            None
            if not incomplete
            else f"insufficient valid draws: {n_valid} < {int(min_valid)}"
        ),
    }


def shared_bootstrap_indices(
    n_donors: int,
    *,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    seed: int = S7_BOOTSTRAP_SEED,
) -> np.ndarray:
    """Predeclare paired shared donor-resample indices for one trial."""
    if n_donors < 1:
        raise ValueError(f"n_donors must be >= 1, got {n_donors}")
    if n_draws < 1:
        raise ValueError(f"n_draws must be >= 1, got {n_draws}")
    rng = np.random.default_rng(int(seed))
    return rng.integers(0, n_donors, size=(int(n_draws), int(n_donors)))


def build_one_trial_contrasts(
    records: Sequence[Mapping[str, Any]],
    *,
    generator_seed: int,
    baselines: tuple[str, ...] = S7_NON_ATTENTION,
    ca_model: str = S7_CONFIRM_CA,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    bootstrap_seed: int = S7_BOOTSTRAP_SEED,
    min_valid: int = S7_MIN_VALID_DRAWS,
) -> dict[str, Any]:
    """Build CA−baseline contrasts for one confirmation generator seed."""
    models = (ca_model, *baselines)
    pooled = pool_trial_model_tables(
        records, generator_seed=generator_seed, models=models
    )
    mean_fold = mean_fold_donor_ba(
        records, generator_seed=generator_seed, models=models
    )
    if not pooled["complete"]:
        return {
            "generator_seed": int(generator_seed),
            "complete": False,
            "reason": pooled["reason"],
            "contrasts": {},
            "mean_fold_donor_ba": mean_fold,
            "n_donors": 0,
        }
    tables = pooled["tables"]
    y_true = tables[ca_model]["y_true"]
    p_ca = tables[ca_model]["p"]
    n_donors = int(pooled["n_donors"])
    if n_donors < 2:
        return {
            "generator_seed": int(generator_seed),
            "complete": False,
            "reason": f"donor bootstrap needs at least two donors, got {n_donors}",
            "contrasts": {},
            "mean_fold_donor_ba": mean_fold,
            "n_donors": n_donors,
        }
    draws = shared_bootstrap_indices(
        n_donors, n_draws=n_draws, seed=bootstrap_seed
    )
    contrasts: dict[str, dict[str, Any]] = {}
    incomplete_any = False
    for name in baselines:
        row = paired_ba_contrast(
            y_true,
            p_ca,
            tables[name]["p"],
            draw_indices=draws,
            min_valid=min_valid,
        )
        contrasts[name] = {
            "estimate": row["estimate"],
            "lower": row["lower"],
            "upper": row["upper"],
            "n_valid": row["n_valid"],
            "n_failed": row["n_failed"],
            "incomplete": row["incomplete"],
            "reason": row["reason"],
        }
        if row["incomplete"]:
            incomplete_any = True
    return {
        "generator_seed": int(generator_seed),
        "complete": not incomplete_any,
        "reason": (
            None
            if not incomplete_any
            else "one or more baseline contrasts incomplete"
        ),
        "contrasts": contrasts,
        "mean_fold_donor_ba": mean_fold,
        "pooled_donor_ba": {
            model: _ba_from_probs(
                np.asarray(tables[model]["y_true"], dtype=np.float64),
                np.asarray(tables[model]["p"], dtype=np.float64),
            )
            for model in models
        },
        "n_donors": n_donors,
        "bootstrap": {
            "draws": int(n_draws),
            "seed": int(bootstrap_seed),
            "paired_shared_draws": True,
            "min_valid": int(min_valid),
        },
    }


def build_trial_contrasts(
    records: Sequence[Mapping[str, Any]],
    *,
    seeds: tuple[int, ...] = S7_CONFIRM_SEEDS,
    baselines: tuple[str, ...] = S7_NON_ATTENTION,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    bootstrap_seed: int = S7_BOOTSTRAP_SEED,
    min_valid: int = S7_MIN_VALID_DRAWS,
) -> list[dict[str, Any]]:
    """Build one trial-contrast row per frozen confirmation seed."""
    return [
        build_one_trial_contrasts(
            records,
            generator_seed=int(seed),
            baselines=baselines,
            n_draws=n_draws,
            bootstrap_seed=bootstrap_seed,
            min_valid=min_valid,
        )
        for seed in seeds
    ]


def run_confirmation_evaluation(
    records: Sequence[Mapping[str, Any]],
    *,
    eligible: bool,
    seeds: tuple[int, ...] = S7_CONFIRM_SEEDS,
    baselines: tuple[str, ...] = S7_NON_ATTENTION,
    n_draws: int = S7_BOOTSTRAP_DRAWS,
    bootstrap_seed: int = S7_BOOTSTRAP_SEED,
    min_valid: int = S7_MIN_VALID_DRAWS,
) -> dict[str, Any]:
    """Coverage → trial contrasts → confirmation label.

    Eligibility False short-circuits to ``CONFIRM_SKIPPED``. Incomplete fit
    coverage or incomplete bootstrap on any trial => ``CONFIRM_INCOMPLETE``.
    """
    if not eligible:
        skipped = evaluate_confirmation([], eligible=False)
        skipped["trial_contrasts"] = []
        return skipped

    coverage = confirmation_coverage(records, seeds=seeds)
    if not coverage["complete"]:
        return {
            "confirm_label": CONFIRM_INCOMPLETE,
            "reason": "incomplete confirmation coverage",
            "coverage": coverage,
            "trial_contrasts": [],
            "ca_tc_successes": None,
            "all_baseline_successes": None,
            "ca_tc_wilson": None,
            "all_baseline_wilson": None,
            "trials": [],
        }

    trials = build_trial_contrasts(
        records,
        seeds=seeds,
        baselines=baselines,
        n_draws=n_draws,
        bootstrap_seed=bootstrap_seed,
        min_valid=min_valid,
    )
    incomplete_trials = [t for t in trials if not t.get("complete")]
    if incomplete_trials:
        return {
            "confirm_label": CONFIRM_INCOMPLETE,
            "reason": "incomplete confirmation trial contrasts",
            "coverage": coverage,
            "trial_contrasts": trials,
            "incomplete_seeds": [t["generator_seed"] for t in incomplete_trials],
            "ca_tc_successes": None,
            "all_baseline_successes": None,
            "ca_tc_wilson": None,
            "all_baseline_wilson": None,
            "trials": [],
        }

    evaluated = evaluate_confirmation(
        trials,
        eligible=True,
        seeds=seeds,
        baselines=baselines,
        fit_records=records,
    )
    evaluated["trial_contrasts"] = trials
    return evaluated


def expected_confirmation_jobs() -> list[dict[str, Any]]:
    """Frozen 350-job confirmation enumeration (alias for callers/tests)."""
    return enumerate_confirmation_jobs()


# Re-export stage token used by runner retention.
assert S7_CONFIRM_STAGE == "confirm"
assert CONFIRM_SKIPPED  # imported for API symmetry with pairing_exec
