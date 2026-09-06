#!/usr/bin/env python
"""Run a local, synthetic-only paired-model benchmark. No real-data input flags."""

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from scipy import sparse  # noqa: E402

from p22.data.group_splits import (  # noqa: E402
    iter_repeated_stratified_group_folds,
    validate_group_folds,
)
from p22.data.real_cohort import sample_nested_capped_cells  # noqa: E402
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol, paired_comparison  # noqa: E402
from p22.eval.multiome_runner import run_paired_fold  # noqa: E402
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.runs.registry import current_git_commit, data_fingerprint  # noqa: E402
from p22.testing.synthetic import make_synthetic_multimodal  # noqa: E402


def benchmark(protocol, dataset):
    fixture = make_synthetic_multimodal(**dataset, n_classes=2, label_unit="donor")
    rows = sample_nested_capped_cells(
        fixture.metadata,
        np.ones(fixture.n_cells, dtype=bool),
        (protocol.cell_cap,),
        protocol.sampling_seed,
    )[protocol.cell_cap]
    metadata = fixture.metadata.iloc[rows].reset_index(drop=True)
    dense = {VIEW_A: fixture.view_a[rows], VIEW_B: fixture.view_b[rows]}
    views = {key: sparse.csr_matrix(value) for key, value in dense.items()}
    folds = list(
        iter_repeated_stratified_group_folds(
            metadata.donor_id,
            metadata.label,
            protocol.n_repeats,
            protocol.n_folds,
            protocol.split_seed,
        )
    )
    problems = validate_group_folds(folds)
    if problems:
        raise ValueError("; ".join(problems))
    records = []
    for outer in folds:
        training = metadata.iloc[outer.train_index]
        inner = next(
            iter_repeated_stratified_group_folds(
                training.donor_id,
                training.label,
                n_repeats=1,
                n_folds=3,
                base_seed=outer.split_seed,
            )
        )
        indices = {
            "train": outer.train_index[inner.train_index],
            "val": outer.train_index[inner.test_index],
            "test": outer.test_index,
        }
        record = run_paired_fold(views, metadata, indices, protocol)
        records.append(record | {"repeat": outer.repeat, "fold": outer.fold})
    comparisons = []
    for repeat in range(protocol.n_repeats):
        tables = {}
        for model in ("cross_attention", "token_concat"):
            tables[model] = pd.DataFrame(
                [
                    prediction
                    for record in records
                    if record["repeat"] == repeat
                    for prediction in record["models"][model]["predictions"]
                ]
            )
        comparisons.append(
            {
                "repeat": repeat,
                **paired_comparison(tables["cross_attention"], tables["token_concat"]),
            }
        )
    return {
        "data_mode": "synthetic",
        "scientific_claim_allowed": False,
        "real_data_training_performed": False,
        "external_evaluation_performed": False,
        "generation": fixture.generation,
        "data_fingerprint": data_fingerprint(dense, metadata.label, metadata.donor_id),
        "donors_below_cap": metadata.groupby("donor_id")
        .size()
        .loc[lambda values: values < protocol.cell_cap]
        .to_dict(),
        "folds": records,
        "synthetic_paired_comparisons_by_repeat": comparisons,
        "not_applicable_controls": {
            "chr21_dosage": "no biological chromosome annotation in neutral fixture",
            "qc_covariate_logistic": "no biological QC covariates in neutral fixture",
            "pseudobulk_rna_logistic": "fixture is not RNA count data",
        },
        "limitations": [
            "Synthetic wiring only; scores and advantage flags are not scientific evidence.",
            "No accepted real normalization, release/QC, specimen, or ATAC feature contract.",
            "No external cohort, final all-development refit, or frozen external checkpoint.",
            "Fold weights are hashed in memory, not saved deployment artifacts.",
            "Attention has more parameters than its matched-token concat control.",
            "Each repeat resamples donors, never cells or repeat rows as independent donors.",
            "Resource figures apply to this bounded synthetic workload only.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    created = False
    try:
        config = json.loads(args.config.read_text())
        if (
            set(config) != {"data_mode", "dataset", "protocol"}
            or config["data_mode"] != "synthetic"
        ):
            raise ValueError("only an explicit synthetic configuration is supported")
        protocol = MultiomeProtocol(**config["protocol"])
        dataset = config["dataset"]
        expected = {"n_donors", "cells_per_donor", "n_features_a", "n_features_b", "seed"}
        if set(dataset) != expected or any(
            type(value) is not int or value < 0 for value in dataset.values()
        ):
            raise ValueError("dataset requires non-negative integer fixture dimensions and seed")
        raw_size = (
            dataset["n_donors"]
            * dataset["cells_per_donor"]
            * (dataset["n_features_a"] + dataset["n_features_b"])
        )
        if (
            raw_size > 2_000_000
            or protocol.n_repeats * protocol.n_folds > 25
            or protocol.max_epochs > 40
        ):
            raise ValueError("synthetic benchmark exceeds bounded local budget")
        if (
            protocol.n_tokens * protocol.embed_dim > 256
            or protocol.hidden_dim > 128
            or protocol.batch_size > 256
            or protocol.cell_cap > 256
        ):
            raise ValueError("model exceeds bounded local token/width/batch/cell budget")
        args.output_dir.mkdir(parents=True, exist_ok=False)
        created = True
        resolved = config | {"protocol": asdict(protocol)}
        (args.output_dir / "config.json").write_text(json.dumps(resolved, indent=2) + "\n")
        torch.set_num_threads(1)
        report, resource = measure_stage(
            "synthetic_paired_training",
            lambda: benchmark(protocol, dataset),
            cells_per_donor_cap=protocol.cell_cap,
            disk_path=args.output_dir,
            notes="Complete synthetic run on CPU with one PyTorch thread; not a real-data estimate",
        )
        report.update(
            protocol=asdict(protocol),
            protocol_sha256=protocol.fingerprint,
            git_commit=current_git_commit(),
            environment=environment_record(),
            resources=resource.to_dict(),
            torch_threads=torch.get_num_threads(),
        )
        paths = [Path(__file__), *(ROOT / "src/p22").rglob("*.py")]
        report["source_sha256"] = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)
        }
        (args.output_dir / "run.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        lines = [
            "# Synthetic paired-model benchmark",
            "",
            "Software verification only. No biological result.",
            "",
            f"- Folds: {len(report['folds'])}; neural families: 6.",
            f"- Elapsed seconds: {resource.elapsed_seconds}; "
            f"process peak RAM: {resource.peak_rss_gb} GB.",
            f"- Protocol SHA-256: `{protocol.fingerprint}`.",
            "- Real-data training and external evaluation: not performed.",
            "",
            "See run.json for per-model results, checkpoint hashes, splits, and limitations.",
        ]
        (args.output_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n")
        print(args.output_dir / "SUMMARY.md")
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        if created:
            (args.output_dir / "failure.json").write_text(
                json.dumps({"error": str(error)}, indent=2)
            )
        print(f"Benchmark refused or failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
