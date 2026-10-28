#!/usr/bin/env python3
"""Stage: build controls/controls.jsonl and controls/render_log.json.

Forward CV-syllabic rendering of the calibration control texts described in
controls/sources.md, implementing the published spelling algorithms:
ref-semitic-to-minoan-spelling.md (NWS + Egyptian contact §9.1),
ref-luwian-to-minoan-spelling.md, ref-hurrian-to-minoan-spelling.md.

Reads snapshot inputs only through common.paths.load_snapshot/load_data.
Vendored library modules are imported as top-level names after `from common
import paths` (paths.py inserts vendor/ onto sys.path).

Attribution: di Mino.
"""
from __future__ import annotations

import json
import random
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import paths  # noqa: E402
import skeleton  # noqa: E402
import phonetics  # noqa: E402

SCRIPT = "scripts/render_la.py"
ATTRIBUTION = "di Mino"
MAX_ALTERNATIVES = 8

# ---------------------------------------------------------------------------
# 0. Sign inventory helpers (vendor/skeleton.py is the only source of truth
#    for which CV signs exist; a rendering may only use signs in this table).
# ---------------------------------------------------------------------------

# Reverse index: (consonant, vowel) -> sign name, built from skeleton.py so a
# drift in the vendored inventory is picked up automatically.
_CV_TO_SIGN: dict[tuple[str | None, str], str] = {}
for _name, (_c, _v) in skeleton.SIGN_DECOMPOSITION.items():
    # Prefer the plain two-letter sign names (PA, KI, ...) over the special
    # ("*NNN") ones when both decode to the same (c, v); special signs are
    # looked up explicitly by name where the spelling guide calls for them.
    if _name.startswith("*"):
        continue
    _CV_TO_SIGN.setdefault((_c, _v), _name)

VOWEL_ONLY = {v: n for n, (c, v) in skeleton.SIGN_DECOMPOSITION.items() if c is None}

# Dedicated/resolved signs named explicitly in ref-semitic-to-minoan-spelling.md
SIGN_H_A = "*21F"      # he, /a/ only
SIGN_HET_A = "*314"    # het, /a/ only (also Luwian/Hurrian ḫa)
SIGN_AYIN_A = "*306"   # ayin, /a/ only
SIGN_TET_A = "*118"    # emphatic dental, /a/ only (also Hurrian fortis dental)
SIGN_PA3 = "PA3"       # /ba/
SIGN_ZU = "ZU"         # /ṯu/ (NWS) or /zu/ (Hurrian)
SIGN_JU = "JU"         # /lu/
SIGN_RA2 = "RA2"       # /la/
SIGN_JI = "*28B"       # /yi/
SIGN_DHA = "*305"      # /ḏa/
SIGN_AU = "AU"         # /aw/ VC
SIGN_IN = "*310"       # /in/ VC

GUTTURALS_NWS = {"ʾ", "ʿ", "h", "ḥ", "ḫ", "ġ"}
VOWELS5 = ("a", "e", "i", "o", "u")


def _series_signs(cons_for_vowel: dict[str, str]) -> dict[str, str]:
    """cons_for_vowel: {vowel: sign_name} — helper for building consonant tables."""
    return cons_for_vowel


# ---------------------------------------------------------------------------
# 1. Segment representation and the generic CV-rendering engine
# ---------------------------------------------------------------------------
# A word's phonemic form is a list of (consonant_or_None, vowel_or_None)
# tuples in left-to-right reading order:
#   (c, v)   -- full onset+nucleus syllable
#   (c, None)-- bare coda consonant, needs dead-vowel insertion (§6)
#   (None, v)-- bare vowel, no onset (word-initial vowel or hiatus)

Segment = tuple[str | None, str | None]


@dataclass
class Decision:
    word: str
    note: str


@dataclass
class WordRendering:
    canonical: list[str]
    alternatives: list[list[str]]
    notes: list[str] = field(default_factory=list)


class ArmRules:
    """Per-language consonant mapping + guttural/emphatic/sibilant policy."""

    name: str

    def map_cv(self, c: str | None, v: str) -> tuple[str, list[str], list[str]]:
        """Return (canonical_sign, alt_signs, notes) for a (consonant, vowel) pair."""
        raise NotImplementedError

    def bare_vowel(self, v: str) -> str:
        return VOWEL_ONLY[v]


class NWSRules(ArmRules):
    """Northwest Semitic (Ugaritic/Hebrew/Phoenician/Amorite/Amarna Canaanite),
    §§2-8 of ref-semitic-to-minoan-spelling.md."""

    name = "nws"

    def map_cv(self, c, v):
        notes: list[str] = []
        alts: list[str] = []
        if c is None:
            return self.bare_vowel(v), [], notes

        # §5 Guttural treatment
        if c in GUTTURALS_NWS:
            if c == "ʾ":
                notes.append("§5.3 aleph: no dedicated sign, represented by vowel alone")
                return self.bare_vowel(v), [], notes
            if v == "a":
                dedicated = {"h": SIGN_H_A, "ḥ": SIGN_HET_A, "ʿ": SIGN_AYIN_A}.get(c)
                if dedicated:
                    notes.append(f"§5.1 {c}+a: dedicated sign {dedicated} (canonical); drop is the alternative")
                    return dedicated, ["A"], notes
            notes.append(f"§5.2 guttural {c}+{v}: no dedicated sign for this vowel, drops")
            return self.bare_vowel(v), [], notes
        if c == "ġ":
            notes.append("ġ (voiced velar fricative): no Linear A sign documented; treated as a "
                         "guttural-class drop by analogy with §5.2 (not in the ref's explicit table)")
            return self.bare_vowel(v), [], notes

        # §4 Voicing
        if c == "b":
            if v == "a":
                notes.append("§4 /b/+a: PA3 dedicated voiced sign (conf. 0.90)")
                return SIGN_PA3, ["PA"], notes
            notes.append(f"§4 /b/+{v}: no PA3-series beyond /a/, folds into P-series (ambiguous with p)")
            return _CV_TO_SIGN[("p", v)], [], notes
        if c == "p":
            return _CV_TO_SIGN[("p", v)], [], notes
        if c == "d":
            return _CV_TO_SIGN[("d", v)], [], notes
        if c == "g":
            notes.append("§4 /g/: no G-series, neutralized into K-series")
            return _CV_TO_SIGN[("k", v)], [], notes
        if c == "k":
            return _CV_TO_SIGN[("k", v)], [], notes

        # §3 Emphatics
        if c == "ṭ":
            base = _CV_TO_SIGN[("t", v)]
            if v == "a":
                notes.append("§3 /ṭ/+a: T-series default (canonical); *118 dedicated alt")
                return base, [SIGN_TET_A], notes
            notes.append("§3 /ṭ/: T-series default (no vowel-restricted dedicated sign here)")
            return base, [], notes
        if c == "q":
            if v in ("a", "e"):
                return _CV_TO_SIGN[("q", v)], [], notes
            notes.append(f"§3 /q/+{v}: Q-series only attested for a/e; falls to K-series (velar merge)")
            return _CV_TO_SIGN[("k", v)], [], notes
        if c == "t":
            return _CV_TO_SIGN[("t", v)], [], notes

        # §2 Coronal/sibilant classes -- broad S/Z neutralization profile
        if c in ("š", "ś", "s"):
            alt = []
            if v in ("a", "e"):
                alt.append(_CV_TO_SIGN[("z", v)])
            return _CV_TO_SIGN[("s", v)], alt, notes
        if c == "z":
            alt = [_CV_TO_SIGN[("z", v)]] if v in ("a", "e") else []
            return _CV_TO_SIGN[("s", v)], alt, notes
        if c == "ṣ":
            notes.append("§3 /ṣ/: no dedicated sign; S-series canonical, Z-series alt where it exists")
            alt = [_CV_TO_SIGN[("z", v)]] if v in ("a", "e") else []
            return _CV_TO_SIGN[("s", v)], alt, notes
        if c == "ṯ":
            if v == "u":
                notes.append("§2/§7 /ṯ/+u: ZU dedicated innovation sign (canonical)")
                return SIGN_ZU, [_CV_TO_SIGN[("s", v)]], notes
            notes.append(f"§2 /ṯ/+{v}: no dedicated sign outside /u/; S-series canonical, T-series alt")
            return _CV_TO_SIGN[("s", v)], [_CV_TO_SIGN[("t", v)]], notes
        if c == "ḏ":
            if v == "a":
                notes.append("§2 /ḏ/+a: *305 dedicated sign (canonical)")
                return SIGN_DHA, [_CV_TO_SIGN[("d", v)]], notes
            notes.append(f"§2 /ḏ/+{v}: no dedicated sign; nearest is Z/S-series (phonetics.py ḏ-z=0.2)")
            return _CV_TO_SIGN[("s", v)], [_CV_TO_SIGN[("d", v)]], notes
        if c == "ẓ":
            notes.append("§2 /ẓ/: no dedicated sign; treated with the broad S/Z search class")
            alt = [_CV_TO_SIGN[("z", v)]] if v in ("a", "e") else [_CV_TO_SIGN[("t", v)]]
            return _CV_TO_SIGN[("s", v)], alt, notes

        # Liquids
        if c == "l":
            alt = []
            if v == "a":
                alt.append(SIGN_RA2)
            if v == "u":
                alt.append(SIGN_JU)
            return _CV_TO_SIGN[("r", v)], alt, notes
        if c == "r":
            return _CV_TO_SIGN[("r", v)], [], notes

        # Nasals/labials/semivowels
        if c == "m":
            return _CV_TO_SIGN[("m", v)], [], notes
        if c == "n":
            return _CV_TO_SIGN[("n", v)], [], notes
        if c == "w":
            if v in ("a", "e", "i"):
                return _CV_TO_SIGN[("w", v)], [], notes
            notes.append(f"/w/+{v}: no WO/WU sign; fell back to U vowel-only + dropped glide")
            return "U", [], notes
        if c == "y":
            if v in ("a", "e"):
                return _CV_TO_SIGN[("y", v)], [], notes
            if v == "i":
                notes.append("/y/+i: *28B dedicated sign")
                return SIGN_JI, [], notes
            notes.append(f"/y/+{v}: no J-series beyond a/e/i; fell back to bare vowel")
            return self.bare_vowel(v), [], notes

        raise KeyError(f"NWSRules: no mapping for consonant {c!r}")


