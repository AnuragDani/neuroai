"""Frozen final models and one-shot donor scoring; array contracts are caller-audited.

Synthetic execution proves software only. Real input orchestration is deliberately
refused until release, specimen, normalization and measurement contracts are accepted.
"""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy import sparse
from sklearn.preprocessing import StandardScaler

from p22.data.census import sha256_file
from p22.data.group_splits import aggregate_donor_probabilities
from p22.data.splits import _as_donor_array
from p22.data.transforms import FittedTransform
from p22.eval.metrics import balanced_accuracy
from p22.eval.multiome_protocol import MultiomeProtocol, paired_comparison
from p22.eval.multiome_runner import (
    NEURAL_FAMILIES,
    fit_paired_preprocessing,
    model_inputs,
    paired_model,
)
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import _binary_donors, predict, refit_model


def _synthetic_only(mode):
    if mode != "synthetic":
        raise PermissionError(
            "real orchestration needs accepted release/QC, specimen independence, "
            "common ATAC counts, normalization/protocol, and Professor approval"
        )


def _validate(views, metadata, feature_ids, protocol):
    if set(views) != {VIEW_A, VIEW_B} or set(feature_ids) != set(views):
        raise ValueError("need paired views and ordered feature IDs")
    ids = _as_donor_array(metadata.cell_id).astype(str)
    donors, truth = _binary_donors(metadata.donor_id, metadata.label)
    if len(set(ids)) != len(ids):
        raise ValueError("cell IDs must be unique")
    if metadata.groupby("donor_id").size().max() > protocol.cell_cap:
        raise ValueError("input exceeds frozen cell cap")
    for name, matrix in views.items():
        features = _as_donor_array(feature_ids[name]).astype(str)
        if (
            matrix.ndim != 2
            or matrix.shape != (len(ids), len(features))
            or len(set(features)) != len(features)
            or len(features) == 0
        ):
            raise ValueError("invalid matrix dimensions or duplicate/empty feature IDs")
        if not np.isfinite(matrix.data if sparse.issparse(matrix) else matrix).all():
            raise ValueError("non-finite input")
    return ids, donors, truth


