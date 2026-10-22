"""Shared schema rules for ``data/semitic_roots.json``."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

ANALOGUE_RESERVED_KEYS = frozenset({"Notes"})

_BROWSE_KEY_VOWELS = frozenset(
    "aeiouvāēīōūăĕĭŏŭəǝâêîôûáéíóúàèìòùäëïöü"
)
_BROWSE_KEY_TRANSLATION = str.maketrans({
    "√": "",
    "*": "",
    "ʿ": "ʕ",
    "ʻ": "ʕ",
    "ˁ": "ʕ",
    "ʾ": "ʔ",
    "ʼ": "ʔ",
    "ˀ": "ʔ",
    "ả": "ʔ",
    "ỉ": "ʔ",
    "ủ": "ʔ",
})


def roots_records(doc: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The records of a semitic_roots file in the shape the tools key on: Number, Proto-Semitic, Meaning,
    Analogues (language → text) and Notes. The shipped file (schema 2) is converted; a reflex without text
    (`text_withheld`) has no Analogues entry. The private list format passes through unchanged."""
    if isinstance(doc, list):
        return doc
    if doc.get("schema_version") != 2:
        raise ValueError(f"semitic_roots.json schema_version {doc.get('schema_version')} is not 2")
    records = []
    for root in doc["roots"]:
        rec = {"Number": root["id"], "Proto-Semitic": root["ps"], "Meaning": root["meaning"],
               "Analogues": {x["lang"]: x["text"] for x in root["reflexes"] if "text" in x}}
        if "notes" in root:
            rec["Notes"] = root["notes"]
        records.append(rec)
    return records


def is_analogue_language_key(key: str) -> bool:
    """Return whether an ``Analogues`` key names a language or dialect."""
    return key not in ANALOGUE_RESERVED_KEYS


def exact_entry_content_key(entry: dict[str, Any]) -> str:
    """Return a stable, lossless content key, excluding record numbering."""
    content = {key: value for key, value in entry.items() if key != "Number"}
    return json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def root_meaning_identity_key(entry: dict[str, Any]) -> tuple[str, str] | None:
    """Return the exact NFC root-and-meaning identity, if both fields exist."""
    root = entry.get("Proto-Semitic")
    meaning = entry.get("Meaning")
    if not isinstance(root, str) or not isinstance(meaning, str):
        return None
    root = unicodedata.normalize("NFC", root).strip()
    meaning = unicodedata.normalize("NFC", meaning).strip()
    if not root or not meaning:
        return None
    return root, meaning


def normalize_root_browse_key(value: str) -> str:
    """Return a lossy consonantal key for browsing and collision review.

    This key preserves distinct Semitic consonants. Never use it to establish
    duplicate identity or to delete records.
    """
    text = unicodedata.normalize("NFC", value or "").lower()
    text = text.translate(_BROWSE_KEY_TRANSLATION)
    key = "".join(
        character
        for character in text
        if (
            character == "~"
            or (
                character not in _BROWSE_KEY_VOWELS
                and not character.isdigit()
                and unicodedata.category(character)[0] not in {"P", "S", "Z"}
            )
        )
    )
    return re.sub(r"~+", "~", key).strip("~")


# --- Root-key resolver -------------------------------------------------------------------------------------
# Radical keys for comparing PS headwords with daughter-language roots and forms. A PS headword becomes one or
# more tuples of radicals in Huehnergard Table 3.2 notation; a daughter form becomes, per position, the set of
# PS phonemes its consonant can continue (data/semitic_correspondences.json, reverse table, via its proxies).
# Matches are "exact" (radical for radical) or "reduced" (a PS radical absorbed: Akkadian/Mehri Ø, a weak w/y,
# or a geminate written once). A key match is a lead for review, never identity.

from dataclasses import dataclass
from functools import cache, lru_cache
from itertools import product
from pathlib import Path

try:
    from ..paths import SEMITIC_ROOTS_DATA, require
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import SEMITIC_ROOTS_DATA, require

