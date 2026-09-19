"""Validate one captured HTTP/1.x header block; never make a network request.

This is a strict metadata subset, not a general HTTP client. Duplicate observed
fields and Transfer-Encoding are refused by policy, not by universal HTTP rules.
"""

import hashlib
import re

MAX_BYTES = 65536
MAX_CL_DIGITS = 19
MAX_CL_VALUE = 2**63 - 1


def _validate_label(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        raise ValueError(f"{name} contains control characters")


def _parse_content_length(value: str) -> int:
    if not value:
        raise ValueError("Content-Length is blank")
    if len(value) > MAX_CL_DIGITS:
        raise ValueError("Content-Length has excessive digits")
    if not value.isascii() or not value.isdigit():
        raise ValueError("Content-Length contains non-ASCII digits or invalid characters")
    n = int(value)
    if n < 1:
        raise ValueError("Content-Length must be positive")
    if n > MAX_CL_VALUE:
        raise ValueError("Content-Length exceeds maximum")
    return n


def parse_head_evidence(raw_headers: bytes, *, url: str, observed_at: str) -> dict:
    """Return metadata or raise ValueError for an unsupported/invalid capture.

    URL/time are caller labels, not verified provenance. The size cap applies to
    this already-captured record; it proves no transport, deadline or RAM bound.
    body_bytes=0 describes this input only. Length/validators/header hash do not
    establish payload integrity, contents, decoded size or scientific acceptance.
    """
    if not isinstance(raw_headers, bytes):
        raise ValueError("raw_headers must be bytes")
    if len(raw_headers) > MAX_BYTES:
        raise ValueError("raw_headers exceeds maximum size")
    _validate_label(url, "url")
    _validate_label(observed_at, "observed_at")

    end = raw_headers.find(b"\r\n\r\n")
    if end < 0:
        raise ValueError("missing final CRLF CRLF terminator")
    if end != len(raw_headers) - 4:
        raise ValueError("trailing bytes after headers")

    lines = raw_headers[:end].split(b"\r\n")
    status = re.fullmatch(rb"HTTP/1\.[01] ([0-9]{3}) [\t\x20-\x7e\x80-\xff]*", lines[0])
    if status is None:
        raise ValueError("malformed status line")
    http_status = int(status[1])
    if http_status != 200:
        raise ValueError(f"non-200 status: {http_status}")

    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        if not line:
            raise ValueError("empty header line")
        if line.startswith(b" ") or line.startswith(b"\t"):
            raise ValueError("obsolete folded header")
        if b"\r" in line or b"\n" in line:
            raise ValueError("bare LF or CR in header")
        if b":" not in line:
            raise ValueError("malformed header line")
        name_bytes, value_bytes = line.split(b":", 1)
        if re.fullmatch(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name_bytes) is None:
            raise ValueError(f"invalid header name: {name_bytes!r}")
        name = name_bytes.decode("ascii")
        value = value_bytes.decode("latin-1").strip(" \t")
        if any((ord(c) < 32 and c != "\t") or ord(c) == 127 for c in value):
            raise ValueError(f"control character in header value: {name!r}")
        headers.setdefault(name.lower(), []).append(value)

    if "transfer-encoding" in headers:
        raise ValueError("Transfer-Encoding is not allowed")

    cl_values = headers.get("content-length")
    if cl_values is None:
        raise ValueError("missing Content-Length")
    if len(cl_values) > 1:
        raise ValueError("duplicate Content-Length")
    if "," in cl_values[0]:
        raise ValueError("Content-Length contains comma list")
    declared_payload_bytes = _parse_content_length(cl_values[0])

    def _single(name: str) -> str | None:
        vals = headers.get(name)
        if vals is None:
            return None
        if len(vals) > 1:
            raise ValueError(f"duplicate {name} header")
        return vals[0]

    return {
        "record_kind": "development_head_metadata",
        "status": "SOURCE_METADATA_OBSERVED",
        "url": url,
        "observed_at": observed_at,
        "http_status": 200,
        "header_record_sha256": hashlib.sha256(raw_headers).hexdigest(),
        "header_bytes": len(raw_headers),
        "declared_payload_bytes": declared_payload_bytes,
        "etag": _single("etag"),
        "last_modified": _single("last-modified"),
        "accept_ranges": _single("accept-ranges"),
        "publisher_payload_checksum": None,
        "body_bytes": 0,
        "scientific_gate_effect": "NONE",
    }
