"""Weighted Levenshtein distance with language-specific sound shift costs.

Supports Semitic, Luwian (Anatolian), and Egyptian phonological distance tables.
Semitic: voicing pairs, emphatic shifts, sibilant/guttural correspondences.
Luwian: fortis/lenis stops, labiovelars, lenition, i-mutation.
Egyptian: pharyngeal cognates, Afroasiatic f/p shift, sibilant mergers.

Operates on phoneme tokens, not raw characters, so multi-character phonemes
(sh, ts, kw) and Unicode diacritical consonants (š, ṣ, ṭ) are handled correctly.
"""
from __future__ import annotations

import re
import unicodedata

# Canonical phoneme alphabet: map all representations to single tokens.
# Skeletons use ASCII multi-char (sh, ts); roots use Unicode (š, ṣ).
# Both normalize to the same canonical form for comparison.
_TO_CANONICAL: dict[str, str] = {
    # Multi-char skeleton phonemes
    "sh": "š", "ts": "ṣ",
    # NFC Unicode consonants
    "š": "š",  # š
    "ṣ": "ṣ",  # ṣ
    "ṭ": "ṭ",  # ṭ
    "ḥ": "ḥ",  # ḥ
    "ḫ": "ḫ",  # ḫ
    "ṯ": "ṯ",  # ṯ
    "ḏ": "ḏ",  # ḏ
    "ś": "ś",  # ś
    "ẓ": "ẓ",  # ẓ
    "ʿ": "ʿ",  # ʿ (U+02BF modifier letter left half ring)
    "ʕ": "ʿ",  # ʕ (U+0295 latin pharyngeal) → canonical ʿ
    "ʾ": "ʾ",  # ʾ
    "ʔ": "ʔ",  # ʔ
    "ġ": "ġ",  # ġ (voiced velar fricative, Semitist convention)
    "ɣ": "ġ",  # ɣ (IPA) → ġ (Semitist canonical)
    "ǯ": "ǯ",  # ǯ
    "č": "č",  # č
    "ŝ": "š",  # ŝ → š
    "ḍ": "ḏ",  # ḍ → ḏ
    "ṇ": "n",  # ṇ (*86 emphatic nasal) → n: no plain/emphatic nasal contrast is
               # recoverable through LB values or root skeletons, so unlike
               # ṭ/ṯ/ḏ (kept distinct, distance-table mediated) ṇ normalizes
               # to n. Formalizes what NFD mark-stripping previously did.
    # Egyptian-specific phonemes (Latin Extended-D)
    "ꜥ": "ꜥ",  # U+A725 Egyptological ain
    "ꜣ": "ꜣ",  # U+A723 Egyptological alef
    # Contact-lexicon encoding variants (θ/ġ canonicalization repair, 2026-07-21).
    # DULAT, CUC, and other source databases encode Semitic phonemes using Greek,
    # Cyrillic, and Latin-Extended characters that _tokenize_phonemes previously
    # passed through as raw chars, making 568 contact entries invisible to matching.
    # Validated by thrust3_shadow_canon_sweep.py against 48 targets (30 new matches).
    "θ": "ṯ",  # Greek theta → interdental (DULAT convention for Ugaritic ṯ)
    "ө": "ṯ",  # Cyrillic ө → interdental
    "ǵ": "ġ",  # g-acute → voiced velar fricative
    "ḡ": "ġ",  # g-macron → voiced velar fricative
    "H̱": "ḫ",  # H-macron-below → ḫ (uppercase)
    "ẖ": "ḫ",  # h-macron-below → ḫ (lowercase)
    "đ": "ḏ",  # d-stroke → voiced interdental
    "δ": "ḏ",  # Greek delta → voiced interdental
    "ş": "ṣ",  # s-cedilla → emphatic s
    "ṱ": "ṭ",  # t-dot-below variant → emphatic t
    "ț": "ṭ",  # t-cedilla → emphatic t
    "ħ": "ḥ",  # h-stroke → pharyngeal h
    "ḵ": "k",  # k-macron-below → k
    "ž": "z",  # z-háček → z
    "ˁ": "ʿ",  # modifier letter pharyngeal voiced fricative → ayin
    "ʼ": "ʾ",  # modifier letter apostrophe → aleph
    "’": "ʾ",  # right single quotation mark → aleph
    "ꞽ": "y",  # Latin small letter i with stroke → y
    "ỉ": "y",  # i with hook below → y (Egyptological yod)
    # Syriac consonant letters (Aramaic-script contact entries)
    "ܐ": "ʾ", "ܒ": "b", "ܓ": "g", "ܕ": "d", "ܗ": "h", "ܘ": "w",
    "ܙ": "z", "ܚ": "ḥ", "ܛ": "ṭ", "ܝ": "y", "ܟ": "k", "ܠ": "l",
    "ܡ": "m", "ܢ": "n", "ܣ": "s", "ܥ": "ʿ", "ܦ": "p", "ܨ": "ṣ",
    "ܩ": "q", "ܪ": "r", "ܫ": "š", "ܬ": "t",
}

