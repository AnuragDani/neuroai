"""Missing simple linear controls for the paired RNA+ATAC comparison.

The six-family neural comparison has no matched linear control. Existing
pseudobulk logistic outputs use a different input/aggregation setup, so they
cannot stand in for cell-level logistic regression on the *same* selected and
scaled cell features, the same inner-training donors and the same held-out donor
aggregation.

This script fits three frozen controls per outer fold:

* ``logreg_rna``: logistic regression on the selected/scaled RNA cell features;
* ``logreg_atac``: logistic regression on the selected/scaled ATAC cell features;
* ``logreg_concat``: logistic regression on the concatenation of both views.

It reuses the exact training-only variance selection and scaling of the neural
comparison (:func:`p22.eval.multiome_runner.prepare_paired_fold`), the executable
donor split, and the declared primary statistic. Regularisation is frozen
(``C=1.0``, ``lbfgs``, ``max_iter=1000``, ``tol=1e-4``, ``random_state=0``), donor
training weights match the neural inverse-donor-cell-count weighting normalised to
mean one, and no class reweighting is added. An unconverged fit is reported, not
silently used as a benchmark; a single recorded numerical extension to a higher
iteration cap is permitted and never depends on test accuracy.

It measures only. External paired data are not accessed and no biological
mechanism is claimed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from p22.data.group_splits import aggregate_donor_probabilities  # noqa: E402
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.metrics import balanced_accuracy  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.multiome_runner import prepare_paired_fold  # noqa: E402
from p22.eval.repeated_comparison import (  # noqa: E402
    PRIMARY_REFERENCE,
    repeated_model_accuracy,
    repeated_primary_contrast,
)
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from run_real_paired_comparison import _acceptance_decision, _fold_map, _indices  # noqa: E402
from run_real_paired_pilot import DEFAULT_H5AD, load_development_inputs  # noqa: E402

CONTROLS = ("logreg_rna", "logreg_atac", "logreg_concat")
FROZEN = {
    "C": 1.0,
    "solver": "lbfgs",
    "max_iter": 1000,
    "tol": 1e-4,
    "random_state": 0,
}
CONVERGENCE_EXTENSION_MAX_ITER = 10000


def donor_cell_weights(donor_ids) -> np.ndarray:
    """Inverse-donor-cell-count weights normalised so their mean is one.

    This reproduces the neural trainer's ``len(train_donors) / (n_donors *
    count[donor])`` weighting, whose per-cell mean is exactly one.
    """
    donors = np.asarray([str(value) for value in donor_ids], dtype=object)
    _, inverse, counts = np.unique(donors, return_inverse=True, return_counts=True)
    return len(donors) / (len(counts) * counts[inverse])


def fit_logistic(matrix, labels, weights):
    """Fit the frozen logistic control, extending iterations once if needed.

    Returns ``(estimator, convergence)``. Convergence is judged by whether the
    optimiser stopped before the iteration cap, never by held-out performance.
    """
    estimator = LogisticRegression(**FROZEN)
    estimator.fit(matrix, labels, sample_weight=weights)
    n_iter = int(np.atleast_1d(estimator.n_iter_)[0])
    convergence = {
        "max_iter": FROZEN["max_iter"],
        "n_iter": n_iter,
        "converged": n_iter < FROZEN["max_iter"],
        "extension_used": False,
    }
    if not convergence["converged"]:
        extended = LogisticRegression(**{**FROZEN, "max_iter": CONVERGENCE_EXTENSION_MAX_ITER})
        extended.fit(matrix, labels, sample_weight=weights)
        n_iter_ext = int(np.atleast_1d(extended.n_iter_)[0])
        convergence.update(
            {
                "extension_used": True,
                "extension_max_iter": CONVERGENCE_EXTENSION_MAX_ITER,
                "extension_n_iter": n_iter_ext,
                "converged": n_iter_ext < CONVERGENCE_EXTENSION_MAX_ITER,
                "reason": "iteration cap reached at the frozen max_iter; extended once for "
                "numerical convergence, independent of test accuracy",
            }
        )
        return extended, convergence
    return estimator, convergence


def _reference_repeats(reference_run: Path | None) -> dict[int, dict[str, list]]:
    """Load the primary reference family's per-fold donor predictions, if supplied."""
    if reference_run is None:
        return {}
    per_fold = json.loads((Path(reference_run) / "per_fold.json").read_text())
    repeats: dict[int, dict[str, list]] = {}
    for fold in per_fold:
        predictions = fold["record"]["models"][PRIMARY_REFERENCE]["predictions"]
        repeats.setdefault(int(fold["repeat"]), {}).setdefault(PRIMARY_REFERENCE, []).append(
            pd.DataFrame(predictions)
        )
    return repeats


