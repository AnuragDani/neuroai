"""Offline tests for the cell-state feasibility assessment."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def synthetic_obs():
    donors = ["d1"] * 6 + ["d2"] * 4
    return pd.DataFrame(
        {
            "cell_id": [f"c{i}" for i in range(10)],
            "donor_id": donors,
            "library": ["L1"] * 6 + ["L2"] * 4,
            "disease": ["normal"] * 10,
            "dev_PCW": ["12"] * 10,
            "batch_seq": ["E1"] * 5 + ["E2"] + ["E1"] * 4,
            "sex": ["male"] * 10,
            "tissue_quality": ["ok"] * 10,
            "development_stage": ["stage"] * 10,
            "author_cell_type": ["A", "A", "A", "B", "B", "C", "A", "B", "B", "C"],
            "cell_class": ["x"] * 10,
            "nCount_RNA": np.arange(10) + 1,
            "nFeature_RNA": np.arange(10) + 1,
            "nCount_ATAC": np.arange(10) + 1,
            "nFeature_ATAC": np.arange(10) + 1,
            "nucleosome_signal": np.ones(10),
            "TSS.enrichment": np.ones(10),
            "percent.mt": np.zeros(10),
        }
    )


def test_donor_invariance_flags_within_donor_batch_change():
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    report = module.donor_invariance(synthetic_obs())
    assert report["disease"]["donor_invariant"] is True
    assert report["dev_PCW"]["donor_invariant"] is True
    assert report["batch_seq"]["donor_invariant"] is False
    assert report["batch_seq"]["n_varying_donors"] == 1


def test_support_table_reports_donor_fractions():
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    table = module.support_table(synthetic_obs(), ["A", "B", "C"])
    row = table[(table.donor_id == "d1") & (table.author_cell_type == "A")].iloc[0]
    assert row["n_cells"] == 3
    assert row["n_cells_donor"] == 6
    assert np.isclose(row["fraction_of_donor"], 0.5)


def test_allocate_within_donor_is_deterministic_and_reserves_rare_strata():
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    available = {"A": 1000, "B": 10, "C": 1}
    first = module.allocate_within_donor(50, available)
    second = module.allocate_within_donor(50, dict(reversed(list(available.items()))))
    assert first == second
    assert sum(first.values()) == 50
    assert first["C"] >= 1
    assert first["A"] > first["B"]


def test_allocate_within_donor_returns_all_when_under_cap():
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    available = {"A": 3, "B": 2}
    assert module.allocate_within_donor(50, available) == {"A": 3, "B": 2}


def test_compact_record_strips_per_region_and_allocations(tmp_path):
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    record = {
        "generated_at": "t",
        "sampling_seed": 22,
        "cell_cap": 256,
        "inputs": {},
        "n_accepted_cells": 10,
        "n_capped_cells": 6,
        "n_donors": 2,
        "missingness": {},
        "donor_invariance": {},
        "celltype_counts_full": {},
        "celltype_counts_capped": {},
        "excitatory_lineage_subset_counts_full": {},
        "excitatory_lineage_subset_counts_capped": {},
        "cell_class_counts_full": {},
        "qc_by_celltype_capped": [],
        "atac_panels": {
            "p": {
                "n_regions": 3,
                "total_nnz": 4,
                "panel_zero_regions": 0,
                "chrom_region_counts": {},
                "capped": {
                    "zero_fraction": 0.0,
                    "nonzero_regions": {},
                    "overlap_sum": {},
                    "by_celltype": [],
                },
                "coverage_by_celltype": {},
            }
        },
        "proposal": {"p": {"n_cells": 6, "allocations": [{"donor_id": "d1"}]}},
        "program_feature_coverage": {},
        "claim_boundaries": [],
    }
    args = type(
        "Args",
        (),
        {
            "historical_matrix": tmp_path / "missing.npz",
            "tiebreak_matrix": tmp_path / "missing2.npz",
        },
    )()
    compact = module.compact_record(record, args)
    assert "allocations" not in compact["proposal"]["p"]
    assert compact["inputs"]["historical_matrix_sidecar"] == {}


def test_panel_support_tables_counts_nonzero_regions():
    module = load("assess_cellstate_feasibility", "scripts/assess_cellstate_feasibility.py")
    obs = synthetic_obs()
    regions = ["chr1:1-10", "chr2:1-10", "chr3:1-10"]
    matrix = sparse.csr_matrix(
        np.array(
            [
                [1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            ]
        )
    )
    rows = np.arange(10)
    result = module.panel_support_tables(obs, matrix, regions, rows)
    assert result["n_regions"] == 3
    assert result["capped"]["nonzero_regions"]["mean"] == 0.5
    assert result["panel_zero_regions"] == 0
    assert result["coverage_by_celltype"]["A"]["n_cells"] == 4
