"""Minimum S7 single-fit runner: plant, train, score, ledger, resource gates.

Orchestrates one predeclared fit at a time under the immutable ledger. Does not
search scenarios, seeds or hyperparameters. Retains CA/TC checkpoints for the
pairing-PC stage. No real-disease-label fits.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

from p22.data.group_splits import aggregate_donor_probabilities
from p22.data.nn_inputs import FoldArrays
from p22.eval.metrics import balanced_accuracy
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import model_inputs, paired_model
from p22.eval.planted_signal import plant_covariance
from p22.eval.s7_ledger import (
    S7_MAX_TOTAL_FITS,
    S7_MODELS,
    S7_N_FOLDS,
    S7_SCREEN_SEED,
    S7_SMOKE_FIT_LIMIT,
    S7FitLedger,
    make_fit_id,
)
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import predict, train_model

# Frozen N4 widths from BENCHMARK_SPEC.json training block.
S7_PROTOCOL = MultiomeProtocol(
    n_tokens=8,
    embed_dim=32,
    hidden_dim=128,
    n_heads=4,
    dropout=0.2,
    n_repeats=1,
    n_folds=5,
    split_seed=0,
    model_seed=0,
    sampling_seed=22,
    max_epochs=20,
    patience=5,
    learning_rate=0.001,
    batch_size=64,
)

S7_LOGREG_MODELS: tuple[str, ...] = ("logreg_concat", "logreg_rna", "logreg_atac")
S7_NEURAL_MODELS: tuple[str, ...] = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
)
S7_CHECKPOINT_MODELS: frozenset[str] = frozenset({"cross_attention", "token_concat"})
S7_SMOKE_RHOS: tuple[float, ...] = (0.0, 1.0)
S7_SMOKE_FOLD = 0
S7_MIN_FREE_DISK_GIB = 11.0
S7_MAX_NEW_ARTIFACTS_GIB = 2.0
S7_LOGREG_FROZEN = {
    "C": 1.0,
    "solver": "lbfgs",
    "max_iter": 1000,
    "tol": 1e-4,
    "random_state": 0,
}

assert set(S7_LOGREG_MODELS) | set(S7_NEURAL_MODELS) == set(S7_MODELS)
assert len(S7_SMOKE_RHOS) * 1 * len(S7_MODELS) <= S7_SMOKE_FIT_LIMIT


def enumerate_smoke_jobs(
    *,
    rhos: tuple[float, ...] = S7_SMOKE_RHOS,
    generator_seed: int = S7_SCREEN_SEED,
    fold: int = S7_SMOKE_FOLD,
    models: tuple[str, ...] = S7_MODELS,
) -> list[dict[str, Any]]:
    """Predeclared smoke jobs: |rho| × one fold × models (14 under frozen spec)."""
    jobs: list[dict[str, Any]] = []
    for rho in rhos:
        for model in models:
            fit_id = make_fit_id("smoke", rho, generator_seed, fold, model)
            jobs.append(
                {
                    "fit_id": fit_id,
                    "stage": "smoke",
                    "rho": float(rho),
                    "generator_seed": int(generator_seed),
                    "fold": int(fold),
                    "model": model,
                }
            )
    if len(jobs) > S7_SMOKE_FIT_LIMIT:
        raise ValueError(
            f"smoke enumeration {len(jobs)} exceeds smoke_fit_limit {S7_SMOKE_FIT_LIMIT}"
        )
    return jobs


def check_disk_resources(
    *,
    output_root: Path | str | None = None,
    min_free_gib: float = S7_MIN_FREE_DISK_GIB,
    max_artifacts_gib: float = S7_MAX_NEW_ARTIFACTS_GIB,
) -> dict[str, Any]:
    """Refuse stage start when free disk or artifact budget is exceeded."""
    path = Path(output_root) if output_root is not None else Path.cwd()
    path = path if path.exists() else path.parent
    usage = shutil.disk_usage(path)
    free_gib = usage.free / (1024**3)
    artifacts_gib = 0.0
    if output_root is not None and Path(output_root).exists():
        artifacts_gib = _dir_size_bytes(Path(output_root)) / (1024**3)
    record = {
        "free_gib": round(free_gib, 3),
        "artifacts_gib": round(artifacts_gib, 3),
        "min_free_gib": float(min_free_gib),
        "max_artifacts_gib": float(max_artifacts_gib),
        "ok": free_gib >= float(min_free_gib) and artifacts_gib <= float(max_artifacts_gib),
    }
    if free_gib < float(min_free_gib):
        raise RuntimeError(
            f"disk free {free_gib:.2f} GiB < min_free_disk_gib {min_free_gib}"
        )
    if artifacts_gib > float(max_artifacts_gib):
        raise RuntimeError(
            f"artifacts {artifacts_gib:.2f} GiB > max_new_artifacts_gib {max_artifacts_gib}"
        )
    return record


def _dir_size_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def donor_cell_weights(donor_ids: Sequence[Any]) -> np.ndarray:
    """Inverse-donor-cell-count weights normalised so their mean is one."""
    donors = np.asarray([str(value) for value in donor_ids], dtype=object)
    _, inverse, counts = np.unique(donors, return_inverse=True, return_counts=True)
    return len(donors) / (len(counts) * counts[inverse])


def donor_scores(
    labels: np.ndarray, probabilities: np.ndarray, donors: np.ndarray
) -> dict[str, Any]:
    """Aggregate cell probabilities per donor and score donor-level metrics."""
    frame = aggregate_donor_probabilities(probabilities, donors)
    truth = pd.Series(labels, index=donors).groupby(level=0).first()
    frame["label"] = frame.donor_id.map(truth).astype(int)
    y = frame["label"].to_numpy(dtype=int)
    p = frame["probability"].to_numpy(dtype=float)
    if set(np.unique(y)) != {0, 1}:
        return {
            "donor_balanced_accuracy": None,
            "donor_auroc": None,
            "donor_log_loss": None,
            "n_test_donors": int(len(y)),
            "status": "single_class",
            "donor_probabilities": frame.to_dict(orient="list"),
        }
    return {
        "donor_balanced_accuracy": balanced_accuracy(frame.label, frame.prediction).value,
        "donor_auroc": float(roc_auc_score(y, p)),
        "donor_log_loss": float(log_loss(y, p, labels=[0, 1])),
        "n_test_donors": int(len(y)),
        "status": "ok",
        "donor_probabilities": frame.to_dict(orient="list"),
        "test_cell_probabilities": np.asarray(probabilities, dtype=np.float64).tolist(),
    }


def _matrix_for_logreg(name: str, views: Mapping[str, np.ndarray]) -> np.ndarray:
    if name == "logreg_rna":
        return np.asarray(views[VIEW_A], dtype=np.float64)
    if name == "logreg_atac":
        return np.asarray(views[VIEW_B], dtype=np.float64)
    if name == "logreg_concat":
        return np.hstack([views[VIEW_A], views[VIEW_B]])
    raise ValueError(f"not a logreg model: {name!r}")


def fit_s7_arm(
    name: str,
    views: Mapping[str, np.ndarray],
    labels_all: np.ndarray,
    donors: np.ndarray,
    positions: Mapping[str, np.ndarray],
    protocol: MultiomeProtocol,
    *,
    model_seed: int | None = None,
) -> dict[str, Any]:
    """Fit one S7 arm on already-planted views; return donor scores + optional state."""
    if name not in S7_MODELS:
        raise ValueError(f"unknown S7 model {name!r}; expected {S7_MODELS}")
    seed = protocol.model_seed if model_seed is None else int(model_seed)
    train = np.asarray(positions["train"], dtype=np.int64)
    val = np.asarray(positions["val"], dtype=np.int64)
    test = np.asarray(positions["test"], dtype=np.int64)
    if seed == protocol.model_seed:
        proto = protocol
    else:
        fields = {
            key: getattr(protocol, key)
            for key in (
                "n_tokens",
                "embed_dim",
                "hidden_dim",
                "n_heads",
                "dropout",
                "feature_budget",
                "cell_cap",
                "max_epochs",
                "patience",
                "batch_size",
                "learning_rate",
                "n_repeats",
                "n_folds",
                "split_seed",
                "sampling_seed",
            )
        }
        proto = MultiomeProtocol(**fields, model_seed=seed)

    checkpoint: dict[str, Any] | None = None
    if name in S7_LOGREG_MODELS:
        matrix = _matrix_for_logreg(name, views)
        weights = donor_cell_weights(donors[train])
        estimator = LogisticRegression(**S7_LOGREG_FROZEN)
        estimator.fit(matrix[train], labels_all[train], sample_weight=weights)
        probability = estimator.predict_proba(matrix[test])[:, 1]
        checkpoint = {
            "kind": "logreg",
            "model": name,
            "coef": estimator.coef_.tolist(),
            "intercept": estimator.intercept_.tolist(),
            "classes": estimator.classes_.tolist(),
        }
    else:
        widths = [views[VIEW_A].shape[1], views[VIEW_B].shape[1]]
        model = paired_model(name, widths, proto)
        selected = model_inputs(name, dict(views))
        trained = train_model(
            model,
            {key: value[train] for key, value in selected.items()},
            labels_all[train],
            {key: value[val] for key, value in selected.items()},
            labels_all[val],
            max_epochs=proto.max_epochs,
            patience=proto.patience,
            batch_size=proto.batch_size,
            learning_rate=proto.learning_rate,
            seed=proto.model_seed,
            train_donor_ids=donors[train],
            val_donor_ids=donors[val],
        )
        _, probability = predict(
            trained.model,
            {key: value[test] for key, value in selected.items()},
        )
        probability = probability[:, 1]
        checkpoint = {
            "kind": "neural",
            "model": name,
            "widths": widths,
            "state_dict": {k: v.detach().cpu() for k, v in trained.model.state_dict().items()},
            "protocol": {
                "n_tokens": proto.n_tokens,
                "embed_dim": proto.embed_dim,
                "hidden_dim": proto.hidden_dim,
                "n_heads": proto.n_heads,
                "dropout": proto.dropout,
                "model_seed": proto.model_seed,
            },
        }

    scores = donor_scores(labels_all[test], probability, donors[test])
    scores["checkpoint"] = checkpoint
    scores["model_seed"] = int(proto.model_seed)
    return scores


def plant_and_fit_job(
    fold: FoldArrays,
    job: Mapping[str, Any],
    positions: Mapping[str, np.ndarray],
    *,
    cell_ids: np.ndarray | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    feature_seed: int | None = None,
) -> dict[str, Any]:
    """Plant S7 covariance then fit one job; return ledger-ready record."""
    rho = float(job["rho"])
    generator_seed = int(job["generator_seed"])
    model = str(job["model"])
    stage = str(job.get("stage", "screen"))
    fold_idx = int(job["fold"])
    planted, fake = plant_covariance(
        fold,
        rho=rho,
        generator_seed=generator_seed,
        cell_ids=cell_ids,
        feature_seed=feature_seed,
    )
    views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
    try:
        scores = fit_s7_arm(
            model,
            views,
            fake,
            planted.donor,
            positions,
            protocol,
            model_seed=generator_seed,
        )
    except Exception as error:  # noqa: BLE001 - record and continue via caller
        return {
            "fit_id": str(job.get("fit_id") or make_fit_id(stage, rho, generator_seed, fold_idx, model)),
            "stage": stage,
            "rho": rho,
            "generator_seed": generator_seed,
            "fold": fold_idx,
            "model": model,
            "status": f"error: {type(error).__name__}: {error}",
        }
    fit_id = str(job.get("fit_id") or make_fit_id(stage, rho, generator_seed, fold_idx, model))
    record = {
        "fit_id": fit_id,
        "stage": stage,
        "rho": rho,
        "generator_seed": generator_seed,
        "fold": fold_idx,
        "model": model,
        "status": scores["status"],
        "donor_balanced_accuracy": scores.get("donor_balanced_accuracy"),
        "donor_auroc": scores.get("donor_auroc"),
        "donor_log_loss": scores.get("donor_log_loss"),
        "n_test_donors": scores.get("n_test_donors"),
        "model_seed": scores.get("model_seed"),
        "checkpoint": scores.get("checkpoint"),
        "test_cell_probabilities": scores.get("test_cell_probabilities"),
        "donor_probabilities": scores.get("donor_probabilities"),
    }
    return record


def should_retain_checkpoint(job: Mapping[str, Any]) -> bool:
    """Retain CA/TC weights for rho=1 screen/confirm (and smoke) diagnostics."""
    model = str(job["model"])
    rho = float(job["rho"])
    stage = str(job.get("stage", ""))
    return (
        model in S7_CHECKPOINT_MODELS
        and abs(rho - 1.0) < 1e-12
        and stage in {"screen", "confirm", "smoke"}
    )


def save_checkpoint(
    record: Mapping[str, Any],
    checkpoint_dir: Path | str,
) -> Path | None:
    """Persist CA/TC checkpoint payload when retention is required."""
    if not should_retain_checkpoint(record):
        return None
    payload = record.get("checkpoint")
    if payload is None:
        raise ValueError("missing checkpoint payload for retainable fit")
    root = Path(checkpoint_dir)
    root.mkdir(parents=True, exist_ok=True)
    fit_id = str(record["fit_id"]).replace("|", "__")
    path = root / f"{fit_id}.pt"
    # Strip large probability lists from sidecar; keep metrics in ledger.
    torch.save(
        {
            "fit_id": record["fit_id"],
            "stage": record["stage"],
            "rho": record["rho"],
            "generator_seed": record["generator_seed"],
            "fold": record["fold"],
            "model": record["model"],
            "model_seed": record.get("model_seed"),
            "checkpoint": payload,
        },
        path,
    )
    return path


def reload_checkpoint_predictions(
    checkpoint_path: Path | str,
    views: Mapping[str, np.ndarray],
    test_rows: np.ndarray,
    protocol: MultiomeProtocol = S7_PROTOCOL,
) -> np.ndarray:
    """Reload a saved neural checkpoint and score test-cell probabilities."""
    blob = torch.load(Path(checkpoint_path), map_location="cpu", weights_only=False)
    ckpt = blob["checkpoint"]
    if ckpt["kind"] != "neural":
        raise ValueError("reload_checkpoint_predictions supports neural checkpoints only")
    name = str(blob["model"])
    widths = [int(w) for w in ckpt["widths"]]
    proto_fields = dict(ckpt["protocol"])
    proto = MultiomeProtocol(
        n_tokens=int(proto_fields["n_tokens"]),
        embed_dim=int(proto_fields["embed_dim"]),
        hidden_dim=int(proto_fields["hidden_dim"]),
        n_heads=int(proto_fields["n_heads"]),
        dropout=float(proto_fields["dropout"]),
        n_repeats=protocol.n_repeats,
        n_folds=protocol.n_folds,
        split_seed=protocol.split_seed,
        model_seed=int(proto_fields["model_seed"]),
        sampling_seed=protocol.sampling_seed,
        max_epochs=protocol.max_epochs,
        patience=protocol.patience,
        learning_rate=protocol.learning_rate,
        batch_size=protocol.batch_size,
    )
    model = paired_model(name, widths, proto)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    selected = model_inputs(name, dict(views))
    test = np.asarray(test_rows, dtype=np.int64)
    _, probability = predict(
        model, {key: value[test] for key, value in selected.items()}
    )
    return np.asarray(probability[:, 1], dtype=np.float64)


def ledger_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Strip non-JSON / bulky fields before appending to the fit ledger."""
    skip = {"checkpoint", "test_cell_probabilities", "donor_probabilities"}
    return {k: v for k, v in record.items() if k not in skip}


