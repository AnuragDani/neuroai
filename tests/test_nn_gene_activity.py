"""Offline tests for the N19 gene-activity panel and transfer estimator."""

import importlib.util
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parents[1]
SRC_WT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8"
)
UNION_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
LOCAL_TBI = (
    SRC_WT / "reports/generated/development_region_set_20260921/fragment.tbi"
)
UNION_EXPECTED_BYTES = 3_171_155_968


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def make_index(chunks):
    names = b"chr1\x00"
    header = struct.pack("<8i", 1, 65536, 1, 2, 3, 35, 0, len(names))
    index = bytearray(b"TBI\x01" + header + names)
    index += struct.pack("<i", 1)
    index += struct.pack("<I", 0)
    index += struct.pack("<i", len(chunks))
    for start, stop in chunks:
        index += struct.pack("<QQ", start, stop)
    index += struct.pack("<i", 1)
    index += struct.pack("<Q", 0)
    return bytes(index)


class FakeIndex:
    """Duck-typed stand-in returning pre-seeded merged chunks per region."""

    def __init__(self, chunks_by_region):
        self.chunks_by_region = chunks_by_region

    def query_chunks(self, name, beg, end):
        return self.chunks_by_region.get((name, beg, end), [])


W = 262_144


def test_windows_for_chunk_accounting():
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    assert mod.windows_for_chunk(0, 0, W) == 1
    assert mod.windows_for_chunk(0, (W - 1) << 16, W) == 1
    assert mod.windows_for_chunk(0, W << 16, W) == 1
    assert mod.windows_for_chunk(0, (W + 1) << 16, W) == 2
    assert mod.windows_for_chunk(0, (2 * W + 1) << 16, W) == 3
    with pytest.raises(ValueError):
        mod.windows_for_chunk(0, 1, 0)
    with pytest.raises(ValueError):
        mod.windows_for_chunk(5 << 16, 1 << 16, W)


def test_windows_for_chunk_ignores_sub_window_spans():
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    # Sub-window spans (including zero) still cost exactly one window.
    for span in (0, 1, 5, W - 1):
        assert mod.windows_for_chunk(0, span << 16, W) == 1


def test_estimate_regions_sums_windows_and_bytes():
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    index = FakeIndex(
        {
            ("chr1", 0, 100): [(0, (W + 5) << 16)],
            ("chr1", 200, 300): [(0, 0), (10 << 16, 10 << 16)],
        }
    )
    regions = [("chr1", 0, 100), ("chr1", 200, 300), ("chr2", 0, 10)]
    stats = mod.estimate_regions(index, regions, window=W)
    # chr1:0-100 -> one chunk spanning > W -> 2 windows; chr1:200-300 -> 2 chunks -> 2 windows.
    assert stats["n_regions"] == 3
    assert stats["n_chunks"] == 3
    assert stats["n_windows"] == 4
    assert stats["estimated_bytes"] == 4 * W
    assert [r["windows"] for r in stats["per_region"]] == [2, 2, 0]


def test_read_regions_file_parses_bed(tmp_path):
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    bed = tmp_path / "regions.bed"
    bed.write_text("# comment\nchr1\t10\t20\nchr2\t30\t40\tname\n\n")
    assert qfr.read_regions_file(str(bed)) == [
        ("chr1", 10, 20),
        ("chr2", 30, 40),
    ]


def test_main_matches_synthetic_index_and_validates(tmp_path):
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    tbi = tmp_path / "fragment.tbi"
    tbi.write_bytes(make_index([(0, 3 << 16)]))
    bed = tmp_path / "regions.bed"
    bed.write_text("chr1\t0\t100\n")

    # span of 3 bytes is one window.
    assert mod.main(["--regions-bed", str(bed), "--index-path", str(tbi)]) == 0
    assert (
        mod.main(
            [
                "--regions-bed",
                str(bed),
                "--index-path",
                str(tbi),
                "--expect-bytes",
                str(W),
            ]
        )
        == 0
    )
    assert (
        mod.main(
            [
                "--regions-bed",
                str(bed),
                "--index-path",
                str(tbi),
                "--expect-bytes",
                "1000",
            ]
        )
        == 2
    )


def test_main_writes_json_report(tmp_path):
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    tbi = tmp_path / "fragment.tbi"
    tbi.write_bytes(make_index([(0, 3 << 16)]))
    bed = tmp_path / "regions.bed"
    bed.write_text("chr1\t0\t100\n")
    out = tmp_path / "estimate.json"
    assert (
        mod.main(
            ["--regions-bed", str(bed), "--index-path", str(tbi), "--json-out", str(out)]
        )
        == 0
    )
    report = json.loads(out.read_text())
    assert report["estimated_bytes"] == W
    assert report["n_windows"] == 1
    assert "per_region" not in report
    assert report["regions_file_sha256"]


