#!/usr/bin/env python3
"""Compare downloaded Colab evidence against the frozen local RNA execution."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[2]
LOCAL = REPO / "reports/generated/external_rna_20260908_final/run_20260909T044905Z"
CANONICAL = REPO / "P22_down_syndrome_all_in_one.ipynb"
EXPECTED_SHA = "819604b370d8784303764ab0e2dbfe4e3a975c88b9a6df750321b7e0c92caf9f"
TOLERANCE = 1e-9


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(cell):
    value = cell.get("source", "")
    return value if isinstance(value, str) else "".join(value)


def signature(cell):
    return cell["cell_type"], source(cell)


def compare_values(expected, actual, path=""):
    """Report every differing leaf/key; booleans are not numeric counts."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(expected.keys() | actual.keys()):
            child = f"{path}.{key}" if path else key
            if key not in expected or key not in actual:
                result.append(
                    {
                        "path": child,
                        "kind": "extra_key" if key not in expected else "missing_key",
                        "within_tolerance": False,
                    }
                )
            else:
                result.extend(compare_values(expected[key], actual[key], child))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [
                {
                    "path": path,
                    "kind": "length",
                    "expected": len(expected),
                    "actual": len(actual),
                    "within_tolerance": False,
                }
            ]
        return [
            item
            for index, (left, right) in enumerate(zip(expected, actual, strict=True))
            for item in compare_values(left, right, f"{path}[{index}]")
        ]
    if type(expected) in (int, float) and type(actual) in (int, float):
        if not math.isfinite(expected) or not math.isfinite(actual):
            return [
                {
                    "path": path,
                    "kind": "nonfinite",
                    "expected": repr(expected),
                    "actual": repr(actual),
                    "within_tolerance": False,
                }
            ]
        delta = abs(expected - actual)
        if delta == 0:
            return []
        return [
            {
                "path": path,
                "kind": "numeric",
                "expected": expected,
                "actual": actual,
                "absolute_delta": delta,
                "within_tolerance": delta <= TOLERANCE,
            }
        ]
    if type(expected) is type(actual) and expected == actual:
        return []
    return [
        {
            "path": path,
            "kind": "value",
            "expected": expected,
            "actual": actual,
            "within_tolerance": False,
        }
    ]


def match_native_cells(canonical, native):
    matched = []
    cursor = 0
    for index, cell in enumerate(native):
        if cursor < len(canonical) and signature(cell) == signature(canonical[cursor]):
            matched.append(index)
            cursor += 1
    return matched, [i for i in range(len(native)) if i not in matched]