_CORRESPONDENCES = SEMITIC_ROOTS_DATA / "semitic_correspondences.json"
_KEY_VOWELS = frozenset("aeiouəǝvɛɔæ")
_KEY_GLOTTALS = {"ʔ": "ʾ", "ʼ": "ʾ", "ˀ": "ʾ", "ả": "ʾ", "ỉ": "ʾ", "ủ": "ʾ", "ʕ": "ʿ", "ʻ": "ʿ", "ˁ": "ʿ", "`": "ʿ"}
_SUBSCRIPT_DIGITS = frozenset("₀₁₂₃₄₅₆₇₈₉")
_WEAK = frozenset("wy")
# Daughter consonants a match may absorb, each counted, the match then "reduced": w/y/ʾ anywhere (weak radical,
# mater lectionis), prefixes before the first matched radical (ʾaCCaC, maCCaC, taCCīC, niphal, yiqtol, hiphil),
# suffixes after the last (-at, -ah, -īm, -ayim, -īn, -ān, -ūt). At most MAX_ABSORB in all; once any daughter
# consonant is absorbed, at least two PS radicals (or all of a shorter key) must be matched outright. PS-side
# absorption alone (Akkadian Ø, a weak or geminate radical) needs one matched radical: Akk. abu for *ʾab-.
_DAUGHTER_WEAK = frozenset("wyʾ")
_DAUGHTER_PREFIX = frozenset("ʾmtnyh")
_DAUGHTER_SUFFIX = frozenset("tmnyhw")
MAX_ABSORB = 3


def _notation():
    try:
        from .semitic_notation import normalise
    except ImportError:  # lib/ itself on sys.path
        from semitic_notation import normalise
    return normalise


@lru_cache(maxsize=1)
def _correspondences() -> dict[str, Any]:
    return json.loads(require(_CORRESPONDENCES, _CORRESPONDENCES.name).read_text(encoding="utf-8"))


def _radicals(text: str) -> tuple[tuple[str, ...], bool]:
    """Consonant tokens of one form, and whether it began with a bare vowel. A token is a base letter with its
    combining marks and subscript digits (ṯ, x̣, s₁); vowels, length marks, digits and punctuation drop."""
    text = unicodedata.normalize("NFC", text).lower()
    for src, dst in _KEY_GLOTTALS.items():
        text = text.replace(src, dst)
    tokens: list[str] = []
    first_vowel = None
    for ch in text:
        if (unicodedata.category(ch).startswith("M") or ch in _SUBSCRIPT_DIGITS) and tokens and tokens[-1]:
            tokens[-1] += ch
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        if base in _KEY_VOWELS:
            first_vowel = True if first_vowel is None else first_vowel
            tokens.append("")              # placeholder: marks after a vowel are dropped with it
            continue
        if ch in "ʾʿ" or (ch.isalpha() and unicodedata.category(ch) != "Lm"):
            first_vowel = False if first_vowel is None else first_vowel
            tokens.append(ch)
        else:
            tokens.append("")
    return tuple(t for t in tokens if t), bool(first_vowel)


_SEGMENT = r"(?:[^\W\d_]|[ʾʿ])[\u0300-\u036f₀-₉]*"
_SLOT_ALTERNATION = re.compile(rf"{_SEGMENT}(?:/{_SEGMENT})+")
_GLOSS_OR_NOTE = re.compile(r"'[^']*'|‘[^’]*’|\"[^\"]*\"|\([^()]*[<>?=\s][^()]*\)")


def _expand_optional(text: str) -> list[str]:
    """Every reading with its parenthesised parts in and out: *(ʔi-)nVš- → ʔi-nVš-, nVš-."""
    parts = re.split(r"(\([^()]*\))", text)
    optional = [i for i, p in enumerate(parts) if p.startswith("(") and p.endswith(")")][:3]
    out = []
    for keep in product((True, False), repeat=len(optional)):
        chosen = dict(zip(optional, keep))
        pieces = []
        for i, p in enumerate(parts):
            if i not in chosen:
                pieces.append(p)
            elif chosen[i]:
                pieces.append(p[1:-1])
        out.append("".join(pieces))
    return out