@pytest.mark.skipif(
    not (UNION_BED.exists() and LOCAL_TBI.exists()),
    reason="tie-break union BED or local fragment.tbi not present",
)
def test_estimator_reproduces_tiebreak_contract_bytes():
    mod = load("estimate_fragment_transfer", "scripts/estimate_fragment_transfer.py")
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    index = qfr.TabixIndex.from_path(LOCAL_TBI)
    regions = qfr.read_regions_file(str(UNION_BED))
    stats = mod.estimate_regions(index, regions)
    assert stats["n_regions"] == 465
    assert stats["estimated_bytes"] == UNION_EXPECTED_BYTES
    assert stats["n_windows"] == UNION_EXPECTED_BYTES // W


# --- N19 gene-activity panel builder -----------------------------------------


def make_index_multi(seqs):
    """TBI with one root bin per reference, usable by the tabix parser."""
    names = b"".join(name.encode("utf-8") + b"\x00" for name, _ in seqs)
    header = struct.pack("<8i", len(seqs), 65536, 1, 2, 3, 35, 0, len(names))
    index = bytearray(b"TBI\x01" + header + names)
    for _name, chunks in seqs:
        index += struct.pack("<i", 1)  # n_bin
        index += struct.pack("<I", 0)  # root bin covers every region
        index += struct.pack("<i", len(chunks))
        for start, stop in chunks:
            index += struct.pack("<QQ", start, stop)
        index += struct.pack("<i", 1)  # n_intv
        index += struct.pack("<Q", 0)
    return bytes(index)


class AnyChunkIndex:
    """Index returning a single one-window chunk for any region."""

    def __init__(self, chunk=(0, 0)):
        self.chunk = chunk

    def query_chunks(self, name, beg, end):
        return [self.chunk]


def _write_categorical(group, key, values):
    h5py = pytest.importorskip("h5py")
    np = pytest.importorskip("numpy")
    cats = sorted({str(v) for v in values})
    codes = np.array([cats.index(str(v)) for v in values], dtype=np.int64)
    sub = group.create_group(key)
    sub.create_dataset(
        "categories", data=np.array(cats, dtype=object), dtype=h5py.string_dtype("utf-8")
    )
    sub.create_dataset("codes", data=codes)
    sub.attrs["encoding-type"] = "categorical"


def make_h5ad(path, chroms, starts, ends, names, matrix):
    h5py = pytest.importorskip("h5py")
    np = pytest.importorskip("numpy")
    sparse = pytest.importorskip("scipy.sparse")
    csr = sparse.csr_matrix(np.asarray(matrix, dtype=np.float32))
    with h5py.File(path, "w") as handle:
        var = handle.create_group("raw/var")
        var.create_dataset(
            "_index",
            data=np.array([f"g{i}" for i in range(len(names))], dtype=object),
            dtype=h5py.string_dtype("utf-8"),
        )
        _write_categorical(var, "gene_name", names)
        _write_categorical(var, "seqnames", chroms)
        var.create_dataset("start", data=np.array(starts, dtype=np.int64))
        var.create_dataset("end", data=np.array(ends, dtype=np.int64))
        x = handle.create_group("raw/X")
        x.attrs["encoding-type"] = "csr_matrix"
        x.attrs["shape"] = np.array(csr.shape, dtype=np.int64)
        x.create_dataset("data", data=csr.data.astype(np.float32))
        x.create_dataset("indices", data=csr.indices.astype(np.int64))
        x.create_dataset("indptr", data=csr.indptr.astype(np.int64))
    return path


def test_read_gene_table_expands_categoricals(tmp_path):
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    h5ad = make_h5ad(
        tmp_path / "tiny.h5ad",
        ["chr21", "chr1", "chrY"],
        [1000, 2000, 500],
        [2000, 3000, 900],
        ["APP", "RORB", "MISC"],
        [[1.0, 0.0, 2.0], [0.0, 3.0, 1.0]],
    )
    table = builder.read_gene_table(h5ad)
    assert table.n_genes == 3
    assert list(table.names) == ["APP", "RORB", "MISC"]
    assert list(table.chrom) == ["chr21", "chr1", "chrY"]
    assert list(table.start) == [1000, 2000, 500]
    assert list(table.end) == [2000, 3000, 900]
    assert list(table.gene_ids) == ["g0", "g1", "g2"]


def test_stream_gene_stats_matches_manual_lognorm(tmp_path):
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    h5ad = make_h5ad(
        tmp_path / "tiny.h5ad",
        ["chr1", "chr1", "chr1"],
        [10, 20, 30],
        [20, 30, 40],
        ["A", "B", "C"],
        [[1.0, 0.0, 2.0], [0.0, 3.0, 1.0]],
    )
    stats = builder.stream_gene_stats(h5ad, chunk_cells=1)
    assert stats["n_cells"] == 2
    assert list(stats["nnz"]) == [1, 1, 2]
    manual = [
        np.log1p(1e4 / 3) / 2,
        np.log1p(3e4 / 4) / 2,
        (np.log1p(2e4 / 3) + np.log1p(1e4 / 4)) / 2,
    ]
    assert np.allclose(stats["mean"], manual)
    assert np.all(stats["dispersion"] >= 0)


