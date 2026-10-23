import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluate import bool_match, date_match, parties_f1, text_match  # noqa: E402


def test_date_match_both_null():
    assert date_match(None, None) is True


def test_date_match_normalizes_case_and_whitespace():
    assert date_match(" 2001-08-13 ", "2001-08-13") is True


def test_date_match_mismatch():
    assert date_match("2001-08-13", "2001-08-14") is False


def test_bool_match_coerces_truthy():
    assert bool_match(True, True) is True
    assert bool_match(False, True) is False


def test_text_match_fuzzy_ok_for_close_strings():
    assert text_match("Delaware", "State of Delaware") is True


def test_text_match_both_null():
    assert text_match(None, None) is True


def test_parties_f1_perfect_match():
    pred = [{"name": "Acme Corp", "role": "first_party"}]
    gold = [{"name": "Acme Corp", "role": "first_party"}]
    assert parties_f1(pred, gold) == 1.0


def test_parties_f1_partial_match():
    pred = [{"name": "Acme Corp"}, {"name": "Totally Unrelated Inc"}]
    gold = [{"name": "Acme Corporation"}, {"name": "Beta LLC"}]
    f1 = parties_f1(pred, gold)
    assert 0.0 < f1 < 1.0


def test_parties_f1_empty_both():
    assert parties_f1([], []) == 1.0


def test_parties_f1_empty_pred_nonempty_gold():
    assert parties_f1([], [{"name": "Acme"}]) == 0.0
