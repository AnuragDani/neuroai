"""Tests for P2 planted gene-aligned S6 regime (offline + helper checks)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


bench = load("run_nn_planted_benchmark", "scripts/run_nn_planted_benchmark.py")
v5 = load("nn_v5_planted_gene_aligned", "scripts/nn_v5_planted_gene_aligned.py")

from p22.data.nn_inputs import FoldArrays  # noqa: E402
from p22.eval.planted_signal import GENE_ALIGNED_SCENARIO, fake_donor_labels, plant  # noqa: E402


def _matched_fold(n_genes: int = 8) -> FoldArrays:
    donors, labels = [], []
    for group in (0, 1):
        for i in range(4):
            donors.extend([f"g{group}d{i}"] * 20)
            labels.extend([group] * 20)
    n = len(donors)
    rng = np.random.default_rng(3)
    train = np.zeros(n, dtype=bool)
    train[: n // 2] = True
    return FoldArrays(
        rna=rng.normal(size=(n, n_genes)).astype(np.float32),
        atac=rng.normal(size=(n, n_genes)).astype(np.float32),
        qc=np.zeros((n, 5), dtype=np.float32),
        label=np.asarray(labels, dtype=np.int64),
        donor=np.asarray(donors, dtype=object),
        nuisance_codes={},
        train_position=train,
        gene_ids=np.asarray([f"g{i}" for i in range(n_genes)], dtype=object),
        region_ids=tuple(f"g{i}" for i in range(n_genes)),
        evidence={},
    )


def test_gene_aligned_delta_grid():
    cells = bench.gene_aligned_delta_grid()
    assert cells == [("S6", 0.5), ("S6", 1.0)]
    assert len(bench.delta_grid()) == 16  # N4 grid unchanged


def test_s6_requires_matched_widths():
    fold = _matched_fold(6)
    fold.atac = fold.atac[:, :4]
    try:
        plant(fold, GENE_ALIGNED_SCENARIO, 1.0, seed=0)
        raise AssertionError("expected ValueError")
    except ValueError as err:
        assert "matched" in str(err).lower()


def test_s6_plants_per_gene_interaction():
    fold = _matched_fold(6)
    fake = fake_donor_labels(fold.donor, fold.label)
    planted, _ = plant(fold, GENE_ALIGNED_SCENARIO, 1.0, seed=0)
    train = fold.train_position
    medians = np.median(fold.atac[train], axis=0)
    pos = fake == 1
    for g in range(6):
        context = pos & (fold.atac[:, g] > medians[g])
        other = ~context
        assert np.allclose(planted.rna[context, g] - fold.rna[context, g], 1.0)
        assert np.array_equal(planted.rna[other, g], fold.rna[other, g])
    assert np.array_equal(planted.atac, fold.atac)


def test_gene_aligned_regime_labels_ca_favoured():
    records = []
    for fold in range(3):
        records.append({
            "scenario": "S6", "delta": 1.0, "fold": fold, "model": "gene_aligned_ca",
            "donor_balanced_accuracy": 0.9, "status": "ok",
        })
        records.append({
            "scenario": "S6", "delta": 1.0, "fold": fold, "model": "gene_aligned_tc",
            "donor_balanced_accuracy": 0.7, "status": "ok",
        })
        records.append({
            "scenario": "S6", "delta": 1.0, "fold": fold, "model": "rna_atac_concat",
            "donor_balanced_accuracy": 0.65, "status": "ok",
        })
    labels = bench.gene_aligned_regime_labels(records)
    assert labels["S6@1.0"]["regime"] == "CA_FAVOURED"
    assert labels["S6@1.0"]["cross_attention_minus_best_non_attention"] >= 0.07


def test_summarize_null_finding():
    records = []
    for fold in range(2):
        for delta in (0.5, 1.0):
            for model, ba in (
                ("gene_aligned_ca", 0.6),
                ("gene_aligned_tc", 0.7),
                ("rna_atac_concat", 0.75),
            ):
                records.append({
                    "scenario": "S6", "delta": delta, "fold": fold, "model": model,
                    "donor_balanced_accuracy": ba, "status": "ok",
                })
    summary = v5.summarize(records, {"ga_n_genes": 64}, cap=1000)
    assert summary["any_ca_favoured"] is False
    assert "null" in summary["finding"].lower()
    assert set(summary["regime_labels"]) == {"S6@0.5", "S6@1.0"}
