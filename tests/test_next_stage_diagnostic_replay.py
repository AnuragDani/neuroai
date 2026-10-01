"""Focused Q1 refusal/replay checks for next_stage diagnostic replay."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "replay_next_stage_diagnostics.py"


def load_module():
    spec = importlib.util.spec_from_file_location("replay_next_stage_diagnostics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def replay():
    return load_module()


def _tiny_obs(n_cells: int = 8) -> pd.DataFrame:
    donors = ["PCW12_CON_A", "PCW13_DS_B"]
    types = ["AST", "IPC"]
    rows = []
    for i in range(n_cells):
        donor = donors[i % 2]
        rows.append(
            {
                "donor_id": donor,
                "disease": "normal" if "_CON_" in donor else "complete trisomy 21",
                "author_cell_type": types[i % 2],
                "library": f"L{i % 2}",
                "dev_PCW": "12" if "_CON_" in donor else "13",
                "nCount_RNA": 1000 + i,
                "nCount_ATAC": 2000 + i,
            }
        )
    index = [f"CELL{i}" for i in range(n_cells)]
    return pd.DataFrame(rows, index=index)


def test_prepare_output_dir_refuses_overwrite(replay, tmp_path: Path):
    out = tmp_path / "already"
    out.mkdir()
    with pytest.raises(replay.DiagnosticReplayError, match="refusing to overwrite"):
        replay.prepare_output_dir(out)


def test_missing_columns_fail(replay):
    obs = _tiny_obs().drop(columns=["donor_id"])
    with pytest.raises(replay.DiagnosticReplayError, match="missing required columns"):
        replay.require_columns(obs, replay.OBS_COLUMNS)


def test_tampered_matrix_hash_refused(replay, tmp_path: Path, monkeypatch):
    obs = _tiny_obs()
    h5ad = tmp_path / "fake.h5ad"
    atac = tmp_path / "counts.npz"
    bed = tmp_path / "regions.bed"
    bed.write_text("chr1\t0\t10\nchr1\t10\t20\n")
    matrix = sparse.csr_matrix(np.ones((2, len(obs)), dtype=np.float64))
    sparse.save_npz(atac, matrix)
    sidecar = {
        "shape": [2, len(obs)],
        "cells_sha256": replay.sha256_text(list(obs.index.astype(str))),
        "count_unit": "unique_fragment_overlap",
    }
    atac.with_name("counts.json").write_text(json.dumps(sidecar))

    monkeypatch.setattr(replay, "ordered_cell_ids", lambda _path: list(obs.index.astype(str)))
    h5ad.write_text("placeholder")

    with pytest.raises(replay.DiagnosticReplayError, match="matrix sha256 mismatch"):
        replay.build_measurement_audit(
            obs=obs,
            h5ad_path=h5ad,
            atac_npz=atac,
            union_bed=bed,
            require_matrix_sha256="0" * 64,
        )


def test_changed_cell_order_refused_via_sidecar(replay, tmp_path: Path, monkeypatch):
    obs = _tiny_obs()
    h5ad = tmp_path / "fake.h5ad"
    atac = tmp_path / "counts.npz"
    bed = tmp_path / "regions.bed"
    bed.write_text("chr1\t0\t10\nchr1\t10\t20\n")
    matrix = sparse.csr_matrix(np.ones((2, len(obs)), dtype=np.float64))
    sparse.save_npz(atac, matrix)
    # Sidecar records the original order hash; replay sees a shuffled order.
    original = list(obs.index.astype(str))
    shuffled = list(reversed(original))
    atac.with_name("counts.json").write_text(
        json.dumps(
            {
                "shape": [2, len(obs)],
                "cells_sha256": replay.sha256_text(original),
                "count_unit": "unique_fragment_overlap",
            }
        )
    )
    monkeypatch.setattr(replay, "ordered_cell_ids", lambda _path: shuffled)
    h5ad.write_text("placeholder")

    with pytest.raises(replay.DiagnosticReplayError, match="ordered-cell hash differs"):
        replay.build_measurement_audit(
            obs=obs,
            h5ad_path=h5ad,
            atac_npz=atac,
            union_bed=bed,
        )


def test_compare_records_detects_drift(replay):
    problems = replay.compare_records(
        "DATA",
        {"donors": 30, "classes": {"CON": 15, "DS": 14}},
        {"donors": 30, "classes": {"CON": 15, "DS": 15}},
    )
    assert problems
    assert any("DS" in problem for problem in problems)


def test_main_overwrite_exit_code(replay, tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    code = replay.main(
        [
            "--output-dir",
            str(out),
            "--no-compare-expected",
            "--h5ad",
            str(tmp_path / "missing.h5ad"),
        ]
    )
    assert code == 2
