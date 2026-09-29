"""Tests for the semi-synthetic planted-signal generator (N3).

The fixture builds a synthetic ``FoldArrays`` directly so the contract
(balanced label, S0 identity, S5 donor-marginal preservation) is proven without
the real H5AD. Kept fast and self-contained.
"""

from __future__ import annotations

import numpy as np

from p22.data.nn_inputs import FoldArrays
from p22.eval.planted_signal import (
    N_ATAC_FEATURES,
    N_RNA_FEATURES,
    fake_donor_labels,
    plant,
    select_features,
)

N_DONORS_PER_GROUP = 4
N_CELLS_PER_DONOR = 25
N_GENES = 30
N_REGIONS = 30


def make_fold() -> FoldArrays:
    donors: list[str] = []
    labels: list[int] = []
    for group in (0, 1):
        for i in range(N_DONORS_PER_GROUP):
            donors.extend([f"g{group}d{i}"] * N_CELLS_PER_DONOR)
            labels.extend([group] * N_CELLS_PER_DONOR)
    n_cells = len(donors)
    rng = np.random.default_rng(11)
    rna = rng.normal(size=(n_cells, N_GENES)).astype(np.float32)
    atac = rng.normal(size=(n_cells, N_REGIONS)).astype(np.float32)
    # First half of the donors (g0d0..g0d3, g1d0..g1d1) are training cells.
    train = np.zeros(n_cells, dtype=bool)
    train[: N_DONORS_PER_GROUP * N_CELLS_PER_DONOR + 2 * N_CELLS_PER_DONOR] = True
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


def test_fake_labels_balanced_and_independent_of_disease() -> None:
    fold = make_fold()
    fake = fake_donor_labels(fold.donor, fold.label)
    table = np.zeros((2, 2), dtype=np.int64)
    for group in (0, 1):
        for value in (0, 1):
            donors = {
                fold.donor[i] for i in np.flatnonzero((fold.label == group) & (fake == value))
            }
            table[group, value] = len(donors)
    # Exactly balanced 2/2 within each true disease group.
    assert table.tolist() == [[2, 2], [2, 2]]
    # Every cell of a donor carries the donor's fake label.
    for name in np.unique(fold.donor):
        assert len(set(fake[fold.donor == name].tolist())) == 1


def test_s0_is_identity() -> None:
    fold = make_fold()
    planted, fake = plant(fold, "S0", 1.0, seed=3)
    assert np.array_equal(planted.rna, fold.rna)
    assert np.array_equal(planted.atac, fold.atac)
    assert fake.shape == fold.donor.shape
    # Input is never mutated.
    assert not np.shares_memory(planted.rna, fold.rna)


def test_s5_preserves_donor_marginal_means() -> None:
    fold = make_fold()
    rna_idx, atac_idx = select_features(fold, seed=0)
    planted, _ = plant(fold, "S5", 1.0, seed=0)
    for name in np.unique(fold.donor):
        cells = np.flatnonzero(fold.donor == name)
        for idx, before, after in (
            (rna_idx, fold.rna, planted.rna),
            (atac_idx, fold.atac, planted.atac),
        ):
            delta = float(before[np.ix_(cells, idx)].mean() - after[np.ix_(cells, idx)].mean())
            assert abs(delta) < 1e-5, (name, delta)
    # ATAC is untouched by S5.
    assert np.array_equal(planted.atac, fold.atac)


def test_s1_changes_only_positive_donor_rna() -> None:
    fold = make_fold()
    fake = fake_donor_labels(fold.donor, fold.label)
    rna_idx, _ = select_features(fold, seed=0)
    planted, _ = plant(fold, "S1", 0.5, seed=0)
    positive = fake == 1
    pos = np.ix_(positive, rna_idx)
    assert np.allclose(planted.rna[pos] - fold.rna[pos], 0.5)
    unchanged = np.ones(N_GENES, dtype=bool)
    unchanged[rna_idx] = False
    other = np.ix_(~positive, unchanged)
    assert np.array_equal(planted.rna[other], fold.rna[other])
    assert np.array_equal(planted.atac, fold.atac)


def test_s6_preserves_s0_s5_and_is_exported():
    from p22.eval.planted_signal import ALL_SCENARIOS, GENE_ALIGNED_SCENARIO, SCENARIOS

    assert GENE_ALIGNED_SCENARIO == "S6"
    assert "S6" in ALL_SCENARIOS
    assert "S6" not in SCENARIOS


def test_select_features_sizes_and_determinism() -> None:
    fold = make_fold()
    rna_idx, atac_idx = select_features(fold, seed=7)
    assert rna_idx.size == N_RNA_FEATURES
    assert atac_idx.size == N_ATAC_FEATURES
    assert np.unique(rna_idx).size == N_RNA_FEATURES
    again = select_features(fold, seed=7)
    assert np.array_equal(rna_idx, again[0])
    assert np.array_equal(atac_idx, again[1])
