#!/usr/bin/env python3
"""Contextual neighborhood analysis for Linear A corpus searches.

This tool turns a word, syllabic pattern, or consonantal root into annotated
tablet contexts with deterministic semantic tags from local lexica.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.normalization import lookup_in
from ..core.skeleton import extract_skeleton
from ..paths import LINEAR_A_DATA, NotInCheckout
from .cognate_search import (
    load_corpus,
    load_gordon,
    load_scholarly,
    load_yashar_mana,
    reverse_root_search,
    syllabic_grep,
)

DATA_DIR = LINEAR_A_DATA
SEPARATORS = {"", "\n", "\U00010101", "—", "–", "-"}
FRACTION_CHARS = frozenset("¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞⁄")
PARTICLE_WORDS = {"U", "DU", "KI", "RE", "A"}

VC_SIGNS = frozenset({"*310"})


def load_sign_resolution_map() -> dict[str, str]:
    """Build a map from star-numbered signs to resolved phonemic display names.

    Reads sign_values.json and converts each resolved sign (*34, *118, etc.)
    to its phonemic syllable value (QI, ṬA, etc.).  Only signs with
    confidence >= 0.5 are included.  Returns e.g. {"*34": "QI", "*118": "ṬA"}.
    """
    path = DATA_DIR / "sign_values.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    sign_map: dict[str, str] = {}
    for key, entry in data.get("signs", {}).items():
        if not key.startswith("*"):
            continue
        primary = entry.get("primary", {})
        c = primary.get("consonant") or ""
        v = primary.get("vowel") or ""
        conf = primary.get("confidence", 0)
        if conf < 0.5:
            continue
        if c and v:
            if key in VC_SIGNS:
                display = v.upper() + c.upper()
            else:
                display = c.upper() + v.upper()
        elif v:
            display = v.upper()
        elif c:
            display = c.upper()
        else:
            continue
        sign_map[key] = display
    return sign_map


def resolve_word_signs(word: str, sign_map: dict[str, str]) -> str:
    """Replace star-numbered signs in a hyphenated word with phonemic values."""
    if not sign_map or "*" not in word:
        return word
    parts = word.split("-")
    resolved_parts = [sign_map.get(p, p) for p in parts]
    return "-".join(resolved_parts)


GORDON_CATEGORIES = {
    "divine": "DIVINE",
    "personal-nws": "PN",
    "personal-egyptian": "PN",
    "personal-hurrian": "PN",
    "religious": "RITUAL",
    "vocabulary": "VOCAB",
    "verbal": "VERB",
    "place": "TOPONYM",
}

LEXICON_CATEGORIES = {
    "divine_name": "DIVINE",
    "personal_name": "PN",
    "ritual": "RITUAL",
    "vocabulary": "VOCAB",
    "verb": "VERB",
    "particle": "PARTICLE",
    "grammar": "GRAMMAR",
    "toponym": "TOPONYM",
}

DISCLAIMER = (
    "⚠ Readings follow di Mino's Semitic decipherment. Confidence tiers apply."
)


def load_lexicon_entries() -> dict[str, dict[str, Any]]:
    """Load known reading entries keyed by Linear A word."""
    path = DATA_DIR / "lexicon.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: dict[str, dict[str, Any]] = {}
    for entry in data.get("entries", []):
        word = entry.get("word")
        if isinstance(word, str) and word:
            entries[word] = entry
    return entries


def is_separator(word: Any) -> bool:
    """Return True for corpus separators and line dividers."""
    return not isinstance(word, str) or word.strip() in SEPARATORS


def is_numeral(word: str) -> bool:
    """Detect numeric tokens, including Unicode fractions."""
    compact = word.strip()
    if not compact:
        return False
    if any(ch.isalpha() for ch in compact):
        return False
    if compact.isdigit():
        return True
    return any(ch.isdigit() or ch in FRACTION_CHARS - {"⁄"} for ch in compact) and all(
        ch.isdigit() or ch in FRACTION_CHARS for ch in compact
    )


def _semantic_category(source_category: str | None, source: str) -> str:
    if source == "lexicon":
        # Lexicon entries without a display label still have readings; UNKNOWN is kept for unmatched words.
        return LEXICON_CATEGORIES.get(source_category or "", "LEX")
    if not source_category:
        return "UNKNOWN"
    return GORDON_CATEGORIES.get(source_category, "UNKNOWN")


def _description(entry: dict[str, Any], source: str) -> str:
    reading = entry.get("reading") or entry.get("semitic") or entry.get("gordonTranslit") or ""
    meaning = entry.get("meaning") or ""
    confidence = entry.get("confidence") or ""
    pieces = []
    if reading:
        pieces.append(str(reading))
    if meaning:
        pieces.append(f'"{meaning}"')
    if confidence:
        pieces.append(f"({confidence})")
    if not pieces and source:
        pieces.append(source)
    return " ".join(pieces)


def annotate_word(
    word: str,
    gordon: dict[str, dict[str, Any]],
    ym: dict[str, dict[str, Any]],
    scholarly: dict[str, dict[str, Any]],
    lexicon_entries: dict[str, dict[str, Any]],
    matched_words: set[str] | None = None,
    sign_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Annotate one corpus token with category, reading, and skeleton."""
    lexicon_lookup = lexicon_entries
    resolved = resolve_word_signs(word, sign_map or {})

    annotation: dict[str, Any] = {
        "word": word,
        "resolved_word": resolved if resolved != word else None,
        "category": "UNKNOWN",
        "source": None,
        "reading": "",
        "meaning": "",
        "confidence": "",
        "skeleton": extract_skeleton(word),
        "is_match": word in (matched_words or set()),
    }

    if is_numeral(word):
        annotation.update({
            "category": "NUM",
            "source": "detected",
            "reading": word,
            "meaning": "numeral",
            "description": "numeral",
            "skeleton": "",
        })
        return annotation

    lex = lookup_in(lexicon_lookup, word)
    if lex:
        annotation.update({
            "category": _semantic_category(lex.get("category"), "lexicon"),
            "source": "lexicon",
            "reading": lex.get("reading", ""),
            "meaning": lex.get("meaning", ""),
            "confidence": lex.get("confidence", ""),
            "description": _description(lex, "lexicon"),
        })
        return annotation

    if word in PARTICLE_WORDS:
        annotation.update({
            "category": "PARTICLE",
            "source": "particle",
            "reading": word.lower(),
            "meaning": "particle",
            "description": "particle",
        })
        return annotation

    for source, entries in (
        ("gordon", gordon),
        ("yasharMana", ym),
        ("scholarly", scholarly),
    ):
        match = lookup_in(entries, word)
        if match:
            annotation.update({
                "category": _semantic_category(match.get("category"), source),
                "source": source,
                "reading": match.get("semitic") or match.get("gordonTranslit", ""),
                "meaning": match.get("meaning", ""),
                "description": _description(match, source),
            })
            return annotation

    if annotation["skeleton"]:
        annotation["description"] = annotation["skeleton"]
    return annotation