def test_normalized_dispersion_z_is_binned_standard_score(tmp_path):
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    mean = np.full(40, 5.0)
    dispersion = np.arange(40, dtype=np.float64)
    z = builder.normalized_dispersion_z(mean, dispersion)
    # 40 equal-mean genes -> 20 bins of 2, each pair z-scores to [-1, +1].
    assert np.allclose(z, np.tile([-1.0, 1.0], 20))


def test_region_for_gene_filters_and_clips():
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    assert builder.region_for_gene("chr21", 1000, 2000, 2000) == ("chr21", 0, 4000)
    assert builder.region_for_gene("chrX", 100, 200, 0) == ("chrX", 100, 200)
    assert builder.region_for_gene("chrY", 100, 200, 0) is None
    assert builder.region_for_gene("GL000009.2", 1, 2, 2000) is None
    assert builder.region_for_gene("chr1", 5000, 1000, 0) is None


def _panorama_table():
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    np = pytest.importorskip("numpy")
    chrom = ["chr21", "chr1", "chr1", "chrY"] + ["chr1"] * 36
    names = ["APP", "RORB", "FOO", "BAR"] + [f"G{i}" for i in range(4, 40)]
    starts = np.array([i * 2000 + 1000 for i in range(40)], dtype=np.int64)
    table = builder.GeneTable(
        gene_ids=np.array([f"g{i}" for i in range(40)], dtype=object),
        names=np.array(names, dtype=object),
        chrom=np.array(chrom, dtype=object),
        start=starts,
        end=starts + 1000,
    )
    dispersion = np.linspace(0.001, 0.5, 40)
    dispersion[2] = 1000.0
    dispersion[5] = 9999.0
    stats = {
        "n_cells": 100,
        "nnz": np.full(40, 10, dtype=np.int64),
        "mean": np.ones(40),
        "dispersion": dispersion,
    }
    stats["nnz"][0] = 50
    return builder, table, stats


def test_select_genes_prioritizes_chr21_then_candidates_then_dispersion():
    builder, table, stats = _panorama_table()
    chosen = builder.select_genes(
        table, stats, AnyChunkIndex(), window=100, flank=0, target_bytes=1_000_000
    )
    selection = chosen["selection"]
    assert selection.indices[:2] == [0, 1]
    assert selection.priority[0] == "chr21_detection"
    assert selection.priority[1] == "candidate"
    assert selection.indices[2] == 2
    assert selection.priority[2] == "dispersion"
    assert 3 not in selection.indices  # non-canonical contig excluded
    assert chosen["blocked"] is False


def test_select_genes_stops_at_planning_budget():
    builder, table, stats = _panorama_table()
    chosen = builder.select_genes(
        table, stats, AnyChunkIndex(), window=100, flank=0, target_bytes=250
    )
    assert chosen["planning_budget"] == 250
    assert len(chosen["selection"].indices) == 2  # mandatory costs 200, next would add 100
    assert chosen["blocked"] is False


def test_select_genes_reports_blocked_when_mandatory_exceeds_target():
    builder, table, stats = _panorama_table()
    chosen = builder.select_genes(
        table, stats, AnyChunkIndex(), window=100, flank=0, target_bytes=150
    )
    assert chosen["fallback_applied"] is True
    assert chosen["blocked"] is True
    assert len(chosen["selection"].indices) == 2


def test_main_builds_bed_json_and_validates(tmp_path):
    builder = load("build_gene_activity_bed", "scripts/build_gene_activity_bed.py")
    h5ad = make_h5ad(
        tmp_path / "tiny.h5ad",
        ["chr21", "chr1"],
        [1000, 1000],
        [2000, 2000],
        ["APP", "RORB"],
        [[1.0, 1.0], [1.0, 1.0], [1.0, 0.0]],
    )
    tbi = tmp_path / "fragment.tbi"
    tbi.write_bytes(make_index_multi([("chr21", [(0, 1)]), ("chr1", [(0, 1)])]))
    vbed = tmp_path / "validation.bed"
    vbed.write_text("chr21\t0\t10\n")
    bed_out = tmp_path / "panel.bed"
    json_out = tmp_path / "panel.json"
    assert (
        builder.main(
            [
                "--h5ad",
                str(h5ad),
                "--index-path",
                str(tbi),
                "--bed-out",
                str(bed_out),
                "--json-out",
                str(json_out),
                "--flank",
                "0",
                "--window",
                "128",
                "--target-bytes",
                "1000000",
                "--reserve-fraction",
                "0",
                "--max-genes",
                "10",
                "--validation-bed",
                str(vbed),
                "--validation-expected-bytes",
                "128",
            ]
        )
        == 0
    )
    report = json.loads(json_out.read_text())
    assert report["n_selected"] == 2
    assert report["priority_counts"] == {"chr21_detection": 1, "candidate": 1}
    assert report["estimated_bytes"] == 256
    assert report["selection_cost_reconciles"] is True
    assert report["blocked"] is False
    assert report["estimator_validation"]["within_tolerance"] is True
    assert bed_out.read_text().splitlines()[0] == "chr21\t1000\t2000\tAPP"
    assert report["bed_sha256"]