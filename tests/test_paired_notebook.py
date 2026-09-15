"""The paired-workflow notebook must run offline from a fresh Jupyter kernel."""

import hashlib
import json
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/P22_paired_workflow.ipynb"


def test_paired_notebook_has_clean_executable_sources():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    assert notebook.metadata["p22_scope"] == "offline_evidence_and_tests"
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert code[1].id == "offline-tests"
    assert len(code) >= 6
    for cell in code:
        assert cell.execution_count is None
        assert cell.outputs == []
        compile(cell.source, cell.id, "exec")


def test_paired_notebook_runs_in_fresh_kernel(tmp_path):
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    original_sources = [cell.source for cell in notebook.cells]
    protected = [
        ROOT / "P22_down_syndrome_all_in_one.ipynb",
        ROOT / "configs/development_object_source_contract.json",
        ROOT / "docs/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md",
        ROOT / "tasks/plan.md",
        ROOT / "tasks/todo.md",
    ]
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    client = NotebookClient(
        notebook,
        kernel_name="python3",
        timeout=120,
        allow_errors=False,
        resources={"metadata": {"path": str(ROOT)}},
    )
    manager = client.create_kernel_manager()
    manager.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    client.execute(cwd=str(ROOT))
    assert not manager.has_kernel
    assert [cell.source for cell in notebook.cells] == original_sources
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert [cell.execution_count for cell in code] == list(range(1, len(code) + 1))
    assert not any(out.output_type == "error" for cell in code for out in cell.outputs)
    final_cell = next(cell for cell in code if cell.id == "decision")
    final = json.loads("".join(out.get("text", "") for out in final_cell.outputs))
    assert final["offline_tests_passed"] is True
    assert final["source_status"] == "SOURCE_UNRESOLVED"
    assert final["scientific_outcome"] == "INCONCLUSIVE"
    assert final["live_requests_attempted"] == 0
    assert final["training_performed"] is False
    assert final["live_allowed"] is False
    assert final["output_reserved"] is False
    assert final["demo_header_is_synthetic"] is True
    assert before == {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
    }
    nbformat.write(notebook, tmp_path / "P22_paired_workflow.executed.ipynb")
