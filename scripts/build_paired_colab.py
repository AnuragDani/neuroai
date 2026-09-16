"""Package the unchanged offline notebook for a free CPU Colab runtime."""

import hashlib
import sys
from pathlib import Path

import nbformat

REPO = Path(__file__).resolve().parents[1]
SOURCE = "notebooks/P22_paired_workflow.ipynb"
FILES = (
    SOURCE,
    "pyproject.toml",
    "scripts/launcher_head_capture.py",
    "scripts/capture_development_head.py",
    "scripts/validate_development_head.py",
    "tests/test_development_head.py",
    "tests/test_development_head_capture.py",
    "tests/test_launcher_head_capture.py",
    "configs/development_object_source_contract.json",
    "docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md",
    "docs/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md",
    "docs/RNA_DONOR_INFLUENCE_RESULTS_2026-09-10.md",
)

MATERIALIZE = """import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

PAYLOAD = __PAYLOAD__
EXPECTED_SHA256 = __HASHES__
ROOT = Path(tempfile.mkdtemp(prefix="p22-paired-colab-")).resolve()
for name, content in PAYLOAD.items():
    relative = Path(name)
    assert not relative.is_absolute() and ".." not in relative.parts
    raw = content.encode("utf-8")
    assert len(raw) <= 262144
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256[name]
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(raw)
(ROOT / "reports/generated").mkdir(parents=True)
print("Embedded files verified:", len(PAYLOAD), "Root:", ROOT)
print("Only offline code, tests, and saved reports; no raw datasets.")
"""

ENVIRONMENT = """# Keep the native Colab kernel unchanged. Use Python 3.11 for P22.
import shutil
if sys.version_info[:2] == (3, 11):
    P22_PYTHON = sys.executable  # Local verification uses the existing P22 environment.
else:
    assert Path("/content").is_dir(), "Use Python 3.11 locally, or run in Colab."
    uv = shutil.which("uv")
    if uv is None:
        tools_dir = ROOT / "uv-tools"
        subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:",
                        "--target", str(tools_dir), "uv==0.12.13"], check=True, timeout=180)
        uv = str(tools_dir / "bin/uv")
    subprocess.run([uv, "venv", "--python", "3.11", str(ROOT / "venv")],
                   check=True, timeout=240)
    P22_PYTHON = str(ROOT / "venv/bin/python")
    subprocess.run([uv, "pip", "install", "--python", P22_PYTHON, "--only-binary=:all:",
                    "pytest==8.4.2", "nbformat==5.10.4", "nbclient==0.11.0",
                    "ipykernel==7.3.0"], check=True, timeout=240)
version_check = "import sys; assert sys.version_info[:2] == (3,11); print(sys.version)"
subprocess.run([P22_PYTHON, "-c", version_check],
               check=True, timeout=15)
print("Environment ready. No ML stack or datasets installed.")
"""

RUNNER = """import json, os, sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
import nbformat
from nbclient import NotebookClient

assert sys.version_info[:2] == (3, 11)
root = Path.cwd()
source = nbformat.read(root / "notebooks/P22_paired_workflow.ipynb", as_version=4)
before = [(c.id, c.source) for c in source.cells]
client = NotebookClient(source, kernel_name="python3", timeout=120, allow_errors=False)
manager = client.create_kernel_manager()
manager.kernel_spec.argv = [
    sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}",
    "--IPKernelApp.kernel_class=ipykernel.ipkernel.IPythonKernel",
    "--InteractiveShellApp.extensions=[]",
]
try:
    client.execute(cwd=str(root), env=dict(os.environ))
finally:
    nbformat.write(source, root / "P22_paired_workflow.executed.ipynb")
assert before == [(c.id, c.source) for c in source.cells]
code = [c for c in source.cells if c.cell_type == "code"]
assert [c.execution_count for c in code] == list(range(1, 10))
assert not [o for c in code for o in c.outputs if o.output_type == "error"]
tests = "".join(o.get("text", "") for o in code[1].outputs)
assert "181 passed" in tests
decision = json.loads("".join(o.get("text", "") for o in code[-1].outputs))
assert decision["scientific_outcome"] == "INCONCLUSIVE"
assert decision["training_performed"] is False and decision["live_allowed"] is False
assert decision["live_requests_attempted"] == 0
record = {"completed_at": datetime.now(UTC).isoformat(), "python": sys.version,
          "source_cells_unchanged": True, "executed_code_cells": len(code),
          "packages": {p: version(p) for p in ["pytest", "nbformat", "nbclient", "ipykernel"]},
          "offline_test_output": tests, "decision": decision}
(root / "verification.json").write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
"""

