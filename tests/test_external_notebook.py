"""Canonical notebook adds bounded RNA evidence without changing existing gates."""

import copy
import hashlib
import importlib.util
import io
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import matplotlib
import pandas as pd
import pytest

from p22.data.census import sha256_file
from p22.eval.gates import GateBoard, make_gate

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]


def rewrite_module():
    spec = importlib.util.spec_from_file_location(
        "rewrite_canonical_notebook", ROOT / "scripts" / "rewrite_canonical_notebook.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_cell_insertion_is_idempotent_and_preserves_hand_cells(tmp_path):
    module = rewrite_module()
    notebook = json.loads((ROOT / "P22_down_syndrome_all_in_one.ipynb").read_text())
    notebook["cells"] = [cell for cell in notebook["cells"] if cell.get("id") != "ext-rna1"]
    original = copy.deepcopy(notebook)
    module.NB_PATH = tmp_path / "notebook.ipynb"
    module.NB_PATH.write_text(json.dumps(notebook))
    module.main()
    first = module.NB_PATH.read_bytes()
    updated = json.loads(first)
    assert len(updated["cells"]) == 25
    assert updated["cells"][20]["id"] == "measurement-correction-md"
    assert updated["cells"][21]["id"] == "measurement-correction-code"
    assert updated["cells"][22]["id"] == "ext-rna1"
    for index in (2, 3, 5):
        assert updated["cells"][index] == original["cells"][index]
    assert "".join(updated["cells"][23]["source"]) == module.CELL20
    assert "".join(updated["cells"][24]["source"]) == module.CELL21
    assert "".join(updated["cells"][21]["source"]) == module.CELL_MEASUREMENT_CODE
    for cell in updated["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), cell["id"], "exec")
    module.main()
    assert module.NB_PATH.read_bytes() == first
    assert "openpyxl==3.1.5" in module.CELL1
    assert '"external_rna_replication": external_rna_record' in module.CELL21
    assert "## External RNA direction replication" in module.CELL21
    assert "Corrected real paired workflow" in module.CELL_MEASUREMENT_MD


def test_external_cell_rejects_unexpected_layout(tmp_path):
    module = rewrite_module()
    module.NB_PATH = tmp_path / "bad.ipynb"
    module.NB_PATH.write_text(json.dumps({"cells": [{"id": str(i)} for i in range(23)]}))
    before = module.NB_PATH.read_bytes()
    with pytest.raises(AssertionError):
        module.main()
    assert module.NB_PATH.read_bytes() == before


@pytest.mark.parametrize("blocked", ["mode", "approval", "model", "qc"])
def test_external_cell_never_downloads_or_fits_without_gates(tmp_path, blocked):
    module = rewrite_module()
    namespace = {
        "REAL_MODE_ACTIVE": blocked != "mode",
        "PROFESSOR_APPROVED": blocked != "approval",
        "mode": SimpleNamespace(allow_model_fit=blocked != "model"),
        "real_state": SimpleNamespace(keep_mask=None if blocked == "qc" else [True]),
    }
    exec(module.CELL_EXTERNAL, namespace)
    assert namespace["external_rna_result"]["execution_status"] == "blocked"
    assert namespace["external_rna_result"]["gene_tables"] == {}


def test_external_cell_checks_hash_reuses_cache_and_preserves_alias(tmp_path, monkeypatch):
    module = rewrite_module()
    payload = b"pinned workbook fixture"
    calls = []

    def open_source(url, timeout):
        calls.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr("urllib.request.urlopen", open_source)
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)
    state = SimpleNamespace(
        keep_mask=[True],
        validation_rows=[{"analysis": "existing"}],
        validation={
            "status": "INCONCLUSIVE",
            "processed_rna_summary": {"execution_status": "completed"},
        },
    )
    board = GateBoard()
    board.set(make_gate("G8", "INCONCLUSIVE"))
    alias = state.validation_rows
    populations = ("oRG", "vRG", "CP", "IP")

    def replication(h5ad_path, external_xlsx, *, state, approval_present):
        assert external_xlsx.read_bytes() == payload
        assert approval_present is True
        rows = [{"external_population": population} for population in populations]
        state.validation_rows.extend(rows)
        return {
            "rows": rows,
            "headline_outcome": "inconclusive",
            "execution_status": "completed",
            "gene_tables": {
                population: [{"gene": "A", "coefficient": 0.1, "avg_log2FC": -0.2}]
                for population in populations
            },
        }

    namespace = {
        "REAL_MODE_ACTIVE": True,
        "PROFESSOR_APPROVED": True,
        "mode": SimpleNamespace(allow_model_fit=True, mode="real_analysis"),
        "real_state": state,
        "DATA_ROOT": tmp_path,
        "OUTPUT_ROOT": tmp_path / "output",
        "SEED": 22,
        "EXTERNAL_RNA_URL": "https://example.test/pinned.xlsx",
        "EXTERNAL_RNA_SHA256": "0" * 64,
        "EXTERNAL_RNA_BYTES": len(payload),
        "h5ad_path": tmp_path / "fixture.h5ad",
        "run_external_rna_replication": replication,
        "sha256_file": sha256_file,
        "hashlib": hashlib,
        "pd": pd,
        "board": board,
        "replace": replace,
    }
    exec(module.CELL_EXTERNAL, namespace)
    assert namespace["external_rna_result"]["execution_status"] == "failed"
    assert alias == [{"analysis": "existing"}]
    assert not (tmp_path / "41467_2025_63752_MOESM4_ESM.xlsx").exists()

    namespace["EXTERNAL_RNA_SHA256"] = hashlib.sha256(payload).hexdigest()
    exec(module.CELL_EXTERNAL, namespace)
    assert len(calls) == 2
    assert len(alias) == 5
    assert namespace["external_rna_result"]["headline_outcome"] == "inconclusive"
    assert board.get("G8").status == "INCONCLUSIVE"
    assert "verified and analyzed" in board.get("G8").notes
    assert board.get("G8").evidence["processed_rna_summary"]["execution_status"] == "completed"
    figure = tmp_path / "output/runs/real_analysis_22/figures/external_rna_concordance.png"
    assert figure.is_file()
    exec(module.CELL_EXTERNAL, namespace)
    assert len(calls) == 2

    cached = tmp_path / "41467_2025_63752_MOESM4_ESM.xlsx"
    cached.write_bytes(b"x" * len(payload))
    rows_before = len(alias)
    exec(module.CELL_EXTERNAL, namespace)
    assert namespace["external_rna_result"]["execution_status"] == "failed"
    assert len(alias) == rows_before
    assert len(calls) == 2
