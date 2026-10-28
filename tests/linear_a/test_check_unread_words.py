"""`check_unread_words`: what counts as a reading, and how a broken entry finds its corpus token.

Unit tests only: every input is written inline, and the sign pattern is set here instead of read from
`sign_values.json`.
"""
import json
import re
from collections import Counter

import pytest

from tools.linear_a.validation import check_unread_words as b


@pytest.fixture(autouse=True)
def plain_signs(monkeypatch):
    monkeypatch.setattr(b, "SYL", re.compile(r"[BCDGHJKLMNPQRSTWZ]{0,2}[AEIOU][₂₃]?|\*\d+"))


@pytest.mark.parametrize("gloss", [
    "personal or institutional label",
    "personal or institutional name; unidentified",
    "administrative label or name",
    "untranslated administrative heading or entity",
    "unidentified entity: 29",
    "unidentified header entity or account label",
    "transaction sign + logogram",
    "personal name(?)",
])
def test_role_labels_are_not_readings(gloss):
    assert b.LABEL_ONLY.search(gloss)


@pytest.mark.parametrize("gloss", [
    "my Creator (divine epithet)",
    "Rule! (jussive/imperative)",
    "personal name ʿAnānu (√ʿ-n-n)",
    "PN/epithet: 'Earth is my mother' (pre-Greek Artemis)",
    "the sanctuary (base/foundation)",
    "broken bread (round loaf)",
])
def test_glosses_stay_readings(gloss):
    assert not b.LABEL_ONLY.search(gloss)


@pytest.mark.parametrize("gloss", [
    "intact and undotted. No reading.",
    "KE dotted (GORILA IV 154–155). Not readable.",
    "a divider, not a sign group. Not a word.",
])
def test_glosses_ending_in_a_verdict_are_not_readings(gloss):
    assert b.LABEL_ONLY.search(gloss)


@pytest.mark.parametrize("gloss", ["broken word", "broken word, 1"])
def test_broken_word_labels_are_not_readings(gloss):
    assert b.LABEL_ONLY.search(gloss)


@pytest.mark.parametrize("reading, word", [
    ("unread", "DA-TA-RE"),
    ("Didizake", "DI-DI-ZA-KE"),  # the signs spelled out, not a reading
    ("Sidu(?)", "SI-DU"),
    ("Pa₃-ni-na", "PA₃-NI-NA"),
])
def test_placeholder_readings_propose_nothing(reading, word):
    assert not b.proposes(reading, word)


@pytest.mark.parametrize("reading, word", [
    ("burēyā", "PU₂-RE-JA"),
    ("dubur", "PU₂-RE"),
    ("Qaqqaru", "QA-QA-RU"),  # a reading may keep the signs' sounds
])
def test_readings_propose(reading, word):
    assert b.proposes(reading, word)


def test_a_speculative_syllabogram_stays_in_its_word(tmp_path, monkeypatch):
    # *21F is held in `signs` as speculative, outside resolution_summary: still a syllable, not a logogram
    (tmp_path / "sign_values.json").write_text(json.dumps({
        "resolution_summary": {"phonemic": ["AU=au"], "proposed": {"phonemic": [{"entry": "*306=ʿA"}]}},
        "signs": {"*21F": {"primary": {"consonant": "h", "vowel": "a"}},
                  "*306": {"primary": {"consonant": "ʿ", "vowel": "a"}}}}), encoding="utf-8")
    monkeypatch.undo()
    b.load_sign_classes(tmp_path)
    assert b.syllabic_runs("*21F-JA-DU") == ["*21F-JA-DU"]
    assert b.syllabic_runs("*309B-KI-PU") == ["KI-PU"]  # a lettered sign with no syllabic record splits
    assert b.make_lex_hit({"TU": {"word": "TU"}})("*306-TU") is None  # *306 is no logogram prefix


def _occ(*tokens):
    idx, raw_idx = {}, {}
    for doc, site, tok in tokens:
        raw_idx.setdefault(tok, []).append((doc, site))
        for k in b.keys_of(b.parts_of(tok)):
            idx.setdefault(k, []).append((doc, site))
    return idx, raw_idx


def _entry(word, docs, sites):
    return {"word": word, "status": "unread", "frequency": len(docs), "attestations": docs, "sites": sites,
            "cross_site": len(sites) > 1}


def _doc(*ents):
    return {"entries": list(ents), "excluded": {}, "stats": {
        "corpus_words": 0, "read": 0, "excluded_tokens": {}, "unread_listed": len(ents),
        "by_status": dict(Counter(e["status"] for e in ents)), "hapax": sum(e["frequency"] == 1 for e in ents),
        "repeated": sum(e["frequency"] >= 2 for e in ents), "cross_site": sum(e["cross_site"] for e in ents),
        "surface_damaged": 0}}


