"""NN v2 loader and fold-data contracts (N2).

The loader samples cells with the N1 donor x cell-type x library sampler, reads
RNA raw counts for the sampled rows, transposes the ATAC region x cell matrix to
cells x regions, and carries the gene/region tables plus chr21 masks.

Fold preprocessing (:func:`prepare_nn_fold`) lives in :mod:`p22.data.nn_fold`,
which fits every statistic (HVG, scalers, ATAC IDF) on training rows only; this
module re-exports it lazily to keep the documented import path.

Assumptions: A7 (RNA ``log1p(1e4 * raw / cell_total)``, HVG top 2000 train-only),
A8 (ATAC TF-IDF ``log1p(tf * idf)``, train-only IDF), A9 (gene windows from
``raw/var``), A10 (QC and nuisance fields).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from p22.data.nn_sampling import sample_donor_stratified_cells
from p22.data.real_cohort import (
    DEFAULT_RNA_MATRIX_KEY,
    load_cell_matrix,
    read_matrix_axis,
)

OBS_COLUMNS = (
    "donor_id",
    "disease",
    "author_cell_type",
    "cell_class",
    "library",
    "batch_seq",
    "sex",
    "dev_PCW",
    "nCount_RNA",
    "nCount_ATAC",
    "TSS.enrichment",
    "percent.mt",
    "nucleosome_signal",
)
LABEL_DISEASE = "complete trisomy 21"
QC_RAW_COLUMNS = (
    "nCount_RNA",
    "nCount_ATAC",
    "TSS.enrichment",
    "percent.mt",
    "nucleosome_signal",
)
QC_LOG_COLUMNS = ("nCount_RNA", "nCount_ATAC")
NUISANCE_CATEGORICAL = ("library", "batch_seq")
N_HVG_DEFAULT = 2000
N_MEAN_BINS = 20


def _as_text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _decode_categorical(group: Any, name: str) -> np.ndarray:
    """Decode an AnnData categorical or string dataset into object strings."""
    import h5py

    dataset = group[name]
    if isinstance(dataset, h5py.Group):
        categories = np.asarray(dataset["categories"][:])
        codes = np.asarray(dataset["codes"][:])
        return np.asarray([_as_text(value) for value in categories[codes]], dtype=object)
    return np.asarray([_as_text(value) for value in np.asarray(dataset[:])], dtype=object)


@dataclass
class NNInputs:
    """Sampled cells with aligned RNA, ATAC, gene and region tables."""

    metadata: pd.DataFrame
    rna: sparse.csr_matrix
    rna_totals: np.ndarray
    gene_ids: np.ndarray
    gene_names: np.ndarray
    gene_chrom: np.ndarray
    gene_start: np.ndarray
    gene_end: np.ndarray
    atac: sparse.csr_matrix
    regions: tuple[str, ...]
    region_index: dict[str, int]
    region_chrom: np.ndarray

    def gene_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "gene_id": self.gene_ids,
                "gene_name": self.gene_names,
                "chrom": self.gene_chrom,
                "start": self.gene_start,
                "end": self.gene_end,
            }
        )

    def region_table(self) -> pd.DataFrame:
        return pd.DataFrame({"region_id": list(self.regions), "chrom": self.region_chrom})

    def chr21_gene_mask(self) -> np.ndarray:
        return self.gene_chrom == "chr21"

    def chr21_region_mask(self) -> np.ndarray:
        return self.region_chrom == "chr21"


@dataclass
class FoldArrays:
    """Dense float32 fold tensors plus fit evidence."""

    rna: np.ndarray
    atac: np.ndarray
    qc: np.ndarray
    label: np.ndarray
    donor: np.ndarray
    nuisance_codes: dict[str, np.ndarray]
    train_position: np.ndarray
    gene_ids: np.ndarray
    region_ids: tuple[str, ...]
    evidence: dict[str, Any]


def read_gene_table(
    h5ad: str | Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read ``raw/var`` gene id, name, chrom, start, end in matrix column order."""
    import h5py

    axis = read_matrix_axis(h5ad, DEFAULT_RNA_MATRIX_KEY)
    with h5py.File(Path(h5ad), "r") as handle:
        var = handle["raw/var"]
        names = _decode_categorical(var, "gene_name")
        chrom = _decode_categorical(var, "seqnames")
        start = np.asarray(var["start"][:], dtype=np.int64)
        end = np.asarray(var["end"][:], dtype=np.int64)
    ids = np.asarray(axis["gene_ids"], dtype=object)
    if not (len(ids) == len(names) == len(chrom) == len(start) == len(end)):
        raise ValueError("raw/var columns are not aligned with the raw/X gene axis")
    return ids, names, chrom, start, end


