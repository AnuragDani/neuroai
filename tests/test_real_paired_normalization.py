"""Offline tests for the paired normalization-sensitivity helpers."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse


def module():
    spec = importlib.util.spec_from_file_location(
        "run_real_paired_normalization_sensitivity",
        Path(__file__).parents[1] / "scripts/run_real_paired_normalization_sensitivity.py",
    )
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def test_apply_log1p_sparse_matches_dense():
    mod = module()
    dense = np.array([[0.0, 1.0, 3.0], [10.0, 0.0, 7.0]])
    matrix = sparse.csr_matrix(dense)
    result = mod.apply_log1p(matrix)
    assert sparse.issparse(result)
    np.testing.assert_allclose(result.toarray(), np.log1p(dense))
    # original unchanged
    np.testing.assert_allclose(matrix.toarray(), dense)


def test_apply_log1p_dense_returns_log1p():
    mod = module()
    dense = np.array([[0.0, 2.0], [4.0, 8.0]])
    np.testing.assert_allclose(mod.apply_log1p(dense), np.log1p(dense))


def test_variant_views_raw_is_identity():
    mod = module()
    views = {"a": sparse.csr_matrix(np.eye(2)), "b": sparse.csr_matrix(np.ones((2, 3)))}
    result = mod.variant_views(views, "raw_standard_scaler")
    assert result is views


def test_variant_views_log1p_transforms_each_view():
    mod = module()
    views = {
        "a": sparse.csr_matrix(np.array([[0.0, 1.0]])),
        "b": sparse.csr_matrix(np.array([[3.0], [0.0]])),
    }
    result = mod.variant_views(views, "log1p_standard_scaler")
    np.testing.assert_allclose(result["a"].toarray(), np.log1p(np.array([[0.0, 1.0]])))
    np.testing.assert_allclose(result["b"].toarray(), np.log1p(np.array([[3.0], [0.0]])))


def test_variant_views_rejects_unknown_variant():
    mod = module()
    with pytest.raises(ValueError):
        mod.variant_views({}, "median_scale")
