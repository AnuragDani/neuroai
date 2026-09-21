"""Bounded remote tabix region queries against the P22 ATAC fragment.

This implements the enabling mechanism for the development indexed-fragment
quantification route: random-access reads of a remote BGZF fragment using its
served ``.tbi`` index, without downloading the whole 25.5 GB asset. For each
queried region it returns the overlapping fragment rows, joins their barcodes
against a cell allowlist, and records the exact bytes/requests used.

The route gate it supports: the development CELLxGENE fragment is open, indexed
and library-prefixed, so measured ATAC counts can be recovered on any fixed
reference region set by remote indexed queries. It is a mechanism proof, not a
scientific feature contract; a fixed-reference/training-fold region set must be
frozen separately before the counts are used in a comparison.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import struct
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
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
DEFAULT_WINDOW = 262_144
DEFAULT_MAX_BYTES_PER_REGION = 32 * 1024**2

TABIX_MAGIC = b"TBI\x01"
BGZF_MAGIC = b"\x1f\x8b"
TABIX_BIN_SHIFT = 14
TABIX_MAX_COORD = 1 << 29

Transport = Callable[[str, int, int], bytes]


def http_range(url: str, start: int, end: int, timeout: float = 120.0) -> bytes:
    """Fetch the inclusive byte range ``start..end`` from ``url``."""
    if start < 0 or end < start:
        raise ValueError("invalid byte range")
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def reg2bins(beg: int, end: int) -> list[int]:
    """Return the tabix bins overlapping the 0-based half-open interval [beg, end)."""
    beg = max(beg, 0)
    end = min(end, TABIX_MAX_COORD)
    if beg >= end:
        return []
    end -= 1
    bins = [0]
    for k in range(1 + (beg >> 26), 1 + (end >> 26) + 1):
        bins.append(k)
    for k in range(9 + (beg >> 23), 9 + (end >> 23) + 1):
        bins.append(k)
    for k in range(73 + (beg >> 20), 73 + (end >> 20) + 1):
        bins.append(k)
    for k in range(585 + (beg >> 17), 585 + (end >> 17) + 1):
        bins.append(k)
    for k in range(4681 + (beg >> 14), 4681 + (end >> 14) + 1):
        bins.append(k)
    return bins


@dataclass
class TabixIndex:
    """A parsed tabix ``.tbi`` index: per-reference bin chunks and linear index."""

    names: list[str]
    refs: dict[str, tuple[dict[int, list[tuple[int, int]]], list[int]]]
    header: dict

    @classmethod
    def from_bytes(cls, raw: bytes) -> TabixIndex:
        if raw[:2] == BGZF_MAGIC:
            raw = gzip.decompress(raw)
        if len(raw) < 36 or raw[:4] != TABIX_MAGIC:
            raise ValueError("not a tabix index")
        (
            n_ref,
            fmt,
            col_seq,
            col_beg,
            col_end,
            meta,
            skip,
            l_nm,
        ) = struct.unpack("<8i", raw[4:36])
        names_blob = raw[36 : 36 + l_nm]
        names = [n.decode("ascii") for n in names_blob.split(b"\x00") if n]
        if len(names) != n_ref:
            raise ValueError("tabix reference count does not match names")
        offset = 36 + l_nm
        refs: dict[str, tuple[dict[int, list[tuple[int, int]]], list[int]]] = {}
        for name in names:
            (n_bin,) = struct.unpack("<i", raw[offset : offset + 4])
            offset += 4
            bins: dict[int, list[tuple[int, int]]] = {}
            for _ in range(n_bin):
                (bin_id,) = struct.unpack("<I", raw[offset : offset + 4])
                offset += 4
                (n_chunk,) = struct.unpack("<i", raw[offset : offset + 4])
                offset += 4
                chunks = []
                for _ in range(n_chunk):
                    chunk = struct.unpack("<QQ", raw[offset : offset + 16])
                    offset += 16
                    chunks.append(chunk)
                bins[bin_id] = chunks
            (n_intv,) = struct.unpack("<i", raw[offset : offset + 4])
            offset += 4
            intv = list(struct.unpack(f"<{n_intv}Q", raw[offset : offset + 8 * n_intv]))
            offset += 8 * n_intv
            refs[name] = (bins, intv)
        return cls(
            names=names,
            refs=refs,
            header={
                "n_ref": n_ref,
                "format": fmt,
                "col_seq": col_seq,
                "col_beg": col_beg,
                "col_end": col_end,
                "meta": meta,
                "skip": skip,
                "l_nm": l_nm,
            },
        )

    @classmethod
    def from_path(cls, path: str | Path) -> TabixIndex:
        return cls.from_bytes(Path(path).read_bytes())

    def query_chunks(self, name: str, beg: int, end: int) -> list[tuple[int, int]]:
        """Return merged, sorted virtual-offset chunks for a region query."""
        if name not in self.refs:
            return []
        bins, intv = self.refs[name]
        wanted = reg2bins(beg, end)
        raw_chunks: list[tuple[int, int]] = []
        for bin_id in wanted:
            raw_chunks.extend(bins.get(bin_id, []))
        window = beg >> TABIX_BIN_SHIFT
        min_offset = intv[window] if window < len(intv) else 0
        raw_chunks = [chunk for chunk in raw_chunks if chunk[1] > min_offset]
        raw_chunks.sort()
        merged: list[tuple[int, int]] = []
        for start, stop in raw_chunks:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
            else:
                merged.append((start, stop))
        return merged


def parse_bgzf_members(blob: bytes, base_coffset: int) -> tuple[list[tuple[int, bytes]], int]:
    """Parse consecutive complete BGZF members from ``blob``.

    Returns ``(members, consumed)`` where each member is ``(compressed_offset,
    uncompressed_bytes)`` and ``consumed`` is the number of leading bytes that
    formed complete members. A truncated trailing member is ignored.
    """
    members: list[tuple[int, bytes]] = []
    pos = 0
    while pos + 18 <= len(blob):
        if blob[pos : pos + 2] != BGZF_MAGIC:
            break
        xlen = struct.unpack("<H", blob[pos + 10 : pos + 12])[0]
        extra = blob[pos + 12 : pos + 12 + xlen]
        bsize = None
        cursor = 0
        while cursor + 4 <= len(extra):
            si1, si2 = extra[cursor], extra[cursor + 1]
            slen = struct.unpack("<H", extra[cursor + 2 : cursor + 4])[0]
            if si1 == ord("B") and si2 == ord("C") and slen == 2:
                bsize = struct.unpack("<H", extra[cursor + 4 : cursor + 6])[0]
                break
            cursor += 4 + slen
        if bsize is None:
            break
        total = bsize + 1
        if pos + total > len(blob):
            break
        try:
            data = gzip.GzipFile(fileobj=io.BytesIO(blob[pos : pos + total])).read()
        except (OSError, EOFError, gzip.BadGzipFile):
            break
        members.append((base_coffset + pos, data))
        pos += total
    return members, pos


def parse_fragment_rows(
    text: bytes, name: str, beg: int, end: int
) -> list[tuple[int, int, str, int]]:
    """Parse fragment rows overlapping [beg, end); return (start, end, barcode, count)."""
    rows: list[tuple[int, int, str, int]] = []
    for line in text.split(b"\n"):
        if not line or line[0] == ord("#"):
            continue
        fields = line.split(b"\t")
        if len(fields) != 5 or fields[0] != name.encode("ascii"):
            continue
        try:
            start, stop, count = int(fields[1]), int(fields[2]), int(fields[4])
        except ValueError:
            continue
        if start >= stop:
            continue
        if start < end and stop > beg:
            rows.append((start, stop, fields[3].decode("utf-8", "replace"), count))
    return rows


@dataclass
class QueryStats:
    region: str
    rows: int = 0
    unique_barcodes: int = 0
    bytes_fetched: int = 0
    requests: int = 0
    chunks: int = 0
    truncated: bool = False
    rows_by_barcode: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "region": self.region,
            "rows": self.rows,
            "unique_barcodes": self.unique_barcodes,
            "bytes_fetched": self.bytes_fetched,
            "requests": self.requests,
            "chunks": self.chunks,
            "truncated": self.truncated,
        }


def query_region(
    url: str,
    index: TabixIndex,
    name: str,
    beg: int,
    end: int,
    *,
    transport: Transport = http_range,
    window: int = DEFAULT_WINDOW,
    max_bytes: int = DEFAULT_MAX_BYTES_PER_REGION,
) -> QueryStats:
    """Query one region remotely and return row/byte statistics.

    Each chunk is read as consecutive BGZF windows until the chunk's end
    compressed offset is passed. ``max_bytes`` caps total transfer per region.
    """
    if beg < 0 or end <= beg:
        raise ValueError("invalid region")
    stats = QueryStats(region=f"{name}:{beg}-{end}")
    chunks = index.query_chunks(name, beg, end)
    stats.chunks = len(chunks)
    counts: dict[str, int] = {}
    seen_rows = 0
    for chunk_start, chunk_stop in chunks:
        start_coffset = chunk_start >> 16
        stop_coffset = chunk_stop >> 16
        position = start_coffset
        while position <= stop_coffset:
            if stats.bytes_fetched + window > max_bytes:
                stats.truncated = True
                break
            blob = transport(url, position, position + window - 1)
            stats.bytes_fetched += len(blob)
            stats.requests += 1
            members, consumed = parse_bgzf_members(blob, position)
            if not members:
                break
            for coffset, data in members:
                skip = (chunk_start & 0xFFFF) if coffset == start_coffset else 0
                rows = parse_fragment_rows(data[skip:], name, beg, end)
                for _start, _stop, barcode, count in rows:
                    counts[barcode] = counts.get(barcode, 0) + count
                    seen_rows += 1
            position += consumed
            if position > stop_coffset:
                break
        if stats.truncated:
            break
    stats.rows = seen_rows
    stats.rows_by_barcode = counts
    stats.unique_barcodes = len(counts)
    return stats


def load_ordered_cells(obs_h5ad: str | None, allowlist_path: str | None) -> list[str]:
    if allowlist_path:
        return [
            line.strip() for line in Path(allowlist_path).read_text().splitlines() if line.strip()
        ]
    if not obs_h5ad:
        raise ValueError("one of obs_h5ad or allowlist_path is required")
    import anndata as ad

    backed = ad.read_h5ad(obs_h5ad, backed="r")
    try:
        return backed.obs.index.astype(str).tolist()
    finally:
        backed.file.close()


def load_allowlist(obs_h5ad: str | None, allowlist_path: str | None) -> set[str]:
    return set(load_ordered_cells(obs_h5ad, allowlist_path))


def counts_matrix(regions: list[tuple[str, int, int]], results: list[dict], cells: list[str]):
    """Assemble a sparse regions x cells integer matrix from query results."""
    from scipy import sparse

    cell_index = {cell: position for position, cell in enumerate(cells)}
    rows: list[int] = []
    columns: list[int] = []
    data: list[int] = []
    for region_index, record in enumerate(results):
        for barcode, count in record["counts"].items():
            position = cell_index.get(barcode)
            if position is None:
                continue
            rows.append(region_index)
            columns.append(position)
            data.append(count)
    return sparse.csr_matrix(
        (data, (rows, columns)), shape=(len(regions), len(cells)), dtype="int64"
    )


def parse_region_spec(spec: str) -> tuple[str, int, int]:
    match = re.fullmatch(r"([^:\s]+):([0-9]+)-([0-9]+)", spec)
    if match is None:
        raise ValueError(f"invalid region spec: {spec}")
    name, beg, end = match.group(1), int(match.group(2)), int(match.group(3))
    if end <= beg:
        raise ValueError(f"region end must exceed start: {spec}")
    return name, beg, end


def read_regions_file(path: str) -> list[tuple[str, int, int]]:
    regions = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 3:
            raise ValueError(f"invalid region row: {line}")
        regions.append((fields[0], int(fields[1]), int(fields[2])))
    return regions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragment-url", default=DEFAULT_FRAGMENT_URL)
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL)
    parser.add_argument(
        "--index-path",
        default=None,
        help="local .tbi (raw or gzip) to avoid re-downloading the index",
    )
    parser.add_argument("--region", action="append", default=[], help="chr:start-end, repeatable")
    parser.add_argument("--regions-file", default=None, help="BED-like chrom<TAB>start<TAB>end")
    parser.add_argument("--obs-h5ad", default=DEFAULT_OBS_H5AD)
    parser.add_argument("--allowlist-path", default=None)
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument("--max-bytes-per-region", type=int, default=DEFAULT_MAX_BYTES_PER_REGION)
    parser.add_argument(
        "--counts-out",
        default=None,
        help="directory to write a sparse regions x cells counts matrix (npz + sidecar)",
    )
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    regions = [parse_region_spec(spec) for spec in args.region]
    if args.regions_file:
        regions.extend(read_regions_file(args.regions_file))
    if not regions:
        raise SystemExit("at least one --region or --regions-file is required")
    if args.index_path:
        index = TabixIndex.from_path(args.index_path)
        index_sha256 = hashlib.sha256(Path(args.index_path).read_bytes()).hexdigest()
    else:
        raw = http_range(args.index_url, 0, 5_339_154)
        index = TabixIndex.from_bytes(raw)
        index_sha256 = hashlib.sha256(raw).hexdigest()
    cells = load_ordered_cells(args.obs_h5ad, args.allowlist_path)
    allowlist = set(cells)
    results = []
    stats_list = []
    total_bytes = 0
    for name, beg, end in regions:
        stats = query_region(
            args.fragment_url,
            index,
            name,
            beg,
            end,
            window=args.window,
            max_bytes=args.max_bytes_per_region,
        )
        total_bytes += stats.bytes_fetched
        record = stats.to_dict()
        observed = set(stats.rows_by_barcode)
        record["allowlist_size"] = len(allowlist)
        record["n_in_allowlist"] = len(observed & allowlist)
        record["n_unknown"] = len(observed - allowlist)
        record["join_complete"] = bool(observed) and not (observed - allowlist)
        results.append(record)
        stats_list.append(stats)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "fragment_url": args.fragment_url,
        "index_url": args.index_url,
        "index_sha256": index_sha256,
        "index_header": index.header,
        "window_bytes": args.window,
        "n_regions": len(regions),
        "total_bytes_fetched": total_bytes,
        "regions": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.counts_out:
        from scipy import sparse

        records = [{"counts": stats.rows_by_barcode} for stats in stats_list]
        matrix = counts_matrix(regions, records, cells)
        counts_dir = Path(args.counts_out)
        counts_dir.mkdir(parents=True, exist_ok=True)
        matrix_path = counts_dir / "counts.npz"
        sparse.save_npz(matrix_path, matrix)
        sidecar = {
            "matrix": matrix_path.name,
            "matrix_sha256": hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
            "shape": list(matrix.shape),
            "nnz": int(matrix.nnz),
            "regions": [f"{name}:{beg}-{end}" for name, beg, end in regions],
            "n_cells": len(cells),
            "cells_sha256": hashlib.sha256("\n".join(cells).encode()).hexdigest(),
            "count_unit": "fragment_overlap_sum",
        }
        (counts_dir / "counts.json").write_text(json.dumps(sidecar, indent=2) + "\n")
        print(json.dumps({"counts_shape": sidecar["shape"], "nnz": sidecar["nnz"]}, indent=2))
    print(json.dumps({"n_regions": len(regions), "total_bytes_fetched": total_bytes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
