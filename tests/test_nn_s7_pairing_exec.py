"""Focused checks for the S7 pairing-PC diagnostic executor.

Tiny synthetic folds + injected score_fn for deterministic gates. One live
checkpoint identity path. No H5AD loads.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.planted_signal import plant_covariance
from p22.eval.s7_ledger import S7_N_FOLDS, S7_SCREEN_SEED, make_fit_id
from p22.eval.s7_pairing import (
    PC_FAIL,
    PC_INCOMPLETE,
    PC_PASS,
    S7_IDENTITY_ATOL,
    S7_PAIRING_SEEDS,
)
from p22.eval.s7_pairing_exec import (
    S7_PC_MODEL,
    S7_PC_RHO,
    cell_probs_to_donor,
    expected_ca_rho1_screen_jobs,
    run_pairing_pc_diagnostic,
    select_pc_checkpoint_records,
)
from p22.eval.s7_runner import (
    plant_and_fit_job,
    reload_checkpoint_predictions,
    save_checkpoint,
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


def make_fold(*, tag: str = "") -> FoldArrays:
    donors: list[str] = []
    labels: list[int] = []
    for group in (0, 1):
        for i in range(4):
            donors.extend([f"{tag}g{group}d{i}"] * N_CELLS)
            labels.extend([group] * N_CELLS)
    n_cells = len(donors)
    rng = np.random.default_rng(7)
    train = np.zeros(n_cells, dtype=bool)
    for name in (f"{tag}g0d0", f"{tag}g0d1", f"{tag}g1d0", f"{tag}g1d1"):
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


def split_positions(fold: FoldArrays, *, tag: str = "") -> dict[str, np.ndarray]:
    donor = fold.donor
    train_donors = {f"{tag}g0d0", f"{tag}g0d1", f"{tag}g1d0", f"{tag}g1d1"}
    val_donors = {f"{tag}g0d2", f"{tag}g1d2"}
    test_donors = {f"{tag}g0d3", f"{tag}g1d3"}
    return {
        "train": np.flatnonzero(np.isin(donor, list(train_donors))),
        "val": np.flatnonzero(np.isin(donor, list(val_donors))),
        "test": np.flatnonzero(np.isin(donor, list(test_donors))),
    }


def test_expected_ca_rho1_jobs_cover_five_folds() -> None:
    jobs = expected_ca_rho1_screen_jobs()
    assert len(jobs) == S7_N_FOLDS == 5
    assert all(j["model"] == S7_PC_MODEL for j in jobs)
    assert all(abs(j["rho"] - S7_PC_RHO) < 1e-12 for j in jobs)
    assert all(j["generator_seed"] == S7_SCREEN_SEED for j in jobs)
    assert [j["fold"] for j in jobs] == list(range(5))
    assert jobs[0]["fit_id"] == make_fit_id(
        "screen", 1.0, S7_SCREEN_SEED, 0, S7_PC_MODEL
    )


def test_select_pc_records_reports_missing_checkpoints(tmp_path: Path) -> None:
    jobs = expected_ca_rho1_screen_jobs(n_folds=2)
    records = [
        {
            "fit_id": jobs[0]["fit_id"],
            "fold": 0,
            "model": S7_PC_MODEL,
            "rho": 1.0,
            "generator_seed": S7_SCREEN_SEED,
            "status": "ok",
        }
    ]
    sel = select_pc_checkpoint_records(records, n_folds=2)
    assert sel["complete"] is False
    assert jobs[0]["fit_id"] in sel["missing"]
    assert jobs[1]["fit_id"] in sel["missing"]

    records[0]["checkpoint_path"] = str(tmp_path / "a.pt")
    records.append(
        {
            **jobs[1],
            "checkpoint_path": str(tmp_path / "b.pt"),
            "status": "ok",
        }
    )
    sel2 = select_pc_checkpoint_records(records, n_folds=2)
    assert sel2["complete"] is True
    assert sel2["present"] == 2


def test_cell_probs_to_donor_means() -> None:
    donors = ["d0", "d0", "d1", "d1"]
    labels = [1, 1, 0, 0]
    probs = [0.2, 0.4, 0.8, 1.0]
    out = cell_probs_to_donor(probs, donors, labels)
    assert out["donor_ids"] == ["d0", "d1"]
    assert out["y_true"] == pytest.approx([1.0, 0.0])
    assert out["p"] == pytest.approx([0.3, 0.9])


def test_missing_checkpoints_yield_pc_incomplete() -> None:
    fold = make_fold()
    positions = split_positions(fold)
    result = run_pairing_pc_diagnostic(
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger_records=[],
        n_folds=1,
    )
    assert result["pc_label"] == PC_INCOMPLETE
    assert result["eligible_for_confirmation"] is False
    assert result["selection"]["complete"] is False


def _injected_score_factory(*, labels_by_test_row: np.ndarray, sensitive: bool):
    """Deterministic scorer: calls 1–2 are identity; later calls are shuffles.

    ``score_fold_pairing_pc`` always scores original, then reload, then each
    pairing seed — so a call counter is a stable stand-in for ATAC shuffle.
    """
    state = {"n": 0}

    def score_fn(path, views, test_rows, protocol):  # noqa: ANN001
        del path, views, protocol
        state["n"] += 1
        test = np.asarray(test_rows, dtype=np.int64)
        y = labels_by_test_row
        # First two calls: original + identity reload.
        if state["n"] <= 2 or not sensitive:
            return np.where(y == 1, 0.92, 0.08).astype(np.float64)
        return np.full(test.shape[0], 0.5, dtype=np.float64)

    return score_fn


def test_diagnostic_sensitive_pass_and_insensitive_fail(tmp_path: Path) -> None:
    fold = make_fold(tag="t")
    positions = split_positions(fold, tag="t")
    cell_ids = np.asarray([f"c{i}" for i in range(fold.donor.size)], dtype=object)
    ckpt = tmp_path / "fake.pt"
    ckpt.write_bytes(b"unused")
    fit_id = make_fit_id("screen", 1.0, SEED, 0, S7_PC_MODEL)
    records = [
        {
            "fit_id": fit_id,
            "stage": "screen",
            "rho": 1.0,
            "generator_seed": SEED,
            "fold": 0,
            "model": S7_PC_MODEL,
            "checkpoint_path": str(ckpt),
            "status": "ok",
        }
    ]
    _, fake = plant_covariance(fold, rho=1.0, generator_seed=SEED, cell_ids=cell_ids)
    labels_test = fake[positions["test"]]

    sensitive = run_pairing_pc_diagnostic(
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger_records=records,
        cell_ids_by_fold={0: cell_ids},
        n_folds=1,
        generator_seed=SEED,
        score_fn=_injected_score_factory(
            labels_by_test_row=labels_test, sensitive=True
        ),
    )
    assert sensitive["pc_label"] == PC_PASS
    assert sensitive["eligible_for_confirmation"] is True
    assert sensitive["n_donors"] == 2
    assert sensitive["evaluate"]["drops"]["n_seeds"] == len(S7_PAIRING_SEEDS)

    insensitive = run_pairing_pc_diagnostic(
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger_records=records,
        cell_ids_by_fold={0: cell_ids},
        n_folds=1,
        generator_seed=SEED,
        score_fn=_injected_score_factory(
            labels_by_test_row=labels_test, sensitive=False
        ),
    )
    assert insensitive["pc_label"] == PC_FAIL
    assert insensitive["eligible_for_confirmation"] is False


def test_live_checkpoint_identity_path(tmp_path: Path) -> None:
    """Fit tiny CA, save checkpoint, diagnostic identity must pass atol."""
    # Untagged donors match runner tests so fake labels keep both test classes.
    fold = make_fold()
    positions = split_positions(fold)
    cell_ids = np.asarray([f"c{i}" for i in range(fold.donor.size)], dtype=object)
    job = {
        "fit_id": make_fit_id("screen", 1.0, SEED, 0, S7_PC_MODEL),
        "stage": "screen",
        "rho": 1.0,
        "generator_seed": SEED,
        "fold": 0,
        "model": S7_PC_MODEL,
    }
    record = plant_and_fit_job(
        fold, job, positions, cell_ids=cell_ids, protocol=_tiny_protocol()
    )
    assert record["status"] in {"ok", "single_class"}
    assert record.get("checkpoint") is not None
    path = save_checkpoint(record, tmp_path)
    assert path is not None
    record["checkpoint_path"] = str(path)

    planted, _ = plant_covariance(
        fold, rho=1.0, generator_seed=SEED, cell_ids=cell_ids
    )
    views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
    a = reload_checkpoint_predictions(path, views, positions["test"], _tiny_protocol())
    b = reload_checkpoint_predictions(path, views, positions["test"], _tiny_protocol())
    assert np.max(np.abs(a - b)) <= S7_IDENTITY_ATOL

    short_seeds = (3001, 3002)

    def score_fn(p, v, t, proto):  # noqa: ANN001
        return reload_checkpoint_predictions(p, v, t, proto)

    result = run_pairing_pc_diagnostic(
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger_records=[record],
        cell_ids_by_fold={0: cell_ids},
        protocol=_tiny_protocol(),
        pairing_seeds=short_seeds,
        n_folds=1,
        generator_seed=SEED,
        score_fn=score_fn,
    )
    assert result["evaluate"]["identity"]["passed"] is True
    assert result["pc_label"] in {PC_PASS, PC_FAIL, PC_INCOMPLETE}
    assert result["n_donors"] == 2