# NFD-normalized lookup: keys decomposed so base+combining pairs match
# during NFD iteration (e.g., NFC "š" → NFD "š" as a dict key).
_NFD_LOOKUP: dict[str, str] = {}
for _k, _v in _TO_CANONICAL.items():
    _NFD_LOOKUP[unicodedata.normalize("NFD", _k)] = _v

# Substitution costs for known Semitic sound correspondences.
# All entries use canonical phoneme tokens.
SEMITIC_DISTANCES: dict[tuple[str, str], float] = {
    # Voicing pairs (minimal distance)
    ("t", "d"): 0.1,
    ("k", "g"): 0.1,
    ("p", "b"): 0.1,
    ("s", "z"): 0.1,
    # Sibilant correspondences
    ("s", "š"): 0.15,   # s/š
    ("z", "š"): 0.2,    # z/š
    ("s", "ś"): 0.2,    # s/ś
    ("š", "ś"): 0.15,  # š/ś
    # Liquid interchange
    ("l", "r"): 0.15,
    # Emphatic correspondences
    ("t", "ṭ"): 0.3,    # t/ṭ
    ("d", "ṭ"): 0.35,   # d/ṭ
    ("k", "q"): 0.15,   # script-level neutralization: glottalic *kʼ with no emphatic series (Huehnergard 2019 §2.1)
    ("s", "ṣ"): 0.3,    # s/ṣ
    ("z", "ṣ"): 0.15,   # ṣ = [tsʼ] is a glottalic member of the Z-series affricate class (Huehnergard 2019 §2.1)
    ("z", "ẓ"): 0.3,    # z/ẓ
    ("s", "ẓ"): 0.35,   # s/ẓ
    # Guttural / laryngeal
    ("h", "ḥ"): 0.2,    # h/ḥ
    ("h", "ḫ"): 0.25,   # h/ḫ
    ("ḥ", "ḫ"): 0.15,  # ḥ/ḫ
    # Interdental ↔ dental/sibilant (pre-merger forms)
    ("ṯ", "š"): 0.2,   # ṯ/š
    ("ṯ", "z"): 0.2,   # interdentals live in the Z-series (ZU = /ṯu/); affricate-model class proximity
    ("ṯ", "t"): 0.3,       # ṯ/t
    ("ḏ", "z"): 0.2,       # ḏ/z
    ("ḏ", "d"): 0.3,       # ḏ/d
    # Semivowel interchange
    ("w", "y"): 0.25,
    # Voiced velar fricative (PS *ġ, Arabic غ)
    ("ġ", "g"): 0.15,   # closest stop
    ("ġ", "k"): 0.25,   # voiceless velar
    ("ġ", "ʿ"): 0.2,    # PS *ġ merges with ʿ in Canaanite
    ("ġ", "ḫ"): 0.25,   # both uvular/pharyngeal area
    ("ġ", "q"): 0.3,    # back-of-throat
}


