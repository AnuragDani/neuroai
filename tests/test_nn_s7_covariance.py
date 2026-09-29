"""Focused checks for the S7 prospective covariance planter.

Synthetic FoldArrays only — no real H5AD, no model fits.
"""

from __future__ import annotations

import numpy as np
import pytest

from p22.data.nn_inputs import FoldArrays
from p22.eval.planted_signal import (
    COVARIANCE_SCENARIO,
    fake_donor_labels,
    paired_channel_indices,
    plant_covariance,
    s7_label_tag,
    shuffle_atac_within_donor,
)

N_DONORS_PER_GROUP = 4
N_CELLS_PER_DONOR = 25
N_GENES = 30
N_REGIONS = 30
SEED = 1001


def make_fold(*, n_cells_per_donor: int = N_CELLS_PER_DONOR) -> FoldArrays:
    donors: list[str] = []
    labels: list[int] = []
    for group in (0, 1):
        for i in range(N_DONORS_PER_GROUP):
            donors.extend([f"g{group}d{i}"] * n_cells_per_donor)
            labels.extend([group] * n_cells_per_donor)
    n_cells = len(donors)
    rng = np.random.default_rng(11)
    rna = rng.normal(size=(n_cells, N_GENES)).astype(np.float32)
    atac = rng.normal(size=(n_cells, N_REGIONS)).astype(np.float32)
    train = np.zeros(n_cells, dtype=bool)
    train[: n_cells // 2] = True
    return FoldArrays(
        rna=rna,
        atac=atac,
        qc=rng.normal(size=(n_cells, 5)).astype(np.float32),
        label=np.asarray(labels, dtype=np.int64),
        donor=np.asarray(donors, dtype=object),
        nuisance_codes={},
        train_position=train,
        gene_ids=np.asarray([f"ENSG{i}" for i in range(N_GENES)], dtype=object),
        region_ids=tuple(f"chr1:{100 * (i + 1)}-{100 * (i + 1) + 50}" for i in range(N_REGIONS)),
        evidence={},
    )


def test_s7_tag_and_fake_label_balance() -> None:
    assert COVARIANCE_SCENARIO == "S7"
    assert s7_label_tag(SEED) == "prospective-s7:1001"
    fold = make_fold()
    fake = fake_donor_labels(fold.donor, fold.label, tag=s7_label_tag(SEED))
    # Balanced 2/2 within each disease group; donor-constant fake labels.
    for name in np.unique(fold.donor):
        assert len(set(fake[fold.donor == name].tolist())) == 1
    for group in (0, 1):
        donors = {
            fold.donor[i]
            for i in range(fold.donor.size)
            if fold.label[i] == group
        }
        zeros = {d for d in donors if fake[fold.donor == d][0] == 0}
        ones = {d for d in donors if fake[fold.donor == d][0] == 1}
        assert len(zeros) == len(ones) == 2


def test_rho0_zero_cross_covariance_unit_moments() -> None:
    fold = make_fold()
    planted, fake = plant_covariance(fold, rho=0.0, generator_seed=SEED)
    rna_cols, atac_cols = paired_channel_indices(fold, SEED)
    # Unselected columns unchanged.
    other_rna = np.ones(N_GENES, dtype=bool)
    other_rna[rna_cols] = False
    other_atac = np.ones(N_REGIONS, dtype=bool)
    other_atac[atac_cols] = False
    assert np.array_equal(planted.rna[:, other_rna], fold.rna[:, other_rna])
    assert np.array_equal(planted.atac[:, other_atac], fold.atac[:, other_atac])
    for name in np.unique(fold.donor):
        rows = np.flatnonzero(fold.donor == name)
        for channel in range(rna_cols.size):
            z = planted.rna[rows, rna_cols[channel]].astype(np.float64)
            a = planted.atac[rows, atac_cols[channel]].astype(np.float64)
            assert abs(float(z.mean())) < 1e-5
            assert abs(float(a.mean())) < 1e-5
            assert abs(float(np.mean(z * z)) - 1.0) < 1e-4
            assert abs(float(np.mean(a * a)) - 1.0) < 1e-4
            # rho=0 => ATAC orthogonal to RNA (w ⊥ z after construction).
            assert abs(float(np.mean(z * a))) < 1e-4
    assert fake.shape == fold.donor.shape
    assert not np.shares_memory(planted.rna, fold.rna)


def test_rho1_signed_covariance_and_determinism() -> None:
    fold = make_fold()
    cell_ids = np.asarray([f"c{i:04d}" for i in range(fold.donor.size)], dtype=object)
    a, fake_a = plant_covariance(fold, rho=1.0, generator_seed=SEED, cell_ids=cell_ids)
    b, fake_b = plant_covariance(fold, rho=1.0, generator_seed=SEED, cell_ids=cell_ids)
    assert np.array_equal(fake_a, fake_b)
    assert np.allclose(a.rna, b.rna)
    assert np.allclose(a.atac, b.atac)
    rna_cols, atac_cols = paired_channel_indices(fold, SEED)
    for name in np.unique(fold.donor):
        rows = np.flatnonzero(fold.donor == name)
        y = int(fake_a[rows[0]])
        sign = 2 * y - 1
        for channel in range(rna_cols.size):
            z = a.rna[rows, rna_cols[channel]].astype(np.float64)
            atac = a.atac[rows, atac_cols[channel]].astype(np.float64)
            # At rho=1, ATAC == sign * RNA (w term vanishes).
            assert np.allclose(atac, sign * z, atol=1e-5)
            assert abs(float(np.mean(z * atac)) - float(sign)) < 1e-4


def test_cell_id_order_independent_of_fold_row_permutation() -> None:
    fold = make_fold()
    cell_ids = np.asarray([f"c{i:04d}" for i in range(fold.donor.size)], dtype=object)
    perm = np.random.default_rng(0).permutation(fold.donor.size)
    shuffled = FoldArrays(
        rna=fold.rna[perm],
        atac=fold.atac[perm],
        qc=fold.qc[perm],
        label=fold.label[perm],
        donor=fold.donor[perm],
        nuisance_codes={},
        train_position=fold.train_position[perm],
        gene_ids=fold.gene_ids,
        region_ids=fold.region_ids,
        evidence={},
    )
    base, _ = plant_covariance(fold, rho=0.5, generator_seed=SEED, cell_ids=cell_ids)
    alt, _ = plant_covariance(
        shuffled, rho=0.5, generator_seed=SEED, cell_ids=cell_ids[perm]
    )
    # Recover values by cell_id for one planted channel.
    rna_cols, _ = paired_channel_indices(fold, SEED)
    col = int(rna_cols[0])
    by_id_base = {str(cid): float(base.rna[i, col]) for i, cid in enumerate(cell_ids)}
    by_id_alt = {
        str(cid): float(alt.rna[i, col]) for i, cid in enumerate(cell_ids[perm])
    }
    assert by_id_base == by_id_alt


def test_refuse_tiny_donor() -> None:
    fold = make_fold(n_cells_per_donor=3)
    with pytest.raises(ValueError, match="refuses donor"):
        plant_covariance(fold, rho=1.0, generator_seed=SEED)


def test_within_donor_atac_shuffle_preserves_marginal_multiset() -> None:
    fold = make_fold()
    planted, _ = plant_covariance(fold, rho=1.0, generator_seed=SEED)
    shuffled = shuffle_atac_within_donor(planted, seed=3001)
    assert np.array_equal(shuffled.rna, planted.rna)
    assert np.array_equal(shuffled.label, planted.label)
    assert np.array_equal(shuffled.donor, planted.donor)
    for name in np.unique(planted.donor):
        rows = np.flatnonzero(planted.donor == name)
        before = np.sort(planted.atac[rows], axis=0)
        after = np.sort(shuffled.atac[rows], axis=0)
        assert np.allclose(before, after)
    # Identity vs shuffle: not identical for these sizes.
    assert not np.allclose(shuffled.atac, planted.atac)
