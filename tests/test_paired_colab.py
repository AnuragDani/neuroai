import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def test_colab_bundle_runs_unchanged_notebook_without_checkout(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "build_paired_colab", ROOT / "scripts/build_paired_colab.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    notebook = module.build()
    nbformat.validate(notebook)
    monkeypatch.chdir(tmp_path)
    namespace = {}
    exec(notebook.cells[1].source, namespace)
    root = namespace["ROOT"]
    assert root != ROOT and root.is_dir()
    assert (root / module.SOURCE).read_bytes() == (ROOT / module.SOURCE).read_bytes()
    assert set(namespace["PAYLOAD"]) == set(module.FILES)
    exec(notebook.cells[2].source, namespace)
    assert namespace["P22_PYTHON"] == sys.executable
    profile = root / "ipythondir/profile_default"
    profile.mkdir(parents=True)
    (profile / "ipython_kernel_config.py").write_text(
        "c = get_config()\n"
        "c.IPKernelApp.kernel_class = 'google.colab._kernel.Kernel'\n"
        "c.InteractiveShellApp.extensions = ['google.colab']\n"
    )
    exec(notebook.cells[3].source, namespace)
    exec(notebook.cells[4].source, namespace)
    with zipfile.ZipFile(namespace["ARCHIVE"]) as archive:
        assert set(archive.namelist()) == set(module.FILES) | {
            "P22_paired_workflow.executed.ipynb",
            "verification.json",
        }
        assert archive.read(module.SOURCE) == (ROOT / module.SOURCE).read_bytes()
    executed = nbformat.read(root / "P22_paired_workflow.executed.ipynb", as_version=4)
    source = nbformat.read(ROOT / module.SOURCE, as_version=4)
    assert [(c.id, c.source) for c in executed.cells] == [(c.id, c.source) for c in source.cells]
    code = [c for c in executed.cells if c.cell_type == "code"]
    assert [c.execution_count for c in code] == list(range(1, 10))
    assert not [o for c in code for o in c.outputs if o.output_type == "error"]
    assert "181 passed" in "".join(o.get("text", "") for o in code[1].outputs)
    decision = json.loads("".join(o.get("text", "") for o in code[-1].outputs))
    assert decision["scientific_outcome"] == "INCONCLUSIVE"
    assert decision["training_performed"] is False
    assert decision["live_requests_attempted"] == 0
    assert decision["live_allowed"] is False
