"""Deterministic two-view synthetic data with donor structure.

The generated world has three properties the rest of the package depends on:

1. the label signal is imperfect, so a perfect score means a bug, not a result;
2. each view carries a different part of the label signal, so routing has
   something to do;
3. donors add a nuisance shift, so cell-level splitting looks better than it is.

Feature and class names are deliberately neutral: ``view_a``, ``view_b``,
``class_0``, ``donor_00``. Nothing here refers to a measurement technology, a
tissue, or a condition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

LATENT_DIM = 8


@dataclass(frozen=True)
class SyntheticMultimodal:
    """One synthetic two-view dataset with donor structure.

    Attributes:
        view_a: ``(n_cells, n_features_a)`` float32 matrix.
        view_b: ``(n_cells, n_features_b)`` float32 matrix.
        labels: ``(n_cells,)`` int64 class codes.
        donor_ids: ``(n_cells,)`` donor identifier per cell.
        cell_ids: ``(n_cells,)`` unique cell identifier.
        metadata: per-cell table with identifiers, label, and neutral covariates.
        generation: parameters and derived counts used to produce the arrays.
    """

    view_a: np.ndarray
    view_b: np.ndarray
    labels: np.ndarray
    donor_ids: np.ndarray
    cell_ids: np.ndarray
    metadata: pd.DataFrame
    generation: dict[str, Any]

    @property
    def n_cells(self) -> int:
        return int(self.view_a.shape[0])

    @property
    def n_donors(self) -> int:
        return int(np.unique(self.donor_ids).size)

    @property
    def n_classes(self) -> int:
        return int(self.generation["n_classes"])

    def label_distribution(self) -> pd.Series:
        """Return observed cell count per class. Balance is reported, not promised."""
        counts = pd.Series(self.labels).value_counts().sort_index()
        counts.index = [f"class_{code}" for code in counts.index]
        counts.name = "cells"
        return counts

    def donor_label_counts(self) -> pd.DataFrame:
        """Return a donor-by-class cell count table."""
        table = pd.crosstab(self.metadata["donor_id"], self.metadata["label_name"])
        return table.sort_index()


def _validate_positive(name: str, value: int, minimum: int = 1) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return int(value)


def _sample_labels(
    rng: np.random.Generator,
    n_donors: int,
    cells_per_donor: int,
    n_classes: int,
    concentration: float,
) -> np.ndarray:
    """Sample per-donor class propensities, then labels, then repair empty classes.

    Donor-specific propensities make the label distribution uneven on purpose.
    """
    labels = np.empty(n_donors * cells_per_donor, dtype=np.int64)
    for donor in range(n_donors):
        weights = rng.dirichlet(np.full(n_classes, concentration))
        start = donor * cells_per_donor
        labels[start : start + cells_per_donor] = rng.choice(
            n_classes, size=cells_per_donor, p=weights
        )
    missing = [code for code in range(n_classes) if not np.any(labels == code)]
    if missing:
        # Every class must appear at least once, otherwise metric code is tested
        # against a world it cannot represent.
        positions = rng.choice(labels.size, size=len(missing), replace=False)
        labels[positions] = missing
    return labels


def make_synthetic_multimodal(
    n_donors: int = 12,
    cells_per_donor: int = 20,
    n_features_a: int = 16,
    n_features_b: int = 12,
    n_classes: int = 3,
    seed: int = 42,
    class_signal: float = 0.9,
    donor_nuisance: float = 0.7,
    noise: float = 1.0,
    label_concentration: float = 3.0,
    label_unit: str = "cell",
) -> SyntheticMultimodal:
    """Generate a deterministic two-view dataset with donor nuisance.

    Args:
        n_donors: number of donors.
        cells_per_donor: cells generated for each donor.
        n_features_a: feature count of view A.
        n_features_b: feature count of view B.
        n_classes: number of label classes, at least two.
        seed: seed for the generator; the same seed returns identical arrays.
        class_signal: strength of the class effect in latent space.
        donor_nuisance: strength of the donor shift in latent space.
        noise: per-cell latent noise scale.
        label_concentration: Dirichlet concentration for per-donor class mix;
            smaller values make donors more skewed.
        label_unit: "cell" preserves the original class-mix fixture; "donor"
            assigns one neutral class per donor for binary donor-training tests.

    Returns:
        A :class:`SyntheticMultimodal` whose arrays contain no NaN or infinity.

    Raises:
        TypeError: if a count argument is not an integer.
        ValueError: if a count argument is out of range or a scale is negative.
    """
    n_donors = _validate_positive("n_donors", n_donors, minimum=2)
    cells_per_donor = _validate_positive("cells_per_donor", cells_per_donor, minimum=2)
    n_features_a = _validate_positive("n_features_a", n_features_a, minimum=2)
    n_features_b = _validate_positive("n_features_b", n_features_b, minimum=2)
    n_classes = _validate_positive("n_classes", n_classes, minimum=2)
    for name, value in (
        ("class_signal", class_signal),
        ("donor_nuisance", donor_nuisance),
        ("noise", noise),
    ):
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
    if label_concentration <= 0:
        raise ValueError(f"label_concentration must be > 0, got {label_concentration}")
    if n_donors * cells_per_donor < n_classes:
        raise ValueError("not enough cells to place every class at least once")
    if label_unit not in {"cell", "donor"}:
        raise ValueError("label_unit must be cell or donor")
    if label_unit == "donor" and n_donors < n_classes:
        raise ValueError("not enough donors to place every class at least once")

    rng = np.random.default_rng(seed)
    n_cells = n_donors * cells_per_donor

    donor_index = np.repeat(np.arange(n_donors), cells_per_donor)
    donor_ids = np.array([f"donor_{index:02d}" for index in donor_index], dtype=object)
    cell_ids = np.array([f"cell_{index:05d}" for index in range(n_cells)], dtype=object)
    if label_unit == "donor":
        labels = np.repeat(rng.permutation(np.arange(n_donors) % n_classes), cells_per_donor)
    else:
        labels = _sample_labels(rng, n_donors, cells_per_donor, n_classes, label_concentration)

    class_centres = rng.normal(0.0, 1.0, size=(n_classes, LATENT_DIM))
    donor_offsets = rng.normal(0.0, 1.0, size=(n_donors, LATENT_DIM))
    latent = (
        class_signal * class_centres[labels]
        + donor_nuisance * donor_offsets[donor_index]
        + noise * rng.normal(0.0, 1.0, size=(n_cells, LATENT_DIM))
    )

    # Each view reads a different half of the latent space strongly and the other
    # half weakly, so neither view alone explains the label.
    half = LATENT_DIM // 2
    weights_a = np.concatenate([np.full(half, 1.0), np.full(LATENT_DIM - half, 0.25)])
    weights_b = np.concatenate([np.full(half, 0.25), np.full(LATENT_DIM - half, 1.0)])

    loading_a = rng.normal(0.0, 1.0, size=(LATENT_DIM, n_features_a)) * weights_a[:, None]
    loading_b = rng.normal(0.0, 1.0, size=(LATENT_DIM, n_features_b)) * weights_b[:, None]

    view_a = latent @ loading_a + 0.5 * rng.normal(0.0, 1.0, size=(n_cells, n_features_a))
    view_b = latent @ loading_b + 0.5 * rng.normal(0.0, 1.0, size=(n_cells, n_features_b))

    # View B additionally carries a direct donor offset, so donor structure is not
    # symmetric across views.
    donor_shift_b = rng.normal(0.0, 1.0, size=(n_donors, n_features_b))
    view_b = view_b + donor_nuisance * donor_shift_b[donor_index]

    view_a = np.ascontiguousarray(view_a, dtype=np.float32)
    view_b = np.ascontiguousarray(view_b, dtype=np.float32)
    for name, array in (("view_a", view_a), ("view_b", view_b)):
        if not np.isfinite(array).all():
            raise ValueError(f"{name} contains non-finite values")

    label_names = np.array([f"class_{code}" for code in labels], dtype=object)
    metadata = pd.DataFrame(
        {
            "cell_id": cell_ids,
            "donor_id": donor_ids,
            "label": labels,
            "label_name": label_names,
            "capture_batch": [f"batch_{index % 3}" for index in donor_index],
            "view_a_total": view_a.sum(axis=1).astype(np.float64),
            "view_b_total": view_b.sum(axis=1).astype(np.float64),
        }
    )

    generation = {
        "generator": "p22.testing.synthetic.make_synthetic_multimodal",
        "data_mode": "synthetic",
        "seed": int(seed),
        "n_donors": n_donors,
        "cells_per_donor": cells_per_donor,
        "n_cells": n_cells,
        "n_features_a": n_features_a,
        "n_features_b": n_features_b,
        "n_classes": n_classes,
        "latent_dim": LATENT_DIM,
        "class_signal": float(class_signal),
        "donor_nuisance": float(donor_nuisance),
        "noise": float(noise),
        "label_concentration": float(label_concentration),
        "view_latent_weights": {"view_a": weights_a.tolist(), "view_b": weights_b.tolist()},
        "notes": (
            "Imperfect label signal by construction. Views read different latent "
            "halves. View B also carries a direct donor offset."
        ),
    }

    if label_unit == "donor":
        generation["label_unit"] = label_unit
    return SyntheticMultimodal(
        view_a=view_a,
        view_b=view_b,
        labels=labels,
        donor_ids=donor_ids,
        cell_ids=cell_ids,
        metadata=metadata,
        generation=generation,
    )