def read_raw_row_totals(h5ad: str | Path, rows: np.ndarray) -> np.ndarray:
    """Per-cell raw count totals over **all** genes for the given rows."""
    import h5py

    rows = np.sort(np.asarray(rows, dtype=np.int64))
    with h5py.File(Path(h5ad), "r") as handle:
        group = handle[DEFAULT_RNA_MATRIX_KEY]
        indptr = np.asarray(group["indptr"][:])
        data = group["data"]
        totals = np.empty(rows.size, dtype=np.float64)
        for i, row in enumerate(rows):
            totals[i] = float(np.asarray(data[indptr[row] : indptr[row + 1]]).sum())
    return totals


def _read_regions(union_bed: str | Path) -> tuple[tuple[str, ...], np.ndarray]:
    regions: list[str] = []
    chrom: list[str] = []
    for line in Path(union_bed).read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        chrom.append(fields[0])
        regions.append(f"{fields[0]}:{fields[1]}-{fields[2]}")
    return tuple(regions), np.asarray(chrom, dtype=object)


def load_nn_inputs(
    h5ad: str | Path,
    atac_npz: str | Path,
    cap: int,
    seed: int,
    *,
    union_bed: str | Path,
) -> NNInputs:
    """Load sampled cells with aligned RNA counts, ATAC counts and tables."""
    import anndata as ad

    backed = ad.read_h5ad(h5ad, backed="r")
    try:
        obs = backed.obs[list(OBS_COLUMNS)].copy()
        n_cells = int(backed.n_obs)
    finally:
        backed.file.close()
    obs.index = obs.index.astype(str)
    text_columns = (
        "donor_id",
        "disease",
        "author_cell_type",
        "cell_class",
        "library",
        "batch_seq",
        "sex",
    )
    for column in text_columns:
        obs[column] = obs[column].astype(str)
    if obs.index.duplicated().any():
        raise ValueError("obs cell identifiers are not unique")

    rows = sample_donor_stratified_cells(obs, cap=cap, seed=seed)
    metadata = obs.iloc[rows].copy()

    rna = load_cell_matrix(h5ad, rows, matrix_key=DEFAULT_RNA_MATRIX_KEY)
    rna_totals = read_raw_row_totals(h5ad, rows)
    gene_ids, gene_names, gene_chrom, gene_start, gene_end = read_gene_table(h5ad)

    atac_matrix = sparse.load_npz(atac_npz)
    if atac_matrix.shape[1] != n_cells:
        raise ValueError(
            f"ATAC matrix has {atac_matrix.shape[1]} cells but H5AD has {n_cells}"
        )
    atac = atac_matrix.tocsc()[:, rows].T.tocsr()

    regions, region_chrom = _read_regions(union_bed)
    if len(regions) != atac_matrix.shape[0]:
        raise ValueError(
            f"union BED has {len(regions)} regions but ATAC matrix has {atac_matrix.shape[0]}"
        )
    region_index = {region: i for i, region in enumerate(regions)}
    return NNInputs(
        metadata=metadata,
        rna=rna,
        rna_totals=rna_totals,
        gene_ids=gene_ids,
        gene_names=gene_names,
        gene_chrom=gene_chrom,
        gene_start=gene_start,
        gene_end=gene_end,
        atac=atac,
        regions=regions,
        region_index=region_index,
        region_chrom=region_chrom,
    )


def region_indices(inputs: NNInputs, region_ids: Sequence[str]) -> np.ndarray:
    """Map fold region ids to their row positions in ``inputs.regions``."""
    missing = [region for region in region_ids if region not in inputs.region_index]
    if missing:
        raise KeyError(f"{len(missing)} fold regions absent from the union, e.g. {missing[:3]}")
    return np.asarray([inputs.region_index[region] for region in region_ids], dtype=np.int64)


def __getattr__(name: str) -> Any:
    """Lazily expose :func:`prepare_nn_fold` from :mod:`p22.data.nn_fold`.

    The preprocessing half lives in ``nn_fold`` (which imports this module), so
    the re-export is deferred to avoid an import cycle.
    """
    if name == "prepare_nn_fold":
        from p22.data.nn_fold import prepare_nn_fold

        return prepare_nn_fold
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
