"""Focused checks for the S7 stage orchestrator (no H5AD, synthetic folds only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_confirmation import CONFIRM_RELIABLE, CONFIRM_SKIPPED
from p22.eval.s7_handoff import LABEL_CA_FAVOURED_CONTROL, LABEL_CONTROL_NEGATIVE
from p22.eval.s7_ledger import (
    S7_MODELS,
    Provenance,
    S7FitLedger,
    enumerate_screen_jobs,
    make_fit_id,
)
from p22.eval.s7_pairing import PC_FAIL, PC_PASS
from p22.eval.s7_pipeline import (
    ACTION_RUN_CONFIRMATION,
    ACTION_RUN_PAIRING_PC,
    ACTION_RUN_SCREEN,
    ACTION_RUN_SMOKE,
    ACTION_WRITE_HANDOFF,
    assemble_stage_results,
    decide_next_action,
    pending_jobs,
    planned_stage_jobs,
    run_fit_jobs,
    smoke_is_complete,
    write_pipeline_handoff,
)
from p22.eval.s7_runner import enumerate_smoke_jobs
from p22.eval.s7_screen import SCREEN_CA_FAVOURED, SCREEN_NEGATIVE

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
        max_epochs=1,
        patience=1,
        learning_rate=0.01,
        batch_size=16,
        feature_budget=16,
        cell_cap=10_000,
    )


def make_fold() -> FoldArrays:
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
    return {
        "train": np.flatnonzero(np.isin(donor, ["g0d0", "g0d1", "g1d0", "g1d1"])),
        "val": np.flatnonzero(np.isin(donor, ["g0d2", "g1d2"])),
        "test": np.flatnonzero(np.isin(donor, ["g0d3", "g1d3"])),
    }


def _freeze(ledger: S7FitLedger) -> None:
    ledger.freeze(
        Provenance(
            protocol_id="S7_covariance_20260929",
            spec_sha256="a" * 64,
            source_sha256={"s7_pipeline.py": "b" * 64},
            input_sha256={"h5ad": "c" * 64},
        )
    )


def test_decide_next_action_stage_order() -> None:
    assert decide_next_action(
        smoke_complete=False,
        screen_label=None,
        pc_label=None,
        confirm_label=None,
    )["action"] == ACTION_RUN_SMOKE

    assert decide_next_action(
        smoke_complete=True,
        screen_label=None,
        pc_label=None,
        confirm_label=None,
    )["action"] == ACTION_RUN_SCREEN

    assert decide_next_action(
        smoke_complete=True,
        screen_label=SCREEN_NEGATIVE,
        pc_label=None,
        confirm_label=None,
    )["action"] == ACTION_RUN_PAIRING_PC

    skip = decide_next_action(
        smoke_complete=True,
        screen_label=SCREEN_NEGATIVE,
        pc_label=PC_FAIL,
        confirm_label=None,
    )
    assert skip["action"] == ACTION_WRITE_HANDOFF
    assert skip["confirmation_eligible"] is False

    need_confirm = decide_next_action(
        smoke_complete=True,
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=None,
    )
    assert need_confirm["action"] == ACTION_RUN_CONFIRMATION
    assert need_confirm["confirmation_eligible"] is True

    done = decide_next_action(
        smoke_complete=True,
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_RELIABLE,
    )
    assert done["action"] == ACTION_WRITE_HANDOFF


def test_pending_jobs_skips_completed(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path, max_total_fits=20, smoke_fit_limit=14)
    _freeze(ledger)
    jobs = enumerate_smoke_jobs()
    assert len(pending_jobs(jobs, ledger)) == 14
    first = jobs[0]
    ledger.record_fit(
        first["fit_id"],
        {
            "stage": "smoke",
            "rho": first["rho"],
            "generator_seed": first["generator_seed"],
            "fold": first["fold"],
            "model": first["model"],
            "status": "ok",
        },
    )
    left = pending_jobs(jobs, ledger)
    assert len(left) == 13
    assert first["fit_id"] not in {j["fit_id"] for j in left}
    assert smoke_is_complete(ledger) is False


def test_run_fit_jobs_records_and_skips(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=10, smoke_fit_limit=5)
    _freeze(ledger)
    fold = make_fold()
    positions = split_positions(fold)
    jobs = [
        {
            "fit_id": make_fit_id("smoke", 0.0, SEED, 0, "logreg_rna"),
            "stage": "smoke",
            "rho": 0.0,
            "generator_seed": SEED,
            "fold": 0,
            "model": "logreg_rna",
        },
        {
            "fit_id": make_fit_id("smoke", 0.0, SEED, 0, "logreg_atac"),
            "stage": "smoke",
            "rho": 0.0,
            "generator_seed": SEED,
            "fold": 0,
            "model": "logreg_atac",
        },
    ]
    out = run_fit_jobs(
        jobs,
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger=ledger,
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        protocol=_tiny_protocol(),
        check_disk=False,
    )
    assert out["n_recorded"] == 2
    assert ledger.n_completed == 2
    assert all(r["status"] == "ok" for r in out["records"])

    again = run_fit_jobs(
        jobs,
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        ledger=ledger,
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        protocol=_tiny_protocol(),
        check_disk=False,
    )
    assert again["n_recorded"] == 0
    assert again["n_skipped_completed"] == 2
    assert ledger.n_completed == 2


def test_assemble_skips_confirmation_when_not_eligible() -> None:
    stages = assemble_stage_results(
        screen_records=[],
        pairing_pc={"pc_label": PC_FAIL, "eligible_for_confirmation": False},
        confirmation=None,
    )
    assert stages["confirm_label"] == CONFIRM_SKIPPED
    assert stages["confirmation_eligible"] is False


def test_assemble_leaves_confirm_none_when_eligible_but_missing() -> None:
    records = []
    for fold in range(5):
        for model in S7_MODELS:
            for rho in (0.0, 0.5, 1.0):
                ba = 0.5
                if rho == 1.0:
                    if model == "cross_attention":
                        ba = 0.85
                    elif model in ("logreg_rna", "logreg_atac"):
                        ba = 0.55
                    else:
                        ba = 0.70
                records.append(
                    {
                        "fit_id": make_fit_id("screen", rho, SEED, fold, model),
                        "stage": "screen",
                        "rho": rho,
                        "generator_seed": SEED,
                        "fold": fold,
                        "model": model,
                        "status": "ok",
                        "donor_balanced_accuracy": ba,
                    }
                )
    stages = assemble_stage_results(
        screen_records=records,
        pairing_pc={"pc_label": PC_PASS, "eligible_for_confirmation": True},
        confirmation=None,
    )
    assert stages["screen_label"] == SCREEN_CA_FAVOURED
    assert stages["confirmation_eligible"] is True
    assert stages["confirm_label"] is None


def test_write_pipeline_handoff_negative(tmp_path: Path) -> None:
    stages = {
        "screen_label": SCREEN_NEGATIVE,
        "pc_label": PC_FAIL,
        "confirm_label": CONFIRM_SKIPPED,
        "screen": {"screen_label": SCREEN_NEGATIVE},
        "pairing_pc": {"pc_label": PC_FAIL},
        "confirmation": {"confirm_label": CONFIRM_SKIPPED},
    }
    out = write_pipeline_handoff(
        result_dir=tmp_path / "docs",
        stages=stages,
        ledger_path="/abs/ledger/fit_ledger.jsonl",
        checkpoint_root="/abs/checkpoints",
    )
    assert out["finalize"]["scientific_label"] == LABEL_CONTROL_NEGATIVE
    assert Path(out["paths"]["markdown"]).exists()
    assert Path(out["paths"]["json"]).exists()
    text = Path(out["paths"]["markdown"]).read_text(encoding="utf-8")
    assert "CONTROL_NEGATIVE" in text
    assert "POWER_UNESTABLISHED" in text
    assert "B_NULL" in text


def test_write_pipeline_handoff_favourable(tmp_path: Path) -> None:
    stages = {
        "screen_label": SCREEN_CA_FAVOURED,
        "pc_label": PC_PASS,
        "confirm_label": CONFIRM_RELIABLE,
        "screen": {"screen_label": SCREEN_CA_FAVOURED},
        "pairing_pc": {"pc_label": PC_PASS},
        "confirmation": {"confirm_label": CONFIRM_RELIABLE},
    }
    out = write_pipeline_handoff(result_dir=tmp_path, stages=stages)
    assert out["finalize"]["scientific_label"] == LABEL_CA_FAVOURED_CONTROL
    assert out["payload"]["claims"]["biological_advantage"] is False


def test_planned_stage_job_counts() -> None:
    assert len(planned_stage_jobs("smoke")) == 14
    assert len(planned_stage_jobs("screen")) == len(enumerate_screen_jobs()) == 105
    assert len(planned_stage_jobs("confirm")) == 350