def _expand_slots(text: str) -> list[str]:
    """SED a/b alternates a single slot: *w/nVpVt_- → wVpVt_-, nVpVt_-; *bVṣ/s/zVḳ- gives three readings.
    Between vowelless roots of three or more radicals the slash separates whole forms instead: *dkr/zkr/skr.
    Two-letter parts still share a slot: *mw/yt is m-w/y-t."""
    parts = [x for x in text.split("/") if x]
    if len(parts) > 1 and all(not any(unicodedata.normalize("NFD", c)[0] in _KEY_VOWELS for c in x.lower())
                              and len(_radicals(x)[0]) >= 3 for x in parts):
        return parts
    pieces = _SLOT_ALTERNATION.split(text)
    choices = [m.group().split("/") for m in _SLOT_ALTERNATION.finditer(text)][:5]
    out = []
    for pick in product(*choices):
        out.append("".join(p + (pick[i] if i < len(pick) else "") for i, p in enumerate(pieces)))
    return out


def _ps_forms(text: str) -> list[str]:
    """The starred forms of a headword. Quoted glosses and notes in parentheses with spaces, < or ? drop;
    forms separate at commas (SED sense numbers), ~, ; and spaces; unstarred words (dissim, or) are ignored."""
    text = _GLOSS_OR_NOTE.sub(" ", text)
    forms = [f.rstrip("/") for f in re.findall(r"\*[^\s,~;<*]+", text)]
    return forms or [text]


def ps_radical_keys(ps: str) -> tuple[tuple[str, ...], ...]:
    """Radical keys of a PS headword, in order, without duplicates. Each starred form, slot alternative and
    optional part gives a key; only the stem counts (the first hyphen segment: -at-, -t- are suffixes). A
    word-initial bare vowel is a lost ʾ (the cognate_search rule), so the ʾ-prefixed key comes first and the
    bare key is kept as fallback."""
    keys: list[tuple[str, ...]] = []
    for variant in _notation()(ps or "", "ps").variants:
        for form in _ps_forms(variant):
            form = form.strip().lstrip("*").rstrip("?")
            for slot_reading in _expand_slots(form):
                for reading in _expand_optional(slot_reading):
                    for key in _stem_keys(reading):
                        if key and key not in keys:
                            keys.append(key)
    return tuple(keys)


def _stem_keys(reading: str, lost_glottal: bool = True) -> list[tuple[str, ...]]:
    """Keys of one hyphenated reading. The stem is the first segment with two or more radicals; segments before
    it are prefixes (ma-, ʾa-, nu-), after it suffixes (-at-, -t-). Stem first, then prefix + stem if it stays
    within 5 radicals. A reading with no two-radical segment is read whole (*sū-t- → s t). lost_glottal adds the
    ʾ-prefixed key for a bare initial vowel (PS headwords only; in daughters that is Akkadian/Mehri Ø)."""
    segs = [_radicals(x) for x in reading.split("-") if x]
    segs = [(r, v) for r, v in segs if r]
    if not segs:
        return []
    idx = next((i for i, (r, _) in enumerate(segs) if len(r) >= 2), None)
    if idx is None:
        rads = tuple(c for r, _ in segs for c in r)
        return [("ʾ",) + rads, rads] if lost_glottal and segs[0][1] else [rads]
    stem, bare_vowel = segs[idx]
    out = [("ʾ",) + stem, stem] if lost_glottal and bare_vowel and idx == 0 else [stem]
    if idx:
        full = tuple(c for r, _ in segs[: idx + 1] for c in r)
        if len(full) <= 5:
            out.append(full)
    return out


@dataclass(frozen=True)
class RootPattern:
    """Per variant, per position: the PS phonemes a daughter consonant can continue."""
    patterns: tuple[tuple[frozenset[str], ...], ...]
    tokens: tuple[tuple[str, ...], ...]
    zero: frozenset[str]           # PS phonemes this branch can lose entirely (Akkadian, Mehri Ø)
    branch: str | None
    flags: tuple[str, ...]
    derived: frozenset[int] = frozenset()   # indexes of patterns widened by a conditioned change: reduced only
    nasal_assimilation: bool = False        # PS n may surface as a doubling of the next consonant (Akkadian)
    tt_sources: frozenset[str] = frozenset()  # key-final PS radicals that surface as t before the feminine t


def language_branch(language: str) -> str | None:
    table = _correspondences()
    if language in table["branches"]:
        return language
    return table["proxies"].get(language)


# Akkadian conditioned changes (Huehnergard, A Grammar of Akkadian): Geers' law dissimilates one of two emphatics
# to its plain counterpart (*ṣbṭ → ṣabātu, *qrṣ → karāṣu), as a widened pattern here; in _align, a key-final dental
# or n before the feminine t assimilates to it (*kabid-t- → kabattu, *šan-at- → šattu), and PS n before a radical
# assimilates to it (*ʾanp- → appu).
_GEERS = {"k": "q", "t": "ṭ", "s": "ṣ"}
_EMPHATICS = frozenset("qṭṣ")


