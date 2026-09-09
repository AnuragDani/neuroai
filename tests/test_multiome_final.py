"""Final artifact and one-shot held-out scoring, using neutral arrays only."""

import json

import pytest

from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import NEURAL_FAMILIES
from p22.models.fusion import VIEW_A, VIEW_B
from p22.testing.synthetic import make_synthetic_multimodal


def inputs():
    fixture = make_synthetic_multimodal(
        n_donors=12,
        cells_per_donor=4,
        n_features_a=8,
        n_features_b=6,
        n_classes=2,
        label_unit="donor",
    )
    args = {
        "views": {VIEW_A: fixture.view_a, VIEW_B: fixture.view_b},
        "metadata": fixture.metadata,
        "protocol": MultiomeProtocol(max_epochs=1, feature_budget=4, hidden_dim=8, embed_dim=8),
    }
    args["feature_ids"] = {
        key: [f"{key}:{i}" for i in range(value.shape[1])] for key, value in args["views"].items()
    }
    return args


def test_final_refit_persists_and_scores_once_without_external_fitting(tmp_path):
    from p22.eval.multiome_final import evaluate_final, freeze_final

    args = inputs()
    epochs = {name: 1 for name in NEURAL_FAMILIES}
    folder = tmp_path / "models"
    frozen = freeze_final(**args, epochs=epochs, output_dir=folder, mode="synthetic")
    assert frozen["epoch_counts"] == epochs
    assert set(frozen["models"]) == set(NEURAL_FAMILIES)
    before = (folder / "models.pt").read_bytes()
    external = args["metadata"].copy()
    external["cell_id"] = "external:" + external.cell_id
    external["donor_id"] = "external:" + external.donor_id
    scored = evaluate_final(
        folder,
        frozen["manifest_sha256"],
        args["views"],
        external,
        args["feature_ids"],
        output_dir=tmp_path / "evaluation",
        mode="synthetic",
    )
    assert scored["scientific_claim_allowed"] is False
    assert len(scored["predictions"]) == 12 * 7
    assert (folder / "models.pt").read_bytes() == before
    assert (tmp_path / "evaluation/validation.csv").is_file()
    with pytest.raises(FileExistsError):
        evaluate_final(
            folder,
            frozen["manifest_sha256"],
            args["views"],
            external,
            args["feature_ids"],
            output_dir=tmp_path / "repeat",
            mode="synthetic",
        )


@pytest.mark.parametrize("problem", ["overlap", "features", "weights", "manifest", "approval"])
def test_external_contract_fails_before_prediction(tmp_path, problem):
    from p22.eval.multiome_final import evaluate_final, freeze_final

    args = inputs()
    folder = tmp_path / "models"
    frozen = freeze_final(
        **args, epochs={name: 1 for name in NEURAL_FAMILIES}, output_dir=folder, mode="synthetic"
    )
    external = args["metadata"].copy()
    if problem != "overlap":
        external["cell_id"] = "external:" + external.cell_id
        external["donor_id"] = "external:" + external.donor_id
    if problem == "features":
        args["feature_ids"] = {
            key: list(reversed(value)) for key, value in args["feature_ids"].items()
        }
    elif problem == "weights":
        with (folder / "models.pt").open("ab") as stream:
            stream.write(b"changed")
    elif problem == "manifest":
        manifest = json.loads((folder / "manifest.json").read_text())
        manifest["majority_class"] = 1 - manifest["majority_class"]
        (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises((ValueError, PermissionError)):
        evaluate_final(
            folder,
            frozen["manifest_sha256"],
            args["views"],
            external,
            args["feature_ids"],
            output_dir=tmp_path / "evaluation",
            mode="real" if problem == "approval" else "synthetic",
        )
    assert not (tmp_path / "evaluation").exists()
    assert not (folder / "external_evaluation.lock").exists()
