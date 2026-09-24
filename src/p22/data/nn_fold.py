"""NN v2 fold preprocessing (N2).

``prepare_nn_fold`` fits every preprocessing statistic (HVG, scalers, ATAC IDF)
on the training rows only and asserts the donors behind each fit are a subset of
the training donors, so a holdout value cannot influence a fitted transform.
Split out of :mod:`p22.data.nn_inputs` to keep each module under the size cap.

Assumptions: A7 (RNA ``log1p(1e4 * raw / cell_total)``, HVG top 2000 train-only),
A8 (ATAC TF-IDF ``log1p(tf * idf)``, train-only IDF), A10 (QC and nuisance
fields).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import sparse

from p22.data.nn_inputs import (
    LABEL_DISEASE,
    N_HVG_DEFAULT,
    N_MEAN_BINS,
    NUISANCE_CATEGORICAL,
    QC_LOG_COLUMNS,
    QC_RAW_COLUMNS,
    FoldArrays,
    NNInputs,
)


def _rna_lognorm(rna: sparse.csr_matrix, totals: np.ndarray) -> sparse.csr_matrix:
    """A7: ``log1p(1e4 * raw / cell_total)`` over all genes."""
    out = rna.astype(np.float64).tocsr()
    safe = np.where(totals > 0, totals, 1.0)
    row = np.repeat(np.arange(out.shape[0]), np.diff(out.indptr))
    out.data = np.log1p(out.data * (1e4 / safe[row]))
    return out.astype(np.float32).tocsr()


def _hvg_indices(train_norm: sparse.csr_matrix, n_hvg: int) -> np.ndarray:
    """Dispersion (var/mean) ranked within 20 mean bins, top ``n_hvg`` columns."""
    n_genes = train_norm.shape[1]
    mean = np.asarray(train_norm.mean(axis=0)).ravel().astype(np.float64)
    sq = np.asarray(train_norm.multiply(train_norm).mean(axis=0)).ravel().astype(np.float64)
    var = np.maximum(sq - mean * mean, 0.0)
    disp = np.divide(var, mean, out=np.zeros_like(var), where=mean > 0)
    order = np.argsort(mean, kind="stable")
    ranks = np.empty(n_genes, dtype=np.int64)
    ranks[order] = np.arange(n_genes)
    bins = np.minimum((ranks * N_MEAN_BINS) // max(n_genes, 1), N_MEAN_BINS - 1)
    z = np.zeros(n_genes, dtype=np.float64)
    for b in range(N_MEAN_BINS):
        mask = bins == b
        if int(mask.sum()) > 1:
            values = disp[mask]
            std = values.std()
            z[mask] = (values - values.mean()) / std if std > 0 else 0.0
    take = min(int(n_hvg), n_genes)
    return np.sort(np.argsort(-z, kind="stable")[:take])


def _atac_tfidf(
    atac: sparse.csr_matrix, train_position: np.ndarray
) -> tuple[sparse.csr_matrix, np.ndarray]:
    """A8: ``log1p(tf * idf)`` with train-only IDF; tf over the panel total."""
    counts = atac.astype(np.float64).tocsr()
    panel_total = np.asarray(counts.sum(axis=1)).ravel()
    panel_total[panel_total == 0] = 1.0
    row = np.repeat(np.arange(counts.shape[0]), np.diff(counts.indptr))
    tf = counts.copy()
    tf.data = counts.data / panel_total[row]
    df = np.asarray((counts[train_position] > 0).sum(axis=0)).ravel().astype(np.float64)
    n_train = int(train_position.sum())
    idf = np.log((1.0 + n_train) / (1.0 + df)) + 1.0
    out = tf.multiply(idf).tocsr()
    out.data = np.log1p(out.data)
    return out.astype(np.float32).tocsr(), idf


def _qc_matrix(metadata: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    frame = metadata[list(columns)].astype(np.float64).copy()
    for column in QC_LOG_COLUMNS:
        if column in frame:
            frame[column] = np.log1p(frame[column].to_numpy())
    values = frame.to_numpy(dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("QC matrix contains non-finite values")
    return values


def _array_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values, dtype=np.float64).tobytes()).hexdigest()


def prepare_nn_fold(
    inputs: NNInputs,
    train_rows: np.ndarray,
    holdout_rows: np.ndarray,
    region_rows: np.ndarray,
    *,
    n_hvg: int = N_HVG_DEFAULT,
    exclude_chr21: bool = False,
) -> FoldArrays:
    """Fit all preprocessing on train rows and return dense fold tensors.

    ``region_rows`` are row positions into ``inputs.regions`` (use
    :func:`p22.data.nn_inputs.region_indices` to map the fold's region ids).
    """
    from sklearn.preprocessing import StandardScaler

    train_rows = np.asarray(train_rows, dtype=np.int64)
    holdout_rows = np.asarray(holdout_rows, dtype=np.int64)
    region_rows = np.asarray(region_rows, dtype=np.int64)
    rows = np.concatenate([train_rows, holdout_rows])
    train_position = np.zeros(rows.size, dtype=bool)
    train_position[: train_rows.size] = True

    gene_keep = np.ones(inputs.gene_ids.size, dtype=bool)
    if exclude_chr21:
        gene_keep &= ~inputs.chr21_gene_mask()
        region_rows = region_rows[~inputs.chr21_region_mask()[region_rows]]

    train_donors = set(inputs.metadata["donor_id"].iloc[train_rows].astype(str))
    holdout_donors = set(inputs.metadata["donor_id"].iloc[holdout_rows].astype(str))
    if train_donors & holdout_donors:
        raise ValueError("train and holdout rows share a donor; fold is not donor-held-out")

    rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, gene_keep]
    hvg = _hvg_indices(rna_norm[train_position], n_hvg)
    selected_cols = np.flatnonzero(gene_keep)[hvg]
    rna_dense = np.asarray(rna_norm[:, selected_cols].todense(), dtype=np.float32)
    rna_scaler = StandardScaler().fit(rna_dense[train_position])
    rna = rna_scaler.transform(rna_dense).astype(np.float32)

    atac_raw = inputs.atac[:, region_rows]
    atac_tfidf, idf = _atac_tfidf(atac_raw, train_position)
    atac_dense = np.asarray(atac_tfidf.todense(), dtype=np.float32)
    atac_scaler = StandardScaler().fit(atac_dense[train_position])
    atac = atac_scaler.transform(atac_dense).astype(np.float32)

    qc_raw = _qc_matrix(inputs.metadata.iloc[rows], QC_RAW_COLUMNS)
    qc_scaler = StandardScaler().fit(qc_raw[train_position])
    qc = qc_scaler.transform(qc_raw).astype(np.float32)

    nuisance_codes = {
        column: pd.factorize(inputs.metadata[column].iloc[rows].astype(str))[0].astype(np.int64)
        for column in NUISANCE_CATEGORICAL
    }
    label = (inputs.metadata["disease"].iloc[rows].astype(str) == LABEL_DISEASE).to_numpy(np.int64)
    donor = inputs.metadata["donor_id"].iloc[rows].astype(str).to_numpy()

    fit_donors = sorted(train_donors)
    if not set(fit_donors) <= train_donors:
        raise AssertionError("a fitted transform saw a non-training donor")
    if set(donor[train_position]) != train_donors:
        raise AssertionError("train rows do not match the recorded training donors")

    evidence = {
        "n_train_rows": int(train_rows.size),
        "n_holdout_rows": int(holdout_rows.size),
        "n_hvg": int(selected_cols.size),
        "n_regions": int(region_rows.size),
        "exclude_chr21": bool(exclude_chr21),
        "fit_donors": fit_donors,
        "holdout_donors": sorted(holdout_donors),
        "idf_sha256": _array_sha256(idf),
        "qc_columns": list(QC_RAW_COLUMNS),
        "nuisance_categorical": list(NUISANCE_CATEGORICAL),
    }
    return FoldArrays(
        rna=rna,
        atac=atac,
        qc=qc,
        label=label,
        donor=donor,
        nuisance_codes=nuisance_codes,
        train_position=train_position,
        gene_ids=inputs.gene_ids[selected_cols],
        region_ids=tuple(inputs.regions[i] for i in region_rows),
        evidence=evidence,
    )