def _akkadian_widened(rads: tuple[str, ...], sets: list[frozenset[str]], reverse: dict) -> list[frozenset[str]]:
    out = list(sets)
    if _EMPHATICS & set(rads):
        for n, r in enumerate(rads):
            if r in _GEERS:
                out[n] = out[n] | frozenset(x.lstrip("*") for x in reverse.get(_GEERS[r], []))
    return out


def daughter_root_pattern(form: str, language: str, scheme: str = "sed_daughter") -> RootPattern:
    """PS candidates per consonant of a daughter form. scheme is a semitic_notation scheme: sed_daughter for
    SED/StarLing analogues (branch overlay applied), buckwalter for K-series Arabic, or a lexicon's own.
    Akkadian readings widened by Geers' law are extra patterns listed in derived: a match through one is reduced,
    never exact. Akkadian forms with mimation (-um, -am, -im, -(m)) are also read without it."""
    table = _correspondences()
    branch = language_branch(language)
    flags: list[str] = []
    if branch is None:
        flags.append("no_branch")
    reverse = table["reverse"].get(branch, {}) if branch else {}
    norm = _notation()(form or "", scheme, branch if scheme == "sed_daughter" else None)
    flags.extend(norm.flags)
    patterns, tokens = [], []
    readings = []
    variants = list(norm.variants)
    if branch == "Akkadian":
        variants += [re.sub(r"(?:(?<=[aiuāīū])m|\(m\))$", "", v) for v in variants
                     if re.search(r"(?:[aiuāīū]m|\(m\))$", v) and len(_radicals(v)[0]) > 2]
    for variant in variants:
        readings.append(_radicals(variant.replace("-", ""))[0])        # whole form
        readings.extend(_stem_keys(variant, lost_glottal=False))      # stem without affixes (ʔins-ān-)
    for rads in dict.fromkeys(readings):
        sets = []
        for r in rads:
            ps = reverse.get(r)
            if ps is None:
                if branch:
                    flags.append(f"unmapped:{r}")
                sets.append(frozenset({r}))
            else:
                sets.append(frozenset(p.lstrip("*") for p in ps if p != "Ø"))
        if rads and tuple(sets) not in patterns:
            patterns.append(tuple(sets))
            tokens.append(rads)
    derived = []
    if branch == "Akkadian":
        for sets, rads in list(zip(patterns, tokens)):
            wide = tuple(_akkadian_widened(rads, list(sets), reverse))
            if wide != sets and wide not in patterns:
                derived.append(len(patterns))
                patterns.append(wide)
                tokens.append(rads)
    zero = frozenset(p.lstrip("*") for p in reverse.get("Ø", []))
    tt = frozenset(x.lstrip("*") for x in reverse.get("d", []) + reverse.get("ṭ", []) + ["*n"]) \
        if branch == "Akkadian" else frozenset()
    return RootPattern(tuple(patterns), tuple(tokens), zero, branch, tuple(dict.fromkeys(flags)), frozenset(derived),
                       branch == "Akkadian", tt)


