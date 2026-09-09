"""Synthetic fold integration and train-only preprocessing checks."""

from dataclasses import replace

import numpy as np
import pytest
from scipy import sparse

from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import prepare_paired_fold
from p22.models.fusion import VIEW_A, VIEW_B
from p22.testing.synthetic import make_synthetic_multimodal


def fixture_arguments():
    fixture = make_synthetic_multimodal(
        n_donors=12,
        cells_per_donor=4,
        n_features_a=8,
        n_features_b=6,
        n_classes=2,
        label_unit="donor",
    )
    truth = fixture.metadata.groupby("donor_id")["label"].first()
    groups = [[], [], []]
    for label in (0, 1):
        donors = truth[truth == label].index.to_list()
        for index, donor in enumerate(donors):
            groups[min(index // 2, 2)].append(donor)
    indices = {
        name: np.flatnonzero(np.isin(fixture.donor_ids, donors))
        for name, donors in zip(("train", "val", "test"), groups, strict=True)
    }
    return dict(
        views={
            VIEW_A: sparse.csr_matrix(fixture.view_a),
            VIEW_B: sparse.csr_matrix(fixture.view_b),
        },
        metadata=fixture.metadata,
        indices=indices,
        protocol=MultiomeProtocol(
            max_epochs=2, patience=2, feature_budget=4, embed_dim=8, hidden_dim=8
        ),
    )


@pytest.mark.parametrize("split", ["val", "test"])
def test_fold_preprocessing_never_learns_from_held_out_values(split):
    arguments = fixture_arguments()
    _, first = prepare_paired_fold(**arguments)
    changed = {name: matrix.toarray() for name, matrix in arguments["views"].items()}
    for matrix in changed.values():
        matrix[arguments["indices"][split]] *= 1000
    _, second = prepare_paired_fold(**(arguments | {"views": changed}))
    for name in (VIEW_A, VIEW_B):
        assert first[name]["selected_features"] == second[name]["selected_features"]
        assert (
            first[name]["transform"]["parameter_fingerprint"]
            == (second[name]["transform"]["parameter_fingerprint"])
        )


@pytest.mark.parametrize("problem", ["overlap", "duplicate", "out_of_bounds", "budget", "cap"])
def test_fold_rejects_bad_partitions_or_unbounded_dense_conversion(problem):
    arguments = fixture_arguments()
    if problem == "overlap":
        arguments["metadata"] = arguments["metadata"].copy()
        test_row = arguments["indices"]["test"][0]
        train_row = arguments["indices"]["train"][0]
        arguments["metadata"].loc[test_row, "donor_id"] = arguments["metadata"].loc[
            train_row, "donor_id"
        ]
    elif problem == "duplicate":
        arguments["indices"]["train"] = np.repeat(arguments["indices"]["train"], 2)
    elif problem == "out_of_bounds":
        arguments["indices"]["train"][0] = 999
    elif problem == "cap":
        arguments["protocol"] = replace(arguments["protocol"], cell_cap=1)
    else:
        arguments["max_dense_elements"] = 1
    with pytest.raises(ValueError):
        prepare_paired_fold(**arguments)


def test_all_neural_families_use_same_partitions_and_donor_selection():
    from p22.eval.multiome_runner import run_paired_fold

    arguments = fixture_arguments()
    result = run_paired_fold(**arguments)
    assert result["majority_control"]["donor_balanced_accuracy"]["value"] == 0.5
    assert len(result["majority_control"]["predictions"]) == 4
    assert set(result["models"]) == {
        "rna_only",
        "atac_only",
        "rna_atac_concat",
        "gated_fusion",
        "token_concat",
        "cross_attention",
    }
    sets = []
    for record in result["models"].values():
        assert record["training"]["selection_unit"] == "donor"
        assert record["parameters"] > 0 and len(record["checkpoint_sha256"]) == 64
        sets.append({row["donor_id"] for row in record["predictions"]})
    assert all(donors == sets[0] for donors in sets)
    assert result["protocol_sha256"] == arguments["protocol"].fingerprint
    assert result["preprocessing"][VIEW_A]["transform"]["n_train_cells"] == 16
    changed = run_paired_fold(
        **(arguments | {"protocol": replace(arguments["protocol"], max_epochs=1)})
    )
    assert changed["protocol_sha256"] != result["protocol_sha256"]


def test_synthetic_command_runs_and_refuses_real_data_or_existing_outputs(tmp_path):
    import json
    import subprocess
    import sys
    from dataclasses import asdict
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    config = {
        "data_mode": "synthetic",
        "dataset": {
            "n_donors": 20,
            "cells_per_donor": 4,
            "n_features_a": 8,
            "n_features_b": 6,
            "seed": 22,
        },
        "protocol": asdict(
            MultiomeProtocol(
                n_repeats=1, n_folds=2, max_epochs=1, feature_budget=4, hidden_dim=8, embed_dim=8
            )
        ),
    }
    config_path, output = tmp_path / "config.json", tmp_path / "run"
    config_path.write_text(json.dumps(config))
    command = [
        sys.executable,
        str(root / "scripts/train_multiome.py"),
        "--config",
        str(config_path),
        "--output-dir",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    report = json.loads((output / "run.json").read_text())
    assert report["data_mode"] == "synthetic" and not report["scientific_claim_allowed"]
    assert len(report["folds"]) == 2
    assert report["real_data_training_performed"] is False
    assert report["final_artifacts"]["epoch_rule"] == "ceil(median(internal best epochs))"
    assert (output / "final/models.pt").is_file()
    assert (output / "synthetic_external/validation.csv").is_file()
    assert report["synthetic_external_evaluation"]["scientific_claim_allowed"] is False
    assert subprocess.run(command, capture_output=True).returncode != 0
    config["data_mode"] = "real"
    config_path.write_text(json.dumps(config))
    command[-1] = str(tmp_path / "real")
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (tmp_path / "real").exists()
