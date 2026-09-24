"""Stable donor x cell-type x library stratified cell sampler (N1).

Repairs the 2026-09-21 review defect 2: the historical sampler took the lowest
row indices after one donor-level permutation, which dropped whole libraries for
5 of the 7 two-library donors. This module allocates the per-donor cap across
strata proportionally (largest remainder, at least one cell per present stratum
when the cap allows) and then picks cells inside each stratum by stable hash
rank ``sha256(f"{seed}\\n{cell_id}")``.

Design choices:

* Allocation is hierarchical. The cap is first split across the outer stratum
  (``library`` when present, else the last entry of ``strata``) so that each
  library's share is within one cell of its proportional share. The library
  allocation is then split across the remaining strata (by default the author
  cell type) inside that library.
* Selection uses a hash of the cell identifier, not the row position, so
  shuffling the rows of ``obs`` leaves the selected cell IDs unchanged.
* Only the donor column and the requested stratum columns are read. No disease,
  condition or label column is consulted, so the sampler is label-free.

Nothing here modifies ``sample_nested_capped_cells``; that historical helper is
left untouched as the reproduction reference.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

DONOR_COLUMN = "donor_id"
DEFAULT_STRATA = ("author_cell_type", "library")
OUTER_STRATUM = "library"


def _allocate(cap: int, counts: np.ndarray) -> np.ndarray:
    """Split ``cap`` over ``counts`` proportionally by largest remainder.

    When ``cap >= n`` every stratum keeps at least one cell. The result never
    exceeds the available count of any stratum.
    """
    counts = np.asarray(counts, dtype=np.int64)
    n = counts.size
    if cap <= 0 or n == 0:
        return np.zeros(n, dtype=np.int64)
    total = int(counts.sum())
    if cap >= total:
        return counts.copy()
    if cap >= n:
        alloc = np.ones(n, dtype=np.int64)
        remaining = cap - n
    else:
        alloc = np.zeros(n, dtype=np.int64)
        remaining = cap
    if remaining > 0:
        quotas = counts * (remaining / total)
        base = np.floor(quotas).astype(np.int64)
        alloc = alloc + base
        left = cap - int(alloc.sum())
        frac = quotas - base
        order = np.lexsort((np.arange(n), -frac))
        for index in order:
            if left <= 0:
                break
            if alloc[index] < counts[index]:
                alloc[index] += 1
                left -= 1
        if left > 0:
            for index in np.argsort(-counts, kind="stable"):
                if left <= 0:
                    break
                take = min(int(counts[index] - alloc[index]), left)
                alloc[index] += take
                left -= take
    return np.minimum(alloc, counts)


def _stable_hash_order(cell_ids: np.ndarray, seed: int) -> np.ndarray:
    """Order positions by ``sha256(f"{seed}\\n{cell_id}")`` (stable tie-break)."""
    digests = [
        hashlib.sha256(f"{seed}\n{cell_id}".encode()).digest()
        for cell_id in cell_ids
    ]
    return np.array(
        sorted(range(len(digests)), key=lambda i: (digests[i], cell_ids[i])),
        dtype=np.int64,
    )


def _pick(positions: np.ndarray, cell_ids: np.ndarray, seed: int, take: int) -> np.ndarray:
    if take <= 0:
        return np.zeros(0, dtype=np.int64)
    if take >= positions.size:
        return positions.astype(np.int64)
    order = _stable_hash_order(cell_ids, seed)
    return positions[order[:take]].astype(np.int64)


def _group_levels(values: np.ndarray) -> tuple[list[str], np.ndarray]:
    levels = sorted(set(values.tolist()))
    index = {level: i for i, level in enumerate(levels)}
    codes = np.array([index[value] for value in values.tolist()], dtype=np.int64)
    return levels, codes


def _donor_selection(
    positions: np.ndarray,
    cell_ids: np.ndarray,
    strata_values: list[np.ndarray],
    cap: int,
    seed: int,
) -> np.ndarray:
    if positions.size <= cap:
        return positions.astype(np.int64)
    if not strata_values:
        return _pick(positions, cell_ids, seed, cap)

    outer_values = strata_values[-1]
    outer_levels, outer_codes = _group_levels(outer_values)
    outer_counts = np.array(
        [int((outer_codes == i).sum()) for i in range(len(outer_levels))], dtype=np.int64
    )
    outer_alloc = _allocate(cap, outer_counts)

    selected: list[np.ndarray] = []
    for outer_index, _level in enumerate(outer_levels):
        take = int(outer_alloc[outer_index])
        if take <= 0:
            continue
        in_level = outer_codes == outer_index
        level_positions = positions[in_level]
        level_ids = cell_ids[in_level]
        inner_values = [values[in_level] for values in strata_values[:-1]]
        if not inner_values:
            selected.append(_pick(level_positions, level_ids, seed, take))
            continue
        joint = np.array(
            [
                "|".join(str(values[i]) for values in inner_values)
                for i in range(level_positions.size)
            ]
        )
        inner_levels, inner_codes = _group_levels(joint)
        inner_counts = np.array(
            [int((inner_codes == i).sum()) for i in range(len(inner_levels))], dtype=np.int64
        )
        inner_alloc = _allocate(take, inner_counts)
        for inner_index in range(len(inner_levels)):
            inner_take = int(inner_alloc[inner_index])
            if inner_take <= 0:
                continue
            in_inner = inner_codes == inner_index
            selected.append(
                _pick(
                    level_positions[in_inner],
                    level_ids[in_inner],
                    seed,
                    inner_take,
                )
            )
    if not selected:
        return np.zeros(0, dtype=np.int64)
    return np.sort(np.concatenate(selected)).astype(np.int64)


def sample_donor_stratified_cells(
    obs: pd.DataFrame,
    cap: int,
    seed: int,
    strata: tuple[str, ...] = DEFAULT_STRATA,
) -> np.ndarray:
    """Pick at most ``cap`` cells per donor, spread over the given strata.

    Parameters
    ----------
    obs:
        Cell metadata. ``obs.index`` supplies the stable cell identifier.
    cap:
        Maximum cells kept per donor. Donors with ``<= cap`` cells are kept whole.
    seed:
        Hash seed; the same seed reproduces the same selection exactly.
    strata:
        Columns to stratify on. When ``"library"`` is present it forms the outer
        allocation level; otherwise the last entry is used as the outer level.

    Returns
    -------
    numpy.ndarray
        Sorted integer row positions into ``obs`` (``int64``).
    """
    if cap < 1:
        raise ValueError("cap must be a positive integer")
    missing = [column for column in (DONOR_COLUMN, *strata) if column not in obs.columns]
    if missing:
        raise KeyError(f"missing required columns: {missing}")
    if obs.index.duplicated().any():
        raise ValueError("obs cell identifiers are not unique")

    strata = tuple(strata)
    outer = OUTER_STRATUM if OUTER_STRATUM in strata else strata[-1]
    inner = tuple(column for column in strata if column != outer)
    ordered_strata = (*inner, outer)

    donors = obs[DONOR_COLUMN].astype(str).to_numpy()
    cell_ids = obs.index.astype(str).to_numpy()
    strata_values = [obs[column].astype(str).to_numpy() for column in ordered_strata]

    chosen: list[np.ndarray] = []
    for donor in sorted(set(donors.tolist())):
        positions = np.flatnonzero(donors == donor)
        chosen.append(
            _donor_selection(
                positions,
                cell_ids[positions],
                [values[positions] for values in strata_values],
                cap,
                seed,
            )
        )
    if not chosen:
        return np.zeros(0, dtype=np.int64)
    return np.sort(np.concatenate(chosen)).astype(np.int64)