def _align(ps_key: tuple[str, ...], sets: tuple[frozenset[str], ...], toks: tuple[str, ...], zero,
           nasal: bool = False, tt: frozenset[str] = frozenset()) -> bool | None:
    """True = radical for radical, False = matched with absorptions (see _DAUGHTER_*), None = no match. With
    nasal, a PS n before a radical the daughter writes doubled is absorbed with the doubling, in one step
    (Akkadian *ʾanp- → appu); a key-final radical in tt (after it only weak radicals) is read as the first t of a
    tt, the second absorbed as the feminine (*šan-at- → šattu, *ṯVny- → šittān). PS radicals
    the branch loses (zero) or assimilates (nasal), and a geminate's second copy, do not count toward the radicals
    that must match outright, in Akkadian (nasal set) only, provided the daughter adds at most one absorbed
    consonant (*ʾir-at- irtu, *ʾanp- appu):
    with two or more, two radicals must match (measured on the Akkadian sweeps: allowing any number added 0.2-1.0
    points of key recall and cost 4-5 roots of real-minus-shuffled present)."""
    n_ps, n_d = len(ps_key), len(sets)

    @cache
    def go(i: int, j: int) -> tuple[int, int, int, int, int] | None:
        # (absorptions, matched, daughter abs., lost, daughter abs. not a feminine t or nasal doubling)
        if i == n_ps and j == n_d:
            return (0, 0, 0, 0, 0)
        options = []
        if i < n_ps and j < n_d and ps_key[i] in sets[j]:
            sub = go(i + 1, j + 1)
            if sub:
                options.append((sub[0], sub[1] + 1, sub[2], sub[3], sub[4]))
        if i < n_ps and ps_key[i] in zero:
            sub = go(i + 1, j)
            if sub:
                options.append((sub[0] + 1, sub[1], sub[2], sub[3] + 1, sub[4]))
        if (nasal and i + 1 < n_ps and j + 1 < n_d and ps_key[i] == "n" and toks[j] == toks[j + 1]
                and ps_key[i + 1] in sets[j]):                  # nC → CC: the n and the doubling, explained
            sub = go(i + 2, j + 2)
            if sub:
                options.append((sub[0] + 2, sub[1] + 1, sub[2] + 1, sub[3] + 1, sub[4]))
        if (i < n_ps and ps_key[i] in tt and all(c in _WEAK for c in ps_key[i + 1:]) and j + 1 < n_d
                and toks[j] == toks[j + 1] == "t"):           # C-t → tt: the second t is the feminine
            sub = go(i + 1, j + 2)
            if sub:
                options.append((sub[0] + 1, sub[1] + 1, sub[2] + 1, sub[3], sub[4]))
        if i < n_ps and i and ps_key[i - 1] == ps_key[i]:      # a geminate's second copy: not a new radical
            sub = go(i + 1, j)
            if sub:
                options.append((sub[0] + 1, sub[1], sub[2], sub[3] + 1, sub[4]))
        absorb_ps = i < n_ps and ps_key[i] in _WEAK
        absorb_d = j < n_d and (
            (j and toks[j] == toks[j - 1])                    # daughter gemination
            or toks[j] in _DAUGHTER_WEAK
            or (i == 0 and toks[j] in _DAUGHTER_PREFIX)
            or (i == n_ps and toks[j] in _DAUGHTER_SUFFIX))
        explained = j < n_d and i == n_ps and toks[j] == "t"                         # feminine -t
        for ok, nxt, d in ((absorb_ps, (i + 1, j), 0), (absorb_d, (i, j + 1), 1)):
            if ok:
                sub = go(*nxt)
                if sub:
                    options.append((sub[0] + 1, sub[1], sub[2] + d, sub[3], sub[4] + (d and not explained)))
        return min(options, key=lambda o: (o[0], o[2], -o[1], o[4])) if options else None

    best = go(0, 0)
    # The relaxation is measured on Akkadian only, and only for a feminine t or the doubling an assimilated n leaves.
    lost = best[3] if best and nasal and not best[4] else 0
    if best is None or best[0] > MAX_ABSORB or best[1] < (1 if not best[2] else min(2, n_ps - lost) if best[2] == 1 else min(2, n_ps)):
        return None
    return best[0] == 0


def match_root_key(ps_key: tuple[str, ...], pattern: RootPattern) -> str | None:
    """'exact', 'reduced' or None for one PS key against a daughter pattern."""
    result = None
    for n, (sets, toks) in enumerate(zip(pattern.patterns, pattern.tokens)):
        hit = _align(tuple(ps_key), sets, toks, pattern.zero, pattern.nasal_assimilation, pattern.tt_sources)
        if hit and n not in pattern.derived:
            return "exact"
        if hit is not None:
            result = "reduced"
    return result


