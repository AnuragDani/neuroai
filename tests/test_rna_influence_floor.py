"""Count-driven diagnostic support changes; synthetic donors, never real evidence."""

import json

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from p22.data.real_cohort import DonorPseudobulk
from p22.eval.external_validation import fit_discovery_effects
from p22.eval.rna_donor_influence import omission_rows, prepare_baselines
from tests.test_external_validation import _discovery_fixture


def floor_fixture():
    counts, metadata, genes = _discovery_fixture(650)
    metadata = pd.concat([metadata, metadata.iloc[[12]].rename(index={"donor12": "donor24"})])
    counts = np.vstack([counts, counts[12]])
    # LOSS is expressed in six of twelve controls; NEW in six of thirteen cases.
    loss = np.zeros(25, dtype=int)
    loss[:6] = loss[12:] = 10_000
    new = np.zeros(25, dtype=int)
    new[:12] = new[12:18] = 10_000
    # Excluded from the endpoint, but this large gene must stay in library totals.
    dosage = 1_000_000 + 100_000 * np.arange(25)
    counts = np.column_stack([counts, loss, new, dosage])
    genes = pd.concat(
        [
            genes,
            pd.DataFrame(
                {"gene_name": ["LOSS", "NEW", "DOSAGE"], "seqnames": ["chr1", "chr1", "chr21"]}
            ),
        ],
        ignore_index=True,
    )
    bulk = DonorPseudobulk(
        donor_ids=tuple(metadata.index),
        conditions=tuple(metadata.disease),
        labels=metadata.label.to_numpy(),
        n_cells=np.full(25, 50),
        total_counts=counts.sum(axis=1),
        gene_sums=counts,
        chr21_fraction=None,
        gene_ids=tuple(genes.index.astype(str)),
        chr21_mapping=None,
    )
    external = {
        "oRG": pd.DataFrame(
            {"gene": genes.gene_name, "avg_log2FC": np.linspace(-0.8, 0.8, len(genes))}
        )
    }
    return bulk, metadata, genes, external


def test_baseline_uses_excluded_genes_in_library_denominator():
    bulk, metadata, genes, external = floor_fixture()
    fitted, tables = prepare_baselines(bulk, metadata, genes, external)
    assert len(tables["oRG"]) == 651
    assert "LOSS" in set(tables["oRG"].gene)
    assert {"NEW", "DOSAGE"}.isdisjoint(tables["oRG"].gene)
    selected = pd.Index(genes.gene_name).get_indexer(fitted.effects.gene)
    expected = np.log1p(bulk.gene_sums / bulk.total_counts[:, None] * 1e6)[:, selected]
    np.testing.assert_allclose(fitted.log_cpm, expected, rtol=0, atol=1e-12)
    wrong = np.log1p(
        bulk.gene_sums[:, selected] / bulk.gene_sums[:, selected].sum(axis=1)[:, None] * 1e6
    )
    assert np.max(np.abs(expected - wrong)) > 1.0


@pytest.mark.parametrize(
    ("donor", "lost", "new", "shared"),
    [("donor00", ["LOSS"], [], 650), ("donor24", [], ["NEW"], 651)],
)
def test_omission_reapplies_floor_without_renormalizing_selected_genes(donor, lost, new, shared):
    bulk, metadata, genes, external = floor_fixture()
    _, baselines = prepare_baselines(bulk, metadata, genes, external)
    actual = next(
        row
        for row in omission_rows(bulk, metadata, genes, external, baselines)
        if row["omitted_donor"] == donor
    )
    assert actual["status"] == "AVAILABLE"
    assert actual["n_shared_genes"] == shared
    assert json.loads(actual["lost_genes"]) == lost
    assert json.loads(actual["new_genes"]) == new
    assert actual["n_lost_genes"] == len(lost) and actual["n_new_genes"] == len(new)

    keep = metadata.index != donor
    # Independently refit original full-gene counts, not baseline-eligible columns.
    fitted = fit_discovery_effects(
        bulk.gene_sums[keep], metadata.loc[keep], genes, n_cells=bulk.n_cells[keep]
    )
    selected = pd.Index(genes.gene_name).get_indexer(fitted.effects.gene)
    expected_log = np.log1p(bulk.gene_sums[keep] / bulk.total_counts[keep, None] * 1e6)
    np.testing.assert_allclose(fitted.log_cpm, expected_log[:, selected], rtol=0, atol=1e-12)
    baseline = baselines["oRG"].set_index("gene")
    omission = fitted.effects.set_index("gene")
    gi = baseline.index.intersection(omission.index).sort_values()
    rho0 = spearmanr(baseline.coefficient, baseline.avg_log2FC).statistic
    rho0_gi = spearmanr(baseline.loc[gi].coefficient, baseline.loc[gi].avg_log2FC).statistic
    rho_i = spearmanr(omission.loc[gi].coefficient, baseline.loc[gi].avg_log2FC).statistic
    assert actual["rho_loo"] == pytest.approx(rho_i, abs=1e-12, rel=0)
    assert actual["same_support_delta"] == pytest.approx(rho_i - rho0_gi, abs=1e-12, rel=0)
    assert actual["support_delta"] == pytest.approx(rho0_gi - rho0, abs=1e-12, rel=0)
    assert actual["total_delta"] == pytest.approx(rho_i - rho0, abs=1e-12, rel=0)

    wrong_fit = fit_discovery_effects(
        bulk.gene_sums[keep, :-1], metadata.loc[keep], genes.iloc[:-1], n_cells=bulk.n_cells[keep]
    )
    wrong_coefficient = wrong_fit.effects.set_index("gene").loc[gi].coefficient
    wrong_rho = spearmanr(wrong_coefficient, baseline.loc[gi].avg_log2FC).statistic
    assert abs(wrong_rho - rho_i) > 1e-5
