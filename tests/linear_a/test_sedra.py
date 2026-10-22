"""Tests for lib/sedra.py: SEDRA III ASCII (Kiraz 1996) to Syriac script and to the database's Latin notation.

Words are real SEDRA III vocalised words (tblWords.txt): D'i;NoA 'judgment', RuOK 'spirit', AaLoHoA 'god',
A_NoWoA 'people', B'RoA 'son', D'a;oNoA 'judge'.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.core.sedra import to_latin, to_syriac


@pytest.mark.parametrize("sedra, latin", [
    ("AaLoHoA", "ʔalāhā"),          # zqapa ā, final alaph after a vowel is a mater
    ("B'RoA", "brā"),               # qushshaya is not written in Latin
    ("D'i;NoA", "dīnā"),            # hbasa + vowelless yodh = ī
    ("RuOK", "rūḥ"),                # esasa + vowelless waw = ū
    ("D'a;oNoA", "dayānā"),         # a yodh with its own vowel stays a consonant
    ("A_NoWoA", "nāšā"),            # linea occultans: the letter is silent
    ("ROaK", "rwaḥ"),               # a waw with its own vowel stays a consonant
    ("NeWeA", "neše"),              # rbasa is e; a final alaph after it is a mater
    ("D'e;N", "dēn"),               # rbasa + vowelless yodh = ē
    ("AaB,oA", "ʔabā"),             # rukkakha not written; gemination is never guessed
    ("EaB,D'oA", "ʕabdā"),          # ʿe is ʕ, alaph is ʔ (database notation)
])
def test_to_latin(sedra, latin):
    assert to_latin(sedra) == latin


def test_to_latin_keeps_a_word_joint_and_ignores_seyame():
    assert to_latin("B'*Na;-RG,eW;") == "bnay-rgešy"      # Boanerges, Mark 3:17


def test_to_syriac_writes_west_syriac_vowels_and_points():
    assert to_syriac("AaLoHoA") == unicodedata.normalize("NFC", "ܐܰܠܳܗܳܐ")
    # qushshaya U+0741, rukkakha U+0742, linea occultans as U+0331, seyame U+0308
    assert to_syriac("B'RoA") == unicodedata.normalize("NFC", "ܒ݁ܪܳܐ")
    assert to_syriac("AaB,oA") == unicodedata.normalize("NFC", "ܐܰܒ݂ܳܐ")
    assert to_syriac("A_NoWoA") == unicodedata.normalize("NFC", "ܐ̱ܢܳܫܳܐ")
    assert to_syriac("B'*Na") == unicodedata.normalize("NFC", "ܒ݁̈ܢܰ")


def test_to_syriac_unvocalised_root_and_lexeme():
    assert to_syriac("D;N") == "ܕܝܢ"
    assert to_latin("D;N") == "dyn"


@pytest.mark.parametrize("bad", ["AQ", "aB", "B'x", "B''A", "B o"])
def test_unknown_or_misplaced_code_is_an_error(bad):
    with pytest.raises(ValueError):
        to_latin(bad)
    with pytest.raises(ValueError):
        to_syriac(bad)
