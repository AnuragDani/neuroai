"""Offline tests for the N16 cell-state spectrum helpers.

Synthetic donors with a planted shift in one cell type: only that type is
significant after Holm. No real data is read.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


spec_mod = load("analyze_nn_v2_spectrum", "scripts/analyze_nn_v2_spectrum.py")


def test_holm_adjust_known_values():
    p = np.array([0.01, 0.04, 0.03, 0.5])
    adj = spec_mod.holm_adjust(p)
    # sorted p: 0.01, 0.03, 0.04, 0.5 -> *4, *3, *2, *1 with running max
    assert np.allclose(adj, [0.04, 0.09, 0.09, 0.5])


def test_holm_adjust_nan_passthrough():
    adj = spec_mod.holm_adjust([0.02, np.nan, 0.5])
    assert adj[0] == 0.04
    assert np.isnan(adj[1])
    assert adj[2] == 0.5


def test_derive_stage_bins():
    stages = spec_mod.derive_stage([11.0, 12.5, 13.0, 16.5, 17.5, 20.9, 9.0])
    assert list(stages) == [
        "PCW11_12",
        "PCW11_12",
        "PCW13_16",
        "PCW13_16",
        "PCW17_20",
        "PCW17_20",
        "unknown",
    ]


def _synthetic_cells(seed=7, n_cells_per_donor=25):
    rng = np.random.default_rng(seed)
    donors_con = [f"con{d}" for d in range(8)]
    donors_ds = [f"ds{d}" for d in range(8)]
    stage_by_donor = {}
    for i, d in enumerate(donors_con + donors_ds):
        stage_by_donor[d] = ["PCW11_12", "PCW13_16", "PCW17_20"][i % 3]
    rows = []
    for ctype in ("t0", "t1", "t2", "t3"):
        shift = 1.5 if ctype == "t2" else 0.0
        for donor in donors_con + donors_ds:
            is_ds = donor in donors_ds
            donor_offset = rng.normal(0, 0.05)
            for _ in range(n_cells_per_donor):
                rows.append(
                    {
                        "donor": donor,
                        "label": 1 if is_ds else 0,
                        "author_cell_type": ctype,
                        "stage": stage_by_donor[donor],
                        "s_mean": rng.normal(0, 0.15) + donor_offset + (shift if is_ds else 0.0),
                        "a_mean": rng.normal(0.5, 0.1),
                        "chr21_dosage": rng.normal(0, 1) + (1.0 if is_ds else 0.0),
                        "dev_PCW": rng.normal(15, 2),
                        "log_nCount_RNA": rng.normal(8, 0.5),
                        "log_nCount_ATAC": rng.normal(7, 0.5),
                    }
                )
    return pd.DataFrame(rows)


def test_planted_shift_only_target_type_significant():
    cells = _synthetic_cells()
    payload = spec_mod.analyze_cells(cells, n_boot=200, n_perm=400, seed=22)
    assert payload["status"] == "estimated"
    assert set(payload["eligible_types"]) == {"t0", "t1", "t2", "t3"}
    by_type = {r["author_cell_type"]: r for r in payload["results"]}
    assert by_type["t2"]["s"]["significant"] is True
    for other in ("t0", "t1", "t3"):
        assert by_type[other]["s"]["significant"] is False
    assert payload["spectrum_call"] == "SPECTRUM_LOCALIZED:t2"
    assert by_type["t2"]["s"]["p_holm"] is not None
    assert by_type["t2"]["s"]["diff"] > 1.0
    assert by_type["t2"]["s"]["ci_low"] > 0


def test_support_floor_excludes_small_groups():
    cells = _synthetic_cells()
    # Make t3 rare in the CON group only: 3 donors with 5 cells, rest dropped.
    mask = (cells["author_cell_type"] == "t3") & (cells["label"] == 0)
    keep = cells.loc[mask, "donor"].isin(["con0", "con1", "con2"])
    drop = mask & ~keep
    cells = cells.loc[~drop]
    eligible, excluded = spec_mod.eligible_types(cells)
    assert "t3" not in eligible
    assert any(e["author_cell_type"] == "t3" for e in excluded)


def test_no_eligible_types_returns_not_estimable():
    cells = _synthetic_cells()
    cells = cells.loc[cells["author_cell_type"] == "t0"].head(40)
    payload = spec_mod.analyze_cells(cells, n_boot=50, n_perm=50, seed=1)
    assert payload["spectrum_call"] == "NOT_ESTIMABLE"
    assert payload["results"] == []


def test_log1p_depth_aliases_enable_residualization():
    cells = _synthetic_cells()
    cells = cells.rename(
        columns={
            "log_nCount_RNA": "log1p_nCount_RNA",
            "log_nCount_ATAC": "log1p_nCount_ATAC",
        }
    )
    payload = spec_mod.analyze_cells(cells, n_boot=50, n_perm=100, seed=3)
    assert payload["status"] == "estimated"
    assert all(r.get("residualized") is not None for r in payload["results"])
