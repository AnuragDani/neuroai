"""Frozen marker panels and held-out donor association tests (G8).

The panels below are module constants, so they are fixed before any result is
seen. Two panels are declared on purpose: a chromosome-21 dosage panel that
should move up in trisomy 21, and an off-chromosome-21 housekeeping panel that
should not. A panel that moves in both directions is a specificity failure, not
a finding.

An association measured inside this cohort is internal held-out evidence. It is
not external validation, and this module never labels it as such.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

CHR21_DOSAGE_PANEL_NAME = "HSA21 dosage-sensitive cortical panel v1"
CHR21_DOSAGE_PANEL = (
    "APP",
    "DYRK1A",
    "SOD1",
    "RCAN1",
    "S100B",
    "TTC3",
    "SYNJ1",
    "ITSN1",
    "BACE2",
    "PCP4",
    "ETS2",
    "RUNX1",
    "OLIG1",
    "OLIG2",
    "CSTB",
    "HMGN1",
    "NCAM2",
    "COL6A1",
    "CBS",
    "ADAMTS1",
)

CONTROL_PANEL_NAME = "off-chromosome-21 housekeeping control panel v1"
CONTROL_PANEL = ("ACTB", "GAPDH", "B2M", "TUBB", "RPL13A", "PPIA", "TBP", "PGK1")

GEO_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


@dataclass(frozen=True)
class PanelResult:
    """Donor-level association of one panel inside held-out donors."""

    panel: str
    expectation: str
    status: str
    n_genes_requested: int
    n_genes_found: int
    n_donors: int
    median_log2_fold_change: float | None = None
    n_genes_up_in_ds: int | None = None
    fraction_up_in_ds: float | None = None
    panel_p_value: float | None = None
    genes_found: tuple[str, ...] = ()
    genes_missing: tuple[str, ...] = ()
    per_gene: list[dict[str, Any]] = field(default_factory=list)
    not_applicable: str | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "panel": self.panel,
            "expectation": self.expectation,
            "status": self.status,
            "n_genes_requested": self.n_genes_requested,
            "n_genes_found": self.n_genes_found,
            "n_donors": self.n_donors,
            "median_log2_fold_change": self.median_log2_fold_change,
            "n_genes_up_in_ds": self.n_genes_up_in_ds,
            "fraction_up_in_ds": self.fraction_up_in_ds,
            "panel_p_value": self.panel_p_value,
            "genes_missing": list(self.genes_missing),
            "not_applicable": self.not_applicable,
            "evidence_scope": "internal held-out donors; not external validation",
        }


def evaluate_panel(
    panel_name: str,
    symbols: tuple[str, ...],
    expectation: str,
    log_cpm: np.ndarray,
    gene_symbols: pd.Series,
    labels: np.ndarray,
    donor_ids: tuple[str, ...],
    held_out_donors: set[str],
) -> PanelResult:
    """Compare donor-level expression of a fixed panel between conditions.

    Args:
        panel_name: frozen panel name.
        symbols: gene symbols in the panel, locked before any lookup.
        expectation: the declared direction, for reporting.
        log_cpm: donor-by-gene log counts-per-million.
        gene_symbols: gene symbol per column of ``log_cpm``.
        labels: donor labels, 1 for trisomy 21.
        donor_ids: donor identifier per row of ``log_cpm``.
        held_out_donors: donors that were never used to derive the panel.
    """
    keep = np.array([donor in held_out_donors for donor in donor_ids], dtype=bool)
    n_donors = int(keep.sum())
    upper = gene_symbols.astype(str).str.upper()
    if n_donors < 4 or np.unique(labels[keep]).size < 2:
        return PanelResult(
            panel=panel_name,
            expectation=expectation,
            status="NOT_APPLICABLE",
            n_genes_requested=len(symbols),
            n_genes_found=0,
            n_donors=n_donors,
            not_applicable="need at least four held-out donors covering both conditions",
        )

    subset = log_cpm[keep]
    y = labels[keep]
    per_gene: list[dict[str, Any]] = []
    found: list[str] = []
    missing: list[str] = []
    for symbol in symbols:
        columns = np.flatnonzero((upper == symbol.upper()).to_numpy())
        if columns.size == 0:
            missing.append(symbol)
            continue
        values = subset[:, columns].mean(axis=1)
        control_mean = float(values[y == 0].mean())
        case_mean = float(values[y == 1].mean())
        try:
            statistic = stats.mannwhitneyu(values[y == 1], values[y == 0], alternative="two-sided")
            p_value: float | None = float(statistic.pvalue)
        except ValueError:
            p_value = None
        found.append(symbol)
        fold_change = float(np.log2((np.expm1(case_mean) + 1e-6) / (np.expm1(control_mean) + 1e-6)))
        per_gene.append(
            {
                "gene": symbol,
                "control_mean_log_cpm": control_mean,
                "ds_mean_log_cpm": case_mean,
                "log2_fold_change": fold_change,
                "p_value": p_value,
            }
        )

    if not per_gene:
        return PanelResult(
            panel=panel_name,
            expectation=expectation,
            status="NOT_APPLICABLE",
            n_genes_requested=len(symbols),
            n_genes_found=0,
            n_donors=n_donors,
            genes_missing=tuple(missing),
            not_applicable="no panel gene present in the feature space",
        )

    changes = np.asarray([row["log2_fold_change"] for row in per_gene], dtype=float)
    n_up = int((changes > 0).sum())
    try:
        panel_p: float | None = float(stats.wilcoxon(changes).pvalue) if changes.size > 5 else None
    except ValueError:
        panel_p = None
    return PanelResult(
        panel=panel_name,
        expectation=expectation,
        status="measured",
        n_genes_requested=len(symbols),
        n_genes_found=len(per_gene),
        n_donors=n_donors,
        median_log2_fold_change=float(np.median(changes)),
        n_genes_up_in_ds=n_up,
        fraction_up_in_ds=float(n_up / changes.size),
        panel_p_value=panel_p,
        genes_found=tuple(found),
        genes_missing=tuple(missing),
        per_gene=per_gene,
    )


def check_geo_accession(accession: str, timeout: float = 20.0) -> dict[str, Any]:
    """Ask GEO whether an accession exists. Metadata only; nothing is downloaded."""
    query = urllib.parse.urlencode(
        {"db": "gds", "term": f"{accession}[Accession]", "retmode": "json"}
    )
    try:
        with urllib.request.urlopen(f"{GEO_ESEARCH}?{query}", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        count = int(payload.get("esearchresult", {}).get("count", 0))
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        return {
            "accession": accession,
            "listed": None,
            "matrix_ingested": False,
            "reason": f"GEO lookup failed: {error}",
        }
    return {
        "accession": accession,
        "listed": count > 0,
        "matrix_ingested": False,
        "reason": (
            "accession is listed in GEO; no expression matrix was downloaded or "
            "harmonised in this run"
            if count > 0
            else "accession not found in GEO"
        ),
    }
