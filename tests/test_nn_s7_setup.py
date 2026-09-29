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
    S7_V2_CLASS0_OUTER_QUOTAS,
    S7_V2_CLASS1_OUTER_QUOTAS,
    S7_V2_DECLARED_SEEDS,
    S7_V2_EXPECTED_N_CLASS0,
    S7_V2_EXPECTED_N_CLASS1,
    S7_V2_N_TRIPLETS,
    FoldPackCache,
    S7V2PreflightError,
    allocate_s7_v2_donor_folds,
    assert_s7_v2_fake_label_agreement,
    build_provenance,
    build_s7_v2_all_seed_split_manifest,
    collect_s7_v2_donor_labels,
    donor_inventory,
    fold_positions,
    guarded_s7_v2_call,
    preflight_param_match,
    recount_s7_v2_split_manifest,
    require_s7_v2_preflight_pass,
    resolve_repo_root,
    resolve_s7_paths,
    run_s7_v2_all_seed_nofit_preflight,
    s7_v2_cell_id_hash,
    s7_v2_rank_donors,
    s7_v2_split_digest,
    validate_s7_v2_allocation,
    write_preflight_record,
    write_split_log,
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


def test_write_split_log_records_seed_and_tag(tmp_path: Path) -> None:
    pack = {
        "generator_seed": 2001,
        "fake_label_tag": "prospective-s7:2001",
        "donor_inventory": {"n_donors": 30},
        "split_log": {"0": {"train_donors": ["d0"]}},
    }
    path = write_split_log(tmp_path / "split_log_seed_2001.json", pack)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["generator_seed"] == 2001
    assert payload["fake_label_tag"] == "prospective-s7:2001"
    assert payload["split_log"]["0"]["train_donors"] == ["d0"]


def test_fold_pack_cache_reuses_initial_and_logs_new(tmp_path: Path, monkeypatch) -> None:
    screen = {
        "generator_seed": 1001,
        "fake_label_tag": "prospective-s7:1001",
        "folds_by_index": {0: "screen-fold"},
        "positions_by_fold": {0: {"train": np.asarray([0])}},
        "cell_ids_by_fold": {0: np.asarray(["c0"])},
        "donor_inventory": {"n_donors": 30},
        "split_log": {"0": {"fake_label_tag": "prospective-s7:1001"}},
    }
    confirm = {
        "generator_seed": 2001,
        "fake_label_tag": "prospective-s7:2001",
        "folds_by_index": {0: "confirm-fold"},
        "positions_by_fold": {0: {"train": np.asarray([1])}},
        "cell_ids_by_fold": {0: np.asarray(["c1"])},
        "donor_inventory": {"n_donors": 30},
        "split_log": {"0": {"fake_label_tag": "prospective-s7:2001"}},
    }
    prepared: list[int] = []

    def _fake_prepare(inputs, panels, *, generator_seed, protocol, n_folds, split_method="v1"):
        del inputs, panels, protocol, n_folds, split_method
        prepared.append(int(generator_seed))
        assert int(generator_seed) == 2001
        return confirm

    monkeypatch.setattr(
        "p22.eval.s7_setup.prepare_s7_folds",
        _fake_prepare,
    )

    class _Inputs:
        pass

    cache = FoldPackCache(
        _Inputs(),  # type: ignore[arg-type]
        panels={},
        split_log_dir=tmp_path / "split_logs",
        initial={1001: screen},
    )

    assert cache.get(1001)["folds_by_index"][0] == "screen-fold"
    assert prepared == []
    resolved = cache.resolver()(2001)
    assert resolved["fake_label_tag"] == "prospective-s7:2001"
    assert prepared == [2001]
    assert cache.get(2001) is resolved  # cached; no second prepare
    assert prepared == [2001]
    log_path = tmp_path / "split_logs" / "split_log_seed_2001.json"
    assert log_path.is_file()
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert payload["generator_seed"] == 2001
    assert payload["fake_label_tag"] == "prospective-s7:2001"
    assert set(cache.prepared_seeds) == {1001, 2001}


def test_confirm_seeds_use_distinct_fake_label_tags() -> None:
    assert s7_label_tag(1001) != s7_label_tag(2001)
    assert s7_label_tag(2001) == "prospective-s7:2001"
    assert s7_label_tag(2010) == "prospective-s7:2010"


