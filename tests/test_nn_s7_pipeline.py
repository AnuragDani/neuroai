"""Focused checks for the S7 stage orchestrator (no H5AD, synthetic folds only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.s7_confirmation import (
    CONFIRM_NEGATIVE,
    CONFIRM_RELIABLE,
    CONFIRM_SKIPPED,
)
from p22.eval.s7_handoff import LABEL_CA_FAVOURED_CONTROL, LABEL_CONTROL_NEGATIVE
from p22.eval.s7_ledger import (
    S7_MODELS,
    Provenance,
    S7FitLedger,
    enumerate_screen_jobs,
    make_fit_id,
)
from p22.eval.s7_pairing import PC_FAIL, PC_INCOMPLETE, PC_PASS
from p22.eval.s7_pipeline import (
    ACTION_RUN_CONFIRMATION,
    ACTION_RUN_PAIRING_PC,
    ACTION_RUN_SCREEN,
    ACTION_RUN_SMOKE,
    ACTION_WRITE_HANDOFF,
    assemble_stage_results,
    decide_next_action,
    empty_stage_state,
    execute_next_stage,
    load_stage_state,
    pending_jobs,
    planned_stage_jobs,
    run_fit_jobs,
    run_until_handoff,
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


def test_run_fit_jobs_uses_fold_pack_resolver_per_seed(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=10, smoke_fit_limit=5)
    _freeze(ledger)
    screen_fold = make_fold()
    confirm_fold = make_fold()
    assert id(screen_fold) != id(confirm_fold)
    positions = split_positions(screen_fold)
    seen: list[tuple[int, int]] = []

    def _resolver(seed: int):
        fold = screen_fold if seed == SEED else confirm_fold
        return {
            "folds_by_index": {0: fold},
            "positions_by_fold": {0: positions},
            "cell_ids_by_fold": {0: np.asarray([f"c{i}" for i in range(fold.donor.size)])},
        }

    def _fit(fold, job, positions, **kwargs):
        del positions, kwargs
        seen.append((int(job["generator_seed"]), id(fold)))
        return _stub_fit(fold, job, split_positions(fold))

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
            "fit_id": make_fit_id("confirm", 1.0, 2001, 0, "logreg_rna"),
            "stage": "confirm",
            "rho": 1.0,
            "generator_seed": 2001,
            "fold": 0,
            "model": "logreg_rna",
        },
    ]
    out = run_fit_jobs(
        jobs,
        folds_by_index={0: screen_fold},
        positions_by_fold={0: positions},
        ledger=ledger,
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_fit,
        fold_pack_resolver=_resolver,
    )
    assert out["n_recorded"] == 2
    assert seen == [(SEED, id(screen_fold)), (2001, id(confirm_fold))]


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


def _stub_fit(fold, job, positions, **kwargs):
    """Deterministic stub that never trains; records BA from job model/rho."""
    del fold, positions, kwargs
    model = str(job["model"])
    rho = float(job["rho"])
    ba = 0.50
    if abs(rho - 1.0) < 1e-12:
        if model == "cross_attention":
            ba = 0.85
        elif model in ("logreg_rna", "logreg_atac"):
            ba = 0.55
        else:
            ba = 0.70
    elif abs(rho) < 1e-12:
        ba = 0.50
    # Retainable CA/TC rho=1 jobs need a checkpoint blob for save_checkpoint.
    retain = model in {"cross_attention", "token_concat"} and abs(rho - 1.0) < 1e-12
    checkpoint = None
    if retain:
        checkpoint = {
            "kind": "neural",
            "widths": [16, 16],
            "protocol": {
                "n_tokens": 4,
                "embed_dim": 8,
                "hidden_dim": 16,
                "n_heads": 2,
                "dropout": 0.0,
                "model_seed": int(job["generator_seed"]),
            },
            "state_dict": {},
        }
    return {
        "fit_id": job["fit_id"],
        "stage": job["stage"],
        "rho": job["rho"],
        "generator_seed": job["generator_seed"],
        "fold": job["fold"],
        "model": model,
        "status": "ok",
        "donor_balanced_accuracy": ba,
        "donor_auroc": 0.5,
        "donor_log_loss": 0.7,
        "n_test_donors": 2,
        "model_seed": int(job["generator_seed"]),
        "checkpoint": checkpoint,
        "test_cell_probabilities": None,
        "donor_probabilities": {
            "donor_id": ["d0", "d1"],
            "probability": [0.2, 0.8],
            "label": [0.0, 1.0],
        },
    }


def _record_smoke_complete(ledger: S7FitLedger) -> None:
    for job in enumerate_smoke_jobs():
        ledger.record_fit(
            job["fit_id"],
            {
                "stage": "smoke",
                "rho": job["rho"],
                "generator_seed": job["generator_seed"],
                "fold": job["fold"],
                "model": job["model"],
                "status": "ok",
                "donor_balanced_accuracy": 0.5,
            },
        )


def test_execute_next_stage_smoke_then_screen(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=200, smoke_fit_limit=14)
    _freeze(ledger)
    fold = make_fold()
    positions = split_positions(fold)
    out = execute_next_stage(
        ledger=ledger,
        folds_by_index={0: fold},
        positions_by_fold={0: positions},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
    )
    assert out["action"] == ACTION_RUN_SMOKE
    assert out["done"] is False
    assert out["state"]["smoke_complete"] is True
    assert smoke_is_complete(ledger)
    assert load_stage_state(tmp_path / "out")["smoke_complete"] is True

    again = execute_next_stage(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        state=out["state"],
    )
    assert again["action"] == ACTION_RUN_SCREEN
    assert again["state"]["screen_label"] == SCREEN_CA_FAVOURED
    assert ledger.n_completed == 14 + 105


def test_run_until_handoff_skips_confirmation_on_pc_fail(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=200, smoke_fit_limit=14)
    _freeze(ledger)
    fold = make_fold()
    positions = split_positions(fold)

    def _pc_fail(**kwargs):
        del kwargs
        return {
            "pc_label": PC_FAIL,
            "eligible_for_confirmation": False,
            "reason": "injected fail",
        }

    out = run_until_handoff(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        pairing_fn=_pc_fail,
    )
    assert out["done"] is True
    assert out["final_action"] == ACTION_WRITE_HANDOFF
    actions = [s["action"] for s in out["steps"]]
    assert ACTION_RUN_SMOKE in actions
    assert ACTION_RUN_SCREEN in actions
    assert ACTION_RUN_PAIRING_PC in actions
    assert ACTION_RUN_CONFIRMATION not in actions
    assert out["state"]["confirm_label"] == CONFIRM_SKIPPED
    assert out["state"]["pc_label"] == PC_FAIL
    md = Path(out["state"]["handoff_paths"]["markdown"])
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    assert "CONTROL_NEGATIVE" in text
    assert "POWER_UNESTABLISHED" in text
    # No confirmation fits recorded.
    assert not any(r.get("stage") == "confirm" for r in ledger.records.values())


def test_run_until_handoff_runs_confirmation_when_eligible(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=500, smoke_fit_limit=14)
    _freeze(ledger)
    fold = make_fold()
    positions = split_positions(fold)

    def _pc_pass(**kwargs):
        del kwargs
        return {
            "pc_label": PC_PASS,
            "eligible_for_confirmation": True,
            "reason": None,
        }

    def _confirm_neg(records, *, eligible):
        assert eligible is True
        assert len(records) == 350
        return {
            "confirm_label": CONFIRM_NEGATIVE,
            "ca_tc_successes": 2,
            "all_baseline_successes": 1,
            "reason": "injected negative",
        }

    out = run_until_handoff(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        pairing_fn=_pc_pass,
        confirmation_eval_fn=_confirm_neg,
    )
    assert out["done"] is True
    actions = [s["action"] for s in out["steps"]]
    assert ACTION_RUN_CONFIRMATION in actions
    assert out["state"]["confirm_label"] == CONFIRM_NEGATIVE
    assert out["state"]["confirmation_eligible"] is True
    text = Path(out["state"]["handoff_paths"]["markdown"]).read_text(encoding="utf-8")
    assert "CONTROL_NEGATIVE" in text
    assert ledger.n_completed == 14 + 105 + 350


def test_execute_handoff_after_incomplete_pc(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path / "ledger", max_total_fits=200, smoke_fit_limit=14)
    _freeze(ledger)
    _record_smoke_complete(ledger)
    fold = make_fold()
    positions = split_positions(fold)
    # Screen via stub.
    screen_step = execute_next_stage(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        state=empty_stage_state(),
    )
    assert screen_step["action"] == ACTION_RUN_SCREEN

    def _pc_incomplete(**kwargs):
        del kwargs
        return {
            "pc_label": PC_INCOMPLETE,
            "eligible_for_confirmation": False,
            "reason": "missing checkpoints",
        }

    pc_step = execute_next_stage(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        pairing_fn=_pc_incomplete,
        state=screen_step["state"],
    )
    assert pc_step["action"] == ACTION_RUN_PAIRING_PC
    assert pc_step["state"]["pc_label"] == PC_INCOMPLETE

    handoff = execute_next_stage(
        ledger=ledger,
        folds_by_index={i: fold for i in range(5)},
        positions_by_fold={i: positions for i in range(5)},
        checkpoint_dir=tmp_path / "ckpt",
        output_root=tmp_path / "out",
        result_dir=tmp_path / "docs",
        protocol=_tiny_protocol(),
        check_disk=False,
        fit_fn=_stub_fit,
        state=pc_step["state"],
    )
    assert handoff["action"] == ACTION_WRITE_HANDOFF
    assert handoff["done"] is True
    assert handoff["state"]["confirm_label"] == CONFIRM_SKIPPED
