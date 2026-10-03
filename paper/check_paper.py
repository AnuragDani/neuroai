#!/usr/bin/env python3
"""Paper checker for the P22-NN draft (N31 checks plus numerical source checks).

Stdlib only. Checks:
  (1) every [@key] in the draft is a key in refs_frozen.bib;
  (2) every number with a decimal point or '%' in Abstract/Results appears in claims.csv;
  (3) forbidden words absent (novel, first, mechanism, causal, biomarker, clinically,
      state-of-the-art);
  (4) every markdown image path in the draft exists on disk;
  (5) per-section and total word counts are within the N26-N30 limits.
  (6) signed numerical ledger values match numeric JSON leaves at display precision.

Usage:
    python paper/check_paper.py [--draft P] [--refs P] [--claims P] [--figures D] [--json]
Exit codes: 0 = all checks pass, 1 = at least one check failed, 2 = draft missing.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
DEFAULT_DRAFT = _HERE / "draft.md"
DEFAULT_REFS = _HERE / "refs_frozen.bib"
DEFAULT_CLAIMS = _HERE / "claims.csv"

BIB_KEY_RE = re.compile(r"@\w+\{\s*([^,\s]+)\s*,")
CITATION_GROUP_RE = re.compile(r"\[([^\]]*@[^\]]*)\]")
CITEKEY_RE = re.compile(r"@([A-Za-z0-9_:.\-]+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
NUMBER_RE = re.compile(r"\d+\.\d+|\d+(?:\.\d+)?%")
FORBIDDEN_RE = re.compile(
    r"\b(?:novel|first|mechanisms?|causals?|causality|biomarkers?|clinically|"
    r"state[-\s]of[-\s]the[-\s]art)\b",
    re.IGNORECASE,
)

# (section names, combined word limit) from N26-N30. Sections absent from the draft count 0.
SECTION_RULES: tuple[tuple[tuple[str, ...], int], ...] = (
    (("Abstract",), 200),
    (("Methods",), 1400),
    (("Results",), 1500),
    (("Introduction", "Related Work"), 900),
    (("Discussion", "Limitations"), 700),
)
TOTAL_LIMIT = 5000


def parse_bib_keys(text: str) -> set[str]:
    """Keys from refs_frozen.bib (entries may sit on one line)."""
    return set(BIB_KEY_RE.findall(text))


def parse_citekeys(text: str) -> set[str]:
    """Citekeys used in markdown bracket citations such as [@a; @b]."""
    keys: set[str] = set()
    for group in CITATION_GROUP_RE.findall(text):
        keys.update(CITEKEY_RE.findall(group))
    return keys


def parse_sections(text: str) -> dict[str, str]:
    """Map heading text -> body (heading lines and preamble excluded)."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf)
            current = m.group(2).strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def check_citations(draft_text: str, valid_keys: set[str]) -> list[str]:
    problems = []
    for key in sorted(parse_citekeys(draft_text)):
        if key not in valid_keys:
            problems.append(f"[check1] unknown citation key: @{key}")
    return problems


def check_numbers(sections: dict[str, str], claims_text: str) -> list[str]:
    problems = []
    for name in ("Abstract", "Results"):
        body = sections.get(name)
        if not body:
            continue
        for num in sorted(set(NUMBER_RE.findall(body))):
            if num not in claims_text:
                problems.append(f"[check2] {name}: number {num!r} not in claims.csv")
    return problems