def weak_variants(key: tuple[str, ...]) -> dict[tuple[str, ...], str]:
    """Labelled alternative keys for weak and geminate roots. Leads for key-only review, never identity."""
    out: dict[tuple[str, ...], str] = {}

    def add(k, label):
        k = tuple(k)
        if k != tuple(key) and k not in out:
            out[k] = label

    k = tuple(key)
    if len(k) == 3:
        a, b, c = k
        if a in _WEAK:
            add(("y" if a == "w" else "w", b, c), "I-w/y")
            add((b, c), "I-weak")
        if b in _WEAK:
            add((a, c), "hollow")
            add((a, "y" if b == "w" else "w", c), "II-w/y")
        if c in _WEAK | {"ʾ"}:
            add((a, b), "III-weak")
            for alt in sorted(_WEAK | {"ʾ"} - {c}):
                add((a, b, alt), "III-w/y/ʾ")
        if b == c:
            add((a, b), "geminate")
    elif len(k) == 2:
        a, b = k
        add((a, b, b), "geminate")
        for w in sorted(_WEAK):
            add((a, w, b), "hollow")
            add((w, a, b), "I-weak")
            add((a, b, w), "III-weak")
        add((a, b, "ʾ"), "III-weak")
    return out


_ANALOGUE_STOPWORDS = frozenset({"cf", "pl", "du", "suff", "sg", "fem", "masc", "note", "also", "and", "or", "see",
                                 "redupl"})
_DIALECT_CODE = re.compile(r"[A-ZČŠŽ][\w̆̌]{0,4}\.?")                     # Sab, Qat, Zwy, MAL, PB, Bib.
_LEADING_QUALIFIER = re.compile(r"^\s*\([^()]*\)(?:\s+|(?=\*))")         # (?) šbr, (Bibl) pas-, (?)*färäz
_OPTIONAL_PREFIX = re.compile(r"^\s*\([^()\s]{1,4}\)(?=[^\W\d_])")       # (tä)däbärä: the stem is däbärä
_LEADING_ALEPH_WORD = re.compile(r"^\s*'[^\W\d_][^\s,;]*")                # 'abbā, 'akallə'at: ' written for ʾ
_GLOSS_OPENERS = frozenset({"to", "be", "the", "a", "an", "of", "in", "id"})


def _leading_forms(text: str, codes_alone_are_forms: bool) -> list[str]:
    head = re.split(r"\bid\.|['‘\"(\[]|\s\d", text, maxsplit=1)[0]
    forms = []
    for part in re.split(r"[,;]", head):
        words = [w for w in part.split() if w.lower().rstrip(".") not in _ANALOGUE_STOPWORDS]
        kept = [w for w in words if not _DIALECT_CODE.fullmatch(w)]
        if kept:
            forms.append(kept[0].strip("*.:"))
        elif codes_alone_are_forms and words:
            forms.append(words[-1].strip("*.:"))
    return [f for f in forms if re.search(r"[^\W\d_]", f)]                # +, --, ? mark presence, not a form


def analogue_forms(text: str, number: str, language: str) -> tuple[list[str], str]:
    """Leading forms of one Analogues string and the notation scheme to read them with.

    SED/StarLing: 'ab, aba id. (DM, 1)' → ['ab', 'aba']; dialect codes (SAB, CHA, Zwy.), glosses and cites drop,
    reading stops at the first gloss marker (id., quote, parenthesis). K-series Arabic is Buckwalter
    ('HaSada[Reaped]'): bracketed glosses drop and up to three forms are kept.

    When that finds nothing, a second read: a leading qualifier ((?) šbr, (Bibl) pas-) or optional prefix
    ((tä)däbärä) drops, ' in a string-initial form is ʾ ('abbā '(my) father'), and a capitalised word standing
    alone is the form (Abba 'Father', root-atlas ŠMʿ 'hear'). Placeholders (+, --, ?) are never forms."""
    if language == "Arabic" and str(number).startswith("K"):
        parts = [x for x in re.split(r"\[[^\]]*\]|\s*\|\s*|;\s*", text) if x.strip()][:3]
        return [x.split()[0] for x in parts if x.split()], "buckwalter"
    forms = _leading_forms(text, codes_alone_are_forms=False)
    if forms:
        return forms, "sed_daughter"
    t = text
    while _LEADING_QUALIFIER.match(t):
        t = _LEADING_QUALIFIER.sub("", t, count=1)
    t = _OPTIONAL_PREFIX.sub("", t, count=1)
    m = _LEADING_ALEPH_WORD.match(t)
    if m and m.group().strip().lstrip("'").lower() not in _GLOSS_OPENERS:
        t = m.group().replace("'", "ʾ") + t[m.end():]
    return _leading_forms(t, codes_alone_are_forms=True), "sed_daughter"
