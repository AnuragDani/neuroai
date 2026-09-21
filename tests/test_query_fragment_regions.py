"""Offline tests for bounded remote tabix region queries."""

import gzip
import importlib.util
import struct
import sys
import zlib
from pathlib import Path


def module():
    spec = importlib.util.spec_from_file_location(
        "query_fragment_regions",
        Path(__file__).parents[1] / "scripts/query_fragment_regions.py",
    )
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


def build_fixture(rows: list[str]) -> tuple[bytes, bytes, int, int]:
    """Return (fragment_blob, tabix_raw, first_block_offset, last_block_offset)."""
    # Split rows across two BGZF blocks so continuation is exercised.
    half = max(1, len(rows) // 2)
    first = ("\n".join(rows[:half]) + "\n").encode()
    second = ("\n".join(rows[half:]) + "\n").encode()
    block0 = bgzf_block(first)
    block1 = bgzf_block(second)
    blob = block0 + block1
    first_off, last_off = 0, len(block0)
    chunk_end = (len(blob) - 1) << 16
    names = b"chr1\x00"
    header = struct.pack(
        "<8i",
        1,
        65536,
        1,
        2,
        3,
        35,
        0,
        len(names),
    )
    index = bytearray(b"TBI\x01" + header + names)
    index += struct.pack("<i", 1)  # n_bin
    index += struct.pack("<I", 0)  # bin id
    index += struct.pack("<i", 1)  # n_chunk
    index += struct.pack("<QQ", 0, chunk_end)
    index += struct.pack("<i", 1)  # n_intv
    index += struct.pack("<Q", 0)
    return blob, bytes(index), first_off, last_off


def slice_transport(blob: bytes):
    def transport(_url, start, end):
        return blob[start : end + 1]

    return transport


def test_reg2bins_basic():
    reader = module()
    assert reader.reg2bins(0, 16384) == [0, 1, 9, 73, 585, 4681]
    assert reader.reg2bins(0, 0) == []
    assert reader.reg2bins(100, 100) == []
    # A region spanning several 16 kb windows contributes many level-4 bins.
    bins = reader.reg2bins(0, 65536)
    assert len(bins) > 6
    assert 4681 in bins and 4684 in bins


def test_tabix_index_round_trip_raw_and_gzipped():
    reader = module()
    _blob, index_raw, _a, _b = build_fixture(["chr1\t1\t2\tc-1\t1"])
    parsed = reader.TabixIndex.from_bytes(index_raw)
    assert parsed.names == ["chr1"]
    assert parsed.header["n_ref"] == 1
    assert parsed.header["col_beg"] == 2
    zipped = gzip.compress(index_raw, mtime=0)
    parsed2 = reader.TabixIndex.from_bytes(zipped)
    assert parsed2.names == parsed.names
    assert parsed2.refs["chr1"][1] == parsed.refs["chr1"][1]


def test_tabix_index_rejects_non_tabix():
    reader = module()
    try:
        reader.TabixIndex.from_bytes(b"not-a-tabix-index")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_parse_bgzf_members_ignores_truncated_tail():
    reader = module()
    block = bgzf_block(b"chr1\t1\t2\tc-1\t1\n")
    members, consumed = reader.parse_bgzf_members(block + block[:-3], 0)
    assert len(members) == 1
    assert consumed == len(block)
    assert members[0][1].startswith(b"chr1")


def test_query_region_returns_overlapping_rows():
    reader = module()
    rows = [
        "chr1\t50\t150\tlibA_AAAA-1\t2",
        "chr1\t100\t200\tlibB_BBBB-1\t1",
        "chr1\t400\t500\tlibA_CCCC-1\t3",
    ]
    blob, index_raw, _a, _b = build_fixture(rows)
    index = reader.TabixIndex.from_bytes(index_raw)
    stats = reader.query_region(
        "memory://frag", index, "chr1", 90, 210, transport=slice_transport(blob), window=4096
    )
    assert stats.rows == 2
    assert stats.rows_by_barcode == {"libA_AAAA-1": 2, "libB_BBBB-1": 1}
    assert stats.requests >= 1


def test_query_region_continuation_across_blocks():
    reader = module()
    rows = [f"chr1\t{i * 10}\t{i * 10 + 5}\tlibA_{i:04d}-1\t1" for i in range(200)]
    blob, index_raw, _first_off, second_block_off = build_fixture(rows)
    index = reader.TabixIndex.from_bytes(index_raw)
    # A window equal to one block forces a second transport request for block 1.
    stats = reader.query_region(
        "memory://frag",
        index,
        "chr1",
        0,
        5000,
        transport=slice_transport(blob),
        window=second_block_off,
        max_bytes=10 * 1024**2,
    )
    assert stats.rows == 200
    assert stats.requests >= 2
    assert stats.truncated is False


def test_query_region_max_bytes_refuses():
    reader = module()
    rows = [f"chr1\t{i}\t{i + 1}\tlibA_{i:04d}-1\t1" for i in range(100)]
    blob, index_raw, _a, _b = build_fixture(rows)
    index = reader.TabixIndex.from_bytes(index_raw)
    stats = reader.query_region(
        "memory://frag",
        index,
        "chr1",
        0,
        200,
        transport=slice_transport(blob),
        window=64,
        max_bytes=32,
    )
    assert stats.truncated is True


def test_parse_region_spec_and_rejects():
    reader = module()
    assert reader.parse_region_spec("chr21:100-200") == ("chr21", 100, 200)
    try:
        reader.parse_region_spec("chr21:200-100")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_counts_matrix_places_counts_and_ignores_unknown_cells():
    reader = module()
    cells = ["libA_AAAA-1", "libB_BBBB-1", "libA_CCCC-1"]
    regions = [("chr1", 0, 100), ("chr1", 100, 200)]
    records = [
        {"counts": {"libA_AAAA-1": 2, "libB_BBBB-1": 1, "libZ_ZZZZ-1": 5}},
        {"counts": {"libA_CCCC-1": 3}},
    ]
    matrix = reader.counts_matrix(regions, records, cells)
    assert matrix.shape == (2, 3)
    assert matrix[0].toarray().tolist() == [[2, 1, 0]]
    assert matrix[1].toarray().tolist() == [[0, 0, 3]]
    assert matrix.nnz == 3


def test_query_chunks_merge_and_linear_index_filter():
    reader = module()
    _blob, index_raw, _a, _b = build_fixture(["chr1\t1\t2\tc-1\t1"])
    index = reader.TabixIndex.from_bytes(index_raw)
    assert index.query_chunks("chr1", 0, 100) == [(0, (len(_blob) - 1) << 16)]
    assert index.query_chunks("chrMissing", 0, 100) == []