def _synthetic_s7_v2_donors(
    *, n0: int = S7_V2_EXPECTED_N_CLASS0, n1: int = S7_V2_EXPECTED_N_CLASS1
) -> tuple[list[str], list[int]]:
    donors = [f"d0_{i:02d}" for i in range(n0)] + [f"d1_{i:02d}" for i in range(n1)]
    labels = [0] * n0 + [1] * n1
    return donors, labels


def test_s7_v2_split_digest_matches_frozen_encoding() -> None:
    import hashlib

    expected = hashlib.sha256(
        b"s7-split-v2\n0\n1001\nouter\n0\nPCW11_CON_17833"
    ).hexdigest()
    assert (
        s7_v2_split_digest(
            split_seed=0,
            generator_seed=1001,
            stage="outer",
            label=0,
            donor_id="PCW11_CON_17833",
        )
        == expected
    )


def test_s7_v2_rank_donors_is_order_invariant() -> None:
    donors = ["b", "a", "c", "a"]
    ranked = s7_v2_rank_donors(
        donors,
        split_seed=0,
        generator_seed=1001,
        stage="outer",
        label=0,
    )
    ranked_rev = s7_v2_rank_donors(
        list(reversed(donors)),
        split_seed=0,
        generator_seed=1001,
        stage="outer",
        label=0,
    )
    assert ranked == ranked_rev
    assert ranked == sorted(set(donors), key=lambda d: (s7_v2_split_digest(
        split_seed=0, generator_seed=1001, stage="outer", label=0, donor_id=d
    ), d))


def test_collect_s7_v2_donor_labels_refuses_mixed_and_accepts_repeats() -> None:
    labels = collect_s7_v2_donor_labels(
        ["d0", "d0", "d1"],
        [0, 0, 1],
    )
    assert labels == {"d0": 0, "d1": 1}
    try:
        collect_s7_v2_donor_labels(["d0", "d0"], [0, 1])
    except ValueError as exc:
        assert "mixed-label" in str(exc)
    else:
        raise AssertionError("expected mixed-label refusal")


def test_allocate_s7_v2_donor_folds_quotas_coverage_and_inner() -> None:
    donors, labels = _synthetic_s7_v2_donors()
    # Expand to cell-level rows with shuffled order to prove invariance.
    cell_donors = donors + list(reversed(donors))
    cell_labels = labels + list(reversed(labels))
    alloc = allocate_s7_v2_donor_folds(
        cell_donors,
        cell_labels,
        split_seed=0,
        generator_seed=1001,
    )
    assert alloc["class_balance"] == {"0": 16, "1": 14}
    assert alloc["outer_class0_quotas"] == list(S7_V2_CLASS0_OUTER_QUOTAS)
    assert alloc["outer_class1_quotas"] == list(S7_V2_CLASS1_OUTER_QUOTAS)
    assert alloc["outer_class0_quotas"][0] == 4
    assert alloc["outer_class1_quotas"][0] == 2

    all_test: list[str] = []
    for fold_idx in range(5):
        fold = alloc["folds"][str(fold_idx)]
        assert len(fold["test_donors"]) == 6
        assert len(fold["val_donors"]) == 8
        assert len(fold["train_donors"]) == 16
        assert fold["val_class_counts"] == {"0": 4, "1": 4}
        assert int(fold["test_class_counts"]["0"]) == S7_V2_CLASS0_OUTER_QUOTAS[fold_idx]
        assert int(fold["test_class_counts"]["1"]) == S7_V2_CLASS1_OUTER_QUOTAS[fold_idx]
        assert int(fold["train_class_counts"]["0"]) >= 1
        assert int(fold["train_class_counts"]["1"]) >= 1
        train, val, test = (
            set(fold["train_donors"]),
            set(fold["val_donors"]),
            set(fold["test_donors"]),
        )
        assert not (train & val or train & test or val & test)
        assert train | val | test == set(donors)
        all_test.extend(fold["test_donors"])

    assert len(all_test) == 30
    assert len(set(all_test)) == 30
    assert set(all_test) == set(donors)

    replay = allocate_s7_v2_donor_folds(
        list(reversed(cell_donors)),
        list(reversed(cell_labels)),
        split_seed=0,
        generator_seed=1001,
    )
    assert replay["folds"] == alloc["folds"]
    assert replay["donor_labels"] == alloc["donor_labels"]

    other_seed = allocate_s7_v2_donor_folds(
        cell_donors,
        cell_labels,
        split_seed=0,
        generator_seed=2001,
    )
    assert other_seed["folds"] != alloc["folds"]
    # Quotas unchanged across generator tags.
    for fold_idx in range(5):
        a = alloc["folds"][str(fold_idx)]["test_class_counts"]
        b = other_seed["folds"][str(fold_idx)]["test_class_counts"]
        assert a == b


