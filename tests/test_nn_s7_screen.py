"""Focused checks for S7 screen coverage, controls and CA_FAVOURED gate.

Synthetic records and index mapping only — no H5AD, no model fits.
"""

from __future__ import annotations

import numpy as np
import pytest

from p22.eval.s7_ledger import S7_MODELS, S7_N_FOLDS, S7_RHO_GRID
from p22.eval.s7_screen import (
    SCREEN_CA_FAVOURED,
    SCREEN_INCOMPLETE,
    SCREEN_INVALID,
    SCREEN_NEGATIVE,
    evaluate_screen,
    fold_cell_ids,
    marginal_check,
    null_check,
    rho1_regime,
    screen_coverage,
)


def _full_ok_records(
    *,
    ba_by_rho_model: dict[tuple[float, str], float] | None = None,
) -> list[dict]:
    """Complete 105-cell screen with configurable mean BA per (rho, model)."""
    defaults = {
        (0.0, m): 0.50 for m in S7_MODELS
    }
    defaults.update({(0.5, m): 0.55 for m in S7_MODELS})
    # Favourable rho=1 defaults: CA clearly ahead of non-attention; single-view low.
    defaults.update({(1.0, m): 0.70 for m in S7_MODELS})
    defaults[(1.0, "cross_attention")] = 0.85
    defaults[(1.0, "logreg_rna")] = 0.52
    defaults[(1.0, "logreg_atac")] = 0.51
    if ba_by_rho_model:
        defaults.update(ba_by_rho_model)
    records: list[dict] = []
    for rho in S7_RHO_GRID:
        for fold in range(S7_N_FOLDS):
            for model in S7_MODELS:
                records.append(
                    {
                        "rho": rho,
                        "fold": fold,
                        "model": model,
                        "donor_balanced_accuracy": defaults[(float(rho), model)],
                        "status": "ok",
                    }
                )
    return records


def test_fold_cell_ids_maps_metadata_through_train_val_test_order() -> None:
    index = np.asarray([f"c{i}" for i in range(10)], dtype=object)
    train = np.asarray([3, 1, 7], dtype=np.int64)
    val = np.asarray([0, 9], dtype=np.int64)
    test = np.asarray([4, 2], dtype=np.int64)
    mapped = fold_cell_ids(index, train, val, test)
    assert mapped.tolist() == ["c3", "c1", "c7", "c0", "c9", "c4", "c2"]
    with pytest.raises(ValueError, match="out of range"):
        fold_cell_ids(index, np.asarray([0]), np.asarray([10]), np.asarray([1]))


def test_screen_coverage_requires_all_105() -> None:
    full = _full_ok_records()
    assert screen_coverage(full)["complete"] is True
    assert screen_coverage(full)["n_expected"] == 105
    partial = [r for r in full if not (r["rho"] == 1.0 and r["fold"] == 4 and r["model"] == "cross_attention")]
    cov = screen_coverage(partial)
    assert cov["complete"] is False
    assert cov["missing"] == [{"rho": 1.0, "fold": 4, "model": "cross_attention"}]


def test_null_and_marginal_controls() -> None:
    good = _full_ok_records()
    assert null_check(good)["passed"] is True
    assert marginal_check(good)["passed"] is True

    leaky = _full_ok_records(ba_by_rho_model={(1.0, "logreg_rna"): 0.72})
    marg = marginal_check(leaky)
    assert marg["passed"] is False
    assert "logreg_rna" in marg["failures"]

    broken_null = _full_ok_records(ba_by_rho_model={(0.0, "token_concat"): 0.90})
    null = null_check(broken_null)
    assert null["passed"] is False
    assert "token_concat" in null["failures"]


def test_rho1_regime_ca_favoured_and_linear_sufficient() -> None:
    favoured = rho1_regime(_full_ok_records())
    assert favoured["regime"] == "CA_FAVOURED"
    assert favoured["ca_favoured"] is True
    assert favoured["cross_attention_minus_best_non_attention"] >= 0.07

    linear = _full_ok_records(
        ba_by_rho_model={
            (1.0, "logreg_concat"): 0.90,
            (1.0, "cross_attention"): 0.88,
            (1.0, "token_concat"): 0.80,
        }
    )
    assert rho1_regime(linear)["regime"] == "LINEAR_SUFFICIENT"


def test_evaluate_screen_labels() -> None:
    assert evaluate_screen(_full_ok_records())["screen_label"] == SCREEN_CA_FAVOURED
    assert evaluate_screen(_full_ok_records())["eligible_for_pairing_pc"] is True

    incomplete = evaluate_screen(_full_ok_records()[:-1])
    assert incomplete["screen_label"] == SCREEN_INCOMPLETE
    assert incomplete["eligible_for_pairing_pc"] is False

    # single_class rows are not scoreable: coverage must refuse PASS.
    single_class_rows = _full_ok_records()
    for row in single_class_rows:
        if row["rho"] == 1.0 and row["fold"] == 0 and row["model"] == "cross_attention":
            row["status"] = "single_class"
            row["donor_balanced_accuracy"] = None
            break
    single_class = evaluate_screen(single_class_rows)
    assert single_class["screen_label"] == SCREEN_INCOMPLETE
    assert single_class["eligible_for_pairing_pc"] is False
    assert single_class["coverage"]["complete"] is False

    invalid = evaluate_screen(
        _full_ok_records(ba_by_rho_model={(0.0, "gated_fusion"): 0.10})
    )
    assert invalid["screen_label"] == SCREEN_INVALID

    negative = evaluate_screen(
        _full_ok_records(
            ba_by_rho_model={
                (1.0, "cross_attention"): 0.72,
                (1.0, "token_concat"): 0.71,
                (1.0, "logreg_concat"): 0.60,
            }
        )
    )
    assert negative["screen_label"] == SCREEN_NEGATIVE
    assert negative["eligible_for_pairing_pc"] is False
    assert negative["rho1_regime"]["regime"] != "CA_FAVOURED"
