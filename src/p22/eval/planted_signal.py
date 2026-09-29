"""Semi-synthetic planted-signal generator (N3) plus S7 covariance control.

Builds a *fake* donor label independent of the real disease label and plants a
known signal structure onto the already-preprocessed fold tensors, so the
Phase-1 benchmark (N4) can ask which structures a given fusion architecture can
detect. The fake label is fixed by the donor id (``sha256("planted-v1\\n" +
donor)`` rank, alternating within each true disease group); the feature sets are
chosen without labels by the same hash rank. Planting happens *after* fold
preprocessing, on the scaled arrays, using training-cell medians only.

S7 (prospective covariance control) is a separate path: it replaces paired
selected channels with label-dependent within-cell RNA/ATAC covariance at a
frozen ``rho``, using tag ``prospective-s7:<generator_seed>``. See
``tasks/nn/finish_20260928/BENCHMARK_SPEC.json``.

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
S7_TAG_PREFIX = "prospective-s7"
N_RNA_FEATURES = 20
N_ATAC_FEATURES = 20
MIN_DONOR_CELLS_S7 = 4
_VAR_EPS = 1e-12
SCENARIOS = ("S0", "S1", "S2", "S3", "S4", "S5")
# S6: gene-matched RNA×ATAC interaction (equal-width views); used by P2 / D3.
GENE_ALIGNED_SCENARIO = "S6"
# S7: label-dependent within-cell RNA/ATAC covariance (prospective control).
COVARIANCE_SCENARIO = "S7"
ALL_SCENARIOS = SCENARIOS + (GENE_ALIGNED_SCENARIO,)


def _digest(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def s7_label_tag(generator_seed: int | str) -> str:
    """Fake-label tag for the prospective S7 control (never real disease labels)."""
    return f"{S7_TAG_PREFIX}:{generator_seed}"


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


def paired_channel_indices(fold: FoldArrays, seed) -> tuple[np.ndarray, np.ndarray]:
    """Pair sorted selected RNA/ATAC columns as artificial S7 channels."""
    rna_idx, atac_idx = select_features(fold, seed)
    rna_sorted = np.sort(np.asarray(rna_idx, dtype=np.int64))
    atac_sorted = np.sort(np.asarray(atac_idx, dtype=np.int64))
    n_channels = int(min(rna_sorted.size, atac_sorted.size))
    if n_channels < 1:
        raise ValueError("S7 feature selection produced no paired channels")
    return rna_sorted[:n_channels], atac_sorted[:n_channels]


def _stable_rng(*parts: object) -> np.random.Generator:
    digest = hashlib.sha256("\n".join(str(p) for p in parts).encode("utf-8")).digest()
    # SeedSequence accepts a sequence of uint32 words from the digest.
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


def _donor_row_order(
    donor_rows: np.ndarray, cell_ids: np.ndarray | None
) -> np.ndarray:
    """Stable cell order within a donor: sorted cell_id when provided."""
    if cell_ids is None:
        return np.asarray(donor_rows, dtype=np.int64)
    ids = np.asarray(cell_ids)[donor_rows]
    order = np.argsort(ids.astype(str), kind="mergesort")
    return np.asarray(donor_rows, dtype=np.int64)[order]


def plant_covariance(
    fold: FoldArrays,
    rho: float,
    generator_seed: int,
    *,
    cell_ids: np.ndarray | None = None,
    feature_seed: int | None = None,
) -> tuple[FoldArrays, np.ndarray]:
    """Plant S7 label-dependent within-cell RNA/ATAC covariance at ``rho``.

    For each donor and paired channel, draw independent Gaussians ``z,w`` from a
    SHA256(seed, donor_id, channel) RNG, centre/scale ``z`` to variance 1,
    orthogonalize and centre/scale ``w`` against ``z``, then set::

        RNA = z
        ATAC = (2*y_d - 1) * rho * z + sqrt(1 - rho^2) * w

    Latent draws do not depend on observed feature values or fold index. When
    ``cell_ids`` is provided, generation uses sorted cell-id order within each
    donor and results are written back to fold tensor positions. Donors with
    fewer than four cells or degenerate latent vectors raise ``ValueError``.
    Other transformed columns are left unchanged. Never trains on real labels.
    """
    rho = float(rho)
    if not (-1.0 <= rho <= 1.0):
        raise ValueError(f"rho must be in [-1, 1], got {rho}")
    if cell_ids is not None and np.asarray(cell_ids).shape[0] != fold.donor.shape[0]:
        raise ValueError("cell_ids length must match fold cells")

    tag = s7_label_tag(generator_seed)
    fake = fake_donor_labels(fold.donor, fold.label, tag=tag)
    rna = np.array(fold.rna, dtype=np.float32, copy=True)
    atac = np.array(fold.atac, dtype=np.float32, copy=True)
    sel_seed = generator_seed if feature_seed is None else feature_seed
    rna_cols, atac_cols = paired_channel_indices(fold, sel_seed)
    sign_scale = np.sqrt(max(0.0, 1.0 - rho * rho))

    for donor_name in sorted(set(fold.donor.tolist()), key=str):
        donor_rows = np.flatnonzero(fold.donor == donor_name)
        if donor_rows.size < MIN_DONOR_CELLS_S7:
            raise ValueError(
                f"S7 refuses donor {donor_name!r}: {donor_rows.size} cells "
                f"(need >= {MIN_DONOR_CELLS_S7})"
            )
        ordered = _donor_row_order(donor_rows, cell_ids)
        y_d = int(fake[ordered[0]])
        sign = 2 * y_d - 1
        n_cells = int(ordered.size)
        for channel in range(rna_cols.size):
            rng = _stable_rng(generator_seed, donor_name, channel)
            z_raw = rng.normal(size=n_cells)
            w_raw = rng.normal(size=n_cells)
            z = _centre_scale(z_raw)
            w = _orthogonalize_against(w_raw, z)
            rna[ordered, rna_cols[channel]] = z.astype(np.float32)
            atac[ordered, atac_cols[channel]] = (
                sign * rho * z + sign_scale * w
            ).astype(np.float32)

    return replace(fold, rna=rna, atac=atac), fake


def shuffle_atac_within_donor(
    fold: FoldArrays, seed: int
) -> FoldArrays:
    """Permute ATAC rows within each donor; preserve RNA, labels and marginals."""
    from p22.eval.faithfulness import permute_within_donor

    atac = permute_within_donor(fold.atac, fold.donor, seed=seed)
    return replace(fold, atac=np.asarray(atac, dtype=np.float32))


def plant(
    fold: FoldArrays, scenario: str, delta: float, seed
) -> tuple[FoldArrays, np.ndarray]:
    """Plant ``scenario`` at effect size ``delta`` onto copies of ``fold``.

    Returns ``(planted_fold, fake_labels)`` where ``fake_labels`` is per cell.
    ``S0`` is the identity (null); ``S5`` shifts RNA by
    ``delta * sign(m_i - median_train(m))`` and then re-centres RNA per donor so
    each donor's RNA marginal mean is unchanged. ``S6`` requires equal-width
    matched gene views and adds ``delta`` to RNA gene ``g`` on positive-donor
    cells where ATAC gene ``g`` exceeds its train median (gene-level interaction).
    S7 covariance planting uses :func:`plant_covariance` (rho API), not this path.
    """
    if scenario not in ALL_SCENARIOS:
        raise ValueError(f"unknown planted scenario {scenario!r}; expected {ALL_SCENARIOS}")
    delta = float(delta)
    fake = fake_donor_labels(fold.donor, fold.label)
    rna = np.array(fold.rna, dtype=np.float32, copy=True)
    atac = np.array(fold.atac, dtype=np.float32, copy=True)
    if scenario == "S0":
        return replace(fold, rna=rna, atac=atac), fake

    rows = np.flatnonzero(fake == 1)
    train = np.asarray(fold.train_position, dtype=bool)

    if scenario == GENE_ALIGNED_SCENARIO:
        # Per-gene RNA×ATAC interaction on matched columns (equal widths).
        if rna.shape[1] != atac.shape[1]:
            raise ValueError("S6 requires matched gene views (equal RNA/ATAC widths)")
        medians = np.median(atac[train], axis=0).astype(np.float32)
        for gene in range(rna.shape[1]):
            context = rows[atac[rows, gene] > medians[gene]]
            if context.size:
                rna[context, gene] += delta
        return replace(fold, rna=rna, atac=atac), fake

    rna_idx, atac_idx = select_features(fold, seed)
    m = atac[:, atac_idx].mean(axis=1)
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
