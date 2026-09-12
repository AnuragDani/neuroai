#!/usr/bin/env python
"""Resolve one pinned release declaration. Never fetch its count payload."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import signal
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zlib
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BAG_URL = (
    "https://data.nemoarchive.org/publication_release/"
    "Vuong_delaTorre_Human_snMultiome-2026-05-04/"
    "Analysis_bag_3_Vuong_delaTorre_Human_snMultiome_Analysis_ATAC_Open.tgz"
)
BAG_BYTES = 1867
BAG_SHA256 = "4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45"
MAX_BODY = 65536
MAX_DECODED = 262144
NETWORK_SECONDS = 15
EVIDENCE_PATH = ROOT / "reports/generated/paired_public_recheck_2026-09-09/verification.md"
EVIDENCE_SHA256 = "a1cb7c35b1245bbb6a34d9bd63e337cc3c8a0c4baa3258b681ace943c6e1700e"
TARGET = {
    "filename": "VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz",
    "bytes": 1540753269,
    "md5": "796c8b3aa587b257af0a46615a437dba",
}
HEADER_NAMES = ("Content-Length", "Content-Encoding", "ETag", "Last-Modified")


class Refusal(ValueError):
    """A bounded, reportable source outcome."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise Refusal("UNSAFE_ARCHIVE_PATH")
    return path


def validate_bag(raw: bytes, report: dict) -> dict:
    """Replay only the tiny pinned bag; no network or on-disk extraction."""
    if len(raw) != BAG_BYTES or digest(raw) != BAG_SHA256:
        raise Refusal("SOURCE_EVIDENCE_CHANGED")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decoded = decoder.decompress(raw, MAX_DECODED)
    report["decoded_bytes"] = len(decoded)
    if decoder.unconsumed_tail:
        raise Refusal("DECODED_BYTE_LIMIT")
    if not decoder.eof or decoder.unused_data:
        raise Refusal("INVALID_GZIP")
    texts, seen, total = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(decoded), mode="r:") as archive:
        for member in archive:
            path = safe_path(member.name)
            if path in seen:
                raise Refusal("DUPLICATE_ARCHIVE_PATH")
            seen.add(path)
            if not (member.isfile() or member.isdir()) or member.issparse():
                raise Refusal("UNSAFE_ARCHIVE_MEMBER")
            total += member.size
            if total > len(decoded) or len(seen) > 512:
                raise Refusal("ARCHIVE_MEMBER_LIMIT")
            if path.name in ("fetch.txt", "manifest-md5.txt") and member.isfile():
                if path.name in texts:
                    raise Refusal("AMBIGUOUS_MANIFEST")
                if report["decoded_bytes"] + member.size > MAX_DECODED:
                    raise Refusal("DECODED_BYTE_LIMIT")
                with archive.extractfile(member) as stream:
                    text = stream.read(member.size)
                report["decoded_bytes"] += len(text)
                if len(text) != member.size:
                    raise Refusal("TRUNCATED_MEMBER")
                texts[path.name] = (path, text.decode("utf-8"))
    if set(texts) != {"fetch.txt", "manifest-md5.txt"}:
        raise Refusal("MISSING_MANIFEST")
    fetch_path, fetch_text = texts["fetch.txt"]
    md5_path, md5_text = texts["manifest-md5.txt"]
    if fetch_path.parent != md5_path.parent:
        raise Refusal("MANIFEST_ROOT_MISMATCH")
    rows = []
    for line in fetch_text.splitlines():
        if not line.strip():
            continue
        url, size, name = line.split(maxsplit=2)
        path = safe_path(name)
        if path.name == TARGET["filename"]:
            rows.append((url, size, str(path)))
    if len(rows) != 1:
        raise Refusal("TARGET_ROW_COUNT")
    url, size, payload_path = rows[0]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.fragment:
        raise Refusal("INVALID_PAYLOAD_URL")
    checksums = []
    for line in md5_text.splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(maxsplit=1)
        if str(safe_path(name)) == payload_path:
            checksums.append(checksum)
    if size != str(TARGET["bytes"]) or checksums != [TARGET["md5"]]:
        raise Refusal("PAYLOAD_DECLARATION_MISMATCH")
    report["matched_members"] = [str(fetch_path), str(md5_path)]
    return {"url": url, "path": payload_path, "bytes": int(size), "md5": checksums[0]}


