#!/usr/bin/env python3
"""Core constraint-propagation engine for the Ventris Engine.

Takes known readings (anchors), extracts sign→value constraints, propagates
them through the corpus, and surfaces new Semitic root matches. Includes a
probabilistic language router, text-type priors, per-language neutralization
profiles, and UNKNOWN/SUBSTRATE as valid output.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from collections import Counter

from ..core.contact_lexicon import load_all_contact_indexes, match_contact_term
from ..core.phonetics import (
    EGYPTIAN_DISTANCES,
    GUTTURAL_PHONEMES,
    LUWIAN_DISTANCES,
    SEMITIC_DISTANCES,
    _get_sub_cost,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from ..core.phrase_grammar import PhraseGrammar, load_phrase_grammar
from ..core.semitic_root_schema import roots_records
from ..core.site_profiles import get_site_prior, get_site_weight, load_site_profiles
from ..core.skeleton import SIGN_DECOMPOSITION, _lookup_sign
from ..paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"
SIGN_VALUES_PATH = DATA_DIR / "sign_values.json"
LEXICON_PATH = DATA_DIR / "lexicon.json"
MORPHEMES_PATH = DATA_DIR / "morphemes.json"
ROOTS_PATH = SEMITIC_ROOTS_DATA / "semitic_roots.json"
LUWIAN_ROOTS_PATH = DATA_DIR / "luwian_roots.json"
EGYPTIAN_ROOTS_PATH = DATA_DIR / "egyptian_roots.json"


# --- Neutralization profiles ---
# Gordon, "Evidence for the Minoan Language" (1966):
#   §4, §55-58: stops undifferentiated (p/b, t/d/ṭ, k/g/q)
#   §57: all sibilants merge (s/z/š/ṣ/ś)
#   §76: emphatic dental not distinguished from plain
#   §149: polyphony — one sign, multiple phonetic values

NEUTRALIZATION_PROFILES: dict[str, dict[str, list[str]]] = {
    "NWS": {
        "K": ["k", "g", "q"],
        "P": ["p", "b"],
        "T": ["t", "d", "ṭ"],
        "D": ["d", "t", "ṭ"],
        "S": ["s", "z", "š", "sh", "ṣ", "ś"],
        "Z": ["z", "s", "š", "sh", "ṣ"],
        "R": ["r", "l"],
    },
    "Hurrian": {
        "K": ["k", "g"],
        "S": ["s", "š"],
        "R": ["r", "l"],
    },
    "Egyptian": {
        "K": ["k", "g"],
        "T": ["t", "d"],
        "S": ["s", "z", "š"],
        "R": ["r", "l"],
    },
    "Luwian": {
        "K": ["k", "g", "kw", "gw"],
        "T": ["t", "d"],
        "S": ["s", "z"],
        "R": ["r", "l"],
    },
    "Substrate": {},  # opaque — no phonological reconstruction
}


# --- Language filtering options ---

LanguageMode = Literal["multi", "semitic-only", "contact-aware"]


@dataclass(frozen=True)
class LanguageOptions:
    mode: LanguageMode = "multi"
    use_site_priors: bool = False
    use_site_consistency: bool = False
    site_consistency_threshold: float = 0.70
    site_profiles: dict[str, Any] | None = None
    contact_indexes: dict[str, dict[str, list[dict]]] | None = None


# --- Text-type priors ---

TEXT_TYPE_PRIORS: dict[str, dict[str, float]] = {
    "stone_libation": {"NWS": 0.70, "divine_name": 0.85, "personal_name": 0.20, "commodity": 0.10, "toponym": 0.30},
    "clay_tablet": {"NWS": 0.35, "divine_name": 0.30, "personal_name": 0.65, "commodity": 0.80, "toponym": 0.55},
    "seal": {"NWS": 0.40, "divine_name": 0.50, "personal_name": 0.70, "commodity": 0.10, "toponym": 0.20},
    "stone_vessel": {"NWS": 0.60, "divine_name": 0.70, "personal_name": 0.30, "commodity": 0.15, "toponym": 0.40},
    "default": {"NWS": 0.50, "divine_name": 0.50, "personal_name": 0.50, "commodity": 0.50, "toponym": 0.50},
}

_LANG_TO_TT_KEY: dict[str, str] = {
    "NWS": "NWS",
    "Hurrian_name": "personal_name",
    "Egyptian": "personal_name",
    "Luwian": "personal_name",
    "toponym": "toponym",
    "substrate": "NWS",
}

# Known Hurrian name patterns
HURRIAN_ENDINGS = ["-SE-NE", "-SE-NE-TI", "-TE-SE-JA"]
EGYPTIAN_ENDINGS = ["-RE", "-MU-NI", "-ME-NI", "-PA-TA", "-DU-TI", "-HA-TU"]

# Luwian morphological endings (place-names, ethnics, theophorics, derivational)
LUWIAN_ENDINGS = [
    "-A-SA", "-A-SI", "-WA-NI", "-ZI-TI", "-SI-TI", "-WA-NA-SA",
    "-A-TI", "-A-DI", "-NI-ZI", "-AN-TI", "-WI", "-U-NA",
]

# Spelling rules (digraphs)
DIGRAPHS = [
    (["SA", "SA"], "sh", 0.85, "SA-SA = single /sh/ (Gordon)"),
]


def _extract_consonantal_root(form: str) -> str:
    """Extract consonantal skeleton from a Proto-Semitic or Ugaritic form.

    Handles reconstruction notation noise:
    - / alternatives: *mi/ut- → take first (*mi-)
    - _ encoding artifacts: *pat_t_- → ptt (underscore stripped)
    - Combining diacritics: NFC-normalize before processing
    """
    s = form.strip()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"^\*", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\d+$", "", s)
    s = s.split(",")[0].split(" ")[0]
    # /*  separates whole-form alternatives (*pas-/*pis-); take first
    if "/*" in s:
        s = s.split("/*")[0]
    # / within a form = vowel alternatives (*mi/ut-); just remove it
    s = s.replace("/", "")
    s = s.replace("-", "").replace("_", "")
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    # V = "unknown vowel" in reconstruction notation
    root = "".join(c for c in s if c.lower() not in vowels and c not in "* V")
    return root.lower()


def _extract_ugaritic_root(analogue_str: str) -> str:
    """Extract consonantal form from Ugaritic analogue field.

    'ʔab id. (DUL, 2)' → ʔb
    'kns to gather' → kns
    """
    if not analogue_str:
        return ""
    form = analogue_str.split("(")[0].strip()     # before citation
    form = form.split("id.")[0].strip()           # before 'id.'
    form = re.split(r"\s+", form)[0]              # first token only
    return _extract_consonantal_root(form)


def _prepare_root_entries(raw_roots: list) -> list[dict]:
    """Convert semitic_roots.json entries into searchable root records.

    Each raw entry has Proto-Semitic, Meaning, and Analogues.
    We produce {root, meaning, proto_semitic, source} dicts.
    """
    entries = []
    seen = set()
    for raw in raw_roots:
        ps = raw.get("Proto-Semitic", "")
        meaning = raw.get("Meaning", "").strip("'\"")
        analogues = raw.get("Analogues", {})

        # Primary: from Proto-Semitic form
        ps_root = _extract_consonantal_root(ps)
        if ps_root and len(ps_root) >= 2 and ps_root not in seen:
            entries.append({
                "root": ps_root,
                "meaning": meaning,
                "proto_semitic": ps,
                "source": "Proto-Semitic",
            })
            seen.add(ps_root)

        # Secondary: from Ugaritic analogue (closest to Minoan)
        ug = analogues.get("Ugaritic", "")
        ug_root = _extract_ugaritic_root(ug)
        if ug_root and len(ug_root) >= 2 and ug_root not in seen:
            entries.append({
                "root": ug_root,
                "meaning": meaning,
                "proto_semitic": ps,
                "source": "Ugaritic",
            })
            seen.add(ug_root)

        # Tertiary: from Phoenician (Canaanite maritime peer)
        ph = analogues.get("Phoenician", "")
        ph_root = _extract_ugaritic_root(ph)
        if ph_root and len(ph_root) >= 2 and ph_root not in seen:
            entries.append({
                "root": ph_root,
                "meaning": meaning,
                "proto_semitic": ps,
                "source": "Phoenician",
            })
            seen.add(ph_root)

    return entries


def load_all() -> tuple[dict, dict, dict, dict, list]:
    read = lambda path: json.loads(require(path, path.name).read_text(encoding="utf-8"))
    corpus = read(CORPUS_PATH)
    sign_values = read(SIGN_VALUES_PATH)
    lexicon = read(LEXICON_PATH)
    morphemes = read(MORPHEMES_PATH)
    raw_roots = roots_records(read(ROOTS_PATH))
    roots = _prepare_root_entries(raw_roots)
    return corpus, sign_values, lexicon, morphemes, roots


def _infer_text_type(doc: dict) -> str:
    """Infer text type from support/context fields."""
    support = (doc.get("support") or "").lower()
    if "libation" in support or "offering" in support:
        return "stone_libation"
    if "tablet" in support:
        return "clay_tablet"
    if "seal" in support or "nodule" in support or "roundel" in support:
        return "seal"
    if "stone" in support or "vessel" in support or "vase" in support:
        return "stone_vessel"
    return "default"


def _get_prior(text_type: str, category: str) -> float:
    priors = TEXT_TYPE_PRIORS.get(text_type, TEXT_TYPE_PRIORS["default"])
    return priors.get(category, 0.5)


def _compute_composite_prior(
    lang_category: str,
    text_type: str,
    site: str,
    lang_opts: LanguageOptions | None,
    tt_key_map: dict[str, str],
) -> float:
    """Compose text-type prior with site-language prior.

    Without site priors enabled, returns the text-type prior alone (preserving
    existing behavior). With site priors, multiplicatively adjusts the text-type
    prior toward or away from the site's archaeological language distribution,
    floored at 0.05 so surprises can always surface.
    """
    if lang_category == "substrate":
        tt_prior = 1.0 - _get_prior(text_type, "NWS")
    else:
        tt_prior = _get_prior(text_type, tt_key_map.get(lang_category, "NWS"))

    if not (lang_opts and lang_opts.use_site_priors and lang_opts.site_profiles):
        return tt_prior

    site_prior = get_site_prior(site, lang_category, lang_opts.site_profiles)
    weight = get_site_weight(site, lang_opts.site_profiles)
    combined = (1.0 - weight) * tt_prior + weight * site_prior
    return max(combined, 0.05)


def extract_words_from_corpus(corpus: dict) -> list[dict]:
    """Extract words with metadata from corpus."""
    results = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        text_type = _infer_text_type(doc)
        words_raw = doc.get("transliteratedWords", [])
        for token in words_raw:
            if not isinstance(token, str) or not token.strip() or token == "\n":
                continue
            if len(token) == 1 and ord(token) > 127:
                continue
            signs = token.split("-")
            if any(s.upper().rstrip("₂₃₄₅") in SIGN_DECOMPOSITION or
                   re.sub(r"[₂₃₄₅2345]+$", "", s.upper()) in SIGN_DECOMPOSITION
                   for s in signs):
                results.append({
                    "word": token.upper(),
                    "signs": [s.upper() for s in signs],
                    "doc_id": doc_id,
                    "site": site,
                    "text_type": text_type,
                })
    return results


def build_known_words(lexicon: dict) -> dict[str, dict]:
    """Index known words from lexicon for quick lookup."""
    known = {}
    for entry in lexicon.get("entries", []):
        word = entry.get("word", "").upper()
        if word:
            known[word] = entry
    return known


def apply_digraphs(signs: list[str]) -> list[tuple[str | None, str]]:
    """Apply digraph rules before skeleton extraction.

    Returns list of (consonant, vowel) tuples with digraphs collapsed.
    """
    result = []
    i = 0
    while i < len(signs):
        matched = False
        for pattern, value, conf, note in DIGRAPHS:
            plen = len(pattern)
            if i + plen <= len(signs) and [s.upper() for s in signs[i:i+plen]] == pattern:
                result.append((value, "a"))  # digraph produces single consonant
                i += plen
                matched = True
                break
        if not matched:
            decomp = _lookup_sign(signs[i])
            if decomp:
                result.append(decomp)
            i += 1
    return result


def strip_affixes(word: str, morphemes: dict) -> list[tuple[str, str, str]]:
    """Try stripping known prefixes and suffixes.

    Returns list of (stripped_word, prefix_removed, suffix_removed).
    Always includes the original word as first entry.
    """
    results = [(word, "", "")]

    prefixes = morphemes.get("prefixes", [])
    suffixes = morphemes.get("suffixes", [])

    for pfx in prefixes:
        form = pfx["form"].rstrip("-")
        if word.startswith(form + "-") and len(word) > len(form) + 1:
            stripped = word[len(form)+1:]
            results.append((stripped, form, ""))

    for sfx in suffixes:
        form = sfx["form"].lstrip("-")
        if word.endswith("-" + form) and len(word) > len(form) + 1:
            stripped = word[:-(len(form)+1)]
            results.append((stripped, "", form))

    # Combined prefix + suffix stripping
    for pfx in prefixes:
        pform = pfx["form"].rstrip("-")
        if not word.startswith(pform + "-"):
            continue
        inner = word[len(pform)+1:]
        for sfx in suffixes:
            sform = sfx["form"].lstrip("-")
            if inner.endswith("-" + sform) and len(inner) > len(sform) + 1:
                stripped = inner[:-(len(sform)+1)]
                results.append((stripped, pform, sform))

    return results


_NWS_INITIAL_LARYNGEALS = ["ʔ", "ʿ", "h", "ḥ"]


def skeleton_with_neutralization(
    signs: list[str],
    profile: str = "NWS",
    beam_width: int = 16,
    alt_confidence: float = 0.5,
) -> list[tuple[str, float]]:
    """Generate candidate skeletons with neutralization-class expansion.

    Returns list of (skeleton_string, cumulative_confidence) pairs,
    pruned to the top beam_width candidates at each step.

    Gordon §4, §61: pure vowel signs may begin with a laryngeal (ʔ, ʿ, h, ḥ).
    For NWS profiles, word-initial vowel signs expand to include optional
    laryngeal prefixes at reduced confidence.
    """
    neut = NEUTRALIZATION_PROFILES.get(profile, {})
    decomposed = apply_digraphs(signs)

    position_options: list[list[tuple[str, float]]] = []
    is_first_position = True
    for consonant, vowel in decomposed:
        if consonant is None:
            if is_first_position and profile == "NWS":
                options: list[tuple[str, float]] = [("", 1.0)]
                for lar in _NWS_INITIAL_LARYNGEALS:
                    options.append((lar, alt_confidence * 0.6))
                position_options.append(options)
            is_first_position = False
            continue
        is_first_position = False
        options = [(consonant, 1.0)]
        for members in neut.values():
            if consonant in members:
                for alt in members:
                    if alt != consonant:
                        options.append((alt, alt_confidence))
                break
        position_options.append(options)

    if not position_options:
        return [("", 1.0)]

    candidates: list[tuple[str, float]] = [("", 1.0)]
    for options in position_options:
        new_candidates = []
        for skeleton, conf in candidates:
            for char, char_conf in options:
                new_candidates.append((skeleton + char, conf * char_conf))
        new_candidates.sort(key=lambda x: -x[1])
        candidates = new_candidates[:beam_width]

    return candidates


def skeleton_multi_profile(
    signs: list[str],
    beam_width: int = 16,
    alt_confidence: float = 0.5,
) -> list[tuple[str, float, str]]:
    """Run beam search across all neutralization profiles, merge results.

    Returns (skeleton, confidence, profile_name) tuples, deduplicated by
    skeleton string (keeps highest confidence).
    """
    seen: dict[str, tuple[float, str]] = {}
    for profile_name in NEUTRALIZATION_PROFILES:
        candidates = skeleton_with_neutralization(
            signs, profile_name, beam_width, alt_confidence,
        )
        for skel, conf in candidates:
            if skel not in seen or conf > seen[skel][0]:
                seen[skel] = (conf, profile_name)

    results = [(skel, conf, prof) for skel, (conf, prof) in seen.items()]
    results.sort(key=lambda x: -x[1])
    return results[:beam_width]


_WEAK_MEDIAL = frozenset({"w", "y"})

_COMPLETION_FACTORS = {
    "r1_r2": 0.60,
    "r2_r3": 0.58,
    "r1_r3_hollow": 0.72,
    "r1_r3_guttural": 0.78,
}


def find_triconsonantal_completions(
    skeleton: str,
    root_clean: str,
    max_aligned_distance: float = 0.55,
) -> list[tuple[str, float, str]]:
    """Find completion patterns for a 2-consonant skeleton against a 3-consonant root.

    Returns list of (pattern_name, aligned_distance, missing_radical) tuples.
    Explicit aligned subsequence matching with Semitic phoneme costs, not
    generic wildcard Levenshtein.
    """
    skel_tokens = _tokenize_phonemes(skeleton)
    root_tokens = _tokenize_phonemes(root_clean)

    if len(skel_tokens) != 2 or len(root_tokens) != 3:
        return []

    s0, s1 = skel_tokens
    r0, r1, r2 = root_tokens
    results = []

    # r1_r2: s0~r0, s1~r1, missing r2
    d = _get_sub_cost(s0, r0, SEMITIC_DISTANCES) + _get_sub_cost(s1, r1, SEMITIC_DISTANCES)
    if d <= max_aligned_distance:
        results.append(("r1_r2", d, r2))

    # r2_r3: s0~r1, s1~r2, missing r0
    d = _get_sub_cost(s0, r1, SEMITIC_DISTANCES) + _get_sub_cost(s1, r2, SEMITIC_DISTANCES)
    if d <= max_aligned_distance:
        results.append(("r2_r3", d, r0))

    # r1_r3_hollow: s0~r0, s1~r2, missing r1 — only if r1 is weak (w/y)
    if r1 in _WEAK_MEDIAL:
        d = _get_sub_cost(s0, r0, SEMITIC_DISTANCES) + _get_sub_cost(s1, r2, SEMITIC_DISTANCES)
        if d <= max_aligned_distance:
            results.append(("r1_r3_hollow", d, r1))

    # r1_r3_guttural: s0~r0, s1~r2, missing r1 — only if r1 is guttural
    if r1 in GUTTURAL_PHONEMES:
        d = _get_sub_cost(s0, r0, SEMITIC_DISTANCES) + _get_sub_cost(s1, r2, SEMITIC_DISTANCES)
        if d <= max_aligned_distance:
            results.append(("r1_r3_guttural", d, r1))

    return results


def score_against_roots(
    skeleton: str,
    skeleton_conf: float,
    roots: list,
    max_distance: float = 1.5,
    enable_root_completion: bool = True,
    max_completion_distance: float = 0.55,
) -> list[dict]:
    """Score a skeleton against Proto-Semitic root database.

    Applies length-based penalties: biconsonantal skeletons are heavily
    discounted because any CV-CV word trivially matches hundreds of roots.
    Triconsonantal matches are preferred (the Semitic sweet spot).

    When enable_root_completion=True and the skeleton has exactly 2 consonants,
    also tests triconsonantal root completion (Gordon's shoresh inference).
    """
    skel_len = len(_tokenize_phonemes(skeleton))
    if skel_len < 2:
        return []

    length_factor = {2: 0.3, 3: 1.0}.get(skel_len, 0.9)

    matches = []
    for root_entry in roots:
        root_str = root_entry.get("root", "")
        if not root_str:
            continue
        root_clean = root_str.replace("-", "")
        if not root_clean or len(root_clean) < 2:
            continue

        root_tokens = _tokenize_phonemes(root_clean)
        visible_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)
        if visible_len < 1:
            continue

        # Standard Levenshtein path
        len_diff = abs(skel_len - visible_len)
        len_penalty = 1.0 if len_diff == 0 else 0.7 if len_diff == 1 else 0.4

        dist = weighted_levenshtein(skeleton, root_clean, guttural_transparent=True)
        if dist <= max_distance:
            raw_score = (1 / (1 + dist)) * skeleton_conf
            adjusted = raw_score * length_factor * len_penalty
            matches.append({
                "root": root_str,
                "meaning": root_entry.get("meaning", ""),
                "proto_semitic": root_entry.get("proto_semitic", ""),
                "source_lang": root_entry.get("source", ""),
                "distance": round(dist, 2),
                "skeleton_confidence": round(skeleton_conf, 3),
                "score": round(adjusted, 3),
            })

        # Root completion path for biconsonantal skeletons
        if enable_root_completion and skel_len == 2 and len(root_tokens) == 3:
            completions = find_triconsonantal_completions(
                skeleton, root_clean, max_completion_distance,
            )
            for pattern, aligned_dist, missing in completions:
                factor = _COMPLETION_FACTORS[pattern]
                comp_score = (1 / (1 + aligned_dist)) * skeleton_conf * factor
                if comp_score > 0.1:
                    matches.append({
                        "root": root_str,
                        "meaning": root_entry.get("meaning", ""),
                        "proto_semitic": root_entry.get("proto_semitic", ""),
                        "source_lang": root_entry.get("source", ""),
                        "distance": round(aligned_dist, 2),
                        "skeleton_confidence": round(skeleton_conf, 3),
                        "score": round(comp_score, 3),
                        "match_type": "triconsonantal_completion",
                        "completion_pattern": pattern,
                        "missing_radical": missing,
                        "completion_factor": factor,
                    })

    matches.sort(key=lambda x: -x["score"])
    return matches[:10]


def _load_luwian_roots() -> list[dict]:
    """Load and normalize the Luwian root database."""
    if not LUWIAN_ROOTS_PATH.exists():
        return []
    raw = json.loads(LUWIAN_ROOTS_PATH.read_text(encoding="utf-8"))
    roots = []
    for entry in raw:
        lemma = entry.get("Proto-Luwian", "")
        root = entry.get("Consonantal_Root", "")
        if root and len(root) >= 2:
            roots.append({
                "root": root,
                "lemma": lemma,
                "meaning": entry.get("Meaning", ""),
            })
    return roots


_LUWIAN_ROOTS_CACHE: list[dict] | None = None


def _get_luwian_roots() -> list[dict]:
    global _LUWIAN_ROOTS_CACHE
    if _LUWIAN_ROOTS_CACHE is None:
        _LUWIAN_ROOTS_CACHE = _load_luwian_roots()
    return _LUWIAN_ROOTS_CACHE


def score_against_luwian_roots(
    skeleton: str,
    skeleton_conf: float,
    max_distance: float = 1.5,
) -> list[dict]:
    """Score a skeleton against the Luwian root database.

    No guttural transparency — Luwian lacks pharyngeals/laryngeals.
    Uses LUWIAN_DISTANCES for fortis/lenis, labiovelars, i-mutation.
    """
    roots = _get_luwian_roots()
    if not roots:
        return []

    skel_len = len(_tokenize_phonemes(skeleton))
    if skel_len < 2:
        return []

    length_factor = {2: 0.3, 3: 1.0}.get(skel_len, 0.9)

    matches = []
    for root_entry in roots:
        root_str = root_entry["root"]
        root_tokens = _tokenize_phonemes(root_str)
        if len(root_tokens) < 2:
            continue

        len_diff = abs(skel_len - len(root_tokens))
        len_penalty = 1.0 if len_diff == 0 else 0.7 if len_diff == 1 else 0.4

        dist = weighted_levenshtein(skeleton, root_str, distances=LUWIAN_DISTANCES)
        if dist <= max_distance:
            raw_score = (1 / (1 + dist)) * skeleton_conf
            adjusted = raw_score * length_factor * len_penalty
            matches.append({
                "root": root_str,
                "lemma": root_entry.get("lemma", ""),
                "meaning": root_entry.get("meaning", ""),
                "distance": round(dist, 2),
                "score": round(adjusted, 3),
                "language": "Luwian",
            })

    matches.sort(key=lambda x: -x["score"])
    return matches[:5]


def _load_egyptian_roots() -> list[dict]:
    """Load and normalize the Egyptian root database."""
    if not EGYPTIAN_ROOTS_PATH.exists():
        return []
    raw = json.loads(EGYPTIAN_ROOTS_PATH.read_text(encoding="utf-8"))
    roots = []
    for entry in raw:
        lemma = entry.get("Middle_Egyptian", "")
        root = entry.get("Consonantal_Root", "")
        if root and len(root) >= 2:
            roots.append({
                "root": root,
                "lemma": lemma,
                "meaning": entry.get("Meaning", ""),
            })
    return roots


_EGYPTIAN_ROOTS_CACHE: list[dict] | None = None


def _get_egyptian_roots() -> list[dict]:
    global _EGYPTIAN_ROOTS_CACHE
    if _EGYPTIAN_ROOTS_CACHE is None:
        _EGYPTIAN_ROOTS_CACHE = _load_egyptian_roots()
    return _EGYPTIAN_ROOTS_CACHE


def score_against_egyptian_roots(
    skeleton: str,
    skeleton_conf: float,
    max_distance: float = 1.5,
) -> list[dict]:
    """Score a skeleton against the Egyptian root database.

    Guttural-transparent: Egyptian pharyngeals/laryngeals (ꜥ, ꜣ, ḥ, h)
    are invisible in Linear A's CV syllabary, same as Semitic gutturals.
    Uses EGYPTIAN_DISTANCES for f/p Afroasiatic shift, sibilant mergers.
    """
    roots = _get_egyptian_roots()
    if not roots:
        return []

    skel_len = len(_tokenize_phonemes(skeleton))
    if skel_len < 2:
        return []

    length_factor = {2: 0.3, 3: 1.0}.get(skel_len, 0.9)

    matches = []
    for root_entry in roots:
        root_str = root_entry["root"]
        root_tokens = _tokenize_phonemes(root_str)
        visible_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)
        if visible_len < 1:
            continue

        len_diff = abs(skel_len - visible_len)
        len_penalty = 1.0 if len_diff == 0 else 0.7 if len_diff == 1 else 0.4

        dist = weighted_levenshtein(
            skeleton, root_str,
            distances=EGYPTIAN_DISTANCES,
            guttural_transparent=True,
        )
        if dist <= max_distance:
            raw_score = (1 / (1 + dist)) * skeleton_conf
            adjusted = raw_score * length_factor * len_penalty
            matches.append({
                "root": root_str,
                "lemma": root_entry.get("lemma", ""),
                "meaning": root_entry.get("meaning", ""),
                "distance": round(dist, 2),
                "score": round(adjusted, 3),
                "language": "Egyptian",
            })

    matches.sort(key=lambda x: -x["score"])
    return matches[:5]


def classify_language(
    word: str,
    signs: list[str],
    nws_matches: list[dict],
    text_type: str,
    known_words: dict,
    skeleton: str = "",
    skeleton_conf: float = 0.5,
    egyptian_matches: list[dict] | None = None,
    luwian_matches: list[dict] | None = None,
    lang_opts: LanguageOptions | None = None,
    site: str = "",
) -> dict:
    """Probabilistic language classification.

    Computes raw likelihoods per category (NWS, Hurrian, Egyptian, Luwian,
    toponym, substrate), applies text-type priors uniformly, then normalizes
    to a posterior distribution.
    """
    semitic_only = lang_opts is not None and lang_opts.mode == "semitic-only"
    likelihoods = {"NWS": 0.0, "Hurrian_name": 0.0, "Egyptian": 0.0,
                   "Luwian": 0.0, "toponym": 0.0, "substrate": 0.0}

    if nws_matches:
        likelihoods["NWS"] = nws_matches[0]["score"]

    for ending in HURRIAN_ENDINGS:
        if word.endswith(ending):
            likelihoods["Hurrian_name"] = 0.8
            break

    if not semitic_only:
        for ending in EGYPTIAN_ENDINGS:
            if word.endswith(ending) and len(signs) >= 3:
                likelihoods["Egyptian"] = 0.7
                break

        if egyptian_matches is None and skeleton:
            egyptian_matches = score_against_egyptian_roots(skeleton, skeleton_conf)
        if egyptian_matches:
            likelihoods["Egyptian"] = max(likelihoods["Egyptian"],
                                          egyptian_matches[0]["score"])

        for ending in LUWIAN_ENDINGS:
            if word.endswith(ending):
                likelihoods["Luwian"] = 0.7
                break

        if luwian_matches is None and skeleton:
            luwian_matches = score_against_luwian_roots(skeleton, skeleton_conf)
        if luwian_matches:
            likelihoods["Luwian"] = max(likelihoods["Luwian"],
                                        luwian_matches[0]["score"])

    if word in known_words:
        entry = known_words[word]
        cat = entry.get("category", "")
        if cat == "personal_name" and "Hurrian" in entry.get("note", ""):
            if not semitic_only:
                likelihoods["Hurrian_name"] = 0.95
        elif cat == "personal_name" and "Egyptian" in entry.get("note", ""):
            if not semitic_only:
                likelihoods["Egyptian"] = 0.95
        elif cat == "toponym":
            likelihoods["toponym"] = 0.90
        elif entry.get("is_anchor"):
            likelihoods["NWS"] = max(likelihoods["NWS"], 0.90)

    max_classified = max(likelihoods["NWS"], likelihoods["Hurrian_name"],
                         likelihoods["Egyptian"],
                         likelihoods["Luwian"], likelihoods["toponym"])
    if max_classified < 0.3:
        likelihoods["substrate"] = 0.5

    posteriors = {}
    for lang, likelihood in likelihoods.items():
        prior = _compute_composite_prior(lang, text_type, site, lang_opts, _LANG_TO_TT_KEY)
        posteriors[lang] = likelihood * prior

    total = sum(posteriors.values())
    if total > 0:
        scores = {k: v / total for k, v in posteriors.items()}
    else:
        scores = posteriors

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]
    decision = best_lang if best_score >= 0.2 else "unknown"

    return {
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "decision": decision,
        "confidence": round(best_score, 3),
    }


def propagate_word(
    word_info: dict,
    morphemes: dict,
    roots: list,
    known_words: dict,
    beam_width: int = 16,
    alt_confidence: float = 0.5,
    lang_opts: LanguageOptions | None = None,
) -> dict | None:
    """Propagate constraints through a single word.

    Returns candidate reading or None if no good match.
    """
    word = word_info["word"]
    signs = word_info["signs"]
    text_type = word_info["text_type"]

    if word in known_words:
        entry = known_words[word]
        return {
            "word": word,
            "status": "known",
            "reading": entry.get("reading", ""),
            "root": entry.get("root", ""),
            "confidence": entry.get("confidence", ""),
            "source": entry.get("source", ""),
        }

    all_forms = strip_affixes(word, morphemes)
    best_result = None
    best_score = 0
    best_skeleton_info = None
    best_skeleton_conf = 0.0

    for stripped, prefix, suffix in all_forms:
        stripped_signs = stripped.split("-")
        candidates = skeleton_multi_profile(
            stripped_signs, beam_width, alt_confidence,
        )

        for skeleton, skel_conf, profile in candidates:
            if not skeleton:
                continue
            if skel_conf > best_skeleton_conf:
                best_skeleton_conf = skel_conf
                best_skeleton_info = (skeleton, skel_conf, profile,
                                     stripped, prefix, suffix)
            matches = score_against_roots(skeleton, skel_conf, roots)
            if matches and matches[0]["score"] > best_score:
                best_score = matches[0]["score"]
                best_result = {
                    "word": word,
                    "stripped": stripped if stripped != word else None,
                    "prefix_removed": prefix or None,
                    "suffix_removed": suffix or None,
                    "skeleton": skeleton,
                    "skeleton_confidence": round(skel_conf, 3),
                    "neut_profile": profile,
                    "best_root": matches[0]["root"],
                    "best_meaning": matches[0]["meaning"],
                    "distance": matches[0]["distance"],
                    "score": matches[0]["score"],
                    "source_lang": matches[0].get("source_lang", ""),
                    "proto_semitic": matches[0].get("proto_semitic", ""),
                    "top_matches": matches[:3],
                }

    # Determine working skeleton for non-Semitic root scoring
    if best_result:
        work_skel = best_result["skeleton"]
        work_conf = best_result["skeleton_confidence"]
    elif best_skeleton_info:
        work_skel = best_skeleton_info[0]
        work_conf = best_skeleton_info[1]
    else:
        return None

    # Score against Egyptian and Luwian roots (skipped in semitic-only mode)
    semitic_only = lang_opts and lang_opts.mode == "semitic-only"
    if semitic_only:
        eg_matches = []
        lw_matches = []
    else:
        eg_matches = score_against_egyptian_roots(work_skel, work_conf)
        lw_matches = score_against_luwian_roots(work_skel, work_conf)

    # If no Semitic match, try Egyptian/Luwian as primary match
    if best_result is None and best_skeleton_info and not semitic_only:
        skel, skel_conf, profile, stripped, prefix, suffix = best_skeleton_info
        best_alt = None
        best_alt_score = 0.0
        for match_list in (eg_matches, lw_matches):
            if match_list and match_list[0]["score"] > best_alt_score:
                best_alt = match_list[0]
                best_alt_score = match_list[0]["score"]
        if best_alt:
            best_result = {
                "word": word,
                "stripped": stripped if stripped != word else None,
                "prefix_removed": prefix or None,
                "suffix_removed": suffix or None,
                "skeleton": skel,
                "skeleton_confidence": round(skel_conf, 3),
                "neut_profile": profile,
                "best_root": best_alt["root"],
                "best_meaning": best_alt["meaning"],
                "distance": best_alt["distance"],
                "score": best_alt["score"],
                "source_lang": best_alt.get("language", ""),
                "proto_semitic": best_alt.get("lemma", ""),
                "top_matches": [best_alt],
            }

    # Contact-aware mode: check contact lexicon for Egyptian/Anatolian loans
    if lang_opts and lang_opts.mode == "contact-aware" and lang_opts.contact_indexes and best_result:
        contact_matches = []
        for lang_key in ("egyptian", "anatolian", "hurrian"):
            contact_result = match_contact_term(
                work_skel, lang_key.title(), lang_opts.contact_indexes,
            )
            if contact_result["matched"]:
                contact_matches.append(contact_result)
        if contact_matches:
            best_result["contact_matches"] = contact_matches

    if best_result is None:
        return None

    # Language classification — pass only Semitic matches as nws_matches
    semitic_matches = [m for m in best_result.get("top_matches", [])
                       if "language" not in m]
    lang = classify_language(
        word, signs, semitic_matches, text_type, known_words,
        skeleton=best_result.get("skeleton", ""),
        skeleton_conf=best_result.get("skeleton_confidence", 0.5),
        egyptian_matches=eg_matches,
        luwian_matches=lw_matches,
        lang_opts=lang_opts,
        site=word_info.get("site", ""),
    )
    best_result["language"] = lang

    # Update root display when classified as non-Semitic
    decision = lang.get("decision", "")
    if decision == "Egyptian" and eg_matches:
        best_result["best_root"] = eg_matches[0]["root"]
        best_result["best_meaning"] = eg_matches[0]["meaning"]
        best_result["source_lang"] = "Egyptian"
        best_result["distance"] = eg_matches[0]["distance"]
    elif decision == "Luwian" and lw_matches:
        best_result["best_root"] = lw_matches[0]["root"]
        best_result["best_meaning"] = lw_matches[0]["meaning"]
        best_result["source_lang"] = "Luwian"
        best_result["distance"] = lw_matches[0]["distance"]

    best_result["site"] = word_info["site"]
    best_result["doc_id"] = word_info["doc_id"]
    best_result["text_type"] = text_type

    return best_result


def compute_empirical_site_distribution(results: list[dict]) -> dict[str, dict[str, float]]:
    """Aggregate first-pass language decisions by site into empirical priors."""
    site_counts: dict[str, Counter] = {}
    for r in results:
        if r.get("status") == "known":
            continue
        site = r.get("site", "")
        decision = r.get("language", {}).get("decision", "unknown")
        if decision == "unknown":
            continue
        if site not in site_counts:
            site_counts[site] = Counter()
        site_counts[site][decision] += 1

    categories = ["NWS", "Hurrian_name", "Egyptian", "Luwian", "toponym", "substrate"]
    distributions: dict[str, dict[str, float]] = {}
    for site, counts in site_counts.items():
        total = sum(counts.values())
        if total == 0:
            continue
        distributions[site] = {cat: counts.get(cat, 0) / total for cat in categories}
    return distributions


def apply_site_consistency(
    results: list[dict],
    empirical: dict[str, dict[str, float]],
    known_words: dict,
    lang_opts: LanguageOptions,
) -> tuple[list[dict], dict]:
    """Re-classify low-confidence words using empirical site priors.

    Returns (updated_results, consistency_summary).
    """
    rescored = 0
    replaced = 0

    site_results: dict[str, list[tuple[int, float]]] = {}
    for i, r in enumerate(results):
        if r.get("status") == "known":
            continue
        site = r.get("site", "")
        conf = r.get("language", {}).get("confidence", 1.0)
        if site not in site_results:
            site_results[site] = []
        site_results[site].append((i, conf))

    site_low_conf: dict[str, list[int]] = {}
    for site, entries in site_results.items():
        if site not in empirical or len(entries) < 4:
            continue
        k = max(1, len(entries) // 4)
        ranked = sorted(entries, key=lambda pair: pair[1])
        for idx, _conf in ranked[:k]:
            site_low_conf.setdefault(site, []).append(idx)

    base_profiles = lang_opts.site_profiles or load_site_profiles()
    for site, indices in site_low_conf.items():
        emp_site = {"languages": empirical[site], "site_weight": 0.50}
        patched_sites = dict(base_profiles.get("sites", {}))
        patched_sites[site] = emp_site
        patched = dict(base_profiles)
        patched["sites"] = patched_sites
        emp_opts = dataclasses.replace(
            lang_opts, use_site_priors=True, site_profiles=patched,
        )

        for idx in indices:
            r = results[idx]
            semitic_matches = [m for m in r.get("top_matches", []) if "language" not in m]
            new_lang = classify_language(
                r["word"], r["word"].split("-"), semitic_matches,
                r.get("text_type", "default"), known_words,
                skeleton=r.get("skeleton", ""),
                skeleton_conf=r.get("skeleton_confidence", 0.5),
                lang_opts=emp_opts,
                site=site,
            )
            rescored += 1

            old_decision = r.get("language", {}).get("decision", "unknown")
            new_decision = new_lang.get("decision", "unknown")
            if old_decision != new_decision:
                replaced += 1
                r["language"] = new_lang
                r["consistency_revised"] = {
                    "original_decision": old_decision,
                    "new_decision": new_decision,
                    "empirical_prior": empirical[site],
                }

    strongly_monolingual = []
    for site, dist in empirical.items():
        dominant = max(dist.values())
        if dominant >= lang_opts.site_consistency_threshold:
            dominant_lang = max(dist, key=dist.get)
            strongly_monolingual.append({"site": site, "language": dominant_lang,
                                         "proportion": round(dominant, 2)})

    summary = {
        "eligible_sites": len(site_results),
        "sites_with_empirical": len(empirical),
        "rescored": rescored,
        "replaced": replaced,
        "unchanged": rescored - replaced,
        "strongly_monolingual": strongly_monolingual,
    }
    return results, summary


def run_propagation(
    min_score: float = 0.4,
    new_only: bool = False,
    tablet: str | None = None,
    max_results: int = 50,
    beam_width: int = 16,
    alt_confidence: float = 0.5,
    lang_opts: LanguageOptions | None = None,
    phrase_grammar: PhraseGrammar | None = None,
) -> dict:
    """Run full constraint propagation across the corpus."""
    if lang_opts is None:
        lang_opts = LanguageOptions()

    if lang_opts.use_site_priors and lang_opts.site_profiles is None:
        lang_opts = dataclasses.replace(
            lang_opts, site_profiles=load_site_profiles(),
        )

    if lang_opts.mode == "contact-aware" and lang_opts.contact_indexes is None:
        lang_opts = dataclasses.replace(
            lang_opts, contact_indexes=load_all_contact_indexes(),
        )

    corpus, _sign_values, lexicon, morphemes, roots = load_all()

    known_words = build_known_words(lexicon)
    words = extract_words_from_corpus(corpus)

    if tablet:
        tablet_upper = tablet.upper()
        words = [w for w in words if w["doc_id"].upper().startswith(tablet_upper)]

    results = []
    known_count = 0
    new_count = 0
    no_match_count = 0

    pg_adjustments = 0

    for word_info in words:
        result = propagate_word(
            word_info, morphemes, roots, known_words,
            beam_width=beam_width, alt_confidence=alt_confidence,
            lang_opts=lang_opts,
        )
        if result is None:
            no_match_count += 1
            continue

        if result.get("status") != "known" and phrase_grammar is not None:
            meaning = result.get("best_meaning", "")
            adj, pg_details = phrase_grammar.score_compatibility(
                result["word"], meaning,
            )
            if adj != 0.0:
                result["score"] = max(round(result.get("score", 0) + adj, 3), 0.0)
                pg_adjustments += 1
            result["phrase_grammar"] = pg_details

        if result.get("status") == "known":
            known_count += 1
            if not new_only:
                results.append(result)
        elif result.get("score", 0) >= min_score:
            new_count += 1
            results.append(result)

    # Sort by score descending, known first then new
    results.sort(key=lambda x: (x.get("status") != "known", -x.get("score", 0)))

    if new_only:
        results = [r for r in results if r.get("status") != "known"]

    consistency_summary = None
    if lang_opts.use_site_consistency:
        empirical = compute_empirical_site_distribution(results)
        results, consistency_summary = apply_site_consistency(
            results, empirical, known_words, lang_opts,
        )

    summary = {
        "total_words": len(words),
        "known": known_count,
        "new_candidates": new_count,
        "no_match": no_match_count,
        "min_score": min_score,
        "language_mode": lang_opts.mode,
        "site_priors_enabled": lang_opts.use_site_priors,
        "site_consistency_enabled": lang_opts.use_site_consistency,
        "phrase_grammar_enabled": phrase_grammar is not None,
    }
    if phrase_grammar is not None:
        summary["phrase_grammar_adjustments"] = pg_adjustments
    if consistency_summary:
        summary["site_consistency"] = consistency_summary

    return {
        "summary": summary,
        "results": results[:max_results],
    }


def format_results(data: dict, args) -> str:
    lines = []
    summary = data["summary"]
    lines.append("Ventris Engine — Constraint Propagation Results")
    lines.append("=" * 65)
    lines.append(f"Total words analyzed:  {summary['total_words']:,}")
    lines.append(f"Known (in lexicon):    {summary['known']:,}")
    lines.append(f"New candidates:        {summary['new_candidates']:,}")
    lines.append(f"No match:              {summary['no_match']:,}")
    lines.append(f"Min score threshold:   {summary['min_score']}")
    lines.append("")

    for r in data["results"]:
        if r.get("status") == "known":
            lines.append(f"  ✓ {r['word']:<25} = {r.get('reading','?'):<20} [{r.get('confidence','')}]")
        else:
            lang = r.get("language", {})
            lang_tag = lang.get("decision", "?")
            lang_conf = lang.get("confidence", 0)
            prefix = f"({r['prefix_removed']}-)" if r.get("prefix_removed") else ""
            suffix = f"(-{r['suffix_removed']})" if r.get("suffix_removed") else ""
            affix_info = f" [{prefix}stem{suffix}]" if prefix or suffix else ""

            src = r.get("source_lang", "")
            src_tag = f" ({src})" if src else ""
            lines.append(
                f"  → {r['word']:<25} skel={r['skeleton']:<8} "
                f"√{r['best_root']:<8} \"{r['best_meaning']}\" "
                f"dist={r['distance']:.2f} score={r['score']:.3f} "
                f"[{lang_tag} {lang_conf:.2f}]{affix_info}{src_tag}"
            )
            lines.append(f"    site={r.get('site','?')} doc={r.get('doc_id','?')} type={r.get('text_type','?')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ventris Engine constraint propagation")
    parser.add_argument("--min-score", type=float, default=0.4, help="Minimum score threshold")
    parser.add_argument("--new-only", action="store_true", help="Show only new (not in lexicon) readings")
    parser.add_argument("--tablet", help="Analyze a single tablet (e.g., HT86a)")
    parser.add_argument("--max-results", type=int, default=50, help="Max results to show")
    parser.add_argument("--beam-width", type=int, default=16, help="Beam search width")
    parser.add_argument("--alt-confidence", type=float, default=0.5, help="Confidence for neutralization alternatives")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--language", choices=["multi", "semitic-only", "contact-aware"],
                        default="multi", help="Language filtering mode")
    parser.add_argument("--site-priors", action="store_true",
                        help="Enable per-site language priors")
    parser.add_argument("--site-consistency", action="store_true",
                        help="Enable two-pass site consistency refinement")
    parser.add_argument("--site-consistency-threshold", type=float, default=0.70,
                        help="Confidence threshold for consistency re-scoring")
    parser.add_argument("--phrase-grammar", type=str, default=None,
                        help="Path to artifacts/ dir with phrase grammar (enables slot-role priors)")
    parser.add_argument("--save", action="store_true",
                        help="Persist run to the run cache with full provenance (see ventris_runs.py)")
    parser.add_argument("--label", type=str, default=None,
                        help="Optional label for the saved run (e.g., 'nws-only', 'contact-test')")
    args = parser.parse_args()

    lang_opts = LanguageOptions(
        mode=args.language,
        use_site_priors=args.site_priors,
        use_site_consistency=args.site_consistency,
        site_consistency_threshold=args.site_consistency_threshold,
    )

    pg = None
    if args.phrase_grammar:
        pg = load_phrase_grammar(Path(args.phrase_grammar))
        print(f"Phrase grammar loaded: {pg.word_count} words, {pg.family_count} families",
              file=sys.stderr)

    try:
        data = run_propagation(
            min_score=args.min_score,
            new_only=args.new_only,
            tablet=args.tablet,
            max_results=args.max_results,
            beam_width=args.beam_width,
            alt_confidence=args.alt_confidence,
            lang_opts=lang_opts,
            phrase_grammar=pg,
        )
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2

    if args.save:
        from ..core.run_saver import save_run
        params = {
            "min_score": args.min_score,
            "new_only": args.new_only,
            "tablet": args.tablet,
            "max_results": args.max_results,
            "beam_width": args.beam_width,
            "alt_confidence": args.alt_confidence,
            "language": args.language,
            "site_priors": args.site_priors,
            "site_consistency": args.site_consistency,
            "site_consistency_threshold": args.site_consistency_threshold,
            "phrase_grammar": args.phrase_grammar,
        }
        run_dir = save_run("propagation", params, data, label=args.label)
        print(f"Run saved to {run_dir}", file=sys.stderr)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_results(data, args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
