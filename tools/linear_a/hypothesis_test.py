"""Cross-validated candidate hypothesis testing.

Tests a decode run's cross-validated Ventris Engine candidates against:
1. Phrase-grammar slot compatibility (the WORD_ROLE_DOSSIER)
2. Site distribution consistency (baseline vs site-prior runs)
3. Neighbor-anchor coherence (do adjacent known words form coherent phrases?)
4. Linear B administrative slot transfer (structural validation)

The phrase grammar is read from <artifacts-dir>/linear-a-phrase-grammar/ (default: data/linear-a/).

Usage:
    uv run tools/linear_a/hypothesis_test.py --decode-run <run_id> --baseline <run_id> --site-prior <run_id>
    uv run tools/linear_a/hypothesis_test.py --decode-run <run_id> --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core import run_saver
from ..core.corpus_utils import load_corpus
from ..core.phrase_grammar import load_inscription_templates, load_phrase_grammar
from ..paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
ARTIFACTS_DIR = LINEAR_A_DATA
PHRASE_GRAMMAR_DIR = ARTIFACTS_DIR / "linear-a-phrase-grammar"
WORD_ROLE_PATH = PHRASE_GRAMMAR_DIR / "WORD_ROLE_DOSSIER.json"

ROOT_SEMANTIC_MAP = {
    "grain": "COMMODITY_LABEL",
    "wheat": "COMMODITY_LABEL",
    "emmer": "COMMODITY_LABEL",
    "barley": "COMMODITY_LABEL",
    "olive": "COMMODITY_LABEL",
    "oil": "COMMODITY_LABEL",
    "wine": "COMMODITY_LABEL",
    "honey": "COMMODITY_LABEL",
    "fig": "COMMODITY_LABEL",
    "wool": "COMMODITY_LABEL",
    "textile": "COMMODITY_LABEL",
    "cloth": "COMMODITY_LABEL",
    "bronze": "COMMODITY_LABEL",
    "copper": "COMMODITY_LABEL",
    "gold": "COMMODITY_LABEL",
    "silver": "COMMODITY_LABEL",
    "total": "ACCOUNTING_TOTAL",
    "all": "ACCOUNTING_TOTAL",
    "sum": "ACCOUNTING_TOTAL",
    "town": "TOPONYM",
    "village": "TOPONYM",
    "city": "TOPONYM",
    "give": "VERB_ACTION",
    "offer": "VERB_ACTION",
    "dedicate": "VERB_ACTION",
    "pour": "VERB_ACTION",
    "smith": "PERSONAL_NAME",
    "servant": "PERSONAL_NAME",
    "lord": "CULTIC_RECIPIENT",
    "king": "CULTIC_RECIPIENT",
    "goddess": "CULTIC_RECIPIENT",
    "god": "CULTIC_RECIPIENT",
    "mother": "PERSONAL_NAME",
    "father": "PERSONAL_NAME",
    "son": "PERSONAL_NAME",
    "daughter": "PERSONAL_NAME",
    "heart": "VERB_ACTION",
    "hand": "VERB_ACTION",
    "eye": "VERB_ACTION",
    "mouth": "VERB_ACTION",
    "water": "COMMODITY_LABEL",
    "fire": "VERB_ACTION",
    "earth": "TOPONYM",
    "mountain": "TOPONYM",
    "field": "COMMODITY_LABEL",
    "house": "TOPONYM",
    "gate": "TOPONYM",
    "place": "TOPONYM",
    "buck": "COMMODITY_LABEL",
    "goat": "COMMODITY_LABEL",
    "sheep": "COMMODITY_LABEL",
    "ox": "COMMODITY_LABEL",
    "cattle": "COMMODITY_LABEL",
    "pig": "COMMODITY_LABEL",
    "horse": "COMMODITY_LABEL",
}


SUBSCRIPT_MAP = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
})


def normalize_word(w: str) -> str:
    return w.translate(SUBSCRIPT_MAP)


def load_word_roles(artifacts_dir: Path | None = None) -> dict[str, dict]:
    path = WORD_ROLE_PATH
    if artifacts_dir is not None:
        path = artifacts_dir / "linear-a-phrase-grammar" / "WORD_ROLE_DOSSIER.json"
    if not path.exists():
        print(f"Warning: word role dossier not found at {path}", file=sys.stderr)
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    roles: dict[str, dict] = {}
    for entry in data:
        roles[entry["word"]] = entry
        normed = normalize_word(entry["word"])
        if normed != entry["word"]:
            roles[normed] = entry
    return roles


def load_lexicon() -> dict[str, dict]:
    lex_path = DATA_DIR / "lexicon.json"
    data = json.loads(require(lex_path, lex_path.name).read_text(encoding="utf-8"))
    return {entry["word"]: entry for entry in data.get("entries", [])}


def get_cross_validated_candidates(decode_run_id: str) -> list[dict]:
    _, output = run_saver.load_run(decode_run_id)
    return output.get("cross_validated", [])


def get_propagation_results(run_id: str) -> list[dict]:
    _, output = run_saver.load_run(run_id)
    return output.get("results", [])


def build_corpus_index(corpus: dict) -> dict[str, list[dict]]:
    """Build word -> list of (doc_id, site, position, neighbors) index."""
    index: dict[str, list[dict]] = {}
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        tokens = doc.get("transliteratedWords", [])
        word_tokens = []
        for i, tok in enumerate(tokens):
            if isinstance(tok, str) and tok.strip() and tok != "\n" and "-" in tok:
                word_tokens.append((i, tok.upper()))

        for pos, (orig_idx, word) in enumerate(word_tokens):
            neighbors = []
            if pos > 0:
                neighbors.append(word_tokens[pos - 1][1])
            if pos < len(word_tokens) - 1:
                neighbors.append(word_tokens[pos + 1][1])
            index.setdefault(word, []).append({
                "doc_id": doc_id,
                "site": site,
                "position": pos,
                "total_words": len(word_tokens),
                "neighbors": neighbors,
            })
    return index


def infer_semantic_category(meaning: str) -> str | None:
    meaning_lower = meaning.lower()
    for keyword, role in ROOT_SEMANTIC_MAP.items():
        if keyword in meaning_lower:
            return role
    return None


def test_slot_compatibility(
    word: str,
    meaning: str,
    word_roles: dict[str, dict],
    decomposed_roles: dict[str, str] | None = None,
) -> dict:
    role_entry = word_roles.get(word) or word_roles.get(normalize_word(word))
    if not role_entry:
        return {"verdict": "NO_DATA", "assigned_role": None, "inferred_category": None}

    assigned_role = role_entry["role"]
    inferred = infer_semantic_category(meaning)

    if assigned_role == "UNKNOWN_FORMULA_ELEMENT":
        subrole = None
        if decomposed_roles:
            subrole = decomposed_roles.get(word) or decomposed_roles.get(normalize_word(word))
        if subrole is None or subrole == "LOW_INFORMATION_UNKNOWN":
            return {
                "verdict": "UNKNOWN_ROLE",
                "assigned_role": assigned_role,
                "decomposed_subrole": subrole,
                "inferred_category": inferred,
                "note": "UNKNOWN slot provides no discriminating evidence",
            }
        assigned_role = subrole

    if inferred is None:
        return {
            "verdict": "UNDETERMINED",
            "assigned_role": assigned_role,
            "inferred_category": None,
            "note": "Could not infer semantic category from meaning",
        }

    COMPATIBLE_WITH = {
        "PERSONAL_NAME": {"PERSONAL_NAME", "TOPONYM", "CULTIC_RECIPIENT", "NAME_TITLE"},
        "TOPONYM": {"PERSONAL_NAME", "TOPONYM", "NAME_TITLE"},
        "CULTIC_RECIPIENT": {"PERSONAL_NAME", "CULTIC_RECIPIENT", "NAME_TITLE"},
        "VERB_ACTION": {"VERB_ACTION", "ACCOUNTING_PARTICLE"},
        "COMMODITY_LABEL": {"COMMODITY_LABEL", "QUANTITY_OR_MEASURE"},
        "ACCOUNTING_TOTAL": {"ACCOUNTING_TOTAL", "ACCOUNTING_PARTICLE"},
        "NAME_TITLE": {"NAME_TITLE", "PERSONAL_NAME", "TOPONYM", "CULTIC_RECIPIENT"},
        "ACCOUNTING_PARTICLE": {"ACCOUNTING_PARTICLE", "VERB_ACTION", "ACCOUNTING_TOTAL"},
        "QUANTITY_OR_MEASURE": {"QUANTITY_OR_MEASURE", "COMMODITY_LABEL"},
        "VESSEL_MARK": {"VESSEL_MARK"},
    }

    if inferred == assigned_role:
        return {
            "verdict": "MATCH",
            "assigned_role": assigned_role,
            "inferred_category": inferred,
        }

    compatible_set = COMPATIBLE_WITH.get(assigned_role, set())
    if inferred in compatible_set:
        return {
            "verdict": "MATCH",
            "assigned_role": assigned_role,
            "inferred_category": inferred,
            "note": f"Compatible: {inferred} accepted in {assigned_role} slot",
        }

    return {
        "verdict": "MISMATCH",
        "assigned_role": assigned_role,
        "inferred_category": inferred,
    }


def test_site_consistency(
    word: str,
    baseline_results: list[dict],
    siteprior_results: list[dict],
) -> dict:
    base_map = {r["word"]: r for r in baseline_results if r.get("status") != "known"}
    site_map = {r["word"]: r for r in siteprior_results if r.get("status") != "known"}

    base = base_map.get(word)
    site = site_map.get(word)

    if not base or not site:
        return {"verdict": "NO_DATA", "baseline_lang": None, "siteprior_lang": None}

    base_lang = base.get("language", {})
    site_lang = site.get("language", {})
    base_decision = base_lang.get("decision", "unknown")
    site_decision = site_lang.get("decision", "unknown")
    base_conf = base_lang.get("confidence", 0)
    site_conf = site_lang.get("confidence", 0)

    stable = base_decision == site_decision
    strengthened = stable and site_conf > base_conf
    flipped = not stable

    if strengthened:
        verdict = "STRENGTHENED"
    elif stable:
        verdict = "STABLE"
    elif flipped and site_conf > 0.5:
        verdict = "RECLASSIFIED_CONFIDENT"
    else:
        verdict = "RECLASSIFIED_WEAK"

    return {
        "verdict": verdict,
        "baseline_lang": base_decision,
        "baseline_conf": round(base_conf, 3),
        "siteprior_lang": site_decision,
        "siteprior_conf": round(site_conf, 3),
        "delta_conf": round(site_conf - base_conf, 3),
        "site": site.get("site", ""),
    }


def test_neighbor_coherence(
    word: str,
    corpus_index: dict[str, list[dict]],
    lexicon: dict[str, dict],
) -> dict:
    attestations = corpus_index.get(word, [])
    if not attestations:
        return {"verdict": "NO_DATA", "attestation_count": 0, "anchor_adjacency": 0}

    anchor_adjacent = 0
    total_neighbors = 0
    neighbor_anchors = []

    for att in attestations:
        for nb in att["neighbors"]:
            total_neighbors += 1
            if nb in lexicon:
                entry = lexicon[nb]
                if entry.get("confidence") in ("CONFIRMED", "PROBABLE"):
                    anchor_adjacent += 1
                    neighbor_anchors.append({
                        "word": nb,
                        "meaning": entry.get("meaning", ""),
                        "confidence": entry.get("confidence", ""),
                    })

    ratio = anchor_adjacent / total_neighbors if total_neighbors > 0 else 0

    if ratio >= 0.5:
        verdict = "STRONG"
    elif ratio >= 0.2:
        verdict = "MODERATE"
    elif anchor_adjacent > 0:
        verdict = "WEAK"
    else:
        verdict = "NONE"

    return {
        "verdict": verdict,
        "attestation_count": len(attestations),
        "total_neighbors": total_neighbors,
        "anchor_adjacent": anchor_adjacent,
        "anchor_ratio": round(ratio, 3),
        "anchor_neighbors": neighbor_anchors[:5],
    }


def compute_composite_verdict(
    slot: dict,
    site: dict,
    neighbor: dict,
    score: float,
    null_pvalues: dict | None = None,
) -> dict:
    points = 0
    max_points = 0
    independent_axes = 0
    site_restored = False

    # Slot: MATCH/MISMATCH score; UNKNOWN_ROLE, NO_DATA, UNDETERMINED excluded
    if slot["verdict"] in ("MATCH", "MISMATCH"):
        max_points += 2
        independent_axes += 1
        if slot["verdict"] == "MATCH":
            points += 2
        elif slot["verdict"] == "MISMATCH":
            points -= 2

    # Site: restored behind p < 0.05 gate when null model is available
    if null_pvalues and null_pvalues.get("site"):
        site_p = null_pvalues["site"].get("p_value")
        if site_p is not None and site_p < 0.05:
            site_restored = True
            max_points += 2
            independent_axes += 1
            if site["verdict"] in ("STRENGTHENED", "STABLE"):
                points += 2
            elif site["verdict"] == "RECLASSIFIED_WEAK":
                points += 1

    # Neighbor: upweighted — genuinely independent axis
    if neighbor["verdict"] in ("STRONG", "MODERATE", "WEAK"):
        max_points += 3
        independent_axes += 1
        if neighbor["verdict"] == "STRONG":
            points += 3
        elif neighbor["verdict"] == "MODERATE":
            points += 2
        elif neighbor["verdict"] == "WEAK":
            points += 1

    # Cross-validated score (reduced weight: max 1 point, not 2)
    max_points += 1
    if score >= 1.0:
        points += 1

    ratio = points / max_points if max_points > 0 else 0

    if ratio >= 0.75 and independent_axes >= 1:
        verdict = "PROMOTE_TO_PROBABLE"
    elif ratio >= 0.50 and independent_axes >= 1:
        verdict = "STRENGTHEN"
    elif ratio >= 0.0:
        verdict = "RETAIN"
    else:
        verdict = "WEAKEN"

    return {
        "verdict": verdict,
        "points": points,
        "max_points": max_points,
        "ratio": round(ratio, 3),
        "independent_axes": independent_axes,
        "site_restored": site_restored,
    }


def run_hypothesis_tests(
    decode_run_id: str,
    baseline_run_id: str | None,
    siteprior_run_id: str | None,
    artifacts_dir: Path | None = None,
    use_null_model: bool = False,
) -> list[dict]:
    candidates = get_cross_validated_candidates(decode_run_id)
    if not candidates:
        print("No cross-validated candidates found in decode run.", file=sys.stderr)
        return []

    word_roles = load_word_roles(artifacts_dir=artifacts_dir)
    lexicon = load_lexicon()
    corpus = load_corpus()
    corpus_index = build_corpus_index(corpus)

    a_dir = artifacts_dir if artifacts_dir else ARTIFACTS_DIR
    decomposed_roles: dict[str, str] | None = None
    try:
        pg = load_phrase_grammar(a_dir)
        templates = load_inscription_templates(a_dir)
        decomposed_roles = pg.decompose_unknown_roles(corpus, templates)
        unknown_total = sum(1 for e in word_roles.values() if e.get("role") == "UNKNOWN_FORMULA_ELEMENT")
        low_info = sum(1 for r in decomposed_roles.values() if r == "LOW_INFORMATION_UNKNOWN")
        print(f"UNKNOWN decomposition: {len(decomposed_roles)} words, "
              f"{low_info}/{unknown_total} LOW_INFORMATION_UNKNOWN "
              f"({low_info/unknown_total:.0%})", file=sys.stderr)
    except FileNotFoundError as e:
        print(f"Warning: UNKNOWN decomposition unavailable: {e}", file=sys.stderr)

    baseline_results = get_propagation_results(baseline_run_id) if baseline_run_id else []
    siteprior_results = get_propagation_results(siteprior_run_id) if siteprior_run_id else []

    prop_map = {}
    for source in (baseline_results, siteprior_results):
        for r in source:
            if r.get("status") != "known" and r.get("word") not in prop_map:
                prop_map[r["word"]] = r

    all_null_pvalues: dict[str, dict] = {}
    if use_null_model:
        from ..core.null_model import compute_all_null_pvalues
        prop_candidates = [prop_map.get(c.get("word", ""), c) for c in candidates]
        print("Running permutation null model (1000 permutations per axis)...", file=sys.stderr)
        all_null_pvalues = compute_all_null_pvalues(
            prop_candidates, corpus_index, baseline_results + siteprior_results,
            word_roles, lexicon, n_permutations=1000, seed=42,
            decomposed_roles=decomposed_roles,
        )
        site_sig = sum(1 for v in all_null_pvalues.values()
                       if v.get("site", {}).get("p_value", 1.0) < 0.05)
        print(f"Null model: {site_sig}/{len(all_null_pvalues)} candidates with site p < 0.05", file=sys.stderr)

    results = []
    for cand in candidates:
        word = cand.get("word", "")
        combined_score = cand.get("combined_score", 0)

        prop_data = prop_map.get(word, {})
        meaning = prop_data.get("best_meaning", "")
        root = prop_data.get("best_root", "")
        skeleton = prop_data.get("skeleton", "")
        source_lang = prop_data.get("source_lang", "")

        slot = test_slot_compatibility(word, meaning, word_roles, decomposed_roles)
        site = test_site_consistency(word, baseline_results, siteprior_results)
        neighbor = test_neighbor_coherence(word, corpus_index, lexicon)
        null_pv = all_null_pvalues.get(word)
        composite = compute_composite_verdict(slot, site, neighbor, combined_score, null_pv)

        attestations = corpus_index.get(word, [])
        sites = list({a["site"] for a in attestations})
        doc_ids = list({a["doc_id"] for a in attestations})

        results.append({
            "word": word,
            "combined_score": combined_score,
            "skeleton": skeleton,
            "best_root": root,
            "best_meaning": meaning,
            "source_lang": source_lang,
            "attestation_count": len(attestations),
            "sites": sites,
            "doc_ids": doc_ids[:10],
            "slot_test": slot,
            "site_test": site,
            "neighbor_test": neighbor,
            "null_pvalues": null_pv,
            "composite": composite,
        })

    results.sort(key=lambda r: (-r["composite"]["ratio"], -r["combined_score"]))
    return results


def format_results(results: list[dict]) -> str:
    lines = []
    lines.append("Cross-Validated Candidate Hypothesis Test Results")
    lines.append("=" * 70)
    lines.append(f"Candidates tested: {len(results)}")
    lines.append("")

    verdicts = Counter(r["composite"]["verdict"] for r in results)
    for v, c in verdicts.most_common():
        lines.append(f"  {v}: {c}")
    lines.append("")

    for r in results:
        v = r["composite"]
        lines.append(f"{'=' * 60}")
        lines.append(f"  {r['word']}")
        lines.append(f"  Score: {r['combined_score']:.3f}  Skeleton: {r['skeleton']}")
        lines.append(f"  Root: {r['best_root']}  Meaning: \"{r['best_meaning']}\"  Lang: {r['source_lang']}")
        lines.append(f"  Attestations: {r['attestation_count']}  Sites: {', '.join(r['sites'][:5])}")
        slot_role_label = r['slot_test']['assigned_role']
        if r['slot_test'].get('decomposed_subrole'):
            slot_role_label = f"{r['slot_test']['assigned_role']}→{r['slot_test']['decomposed_subrole']}"
        lines.append(f"  Slot: {r['slot_test']['verdict']}  (role={slot_role_label}, inferred={r['slot_test']['inferred_category']})")
        site_tag = "[NOT SCORED — circular]"
        if v.get("site_restored"):
            site_tag = "[SCORED — p < 0.05]"
        np = r.get("null_pvalues")
        site_p_str = ""
        if np and np.get("site"):
            sp = np["site"].get("p_value")
            if sp is not None:
                site_p_str = f", site_p={sp:.3f}"
        lines.append(f"  Site: {r['site_test']['verdict']}  ({r['site_test'].get('baseline_lang','?')} -> {r['site_test'].get('siteprior_lang','?')}, delta={r['site_test'].get('delta_conf',0):+.3f}{site_p_str}) {site_tag}")
        lines.append(f"  Neighbors: {r['neighbor_test']['verdict']}  (anchors={r['neighbor_test']['anchor_adjacent']}/{r['neighbor_test']['total_neighbors']})")

        if r["neighbor_test"].get("anchor_neighbors"):
            for nb in r["neighbor_test"]["anchor_neighbors"][:3]:
                lines.append(f"    → {nb['word']} = \"{nb['meaning']}\" [{nb['confidence']}]")

        lines.append(f"  ▶ VERDICT: {v['verdict']}  ({v['points']}/{v['max_points']} = {v['ratio']:.0%}, {v.get('independent_axes',0)} independent axes)")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Cross-validated candidate hypothesis testing",
    )
    parser.add_argument("--decode-run", required=True,
                        help="Run ID of the decode run with cross_validated candidates, or 'latest'")
    parser.add_argument("--baseline", default=None,
                        help="Run ID of baseline propagation (no site priors)")
    parser.add_argument("--site-prior", default=None,
                        help="Run ID of site-prior propagation")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--artifacts-dir", type=Path, default=None,
                        help="Folder holding linear-a-phrase-grammar/ (default: data/linear-a/)")
    parser.add_argument("--save", action="store_true",
                        help="Save results to the run cache (see ventris_runs.py)")
    parser.add_argument("--label", default=None,
                        help="Optional label for saved run")
    parser.add_argument("--null-model", action="store_true",
                        help="Enable permutation null model for empirical p-values (site, slot, neighbor)")
    args = parser.parse_args()
    if args.decode_run == "latest":
        latest = run_saver.list_runs("decode", limit=1)
        if not latest:
            print("no saved decode run (save one with ventris_decode.py --save)", file=sys.stderr)
            return 1
        args.decode_run = latest[0]["run_id"]

    try:
        results = run_hypothesis_tests(
            args.decode_run,
            args.baseline,
            args.site_prior,
            artifacts_dir=args.artifacts_dir,
            use_null_model=args.null_model,
        )
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"no saved run: {e.filename} (list the saved runs with ventris_runs.py list)", file=sys.stderr)
        return 1

    output = {
        "test_type": "cross_validated_hypothesis",
        "decode_run": args.decode_run,
        "baseline_run": args.baseline,
        "siteprior_run": args.site_prior,
        "null_model_enabled": args.null_model,
        "candidates_tested": len(results),
        "verdicts": dict(Counter(r["composite"]["verdict"] for r in results)),
        "results": results,
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_results(results))

    if args.save:
        run_saver.save_run(
            "hypothesis_test",
            {
                "decode_run": args.decode_run,
                "baseline_run": args.baseline,
                "siteprior_run": args.site_prior,
                "null_model": args.null_model,
            },
            output,
            label=args.label,
        )
        print("\nRun saved.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
