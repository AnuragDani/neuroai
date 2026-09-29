"""P6/X6 paper-revision checks: DRAFT_V2→V3, per-fold AUROC phrase, fig6 builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


make_figures = _load("make_figures_v5", "paper/make_figures.py")


def test_draft_v2_complete_and_per_fold_auroc_phrase():
    text = (_ROOT / "paper" / "draft.md").read_text(encoding="utf-8")
    # V3 supersedes V2; either complete label is acceptable for the v5 content checks.
    assert ("DRAFT_V3_COMPLETE" in text) or ("DRAFT_V2_COMPLETE" in text)
    assert "per-fold AUROC" in text
    assert "0.924" in text  # positive control
    assert "PIPELINE_BUG_FIXED" in text


def test_make_figures_builds_fig6_per_fold(tmp_path):
    src = _ROOT / "docs" / "nn_v2" / "v5" / "per_fold_metrics.json"
    assert src.is_file()
    data = make_figures.load_source(src)
    written = make_figures.build_fig6(data, tmp_path)
    assert sorted(p.name for p in written) == [
        "fig6_per_fold_auroc.pdf",
        "fig6_per_fold_auroc.png",
    ]
    for path in written:
        assert path.stat().st_size > 0