def test_allocate_s7_v2_refuses_wrong_balance() -> None:
    donors, labels = _synthetic_s7_v2_donors(n0=15, n1=14)
    try:
        allocate_s7_v2_donor_folds(donors, labels, split_seed=0, generator_seed=1001)
    except ValueError as exc:
        assert "16/14" in str(exc)
    else:
        raise AssertionError("expected class-balance refusal")


def _label_rows_for_all_declared_seeds() -> dict[int, tuple[list[str], list[int]]]:
    donors, labels = _synthetic_s7_v2_donors()
    # Distinct cell-level expansion; labels are donor-pure.
    cell_donors = donors + list(reversed(donors))
    cell_labels = labels + list(reversed(labels))
    return {int(seed): (cell_donors, cell_labels) for seed in S7_V2_DECLARED_SEEDS}


def test_s7_v2_all_seed_manifest_covers_55_triplets(tmp_path: Path) -> None:
    label_rows = _label_rows_for_all_declared_seeds()
    planted = {
        seed: collect_s7_v2_donor_labels(donors, labels)
        for seed, (donors, labels) in label_rows.items()
    }
    cell_hashes = {
        seed: {
            str(fold): {
                "train": s7_v2_cell_id_hash([f"{seed}-{fold}-train"]),
                "val": s7_v2_cell_id_hash([f"{seed}-{fold}-val"]),
                "test": s7_v2_cell_id_hash([f"{seed}-{fold}-test"]),
            }
            for fold in range(5)
        }
        for seed in S7_V2_DECLARED_SEEDS
    }
    manifest_path = tmp_path / "split_manifest_v2.json"
    manifest = run_s7_v2_all_seed_nofit_preflight(
        label_rows_by_seed=label_rows,
        split_seed=0,
        planted_labels_by_seed=planted,
        cell_id_hashes_by_seed=cell_hashes,
        manifest_path=manifest_path,
    )
    assert manifest["ok"] is True
    assert manifest["n_seeds"] == 11
    assert manifest["n_triplets"] == S7_V2_N_TRIPLETS == 55
    assert list(manifest["declared_seeds"]) == list(S7_V2_DECLARED_SEEDS)
    assert manifest_path.is_file()

    recount = recount_s7_v2_split_manifest(manifest)
    assert recount["ok"] is True
    assert recount["n_seeds"] == 11
    assert recount["n_triplets"] == 55
    for seed in S7_V2_DECLARED_SEEDS:
        entry = manifest["seeds"][str(seed)]
        assert entry["n_test_donors_unique"] == 30
        for fold_idx in range(5):
            fold = entry["folds"][str(fold_idx)]
            assert fold["n_train_donors"] == 16
            assert fold["n_val_donors"] == 8
            assert fold["n_test_donors"] == 6
            assert fold["train_class_counts"]["0"] >= 1
            assert fold["train_class_counts"]["1"] >= 1
            assert fold["val_class_counts"]["0"] >= 1
            assert fold["val_class_counts"]["1"] >= 1
            assert fold["test_class_counts"]["0"] >= 1
            assert fold["test_class_counts"]["1"] >= 1
        assert "cell_id_hashes" in entry


