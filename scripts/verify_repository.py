#!/usr/bin/env python
"""One local command that answers whether this repository is in a reportable state.

Every check returns PASS, INCONCLUSIVE, or BLOCKED, and the run ends with one verdict.
INCONCLUSIVE means the evidence is missing, not that the check succeeded: for example, the
executed notebooks are absent because nobody ran `make notebook-check` yet. That distinction
is the point of the script.

    python scripts/verify_repository.py
    python scripts/verify_repository.py --allow-dirty --json

Standard library only, so it runs before anything else is installed.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
GENERATED = REPO_ROOT / "reports" / "generated"
NOTEBOOK_DIR = REPO_ROOT / "notebooks" / "implementation"
KERNEL_ROOT = GENERATED / "jupyter"
KERNEL_DIR = KERNEL_ROOT / "kernels" / "python3"

# nbconvert's default kernel startup timeout is 60s. On this machine cold imports of
# numpy/sklearn/torch regularly exceed that, so executed copies never appear. The Makefile
# is frozen after C01; this script owns the longer startup budget for local and CI runs.
NOTEBOOK_STARTUP_TIMEOUT_S = 300
NOTEBOOK_EXECUTE_TIMEOUT_S = 1800

PASS = "PASS"
INCONCLUSIVE = "INCONCLUSIVE"
BLOCKED = "BLOCKED"

REAL_DATA_SUFFIXES = (".h5ad", ".h5", ".loom", ".mtx", ".rds", ".fastq", ".bam", ".cram")
EXPECTED_INTERVENTIONS = 7
EXPECTED_REPORT_SECTIONS = (
    "Provenance",
    "Predictive performance",
    "Routing signals",
    "Intervention evidence",
    "Limitations",
    "Approval and next step",
)
SCAN_DIRECTORIES = ("src", "tests", "scripts", "plan", "configs")
LEGACY_NOTEBOOK_NAME = "01_tasic_evidence_boundary.ipynb"


@dataclass
class CheckResult:
    """One check and what it found."""

    name: str
    status: str
    detail: str
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "facts": self.facts,
        }


def run(command: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def python_executable() -> str:
    """Prefer the project virtual environment, so checks match `make verify`."""
    candidate = REPO_ROOT / ".venv-p22" / "bin" / "python"
    return str(candidate) if candidate.is_file() else sys.executable


def check_plan_guard() -> CheckResult:
    completed = run([python_executable(), "scripts/plan_guard.py", "status"])
    if completed.returncode != 0:
        return CheckResult(
            "plan guard status",
            BLOCKED,
            "plan_guard status exited non-zero",
            {"stderr": completed.stderr.strip()[-400:]},
        )
    state = json.loads((REPO_ROOT / "plan" / "state.json").read_text())
    steps = state["steps"]
    complete = [name for name, entry in steps.items() if entry["status"] == "complete"]
    return CheckResult(
        "plan guard status",
        PASS,
        f"plan guard runs; {len(complete)} of {len(steps)} steps complete, "
        f"next action {state['next_action']}",
        {
            "branch": state["branch"],
            "next_action": state["next_action"],
            "steps_complete": len(complete),
            "approval_state": state.get("approval_state"),
        },
    )


def check_python_compiles() -> CheckResult:
    failures = []
    files = []
    for directory in ("src", "tests", "scripts"):
        files.extend(sorted((REPO_ROOT / directory).rglob("*.py")))
    for path in files:
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as error:
            failures.append(f"{path.relative_to(REPO_ROOT)}: {error}")
    if failures:
        return CheckResult(
            "python sources parse", BLOCKED, "; ".join(failures[:3]), {"n_failures": len(failures)}
        )
    return CheckResult(
        "python sources parse", PASS, f"{len(files)} files parse", {"n_files": len(files)}
    )


def check_test_suite_collects() -> CheckResult:
    completed = run([python_executable(), "-m", "pytest", "--collect-only", "-q"])
    if completed.returncode != 0:
        return CheckResult(
            "test suite collects",
            BLOCKED,
            "pytest could not collect the suite",
            {"stderr": completed.stderr.strip()[-400:]},
        )
    lines = [line for line in completed.stdout.splitlines() if "::" in line]
    end_to_end = [line for line in lines if line.startswith("tests/test_end_to_end.py")]
    if not end_to_end:
        return CheckResult(
            "test suite collects",
            INCONCLUSIVE,
            f"{len(lines)} tests collected but tests/test_end_to_end.py has none",
            {"n_tests": len(lines)},
        )
    return CheckResult(
        "test suite collects",
        PASS,
        f"{len(lines)} tests collected, {len(end_to_end)} in the end-to-end module",
        {"n_tests": len(lines), "n_end_to_end": len(end_to_end)},
    )


def check_end_to_end_is_marked() -> CheckResult:
    path = REPO_ROOT / "tests" / "test_end_to_end.py"
    if not path.is_file():
        return CheckResult(
            "end-to-end test marked slow and integration",
            BLOCKED,
            "tests/test_end_to_end.py is missing",
        )
    tree = ast.parse(path.read_text(), filename=str(path))
    marks = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            for decorator in node.decorator_list:
                marks.update(_marker_names(decorator))
        elif isinstance(node, ast.Assign):
            marks.update(_module_marker_names(node))
    missing = sorted({"slow", "integration"} - marks)
    if missing:
        return CheckResult(
            "end-to-end test marked slow and integration",
            BLOCKED,
            f"missing marker(s) {missing}",
            {"markers_found": sorted(marks)},
        )
    return CheckResult(
        "end-to-end test marked slow and integration",
        PASS,
        "slow and integration markers present",
        {"markers_found": sorted(marks)},
    )


def check_run_configuration() -> CheckResult:
    path = REPO_ROOT / "configs" / "toy_pilot.json"
    if not path.is_file():
        return CheckResult("run configuration", BLOCKED, "configs/toy_pilot.json is missing")
    payload = json.loads(path.read_text())
    problems = []
    if payload.get("data_mode") != "synthetic":
        problems.append(f"data_mode is {payload.get('data_mode')!r}, expected 'synthetic'")
    if len(payload.get("seeds", [])) != 5:
        problems.append(f"{len(payload.get('seeds', []))} seeds declared, expected 5")
    if len(payload.get("models", [])) != 6:
        problems.append(f"{len(payload.get('models', []))} models declared, expected 6")
    if not payload.get("limitations"):
        problems.append("limitations list is empty")
    if payload.get("training", {}).get("device") != "cpu":
        problems.append("training device is not cpu")
    if problems:
        return CheckResult("run configuration", BLOCKED, "; ".join(problems))
    return CheckResult(
        "run configuration",
        PASS,
        "synthetic, five seeds, six baselines, cpu, limitations stated",
        {
            "seeds": payload["seeds"],
            "models": [model["name"] for model in payload["models"]],
            "n_limitations": len(payload["limitations"]),
        },
    )


def check_intervention_set() -> CheckResult:
    sys.path.insert(0, str(SRC))
    try:
        from p22.eval.faithfulness import INTERVENTIONS
    except Exception as error:  # noqa: BLE001 - report rather than crash the verifier
        return CheckResult("intervention set", BLOCKED, f"could not import interventions: {error}")
    if len(INTERVENTIONS) != EXPECTED_INTERVENTIONS:
        return CheckResult(
            "intervention set",
            BLOCKED,
            f"{len(INTERVENTIONS)} interventions defined, expected {EXPECTED_INTERVENTIONS}",
            {"interventions": list(INTERVENTIONS)},
        )
    return CheckResult(
        "intervention set",
        PASS,
        f"{len(INTERVENTIONS)} held-out interventions defined",
        {"interventions": list(INTERVENTIONS)},
    )


def check_report_schema() -> CheckResult:
    sys.path.insert(0, str(SRC))
    try:
        from p22.reports.render import SECTION_TITLES
    except Exception as error:  # noqa: BLE001
        return CheckResult("report schema", BLOCKED, f"could not import the renderer: {error}")
    missing = [title for title in EXPECTED_REPORT_SECTIONS if title not in SECTION_TITLES]
    if missing:
        return CheckResult("report schema", BLOCKED, f"report is missing section(s) {missing}")
    return CheckResult(
        "report schema",
        PASS,
        "reports carry provenance, performance, routing, interventions, limitations, approval",
        {"sections": list(SECTION_TITLES)},
    )


def check_legacy_paths_unchanged() -> CheckResult:
    completed = run([python_executable(), "scripts/build_legacy_manifest.py", "verify"])
    if completed.returncode != 0:
        return CheckResult(
            "legacy evidence unchanged",
            BLOCKED,
            "legacy manifest verification failed",
            {"output": (completed.stdout + completed.stderr).strip()[-400:]},
        )
    tracked = run(["git", "ls-files", "experiments", "legacy"]).stdout.split()
    diff = run(["git", "diff", "--name-only", "HEAD", "--", "experiments", "legacy"]).stdout.split()
    if diff:
        return CheckResult(
            "legacy evidence unchanged",
            BLOCKED,
            f"uncommitted changes under legacy or experiments: {diff[:5]}",
        )
    return CheckResult(
        "legacy evidence unchanged",
        PASS,
        f"manifest verifies and {len(tracked)} legacy or experiment files are unmodified",
        {"n_tracked": len(tracked)},
    )


def check_no_real_data() -> CheckResult:
    tracked = run(["git", "ls-files"]).stdout.split()
    offenders = [path for path in tracked if Path(path).suffix.lower() in REAL_DATA_SUFFIXES]
    if offenders:
        return CheckResult(
            "no real dataset files tracked",
            BLOCKED,
            f"tracked data file(s) {offenders[:5]}",
            {"n_offenders": len(offenders)},
        )
    return CheckResult(
        "no real dataset files tracked",
        PASS,
        f"no tracked file carries a dataset suffix ({', '.join(REAL_DATA_SUFFIXES[:4])}, ...)",
        {"n_tracked": len(tracked)},
    )


def check_no_condition_specific_work() -> CheckResult:
    approvals = json.loads((REPO_ROOT / "plan" / "approvals.json").read_text())
    state = approvals.get("approval_state")
    if state != "blocked":
        return CheckResult(
            "no condition-specific work while approval is blocked",
            INCONCLUSIVE,
            f"approval state is {state!r}; this check only applies while it is 'blocked'",
            {"approval_state": state},
        )
    terms = [str(term).lower() for term in approvals.get("condition_terms", [])]
    if not terms:
        return CheckResult(
            "no condition-specific work while approval is blocked",
            INCONCLUSIVE,
            "approvals.json lists no condition terms to scan for",
        )
    hits = []
    for directory in SCAN_DIRECTORIES:
        root = REPO_ROOT / directory
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in (".py", ".json", ".md"):
                continue
            if path.name in ("approvals.json", "verify_repository.py", "plan_guard.py"):
                continue
            lowered = path.read_text(errors="ignore").lower()
            for term in terms:
                if term in lowered:
                    hits.append(f"{path.relative_to(REPO_ROOT)}: {term}")
    if hits:
        return CheckResult(
            "no condition-specific work while approval is blocked",
            BLOCKED,
            f"condition term(s) found: {hits[:5]}",
            {"n_hits": len(hits)},
        )
    return CheckResult(
        "no condition-specific work while approval is blocked",
        PASS,
        f"none of the {len(terms)} condition terms appear in scanned source, plan, or config files",
        {"n_terms": len(terms), "directories": list(SCAN_DIRECTORIES)},
    )


def check_generated_outputs_ignored() -> CheckResult:
    # Trailing slash matches the .gitignore directory rule and still works when
    # reports/generated has been removed by make clean-generated. A bare path
    # name fails check-ignore when the directory is absent.
    ignored = run(["git", "check-ignore", "reports/generated/"]).returncode == 0
    tracked = [
        path
        for path in run(["git", "ls-files"]).stdout.split()
        if path.startswith("reports/generated")
    ]
    if not ignored:
        return CheckResult(
            "generated outputs stay out of the source tree",
            BLOCKED,
            "reports/generated is not covered by .gitignore",
        )
    if tracked:
        return CheckResult(
            "generated outputs stay out of the source tree",
            BLOCKED,
            f"tracked artefact(s) under reports/generated: {tracked[:5]}",
        )
    return CheckResult(
        "generated outputs stay out of the source tree",
        PASS,
        "reports/generated is ignored and nothing under it is tracked",
    )


def check_executed_notebooks() -> CheckResult:
    sources = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    executed_dir = GENERATED / "notebooks"
    executed = sorted(executed_dir.glob("*.ipynb")) if executed_dir.is_dir() else []
    if not executed:
        return CheckResult(
            "notebooks executed",
            INCONCLUSIVE,
            "no executed notebooks found; run `make notebook-check`",
            {"n_source_notebooks": len(sources)},
        )
    executed_names = {path.name for path in executed}
    missing = [path.name for path in sources if path.name not in executed_names]
    failures = []
    gates = []
    for path in executed:
        payload = json.loads(path.read_text())
        for cell in payload.get("cells", []):
            for output in cell.get("outputs", []):
                if output.get("output_type") == "error":
                    failures.append(f"{path.name}: {output.get('ename')}")
                text = "".join(output.get("text", []))
                for line in text.splitlines():
                    if line.startswith("FAIL:"):
                        failures.append(f"{path.name}: {line}")
                    if "gate: PASS" in line:
                        gates.append(f"{path.name}: {line.strip()}")
    if failures:
        return CheckResult(
            "notebooks executed",
            BLOCKED,
            f"executed notebooks contain failures: {failures[:3]}",
            {"n_failures": len(failures)},
        )
    if missing:
        # The legacy notebook has its own target because it reads tracked legacy outputs.
        target = (
            "make notebook-check-legacy"
            if missing == [LEGACY_NOTEBOOK_NAME]
            else "make notebook-check"
        )
        return CheckResult(
            "notebooks executed",
            INCONCLUSIVE,
            f"{len(executed)} executed; {missing} not yet run, so run `{target}`",
            {"gates": gates, "missing": missing},
        )
    status = PASS
    detail = f"{len(executed)} notebooks executed with {len(gates)} passing gate(s)"
    return CheckResult(
        "notebooks executed",
        status,
        detail,
        {"gates": gates, "missing": missing},
    )


def check_repository_clean(allow_dirty: bool) -> CheckResult:
    porcelain = run(["git", "status", "--porcelain"]).stdout.splitlines()
    dirty = [line for line in porcelain if line.strip()]
    if not dirty:
        return CheckResult("repository clean", PASS, "working tree and index are clean")
    if allow_dirty:
        return CheckResult(
            "repository clean",
            INCONCLUSIVE,
            f"{len(dirty)} uncommitted path(s); allowed by --allow-dirty",
            {"paths": [line[3:] for line in dirty[:10]]},
        )
    return CheckResult(
        "repository clean",
        BLOCKED,
        f"{len(dirty)} uncommitted path(s)",
        {"paths": [line[3:] for line in dirty[:10]]},
    )


def _module_marker_names(node: ast.Assign) -> set[str]:
    """Extract marker names from a module-level ``pytestmark = [...]`` assignment."""
    if not any(
        isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets
    ):
        return set()
    values = node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
    marks: set[str] = set()
    for value in values:
        marks.update(_marker_names(value))
    return marks


def _marker_names(decorator: ast.expr) -> set[str]:
    """Extract marker names from a ``@pytest.mark.x`` decorator."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    if len(parts) >= 3 and parts[0] == "pytest" and parts[1] == "mark":
        return {parts[2]}
    if len(parts) >= 2 and parts[0] == "mark":
        return {parts[1]}
    return set()


