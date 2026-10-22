"""Per-source transliteration normalisers for Semitic root comparison.

Every source spells the same consonant its own way: SED writes ʔ ʕ ḳ ŝ ɣ and ``t_``; Kogan's K-series writes ḍ
for *ṣ́; the Sabaic dictionary's ``root`` column uses š for s₁ in Beeston rows and for s₂ in the rest; the Geʿez
lexicon's Latin root merges h/ḥ/ḫ and s/ś/š. ``normalise`` maps one string from one named scheme into the
notation of Huehnergard 2019 Table 3.2, so a reflex
can be looked up in ``data/semitic_correspondences.json`` directly: PS headwords into the PS column's symbols,
daughter forms into their branch column's symbols (Arabic ǧ and ḍ, Sabaic s₁ s₂ s₃ and ṣ́, Mehri ź and ḏ̣).

Only consonant notation changes. Vowels, hyphens, ``V`` placeholders, parentheses, glosses and sense numbers
pass through untouched; turning a headword into radicals is the root-key resolver's job. Where a source's
notation cannot decide between two consonants, the result carries every reading as a separate variant and a
flag says why. Letters no scheme accounts for are flagged ``unmapped:<char>``, never guessed.

    from tools.core.semitic_notation import normalise, geez_fidel_consonants
    normalise("*t_̣Vl-", "ps").variants          # ('*ẓVl-',)
    normalise("ʿŠR", "sabaic_display").variants  # ('ʿs₂r',)
    geez_fidel_consonants("ኀለለ")                # 'ḫll'

Attribution: di Mino
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# Placeholders for symbols whose source notation is ambiguous; expanded into variants at the end.
_AMBIGUOUS = {
    "": ("š", "ś"),    # SED ŝx / sx̂: sibilant left undecided between *š and *ś
    "": ("s₁", "s₃"),  # Sabaic dictionary rows without superscripts: S is s¹ or s³
    # George & Krebernik, RA 116 (2022) §3.2: ’ an unclear guttural; capitals cover what cuneiform does not tell
    # apart (voicing, emphasis, š/ŝ).
    "": ("ʾ", "ʿ", "h", "ḥ"), "": ("š", "ś"), "": ("p", "b"), "": ("b", "p"),
    "": ("d", "t", "ṭ"), "": ("t", "d", "ṭ"), "": ("g", "k", "q"), "": ("k", "g", "q"),
    "": ("q", "k", "g"), "": ("s", "z", "ṣ"), "": ("z", "s", "ṣ"),
}
MAX_VARIANTS = 16
_GK_COVER = {"Š": "", "P": "", "B": "", "D": "", "T": "", "G": "",
             "K": "", "Q": "", "S": "", "Z": ""}
_GK_SLOT = re.compile(r"([^\W\d_])/([^\W\d_])")

# Applied to every scheme, after NFC.
_COMMON = [("ʔ", "ʾ"), ("ʕ", "ʿ"), ("ˤ", "ʿ"), ("ᶜ", "ʿ"), ("ʼ", "ʾ")]

# PS headwords: SED numbered records and the K, S and SA series of semitic_roots.json.
_PS = [
    ("t_̣", "ẓ"), ("ṯ̣", "ẓ"), ("ṭ_", "ẓ"),     # SED emphatic interdental (ṭ_ with precomposed ṭ)
    ("ŝx", ""), ("sx̂", ""),            # SED undecided š/ś
    ("ṣ̂", "ṣ́"),                                       # SED emphatic lateral
    ("t_", "ṯ"), ("d_", "ḏ"), ("h_", "ḫ"),
    ("ŝ", "ś"), ("ḳ", "q"), ("ɣ", "ġ"), ("ǵ", "ġ"), ("θ", "ṯ"),
    ("ḍ", "ṣ́"),                                          # K and S series write *ṣ́ as Arabic ḍ
    ("ʷ", ""), ("Ṣ", "ṣ"),
]
# SED's affricate reconstruction (after "{}", or standing alone): ĉ = *ś, č = *ṯ, ǯ = *ḏ, ʒ = *z.
_PS_AFFRICATE = [("ĉ̣", "ṣ́"), ("č̣", "ẓ"), ("ĉ", "ś"), ("č", "ṯ"), ("ǯ", "ḏ"), ("ʒ", "z")]

# Daughter forms quoted in SED/StarLing notation (semitic_roots.json Analogues).
_SED_DAUGHTER = [
    ("t_̣", "ẓ"), ("ṣ̂", "ṣ́"),
    ("t_", "ṯ"), ("d_", "ḏ"), ("h_", "ḫ"),
    ("ŝ", "ś"), ("ḳ", "q"), ("ɣ", "ġ"), ("ʷ", ""),
]
_BRANCH_OVERLAY = {
    "Arabic": [("ǯ", "ǧ"), ("ğ", "ǧ")],
    "Sabaic": [("s1", "s₁"), ("s2", "s₂"), ("s3", "s₃"), ("s¹", "s₁"), ("s²", "s₂"), ("s³", "s₃"), ("ḍ", "ṣ́")],
    "Mehri": [("ẑ", "ź")],
}

_UGARITIC = [("θ", "ṯ")]
# Alphabetic Ugaritic writes its three alephs as ả ỉ ủ, or plain a i u (Huehnergard á í ú): udn = ʾudn 'ear'.
_UGARITIC_ALEPH = re.compile(r"(?<!ʾ)[ảỉủáíúaiu]")
_UGARITIC_ALEPH_VOWEL = {"ả": "a", "ỉ": "i", "ủ": "u", "á": "a", "í": "i", "ú": "u", "a": "a", "i": "i", "u": "u"}
_PHOENICIAN = [("'", "ʾ"), ("’", "ʾ"), ("ț", "ṭ")]
_DASI = [("s1", "s₁"), ("s2", "s₂"), ("s3", "s₃"), ("s¹", "s₁"), ("s²", "s₂"), ("s³", "s₃"), ("ḍ", "ṣ́")]

SCHEMES = {
    "ps": "PS headwords of semitic_roots.json (SED, K, S, SA series)",
    "sed_daughter": "Analogues forms in SED/StarLing notation; pass branch= for Arabic, Sabaic or Mehri",
    "hebrew": "TBESH/BDB/BHSA roots and keys (already canonical)",
    "aramaic": "Aramaic Root Atlas/SEDRA roots (already canonical)",
    "akkadian": "Huehnergard 1997 glossary root_consonants (already canonical)",
    "ugaritic": "CUC roots, DULAT lexemes and the Ugaritic lexicon's keys: aleph signs ả ỉ ủ / a i u / á í ú, θ",
    "phoenician": "Krahmalkov and Tomback roots (ASCII apostrophe = ʾ, ț = ṭ)",
    "arabic_qac": "Quranic Arabic Corpus root keys (ǧ kept: it is the table's Arabic symbol)",
    "sabaic_display": "Sabaic dictionary root_display: S¹/S²/S³ when marked; otherwise Š = s₂, S = s₁ or s₃",
    "dasi": "DASI/CSAI forms with s¹ s² s³ or s1 s2 s3",
    "geez_latin": "Leslau-style Latin Geʿez roots (ḍ kept: it is the table's Geʿez symbol)",
    "amorite": "Gelb/Huffmon normalized keys",
    "amorite_gk": "George & Krebernik 2022 lemmas and roots: ŝ, ’ unclear guttural, capital cover symbols, a/b slots",
    "buckwalter": "Buckwalter Arabic (K-series analogues): case-sensitive; A^ hamza seat, ~ shadda, o sukun",
}

_SIMPLE = {
    "hebrew": [], "aramaic": [], "akkadian": [], "arabic_qac": [], "geez_latin": [], "amorite": [],
    "phoenician": _PHOENICIAN, "dasi": _DASI,
}

_SABAIC_LETTERS = {
    "Ḥ": "ḥ", "Ḫ": "ḫ", "Ġ": "ġ", "Ṣ": "ṣ", "Ṭ": "ṭ", "Ṯ": "ṯ", "Ḏ": "ḏ", "Ẓ": "ẓ", "Ḍ": "ṣ́",
    "'": "ʾ", "’": "ʾ", "X": "ḫ",                           # Beeston root_display: XBB = ḫbb
}

# Consonant symbols the output may contain (table notation plus modern Ethiopian and MSA phonemes).
CANONICAL_CONSONANTS = frozenset(
    "bdgzhwyklmnpqrstfvjxc"
    "ʾʿḏġḥḫśšṣṭṯẓǧḍźžčñǯň"
) | {"ṣ́", "s₁", "s₂", "s₃", "ḏ̣"}
_VOWEL_BASES = frozenset("aeiouəǝɛɔɨʌy")


@dataclass(frozen=True)
class Normalised:
    variants: tuple[str, ...]
    flags: tuple[str, ...]


def _apply(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(_nfc(old), new)
    return text


# Buckwalter transliteration (case-sensitive). SED digraphs (d_ t_ h_) are read first: a few K-series records mix
# them in, and Buckwalter's own "_" is the tatweel.
_BUCKWALTER = {
    "'": "ʾ", ">": "ʾ", "<": "ʾ", "&": "ʾ", "}": "ʾ", "^": "ʾ", "|": "ʾā", "A": "ā", "Y": "ā", "`": "ā", "{": "",
    "p": "t", "v": "ṯ", "j": "ǧ", "H": "ḥ", "x": "ḫ", "*": "ḏ", "$": "š", "S": "ṣ", "D": "ḍ", "T": "ṭ",
    "Z": "ẓ", "E": "ʿ", "g": "ġ", "_": "", "o": "", "F": "", "N": "", "K": "",
}


def _buckwalter(text: str) -> str:
    text = _apply(text, [("t_̣", "ẓ"), ("d_̣", "ẓ"), ("t_", "ṯ"), ("d_", "ḏ"), ("h_", "ḫ")])
    text = re.sub(r"A\^", "^", text)                      # A^ = hamza on its alif seat
    text = text.replace("aA", "A").replace("aY", "Y")       # fatha + alif / alif maqsura = one long ā
    out: list[str] = []
    for ch in text:
        if ch == "~":
            if out:
                out.append(out[-1])                        # shadda doubles the consonant before it
            continue
        out.append(_BUCKWALTER.get(ch, ch))
    return "".join(out)


def _sabaic_display(text: str, flags: list[str]) -> str:
    text = re.sub(r"\s+[IVX]+\b", "", text).strip()          # homograph numerals: "BŠR I"
    text = text.replace("S¹", "s₁").replace("S²", "s₂").replace("S³", "s₃")
    if any(c in text for c in "²³"):                       # Beeston writes ʾ as ² or ³ outside S: '²BW', 'MR³'
        flags.append("sabaic_digit_aleph")
        text = text.replace("²", "ʾ").replace("³", "ʾ")
    text = text.replace("Š", "s₂")
    if "S" in text:
        flags.append("sabaic_s1_s3_unmarked")
        text = text.replace("S", "")
    text = "".join(_SABAIC_LETTERS.get(c, c) for c in text)
    return "".join(c.lower() if c.isascii() else c for c in text)


def _unmapped(text: str) -> list[str]:
    found = []
    for ch in text:
        if ch in _AMBIGUOUS or not ch.isalpha() or ch == "V":
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        if ch.lower() in CANONICAL_CONSONANTS or base.lower() in _VOWEL_BASES:
            continue
        if base.isascii() and base.isalpha() and ch.isascii():
            continue
        if f"unmapped:{ch}" not in found:
            found.append(f"unmapped:{ch}")
    return found


def _expand(text: str, flags: list[str], cap: int = MAX_VARIANTS) -> tuple[str, ...]:
    slots = [_AMBIGUOUS.get(ch, (ch,)) for ch in text]
    count = 1
    for s in slots:
        count *= len(s)
    if count > cap:
        flags.append("variant_cap")
        return ("".join(s[0] for s in slots),)
    return tuple("".join(p) for p in itertools.product(*slots))


def _amorite_gk(text: str) -> Normalised:
    """G&K readings: '(?)' and '?' dropped; 'mā (or mah)' gives both words; a/b one-letter slots (ḫan/mp-) and
    parenthesised optional parts ((y)id-) give each reading; then ŝ → ś and the cover symbols expand."""
    flags: list[str] = []
    text = re.sub(r"\(\?\)|\?", "", text).strip()
    m = re.fullmatch(r"(.+?)\s*\(or ([^()]+)\)", text)
    readings = [m.group(1).strip(), m.group(2).strip()] if m else [text]
    while any(_GK_SLOT.search(r) for r in readings):
        readings = [x for r in readings for x in ((_GK_SLOT.sub(r"\1", r, count=1), _GK_SLOT.sub(r"\2", r, count=1))
                                                  if _GK_SLOT.search(r) else (r,))]
    while any("(" in r for r in readings):
        readings = [x for r in readings for x in ((re.sub(r"\(([^()]*)\)", r"\1", r, count=1),
                                                   re.sub(r"\([^()]*\)", "", r, count=1)) if "(" in r else (r,))]
    variants: list[str] = []
    for r in readings:
        if any(c in _GK_COVER for c in r):
            flags.append("cover_symbol")
        if "’" in r:
            flags.append("guttural_unclear")
        r = "".join(_GK_COVER.get(c, c) for c in r.replace("ŝ", "ś").replace("’", "\ue010"))
        flags.extend(_unmapped(r))
        variants.extend(v for v in _expand(_nfc(r), flags, cap=64) if v not in variants)
    return Normalised(tuple(variants), tuple(dict.fromkeys(flags)))


def normalise(text: str, scheme: str, branch: str | None = None) -> Normalised:
    """Map ``text`` from ``scheme`` into Huehnergard Table 3.2 notation; see the module docstring."""
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; known: {sorted(SCHEMES)}")
    flags: list[str] = []
    out = _apply(_nfc(text or ""), _COMMON)
    if scheme == "amorite_gk":
        return _amorite_gk(out)

    if scheme == "ps":
        if "{}" in out:
            out = out.split("{}", 1)[0].rstrip()
            flags.append("affricate_alternative_dropped")
        out = _apply(out, _PS)
        if any(_nfc(a) in out for a, _ in _PS_AFFRICATE):
            flags.append("affricate_notation")
            out = _apply(out, _PS_AFFRICATE)
        if "ṗ" in out:
            flags.append("emphatic_p")
            out = out.replace("ṗ", "p")
    elif scheme == "sed_daughter":
        out = _apply(out, _SED_DAUGHTER + _BRANCH_OVERLAY.get(branch or "", []))
    elif scheme == "sabaic_display":
        out = _sabaic_display(out, flags)
    elif scheme == "buckwalter":
        out = _buckwalter(out)
    elif scheme == "ugaritic":
        out = _UGARITIC_ALEPH.sub(lambda m: "ʾ" + _UGARITIC_ALEPH_VOWEL[m.group()], _apply(out, _UGARITIC))
    else:
        out = _apply(out, _SIMPLE[scheme])

    if "" in out:
        flags.append("sed_sibilant_undecided")
    flags.extend(_unmapped(out))
    return Normalised(_expand(_nfc(out), flags), tuple(flags))


# Geʿez fidel: one consonant per series, all distinctions kept (h/ḥ/ḫ, s/ś/š, ṣ/ḍ), no geminate collapsing.
# Labiovelars drop the labialisation, as SED's ʷ does. Series start code points, Unicode Ethiopic block.
_FIDEL_SERIES = [
    (0x1200, "h"), (0x1208, "l"), (0x1210, "ḥ"), (0x1218, "m"), (0x1220, "ś"), (0x1228, "r"), (0x1230, "s"),
    (0x1238, "š"), (0x1240, "q"), (0x1248, "q"), (0x1250, "q"), (0x1258, "q"), (0x1260, "b"), (0x1268, "v"),
    (0x1270, "t"), (0x1278, "č"), (0x1280, "ḫ"), (0x1288, "ḫ"), (0x1290, "n"), (0x1298, "ñ"), (0x12A0, "ʾ"),
    (0x12A8, "k"), (0x12B0, "k"), (0x12B8, "x"), (0x12C0, "x"), (0x12C8, "w"), (0x12D0, "ʿ"), (0x12D8, "z"),
    (0x12E0, "ž"), (0x12E8, "y"), (0x12F0, "d"), (0x12F8, "ɗ"), (0x1300, "ǧ"), (0x1308, "g"), (0x1310, "g"),
    (0x1318, "g"), (0x1320, "ṭ"), (0x1328, "č̣"), (0x1330, "p"), (0x1338, "ṣ"), (0x1340, "ḍ"), (0x1348, "f"),
    (0x1350, "p"),
]
FIDEL_CONSONANTS: dict[str, str] = {
    chr(base + order): cons for base, cons in _FIDEL_SERIES for order in range(8) if chr(base + order).strip()
}


def geez_fidel_consonants(fidel: str) -> str:
    """Return the consonants of a fidel string, one per written sign, with every distinction kept."""
    return "".join(FIDEL_CONSONANTS[ch] for ch in fidel if ch in FIDEL_CONSONANTS)
