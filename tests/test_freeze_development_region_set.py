"""Offline tests for the frozen training-fold development region set."""

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "freeze_development_region_set",
        Path(__file__).parents[1] / "scripts/freeze_development_region_set.py",
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


def test_union_prevalence_and_selection(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500), ("chr1", 2000, 2500)])
    write_features(tmp_path, "LIB2", [("chr1", 1000, 1500), ("chr2", 500, 900)])
    write_features(tmp_path, "LIB3", [("chr1", 1000, 1500)])
    record = reader.build_region_set(tmp_path, ["LIB1", "LIB2", "LIB3"], top_n=2)
    assert record["n_union_regions"] == 3
    assert record["n_selected"] == 2
    assert record["prevalence_max"] == 3
    # chr1:1000-1500 has prevalence 3; next tie between chr1:2000-2500 and chr2:500-900
    # breaks by (chromosome, start, end): chr1 before chr2.
    assert record["regions"] == ["chr1:1000-1500", "chr1:2000-2500"]
    assert record["per_library"]["LIB1"]["n_peaks"] == 2


def test_duplicate_peak_refused(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500), ("chr1", 1000, 1500)])
    with pytest.raises(ValueError, match="duplicate peak interval"):
        reader.parse_features_peaks(tmp_path / "GSE305146_LIB1_features.tsv.gz")


def test_invalid_interval_refused(tmp_path):
    reader = module()
    path = tmp_path / "GSE305146_LIB1_features.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("p\tpeak\tPeaks\tchr1\t500\t500\n")
    with pytest.raises(ValueError, match="invalid peak interval"):
        reader.parse_features_peaks(path)


def test_no_peaks_refused(tmp_path):
    reader = module()
    path = tmp_path / "GSE305146_LIB1_features.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("ENSG000001\tGENE1\tGene Expression\tchr1\t100\t200\n")
    with pytest.raises(ValueError, match="no Peaks rows"):
        reader.parse_features_peaks(path)


def test_missing_library_refused(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500)])
    with pytest.raises(FileNotFoundError):
        reader.build_region_set(tmp_path, ["LIB1", "LIB2"], top_n=1)


def test_duplicate_libraries_refused(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500)])
    with pytest.raises(ValueError, match="duplicate training libraries"):
        reader.build_region_set(tmp_path, ["LIB1", "LIB1"], top_n=1)


def test_top_n_must_be_positive(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500)])
    with pytest.raises(ValueError, match="top_n"):
        reader.build_region_set(tmp_path, ["LIB1"], top_n=0)


def test_deterministic_selection(tmp_path):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr2", 100, 200), ("chr1", 300, 400), ("chr1", 100, 200)])
    write_features(tmp_path, "LIB2", [("chr2", 100, 200), ("chr1", 300, 400)])
    first = reader.build_region_set(tmp_path, ["LIB1", "LIB2"], top_n=3)
    second = reader.build_region_set(tmp_path, ["LIB2", "LIB1"], top_n=3)
    assert first["regions"] == second["regions"]
    assert first["regions_sha256"] == second["regions_sha256"]


def test_write_regions_file_round_trip(tmp_path):
    reader = module()
    record = {"regions": ["chr1:1000-1500", "chrX:5-9"]}
    out = tmp_path / "regions.bed"
    reader.write_regions_file(record, out)
    assert out.read_text() == "chr1\t1000\t1500\nchrX\t5\t9\n"


def test_main_writes_record_and_regions(tmp_path, capsys):
    reader = module()
    write_features(tmp_path, "LIB1", [("chr1", 1000, 1500), ("chr1", 2000, 2500)])
    libs = tmp_path / "libs.txt"
    libs.write_text("LIB1\n")
    out = tmp_path / "record.json"
    regions = tmp_path / "regions.bed"
    code = reader.main(
        [
            "--features-dir",
            str(tmp_path),
            "--train-libraries-file",
            str(libs),
            "--top-n",
            "1",
            "--out",
            str(out),
            "--regions-file",
            str(regions),
        ]
    )
    assert code == 0
    record = json.loads(out.read_text())
    assert record["n_selected"] == 1
    assert record["regions"] == ["chr1:1000-1500"]
    assert regions.exists()
    assert "n_selected" in capsys.readouterr().out
