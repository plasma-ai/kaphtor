#!/usr/bin/env python3
"""Propose candidate CV values for undeciphered Linear A signs.

The proposal is a read-only Ventris-style ranking: corpus contexts, neighboring
known signs, available CH-origin evidence, and cognate root tests are reported
as auditable components rather than accepted decipherments.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core import data_cache
from ..core.phonetics import normalize_phonemes
from ..core.skeleton import _lookup_sign
from ..paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
REGISTRY_PATH = DATA_DIR / "sign-registry.json"
SIGN_VALUES_PATH = DATA_DIR / "sign_values.json"
EVOLUTION_PATH = DATA_DIR / "sign-evolution-map.json"
MISSING_SOUND_MAP_PATH = DATA_DIR / "missing_sound_map.json"
REJECTED_VALUES_PATH = DATA_DIR / "rejected_sign_values.json"

from .ventris_propagate import (
    _prepare_root_entries,
    score_against_egyptian_roots,
    score_against_luwian_roots,
    score_against_roots,
)

DISCLAIMER = (
    "Readings follow di Mino's Semitic decipherment. Confidence tiers apply. "
    "This report ranks proposal evidence; it does not update the sign registry."
)

IDEOGRAMS = {
    "GRA", "OLE", "VIN", "FIC", "CYP", "ARE", "AUR", "BOS", "CAP", "CER",
    "EQU", "FAR", "HOR", "OVI", "SUS", "TELA", "LUNA", "SOL", "LANA", "VAS",
    "VIR",
}

_SUBSCRIPT_MAP = str.maketrans("₂₃₄₅", "2345")
_SIGN_SPLIT_RE = re.compile(r"[-+]")
_SIGN_PART_RE = re.compile(r"([-+])")


def load_corpus() -> dict:
    """Load corpus.json through the shared local cache."""
    return data_cache.corpus()


def load_registry() -> dict:
    """Load the unified sign registry."""
    return json.loads(require(REGISTRY_PATH, REGISTRY_PATH.name).read_text(encoding="utf-8"))


def load_sign_values() -> dict:
    """Load the sign value decomposition table."""
    return data_cache.sign_values()


def load_evolution_map() -> dict:
    """Load the CH-to-LA-to-LB evolution map if present."""
    if not EVOLUTION_PATH.exists():
        return {"signs": []}
    return json.loads(EVOLUTION_PATH.read_text(encoding="utf-8"))


def load_rejected_values() -> dict[str, list[dict]]:
    """Load rejected sign values keyed by corpus sign form, with keys and values normalized."""
    if not REJECTED_VALUES_PATH.exists():
        print(f"warning: {REJECTED_VALUES_PATH.name} not found; rejected values will be ranked", file=sys.stderr)
        return {}
    rejected = json.loads(REJECTED_VALUES_PATH.read_text(encoding="utf-8")).get("rejected", {})
    return {
        normalize_target_sign(sign)["corpus_form"]: [{**r, "value": r["value"].lower()} for r in records]
        for sign, records in rejected.items()
    }


def apply_rejected_values(
    candidates: list[dict],
    target_corpus_sign: str,
    rejected: dict[str, list[dict]],
    include_rejected: bool,
) -> tuple[list[dict], list[dict]]:
    """Drop rejected readings for the target sign, or tag them when include_rejected is set."""
    records = {r["value"]: r for r in rejected.get(target_corpus_sign, [])}
    kept: list[dict] = []
    excluded: list[dict] = []
    for candidate in candidates:
        record = records.get(candidate["value"])
        if record is None:
            kept.append(candidate)
        elif include_rejected:
            kept.append({**candidate, "rejected": record})
        else:
            excluded.append(record)
    return kept, excluded


def rejected_class_phonemes(
    target_corpus_sign: str,
    rejected: dict[str, list[dict]],
    sign_values: dict,
) -> dict[str, dict]:
    """Map each phoneme in a rejected CV value's neutralization class to its rejection record."""
    classes = sign_values.get("neutralization_classes", {})
    by_phoneme: dict[str, dict] = {}
    for record in rejected.get(target_corpus_sign, []):
        parsed = parse_candidate_value(record["value"])
        consonant = parsed[0] if parsed else None
        if not consonant:
            continue
        class_name = neutralization_class_for(consonant, sign_values)
        phonemes = classes[class_name]["phonemes"] if class_name else [consonant]
        for phoneme in phonemes:
            by_phoneme.setdefault(normalize_phonemes(phoneme), record)
    return by_phoneme


def normalize_target_sign(raw: str) -> dict[str, str]:
    """Normalize target forms such as *301, 301, A301, and AB301."""
    if raw is None or not str(raw).strip():
        raise ValueError("target sign must not be empty")

    original = str(raw).strip()
    value = original.upper().lstrip("*").translate(_SUBSCRIPT_MAP)

    if value.isdigit():
        return {
            "input": original,
            "corpus_form": f"*{value}",
            "registry_form": f"A{value}",
            "number": value,
            "kind": "undeciphered_number",
        }

    match_alpha = re.fullmatch(r"(\d+[A-Z]+)", value)
    if match_alpha:
        num_part = re.match(r"\d+", value).group()
        return {
            "input": original,
            "corpus_form": f"*{value}",
            "registry_form": f"A{value}",
            "number": num_part,
            "kind": "undeciphered_alphanumeric",
        }

    match = re.fullmatch(r"A(\d+)", value)
    if match:
        number = match.group(1)
        return {
            "input": original,
            "corpus_form": f"*{number}",
            "registry_form": f"A{number}",
            "number": number,
            "kind": "a_number",
        }

    match = re.fullmatch(r"AB(\d+)", value)
    if match:
        number = match.group(1)
        registry_prefix = "A" if int(number) >= 300 else "AB"
        corpus_form = f"*{number}" if registry_prefix == "A" else f"AB{number}"
        return {
            "input": original,
            "corpus_form": corpus_form,
            "registry_form": f"{registry_prefix}{number}",
            "number": number,
            "kind": "ab_number",
        }

    return {
        "input": original,
        "corpus_form": value,
        "registry_form": value,
        "number": "",
        "kind": "name",
    }


