"""X6 paper-revision checks: DRAFT_V3, chr21-forced + detectability phrases, fig7."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


make_figures = _load("make_figures_v6", "paper/make_figures.py")


def test_draft_v3_label_and_phrases():
    draft = (ROOT / "paper" / "draft.md").read_text(encoding="utf-8")
    assert "DRAFT_V3_COMPLETE" in draft
    assert "chr21-forced" in draft
    assert "detectability" in draft.lower()


def test_make_figures_builds_fig7_detectability(tmp_path):
    src = ROOT / "docs" / "nn_v2" / "v6" / "detectability.json"
    data = make_figures.load_source(src)
    written = make_figures.build_fig7(data, tmp_path)
    names = {p.name for p in written}
    assert "fig7_detectability.pdf" in names
    assert "fig7_detectability.png" in names


def test_make_figures_detectability_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(make_figures, "DEFAULT_DETECT", ROOT / "docs" / "nn_v2" / "v6" / "detectability.json")
    rc = make_figures.main(["--only", "detectability", "--outdir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "fig7_detectability.png").exists()