EXECUTE = """# Private configuration avoids inheriting Colab's incompatible kernel extensions.
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
environment.pop("PYTHONPATH", None)
for key in ("IPYTHONDIR", "JUPYTER_CONFIG_DIR"):
    directory = ROOT / key.lower()
    directory.mkdir(exist_ok=True)
    environment[key] = str(directory)
run = subprocess.run([P22_PYTHON, "-c", __RUNNER__], cwd=ROOT,
                     env=environment, capture_output=True, text=True, timeout=240)
print(run.stdout)
if run.stderr:
    print(run.stderr)
run.check_returncode()
""".replace("__RUNNER__", repr(RUNNER))

DISPLAY = """from IPython.display import Markdown, display
executed = json.loads((ROOT / "P22_paired_workflow.executed.ipynb").read_text())
for cell in executed["cells"]:
    if cell["cell_type"] == "markdown":
        display(Markdown("".join(cell["source"])))
    else:
        for output in cell.get("outputs", []):
            if output["output_type"] == "stream":
                print("".join(output["text"]))
            elif "data" in output:
                display({k: "".join(v) if isinstance(v, list) else v
                         for k, v in output["data"].items()}, raw=True)
import zipfile
ARCHIVE = ROOT / "P22_paired_colab_verification.zip"
with zipfile.ZipFile(ARCHIVE, "x", zipfile.ZIP_DEFLATED) as archive:
    for name in (*PAYLOAD, "P22_paired_workflow.executed.ipynb", "verification.json"):
        archive.write(ROOT / name, name)
print("VERIFIED: 9 unchanged code cells, 181 offline tests; scientific result still INCONCLUSIVE.")
print("Evidence archive:", ARCHIVE)
"""


def build():
    payload = {name: (REPO / name).read_text(encoding="utf-8") for name in FILES}
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in payload.items()}
    materialize = MATERIALIZE.replace("__PAYLOAD__", repr(payload)).replace(
        "__HASHES__", repr(hashes)
    )
    return nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                "# P22 paired workflow — standalone Colab CPU runner\n\n"
                "Run all cells on **free CPU**. No Drive mount, GPU, dataset acquisition, or real "
                "training. Setup may download Python 3.11 and four notebook/test packages.\n\n"
                "The unchanged 17-cell source notebook runs in a separate Python 3.11 kernel; "
                "this does not replace Colab's native kernel. All nine code cells must pass. "
                "Saved RNA findings are displayed, not recomputed. Relative links refer to "
                "the full repository and are not all bundled. Final cell offers an evidence ZIP."
            ),
            *[
                nbformat.v4.new_code_cell(
                    "#@title " + title + "\n" + source,
                    metadata={"cellView": "form"},
                )
                for title, source in (
                    ("Verify embedded supporting files", materialize),
                    ("Prepare Python 3.11 (CPU only)", ENVIRONMENT),
                    ("Execute the unchanged notebook and verify outputs", EXECUTE),
                    ("Show results and package evidence", DISPLAY),
                )
            ],
            nbformat.v4.new_code_cell(
                "from google.colab import files\nfiles.download(str(ARCHIVE))"
            ),
        ],
        metadata={
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "p22_scope": "offline_evidence_and_tests",
            "p22_payload_sha256": hashes,
        },
    )


if __name__ == "__main__":
    # ponytail: explicit 12-file allowlist; no checkout archive or dependency vendoring.
    with Path(sys.argv[1]).open("x", encoding="utf-8") as target:
        nbformat.write(build(), target)