def record_completed_fit(
    ledger: S7FitLedger,
    record: Mapping[str, Any],
    *,
    checkpoint_dir: Path | str | None = None,
    prediction_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Append fit to ledger; optionally save checkpoint and donor predictions."""
    # Local import avoids a cycle: confirm_exec imports confirmation gates only.
    from p22.eval.s7_confirm_exec import save_donor_predictions

    ckpt_path = None
    if checkpoint_dir is not None:
        ckpt_path = save_checkpoint(record, checkpoint_dir)
    pred_root = prediction_dir
    if pred_root is None and checkpoint_dir is not None:
        pred_root = Path(checkpoint_dir).parent / "donor_predictions"
    pred_path = None
    if pred_root is not None:
        pred_path = save_donor_predictions(record, pred_root)
    payload = ledger_payload(record)
    if ckpt_path is not None:
        payload["checkpoint_path"] = str(ckpt_path)
    if pred_path is not None:
        payload["donor_predictions_path"] = str(pred_path)
    return ledger.record_fit(str(record["fit_id"]), payload)


def remaining_fit_budget(ledger: S7FitLedger) -> dict[str, int]:
    return {
        "completed": ledger.n_completed,
        "remaining_total": ledger.remaining_budget(),
        "smoke_remaining": ledger.smoke_remaining(),
        "max_total_fits": S7_MAX_TOTAL_FITS,
        "smoke_fit_limit": S7_SMOKE_FIT_LIMIT,
        "n_folds": S7_N_FOLDS,
    }


def write_resource_snapshot(path: Path | str, snapshot: Mapping[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(snapshot), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
