"""Real-data smoke for N2 fold prep (repeat 0 / fold 0, cap 1000).

Loads the sampled cells once, then runs :func:`prepare_nn_fold` for the first
donor fold and writes shapes, fit evidence, wall time and peak RSS to
``docs/nn_v2/fold_prep_smoke.json``. Not a unit test; it touches the real H5AD.
"""

from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold, region_indices

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "nn_inputs_2026-09-23.json"
OUT = ROOT / "docs" / "nn_v2" / "fold_prep_smoke.json"
CAP = 1000
SEED = 22


def main() -> None:
    config = json.loads(CONFIG.read_text())["inputs"]
    h5ad = config["h5ad"]["path"]
    atac_npz = config["atac_tiebreak_counts"]["path"]
    union_bed = config["tracked_union_bed"]["path"]
    region_sets = json.loads(Path(config["region_sets_sha256_json"]["path"]).read_text())

    fold = next(
        entry
        for entry in region_sets["per_fold"]
        if entry["repeat"] == 0 and entry["fold"] == 0
    )

    started = time.time()
    inputs = load_nn_inputs(h5ad, atac_npz, cap=CAP, seed=SEED, union_bed=union_bed)
    load_seconds = time.time() - started

    donors = inputs.metadata["donor_id"].astype(str)
    train_donors = set(fold["train_donors"])
    test_donors = set(fold["test_donors"])
    train_rows = np.flatnonzero(donors.isin(train_donors).to_numpy())
    holdout_rows = np.flatnonzero(donors.isin(test_donors).to_numpy())
    region_rows = region_indices(inputs, fold["regions"])

    started = time.time()
    fold_arrays = prepare_nn_fold(
        inputs,
        train_rows=train_rows,
        holdout_rows=holdout_rows,
        region_rows=region_rows,
        n_hvg=2000,
    )
    prep_seconds = time.time() - started
    peak_rss_gib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
        1024**3 if sys.platform == "darwin" else 1024**2
    )

    report = {
        "record_type": "nn_fold_prep_smoke",
        "repeat": 0,
        "fold": 0,
        "cap": CAP,
        "sampler_seed": SEED,
        "n_cells_sampled": int(inputs.metadata.shape[0]),
        "n_genes_union": int(inputs.gene_ids.size),
        "n_regions_union": len(inputs.regions),
        "load_seconds": round(load_seconds, 2),
        "prep_seconds": round(prep_seconds, 2),
        "peak_rss_gib": round(peak_rss_gib, 3),
        "rna_shape": list(fold_arrays.rna.shape),
        "atac_shape": list(fold_arrays.atac.shape),
        "qc_shape": list(fold_arrays.qc.shape),
        "n_positive_labels": int(fold_arrays.label.sum()),
        "evidence": fold_arrays.evidence,
        "region_set_sha256": fold["regions_sha256"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in report.items() if k != "evidence"}, sort_keys=True))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