def controls_run(
    protocol,
    h5ad_path,
    atac_path,
    regions_path,
    output_dir,
    req_path,
    man_path,
    reference_run=None,
    n_replicates: int = 1000,
    seed: int = 22,
):
    views, metadata, fingerprints = load_development_inputs(h5ad_path, atac_path, protocol)
    region_sets = json.loads(Path(regions_path).read_text())
    union_regions = region_sets["union_regions"]
    union_index = {region: index for index, region in enumerate(union_regions)}
    if views[VIEW_B].shape[1] != len(union_regions):
        raise ValueError("ATAC matrix columns do not match the union region set")
    folds = _fold_map(metadata, protocol)
    if len(region_sets["per_fold"]) != len(folds):
        raise ValueError("region-set fold count does not match the split plan")
    acceptance = _acceptance_decision(
        protocol,
        fingerprints,
        region_sets,
        list(folds.values()),
        metadata,
        atac_path,
        regions_path,
        req_path,
        man_path,
    )

    labels = metadata.label.to_numpy()
    donors = metadata.donor_id.astype(str).to_numpy()
    per_repeat: dict[int, dict[str, list]] = {}
    convergence_records = []
    per_fold = []
    for entry in region_sets["per_fold"]:
        key = (entry["repeat"], entry["fold"])
        if key not in folds:
            raise ValueError(f"region set references an unknown fold {key}")
        outer = folds[key]
        columns = [union_index[region] for region in entry["regions"]]
        fold_views = {VIEW_A: views[VIEW_A], VIEW_B: views[VIEW_B][:, columns]}
        indices = _indices(metadata, outer)
        transformed, _evidence = prepare_paired_fold(fold_views, metadata, indices, protocol)
        train, test = indices["train"], indices["test"]
        matrices = {
            "logreg_rna": transformed[VIEW_A],
            "logreg_atac": transformed[VIEW_B],
            "logreg_concat": np.hstack(
                [transformed[VIEW_A], transformed[VIEW_B]]
            ),
        }
        weights = donor_cell_weights(donors[train])
        truth = pd.Series(labels[test], index=donors[test]).groupby(level=0).first()
        fold_scores = {}
        for name, matrix in matrices.items():
            estimator, convergence = fit_logistic(matrix[train], labels[train], weights)
            probabilities = estimator.predict_proba(matrix[test])[:, 1]
            table = aggregate_donor_probabilities(probabilities, donors[test])
            table["label"] = table.donor_id.map(truth).astype(int)
            per_repeat.setdefault(outer.repeat, {}).setdefault(name, []).append(table)
            fold_scores[name] = balanced_accuracy(table.label, table.prediction).to_dict()
            convergence_records.append(
                {"repeat": outer.repeat, "fold": outer.fold, "control": name, **convergence}
            )
        per_fold.append(
            {
                "repeat": outer.repeat,
                "fold": outer.fold,
                "regions_sha256": entry["regions_sha256"],
                "n_test_donors": len(outer.test_donors),
                "test_donors": list(outer.test_donors),
                "donor_balanced_accuracy": fold_scores,
            }
        )

    reference_repeats = _reference_repeats(reference_run)
    repeats = []
    for repeat in sorted(per_repeat):
        entry = {"repeat": repeat}
        for name in CONTROLS:
            entry[name] = pd.concat(per_repeat[repeat][name], ignore_index=True)
        if repeat in reference_repeats:
            entry[PRIMARY_REFERENCE] = pd.concat(
                reference_repeats[repeat][PRIMARY_REFERENCE], ignore_index=True
            )
        repeats.append(entry)

    summaries = {name: repeated_model_accuracy(repeats, name) for name in CONTROLS}
    contrasts = {}
    if reference_repeats:
        for name in CONTROLS:
            contrasts[name] = repeated_primary_contrast(
                repeats,
                model=name,
                reference=PRIMARY_REFERENCE,
                n_replicates=n_replicates,
                seed=seed,
            )

    return {
        "data_mode": "real_development_linear_controls",
        "scientific_claim_allowed": acceptance.scientific_claim_allowed,
        "pilot": not acceptance.scientific_claim_allowed,
        "final_internal_estimate": False,
        "external_evaluation_performed": False,
        "acceptance": acceptance.to_dict(),
        "n_folds_run": len(per_fold),
        "input_fingerprints": fingerprints,
        "region_set_fingerprint": {
            "path": str(regions_path),
            "union_sha256": region_sets["union_sha256"],
            "n_union_regions": region_sets["n_union_regions"],
        },
        "controls": list(CONTROLS),
        "frozen_regularisation": dict(FROZEN),
        "reference_model": PRIMARY_REFERENCE,
        "reference_run": str(reference_run) if reference_run else None,
        "convergence": convergence_records,
        "per_fold": per_fold,
        "donor_predictions": {
            str(repeat): {
                name: pd.concat(frames, ignore_index=True).to_dict(orient="records")
                for name, frames in families.items()
            }
            for repeat, families in sorted(per_repeat.items())
        },
        "model_summaries": summaries,
        "secondary_contrasts_vs_reference": contrasts,
        "limitations": [
            "Internal development comparison only; external paired data were not accessed.",
            "Cell-level logistic regression on selected/scaled features; a different "
            "estimator from the neural families.",
            "Secondary contrasts versus the primary reference are descriptive and do not "
            "replace the declared cross-attention minus token-concat primary contrast.",
            "Predictions must not be used to select outcome-favourable donors.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", required=True, type=Path)
    parser.add_argument("--region-sets", required=True, type=Path)
    parser.add_argument("--acceptance-requirements", type=Path, required=True)
    parser.add_argument("--acceptance-manifest", type=Path, required=True)
    parser.add_argument(
        "--reference-run",
        type=Path,
        default=None,
        help="comparison run directory supplying token_concat donor predictions",
    )
    parser.add_argument("--n-replicates", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print("refusing to overwrite an existing output directory", file=sys.stderr)
        return 2
    config = json.loads(args.config.read_text())
    protocol = MultiomeProtocol(**config["protocol"])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report, resource = measure_stage(
        "real_paired_linear_controls",
        lambda: controls_run(
            protocol,
            args.h5ad,
            args.atac_matrix,
            args.region_sets,
            args.output_dir,
            args.acceptance_requirements,
            args.acceptance_manifest,
            args.reference_run,
            args.n_replicates,
            args.seed,
        ),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Frozen-fold linear controls on CPU; not external",
    )
    report.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        protocol=asdict(protocol),
        protocol_sha256=protocol.fingerprint,
        environment=environment_record(),
        resources=resource.to_dict(),
    )
    per_fold = report.pop("per_fold")
    (args.output_dir / "per_fold.json").write_text(
        json.dumps(per_fold, indent=2, default=str) + "\n"
    )
    donor_predictions = report.pop("donor_predictions")
    (args.output_dir / "donor_predictions.json").write_text(
        json.dumps(donor_predictions, indent=2, default=str) + "\n"
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(args.output_dir / "run.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
