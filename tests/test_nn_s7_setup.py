"""Focused checks for S7 setup / preflight helpers (no H5AD loads)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from p22.eval.planted_signal import s7_label_tag
from p22.eval.s7_ledger import Provenance, S7_SCREEN_SEED, sha256_file
from p22.eval.s7_runner import S7_PROTOCOL
from p22.eval.s7_setup import (
    S7_CAP,
    S7_DURABLE_ROOT,
    S7_FITTING_SOURCE_RELS,
    S7_PROTOCOL_ID,
    S7_SPEC_REL,
    build_provenance,
    donor_inventory,
    fold_positions,
    preflight_param_match,
    resolve_repo_root,
    resolve_s7_paths,
    write_preflight_record,
)


def test_resolve_paths_and_frozen_locations() -> None:
    root = resolve_repo_root()
    assert (root / S7_SPEC_REL).is_file()
    paths = resolve_s7_paths(root)
    assert paths["repo_root"] == root
    assert paths["durable_root"] == S7_DURABLE_ROOT
    assert paths["result_dir"] == root / "docs/nn_v2/s7"
    assert paths["ledger_root"] == S7_DURABLE_ROOT / "ledger"
    assert paths["checkpoint_dir"] == S7_DURABLE_ROOT / "checkpoints"
    assert S7_CAP == 256


def test_fold_positions_train_val_test_order() -> None:
    train = np.asarray([10, 11, 12], dtype=np.int64)
    val = np.asarray([20, 21], dtype=np.int64)
    test = np.asarray([30], dtype=np.int64)
    pos = fold_positions(train, val, test)
    assert pos["train"].tolist() == [0, 1, 2]
    assert pos["val"].tolist() == [3, 4]
    assert pos["test"].tolist() == [5]
    assert pos["holdout_rows"].tolist() == [20, 21, 30]
    assert pos["source_train"].tolist() == [10, 11, 12]


def test_donor_inventory_counts_unique() -> None:
    meta = pd.DataFrame(
        {
            "donor_id": ["d0", "d0", "d1", "d2"],
            "disease": [
                "complete trisomy 21",
                "complete trisomy 21",
                "control",
                "control",
            ],
            "label": [1, 1, 0, 0],
        }
    )
    inv = donor_inventory(meta)
    assert inv["n_donors"] == 3
    assert inv["donors_match_expected"] is False
    assert inv["n_disease"] == 1
    assert inv["n_control"] == 2
    assert inv["donor_ids"] == ["d0", "d1", "d2"]


def test_build_provenance_hashes_spec_and_sources(tmp_path: Path) -> None:
    # Use live repo roots; assert structure and that hashes are 64 hex chars.
    root = resolve_repo_root()
    # Point inputs at tiny temp files so we do not re-hash the multi-GiB h5ad.
    tiny = {
        "h5ad": tmp_path / "h5ad.bin",
        "atac": tmp_path / "atac.bin",
        "bed": tmp_path / "union.bed",
        "regions": tmp_path / "regions.json",
        "config": tmp_path / "config.json",
    }
    for path in tiny.values():
        path.write_bytes(b"s7-preflight-input\n")
    prov = build_provenance(
        root,
        input_paths={
            "h5ad": tiny["h5ad"],
            "atac_tiebreak_counts": tiny["atac"],
            "tracked_union_bed": tiny["bed"],
            "region_sets_sha256_json": tiny["regions"],
            "nn_inputs_config": tiny["config"],
        },
        extra={"note": "unit-test"},
    )
    assert isinstance(prov, Provenance)
    assert prov.protocol_id == S7_PROTOCOL_ID
    assert len(prov.spec_sha256) == 64
    assert prov.spec_sha256 == sha256_file(root / S7_SPEC_REL)
    for rel in S7_FITTING_SOURCE_RELS:
        assert rel.name in prov.source_sha256
        assert len(prov.source_sha256[rel.name]) == 64
    assert set(prov.input_sha256) == {
        "h5ad",
        "atac_tiebreak_counts",
        "tracked_union_bed",
        "region_sets_sha256_json",
        "nn_inputs_config",
    }
    assert prov.extra == {"note": "unit-test"}


def test_preflight_param_match_passes_frozen_widths() -> None:
    record = preflight_param_match(S7_PROTOCOL)
    assert record["matched"] is True
    assert record["relative_error"] <= record["tolerance"]
    assert record["cross_attention"] > 0
    assert record["token_concat"] > 0


def test_s7_label_tag_matches_screen_seed() -> None:
    assert s7_label_tag(S7_SCREEN_SEED) == f"prospective-s7:{S7_SCREEN_SEED}"


def test_write_preflight_record(tmp_path: Path) -> None:
    path = write_preflight_record(tmp_path / "preflight.json", {"ok": True, "n": 1})
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {"n": 1, "ok": True}
