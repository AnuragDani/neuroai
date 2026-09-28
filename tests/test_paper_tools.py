"""Focused tests for the paper tooling (P1 checker; P2 figures).

Run: PY -m pytest -q tests/test_paper_tools.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_paper = _load("check_paper", "paper/check_paper.py")
make_figures = _load("make_figures", "paper/make_figures.py")

VALID_DRAFT = """\
## Abstract
We ask when cross-modal attention helps on paired RNA and ATAC data.

## Introduction
Attention fusion is an adapted combination of known techniques
[@tsai2019multimodal; @nagrani2021attention].

## Related Work
Per-cell modality weights [@hao2021integrated], MultiVI [@ashuach2023multivi]
and donor-level inference [@squair2021confronting] are precedents.

## Methods
Models are fit with donor-held-out folds.

## Results
The primary estimate was 0.05.

## Discussion
We report the estimate without over-reading the attention weights.

## Limitations
Thirty donors; internal cohort only.

## References
- Tsai et al. 2019.
"""

CLAIMS = "sentence_id,value,json_path,json_key\ns1,0.05,docs/nn_v2/x.json,estimate\n"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _run(tmp_path: Path, draft: str, refs_text: str, claims: str):
    valid = check_paper.parse_bib_keys(refs_text)
    return check_paper.run_checks(draft, valid, claims, tmp_path)


# --- check (1) citations ---------------------------------------------------


def test_citations_pass():
    refs = "\n".join(
        f"@article{{{k}," for k in sorted(check_paper.parse_citekeys(VALID_DRAFT))
    )
    report = _run(Path("."), VALID_DRAFT, refs, CLAIMS)
    assert report["citations"] == []


def test_citations_fail_unknown_key():
    refs = "@article{hao2021integrated,"
    draft = VALID_DRAFT.replace("[@hao2021integrated]", "[@notarealkey]")
    report = _run(Path("."), draft, refs, CLAIMS)
    assert any("@notarealkey" in p for p in report["citations"])


# --- check (2) numbers in Abstract/Results ---------------------------------


def test_numbers_pass():
    report = _run(Path("."), VALID_DRAFT, "@article{hao2021integrated,", CLAIMS)
    assert report["numbers"] == []


def test_numbers_fail_missing_value():
    draft = VALID_DRAFT.replace("was 0.05", "was 0.99")
    report = _run(Path("."), draft, "@article{hao2021integrated,", CLAIMS)
    assert any("0.99" in p for p in report["numbers"])


# --- check (3) forbidden words ---------------------------------------------


def test_forbidden_pass():
    report = _run(Path("."), VALID_DRAFT, "@article{hao2021integrated,", CLAIMS)
    assert report["forbidden"] == []


def test_forbidden_fail_novel():
    draft = VALID_DRAFT.replace("We report the estimate", "This is a novel result. We report")
    report = _run(Path("."), draft, "@article{hao2021integrated,", CLAIMS)
    assert any("novel" in p for p in report["forbidden"])


# --- check (4) figure paths ------------------------------------------------


def test_figures_pass(tmp_path):
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "fig2_planted.png").write_bytes(b"png")
    draft = VALID_DRAFT + "\n![Fig 2](figures/fig2_planted.png)\n"
    report = _run(tmp_path, draft, "@article{hao2021integrated,", CLAIMS)
    assert report["figures"] == []


def test_figures_fail_missing(tmp_path):
    draft = VALID_DRAFT + "\n![Fig 2](figures/fig2_planted.png)\n"
    report = _run(tmp_path, draft, "@article{hao2021integrated,", CLAIMS)
    assert any("fig2_planted.png" in p for p in report["figures"])


# --- check (5) word counts -------------------------------------------------


def test_word_counts_pass():
    report = _run(Path("."), VALID_DRAFT, "@article{hao2021integrated,", CLAIMS)
    assert report["word_counts"] == []


def test_word_counts_fail_abstract_too_long():
    long_abstract = "## Abstract\n" + " ".join(["word"] * 201) + "\n"
    rest = "## Introduction\n" + VALID_DRAFT.split("## Introduction\n", 1)[1]
    report = _run(Path("."), long_abstract + rest, "@article{hao2021integrated,", CLAIMS)
    assert any("Abstract word count 201" in p for p in report["word_counts"])


# --- CLI on a missing draft does not crash ---------------------------------


def test_main_missing_draft_returns_2(tmp_path, capsys):
    rc = check_paper.main(["--draft", str(tmp_path / "nope.md")])
    assert rc == 2
    assert "draft not found" in capsys.readouterr().out


def test_main_runs_on_current_draft_without_crash():
    """P1 acceptance: runs on the current paper/draft.md without crashing."""
    draft = _ROOT / "paper" / "draft.md"
    rc = check_paper.main(["--draft", str(draft), "--json"])
    assert rc in (0, 1, 2)


# --- P2 make_figures -------------------------------------------------------


def test_make_figures_missing_source_raises(tmp_path):
    with pytest.raises(make_figures.MissingSourceError):
        make_figures.load_source(tmp_path / "nope.json")


def test_make_figures_missing_source_cli_exit2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(make_figures, "DEFAULT_PLANTED", tmp_path / "nope.json")
    rc = make_figures.main(["--only", "planted", "--outdir", str(tmp_path / "figs")])
    assert rc == 2
    assert "source JSON not found" in capsys.readouterr().err


def test_make_figures_builds_fig2(tmp_path):
    """P2 acceptance: Fig 2 PNG+PDF are written from the real planted JSON."""
    src = _ROOT / "docs" / "nn_v2" / "planted_benchmark.json"
    if not src.exists():
        pytest.skip("planted_benchmark.json not present")
    data = make_figures.load_source(src)
    written = make_figures.build_fig2(data, tmp_path)
    names = sorted(p.name for p in written)
    assert names == ["fig2_planted.pdf", "fig2_planted.png"]
    for path in written:
        assert path.exists() and path.stat().st_size > 0


def test_make_figures_builds_fig3_ladder(tmp_path):
    src = _ROOT / "docs" / "nn_v2" / "ladder_summary.json"
    if not src.exists():
        pytest.skip("ladder_summary.json not present")
    data = make_figures.load_source(src)
    written = make_figures.build_fig3(data, tmp_path)
    assert sorted(p.name for p in written) == ["fig3_ladder.pdf", "fig3_ladder.png"]
    for path in written:
        assert path.stat().st_size > 0


def test_make_figures_builds_fig4_faithfulness(tmp_path):
    src = _ROOT / "docs" / "nn_v2" / "faithfulness.json"
    if not src.exists():
        pytest.skip("faithfulness.json not present")
    data = make_figures.load_source(src)
    written = make_figures.build_fig4(data, tmp_path)
    assert sorted(p.name for p in written) == [
        "fig4_faithfulness.pdf",
        "fig4_faithfulness.png",
    ]
    for path in written:
        assert path.stat().st_size > 0


def test_make_figures_builds_fig5_spectrum(tmp_path):
    src = _ROOT / "docs" / "nn_v2" / "spectrum.json"
    if not src.exists():
        pytest.skip("spectrum.json not present")
    data = make_figures.load_source(src)
    written = make_figures.build_fig5(data, tmp_path)
    assert sorted(p.name for p in written) == ["fig5_spectrum.pdf", "fig5_spectrum.png"]
    for path in written:
        assert path.stat().st_size > 0


def test_make_figures_all_writes_fig3_to_fig5(tmp_path, monkeypatch):
    """N25: with all source JSON present, --only all emits fig3–fig5 stems."""
    for name, default in (
        ("planted_benchmark.json", "DEFAULT_PLANTED"),
        ("ladder_summary.json", "DEFAULT_LADDER"),
        ("faithfulness.json", "DEFAULT_FAITH"),
        ("spectrum.json", "DEFAULT_SPECTRUM"),
    ):
        src = _ROOT / "docs" / "nn_v2" / name
        if not src.exists():
            pytest.skip(f"{name} not present")
        monkeypatch.setattr(make_figures, default, src)
    out = tmp_path / "figs"
    rc = make_figures.main(["--only", "all", "--outdir", str(out)])
    assert rc == 0
    for stem in (
        "fig1_schematic",
        "fig2_planted",
        "fig3_ladder",
        "fig4_faithfulness",
        "fig5_spectrum",
    ):
        assert (out / f"{stem}.png").stat().st_size > 0
        assert (out / f"{stem}.pdf").stat().st_size > 0
    assert make_figures.SKIPPED_FIGURES == []
