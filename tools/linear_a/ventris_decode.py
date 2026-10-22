#!/usr/bin/env python3
"""Full-cycle Ventris Engine orchestrator.

Runs the complete decipherment pipeline:
1. Stats census (sign frequency, bigrams)
2. Grid (sign-value confidence)
3. Propagation (constraint-based root matching)
4. Paradigms (morphological pattern detection)
5. Ideograms (semantic validation)
6. Toponyms (place-name hypothesis)

Then cross-validates results and produces a unified report with
confidence-ranked candidate readings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

# Import all engine modules
from ..core.data_cache import corpus as cached_corpus
from ..core.data_cache import lexicon as cached_lexicon
from ..core.data_cache import sign_values as cached_sign_values
from ..paths import NotInCheckout
from .analysis.ventris_grid import build_grid, derive_constraints_from_lexicon, find_conflicts, find_unconstrained
from .analysis.ventris_ideograms import compute_ideogram_summary, extract_ideogram_contexts, validate_readings
from .analysis.ventris_paradigms import extract_word_list, find_case_triplets, find_feminine_pairs, find_paradigms
from .analysis.ventris_stats import bigrams, extract_words, word_frequency
from .analysis.ventris_toponyms import (
    SITE_HYPOTHESES,
    build_site_word_map,
    find_site_specific_words,
    test_toponym_hypothesis,
)
from .ventris_propagate import LanguageOptions, run_propagation


def run_full_cycle(
    min_score: float = 0.5,
    max_candidates: int = 50,
    lang_opts: LanguageOptions | None = None,
) -> dict:
    """Run the complete Ventris Engine pipeline."""
    results = {}

    # --- Phase 1: Statistics ---
    corpus = cached_corpus()
    lexicon = cached_lexicon()
    words = extract_words(corpus)
    top_bigrams = bigrams(words, 20)
    top_words = word_frequency(words)
    all_signs = set()
    for _, _, signs in words:
        all_signs.update(signs)

    results["stats"] = {
        "total_word_tokens": len(words),
        "unique_word_types": len({"-".join(s) for _, _, s in words}),
        "unique_signs": len(all_signs),
        "top_bigrams": top_bigrams[:10],
        "top_words": top_words[:10],
    }

    # --- Phase 2: Grid ---
    sv = cached_sign_values()
    constraints = derive_constraints_from_lexicon(lexicon)
    grid = build_grid(sv, constraints)
    conflicts = find_conflicts(grid)
    unconstrained = find_unconstrained(grid)

    results["grid"] = {
        "total_signs_mapped": len(grid),
        "conflicts": len(conflicts),
        "unconstrained_signs": len(unconstrained),
    }

    # --- Phase 3: Propagation ---
    prop_data = run_propagation(
        min_score=min_score,
        new_only=True,
        max_results=max_candidates,
        lang_opts=lang_opts,
    )
    results["propagation"] = prop_data["summary"]
    candidates = prop_data["results"]

    # --- Phase 4: Paradigms ---
    p_words = extract_word_list(corpus)
    paradigms = find_paradigms(p_words)
    triplets = find_case_triplets(p_words)
    fem_pairs = find_feminine_pairs(p_words)

    multi_sign_paradigms = [p for p in paradigms
                           if len(p["stem"].split("-")) >= 2 and p["morph_ratio"] > 0]
    results["paradigms"] = {
        "total_paradigms": len(paradigms),
        "multi_sign_with_morphology": len(multi_sign_paradigms),
        "case_doublets": sum(1 for t in triplets if not t["is_triplet"]),
        "case_triplets": sum(1 for t in triplets if t["is_triplet"]),
        "feminine_pairs": len(fem_pairs),
    }

    # --- Phase 5: Ideograms ---
    ideo_contexts = extract_ideogram_contexts(corpus)
    ideo_results = validate_readings(ideo_contexts, lexicon)
    ideo_summary = compute_ideogram_summary(ideo_results)

    total_known = sum(s["known_readings"] for s in ideo_summary.values())
    total_match = sum(s["semantic_matches"] for s in ideo_summary.values())
    results["ideograms"] = {
        "total_contexts": len(ideo_contexts),
        "known_readings": total_known,
        "semantic_matches": total_match,
        "match_rate": round(total_match / total_known, 2) if total_known else 0,
    }

    # --- Phase 6: Toponyms ---
    site_words = build_site_word_map(corpus)
    site_specific = find_site_specific_words(site_words)
    all_corpus_words = set()
    for w in site_words.values():
        all_corpus_words.update(w.keys())

    topo_results = []
    for site, hyp in SITE_HYPOTHESES.items():
        specific = site_specific.get(site, [])
        result = test_toponym_hypothesis(site, specific, all_corpus_words, hyp)
        if result["matches"]:
            topo_results.append({
                "site": site,
                "best_match": result["matches"][0]["word"],
                "match_type": result["matches"][0]["match_type"],
                "score": result["matches"][0]["score"],
            })

    results["toponyms"] = {
        "hypotheses_tested": len(SITE_HYPOTHESES),
        "with_matches": len(topo_results),
        "matches": topo_results,
    }

    # --- Cross-Validation ---
    # Boost candidates that appear in multiple evidence streams
    candidate_evidence: dict[str, dict] = {}
    for c in candidates:
        word = c["word"]
        if word not in candidate_evidence:
            candidate_evidence[word] = {
                "word": word,
                "propagation": c,
                "evidence_lines": ["propagation"],
                "combined_score": c["score"],
            }

    # Check if any candidates also appear in paradigms
    paradigm_words = set()
    for p in multi_sign_paradigms:
        for m in p.get("morphological_matches", []):
            paradigm_words.add(m["word"])
    for word in paradigm_words:
        if word in candidate_evidence:
            candidate_evidence[word]["evidence_lines"].append("paradigm")
            candidate_evidence[word]["combined_score"] *= 1.3

    # Check if any candidates appear near ideograms
    ideo_words = {r["word"] for r in ideo_results if r["semantic_match"]["match"]}
    for word in ideo_words:
        if word in candidate_evidence:
            candidate_evidence[word]["evidence_lines"].append("ideogram")
            candidate_evidence[word]["combined_score"] *= 1.5

    # Check toponym matches
    topo_words = {t["best_match"] for t in topo_results}
    for word in topo_words:
        if word in candidate_evidence:
            candidate_evidence[word]["evidence_lines"].append("toponym")
            candidate_evidence[word]["combined_score"] *= 1.4

    # Rank by combined score
    ranked = sorted(candidate_evidence.values(), key=lambda x: -x["combined_score"])
    results["cross_validated"] = ranked[:max_candidates]

    return results


def format_full_report(results: dict) -> str:
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║        VENTRIS ENGINE — Full Decipherment Report        ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")

    # Stats
    s = results["stats"]
    lines.append("1. CORPUS STATISTICS")
    lines.append(f"   Word tokens: {s['total_word_tokens']:,}  |  "
                f"Types: {s['unique_word_types']:,}  |  "
                f"Signs: {s['unique_signs']}")
    lines.append("")

    # Grid
    g = results["grid"]
    lines.append("2. SIGN-VALUE GRID")
    lines.append(f"   Signs mapped: {g['total_signs_mapped']}  |  "
                f"Conflicts: {g['conflicts']}  |  "
                f"Unconstrained: {g['unconstrained_signs']}")
    lines.append("")

    # Propagation
    p = results["propagation"]
    lines.append("3. CONSTRAINT PROPAGATION")
    lines.append(f"   Words analyzed: {p['total_words']:,}  |  "
                f"Known: {p['known']}  |  "
                f"New candidates: {p['new_candidates']}  |  "
                f"No match: {p['no_match']:,}")
    mode = p.get("language_mode", "multi")
    site_p = "on" if p.get("site_priors_enabled") else "off"
    site_c = "on" if p.get("site_consistency_enabled") else "off"
    lines.append(f"   Language: {mode}  |  Site priors: {site_p}  |  Consistency: {site_c}")
    sc = p.get("site_consistency")
    if sc:
        lines.append(f"   Consistency pass: rescored {sc['rescored']}, "
                     f"replaced {sc['replaced']}, "
                     f"monolingual sites: {len(sc.get('strongly_monolingual', []))}")
    lines.append("")

    # Paradigms
    pa = results["paradigms"]
    lines.append("4. MORPHOLOGICAL PARADIGMS")
    lines.append(f"   Paradigm families: {pa['total_paradigms']}  |  "
                f"With Semitic morphology: {pa['multi_sign_with_morphology']}  |  "
                f"Feminine pairs: {pa['feminine_pairs']}")
    lines.append(f"   Case doublets: {pa['case_doublets']}  |  "
                f"Case triplets: {pa['case_triplets']}")
    lines.append("")

    # Ideograms
    i = results["ideograms"]
    lines.append("5. IDEOGRAPHIC VALIDATION")
    lines.append(f"   Contexts: {i['total_contexts']}  |  "
                f"Known readings: {i['known_readings']}  |  "
                f"Semantic matches: {i['semantic_matches']}  |  "
                f"Match rate: {i['match_rate']:.0%}")
    lines.append("")

    # Toponyms
    t = results["toponyms"]
    lines.append("6. TOPONYM HYPOTHESES")
    lines.append(f"   Tested: {t['hypotheses_tested']}  |  "
                f"With matches: {t['with_matches']}")
    for m in t["matches"]:
        lines.append(f"   ★ {m['site']}: {m['best_match']} ({m['match_type']}, score={m['score']:.2f})")
    lines.append("")

    # Cross-validated candidates
    lines.append("═" * 60)
    lines.append("CROSS-VALIDATED CANDIDATES (ranked by combined evidence)")
    lines.append("═" * 60)

    for entry in results["cross_validated"]:
        prop = entry["propagation"]
        evidence = " + ".join(entry["evidence_lines"])
        multi = len(entry["evidence_lines"]) > 1
        marker = "★★" if multi else "  "
        lang = prop.get("language", {}).get("decision", "?")
        lines.append(
            f"{marker} {prop['word']:<25} skel={prop['skeleton']:<8} "
            f"√{prop['best_root']:<8} \"{prop['best_meaning'][:30]}\" "
            f"score={entry['combined_score']:.3f} [{lang}]"
        )
        if multi:
            lines.append(f"     Evidence: {evidence}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ventris Engine — full decipherment cycle")
    parser.add_argument("--min-score", type=float, default=0.5, help="Minimum propagation score")
    parser.add_argument("--max-candidates", type=int, default=50, help="Max candidates to show")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--language", choices=["multi", "semitic-only", "contact-aware"],
                        default="multi", help="Language filtering mode")
    parser.add_argument("--site-priors", action="store_true",
                        help="Enable per-site language priors")
    parser.add_argument("--site-consistency", action="store_true",
                        help="Enable two-pass site consistency refinement")
    parser.add_argument("--site-consistency-threshold", type=float, default=0.70,
                        help="Confidence threshold for consistency re-scoring")
    parser.add_argument("--save", action="store_true",
                        help="Persist run to the run cache with full provenance (see ventris_runs.py)")
    parser.add_argument("--label", type=str, default=None,
                        help="Optional label for the saved run (e.g., 'baseline', 'contact-aware-test')")
    args = parser.parse_args()

    lang_opts = LanguageOptions(
        mode=args.language,
        use_site_priors=args.site_priors,
        use_site_consistency=args.site_consistency,
        site_consistency_threshold=args.site_consistency_threshold,
    )

    try:
        results = run_full_cycle(
            min_score=args.min_score,
            max_candidates=args.max_candidates,
            lang_opts=lang_opts,
        )
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2

    if args.save:
        from ..core.run_saver import save_run
        params = {
            "min_score": args.min_score,
            "max_candidates": args.max_candidates,
            "language": args.language,
            "site_priors": args.site_priors,
            "site_consistency": args.site_consistency,
            "site_consistency_threshold": args.site_consistency_threshold,
        }
        run_dir = save_run("decode", params, results, label=args.label)
        print(f"Run saved to {run_dir}", file=sys.stderr)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_full_report(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
