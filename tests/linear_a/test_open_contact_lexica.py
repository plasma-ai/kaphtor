"""The open lexica in the root index's Syriac and Akkadian slots (data/contact/syriac_lexicon.md and
akkadian_lexicon.md): each Syriac root is its Wiktionary letters read as sedra.py reads Syriac, each Akkadian row is
the CAMS/GKAB glossary's with ORACC's h written ḫ and every ORACC name class marked as a name, and the root index keys
every row that has a consonant. Nothing here writes.
"""
import json
import re
import unicodedata

import pytest

from tools.core import root_index as ri
from tools.core.sedra import LETTERS
from tools.core.semitic_root_schema import daughter_root_pattern
from tools.paths import ANE_DATA, CONTACT_DATA, SEMITIC_ROOTS_DATA

SYRIAC = CONTACT_DATA / "syriac_lexicon.jsonl"
AKKADIAN = CONTACT_DATA / "akkadian_lexicon.jsonl"
GLOSSARY = ANE_DATA / "akkadian_literary.jsonl"
# the keying reads each form through the correspondence table
TABLE = SEMITIC_ROOTS_DATA / "semitic_correspondences.json"
MISSING = [p.name for p in (SYRIAC, AKKADIAN, GLOSSARY, TABLE) if not p.exists()]
pytestmark = [pytest.mark.data,
              pytest.mark.skipif(bool(MISSING), reason=f"{', '.join(MISSING)} not in this checkout")]

ORACC_NAMES = {"AN", "CN", "DN", "EN", "FN", "GN", "LN", "MN", "ON", "PN", "QN", "RN", "SN", "TN", "WN", "YN"}
LEXICA = {lex.name: lex for lex in ri.LEXICA}


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_syriac_root_is_its_letters_in_latin():
    latin = {syr: lat for syr, lat in LETTERS.values()}
    for r in rows(SYRIAC):
        assert r["root"] == "-".join(latin[x] for x in r["root_original"].split()), r["id"]
        pattern = daughter_root_pattern(r["root"], "Syrian Aramaic", "aramaic")
        assert pattern.tokens and not [f for f in pattern.flags if f.startswith("unmapped")], r["id"]


def test_syriac_ids_are_distinct_and_names_are_proper_nouns():
    syriac = rows(SYRIAC)
    assert len({r["id"] for r in syriac}) == len(syriac)
    assert not [r["id"] for r in syriac if r["pos"] == "name"]
    assert all(r["source_refs"][0]["url"].startswith("https://en.wiktionary.org/wiki/") for r in syriac)


def test_akkadian_rows_are_the_glossarys_with_h_written_ḫ():
    akkadian, glossary = rows(AKKADIAN), rows(GLOSSARY)
    assert [r["id"] for r in akkadian] == [g["id"] for g in glossary]
    for r, g in zip(akkadian, glossary):
        assert r["form_original"] == g["form_original"] and r["oracc_pos"] == g["pos"], r["id"]
        assert r["form"] == r["normalized"] == unicodedata.normalize("NFC", g["cf"]).replace("h", "ḫ").replace("H", "Ḫ")


def test_every_oracc_name_class_is_a_proper_noun():
    for r in rows(AKKADIAN):
        assert (r["pos"] == "proper_noun") == (r["oracc_pos"] in ORACC_NAMES), r["id"]
        assert r["pos"] == "proper_noun" or r["pos"] == r["oracc_pos"], r["id"]


@pytest.mark.parametrize("name", ["syriac", "akkadian"])
def test_the_index_keys_every_row_with_a_consonant(name):
    lex = LEXICA[name]
    keyless = [lm.forms for lm in ri.iter_lexemes(lex) if not ri.lexeme_keys(lm, lex.scheme)[0]]
    assert not [forms for forms in keyless if any(re.search(r"[^aeiouāēīūâêîûAEIOU\s]", f) for f in forms)]
