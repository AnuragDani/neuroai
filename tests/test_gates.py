"""Tests for human-readable G0-G9 gate board."""

from p22.eval.gates import (
    GATE_IDS,
    GATE_QUESTIONS,
    ONE_NOTEBOOK_CONTRACT,
    STATUS_BLOCKED,
    STATUS_PASS,
    empty_board,
    make_gate,
)


def test_gate_ids_are_g0_through_g9():
    assert tuple(f"G{index}" for index in range(10)) == GATE_IDS
    assert set(GATE_QUESTIONS) == set(GATE_IDS)


def test_one_notebook_contract_names_canonical_notebook():
    assert "P22_down_syndrome_all_in_one.ipynb" in ONE_NOTEBOOK_CONTRACT
    assert "never disease evidence" in ONE_NOTEBOOK_CONTRACT


def test_gate_board_records_status_map():
    board = empty_board()
    board.set(make_gate("G0", STATUS_PASS, evidence={"python": "3.11"}))
    board.set(make_gate("G3", STATUS_BLOCKED, notes="approval absent"))
    rows = board.as_rows()
    assert rows[0]["status"] == STATUS_PASS
    assert rows[3]["status"] == STATUS_BLOCKED
    assert rows[9]["status"] == "PENDING"
    assert board.status_map() == {"G0": STATUS_PASS, "G3": STATUS_BLOCKED}
