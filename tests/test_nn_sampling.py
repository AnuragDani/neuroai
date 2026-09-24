"""Tests for the stable donor x cell-type x library sampler (N1).

The synthetic fixture proves the allocation contract (both libraries kept,
proportional shares, determinism, label-free). One test runs on the real H5AD
``obs`` when the file is present, since the defect being repaired is specific to
the real donor/library layout.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from p22.data.nn_sampling import sample_donor_stratified_cells

H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
LIBRARIES = ("L1", "L2")
CELL_TYPES = ("A", "B", "C", "D")


def synthetic_obs() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    # d1/d2/d4 span two libraries; d3 has one; d5 is tiny (kept whole).
    donors = {
        "d1": ("L1", "L2"),
        "d2": ("L1", "L2"),
        "d3": ("L1",),
        "d4": ("L1", "L2"),
        "d5": ("L1",),
    }
    for donor, libs in donors.items():
        for library in libs:
            for cell_type in CELL_TYPES:
                n = int(rng.integers(4, 90))
                if donor == "d5":
                    n = 3
                for i in range(n):
                    rows.append(
                        {
                            "donor_id": donor,
                            "library": library,
                            "author_cell_type": cell_type,
                            "cell_id": f"{donor}|{library}|{cell_type}|{i}",
                        }
                    )
    return pd.DataFrame(rows).set_index("cell_id")


def test_two_library_donors_keep_both_libraries_proportionally() -> None:
    obs = synthetic_obs()
    selected = obs.iloc[sample_donor_stratified_cells(obs, cap=120, seed=22)]
    for donor in ("d1", "d2", "d4"):
        donor_obs = obs[obs["donor_id"] == donor]
        donor_sel = selected[selected["donor_id"] == donor]
        assert set(donor_sel["library"]) == set(LIBRARIES)
        total = len(donor_obs)
        for library in LIBRARIES:
            expected = len(donor_obs[donor_obs["library"] == library]) / total * 120
            got = len(donor_sel[donor_sel["library"] == library])
            assert abs(got - expected) <= 2, (donor, library, got, expected)


def test_cap_below_stratum_count_never_keeps_zero_stratum() -> None:
    # cap >= number of joint strata, so every present stratum gets at least one.
    obs = synthetic_obs()
    selected = obs.iloc[sample_donor_stratified_cells(obs, cap=20, seed=7)]
    for donor in ("d1", "d2", "d4"):
        donor_obs = obs[obs["donor_id"] == donor]
        donor_sel = selected[selected["donor_id"] == donor]
        assert set(donor_sel["library"]) == set(LIBRARIES)
        present = set(donor_obs["author_cell_type"])
        assert set(donor_sel["author_cell_type"]) == present


def test_deterministic_and_row_order_invariant() -> None:
    obs = synthetic_obs()
    first = sample_donor_stratified_cells(obs, cap=150, seed=5)
    second = sample_donor_stratified_cells(obs, cap=150, seed=5)
    assert np.array_equal(first, second)

    shuffled = obs.sample(frac=1.0, random_state=99)
    third = sample_donor_stratified_cells(shuffled, cap=150, seed=5)
    assert set(obs.index[first]) == set(shuffled.index[third])

    different = sample_donor_stratified_cells(obs, cap=150, seed=6)
    assert not np.array_equal(first, different)


def test_small_donors_kept_whole_and_sorted_int64() -> None:
    obs = synthetic_obs()
    selected = sample_donor_stratified_cells(obs, cap=1000, seed=22)
    assert selected.dtype == np.int64
    assert np.array_equal(selected, np.sort(selected))
    tiny = obs.index[obs["donor_id"] == "d5"]
    assert set(tiny).issubset(set(obs.index[selected]))
    assert len(selected) == len(obs)  # every donor has <= 1000 cells


def test_no_label_column_is_read() -> None:
    obs = synthetic_obs()
    without_label = obs.drop(columns=[])  # no disease column at all
    baseline = sample_donor_stratified_cells(without_label, cap=130, seed=3)

    with_label = obs.copy()
    with_label["disease"] = "complete trisomy 21"
    flipped = obs.copy()
    flipped["disease"] = "normal"
    assert np.array_equal(
        sample_donor_stratified_cells(with_label, cap=130, seed=3), baseline
    )
    assert np.array_equal(
        sample_donor_stratified_cells(flipped, cap=130, seed=3), baseline
    )


def test_missing_columns_and_bad_cap_raise() -> None:
    obs = synthetic_obs()
    with pytest.raises(ValueError):
        sample_donor_stratified_cells(obs, cap=0, seed=1)
    with pytest.raises(KeyError):
        sample_donor_stratified_cells(
            obs.drop(columns=["library"]), cap=10, seed=1
        )


@pytest.mark.skipif(not H5AD.exists(), reason="real H5AD not present")
def test_real_obs_two_library_donors() -> None:
    import anndata as ad

    backed = ad.read_h5ad(H5AD, backed="r")
    try:
        obs = backed.obs[["donor_id", "library", "author_cell_type"]].copy()
    finally:
        backed.file.close()
    for column in obs.columns:
        obs[column] = obs[column].astype(str)

    two_library = [
        donor
        for donor, group in obs.groupby("donor_id")
        if group["library"].nunique() > 1
    ]
    assert len(two_library) == 7
    selected = obs.iloc[sample_donor_stratified_cells(obs, cap=1000, seed=22)]
    for donor in two_library:
        donor_obs = obs[obs["donor_id"] == donor]
        donor_sel = selected[selected["donor_id"] == donor]
        assert set(donor_sel["library"]) == set(donor_obs["library"])
        total = len(donor_obs)
        for library in donor_obs["library"].unique():
            expected = len(donor_obs[donor_obs["library"] == library]) / total * 1000
            got = len(donor_sel[donor_sel["library"] == library])
            assert abs(got - expected) <= 2, (donor, library, got, expected)
