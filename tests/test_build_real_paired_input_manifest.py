"""Tests for the measured artifact manifest builder used by the acceptance gate.

The builder hashes the exact corrected artifacts the real paired entry points
consume. A synthetic H5AD and sidecar prove the wiring and the refusal cases
without touching the 1.57 GB asset.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parents[1]


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


builder = load_script(
    "build_real_paired_input_manifest", "scripts/build_real_paired_input_manifest.py"
)


def _write_h5ad(path: Path, cells: list[str], genes: list[str]) -> None:
    anndata = pytest.importorskip("anndata")
    from scipy import sparse

    counts = np.ones((len(cells), len(genes)), dtype=np.float32)
    processed = counts / 2.0
    adata = anndata.AnnData(
        X=sparse.csr_matrix(processed),
        obs=None,
        var=None,
    )
    adata.obs.index = cells
    adata.var.index = genes
    adata.raw = anndata.AnnData(X=sparse.csr_matrix(counts))
    adata.raw.var.index = genes
    adata.write_h5ad(path)


def _sha(items) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


@pytest.fixture()
def artifacts(tmp_path: Path):
    cells = ["cellA", "cellB", "cellC"]
    genes = ["gene1", "gene2", "gene3", "gene4"]
    h5ad = tmp_path / "fixture.h5ad"
    _write_h5ad(h5ad, cells, genes)

    union_regions = ["chr1:100-200", "chr1:300-400"]
    union_bed = tmp_path / "union.bed"
    union_bed.write_text("chr1\t100\t200\nchr1\t300\t400\n")
    union_sha = hashlib.sha256(union_bed.read_bytes()).hexdigest()

    region_sets = tmp_path / "region_sets.json"
    region_sets.write_text(
        json.dumps(
            {
                "union_sha256": union_sha,
                "n_union_regions": len(union_regions),
                "union_regions": union_regions,
            }
        )
    )

    counts_dir = tmp_path / "counts"
    counts_dir.mkdir()
    matrix = counts_dir / "counts.npz"
    matrix.write_bytes(b"not-read-by-the-builder")
    sidecar = {
        "matrix_sha256": "a" * 64,
        "shape": [len(union_regions), len(cells)],
        "n_cells": len(cells),
        "cells_sha256": _sha(cells),
        "count_unit": "unique_fragment_overlap",
        "count_mode": "fragment",
        "unknown_policy": "error",
    }
    (counts_dir / "counts.json").write_text(json.dumps(sidecar))
    return {
        "h5ad": h5ad,
        "matrix": matrix,
        "region_sets": region_sets,
        "union_bed": union_bed,
        "cells": cells,
        "genes": genes,
        "union_sha": union_sha,
    }


def test_manifest_binds_ordered_cells_and_axes(artifacts):
    manifest = builder.build_manifest(
        artifacts["h5ad"],
        artifacts["matrix"],
        artifacts["region_sets"],
        artifacts["union_bed"],
    )
    assert manifest["record_type"] == "real_paired_input_manifest"
    assert manifest["rna"]["matrix_key"] == "raw/X"
    assert manifest["rna"]["axis_key"] == "raw/var"
    assert manifest["rna"]["n_cells"] == len(artifacts["cells"])
    assert manifest["rna"]["n_genes"] == len(artifacts["genes"])
    assert manifest["rna"]["cells_sha256"] == _sha(artifacts["cells"])
    assert manifest["atac"]["cells_sha256"] == _sha(artifacts["cells"])
    assert manifest["atac"]["n_regions"] == 2
    assert manifest["atac"]["count_unit"] == "unique_fragment_overlap"
    assert manifest["atac"]["regions_file_sha256"] == artifacts["union_sha"]
    assert manifest["region_sets"]["union_sha256"] == artifacts["union_sha"]


def test_manifest_is_accepted_by_the_gate_loader(artifacts, tmp_path):
    from p22.eval.real_paired_acceptance import load_manifest

    manifest = builder.build_manifest(
        artifacts["h5ad"],
        artifacts["matrix"],
        artifacts["region_sets"],
        artifacts["union_bed"],
    )
    out = tmp_path / "manifest.json"
    out.write_text(json.dumps(manifest))
    loaded = load_manifest(out)
    assert loaded["rna"]["h5ad_sha256"] == manifest["rna"]["h5ad_sha256"]


def test_manifest_refuses_mismatched_cell_order(artifacts):
    sidecar_path = artifacts["matrix"].parent / "counts.json"
    sidecar = json.loads(sidecar_path.read_text())
    sidecar["cells_sha256"] = _sha(["other", "cells", "here"])
    sidecar_path.write_text(json.dumps(sidecar))
    with pytest.raises(SystemExit, match="ordered cells"):
        builder.build_manifest(
            artifacts["h5ad"],
            artifacts["matrix"],
            artifacts["region_sets"],
            artifacts["union_bed"],
        )


def test_manifest_refuses_union_hash_mismatch(artifacts):
    artifacts["union_bed"].write_text("chr1\t100\t200\nchr1\t300\t401\n")
    with pytest.raises(SystemExit, match="does not decode"):
        builder.build_manifest(
            artifacts["h5ad"],
            artifacts["matrix"],
            artifacts["region_sets"],
            artifacts["union_bed"],
        )


def test_manifest_refuses_absent_sidecar(artifacts):
    (artifacts["matrix"].parent / "counts.json").unlink()
    with pytest.raises(SystemExit, match="sidecar"):
        builder.build_manifest(
            artifacts["h5ad"],
            artifacts["matrix"],
            artifacts["region_sets"],
            artifacts["union_bed"],
        )