LUWIAN_DISTANCES: dict[tuple[str, str], float] = {
    # Fortis/lenis pairs (Luwian stop contrast)
    ("t", "d"): 0.1,
    ("k", "g"): 0.1,
    ("p", "b"): 0.1,
    # Labiovelars (Luwian-specific, absent from Semitic)
    ("kw", "k"): 0.15,
    ("kw", "g"): 0.2,
    ("gw", "g"): 0.15,
    ("gw", "k"): 0.2,
    # Lenition (stops → fricatives)
    ("t", "z"): 0.2,
    ("d", "z"): 0.15,
    # Sibilants (simpler than Semitic — no emphatics)
    ("s", "z"): 0.1,
    ("s", "š"): 0.15,
    # Liquid interchange (shared with Semitic)
    ("l", "r"): 0.15,
    # Nasal assimilation
    ("n", "m"): 0.2,
    # h-loss (Anatolian laryngeals → h or ∅)
    ("ḫ", "h"): 0.05,
    # Semivowel patterns (Luwian w is prominent)
    ("w", "u"): 0.2,
    ("y", "i"): 0.2,
    # i-mutation (productive in Luwian, absent in NWS)
    ("a", "i"): 0.15,
}

EGYPTIAN_DISTANCES: dict[tuple[str, str], float] = {
    # Pharyngeal/laryngeal cognates (Proto-Afroasiatic identity)
    ("ꜥ", "ʿ"): 0.05,
    ("ꜣ", "ʾ"): 0.05,
    ("ꜣ", "ʔ"): 0.05,
    # Guttural/fricative correspondences
    ("ḫ", "h"): 0.1,
    ("ḥ", "h"): 0.15,
    ("ḫ", "ḥ"): 0.15,
    # Afroasiatic *p > Egyptian f
    ("f", "p"): 0.15,
    ("f", "b"): 0.25,
    # Voicing pairs (no emphatic series in Egyptian)
    ("t", "d"): 0.1,
    ("k", "g"): 0.1,
    ("p", "b"): 0.1,
    # Sibilant mergers (simpler than Semitic)
    ("s", "z"): 0.1,
    ("s", "š"): 0.15,
    ("š", "ś"): 0.15,
    # Interdental/dental correspondences (pre-merger)
    ("ṯ", "t"): 0.2,
    ("ḏ", "d"): 0.2,
    ("ṯ", "š"): 0.2,
    ("ḏ", "z"): 0.2,
    # Liquid interchange (l rare in older Egyptian)
    ("l", "r"): 0.15,
    # Nasal assimilation
    ("n", "m"): 0.2,
    # Semivowel patterns
    ("w", "u"): 0.2,
    ("y", "i"): 0.2,
    ("w", "y"): 0.3,
    # Notational convention: Egyptological j = Linear A y (same phoneme)
    ("j", "y"): 0.05,
    # Voiced velar fricative (contact entries)
    ("ġ", "g"): 0.15,
    ("ġ", "ʿ"): 0.2,
}


# Multi-char phoneme tokens for Luwian labiovelars
_LUWIAN_DIGRAPHS = {"kw", "gw"}


def _tokenize_phonemes(s: str) -> list[str]:
    """Split a string into phoneme tokens, recognizing multi-char phonemes."""
    tokens: list[str] = []
    i = 0
    s_nfd = unicodedata.normalize("NFD", s)
    while i < len(s_nfd):
        # Try two-char combinations first (sh, ts, kw, gw, or base+combining)
        if i + 1 < len(s_nfd):
            pair = s_nfd[i:i+2]
            if pair in _NFD_LOOKUP:
                tokens.append(_NFD_LOOKUP[pair])
                i += 2
                continue
            if pair in _LUWIAN_DIGRAPHS:
                tokens.append(pair)
                i += 2
                continue
        # Single char
        ch = s_nfd[i]
        # Skip combining marks that weren't caught above
        if unicodedata.category(ch).startswith("M"):
            i += 1
            continue
        tokens.append(_NFD_LOOKUP.get(ch, ch))
        i += 1
    return tokens


