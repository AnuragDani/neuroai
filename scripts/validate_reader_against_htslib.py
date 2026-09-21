"""Independent oracle: compare the custom reader against HTSlib via pysam.

This script is evidence tooling, not a project test: it requires ``pysam``
(bundled HTSlib), which is intentionally not a project dependency. It runs the
custom bounded reader and ``pysam.TabixFile`` over the same locally generated
BGZF+tabix fixtures and asserts their per-barcode fragment counts agree. It can
also be pointed at the real remote fragment to check a small set of regions.

Run with an isolated environment that has pysam and this worktree on the path::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
        /path/to/pysam-venv/bin/python scripts/validate_reader_against_htslib.py

The local fixtures deliberately split one TSV record across two BGZF members so
the split-member case is exercised against HTSlib, not only against the custom
parser.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import query_fragment_regions as qfr  # noqa: E402


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


def file_transport(path: Path):
    blob = path.read_bytes()

    def transport(_url, start, end):
        return blob[start : end + 1]

    return transport


def local_agreement(tmp: Path) -> dict:
    import pysam

    rows = [
        "chr1\t100\t200\tlibA_AAAA-1\t7",
        "chr1\t150\t260\tlibB_BBBB-1\t3",
        "chr1\t400\t500\tlibA_CCCC-1\t2",
        "chr1\t900\t1000\tlibA_AAAA-1\t5",
    ]
    # Split the first record across two BGZF members: HTSlib must join it.
    first = ("\n".join(rows[:1]) + "\n").encode()
    cut = 15
    members = [bgzf_block(first[:cut]), bgzf_block(first[cut:])]
    tail = ("\n".join(rows[1:]) + "\n").encode()
    members.append(bgzf_block(tail))
    bgz = tmp / "frag.tsv.bgz"
    bgz.write_bytes(b"".join(members))

    pysam.tabix_index(
        str(bgz), preset=None, seq_col=0, start_col=1, end_col=2, meta_char="#", force=True
    )
    tbi = Path(str(bgz) + ".tbi")
    index = qfr.TabixIndex.from_path(tbi)
    transport = file_transport(bgz)

    cases = [("chr1", 50, 300), ("chr1", 400, 500), ("chr1", 0, 5000), ("chr1", 700, 800)]
    results = []
    for name, beg, end in cases:
        stats = qfr.query_region(
            "memory://local", index, name, beg, end, transport=transport, window=262144
        )
        with pysam.TabixFile(str(bgz)) as handle:
            reference = {}
            for line in handle.fetch(name, beg, end):
                fields = line.split("\t")
                reference[fields[3]] = reference.get(fields[3], 0) + 1
        agree = stats.rows_by_barcode == reference
        results.append(
            {
                "region": f"{name}:{beg}-{end}",
                "custom": stats.rows_by_barcode,
                "htslib": reference,
                "agree": agree,
            }
        )
    return {"fixture": "local_split_member", "cases": results}


def remote_agreement(
    fragment_url: str, index_url: str, regions: list[tuple[str, int, int]]
) -> dict:
    import pysam

    raw_index = qfr.http_range(index_url, 0, 5_339_154)
    index = qfr.TabixIndex.from_bytes(raw_index)
    results = []
    with pysam.TabixFile(fragment_url, index=index_url) as handle:
        for name, beg, end in regions:
            stats = qfr.query_region(fragment_url, index, name, beg, end)
            reference: dict[str, int] = {}
            try:
                iterator = handle.fetch(name, beg, end)
            except ValueError:
                iterator = []
            for line in iterator:
                fields = line.split("\t")
                reference[fields[3]] = reference.get(fields[3], 0) + 1
            results.append(
                {
                    "region": f"{name}:{beg}-{end}",
                    "custom_rows": stats.rows,
                    "htslib_rows": sum(reference.values()),
                    "agree": stats.rows_by_barcode == reference,
                }
            )
    return {"fixture": "remote", "cases": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragment-url", default=None)
    parser.add_argument("--index-url", default=None)
    parser.add_argument("--region", action="append", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report: dict = {"reader_version": getattr(qfr, "__doc__", "")[:0] or "custom"}
    with tempfile.TemporaryDirectory() as tmpdir:
        report["local"] = local_agreement(Path(tmpdir))
    if args.fragment_url and args.index_url and args.region:
        regions = [qfr.parse_region_spec(spec) for spec in args.region]
        report["remote"] = remote_agreement(args.fragment_url, args.index_url, regions)
    report["all_agree"] = all(
        case["agree"]
        for group in ("local", "remote")
        for case in report.get(group, {}).get("cases", [])
    )
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
