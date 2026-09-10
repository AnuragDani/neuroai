"""Local-model draft, corrected/reviewed by supervisor to keep external effects fixed."""

import numpy as np
import pandas as pd
import pytest

from p22.eval.rna_donor_influence import same_support_components


def test_hand_calculated_decomposition_and_alignment():
    baseline = pd.DataFrame(
        {
            "gene": [f"g{i:04d}" for i in range(800)],
            "coefficient": np.repeat([1.0, 2.0, 3.0, 4.0], 200),
            "avg_log2FC": np.repeat([1.0, 4.0, 2.0, 3.0], 200),
        }
    )
    omission = baseline.iloc[:600].copy()
    omission["coefficient"] = np.repeat([3.0, 1.0, 2.0], 200)
    new_rows = pd.DataFrame(
        {"gene": [f"n{i:04d}" for i in range(200)], "coefficient": 2.0, "avg_log2FC": 3.0}
    )
    omission = pd.concat([omission, new_rows], ignore_index=True)
    result = same_support_components(baseline, omission)
    assert result["status"] == "AVAILABLE"
    assert result["n_baseline_genes"] == 800
    assert result["n_shared_genes"] == 600
    assert result["n_lost_genes"] == 200
    assert result["n_new_genes"] == 200
    for name, value in {
        "rho_baseline": 0.4,
        "rho_baseline_same_support": 0.5,
        "rho_loo": -1.0,
        "same_support_delta": -1.5,
        "support_delta": 0.1,
        "total_delta": -1.4,
    }.items():
        assert result[name] == pytest.approx(value, abs=1e-12)
    assert result == same_support_components(
        baseline.sample(frac=1, random_state=22), omission.sample(frac=1, random_state=22)
    )
