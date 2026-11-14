"""A typed excavation (find) number as a regular expression.

Zero padding and spacing do not matter (RS 16.156 = RS 16.0156 = RS16.156), and a longer number is another tablet
(EA 34 is not EA 340). The pattern runs unchanged in Python and in DuckDB's RE2, so it uses no lookahead.
"""
from __future__ import annotations

import re

DOTTED = re.compile(r"\s*(?:([A-Za-z]{1,5})\.?\s*)?(\d+)\s*([./])\s*(\d+)\s*")      # RS 16.156, RIH 77/9, 16.156
PLAIN = re.compile(r"\s*([A-Za-z]{1,5})\.?\s+(\d+)\s*")                             # ND 2390, EA 34


def find_number_pattern(typed: str) -> str | None:
    """A regular expression for a typed find number, or None when the text is not one. Leading zeros and the
    space after the siglum are free; the number must end where the typed one ends."""
    if m := DOTTED.fullmatch(typed or ""):
        siglum, first, sep, second = m.groups()
        number = rf"0*{int(first)}\s*[{re.escape(sep)}]\s*0*{int(second)}($|[^0-9./]|[./]($|[^0-9]))"
        return rf"(?i)(^|[^0-9A-Za-z]){re.escape(siglum)}\.?\s*{number}" if siglum else rf"(^|[^0-9./]){number}"
    if m := PLAIN.fullmatch(typed or ""):
        siglum, number = m.groups()
        return rf"(?i)(^|[^0-9A-Za-z]){re.escape(siglum)}\.?\s*0*{int(number)}($|[^0-9])"
    return None
