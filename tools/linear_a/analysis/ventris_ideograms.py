#!/usr/bin/env python3
"""Ideographic semantic validation for Linear A readings.

Ventris's Step 6: test if decoded words match their adjacent ideograms.
If a word next to the GRAIN ideogram decodes as a Semitic grain word,
that's independent confirmation. If it decodes as "sea," something's wrong.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
LEXICON_PATH = DATA_DIR / "lexicon.json"

# Ideogram → semantic field mapping
# Each ideogram maps to Semitic semantic domains that would validate a reading
IDEOGRAM_SEMANTICS: dict[str, dict] = {
    "GRA": {
        "name": "grain/wheat",
        "semantic_fields": ["grain", "wheat", "barley", "cereal", "flour", "bread",
                           "harvest", "field", "sow", "reap", "thresh"],
        "semitic_roots": ["ḥṭ", "šʿr", "dgn", "qmḥ", "ḥrš", "qṣr", "kns"],
    },
    "OLE": {
        "name": "olive/oil",
        "semantic_fields": ["olive", "oil", "anoint", "press", "fat", "lamp"],
        "semitic_roots": ["šmn", "zt", "yṣq", "mšḥ"],
    },
    "VIN": {
        "name": "wine/vine",
        "semantic_fields": ["wine", "vine", "vineyard", "grape", "drink", "press",
                           "cup", "libation"],
        "semitic_roots": ["yn", "krm", "gpn", "nsk", "šqy", "štr"],
    },
    "FIC": {
        "name": "fig",
        "semantic_fields": ["fig", "fruit", "tree", "garden", "sweet"],
        "semitic_roots": ["tʔn", "pr"],
    },
    "CYP": {
        "name": "cypress/spice",
        "semantic_fields": ["spice", "aromatic", "cypress", "incense", "herb",
                           "perfume", "sacred", "offering"],
        "semitic_roots": ["qṭr", "lbn", "bśm", "smk"],
    },
    "NI": {
        "name": "fig (NI)",
        "semantic_fields": ["fig", "fruit"],
        "semitic_roots": ["tʔn"],
    },
    "AROM": {
        "name": "aromatic",
        "semantic_fields": ["spice", "aromatic", "incense", "perfume", "herb",
                           "offering", "sacred"],
        "semitic_roots": ["qṭr", "lbn", "bśm"],
    },
    "BOS": {
        "name": "cattle",
        "semantic_fields": ["cattle", "bull", "ox", "cow", "herd", "livestock"],
        "semitic_roots": ["ṯr", "bqr", "ʿgl", "ʾlp"],
    },
    "OVI": {
        "name": "sheep",
        "semantic_fields": ["sheep", "ram", "ewe", "flock", "wool", "lamb"],
        "semitic_roots": ["ṣʔn", "kbš", "ʿz"],
    },
    "CAP": {
        "name": "goat",
        "semantic_fields": ["goat", "kid", "flock", "herd"],
        "semitic_roots": ["ʿz", "gdy"],
    },
    "SUS": {
        "name": "pig",
        "semantic_fields": ["pig", "swine"],
        "semitic_roots": ["ḥzr"],
    },
    "TELA": {
        "name": "textile/cloth",
        "semantic_fields": ["cloth", "textile", "weave", "linen", "garment",
                           "wool", "spin", "dye"],
        "semitic_roots": ["ktn", "ṭwy", "ʾrg", "lbš"],
    },
    "HIDE": {
        "name": "hide/leather",
        "semantic_fields": ["hide", "skin", "leather", "tan"],
        "semitic_roots": ["ʿr", "mšk"],
    },
}

# Strip modifiers from compound ideograms: GRA+PA → GRA, OLE+KI → OLE
def _base_ideogram(token: str) -> str | None:
    parts = token.upper().split("+")
    for p in parts:
        clean = p.rstrip("₂₃₄₅").lstrip("*")
        if clean in IDEOGRAM_SEMANTICS:
            return clean
    return None


def load_data():
    corpus = json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))
    lexicon = json.loads(require(LEXICON_PATH, LEXICON_PATH.name).read_text(encoding="utf-8"))
    return corpus, lexicon


def extract_ideogram_contexts(corpus: dict) -> list[dict]:
    """Find words adjacent to ideograms in the corpus.

    Returns list of {word, ideogram, doc_id, site, position}.
    """
    results = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        tokens = doc.get("transliteratedWords", [])
        for i, token in enumerate(tokens):
            if not isinstance(token, str):
                continue
            ideo = _base_ideogram(token)
            if ideo is None:
                continue
            # Collect adjacent syllabographic words (±2 positions)
            for offset in [-2, -1, 1, 2]:
                j = i + offset
                if 0 <= j < len(tokens) and isinstance(tokens[j], str):
                    adj = tokens[j]
                    if "-" in adj and not _base_ideogram(adj):
                        results.append({
                            "word": adj.upper(),
                            "ideogram": ideo,
                            "raw_ideogram": token.upper(),
                            "doc_id": doc_id,
                            "site": site,
                            "position": "before" if offset < 0 else "after",
                        })
    return results


def score_semantic_match(
    word: str,
    reading: str,
    meaning: str,
    root: str,
    ideogram: str,
) -> dict:
    """Score how well a reading matches an ideogram's semantic field."""
    ideo_info = IDEOGRAM_SEMANTICS.get(ideogram, {})
    if not ideo_info:
        return {"match": False, "score": 0, "reason": "unknown ideogram"}

    fields = ideo_info.get("semantic_fields", [])
    roots = ideo_info.get("semitic_roots", [])
    meaning_lower = meaning.lower()

    # Check semantic field match
    field_match = any(f in meaning_lower for f in fields)

    # Check root match
    root_clean = (root or "").replace("-", "").lower()
    root_match = any(r.replace("-", "").lower() in root_clean or
                     root_clean in r.replace("-", "").lower()
                     for r in roots)

    if field_match and root_match:
        return {"match": True, "score": 1.0, "reason": "semantic + root match"}
    elif field_match:
        return {"match": True, "score": 0.7, "reason": "semantic field match"}
    elif root_match:
        return {"match": True, "score": 0.8, "reason": "root match"}
    else:
        return {"match": False, "score": 0.0, "reason": "no match"}


