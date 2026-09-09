"""Frozen RNA-effect replication contract; fixtures contain no biological evidence."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from p22.data.real_cohort import CONTROL_CONDITION, POSITIVE_CONDITION, DonorPseudobulk
from p22.eval.external_validation import (
    COMPARISONS,
    SHEETS,
    _comparison_outcome,
    _metrics,
    collapse_donor_metadata,
    compare_effect_directions,
    fit_discovery_effects,
    gene_eligibility,
    load_external_effects,
    summarize_headline_outcome,
)


def _genes():
    return pd.DataFrame(
        {
            "gene_name": [" a ", "dup", " DUP ", "XG", "YG", "MT-CO1", "UNK", "ALT", "APP"],
            "seqnames": ["chr1", "chr2", "chr2", "chrX", "chrY", "chr1", None, "KI270", "chr21"],
        }
    )


def _workbook(
    path, *, celltype_error=False, orientation=-1, missing_column=False, omit_sheet=False
):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, celltype in SHEETS.items():
            if omit_sheet and sheet == "IP":
                continue
            table = pd.DataFrame(
                {
                    "gene": ["a", "APP", " b ", "B"],
                    "avg_log2FC": [0.3, orientation * 0.5, 0.1, 0.2],
                    "p_val": [0.1] * 4,
                    "p_val_adj": [0.2] * 4,
                    "pct.1": [0.3] * 4,
                    "pct.2": [0.3] * 4,
                    "celltype": ["wrong" if celltype_error else celltype] * 4,
                    "FDR": [0.2] * 4,
                    "sig": [False] * 4,
                }
            )
            if missing_column:
                table = table.drop(columns="p_val")
            table.to_excel(writer, sheet_name=sheet, index=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_workbook_hash_schema_orientation_and_duplicate_drop(tmp_path):
    path = tmp_path / "effects.xlsx"
    digest = _workbook(path, orientation=1)
    loaded = load_external_effects(path, gene_metadata=_genes(), expected_sha256=digest)
    assert tuple(loaded) == ("oRG", "vRG", "CP", "IP")
    assert loaded["CP"]["gene"].tolist() == ["A", "APP"]
    assert loaded["CP"].attrs["dropped_duplicate_external"] == 2
    assert loaded["CP"].attrs["external_sha256"] == digest
    with pytest.raises(ValueError, match="hash"):
        load_external_effects(path, gene_metadata=_genes(), expected_sha256="0" * 64)
    for options, reason in [
        ({"orientation": -1}, "external orientation check failed"),
        ({"orientation": 1, "celltype_error": True}, "celltype"),
        ({"orientation": 1, "missing_column": True}, "schema"),
        ({"orientation": 1, "omit_sheet": True}, "sheet"),
    ]:
        digest = _workbook(path, **options)
        with pytest.raises(ValueError, match=reason):
            load_external_effects(path, gene_metadata=_genes(), expected_sha256=digest)


def test_exclusions_normalize_symbols_and_drop_every_duplicate():
    frame, audit = gene_eligibility(_genes())
    assert frame.loc[frame["eligible"], "gene"].tolist() == ["A"]
    assert audit["dropped_duplicate_primary"] == 2
    assert audit["excluded_chromosome_or_mito"] == 6
    assert COMPARISONS[2] == ("cycling_progenitors", ("RG_prol", "IPC_prol"), "CP")


def test_donor_metadata_requires_invariance_and_explicit_classes():
    obs = pd.DataFrame(
        {
            "donor_id": ["b", "b", "a", "a"],
            "disease": [POSITIVE_CONDITION] * 2 + [CONTROL_CONDITION] * 2,
            "dev_PCW": [13, 13, 14, 14],
            "sex": ["male", "male", "female", "female"],
        }
    )
    result = collapse_donor_metadata(obs, donor_ids=("a", "b"))
    assert result.index.tolist() == ["a", "b"]
    assert result["label"].tolist() == [0, 1]
    for column, value in [("disease", CONTROL_CONDITION), ("dev_PCW", 15), ("sex", "female")]:
        bad = obs.copy()
        bad.loc[0, column] = value
        with pytest.raises(ValueError, match="invariant"):
            collapse_donor_metadata(bad)
    bad = obs.copy()
    bad["disease"] = "unknown"
    with pytest.raises(ValueError, match="condition"):
        collapse_donor_metadata(bad)


def _discovery_fixture(n_genes=650):
    rng = np.random.default_rng(9)
    labels = np.repeat([0, 1], 12)
    metadata = collapse_donor_metadata(
        pd.DataFrame(
            {
                "donor_id": [f"donor{i:02}" for i in range(24)],
                "disease": np.where(labels, POSITIVE_CONDITION, CONTROL_CONDITION),
                "dev_PCW": np.tile([13, 14, 15, 16, 17, 18], 4),
                "sex": np.tile(["male", "female", "female", "male"], 6),
            }
        )
    )
    effects = np.linspace(-0.8, 0.8, n_genes)
    counts = rng.poisson(100 * np.exp(labels[:, None] * effects[None, :]))
    genes = pd.DataFrame(
        {
            "gene_name": [f"GENE{i:04}" for i in range(n_genes)],
            "seqnames": ["chr1"] * n_genes,
        }
    )
    return counts, metadata, genes


def test_ols_matches_direct_fit_and_floor_precedes_ranking():
    counts, metadata, genes = _discovery_fixture()
    counts[:, 0] = 0
    counts[0, 0] = 1
    counts[12:, 0] = 1000  # A large apparent effect still fails the control-class floor.
    fitted = fit_discovery_effects(counts, metadata, genes, n_cells=np.full(24, 50))
    assert "GENE0000" not in set(fitted.effects.gene)
    assert fitted.audit["n_expression_eligible"] == 649
    expected = np.linalg.lstsq(fitted.design, fitted.log_cpm, rcond=None)[0][1]
    np.testing.assert_allclose(fitted.effects.coefficient, expected, atol=1e-12)
    assert np.sign(fitted.effects.iloc[-1].coefficient) == 1
    assert set(fitted.effects.columns) >= {"gene", "coefficient", "standard_error", "t_statistic"}
    assert fitted.audit["design_rank"] == 4
    assert fitted.audit["residual_df"] == 20


def test_pseudobulk_path_verifies_identifiers_conditions_and_uses_existing_log_cpm():
    from dataclasses import replace

    counts, metadata, genes = _discovery_fixture()
    bulk = DonorPseudobulk(
        donor_ids=tuple(metadata.index),
        conditions=tuple(metadata.disease),
        labels=metadata.label.to_numpy(),
        n_cells=np.full(24, 50),
        total_counts=counts.sum(axis=1),
        gene_sums=counts,
        chr21_fraction=None,
        gene_ids=tuple(genes.index.astype(str)),
        chr21_mapping=None,
    )
    fit = fit_discovery_effects(bulk, metadata, genes)
    np.testing.assert_array_equal(fit.log_cpm, bulk.log_cpm())
    for bad in (
        replace(bulk, donor_ids=tuple(reversed(bulk.donor_ids))),
        replace(bulk, gene_ids=tuple(reversed(bulk.gene_ids))),
        replace(bulk, conditions=(CONTROL_CONDITION,) * 24),
    ):
        with pytest.raises(ValueError, match="mismatch"):
            fit_discovery_effects(bad, metadata, genes)


@pytest.mark.parametrize("failure", ["rank", "class", "cell_floor", "negative", "empty_donor"])
def test_discovery_fail_closed(failure):
    counts, metadata, genes = _discovery_fixture()
    cells = np.full(24, 50)
    if failure == "rank":
        metadata["sex"] = "male"
    elif failure == "class":
        metadata["label"] = 0
        metadata["disease"] = CONTROL_CONDITION
    elif failure == "cell_floor":
        cells[0] = 49
    elif failure == "negative":
        counts[0, 0] = -1
    else:
        counts[0] = 0
    with pytest.raises(ValueError):
        fit_discovery_effects(counts, metadata, genes, n_cells=cells)


def test_metrics_rank_by_absolute_t_not_effect_magnitude():
    coefficient = np.array([10.0, -0.1, 0.2, -3.0])
    statistic = np.array([0.1, -10.0, 9.0, -0.2])
    external = np.array([-10.0, -2.0, 1.0, 3.0])
    rho, agreement, selected = _metrics(coefficient, statistic, external, 2)
    assert selected.tolist() == [1, 2]
    assert agreement == 1.0
    # Ranks (4, 2, 3, 1) versus (1, 2, 3, 4): 1 - 6*18/(4*15).
    assert rho == pytest.approx(-0.8)


def test_bootstrap_refits_reranks_and_permutation_is_reproducible():
    from scipy.stats import spearmanr

    counts, metadata, genes = _discovery_fixture()
    fit = fit_discovery_effects(counts, metadata, genes, n_cells=np.full(24, 50))
    external = pd.DataFrame({"gene": fit.effects.gene, "avg_log2FC": np.linspace(-0.6, 0.8, 650)})
    args = dict(n_bootstrap=40, n_permutations=100, top_n=20, seed=22)
    first = compare_effect_directions(fit, external, **args)
    second = compare_effect_directions(fit, external, **args)
    for key in (
        "spearman_ci_low",
        "spearman_ci_high",
        "agreement_ci_low",
        "agreement_ci_high",
        "agreement_permutation_p_upper",
        "agreement_permutation_p_lower",
    ):
        assert first[key] == pytest.approx(second[key], abs=1e-12)
    assert first["execution_status"] == "completed"
    assert first["n_shared_genes"] == 650
    assert first["bootstrap_reranked_top_set_changes"] > 0
    assert first["bootstrap_failed"] <= 2
    _, permutation_seed = np.random.SeedSequence(22).spawn(2)
    rng = np.random.default_rng(permutation_seed)
    joined = first["joined_effects"]
    _, observed, selected = _metrics(
        joined.coefficient.to_numpy(),
        joined.t_statistic.to_numpy(),
        joined.avg_log2FC.to_numpy(),
        20,
    )
    null = np.array(
        [
            np.mean(
                np.sign(joined.coefficient.to_numpy()[selected])
                == np.sign(rng.permutation(joined.avg_log2FC.to_numpy())[selected])
            )
            for _ in range(100)
        ]
    )
    assert first["agreement_permutation_p_upper"] == (1 + np.sum(null >= observed)) / 101
    assert first["agreement_permutation_p_lower"] == (1 + np.sum(null <= observed)) / 101
    # Independent small-fixture calculation checks every refit and the top-N reranking.
    boot_rng = np.random.default_rng(np.random.SeedSequence(22).spawn(2)[0])
    manual = []
    for _ in range(40):
        rows = np.concatenate(
            [boot_rng.choice(np.flatnonzero(fit.labels == label), 12) for label in (0, 1)]
        )
        x, y = fit.design[rows], fit.log_cpm[rows]
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        se = np.sqrt(np.sum((y - x @ beta) ** 2, axis=0) / 20 * np.linalg.inv(x.T @ x)[1, 1])
        top = np.argsort(-np.abs(beta[1] / se), kind="stable")[:20]
        manual.append(
            (
                spearmanr(beta[1], external.avg_log2FC).statistic,
                np.mean(np.sign(beta[1, top]) == np.sign(external.avg_log2FC.to_numpy()[top])),
            )
        )
    intervals = np.quantile(manual, [0.025, 0.975], axis=0)
    np.testing.assert_allclose(
        intervals,
        [
            [first["spearman_ci_low"], first["agreement_ci_low"]],
            [first["spearman_ci_high"], first["agreement_ci_high"]],
        ],
        atol=1e-12,
    )
    child = np.random.SeedSequence(22).spawn(1)[0]
    a = compare_effect_directions(fit, external, **{**args, "seed": child})
    b = compare_effect_directions(fit, external, **{**args, "seed": child})
    assert a["agreement_ci_low"] == b["agreement_ci_low"]


def test_shared_floor_after_filtering_and_failed_bootstrap_budget(monkeypatch):
    from p22.eval import external_validation as module

    counts, metadata, genes = _discovery_fixture()
    fit = fit_discovery_effects(counts, metadata, genes, n_cells=np.full(24, 50))
    external = pd.DataFrame({"gene": fit.effects.gene, "avg_log2FC": np.linspace(-1, 1, 650)})
    failed = compare_effect_directions(fit, external.iloc[:499], n_bootstrap=20, n_permutations=20)
    assert failed["execution_status"] == "failed"
    assert failed["scientific_outcome"] == "not_evaluated"
    assert "shared" in failed["reason"]

    original = module._fit_ols
    calls = 0

    def fail_two(log_cpm, design):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise ValueError("rank-deficient test replicate")
        return original(log_cpm, design)

    monkeypatch.setattr(module, "_fit_ols", fail_two)
    failed = compare_effect_directions(fit, external, n_bootstrap=20, n_permutations=20)
    assert failed["execution_status"] == "failed"
    assert failed["bootstrap_failed"] == 2
    assert "5%" in failed["reason"]
    calls = 1  # Exactly 1/20 failed fits is the allowed boundary.
    accepted = compare_effect_directions(fit, external, n_bootstrap=20, n_permutations=20)
    assert accepted["bootstrap_failed"] == 1
    assert accepted["execution_status"] == "completed"


def test_external_duplicates_are_dropped_before_shared_gene_count():
    counts, metadata, genes = _discovery_fixture(n_genes=500)
    fit = fit_discovery_effects(counts, metadata, genes, n_cells=np.full(24, 50))
    external = pd.DataFrame({"gene": fit.effects.gene, "avg_log2FC": np.linspace(-1, 1, 500)})
    external = pd.concat([external, external.iloc[[0]]], ignore_index=True)
    result = compare_effect_directions(fit, external, n_bootstrap=20, n_permutations=20)
    assert result["n_shared_genes"] == 499
    assert result["dropped_duplicate_external"] == 2
    assert result["execution_status"] == "failed"


def test_nominal_boundaries_and_four_comparison_headline():
    assert _comparison_outcome(0.01, 0.2, 0.025, 1.0) == "directionally_supported"
    assert _comparison_outcome(0.0, 0.2, 0.025, 1.0) == "inconclusive"
    assert _comparison_outcome(-0.2, -0.01, 1.0, 0.025) == "discordant"
    assert _comparison_outcome(-0.2, 0.0, 1.0, 0.025) == "inconclusive"
    rows = [{"scientific_outcome": "directionally_supported"}] * 3
    assert (
        summarize_headline_outcome(rows + [{"scientific_outcome": "inconclusive"}])
        == "directionally_supported"
    )
    assert (
        summarize_headline_outcome(rows + [{"scientific_outcome": "discordant"}]) == "inconclusive"
    )
    with pytest.raises(ValueError, match="four"):
        summarize_headline_outcome(rows)