def _iter_words(doc: dict[str, Any]) -> list[str]:
    words = doc.get("transliteratedWords", [])
    if not isinstance(words, list):
        return []
    return [w for w in words if not is_separator(w)]


def _site_matches(doc: dict[str, Any], site: str | None) -> bool:
    if not site:
        return True
    return str(doc.get("site", "")).lower() == site.lower()


def _word_matches(target: str, corpus: dict[str, dict[str, Any]], site: str | None) -> dict[str, set[str]]:
    matches: dict[str, set[str]] = {}
    for tablet_id, doc in corpus.items():
        if not _site_matches(doc, site):
            continue
        matched = {word for word in _iter_words(doc) if word == target}
        if matched:
            matches[tablet_id] = matched
    return matches


def _syllabic_matches(target: str, corpus: dict[str, dict[str, Any]], site: str | None, limit: int) -> dict[str, set[str]]:
    result = syllabic_grep(target, top_n=max(limit * 20, 500))
    matches: dict[str, set[str]] = defaultdict(set)
    for hit in result.get("hits", []):
        tablet_id = hit.get("tablet")
        doc = corpus.get(tablet_id, {})
        if tablet_id and _site_matches(doc, site):
            matches[tablet_id].add(hit.get("word", ""))
    return dict(matches)


def _root_matches(
    target: str,
    corpus: dict[str, dict[str, Any]],
    site: str | None,
    limit: int,
    max_dist: float | None,
) -> dict[str, set[str]]:
    result = reverse_root_search(target, max_distance=max_dist, top_n=max(limit * 20, 500))
    matches: dict[str, set[str]] = defaultdict(set)
    for match in result.get("matches", []):
        word = match.get("word", "")
        for tablet_id in match.get("inscriptions", []):
            doc = corpus.get(tablet_id, {})
            if _site_matches(doc, site):
                matches[tablet_id].add(word)
    return dict(matches)


