"""sign_proposer --reflexes scores against a root header's other alternates and the forms in every Semitic
language cell, names the language of each such match, and stays off unless asked. The reflex keys are given
inline; no index is read. No network.
"""
from __future__ import annotations

from tools.linear_a import cognate_search as cs
from tools.linear_a import sign_proposer as sp


def _fake_keys(monkeypatch, keys):
    monkeypatch.setattr(cs, "_reflex_keys", lambda: tuple(keys))


RAW_ROOTS = [{"Number": "1", "Proto-Semitic": "*zapp-/*zabb-", "Meaning": "'bristle'",
              "Analogues": {"Ugaritic": "zp 'x' (DUL 1)"}}]


def test_reflex_entries_add_the_other_alternate_and_each_language_cell(monkeypatch):
    _fake_keys(monkeypatch, [("1", "Arabic", "zbb", "zabab", "*zapp-/*zabb-", "'hair'"),      # the header has it
                             ("1", "Hebrew", "kkr", "kikkār", "*zapp-/*zabb-", "'disk'"),
                             ("1", "Ugaritic", "kkr", "kkr", "*zapp-/*zabb-", "'talent'")])
    base = sp._prepare_root_entries(RAW_ROOTS)
    assert "zbb" not in [e["root"] for e in base]                 # the first alternate only
    extra = sp.reflex_root_entries(RAW_ROOTS, base)
    assert [(e["root"], e["source"], e["form"]) for e in extra] == [
        ("zbb", "Proto-Semitic", ""), ("kkr", "Ugaritic", "kkr")]  # Ugaritic before Hebrew; no skeleton twice


def test_a_match_through_a_cell_names_its_language(monkeypatch):
    _fake_keys(monkeypatch, [("1", "Hebrew", "kkr", "kikkār", "*zapp-/*zabb-", "'disk'")])
    roots = sp.reflex_root_entries(RAW_ROOTS, [])
    on = sp.root_matches_for_skeleton("kkr", {"roots": roots, "reflexes": True})
    off = sp.root_matches_for_skeleton("kkr", {"roots": roots})
    assert on[0]["root"] == "kkr" and on[0]["language"] == "Hebrew"
    assert off[0]["language"] == "Proto-Semitic"


def test_reflexes_off_by_default_and_a_missing_index_is_reported(monkeypatch):

    def missing():
        raise FileNotFoundError("root_index.sqlite not built")

    monkeypatch.setattr(cs, "_reflex_keys", missing)
    plain = sp.propose_sign_value("*312", {"candidates": ["zo"], "top": 1})
    asked = sp.propose_sign_value("*312", {"candidates": ["zo"], "top": 1, "reflexes": True})
    assert "reflex_note" not in plain
    assert "not built" in asked["reflex_note"]
    assert asked["candidates"] == plain["candidates"]
