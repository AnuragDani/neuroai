"""Post-hoc donor diagnostics: fixtures are not biological evidence."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from p22.data.real_cohort import DonorPseudobulk
from p22.eval.rna_donor_influence import (
    load_config,
    omission_rows,
    prepare_baselines,
    same_support_components,
    validate_baseline,
    verify_inputs,
)
from tests.test_external_validation import _discovery_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_config_refuses_model_or_gene_filter_changes(tmp_path):
    source = ROOT / "configs/rna_donor_influence.json"
    config = load_config(source)
    assert config["gene_rules"]["exclude_chr21"] is True
    assert config["gene_rules"]["expression_min_fraction_per_class"] == 0.5
    for section, field, value in [
        ("gene_rules", "exclude_chr21", False),
        ("model", "formula", "raw_counts ~ DS + PCW + female"),
        ("same_support_contract", "rho_atol", 0.1),
    ]:
        changed = json.loads(source.read_text())
        changed[section][field] = value
        path = tmp_path / "changed.json"
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="frozen config"):
            load_config(path)


def test_input_hash_mismatch_refuses(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"changed")
    config = {"sources": {"h5ad": {"path": "source", "sha256": "0" * 64}}, "source_code_sha256": {}}
    with pytest.raises(ValueError, match="source hash mismatch"):
        verify_inputs(tmp_path, config)


def population_fixture(*, stable=False):
    counts, metadata, genes = _discovery_fixture()
    if stable:
        counts[:12] = 100
        counts[12:] = np.arange(100, 750)
    else:
        counts[0] = np.rint(100 * np.exp(4 * np.sin(np.linspace(0, 4 * np.pi, 650))))
    bulk = DonorPseudobulk(
        tuple(metadata.index),
        tuple(metadata.disease),
        metadata.label.to_numpy(),
        np.full(24, 50),
        counts.sum(axis=1),
        counts,
        None,
        tuple(genes.index.astype(str)),
        None,
    )
    external = {
        "oRG": pd.DataFrame({"gene": genes.gene_name, "avg_log2FC": np.linspace(-0.8, 0.8, 650)})
    }
    return bulk, metadata, genes, external


def test_influential_donor_and_stable_control():
    for stable in (False, True):
        bulk, metadata, genes, external = population_fixture(stable=stable)
        fitted, tables = prepare_baselines(bulk, metadata, genes, external)
        result = omission_rows(bulk, metadata, genes, external, tables)
        assert len(result) == 24
        assert {row["status"] for row in result} == {"AVAILABLE"}
        assert {row["n_shared_genes"] for row in result} == {650}
        assert all(row["support_delta"] == 0 for row in result)
        if stable:
            assert all(abs(row["same_support_delta"]) <= 1e-12 for row in result)
        else:
            ranked = sorted(result, key=lambda row: -abs(row["same_support_delta"]))
            assert ranked[0]["omitted_donor"] == "donor00"
            assert ranked[0]["same_support_delta"] > 0.09
            assert ranked[0]["same_support_delta"] > 3 * abs(ranked[1]["same_support_delta"])
        assert fitted.audit["n_primary_eligible"] == 650


def test_rank_failure_is_reported_without_covariate_drop():
    bulk, metadata, genes, external = population_fixture()
    metadata["sex"] = "male"
    metadata.loc["donor00", "sex"] = "female"
    _, tables = prepare_baselines(bulk, metadata, genes, external)
    rows = omission_rows(bulk, metadata, genes, external, tables)
    invalid = next(row for row in rows if row["omitted_donor"] == "donor00")
    assert invalid["status"] == "UNAVAILABLE"
    assert "rank-deficient" in invalid["reason"]
    assert invalid["same_support_delta"] is None
    assert invalid["n_ds_donors"] == 12 and invalid["n_control_donors"] == 11


def test_omission_of_only_class_member_is_unavailable():
    bulk, metadata, genes, external = population_fixture()
    metadata["disease"] = bulk.conditions[0]
    metadata["label"] = 0
    metadata.loc["donor23", ["disease", "label"]] = [bulk.conditions[-1], 1]
    bulk = replace(bulk, conditions=tuple(metadata.disease), labels=metadata.label.to_numpy())
    _, tables = prepare_baselines(bulk, metadata, genes, external)
    rows = omission_rows(bulk, metadata, genes, external, tables)
    invalid = next(row for row in rows if row["omitted_donor"] == "donor23")
    assert invalid["status"] == "UNAVAILABLE"
    assert invalid["n_ds_donors"] == 0 and invalid["n_control_donors"] == 23
    assert "both disease classes" in invalid["reason"]
    assert invalid["same_support_delta"] is None


def test_baseline_mismatch_refuses_and_identifier_mismatch_fails():
    bulk, metadata, genes, external = population_fixture()
    fitted, tables = prepare_baselines(bulk, metadata, genes, external)
    expected = {
        **fitted.audit,
        "spearman_rho": 0.8943591564258596,
        "n_shared_genes": 650,
        "primary_cells": 1200,
        "donor_ids": list(bulk.donor_ids),
    }
    validate_baseline(fitted, bulk, tables["oRG"], expected)
    for key, value in [
        ("spearman_rho", 0.2),
        ("n_shared_genes", 649),
        ("donor_ids", list(reversed(bulk.donor_ids))),
    ]:
        with pytest.raises(ValueError, match="baseline mismatch"):
            validate_baseline(fitted, bulk, tables["oRG"], expected | {key: value})
    with pytest.raises(ValueError, match="mismatch"):
        prepare_baselines(
            replace(bulk, donor_ids=tuple(reversed(bulk.donor_ids))), metadata, genes, external
        )
    with pytest.raises(ValueError, match="alignment"):
        omission_rows(bulk, metadata.iloc[::-1], genes, external, tables)


def test_support_and_external_effect_guards():
    bulk, metadata, genes, external = population_fixture()
    _, tables = prepare_baselines(bulk, metadata, genes, external)
    baseline = tables["oRG"]
    assert same_support_components(baseline, baseline.iloc[:499])["status"] == "UNAVAILABLE"
    constant = baseline.assign(coefficient=1.0)
    assert "constant" in same_support_components(baseline, constant)["reason"]
    changed = baseline.assign(avg_log2FC=baseline.avg_log2FC + 1)
    with pytest.raises(ValueError, match="external effects changed"):
        same_support_components(baseline, changed)
    with pytest.raises(ValueError, match="unique"):
        same_support_components(baseline, pd.concat([baseline, baseline.iloc[:1]]))
    nonfinite = baseline.copy()
    nonfinite.loc[0, "coefficient"] = np.inf
    assert same_support_components(baseline, nonfinite)["status"] == "UNAVAILABLE"


def test_supervisor_timeout_memory_and_no_overwrite(tmp_path, monkeypatch):
    from scripts import diagnose_rna_replication as cli

    command = [sys.executable, "-c", "import time; time.sleep(20)"]
    monkeypatch.setattr(cli, "_rss_bytes", lambda pid: 1024)
    timeout = cli.supervise(command, tmp_path / "timeout", timeout_seconds=0.1)
    assert timeout["status"] == "TIMEOUT" and timeout["exit_code"] is not None
    memory = cli.supervise(command, tmp_path / "memory", stop_rss_bytes=512)
    assert memory["status"] == "MEMORY_LIMIT" and memory["exit_code"] is not None
    sentinel = tmp_path / "memory" / "sentinel"
    sentinel.write_text("keep")
    with pytest.raises(FileExistsError):
        cli.supervise(command, tmp_path / "memory")
    assert sentinel.read_text() == "keep"


def test_supervisor_refuses_missing_monitor_and_records_success(tmp_path, monkeypatch):
    from scripts import diagnose_rna_replication as cli

    def absent(pid):
        raise OSError("monitor absent")

    monkeypatch.setattr(cli, "_rss_bytes", absent)
    failed = cli.supervise(
        [sys.executable, "-c", "raise RuntimeError('must not start')"], tmp_path / "missing"
    )
    assert failed["status"] == "MONITOR_ERROR" and failed["pid"] is None
    monkeypatch.setattr(cli, "_rss_bytes", lambda pid: 1024)
    success = cli.supervise([sys.executable, "-c", "print('completed')"], tmp_path / "success")
    assert success["status"] == "COMPLETED" and success["exit_code"] == 0
    assert (tmp_path / "success" / "stdout.log").read_text().strip() == "completed"