def find_tablets(
    target: str,
    kind: str,
    corpus: dict[str, dict[str, Any]],
    *,
    site: str | None = None,
    max_dist: float | None = None,
    limit: int = 50,
) -> dict[str, list[str]]:
    """Find tablets and matched words for the requested search kind."""
    if kind == "auto":
        if "-" in target:
            matches = _word_matches(target, corpus, site)
            matches = matches or _syllabic_matches(target, corpus, site, limit)
        else:
            matches = _root_matches(target, corpus, site, limit, max_dist)
    elif kind == "word":
        matches = _word_matches(target, corpus, site)
    elif kind == "syllabic":
        matches = _syllabic_matches(target, corpus, site, limit)
    elif kind == "root":
        matches = _root_matches(target, corpus, site, limit, max_dist)
    else:
        raise ValueError(f"Unsupported search kind: {kind}")
    return {tablet_id: sorted(words) for tablet_id, words in matches.items()}


def _word_is_match(word: str, target: str, kind: str, matched_words: set[str]) -> bool:
    if word in matched_words:
        return True
    if kind == "syllabic":
        if "-" not in word:
            return False
        patterns = [p.strip().upper() for p in target.split(",")]
        return any(pattern and pattern in word.upper() for pattern in patterns)
    if kind == "word":
        return word == target
    return False


