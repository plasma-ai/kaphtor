"""Greek → Linear B CV spelling converter.

Renders a transliterated Greek lemma (the greek_lexicon.jsonl `normalized`
form) into its expected Linear B orthography, per the standard Mycenological
spelling rules, so candidate substitutions can be scored against attested
LB forms directly (khrusos → kuruso ↔ ku-ru-so).

Rules implemented:
  1. Series folding — LB neutralizes aspiration and (except d) voicing:
     kh/g → k, ph/b → p, th → t; h drops; l → r (single liquid series).
  2. Coda drop — syllable-final l, r, m, n, s before a consonant and all
     word-final consonants are unwritten (khalkos → kako, tripos → tiripo).
  3. Dead-vowel echo — remaining consonant clusters (stop+liquid/glide,
     s+stop after s-retention contexts, ks/ps) spell each consonant with
     the following syllable's vowel (khrusos → ku-ru-so).
  4. i-diphthongs lose the glide (poimen → pome); u stays as a vowel
     nucleus in hiatus (au → a-u).

Known limitations (accepted, documented): labiovelars are not recoverable
from alphabetic Greek (a-to-ro-qo will surface as atoropo, one substitution
away); Mycenaean forms predating contraction (do-e-ra vs δούλη) match only
at distance. These bound the metric, not the method.
"""
from __future__ import annotations

import re

VOWELS = "aeiou"

# Order matters: digraphs before single letters.
_FOLDS = [
    ("kh", "k"), ("ph", "p"), ("th", "t"), ("ps", "ps"), ("ks", "ks"),
    ("x", "ks"), ("g", "k"), ("b", "p"), ("l", "r"), ("h", ""),
]

_CODA_DROP = set("rmns")  # post-fold: l has become r


def _fold(translit: str) -> str:
    s = translit.lower()
    s = re.sub(r"[^a-z]", "", s)
    for src, tgt in _FOLDS:
        s = s.replace(src, tgt)
    # Geminate collapse: LB writes double consonants single (ippos → i-po,
    # aggelos → folded akkeros → a-ke-ro). Must follow the series folds so
    # kh+k, g+g etc. have already merged into identical letters.
    s = re.sub(r"([^aeiou])\1+", r"\1", s)
    return s


def _drop_glides(s: str) -> str:
    """Drop i-glide in diphthongs (ai/ei/oi/ui before consonant or end)."""
    return re.sub(rf"([{VOWELS}])i(?![{VOWELS}])", r"\1", s)


def greek_to_lb(translit: str, *, hyphens: bool = False) -> str:
    """Convert a transliterated Greek lemma to its expected LB spelling.

    Returns a CV-sequence string, hyphen-separated if requested
    (greek_to_lb("khrusos", hyphens=True) → "ku-ru-so").
    """
    s = _fold(translit)
    if not s:
        return ""

    # Drop i-glide in diphthongs (ai/ei/oi/ui followed by consonant or end).
    s = _drop_glides(s)

    # Tokenize into consonant-run / vowel alternation.
    parts = re.findall(rf"[{VOWELS}]|[^{VOWELS}]+", s)

    syllables: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if part[0] in VOWELS:
            syllables.append(part)
            i += 1
            continue
        cluster = part
        next_vowel = parts[i + 1] if i + 1 < len(parts) and parts[i + 1][0] in VOWELS else None
        if next_vowel is None:
            # Word-final: the last consonant is unwritten; any consonants
            # before it take a regressive echo of the preceding vowel
            # (wanaks → wa-na-ka).
            prev_vowel = syllables[-1][-1] if syllables else None
            if prev_vowel:
                for c in cluster[:-1]:
                    syllables.append(c + prev_vowel)
            i += 1
            continue
        # Word-initial s before a consonant is unwritten (sperma → pe-ma).
        if len(cluster) > 1 and cluster[0] == "s" and not syllables:
            cluster = cluster[1:]
        # Coda drop: liquid/nasal/s closing the previous syllable.
        while len(cluster) > 1 and cluster[0] in _CODA_DROP and syllables:
            cluster = cluster[1:]
        # Remaining cluster: dead-vowel echo of the following vowel.
        for c in cluster[:-1]:
            syllables.append(c + next_vowel)
        syllables.append(cluster[-1] + next_vowel)
        i += 2

    return "-".join(syllables) if hyphens else "".join(syllables)


