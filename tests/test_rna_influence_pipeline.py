"""Synthetic end-to-end wiring; fixture overrides never expose a production bypass."""

import copy
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest
from anndata.io import read_elem
from scipy.stats import spearmanr

from p22.data.census import sha256_file
from p22.data.real_cohort import donor_pseudobulk
from p22.eval import real_pipeline
from p22.eval import rna_donor_influence as diagnostic
from p22.eval.external_validation import (
    collapse_donor_metadata,
    fit_discovery_effects,
    load_external_effects,
)
from tests import test_external_pipeline

ROOT = Path(__file__).resolve().parents[1]
external_inputs = test_external_pipeline.inputs


@pytest.fixture
def diagnostic_inputs(external_inputs, tmp_path, monkeypatch):
    path, workbook, obs = external_inputs
    config = json.loads((ROOT / "configs/rna_donor_influence.json").read_text())
    with h5py.File(path, "r") as handle:
        genes = read_elem(handle["var"])
    external = load_external_effects(
        workbook, gene_metadata=genes, expected_sha256=sha256_file(workbook)
    )
    reference_rows, populations = [], {}
    for comparison in config["comparisons"]:
        population, sheet = comparison["population"], comparison["sheet"]
        if population not in populations:
            mask = obs.dev_PCW.between(13, 19) & obs.author_cell_type.isin(comparison["labels"])
            bulk = donor_pseudobulk(path, obs, mask.to_numpy())
            metadata = collapse_donor_metadata(obs.loc[mask], bulk.donor_ids)
            populations[population] = (bulk, fit_discovery_effects(bulk, metadata, genes))
        bulk, fitted = populations[population]
        joined = fitted.effects.merge(
            external[sheet][["gene", "avg_log2FC"]], on="gene", validate="one_to_one"
        ).sort_values("gene")
        rho = float(spearmanr(joined.coefficient, joined.avg_log2FC).statistic)
        comparison.update(
            rho=rho,
            shared_count=len(joined),
            expression_eligible_genes=fitted.audit["n_expression_eligible"],
            discovery_eligible_genes=fitted.audit["n_primary_eligible"],
            retained_cells=int(bulk.n_cells.sum()),
            min_cells_per_donor=int(bulk.n_cells.min()),
        )
        reference_rows.append(
            fitted.audit
            | {
                "analysis": "external_rna_direction_replication",
                "discovery_population": population,
                "primary_labels": "|".join(comparison["labels"]),
                "external_population": sheet,
                "spearman_rho": rho,
                "n_shared_genes": len(joined),
                "primary_cells": int(bulk.n_cells.sum()),
                "donor_ids": repr(list(bulk.donor_ids)),
                "external_sha256": sha256_file(workbook),
                "execution_status": "completed",
                "scientific_outcome": "inconclusive",
                "headline_outcome": "inconclusive",
            }
        )
    config["donors"].update(
        ordered_ids=list(bulk.donor_ids),
        ds_count=fitted.audit["n_ds_donors"],
        control_count=fitted.audit["n_control_donors"],
        baseline_design_rank=fitted.audit["design_rank"],
        baseline_residual_df=fitted.audit["residual_df"],
    )
    reference = tmp_path / "reference.csv"
    pd.DataFrame(reference_rows).to_csv(reference, index=False)
    for name, source in {"h5ad": path, "workbook": workbook, "reference": reference}.items():
        config["sources"][name].update(path=str(source), sha256=sha256_file(source))
    config_path = tmp_path / "fixture_config.json"
    config_path.write_text(json.dumps(config))
    protected = [path, workbook, reference, config_path]
    protected.extend(ROOT / source for source in config["source_code_sha256"])
    hashes = {source: sha256_file(source) for source in protected}
    states = []

    def synthetic_qc(source, state):
        assert Path(source) == path
        state.obs = obs.copy()
        state.keep_mask = np.ones(len(obs), dtype=bool)
        state.qc = {"status": "PASS", "data_mode": "synthetic_wiring_fixture"}
        state.validation = {"status": "INCONCLUSIVE"}
        state.validation_rows = [{"analysis": "existing_fixture"}]
        states.append(state)
        return state

    monkeypatch.setattr(diagnostic, "load_config", lambda _: copy.deepcopy(config))
    monkeypatch.setattr(real_pipeline, "run_schema_qc_census", synthetic_qc)
    monkeypatch.setenv("P22_PROFESSOR_APPROVED", "1")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
    return config_path, config, hashes, states


