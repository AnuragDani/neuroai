"""Offline tests for the bounded fragment/index header validation."""

import gzip
import importlib.util
import struct
from pathlib import Path


def module():
    spec = importlib.util.spec_from_file_location(
        "validate_fragment_join",
        Path(__file__).parents[1] / "scripts/validate_fragment_join.py",
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_decompress_prefix_ignores_truncated_tail():
    reader = module()
    # BGZF is a series of gzip members; a byte-capped prefix ends mid-member.
    block = gzip.compress(b"hello world\n" * 100, mtime=0)
    blob = block + block + block[:-4]
    out = reader.decompress_prefix(blob, 5000)
    assert out.startswith(b"hello world\n")
    assert len(out) <= 5000


def test_parse_fragment_lines_drops_partial_tail_and_counts_bad_rows():
    reader = module()
    text = (
        "chr1\t100\t200\tB10C1Q_AAAA-1\t2\n"
        "chr1\t300\t250\tB10C1Q_BBBB-1\t1\n"  # end <= start
        "chr1\t500\t600\tB10C1Q_CCCC-1\t0\n"  # nonpositive count
        "chr1\t700\t800\tB10C1Q_DDDD-1\t3\n"
        "chr1\t900\t1000\tB10C1Q_EEEE"  # partial trailing row
    )
    summary = reader.parse_fragment_lines(text)
    assert summary["n_rows"] == 3
    assert summary["n_bad_rows"] == 1
    assert summary["n_nonpositive_counts"] == 1
    assert summary["n_unique_barcodes"] == 3
    assert summary["has_library_prefix"] is True
    assert summary["all_suffix_minus1"] is True


def test_parse_tabix_header_roundtrip():
    reader = module()
    names = b"chr1\x00chr2\x00"
    header = reader.TABIX_MAGIC + struct.pack("<8i", 2, 65536, 1, 2, 3, 35, 0, len(names)) + names
    parsed = reader.parse_tabix_header(header)
    assert parsed["magic_ok"] is True
    assert parsed["n_ref"] == 2
    assert parsed["format"] == 65536
    assert (parsed["col_seq"], parsed["col_beg"], parsed["col_end"]) == (1, 2, 3)
    assert parsed["names"] == "chr1\x00chr2"


def test_parse_tabix_header_rejects_non_tabix():
    reader = module()
    parsed = reader.parse_tabix_header(b"\x1f\x8b\x08\x04")
    assert parsed["magic_ok"] is False


def test_validate_join_flags_unknown_and_reports_coverage():
    reader = module()
    allowlist = {"B10C1Q_AAAA-1", "B10C1Q_BBBB-1"}
    complete = reader.validate_join(["B10C1Q_AAAA-1", "B10C1Q_BBBB-1", "B10C1Q_AAAA-1"], allowlist)
    assert complete["complete_coverage"] is True
    assert complete["n_unknown"] == 0
    partial = reader.validate_join(["B10C1Q_AAAA-1", "rawbarcode"], allowlist)
    assert partial["complete_coverage"] is False
    assert partial["unknown_examples"] == ["rawbarcode"]


def test_run_validation_uses_injected_transport(monkeypatch):
    reader = module()
    frag_text = b"chr1\t100\t200\tB10C1Q_AAAA-1\t1\n" * 50
    frag_blob = gzip.compress(frag_text, mtime=0)
    names = b"chr1\x00"
    tbi_plain = (
        reader.TABIX_MAGIC + struct.pack("<8i", 1, 65536, 1, 2, 3, 35, 0, len(names)) + names
    )
    tbi_blob = gzip.compress(tbi_plain, mtime=0)

    def fake_head(url, timeout=30.0):
        size = len(frag_blob) if url.endswith(".bgz") else len(tbi_blob)
        return {"content-length": str(size), "accept-ranges": "bytes"}

    def fake_range(url, start, end, timeout=60.0):
        blob = frag_blob if url.endswith(".bgz") else tbi_blob
        return blob[start : end + 1]

    monkeypatch.setattr(reader, "head_headers", fake_head)
    monkeypatch.setattr(reader, "range_bytes", fake_range)
    result = reader.run_validation(
        fragment_url="https://example.test/x-fragment.tsv.bgz",
        index_url="https://example.test/x-fragment.tsv.bgz.tbi",
        allowlist={"B10C1Q_AAAA-1"},
    )
    assert result["status"] == "PASS"
    assert result["join"]["complete_coverage"] is True
    assert result["index"]["magic_ok"] is True
