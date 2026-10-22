#!/usr/bin/env python3
"""Query the Eteocretan inscription and word analysis databases.

Eteocretan = alphabetic Greek texts from Crete (7th-3rd c. BCE) preserving
the pre-Greek Minoan language. Cross-references words against the Linear A
lexicon to identify root continuity across 800+ years.

Examples:
  eteocretan_lookup.py --stats
  eteocretan_lookup.py --inscription ETEOCRETAN_DREROS_1
  eteocretan_lookup.py --inscription all
  eteocretan_lookup.py --word IHIA
  eteocretan_lookup.py --site Dreros
  eteocretan_lookup.py --bilingual
  eteocretan_lookup.py --la-cognates
  eteocretan_lookup.py --la-cognates --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

INSCRIPTIONS_FILE = LINEAR_A_DATA / "eteocretan_inscriptions.json"
WORDS_FILE = LINEAR_A_DATA / "eteocretan_word_analysis.json"
LEXICON_FILE = LINEAR_A_DATA / "lexicon.json"


def load_inscriptions() -> dict:
    return json.loads(require(INSCRIPTIONS_FILE, INSCRIPTIONS_FILE.name).read_text(encoding="utf-8"))


def load_words() -> dict:
    return json.loads(require(WORDS_FILE, WORDS_FILE.name).read_text(encoding="utf-8"))


def load_lexicon_roots() -> dict[str, list[dict]]:
    """Build root -> [entry] map from lexicon.json; empty when the lexicon is not in the checkout."""
    if not LEXICON_FILE.exists():
        return {}
    lex = json.loads(LEXICON_FILE.read_text(encoding="utf-8"))
    roots: dict[str, list[dict]] = {}
    for e in lex.get("entries", []):
        if e.get("confidence") == "REJECTED":
            continue
        r = e.get("root") or ""
        if not r:
            continue
        roots.setdefault(r, []).append({
            "linear_a": e.get("linear_a", ""),
            "meaning": e.get("meaning", ""),
            "confidence": e.get("confidence", ""),
        })
    return roots


def normalize_root(raw: str) -> str:
    """Strip decorations to get bare consonantal root for matching."""
    s = raw.replace("√", "").strip().lstrip("*")
    s = re.sub(r"\(.*?\)", "", s).strip()
    return s.split("/")[0].strip().split()[0] if s else ""


def find_lexicon_matches(root_field: str, lex_roots: dict[str, list[dict]]) -> list[dict]:
    """Find lexicon entries whose root matches the Eteocretan word's root."""
    if not root_field:
        return []
    if root_field in lex_roots:
        return lex_roots[root_field]
    norm = normalize_root(root_field)
    if not norm:
        return []
    matches = []
    for lr, entries in lex_roots.items():
        lr_norm = normalize_root(lr)
        if lr_norm and lr_norm == norm:
            matches.extend(entries)
    return matches


def is_contaminated(w: dict) -> bool:
    return w.get("status") == "CONTAMINATED_FORGERY"


def fmt_inscription(insc: dict) -> str:
    status = insc.get("status", "?")
    prefix = "⚠ PROVEN FAKE — " if status == "PROVEN_FAKE" else ""
    lines = [
        f"  {prefix}{insc['id']}  ({insc.get('common_name', '')})",
        f"  Site: {insc.get('site', '?')}   Date: {insc.get('date', '?')}",
        f"  Script: {insc.get('script', '?')}   Direction: {insc.get('direction', '?')}",
        f"  Status: {status}   Relation to LA: {insc.get('relationship_to_linear_a', '?')}",
    ]
    if status == "PROVEN_FAKE" and insc.get("forgery_evidence"):
        ev = insc["forgery_evidence"]
        lines.append(f"  FORGERY: debunked by {ev.get('debunker', '?')} ({ev.get('publication', '?')})")
        lines.append(f"    {ev.get('impact', '')[:150]}")
    if insc.get("gordon_word_readings"):
        lines.append("  Gordon readings:")
        for w in insc["gordon_word_readings"]:
            lines.append(f"    {w['form']:12s}  {w.get('meaning',''):30s}  [{w.get('constraint','')}]")
    if insc.get("notes"):
        lines.append(f"  Notes: {insc['notes']}")
    return "\n".join(lines)


