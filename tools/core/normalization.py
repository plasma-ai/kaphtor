"""Port of SEMITIC._normalize() and SEMITIC._lookupIn() from semiticLexicon.js."""
from __future__ import annotations

import re
from typing import TypeVar

T = TypeVar("T")

SUBSCRIPT_MAP = str.maketrans("₂₃₄₅", "2345")
WORD_SEPARATORS: frozenset[str] = frozenset({"\n", "\U00010101"})   # line break, Aegean word separator 𐄁
LOGOGRAM_PREFIX = re.compile(r"^\*\d+(-VS)?-")


def normalize_id(value: str) -> str:
    """Normalize an inscription ID for lookup: strip whitespace and lowercase."""
    return "".join(str(value).lower().split())


def normalize(word: str) -> str:
    """Strip subscripts and logogram prefixes (*NNN- or *NNN-VS-).

    Matches the JS SEMITIC._normalize(): subscript chars (₂₃₄₅) are removed
    entirely, not converted to digits. This ensures KU-PA₃-NU → KU-PA-NU
    (matching the Gordon lexicon key), not KU-PA3-NU.
    """
    # Strip Unicode subscript digits (₂₃₄₅) entirely — matches JS behavior
    result = re.sub(r"[₂₃₄₅]", "", word)
    # Strip logogram prefix: *NNN- or *NNN-VS-
    return LOGOGRAM_PREFIX.sub("", result)


def is_word(token: str) -> bool:
    """A sign or sign group: not a line break, word separator, numeral, fraction or damage mark."""
    return bool(token) and token not in WORD_SEPARATORS and (any(ch.isalpha() for ch in token) or "*" in token)


def lookup_in(entries: dict[str, T], word: str) -> T | None:
    """Look up a word as written, then without a leading logogram (*NNN- or *NNN-VS-) when a sign group remains,
    then with J and Y swapped. Subscripts are kept (SU-PU₂ is not SU-PU), and a logogram's lone complement is not
    the word it spells (*301-NA is not NA)."""
    if not word or word in WORD_SEPARATORS:
        return None
    forms = [word]
    bare = LOGOGRAM_PREFIX.sub("", word)
    if bare != word and "-" in bare:
        forms.append(bare)
    forms += [v for form in list(forms) for v in _jy_variants(form)]
    return next((entries[f] for f in forms if f in entries), None)


def _jy_variants(word: str) -> list[str]:
    """Generate J/Y substitution variants for GORILA/Gordon convention mismatch."""
    variants = []
    ja_to_ya = re.sub(r"\bJA", "YA", word).replace("-JA-", "-YA-").replace("-JA", "-YA")
    if ja_to_ya != word:
        variants.append(ja_to_ya)
    ya_to_ja = re.sub(r"\bYA", "JA", word).replace("-YA-", "-JA-").replace("-YA", "-JA")
    if ya_to_ja != word:
        variants.append(ya_to_ja)
    return variants