def test_s7_v2_single_class_fold_blocks_entire_batch_and_fits() -> None:
    label_rows = _label_rows_for_all_declared_seeds()
    # Keep 16/14 balance but force fold-0 test to six class-0 donors only.
    good = allocate_s7_v2_donor_folds(
        *label_rows[2005],
        split_seed=0,
        generator_seed=2005,
    )
    donor_labels = dict(good["donor_labels"])
    class0 = sorted(d for d, lab in donor_labels.items() if lab == 0)
    class1 = sorted(d for d, lab in donor_labels.items() if lab == 1)
    bad_test = class0[:6]
    rem0 = class0[6:]
    rem1 = class1
    bad_val = sorted(rem0[:4] + rem1[:4])
    bad_train = sorted(rem0[4:] + rem1[4:])
    poisoned_folds = {k: dict(v) for k, v in good["folds"].items()}
    poisoned_folds["0"] = {
        "train_donors": bad_train,
        "val_donors": bad_val,
        "test_donors": bad_test,
        "train_class_counts": {"0": 6, "1": 10},
        "val_class_counts": {"0": 4, "1": 4},
        "test_class_counts": {"0": 6, "1": 0},
        "outer_quotas": {"class0": 6, "class1": 0},
    }
    poisoned = dict(good)
    poisoned["folds"] = poisoned_folds

    try:
        validate_s7_v2_allocation(poisoned)
    except S7V2PreflightError as exc:
        assert "INVALID_PREFLIGHT" in str(exc)
        assert "single-class" in str(exc)
    else:
        raise AssertionError("expected single-class preflight refusal")

    fit_calls: list[str] = []

    def _fake_fit(name: str) -> str:
        fit_calls.append(name)
        return "fitted"

    try:
        guarded_s7_v2_call({"ok": False, "n_triplets": 0}, _fake_fit, "cross_attention")
    except S7V2PreflightError as exc:
        assert "INVALID_PREFLIGHT" in str(exc)
    else:
        raise AssertionError("expected fit refusal")
    assert fit_calls == []

    # Missing confirmation seed in label rows also blocks the whole batch.
    incomplete = dict(label_rows)
    del incomplete[2007]
    try:
        build_s7_v2_all_seed_split_manifest(label_rows_by_seed=incomplete, split_seed=0)
    except S7V2PreflightError as exc:
        assert "2007" in str(exc)
    else:
        raise AssertionError("expected missing-seed refusal")
    assert fit_calls == []

    require_s7_v2_preflight_pass(
        run_s7_v2_all_seed_nofit_preflight(label_rows_by_seed=label_rows, split_seed=0)
    )
    assert guarded_s7_v2_call(
        {"ok": True, "n_triplets": 55}, _fake_fit, "token_concat"
    ) == "fitted"
    assert fit_calls == ["token_concat"]


def test_s7_v2_planted_full_label_mismatch_refused() -> None:
    donors, labels = _synthetic_s7_v2_donors()
    full = collect_s7_v2_donor_labels(donors, labels)
    planted = dict(full)
    planted[donors[0]] = 1 - int(full[donors[0]])
    try:
        assert_s7_v2_fake_label_agreement(full, planted)
    except S7V2PreflightError as exc:
        assert "disagree" in str(exc)
    else:
        raise AssertionError("expected planted/full mismatch refusal")

    label_rows = _label_rows_for_all_declared_seeds()
    planted_by_seed = {
        seed: collect_s7_v2_donor_labels(d, labs)
        for seed, (d, labs) in label_rows.items()
    }
    planted_by_seed[2003] = dict(planted_by_seed[2003])
    victim = next(iter(planted_by_seed[2003]))
    planted_by_seed[2003][victim] = 1 - planted_by_seed[2003][victim]
    try:
        build_s7_v2_all_seed_split_manifest(
            label_rows_by_seed=label_rows,
            split_seed=0,
            planted_labels_by_seed=planted_by_seed,
        )
    except S7V2PreflightError as exc:
        assert "2003" in str(exc) or "disagree" in str(exc)
    else:
        raise AssertionError("expected one invalid confirmation seed to block batch")


def test_s7_v2_cell_id_hash_is_stable() -> None:
    assert s7_v2_cell_id_hash(["c0", "c1"]) == s7_v2_cell_id_hash(["c0", "c1"])
    assert s7_v2_cell_id_hash(["c0", "c1"]) != s7_v2_cell_id_hash(["c1", "c0"])
