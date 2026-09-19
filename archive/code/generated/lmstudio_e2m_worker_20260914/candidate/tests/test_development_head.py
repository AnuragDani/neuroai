import importlib.util
import hashlib
from pathlib import Path

import pytest


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "validate_development_head",
        Path(__file__).parents[1] / "scripts" / "validate_development_head.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _make_headers(status_line="HTTP/1.1 200 OK", headers=None):
    if headers is None:
        headers = []
    lines = [status_line]
    for name, value in headers:
        lines.append(f"{name}: {value}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")


def test_valid_200_mixed_case_headers():
    raw = _make_headers(
        headers=[
            ("Content-Length", "1234"),
            ("ETag", '"abc123"'),
            ("Last-Modified", "Wed, 21 Oct 2015 07:28:00 GMT"),
            ("Accept-Ranges", "bytes"),
        ]
    )
    result = mod.parse_head_evidence(
        raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    assert result["record_kind"] == "development_head_metadata"
    assert result["status"] == "SOURCE_METADATA_OBSERVED"
    assert result["url"] == "https://example.invalid/object.rda.gz"
    assert result["observed_at"] == "2024-01-01T00:00:00Z"
    assert result["http_status"] == 200
    assert result["header_record_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["header_bytes"] == len(raw)
    assert result["declared_payload_bytes"] == 1234
    assert result["etag"] == '"abc123"'
    assert result["last_modified"] == "Wed, 21 Oct 2015 07:28:00 GMT"
    assert result["accept_ranges"] == "bytes"
    assert result["publisher_payload_checksum"] is None
    assert result["body_bytes"] == 0
    assert result["scientific_gate_effect"] == "NONE"


def test_optional_validators_absent():
    raw = _make_headers(headers=[("Content-Length", "100")])
    result = mod.parse_head_evidence(
        raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    assert result["etag"] is None
    assert result["last_modified"] is None
    assert result["accept_ranges"] is None


@pytest.mark.parametrize("status", [301, 302, 304, 404, 500])
def test_non_200_rejection(status):
    raw = _make_headers(status_line=f"HTTP/1.1 {status} Status", headers=[("Content-Length", "100")])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_missing_content_length():
    raw = _make_headers(headers=[("ETag", '"abc"')])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_duplicate_content_length():
    raw = _make_headers(headers=[("Content-Length", "100"), ("Content-Length", "100")])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_invalid_content_length_unicode_digit():
    # U+0661 Arabic-Indic Digit One, encoded as Latin-1 byte 0x61? No, Latin-1 doesn't have it.
    # Let's use a byte that is not ASCII digit. E.g. 0xC1 (Latin-1 A with acute)
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: \xc100\r\n\r\n"
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_extremely_long_digits():
    raw = _make_headers(headers=[("Content-Length", "1" * 20)])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_max_signed_64_bit_accepted():
    max_val = 2**63 - 1
    raw = _make_headers(headers=[("Content-Length", str(max_val))])
    result = mod.parse_head_evidence(
        raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    assert result["declared_payload_bytes"] == max_val


def test_larger_than_max_signed_64_bit_rejected():
    raw = _make_headers(headers=[("Content-Length", str(2**63))])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_boundary_65536_bytes():
    # Construct a header block exactly 65536 bytes
    # "HTTP/1.1 200 OK\r\n" is 16 bytes.
    # "Content-Length: 100\r\n" is 21 bytes.
    # "\r\n" is 2 bytes.
    # Total so far: 39 bytes.
    # Need 65536 - 39 = 65497 bytes of padding in a header value.
    padding = "A" * 65497
    raw = _make_headers(headers=[("Content-Length", "100"), ("X-Pad", padding)])
    assert len(raw) == 65536
    result = mod.parse_head_evidence(
        raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    assert result["header_bytes"] == 65536


def test_boundary_65537_bytes():
    padding = "A" * 65498
    raw = _make_headers(headers=[("Content-Length", "100"), ("X-Pad", padding)])
    assert len(raw) == 65537
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_folded_headers_rejected():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n X-Folded: value\r\n\r\n"
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_duplicate_optional_field_rejected():
    raw = _make_headers(headers=[("Content-Length", "100"), ("ETag", '"a"'), ("ETag", '"b"')])
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_appended_body_rejected():
    raw = _make_headers(headers=[("Content-Length", "100")]) + b"BODY"
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_truncated_terminator_rejected():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n"
    with pytest.raises(ValueError):
        mod.parse_head_evidence(
            raw, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
        )


def test_hash_changes_with_bytes():
    raw1 = _make_headers(headers=[("Content-Length", "100")])
    raw2 = _make_headers(headers=[("Content-Length", "101")])
    r1 = mod.parse_head_evidence(
        raw1, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    r2 = mod.parse_head_evidence(
        raw2, url="https://example.invalid/object.rda.gz", observed_at="2024-01-01T00:00:00Z"
    )
    assert r1["header_record_sha256"] != r2["header_record_sha256"]
    assert r1["publisher_payload_checksum"] is None
    assert r1["scientific_gate_effect"] == "NONE"
