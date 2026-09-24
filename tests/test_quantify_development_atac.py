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
    # One count per unique qualifying fragment record (bcA: 2 records, bcB: 1).
    assert matrix.toarray().tolist() == [[2, 1, 0]]
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
        unknown_policy="drop",
    )
    assert records[0]["n_unknown"] == 1
    assert records[0]["unknown_barcodes"] == ["bcZ"]
    assert records[0]["join_complete"] is False
    assert matrix.nnz == 0


def test_quantify_regions_refuses_unknown_barcodes_by_default():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    blob, index_raw = build_fixture(["chr1\t10\t20\tbcZ\t1"])
    index = qfr.TabixIndex.from_bytes(index_raw)
    try:
        module.quantify_regions(
            [("chr1", 0, 100)],
            ["bcA"],
            index,
            "fixture",
            transport=slice_transport(blob),
            workers=1,
        )
    except module.IncompleteQueryError as error:
        assert "retained population" in str(error)
    else:
        raise AssertionError("unknown barcodes must be refused by default")


def test_quantify_regions_refuses_truncated_query():
    """Review case: a short transfer allowance must not yield a usable matrix."""
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    line1 = b"chr1\t100\t200\tbcA\t1\n"
    line2 = b"chr1\t101\t201\tbcA\t1\n"
    block0, block1 = bgzf_block(line1), bgzf_block(line2)
    blob = block0 + block1
    index = qfr.TabixIndex.from_bytes(make_index([(0, (len(block0) << 16) | len(line2))]))
    try:
        module.quantify_regions(
            [("chr1", 100, 200)],
            ["bcA"],
            index,
            "fixture",
            transport=slice_transport(blob),
            window=len(block0),
            max_bytes=len(block0),
            workers=1,
        )
    except module.IncompleteQueryError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("truncated query must be refused before matrix assembly")


def test_quantify_regions_accepts_valid_empty_region():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    blob, index_raw = build_fixture(["chr1\t100\t200\tbcA\t1"])
    index = qfr.TabixIndex.from_bytes(index_raw)
    records, _stats, matrix = module.quantify_regions(
        [("chr1", 5000, 6000)],
        ["bcA"],
        index,
        "fixture",
        transport=slice_transport(blob),
        workers=1,
    )
    assert records[0]["empty_region"] is True
    assert records[0]["join_complete"] is True
    assert records[0]["truncated"] is False
    assert matrix.nnz == 0


def test_quantify_regions_enforces_aggregate_budget():
    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    rows = ["chr1\t10\t20\tbcA\t1", "chr1\t30\t40\tbcA\t1"]
    blob, index_raw = build_fixture(rows)
    index = qfr.TabixIndex.from_bytes(index_raw)
    try:
        module.quantify_regions(
            [("chr1", 0, 100), ("chr1", 200, 300)],
            ["bcA"],
            index,
            "fixture",
            transport=slice_transport(blob),
            workers=1,
            total_max_bytes=16,
        )
    except module.TransferBudgetExceeded:
        pass
    else:
        raise AssertionError("aggregate budget must be enforced")


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


def test_retrying_transport_recovers_from_transient_faults():
    import urllib.error

    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    calls = {"n": 0}

    def flaky(_url, start, end):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("temporary DNS failure")
        return b"x" * (end - start + 1)

    transport = module._RetryingTransport(flaky, retries=4, backoff=0, sleep=lambda _s: None)
    assert transport("u", 0, 3) == b"xxxx"
    assert calls["n"] == 3


def test_retrying_transport_exhausts_and_propagates():
    import urllib.error

    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    calls = {"n": 0}

    def always_fail(_url, _start, _end):
        calls["n"] += 1
        raise urllib.error.URLError("still down")

    transport = module._RetryingTransport(always_fail, retries=2, backoff=0, sleep=lambda _s: None)
    try:
        transport("u", 0, 3)
    except urllib.error.URLError:
        pass
    else:
        raise AssertionError("exhausted retries must propagate the transport fault")
    assert calls["n"] == 3


def test_retrying_transport_does_not_retry_validation_errors():
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    calls = {"n": 0}

    def bad_range(_url, _start, _end):
        calls["n"] += 1
        raise ValueError("server did not honor byte range")

    transport = module._RetryingTransport(bad_range, retries=4, backoff=0, sleep=lambda _s: None)
    try:
        transport("u", 0, 3)
    except ValueError:
        pass
    else:
        raise AssertionError("validation errors must propagate immediately")
    assert calls["n"] == 1


def test_retrying_transport_validates_configuration():
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    for kwargs in ({"retries": -1}, {"backoff": -0.5}):
        try:
            module._RetryingTransport(lambda *_: b"", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid retry configuration must be refused: {kwargs}")


def test_budget_charges_every_retried_attempt():
    """N18 regression: a failed attempt and its retry are both charged."""
    import urllib.error

    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    calls = {"n": 0}

    def flaky(_url, start, end):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("temporary DNS failure")
        return b"y" * (end - start + 1)

    budget = module._BudgetedTransport(flaky, total_max_bytes=200)
    transport = module._RetryingTransport(budget, retries=4, backoff=0, sleep=lambda _s: None)
    assert transport("u", 0, 99) == b"y" * 100
    assert calls["n"] == 2
    # Under Budget(Retry(raw)) the retry would be free and this would read 100.
    assert budget.used == 200


def test_budget_exhaustion_is_not_retried_before_transfer():
    """N18 regression: the retried attempt is refused before any transfer."""
    import urllib.error

    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    calls = {"n": 0}

    def always_fail(_url, _start, _end):
        calls["n"] += 1
        raise urllib.error.URLError("still down")

    budget = module._BudgetedTransport(always_fail, total_max_bytes=100)
    transport = module._RetryingTransport(budget, retries=4, backoff=0, sleep=lambda _s: None)
    try:
        transport("u", 0, 99)
    except module.TransferBudgetExceeded:
        pass
    else:
        raise AssertionError("the retried attempt must be refused by the shared budget")
    assert calls["n"] == 1  # the retry never reached the network
    assert budget.used == 100


def test_quantify_regions_charges_retries_against_the_budget():
    """N18 integration: quantify_regions composes Retry(Budget(raw))."""
    import urllib.error

    qfr = load("query_fragment_regions", "scripts/query_fragment_regions.py")
    module = load("quantify_development_atac", "scripts/quantify_development_atac.py")
    blob, index_raw = build_fixture(["chr1\t10\t20\tbcA\t1"])
    index = qfr.TabixIndex.from_bytes(index_raw)
    calls = {"n": 0}

    def flaky(_url, start, end):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("temporary DNS failure")
        return blob[start : end + 1]

    try:
        module.quantify_regions(
            [("chr1", 0, 100)],
            ["bcA"],
            index,
            "fixture",
            transport=flaky,
            window=len(blob),
            max_bytes=len(blob),
            workers=1,
            total_max_bytes=len(blob),
            transport_retries=1,
        )
    except module.TransferBudgetExceeded:
        pass
    else:
        raise AssertionError("a retried fetch must be charged and refused at the cap")
    assert calls["n"] == 1


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