def freeze_final(views, metadata, feature_ids, protocol, *, epochs, output_dir, mode):
    """Save one final artifact per neural family, fitted on all development donors.

    Epoch counts must be fixed from internal validation beforehand. No held-out
    arrays or outcomes are accepted here. State dictionaries and scaler numbers
    only, never executable model/scaler pickle objects.
    """
    _synthetic_only(mode)
    ids, donors, truth = _validate(views, metadata, feature_ids, protocol)
    if set(epochs) != set(NEURAL_FAMILIES) or any(
        type(value) is not int or not 1 <= value <= protocol.max_epochs for value in epochs.values()
    ):
        raise ValueError("need frozen positive epoch counts within protocol for every family")
    transformed, evidence, fitted = fit_paired_preprocessing(
        views, ids, np.arange(len(ids)), np.array([], dtype=int), protocol
    )
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=False)
    contract = {
        "mode": mode,
        "protocol": asdict(protocol),
        "protocol_sha256": protocol.fingerprint,
        "epoch_counts": epochs,
        "epoch_rule": "ceil(median(internal best epochs))",
        "feature_ids": {key: list(map(str, value)) for key, value in feature_ids.items()},
        "development_donors": sorted(set(donors)),
        "development_cell_ids": ids.tolist(),
        "preprocessing": evidence,
        "majority_class": int(np.bincount(truth.astype(int), minlength=2).argmax()),
    }
    # Write the contract before the first final model sees any training values.
    (folder / "refit_contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    states, training, scales = {}, {}, {}
    widths = [transformed[name].shape[1] for name in (VIEW_A, VIEW_B)]
    for name in NEURAL_FAMILIES:
        model = paired_model(name, widths, protocol)
        training[name] = refit_model(
            model,
            model_inputs(name, transformed),
            metadata.label.to_numpy(),
            donors,
            epochs=epochs[name],
            batch_size=protocol.batch_size,
            learning_rate=protocol.learning_rate,
            seed=protocol.model_seed,
        )
        states[name] = model.state_dict()
    for name, scaler in fitted.items():
        scales[name] = {
            attribute: torch.as_tensor(np.asarray(getattr(scaler.transformer, attribute)))
            for attribute in ("mean_", "var_", "scale_", "n_samples_seen_")
        }
    # PyTorch 2.8 state_dict/weights_only workflow:
    # https://docs.pytorch.org/docs/2.8/generated/torch.load.html
    torch.save({"models": states, "scalers": scales}, folder / "models.pt")
    manifest = contract | {"models": training, "models_sha256": sha256_file(folder / "models.pt")}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest | {"manifest_sha256": sha256_file(folder / "manifest.json")}


def evaluate_final(folder, manifest_sha256, views, metadata, feature_ids, *, output_dir, mode):
    """Reload frozen models/scalers; score a disjoint cohort once per artifact.

    A durable exclusive lock is taken before predicting, and remains after failures.
    This prevents accidental repeat selection, not malicious copying/deleting locks.
    Callers must establish specimen independence separately: different IDs are not proof.
    """
    _synthetic_only(mode)
    folder = Path(folder)
    if sha256_file(folder / "manifest.json") != manifest_sha256:
        raise ValueError("frozen manifest hash mismatch")
    manifest = json.loads((folder / "manifest.json").read_text())
    protocol = MultiomeProtocol(**manifest["protocol"])
    if manifest["mode"] != mode or protocol.fingerprint != manifest["protocol_sha256"]:
        raise ValueError("frozen mode/protocol mismatch")
    ids, donors, _ = _validate(views, metadata, feature_ids, protocol)
    if set(donors) & set(manifest["development_donors"]) or set(ids) & set(
        manifest["development_cell_ids"]
    ):
        raise ValueError("external and development identities overlap")
    if {key: list(map(str, value)) for key, value in feature_ids.items()} != manifest[
        "feature_ids"
    ]:
        raise ValueError("external feature order differs from frozen contract")
    if sha256_file(folder / "models.pt") != manifest["models_sha256"]:
        raise ValueError("frozen weights/scaler hash mismatch")
    total = sum(
        len(ids) * len(record["selected_features"]) for record in manifest["preprocessing"].values()
    )
    if total > 2_000_000:
        raise ValueError("external selected arrays exceed dense element budget")
    saved = torch.load(folder / "models.pt", weights_only=True, map_location="cpu")
    transformed = {}
    for name, record in manifest["preprocessing"].items():
        scaler = StandardScaler()
        for attribute, tensor in saved["scalers"][name].items():
            setattr(scaler, attribute, tensor.numpy())
        scaler.n_features_in_ = len(record["selected_features"])
        frozen = FittedTransform("standard_scaler", scaler, record["transform"])
        selected = views[name][:, record["selected_features"]]
        transformed[name] = frozen.transform(
            selected.toarray() if sparse.issparse(selected) else selected
        )
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    with (folder / "external_evaluation.lock").open("x") as lock:
        lock.write(
            json.dumps({"manifest_sha256": manifest_sha256, "output": str(output.resolve())})
        )
    output.mkdir(parents=True, exist_ok=False)
    tables = {}
    truth = pd.Series(metadata.label.to_numpy(), index=donors).groupby(level=0).first()
    widths = [transformed[name].shape[1] for name in (VIEW_A, VIEW_B)]
    for name in (*NEURAL_FAMILIES, "majority"):
        if name == "majority":
            probability = np.full(len(ids), manifest["majority_class"], dtype=float)
        else:
            model = paired_model(name, widths, protocol)
            model.load_state_dict(saved["models"][name], strict=True)
            _, probabilities = predict(model, model_inputs(name, transformed))
            probability = probabilities[:, 1]
        table = aggregate_donor_probabilities(probability, donors)
        table["label"] = table.donor_id.map(truth).astype(int)
        table["model"] = name
        tables[name] = table
    comparison = paired_comparison(tables["cross_attention"], tables["token_concat"])
    predictions = pd.concat(tables.values(), ignore_index=True)
    report = {
        "mode": mode,
        "scientific_claim_allowed": False,
        "manifest_sha256": manifest_sha256,
        "comparison": comparison,
        "predictions": predictions.to_dict(orient="records"),
    }
    predictions.to_csv(output / "donor_predictions.csv", index=False)
    pd.DataFrame(
        [
            {
                "model": name,
                "donor_balanced_accuracy": balanced_accuracy(table.label, table.prediction).value,
                "n_donors": len(table),
                "status": "SYNTHETIC_ONLY",
            }
            for name, table in tables.items()
        ]
    ).to_csv(output / "validation.csv", index=False)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report
