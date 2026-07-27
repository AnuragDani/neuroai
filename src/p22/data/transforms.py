"""Train-only preprocessing.

A transform fitted on all cells leaks held-out information into every later
number. Here a transform is fitted on training cells only, then frozen: the
fitted parameters are fingerprinted, and ``transform`` refuses to run if that
fingerprint changed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from p22 import __version__

STANDARD_SCALER = "standard_scaler"
PCA_KIND = "pca"
SUPPORTED_KINDS = (STANDARD_SCALER, PCA_KIND)
FINGERPRINT_ATTRIBUTES = ("mean_", "scale_", "var_", "components_", "explained_variance_")


@dataclass(frozen=True)
class FittedTransform:
    """A transform fitted on training cells and frozen for later splits.

    Attributes:
        kind: ``standard_scaler`` or ``pca``.
        transformer: the fitted scikit-learn estimator.
        metadata: transformer class, parameters, training identifier hash,
            feature counts, timestamp, package version, and fingerprint.
    """

    kind: str
    transformer: Any
    metadata: dict[str, Any]

    @property
    def n_features_in(self) -> int:
        return int(self.metadata["n_features_in"])

    @property
    def n_features_out(self) -> int:
        return int(self.metadata["n_features_out"])

    @property
    def training_id_hash(self) -> str:
        return str(self.metadata["training_id_hash"])

    def transform(self, matrix: np.ndarray) -> np.ndarray:
        """Apply the frozen transform to any split.

        Args:
            matrix: ``(n_cells, n_features_in)`` matrix.

        Returns:
            Transformed float32 matrix.

        Raises:
            ValueError: if the feature count differs from the fitted matrix, if
                the input is not finite, or if the fitted parameters were mutated
                after fitting.
            RuntimeError: never; refitting is not possible through this object.
        """
        array = _as_matrix(matrix, name="matrix")
        if array.shape[1] != self.n_features_in:
            raise ValueError(
                f"matrix has {array.shape[1]} features, transform was fitted on "
                f"{self.n_features_in}"
            )
        current = _fingerprint(self.transformer)
        if current != self.metadata["parameter_fingerprint"]:
            raise ValueError("fitted parameters changed after fitting; transform is not frozen")
        return np.ascontiguousarray(self.transformer.transform(array), dtype=np.float32)


def _as_matrix(matrix: np.ndarray, name: str = "matrix") -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional, got shape {array.shape}")
    if array.size == 0:
        raise ValueError(f"{name} is empty")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def _as_id_array(values: Sequence[Any] | np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=object)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {array.shape}")
    for position, value in enumerate(array):
        if value is None or not str(value).strip():
            raise ValueError(f"{name} contains a null or blank identifier at position {position}")
    return np.array([str(value) for value in array], dtype=object)


def _fingerprint(transformer: Any) -> str:
    """Hash the fitted attributes so later mutation is detectable."""
    digest = hashlib.sha256()
    digest.update(type(transformer).__name__.encode())
    for attribute in FINGERPRINT_ATTRIBUTES:
        value = getattr(transformer, attribute, None)
        if value is None:
            continue
        array = np.asarray(value, dtype=np.float64)
        digest.update(attribute.encode())
        digest.update(str(array.shape).encode())
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _hash_ids(ids: Sequence[str]) -> str:
    payload = json.dumps(sorted(str(value) for value in ids), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def fit_train_only(
    matrix: np.ndarray,
    cell_ids: Sequence[Any] | np.ndarray,
    train_cell_ids: Sequence[Any] | np.ndarray,
    holdout_cell_ids: Sequence[Any] | np.ndarray = (),
    kind: str = STANDARD_SCALER,
    n_components: int | None = None,
    seed: int = 0,
) -> FittedTransform:
    """Fit a transform on training cells only.

    Args:
        matrix: ``(n_cells, n_features)`` matrix covering every cell in ``cell_ids``.
        cell_ids: identifier per row of ``matrix``.
        train_cell_ids: identifiers allowed to influence the fit.
        holdout_cell_ids: validation and test identifiers. Any overlap with
            ``train_cell_ids`` is rejected.
        kind: ``standard_scaler`` or ``pca``.
        n_components: component count, required for ``pca``.
        seed: seed passed to the estimator where it applies.

    Returns:
        A frozen :class:`FittedTransform`.

    Raises:
        ValueError: on unknown kind, shape or identifier problems, an empty
            training set, unknown training identifiers, or any held-out
            identifier inside the training set.
    """
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"unknown transform kind {kind!r}; expected one of {SUPPORTED_KINDS}")

    array = _as_matrix(matrix)
    ids = _as_id_array(cell_ids, "cell_ids")
    if ids.size != array.shape[0]:
        raise ValueError(f"cell_ids has {ids.size} entries but matrix has {array.shape[0]} rows")
    if np.unique(ids).size != ids.size:
        raise ValueError("cell_ids contains duplicate identifiers")

    train_ids = _as_id_array(train_cell_ids, "train_cell_ids")
    if train_ids.size == 0:
        raise ValueError("train_cell_ids is empty; a transform needs training cells")
    if np.unique(train_ids).size != train_ids.size:
        raise ValueError("train_cell_ids contains duplicate identifiers")

    holdout_ids = _as_id_array(holdout_cell_ids, "holdout_cell_ids")
    leaked = sorted(set(train_ids) & set(holdout_ids))
    if leaked:
        raise ValueError(
            "validation or test identifiers appear in the fit set, which would leak "
            f"held-out information: {leaked[:5]}"
        )

    unknown = sorted(set(train_ids) - set(ids))
    if unknown:
        raise ValueError(f"train_cell_ids not present in cell_ids: {unknown[:5]}")

    position_of = {value: index for index, value in enumerate(ids)}
    train_rows = np.array([position_of[value] for value in train_ids], dtype=int)

    if kind == STANDARD_SCALER:
        if n_components is not None:
            raise ValueError("n_components does not apply to standard_scaler")
        transformer: Any = StandardScaler()
    else:
        if n_components is None:
            raise ValueError("n_components is required for pca")
        max_components = min(train_rows.size, array.shape[1])
        if not 1 <= n_components <= max_components:
            raise ValueError(
                f"n_components must be in [1, {max_components}] for this training set, "
                f"got {n_components}"
            )
        transformer = PCA(n_components=int(n_components), random_state=int(seed))

    fit_matrix = array[train_rows]
    transformer.fit(fit_matrix)
    transformed_probe = transformer.transform(fit_matrix[:1])

    metadata = {
        "kind": kind,
        "transformer_class": f"{type(transformer).__module__}.{type(transformer).__name__}",
        "parameters": {
            key: (value if isinstance(value, (int, float, str, bool, type(None))) else str(value))
            for key, value in transformer.get_params().items()
        },
        "training_id_hash": _hash_ids(train_ids),
        "n_train_cells": int(train_rows.size),
        "n_holdout_ids_declared": int(holdout_ids.size),
        "n_features_in": int(array.shape[1]),
        "n_features_out": int(transformed_probe.shape[1]),
        "seed": int(seed),
        "fitted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "p22_version": __version__,
        "fit_scope": "train cells only",
        "parameter_fingerprint": _fingerprint(transformer),
    }
    return FittedTransform(kind=kind, transformer=transformer, metadata=metadata)
