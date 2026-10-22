#!/usr/bin/env python3
"""Statistical analysis of sign patterns across the Linear A corpus.

Usage:
    uv run tools/linear_a/analysis/sign_analysis.py frequency --top 30
    uv run tools/linear_a/analysis/sign_analysis.py words
    uv run tools/linear_a/analysis/sign_analysis.py cooccurrence --signs KU,RO
    uv run tools/linear_a/analysis/sign_analysis.py position
    uv run tools/linear_a/analysis/sign_analysis.py distribution
    uv run tools/linear_a/analysis/sign_analysis.py unresolved
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.data_cache import sign_value_entries
from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
SIGN_VALUES_PATH = DATA_DIR / "sign_values.json"
SIGLA_MAP_PATH = DATA_DIR / "sigla-sign-map.json"


def load_corpus() -> dict[str, dict[str, Any]]:
    """Load inscription corpus."""
    return json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))


def get_all_words(corpus: dict) -> list[str]:
    """Extract all transliterated words from corpus."""
    words = []
    for entry in corpus.values():
        tw = entry.get("transliteratedWords", [])
        if isinstance(tw, list):
            words.extend(tw)
    return words


def get_all_signs(words: list[str]) -> list[str]:
    """Split words into individual signs."""
    signs = []
    for w in words:
        signs.extend(w.split("-"))
    return signs


def cmd_frequency(args: argparse.Namespace) -> None:
    """Sign frequency analysis."""
    corpus = load_corpus()
    words = get_all_words(corpus)
    signs = get_all_signs(words)

    counter = Counter(signs)
    top_n = args.top or 30

    if args.format == "json":
        print(json.dumps(counter.most_common(top_n), indent=2))
        return

    print(f"Sign Frequency (top {top_n} of {len(counter)} unique signs)")
    print(f"Total sign tokens: {len(signs)}")
    print()
    print(f"{'Sign':<10} {'Count':>8} {'%':>8}")
    print("-" * 28)
    for sign, count in counter.most_common(top_n):
        pct = count / len(signs) * 100
        print(f"{sign:<10} {count:>8} {pct:>7.2f}%")


def cmd_words(args: argparse.Namespace) -> None:
    """Word frequency analysis."""
    corpus = load_corpus()
    words = get_all_words(corpus)
    counter = Counter(words)
    top_n = args.top or 30

    if args.format == "json":
        print(json.dumps(counter.most_common(top_n), indent=2))
        return

    print(f"Word Frequency (top {top_n} of {len(counter)} unique words)")
    print(f"Total word tokens: {len(words)}")
    print()

    # Count hapax legomena
    hapax = sum(1 for c in counter.values() if c == 1)
    print(f"Hapax legomena: {hapax} ({hapax/len(counter)*100:.1f}% of vocabulary)")
    print()

    print(f"{'Word':<25} {'Count':>8}")
    print("-" * 35)
    for word, count in counter.most_common(top_n):
        print(f"{word:<25} {count:>8}")


def cmd_cooccurrence(args: argparse.Namespace) -> None:
    """Sign co-occurrence analysis."""
    corpus = load_corpus()
    words = get_all_words(corpus)

    if args.signs:
        target_signs = [s.upper() for s in args.signs.split(",")]
    else:
        # Default: top 10 most frequent signs
        signs = get_all_signs(words)
        counter = Counter(signs)
        target_signs = [s for s, _ in counter.most_common(10)]

    # Build co-occurrence matrix
    cooccur: dict[str, Counter] = {s: Counter() for s in target_signs}
    for word in words:
        word_signs = word.split("-")
        for i, s1 in enumerate(word_signs):
            if s1 in cooccur:
                for j, s2 in enumerate(word_signs):
                    if i != j:
                        cooccur[s1][s2] += 1

    if args.format == "json":
        print(json.dumps({k: dict(v.most_common(10)) for k, v in cooccur.items()}, indent=2))
        return

    print("Co-occurrence (within same word)")
    for sign in target_signs:
        top = cooccur[sign].most_common(args.top or 5)
        if top:
            pairs = ", ".join(f"{s}({c})" for s, c in top)
            print(f"  {sign}: {pairs}")


def cmd_position(args: argparse.Namespace) -> None:
    """Positional analysis — sign distribution in initial/medial/final position."""
    corpus = load_corpus()
    words = get_all_words(corpus)

    initial: Counter = Counter()
    medial: Counter = Counter()
    final: Counter = Counter()

    for word in words:
        signs = word.split("-")
        if len(signs) >= 1:
            initial[signs[0]] += 1
        if len(signs) >= 2:
            final[signs[-1]] += 1
        for s in signs[1:-1]:
            medial[s] += 1

    top_n = args.top or 15

    if args.format == "json":
        print(json.dumps({
            "initial": initial.most_common(top_n),
            "medial": medial.most_common(top_n),
            "final": final.most_common(top_n),
        }, indent=2))
        return

    print(f"Positional Distribution (top {top_n})")
    for label, counter in [("Initial", initial), ("Medial", medial), ("Final", final)]:
        print(f"\n  {label}:")
        for sign, count in counter.most_common(top_n):
            print(f"    {sign:<8} {count:>6}")


def _load_sigla_sign_map() -> dict[str, dict[str, str]]:
    """Load SigLA sign map and return Unicode char → sign info mapping."""
    sigla = json.loads(require(SIGLA_MAP_PATH, SIGLA_MAP_PATH.name).read_text(encoding="utf-8"))
    mapping: dict[str, dict[str, str]] = {}
    for s in sigla.get("signs", []):
        u_hex = s.get("unicode", "")
        if u_hex and u_hex.startswith("U+"):
            ch = chr(int(u_hex.removeprefix("U+"), 16))
            mapping[ch] = {"name": s.get("name", "?"), "ab": s.get("ab_number", "?")}
    return mapping


def _build_resolved_set() -> tuple[set[str], set[str]]:
    """Build resolved AB numbers and sign names from sign_values.json."""
    sv = json.loads(require(SIGN_VALUES_PATH, SIGN_VALUES_PATH.name).read_text(encoding="utf-8"))
    resolved_ab: set[str] = set()
    resolved_names: set[str] = set()

    for name, data in sv.get("signs", {}).items():
        resolved_names.add(name.lower())
        if isinstance(data, dict):
            for field in ("ab_number", "sign_number"):
                ab = data.get(field, "") or ""
                if ab:
                    resolved_ab.add(ab)

    rs = sv.get("resolution_summary", {})
    for entry_list in (sign_value_entries(rs, "phonemic"), sign_value_entries(rs, "logograms")):
        for entry in entry_list:
            parts = entry.split("=", 1)
            left = parts[0].strip()
            resolved_names.add(left.lower())
            if left.startswith("*"):
                num = left[1:]
                resolved_ab.add(f"AB{num}")
                resolved_ab.add(f"A{num}")
            if len(parts) > 1:
                resolved_names.add(parts[1].strip().lower())

    for name, data in sv.get("logograms", {}).items():
        if name.startswith("_"):
            continue
        resolved_names.add(name.lower())
        if isinstance(data, dict):
            for field in ("ab_number", "sign_number"):
                ab = data.get(field, "") or ""
                if ab:
                    resolved_ab.add(ab)

    return resolved_ab, resolved_names


def cmd_unresolved(args: argparse.Namespace) -> None:
    """Show unresolved signs appearing in the corpus."""
    corpus = load_corpus()
    sigla_map = _load_sigla_sign_map()
    resolved_ab, resolved_names = _build_resolved_set()

    char_counts: Counter = Counter()
    for entry in corpus.values():
        if not isinstance(entry, dict):
            continue
        for w in entry.get("words", []):
            if isinstance(w, str):
                for ch in w:
                    if 0x10600 <= ord(ch) <= 0x1077F:
                        char_counts[ch] += 1

    ab_num_re = re.compile(r"^(?:AB|A)(\d+)")

    resolved_signs: list[dict] = []
    unresolved_std: list[dict] = []
    unresolved_ext: list[dict] = []
    unmapped_signs = 0
    unmapped_occ = 0

    for ch, count in char_counts.most_common():
        info = sigla_map.get(ch)
        if not info:
            unmapped_signs += 1
            unmapped_occ += count
            continue
        ab = info["ab"]
        name = info["name"]
        row = {"ab": ab, "name": name, "count": count, "char": ch}

        if ab in resolved_ab or (len(name) > 1 and name.lower() in resolved_names):
            resolved_signs.append(row)
            continue

        m = ab_num_re.match(ab)
        ab_num = int(m.group(1)) if m else 999
        if ab_num <= 80:
            unresolved_std.append(row)
        else:
            unresolved_ext.append(row)

    total_occ = sum(char_counts.values()) - unmapped_occ
    res_occ = sum(r["count"] for r in resolved_signs)
    std_occ = sum(r["count"] for r in unresolved_std)
    ext_occ = sum(r["count"] for r in unresolved_ext)

    if args.format == "json":
        print(json.dumps({
            "resolved": {"signs": len(resolved_signs), "occurrences": res_occ},
            "unresolved_standard": {"signs": len(unresolved_std), "occurrences": std_occ,
                                    "items": unresolved_std},
            "unresolved_extended": {"signs": len(unresolved_ext), "occurrences": ext_occ,
                                    "items": unresolved_ext[:args.top] if args.top else unresolved_ext},
            "unmapped": {"signs": unmapped_signs, "occurrences": unmapped_occ},
        }, indent=2, ensure_ascii=False))
        return

    pct = res_occ / total_occ * 100 if total_occ else 0
    print(f"Resolution Gap: {len(unresolved_std)} standard syllabograms unresolved ({len(unresolved_ext)} extended)")
    print(f"Resolved: {len(resolved_signs)} signs ({res_occ:,} occurrences, {pct:.1f}%)")
    print(f"Unresolved standard (AB01-AB80): {len(unresolved_std)} signs ({std_occ:,} occurrences)")
    print(f"Unresolved extended (AB81+): {len(unresolved_ext)} signs ({ext_occ:,} occurrences)")
    print(f"Unmapped (numerals/separators): {unmapped_signs} signs ({unmapped_occ:,} occurrences)")

    if unresolved_std:
        print("\nUnresolved Standard Syllabograms:")
        for r in unresolved_std:
            print(f"  {r['ab']:<8s} {r['name']:<8s} {r['count']:>5d} occ")

    if unresolved_ext:
        top_n = args.top or 15
        print(f"\nUnresolved Extended Signs (top {top_n}):")
        for r in unresolved_ext[:top_n]:
            print(f"  {r['ab']:<8s} {r['name']:<8s} {r['count']:>5d} occ")


def cmd_distribution(args: argparse.Namespace) -> None:
    """Site distribution analysis."""
    corpus = load_corpus()

    sites: Counter = Counter()
    site_words: dict[str, int] = {}

    for name, entry in corpus.items():
        # Extract site prefix (e.g., HT from HT1, ZA from ZA1)
        site = ""
        for ch in name:
            if ch.isalpha():
                site += ch
            else:
                break
        sites[site] += 1
        tw = entry.get("transliteratedWords", [])
        word_count = len(tw) if isinstance(tw, list) else 0
        site_words[site] = site_words.get(site, 0) + word_count

    if args.format == "json":
        print(json.dumps({
            "sites": sites.most_common(),
            "words_per_site": dict(sorted(site_words.items(), key=lambda x: -x[1])),
        }, indent=2))
        return

    print(f"Site Distribution ({len(sites)} sites)")
    print()
    print(f"{'Site':<8} {'Inscriptions':>14} {'Words':>8}")
    print("-" * 32)
    for site, count in sites.most_common():
        wc = site_words.get(site, 0)
        print(f"{site:<8} {count:>14} {wc:>8}")


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Linear A sign pattern analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in [
        ("frequency", cmd_frequency, "Sign frequency analysis"),
        ("words", cmd_words, "Word frequency and hapax legomena"),
        ("cooccurrence", cmd_cooccurrence, "Sign co-occurrence within words"),
        ("position", cmd_position, "Sign positional distribution (initial/medial/final)"),
        ("distribution", cmd_distribution, "Inscription distribution by site"),
        ("unresolved", cmd_unresolved, "Unresolved signs in the corpus"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        p.add_argument("--top", "-n", type=int, help="Number of results")
        p.add_argument("--format", choices=["table", "json"], default="table")
        if name == "cooccurrence":
            p.add_argument("--signs", help="Comma-separated signs to analyze")

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