def _target_in_compound(word: str, target_corpus_sign: str) -> bool:
    """Check if target sign participates in a plus-compound within the word."""
    if "+" not in word:
        return False
    parts = _SIGN_PART_RE.split(word)
    for i, part in enumerate(parts):
        if token_matches_target(part, target_corpus_sign) and (
            (i > 0 and parts[i - 1] == "+") or (i < len(parts) - 1 and parts[i + 1] == "+")
        ):
            return True
    return False


def find_target_contexts(corpus: dict, target_corpus_sign: str) -> list[dict]:
    """Return every corpus word containing target_corpus_sign as a sign token."""
    contexts = []
    for tablet_id, entry in corpus.items():
        words = entry.get("transliteratedWords", [])
        if not isinstance(words, list):
            continue
        for index, word in enumerate(words):
            if not isinstance(word, str) or not word.strip() or word == "\n":
                continue
            tokens = split_sign_tokens(word)
            positions = [
                i for i, token in enumerate(tokens)
                if token_matches_target(token, target_corpus_sign)
            ]
            if not positions:
                continue
            first = positions[0]
            contexts.append({
                "tablet_id": tablet_id,
                "word": word,
                "word_index": index,
                "site": entry.get("site", ""),
                "support": entry.get("support", ""),
                "context": entry.get("context", ""),
                "findspot": entry.get("findspot", ""),
                "tokens": tokens,
                "target_positions": positions,
                "left_neighbor": tokens[first - 1] if first > 0 else None,
                "right_neighbor": tokens[first + 1] if first < len(tokens) - 1 else None,
                "word_position": word_position(positions, len(tokens)),
                "is_compound_token": _target_in_compound(word, target_corpus_sign),
            })
    return contexts


def annotate_neighbors(contexts: list[dict], sign_values: dict, registry: dict) -> list[dict]:
    """Attach known-sign annotations to target neighbors."""
    annotated = []
    for context in contexts:
        item = dict(context)
        pairs = []
        for pos in context.get("target_positions", []):
            left = context["tokens"][pos - 1] if pos > 0 else None
            right = context["tokens"][pos + 1] if pos < len(context["tokens"]) - 1 else None
            pairs.append({
                "position": pos,
                "left": annotate_sign(left, sign_values, registry),
                "right": annotate_sign(right, sign_values, registry),
            })
        item["left_annotation"] = annotate_sign(context.get("left_neighbor"), sign_values, registry)
        item["right_annotation"] = annotate_sign(context.get("right_neighbor"), sign_values, registry)
        item["neighbor_pairs"] = pairs
        annotated.append(item)
    return annotated


def lookup_origin_evidence(registry_form: str, registry: dict, evolution_map: dict) -> dict:
    """Look up registry metadata and CH-origin evidence for a sign."""
    registry_record = registry_by_ab(registry).get(registry_form)
    base = {
        "registry_form": registry_form,
        "registry_found": registry_record is not None,
    }
    if registry_record:
        rendering = registry_record.get("rendering", {})
        base["registry"] = {
            "ab_number": registry_record.get("ab_number", ""),
            "name": registry_record.get("name", ""),
            "tier": rendering.get("tier"),
            "sigla_image": rendering.get("sigla_image"),
            "sigla_url": rendering.get("sigla_url"),
            "readings_count": len(registry_record.get("readings", [])),
        }

    for sign in evolution_map.get("signs", []):
        if sign.get("linear_a", {}).get("ab_number") == registry_form:
            return {
                **base,
                "status": "found",
                "cretan_hieroglyphic": sign.get("cretan_hieroglyphic"),
                "proto_sinaitic": sign.get("proto_sinaitic"),
                "linear_b": sign.get("linear_b"),
                "semantic_context": sign.get("semantic_context"),
                "graphic_tendencies": sign.get("graphic_tendencies", []),
                "phonetic_value": sign.get("phonetic_value"),
                "source_id": sign.get("id"),
            }

    if registry_record and registry_record.get("evolution"):
        evo = registry_record["evolution"]
        return {
            **base,
            "status": "found",
            "cretan_hieroglyphic": evo.get("cretan_hieroglyphic"),
            "proto_sinaitic": evo.get("proto_sinaitic"),
            "linear_b": evo.get("linear_b"),
            "semantic_context": registry_record.get("semantic_context"),
            "graphic_tendencies": evo.get("graphic_tendencies", []),
            "phonetic_value": registry_record.get("name") or None,
            "source_id": "sign-registry",
        }

    return {
        **base,
        "status": "not_found",
        "note": "No CH-origin entry for this target exists in current local data.",
    }


def generate_candidate_values(
    sign_values: dict,
    origin_evidence: dict,
    allowed_values: list[str] | None = None,
) -> list[dict]:
    """Build candidate CV readings from known sign values or user input."""
    restricted = allowed_values is not None
    raw_values = allowed_values or []
    candidates: dict[tuple[str | None, str], dict] = {}

    if restricted:
        for value in raw_values:
            parsed = parse_candidate_value(value)
            if parsed is None:
                continue
            consonant, vowel = parsed
            key = (consonant, vowel)
            candidates[key] = candidate_record(
                value=value_from_cv(consonant, vowel),
                consonant=consonant,
                vowel=vowel,
                source="user_supplied",
                sign_name=None,
                origin_evidence=origin_evidence,
                sign_values=sign_values,
            )
    else:
        for sign_name, entry in sign_values.get("signs", {}).items():
            primary = entry.get("primary", {})
            consonant = primary.get("consonant")
            vowel = primary.get("vowel")
            if not vowel:
                continue
            key = (consonant, vowel)
            if key in candidates:
                continue
            candidates[key] = candidate_record(
                value=value_from_cv(consonant, vowel),
                consonant=consonant,
                vowel=vowel,
                source="sign_values",
                sign_name=sign_name,
                origin_evidence=origin_evidence,
                sign_values=sign_values,
            )

    return sorted(candidates.values(), key=lambda c: (c["consonant"] or "", c["vowel"]))


def substitute_candidate(word: str, target_corpus_sign: str, candidate_value: str) -> str:
    """Replace exact target sign tokens in a word with a candidate value."""
    parts = _SIGN_PART_RE.split(word)
    output = []
    replacement = candidate_value.upper()
    for part in parts:
        if part in {"-", "+"}:
            output.append(part)
        elif token_matches_target(part, target_corpus_sign):
            output.append(replacement)
        else:
            output.append(part)
    return "".join(output)


