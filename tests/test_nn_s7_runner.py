"""Focused checks for the S7 single-fit runner (synthetic arrays only).

Tiny FoldArrays + short-epoch protocol. No H5AD loads, no full screen.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.planted_signal import plant_covariance
from p22.eval.s7_ledger import (
    S7_MODELS,
    S7_SMOKE_FIT_LIMIT,
    Provenance,
    S7FitLedger,
    make_fit_id,
)
from p22.eval.s7_pairing import S7_IDENTITY_ATOL
from p22.eval.s7_runner import (
    S7_CHECKPOINT_MODELS,
    S7_PROTOCOL,
    S7_SMOKE_FOLD,
    S7_SMOKE_RHOS,
    check_disk_resources,
    enumerate_smoke_jobs,
    fit_s7_arm,
    ledger_payload,
    plant_and_fit_job,
    record_completed_fit,
    reload_checkpoint_predictions,
    save_checkpoint,
    should_retain_checkpoint,
)
from p22.models.fusion import VIEW_A, VIEW_B

N_CELLS = 12
N_GENES = 16
N_REGIONS = 16
SEED = 1001


def _tiny_protocol() -> MultiomeProtocol:
    return MultiomeProtocol(
        n_tokens=4,
        embed_dim=8,
        hidden_dim=16,
        n_heads=2,
        dropout=0.0,
        n_repeats=1,
        n_folds=5,
        split_seed=0,
        model_seed=0,
        sampling_seed=22,
        max_epochs=2,
        patience=2,
        learning_rate=0.01,
        batch_size=16,
        feature_budget=16,
        cell_cap=10_000,
    )


def make_fold() -> FoldArrays:
    """Eight donors (4/4 labels), 12 cells each — both classes in each split."""
    donors: list[str] = []
    labels: list[int] = []
    for group in (0, 1):
        for i in range(4):
            donors.extend([f"g{group}d{i}"] * N_CELLS)
            labels.extend([group] * N_CELLS)
    n_cells = len(donors)
    rng = np.random.default_rng(7)
    train = np.zeros(n_cells, dtype=bool)
    for name in ("g0d0", "g0d1", "g1d0", "g1d1"):
        train[np.asarray(donors) == name] = True
    return FoldArrays(
        rna=rng.normal(size=(n_cells, N_GENES)).astype(np.float32),
        atac=rng.normal(size=(n_cells, N_REGIONS)).astype(np.float32),
        qc=rng.normal(size=(n_cells, 3)).astype(np.float32),
        label=np.asarray(labels, dtype=np.int64),
        donor=np.asarray(donors, dtype=object),
        nuisance_codes={},
        train_position=train,
        gene_ids=np.asarray([f"g{i}" for i in range(N_GENES)], dtype=object),
        region_ids=tuple(f"r{i}" for i in range(N_REGIONS)),
        evidence={},
    )


def split_positions(fold: FoldArrays) -> dict[str, np.ndarray]:
    donor = fold.donor
    train_donors = {"g0d0", "g0d1", "g1d0", "g1d1"}
    val_donors = {"g0d2", "g1d2"}
    test_donors = {"g0d3", "g1d3"}
    return {
        "train": np.flatnonzero(np.isin(donor, list(train_donors))),
        "val": np.flatnonzero(np.isin(donor, list(val_donors))),
        "test": np.flatnonzero(np.isin(donor, list(test_donors))),
    }


def test_enumerate_smoke_is_14_predeclared() -> None:
    jobs = enumerate_smoke_jobs()
    assert len(jobs) == len(S7_SMOKE_RHOS) * len(S7_MODELS) == 14
    assert len(jobs) <= S7_SMOKE_FIT_LIMIT
    assert all(j["stage"] == "smoke" for j in jobs)
    assert all(j["fold"] == S7_SMOKE_FOLD for j in jobs)
    ids = [j["fit_id"] for j in jobs]
    assert len(ids) == len(set(ids))
    assert jobs[0]["fit_id"] == make_fit_id(
        "smoke", S7_SMOKE_RHOS[0], SEED, S7_SMOKE_FOLD, S7_MODELS[0]
    )


def test_disk_resource_gate_refuses_low_free(tmp_path: Path) -> None:
    ok = check_disk_resources(output_root=tmp_path, min_free_gib=0.001)
    assert ok["ok"] is True
    with pytest.raises(RuntimeError, match="disk free"):
        check_disk_resources(output_root=tmp_path, min_free_gib=10**9)


def test_logreg_plant_and_fit_records_ok() -> None:
    fold = make_fold()
    positions = split_positions(fold)
    cell_ids = np.asarray([f"c{i}" for i in range(fold.donor.size)], dtype=object)
    job = {
        "fit_id": make_fit_id("smoke", 1.0, SEED, 0, "logreg_concat"),
        "stage": "smoke",
        "rho": 1.0,
        "generator_seed": SEED,
        "fold": 0,
        "model": "logreg_concat",
    }
    record = plant_and_fit_job(
        fold, job, positions, cell_ids=cell_ids, protocol=_tiny_protocol()
    )
    assert record["status"] == "ok"
    assert record["fit_id"] == job["fit_id"]
    assert 0.0 <= float(record["donor_balanced_accuracy"]) <= 1.0
    assert record["n_test_donors"] == 2
    assert "checkpoint" in record


def test_unknown_model_refused() -> None:
    fold = make_fold()
    positions = split_positions(fold)
    planted, fake = plant_covariance(fold, rho=0.0, generator_seed=SEED)
    views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
    with pytest.raises(ValueError, match="unknown S7 model"):
        fit_s7_arm(
            "not_a_model",
            views,
            fake,
            planted.donor,
            positions,
            _tiny_protocol(),
        )


def test_neural_checkpoint_identity_reload(tmp_path: Path) -> None:
    fold = make_fold()
    positions = split_positions(fold)
    cell_ids = np.asarray([f"c{i}" for i in range(fold.donor.size)], dtype=object)
    job = {
        "fit_id": make_fit_id("screen", 1.0, SEED, 0, "token_concat"),
        "stage": "screen",
        "rho": 1.0,
        "generator_seed": SEED,
        "fold": 0,
        "model": "token_concat",
    }
    assert should_retain_checkpoint(job)
    assert "token_concat" in S7_CHECKPOINT_MODELS
    record = plant_and_fit_job(
        fold, job, positions, cell_ids=cell_ids, protocol=_tiny_protocol()
    )
    assert record["status"] == "ok"
    path = save_checkpoint(record, tmp_path)
    assert path is not None and path.exists()
    planted, _ = plant_covariance(
        fold, rho=1.0, generator_seed=SEED, cell_ids=cell_ids
    )
    views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
    reloaded = reload_checkpoint_predictions(
        path, views, positions["test"], protocol=_tiny_protocol()
    )
    original = np.asarray(record["test_cell_probabilities"], dtype=np.float64)
    assert reloaded.shape == original.shape
    assert np.max(np.abs(reloaded - original)) <= S7_IDENTITY_ATOL


def test_ledger_records_fit_without_checkpoint_blob(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path, max_total_fits=5, smoke_fit_limit=3)
    ledger.freeze(
        Provenance(
            protocol_id="S7_covariance_20260929",
            spec_sha256="a" * 64,
            source_sha256={"s7_runner.py": "b" * 64},
            input_sha256={"h5ad": "c" * 64},
        )
    )
    fold = make_fold()
    positions = split_positions(fold)
    job = {
        "fit_id": make_fit_id("smoke", 0.0, SEED, 0, "logreg_rna"),
        "stage": "smoke",
        "rho": 0.0,
        "generator_seed": SEED,
        "fold": 0,
        "model": "logreg_rna",
    }
    record = plant_and_fit_job(
        fold, job, positions, protocol=_tiny_protocol()
    )
    assert "checkpoint" in record
    payload = ledger_payload(record)
    assert "checkpoint" not in payload
    written = record_completed_fit(ledger, record, checkpoint_dir=tmp_path / "ckpt")
    assert written["fit_id"] == job["fit_id"]
    assert ledger.n_completed == 1
    assert "checkpoint_path" not in written


def test_frozen_s7_protocol_matches_spec_widths() -> None:
    assert S7_PROTOCOL.n_tokens == 8
    assert S7_PROTOCOL.embed_dim == 32
    assert S7_PROTOCOL.hidden_dim == 128
    assert S7_PROTOCOL.n_heads == 4
    assert S7_PROTOCOL.max_epochs == 20
    assert S7_PROTOCOL.n_folds == 5
    assert S7_PROTOCOL.n_repeats == 1
