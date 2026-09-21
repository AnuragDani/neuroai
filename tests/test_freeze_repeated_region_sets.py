"""Offline tests for the repeated training-only region sets."""

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "freeze_repeated_region_sets",
        Path(__file__).parents[1] / "scripts/freeze_repeated_region_sets.py",
    )
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def write_features(tmp_path: Path, library: str, peaks: list[tuple]) -> Path:
    path = tmp_path / f"GSE305146_{library}_features.tsv.gz"
    rows = ["ENSG000001\tGENE1\tGene Expression\tchr1\t100\t200"]
    for chromosome, start, end in peaks:
        rows.append(f"peak_{chromosome}_{start}\tpeak\tPeaks\t{chromosome}\t{start}\t{end}")
    with gzip.open(path, "wt") as handle:
        handle.write("\n".join(rows) + "\n")
    return path


def fold(repeat, fold_index, libraries):
    return {
        "repeat": repeat,
        "fold": fold_index,
        "split_seed": repeat,
        "n_train_donors": 3,
        "n_test_donors": 1,
        "train_donors": ["a", "b", "c"],
        "test_donors": ["d"],
        "train_libraries": libraries,
    }


def test_per_fold_selection_and_union(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500), ("chr1", 2000, 2500)])
    write_features(tmp_path, "LIB2", [("chr1", 1000, 1500), ("chr2", 500, 900)])
    record = reader.build_repeated_region_sets(
        tmp_path, [fold(0, 0, ["LIB1"]), fold(0, 1, ["LIB2"])], top_n=2
    )
    assert record["n_folds"] == 2
    assert record["per_fold"][0]["regions"] == ["chr1:1000-1500", "chr1:2000-2500"]
    assert record["per_fold"][1]["regions"] == ["chr1:1000-1500", "chr2:500-900"]
    assert record["union_regions"] == ["chr1:1000-1500", "chr1:2000-2500", "chr2:500-900"]
    assert record["n_union_regions"] == 3
    assert record["union_fold_prevalence"]["chr1:1000-1500"] == 2


def test_fold_records_carry_split_metadata(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500)])
    record = reader.build_repeated_region_sets(tmp_path, [fold(1, 2, ["LIB1"])], top_n=1)
    entry = record["per_fold"][0]
    assert (entry["repeat"], entry["fold"]) == (1, 2)
    assert entry["train_donors"] == ["a", "b", "c"]
    assert entry["test_donors"] == ["d"]
    assert entry["n_train_donors"] == 3


def test_empty_folds_refused(tmp_path):
    reader = module()
    with pytest.raises(ValueError, match="at least one fold"):
        reader.build_repeated_region_sets(tmp_path, [], top_n=1)


def test_deterministic_record(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr2", 100, 200), ("chr1", 300, 400)])
    write_features(tmp_path, "LIB2", [("chr2", 100, 200)])
    folds = [fold(0, 0, ["LIB1"]), fold(0, 1, ["LIB2"])]
    first = reader.build_repeated_region_sets(tmp_path, folds, top_n=2)
    second = reader.build_repeated_region_sets(tmp_path, folds, top_n=2)
    assert first["union_regions"] == second["union_regions"]
    assert first["union_sha256"] == second["union_sha256"]


def test_main_writes_record_and_union_bed(tmp_path, capsys):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500), ("chr1", 2000, 2500)])
    out = tmp_path / "record.json"
    bed = tmp_path / "union.bed"
    # Patch fold derivation to avoid needing a real H5AD in the offline test.
    reader.derive_all_fold_libraries = lambda *args, **kwargs: [fold(0, 0, ["LIB1"])]
    code = reader.main(
        [
            "--features-dir",
            str(tmp_path),
            "--obs-h5ad",
            str(tmp_path / "unused.h5ad"),
            "--top-n",
            "1",
            "--out",
            str(out),
            "--union-bed",
            str(bed),
        ]
    )
    assert code == 0
    record = json.loads(out.read_text())
    assert record["n_folds"] == 1
    assert record["n_union_regions"] == 1
    assert bed.read_text() == "chr1\t1000\t1500\n"
    assert "n_union_regions" in capsys.readouterr().out