def check_claim_sources(claims_text: str, source_root: Path) -> list[str]:
    """Check signed ledger values against numeric JSON leaves at display precision."""
    problems = []
    reader = csv.DictReader(io.StringIO(claims_text))
    required = {"sentence_id", "value", "json_path", "json_key"}
    if not required.issubset(reader.fieldnames or []):
        return ["[sources] missing required claim-ledger columns"]
    for line, row in enumerate(reader, 2):
        try:
            source = json.loads((source_root / row["json_path"]).read_text())
            # Accept existing /ci[0] notation and ordinary /ci/0 JSON pointers.
            pointer = re.sub(r"\[(\d+)\]", r"/\1", row["json_key"])
            for key in pointer.strip("/").split("/"):
                key = key.replace("~1", "/").replace("~0", "~")
                source = source[int(key)] if isinstance(source, list) else source[key]
            if isinstance(source, bool) or not isinstance(source, (int, float)):
                raise ValueError("source is not a numeric leaf")
            display = row["value"].strip()
            scale = 100 if display.endswith("%") else 1
            number = display.removesuffix("%")
            value = float(number) / scale
            decimals = len(number.split(".")[1]) if "." in number else 0
            tolerance = 0.5 * 10 ** (-decimals) / scale
            if not math.isfinite(value) or not math.isfinite(source):
                raise ValueError("non-finite value")
            if abs(value - source) > tolerance + 1e-12:
                raise ValueError(f"{display} differs from source {source}")
        except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            problems.append(f"[sources] row {line} ({row.get('sentence_id')}): {exc}")
    return problems


def check_forbidden(draft_text: str) -> list[str]:
    problems = []
    for m in FORBIDDEN_RE.finditer(draft_text):
        line = draft_text.count("\n", 0, m.start()) + 1
        problems.append(f"[check3] forbidden word {m.group(0)!r} at line {line}")
    return problems


def check_figures(draft_text: str, draft_dir: Path) -> list[str]:
    problems = []
    for ref in IMAGE_RE.findall(draft_text):
        raw = ref.strip().split()[0].strip("\"'")
        if raw.startswith(("http://", "https://", "data:")):
            continue
        path = draft_dir / raw
        if not path.exists():
            problems.append(f"[check4] missing figure: {raw}")
    return problems


def _word_count(text: str) -> int:
    return len(text.split())


def check_word_counts(sections: dict[str, str]) -> list[str]:
    problems = []
    lowered = {k.lower(): v for k, v in sections.items()}
    for names, limit in SECTION_RULES:
        total = sum(_word_count(lowered.get(n.lower(), "")) for n in names)
        if total > limit:
            problems.append(f"[check5] {'+'.join(names)} word count {total} > {limit}")
    total_all = sum(
        _word_count(v) for k, v in sections.items() if k.lower() != "references"
    )
    if total_all > TOTAL_LIMIT:
        problems.append(f"[check5] total word count {total_all} > {TOTAL_LIMIT}")
    return problems


def run_checks(
    draft_text: str,
    valid_keys: set[str],
    claims_text: str,
    draft_dir: Path,
) -> dict[str, list[str]]:
    sections = parse_sections(draft_text)
    return {
        "citations": check_citations(draft_text, valid_keys),
        "numbers": check_numbers(sections, claims_text),
        "forbidden": check_forbidden(draft_text),
        "figures": check_figures(draft_text, draft_dir),
        "word_counts": check_word_counts(sections),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check the P22-NN paper draft (N31 checks 1-5).")
    ap.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    ap.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args(argv)

    if not args.draft.exists():
        msg = f"draft not found: {args.draft}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}))
        else:
            print(f"ERROR: {msg}")
        return 2

    draft_text = args.draft.read_text(encoding="utf-8")
    if args.refs.exists():
        valid_keys = parse_bib_keys(args.refs.read_text(encoding="utf-8"))
    else:
        valid_keys = set()
    claims_text = args.claims.read_text(encoding="utf-8") if args.claims.exists() else ""
    report = run_checks(draft_text, valid_keys, claims_text, args.draft.parent)
    report["claim_sources"] = check_claim_sources(claims_text, _HERE.parent)
    failures = sum(len(v) for v in report.values())

    if args.json:
        print(json.dumps({"ok": failures == 0, "failures": failures, "report": report}, indent=2))
    else:
        for name, problems in report.items():
            status = "PASS" if not problems else "FAIL"
            print(f"{status} {name}")
            for p in problems:
                print(f"    {p}")
        print(f"{failures} problem(s) found")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
