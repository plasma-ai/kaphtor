"""Token classes, anchors and quantities for a corpus record's `transliteratedWords`.

This module supplies what every positional reader of a record shares: the token class of each position, the anchor
check that ties a span's `at` range to its form, line spans, and the value of a quantity. The sign-position builder
(tools/linear_a/build_sign_positions.py) keys every sign by the index of its token and its place in
`_bare(token).split("-")`.

Token classes are derived here and never stored. A lone single sign or a lone *NNN sign stays `single_sign`: whether
it is a transaction sign, an abbreviation or a logogram is an adjudicated role, not a token class. A token no rule
recognises is `other`, so new shapes surface instead of passing as signs.

Quantities read the value-rendered transliteration (GORILA/Bennett fraction values).
tools/linear_a/analysis/fraction_arithmetic.py treats those values as a hypothesis and works from the raw
klasmatograms; a raw klasmatogram has no value here, and a residual against a stated total is evidence, not an error.
"""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction
from functools import lru_cache

from .data_cache import sign_value_entries, sign_values

LINE_BREAK = "\n"
DIVIDER = "\U00010101"            # 𐄁
RULES = frozenset({"—", "–"})
DAMAGE = "\U0001076B"             # 𐝫
LACUNA_TOKENS = frozenset({DAMAGE, "[?]", "?", "][?]", "[?][", "[", "]", "None"})
MEASURES = frozenset({"double mina"})

# Latin-named logogram bases: LOGO in tools/linear_a/validation/check_unread_words.py (less L, which the
# transliteration also writes for the fraction sign A709) and MULTI_SIGN_LOGOGRAMS in
# tools/linear_a/logogram_analyzer.py, plus HIDE.
LOGOGRAM_BASES = frozenset({
    "GRA", "OLE", "VIN", "VINA", "TELA", "LANA", "OLIV", "FIC", "CYP", "BOS", "OVIS", "OVI",
    "SUS", "CAP", "EQU", "VIR", "AES", "AUR", "HORD", "COR", "ARE", "TRI", "AROM", "GAL",
    "VAS", "CER", "HIDE",
})

FRAC_CP_RANGE = range(0x10740, 0x10756)  # raw klasmatograms (fraction_arithmetic.py)
AEGEAN_NUMBERS = range(0x10107, 0x10134)
# Rendered fraction values; FRACTION_VALUES in tools/linear_a/logogram_analyzer.py, as Fractions.
VULGAR = {
    "¼": Fraction(1, 4), "½": Fraction(1, 2), "¾": Fraction(3, 4),
    "⅐": Fraction(1, 7), "⅑": Fraction(1, 9), "⅒": Fraction(1, 10),
    "⅓": Fraction(1, 3), "⅔": Fraction(2, 3), "⅕": Fraction(1, 5),
    "⅖": Fraction(2, 5), "⅗": Fraction(3, 5), "⅘": Fraction(4, 5),
    "⅙": Fraction(1, 6), "⅚": Fraction(5, 6), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8),
}
SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_FRACTION_RE = re.compile(r"^(≈\s*)?([⁰¹²³⁴⁵⁶⁷⁸⁹]+)⁄([₀₁₂₃₄₅₆₇₈₉]+)$")
_SLASH_FRACTION_RE = re.compile(r"^(\d+)/(\d+)$")          # "13/20" (KH91)
_KLASMA_LETTER_RE = re.compile(r"^(?:[A-Z]|L\d)(?:\+(?:[A-Z]|L\d))*$")  # "L", "J+L2"

_SINGLE_RE = re.compile(r"^(?:\*\d{2,3}|AB\d{2,3}|[A-Z]{1,3}[₂₃]?)$")   # TWE, AB77
_LETTERED_RE = re.compile(r"^\*\d{2,3}([A-Za-z])$")      # *21F, *28B, *131B
_VESSEL_RE = re.compile(r"^\*\d{2,3}-VS(?:-.*)?$")        # *402-VS, *402-VS-QA-PA₃
_GORILA_NO_RE = re.compile(r"^A(\d{3})\b")                # A319 logogram, A70x fraction sign
_ERASED_RE = re.compile(r"^\[\[.*\]\]$")

CLASSES = (
    "word", "mixed", "single_sign", "logogram", "numeral", "fraction", "measure",
    "divider", "line_break", "rule", "lacuna", "other",
)


def _text(token: object) -> str:
    return token if isinstance(token, str) else ("" if token is None else str(token))


def _bare(token: object) -> str:
    """The token without editorial brackets."""
    return _text(token).replace("[", "").replace("]", "")


def is_erased(token: object) -> bool:
    """[[14]]: the scribe erased it (GORILA double brackets)."""
    return bool(_ERASED_RE.match(_text(token).strip()))


