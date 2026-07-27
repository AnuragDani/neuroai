"""Uncertainty and comparison statistics at the donor level.

Cells from one donor are not independent observations. Resampling cells therefore
produces intervals that are too narrow. Everything here resamples whole donors and
reports how many replicates were usable, so a partly failed bootstrap cannot be
mistaken for a clean one.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from p22.eval.metrics import MetricValue

MetricFunction = Callable[[np.ndarray, np.ndarray], MetricValue]


@dataclass(frozen=True)
class BootstrapResult:
    """Donor-cluster bootstrap outcome.

    Attributes:
        metric: metric name.
        estimate: metric on the full sample, or ``None`` when undefined.
        lower: lower interval bound, or ``None``.
        upper: upper interval bound, or ``None``.
        level: interval level, for example 0.95.
        unit: resampling unit; always ``donor``.
        n_replicates_requested: replicates asked for.
        n_valid: replicates that produced a value.
        n_failed: replicates where the metric did not apply.
        failure_reasons: distinct reasons replicates failed.
        not_applicable: reason the whole bootstrap does not apply.
    """

    metric: str
    estimate: float | None
    lower: float | None
    upper: float | None
    level: float
    unit: str
    n_replicates_requested: int
    n_valid: int
    n_failed: int
    failure_reasons: tuple[str, ...] = ()
    not_applicable: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "estimate": self.estimate,
            "interval": [self.lower, self.upper],
            "level": self.level,
            "unit": self.unit,
            "n_replicates_requested": self.n_replicates_requested,
            "n_valid": self.n_valid,
            "n_failed": self.n_failed,
            "failure_reasons": list(self.failure_reasons),
            "not_applicable": self.not_applicable,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class McNemarResult:
    """Paired comparison of two classifiers on the same cells."""

    n_only_a_correct: int
    n_only_b_correct: int
    statistic: float | None
    p_value: float | None
    continuity_corrected: bool
    not_applicable: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_only_a_correct": self.n_only_a_correct,
            "n_only_b_correct": self.n_only_b_correct,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "continuity_corrected": self.continuity_corrected,
            "not_applicable": self.not_applicable,
        }


@dataclass(frozen=True)
class SeedSummary:
    """Across-seed summary of one metric for one model."""

    metric: str
    n_seeds: int
    mean: float | None
    std: float | None
    minimum: float | None
    maximum: float | None
    lower: float | None
    upper: float | None
    level: float
    not_applicable: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "n_seeds": self.n_seeds,
            "mean": self.mean,
            "std": self.std,
            "min": self.minimum,
            "max": self.maximum,
            "interval": [self.lower, self.upper],
            "level": self.level,
            "not_applicable": self.not_applicable,
        }


def _donor_positions(donor_ids: Sequence[Any] | np.ndarray) -> dict[str, np.ndarray]:
    array = np.asarray(donor_ids, dtype=object)
    if array.ndim != 1:
        raise ValueError(f"donor_ids must be one-dimensional, got shape {array.shape}")
    if array.size == 0:
        raise ValueError("donor_ids is empty")
    as_str = np.array([str(value) for value in array], dtype=object)
    return {donor: np.flatnonzero(as_str == donor) for donor in sorted(set(as_str))}


def donor_bootstrap(
    metric_fn: MetricFunction,
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    donor_ids: Sequence[Any],
    n_replicates: int = 200,
    level: float = 0.95,
    seed: int = 0,
) -> BootstrapResult:
    """Resample whole donors with replacement and report a percentile interval.

    Args:
        metric_fn: callable returning a :class:`MetricValue` for a subset.
        y_true: true labels per cell.
        y_pred: predicted labels per cell.
        donor_ids: donor identifier per cell.
        n_replicates: number of donor resamples.
        level: interval level.
        seed: seed for the resampling.

    Returns:
        A :class:`BootstrapResult`. When fewer than two donors exist, or when the
        metric does not apply to the full sample, the result carries a
        ``not_applicable`` reason instead of a number.

    Raises:
        ValueError: on mismatched lengths, a non-positive replicate count, or a
            level outside (0, 1).
    """
    true_labels = np.asarray(y_true)
    pred_labels = np.asarray(y_pred)
    if true_labels.shape != pred_labels.shape:
        raise ValueError(
            f"y_true has shape {true_labels.shape}, y_pred has shape {pred_labels.shape}"
        )
    if n_replicates < 1:
        raise ValueError(f"n_replicates must be >= 1, got {n_replicates}")
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")

    positions = _donor_positions(donor_ids)
    total_cells = sum(index.size for index in positions.values())
    if total_cells != true_labels.size:
        raise ValueError(f"donor_ids covers {total_cells} cells but y_true has {true_labels.size}")

    full_sample = metric_fn(true_labels, pred_labels)
    donors = list(positions)
    common = {
        "metric": full_sample.name,
        "level": level,
        "unit": "donor",
        "n_replicates_requested": int(n_replicates),
        "detail": {"n_donors": len(donors), "n_cells": int(true_labels.size), "seed": int(seed)},
    }

    if len(donors) < 2:
        return BootstrapResult(
            estimate=full_sample.value,
            lower=None,
            upper=None,
            n_valid=0,
            n_failed=0,
            not_applicable=f"donor bootstrap needs at least two donors, got {len(donors)}",
            **common,
        )
    if not full_sample.applicable:
        return BootstrapResult(
            estimate=None,
            lower=None,
            upper=None,
            n_valid=0,
            n_failed=0,
            not_applicable=(
                f"metric does not apply to the full sample: {full_sample.not_applicable}"
            ),
            **common,
        )

    rng = np.random.default_rng(seed)
    values: list[float] = []
    reasons: list[str] = []
    for _ in range(int(n_replicates)):
        drawn = rng.choice(len(donors), size=len(donors), replace=True)
        index = np.concatenate([positions[donors[position]] for position in drawn])
        replicate = metric_fn(true_labels[index], pred_labels[index])
        if replicate.applicable:
            values.append(float(replicate.value))
        else:
            reasons.append(str(replicate.not_applicable))

    if not values:
        return BootstrapResult(
            estimate=full_sample.value,
            lower=None,
            upper=None,
            n_valid=0,
            n_failed=len(reasons),
            failure_reasons=tuple(sorted(set(reasons))),
            not_applicable="every replicate failed, so no interval exists",
            **common,
        )

    tail = (1.0 - level) / 2.0
    lower, upper = np.percentile(values, [100 * tail, 100 * (1.0 - tail)])
    return BootstrapResult(
        estimate=full_sample.value,
        lower=float(lower),
        upper=float(upper),
        n_valid=len(values),
        n_failed=len(reasons),
        failure_reasons=tuple(sorted(set(reasons))),
        **common,
    )


def mcnemar_test(
    correct_a: Sequence[bool] | np.ndarray,
    correct_b: Sequence[bool] | np.ndarray,
    continuity: bool = True,
) -> McNemarResult:
    """Compare two classifiers on the same cells.

    Args:
        correct_a: per-cell correctness of model A.
        correct_b: per-cell correctness of model B on the same cells.
        continuity: apply the continuity correction.

    Returns:
        A :class:`McNemarResult`. When the two models never disagree, the test does
        not apply and says so.

    Raises:
        ValueError: on mismatched lengths or empty input.
    """
    first = np.asarray(correct_a, dtype=bool)
    second = np.asarray(correct_b, dtype=bool)
    if first.shape != second.shape:
        raise ValueError(f"correct_a has shape {first.shape}, correct_b has shape {second.shape}")
    if first.size == 0:
        raise ValueError("correctness arrays are empty")

    only_a = int(np.sum(first & ~second))
    only_b = int(np.sum(~first & second))
    discordant = only_a + only_b
    if discordant == 0:
        return McNemarResult(
            n_only_a_correct=only_a,
            n_only_b_correct=only_b,
            statistic=None,
            p_value=None,
            continuity_corrected=continuity,
            not_applicable="the two models never disagree, so the test is undefined",
        )
    difference = abs(only_a - only_b)
    if continuity:
        difference = max(difference - 1.0, 0.0)
    statistic = float(difference**2 / discordant)
    p_value = float(stats.chi2.sf(statistic, df=1))
    return McNemarResult(
        n_only_a_correct=only_a,
        n_only_b_correct=only_b,
        statistic=statistic,
        p_value=p_value,
        continuity_corrected=continuity,
    )


def cohens_h(proportion_a: float, proportion_b: float) -> float:
    """Effect size for two proportions, on the arcsine scale.

    Args:
        proportion_a: first proportion in [0, 1].
        proportion_b: second proportion in [0, 1].

    Returns:
        The absolute difference of arcsine-transformed proportions.

    Raises:
        ValueError: if a proportion is outside [0, 1].
    """
    for name, value in (("proportion_a", proportion_a), ("proportion_b", proportion_b)):
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {value}")
    phi_a = 2.0 * np.arcsin(np.sqrt(float(proportion_a)))
    phi_b = 2.0 * np.arcsin(np.sqrt(float(proportion_b)))
    return float(abs(phi_a - phi_b))


def summarize_seeds(
    values: Sequence[float | None],
    metric: str = "metric",
    level: float = 0.95,
) -> SeedSummary:
    """Summarise one metric across seeds.

    Args:
        values: one value per seed; ``None`` entries are counted as unusable.
        metric: metric name for the record.
        level: interval level for the across-seed interval.

    Returns:
        A :class:`SeedSummary`. With fewer than two usable seeds the summary is
        marked not applicable rather than reporting a zero-width interval.
    """
    usable = [float(value) for value in values if value is not None and np.isfinite(value)]
    n_seeds = len(usable)
    if n_seeds < 2:
        return SeedSummary(
            metric=metric,
            n_seeds=n_seeds,
            mean=usable[0] if usable else None,
            std=None,
            minimum=usable[0] if usable else None,
            maximum=usable[0] if usable else None,
            lower=None,
            upper=None,
            level=level,
            not_applicable=f"need at least two usable seeds for a spread, got {n_seeds}",
        )
    array = np.asarray(usable, dtype=np.float64)
    mean = float(array.mean())
    std = float(array.std(ddof=1))
    if std == 0.0:
        lower = upper = mean
    else:
        half_width = float(
            stats.t.ppf(1.0 - (1.0 - level) / 2.0, df=n_seeds - 1) * std / np.sqrt(n_seeds)
        )
        lower, upper = mean - half_width, mean + half_width
    return SeedSummary(
        metric=metric,
        n_seeds=n_seeds,
        mean=mean,
        std=std,
        minimum=float(array.min()),
        maximum=float(array.max()),
        lower=lower,
        upper=upper,
        level=level,
    )
