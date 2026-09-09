"""Bounded paired-array model adapter. No downloads or real-data approval bypass.

The command-line entry point generates synthetic data itself. Array-level helpers
are reusable, but do not establish provenance, approved use, or ATAC compatibility.
Real-data orchestration must enforce those gates before calling this module.
Inputs must already have matched cells/features and an accepted normalization.
"""

import hashlib

import numpy as np
import pandas as pd
from scipy import sparse

from p22.data.group_splits import aggregate_donor_probabilities
from p22.data.resources import measure_stage
from p22.data.splits import _as_donor_array
from p22.data.transforms import fit_train_only
from p22.eval.metrics import balanced_accuracy
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.models.baselines import BaselineMLP
from p22.models.cross_attention import CrossAttentionModel, TokenConcatFusionModel
from p22.models.fusion import VIEW_A, VIEW_B, ConcatFusionModel, GatedFusionModel
from p22.training.loop import _binary_donors, predict, set_all_seeds, train_model


def prepare_paired_fold(
    views: dict,
    metadata: pd.DataFrame,
    indices: dict,
    protocol: MultiomeProtocol,
    max_dense_elements: int = 2_000_000,
) -> tuple[dict, dict]:
    """Training-only variance selection and scaling after bounded sparse input.

    Dense budget is the total selected elements across views, not a RAM promise.
    Metadata order must equal matrix row order; all three splits partition rows.
    """
    if set(views) != {VIEW_A, VIEW_B} or set(indices) != {"train", "val", "test"}:
        raise ValueError("need both paired views and train/val/test partitions")
    if not {"cell_id", "donor_id", "label"}.issubset(metadata.columns):
        raise ValueError("metadata requires cell_id, donor_id, label")
    ids = _as_donor_array(metadata.cell_id).astype(str)
    donors, _ = _binary_donors(metadata.donor_id, metadata.label)
    if pd.Series(donors).value_counts().max() > protocol.cell_cap:
        raise ValueError("input exceeds frozen cell_cap; apply paired donor sampling first")
    if len(set(ids)) != len(ids):
        raise ValueError("cell IDs must be unique")
    if type(max_dense_elements) is not int or max_dense_elements < 1:
        raise ValueError("max_dense_elements must be a positive integer")
    donor_sets, all_rows = [], []
    for name in ("train", "val", "test"):
        rows = np.asarray(indices[name])
        if (
            rows.ndim != 1
            or rows.dtype.kind not in "iu"
            or len(rows) == 0
            or (rows < 0).any()
            or (rows >= len(ids)).any()
        ):
            raise ValueError(f"invalid {name} row indices")
        _binary_donors(donors[rows], metadata.label.to_numpy()[rows])
        donor_sets.append(set(donors[rows]))
        all_rows.extend(rows.tolist())
    if len(all_rows) != len(ids) or len(set(all_rows)) != len(ids):
        raise ValueError("splits must partition all rows exactly once")
    if any(donor_sets[i] & donor_sets[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("train/val/test donors overlap")

    transformed, evidence, _ = fit_paired_preprocessing(
        views,
        ids,
        indices["train"],
        np.concatenate((indices["val"], indices["test"])),
        protocol,
        max_dense_elements,
    )
    return transformed, evidence


def fit_paired_preprocessing(views, ids, train, holdout, protocol, max_dense_elements=2_000_000):
    """Shared training-only feature/scaler fit for folds and all-development refits."""
    for name, matrix in views.items():
        if matrix.ndim != 2 or matrix.shape[0] != len(ids) or matrix.shape[1] < 1:
            raise ValueError(f"{name} dimensions do not match metadata")
        if not np.isfinite(matrix.data if sparse.issparse(matrix) else matrix).all():
            raise ValueError(f"{name} contains non-finite values")
    selected_size = sum(
        len(ids) * min(matrix.shape[1], protocol.feature_budget) for matrix in views.values()
    )
    if selected_size > max_dense_elements:
        raise ValueError("selected arrays exceed max_dense_elements; lower cap/feature budget")
    transformed, evidence, fitted_views = {}, {}, {}
    for name, matrix in views.items():
        training = matrix[train].astype(np.float64)
        if sparse.issparse(training):
            variance = np.asarray(training.power(2).mean(axis=0)).ravel() - np.square(
                np.asarray(training.mean(axis=0)).ravel()
            )
        else:
            variance = training.var(axis=0)
        selected = np.sort(np.argsort(-variance, kind="stable")[: protocol.feature_budget])
        chosen = matrix[:, selected]
        bounded = chosen.toarray() if sparse.issparse(chosen) else np.asarray(chosen)
        fitted = fit_train_only(bounded, ids, ids[train], ids[holdout])
        transformed[name] = fitted.transform(bounded)
        evidence[name] = {"selected_features": selected.tolist(), "transform": fitted.metadata}
        fitted_views[name] = fitted
    return transformed, evidence, fitted_views


NEURAL_FAMILIES = (
    "rna_only",
    "atac_only",
    "rna_atac_concat",
    "gated_fusion",
    "token_concat",
    "cross_attention",
)


def paired_model(name, widths, protocol):
    """Same initialized architecture for internal folds, final refit, and reload."""
    set_all_seeds(protocol.model_seed)
    common = dict(
        n_classes=2,
        embed_dim=protocol.embed_dim,
        hidden_dim=protocol.hidden_dim,
        dropout=protocol.dropout,
    )
    if name in {"rna_only", "atac_only"}:
        return BaselineMLP(widths[0 if name == "rna_only" else 1], **common)
    families = {
        "rna_atac_concat": ConcatFusionModel,
        "gated_fusion": GatedFusionModel,
        "token_concat": TokenConcatFusionModel,
        "cross_attention": CrossAttentionModel,
    }
    extras = {"n_tokens": protocol.n_tokens} if name in {"token_concat", "cross_attention"} else {}
    if name == "cross_attention":
        extras["n_heads"] = protocol.n_heads
    return families[name](*widths, **common, **extras)


def model_inputs(name, views):
    if name in {"rna_only", "atac_only"}:
        view = VIEW_A if name == "rna_only" else VIEW_B
        return {view: views[view]}
    return views


def run_paired_fold(
    views: dict,
    metadata: pd.DataFrame,
    indices: dict,
    protocol: MultiomeProtocol,
) -> dict:
    """Train six neural families on one predeclared donor-isolated fold.

    Only the validation donors choose epochs. Test scores are reporting-only.
    No input file reading or final external scoring occurs here.
    """
    transformed, evidence = prepare_paired_fold(views, metadata, indices, protocol)
    train, val, test = (indices[name] for name in ("train", "val", "test"))
    labels, donors = metadata.label.to_numpy(), metadata.donor_id.astype(str).to_numpy()
    widths = [transformed[name].shape[1] for name in (VIEW_A, VIEW_B)]
    records = {}
    for name in NEURAL_FAMILIES:
        inputs = model_inputs(name, transformed)
        model = paired_model(name, widths, protocol)
        trained, resource = measure_stage(
            name,
            lambda model=model, inputs=inputs: train_model(
                model,
                {key: value[train] for key, value in inputs.items()},
                labels[train],
                {key: value[val] for key, value in inputs.items()},
                labels[val],
                max_epochs=protocol.max_epochs,
                patience=protocol.patience,
                batch_size=protocol.batch_size,
                learning_rate=protocol.learning_rate,
                seed=protocol.model_seed,
                train_donor_ids=donors[train],
                val_donor_ids=donors[val],
            ),
            cells_per_donor_cap=protocol.cell_cap,
            notes="CPU; process high-water RSS, not incremental model memory",
        )
        _, probabilities = predict(
            trained.model, {key: value[test] for key, value in inputs.items()}
        )
        predictions = aggregate_donor_probabilities(probabilities[:, 1], donors[test])
        truth = pd.Series(labels[test], index=donors[test]).groupby(level=0).first()
        predictions["label"] = predictions.donor_id.map(truth).astype(int)
        digest = hashlib.sha256()
        for key, value in sorted(trained.model.state_dict().items()):
            digest.update(key.encode())
            digest.update(str(tuple(value.shape)).encode())
            digest.update(value.detach().cpu().numpy().tobytes())
        records[name] = {
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "training": trained.to_dict(),
            "resources": resource.to_dict(),
            "checkpoint_sha256": digest.hexdigest(),
            "predictions": predictions.to_dict(orient="records"),
            "donor_balanced_accuracy": balanced_accuracy(
                predictions.label, predictions.prediction
            ).to_dict(),
        }
    training_truth = pd.Series(labels[train], index=donors[train]).groupby(level=0).first()
    majority = int(np.bincount(training_truth.to_numpy(dtype=int), minlength=2).argmax())
    majority_predictions = pd.DataFrame({"donor_id": sorted(set(donors[test]))})
    majority_predictions["label"] = majority_predictions.donor_id.map(truth).astype(int)
    majority_predictions["probability"] = float(majority)
    majority_predictions["prediction"] = majority
    return {
        "protocol_sha256": protocol.fingerprint,
        "preprocessing": evidence,
        "splits": {name: sorted(set(donors[rows])) for name, rows in indices.items()},
        "models": records,
        "majority_control": {
            "tie_rule": "class_0",
            "fit_scope": "training donors only",
            "predictions": majority_predictions.to_dict(orient="records"),
            "donor_balanced_accuracy": balanced_accuracy(
                majority_predictions.label, majority_predictions.prediction
            ).to_dict(),
        },
    }