def is_restored(token: object) -> bool:
    text = _text(token)
    return not is_erased(text) and ("[" in text or "]" in text)


def is_damaged(token: object, glyph: object = None) -> bool:
    return DAMAGE in _text(token) or DAMAGE in _text(glyph)


def is_raw_fraction(text: object) -> bool:
    """Every sign a klasmatogram (damage marks aside)."""
    signs = [ch for ch in _text(text) if ch != DAMAGE]
    return bool(signs) and all(ord(ch) in FRAC_CP_RANGE for ch in signs)


def _is_aegean_number(text: str) -> bool:
    signs = [ch for ch in text if ch != ","]
    return bool(signs) and all(ord(ch) in AEGEAN_NUMBERS for ch in signs)


def _is_rendered_fraction(text: str) -> bool:
    return (text in VULGAR or bool(_FRACTION_RE.match(text))
            or bool(_SLASH_FRACTION_RE.match(text)) or is_raw_fraction(text))


@lru_cache(maxsize=1)
def lettered_syllabograms() -> frozenset[str]:
    """Letter-suffixed signs with a phonemic value (*28B = JI), from sign_values.json.

    Same source as LETTERED in tools/linear_a/validation/check_unread_words.py.
    """
    signs = (p.split("=")[0] for p in sign_value_entries(sign_values()["resolution_summary"], "phonemic"))
    return frozenset(s for s in signs if re.fullmatch(r"\*\d+[A-Z]", s))


def _logogram_base(part: str) -> str:
    """'OVISf' -> 'OVIS', '*OLIV+TU' -> 'OLIV', 'AB22/CAPF' -> 'CAP'."""
    base = part.split("/")[-1].lstrip("*").split("+")[0]
    if base[-1:] in ("f", "m", "F", "M") and base[:-1] in LOGOGRAM_BASES:
        return base[:-1]
    return base


def _is_logogram_part(part: str) -> bool:
    if "+" in part or _VESSEL_RE.match(part) or _is_aegean_number(part):
        return True
    return _logogram_base(part) in LOGOGRAM_BASES


def token_class(token: object) -> str:
    """The class of one transliteratedWords token, read without its glyph."""
    text = _text(token)
    if text == LINE_BREAK:
        return "line_break"
    if text == DIVIDER or text.strip() == "≈":       # lone ≈ stands between words (ARGZg1, TELZb1)
        return "divider"
    if text in RULES:
        return "rule"
    if text in LACUNA_TOKENS:
        return "lacuna"
    if text in MEASURES:
        return "measure"
    bare = _bare(text).strip()
    if not bare or bare in ("?", "…", "?…"):
        return "lacuna"
    if bare.isdigit() or _is_aegean_number(bare):
        return "numeral"
    if _is_rendered_fraction(bare):
        return "fraction"
    gorila = _GORILA_NO_RE.match(bare)
    if gorila and "-" not in bare:
        return "fraction" if gorila.group(1).startswith("7") else "logogram"
    if _VESSEL_RE.match(bare):
        return "logogram"
    lettered = _LETTERED_RE.match(bare)
    if lettered:
        if lettered.group(1) in "FMfm":                # sex-marked: livestock (*21F, *22M)
            return "logogram"
        return "single_sign" if bare in lettered_syllabograms() else "logogram"
    if "-" in bare:
        parts = [p for p in bare.split("-") if p]
        return "mixed" if any(_is_logogram_part(p) for p in parts) else "word"
    if _is_logogram_part(bare):
        return "logogram"
    if _SINGLE_RE.match(bare):
        return "single_sign"
    return "other"


def classify(record: dict) -> list[dict]:
    """One row per transliteratedWords token: index, token, glyph, class and flags.

    When the lists line up, the glyph decides two things the transliteration hides:
    a token whose glyph is all klasmatogram is a fraction (".3" is A711 X, "?" on
    KEWc2 is A702 B twice), and a 𐝫 in the glyph marks the token damaged. Such a
    fraction is raw, without a value, only when its transliteration renders none:
    "¹⁄₂" over 𐝆 keeps its ½.
    """
    tw = record.get("transliteratedWords") or []
    words = record.get("words") or []
    aligned = len(tw) == len(words)
    rows = []
    for i, tok in enumerate(tw):
        tok = _text(tok)
        glyph = _text(words[i]) if aligned else ""
        cls = token_class(tok)
        klasma = is_raw_fraction(glyph) and cls not in ("line_break", "divider", "rule")
        raw = klasma and fraction_value(tok) is None
        rows.append({
            "i": i,
            "token": tok,
            "glyph": glyph,
            "class": "fraction" if klasma else cls,
            "raw_fraction": raw or is_raw_fraction(tok),
            "damaged": is_damaged(tok, glyph),
            "restored": is_restored(tok),
            "erased": is_erased(tok),
        })
    return rows