def normalize_phonemes(s: str) -> str:
    """Normalize a phoneme string to canonical form. Convenience wrapper."""
    return "".join(_tokenize_phonemes(s))


GUTTURAL_PHONEMES = frozenset({"ʔ", "ʿ", "ʾ", "ʕ", "h", "ḥ", "ḫ", "ġ", "ꜥ", "ꜣ"})
GUTTURAL_INSERT_COST = 0.1
IndelCostMap = dict[str, float]


def _get_sub_cost(a: str, b: str, distances: dict[tuple[str, str], float]) -> float:
    """Look up substitution cost (symmetric)."""
    if a == b:
        return 0.0
    return distances.get((a, b), distances.get((b, a), 1.0))


def _insert_cost(
    phoneme: str,
    guttural_transparent: bool,
    insert_costs: IndelCostMap | None = None,
) -> float:
    if insert_costs and phoneme in insert_costs:
        return insert_costs[phoneme]
    if guttural_transparent and phoneme in GUTTURAL_PHONEMES:
        return GUTTURAL_INSERT_COST
    return 1.0


def _delete_cost(phoneme: str, delete_costs: IndelCostMap | None = None) -> float:
    if delete_costs and phoneme in delete_costs:
        return delete_costs[phoneme]
    return 1.0


def weighted_levenshtein(
    s1: str,
    s2: str,
    distances: dict[tuple[str, str], float] | None = None,
    guttural_transparent: bool = False,
    insert_costs: IndelCostMap | None = None,
    delete_costs: IndelCostMap | None = None,
) -> float:
    """Weighted Levenshtein operating on phoneme tokens.

    Returns raw edit distance (not normalized). For skeletons of 2-4 phonemes,
    distances < 0.5 indicate strong matches.

    When guttural_transparent=True, inserting a guttural from s2 (the root)
    that is absent from s1 (the skeleton) costs 0.1 instead of 1.0, because
    Linear A's syllabary cannot write gutturals (ʔ, ʿ, h, ḥ, ḫ).

    Optional ``insert_costs`` and ``delete_costs`` are directional per-phoneme
    indel overrides after tokenization. Insertions are phonemes present in ``s2``
    but absent from ``s1``; deletions are phonemes present in ``s1`` but absent
    from ``s2``. Existing guttural transparency remains the default shorthand
    for root-side guttural insertions.
    """
    costs = distances or SEMITIC_DISTANCES
    t1 = _tokenize_phonemes(s1)
    t2 = _tokenize_phonemes(s2)
    n, m = len(t1), len(t2)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        if i:
            dp[i][0] = dp[i - 1][0] + _delete_cost(t1[i - 1], delete_costs)
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + _insert_cost(
            t2[j - 1], guttural_transparent, insert_costs
        )

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub_cost = _get_sub_cost(t1[i - 1], t2[j - 1], costs)
            dp[i][j] = min(
                dp[i - 1][j] + _delete_cost(t1[i - 1], delete_costs),
                dp[i][j - 1] + _insert_cost(
                    t2[j - 1], guttural_transparent, insert_costs
                ),
                dp[i - 1][j - 1] + sub_cost,  # substitution
            )

    return dp[n][m]


def guttural_transparent_levenshtein(
    skeleton: str,
    root: str,
    distances: dict[tuple[str, str], float] | None = None,
) -> float:
    """Levenshtein for comparing Linear A skeletons against Semitic roots.

    Gutturals in the root that are absent from the skeleton cost 0.1 (not 1.0),
    because Linear A's syllabary cannot write them.
    """
    return weighted_levenshtein(skeleton, root, distances, guttural_transparent=True)
