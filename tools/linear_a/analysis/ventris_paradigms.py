#!/usr/bin/env python3
"""Morphological paradigm detection for Linear A.

Ventris's Step 3: find words sharing a stem with systematic final-sign
alternation. In Semitic morphology, case vowels (-u nom, -a acc, -i gen),
feminine -tu, and gentillic -nu produce exactly these alternation patterns.
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

from ...core.corpus_utils import extract_word_tuples
from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
MORPHEMES_PATH = DATA_DIR / "morphemes.json"
LEXICON_PATH = DATA_DIR / "lexicon.json"

# Case-vowel signs that could signal Semitic declension
CASE_ENDINGS = {
    "U": {"case": "nominative", "vowel": "u"},
    "A": {"case": "accusative", "vowel": "a"},
    "I": {"case": "genitive", "vowel": "i"},
}

# Known Semitic morphological suffixes (sign-level)
SUFFIX_PATTERNS = {
    "TE": {"function": "feminine -t", "confidence": 0.8},
    "TI": {"function": "feminine -ti", "confidence": 0.7},
    "TU": {"function": "feminine -tu (nominative)", "confidence": 0.7},
    "NA": {"function": "demonstrative -na / enclitic", "confidence": 0.7},
    "NU": {"function": "gentillic -nu", "confidence": 0.6},
    "NE": {"function": "personal name suffix / oblique", "confidence": 0.5},
    "ME": {"function": "enclitic -ma", "confidence": 0.5},
    "MA": {"function": "mimation (archaic nominative -m)", "confidence": 0.6},
    "MU": {"function": "mimation -mu (nominative variant)", "confidence": 0.5},
}


def load_data():
    corpus = json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))
    morphemes = json.loads(require(MORPHEMES_PATH, MORPHEMES_PATH.name).read_text(encoding="utf-8"))
    lexicon = json.loads(require(LEXICON_PATH, LEXICON_PATH.name).read_text(encoding="utf-8"))
    return corpus, morphemes, lexicon


def extract_word_list(corpus: dict) -> list[tuple[str, str, str]]:
    """Extract (word, site, doc_id) tuples from corpus."""
    return extract_word_tuples(corpus)


def find_paradigms(words: list[tuple[str, str, str]]) -> list[dict]:
    """Find word-families with shared stems and systematic alternation.

    A paradigm is a set of words that share a common stem (all signs
    except the final 1-2) but differ in their endings. This is the
    Ventris technique that cracked case endings in Linear B.
    """
    word_counter = Counter(w for w, _, _ in words)
    unique_words = sorted(word_counter.keys())

    # Group by stem (all but last sign)
    stem_1: dict[str, list[str]] = defaultdict(list)  # drop last 1 sign
    stem_2: dict[str, list[str]] = defaultdict(list)  # drop last 2 signs

    for word in unique_words:
        signs = word.split("-")
        if len(signs) >= 2:
            stem = "-".join(signs[:-1])
            stem_1[stem].append(word)
        if len(signs) >= 3:
            stem = "-".join(signs[:-2])
            stem_2[stem].append(word)

    paradigms = []

    # Stem-1 paradigms (vary in final sign only)
    for stem, members in sorted(stem_1.items(), key=lambda x: -len(x[1])):
        if len(members) < 2:
            continue
        endings = []
        for w in members:
            final = w.split("-")[-1]
            count = word_counter[w]
            endings.append({"word": w, "ending": final, "count": count})

        # Check if endings match known morphological patterns
        morphological_hits = []
        for e in endings:
            end_sign = e["ending"]
            if end_sign in CASE_ENDINGS:
                morphological_hits.append({
                    **e,
                    "interpretation": CASE_ENDINGS[end_sign],
                    "type": "case_vowel",
                })
            elif end_sign in SUFFIX_PATTERNS:
                morphological_hits.append({
                    **e,
                    "interpretation": SUFFIX_PATTERNS[end_sign],
                    "type": "suffix",
                })

        # Score: more members and more morphological matches = higher confidence
        morph_ratio = len(morphological_hits) / len(endings) if endings else 0
        paradigm_score = len(members) * 0.3 + morph_ratio * 0.7

        paradigms.append({
            "stem": stem,
            "alternation_depth": 1,
            "members": members,
            "member_count": len(members),
            "endings": endings,
            "morphological_matches": morphological_hits,
            "morph_ratio": round(morph_ratio, 2),
            "score": round(paradigm_score, 2),
            "total_attestations": sum(word_counter[m] for m in members),
        })

    # Stem-2 paradigms (vary in final two signs — compound suffixes)
    for stem, members in sorted(stem_2.items(), key=lambda x: -len(x[1])):
        if len(members) < 2:
            continue
        # Only include if stem isn't already captured with better resolution
        if stem in stem_1 and len(stem_1[stem]) >= len(members):
            continue

        endings = []
        for w in members:
            signs = w.split("-")
            final_2 = "-".join(signs[-2:])
            count = word_counter[w]
            endings.append({"word": w, "ending": final_2, "count": count})

        paradigms.append({
            "stem": stem,
            "alternation_depth": 2,
            "members": members,
            "member_count": len(members),
            "endings": endings,
            "morphological_matches": [],
            "morph_ratio": 0,
            "score": round(len(members) * 0.2, 2),
            "total_attestations": sum(word_counter[m] for m in members),
        })

    paradigms.sort(key=lambda x: -x["score"])
    return paradigms


def find_case_triplets(words: list[tuple[str, str, str]]) -> list[dict]:
    """Find specific triplets where stem + {U, A, I} all appear.

    This is the strongest paradigmatic evidence: a word appearing in
    nominative (-U), accusative (-A), and genitive (-I) forms suggests
    Semitic-style tripartite case marking.
    """
    word_set = {w for w, _, _ in words}
    word_counter = Counter(w for w, _, _ in words)

    # Find all stems that could have case triplets
    stems = set()
    for word in word_set:
        signs = word.split("-")
        if len(signs) >= 2:
            stem = "-".join(signs[:-1])
            final = signs[-1]
            if final in CASE_ENDINGS:
                stems.add(stem)

    triplets = []
    for stem in sorted(stems):
        forms = {}
        for case_sign, case_info in CASE_ENDINGS.items():
            candidate = f"{stem}-{case_sign}"
            if candidate in word_set:
                forms[case_info["case"]] = {
                    "word": candidate,
                    "count": word_counter[candidate],
                }

        if len(forms) >= 2:  # at least a doublet
            triplets.append({
                "stem": stem,
                "forms": forms,
                "form_count": len(forms),
                "is_triplet": len(forms) == 3,
                "total_attestations": sum(f["count"] for f in forms.values()),
            })

    triplets.sort(key=lambda x: (-x["form_count"], -x["total_attestations"]))
    return triplets


def find_feminine_pairs(words: list[tuple[str, str, str]]) -> list[dict]:
    """Find words that appear with and without feminine -TE/-TI/-TU.

    If STEM and STEM-TE both exist, it may be a masculine/feminine pair.
    """
    word_set = {w for w, _, _ in words}
    word_counter = Counter(w for w, _, _ in words)
    fem_signs = ["TE", "TI", "TU"]

    pairs = []
    checked = set()
    for word in sorted(word_set):
        signs = word.split("-")
        if len(signs) < 2:
            continue
        final = signs[-1]
        if final in fem_signs:
            stem = "-".join(signs[:-1])
            if stem in checked:
                continue
            checked.add(stem)
            # Check if bare stem or stem+case-vowel exists
            masc_forms = []
            if stem in word_set:
                masc_forms.append({"word": stem, "count": word_counter[stem]})
            for cv in CASE_ENDINGS:
                candidate = f"{stem}-{cv}"
                if candidate in word_set:
                    masc_forms.append({"word": candidate, "count": word_counter[candidate]})

            if masc_forms:
                pairs.append({
                    "stem": stem,
                    "feminine": {"word": word, "suffix": final, "count": word_counter[word]},
                    "masculine_forms": masc_forms,
                })

    return pairs


def format_report(paradigms, triplets, fem_pairs, args) -> str:
    lines = []

    if args.triplets:
        lines.append(f"Case Triplets/Doublets ({len(triplets)} stems)")
        lines.append("=" * 60)
        for t in triplets[:30]:
            kind = "TRIPLET" if t["is_triplet"] else "doublet"
            forms_str = ", ".join(
                f"{case}={info['word']}(×{info['count']})"
                for case, info in sorted(t["forms"].items())
            )
            lines.append(f"  {t['stem']:<20} [{kind}] {forms_str}")
        return "\n".join(lines)

    if args.feminine:
        lines.append(f"Feminine Pairs ({len(fem_pairs)} stems)")
        lines.append("=" * 60)
        for p in fem_pairs[:30]:
            masc = ", ".join(f"{m['word']}(×{m['count']})" for m in p["masculine_forms"])
            lines.append(
                f"  {p['stem']:<20} fem={p['feminine']['word']}(×{p['feminine']['count']}) "
                f"masc={masc}"
            )
        return "\n".join(lines)

    # Default: full paradigm report
    lines.append(f"Morphological Paradigms ({len(paradigms)} stem families)")
    lines.append("=" * 70)
    lines.append(
        f"{'Stem':<22} {'#':>3} {'Attest':>6} {'Morph%':>6} {'Score':>6} {'Endings'}"
    )
    lines.append("-" * 70)

    shown = 0
    for p in paradigms:
        if shown >= (args.top or 40):
            break
        endings_str = ", ".join(
            f"{e['ending']}(×{e['count']})" for e in p["endings"][:6]
        )
        marker = " ★" if p["morph_ratio"] > 0.5 else ""
        lines.append(
            f"  {p['stem']:<20} {p['member_count']:>3} {p['total_attestations']:>6} "
            f"{p['morph_ratio']:>5.0%} {p['score']:>6.2f}  {endings_str}{marker}"
        )
        if p["morphological_matches"] and args.verbose:
            for m in p["morphological_matches"]:
                interp = m["interpretation"]
                if isinstance(interp, dict):
                    label = interp.get("case") or interp.get("function", "")
                else:
                    label = str(interp)
                lines.append(f"    → {m['word']}: {label}")
        shown += 1

    if len(paradigms) > shown:
        lines.append(f"  ... and {len(paradigms) - shown} more paradigms")

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
    parser = argparse.ArgumentParser(description="Morphological paradigm detection")
    parser.add_argument("--triplets", action="store_true", help="Show case triplets only")
    parser.add_argument("--feminine", action="store_true", help="Show feminine pairs only")
    parser.add_argument("--top", type=int, help="Number of paradigms to show")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show morphological interpretations")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    corpus, _morphemes, _lexicon = load_data()
    words = extract_word_list(corpus)
    paradigms = find_paradigms(words)
    triplets = find_case_triplets(words)
    fem_pairs = find_feminine_pairs(words)

    if args.json:
        if args.triplets:
            print(json.dumps(triplets, indent=2, ensure_ascii=False))
        elif args.feminine:
            print(json.dumps(fem_pairs, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({
                "paradigms": paradigms[:100],
                "triplets": triplets,
                "feminine_pairs": fem_pairs,
                "summary": {
                    "total_paradigms": len(paradigms),
                    "total_triplets": sum(1 for t in triplets if t["is_triplet"]),
                    "total_doublets": sum(1 for t in triplets if not t["is_triplet"]),
                    "feminine_pairs": len(fem_pairs),
                },
            }, indent=2, ensure_ascii=False))
    else:
        print(format_report(paradigms, triplets, fem_pairs, args))


if __name__ == "__main__":
    sys.exit(main())
