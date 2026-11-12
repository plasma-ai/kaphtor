"""`check_unread_signs`: which corpus tokens are sign tokens, what the check reports, and the ranking.

Unit tests only: every input is written inline, and the sign pattern is set here instead of read from
`sign_values.json`.
"""
import re

import pytest

from tools.linear_a.validation import check_unread_signs as s
from tools.linear_a.validation import check_unread_words as w


@pytest.fixture(autouse=True)
def plain_signs(monkeypatch):
    monkeypatch.setattr(w, "SYL", re.compile(r"[BCDGHJKLMNPQRSTWZ]{0,2}[AEIOU][₂₃]?|\*\d+"))
    monkeypatch.setattr(w, "PHON_STAR", set())


LEXICON = {"KU": {"word": "KU", "reading": "kull"}, "GRA": {"word": "GRA", "reading": None}}


def lex_hit(token):
    return LEXICON.get(token)


CORPUS = {
    "D1": {"site": "Haghia Triada", "transliteratedWords": ["I"]},
    "D2": {"site": "Khania", "transliteratedWords": ["I", "\n", "5", "¹⁄₂"]},
    "D3": {"site": "Haghia Triada", "transliteratedWords": ["KU-RO", "𐄁", "*301+*311", "GRA", "3"]},
    "D4": {"site": "Haghia Triada", "transliteratedWords": ["KU", "*409-VS", "]TA", "𐝫"]},
    "D5": {"site": "Zakros", "transliteratedWords": ["SA-VIN", "9", "PA-[?]"]},
}


def test_a_sign_token_is_undamaged_and_no_word():
    found = {key: list(s.sign_tokens(rec)) for key, rec in CORPUS.items()}
    assert found == {"D1": ["I"], "D2": ["I"], "D3": ["*301+*311", "GRA"], "D4": ["KU", "*409-VS"],
                     "D5": ["SA-VIN"]}


def test_occurrences_leave_out_what_the_lexicon_reads_and_what_is_excluded():
    occ = s.occurrences(CORPUS, lex_hit, excluded={"SA-VIN"})
    assert occ == {"I": [("D1", "Haghia Triada"), ("D2", "Khania")], "*301+*311": [("D3", "Haghia Triada")],
                   "*409-VS": [("D4", "Haghia Triada")]}


def entry(sign, kind, status, frequency, attestations, sites):
    return {"sign": sign, "kind": kind, "status": status, "frequency": frequency, "attestations": attestations,
            "sites": sites, "cross_site": len(sites) > 1}


def doc(entries, **stats):
    counted = {"listed": len(entries), "by_status": {}, "by_kind": {}, "occurrences": 0, "hapax": 0, "cross_site": 0}
    for e in entries:
        counted["by_status"][e["status"]] = counted["by_status"].get(e["status"], 0) + 1
        counted["by_kind"][e["kind"]] = counted["by_kind"].get(e["kind"], 0) + 1
        counted["occurrences"] += e["frequency"]
        counted["hapax"] += e["frequency"] == 1
        counted["cross_site"] += e["cross_site"]
    return {"entries": entries, "excluded": {"SA-VIN": "kept out for the test"}, "stats": counted | stats}


GOOD = [entry("I", "syllabogram", "unread", 2, ["D1", "D2"], ["Haghia Triada", "Khania"]),
        entry("*301+*311", "ligature", "component_read", 1, ["D3"], ["Haghia Triada"]),
        entry("*409-VS", "vessel", "unread", 1, ["D4"], ["Haghia Triada"])]


def issues(document):
    return s.check(document, s.occurrences(CORPUS, lex_hit, document.get("excluded", {})), lex_hit)


def test_a_file_in_step_with_the_corpus_reports_nothing():
    assert issues(doc(GOOD)) == []


def test_an_unlisted_sign_is_reported():
    kinds = {(kind, sign) for kind, sign, _ in issues(doc(GOOD[:2]))}
    assert ("unlisted", "*409-VS") in kinds


def test_a_listed_sign_the_lexicon_reads_is_reported_once():
    found = issues(doc([*GOOD, entry("KU", "syllabogram", "unread", 1, ["D4"], ["Haghia Triada"])]))
    assert [(kind, sign) for kind, sign, _ in found] == [("now_read", "KU")]


def test_a_listed_sign_absent_from_the_corpus_is_reported():
    found = issues(doc([*GOOD, entry("O", "syllabogram", "unread", 1, ["D9"], ["Haghia Triada"])]))
    assert ("not_in_corpus", "O") in {(kind, sign) for kind, sign, _ in found}


def test_a_wrong_count_and_a_wrong_stat_are_reported():
    wrong = [entry("I", "syllabogram", "unread", 3, ["D1"], ["Haghia Triada"]), *GOOD[1:]]
    found = issues(doc(wrong, hapax=7))
    assert {(kind, sign) for kind, sign, _ in found} == {("field", "I"), ("stats", "hapax")}
    details = " ".join(detail for kind, sign, detail in found if sign == "I")
    assert "frequency" in details and "attestations" in details and "sites" in details and "cross_site" in details


def test_the_ranking_counts_only_records_where_the_sign_is_the_last_thing_unread():
    listed = {e["sign"]: e for e in GOOD}
    blocked = s.sole_blockers(CORPUS, translated={"D2"}, listed=listed, lex_hit=lex_hit, named={"KU-RO"})
    # D1: I alone. D2: translated. D3: only the ligature is unread (KU-RO is a name with a reading, GRA is read).
    # D4: the broken ]TA is unread beside the vessel sign. D5: nothing listed.
    assert blocked == {"I": ["D1"], "*301+*311": ["D3"]}


def test_a_ligature_with_an_unnamed_component_is_a_sign_token_and_no_damage():
    # VIR+[?] is the person sign joined to an element the transcription does not name; KH Wc 2100 is whole
    record = {"site": "Khania", "transliteratedWords": ["VIR+[?]", "VIR+[?]-I", "VIR+[?][", "VIR+[?]-[?]", "]HIDE+[?]"]}
    assert list(s.sign_tokens(record)) == ["VIR+[?]", "VIR+[?]-I"]