def fmt_word(w: dict, la_match: list[dict] | None = None) -> str:
    tag = " [QUARANTINED — source is proven fake]" if is_contaminated(w) else ""
    lines = [
        f"  {w['form']:14s}  {w.get('gordon_meaning',''):30s}  [{w.get('constraint_type','')}]{tag}",
        f"    Root: {w.get('root', '?')}   Site: {w.get('site', '?')}   Inscription: {w.get('inscription_id', '?')}",
    ]
    if w.get("forgery_note"):
        lines.append(f"    FORGERY: {w['forgery_note'][:120]}")
    if la_match:
        for m in la_match[:3]:
            lines.append(
                f"    LA match: {m['linear_a'] or '(logogram)'} = {m['meaning'][:50]} ({m['confidence']})"
            )
    return "\n".join(lines)


def print_stats(inscriptions: list[dict], words: list[dict], lex_roots: dict) -> None:
    valid_inscs = [i for i in inscriptions if i.get("status") != "PROVEN_FAKE"]
    fake_inscs = [i for i in inscriptions if i.get("status") == "PROVEN_FAKE"]
    valid_words = [w for w in words if not is_contaminated(w)]
    quarantined = [w for w in words if is_contaminated(w)]

    print(f"Eteocretan Corpus — {len(inscriptions)} records ({len(valid_inscs)} valid, {len(fake_inscs)} proven fake)")
    print(f"  Word analysis: {len(words)} total ({len(valid_words)} valid, {len(quarantined)} quarantined)")
    print("=" * 65)

    sites: dict[str, int] = {}
    for i in valid_inscs:
        s = i.get("site", "unknown")
        sites[s] = sites.get(s, 0) + 1
    print("By site (valid inscriptions):")
    for s, n in sorted(sites.items(), key=lambda x: -x[1]):
        print(f"  {s:<30s}  {n}")

    if fake_inscs:
        print("Proven fakes:")
        for i in fake_inscs:
            print(f"  {i['id']}  ({i.get('forgery_evidence', {}).get('debunker', '?')})")

    constraints: dict[str, int] = {}
    for w in valid_words:
        ct = w.get("constraint_type", "unknown")
        constraints[ct] = constraints.get(ct, 0) + 1
    print("By constraint type (valid words):")
    for ct, n in sorted(constraints.items(), key=lambda x: -x[1]):
        print(f"  {ct:<30s}  {n}")

    word_sites: dict[str, int] = {}
    for w in valid_words:
        s = w.get("site", "unknown")
        word_sites[s] = word_sites.get(s, 0) + 1
    print("By site (valid words):")
    for s, n in sorted(word_sites.items(), key=lambda x: -x[1]):
        print(f"  {s:<30s}  {n}")

    la_count = sum(1 for w in valid_words if find_lexicon_matches(w.get("root", ""), lex_roots))
    unique_forms = len({w["form"] for w in valid_words})
    print(f"\nUnique word forms (valid): {unique_forms}")
    print(f"Words with Linear A lexicon root matches: {la_count}/{len(valid_words)} (excluding quarantined)")
    print(f"Lexicon entries with a root: {sum(len(v) for v in lex_roots.values())}")

    if quarantined:
        print(f"\nQuarantined words ({len(quarantined)}) — source inscription proven fake:")
        for w in quarantined:
            print(f"  {w['form']:14s}  [{w.get('constraint_type', '')}]  from {w.get('inscription_id', '?')}")


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Query Eteocretan inscriptions and word analysis")
    parser.add_argument("--inscription", metavar="ID", help="Show inscription by ID ('all' for all)")
    parser.add_argument("--word", metavar="FORM", help="Lookup word (case-insensitive partial match)")
    parser.add_argument("--site", metavar="SITE", help="Filter inscriptions/words by site")
    parser.add_argument("--bilingual", action="store_true", help="Show only bilingual-constrained words")
    parser.add_argument("--la-cognates", action="store_true", help="Show words with Linear A lexicon root matches")
    parser.add_argument("--stats", action="store_true", help="Summary statistics")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    if not any([args.inscription, args.word, args.site, args.bilingual, args.la_cognates, args.stats]):
        parser.print_help()
        sys.exit(0)

    insc_data = load_inscriptions()
    word_data = load_words()
    lex_roots = load_lexicon_roots()

    inscriptions = insc_data.get("inscriptions", [])
    words = word_data.get("words", [])

    if args.stats:
        if args.json:
            valid_inscs = [i for i in inscriptions if i.get("status") != "PROVEN_FAKE"]
            fake_inscs = [i for i in inscriptions if i.get("status") == "PROVEN_FAKE"]
            valid_words = [w for w in words if not is_contaminated(w)]
            quarantined = [w for w in words if is_contaminated(w)]
            sites = {}
            for i in valid_inscs:
                s = i.get("site", "unknown")
                sites[s] = sites.get(s, 0) + 1
            constraints = {}
            for w in valid_words:
                ct = w.get("constraint_type", "unknown")
                constraints[ct] = constraints.get(ct, 0) + 1
            la_count = sum(1 for w in valid_words if find_lexicon_matches(w.get("root", ""), lex_roots))
            print(json.dumps({
                "inscription_count": len(inscriptions),
                "valid_inscriptions": len(valid_inscs),
                "proven_fakes": len(fake_inscs),
                "word_count": len(words),
                "valid_words": len(valid_words),
                "quarantined_words": len(quarantined),
                "unique_forms_valid": len({w["form"] for w in valid_words}),
                "la_root_matches_valid": la_count,
                "sites": sites,
                "constraint_types": constraints,
            }, indent=2))
        else:
            print_stats(inscriptions, words, lex_roots)
        return

    if args.inscription:
        target = args.inscription.upper()
        if target == "ALL":
            hits = inscriptions
        else:
            hits = [i for i in inscriptions if target in i["id"].upper()]
        if args.json:
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            if not hits:
                print(f"No inscription matching '{args.inscription}'")
            for i in hits:
                print(fmt_inscription(i))
                print()
        return

    if args.word:
        pattern = args.word.upper()
        hits = [w for w in words if pattern in w["form"].upper()]
        if args.json:
            result = []
            for w in hits:
                entry = dict(w)
                entry["la_matches"] = find_lexicon_matches(w.get("root", ""), lex_roots)
                result.append(entry)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if not hits:
                print(f"No word matching '{args.word}'")
            for w in hits:
                matches = find_lexicon_matches(w.get("root", ""), lex_roots)
                print(fmt_word(w, matches))
                print()
        return

    if args.site:
        site_lower = args.site.lower()
        insc_hits = [i for i in inscriptions if site_lower in i.get("site", "").lower()]
        word_hits = [w for w in words if site_lower in w.get("site", "").lower()]
        if args.json:
            print(json.dumps({"inscriptions": insc_hits, "words": word_hits}, indent=2, ensure_ascii=False))
        else:
            if not insc_hits and not word_hits:
                print(f"No data for site '{args.site}'")
            if insc_hits:
                print(f"Inscriptions from {args.site}:")
                for i in insc_hits:
                    print(fmt_inscription(i))
                    print()
            if word_hits:
                print(f"Words from {args.site}:")
                for w in word_hits:
                    matches = find_lexicon_matches(w.get("root", ""), lex_roots)
                    print(fmt_word(w, matches))
                    print()
        return

    if args.bilingual:
        hits = [w for w in words if "bilingual" in w.get("constraint_type", "").lower()]
        if args.json:
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            print(f"Bilingual-constrained words ({len(hits)}):")
            for w in hits:
                matches = find_lexicon_matches(w.get("root", ""), lex_roots)
                print(fmt_word(w, matches))
                print()
        return

    if args.la_cognates:
        valid_hits = []
        quarantined_hits = []
        for w in words:
            matches = find_lexicon_matches(w.get("root", ""), lex_roots)
            if matches:
                if is_contaminated(w):
                    quarantined_hits.append((w, matches))
                else:
                    valid_hits.append((w, matches))
        if args.json:
            result = []
            for w, m in valid_hits:
                entry = dict(w)
                entry["la_matches"] = m
                result.append(entry)
            if quarantined_hits:
                for w, m in quarantined_hits:
                    entry = dict(w)
                    entry["la_matches"] = m
                    result.append(entry)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Valid words with Linear A lexicon root matches ({len(valid_hits)}):")
            for w, m in valid_hits:
                print(fmt_word(w, m))
                print()
            if quarantined_hits:
                print(f"\nQuarantined matches ({len(quarantined_hits)}) — source inscription proven fake:")
                for w, m in quarantined_hits:
                    print(fmt_word(w, m))
                    print()
        return


if __name__ == "__main__":
    sys.exit(main())