def extract_candidate_skeleton(substituted_word: str, candidate_value: str) -> dict:
    """Extract a skeleton from a substituted word, tolerating plus compounds."""
    tokens = split_sign_tokens(substituted_word)
    consonants = []
    analyzed = []
    skipped = []

    cv_upper = candidate_value.upper()
    candidate_decomp = _lookup_sign(cv_upper)
    if not candidate_decomp:
        c = "".join(ch for ch in candidate_value.lower() if ch not in "aeiou")
        v = next((ch for ch in candidate_value.lower() if ch in "aeiou"), "")
        candidate_decomp = (c, v)

    for token in tokens:
        clean = clean_sign_token(token)
        if not clean:
            continue
        decomp = _lookup_sign(clean)
        if not decomp and clean == cv_upper:
            decomp = candidate_decomp
        if decomp:
            analyzed.append(clean)
            if decomp[0]:
                consonants.append(decomp[0])
        elif is_non_syllabic(clean):
            skipped.append(clean)
        else:
            skipped.append(clean)

    total = len(analyzed) + len(skipped)
    coverage = len(analyzed) / total if total else 0.0
    return {
        "word": substituted_word,
        "skeleton": "".join(consonants),
        "tokens": tokens,
        "analyzed_tokens": analyzed,
        "skipped_tokens": skipped,
        "analyzed_count": len(analyzed),
        "skipped_count": len(skipped),
        "total_tokens": total,
        "coverage": round(coverage, 3),
    }


def score_candidate_against_contexts(candidate: dict, contexts: list[dict], options: dict) -> dict:
    """Substitute a candidate into every context and score root coherence."""
    root_cache = options.setdefault("_root_cache", {})
    skeleton_cache = options.setdefault("_skeleton_cache", {})
    min_coverage = float(options.get("min_coverage", 0.0))
    target = options["target_corpus_sign"]

    word_results = []
    best_scores = []
    coverages = []
    root_counter: Counter[str] = Counter()
    tablets_by_root: dict[str, set[str]] = {}

    for context in contexts:
        substituted = substitute_candidate(context["word"], target, candidate["value"])
        skeleton_key = (substituted, candidate["value"])
        if skeleton_key not in skeleton_cache:
            skeleton_cache[skeleton_key] = extract_candidate_skeleton(substituted, candidate["value"])
        skeleton_info = skeleton_cache[skeleton_key]
        coverages.append(skeleton_info["coverage"])

        matches: list[dict] = []
        if skeleton_info["skeleton"] and skeleton_info["coverage"] >= min_coverage:
            skel = skeleton_info["skeleton"]
            if skel not in root_cache:
                root_cache[skel] = root_matches_for_skeleton(skel, options)
            matches = root_cache[skel]

        best_score = max((m.get("score", 0.0) for m in matches), default=0.0)
        if best_score:
            best_scores.append(best_score)
        for match in matches[:3]:
            root = str(match.get("root", ""))
            if root:
                root_counter[root] += 1
                tablets_by_root.setdefault(root, set()).add(context["tablet_id"])

        word_results.append({
            "tablet_id": context["tablet_id"],
            "original_word": context["word"],
            "substituted_word": substituted,
            "skeleton": skeleton_info["skeleton"],
            "coverage": skeleton_info["coverage"],
            "matches": matches[:3],
            "best_score": round(best_score, 3),
        })

    coverage_score = sum(coverages) / len(coverages) if coverages else 0.0
    avg_best = sum(best_scores) / len(best_scores) if best_scores else 0.0
    repeated_roots = sum(1 for count in root_counter.values() if count >= 2)
    repeated_tablets = sum(len(tablets) for tablets in tablets_by_root.values() if len(tablets) >= 2)
    coherence_bonus = min(0.25, repeated_roots * 0.05 + repeated_tablets * 0.01)
    cognate_score = min(1.0, avg_best + coherence_bonus)

    no_skeleton = sum(1 for item in word_results if not item["skeleton"])
    one_letter = sum(1 for item in word_results if len(item["skeleton"]) == 1)
    bicon_low = sum(
        1 for item in word_results
        if len(item["skeleton"]) == 2 and item["best_score"] < 0.2
    )
    total = len(word_results) or 1
    penalty_score = min(1.0, (no_skeleton / total) + 0.5 * (one_letter / total) + 0.2 * (bicon_low / total))

    best_matches = []
    for root, count in root_counter.most_common(5):
        first = next(
            match for item in word_results for match in item["matches"]
            if match.get("root") == root
        )
        best_matches.append({
            "root": root,
            "count": count,
            "meaning": first.get("meaning", ""),
            "language": first.get("language") or first.get("source_lang") or "Proto-Semitic",
            "score": first.get("score", 0.0),
        })

    return {
        "cognate_score": round(cognate_score, 3),
        "coverage_score": round(coverage_score, 3),
        "penalty_score": round(penalty_score, 3),
        "word_results": word_results,
        "best_matches": best_matches,
        "tested_contexts": len(word_results),
    }


def rank_candidates(
    candidates: list[dict],
    contexts: list[dict],
    origin_evidence: dict,
    options: dict,
) -> list[dict]:
    """Rank candidates using transparent weighted score components."""
    pair_inventory = options.get("known_pair_inventory", set())
    ranked = []
    for candidate in candidates:
        positional_score = positional_score_for_candidate(candidate, contexts, pair_inventory)
        scored = score_candidate_against_contexts(candidate, contexts, options)
        origin_score = candidate.get("origin_score", 0.5)
        final = (
            0.30 * positional_score
            + 0.15 * origin_score
            + 0.40 * scored["cognate_score"]
            + 0.10 * scored["coverage_score"]
            - 0.15 * scored["penalty_score"]
        )
        row = {
            **candidate,
            "final_score": round(final, 3),
            "score_components": {
                "positional_score": round(positional_score, 3),
                "origin_score": round(origin_score, 3),
                "cognate_score": scored["cognate_score"],
                "coverage_score": scored["coverage_score"],
                "penalty_score": scored["penalty_score"],
            },
            "best_matches": scored["best_matches"],
            "context_tests": scored["word_results"],
            "rationale": candidate_rationale(candidate, origin_evidence, scored),
        }
        min_cov = float(options.get("min_coverage", 0.0))
        if min_cov > 0.0:
            analyzable = sum(
                1 for wr in scored["word_results"] if wr["coverage"] >= min_cov
            )
            total = len(scored["word_results"]) or 1
            if analyzable / total < 0.5:
                continue
        ranked.append(row)

    ranked.sort(key=lambda item: (-item["final_score"], item["value"]))
    return ranked


