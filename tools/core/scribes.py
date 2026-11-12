"""Scribes of the corpus: the records under each label of `scribe` and `scribe_also`, and the part each wrote.

A record's `scribe` is a label of scribes.json (`HT Scribe 9`); `scribe_also` lists further scribes of the same
record as `[{"scribe": label, "part": "lines 4–6"}]`, and `scribe_part` gives the part the first one wrote.
"""
from __future__ import annotations

import re


def natural(text: str) -> list:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]


def scribe_sort_key(label: str) -> list:
    """Site and class first, then the scribe's number as a number: HT Scribe 9 before HT Scribe 10."""
    return natural(label)


def also(rec: dict) -> list[dict]:
    """The record's further scribes, from `scribe_also`; an entry without a label is left out."""
    return [a for a in (rec.get("scribe_also") or []) if isinstance(a, dict) and (a.get("scribe") or "").strip()]


def labels(rec: dict) -> list[str]:
    """Every scribe of the record, the first one first."""
    return [x for x in dict.fromkeys([(rec.get("scribe") or "").strip()] + [a["scribe"] for a in also(rec)]) if x]


def scribe_index(corpus: dict) -> dict[str, list[str]]:
    """Each scribe label with the records that carry it in either field; unassigned records are left out."""
    index: dict[str, list[str]] = {}
    for name, rec in corpus.items():
        for label in labels(rec):
            index.setdefault(label, []).append(name)
    return {label: sorted(index[label], key=natural) for label in sorted(index, key=scribe_sort_key)}


def scribe_part(rec: dict, label: str) -> str:
    """The part of the record the scribe wrote, where two scribes share it; empty where one wrote it all."""
    if (rec.get("scribe") or "").strip() == label:
        return rec.get("scribe_part") or ""
    return next((a.get("part") or "" for a in also(rec) if a["scribe"] == label), "")


def doubtful(rec: dict, label: str) -> bool:
    """`scribe_doubt` marks the record's first scribe only."""
    return bool(rec.get("scribe_doubt")) and (rec.get("scribe") or "").strip() == label


def resolve_scribe(query: str, known: list[str]) -> list[str]:
    """Labels that carry every token of the query, whole tokens only, any case; the word 'scribe' may be left out."""
    want = [t for t in query.upper().split() if t != "SCRIBE"]
    hits = [lab for lab in known if all(t in [x for x in lab.upper().split() if x != "SCRIBE"] for t in want)]
    return sorted(hits, key=scribe_sort_key)


def scribe_shared_words(corpus: dict, names: list[str]) -> list[tuple[str, list[str]]]:
    """Words written on two or more of the given records, most widely shared first. Numerals and dividers are left out."""
    seen: dict[str, list[str]] = {}
    for name in names:
        words = corpus[name].get("transliteratedWords") or []
        for w in dict.fromkeys(w for w in words if isinstance(w, str)):
            if (any(ch.isalpha() for ch in w) or "*" in w) and "𐝫" not in w:
                seen.setdefault(w, []).append(name)
    shared = [(w, docs) for w, docs in seen.items() if len(docs) > 1]
    return sorted(shared, key=lambda x: (-len(x[1]), x[0]))
