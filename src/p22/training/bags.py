"""Bag construction for multiple-instance learning over donor cells.

A bag is a set of row positions drawn from one donor. Bags never mix donors, so a
bag inherits its donor's label. Shuffling is seeded by ``(seed, epoch)`` so each
epoch sees a fresh but reproducible partition.
"""

from __future__ import annotations

import numpy as np

MIN_PARTIAL_BAG = 16


def make_bags(
    donor_ids: np.ndarray,
    bag_size: int = 64,
    seed: int = 0,
    epoch: int = 0,
) -> list[np.ndarray]:
    """Partition cell rows into per-donor bags.

    Each donor's rows are shuffled with a generator seeded by ``(seed, epoch)``
    and sliced into bags of ``bag_size``. A trailing partial bag is kept when it
    holds at least :data:`MIN_PARTIAL_BAG` cells and dropped otherwise, so a
    donor with too few cells contributes no bag.

    Args:
        donor_ids: ``(n_cells,)`` donor label per row.
        bag_size: maximum cells per bag.
        seed: base seed.
        epoch: epoch number mixed into the seed.

    Returns:
        A list of integer index arrays, each indexing one donor's rows.

    Raises:
        ValueError: if inputs are malformed.
    """
    donors = np.asarray(donor_ids)
    if donors.ndim != 1:
        raise ValueError(f"donor_ids must be one-dimensional, got {donors.shape}")
    for name, value in (("bag_size", bag_size), ("seed", seed), ("epoch", epoch)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    if bag_size < 1:
        raise ValueError("bag_size must be >= 1")

    rng = np.random.default_rng([seed, epoch])
    bags: list[np.ndarray] = []
    for donor in sorted(set(donors.tolist())):
        positions = np.flatnonzero(donors == donor)
        positions = positions[rng.permutation(len(positions))]
        for start in range(0, len(positions), bag_size):
            chunk = positions[start : start + bag_size]
            if len(chunk) == bag_size or len(chunk) >= MIN_PARTIAL_BAG:
                bags.append(chunk)
    return bags