def propose_sign_value(target: str, options: dict) -> dict:
    """Run the full sign-value proposal pipeline."""
    corpus = load_corpus()
    registry = load_registry()
    sign_values = load_sign_values()
    evolution = load_evolution_map()

    normalized = normalize_target_sign(target)
    registry_record = resolve_registry_record(normalized, registry)
    if registry_record and registry_record.get("name") and not normalized["corpus_form"].startswith("*"):
        normalized["corpus_form"] = registry_record["name"].upper()
    normalized["already_deciphered"] = bool(registry_record and registry_record.get("readings"))

    contexts = find_target_contexts(corpus, normalized["corpus_form"])
    annotated_contexts = annotate_neighbors(contexts, sign_values, registry)
    origin = lookup_origin_evidence(normalized["registry_form"], registry, evolution)
    registry_summary = summarize_registry_record(registry_record, normalized["registry_form"])

    result_options = {
        "top": options.get("top", 10),
        "limit_contexts": options.get("limit_contexts", 20),
        "include_luwian": bool(options.get("include_luwian", False)),
        "include_egyptian": bool(options.get("include_egyptian", False)),
        "max_distance": float(options.get("max_distance", 1.5)),
        "min_coverage": float(options.get("min_coverage", 0.0)),
        "candidates": options.get("candidates"),
        "include_rejected": bool(options.get("include_rejected", False)),
    }

    result = {
        "target": normalized,
        "registry": registry_summary,
        "origin_evidence": origin,
        "corpus_evidence": summarize_contexts(annotated_contexts, options.get("limit_contexts", 20)),
        "candidate_generation": {
            "total_candidates_generated": 0,
            "total_candidates_tested": 0,
            "total_candidates_returned": 0,
            "restricted_by_user": options.get("candidates") is not None,
            "filtered_by_min_coverage": 0,
            "excluded_rejected": [],
        },
        "candidates": [],
        "options": result_options,
        "disclaimer": DISCLAIMER,
    }

    if normalized["already_deciphered"]:
        result["candidate_generation"]["note"] = "Target already has registry readings; no proposal ranking was generated."
        return result

    candidate_values = generate_candidate_values(sign_values, origin, options.get("candidates"))
    total_generated = len(candidate_values)
    rejected = load_rejected_values()
    candidate_values, excluded = apply_rejected_values(
        candidate_values,
        normalized["corpus_form"],
        rejected,
        result_options["include_rejected"],
    )
    result["candidate_generation"]["excluded_rejected"] = excluded
    ranking_options = {
        **result_options,
        "target_corpus_sign": normalized["corpus_form"],
        "roots": _prepare_root_entries(data_cache.semitic_roots()),
        "known_pair_inventory": known_pair_inventory(corpus, sign_values),
    }
    ranked = rank_candidates(candidate_values, annotated_contexts, origin, ranking_options)
    top_n = int(options.get("top", 10))
    result["candidate_generation"].update({
        "total_candidates_generated": total_generated,
        "total_candidates_tested": len(candidate_values),
        "total_candidates_returned": len(ranked[:top_n]),
        "filtered_by_min_coverage": len(candidate_values) - len(ranked),
    })
    result["candidates"] = ranked[:top_n]

    if options.get("polyvalent"):
        msm = load_missing_sound_map()
        poly_candidates = generate_polyvalent_candidates(origin, msm)
        poly_options = {
            **ranking_options,
            "grid_consonants": grid_consonant_inventory(sign_values),
        }
        poly_ranked = rank_polyvalent_candidates(
            poly_candidates, annotated_contexts, poly_options,
        )
        poly_heuristics = compute_polyvalent_heuristics(annotated_contexts, sign_values)
        class_records = rejected_class_phonemes(normalized["corpus_form"], rejected, sign_values)
        for candidate in poly_ranked:
            record = class_records.get(normalize_phonemes(candidate["consonant"]))
            if record is not None:
                candidate["rejected_class"] = record
        result["polyvalent_candidates"] = poly_ranked[:top_n]
        result["polyvalent_heuristics"] = poly_heuristics

    return result


def format_report(result: dict) -> str:
    """Format a human-readable proposal report."""
    target = result["target"]
    registry = result["registry"]
    corpus = result["corpus_evidence"]
    origin = result["origin_evidence"]
    lines = [
        "Linear A Sign Value Proposal",
        "=" * 60,
        DISCLAIMER,
        "",
        f"Target: {target['input']} -> corpus {target['corpus_form']}, registry {target['registry_form']}",
        f"Registry: {'found' if registry.get('found') else 'not found'}, readings={registry.get('readings_count', 0)}",
    ]
    if target.get("already_deciphered"):
        readings = ", ".join(r.get("value", "") for r in registry.get("readings", []))
        lines.append(f"Already deciphered in registry: {readings or 'yes'}")
    if registry.get("sigla_image"):
        lines.append(f"SigLA image: {registry['sigla_image']}")
    lines.extend([
        f"Origin evidence: {origin.get('status', 'unknown')}",
        f"Corpus contexts: {corpus['total_contexts']} across {len(corpus['tablets'])} tablets",
        "",
        "Representative Contexts",
        "-" * 60,
    ])
    if corpus["examples"]:
        for example in corpus["examples"]:
            left = example.get("left_neighbor") or "."
            right = example.get("right_neighbor") or "."
            lines.append(
                f"{example['tablet_id']:<12} {example['word']:<28} "
                f"pos={example['word_position']:<8} left={left:<8} right={right:<8} {example.get('site', '')}"
            )
    else:
        lines.append("No corpus contexts found.")

    lines.extend(["", "Ranked Candidates", "-" * 60])
    if result["candidates"]:
        lines.append(
            f"{'Value':<7} {'Final':>6} {'Pos':>5} {'Orig':>5} {'Cog':>5} "
            f"{'Cov':>5} {'Pen':>5}  Best roots"
        )
        for candidate in result["candidates"]:
            comp = candidate["score_components"]
            roots = ", ".join(
                f"{m['root']}({m['count']})" for m in candidate.get("best_matches", [])[:3]
            ) or "-"
            tag = f"  [REJECTED: {candidate['rejected']['decision']}]" if "rejected" in candidate else ""
            lines.append(
                f"{candidate['value']:<7} {candidate['final_score']:>6.3f} "
                f"{comp['positional_score']:>5.2f} {comp['origin_score']:>5.2f} "
                f"{comp['cognate_score']:>5.2f} {comp['coverage_score']:>5.2f} "
                f"{comp['penalty_score']:>5.2f}  {roots}{tag}"
            )
    else:
        note = result.get("candidate_generation", {}).get("note")
        lines.append(note or "No candidates passed the configured filters.")
    excluded = result.get("candidate_generation", {}).get("excluded_rejected", [])
    if excluded:
        lines.append(
            "Excluded (rejected): "
            + ", ".join(f"{e['value']} ({e['decision']})" for e in excluded)
            + "; pass --include-rejected to score them"
        )

    if "polyvalent_candidates" in result:
        lines.extend(format_polyvalent_section(result))

    return "\n".join(lines)


