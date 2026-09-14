import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "validate_development_head", Path(__file__).parents[1] / "scripts/validate_development_head.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
parse_head_evidence = mod.parse_head_evidence

URL = "https://example.invalid/object.rda.gz"
TS = "2024-01-01T00:00:00Z"


def _hdr(status: int = 200, extra: str = "") -> bytes:
    return f"HTTP/1.1 {status} OK\r\n{extra}Content-Length: 100\r\n\r\n".encode("latin-1")


def test_valid_minimal():
    raw = _hdr()
    r = parse_head_evidence(raw, url=URL, observed_at=TS)
    assert r["record_kind"] == "development_head_metadata"
    assert r["status"] == "SOURCE_METADATA_OBSERVED"
    assert r["url"] == URL
    assert r["observed_at"] == TS
    assert r["http_status"] == 200
    assert r["header_record_sha256"] == hashlib.sha256(raw).hexdigest()
    assert r["header_bytes"] == len(raw)
    assert r["declared_payload_bytes"] == 100
    assert r["etag"] is None
    assert r["last_modified"] is None
    assert r["accept_ranges"] is None
    assert r["publisher_payload_checksum"] is None
    assert r["body_bytes"] == 0
    assert r["scientific_gate_effect"] == "NONE"


def test_mixed_case_headers():
    raw = (
        b'HTTP/1.1 200 OK\r\neTaG:\t "abc" \t\r\n'
        b"LAST-modified: Mon, 01 Jan 2024 00:00:00 GMT\r\n"
        b"accept-RANGES: bytes\r\ncONTENT-lENGTH: 42\r\n\r\n"
    )
    r = parse_head_evidence(raw, url=URL, observed_at=TS)
    assert r["etag"] == '"abc"'
    assert r["last_modified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert r["accept_ranges"] == "bytes"
    assert r["declared_payload_bytes"] == 42


@pytest.mark.parametrize("status", [301, 302, 304, 404, 500])
def test_non_200_rejected(status):
    raw = f"HTTP/1.1 {status} X\r\nContent-Length: 10\r\n\r\n".encode()
    with pytest.raises(ValueError, match="non-200"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_missing_content_length():
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    with pytest.raises(ValueError, match="missing Content-Length"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("second", ["100", "200"])
def test_duplicate_content_length(second):
    raw = _hdr(extra=f"content-LENGTH: {second}\r\n")
    with pytest.raises(ValueError, match="duplicate Content-Length"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("val", ["", "  ", "+5", "-5", "1e5", "1,000", "1,1", "1.5", "0", "000"])
def test_invalid_content_length(val):
    raw = f"HTTP/1.1 200 OK\r\nContent-Length: {val}\r\n\r\n".encode("latin-1")
    with pytest.raises(ValueError):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_unicode_digit_latin1():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: \xb25\r\n\r\n"
    with pytest.raises(ValueError, match="non-ASCII"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("digits", [20, 5000])
def test_excessive_digits(digits):
    raw = f"HTTP/1.1 200 OK\r\nContent-Length: {'1' * digits}\r\n\r\n".encode()
    with pytest.raises(ValueError, match="excessive"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_max_s64_accepted():
    raw = f"HTTP/1.1 200 OK\r\nContent-Length: {2**63 - 1}\r\n\r\n".encode()
    r = parse_head_evidence(raw, url=URL, observed_at=TS)
    assert r["declared_payload_bytes"] == 2**63 - 1


def test_over_max_s64_rejected():
    raw = f"HTTP/1.1 200 OK\r\nContent-Length: {2**63}\r\n\r\n".encode()
    with pytest.raises(ValueError, match="exceeds maximum"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_boundary_65536():
    raw = _hdr(extra="X-Pad: " + "a" * (65536 - len(_hdr(extra="X-Pad: \r\n"))) + "\r\n")
    assert len(raw) == 65536
    r = parse_head_evidence(raw, url=URL, observed_at=TS)
    assert r["header_bytes"] == 65536


def test_boundary_65537_rejected():
    raw = _hdr(extra="X-Pad: " + "a" * (65537 - len(_hdr(extra="X-Pad: \r\n"))) + "\r\n")
    assert len(raw) == 65537
    with pytest.raises(ValueError, match="exceeds maximum size"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("prefix", [" ", "\t"])
def test_folded_header_rejected(prefix):
    raw = _hdr(extra=f"{prefix}X-Folded: yes\r\n")
    with pytest.raises(ValueError, match="folded"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_bare_lf_rejected():
    raw = b"HTTP/1.1 200 OK\nContent-Length: 10\n\n"
    with pytest.raises(ValueError):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("suffix", [b"AB", b"\r\n", _hdr()])
def test_appended_bytes_rejected(suffix):
    raw = _hdr() + suffix
    with pytest.raises(ValueError, match="trailing bytes"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_truncated_terminator():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n"
    with pytest.raises(ValueError, match="missing final"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("name", ["ETag", "Last-Modified", "Accept-Ranges"])
def test_duplicate_optional_rejected(name):
    raw = _hdr(extra=f"{name}: a\r\n{name.lower()}: a\r\n")
    with pytest.raises(ValueError, match=f"duplicate {name.lower()}"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_transfer_encoding_rejected():
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Length: 10\r\n\r\n"
    with pytest.raises(ValueError, match="Transfer-Encoding"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("name", ["Bad Name", "Bad(Name", "Bad/Name", "Bad\xffName", "", "Bad\t"])
def test_invalid_header_name(name):
    raw = _hdr(extra=f"{name}: x\r\n")
    with pytest.raises(ValueError, match="invalid header name"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("control", ["\x00", "\x01", "\x0b", "\x0c", "\x7f"])
def test_control_byte_in_value(control):
    raw = _hdr(extra=f"X-Test: a{control}b\r\n")
    with pytest.raises(ValueError, match="control character"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


def test_hash_changes_with_bytes():
    raw1 = _hdr()
    raw2 = _hdr(extra="X-Extra: 1\r\n")
    r1 = parse_head_evidence(raw1, url=URL, observed_at=TS)
    r2 = parse_head_evidence(raw2, url=URL, observed_at=TS)
    assert r1["header_record_sha256"] != r2["header_record_sha256"]
    assert r1["publisher_payload_checksum"] is None
    assert r2["publisher_payload_checksum"] is None
    assert r1["scientific_gate_effect"] == "NONE"
    assert r2["scientific_gate_effect"] == "NONE"


@pytest.mark.parametrize(
    "url,ts,match",
    [
        ("", TS, "url"),
        (URL, "", "observed_at"),
        ("a\x01b", TS, "control"),
        (URL, "a\x01b", "control"),
        ("a\x7fb", TS, "control"),
        (URL, "a\x80b", "control"),
        ("a\x9fb", TS, "control"),
        (None, TS, "url"),
        (URL, 123, "observed_at"),
    ],
)
def test_invalid_labels(url, ts, match):
    with pytest.raises(ValueError, match=match):
        parse_head_evidence(_hdr(), url=url, observed_at=ts)


@pytest.mark.parametrize("version", [b"HTTP/1.0", b"HTTP/1.1"])
@pytest.mark.parametrize("reason", [b"", b"OK", b"\t\x80\xff"])
def test_valid_status_syntax(version, reason):
    raw = version + b" 200 " + reason + b"\r\nContent-Length: 007\r\n\r\n"
    assert parse_head_evidence(raw, url=URL, observed_at=TS)["declared_payload_bytes"] == 7


@pytest.mark.parametrize(
    "status",
    [
        b"HTTP/1.2 200 OK",
        b"HTTP/1.1junk 200 OK",
        b"HTTP/2.0 200 OK",
        b"HTTP/1.1 200",
        b"HTTP/1.1  200 OK",
        b"HTTP/1.1\t200 OK",
        b"HTTP/1.1 20\xb2 OK",
        b"HTTP/1.1 200 O\nK",
        b"HTTP/1.1 200 O\rK",
        b"HTTP/1.1 200 O\x00K",
        b"HTTP/1.1 200 O\x7fK",
    ],
)
def test_invalid_status_syntax(status):
    raw = status + b"\r\nContent-Length: 1\r\n\r\n"
    with pytest.raises(ValueError, match="malformed status line"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("raw", ["headers", bytearray(_hdr()), memoryview(_hdr())])
def test_non_bytes_rejected(raw):
    with pytest.raises(ValueError, match="must be bytes"):
        parse_head_evidence(raw, url=URL, observed_at=TS)


@pytest.mark.parametrize("extra", ["No-Colon\r\n", "X-Test: a\nb\r\n", "X-Test: a\rb\r\n"])
def test_malformed_field_rejected(extra):
    with pytest.raises(ValueError, match="malformed header|bare LF or CR"):
        parse_head_evidence(_hdr(extra=extra), url=URL, observed_at=TS)


def test_latin1_values_and_token_names_preserved():
    raw = _hdr(extra="ETag: \t\xa0\x80\xff\t\xa0 \t\r\n!#$%&'*+-.^_`|~: ignored\r\n")
    r = parse_head_evidence(raw, url=" caller label ", observed_at=" caller time ")
    assert r["etag"] == "\xa0\x80\xff\t\xa0"
    assert r["url"] == " caller label "
    assert r["observed_at"] == " caller time "
