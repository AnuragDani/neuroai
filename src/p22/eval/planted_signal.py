"""Semi-synthetic planted-signal generator (N3).

Builds a *fake* donor label independent of the real disease label and plants a
known signal structure onto the already-preprocessed fold tensors, so the
Phase-1 benchmark (N4) can ask which structures a given fusion architecture can
detect. The fake label is fixed by the donor id (``sha256("planted-v1\\n" +
donor)`` rank, alternating within each true disease group); the feature sets are
chosen without labels by the same hash rank. Planting happens *after* fold
preprocessing, on the scaled arrays, using training-cell medians only.

Design reference: professor direction D6 (Jul 21 [14:02]) and the N3 task text.
Pure function :func:`plant` returns modified arrays plus the fake labels; it
never mutates its input.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

import numpy as np

from p22.data.nn_inputs import FoldArrays

PLANTED_TAG = "planted-v1"
N_RNA_FEATURES = 20
N_ATAC_FEATURES = 20
SCENARIOS = ("S0", "S1", "S2", "S3", "S4", "S5")


def _digest(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def fake_donor_labels(
    donor: np.ndarray, label: np.ndarray, tag: str = PLANTED_TAG
) -> np.ndarray:
    """Assign each donor a fake 0/1 label, balanced within each true group.

    Donors are ranked by ``sha256(tag, donor)`` inside each disease group and
    labelled alternately. The assignment uses no feature values, so it is
    independent of the real disease label by construction.
    """
    donor = np.asarray(donor)
    label = np.asarray(label)
    fake = np.zeros(donor.size, dtype=np.int64)
    for group in np.unique(label):
        members = sorted(set(donor[label == group].tolist()))
        ranked = sorted(members, key=lambda name: _digest(tag, str(name)))
        for position, name in enumerate(ranked):
            fake[donor == name] = position % 2
    return fake


def _hash_ranked_indices(items, n_features: int, seed) -> np.ndarray:
    names = [str(item) for item in items]
    order = sorted(range(len(names)), key=lambda i: _digest(str(seed), names[i]))
    take = sorted(order[: min(int(n_features), len(names))])
    return np.asarray(take, dtype=np.int64)


def select_features(fold: FoldArrays, seed) -> tuple[np.ndarray, np.ndarray]:
    """Return the RNA and ATAC feature-column indices chosen without labels."""
    rna_idx = _hash_ranked_indices(fold.gene_ids, N_RNA_FEATURES, f"{seed}:rna")
    atac_idx = _hash_ranked_indices(fold.region_ids, N_ATAC_FEATURES, f"{seed}:atac")
    return rna_idx, atac_idx


def plant(
    fold: FoldArrays, scenario: str, delta: float, seed
) -> tuple[FoldArrays, np.ndarray]:
    """Plant ``scenario`` at effect size ``delta`` onto copies of ``fold``.

    Returns ``(planted_fold, fake_labels)`` where ``fake_labels`` is per cell.
    ``S0`` is the identity (null); ``S5`` shifts RNA by
    ``delta * sign(m_i - median_train(m))`` and then re-centres RNA per donor so
    each donor's RNA marginal mean is unchanged.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown planted scenario {scenario!r}; expected {SCENARIOS}")
    delta = float(delta)
    fake = fake_donor_labels(fold.donor, fold.label)
    rna = np.array(fold.rna, dtype=np.float32, copy=True)
    atac = np.array(fold.atac, dtype=np.float32, copy=True)
    if scenario == "S0":
        return replace(fold, rna=rna, atac=atac), fake

    rna_idx, atac_idx = select_features(fold, seed)
    rows = np.flatnonzero(fake == 1)
    m = atac[:, atac_idx].mean(axis=1)
    train = np.asarray(fold.train_position, dtype=bool)
    median = float(np.median(m[train]))

    if scenario == "S1":
        rna[np.ix_(rows, rna_idx)] += delta
    elif scenario == "S2":
        atac[np.ix_(rows, atac_idx)] += delta
    elif scenario == "S3":
        rna[np.ix_(rows, rna_idx)] += delta / 2.0
        atac[np.ix_(rows, atac_idx)] += delta / 2.0
    elif scenario == "S4":
        context = rows[m[rows] > median]
        rna[np.ix_(context, rna_idx)] += delta
    else:  # S5 pairing-only
        added = delta * np.sign(m - median)
        for name in np.unique(fold.donor[rows]):
            cells = rows[fold.donor[rows] == name]
            added[cells] -= added[cells].mean()
        rna[np.ix_(rows, rna_idx)] += added[rows, None]

    return replace(fold, rna=rna, atac=atac), fake