def format_json(result: dict) -> str:
    """Return stable JSON output."""
    return json.dumps(result, ensure_ascii=False, indent=2)


POLYVALENT_VOWELS = ("a", "e", "i", "o", "u")


def load_missing_sound_map() -> dict:
    """Load missing_sound_map.json for polyvalent candidate sourcing."""
    return json.loads(require(MISSING_SOUND_MAP_PATH, MISSING_SOUND_MAP_PATH.name).read_text(encoding="utf-8"))


def grid_consonant_inventory(sign_values: dict) -> set[str]:
    """Distinct consonant classes carried by resolved signs (primary + alternates)."""
    consonants: set[str] = set()
    for entry in sign_values.get("signs", {}).values():
        if not isinstance(entry, dict):
            continue
        primary = entry.get("primary") or {}
        if primary.get("consonant"):
            consonants.add(str(primary["consonant"]).lower())
        for alt in entry.get("alternates", []) or []:
            if isinstance(alt, dict) and alt.get("consonant"):
                consonants.add(str(alt["consonant"]).lower())
    return consonants


def get_unresolved_consonants(missing_sound_map: dict) -> list[dict]:
    """Extract consonants from PS inventory that lack dedicated Linear A signs."""
    candidates = []
    for gap in missing_sound_map.get("open_gaps", []):
        if gap.get("status") != "LIKELY_NEUTRALIZED":
            continue
        for phoneme in gap.get("phonemes", []):
            candidates.append({
                "consonant": phoneme,
                "gap_id": gap["gap_id"],
                "description": gap.get("description", ""),
                "neutralization": gap.get("likely_script_strategy", ""),
            })
    return candidates


def generate_polyvalent_candidates(
    origin_evidence: dict,
    missing_sound_map: dict,
) -> list[dict]:
    """Build polyvalent consonant candidates from unresolved PS gaps."""
    unresolved = get_unresolved_consonants(missing_sound_map)
    candidates = []
    for entry in unresolved:
        c = entry["consonant"]
        origin_score = polyvalent_origin_score(c, origin_evidence)
        candidates.append({
            "value": f"/{c}/",
            "consonant": c,
            "vowel": "*",
            "type": "polyvalent",
            "source": "missing_sound_map",
            "source_sign": None,
            "gap_id": entry["gap_id"],
            "description": entry["description"],
            "neutralization": entry["neutralization"],
            "base_prior": round(origin_score, 3),
            "origin_score": round(origin_score, 3),
            "neutralization_class": None,
        })
    return candidates


def polyvalent_origin_score(consonant: str, origin_evidence: dict) -> float:
    """Score CH-origin evidence for a consonant class (not a specific CV)."""
    if origin_evidence.get("status") != "found":
        return 0.5
    ps_letter = str((origin_evidence.get("proto_sinaitic") or {}).get("letter") or "").lower()
    ps_consonant = proto_sinaitic_consonant(ps_letter)
    if ps_consonant and ps_consonant == consonant:
        return 0.9
    return 0.5


def polyvalent_collision_test(
    consonant: str,
    contexts: list[dict],
    pair_inventory: set[tuple[str, str]],
    grid_consonants: set[str] | None = None,
) -> dict:
    """Test bigram collisions for all 5 vowel variants of a consonant.

    Only informative when the consonant already has CV signs in the resolved
    grid: gap consonants (no existing signs) cannot appear in any attested
    bigram, so a perfect collision-free score would be tautological — those
    return NOT_APPLICABLE instead.
    """
    if grid_consonants is not None and consonant.lower() not in grid_consonants:
        return {
            "status": "NOT_APPLICABLE_NO_EXISTING_CV_SIGNS",
            "note": f"/{consonant}/ has no resolved CV signs in the grid; no attested "
                    "bigram can contain it, so collision-freedom is vacuous by construction.",
            "collisions_by_vowel": None,
            "total_collisions": None,
            "free_variants": None,
            "collision_freedom": None,
        }
    collisions: dict[str, list[str]] = {}
    total_collisions = 0
    for vowel in POLYVALENT_VOWELS:
        cv_upper = f"{consonant}{vowel}".upper()
        variant_hits: list[str] = []
        for context in contexts:
            for pair in context.get("neighbor_pairs", []):
                left = pair["left"]
                right = pair["right"]
                if left.get("known") and (left["sign"], cv_upper) in pair_inventory:
                    variant_hits.append(f"{left['sign']}-{cv_upper}")
                if right.get("known") and (cv_upper, right["sign"]) in pair_inventory:
                    variant_hits.append(f"{cv_upper}-{right['sign']}")
        collisions[vowel] = variant_hits
        total_collisions += len(variant_hits)

    free_variants = sum(1 for v in collisions.values() if not v)
    return {
        "status": "TESTED",
        "collisions_by_vowel": collisions,
        "total_collisions": total_collisions,
        "free_variants": free_variants,
        "collision_freedom": round(free_variants / len(POLYVALENT_VOWELS), 3),
    }