def synthetic_notebooks() -> list[Path]:
    return sorted(
        path for path in NOTEBOOK_DIR.glob("*.ipynb") if path.name != LEGACY_NOTEBOOK_NAME
    )


def ensure_project_kernel() -> Path:
    """Write a kernelspec that points at .venv-p22 under the ignored generated tree."""
    KERNEL_DIR.mkdir(parents=True, exist_ok=True)
    # Keep the venv path unresolved. resolve() follows the symlink to Homebrew Python,
    # which does not see packages installed in .venv-p22.
    python = Path(python_executable())
    if not python.is_absolute():
        python = (REPO_ROOT / python).absolute()
    payload = (
        json.dumps(
            {
                "argv": [str(python), "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "P22 (.venv-p22)",
                "language": "python",
            },
            indent=2,
        )
        + "\n"
    )
    target = KERNEL_DIR / "kernel.json"
    if target.is_file() and target.read_text() == payload:
        return KERNEL_ROOT
    if target.is_file():
        target.unlink()
    target.write_text(payload)
    return KERNEL_ROOT


def execute_notebooks(legacy: bool = False) -> CheckResult:
    """Execute source notebooks into reports/generated/notebooks/ without overwriting sources."""
    import os

    sources = [NOTEBOOK_DIR / LEGACY_NOTEBOOK_NAME] if legacy else synthetic_notebooks()
    sources = [path for path in sources if path.is_file()]
    if not sources:
        return CheckResult(
            "notebook execution",
            INCONCLUSIVE,
            "no notebooks found to execute",
        )
    output_dir = GENERATED / "notebooks"
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["JUPYTER_PATH"] = str(ensure_project_kernel())
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            python_executable(),
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            f"--ExecutePreprocessor.timeout={NOTEBOOK_EXECUTE_TIMEOUT_S}",
            f"--ExecutePreprocessor.startup_timeout={NOTEBOOK_STARTUP_TIMEOUT_S}",
            "--output-dir",
            str(output_dir),
            *[str(path) for path in sources],
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        return CheckResult(
            "notebook execution",
            BLOCKED,
            "nbconvert failed",
            {"stderr": completed.stderr.strip()[-800:], "stdout": completed.stdout.strip()[-400:]},
        )
    return CheckResult(
        "notebook execution",
        PASS,
        f"executed {len(sources)} notebook(s) into {output_dir.relative_to(REPO_ROOT)}",
        {"notebooks": [path.name for path in sources]},
    )


def collect_results(allow_dirty: bool = False) -> list[CheckResult]:
    """Run every check and return the results in reporting order."""
    return [
        check_plan_guard(),
        check_python_compiles(),
        check_test_suite_collects(),
        check_end_to_end_is_marked(),
        check_run_configuration(),
        check_intervention_set(),
        check_report_schema(),
        check_legacy_paths_unchanged(),
        check_no_real_data(),
        check_no_condition_specific_work(),
        check_generated_outputs_ignored(),
        check_executed_notebooks(),
        check_repository_clean(allow_dirty),
    ]


def verdict(results: list[CheckResult]) -> str:
    """BLOCKED beats INCONCLUSIVE beats PASS."""
    statuses = {result.status for result in results}
    if BLOCKED in statuses:
        return BLOCKED
    if INCONCLUSIVE in statuses:
        return INCONCLUSIVE
    return PASS


EXIT_CODES = {PASS: 0, INCONCLUSIVE: 3, BLOCKED: 1}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="report an uncommitted tree as INCONCLUSIVE instead of BLOCKED",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    parser.add_argument(
        "--execute-notebooks",
        action="store_true",
        help=(
            "execute synthetic notebooks into reports/generated/notebooks/ with a "
            f"{NOTEBOOK_STARTUP_TIMEOUT_S}s kernel startup budget, then exit"
        ),
    )
    parser.add_argument(
        "--execute-legacy-notebook",
        action="store_true",
        help="execute the legacy Tasic notebook only, then exit",
    )
    arguments = parser.parse_args(argv)

    if arguments.execute_notebooks or arguments.execute_legacy_notebook:
        result = execute_notebooks(legacy=arguments.execute_legacy_notebook)
        print(f"{result.status}  {result.name}  {result.detail}")
        return EXIT_CODES[result.status]

    results = collect_results(allow_dirty=arguments.allow_dirty)
    overall = verdict(results)

    if arguments.json:
        print(
            json.dumps(
                {"verdict": overall, "checks": [result.to_dict() for result in results]}, indent=2
            )
        )
    else:
        width = max(len(result.name) for result in results)
        for result in results:
            print(f"{result.status:<13} {result.name:<{width}}  {result.detail}")
        print()
        print(f"verdict: {overall}")
        if overall != PASS:
            print("PASS requires every check to pass; INCONCLUSIVE means evidence is missing.")
    return EXIT_CODES[overall]


if __name__ == "__main__":
    raise SystemExit(main())
