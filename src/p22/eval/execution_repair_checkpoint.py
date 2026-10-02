"""E2 model-checkpoint persistence helpers for execution repair (2026-10-02).

Kept outside M8 ``REQUIRED_LOCK_KEYS`` so locked adapter/executor modules remain
byte-stable while neural jobs gain durable initial/final state, epoch history,
and selection identity with atomic writes and overwrite refusal.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch

from p22.eval.masked_atac_adapter import (
    ARM_TO_PAIRED_NAME,
    state_dict_sha256,
    train_cell_target_model,
)
from p22.eval.masked_atac_protocol import NEURAL, SELECTION_RULE
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import model_inputs, paired_model
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import predict

CHECKPOINT_SCHEMA = "execution_repair_checkpoint_v1"
TMP_SUFFIX = ".pt.tmp"


class CheckpointPersistenceError(ValueError):
    """Refuse unsafe checkpoint write/reload contracts."""


def checkpoint_path_for_fit_id(checkpoint_dir: Path | str, fit_id: str) -> Path:
    root = Path(checkpoint_dir)
    safe = str(fit_id).replace("|", "__")
    return root / f"{safe}.pt"


def _tmp_path(path: Path) -> Path:
    return path.with_name(path.name + ".tmp")


def clone_state_dict(state: Mapping[str, Any]) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in state.items()}


def build_selection_identity(
    *,
    best_epoch: int,
    best_val_score: float,
    selection_metric: str,
    selection_rule: str,
    checkpoint_sha256: str,
    initial_state_sha256: str,
) -> dict[str, Any]:
    return {
        "best_epoch": int(best_epoch),
        "best_val_score": float(best_val_score),
        "selection_metric": str(selection_metric),
        "selection_rule": str(selection_rule),
        "selection_split": "val",
        "initial_state_sha256": str(initial_state_sha256),
        "checkpoint_sha256": str(checkpoint_sha256),
    }


def atomic_save_checkpoint(
    path: Path | str,
    payload: Mapping[str, Any],
    *,
    allow_overwrite: bool = False,
) -> Path:
    """Write checkpoint via tmp+replace; refuse overwrite unless explicitly allowed."""
    dest = Path(path)
    if dest.exists() and not allow_overwrite:
        raise CheckpointPersistenceError(
            f"checkpoint already exists; refuse overwrite: {dest}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(dest)
    if tmp.exists():
        tmp.unlink()
    blob = dict(payload)
    blob["schema"] = CHECKPOINT_SCHEMA
    torch.save(blob, tmp)
    if not tmp.is_file() or tmp.stat().st_size <= 0:
        raise CheckpointPersistenceError(f"interrupted or empty write: {tmp}")
    if dest.exists() and not allow_overwrite:
        tmp.unlink(missing_ok=True)
        raise CheckpointPersistenceError(
            f"checkpoint appeared during write; refuse overwrite: {dest}"
        )
    tmp.replace(dest)
    return dest


def load_checkpoint(path: Path | str) -> dict[str, Any]:
    """Load a complete checkpoint; refuse tmp/partial artifacts."""
    dest = Path(path)
    if dest.name.endswith(".tmp") or dest.suffixes[-2:] == [".pt", ".tmp"]:
        raise CheckpointPersistenceError(f"refusing incomplete tmp checkpoint: {dest}")
    tmp = _tmp_path(dest)
    if not dest.is_file():
        if tmp.is_file():
            raise CheckpointPersistenceError(
                f"incomplete interrupted write (tmp only): {tmp}"
            )
        raise CheckpointPersistenceError(f"checkpoint missing: {dest}")
    if dest.stat().st_size <= 0:
        raise CheckpointPersistenceError(f"empty checkpoint file: {dest}")
    blob = torch.load(dest, map_location="cpu", weights_only=False)
    if not isinstance(blob, dict):
        raise CheckpointPersistenceError("checkpoint payload must be a mapping")
    if blob.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointPersistenceError(
            f"unexpected checkpoint schema {blob.get('schema')!r}"
        )
    for key in (
        "fit_id",
        "arm",
        "paired_name",
        "widths",
        "initial_state",
        "final_state",
        "epoch_history",
        "selection_identity",
        "protocol",
    ):
        if key not in blob:
            raise CheckpointPersistenceError(f"checkpoint missing required key {key!r}")
    return blob


def recover_interrupted_tmp(path: Path | str) -> dict[str, Any]:
    """Detect and clear orphaned ``.pt.tmp`` without promoting it to complete."""
    dest = Path(path)
    tmp = _tmp_path(dest)
    if dest.is_file() and dest.stat().st_size > 0:
        if tmp.is_file():
            tmp.unlink()
            return {
                "status": "complete_present_tmp_removed",
                "path": str(dest),
                "tmp_removed": True,
            }
        return {"status": "complete", "path": str(dest), "tmp_removed": False}
    if tmp.is_file():
        size = int(tmp.stat().st_size)
        tmp.unlink()
        return {
            "status": "interrupted_tmp_discarded",
            "path": str(dest),
            "tmp_bytes": size,
            "tmp_removed": True,
            "promoted": False,
        }
    return {"status": "absent", "path": str(dest), "tmp_removed": False}


def reload_probabilities_from_checkpoint(
    checkpoint: Mapping[str, Any],
    views: Mapping[str, np.ndarray],
    row_indices: Sequence[int] | np.ndarray,
) -> np.ndarray:
    """Rebuild model from final_state and score class-1 probabilities."""
    paired_name = str(checkpoint["paired_name"])
    widths = [int(w) for w in checkpoint["widths"]]
    proto_fields = dict(checkpoint["protocol"])
    protocol = MultiomeProtocol(
        n_tokens=int(proto_fields.get("n_tokens", NEURAL.n_tokens)),
        embed_dim=int(proto_fields.get("embed_dim", NEURAL.embed_dim)),
        hidden_dim=int(proto_fields.get("hidden_dim", NEURAL.hidden_dim)),
        n_heads=int(proto_fields.get("n_heads", NEURAL.n_heads)),
        dropout=float(proto_fields.get("dropout", NEURAL.dropout)),
        feature_budget=int(proto_fields.get("feature_budget", NEURAL.feature_budget)),
        cell_cap=int(proto_fields.get("cell_cap", NEURAL.cell_cap)),
        max_epochs=int(proto_fields.get("max_epochs", NEURAL.max_epochs)),
        patience=int(proto_fields.get("patience", NEURAL.patience)),
        learning_rate=float(proto_fields.get("learning_rate", NEURAL.learning_rate)),
        batch_size=int(proto_fields.get("batch_size", NEURAL.batch_size)),
        n_repeats=int(proto_fields.get("n_repeats", NEURAL.n_repeats)),
        n_folds=int(proto_fields.get("n_folds", NEURAL.n_folds)),
        split_seed=int(proto_fields.get("split_seed", NEURAL.split_seed)),
        model_seed=int(proto_fields.get("model_seed", NEURAL.model_seed)),
        sampling_seed=int(proto_fields.get("sampling_seed", NEURAL.sampling_seed)),
    )
    model = paired_model(paired_name, widths, protocol)
    model.load_state_dict(checkpoint["final_state"])
    model.eval()
    selected = model_inputs(paired_name, dict(views))
    rows = np.asarray(row_indices, dtype=np.int64)
    _, probs = predict(
        model, {key: value[rows] for key, value in selected.items()}
    )
    return np.asarray(probs[:, 1], dtype=np.float64)


def fit_neural_with_checkpoint(
    *,
    arm: str,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    donors: Sequence[str],
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    fit_id: str,
    checkpoint_dir: Path | str,
    protocol: MultiomeProtocol | None = None,
    stage: str | None = None,
    fold: int | None = None,
) -> dict[str, Any]:
    """Train one neural arm and persist initial/final/history before return."""
    if arm not in ARM_TO_PAIRED_NAME:
        raise CheckpointPersistenceError(f"unknown neural arm {arm!r}")
    proto = protocol or NEURAL
    paired_name = ARM_TO_PAIRED_NAME[arm]
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(paired_name, widths, proto)
    initial_state = clone_state_dict(model.state_dict())
    selected = model_inputs(paired_name, dict(views))
    train = np.asarray(train_idx, dtype=np.int64)
    val = np.asarray(val_idx, dtype=np.int64)
    test = np.asarray(test_idx, dtype=np.int64)
    donor_arr = np.asarray(donors).astype(str)
    result = train_cell_target_model(
        model,
        {key: value[train] for key, value in selected.items()},
        labels[train],
        donor_arr[train],
        {key: value[val] for key, value in selected.items()},
        labels[val],
        donor_arr[val],
        max_epochs=proto.max_epochs,
        batch_size=proto.batch_size,
        learning_rate=proto.learning_rate,
        patience=proto.patience,
        seed=proto.model_seed,
    )
    initial_sha = state_dict_sha256(initial_state)
    if initial_sha != result.initial_state_sha256:
        raise CheckpointPersistenceError(
            "captured initial_state SHA does not match trainer hash"
        )
    final_state = clone_state_dict(result.trained.model.state_dict())
    final_sha = state_dict_sha256(final_state)
    if final_sha != result.checkpoint_sha256:
        raise CheckpointPersistenceError(
            "captured final_state SHA does not match trainer hash"
        )
    history = [record.to_dict() for record in result.trained.history]
    if not history:
        raise CheckpointPersistenceError("epoch history empty; refuse completion")
    selection = build_selection_identity(
        best_epoch=result.trained.best_epoch,
        best_val_score=result.trained.best_val_score,
        selection_metric=result.trained.selection_metric,
        selection_rule=SELECTION_RULE,
        checkpoint_sha256=final_sha,
        initial_state_sha256=initial_sha,
    )
    _, probs = predict(
        result.trained.model,
        {key: value[test] for key, value in selected.items()},
    )
    test_probs = np.asarray(probs[:, 1], dtype=np.float64)
    ckpt_path = checkpoint_path_for_fit_id(checkpoint_dir, fit_id)
    payload = {
        "fit_id": str(fit_id),
        "stage": stage,
        "arm": arm,
        "fold": fold,
        "paired_name": paired_name,
        "widths": widths,
        "initial_state": initial_state,
        "final_state": final_state,
        "epoch_history": history,
        "selection_identity": selection,
        "protocol": {
            "n_tokens": proto.n_tokens,
            "embed_dim": proto.embed_dim,
            "hidden_dim": proto.hidden_dim,
            "n_heads": proto.n_heads,
            "dropout": proto.dropout,
            "feature_budget": proto.feature_budget,
            "cell_cap": proto.cell_cap,
            "n_repeats": proto.n_repeats,
            "n_folds": proto.n_folds,
            "split_seed": proto.split_seed,
            "model_seed": proto.model_seed,
            "sampling_seed": proto.sampling_seed,
            "max_epochs": proto.max_epochs,
            "patience": proto.patience,
            "learning_rate": proto.learning_rate,
            "batch_size": proto.batch_size,
        },
        "test_probabilities": [float(x) for x in test_probs.tolist()],
        "result": result.to_dict(),
    }
    saved = atomic_save_checkpoint(ckpt_path, payload)
    # Reload identity before returning (bounded verification, not a research fit).
    loaded = load_checkpoint(saved)
    reloaded = reload_probabilities_from_checkpoint(loaded, views, test)
    if not np.allclose(reloaded, test_probs, rtol=0.0, atol=1e-6):
        raise CheckpointPersistenceError("reload probabilities diverge from saved")
    return {
        "arm": arm,
        "paired_name": paired_name,
        "widths": widths,
        "probabilities": test_probs,
        "result": result.to_dict(),
        "model": result.trained.model,
        "checkpoint_path": str(saved),
        "checkpoint_sha256": final_sha,
        "initial_state_sha256": initial_sha,
        "epoch_history": history,
        "selection_identity": selection,
        "reload_identity_ok": True,
    }