def score_polyvalent_candidate(
    candidate: dict,
    contexts: list[dict],
    options: dict,
    pair_inventory: set[tuple[str, str]],
) -> dict:
    """Score a polyvalent consonant candidate across all contexts."""
    c = candidate["consonant"]
    substitute_value = f"{c}a"
    fixed_candidate = {**candidate, "value": substitute_value}
    scored = score_candidate_against_contexts(fixed_candidate, contexts, options)

    collision_info = polyvalent_collision_test(
        c, contexts, pair_inventory, options.get("grid_consonants"),
    )

    positional_score = 0.5
    origin_score = candidate.get("origin_score", 0.5)

    final = (
        0.30 * positional_score
        + 0.15 * origin_score
        + 0.40 * scored["cognate_score"]
        + 0.10 * scored["coverage_score"]
        - 0.15 * scored["penalty_score"]
    )

    return {
        **candidate,
        "final_score": round(final, 3),
        "score_components": {
            "positional_score": round(positional_score, 3),
            "origin_score": round(origin_score, 3),
            "cognate_score": scored["cognate_score"],
            "coverage_score": scored["coverage_score"],
            "penalty_score": scored["penalty_score"],
        },
        "collision_test": collision_info,
        "best_matches": scored["best_matches"],
        "context_tests": scored["word_results"],
        "rationale": polyvalent_rationale(candidate, collision_info, scored),
    }


def polyvalent_rationale(candidate: dict, collision_info: dict, scored: dict) -> str:
    """Build a human-readable rationale for a polyvalent candidate."""
    pieces = [f"polyvalent /{candidate['consonant']}/ from {candidate['gap_id']}"]
    if collision_info.get("status") == "NOT_APPLICABLE_NO_EXISTING_CV_SIGNS":
        pieces.append("collision test n/a (no existing CV signs for this consonant)")
    else:
        pieces.append(f"{collision_info['free_variants']}/5 vowel variants collision-free")
    if scored.get("best_matches"):
        roots = ", ".join(m["root"] for m in scored["best_matches"][:2])
        pieces.append(f"best roots: {roots}")
    return "; ".join(pieces)


def rank_polyvalent_candidates(
    candidates: list[dict],
    contexts: list[dict],
    options: dict,
) -> list[dict]:
    """Rank polyvalent consonant candidates by score."""
    pair_inventory = options.get("known_pair_inventory", set())
    ranked = []
    for candidate in candidates:
        scored = score_polyvalent_candidate(candidate, contexts, options, pair_inventory)
        ranked.append(scored)
    ranked.sort(key=lambda item: (-item["final_score"], item["value"]))
    # Exact ties on (final, cognate) mean the skeleton scorer cannot separate the
    # consonants (guttural-transparent distance collapses e.g. /g/ and /ġ/).
    by_key: dict[tuple, list[dict]] = {}
    for item in ranked:
        by_key.setdefault(
            (item["final_score"], item["score_components"]["cognate_score"]), []
        ).append(item)
    for group in by_key.values():
        if len(group) > 1:
            members = "/".join(i["consonant"] for i in group)
            for item in group:
                item["tie_note"] = (
                    f"exact tie among /{members}/ — indistinguishable under "
                    "guttural-transparent skeleton distance"
                )
    return ranked


def compute_polyvalent_heuristics(contexts: list[dict], sign_values: dict | None = None) -> dict:
    """Detect the WORD-FINAL polyvalent subtype (*321-type consonant absorbers).

    Scope: this signature targets signs that behave like bare consonants in
    word-final position after diverse onsets. Position-general polyvalents
    (*301-type, occurring in all positions) are OUT OF SCOPE and may
    legitimately score LOW here — a LOW is "not the word-final subtype",
    never "not polyvalent".

    Diversity is a saturation measure — unique left-consonant classes over
    the smaller of (observed contexts, classes available in the resolved
    grid) — so high-frequency signs are not punished by the type/token
    decline that a raw unique/total ratio produces.
    """
    scope_note = (
        "Detects the word-final consonant-absorber subtype (*321-type). "
        "Position-general polyvalents (*301-type) are out of scope and may score LOW."
    )
    if not contexts:
        return {
            "scope": scope_note,
            "word_final_rate": 0.0,
            "consonant_diversity": 0.0,
            "word_final_polyvalent_signature": 0.0,
            "interpretation": "no contexts",
        }

    final_count = sum(1 for c in contexts if c.get("word_position") == "final")
    word_final_rate = final_count / len(contexts)

    left_consonants: set[str] = set()
    left_total = 0
    for c in contexts:
        left = c.get("left_annotation") or {}
        if left.get("known") and left.get("consonant"):
            left_consonants.add(left["consonant"])
            left_total += 1
    class_count = len(grid_consonant_inventory(sign_values)) if sign_values else 0
    saturation_ceiling = max(1, min(left_total, class_count) if class_count else left_total)
    consonant_diversity = len(left_consonants) / saturation_ceiling

    signature = 0.50 * word_final_rate + 0.50 * consonant_diversity

    if signature >= 0.7:
        interpretation = "HIGH — consistent with a word-final polyvalent (*321-type) sign"
    elif signature >= 0.4:
        interpretation = "MODERATE — some word-final polyvalent characteristics"
    else:
        interpretation = ("LOW — not the word-final subtype (fixed CV, or a "
                          "position-general polyvalent outside this detector's scope)")
    if left_total < 3:
        interpretation += f" [LOW CONFIDENCE: only {left_total} known left context(s)]"

    return {
        "scope": scope_note,
        "word_final_rate": round(word_final_rate, 3),
        "consonant_diversity": round(consonant_diversity, 3),
        "unique_left_consonants": len(left_consonants),
        "left_contexts_with_known_consonant": left_total,
        "grid_consonant_classes": class_count,
        "word_final_polyvalent_signature": round(signature, 3),
        "interpretation": interpretation,
    }