def test_bracketed_entry_ignores_a_hyphen_at_the_bracket():
    # the corpus writes one broken form as A-RA-[ on KH79+89 and A-RA[ on ARKH1a; a word page joins them
    occ = _occ(("KH79+89", "Khania", "A-RA-["), ("ARKH1a", "Arkhanes", "A-RA["), ("KN32a", "Knossos", "]A-PA-["))
    doc = _doc(_entry("A-RA-[", ["ARKH1a", "KH79+89"], ["Arkhanes", "Khania"]),
               _entry("]A-PA-[", ["KN32a"], ["Knossos"]))
    assert b.check(doc, [], occ, {}) == []


def test_bracketed_entry_still_needs_its_own_break():
    # ]A-PA-[ is broken at both ends; A-PA-[ on another tablet is a different token
    occ = _occ(("ARKH1a", "Arkhanes", "A-PA-["), ("KN32a", "Knossos", "]A-PA-["))
    doc = _doc(_entry("]A-PA-[", ["ARKH1a", "KN32a"], ["Arkhanes", "Knossos"]))
    assert {k for k, _, _ in b.check(doc, [], occ, {})} == {"field"}


def _lex(**entries):
    """word -> (reading, attestations)"""
    return lambda w: ({"word": w, "reading": entries[w][0], "attestations": entries[w][1]}
                      if w in entries else None)


def test_a_listed_word_the_lexicon_reads_on_broken_witnesses_only_is_flagged():
    # TY 2 *309C-[?]-RU-KA and HT 70 ]QA-*118-SA: the lexicon reads both on those tablets alone;
    # RU-KA inside U-NA-RU-KA-NA-TI on PK Za 11, another word on a tablet the lexicon does not cite, saves nothing
    occ = _occ(("TY2", "Tylissos", "*309C-[?]-RU-KA"), ("HT70", "Haghia Triada", "]QA-*118-SA"))
    doc = _doc(_entry("RU-KA", ["TY2"], ["Tylissos"]), _entry("]-QA-*118-SA", ["HT70"], ["Haghia Triada"]))
    lex = _lex(**{"RU-KA": ("ruqāq", ["TY2"]), "QA-*118-SA": ("qaṭʿ-ša", ["HT70"])})
    intact = {"TY2": {"PA-DA"}, "PKZa11": {"U-NA-RU-KA-NA-TI"}}
    kinds = {(k, w) for k, w, _ in b.check(doc, [], occ, {}, lex_hit=lex, intact=intact)}
    assert kinds == {("lexicon_reads", "RU-KA"), ("lexicon_reads", "]-QA-*118-SA")}


def test_a_broken_witness_of_a_word_whole_elsewhere_stays_listed():
    # ]QA-QA-RU on HT 111a (QA-QA-RU whole on HT 118); ]-U-TI-NU on IO Za 11 (whole inside TA-NA-RA-TE-U-TI-NU on IO Za 2)
    occ = _occ(("HT111a", "Haghia Triada", "]QA-QA-RU"), ("IOZa11", "Iouktas", "]-U-TI-NU"))
    doc = _doc(_entry("]QA-QA-RU", ["HT111a"], ["Haghia Triada"]), _entry("]-U-TI-NU", ["IOZa11"], ["Iouktas"]))
    lex = _lex(**{"QA-QA-RU": ("Qaqqaru", ["HT118", "HT93a"]), "U-TI-NU": ("-u-tī-n(u)", ["IOZa2", "IOZa11"])})
    intact = {"HT118": {"QA-QA-RU"}, "IOZa2": {"TA-NA-RA-TE-U-TI-NU"}}
    assert b.check(doc, [], occ, {}, lex_hit=lex, intact=intact) == []


def test_intact_tokens_skip_bracketed_and_surface_damaged_tokens(tmp_path):
    corpus = {"X1": {"transliteratedWords": ["KU-RO", "\n", "]QA-QA-RU", "O-DA", "TA-NA-RA-TE-U-TI-NU"],
                     "words": ["𐘂𐘗", "\n", "𐝫𐘣𐘣𐘗", "𐘵𐘀𐝫", "𐘳𐘅𐘗𐘃𐘁𐘉𐘠𐘯"]},
              "X2": {"transliteratedWords": ["O-DA["]}}
    (tmp_path / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    assert b.intact_tokens(tmp_path) == {"X1": {"KU-RO", "TA-NA-RA-TE-U-TI-NU"}}