class LuwianRules(ArmRules):
    """ref-luwian-to-minoan-spelling.md §§2,4,7,8 -- 3-vowel filter, no
    emphatics/pharyngeals, /z/ = affricate, fortis/lenis stop merger."""

    name = "luwian"

    def map_cv(self, c, v):
        notes: list[str] = []
        if v not in ("a", "i", "u"):
            notes.append(f"§1 negative diagnostic: /{v}/ is not a native Luwian vowel "
                         "(E/O excluded); rendered anyway as the nearest available sign for "
                         "this constructed test string")
        if c is None:
            return self.bare_vowel(v) if v in VOWEL_ONLY else "A", [], notes
        if c == "ḫ":
            if v == "a":
                notes.append("§7.1 /ḫa/: *314 preferred (PI-*314 attestation)")
                return SIGN_HET_A, [_CV_TO_SIGN.get(("k", v), "KA")], notes
            notes.append(f"§7.1 /ḫ/+{v}: no dedicated sign, K-series approximation")
            return _CV_TO_SIGN[("k", v)], [], notes
        if c in ("kw", "gw"):
            notes.append("§7.2 labiovelar: split into KU-W{v} (labialization preserved)")
            return "KU", [_CV_TO_SIGN.get(("k", v), "KA")], notes
        if c in ("b", "p"):
            if c == "b" and v == "a":
                return SIGN_PA3, [_CV_TO_SIGN[("p", v)]], notes
            return _CV_TO_SIGN[("p", v)], [], notes
        if c in ("d", "t"):
            base = "d" if c == "d" else "t"
            return _CV_TO_SIGN[(base, v)], [_CV_TO_SIGN[("t" if base == "d" else "d", v)]], notes
        if c in ("g", "k"):
            return _CV_TO_SIGN[("k", v)], [], notes
        if c == "s":
            return _CV_TO_SIGN[("s", v)], [], notes
        if c == "z":
            notes.append("§2/§8 Luwian /z/ = affricate [ts], ZA/ZI/ZU series (not NWS sibilant)")
            return {"a": "ZA", "e": "ZE", "u": SIGN_ZU}.get(v, "ZA"), [], notes
        if c in ("m", "n"):
            return _CV_TO_SIGN[(c, v)], [], notes
        if c == "l":
            alt = [SIGN_RA2] if v == "a" else ([SIGN_JU] if v == "u" else [])
            return _CV_TO_SIGN[("r", v)], alt, notes
        if c == "r":
            return _CV_TO_SIGN[("r", v)], [], notes
        if c == "w":
            return _CV_TO_SIGN.get(("w", v), "U"), [], notes
        if c == "y":
            return _CV_TO_SIGN.get(("y", v), SIGN_JI if v == "i" else "A"), [], notes
        raise KeyError(f"LuwianRules: no mapping for consonant {c!r}")


class HurrianRules(ArmRules):
    """ref-hurrian-to-minoan-spelling.md §§2,4,7,8 -- 5 real vowels (no dead-
    vowel stripping bias), 4-way labial merger, dental fluidity, /ḫ/ drops."""

    name = "hurrian"

    def map_cv(self, c, v):
        notes: list[str] = []
        if c is None:
            return self.bare_vowel(v), [], notes
        if c == "ḫ":
            notes.append("§7 Hurrian /ḫ/: drops by position; *314 is a flagged soft alternative")
            return self.bare_vowel(v), [SIGN_HET_A] if v == "a" else [], notes
        if c in ("p", "b", "f", "v"):
            notes.append("§2 4-way labial merger (/p b f v/) -> P-series")
            if c == "b" and v == "a":
                return SIGN_PA3, [_CV_TO_SIGN[("p", v)]], notes
            return _CV_TO_SIGN[("p", v)], [], notes
        if c in ("t", "d", "th", "dh"):
            base = "d" if c in ("d", "dh") else "t"
            notes.append("§2 dental fluidity (/t d θ ð/ merge by fortis/lenis default)")
            return _CV_TO_SIGN[(base, v)], [_CV_TO_SIGN[("t" if base == "d" else "d", v)]], notes
        if c in ("k", "g"):
            return _CV_TO_SIGN[("k", v)], [], notes
        if c in ("s", "š"):
            return _CV_TO_SIGN[("s", v)], [], notes
        if c == "z":
            notes.append("§8 Hurrian /z/ can reuse ZU (KU-ZU-NI attestation) or S-series")
            return {"u": SIGN_ZU}.get(v, _CV_TO_SIGN[("s", v)]), [], notes
        if c in ("m", "n"):
            return _CV_TO_SIGN[(c, v)], [], notes
        if c == "l":
            alt = [SIGN_RA2] if v == "a" else ([SIGN_JU] if v == "u" else [])
            return _CV_TO_SIGN[("r", v)], alt, notes
        if c == "r":
            return _CV_TO_SIGN[("r", v)], [], notes
        if c == "w":
            return _CV_TO_SIGN.get(("w", v), "U"), [], notes
        if c == "y":
            return _CV_TO_SIGN.get(("y", v), SIGN_JI if v == "i" else "A"), [], notes
        raise KeyError(f"HurrianRules: no mapping for consonant {c!r}")


class EgyptianRules(ArmRules):
    """ref-semitic-to-minoan-spelling.md §9.1 (contact-language table). NOTE:
    the task brief cites `ref-egyptian-rules-for-ch.md` §9.1 for this arm; that
    document (read in full) has no §9 at all -- it is a 7-section Cretan-
    Hieroglyphic acrophony memo, not a Linear A CV-rendering pipeline. The
    actual Egyptian-contact rendering rules live at §9.1 of
    ref-semitic-to-minoan-spelling.md (ḫ->KA, ꜣ->A/drops, w->WA/AU, fem
    -t->-TI, nisbe -y->-JA), which is what this class implements. Logged as a
    citation correction, not silently substituted."""

    name = "egyptian"

    def map_cv(self, c, v):
        notes: list[str] = []
        if c is None:
            return self.bare_vowel(v), [], notes
        if c in ("ḫ", "ḥ", "h"):
            notes.append("§9.1 Egyptian /ḫ/ (or ḥ/h approximated the same way): KA, no dedicated sign")
            return _CV_TO_SIGN[("k", v)], [], notes
        if c in ("ꜣ", "ʾ", "ʿ", "ꜥ"):
            notes.append("§9.1 Egyptian ꜣ/ʿ (aleph/ayin-class): drops, bare vowel remains")
            return self.bare_vowel(v), [], notes
        if c in ("w",):
            if v == "a":
                notes.append("§9.1 Egyptian initial/diphthong /w/: AU preferred (wsjr -> AU-SI-RE)")
                return SIGN_AU, [_CV_TO_SIGN.get(("w", v), "WA")], notes
            return _CV_TO_SIGN.get(("w", v), "U"), [], notes
        if c in ("j", "y"):
            if v in ("a", "e"):
                return _CV_TO_SIGN[("y", v)], [], notes
            if v == "i":
                return SIGN_JI, [], notes
            notes.append(f"Egyptian /j/+{v}: no J-series beyond a/e/i, bare vowel")
            return self.bare_vowel(v), [], notes
        if c in ("b", "p", "f"):
            if c == "b" and v == "a":
                return SIGN_PA3, [_CV_TO_SIGN[("p", v)]], notes
            notes.append("Egyptian /f/ folded into P-series (no dedicated spirant sign)" if c == "f" else "")
            return _CV_TO_SIGN[("p", v)], [], [n for n in notes if n]
        if c in ("t",):
            notes.append("§9.1 Egyptian feminine -t: -TI in the citation form; general /t/ uses T-series")
            return _CV_TO_SIGN[("t", v)], [], notes
        if c == "d":
            return _CV_TO_SIGN[("d", v)], [], notes
        if c in ("k", "g", "q"):
            return _CV_TO_SIGN[("k", v)], [], notes
        if c in ("s", "š", "z", "ṣ", "ś"):
            return _CV_TO_SIGN[("s", v)], [], notes
        if c in ("ṯ", "ḏ"):
            return _CV_TO_SIGN[("s", v)], [_CV_TO_SIGN[("t" if c == "ṯ" else "d", v)]], notes
        if c in ("m", "n"):
            return _CV_TO_SIGN[(c, v)], [], notes
        if c == "r":
            return _CV_TO_SIGN[("r", v)], [], notes
        if c == "l":
            alt = [SIGN_RA2] if v == "a" else []
            return _CV_TO_SIGN[("r", v)], alt, notes
        raise KeyError(f"EgyptianRules: no mapping for consonant {c!r}")


class EteocretanRules(NWSRules):
    """Alphabetic Greek-letter transliteration of an unknown language: the
    consonant/vowel *sequence* is given directly by the alphabet (no
    reconstruction needed, unlike NWS root-and-pattern skeletons). Applies the
    same script-level CV constraint (§6 dead-vowel insertion) since that is a
    property of the Linear A syllabary, not of any one source language.
    Reuses NWSRules' consonant-class table as the nearest documented fallback
    for phonemes Greek orthography also uses (t/d/k/g/p/b/s/z/l/r/m/n/w/y);
    aspirates (θ φ χ) are folded to their plain-stop counterpart (t/p/k) since
    Linear A has no aspirate series, logged per occurrence."""

    name = "unknown_eteocretan"

    def map_cv(self, c, v):
        if c in ("θ",):
            return super().map_cv("t", v)[0], [], ["Greek θ (aspirate) folded to plain /t/, no LA aspirate series"]
        if c in ("φ",):
            return super().map_cv("p", v)[0], [], ["Greek φ (aspirate) folded to plain /p/"]
        if c in ("χ",):
            return super().map_cv("k", v)[0], [], ["Greek χ (aspirate) folded to plain /k/"]
        if c in ("ϝ", "w"):
            return super().map_cv("w", v)
        return super().map_cv(c, v)


