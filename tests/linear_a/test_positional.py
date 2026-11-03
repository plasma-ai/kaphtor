"""tools/core/positional.py: token classes, anchors, line spans and quantities.

Token lists are copied from corpus records (HT89, HT13, HT91, KEWc2, HT127b, GOWc3), so the unit tests read no data.
The `data` tests read data/linear-a/sign_values.json (lettered syllabograms) and corpus.json (the sweep), read-only.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core import positional as p
from tools.paths import LINEAR_A_DATA

HT89 = ["A-SA-RA₂", "*307", "*305", "23", "\n", "JU+*317+QE", "22", "\n", "MA-I-MI", "24", "\n",
        "VIR+*313a", "13", "\n", "TA-RA", "5", "\n", "KU-RO", "87"]
HT13 = ["KA-U-DE-TA", "VIN", "𐄁", "TE", "𐄁", "\n", "RE-ZA", "5", "¹⁄₂", "\n", "TE-TU", "56", "\n",
        "TE-KI", "27", "¹⁄₂", "\n", "KU-ZU-NI", "18", "\n", "DA-SI-*118", "19", "\n", "I-DU-NE-SI", "5",
        "\n", "KU-RO", "130", "¹⁄₂"]


@pytest.mark.parametrize("token, cls", [
    ("KU-RO", "word"),
    ("JA-SA-SA-RA-[ME]", "word"),
    ("[U-NA-KA-NA]-SI", "word"),
    ("]-NE", "word"),
    ("QE-[", "word"),
    ("I-DA-[?]", "word"),
    ("PA-OLE+MI", "mixed"),
    ("TA-I-AROM", "mixed"),
    ("DI-𐄉-TI-DU", "mixed"),
    ("TE", "single_sign"),
    ("TWE", "single_sign"),
    ("AB77", "single_sign"),
    ("*301", "single_sign"),
    ("*21F", "logogram"),         # sex-marked: livestock beside *21M, *22F (ZA9, PH(?)31a)
    ("*22F", "logogram"),
    ("*402-VS", "logogram"),
    ("VIN", "logogram"),
    ("]VIN", "logogram"),
    ("OLE+U", "logogram"),
    ("VIR+*313a", "logogram"),
    ("OVISf[", "logogram"),
    ("AB22/CAPF", "logogram"),
    ("A319", "logogram"),
    ("A706 (≈ ¹⁄₆?)", "fraction"),
    ("23", "numeral"),
    ("1[", "numeral"),
    ("𐄑,𐄈", "numeral"),
    ("¹⁄₂", "fraction"),          # U+2044 is category Sm, yet the token is a fraction
    ("≈ ¹⁄₆", "fraction"),
    ("13/20", "fraction"),
    ("⅝", "fraction"),
    ("𐝓", "fraction"),
    ("double mina", "measure"),
    ("𐄁", "divider"),
    ("≈", "divider"),             # lone ≈ stands between words (ARGZg1, TELZb1)
    ("\n", "line_break"),
    ("—", "rule"),
    ("𐝫", "lacuna"),
    ("[?]", "lacuna"),
    ("[…]", "lacuna"),
    ("None", "lacuna"),
    ("|||||||||||||", "other"),
    (None, "lacuna"),
    (5, "numeral"),
])
def test_token_class(token, cls):
    assert p.token_class(token) == cls


@pytest.mark.data
@pytest.mark.skipif(not (LINEAR_A_DATA / "sign_values.json").exists(), reason="sign_values.json is not in this checkout")
@pytest.mark.parametrize("token, cls", [
    ("*28B", "single_sign"),      # resolved syllabogram JI
    ("*131B", "logogram"),
])
def test_lettered_sign_class_follows_sign_values(token, cls):
    assert p.token_class(token) == cls


@pytest.mark.parametrize("token, glyph", [
    (".3", "𐝎"),                  # HT91: A711 X
    ("?", "𐝁𐝁"),                  # KEWc2: A702 B twice
    ("L", "𐝈𐝫"),                  # KN49: A709 L, damaged
])
def test_glyph_reveals_raw_fraction(token, glyph):
    row = p.classify({"transliteratedWords": [token], "words": [glyph]})[0]
    assert row["class"] == "fraction" and row["raw_fraction"]
    assert p.quantity_value([row]) == (None, True)


def test_rendered_fraction_over_its_klasmatogram_keeps_its_value():
    rows = p.classify({"transliteratedWords": ["45", "¹⁄₂"], "words": ["𐄒𐄋", "𐝆"]})      # HT104
    assert rows[1]["class"] == "fraction" and not rows[1]["raw_fraction"]
    assert p.quantity_value(rows) == (Fraction(91, 2), False)


def test_classify_flags_damage_restoration_and_erasure():
    rows = p.classify({"transliteratedWords": ["JA-SA-SA-RA-[ME]", "KU-𐝫", "[[14]]"],
                       "words": ["x", "y", "z"]})
    assert [(r["restored"], r["damaged"], r["erased"]) for r in rows] == [
        (True, False, False), (False, True, False), (False, False, True)]


def test_glyph_damage_makes_a_quantity_approximate():
    rows = p.classify({"transliteratedWords": ["33"], "words": ["𐄒𐄉𐝫"]})     # HT102
    assert rows[0]["damaged"]
    assert p.quantity_value(rows) == (33, True)
    assert p.quantity_value(["33"]) == (33, False)


def test_erased_numeral_counts_but_is_approximate():
    assert p.quantity_value(["[[14]]"]) == (14, True)                          # HT127b


def test_lost_quantity_is_flagged():
    rows = p.classify({"transliteratedWords": ["*304+PA", "𐝫"], "words": ["a", "𐝫"]})   # HT100
    assert p.quantity_value(rows) == (None, True)
    assert p.quantity_value(["KA-U-DE-TA", "VIN"]) == (None, False)


def test_anchor_round_trip():
    assert p.anchor_form(HT13, "6-8") == "RE-ZA 5 ¹⁄₂"
    assert p.check_anchor(HT13, "6-8", "RE-ZA 5 ¹⁄₂") is None
    assert p.check_anchor(HT13, "0", "KA-U-DE-TA") is None


def test_anchor_reports_drift():
    assert p.check_anchor(HT13, "6-8", "RE-ZA 5") == "RE-ZA 5 ¹⁄₂"


@pytest.mark.parametrize("at, message", [
    ("8-6", "runs backwards"),
    ("40", "past the last token"),
    ("x", "invalid literal"),
    ("5", "line break"),
    ("5-8", "line break"),
])
def test_bad_anchor_is_reported_not_raised(at, message):
    assert message in p.check_anchor(HT13, at, "RE-ZA")


def test_anchor_drops_inner_line_breaks_and_empty_tokens():
    assert p.anchor_form(HT89, "3-6") == "23 JU+*317+QE 22"
    assert p.anchor_form(["A", "", "B"], "0-2") == "A B"


def test_line_spans():
    assert p.line_spans(HT89) == [(0, 3), (5, 6), (8, 9), (11, 12), (14, 15), (17, 18)]
    assert p.line_spans(["\n", "A", "\n", "\n"]) == [(1, 1)]


def test_ht89_entries_sum_to_ku_ro():
    lines = [HT89[a:b + 1] for a, b in p.line_spans(HT89)]
    entries = sum(p.quantity_value(line)[0] for line in lines[:-1])
    assert entries == p.quantity_value(lines[-1])[0] == 87


def test_ht13_residual_against_ku_ro():
    lines = [HT13[a:b + 1] for a, b in p.line_spans(HT13)]
    entries = sum(v for v, _ in map(p.quantity_value, lines[1:-1]))
    assert entries == 131
    assert p.quantity_value(lines[-1]) == (Fraction(261, 2), False)


def test_quantity_value_edge_cases():
    assert p.quantity_value(["1["]) == (1, True)
    assert p.quantity_value(["≈ ¹⁄₆"]) == (Fraction(1, 6), True)
    assert p.quantity_value(["13/20"]) == (Fraction(13, 20), False)
    assert p.quantity_value(["2", "𐝓"]) == (None, True)          # raw klasmatogram: no value
    assert p.quantity_value(["*809", "𐄑,𐄈"]) == (22, False)
    assert p.quantity_value(["KU", 5]) == (5, False)


def test_format_value():
    assert p.format_value(Fraction(261, 2)) == "130½"
    assert p.format_value(Fraction(3, 4)) == "¾"
    assert p.format_value(Fraction(-1, 2)) == "−½"
    assert p.format_value(Fraction(-3, 2)) == "−1½"
    assert p.format_value(Fraction(1, 16)) == "1/16"
    assert p.format_value(Fraction(17, 16)) == "1 1/16"
    assert p.format_value(None) == "—"


def test_is_aligned():
    assert p.is_aligned({"words": [1, 2], "transliteratedWords": [1, 2], "translatedWords": [1, 2]})
    assert not p.is_aligned({"words": [1], "transliteratedWords": [1, 2]})


@pytest.mark.data
@pytest.mark.skipif(not (LINEAR_A_DATA / "corpus.json").exists(), reason="corpus.json is not in this checkout")
def test_corpus_sweep_reaches_other_only_for_known_shapes():
    """Every live token gets a class; `other` only for the shapes no rule should claim."""
    corpus = json.loads((LINEAR_A_DATA / "corpus.json").read_text(encoding="utf-8"))
    other = {row["token"] for rec in corpus.values() for row in p.classify(rec) if row["class"] == "other"}
    assert other <= {"|||||||||||||", "𐁁"}
