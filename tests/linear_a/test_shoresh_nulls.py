"""shoresh_nulls: the root keys, the name test and the decoy draws Shoresh borrows from the project's validation
scripts. Every expected value here is the private originals' output on the same input, so the copies are pinned to
them. Nothing here writes; the corpus is a two-document fixture.
"""
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core import shoresh_nulls as sn
from tools.paths import NotInCheckout

WORDS = ["KU-PA₃-NU", "KI-RE-TA", "A-SA-SA-RA-ME", "DA-KU-SE-NE", "A-*999-RA", "SA"]


def test_the_geminable_stops():
    assert sn.GEMINABLE_STOPS == {"t", "d", "k", "q", "p", "b"}


@pytest.mark.parametrize("form,root", [
    ("*ʾa-ṯ-r", "ʾṯr"), ("šamaš (1)", "šmš"), ("ka-ta-bu, ka-ta-ba", "ktb"), ("b-n-y/*b-n-w", "bny"), ("qatal2", "qtl"),
])
def test_the_consonantal_root_key(form, root):
    assert sn._extract_consonantal_root(form) == root


@pytest.mark.parametrize("entry,named", [
    ({"Meaning": "Baal (DN)"}, True),
    ({"Meaning": "house", "Analogues": {"Ugaritic": "Ugarit (GN)"}}, True),
    ({"Meaning": "house"}, False),
])
def test_a_name_is_marked_in_the_meaning_or_an_analogue(entry, named):
    assert sn._is_onomastic(entry) is named


def test_the_gold_guard_spelling():
    assert sn.sign_group_key(" a-pa₃-ku- ") == ("A", "PA3", "KU")


@pytest.mark.parametrize("word,expected", [
    ("KU-PA₃-NU", ("kbn", [])), ("A-*999-RA", ("r", ["*999"])), ("A-TA-I-*301-WA-JA", ("tnwy", [])),
])
def test_the_loud_skeleton_names_unmapped_signs(word, expected):
    assert sn.loud_skeleton(word) == expected


def test_position_tables_skip_one_sign_and_unmapped_words():
    assert sn.position_tables(WORDS) == {
        "initial": (("A", "DA", "KI", "KU"), (1, 1, 1, 1)),
        "medial": (("KU", "PA₃", "RA", "RE", "SA", "SE"), (1, 1, 1, 1, 2, 1)),
        "final": (("ME", "NE", "NU", "TA"), (1, 1, 1, 1)),
    }


@pytest.mark.parametrize("seed,word", [(0, "KU-SA-NE"), (1, "DA-RE-NE"), (7, "DA-PA₃-NU")])
def test_fabricate_draws_the_same_decoy_for_a_seed(seed, word):
    tables = sn.position_tables(WORDS)
    assert sn.fabricate(random.Random(seed), 3, 3, tables, set(WORDS)) == word


@pytest.mark.parametrize("ocp", [True, False])
def test_fabricate_with_callers_tokens(ocp):
    tables = sn.position_tables(WORDS)
    assert sn.fabricate(random.Random(3), 3, 3, tables, set(WORDS), tokens=lambda w: w.split("-"), ocp=ocp) == "A-RE-NE"


def test_fabricate_never_returns_a_real_word():
    tables = sn.position_tables(["KU-PA₃-NU"])
    assert sn.fabricate(random.Random(0), 3, 3, tables, {"KU-PA₃-NU"}) is None


def test_fabricate_keeps_the_ocp_unless_told_not_to():
    tables = sn.position_tables(["SA-SA-RA"])
    assert sn.fabricate(random.Random(0), 3, 3, tables, set()) is None
    first_letters = lambda w: [s[0].lower() for s in w.split("-")]
    assert sn.fabricate(random.Random(0), 3, 3, tables, set(), tokens=first_letters, ocp=False) == "SA-SA-RA"


def test_the_permuted_consonant_map():
    cmap = sn.permuted_cons_map(random.Random(0))
    assert {s: cmap[s] for s in ("KU", "PA3", "NA", "A", "*301", "TA")} == {
        "KU": "p", "PA3": "m", "NA": "s", "A": None, "*301": "l", "TA": "s"}
    base = sn.base_consonant_map()
    assert sorted(c for c in cmap.values() if c) == sorted(c for c in base.values() if c)


def test_a_given_base_map_is_permuted():
    assert sn.permuted_cons_map(random.Random(0), sn.base_consonant_map()) == sn.permuted_cons_map(random.Random(0))
    base = {s: c for s, c in sn.base_consonant_map().items() if s not in {"*301", "*306"}} | {"PA3": "p"}
    cmap = sn.permuted_cons_map(random.Random(0), base)
    assert set(cmap) == set(base)
    assert sorted(c for c in cmap.values() if c) == sorted(c for c in base.values() if c)
    assert cmap != base


def test_corpus_words_are_the_multi_sign_words(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"HT1": {"transliteratedWords": ["KU-RO", "A", "1-2", "KU-RO"]},
                                  "HT2": {"transliteratedWords": ["*28B-NU", "\n"]}}), encoding="utf-8")
    monkeypatch.setattr(sn, "CORPUS_PATH", corpus)
    assert sn.load_corpus_words() == ["*28B-NU", "KU-RO"]


def test_a_missing_corpus_is_named(tmp_path, monkeypatch):
    monkeypatch.setattr(sn, "CORPUS_PATH", tmp_path / "corpus.json")
    with pytest.raises(NotInCheckout, match="corpus.json"):
        sn.load_corpus_words()