ARM_RULES = {
    "nws": NWSRules(),
    "luwian": LuwianRules(),
    "hurrian": HurrianRules(),
    "egyptian": EgyptianRules(),
    "unknown_eteocretan": EteocretanRules(),
}


# ---------------------------------------------------------------------------
# 2. Dead-vowel insertion (§6) and the word-level renderer
# ---------------------------------------------------------------------------

def _echo_vowels(segments: list[Segment]) -> list[str | None]:
    """For every position, the nearest preceding real vowel (progressive echo)."""
    out: list[str | None] = []
    last = None
    for c, v in segments:
        if v is not None:
            last = v
        out.append(last)
    return out


def _next_vowels(segments: list[Segment]) -> list[str | None]:
    out: list[str | None] = [None] * len(segments)
    nxt = None
    for i in range(len(segments) - 1, -1, -1):
        c, v = segments[i]
        if v is not None:
            nxt = v
        out[i] = nxt
    return out


GUTTURAL_DROP_SETS: dict[str, set[str]] = {
    "nws": GUTTURALS_NWS | {"ġ"},
    "unknown_eteocretan": set(),
    "egyptian": {"ꜣ", "ʾ", "ʿ", "ꜥ"},
    "luwian": set(),
    "hurrian": set(),
}


def render_word(word_surface: str, segments: list[Segment], arm: str,
                 log: list[dict]) -> WordRendering:
    rules = ARM_RULES[arm]
    prog = _echo_vowels(segments)
    nxt = _next_vowels(segments)
    canonical: list[str] = []
    # alt_pool[i] = list of alternative full-word variants differing only at
    # position i, capped combinatorially at MAX_ALTERNATIVES total.
    per_slot_alts: list[list[str]] = []
    notes: list[str] = []
    drop_set = GUTTURAL_DROP_SETS.get(arm, set())

    for i, (c, v) in enumerate(segments):
        slot_alts: list[str] = []
        sub_notes: list[str] = []
        if v is None and c in drop_set:
            # §5.2/9.1: a guttural with no vowel of its own (bare coda) drops
            # entirely -- it is not given a dead vowel and emits no sign, unlike
            # an ordinary consonant. A guttural that DOES carry an explicit
            # vowel is handled by the normal (c, v) full-syllable path above.
            notes.append(f"{word_surface}[{i}] §5.2 guttural /{c}/ in bare-coda position: "
                         "drops entirely, no sign (documented simplification: no cross-syllable "
                         "vowel contraction is modeled)")
            continue
        if v is not None:
            sign, alt_signs, sub_notes = rules.map_cv(c, v)
            slot_alts.extend(alt_signs)
        else:
            # Bare coda consonant: needs a dead vowel (§6.1).
            echo_v = prog[i]
            is_word_final = (i == len(segments) - 1)
            dv_notes = []
            if is_word_final:
                # §6.1: "Default /u/ in final position: CVC-final words often
                # get /u/ as the terminal dead vowel" -- word-final position
                # prefers default /u/ over the progressive echo.
                chosen_v = "u"
                dv_notes.append(f"§6.1 dead vowel for word-final coda /{c}/: default /u/ (canonical)")
            elif echo_v is not None:
                chosen_v = echo_v
                dv_notes.append(f"§6.1 dead vowel for coda /{c}/: progressive echo /{echo_v}/ (canonical)")
            else:
                chosen_v = nxt[i] or "u"
                dv_notes.append(f"§6.1 dead vowel for coda /{c}/: no preceding vowel, "
                                f"regressive echo/default /{chosen_v}/ (canonical)")
            sign, alt_signs, sub_notes = rules.map_cv(c, chosen_v)
            slot_alts.extend(alt_signs)
            # Alternative dead-vowel choices, each re-mapped through the consonant table.
            alt_vowels = []
            if is_word_final and echo_v is not None and echo_v != chosen_v:
                alt_vowels.append(echo_v)
            if echo_v is not None and nxt[i] is not None and nxt[i] not in (echo_v, chosen_v):
                alt_vowels.append(nxt[i])
            if "u" not in (echo_v, nxt[i], chosen_v):
                alt_vowels.append("u")
            for av in alt_vowels:
                try:
                    alt_sign, _, _ = rules.map_cv(c, av)
                    if alt_sign not in slot_alts and alt_sign != sign:
                        slot_alts.append(alt_sign)
                except KeyError:
                    pass
            notes.extend(dv_notes)
        notes.extend(f"{word_surface}[{i}] {n}" for n in sub_notes if n)
        canonical.append(sign)
        per_slot_alts.append(slot_alts[:MAX_ALTERNATIVES])

    # Combinatorial alternatives, one changed slot at a time, capped at 8 total.
    alternatives: list[list[str]] = []
    for i, alts in enumerate(per_slot_alts):
        for alt_sign in alts:
            if len(alternatives) >= MAX_ALTERNATIVES:
                break
            variant = list(canonical)
            variant[i] = alt_sign
            if variant != canonical and variant not in alternatives:
                alternatives.append(variant)
        if len(alternatives) >= MAX_ALTERNATIVES:
            break

    log.append({"word": word_surface, "arm": arm, "canonical": canonical,
                "alternatives": alternatives, "notes": notes})
    return WordRendering(canonical, alternatives, notes)


# ---------------------------------------------------------------------------
# 2b. Context-aware segment renderer (option B, PROTOCOL-B §4.4).
#     Same consonant tables and §6.1 dead-vowel rules as render_word, but
#     (a) the preceding nucleus may come from outside the rendered span
#     (``prev_vowel``: the stem's last vowel when rendering a suffix chain),
#     (b) the following nucleus may come from outside (``next_vowel``: the
#     stem's first vowel when rendering a prefix chain), (c) the span may be
#     word-medial (``word_final=False``: no default-/u/ terminal rule), and
#     (d) every emitted sign keeps the index of the segment it came from, so
#     a caller can slice affix signs from stem signs.
# ---------------------------------------------------------------------------

RULES_FOR_ARM = {"cs": "nws", "nws_floor": "nws", "nws": "nws", "luwian": "luwian",
                 "hurrian": "hurrian", "egyptian": "egyptian",
                 "unknown_eteocretan": "unknown_eteocretan"}

MAX_CHAIN_ALTERNATIVES = 32


def fuse_segments(segments: list[Segment]) -> list[Segment]:
    """(C, None) followed by (None, V) fuses to (C, V): a bare coda consonant
    followed by a vowel-initial morpheme shares one CV sign (malk + -u ->
    MA-RU-KU). A pure phonological convention, arm-independent."""
    out: list[Segment] = []
    for c, v in segments:
        if out and out[-1][1] is None and out[-1][0] is not None and c is None and v is not None:
            out[-1] = (out[-1][0], v)
        else:
            out.append((c, v))
    return out


def render_segments(segments: list[Segment], arm: str, *, prev_vowel: str | None = None,
                    next_vowel: str | None = None, word_final: bool = True
                    ) -> list[tuple[str, list[str], int]]:
    """Render a (possibly word-medial) span of segments.

    Returns one (canonical_sign, alternative_signs, segment_index) triple per
    emitted sign. Dead vowels follow §6.1 exactly as render_word does:
    word-final bare coda -> default /u/ (echo as alternative); medial bare
    coda -> progressive echo of the nearest preceding nucleus (which may be
    ``prev_vowel``), else regressive echo of the next nucleus (which may be
    ``next_vowel``), else /u/. Gutturals in bare-coda position drop for the
    arms whose drop set says so."""
    rules = ARM_RULES[RULES_FOR_ARM[arm]]
    drop_set = GUTTURAL_DROP_SETS.get(RULES_FOR_ARM[arm], set())
    prog: list[str | None] = []
    last = prev_vowel
    for c, v in segments:
        if v is not None:
            last = v
        prog.append(last)
    nxt: list[str | None] = [None] * len(segments)
    following = next_vowel
    for i in range(len(segments) - 1, -1, -1):
        c, v = segments[i]
        if v is not None:
            following = v
        nxt[i] = following
    out: list[tuple[str, list[str], int]] = []
    for i, (c, v) in enumerate(segments):
        if v is None and c in drop_set:
            continue
        if v is not None:
            sign, alt_signs, _ = rules.map_cv(c, v)
            out.append((sign, list(alt_signs), i))
            continue
        echo_v = prog[i - 1] if i > 0 else prev_vowel
        is_final = word_final and i == len(segments) - 1
        if is_final:
            chosen = "u"
        elif echo_v is not None:
            chosen = echo_v
        else:
            chosen = nxt[i] or "u"
        sign, alt_signs, _ = rules.map_cv(c, chosen)
        alts = list(alt_signs)
        alt_vowels = []
        if is_final and echo_v is not None and echo_v != chosen:
            alt_vowels.append(echo_v)
        if echo_v is not None and nxt[i] is not None and nxt[i] not in (echo_v, chosen):
            alt_vowels.append(nxt[i])
        if "u" not in (echo_v, nxt[i], chosen):
            alt_vowels.append("u")
        for av in alt_vowels:
            try:
                s2, _, _ = rules.map_cv(c, av)
            except KeyError:
                continue
            if s2 != sign and s2 not in alts:
                alts.append(s2)
        out.append((sign, alts, i))
    return out


def sign_variants(rendered: list[tuple[str, list[str], int]]) -> list[tuple[str, ...]]:
    """Every full-span variant (canonical first), one alternative per slot at
    a time and then pairwise, capped at MAX_CHAIN_ALTERNATIVES."""
    canonical = tuple(s for s, _, _ in rendered)
    variants = [canonical]
    slots = [(i, alts) for i, (_, alts, _) in enumerate(rendered) if alts]
    for i, alts in slots:
        for a in alts:
            v = list(canonical)
            v[i] = a
            t = tuple(v)
            if t not in variants:
                variants.append(t)
            if len(variants) >= MAX_CHAIN_ALTERNATIVES:
                return variants
    for x in range(len(slots)):
        for y in range(x + 1, len(slots)):
            for a in slots[x][1]:
                for b in slots[y][1]:
                    v = list(canonical)
                    v[slots[x][0]] = a
                    v[slots[y][0]] = b
                    t = tuple(v)
                    if t not in variants:
                        variants.append(t)
                    if len(variants) >= MAX_CHAIN_ALTERNATIVES:
                        return variants
    return variants