def format_polyvalent_section(result: dict) -> list[str]:
    """Format the polyvalent candidates section for human-readable output."""
    lines: list[str] = []
    heuristics = result.get("polyvalent_heuristics", {})
    candidates = result.get("polyvalent_candidates", [])

    lines.extend([
        "",
        "Polyvalent Consonant Candidates (word-final *321-type detector)",
        "-" * 60,
        (f"Heuristics: word_final={heuristics.get('word_final_rate', 0):.2f}  "
         f"cons_diversity={heuristics.get('consonant_diversity', 0):.2f}  "
         f"signature={heuristics.get('word_final_polyvalent_signature', 0):.2f}"),
        f"            {heuristics.get('interpretation', '')}",
        "  NOTE: scores below use a fixed neutral positional (0.5) and are NOT",
        "  comparable to the fixed-CV candidate scores above.",
        "",
    ])

    if candidates:
        lines.append(
            f"{'Cons.':<8} {'Final':>6} {'Cog':>5} {'Cov':>5} "
            f"{'Pen':>5} {'Free':>5}  Best roots"
        )
        for candidate in candidates:
            comp = candidate["score_components"]
            ct = candidate.get("collision_test", {})
            free = "n/a" if ct.get("status") == "NOT_APPLICABLE_NO_EXISTING_CV_SIGNS" \
                else f"{ct.get('free_variants', 0):>3}/5"
            roots = ", ".join(
                f"{m['root']}({m['count']})" for m in candidate.get("best_matches", [])[:3]
            ) or "-"
            lines.append(
                f"{candidate['value']:<8} {candidate['final_score']:>6.3f} "
                f"{comp['cognate_score']:>5.2f} {comp['coverage_score']:>5.2f} "
                f"{comp['penalty_score']:>5.2f} {free:>5}  {roots}"
            )
            if candidate.get("rejected_class"):
                record = candidate["rejected_class"]
                lines.append(
                    f"         ^ [REJECTED-CLASS: {record['value']}, {record['decision']}] "
                    "same neutralization class as a rejected CV value"
                )
            if candidate.get("tie_note"):
                lines.append(f"         ^ {candidate['tie_note']}")
    else:
        lines.append("No polyvalent candidates generated.")

    return lines


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Propose CV values for undeciphered Linear A signs")
    parser.add_argument("target", help="Target sign, e.g. *301, 301, A301, AB301")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a human report")
    parser.add_argument("--top", type=int, default=10, help="Number of candidates to return")
    parser.add_argument("--limit-contexts", type=int, default=20, help="Context examples in human output")
    parser.add_argument("--candidates", help="Comma-separated candidate CV values to test")
    parser.add_argument("--include-luwian", action="store_true", help="Include Luwian root scoring")
    parser.add_argument("--include-egyptian", action="store_true", help="Include Egyptian root scoring")
    parser.add_argument("--max-distance", type=float, default=1.5, help="Maximum root distance")
    parser.add_argument("--min-coverage", type=float, default=0.0, help="Minimum average analysis coverage")
    parser.add_argument("--polyvalent", action="store_true",
                        help="Also generate polyvalent consonant candidates from unresolved phonemic gaps")
    parser.add_argument("--include-rejected", action="store_true",
                        help="Score values listed in data/rejected_sign_values.json, tagged REJECTED")
    args = parser.parse_args()

    allowed = None
    if args.candidates:
        allowed = [item.strip().lower() for item in args.candidates.split(",") if item.strip()]

    options = {
        "top": args.top,
        "limit_contexts": args.limit_contexts,
        "candidates": allowed,
        "include_luwian": args.include_luwian,
        "include_egyptian": args.include_egyptian,
        "max_distance": args.max_distance,
        "min_coverage": args.min_coverage,
        "polyvalent": args.polyvalent,
        "include_rejected": args.include_rejected,
    }

    try:
        result = propose_sign_value(args.target, options)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print(format_json(result) if args.json else format_report(result))


def split_sign_tokens(word: str) -> list[str]:
    return [part for part in _SIGN_SPLIT_RE.split(word) if part.strip()]


def clean_sign_token(token: str | None) -> str:
    if token is None:
        return ""
    cleaned = str(token).strip().translate(_SUBSCRIPT_MAP)
    cleaned = cleaned.strip("[]{}()?")
    cleaned = cleaned.rstrip(".,;:")
    return cleaned.upper()


def token_matches_target(token: str, target_corpus_sign: str) -> bool:
    return clean_sign_token(token) == clean_sign_token(target_corpus_sign)


def word_position(positions: list[int], token_count: int) -> str:
    if token_count <= 1:
        return "isolated"
    if any(0 < pos < token_count - 1 for pos in positions):
        return "medial"
    if any(pos == 0 for pos in positions) and not any(pos == token_count - 1 for pos in positions):
        return "initial"
    if any(pos == token_count - 1 for pos in positions) and not any(pos == 0 for pos in positions):
        return "final"
    return "medial"


def registry_by_ab(registry: dict) -> dict[str, dict]:
    return {sign.get("ab_number", ""): sign for sign in registry.get("signs", [])}


def registry_by_name(registry: dict) -> dict[str, dict]:
    return {
        sign.get("name", "").upper(): sign
        for sign in registry.get("signs", [])
        if sign.get("name")
    }


def resolve_registry_record(normalized: dict, registry: dict) -> dict | None:
    by_ab = registry_by_ab(registry)
    by_name = registry_by_name(registry)
    return by_ab.get(normalized["registry_form"]) or by_name.get(normalized["corpus_form"].upper())


def summarize_registry_record(record: dict | None, registry_form: str) -> dict:
    if not record:
        return {"found": False, "ab_number": registry_form, "readings_count": 0, "readings": []}
    rendering = record.get("rendering", {})
    return {
        "found": True,
        "ab_number": record.get("ab_number", registry_form),
        "name": record.get("name", ""),
        "readings_count": len(record.get("readings", [])),
        "readings": record.get("readings", []),
        "sigla_image": rendering.get("sigla_image"),
        "sigla_url": rendering.get("sigla_url"),
        "tier": rendering.get("tier"),
    }


def summarize_contexts(contexts: list[dict], limit: int) -> dict:
    return {
        "total_contexts": len(contexts),
        "tablets": sorted({c["tablet_id"] for c in contexts}),
        "sites": dict(Counter(c.get("site", "") for c in contexts if c.get("site"))),
        "supports": dict(Counter(c.get("support", "") for c in contexts if c.get("support"))),
        "word_positions": dict(Counter(c.get("word_position", "") for c in contexts)),
        "compound_contexts": sum(1 for c in contexts if c.get("is_compound_token")),
        "examples": contexts[:limit],
    }