def annotate_tablet(
    tablet_id: str,
    doc: dict[str, Any],
    matched_words: set[str],
    target: str,
    kind: str,
    gordon: dict[str, dict[str, Any]],
    ym: dict[str, dict[str, Any]],
    scholarly: dict[str, dict[str, Any]],
    lexicon_entries: dict[str, dict[str, Any]],
    *,
    compact: bool = False,
    sign_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Annotate every non-separator word in a tablet."""
    words = []
    categories: Counter[str] = Counter()
    position = 0
    for word in _iter_words(doc):
        annotation = annotate_word(word, gordon, ym, scholarly, lexicon_entries, matched_words, sign_map)
        annotation["is_match"] = _word_is_match(word, target, kind, matched_words)
        position += 1
        annotation["position"] = position
        if compact and annotation["source"] is None and not annotation["is_match"]:
            continue
        words.append(annotation)
        categories[annotation["category"]] += 1

    return {
        "tablet_id": tablet_id,
        "site": doc.get("site", ""),
        "support": doc.get("support", ""),
        "context": doc.get("context", ""),
        "findspot": doc.get("findspot", ""),
        "matched_words": sorted(matched_words),
        "words": words,
        "category_distribution": dict(categories),
    }


def co_occurrence_summary(annotated_tablets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate non-target, non-numeral co-occurrences across matched tablets."""
    by_word: dict[str, dict[str, Any]] = {}
    for tablet in annotated_tablets:
        tablet_id = tablet["tablet_id"]
        for word in tablet["words"]:
            if word.get("is_match") or word.get("category") == "NUM":
                continue
            key = word["word"]
            entry = by_word.setdefault(key, {
                "word": key,
                "category": word.get("category", "UNKNOWN"),
                "description": word.get("description") or word.get("skeleton", ""),
                "tablets": set(),
                "occurrences": 0,
            })
            entry["tablets"].add(tablet_id)
            entry["occurrences"] += 1

    summary = []
    for entry in by_word.values():
        tablets = sorted(entry["tablets"])
        summary.append({
            "word": entry["word"],
            "category": entry["category"],
            "description": entry["description"],
            "tablet_count": len(tablets),
            "occurrences": entry["occurrences"],
            "tablets": tablets,
        })
    summary.sort(key=lambda x: (-x["tablet_count"], -x["occurrences"], x["word"]))
    return summary


def build_context_search(
    target: str,
    kind: str,
    *,
    site: str | None = None,
    max_dist: float | None = None,
    limit: int = 50,
    compact: bool = False,
    include_co_occurrence: bool = False,
    raw_signs: bool = False,
) -> dict[str, Any]:
    """Run search and annotation, returning a serializable result object."""
    corpus = load_corpus()
    gordon = load_gordon()
    ym = load_yashar_mana()
    scholarly = load_scholarly()
    lexicon_entries = load_lexicon_entries()
    sign_map = {} if raw_signs else load_sign_resolution_map()

    resolved_kind = kind
    if kind == "auto":
        if "-" in target:
            exact_matches = _word_matches(target, corpus, site)
            if exact_matches:
                found = exact_matches
                resolved_kind = "word"
            else:
                found = _syllabic_matches(target, corpus, site, limit)
                resolved_kind = "syllabic"
        else:
            found = _root_matches(target, corpus, site, limit, max_dist)
            resolved_kind = "root"
    else:
        found_lists = find_tablets(target, kind, corpus, site=site, max_dist=max_dist, limit=limit)
        found = {tablet_id: set(words) for tablet_id, words in found_lists.items()}
    tablet_ids = [t for t in sorted(found) if t in corpus][:limit]

    tablets = [
        annotate_tablet(
            tablet_id,
            corpus[tablet_id],
            found[tablet_id],
            target,
            resolved_kind,
            gordon,
            ym,
            scholarly,
            lexicon_entries,
            compact=compact,
            sign_map=sign_map,
        )
        for tablet_id in tablet_ids
    ]

    search_info = {
        "target": target,
        "kind": kind,
        "resolved_kind": resolved_kind,
        "tablet_count": len({t for t in found if t in corpus}),
        "displayed_tablet_count": len(tablets),
        "site_count": len({corpus[t].get("site", "") for t in found if t in corpus and corpus[t].get("site", "")}),
        "site_filter": site,
        "limit": limit,
        "max_dist": max_dist,
        "sign_resolution": not raw_signs,
        "resolved_signs": len(sign_map),
    }
    result = {"search": search_info, "tablets": tablets}
    if include_co_occurrence:
        result["co_occurrences"] = co_occurrence_summary(tablets)
    return result


def _category_line(categories: dict[str, int]) -> str:
    if not categories:
        return "Categories: none"
    parts = [f"{cat} ×{count}" for cat, count in sorted(categories.items())]
    return "Categories: " + ", ".join(parts)


def _word_detail(word: dict[str, Any]) -> str:
    if word.get("source") is None:
        return word.get("skeleton") or word.get("description") or ""
    return word.get("description") or word.get("skeleton") or ""


def format_report(result: dict[str, Any]) -> str:
    """Format a human-readable contextual report."""
    search = result["search"]
    header = (
        f'CONTEXT SEARCH: "{search["target"]}" '
        f'({search["kind"]} → {search["resolved_kind"]}) — '
        f'{search["tablet_count"]} tablets, {search["site_count"]} sites'
    )
    lines = ["=" * 72, header, "=" * 72, ""]

    if not result["tablets"]:
        lines.append("No matching tablets found.")
    for tablet in result["tablets"]:
        site = tablet.get("site") or "unknown site"
        support = tablet.get("support") or "unknown support"
        lines.append(f"--- {tablet['tablet_id']} ({site}, {support}) ---")
        lines.append("")
        for word in tablet["words"]:
            marker = "►" if word.get("is_match") else " "
            detail = _word_detail(word)
            suffix = "  ← MATCH" if word.get("is_match") else ""
            tag = f"[{word['category']}]"
            display = word.get("resolved_word") or word["word"]
            raw_note = f"  ({word['word']})" if word.get("resolved_word") else ""
            lines.append(
                f"{word['position']:>4}. {marker}{display:<24} "
                f"{tag:<11} {detail}{suffix}{raw_note}"
            )
        lines.append("")
        lines.append(f"  {_category_line(tablet['category_distribution'])}")
        lines.append("")

    co_occurrences = result.get("co_occurrences", [])
    if co_occurrences:
        lines.append("Co-occurrence Summary")
        lines.append("-" * 72)
        for entry in co_occurrences[:50]:
            desc = entry.get("description", "")
            tag = f"[{entry['category']}]"
            lines.append(
                f"{entry['word']:<24} {tag:<11} "
                f"{entry['tablet_count']:>3} tablets  {entry['occurrences']:>3} occ.  {desc}"
            )
        lines.append("")

    lines.append(DISCLAIMER)
    return "\n".join(lines)


def format_json(result: dict[str, Any]) -> str:
    """Format result as stable JSON."""
    return json.dumps(result, ensure_ascii=False, indent=2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Contextual neighborhood analysis for Linear A corpus")
    parser.add_argument("target", help="Search term, syllabic pattern, or consonantal root")
    parser.add_argument("--kind", choices=["auto", "word", "syllabic", "root"], default="auto")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--json", action="store_true", help="Shorthand for --format json")
    parser.add_argument("--co-occur", action="store_true", help="Append cross-tablet co-occurrence summary")
    parser.add_argument("--compact", action="store_true", help="Omit UNKNOWN words in table output")
    parser.add_argument("--site", help="Restrict to tablets from a specific site")
    parser.add_argument("--max-dist", type=float, default=None, help="Max normalized distance for root mode")
    parser.add_argument("-n", "--limit", type=int, default=50, help="Max tablets to display")
    parser.add_argument("--raw-signs", action="store_true", help="Show raw sign numbers (disable *34→QI resolution)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    args = parse_args(argv)
    output_format = "json" if args.json else args.format
    try:
        result = build_context_search(
            args.target,
            args.kind,
            site=args.site,
            max_dist=args.max_dist,
            limit=args.limit,
            compact=args.compact and output_format == "table",
            include_co_occurrence=args.co_occur,
            raw_signs=args.raw_signs,
        )
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    if output_format == "json":
        print(format_json(result))
    else:
        print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