# ---------------------------------------------------------------------------
# 3. Phonemic-string helpers (Latin transliteration -> segments), used for
#    already-vocalized inputs (Amorite names, Eteocretan Greek letters,
#    default-filled Ugaritic/Egyptian skeletons).
# ---------------------------------------------------------------------------

def tokens_to_segments(tokens: list[str]) -> list[Segment]:
    """Group a flat phoneme-token stream (consonants/vowels already
    classified) into (c, v) segments: a consonant followed by a vowel forms
    one syllable; a consonant not followed by a vowel is a bare coda; a vowel
    with no preceding unconsumed consonant is a bare vowel."""
    segs: list[Segment] = []
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t in VOWELS5:
            segs.append((None, t))
            i += 1
            continue
        # consonant
        if i + 1 < n and tokens[i + 1] in VOWELS5:
            segs.append((t, tokens[i + 1]))
            i += 2
        else:
            segs.append((t, None))
            i += 1
    return segs


def latin_to_segments(s: str) -> list[Segment]:
    toks = phonetics._tokenize_phonemes(s)
    return tokens_to_segments(toks)


def dedupe_geminates(s: str) -> str:
    out = []
    for ch in s:
        if out and out[-1] == ch:
            continue
        out.append(ch)
    return "".join(out)


def default_vocalize(skeleton_str: str, overrides: dict[str, list[Segment]]) -> tuple[list[Segment], bool]:
    """NWS default vocalizer: known citation forms from `overrides`, else a
    CaCaCa filler between deduplicated (geminate-collapsed) root consonants.
    Returns (segments, used_override)."""
    if skeleton_str in overrides:
        return overrides[skeleton_str], True
    consonants = dedupe_geminates(skeleton_str)
    toks = phonetics._tokenize_phonemes(consonants)
    # A source "skeleton" occasionally already contains a written vowel letter
    # (Ugaritic alphabetic cuneiform spells word-initial aleph+vowel with one
    # of three dedicated aleph signs, transliterated as a bare a/i/u): treat
    # any vowel token as a bare-vowel segment rather than pairing it with the
    # /a/ filler (aleph + vowel and bare vowel resolve to the same LA sign
    # anyway, per NWSRules.map_cv's aleph handling).
    segs: list[Segment] = []
    for t in toks:
        if t in VOWELS5:
            segs.append((None, t))
        else:
            segs.append((t, "a"))
    return segs, False


# ---------------------------------------------------------------------------
# 4. Control-text data
# ---------------------------------------------------------------------------
# Every entry below cites its edition in controls/sources.md. Ugaritic word
# skeletons are the attested unvocalized consonantal spelling (KTU auto_parsing
# 0.2.7); NWS_OVERRIDES supplies established citation vocalizations for the
# small set of high-frequency words, everything else gets the documented
# default-/a/ filler (see sources.md "Vocalization convention").

NWS_OVERRIDES: dict[str, list[Segment]] = {
    "bʿl": [("b", "a"), ("ʿ", None), ("l", "u")],          # baʿlu
    "il": [("ʾ", "i"), ("l", "u")],                          # ʾilu
    "ym": [("y", "a"), ("m", "u")],                          # yamu (yawmu, simplified)
    "bn": [("b", "i"), ("n", "u")],                          # binu
    "mlk": [("m", "a"), ("l", None), ("k", "u")],            # malku
    "ugrt": [("ʾ", "u"), ("g", "a"), ("r", "i"), ("t", None)],  # ủgaritu (abs. gen.)
    "w": [("w", "a")],                                       # wa- "and"
    "l": [("l", "a")],                                       # la- "to/for"
    "k": [("k", "i")],                                       # ki "when/as"
    "b": [("b", "i")],                                       # bi- "in"
    "d": [("d", "a")],                                       # da/dū relative
    "u": [(None, "u")],                                       # ủ "or" (conj.)
    "hn": [("h", "a"), ("n", "a")],                           # hanna deictic
    "hnd": [("h", "a"), ("n", None), ("d", "a")],             # hannada "this"
}

# --- Ugaritic H1 windows (KTU, Copenhagen Ugaritic corpus auto_parsing/0.2.7) ---
UGARITIC_H1 = [
    dict(id="H1-KTU1.119-26-27", citation="KTU 1.119:26–27",
         words=["k", "gr", "ʿz", "ṯġrkm", "qrd", "ḥmytkm", "ʿnkm", "l", "bʿl"]),
    dict(id="H1-KTU1.119-30-32", citation="KTU 1.119:30–32",
         words=["bʿl", "nšqdš", "mḏr", "bʿl", "nmlu", "dkr", "bʿl", "nšqdš", "ḥtp"]),
    dict(id="H1-KTU1.40-8-9", citation="KTU 1.40:8–9",
         words=["l", "ṯkmn", "w", "šnm", "hn", "š", "w", "šqrb"]),
    dict(id="H1-KTU1.14-II-9-11", citation="KTU 1.14 II:9–11",
         words=["il", "trtḥṣ", "w", "tadm", "rḥṣ", "ydk", "amt", "uṣbʿtk", "ʿd"]),
    dict(id="H1-KTU1.14-II-23-25", citation="KTU 1.14 II:23–25",
         words=["šmm", "dbḥ", "l", "ṯr", "abk", "il", "šrd", "bʿl", "b"]),
]

# --- Ugaritic H3 (administrative/legal/correspondence, substituting for
#     KTU 4.x -- see sources.md for why) ---
UGARITIC_H3 = [
    dict(id="H3-KTU3.1-2-7", citation="KTU 3.1:2–7 (letter opening)",
         words=["ʿm", "mġy", "špš", "ql", "w", "mlkšḫ", "ʿmn"]),
    dict(id="H3-KTU3.2-1-5", citation="KTU 3.2:1–5 (legal deed)",
         words=["l", "ym", "hnd", "ʿmṯtmr", "bn", "nqmpʿ", "mlk", "ugrt", "ytn"]),
    dict(id="H3-KTU3.4-1-4", citation="KTU 3.4:1–4 (legal deed)",
         words=["l", "ym", "hnd", "iwrkl", "pdy", "agdn", "bn", "nwgn", "w"]),
    dict(id="H3-KTU3.9-1-6", citation="KTU 3.9:1–6 (mrzḥ association text)",
         words=["mrzḥ", "d", "qny", "šmmn", "b", "btw", "w", "št", "ibsn"]),
]

# --- Phoenician H3 (KAI 1 only; KAI 4/10/14/26 dropped -- see sources.md) ---
PHOENICIAN_H3 = [
    dict(id="H3-KAI1-curse", citation="KAI 1:2 (Ahiram sarcophagus curse clause)",
         words=["w", "ʾl", "ygl", "mškb", "z", "w", "ʾl", "yhtsp"]),
]

# --- Amarna Canaanite glosses H3 (contact_amarna_canaanite.jsonl) ---
# seeded windows built at runtime from the snapshot, see build_amarna_h3()

