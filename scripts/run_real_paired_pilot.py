"""Real-data paired RNA+ATAC pilot on the frozen development inputs.

This is the missing real orchestration for the paired study. It consumes the two
accepted development views on the same 248,998 cells:

* RNA: the local CELLxGENE H5AD ``raw/X`` (cells x genes, integer raw counts),
  with columns following ``raw/var`` (not the processed ``X``/``var`` axis);
* ATAC: the frozen training-fold region matrix recovered by bounded remote
  fragment queries (``scripts/quantify_development_atac.py``).

It runs one predeclared donor-isolated outer fold plus an inner validation split,
trains the six neural families and reports the primary cross-attention vs matched
token-concat donor-level comparison. It is explicitly a **pilot**: one fold, one
initialization seed, raw-count standard scaling, no final refit and no external
evaluation. Its predictions are not a final estimate and must not be selected on
outcome-favourable donors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
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
from p22.data.real_cohort import (  # noqa: E402
    DEFAULT_RNA_MATRIX_KEY,
    load_cell_matrix,
    read_matrix_axis,
    sample_nested_capped_cells,
)
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol, paired_comparison  # noqa: E402
from p22.eval.multiome_runner import run_paired_fold  # noqa: E402
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402

DEFAULT_H5AD = (
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_ATAC = "reports/generated/development_region_set_20260921/counts/counts.npz"


def load_development_inputs(h5ad_path, atac_path, protocol):
    """Return (views, metadata, input_fingerprints) for the capped pilot cells."""
    import anndata as ad

    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        obs = backed.obs[["library", "donor_id", "disease"]].copy()
        n_cells = backed.n_obs
        n_genes = backed.n_vars
    finally:
        backed.file.close()
    obs = obs.reset_index().rename(columns={"index": "cell_id"})
    if obs["cell_id"].duplicated().any():
        raise ValueError("H5AD cell identifiers are not unique")
    obs["label"] = (obs["disease"] == "complete trisomy 21").astype(int)
    if set(obs["label"].unique()) != {0, 1}:
        raise ValueError("both disease classes are required")
    rows = sample_nested_capped_cells(
        obs[["donor_id"]].rename(columns={"donor_id": "donor_id"}),
        np.ones(len(obs), dtype=bool),
        (protocol.cell_cap,),
        protocol.sampling_seed,
    )[protocol.cell_cap]
    metadata = obs.iloc[rows].reset_index(drop=True)
    axis = read_matrix_axis(h5ad_path, DEFAULT_RNA_MATRIX_KEY)
    if axis["n_cells"] != n_cells:
        raise ValueError("raw RNA block cells do not match the H5AD obs axis")
    rna = load_cell_matrix(h5ad_path, rows, matrix_key=DEFAULT_RNA_MATRIX_KEY)
    if rna.shape[1] != axis["n_genes"]:
        raise ValueError("raw RNA block columns do not match the declared raw axis")
    atac_matrix = sparse.load_npz(atac_path)
    if atac_matrix.shape[1] != n_cells:
        raise ValueError("ATAC matrix cells do not match the H5AD cell count")
    atac = atac_matrix[:, rows].transpose().tocsr()
    views = {VIEW_A: sparse.csr_matrix(rna), VIEW_B: atac}
    gene_ids = axis["gene_ids"] or []
    gene_axis_sha256 = hashlib.sha256("\n".join(gene_ids).encode()).hexdigest()
    fingerprints = {
        "h5ad": {"path": str(h5ad_path), "sha256": _sha256(h5ad_path), "n_genes": int(n_genes)},
        "rna_representation": {
            "matrix_key": DEFAULT_RNA_MATRIX_KEY,
            "axis_key": axis["axis_key"],
            "n_genes": int(axis["n_genes"]),
            "gene_axis_sha256": gene_axis_sha256,
            "integer_counts_validated": True,
        },
        "atac_matrix": {
            "path": str(atac_path),
            "sha256": _sha256(atac_path),
            "n_regions": int(atac_matrix.shape[0]),
        },
        "n_cells_available": int(n_cells),
        "n_cells_sampled": int(len(rows)),
        "cell_cap": protocol.cell_cap,
    }
    return views, metadata, fingerprints


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pilot(protocol, h5ad_path, atac_path, output_dir):
    views, metadata, fingerprints = load_development_inputs(h5ad_path, atac_path, protocol)
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
    outer = folds[0]
    training = metadata.iloc[outer.train_index]
    inner = next(
        iter_repeated_stratified_group_folds(
            training.donor_id, training.label, n_repeats=1, n_folds=3, base_seed=outer.split_seed
        )
    )
    indices = {
        "train": outer.train_index[inner.train_index],
        "val": outer.train_index[inner.test_index],
        "test": outer.test_index,
    }
    record = run_paired_fold(views, metadata, indices, protocol)
    tables = {}
    for model in ("cross_attention", "token_concat"):
        tables[model] = pd.DataFrame(record["models"][model]["predictions"])
    comparison = paired_comparison(tables["cross_attention"], tables["token_concat"])
    features = {
        VIEW_A: [f"gene:{i}" for i in range(views[VIEW_A].shape[1])],
        VIEW_B: [f"region:{i}" for i in range(views[VIEW_B].shape[1])],
    }
    return {
        "data_mode": "real_development_pilot",
        "scientific_claim_allowed": False,
        "pilot": True,
        "final_estimate": False,
        "external_evaluation_performed": False,
        "n_folds_run": 1,
        "input_fingerprints": fingerprints,
        "fold": outer.to_dict(),
        "indices_sizes": {name: int(len(value)) for name, value in indices.items()},
        "feature_counts": {name: int(matrix.shape[1]) for name, matrix in views.items()},
        "record": record,
        "primary_comparison": comparison,
        "features": {key: value[:5] for key, value in features.items()},
        "limitations": [
            "Pilot only: one outer fold and one initialization seed.",
            "Raw-count standard scaling; the accepted normalization is not frozen.",
            "No final refit and no external evaluation.",
            "Predictions must not be used to select outcome-favourable donors.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(ROOT / DEFAULT_ATAC))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print("refusing to overwrite an existing output directory", file=sys.stderr)
        return 2
    config = json.loads(args.config.read_text())
    protocol = MultiomeProtocol(**config["protocol"])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    report, resource = measure_stage(
        "real_paired_pilot",
        lambda: pilot(protocol, args.h5ad, args.atac_matrix, args.output_dir),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Real development pilot on CPU; not a final or external estimate",
    )
    report.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        protocol=asdict(protocol),
        protocol_sha256=protocol.fingerprint,
        environment=environment_record(),
        resources=resource.to_dict(),
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2) + "\n")
    comparison = report["primary_comparison"]
    summary = [
        "# Real paired RNA+ATAC development pilot",
        "",
        "Pilot only. Not a final estimate and not external validation.",
        "",
        f"- Sampled cells: {report['input_fingerprints']['n_cells_sampled']} "
        f"(cap {protocol.cell_cap}/donor).",
        f"- Outer fold: repeat {report['fold']['repeat']} fold {report['fold']['fold']}; "
        f"{len(report['fold']['train_donors'])} train / "
        f"{len(report['fold']['test_donors'])} test donors.",
        f"- Cross-attention minus token-concat donor balanced accuracy: "
        f"{comparison['estimate']} (interval {comparison['interval']}).",
        f"- Practical margin: {comparison['practical_margin']}; "
        f"advantage demonstrated: {comparison['advantage_demonstrated']}.",
        f"- Elapsed seconds: {resource.elapsed_seconds}; peak RSS: {resource.peak_rss_gb} GB.",
        "",
        "See run.json for per-model predictions, splits, checkpoint hashes and resources.",
    ]
    (args.output_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    print(args.output_dir / "SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
