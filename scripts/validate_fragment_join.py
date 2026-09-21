"""Bounded fragment/index header validation for the P22 paired-multiome route.

This is the small, separately scoped measurement identified by the ATAC
feasibility handoff: read only the leading bytes of a public ATAC fragment and
its tabix index, then check that the fragment barcode column resolves against a
cell allowlist. It never reads the whole asset and never writes decoded payload
outside the caller's output directory.

The route gate it tests: the development CELLxGENE fragment must carry
``<library>_<barcode>-1`` values that join to the H5AD ``cell_id`` obs index, and
its ``.tbi`` must be a standard tabix index over the same bgzf stream. A raw or
unprefixed barcode, or an index that is not tabix, blocks the indexed
quantification route.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import struct
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_FRAGMENT_URL = (
    "https://datasets.cellxgene.cziscience.com/"
    "46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz"
)
DEFAULT_INDEX_URL = DEFAULT_FRAGMENT_URL + ".tbi"
DEFAULT_OBS_H5AD = (
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)

TABIX_MAGIC = b"TBI\x01"


def head_headers(url: str, timeout: float = 30.0) -> dict[str, str]:
    """Return lower-cased response headers from a HEAD request."""
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return {key.lower(): value for key, value in response.headers.items()}


def range_bytes(url: str, start: int, end: int, timeout: float = 60.0) -> bytes:
    """Fetch the inclusive byte range ``start..end`` and return the body."""
    if start < 0 or end < start:
        raise ValueError("invalid byte range")
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def decompress_prefix(blob: bytes, limit: int, chunk_size: int = 65_536) -> bytes:
    """Decompress the leading bytes of a (b)gzip stream, ignoring truncation.

    Reads in bounded chunks so complete BGZF members before a truncated member
    are retained instead of being discarded by a single failing ``read`` call.
    """
    out = bytearray()
    stream = gzip.GzipFile(fileobj=io.BytesIO(blob))
    while len(out) < limit:
        try:
            chunk = stream.read1(chunk_size)
        except (EOFError, OSError, gzip.BadGzipFile):
            break
        if not chunk:
            break
        out.extend(chunk)
    return bytes(out[:limit])


def parse_tabix_header(blob: bytes) -> dict:
    """Parse the fixed tabix header from an uncompressed ``.tbi`` payload."""
    if len(blob) < 36 or blob[:4] != TABIX_MAGIC:
        return {"magic_ok": False, "raw_prefix": blob[:4].hex()}
    (
        n_ref,
        fmt,
        col_seq,
        col_beg,
        col_end,
        meta,
        skip,
        l_nm,
    ) = struct.unpack("<8i", blob[4:36])
    names = blob[36 : 36 + l_nm]
    return {
        "magic_ok": True,
        "n_ref": n_ref,
        "format": fmt,
        "col_seq": col_seq,
        "col_beg": col_beg,
        "col_end": col_end,
        "meta": meta,
        "skip": skip,
        "l_nm": l_nm,
        "names": names.rstrip(b"\x00").decode("ascii", "replace"),
    }


def parse_fragment_lines(text: str) -> dict:
    """Summarize fragment rows: barcodes, interval form and count semantics."""
    barcodes: list[str] = []
    n_rows = 0
    bad_rows: list[str] = []
    nonpositive_counts = 0
    coords: list[tuple[int, int]] = []
    # A byte-capped prefix can end mid-record; drop the trailing partial line.
    if text and not text.endswith("\n"):
        text = text.rsplit("\n", 1)[0]
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 5:
            bad_rows.append(line)
            continue
        _chrom, start, end, barcode, count = fields
        try:
            start_i, end_i, count_i = int(start), int(end), int(count)
        except ValueError:
            bad_rows.append(line)
            continue
        if end_i <= start_i:
            bad_rows.append(line)
            continue
        if count_i <= 0:
            nonpositive_counts += 1
        n_rows += 1
        barcodes.append(barcode)
        coords.append((start_i, end_i))
    return {
        "n_rows": n_rows,
        "n_bad_rows": len(bad_rows),
        "bad_row_examples": bad_rows[:5],
        "n_barcodes": len(barcodes),
        "n_unique_barcodes": len(set(barcodes)),
        "barcode_examples": barcodes[:5],
        "barcodes": barcodes,
        "has_library_prefix": all("_" in barcode for barcode in barcodes) if barcodes else False,
        "all_suffix_minus1": all(barcode.endswith("-1") for barcode in barcodes)
        if barcodes
        else False,
        "n_nonpositive_counts": nonpositive_counts,
        "start_min": min((s for s, _ in coords), default=None),
        "end_max": max((e for _, e in coords), default=None),
    }


def load_allowlist(obs_h5ad: str | None, allowlist_path: str | None) -> set[str]:
    """Load cell identifiers from an H5AD obs index or a plain text file."""
    if allowlist_path:
        return {
            line.strip() for line in Path(allowlist_path).read_text().splitlines() if line.strip()
        }
    if not obs_h5ad:
        raise ValueError("one of obs_h5ad or allowlist_path is required")
    import anndata as ad

    backed = ad.read_h5ad(obs_h5ad, backed="r")
    try:
        return set(backed.obs.index.astype(str).tolist())
    finally:
        backed.file.close()


def validate_join(barcodes: list[str], allowlist: set[str]) -> dict:
    """Resolve observed fragment barcodes against the cell allowlist."""
    unique = set(barcodes)
    unknown = sorted(unique - allowlist)
    return {
        "allowlist_size": len(allowlist),
        "n_observed_unique": len(unique),
        "n_in_allowlist": len(unique & allowlist),
        "n_unknown": len(unknown),
        "unknown_examples": unknown[:5],
        "complete_coverage": bool(unique) and not unknown,
    }


def run_validation(
    *,
    fragment_url: str,
    index_url: str,
    allowlist: set[str],
    fragment_bytes: int = 2_097_152,
    index_bytes: int = 524_288,
    text_limit: int = 200_000,
) -> dict:
    """Execute the bounded header validation and return a JSON-ready record."""
    result: dict = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "fragment_url": fragment_url,
        "index_url": index_url,
        "requested_fragment_range_bytes": fragment_bytes,
        "requested_index_range_bytes": index_bytes,
    }
    frag_head = head_headers(fragment_url)
    idx_head = head_headers(index_url)
    result["fragment_head"] = {
        "status": 200,
        "content_length": int(frag_head.get("content-length", 0)),
        "accept_ranges": frag_head.get("accept-ranges"),
        "etag": frag_head.get("etag"),
        "last_modified": frag_head.get("last-modified"),
    }
    result["index_head"] = {
        "status": 200,
        "content_length": int(idx_head.get("content-length", 0)),
        "accept_ranges": idx_head.get("accept-ranges"),
        "etag": idx_head.get("etag"),
        "last_modified": idx_head.get("last-modified"),
    }

    frag_blob = range_bytes(fragment_url, 0, fragment_bytes - 1)
    result["fragment_range_sha256"] = hashlib.sha256(frag_blob).hexdigest()
    result["fragment_bgzf_magic"] = frag_blob[:2].hex()
    frag_text = decompress_prefix(frag_blob, text_limit).decode("utf-8", "replace")
    fragment = parse_fragment_lines(frag_text)
    result["join"] = validate_join(fragment.pop("barcodes"), allowlist)
    result["fragment"] = fragment

    idx_blob = range_bytes(index_url, 0, index_bytes - 1)
    result["index_range_sha256"] = hashlib.sha256(idx_blob).hexdigest()
    idx_text = decompress_prefix(idx_blob, 65536)
    result["index"] = parse_tabix_header(idx_text)

    frag = result["fragment"]
    join = result["join"]
    idx = result["index"]
    checks = {
        "fragment_bgzf": result["fragment_bgzf_magic"] == "1f8b",
        "barcodes_library_prefixed": frag["has_library_prefix"],
        "barcodes_minus1_suffix": frag["all_suffix_minus1"],
        "barcodes_all_in_allowlist": join["complete_coverage"],
        "interval_columns_valid": frag["n_bad_rows"] == 0,
        "index_is_tabix": idx["magic_ok"],
        "index_columns_expected": idx.get("col_seq") == 1
        and idx.get("col_beg") == 2
        and idx.get("col_end") == 3,
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragment-url", default=DEFAULT_FRAGMENT_URL)
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL)
    parser.add_argument("--obs-h5ad", default=DEFAULT_OBS_H5AD)
    parser.add_argument("--allowlist-path", default=None)
    parser.add_argument("--fragment-bytes", type=int, default=2_097_152)
    parser.add_argument("--index-bytes", type=int, default=524_288)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    allowlist = load_allowlist(args.obs_h5ad, args.allowlist_path)
    result = run_validation(
        fragment_url=args.fragment_url,
        index_url=args.index_url,
        allowlist=allowlist,
        fragment_bytes=args.fragment_bytes,
        index_bytes=args.index_bytes,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