def test_pipeline_reproduces_outputs_without_changing_sources(diagnostic_inputs, tmp_path):
    config_path, _, hashes, states = diagnostic_inputs
    csv_bytes = []
    for name in ("first", "second"):
        output = tmp_path / name
        output.mkdir()  # The supervisor owns exclusive directory creation.
        result = diagnostic.run_analysis(ROOT, config_path, output)
        assert isinstance(result, dict)
        assert {
            "donor_influence.csv",
            "baseline_genes.csv",
            "SUMMARY.md",
            "donor_influence.png",
            "run.json",
        }.issubset(item.name for item in output.iterdir())
        rows = pd.read_csv(output / "donor_influence.csv")
        assert len(rows) == 4 * 20
        assert rows.groupby("sheet").size().to_dict() == {"CP": 20, "IP": 20, "oRG": 20, "vRG": 20}
        assert not rows.duplicated(["sheet", "omitted_donor"]).any()
        assert (output / "donor_influence.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert "POST_HOC_EXPLORATORY" in (output / "SUMMARY.md").read_text()
        csv_bytes.append((output / "donor_influence.csv").read_bytes())
    assert csv_bytes[0] == csv_bytes[1]
    assert {source: sha256_file(source) for source in hashes} == hashes
    assert len(states) == 2
    for state in states:
        assert state.validation == {"status": "INCONCLUSIVE"}
        assert state.validation_rows == [{"analysis": "existing_fixture"}]


def test_baseline_mismatch_stops_before_any_omission(diagnostic_inputs, tmp_path, monkeypatch):
    config_path, config, hashes, _ = diagnostic_inputs
    config["comparisons"][0]["rho"] += 0.1

    def forbidden_omissions(*args, **kwargs):
        raise AssertionError("omissions must not run before every baseline matches")

    monkeypatch.setattr(diagnostic, "omission_rows", forbidden_omissions)
    output = tmp_path / "mismatch"
    output.mkdir()
    with pytest.raises(ValueError, match="mismatch"):
        diagnostic.run_analysis(ROOT, config_path, output)
    assert not (output / "donor_influence.csv").exists()
    assert {source: sha256_file(source) for source in hashes} == hashes


def test_pipeline_reports_every_omission_unavailable(diagnostic_inputs, tmp_path, monkeypatch):
    config_path, _, hashes, _ = diagnostic_inputs

    def unavailable_rows(bulk, metadata, genes, external, baselines):
        # Stub the reporting boundary, not the baseline fits or source verification.
        return [
            {
                "sheet": sheet,
                "omitted_donor": donor,
                "status": "UNAVAILABLE",
                "fit_status": "FAILED",
                "reason": "synthetic all-unavailable reporting fixture",
                "n_shared_genes": None,
                "same_support_delta": None,
                "support_delta": None,
                "total_delta": None,
            }
            for sheet in baselines
            for donor in bulk.donor_ids
        ]

    monkeypatch.setattr(diagnostic, "omission_rows", unavailable_rows)
    output = tmp_path / "unavailable"
    output.mkdir()
    report = diagnostic.run_analysis(ROOT, config_path, output)
    assert report["omission_rows"] == 80 and report["available_rows"] == 0
    frame = pd.read_csv(output / "donor_influence.csv")
    assert len(frame) == 80 and frame.status.eq("UNAVAILABLE").all()
    missing = ["same_support_delta", "support_delta", "total_delta", "influence_rank"]
    assert frame[missing].isna().all().all()
    assert (output / "SUMMARY.md").read_text().count("Available omissions: 0/20.") == 4
    assert (output / "donor_influence.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert {source: sha256_file(source) for source in hashes} == hashes
