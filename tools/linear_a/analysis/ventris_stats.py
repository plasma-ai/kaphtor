#!/usr/bin/env python3
"""Sign census and statistical foundation for the Ventris Engine.

Analyzes positional frequency, bigrams, hapax legomena, and site distribution
across the full Linear A corpus. This is Ventris's Step 1: know your signs
before you decode them.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"


def load_corpus() -> dict:
    return json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))


def _is_sign(token: str) -> bool:
    """True if token is a syllabographic sign (not ideogram, numeral, or separator)."""
    if not token or token == "\n":
        return False
    # Skip pure Unicode characters (ideograms rendered as Unicode)
    if len(token) == 1 and ord(token) > 127:
        return False
    # Skip numeric tokens
    if token.replace(".", "").replace("/", "").isdigit():
        return False
    # Skip known ideogram abbreviations
    ideograms = {"GRA", "OLE", "VIN", "FIC", "CYP", "ARE", "AUR", "BOS",
                 "CAP", "CER", "EQU", "FAR", "HOR", "NI", "OVI", "SUS",
                 "TELA", "LUNA", "SOL", "LANA", "VAS"}
    upper = token.upper().rstrip("+").lstrip("*")
    if upper in ideograms:
        return False
    # Skip tokens starting with * followed by digits (undeciphered signs)
    return not (token.startswith("*") and any(c.isdigit() for c in token))


def extract_words(corpus: dict) -> list[tuple[str, str, list[str]]]:
    """Extract (inscription_id, site, [sign_list]) for each word in corpus.

    Each entry in transliteratedWords is either a full hyphenated word (e.g. "KU-RO")
    or a separator ("\n"). We split hyphenated words into their component syllables.
    """
    results = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        words_raw = doc.get("transliteratedWords", [])
        for token in words_raw:
            if not isinstance(token, str) or not token.strip() or token == "\n":
                continue
            # 𐝫 (U+1076B) lacuna marker: damaged tokens would shed their broken
            # signs and register phantom short words, so they are excluded
            if "\U0001076B" in token:
                continue
            # Each token is a complete word — split on hyphens to get signs
            signs = [s.upper() for s in token.split("-") if s.strip()]
            # Filter: keep only tokens where at least one component is a recognizable sign
            valid_signs = [s for s in signs if _is_sign(s)]
            if valid_signs:
                results.append((doc_id, site, valid_signs))
    return results


def sign_frequency(words: list[tuple[str, str, list[str]]]) -> dict:
    """Per-sign frequency and positional distribution."""
    total = Counter()
    initial = Counter()
    final = Counter()
    medial = Counter()

    for _, _, signs in words:
        if not signs:
            continue
        for i, s in enumerate(signs):
            total[s] += 1
            if i == 0:
                initial[s] += 1
            elif i == len(signs) - 1:
                final[s] += 1
            else:
                medial[s] += 1

    result = {}
    for sign in sorted(total, key=lambda x: -total[x]):
        t = total[sign]
        result[sign] = {
            "total": t,
            "initial": initial.get(sign, 0),
            "final": final.get(sign, 0),
            "medial": medial.get(sign, 0),
            "initial_pct": round(initial.get(sign, 0) / t * 100, 1) if t else 0,
            "final_pct": round(final.get(sign, 0) / t * 100, 1) if t else 0,
        }
    return result


def bigrams(words: list[tuple[str, str, list[str]]], top_n: int = 30) -> list[tuple[str, int]]:
    """Most common sign-pairs."""
    counter = Counter()
    for _, _, signs in words:
        for i in range(len(signs) - 1):
            pair = f"{signs[i]}-{signs[i+1]}"
            counter[pair] += 1
    return counter.most_common(top_n)


def hapax_legomena(words: list[tuple[str, str, list[str]]]) -> list[str]:
    """Words appearing exactly once in the corpus."""
    word_counter = Counter()
    for _, _, signs in words:
        key = "-".join(signs)
        word_counter[key] += 1
    return sorted(k for k, v in word_counter.items() if v == 1)


def site_distribution(words: list[tuple[str, str, list[str]]]) -> dict:
    """Per-sign site distribution — which signs are site-specific vs. universal."""
    sign_sites: dict[str, Counter] = defaultdict(Counter)
    for _, site, signs in words:
        for s in signs:
            sign_sites[s][site] += 1
    result = {}
    for sign in sorted(sign_sites):
        sites = dict(sign_sites[sign].most_common())
        result[sign] = {
            "sites": sites,
            "site_count": len(sites),
            "is_universal": len(sites) >= 3,
        }
    return result


def word_frequency(words: list[tuple[str, str, list[str]]]) -> list[tuple[str, int]]:
    """Most frequent words in the corpus."""
    counter = Counter()
    for _, _, signs in words:
        key = "-".join(signs)
        counter[key] += 1
    return counter.most_common(50)


def single_sign_profile(words: list[tuple[str, str, list[str]]], sign: str) -> dict:
    """Detailed profile for a single sign."""
    sign = sign.upper()
    freq = sign_frequency(words)
    if sign not in freq:
        return {"error": f"Sign {sign} not found in corpus"}
    info = freq[sign]
    sites = site_distribution(words).get(sign, {})

    # Co-occurring signs (bigram partners)
    left_context = Counter()
    right_context = Counter()
    for _, _, signs_list in words:
        for i, s in enumerate(signs_list):
            if s == sign:
                if i > 0:
                    left_context[signs_list[i-1]] += 1
                if i < len(signs_list) - 1:
                    right_context[signs_list[i+1]] += 1

    return {
        "sign": sign,
        **info,
        "sites": sites.get("sites", {}),
        "site_count": sites.get("site_count", 0),
        "left_context": dict(left_context.most_common(10)),
        "right_context": dict(right_context.most_common(10)),
    }


def format_report(words, args) -> str:
    """Format human-readable report."""
    lines = []
    total_words = len(words)
    unique_words = len({"-".join(s) for _, _, s in words})
    all_signs = set()
    for _, _, signs in words:
        all_signs.update(signs)

    lines.append("Linear A Corpus Statistics")
    lines.append(f"{'='*50}")
    lines.append(f"Total word tokens:  {total_words:,}")
    lines.append(f"Unique word types:  {unique_words:,}")
    lines.append(f"Unique signs:       {len(all_signs):,}")
    lines.append("")

    if args.sign:
        profile = single_sign_profile(words, args.sign)
        if "error" in profile:
            lines.append(profile["error"])
        else:
            lines.append(f"Profile: {profile['sign']}")
            lines.append(f"  Total: {profile['total']}")
            lines.append(f"  Initial: {profile['initial']} ({profile['initial_pct']}%)")
            lines.append(f"  Final: {profile['final']} ({profile['final_pct']}%)")
            lines.append(f"  Medial: {profile['medial']}")
            lines.append(f"  Sites ({profile['site_count']}): {profile['sites']}")
            lines.append(f"  Left context: {profile['left_context']}")
            lines.append(f"  Right context: {profile['right_context']}")
        return "\n".join(lines)

    if args.bigrams:
        top_n = args.top or 30
        lines.append(f"Top {top_n} Bigrams")
        lines.append(f"{'-'*40}")
        for pair, count in bigrams(words, top_n):
            lines.append(f"  {pair:<20} {count:>5}")
        return "\n".join(lines)

    if args.hapax:
        hap = hapax_legomena(words)
        lines.append(f"Hapax Legomena ({len(hap)} words)")
        lines.append(f"{'-'*40}")
        for w in hap[:50]:
            lines.append(f"  {w}")
        if len(hap) > 50:
            lines.append(f"  ... and {len(hap) - 50} more")
        return "\n".join(lines)

    if args.words:
        lines.append("Top 50 Most Frequent Words")
        lines.append(f"{'-'*40}")
        for word, count in word_frequency(words):
            lines.append(f"  {word:<30} {count:>5}")
        return "\n".join(lines)

    # Default: full frequency report
    freq = sign_frequency(words)
    lines.append("Sign Frequency Table")
    lines.append(f"{'Sign':<10} {'Total':>6} {'Init%':>6} {'Final%':>7} {'Medial':>7}")
    lines.append(f"{'-'*40}")
    for sign, info in list(freq.items())[:40]:
        lines.append(
            f"  {sign:<8} {info['total']:>6} {info['initial_pct']:>5.1f}% "
            f"{info['final_pct']:>5.1f}% {info['medial']:>6}"
        )
    if len(freq) > 40:
        lines.append(f"  ... and {len(freq) - 40} more signs")

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
    parser = argparse.ArgumentParser(description="Linear A sign statistics")
    parser.add_argument("--sign", help="Profile a single sign")
    parser.add_argument("--bigrams", action="store_true", help="Show top bigrams")
    parser.add_argument("--hapax", action="store_true", help="List hapax legomena")
    parser.add_argument("--words", action="store_true", help="Show most frequent words")
    parser.add_argument("--top", type=int, help="Number of results for bigrams")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    corpus = load_corpus()
    words = extract_words(corpus)

    if args.json:
        if args.sign:
            print(json.dumps(single_sign_profile(words, args.sign), indent=2))
        elif args.bigrams:
            print(json.dumps(bigrams(words, args.top or 30), indent=2))
        elif args.hapax:
            print(json.dumps(hapax_legomena(words), indent=2))
        elif args.words:
            print(json.dumps(word_frequency(words), indent=2))
        else:
            print(json.dumps({
                "frequency": sign_frequency(words),
                "site_distribution": site_distribution(words),
                "corpus_size": {"tokens": len(words), "types": len({"-".join(s) for _, _, s in words})},
            }, indent=2))
    else:
        print(format_report(words, args))


if __name__ == "__main__":
    sys.exit(main())