def annotate_sign(raw: str | None, sign_values: dict, registry: dict) -> dict:
    clean = clean_sign_token(raw)
    base = {"raw": raw, "sign": clean, "known": False}
    if not clean:
        return {**base, "reason": "missing"}
    if is_non_syllabic(clean):
        return {**base, "reason": "non_syllabic"}

    entry = sign_values.get("signs", {}).get(clean) or sign_values.get("signs", {}).get(re.sub(r"\d+$", "", clean))
    if entry:
        primary = entry.get("primary", {})
        return {
            **base,
            "known": True,
            "value": value_from_cv(primary.get("consonant"), primary.get("vowel", "")),
            "consonant": primary.get("consonant"),
            "vowel": primary.get("vowel"),
            "confidence": primary.get("confidence"),
            "ab_number": entry.get("ab_number"),
            "neutralization_class": entry.get("neutralization_class"),
        }

    record = registry_by_name(registry).get(clean)
    if record and record.get("readings"):
        reading = next((r for r in record["readings"] if r.get("is_primary")), record["readings"][0])
        return {
            **base,
            "known": True,
            "value": reading.get("value"),
            "consonant": reading.get("consonant"),
            "vowel": reading.get("vowel"),
            "confidence": reading.get("confidence"),
            "ab_number": record.get("ab_number"),
            "neutralization_class": neutralization_class_for(reading.get("consonant"), sign_values),
        }

    return {**base, "reason": "unknown"}


def is_non_syllabic(clean: str) -> bool:
    if not clean:
        return True
    if len(clean) == 1 and ord(clean) > 127:
        return True
    if clean in IDEOGRAMS:
        return True
    compact = clean.replace(".", "").replace("/", "")
    return compact.isdigit()


def parse_candidate_value(value: str) -> tuple[str | None, str] | None:
    clean = value.strip().lower()
    if clean in {"a", "e", "i", "o", "u"}:
        return None, clean
    if len(clean) >= 2 and clean[-1] in "aeiou":
        return clean[:-1], clean[-1]
    return None


def value_from_cv(consonant: str | None, vowel: str) -> str:
    return f"{consonant or ''}{vowel}".lower()


def candidate_record(
    value: str,
    consonant: str | None,
    vowel: str,
    source: str,
    sign_name: str | None,
    origin_evidence: dict,
    sign_values: dict,
) -> dict:
    origin_score = candidate_origin_score(value, consonant, origin_evidence)
    return {
        "value": value,
        "consonant": consonant,
        "vowel": vowel,
        "source": source,
        "source_sign": sign_name,
        "base_prior": round(origin_score, 3),
        "origin_score": round(origin_score, 3),
        "neutralization_class": neutralization_class_for(consonant, sign_values),
    }


def neutralization_class_for(consonant: str | None, sign_values: dict) -> str | None:
    if not consonant:
        return None
    for class_name, entry in sign_values.get("neutralization_classes", {}).items():
        if consonant in entry.get("phonemes", []):
            return class_name
    return None


def candidate_origin_score(value: str, consonant: str | None, origin_evidence: dict) -> float:
    if origin_evidence.get("status") != "found":
        return 0.5
    score = 0.5
    supported_values = {
        str(origin_evidence.get("phonetic_value") or "").lower(),
        str((origin_evidence.get("linear_b") or {}).get("value") or "").lower(),
    }
    if value in supported_values:
        score += 0.4
    supported_consonants = {v[:-1] for v in supported_values if len(v) >= 2 and v[-1] in "aeiou"}
    ps_letter = str((origin_evidence.get("proto_sinaitic") or {}).get("letter") or "").lower()
    ps_consonant = proto_sinaitic_consonant(ps_letter)
    if ps_consonant:
        supported_consonants.add(ps_consonant)
    if consonant and consonant in supported_consonants:
        score += 0.25
    return min(1.0, score)


def proto_sinaitic_consonant(letter: str) -> str | None:
    mapping = {
        "aleph": None,
        "bet": "b",
        "beth": "b",
        "gimel": "g",
        "dalet": "d",
        "he": "h",
        "waw": "w",
        "zayin": "z",
        "heth": "h",
        "tet": "t",
        "yod": "y",
        "kaph": "k",
        "kap": "k",
        "lamed": "l",
        "mem": "m",
        "nun": "n",
        "samekh": "s",
        "ayin": "ʿ",
        "pe": "p",
        "tsade": "ts",
        "qoph": "q",
        "resh": "r",
        "shin": "sh",
        "taw": "t",
    }
    return mapping.get(letter)


def known_pair_inventory(corpus: dict, sign_values: dict) -> set[tuple[str, str]]:
    known = set(sign_values.get("signs", {}))
    pairs: set[tuple[str, str]] = set()
    for entry in corpus.values():
        words = entry.get("transliteratedWords", [])
        if not isinstance(words, list):
            continue
        for word in words:
            if not isinstance(word, str):
                continue
            tokens = [clean_sign_token(token) for token in split_sign_tokens(word)]
            for left, right in pairwise(tokens):
                if left in known and right in known:
                    pairs.add((left, right))
    return pairs


def positional_score_for_candidate(candidate: dict, contexts: list[dict], pair_inventory: set[tuple[str, str]]) -> float:
    candidate_sign = candidate["value"].upper()
    total = 0
    hits = 0
    for context in contexts:
        for pair in context.get("neighbor_pairs", []):
            left = pair["left"]
            right = pair["right"]
            if left.get("known"):
                total += 1
                hits += int((left["sign"], candidate_sign) in pair_inventory)
            if right.get("known"):
                total += 1
                hits += int((candidate_sign, right["sign"]) in pair_inventory)
    return 0.5 if total == 0 else hits / total


def root_matches_for_skeleton(skeleton: str, options: dict) -> list[dict]:
    max_distance = float(options.get("max_distance", 1.5))
    matches = []
    for match in score_against_roots(skeleton, 1.0, options.get("roots", []), max_distance=max_distance):
        matches.append({**match, "language": "Proto-Semitic"})
    if options.get("include_luwian"):
        matches.extend(score_against_luwian_roots(skeleton, 1.0, max_distance=max_distance))
    if options.get("include_egyptian"):
        matches.extend(score_against_egyptian_roots(skeleton, 1.0, max_distance=max_distance))
    matches.sort(key=lambda item: -item.get("score", 0.0))
    return matches[:5]


def candidate_rationale(candidate: dict, origin_evidence: dict, scored: dict) -> str:
    pieces = [f"{candidate['value']} from {candidate['source']}"]
    if candidate.get("neutralization_class"):
        pieces.append(f"{candidate['neutralization_class']} neutralization class")
    if origin_evidence.get("status") == "found" and candidate.get("origin_score", 0) > 0.5:
        pieces.append("origin evidence supports value or consonant")
    if scored.get("best_matches"):
        roots = ", ".join(m["root"] for m in scored["best_matches"][:2])
        pieces.append(f"best repeated roots: {roots}")
    return "; ".join(pieces)


if __name__ == "__main__":
    sys.exit(main())
