#!/usr/bin/env python3
"""Driver-side evidence check: the agent does not decide DONE, this does.

Usage: check_evidence.py FILE [KEY ...] [--eq KEY_A KEY_B] [--grep TEXT]
  KEY    dotted path that must exist and be non-null/non-empty (e.g. primary.ci)
  --eq   two dotted paths whose values must be equal
  --grep text that must occur in FILE (for markdown files)
Exit 0 when every check holds; otherwise print what failed and exit 1.
"""
import json
import sys
from pathlib import Path


def lookup(data, dotted):
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def main(argv):
    if not argv:
        sys.exit(__doc__)
    path, rest, problems = Path(argv[0]), argv[1:], []
    if not path.exists() or path.stat().st_size == 0:
        print(f"FAIL missing or empty: {path}")
        return 1
    text = path.read_text(errors="replace")
    data = json.loads(text) if path.suffix == ".json" else None
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--eq":
            a, b = lookup(data, rest[i + 1]), lookup(data, rest[i + 2])
            if a is None or a != b:
                problems.append(f"{rest[i + 1]}={a!r} != {rest[i + 2]}={b!r}")
            i += 3
        elif arg == "--grep":
            if rest[i + 1] not in text:
                problems.append(f"text not found: {rest[i + 1]!r}")
            i += 2
        else:
            if data is None or lookup(data, arg) in (None, "", [], {}):
                problems.append(f"missing key: {arg}")
            i += 1
    for p in problems:
        print(f"FAIL {path}: {p}")
    if not problems:
        print(f"OK {path}")
    return 1 if problems else 0


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "x.json"
        f.write_text(json.dumps({"a": {"b": 1}, "n": 3, "m": 3, "e": []}))
        assert main([str(f), "a.b", "--eq", "n", "m"]) == 0
        assert main([str(f), "e"]) == 1
        assert main([str(f), "a.c"]) == 1
        assert main([str(Path(d) / "missing.json")]) == 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        demo()
        print("self-test ok")
    else:
        sys.exit(main(sys.argv[1:]))
