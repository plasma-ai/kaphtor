"""SEDRA III ASCII (Kiraz 1996, SEDRA3.DOC "Transcription of Syriac") to Syriac script and to the Latin notation of
semitic_roots.json.

SEDRA writes a letter, then its marks: ' qushshaya, , rukkakha, _ linea occultans (the letter is silent), * seyame,
and at most one vowel (a ptaha, o zqapa, e rbasa, i hbasa, u esasa). `-` joins the two words of a compound.

Latin: alaph ʔ, ʿe ʕ; ptaha a, zqapa ā, rbasa e, hbasa i, esasa u; hbasa or rbasa + vowelless yodh = ī, ē; esasa +
vowelless waw = ū; a vowelless alaph after a vowel is a mater and is not written; a silent letter is not written;
qushshaya, rukkakha and seyame are not written. Gemination is not marked in SEDRA and is never guessed.
Syriac: Unicode letters with the West Syriac vowels (U+0730 ptaha, U+0733 zqapa, U+0736 rbasa, U+073A hbasa,
U+073D esasa), U+0741 qushshaya, U+0742 rukkakha, U+0331 linea occultans, U+0308 seyame; `-` becomes a space.
Any other character, a vowel with no letter, or a doubled mark is a ValueError.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

LETTERS = {  # SEDRA code: (Syriac letter, Latin)
    "A": ("ܐ", "ʔ"), "B": ("ܒ", "b"), "G": ("ܓ", "g"), "D": ("ܕ", "d"), "H": ("ܗ", "h"),
    "O": ("ܘ", "w"), "Z": ("ܙ", "z"), "K": ("ܚ", "ḥ"), "Y": ("ܛ", "ṭ"), ";": ("ܝ", "y"),
    "C": ("ܟ", "k"), "L": ("ܠ", "l"), "M": ("ܡ", "m"), "N": ("ܢ", "n"), "S": ("ܣ", "s"),
    "E": ("ܥ", "ʕ"), "I": ("ܦ", "p"), "/": ("ܨ", "ṣ"), "X": ("ܩ", "q"), "R": ("ܪ", "r"),
    "W": ("ܫ", "š"), "T": ("ܬ", "t"),
}
VOWELS = {"a": ("ܰ", "a"), "o": ("ܳ", "ā"), "e": ("ܶ", "e"), "i": ("ܺ", "i"), "u": ("ܽ", "u")}
MARKS = {"'": "݁", ",": "݂", "_": "̱", "*": "̈"}
LONG = {("i", ";"): "ī", ("e", ";"): "ē", ("u", "O"): "ū"}


@dataclass
class _Unit:
    letter: str
    vowel: str | None = None
    marks: list[str] = field(default_factory=list)   # SEDRA mark and vowel codes in the order written

    @property
    def silent(self) -> bool:
        return "_" in self.marks


def _parse(s: str) -> list[list[_Unit]]:
    """Words (split at `-`), each a list of letters with their marks."""
    words: list[list[_Unit]] = [[]]
    for ch in s:
        if ch in LETTERS:
            words[-1].append(_Unit(ch))
        elif ch == "-":
            if not words[-1]:
                raise ValueError(f"{s!r}: '-' with no word before it")
            words.append([])
        elif ch in VOWELS or ch in MARKS:
            if not words[-1]:
                raise ValueError(f"{s!r}: {ch!r} with no letter before it")
            u = words[-1][-1]
            if ch in VOWELS:
                if u.vowel:
                    raise ValueError(f"{s!r}: two vowels on {u.letter!r}")
                u.vowel = ch
            elif ch != "*" and (ch in u.marks or (ch in "'," and set("',") & set(u.marks))):
                raise ValueError(f"{s!r}: doubled mark {ch!r} on {u.letter!r}")
            u.marks.append(ch)
        else:
            raise ValueError(f"{s!r}: unknown SEDRA code {ch!r}")
    if not words[-1]:
        raise ValueError(f"{s!r}: empty word")
    return words


def to_syriac(s: str) -> str:
    out = []
    for word in _parse(s):
        out.append("".join(LETTERS[u.letter][0] + "".join(VOWELS[m][0] if m in VOWELS else MARKS[m] for m in u.marks)
                           for u in word))
    return unicodedata.normalize("NFC", " ".join(out))


def _latin_word(word: list[_Unit]) -> str:
    units = [u for u in word if not u.silent]
    out = []
    skip = False
    for k, u in enumerate(units):
        if skip:
            skip = False
            continue
        nxt = units[k + 1] if k + 1 < len(units) else None
        prev_vowel = units[k - 1].vowel if k else None
        if u.letter == "A" and u.vowel is None and prev_vowel:
            continue                                        # quiescent alaph after a vowel
        out.append(LETTERS[u.letter][1])
        if u.vowel:
            if nxt and nxt.vowel is None and (u.vowel, nxt.letter) in LONG:
                out.append(LONG[(u.vowel, nxt.letter)])
                skip = True
            else:
                out.append(VOWELS[u.vowel][1])
    return "".join(out)


def to_latin(s: str) -> str:
    return "-".join(_latin_word(w) for w in _parse(s))
