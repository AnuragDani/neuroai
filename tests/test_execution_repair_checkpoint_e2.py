"""E2 checkpoint persistence: save/reload + interrupted-write recovery (toy only)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from p22.eval.execution_repair_checkpoint import (
    CHECKPOINT_SCHEMA,
    CheckpointPersistenceError,
    atomic_save_checkpoint,
    checkpoint_path_for_fit_id,
    fit_neural_with_checkpoint,
    load_checkpoint,
    recover_interrupted_tmp,
    reload_probabilities_from_checkpoint,
)
from p22.eval.masked_atac_adapter import build_toy_mixed_label_fold
from p22.eval.multiome_protocol import MultiomeProtocol

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "tasks" / "checkpoint_persistence_e2.json"
OUT_MD = ROOT / "tasks" / "CHECKPOINT_PERSISTENCE_E2.md"


def _toy_proto() -> MultiomeProtocol:
    return MultiomeProtocol(
        max_epochs=3,
        patience=2,
        batch_size=4,
        n_repeats=1,
        feature_budget=8,
        model_seed=7,
    )


def test_toy_checkpoint_save_reload_and_overwrite_refusal(tmp_path: Path) -> None:
    toy = build_toy_mixed_label_fold()
    ckpt_dir = tmp_path / "checkpoints"
    fitted = fit_neural_with_checkpoint(
        arm="token_concat",
        views=toy["views"],
        labels=toy["labels"],
        donors=toy["donors"],
        train_idx=toy["train_idx"],
        val_idx=toy["val_idx"],
        test_idx=toy["test_idx"],
        fit_id="toy|token_concat|fold0",
        checkpoint_dir=ckpt_dir,
        protocol=_toy_proto(),
        stage="toy",
        fold=0,
    )
    path = Path(fitted["checkpoint_path"])
    assert path.is_file()
    assert path.stat().st_size > 0
    loaded = load_checkpoint(path)
    assert loaded["schema"] == CHECKPOINT_SCHEMA
    assert loaded["epoch_history"]
    assert loaded["selection_identity"]["checkpoint_sha256"] == fitted["checkpoint_sha256"]
    assert loaded["selection_identity"]["initial_state_sha256"] == fitted[
        "initial_state_sha256"
    ]
    reloaded = reload_probabilities_from_checkpoint(
        loaded, toy["views"], toy["test_idx"]
    )
    assert np.allclose(reloaded, fitted["probabilities"], rtol=0.0, atol=1e-6)
    with pytest.raises(CheckpointPersistenceError, match="refuse overwrite"):
        atomic_save_checkpoint(path, {"schema": CHECKPOINT_SCHEMA})


def test_interrupted_tmp_not_promoted_and_recoverable(tmp_path: Path) -> None:
    dest = checkpoint_path_for_fit_id(tmp_path, "toy|interrupted|fold0")
    tmp = dest.with_name(dest.name + ".tmp")
    torch.save({"incomplete": True}, tmp)
    assert not dest.exists()
    with pytest.raises(CheckpointPersistenceError, match="incomplete interrupted"):
        load_checkpoint(dest)
    recovered = recover_interrupted_tmp(dest)
    assert recovered["status"] == "interrupted_tmp_discarded"
    assert recovered["promoted"] is False
    assert not tmp.exists()
    assert not dest.exists()
    # Direct load of tmp path must refuse.
    torch.save({"incomplete": True}, tmp)
    with pytest.raises(CheckpointPersistenceError, match="incomplete tmp"):
        load_checkpoint(tmp)


def test_empty_checkpoint_refused(tmp_path: Path) -> None:
    dest = tmp_path / "empty.pt"
    dest.write_bytes(b"")
    with pytest.raises(CheckpointPersistenceError, match="empty checkpoint"):
        load_checkpoint(dest)


def test_evidence_report_present() -> None:
    assert OUT_JSON.is_file(), "run scripts/report_execution_repair_checkpoint_e2.py"
    assert OUT_MD.is_file()
    report = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert report["disposition"] == "CHECKPOINT_PERSISTENCE_PASS"
    assert report["scientific_status_unchanged"]["masked_atac_m9"] == "NOT_AUTHORIZED"
    assert report["scientific_status_unchanged"]["primary"] == "B_NULL"
    assert report["research_fits"] == 0
    assert "CHECKPOINT_PERSISTENCE_PASS" in OUT_MD.read_text(encoding="utf-8")
