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


def make_index(chunks: list[tuple[int, int]]) -> bytes:
    names = b"chr1\x00"
    header = struct.pack("<8i", 1, 65536, 1, 2, 3, 35, 0, len(names))
    index = bytearray(b"TBI\x01" + header + names)
    index += struct.pack("<i", 1)  # n_bin
    index += struct.pack("<I", 0)  # bin id
    index += struct.pack("<i", len(chunks))
    for start, stop in chunks:
        index += struct.pack("<QQ", start, stop)
    index += struct.pack("<i", 1)  # n_intv
    index += struct.pack("<Q", 0)
    return bytes(index)


def slice_transport(blob: bytes):
    def transport(_url, start, end):
        return blob[start : end + 1]

    return transport


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}
        self.read_size = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        self.read_size = size
        if size is None or size < 0:
            return self._body
        return self._body[:size]


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
    # One count per unique qualifying fragment record, not column-five support.
    assert stats.rows_by_barcode == {"libA_AAAA-1": 1, "libB_BBBB-1": 1}
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


def test_record_split_across_two_members_is_one_record():
    """Review case: a complete TSV record split across two valid BGZF members."""
    reader = module()
    line = b"chr1\t100\t200\tlibA_AAAA-1\t1\n"
    cut = 15
    block0, block1 = bgzf_block(line[:cut]), bgzf_block(line[cut:])
    blob = block0 + block1
    index = reader.TabixIndex.from_bytes(make_index([(0, (len(block0) << 16) | len(line[cut:]))]))
    stats = reader.query_region(
        "memory://frag", index, "chr1", 100, 200, transport=slice_transport(blob), window=4096
    )
    assert stats.rows == 1
    assert stats.rows_by_barcode == {"libA_AAAA-1": 1}
    assert stats.truncated is False


def test_fetch_window_beyond_chunk_end_adds_no_extra_counts():
    """Bytes fetched past the chunk's end virtual offset must not be counted."""
    reader = module()
    row_a = b"chr1\t100\t200\tlibA_AAAA-1\t1\n"
    row_b = b"chr1\t101\t201\tlibB_BBBB-1\t1\n"
    block0, block1 = bgzf_block(row_a), bgzf_block(row_b)
    blob = block0 + block1
    # Chunk ends exactly at the start of block1, so only row_a is in range.
    index = reader.TabixIndex.from_bytes(make_index([(0, len(block0) << 16)]))
    stats = reader.query_region(
        "memory://frag", index, "chr1", 90, 210, transport=slice_transport(blob), window=4096
    )
    assert stats.rows == 1
    assert stats.rows_by_barcode == {"libA_AAAA-1": 1}


def test_adjacent_and_overlapping_chunks_do_not_duplicate():
    reader = module()
    rows = [
        "chr1\t10\t20\tlibA_AAAA-1\t1",
        "chr1\t30\t40\tlibB_BBBB-1\t1",
    ]
    blob, _index_raw, _a, _b = build_fixture(rows)
    stop = (len(blob) - 1) << 16
    for chunks in (
        [(0, stop), (stop, stop)],
        [(0, stop), (0, stop)],
    ):
        index = reader.TabixIndex.from_bytes(make_index(chunks))
        stats = reader.query_region(
            "memory://frag", index, "chr1", 0, 100, transport=slice_transport(blob), window=4096
        )
        assert stats.rows == 2
        assert stats.rows_by_barcode == {"libA_AAAA-1": 1, "libB_BBBB-1": 1}


def test_parse_fragment_line_fragment_mode_weights_one():
    reader = module()
    line = b"chr1\t100\t200\tlibA_AAAA-1\t7"
    assert reader.parse_fragment_line(line, "chr1", 100, 200, "fragment") == ("libA_AAAA-1", 1)
    assert reader.parse_fragment_line(line, "chr1", 100, 200, "read_support") == ("libA_AAAA-1", 7)
    # non-overlapping and inverted records are ignored in both modes
    assert reader.parse_fragment_line(line, "chr1", 500, 600, "fragment") is None
    assert reader.parse_fragment_line(b"chr1\t200\t100\tlibA_AAAA-1\t7", "chr1", 100, 200) is None


def test_read_support_mode_reproduces_historical_weighting():
    reader = module()
    blob, index_raw, _a, _b = build_fixture(["chr1\t100\t200\tlibA_AAAA-1\t7"])
    index = reader.TabixIndex.from_bytes(index_raw)
    stats = reader.query_region(
        "memory://frag",
        index,
        "chr1",
        100,
        200,
        transport=slice_transport(blob),
        window=4096,
        count_mode="read_support",
    )
    assert stats.rows_by_barcode == {"libA_AAAA-1": 7}


def test_valid_zero_count_region_is_not_a_failure():
    reader = module()
    blob, index_raw, _a, _b = build_fixture(["chr1\t100\t200\tlibA_AAAA-1\t1"])
    index = reader.TabixIndex.from_bytes(index_raw)
    stats = reader.query_region(
        "memory://frag", index, "chr1", 5000, 6000, transport=slice_transport(blob), window=4096
    )
    assert stats.rows == 0
    assert stats.rows_by_barcode == {}
    assert stats.truncated is False


def _patch_urlopen(reader, response):
    reader._urlopen = lambda request, timeout: response


def test_http_range_refuses_ignored_range():
    reader = module()
    response = FakeResponse(200, b"x" * 1000, {"Content-Length": "1000"})
    _patch_urlopen(reader, response)
    try:
        reader.http_range("https://fixture.invalid/file", 0, 9)
    except ValueError as error:
        assert "honor" in str(error)
    else:
        raise AssertionError("HTTP 200 for a range request must be refused")


def test_http_range_refuses_oversized_body_and_short_read():
    reader = module()
    oversized = FakeResponse(206, b"x" * 1000, {"Content-Length": "1000"})
    _patch_urlopen(reader, oversized)
    try:
        reader.http_range("https://fixture.invalid/file", 0, 9)
    except ValueError as error:
        assert "exceeds" in str(error)
    else:
        raise AssertionError("oversized body must be refused")
    short = FakeResponse(206, b"x" * 4, {"Content-Length": "4"})
    _patch_urlopen(reader, short)
    try:
        reader.http_range("https://fixture.invalid/file", 0, 9)
    except ValueError as error:
        assert "short read" in str(error)
    else:
        raise AssertionError("short read must be refused")


def test_http_range_bounded_read_and_consistent_content_range():
    reader = module()
    body = b"abcdefghij"
    response = FakeResponse(206, body, {"Content-Length": "10", "Content-Range": "bytes 5-14/1000"})
    _patch_urlopen(reader, response)
    payload = reader.http_range("https://fixture.invalid/file", 5, 14)
    assert payload == body
    assert response.read_size == 10
    bad = FakeResponse(206, body, {"Content-Range": "bytes 0-9/1000"})
    _patch_urlopen(reader, bad)
    try:
        reader.http_range("https://fixture.invalid/file", 5, 14)
    except ValueError as error:
        assert "inconsistent" in str(error)
    else:
        raise AssertionError("inconsistent Content-Range must be refused")


def test_http_range_refuses_unsafe_redirect():
    reader = module()
    handler = reader._SafeRedirectHandler()
    request = reader.urllib.request.Request("https://good.invalid/file")
    try:
        handler.redirect_request(request, None, 302, "Found", {}, "http://evil.invalid/file")
    except reader.UnsafeRedirectError:
        pass
    else:
        raise AssertionError("cross-origin redirect must be refused")