def is_aligned(record: dict) -> bool:
    """True when words, transliteratedWords and translatedWords line up."""
    lengths = {len(record.get(k) or []) for k in ("words", "transliteratedWords", "translatedWords")
               if record.get(k) is not None}
    return len(lengths) <= 1


def parse_at(at: str) -> tuple[int, int]:
    """'6-8' -> (6, 8); '6' -> (6, 6)."""
    first, _, last = str(at).partition("-")
    start = int(first)
    end = int(last) if last else start
    if end < start:
        raise ValueError(f"anchor range runs backwards: {at!r}")
    return start, end


def anchor_form(tokens: list[str], at: str) -> str:
    """The tokens an anchor covers, joined by single spaces (line breaks and empty tokens dropped)."""
    start, end = parse_at(at)
    if end >= len(tokens):
        raise IndexError(f"anchor {at!r} past the last token ({len(tokens) - 1})")
    if LINE_BREAK in (tokens[start], tokens[end]):
        raise ValueError(f"anchor {at!r} starts or ends on a line break")
    return " ".join(t for t in map(_text, tokens[start:end + 1]) if t and t != LINE_BREAK)


def check_anchor(tokens: list[str], at: str, form: str) -> str | None:
    """None when the anchor holds; otherwise what the tokens actually say, or why it cannot."""
    try:
        actual = anchor_form(tokens, at)
    except (ValueError, IndexError) as exc:
        return str(exc)
    return None if actual == form else actual


def line_spans(tokens: list[str]) -> list[tuple[int, int]]:
    """(first, last) token index of each non-empty line."""
    spans, start = [], None
    for i, tok in enumerate(tokens):
        if tok == LINE_BREAK:
            if start is not None:
                spans.append((start, i - 1))
            start = None
        elif start is None:
            start = i
    if start is not None:
        spans.append((start, len(tokens) - 1))
    return spans


def fraction_value(token: object) -> Fraction | None:
    """Value of a rendered fraction token; None for raw or unvalued signs."""
    text = _bare(token).strip()
    if text in VULGAR:
        return VULGAR[text]
    m = _FRACTION_RE.match(text)
    if m:
        return Fraction(int(m.group(2).translate(SUPERSCRIPT)), int(m.group(3).translate(SUBSCRIPT)))
    m = _SLASH_FRACTION_RE.match(text)
    if m and int(m.group(2)):
        return Fraction(int(m.group(1)), int(m.group(2)))
    return None


def numeral_value(token: object) -> int | None:
    """Value of a numeral token: digits or Aegean number signs."""
    text = _bare(token).strip()
    if text.isdigit():
        return int(text)
    if _is_aegean_number(text):
        return int(sum(unicodedata.numeric(ch) for ch in text if ch != ","))
    return None


def _as_row(item: object) -> dict:
    if isinstance(item, dict):
        return item
    tok = _text(item)
    return {"token": tok, "glyph": "", "class": token_class(tok), "raw_fraction": is_raw_fraction(tok),
            "damaged": is_damaged(tok), "restored": is_restored(tok), "erased": is_erased(tok)}


def quantity_value(items: list) -> tuple[Fraction | None, bool]:
    """Sum of the numeral and fraction positions given; (value, approximate).

    Takes classify() rows (preferred: they carry glyph damage and raw klasmatograms)
    or bare tokens. Value is None when there is no quantity or when any fraction has
    no rendered value. Approximate is True when a counted position is damaged,
    restored, erased or marked ≈, when a fraction has no value, or when a lacuna
    follows the line's last counted position.
    """
    total, approx, seen = Fraction(0), False, False
    rows = [_as_row(item) for item in items]
    for row in rows:
        cls, tok = row["class"], row["token"]
        if cls == "numeral":
            value = numeral_value(tok)
        elif cls == "fraction":
            if "≈" in tok:
                approx = True
            value = None if row.get("raw_fraction") else fraction_value(tok)
            if value is None:
                return None, True
        else:
            continue
        if value is None:
            return None, True
        total += value
        seen = True
        if row.get("damaged") or row.get("restored") or row.get("erased"):
            approx = True
    if rows and rows[-1]["class"] == "lacuna":
        approx = True
    return (total if seen else None), approx


def format_value(value: Fraction | None) -> str:
    """130½-style rendering for review pages; −½ for negative residuals."""
    if value is None:
        return "—"
    sign = "−" if value < 0 else ""
    whole, rest = divmod(abs(value), 1)
    if not rest:
        return f"{sign}{int(whole)}"
    glyph = next((g for g, v in VULGAR.items() if v == rest), None)
    if glyph is None:
        frac = f"{rest.numerator}/{rest.denominator}"
        return f"{sign}{int(whole)} {frac}" if whole else f"{sign}{frac}"
    return f"{sign}{int(whole)}{glyph}" if whole else f"{sign}{glyph}"
