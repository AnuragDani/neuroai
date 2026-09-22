"""Build the measured artifact manifest the acceptance gate binds corrected runs to.

After the corrected ATAC matrices are measured, the real paired entry points must
be able to prove that the arrays they consume are the same arrays the correction
protocol declared. This script hashes the exact artifacts (local H5AD raw block,
corrected ATAC sidecar/matrix, frozen union region file and region-set record) and
writes ``configs/real_paired_input_manifest_2026-09-21.json``.

It measures only. It does not train, does not promote a scientific claim and does
not modify the historical matrices.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from p22.data.real_cohort import DEFAULT_RNA_MATRIX_KEY, read_matrix_axis  # noqa: E402


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(items) -> str:
    return hashlib.sha256("\n".join(str(item) for item in items).encode()).hexdigest()


def build_manifest(h5ad: Path, atac_matrix: Path, region_sets: Path, union_bed: Path) -> dict:
    import anndata as ad

    sidecar_path = atac_matrix.parent / "counts.json"
    if not sidecar_path.is_file():
        raise SystemExit(f"ATAC sidecar {sidecar_path} is absent; measure the matrix first")
    sidecar = json.loads(sidecar_path.read_text())

    backed = ad.read_h5ad(h5ad, backed="r")
    try:
        ordered_cells = backed.obs.index.astype(str).tolist()
        n_cells = int(backed.n_obs)
    finally:
        backed.file.close()
    axis = read_matrix_axis(h5ad, DEFAULT_RNA_MATRIX_KEY)
    if axis["n_cells"] != n_cells:
        raise SystemExit("raw RNA block cells do not match the H5AD obs axis")
    gene_ids = axis["gene_ids"]
    if not gene_ids or len(gene_ids) != axis["n_genes"]:
        raise SystemExit("raw RNA gene axis identifiers do not match the loaded columns")
    ordered_cells_sha256 = sha256_text(ordered_cells)

    n_regions = int(sidecar["shape"][0])
    if int(sidecar["n_cells"]) != n_cells:
        raise SystemExit("ATAC matrix cells do not match the H5AD cell count")
    if sidecar["cells_sha256"] != ordered_cells_sha256:
        raise SystemExit("ATAC matrix ordered cells do not match the H5AD obs order")

    region_record = json.loads(region_sets.read_text())
    # The region-set record stores a semantic hash over the ordered region list;
    # the union BED file hash is a separate artifact fingerprint. Both are bound.
    union_sha256 = region_record["union_sha256"]
    regions_file_sha256 = hashlib.sha256(union_bed.read_bytes()).hexdigest()
    decoded = []
    for line in union_bed.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            decoded.append(f"{fields[0]}:{fields[1]}-{fields[2]}")
    if decoded != list(region_record["union_regions"]):
        raise SystemExit("union region file does not decode to the recorded region list")
    if n_regions != region_record["n_union_regions"]:
        raise SystemExit("ATAC matrix rows do not match the union region count")

    return {
        "record_type": "real_paired_input_manifest",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scope": "corrected_development_paired_inputs",
        "note": (
            "Measured artifact manifest for the corrected run. Consumed by "
            "p22.eval.real_paired_acceptance; an ACCEPTED decision still requires "
            "the prospective requirements record and does not replace external "
            "validation."
        ),
        "rna": {
            "path": str(h5ad),
            "h5ad_sha256": sha256_file(h5ad),
            "matrix_key": DEFAULT_RNA_MATRIX_KEY,
            "axis_key": axis["axis_key"],
            "n_cells": n_cells,
            "n_genes": int(axis["n_genes"]),
            "gene_axis_sha256": sha256_text(gene_ids),
            "cells_sha256": ordered_cells_sha256,
        },
        "atac": {
            "path": str(atac_matrix),
            "matrix_sha256": sidecar["matrix_sha256"],
            "count_unit": sidecar.get("count_unit"),
            "count_mode": sidecar.get("count_mode"),
            "unknown_policy": sidecar.get("unknown_policy"),
            "n_regions": n_regions,
            "n_cells": int(sidecar["n_cells"]),
            "cells_sha256": sidecar["cells_sha256"],
            "regions_file_sha256": regions_file_sha256,
        },
        "region_sets": {
            "path": str(region_sets),
            "union_sha256": union_sha256,
            "n_union_regions": int(region_record["n_union_regions"]),
            "union_bed": str(union_bed),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--h5ad",
        default="/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
        "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad",
    )
    parser.add_argument("--atac-matrix", required=True, type=Path)
    parser.add_argument(
        "--region-sets",
        default=str(ROOT / "reports/generated/repeated_comparison_20260921/region_sets.json"),
        type=Path,
    )
    parser.add_argument(
        "--union-bed",
        default=str(ROOT / "reports/generated/repeated_comparison_20260921/union.bed"),
        type=Path,
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "configs/real_paired_input_manifest_2026-09-21.json"),
        type=Path,
    )
    args = parser.parse_args(argv)
    manifest = build_manifest(args.h5ad, args.atac_matrix, args.region_sets, args.union_bed)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {"out": str(args.out), "atac_matrix_sha256": manifest["atac"]["matrix_sha256"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