def validate_readings(
    contexts: list[dict],
    lexicon: dict,
) -> list[dict]:
    """For each word near an ideogram, check if its reading matches semantically."""
    known = {}
    for entry in lexicon.get("entries", []):
        word = entry.get("word", "").upper()
        if word:
            known[word] = entry

    results = []
    for ctx in contexts:
        word = ctx["word"]
        ideo = ctx["ideogram"]

        if word in known:
            entry = known[word]
            reading = entry.get("reading", "")
            meaning = entry.get("meaning", "")
            root = entry.get("root", "")
            match = score_semantic_match(word, reading, meaning, root, ideo)
            results.append({
                **ctx,
                "reading": reading,
                "meaning": meaning,
                "root": root,
                "confidence": entry.get("confidence", ""),
                "semantic_match": match,
                "status": "known",
            })
        else:
            results.append({
                **ctx,
                "reading": None,
                "meaning": None,
                "root": None,
                "confidence": None,
                "semantic_match": {"match": False, "score": 0, "reason": "not in lexicon"},
                "status": "unknown",
            })

    return results


def compute_ideogram_summary(results: list[dict]) -> dict:
    """Per-ideogram statistics."""
    by_ideo: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_ideo[r["ideogram"]].append(r)

    summary = {}
    for ideo, items in sorted(by_ideo.items()):
        known = [i for i in items if i["status"] == "known"]
        matched = [i for i in known if i["semantic_match"]["match"]]
        unique_words = len({i["word"] for i in items})
        summary[ideo] = {
            "name": IDEOGRAM_SEMANTICS.get(ideo, {}).get("name", ideo),
            "total_contexts": len(items),
            "unique_words": unique_words,
            "known_readings": len(known),
            "semantic_matches": len(matched),
            "match_rate": round(len(matched) / len(known), 2) if known else 0,
        }
    return summary


def format_report(results: list[dict], summary: dict, args) -> str:
    lines = []

    if args.summary_only:
        lines.append("Ideographic Validation Summary")
        lines.append("=" * 60)
        lines.append(f"{'Ideogram':<10} {'Name':<15} {'Contexts':>8} {'Known':>6} {'Match':>6} {'Rate':>6}")
        lines.append("-" * 60)
        for ideo, info in sorted(summary.items()):
            lines.append(
                f"  {ideo:<8} {info['name']:<15} {info['total_contexts']:>6} "
                f"{info['known_readings']:>6} {info['semantic_matches']:>6} "
                f"{info['match_rate']:>5.0%}"
            )
        total_known = sum(s["known_readings"] for s in summary.values())
        total_match = sum(s["semantic_matches"] for s in summary.values())
        lines.append("-" * 60)
        lines.append(
            f"  {'TOTAL':<8} {'':<15} "
            f"{sum(s['total_contexts'] for s in summary.values()):>6} "
            f"{total_known:>6} {total_match:>6} "
            f"{total_match/total_known:.0%}" if total_known else ""
        )
        return "\n".join(lines)

    # Full report grouped by ideogram
    lines.append("Ideographic Semantic Validation")
    lines.append("=" * 70)

    ideo_filter = args.ideogram.upper() if args.ideogram else None

    by_ideo: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_ideo[r["ideogram"]].append(r)

    for ideo in sorted(by_ideo):
        if ideo_filter and ideo != ideo_filter:
            continue
        items = by_ideo[ideo]
        info = summary.get(ideo, {})
        lines.append(f"\n{ideo} ({info.get('name', '?')}): {len(items)} contexts")
        lines.append("-" * 50)

        seen = set()
        for r in items:
            key = (r["word"], r["doc_id"])
            if key in seen:
                continue
            seen.add(key)

            if r["status"] == "known":
                match = r["semantic_match"]
                marker = "✓" if match["match"] else "✗"
                lines.append(
                    f"  {marker} {r['word']:<22} = {r['reading'] or '?':<15} "
                    f"\"{r['meaning'] or '?'}\" [{match['reason']}]"
                )
                lines.append(f"      doc={r['doc_id']} site={r['site']}")
            else:
                lines.append(f"  ? {r['word']:<22} [not in lexicon]")
                lines.append(f"      doc={r['doc_id']} site={r['site']}")

    return "\n".join(lines)


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Ideographic semantic validation")
    parser.add_argument("--summary", dest="summary_only", action="store_true",
                       help="Show summary statistics only")
    parser.add_argument("--ideogram", help="Filter to specific ideogram (e.g., GRA)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    corpus, lexicon = load_data()
    contexts = extract_ideogram_contexts(corpus)
    results = validate_readings(contexts, lexicon)
    summary = compute_ideogram_summary(results)

    if args.json:
        print(json.dumps({
            "summary": summary,
            "results": results if not args.summary_only else [],
        }, indent=2, ensure_ascii=False))
    else:
        print(format_report(results, summary, args))


if __name__ == "__main__":
    sys.exit(main())