# Attested-LB-side counterpart to greek_to_lb: render a corpus token into
# the same neutralized phoneme space as the precomputed lb_keys. Values are
# the standard (Ventris-Chadwick) syllabary readings expressed post-fold:
# h unwritten, aspiration folded, glide y written i. Proposed
# values for untransliterated *NN signs are deliberately NOT baked in here —
# open signs are a gate decision for callers, not a transport convention.
_LB_SPECIAL_SIGNS = {
    "a2": "a",      # ha — h is unwritten in the lb_key fold
    "a3": "ai",     # ai
    "au": "au",
    "ja": "ia", "je": "ie", "jo": "io", "ju": "iu",
    "pa2": "pa",    # *56 under its doublet rendering
    "pa3": "pa",    # pai/pha — folds to pa either way
    "pu2": "pu",    # phu — aspiration folds
    "ra2": "ria",   # rya/lya
    "ra3": "rai",
    "ro2": "rio",   # ryo/lyo
    "ta2": "tia",   # tya
    "dwe": "dwe", "dwo": "dwo",
    "twe": "twe", "two": "two",
    "nwa": "nwa",
    "pte": "pte",
}

_LB_PLAIN_SIGN = re.compile(r"[dkmnpqrstwz]?[aeiou]")
_SUBSCRIPT_DIGITS = str.maketrans("₂₃₄", "234")
_EDGE_MARKS = str.maketrans("", "", "[]⸤⸥'’")


def lb_token_to_key(token: str) -> str | None:
    """Render an attested Linear B token into the lb_key phoneme space.

    ku-ru-su-pa2 → "kurusupa", a3-ka-sa-ma → "akasama" (same glide-drop
    rule as greek_to_lb, so both sides of a comparison live in one space).

    Returns None when the token cannot be rendered faithfully: any
    untransliterated *NN sign, a lacuna dot (•), or an unrecognized
    syllable refuses the whole token — a mutilated rendering must never
    reach a distance metric. Edge-damage brackets are stripped and the
    visible signs rendered; whether a broken token should be scored at
    all remains the caller's gate.
    """
    if not token:
        return None
    t = token.lower().translate(_SUBSCRIPT_DIGITS).translate(_EDGE_MARKS)
    if "•" in t or "*" in t:
        return None
    rendered: list[str] = []
    for syl in t.split("-"):
        if not syl:
            continue  # empty segment left by a stripped edge bracket
        r = _LB_SPECIAL_SIGNS.get(syl)
        if r is None:
            if not _LB_PLAIN_SIGN.fullmatch(syl):
                return None
            r = syl
        rendered.append(r)
    if not rendered:
        return None
    return _drop_glides("".join(rendered))


def _selftest() -> None:
    cases = {
        "khrusos": "kuruso",    # ku-ru-so 'gold'
        "khalkos": "kako",      # ka-ko 'bronze'
        "tripos": "tiripo",     # ti-ri-po 'tripod'
        "elephas": "erepa",     # e-re-pa 'ivory'
        "zugon": "zuko",        # cf. -zo-ko/-zu-ko compounds
        "sperma": "pema",       # pe-ma 'seed'
        "poimen": "pome",       # po-me 'shepherd'
        "wanax": "wanaka",      # wa-na-ka (ks cluster echoes a)
        "ippos": "ipo",         # i-qo in LB (labiovelar unrecoverable) — geminate test
        "aggelos": "akero",     # a-ke-ro 'messenger' — γγ via fold+collapse
        "allos": "aro",         # a-ro₂-... family — liquid geminate
    }
    failures = []
    for src, want in cases.items():
        got = greek_to_lb(src)
        if got != want:
            failures.append(f"{src}: want {want}, got {got}")
    if failures:
        raise SystemExit("greek_to_lb selftest FAILED:\n  " + "\n  ".join(failures))
    print(f"greek_to_lb selftest OK ({len(cases)} cases)")


if __name__ == "__main__":
    _selftest()
