"""Offline tests for the development ATAC count-matrix adapter."""

import importlib.util
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def bgzf_block(data: bytes) -> bytes:
    compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
    cdata = compressor.compress(data) + compressor.flush()
    total = 12 + 6 + len(cdata) + 8
    bsize = total - 1
    header = b"\x1f\x8b\x08\x04" + b"\x00\x00\x00\x00" + b"\x00\xff"
    extra = b"BC" + struct.pack("<H", 2) + struct.pack("<H", bsize)
    trailer = struct.pack("<I", zlib.crc32(data) & 0xFFFFFFFF) + struct.pack(
        "<I", len(data) & 0xFFFFFFFF
    )
    return header + struct.pack("<H", len(extra)) + extra + cdata + trailer


def build_fixture(rows: list[str]):
    half = max(1, len(rows) // 2)
    first = ("\n".join(rows[:half]) + "\n").encode()
    second = ("\n".join(rows[half:]) + "\n").encode()
    block0, block1 = bgzf_block(first), bgzf_block(second)
    blob = block0 + block1
    chunk_end = (len(blob) - 1) << 16
    names = b"chr1\x00"
    header = struct.pack("<8i", 1, 65536, 1, 2, 3, 35, 0, len(names))
    index = bytearray(b"TBI\x01" + header + names)
    index += struct.pack("<i", 1)
    index += struct.pack("<I", 0)
    index += struct.pack("<i", 1)
    index += struct.pack("<QQ", 0, chunk_end)
    index += struct.pack("<i", 1)
    index += struct.pack("<Q", 0)
    return blob, bytes(index)


def slice_transport(blob: bytes):
    def transport(_url, start, end):
        return blob[start : end + 1]

    return transport


def test_quantify_regions_concurrent_matrix():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    rows = [
        "chr1\t10\t20\tbcA\t2",
        "chr1\t30\t40\tbcB\t1",
        "chr1\t15\t25\tbcA\t3",
    ]
    blob, index_raw = build_fixture(rows)
    index = qfr.TabixIndex.from_bytes(index_raw)
    cells = ["bcA", "bcB", "bcC"]
    records, _stats, matrix = module.quantify_regions(
        [("chr1", 0, 100)],
        cells,
        index,
        "fixture",
        transport=slice_transport(blob),
        workers=4,
    )
    assert matrix.shape == (1, 3)
    assert matrix.toarray().tolist() == [[5, 1, 0]]
    assert records[0]["join_complete"] is True
    assert records[0]["n_unknown"] == 0


def test_quantify_regions_marks_unknown_barcodes():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    blob, index_raw = build_fixture(["chr1\t10\t20\tbcZ\t1"])
    index = qfr.TabixIndex.from_bytes(index_raw)
    records, _stats, matrix = module.quantify_regions(
        [("chr1", 0, 100)],
        ["bcA"],
        index,
        "fixture",
        transport=slice_transport(blob),
        workers=1,
    )
    assert records[0]["n_unknown"] == 1
    assert records[0]["join_complete"] is False
    assert matrix.nnz == 0


def test_quantify_regions_rejects_empty_and_bad_workers():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    blob, index_raw = build_fixture(["chr1\t10\t20\tbcA\t1"])
    index = qfr.TabixIndex.from_bytes(index_raw)
    try:
        module.quantify_regions([], ["bcA"], index, "fixture", transport=slice_transport(blob))
    except ValueError as error:
        assert "region" in str(error)
    else:
        raise AssertionError("empty region list must be refused")
    try:
        module.quantify_regions(
            [("chr1", 0, 100)],
            ["bcA"],
            index,
            "fixture",
            transport=slice_transport(blob),
            workers=0,
        )
    except ValueError as error:
        assert "workers" in str(error)
    else:
        raise AssertionError("zero workers must be refused")


def test_main_refuses_existing_output(tmp_path, monkeypatch):
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    regions = tmp_path / "regions.bed"
    regions.write_text("chr1\t0\t100\n")
    out = tmp_path / "out.json"
    out.write_text("{}\n")
    try:
        module.main(
            [
                "--regions-file",
                str(regions),
                "--index-path",
                str(regions),
                "--counts-out",
                str(tmp_path / "counts"),
                "--out",
                str(out),
            ]
        )
    except SystemExit as error:
        assert "overwrite" in str(error)
    else:
        raise AssertionError("existing output must be refused")
