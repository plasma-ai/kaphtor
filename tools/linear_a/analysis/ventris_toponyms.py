#!/usr/bin/env python3
"""Place-name hypothesis tester for Linear A.

Ventris's Step 4: test if site-specific words encode the site's name.
Ventris cracked Linear B by hypothesizing that words unique to Knossos
spelled "ko-no-so." We test the same for Linear A with Semitic phonology:
Knossos ↔ √k-n-s, Phaistos ↔ PA-I-TO, Kaphtor ↔ √k-p-t, etc.
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

from ...core.phonetics import weighted_levenshtein
from ...core.skeleton import extract_skeleton
from ...paths import LINEAR_A_DATA, NotInCheckout, require
from ..ventris_propagate import skeleton_with_neutralization

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
LEXICON_PATH = DATA_DIR / "lexicon.json"

# Known/hypothesized site name ↔ Semitic root correspondences
SITE_HYPOTHESES: dict[str, dict] = {
    "Knossos": {
        "expected_roots": ["kns"],
        "expected_words": ["KU-NI-SU", "KI-NI-SA", "KU-NO-SO", "KI-NO-SO"],
        "etymology": "√k-n-s 'to gather' — Knossos as 'the gathering place'",
        "confidence": "PROBABLE",
    },
    "Phaistos": {
        "expected_roots": ["pst", "pyt"],
        "expected_words": ["PA-I-TO", "PA-I-TI"],
        "etymology": "PA-I-TO already confirmed in Linear B as Phaistos",
        "confidence": "CONFIRMED",
    },
    "Kythera": {
        "expected_roots": ["ktr", "qtr"],
        "expected_words": ["KI-TE-RA", "KU-TE-RA"],
        "etymology": "possibly √q-ṭ-r 'incense' — Kythera as incense station",
        "confidence": "SPECULATIVE",
    },
    "Zakros": {
        "expected_roots": ["zkr", "skr"],
        "expected_words": ["ZA-KI-RO", "SA-KU-RO"],
        "etymology": "possibly √z-k-r 'to remember' or pre-Greek toponym",
        "confidence": "SPECULATIVE",
    },
    "Tylissos": {
        "expected_roots": ["tls"],
        "expected_words": ["TU-RI-SO"],
        "etymology": "pre-Greek toponym, possibly √t-l-s substrate",
        "confidence": "SPECULATIVE",
    },
    "Haghia Triada": {
        "expected_roots": [],
        "expected_words": [],
        "etymology": "modern name — ancient name unknown; candidates sought",
        "confidence": "UNKNOWN",
    },
    "Palaikastro": {
        "expected_roots": [],
        "expected_words": [],
        "etymology": "modern name — ancient name unknown",
        "confidence": "UNKNOWN",
    },
    "Malia": {
        "expected_roots": ["ml", "mly"],
        "expected_words": ["MA-RI-JA", "MA-RA-JA"],
        "etymology": "possibly related to √m-l-ʔ 'to fill' or topographic",
        "confidence": "SPECULATIVE",
    },
    "Petras": {
        "expected_roots": ["ptr"],
        "expected_words": ["PE-TA-RA", "PI-TE-RA"],
        "etymology": "Greek πέτρα 'rock' — may be pre-Greek √p-t-r",
        "confidence": "SPECULATIVE",
    },
}


def load_data():
    corpus = json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))
    lexicon = json.loads(require(LEXICON_PATH, LEXICON_PATH.name).read_text(encoding="utf-8"))
    return corpus, lexicon


def build_site_word_map(corpus: dict) -> dict[str, Counter]:
    """Map each site to its word frequency counter."""
    site_words: dict[str, Counter] = defaultdict(Counter)
    for doc in corpus.values():
        site = doc.get("site", "unknown")
        for token in doc.get("transliteratedWords", []):
            if isinstance(token, str) and "-" in token:
                site_words[site][token.upper()] += 1
    return dict(site_words)


def find_site_specific_words(
    site_words: dict[str, Counter],
    min_site_count: int = 2,
    max_other_sites: int = 1,
) -> dict[str, list[dict]]:
    """Find words concentrated at a single site.

    A word is 'site-specific' if it appears at the target site >= min_site_count
    times and at <= max_other_sites other sites.
    """
    # Build global word-to-sites map
    word_sites: dict[str, dict[str, int]] = defaultdict(dict)
    for site, words in site_words.items():
        for word, count in words.items():
            word_sites[word][site] = count

    results: dict[str, list[dict]] = {}
    for site in site_words:
        specific = []
        for word, sites_map in word_sites.items():
            if site not in sites_map:
                continue
            site_count = sites_map[site]
            other_sites = {s: c for s, c in sites_map.items() if s != site}
            if site_count >= min_site_count and len(other_sites) <= max_other_sites:
                specificity = site_count / sum(sites_map.values())
                specific.append({
                    "word": word,
                    "site_count": site_count,
                    "total_count": sum(sites_map.values()),
                    "other_sites": other_sites,
                    "specificity": round(specificity, 2),
                })
        specific.sort(key=lambda x: -x["specificity"])
        if specific:
            results[site] = specific

    return results


def test_toponym_hypothesis(
    site: str,
    specific_words: list[dict],
    all_corpus_words: set[str],
    hypothesis: dict,
) -> dict:
    """Test if any words match the expected toponym.

    Searches both site-specific words AND the full corpus, because
    toponyms often appear as references at archive sites like
    Haghia Triada (e.g. PA-I-TO = Phaistos appears at HT, not PH).
    """
    expected_words = [w.upper() for w in hypothesis.get("expected_words", [])]
    expected_roots = hypothesis.get("expected_roots", [])
    matches = []

    def _match_word_against_roots(word, expected_roots, max_dist, score_discount=1.0):
        """Try all neutralization-expanded skeletons against expected roots."""
        signs = word.split("-")
        candidates = skeleton_with_neutralization(signs, "NWS")
        best = None
        for skeleton, skel_conf in candidates:
            if not skeleton or len(skeleton) < 2:
                continue
            for root in expected_roots:
                dist = weighted_levenshtein(skeleton, root)
                if dist <= max_dist:
                    score = (1 / (1 + dist)) * skel_conf * score_discount
                    if best is None or score > best["score"]:
                        best = {
                            "skeleton": skeleton,
                            "expected_root": root,
                            "distance": round(dist, 2),
                            "score": round(score, 3),
                        }
        return best

    # Check site-specific words
    for word_info in specific_words:
        word = word_info["word"]
        if word in expected_words:
            matches.append({
                "word": word,
                "match_type": "direct_site_specific",
                "score": 1.0,
                **word_info,
            })
            continue
        best = _match_word_against_roots(word, expected_roots, max_dist=1.0)
        if best:
            matches.append({
                "word": word,
                "match_type": "skeleton_site_specific",
                **best,
                **word_info,
            })

    # Check full corpus for expected word forms
    for expected in expected_words:
        if expected in all_corpus_words:
            already = any(m["word"] == expected for m in matches)
            if not already:
                matches.append({
                    "word": expected,
                    "match_type": "direct_corpus",
                    "score": 0.9,
                    "site_count": 0,
                    "total_count": 0,
                    "specificity": 0,
                })

    # Check full corpus for skeleton matches (stricter threshold)
    for word in all_corpus_words:
        if any(m["word"] == word for m in matches):
            continue
        best = _match_word_against_roots(
            word, expected_roots, max_dist=0.5, score_discount=0.7,
        )
        if best and best.get("skeleton") and len(best["skeleton"]) >= 3:
            matches.append({
                "word": word,
                "match_type": "skeleton_corpus",
                **best,
                "site_count": 0,
                "total_count": 0,
                "specificity": 0,
            })

    matches.sort(key=lambda x: -x["score"])
    return {
        "site": site,
        "hypothesis": hypothesis,
        "matches": matches[:10],
        "best_match": matches[0] if matches else None,
        "site_specific_count": len(specific_words),
    }


def discover_unknown_toponyms(
    site: str,
    specific_words: list[dict],
) -> list[dict]:
    """For sites with unknown ancient names, suggest candidates.

    The most site-specific word with a recognizable Semitic skeleton
    is the best candidate for the ancient toponym.
    """
    candidates = []
    for word_info in specific_words:
        word = word_info["word"]
        signs = word.split("-")
        skeleton = extract_skeleton("-".join(signs))
        if skeleton and len(skeleton) >= 2:
            candidates.append({
                "word": word,
                "skeleton": skeleton,
                "specificity": word_info["specificity"],
                "site_count": word_info["site_count"],
                "total_count": word_info["total_count"],
            })

    candidates.sort(key=lambda x: (-x["specificity"], -x["site_count"]))
    return candidates[:10]


def format_report(
    site_specific: dict[str, list[dict]],
    test_results: list[dict],
    discoveries: dict[str, list[dict]],
    args,
) -> str:
    lines = []
    lines.append("Toponym Hypothesis Testing")
    lines.append("=" * 70)

    # Known hypotheses
    lines.append("\n--- Known Site Hypotheses ---")
    for result in test_results:
        site = result["site"]
        hyp = result["hypothesis"]
        lines.append(f"\n{site} ({hyp['confidence']})")
        lines.append(f"  Etymology: {hyp['etymology']}")
        lines.append(f"  Site-specific words: {result['site_specific_count']}")

        if result["matches"]:
            for m in result["matches"][:5]:
                mtype = m["match_type"]
                if "direct" in mtype:
                    lines.append(f"  ★ {m['word']} — DIRECT MATCH [{mtype}] score={m['score']:.2f}")
                else:
                    lines.append(
                        f"  → {m['word']} skel={m.get('skeleton','?')} ↔ √{m.get('expected_root','?')} "
                        f"dist={m.get('distance',0):.2f} score={m['score']:.3f} [{mtype}]"
                    )
        else:
            lines.append("  (no matches found)")

    # Unknown sites — discover candidates
    if args.discover:
        lines.append("\n\n--- Toponym Discovery (Unknown Ancient Names) ---")
        for site, candidates in sorted(discoveries.items()):
            if not candidates:
                continue
            lines.append(f"\n{site}:")
            for c in candidates[:5]:
                lines.append(
                    f"  ? {c['word']:<25} skel={c['skeleton']:<8} "
                    f"specificity={c['specificity']:.2f} ×{c['site_count']}"
                )

    # Site-specific words summary
    if args.verbose:
        lines.append("\n\n--- All Site-Specific Words ---")
        for site in sorted(site_specific):
            words = site_specific[site]
            if len(words) < 2:
                continue
            lines.append(f"\n{site} ({len(words)} specific words):")
            for w in words[:10]:
                lines.append(f"  {w['word']:<25} ×{w['site_count']} specificity={w['specificity']}")

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
    parser = argparse.ArgumentParser(description="Place-name hypothesis tester")
    parser.add_argument("--site", help="Test a specific site only")
    parser.add_argument("--discover", action="store_true", help="Discover unknown toponyms")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all site-specific words")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    corpus, _lexicon = load_data()
    site_words = build_site_word_map(corpus)
    site_specific = find_site_specific_words(site_words)

    # Gather all corpus words for toponym search
    all_corpus_words = set()
    for words in site_words.values():
        all_corpus_words.update(words.keys())

    # Test known hypotheses
    test_results = []
    for site, hyp in SITE_HYPOTHESES.items():
        specific = site_specific.get(site, [])
        result = test_toponym_hypothesis(site, specific, all_corpus_words, hyp)
        test_results.append(result)

    # Discover unknown toponyms
    discoveries = {}
    if args.discover:
        for site, specific in site_specific.items():
            if site not in SITE_HYPOTHESES or SITE_HYPOTHESES[site].get("confidence") == "UNKNOWN":
                discoveries[site] = discover_unknown_toponyms(site, specific)

    if args.json:
        print(json.dumps({
            "test_results": test_results,
            "discoveries": discoveries,
            "site_specific_summary": {
                site: len(words) for site, words in site_specific.items()
            },
        }, indent=2, ensure_ascii=False))
    else:
        print(format_report(site_specific, test_results, discoveries, args))


if __name__ == "__main__":
    sys.exit(main())