def notebook_errors(cells):
    return [
        {
            "cell": index,
            "ename": output.get("ename"),
            "evalue": output.get("evalue"),
            "traceback": output.get("traceback", []),
        }
        for index, cell in enumerate(cells)
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {Path(__file__).name} EXTRACTION_ROOT | --self-test", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    report = {
        "extraction_root": str(root),
        "local_reference": str(LOCAL),
        "tolerance": TOLERANCE,
        "failures": [],
        "pending": [],
        "comparison_scope": "All RNA record and row keys; only outer wall_seconds, "
        "peak_rss_gb and figure path ignored. G0 reported unaltered.",
    }

    def require(condition, message):
        if not condition:
            report["failures"].append(message)

    try:
        require(root.is_dir(), "Archive extraction directory is missing")
        canonical = read_json(CANONICAL)["cells"]
        report["canonical_sha256"] = sha256(CANONICAL)
        require(report["canonical_sha256"] == EXPECTED_SHA, "Local canonical SHA changed")
        require(len(canonical) == 23, "Local canonical is not 23 cells")
        originals = sorted(root.rglob(CANONICAL.name))
        report["archived_originals"] = [{"path": str(p), "sha256": sha256(p)} for p in originals]
        require(bool(originals), "Untouched original canonical not present in archive")
        for item in report["archived_originals"]:
            require(item["sha256"] == EXPECTED_SHA, f"Original SHA mismatch: {item['path']}")

        focused = EVIDENCE / "focused-tests.log"
        report["focused_tests"] = {
            "path": str(focused),
            "exists": focused.is_file(),
            "link": f"[Focused test log]({focused})",
        }
        require(focused.is_file(), "Focused test log is missing")
        local = read_json(LOCAL / "notebook_summary.json")
        reference = local["external_rna_replication"]
        expected_rows = {row["external_population"]: row for row in reference["rows"]}
        outer_ignore = {"rows", "wall_seconds", "peak_rss_gb", "figure"}
        summaries = sorted(root.rglob("notebook_summary.json"))
        require(bool(summaries), "No downloaded notebook summaries")
        report["runs"] = []
        for path in summaries:
            current = read_json(path)
            rna = current["external_rna_replication"]
            actual_rows = {row["external_population"]: row for row in rna["rows"]}
            require(len(rna["rows"]) == len(actual_rows) == 4, f"Not four unique rows: {path}")
            differences = compare_values(expected_rows, actual_rows, "rows")
            differences += compare_values(
                {k: v for k, v in reference.items() if k not in outer_ignore},
                {k: v for k, v in rna.items() if k not in outer_ignore},
                "rna",
            )
            for key in ("mode", "raw_cells", "post_qc_cells", "post_qc_donors", "atac_branch"):
                differences += compare_values(local[key], current[key], key)
            gate_path = path.parent / "gate_board.json"
            gates = read_json(gate_path)["gates"]
            manifest_path = path.parent / "runs/real_analysis_20260728/manifest.json"
            manifest = read_json(manifest_path)
            require(
                manifest["notebook_hash"] == EXPECTED_SHA, f"Manifest source SHA mismatch: {path}"
            )
            require(
                current["gates"]["G8"] == gates["G8"]["status"] == "INCONCLUSIVE",
                f"G8 status changed: {path}",
            )
            require(rna["execution_status"] == "completed", f"RNA execution incomplete: {path}")
            require(
                not any(not d["within_tolerance"] for d in differences),
                f"RNA/cohort comparison mismatch: {path}",
            )
            report["runs"].append(
                {
                    "summary": str(path),
                    "manifest": str(manifest_path),
                    "g0": gates["G0"],
                    "g8": gates["G8"]["status"],
                    "flags": manifest["flags"],
                    "differences": differences,
                    "exact_match": not differences,
                    "max_absolute_numeric_delta": max(
                        (d["absolute_delta"] for d in differences if "absolute_delta" in d),
                        default=0.0,
                    ),
                }
            )
        require(
            any(
                r["g0"]["status"] == "PASS"
                and r["g0"]["evidence"]["python_version"].startswith("3.11.")
                for r in report["runs"]
            ),
            "No passing Python 3.11 G0 evidence",
        )

        py311 = sorted(
            p
            for p in root.rglob("*.ipynb")
            if "py311" in p.name.lower() and "executed" in p.name.lower()
        )
        require(bool(py311), "No executed Python 3.11 notebook")
        report["py311_notebooks"] = []
        for path in py311:
            cells = read_json(path)["cells"]
            same = [signature(c) for c in cells] == [signature(c) for c in canonical]
            errors = notebook_errors(cells)
            executed = all(
                c.get("execution_count") is not None for c in cells if c["cell_type"] == "code"
            )
            require(same and len(cells) == 23, f"Python 3.11 canonical source mismatch: {path}")
            require(not errors and executed, f"Python 3.11 notebook incomplete/error: {path}")
            report["py311_notebooks"].append(
                {
                    "path": str(path),
                    "sha256": sha256(path),
                    "cell_count": len(cells),
                    "source_exact": same,
                    "all_code_executed": executed,
                    "errors": errors,
                }
            )

        native = sorted(
            set(root.rglob("P22_colab_native.executed.ipynb"))
            | set(EVIDENCE.glob("P22_colab_native.executed.ipynb"))
        )
        report["native_notebooks"] = []
        if not native:
            report["pending"].append("Native Colab executed notebook not downloaded yet")
        for path in native:
            cells = read_json(path)["cells"]
            matched, extras = match_native_cells(canonical, cells)
            errors = notebook_errors(cells)
            canonical_errors = [e for e in errors if e["cell"] in matched]
            require(len(matched) == 23, f"Native canonical source sequence mismatch: {path}")
            require(not canonical_errors, f"Native scientific cell errors: {path}")
            require(
                all(
                    cells[i].get("execution_count") is not None
                    for i in matched
                    if cells[i]["cell_type"] == "code"
                ),
                f"Native canonical cells not executed: {path}",
            )
            report["native_notebooks"].append(
                {
                    "path": str(path),
                    "sha256": sha256(path),
                    "canonical_cell_indices": matched,
                    "canonical_errors": canonical_errors,
                    "auxiliary_errors": [e for e in errors if e["cell"] in extras],
                    "documented_extra_cells": [
                        {"index": i, "cell_type": cells[i]["cell_type"], "source": source(cells[i])}
                        for i in extras
                    ],
                }
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["failures"].append(f"Malformed or missing evidence: {type(exc).__name__}: {exc}")

    report["status"] = (
        "failed" if report["failures"] else "pending" if report["pending"] else "passed"
    )
    target = EVIDENCE / "comparison.json"
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(target),
                "failures": report["failures"],
                "pending": report["pending"],
            },
            indent=2,
        )
    )
    assert not report["failures"], "; ".join(report["failures"])
    return 0 if report["status"] == "passed" else 2


def self_test():
    assert compare_values({"x": 1, "flag": False}, {"x": 1, "flag": False}) == []
    small = compare_values({"x": 1.0}, {"x": 1.0 + 1e-10})
    assert len(small) == 1 and small[0]["within_tolerance"]
    assert not compare_values({"x": 1.0}, {"x": 1.01})[0]["within_tolerance"]
    assert compare_values({"flag": False}, {"flag": 0})[0]["kind"] == "value"
    assert compare_values({}, {"unexpected": 1})[0]["kind"] == "extra_key"
    assert compare_values({"required": 1}, {})[0]["kind"] == "missing_key"
    assert compare_values(1.0, float("nan"))[0]["kind"] == "nonfinite"
    cells = [
        {"cell_type": "code", "source": "x=1\n"},
        {"cell_type": "markdown", "source": ["Result\n"]},
    ]
    extra = {"cell_type": "code", "source": "# export\n", "outputs": []}
    matched, extras = match_native_cells(cells, [extra, *cells, extra])
    assert matched == [1, 2] and extras == [0, 3]
    assert match_native_cells(cells, cells[::-1])[0] != [0, 1]
    assert (
        notebook_errors(
            [
                {
                    "outputs": [
                        {"output_type": "error", "ename": "E", "evalue": "bad", "traceback": []}
                    ]
                }
            ]
        )[0]["cell"]
        == 0
    )
    real = read_json(LOCAL / "notebook_summary.json")["external_rna_replication"]
    assert len(real["rows"]) == 4 and not compare_values(
        real, read_json(LOCAL / "notebook_summary.json")["external_rna_replication"]
    )
    executed = read_json(
        REPO / "reports/generated/notebooks/P22_external_rna_20260908_final.executed.ipynb"
    )
    assert [signature(c) for c in executed["cells"]] == [
        signature(c) for c in read_json(CANONICAL)["cells"]
    ]
    assert not notebook_errors(executed["cells"])
    print("comparison self-test passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        raise SystemExit(main())