def fetch_bag(report: dict, *, opener=None) -> bytes:
    """POSIX main-thread deadline includes DNS and stalled reads, not just sockets."""
    if not hasattr(signal, "setitimer") or signal.getitimer(signal.ITIMER_REAL)[0]:
        raise Refusal("DEADLINE_UNAVAILABLE")

    def timeout(signum, frame):
        raise TimeoutError("network deadline")

    old_handler = signal.signal(signal.SIGALRM, timeout)
    start = time.monotonic()
    raw = bytearray()
    request = urllib.request.Request(BAG_URL, headers={"Accept-Encoding": "identity"})
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        signal.setitimer(signal.ITIMER_REAL, NETWORK_SECONDS)
        report["request_attempted"] = True
        ledger = {"method": "GET", "url": BAG_URL, "status": None, "body_bytes": 0}
        report["requests"].append(ledger)
        try:
            response = opener.open(request, timeout=NETWORK_SECONDS)
        except urllib.error.HTTPError as error:
            ledger["status"] = error.code
            report["headers"] = {name: error.headers.get(name) for name in HEADER_NAMES}
            error.close()
            raise Refusal("HTTP_REFUSAL") from error
        with response:
            ledger["status"] = response.status
            report["headers"] = {name: response.headers.get(name) for name in HEADER_NAMES}
            if response.status != 200:
                raise Refusal("HTTP_REFUSAL")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise Refusal("HTTP_ENCODING_REFUSAL")
            length = response.headers.get("Content-Length")
            if length is not None and length != str(BAG_BYTES):
                raise Refusal("SOURCE_EVIDENCE_CHANGED")
            while len(raw) < MAX_BODY:
                chunk = response.read1(min(4096, MAX_BODY - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                report["body_bytes"] = ledger["body_bytes"] = len(raw)
                if time.monotonic() - start >= NETWORK_SECONDS:
                    raise TimeoutError("network deadline")
            else:
                raise Refusal("BODY_BYTE_LIMIT")
        return bytes(raw)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        report["elapsed_seconds"] = time.monotonic() - start
        report["body_sha256"] = digest(raw) if raw else None


def resolve(output: Path, *, opener=None, command=None) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "record_kind": "nemo_source_identity",
        "created_utc": datetime.now(UTC).isoformat(),
        "command": command or ["resolve_nemo_source.py", "--output-dir", str(output)],
        "code_sha256": digest(Path(__file__).read_bytes()),
        "source_evidence": {"path": str(EVIDENCE_PATH), "sha256": EVIDENCE_SHA256},
        "bag_url": BAG_URL,
        "expected_bag": {"bytes": BAG_BYTES, "sha256": BAG_SHA256},
        "declared_payload": TARGET.copy(),
        "limits": {
            "body_bytes": MAX_BODY,
            "decoded_bytes": MAX_DECODED,
            "network_seconds": NETWORK_SECONDS,
        },
        "request_attempted": False,
        "requests": [],
        "headers": {name: None for name in HEADER_NAMES},
        "body_bytes": 0,
        "decoded_bytes": 0,
        "elapsed_seconds": 0,
        "body_sha256": None,
        "raw_bag_path": None,
        "matched_members": [],
        "resolved_payload": None,
        "stop_reason": "SOURCE_IDENTITY_UNRESOLVED",
    }
    try:
        if not EVIDENCE_PATH.is_file() or digest(EVIDENCE_PATH.read_bytes()) != EVIDENCE_SHA256:
            raise Refusal("SOURCE_IDENTITY_UNRESOLVED")
        raw = fetch_bag(report, opener=opener)
        if len(raw) != BAG_BYTES or digest(raw) != BAG_SHA256:
            raise Refusal("SOURCE_EVIDENCE_CHANGED")
        (output / "source-bag.tgz").write_bytes(raw)
        report["raw_bag_path"] = "source-bag.tgz"
        report["resolved_payload"] = validate_bag(raw, report)
        report["stop_reason"] = "RESOLVED"
    except TimeoutError:
        report["stop_reason"] = "NETWORK_DEADLINE"
    except Refusal as error:
        report["stop_reason"] = str(error)
    except (OSError, urllib.error.URLError) as error:
        report["stop_reason"] = "TRANSPORT_OR_IO_FAILURE"
        report["error"] = str(error)
    except (ValueError, UnicodeError, tarfile.TarError, zlib.error) as error:
        report["stop_reason"] = "INVALID_SOURCE_METADATA"
        report["error"] = str(error)
    (output / "source_identity.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = resolve(args.output_dir, command=sys.argv)
    except FileExistsError:
        parser.error("output directory already exists; choose a new directory")
    print(result["stop_reason"])
    return 0 if result["stop_reason"] == "RESOLVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
