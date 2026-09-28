"""P5: professor update v5 coverage (D1–D13) and length bound."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "docs" / "nn_v2" / "v5" / "PROFESSOR_UPDATE_v5.md"


def _body_words(text: str) -> int:
    """Word count excluding the markdown table body (header + separator + rows)."""
    lines = text.splitlines()
    out: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            in_table = True
            continue
        if in_table and not stripped.startswith("|"):
            in_table = False
        if not in_table:
            out.append(line)
    return len(" ".join(out).split())


def test_professor_update_v5_exists() -> None:
    assert UPDATE.is_file(), f"missing {UPDATE}"


def test_professor_update_v5_covers_d1_d13() -> None:
    text = UPDATE.read_text(encoding="utf-8")
    for i in range(1, 14):
        assert f"D{i}" in text, f"missing D{i}"
    assert "unsent" in text.lower()
    assert "immigration" not in text.lower()


def test_professor_update_v5_statuses_and_word_bound() -> None:
    text = UPDATE.read_text(encoding="utf-8")
    assert "| D1 |" in text and "| D13 |" in text
    assert "DONE" in text
    n = _body_words(text)
    assert n <= 600, f"body words {n} > 600 (table excluded)"


def test_professor_update_v5_leads_with_plain_result() -> None:
    text = UPDATE.read_text(encoding="utf-8")
    head = text[:800].lower()
    assert "b_null" in head
    assert "ladder_v3" in head or "ladder_v3" in text.lower()
