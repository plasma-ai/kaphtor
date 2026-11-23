#!/usr/bin/env python3
"""Protocol D, phase D2: pointed Hebrew or Biblical Aramaic -> the renderer's phonemic segments.

`segments(word)` turns one Masoretic word into [(consonant | None, vowel | None), ...], the form
scripts/render_la.py takes. Conventions are those of controls/sources.md for the hand-made Hebrew controls:

- stops, not spirants (p, b, k, t); a doubled consonant is written once;
- a quiescent alef, a vowel letter (yod after i or e, waw as o or u, final he) writes no consonant;
- vocal shewa: i under an opening b, l or k, a under an opening w, e elsewhere; silent shewa leaves a bare consonant;
- the divine name is read yahweh; maqqef joins words into one group.

A simplification for control texts, offered as no philology: qamats is always a, and a shewa after a long vowel is
taken as silent.
"""
from __future__ import annotations

import re
import unicodedata

CONS = {"א": "ʾ", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "w", "ז": "z", "ח": "ḥ", "ט": "ṭ", "י": "y",
        "כ": "k", "ך": "k", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "ʿ", "פ": "p",
        "ף": "p", "צ": "ṣ", "ץ": "ṣ", "ק": "q", "ר": "r", "ש": "š", "ת": "t"}
VOWELS = {"ִ": "i", "ֵ": "e", "ֶ": "e", "ַ": "a", "ָ": "a", "ֹ": "o", "ֺ": "o",
          "ֻ": "u", "ׇ": "o", "ֱ": "e", "ֲ": "a", "ֳ": "o"}
SHEWA, DAGESH, SHIN, SIN, MAQQEF = "ְ", "ּ", "ׁ", "ׂ", "־"
YHWH = [("y", "a"), ("h", None), ("w", "e"), ("h", None)]


def strip_accents(text: str) -> str:
    """Drop cantillation and editorial marks; keep letters, vowel points, dagesh, the shin and sin dots, maqqef."""
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[֑-ֽֿ֯׀׃-׆‍͏]", "", text)
    return re.sub(r"[^ְ-ּ־ׇׁׂא-ת\s]", "", text)


def letters(word: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for ch in word:
        if ch in CONS:
            out.append((ch, ""))
        elif out:
            out[-1] = (out[-1][0], out[-1][1] + ch)
    return out


def segments(word: str) -> list[tuple[str | None, str | None]]:
    word = strip_accents(word)
    if MAQQEF in word:                                   # each part keeps its own opening shewa
        return [s for part in word.split(MAQQEF) if part for s in segments(part)]
    ls = letters(word)
    if "".join(c for c, _ in ls) == "יהוה":
        return list(YHWH)
    if "".join(c for c, _ in ls[-4:]) == "יהוה" and len(ls) > 4:        # a proclitic before the divine name
        return segments("".join(c + m for c, m in ls[:-4])) + list(YHWH)
    segs: list[tuple[str | None, str | None]] = []
    n = len(ls)
    prev_shewa = False
    for i, (ch, marks) in enumerate(ls):
        vowel = next((VOWELS[m] for m in marks if m in VOWELS), None)
        shewa, dagesh = SHEWA in marks, DAGESH in marks
        cons = "ś" if ch == "ש" and SIN in marks else CONS[ch]
        last, prior = i == n - 1, segs[-1] if segs else None
        prior_open = prior is not None and prior[1] is not None

        if ch == "ו" and vowel == "o" and prior is not None and prior[1] is None and prior[0] is not None \
                and not shewa and not prev_shewa_silent(ls, i):
            segs[-1] = (prior[0], "o")                                   # holam male
        elif ch == "ו" and dagesh and vowel is None and not shewa and (prior is None or prior[1] is None):
            if prior is None:
                segs.append((None, "u"))                                 # the conjunction u-
            else:
                segs[-1] = (prior[0], "u")                               # shuruq
        elif ch == "י" and vowel is None and not shewa and not dagesh and prior_open and prior[1] in ("i", "e"):
            pass                                                         # vowel letter
        elif ch == "א" and vowel is None and not shewa:
            pass                                                         # quiescent alef
        elif ch == "ה" and last and vowel is None and not dagesh and prior_open:
            pass                                                         # final vowel letter
        elif vowel is not None:
            if last and ch in "חעה" and vowel == "a" and prior_open and (ch != "ה" or dagesh):
                segs.append((None, "a"))                                 # furtive patah
                segs.append((cons, None))
            else:
                segs.append((cons, vowel))
        elif shewa and not last:
            vocal = i == 0 or prev_shewa or (dagesh and i > 0 and ch not in "בגדכפת") or \
                (i + 1 < n and CONS[ls[i + 1][0]] == CONS[ch])
            if vocal:
                v = "i" if i == 0 and ch in "בלכ" else "a" if i == 0 and ch == "ו" else "e"
                segs.append((cons, v))
                prev_shewa = False
                continue
            segs.append((cons, None))
            prev_shewa = True
            continue
        else:
            segs.append((cons, None))
        prev_shewa = False
    return segs


def prev_shewa_silent(ls: list[tuple[str, str]], i: int) -> bool:
    """A waw with holam after a consonant that carries shewa is a consonant: mitswot, not mitsot."""
    return i > 0 and SHEWA in ls[i - 1][1]


def words(verse: str) -> list[str]:
    # a bare pe or samekh is the Masoretic paragraph mark, no word
    return [w for w in strip_accents(verse).split() if any(c in CONS for c in w) and w not in ("פ", "ס")]


def surface(segs: list[tuple[str | None, str | None]]) -> str:
    return "".join((c or "") + (v or "") for c, v in segs)


if __name__ == "__main__":
    import sys
    for w in words(" ".join(sys.argv[1:])):
        s = segments(w)
        print(surface(s), s)