# --- Hebrew H1 (Sefaria Masoretic text; consonants pre-begadkephat, shewa
#     mobile reconstructed to its historical short vowel per project
#     convention; geminates written once, matching Linear A's own inability
#     to write gemination) ---
HEBREW_H1 = [
    dict(id="H1-Ps19.15", citation="Psalms 19:15 (Sefaria, Masoretic)",
         words=[("yihyū", [("y", "i"), ("h", None), ("y", "u")]),
                ("ləraṣon", [("l", "i"), ("r", "a"), ("ṣ", "o"), ("n", None)]),
                ("ʾimrepi", [("ʾ", "i"), ("m", None), ("r", "e"), ("p", "i")]),
                ("wahegyon", [("w", "a"), ("h", "e"), ("g", None), ("y", "o"), ("n", None)]),
                ("libi", [("l", "i"), ("b", "i")]),
                ("lipaneka", [("l", "i"), ("p", "a"), ("n", "e"), ("k", "a")]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("ṣuri", [("ṣ", "u"), ("r", "i")]),
                ("wagoʾali", [("w", "a"), ("g", "o"), ("ʾ", "a"), ("l", "i")])]),
    dict(id="H1-Ps15.1-2a", citation="Psalms 15:1–2 (partial; Sefaria, Masoretic)",
         words=[("mizmor", [("m", "i"), ("z", None), ("m", "o"), ("r", None)]),
                ("lidawid", [("l", "i"), ("d", "a"), ("w", "i"), ("d", None)]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("miyagur", [("m", "i"), ("y", "a"), ("g", "u"), ("r", None)]),
                ("biʾoheleka", [("b", "i"), ("ʾ", "o"), ("h", "e"), ("l", "e"), ("k", "a")]),
                ("miyiškon", [("m", "i"), ("y", "i"), ("š", None), ("k", "o"), ("n", None)]),
                ("bihar", [("b", "i"), ("h", "a"), ("r", None)]),
                ("qadšeka", [("q", "a"), ("d", None), ("š", "e"), ("k", "a")]),
                ("holek", [("h", "o"), ("l", "e"), ("k", None)])]),
    dict(id="H1-Ps33.1", citation="Psalms 33:1 (Sefaria, Masoretic)",
         words=[("ranenu", [("r", "a"), ("n", "e"), ("n", "u")]),
                ("ṣadiqim", [("ṣ", "a"), ("d", "i"), ("q", "i"), ("m", None)]),
                ("bayahweh", [("b", "a"), ("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("layšarim", [("l", "a"), ("y", None), ("š", "a"), ("r", "i"), ("m", None)]),
                ("naʾwa", [("n", "a"), ("ʾ", "a"), ("w", "a")]),
                ("tahila", [("t", "a"), ("h", "i"), ("l", "a")])]),
    dict(id="H1-Num6.24-25", citation="Numbers 6:24–25 (Sefaria, Masoretic)",
         words=[("yibareka", [("y", "i"), ("b", "a"), ("r", "e"), ("k", "a")]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("wayišmereka", [("w", "a"), ("y", "i"), ("š", None), ("m", "e"), ("r", "e"), ("k", "a")]),
                ("yaʾer", [("y", "a"), ("ʾ", "e"), ("r", None)]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("panayw", [("p", "a"), ("n", "a"), ("y", None), ("w", None)]),
                ("ʾeleka", [("ʾ", "e"), ("l", "e"), ("k", "a")]),
                ("wiḥuneka", [("w", "i"), ("ḥ", "u"), ("n", "e"), ("k", "a")])]),
    dict(id="H1-Num6.26", citation="Numbers 6:26 (Sefaria, Masoretic)",
         words=[("yiśa", [("y", "i"), ("ś", "a")]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("panayw", [("p", "a"), ("n", "a"), ("y", None), ("w", None)]),
                ("ʾeleka", [("ʾ", "e"), ("l", "e"), ("k", "a")]),
                ("wayaśem", [("w", "a"), ("y", "a"), ("ś", "e"), ("m", None)]),
                ("lika", [("l", "i"), ("k", "a")]),
                ("šalom", [("š", "a"), ("l", "o"), ("m", None)])]),
    dict(id="H1-Deut10.8", citation="Deuteronomy 10:8 (first clause; Sefaria, Masoretic)",
         words=[("baʿet", [("b", "a"), ("ʿ", "e"), ("t", None)]),
                ("hahiw", [("h", "a"), ("h", "i"), ("w", None)]),
                ("hibdil", [("h", "i"), ("b", None), ("d", "i"), ("l", None)]),
                ("yahweh", [("y", "a"), ("h", None), ("w", "e"), ("h", None)]),
                ("ʾetšebeṭ", [("ʾ", "e"), ("t", None), ("š", "e"), ("b", "e"), ("ṭ", None)]),
                ("halewi", [("h", "a"), ("l", "e"), ("w", "i")]),
                ("laśet", [("l", "a"), ("ś", "e"), ("t", None)]),
                ("ʾetʾaron", [("ʾ", "e"), ("t", None), ("ʾ", "a"), ("r", "o"), ("n", None)]),
                ("biritjahweh", [("b", "i"), ("r", "i"), ("t", None),
                                  ("y", "a"), ("h", None), ("w", "e"), ("h", None)])]),
]

# H1 windows whose damage mask mirrors IO Za 2's exact per-word pattern
# (data/ioza2.json tokens[0..7].damage_after_sign), applied to the first 8
# words of a 9-word (or exact 8-word) window.
IOZA2_MASK = [[], [], [3], [3, 4], [-1], [], [], [0]]
MASK_TARGETS = {"H1-Ps19.15", "H1-Num6.24-25", "H1-KTU1.14-II-23-25"}

# --- Amarna EA 74 (H1 petition register; unverified, see sources.md) ---
AMARNA_EA74 = dict(
    id="H1-EA74-prostration", citation="EA 74 opening (standard Rib-Hadda prostration "
    "incipit; Moran 1992:133ff, Rainey 2015 II; UNVERIFIED against the specific EA 74 "
    "tablet in this session -- see sources.md)",
    words=[("ana", [(None, "a"), ("n", "a")]),
           ("šarri", [("š", "a"), ("r", "i")]),
           ("belija", [("b", "e"), ("l", "i"), ("y", "a")]),
           ("ilanija", [("ʾ", "i"), ("l", "a"), ("n", "i"), ("y", "a")]),
           ("šamšija", [("š", "a"), ("m", None), ("š", "i"), ("y", "a")]),
           ("umma", [(None, "u"), ("m", "a")]),
           ("ribhadda", [("r", "i"), ("b", None), ("h", "a"), ("d", "a")]),
           ("aradka", [(None, "a"), ("r", "a"), ("d", None), ("k", "a")])],
)

# --- Amorite name lists (H3), seeded from contact_amorite_onomasticon.jsonl ---
AMORITE_SEED = 20260907
N_AMORITE_WINDOWS = 5

# --- Amarna Canaanite lexical glosses (H3), seeded from contact_amarna_canaanite.jsonl ---
AMARNA_H3_SEED = 20260907
N_AMARNA_H3_WINDOWS = 2

# --- Luwian H2 (constructed strings of independently attested word-forms;
#     Karatepe/Zarpiya/CTH 375 running text not independently verified this
#     session -- see sources.md "Luwian and Hurrian: method note") ---
LUWIAN_H2 = [
    dict(id="H2-LUW-massana-paradigm", citation="Constructed string: massana- 'god' case/"
         "i-mutation paradigm (Melchert 1993; Payne 2014, via ref-luwian-to-minoan-spelling.md §5.1,§4)",
         words=[("massanassis", [("m","a"),("s","a"),("n","a"),("s","a"),("s","i"),("s",None)]),
                ("massanassin", [("m","a"),("s","a"),("n","a"),("s","a"),("s","i"),("n",None)]),
                ("massanassi", [("m","a"),("s","a"),("n","a"),("s","a"),("s","i")]),
                ("massanassati", [("m","a"),("s","a"),("n","a"),("s","a"),("s","a"),("t","i")]),
                ("massanant", [("m","a"),("s","a"),("n","a"),("n","a"),("t",None)]),
                ("tarhus", [("t","a"),("r","u"),("ḫ","u"),("s",None)])]),
    dict(id="H2-LUW-onomastic-set", citation="Constructed string: theophoric/toponymic "
         "onomastic elements (Melchert 1993; Payne 2014, via ref-luwian-to-minoan-spelling.md §5.3)",
         words=[("tarhuntassa", [("t","a"),("r","u"),("ḫ","u"),("n","u"),("t","a"),("s","a")]),
                ("tarhuntamuwa", [("t","a"),("r","u"),("ḫ","u"),("n","u"),("t","a"),("m","u"),("w","a")]),
                ("tarhuntapiya", [("t","a"),("r","u"),("ḫ","u"),("n","u"),("t","a"),("p","i"),("y","a")]),
                ("muwaziti", [("m","u"),("w","a"),("z","i"),("t","i")]),
                ("puduhepawiya", [("p","u"),("d","u"),("ḫ","e"),("p","a"),("w","i"),("y","a")]),
                ("lukkawanni", [("l","u"),("k","a"),("w","a"),("n","i")]),
                ("parnassa", [("p","a"),("r","a"),("n","a"),("s","a")])]),
    dict(id="H2-LUW-massana-case-set", citation="Constructed string: massana- 's-stem/n-stem "
         "case forms (Melchert 1993, via ref-luwian-to-minoan-spelling.md §5.1)",
         words=[("massanis", [("m","a"),("s","a"),("n","i"),("s",None)]),
                ("massanin", [("m","a"),("s","a"),("n","i"),("n",None)]),
                ("massani", [("m","a"),("s","a"),("n","i")]),
                ("massana", [("m","a"),("s","a"),("n","a")]),
                ("massanatti", [("m","a"),("s","a"),("n","a"),("t","i")]),
                ("massaniya", [("m","a"),("s","a"),("n","i"),("y","a")])]),
    dict(id="H2-LUW-derivational-set", citation="Constructed string: -alli/-atar/-anza "
         "derivational forms (Melchert 1993, via ref-luwian-to-minoan-spelling.md §5.4)",
         words=[("hantawattalli", [("ḫ","a"),("n","a"),("t","a"),("w","a"),("t","a"),("t","a"),("l","i")]),
                ("hantawatar", [("ḫ","a"),("n","a"),("t","a"),("w","a"),("t","a"),("r",None)]),
                ("hantawattammi", [("ḫ","a"),("n","a"),("t","a"),("w","a"),("t","a"),("m","i")]),
                ("tarhunzanza", [("t","a"),("r","u"),("ḫ","u"),("n","u"),("z","a"),("n","a"),("z","a")]),
                ("warpan", [("w","a"),("r","a"),("p","a"),("n",None)]),
                ("warpi", [("w","a"),("r","a"),("p","i")])]),
    dict(id="H2-LUW-ustem-set", citation="Constructed string: u-stem declension + relative "
         "pronoun (Melchert 1993, via ref-luwian-to-minoan-spelling.md §5.5,§7.2)",
         words=[("tarhus", [("t","a"),("r","u"),("ḫ","u"),("s",None)]),
                ("tarhun", [("t","a"),("r","u"),("ḫ","u"),("n",None)]),
                ("tarhunzi", [("t","a"),("r","u"),("ḫ","u"),("n","i"),("z","i")]),
                ("tarhuinzi", [("t","a"),("r","u"),("ḫ","u"),(None,"i"),("n",None),("z","i")]),
                ("kwis", [("kw","i"),("s",None)]),
                ("massanis", [("m","a"),("s","a"),("n","i"),("s",None)])]),
    dict(id="H2-LUW-toponym-verb-set", citation="Constructed string: toponyms + denominative "
         "verb class (Melchert 1993, via ref-luwian-to-minoan-spelling.md §5.3,§5.6)",
         words=[("millawanda", [("m","i"),("l","a"),("w","a"),("n","a"),("d","a")]),
                ("parnassa", [("p","a"),("r","a"),("n","a"),("s","a")]),
                ("tarhuntassa", [("t","a"),("r","u"),("ḫ","u"),("n","u"),("t","a"),("s","a")]),
                ("massanassanz", [("m","a"),("s","a"),("n","a"),("s","a"),("n","a"),("z",None)]),
                ("azzuna", [(None,"a"),("z","u"),("n","a")]),
                ("wanatis", [("w","a"),("n","a"),("t","i"),("s",None)])]),
]

# --- Hurrian H2 (attested onomastic/theonym forms, several CONFIRMED as
#     already Linear-A-attested per ref-hurrian-to-minoan-spelling.md §5.2,
#     §11; continuous liturgical prose (Nikkal hymn/KUB 27.42) not
#     independently verified this session -- see sources.md) ---
HURRIAN_H2 = [
    dict(id="H2-HUR-confirmed-la-names", citation="Hurrian names/compounds CONFIRMED as "
         "Linear-A contact-layer attestations (ref-hurrian-to-minoan-spelling.md §11.1-11.4)",
         words=[("dakušenni", [("d","a"),("k","u"),("š","e"),("n","i")]),
                ("ašumitta", [(None,"a"),("š","u"),("m","i"),("t","a")]),
                ("pedikešši", [("p","e"),("d","i"),("k","e"),("š","i")]),
                ("tagišše", [("t","a"),("g","i"),("š","e")]),
                ("ewriteššub", [(None,"e"),("w","i"),("r","i"),("t","e"),("š","u"),("b",None)])]),
    dict(id="H2-HUR-theonym-roster", citation="Hurrian theonym roster (ref-hurrian-to-"
         "minoan-spelling.md §5.2 table, Laroche 1980)",
         words=[("teššub", [("t","e"),("š","u"),("b",None)]),
                ("šauška", [("š","a"),(None,"u"),("š","a"),("k","a")]),
                ("kušuḫ", [("k","u"),("š","u"),("ḫ",None)]),
                ("ḫepat", [("ḫ","e"),("p","a"),("t",None)]),
                ("šimige", [("š","i"),("m","i"),("g","e")]),
                ("šarruma", [("š","a"),("r","u"),("m","a")]),
                ("kumarbi", [("k","u"),("m","a"),("r","i"),("b","i")])]),
    dict(id="H2-HUR-onomastic-suffix-set", citation="Hurrian onomastic suffix/element set "
         "(ref-hurrian-to-minoan-spelling.md §5.2)",
         words=[("šenni", [("š","e"),("n","i")]),
                ("ewri", [(None,"e"),("w","i")]),
                ("enni", [(None,"e"),("n","i")]),
                ("šarri", [("š","a"),("r","i")]),
                ("mitta", [("m","i"),("t","a")]),
                ("kešši", [("k","e"),("š","i")]),
                ("tagi", [("t","a"),("g","i")]),
                ("ari", [(None,"a"),("r","i")])]),
    dict(id="H2-HUR-theonym-roster-2", citation="Hurrian theonym roster, second draw "
         "(ref-hurrian-to-minoan-spelling.md §5.2 table, §11.5)",
         words=[("teššub", [("t","e"),("š","u"),("b",None)]),
                ("šauška", [("š","a"),(None,"u"),("š","a"),("k","a")]),
                ("kušuḫ", [("k","u"),("š","u"),("ḫ",None)]),
                ("ḫepat", [("ḫ","e"),("p","a"),("t",None)]),
                ("šimige", [("š","i"),("m","i"),("g","e")]),
                ("šarruma", [("š","a"),("r","u"),("m","a")]),
                ("kumarbi", [("k","u"),("m","a"),("r","i"),("b","i")]),
                ("dakušenni", [("d","a"),("k","u"),("š","e"),("n","i")])]),
]


# ---------------------------------------------------------------------------
# 5. Egyptian sentence sampling (data/snapshot/egyptian_htp_dj_nswt.jsonl)
# ---------------------------------------------------------------------------

EGYPTIAN_SEED = 20260907
N_EGYPTIAN = 20

_EGY_STRIP_CHARS = set("(){}〈〉,.=[]⸢⸣⯑")


def egyptian_consonant_skeleton(word: str) -> str:
    """Strip editorial/grammatical marks, keep the bare consonant sequence.
    Parenthesized letters (scribal-optional, e.g. n(j)swt) are real consonants
    and are kept; only the bracket characters themselves are dropped."""
    s = unicodedata.normalize("NFC", word)
    out = []
    for ch in s:
        if ch in _EGY_STRIP_CHARS:
            continue
        if unicodedata.combining(ch):
            continue
        out.append(ch)
    s = "".join(out).lower()
    # drop anything that survived and isn't a letter this system recognizes
    keep = set("ꜣꜥḫḥšṯḏjwybpfmnrhzsqkgtdʾ")  # standard Egyptological consonant alphabet only
    return "".join(ch for ch in s if ch in keep)


def default_vocalize_egyptian(consonants: str) -> list[Segment]:
    """Egyptological pseudo-vocalization convention: default filler /e/
    between (geminate-collapsed) consonants (nfr -> "nefer")."""
    cons = dedupe_geminates(consonants)
    # j/w act as semi-consonants that may also stand as bare vowel carriers;
    # rendered here as ordinary consonants per §9.1 (mapped via EgyptianRules).
    return [(c, "e") for c in cons]


def build_egyptian_controls() -> list[dict]:
    sentences = paths.load_snapshot("egyptian_htp_dj_nswt.jsonl")
    cands = [s for s in sentences
             if 6 <= len(s["normalized"].split()) <= 9
             and not any(m in s["normalized"] for m in ("[", "⯑", "⸢"))]
    rng = random.Random(EGYPTIAN_SEED)
    chosen = rng.sample(cands, min(N_EGYPTIAN, len(cands)))
    out = []
    for i, s in enumerate(chosen):
        words_raw = s["normalized"].split()
        words = []
        for w in words_raw:
            cons = egyptian_consonant_skeleton(w)
            if not cons:
                continue
            words.append((w, default_vocalize_egyptian(cons)))
        out.append(dict(id=f"H2-EGY-{i+1:02d}-{s['id'].split(':')[-1]}",
                         citation=f"{s['source_corpus']}, sentence {s['id']} "
                                  f"(seed {EGYPTIAN_SEED}, drawn from egyptian_htp_dj_nswt.jsonl)",
                         words=words))
    return out


# ---------------------------------------------------------------------------
# 6. Eteocretan (Greek-alphabet transliteration -> CV), all non-fake, non-
#    placeholder inscriptions in data/snapshot/eteocretan_inscriptions.json
# ---------------------------------------------------------------------------

_GREEK_TO_LATIN = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "e",
    "θ": "t", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "ks",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "u",
    "φ": "p", "χ": "k", "ψ": "ps", "ω": "o", "ϝ": "w", "ϙ": "k", "ϡ": "s",
}


def greek_to_latin(s: str) -> str:
    out = []
    for ch in unicodedata.normalize("NFC", s.lower()):
        if unicodedata.combining(ch):
            continue
        if ch in _GREEK_TO_LATIN:
            out.append(_GREEK_TO_LATIN[ch])
        elif ch.isalpha():
            out.append(ch)  # already-Latin script (e.g. Praisos 5)
    return "".join(out)


def _clean_eteocretan_line(line: str) -> list[str]:
    """One transliterated line -> list of orthographic units, per the
    documented convention (sources.md): '|' is the only genuine word-divider
    in this corpus; a bare space is also treated as a divider (attested once,
    Praisos 3 line 5); '.', '..', '...', and combining underdots mark
    epigraphic damage/uncertainty and are deleted (concatenating the flanking
    letters) rather than treated as boundaries; 'vac.' (vacat) and leading/
    trailing '-' lacuna runs are stripped."""
    s = line.replace("vac.", " ").strip()
    s = s.strip("-").strip()
    s = s.replace("--", " ")
    units: list[str] = []
    for space_chunk in s.split(" "):
        space_chunk = space_chunk.strip("-").strip()
        if not space_chunk or space_chunk.lower() in ("v", "vac", "vacat"):
            continue  # stray vacat-abbreviation markers (e.g. Praisos 3's trailing " v")
        for piece in space_chunk.split("|"):
            piece = piece.replace(".", "").replace("-", "")
            piece = "".join(ch for ch in piece
                            if not unicodedata.combining(ch)
                            and unicodedata.category(ch) != "Lm")  # drop modifier letters (aspiration ʰ)
            piece = piece.strip()
            if piece:
                units.append(piece)
    return units


def build_eteocretan_controls() -> list[dict]:
    data = paths.load_snapshot("eteocretan_inscriptions.json")
    by_id = {i["id"]: i for i in data["inscriptions"]}
    windows: list[dict] = []

    def to_words(units: list[str], is_latin: bool) -> list[tuple[str, list[Segment]]]:
        out = []
        for u in units:
            latin = u if is_latin else greek_to_latin(u)
            segs = latin_to_segments(latin)
            out.append((u, segs))
        return out

    # Dreros 1: 5 lines, Greek alphabet, |-divided lines 1-2.
    d1 = by_id["ETEOCRETAN_DREROS_1"]["current_transliteration"]
    d1_units: list[str] = []
    for ln in d1:
        d1_units.extend(_clean_eteocretan_line(ln))
    windows.append(dict(id="H2-UNK-DREROS1-A",
                         citation="Dreros 1 (Gordon 1966; van Effenterre 1946; Guarducci IC), "
                                  "lines 1-2 (partial), | -divided units",
                         words=to_words(d1_units[:6], False)))
    windows.append(dict(id="H2-UNK-DREROS1-B",
                         citation="Dreros 1 (Gordon 1966; van Effenterre 1946; Guarducci IC), "
                                  "lines 2 (partial)-5",
                         words=to_words(d1_units[6:12], False)))

    # Dreros 2: 3 lines, 5 orthographic units total -- below the 6-9 window
    # minimum with no more attested text; included anyway per "every
    # inscription except the proven fake" (see sources.md).
    d2 = by_id["ETEOCRETAN_DREROS_2"]["current_transliteration"]
    d2_units: list[str] = []
    for ln in d2:
        d2_units.extend(_clean_eteocretan_line(ln))
    windows.append(dict(id="H2-UNK-DREROS2",
                         citation="Dreros 2 (Gordon 1966; van Effenterre BCH 70, 1946), "
                                  "full text (5 units; below 6-word minimum, no further text attested)",
                         words=to_words(d2_units, False)))

    # Praisos 2: 5 lines, no dividers, no more text -- below minimum.
    p2 = by_id["ETEOCRETAN_PRAISOS_2"]["current_transliteration"]
    p2_units: list[str] = []
    for ln in p2:
        p2_units.extend(_clean_eteocretan_line(ln))
    windows.append(dict(id="H2-UNK-PRAISOS2",
                         citation="Praisos 2 (Gordon 1966; Duhoux 1982:68-75; Guarducci IC III:139-140), "
                                  "full text (5 units; below 6-word minimum, no further text attested)",
                         words=to_words(p2_units, False)))

    # Praisos 3: 11 lines, one internal space-divider -> 12 units -> 2 clean windows.
    p3 = by_id["ETEOCRETAN_PRAISOS_3"]["current_transliteration"]
    p3_units: list[str] = []
    for ln in p3:
        p3_units.extend(_clean_eteocretan_line(ln))
    windows.append(dict(id="H2-UNK-PRAISOS3-A",
                         citation="Praisos 3 (Gordon 1966; Duhoux 1982:75-79; Guarducci IC III:140-141), "
                                  "lines 1-5",
                         words=to_words(p3_units[:6], False)))
    windows.append(dict(id="H2-UNK-PRAISOS3-B",
                         citation="Praisos 3 (Gordon 1966; Duhoux 1982:75-79; Guarducci IC III:140-141), "
                                  "lines 6-11",
                         words=to_words(p3_units[6:12], False)))

    # Praisos 5: 4 lines, already Latin-letter transliteration (Ray Brown
    # 1984 convention with '|' dividers and underdot uncertainty marks).
    p5 = by_id["ETEOCRETAN_PRAISOS_5"]["current_transliteration"]
    p5_units: list[str] = []
    for ln in p5:
        p5_units.extend(_clean_eteocretan_line(ln))
    windows.append(dict(id="H2-UNK-PRAISOS5",
                         citation="Praisos 5 (Guarducci 1942 IC III:141; Duhoux 1982:82-85; "
                                  "Ray Brown 1984:231-232), full text",
                         words=to_words(p5_units, True)))
    return windows


# ---------------------------------------------------------------------------
# 7. Amorite name-list / Amarna Canaanite glossary windows (H3), and Linear B
#    negative controls (already CV, direct sign mapping)
# ---------------------------------------------------------------------------

_ALLOWED_TRANSLIT_CHARS = set("aeiouʾʿhḥḫġbptdḏṭṯzẓsṣśšlrmnqkgwy")


def _clean_transliteration(s: str) -> bool:
    """True if every character of s is a phoneme this pipeline maps (a
    whitelist, not a blacklist: contact-lexicon jsonl entries carry a long
    tail of placeholder/encoding artifacts -- 'x' unknown-element markers,
    '[]' unfilled brackets, '^' metathesis flags, '\\'-joined variant
    encodings, stray digits/capitals -- that are not phonemic content).

    Refreeze 2026-09-08: plain "s" added (the first freeze omitted it and so
    excluded every Amorite name and Amarna gloss containing /s/ from the H3
    controls, 2,400 of 7,121 personal names; CLAIMS-REPORT.md, SPECS.md
    caveat 4) and the string is NFC-normalized first, so a decomposed
    diacritic no longer rejects an otherwise clean form."""
    s = unicodedata.normalize("NFC", s)
    return bool(s) and all(ch in _ALLOWED_TRANSLIT_CHARS for ch in s)


def _holdout_records(entries: list[dict]) -> list[dict]:
    """Entry ids and normalized forms of the windowed comparanda, so
    lexicon_arms can withhold them from every arm (the first freeze scored
    the H3 Amorite windows against a database that contained those very
    names; METHOD_REVIEW.md, CODE_REVIEW.md disposition)."""
    return [{"id": e.get("id", ""), "normalized": e["normalized"]} for e in entries]


def build_amorite_h3() -> list[dict]:
    entries = paths.load_snapshot("contact_amorite_onomasticon.jsonl")
    names = [e for e in entries if e.get("pos") == "personal_name"
             and _clean_transliteration(e["normalized"])]
    rng = random.Random(AMORITE_SEED)
    starts = sorted(rng.sample(range(0, len(names) - 8), N_AMORITE_WINDOWS))
    out = []
    for i, start in enumerate(starts):
        window = names[start:start + 8]
        words = [(n["normalized"], latin_to_segments(n["normalized"])) for n in window]
        out.append(dict(id=f"H3-AMORITE-{i+1}",
                         citation=f"Amorite personal names, contact_amorite_onomasticon.jsonl "
                                  f"[{start}:{start+8}] (Gelb 1980 AS 21; seed {AMORITE_SEED})",
                         words=words,
                         holdout={"contact_amorite_onomasticon.jsonl": _holdout_records(window)}))
    return out


def build_amarna_h3() -> list[dict]:
    all_entries = paths.load_snapshot("contact_amarna_canaanite.jsonl")
    entries = [e for e in all_entries if _clean_transliteration(e["normalized"])]
    rng = random.Random(AMARNA_H3_SEED)
    starts = sorted(rng.sample(range(0, len(entries) - 8), N_AMARNA_H3_WINDOWS))
    out = []
    for i, start in enumerate(starts):
        window = entries[start:start + 8]
        words = [(e["normalized"], latin_to_segments(e["normalized"])) for e in window]
        out.append(dict(id=f"H3-AMARNAGLOSS-{i+1}",
                         citation=f"Canaanite glosses in Amarna letters, "
                                  f"contact_amarna_canaanite.jsonl [{start}:{start+8}] "
                                  f"(ORACC aemw/amarna qca glossary; seed {AMARNA_H3_SEED})",
                         words=words,
                         holdout={"contact_amarna_canaanite.jsonl": _holdout_records(window)}))
    return out


def _lb_syllable_to_la_sign(syl: str, notes: list[str]) -> str | None:
    """Map one Linear B syllable to its Linear A sign name, using the same
    subscript-variant fallback already implemented by skeleton._lookup_sign
    (KI2 -> KI). Returns None (dropped, B-only) if no LA sign exists."""
    raw = syl.strip("[]•' ’′")
    if not raw or raw == "-":
        return None
    upper = raw.upper().translate(skeleton._SUBSCRIPT_MAP)
    if upper in skeleton.SIGN_DECOMPOSITION:
        return upper
    import re as _re
    base = _re.sub(r"\d+$", "", upper)
    if base and base in skeleton.SIGN_DECOMPOSITION:
        notes.append(f"LB {raw} -> LA {base} via subscript-variant fallback (skeleton._lookup_sign convention)")
        return base
    notes.append(f"LB syllable {raw!r}: no Linear A sign in this inventory, dropped (B-only)")
    return None


def lb_word_to_la_signs(token: str, notes: list[str]) -> list[str]:
    signs = []
    for syl in token.split("-"):
        sign = _lb_syllable_to_la_sign(syl, notes)
        if sign:
            signs.append(sign)
    return signs


def build_linear_b_negatives() -> list[dict]:
    out = []
    lb = paths.load_snapshot("lb_subset.json")
    docs = lb["documents"]

    # PY Tn 316: every syllabic token, in line order, windows of 7.
    tn = docs["PY Tn 316"][0]["record"]
    tn_tokens = []
    for line in tn["lines"]:
        for tok in line["tokens"]:
            if tok["token_type"] == "syllabic":
                tn_tokens.append(tok["normalized"])
    for wi in range(0, len(tn_tokens), 7):
        chunk = tn_tokens[wi:wi + 7]
        if len(chunk) < 6:
            continue
        out.append(dict(id=f"NEG-PYTn316-{wi//7+1}",
                         citation=f"PY Tn 316 (DAMOS PY Tn(-) 316), tokens {wi}-{wi+len(chunk)-1}",
                         words=[(t, None) for t in chunk], lb_direct=True))

    # KN Fh 339-359 series, tablet order, windows of 8/8/8/8/6.
    order = ["KN Fh 339", "KN Fh 340", "KN Fh 341", "KN Fh 342", "KN Fh 343",
             "KN Fh 344", "KN Fh 345", "KN Fh 347", "KN Fh 348", "KN Fh 349",
             "KN Fh 350", "KN Fh 351", "KN Fh 352", "KN Fh 353", "KN Fh 355",
             "KN Fh 356", "KN Fh 357", "KN Fh 358", "KN Fh 359"]
    fh_tokens = []
    for doc_id in order:
        rec = docs[doc_id][0]["record"]
        for line in rec["lines"]:
            for tok in line["tokens"]:
                if tok["token_type"] == "syllabic":
                    fh_tokens.append((doc_id, tok["normalized"]))
    sizes = [8, 8, 8, 8, len(fh_tokens) - 32]
    idx = 0
    for wi, size in enumerate(sizes):
        if size <= 0:
            continue
        chunk = fh_tokens[idx:idx + size]
        idx += size
        docs_covered = sorted(set(d for d, _ in chunk), key=order.index)
        out.append(dict(id=f"NEG-KNFh-{wi+1}",
                         citation=f"KN Fh 339-359 series, {docs_covered[0]}-{docs_covered[-1]}",
                         words=[(t, None) for _, t in chunk], lb_direct=True))

    # KN Fp 1: hand-transcribed from Ventris & Chadwick 1956 (2nd ed. text
    # reproduced in sources/mycenaean-lexica/Ventris-Chadwick-1956-...md,
    # lines 11431-11438), not present in the frozen snapshot.
    fp1_lines = [
        ["de-u-ki-jo-jo", "me-no"],
        ["di-ka-ta-jo", "di-we"],
        ["da-da-re-jo-de"],
        ["pa-de"],
        ["pa-si-te-o-i"],
        ["qe-ra-si-ja"],
        ["a-mi-ni-so", "pa-si-te-o-i"],
        ["e-ri-nu"],
        ["*47-da-de"],
        ["a-ne-mo", "i-je-re-ja"],
        ["to-so"],
    ]
    fp1_tokens = [t for line in fp1_lines for t in line]
    out.append(dict(id="NEG-KNFp1-A", citation="KN 200=Fp1, lines 1-5 (Ventris & Chadwick "
                     "1956, Documents in Mycenaean Greek, p. 305)",
                     words=[(t, None) for t in fp1_tokens[:7]], lb_direct=True))
    out.append(dict(id="NEG-KNFp1-B", citation="KN 200=Fp1, lines 6-12 (Ventris & Chadwick "
                     "1956, Documents in Mycenaean Greek, pp. 305-306)",
                     words=[(t, None) for t in fp1_tokens[7:]], lb_direct=True))
    return out


# ---------------------------------------------------------------------------
# 8. Assembly: entry -> controls.jsonl record
# ---------------------------------------------------------------------------

def apply_damage_mask(control_id: str, per_word_signs: list[list[str]],
                       notes: list[str]) -> list[dict]:
    if control_id not in MASK_TARGETS:
        return []
    mask_out = []
    for wi, damage in enumerate(IOZA2_MASK):
        if wi >= len(per_word_signs) or not damage:
            continue
        n_signs = len(per_word_signs[wi])
        clamped = []
        for d in damage:
            if d == -1:
                clamped.append(-1)
            elif d >= n_signs:
                clamped.append(n_signs - 1)
                notes.append(f"damage_mask word {wi}: index {d} clamped to {n_signs - 1} "
                             f"(canonical rendering has only {n_signs} signs)")
            else:
                clamped.append(d)
        mask_out.append({"word_index": wi, "damage_after_sign": clamped})
    return mask_out


def process_entry(entry: dict, arm: str, cls: str, language: str,
                   overrides: dict[str, list[Segment]] | None,
                   render_log: list[dict]) -> dict:
    words_in = entry["words"]
    surfaces: list[str] = []
    canon_per_word: list[list[str]] = []
    alt_per_word: list[list[list[str]]] = []
    phonemic_per_word: list[list[list[str | None]]] = []
    entry_notes: list[str] = []
    lb_direct = entry.get("lb_direct", False)

    for w in words_in:
        if lb_direct:
            surface, _ = w
            lb_notes: list[str] = []
            signs = lb_word_to_la_signs(surface, lb_notes)
            surfaces.append(surface)
            canon_per_word.append(signs)
            alt_per_word.append([])
            phonemic_per_word.append([])
            entry_notes.extend(lb_notes)
            render_log.append({"word": surface, "arm": "linear_b_direct",
                               "canonical": signs, "alternatives": [], "notes": lb_notes})
            continue
        if isinstance(w, str):
            segs, used_override = default_vocalize(w, overrides or {})
            surface = w
            entry_notes.append(f"{w}: {'override citation form' if used_override else 'default /a/-filler vocalization'}")
        else:
            surface, segs = w
        rendering = render_word(surface, segs, arm, render_log)
        surfaces.append(surface)
        canon_per_word.append(rendering.canonical)
        alt_per_word.append(rendering.alternatives)
        phonemic_per_word.append([[c, v] for c, v in segs])

    damage_mask = apply_damage_mask(entry["id"], canon_per_word, entry_notes)

    return {
        "id": entry["id"], "class": cls, "language": language,
        "citation": entry["citation"], "translit": " ".join(surfaces),
        "phonemic": phonemic_per_word,
        "la_canonical": ["-".join(s) for s in canon_per_word],
        "la_alternatives": [["-".join(v) for v in alts] for alts in alt_per_word],
        "n_words": len(surfaces), "damage_mask": damage_mask,
        "render_log_ref": entry["id"],
        "notes": entry_notes,
    }


# ---------------------------------------------------------------------------
# 9. Worked-example reproduction check (ref-semitic-to-minoan-spelling.md
#    §10, ref-hurrian-to-minoan-spelling.md §11, ref-luwian... §9)
# ---------------------------------------------------------------------------

WORKED_EXAMPLES = [
    dict(name="kohen->KI-NI (§10.1)", arm="nws",
         segments=[("k", "o"), ("h", None), (None, "e"), ("n", None)], expect="KI-NI"),
    dict(name="dabh->DA-PA3 (§10.2)", arm="nws",
         segments=[("d", "a"), ("b", None), ("ḥ", None)], expect="DA-PA3"),
    dict(name="wsjr->AU-SI-RE (§10.3, Egyptian contact via §9.1; known Osiris "
              "vocalization /wasire/ supplied, not derived from the bare skeleton -- see notes)",
         arm="egyptian",
         segments=[("w", "a"), ("s", "i"), ("r", "e")], expect="AU-SI-RE"),
    dict(name="Dakusenni->DA-KU-SE-NE (hurrian §11.1)", arm="hurrian",
         segments=[("d", "a"), ("k", "u"), ("š", "e"), ("n", "e")], expect="DA-KU-SE-NE"),
    dict(name="massanassis->MA-SA-NA-SA-SI-SU (luwian §9 worked example)", arm="luwian",
         segments=[("m", "a"), ("s", "a"), ("n", "a"), ("s", "a"), ("s", "i"), ("s", None)],
         expect="MA-SA-NA-SA-SI-SU"),
]


def check_worked_examples() -> list[dict]:
    results = []
    for ex in WORKED_EXAMPLES:
        log: list[dict] = []
        rendering = render_word(ex["name"], ex["segments"], ex["arm"], log)
        got = "-".join(rendering.canonical)
        results.append({"name": ex["name"], "expected": ex["expect"], "got": got,
                        "reproduced": got == ex["expect"]})
    return results


# ---------------------------------------------------------------------------
# 10. main
# ---------------------------------------------------------------------------

USED_SNAPSHOTS = ["egyptian_htp_dj_nswt.jsonl", "eteocretan_inscriptions.json",
                  "lb_subset.json", "contact_amorite_onomasticon.jsonl",
                  "contact_amarna_canaanite.jsonl"]


def main() -> int:
    render_log: list[dict] = []
    controls: list[dict] = []

    def add_all(entries, arm, cls, language, overrides=None):
        for e in entries:
            controls.append(process_entry(e, arm, cls, language, overrides, render_log))

    add_all(UGARITIC_H1, "nws", "H1_semitic_prayer", "ugaritic", NWS_OVERRIDES)
    add_all(HEBREW_H1, "nws", "H1_semitic_prayer", "hebrew")
    add_all([AMARNA_EA74], "nws", "H1_semitic_prayer", "akkadian_peripheral")

    add_all(UGARITIC_H3, "nws", "H3_semitic_nonprayer", "ugaritic", NWS_OVERRIDES)
    add_all(PHOENICIAN_H3, "nws", "H3_semitic_nonprayer", "phoenician", NWS_OVERRIDES)
    holdout: dict[str, list[dict]] = {}
    for e in build_amorite_h3() + build_amarna_h3():
        add_all([e], "nws", "H3_semitic_nonprayer", "amorite" if e["id"].startswith("H3-AMORITE") else "canaanite")
        for fname, recs in e["holdout"].items():
            holdout.setdefault(fname, []).extend(dict(r, control=e["id"]) for r in recs)

    add_all(LUWIAN_H2, "luwian", "H2_luwian", "luwian")
    add_all(HURRIAN_H2, "hurrian", "H2_hurrian", "hurrian")
    add_all(build_egyptian_controls(), "egyptian", "H2_egyptian", "egyptian")
    add_all(build_eteocretan_controls(), "unknown_eteocretan", "H2_unknown_eteocretan", "eteocretan")

    for e in build_linear_b_negatives():
        controls.append(process_entry(e, "nws", "NEG_linear_b", "mycenaean_greek", None, render_log))

    now = datetime.now(timezone.utc).isoformat()
    inputs_hashes = {}
    for name in USED_SNAPSHOTS:
        p = paths.verified_path(f"data/snapshot/{name}", strict=False)
        inputs_hashes[name] = paths.sha256(p)

    meta = {"built_by": SCRIPT, "built_at": now, "inputs": inputs_hashes,
            "attribution": ATTRIBUTION}

    controls_path = paths.CONTROLS / "controls.jsonl"
    with open(controls_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for c in controls:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    holdout_path = paths.CONTROLS / "holdout_entries.json"
    holdout_path.write_text(json.dumps({
        "_meta": dict(meta, note="Comparanda withheld from every lexical arm because they are the "
                                 "H3 control windows themselves (lexicon_arms._contact_jsonl_entries)."),
        "holdout": holdout}, ensure_ascii=False, indent=1), encoding="utf-8")

    worked = check_worked_examples()
    class_counts: dict[str, int] = {}
    for c in controls:
        class_counts[c["class"]] = class_counts.get(c["class"], 0) + 1

    render_log_doc = {
        "_meta": meta,
        "per_word_decisions": render_log,
        "worked_example_reproduction": worked,
        "class_counts": class_counts,
        "n_controls": len(controls),
        "notes": [
            "ref-egyptian-rules-for-ch.md has no §9.1 (it is a 7-section Cretan-"
            "Hieroglyphic acrophony memo, not a Linear A CV-rendering pipeline); "
            "Egyptian rendering uses §9.1 of ref-semitic-to-minoan-spelling.md instead. "
            "See controls/sources.md 'Citation correction'.",
            "Luwian and Hurrian H2 controls are constructed strings of independently "
            "attested word-forms (Melchert 1993, Payne 2014, Wegner 2007, Campbell 2007, "
            "Laroche 1980), not continuous inscriptional prose from Karatepe/Zarpiya/"
            "CTH 375/the Nikkal hymn/KUB 27.42 -- see controls/sources.md method note.",
            "NWS consonant skeletons beyond the small NWS_OVERRIDES table use a "
            "documented default /a/-filler, not individually reconstructed comparative "
            "vocalization -- see controls/sources.md 'Vocalization convention'.",
        ],
    }
    log_path = paths.CONTROLS / "render_log.json"
    log_path.write_text(json.dumps(render_log_doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"wrote {controls_path} ({len(controls)} controls)")
    print(f"wrote {log_path} ({len(render_log)} per-word decisions)")
    print(f"wrote {holdout_path} ({sum(len(v) for v in holdout.values())} withheld comparanda)")
    print("\nper-class counts:")
    for cls, n in sorted(class_counts.items()):
        print(f"  {cls}: {n}")
    print("\nworked-example reproduction:")
    for w in worked:
        status = "PASS" if w["reproduced"] else "FAIL"
        print(f"  [{status}] {w['name']}: expected {w['expected']!r}, got {w['got']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
