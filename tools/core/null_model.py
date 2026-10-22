"""Permutation null models for hypothesis testing in the Ventris Engine.

Provides empirical p-values for three scoring axes:
- Site concentration: is a word's site specificity unusual given corpus structure?
- Slot compatibility: does a meaning's slot match exceed chance for same-language candidates?
- Neighbor coherence: do a word's corpus neighbors contain more lexicon entries than chance?

All functions use seeded random.Random instances for reproducibility without
contaminating global random state.

Used by hypothesis_test.py to gate the site axis (p < 0.05) and report
empirical confidence alongside slot and neighbor scores.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LANG_DECISION_KEYS = (
    "language",     # dict with "decision" key, from propagation results
    "source_lang",  # fallback flat key
)


def _lang_family(result: dict) -> str | None:
    """Extract language family label from a propagation result entry."""
    lang = result.get("language")
    if isinstance(lang, dict):
        return lang.get("decision")
    return result.get("source_lang") or None


def _slot_score_for_meaning(
    word: str,
    meaning: str,
    word_roles: dict[str, Any],
    decomposed_roles: dict[str, str] | None = None,
) -> float:
    """Compute slot compatibility score for (word, meaning) using phrase_grammar logic.

    Scores:
      MATCH          →  1.0
      COMPATIBLE     →  0.5
      UNDETERMINED   →  0.0
      MISMATCH       → -1.0

    These are the conceptual MATCH/COMPATIBLE/UNDETERMINED/MISMATCH tiers,
    mapped from PhraseGrammar.score_compatibility's adjustments:
      +0.10 (MATCH)       → 1.0
      +0.05 (COMPATIBLE)  → 0.5
       0.00 (NEUTRAL)     → 0.0
      -0.10 (MISMATCH)    → -1.0

    Importing here avoids circular imports and keeps the function self-contained.
    """
    # Import lazily so null_model can load without phrase_grammar on sys.path in
    # edge-case test scenarios. Try relative (package) first, then absolute (lib on path).
    try:
        from .phrase_grammar import ROLE_COMPATIBILITY, SEMANTIC_KEYWORDS
    except ImportError:
        from phrase_grammar import ROLE_COMPATIBILITY, SEMANTIC_KEYWORDS  # type: ignore[no-redef]
    import re

    entry = word_roles.get(word)
    if entry is None:
        return 0.0  # UNDETERMINED — no role data

    role = entry.get("role", "UNKNOWN_FORMULA_ELEMENT")
    if role == "UNKNOWN_FORMULA_ELEMENT":
        if decomposed_roles and word in decomposed_roles:
            role = decomposed_roles[word]
            if role == "LOW_INFORMATION_UNKNOWN":
                return 0.0
        else:
            return 0.0

    # Infer semantic category from meaning keywords (mirrors PhraseGrammar.infer_semantic_category)
    inferred = None
    if meaning:
        meaning_lower = meaning.lower()
        for keyword, category in SEMANTIC_KEYWORDS.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', meaning_lower):
                inferred = category
                break

    if inferred is None:
        return 0.0  # UNDETERMINED

    if inferred == role:
        return 1.0  # MATCH

    compatible_set = ROLE_COMPATIBILITY.get(role, set())
    if inferred in compatible_set:
        return 0.5  # COMPATIBLE

    return -1.0  # MISMATCH


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_site_null(
    word: str,
    corpus_index: dict[str, list[dict]],
    n_permutations: int = 1000,
    seed: int = 42,
) -> dict:
    """Compute observed site concentration and a permutation null distribution.

    Site concentration = max proportion of attestations at any single site.
    The null asks: given all sites present across the corpus, how often would
    a randomly-positioned word of the same attestation count reach this
    concentration or higher?

    Args:
        word: Linear A word in upper-case transliteration (e.g. 'KU-PA3-PA3').
        corpus_index: dict mapping word → list of attestation dicts, each
            containing at least {'site': str}. Built by hypothesis_test.py
            or the verification snippet.
        n_permutations: number of shuffle iterations.
        seed: RNG seed for reproducibility (does not affect global state).

    Returns:
        {
            "observed": float,       # max-site proportion for this word
            "null_mean": float,      # mean of null distribution
            "null_std": float,       # std of null distribution
            "p_value": float,        # fraction of null >= observed
            "n_permutations": int,
        }

    Edge cases:
        - 0 or 1 attestation → p_value = 1.0, observed = 1.0.
        - word not in corpus_index → same as 0 attestations.
    """
    attestations = corpus_index.get(word, [])
    n_word = len(attestations)

    if n_word <= 1:
        return {
            "observed": 1.0,
            "null_mean": 1.0,
            "null_std": 0.0,
            "p_value": 1.0,
            "n_permutations": n_permutations,
        }

    # Observed concentration: max fraction at any single site
    site_counts: dict[str, int] = defaultdict(int)
    for att in attestations:
        site_counts[att.get("site", "unknown")] += 1
    observed = max(site_counts.values()) / n_word

    # Build the pool of ALL site labels across the entire corpus
    all_sites: list[str] = []
    for atts in corpus_index.values():
        for att in atts:
            all_sites.append(att.get("site", "unknown"))

    pool_size = len(all_sites)
    if pool_size < n_word:
        # Corpus smaller than word count (degenerate case); fallback
        return {
            "observed": observed,
            "null_mean": observed,
            "null_std": 0.0,
            "p_value": 1.0,
            "n_permutations": n_permutations,
        }

    rng = random.Random(seed)
    null_values: list[float] = []

    for _ in range(n_permutations):
        # Sample n_word positions without replacement from the shuffled pool
        sample_sites = rng.sample(all_sites, n_word)
        sc: dict[str, int] = defaultdict(int)
        for s in sample_sites:
            sc[s] += 1
        null_values.append(max(sc.values()) / n_word)

    null_mean = sum(null_values) / n_permutations
    variance = sum((v - null_mean) ** 2 for v in null_values) / n_permutations
    null_std = variance ** 0.5
    p_value = (sum(1 for v in null_values if v >= observed) + 1) / (n_permutations + 1)

    return {
        "observed": round(observed, 4),
        "null_mean": round(null_mean, 4),
        "null_std": round(null_std, 4),
        "p_value": round(p_value, 4),
        "n_permutations": n_permutations,
    }


def build_slot_null(
    word: str,
    meaning: str,
    language: str,
    propagation_results: list[dict],
    word_roles: dict[str, Any],
    n_permutations: int = 1000,
    seed: int = 42,
    decomposed_roles: dict[str, str] | None = None,
) -> dict | None:
    """Compute empirical p-value for a word's slot compatibility score.

    The null distribution is built from same-language-family candidates in
    propagation_results. For each permutation, one of those meanings is
    randomly assigned to this word and scored for slot compatibility.

    A MATCH with p=0.03 means only 3% of random same-language meanings would
    match this slot — strong evidence. A MATCH with p=0.40 is weak.

    Args:
        word: Linear A word.
        meaning: Candidate meaning to evaluate.
        language: Language family label (e.g. 'NWS', 'Luwian', 'Egyptian').
            Used to select same-family meanings for the null pool.
        propagation_results: Full list of propagation result dicts from
            run_propagation()['results'].
        word_roles: dict mapping word → role entry (same as PhraseGrammar._word_roles,
            or built from WORD_ROLE_DOSSIER.json).
        n_permutations: number of shuffle iterations.
        seed: RNG seed.

    Returns:
        {
            "observed_score": float,
            "null_mean": float,
            "null_std": float,
            "p_value": float,
            "n_permutations": int,
        }
        or None if word has no role entry (slot axis not applicable).

    Edge case: if the null pool is empty (no same-language candidates), returns
    p_value = None embedded in the dict to signal insufficient data.
    """
    if word not in word_roles:
        return None

    observed_score = _slot_score_for_meaning(word, meaning, word_roles, decomposed_roles)

    # Build null pool: meanings from same-language candidates
    null_pool: list[str] = []
    for result in propagation_results:
        if result.get("word") == word:
            continue  # exclude self
        result_lang = _lang_family(result)
        if result_lang != language:
            continue
        candidate_meaning = result.get("best_meaning", "")
        if candidate_meaning:
            null_pool.append(candidate_meaning)

    if not null_pool:
        return {
            "observed_score": observed_score,
            "null_mean": None,
            "null_std": None,
            "p_value": None,
            "n_permutations": n_permutations,
        }

    rng = random.Random(seed)
    null_scores: list[float] = []

    for _ in range(n_permutations):
        rand_meaning = rng.choice(null_pool)
        null_scores.append(_slot_score_for_meaning(word, rand_meaning, word_roles, decomposed_roles))

    null_mean = sum(null_scores) / n_permutations
    variance = sum((s - null_mean) ** 2 for s in null_scores) / n_permutations
    null_std = variance ** 0.5
    p_value = (sum(1 for s in null_scores if s >= observed_score) + 1) / (n_permutations + 1)

    return {
        "observed_score": round(observed_score, 4),
        "null_mean": round(null_mean, 4),
        "null_std": round(null_std, 4),
        "p_value": round(p_value, 4),
        "n_permutations": n_permutations,
    }


def build_neighbor_null(
    word: str,
    corpus_index: dict[str, list[dict]],
    lexicon: dict[str, Any],
    n_permutations: int = 1000,
    seed: int = 42,
) -> dict:
    """Test whether a word's corpus neighbors contain more lexicon entries than chance.

    Observed rate = fraction of this word's unique neighbors that appear in lexicon.
    Null: for each permutation, pick a random corpus word with the same number of
    unique neighbors, compute its lexicon-neighbor rate. OR, if no word has the
    same neighbor count, shuffle lexicon membership across all corpus words.

    Args:
        word: Linear A word.
        corpus_index: Attestation index (same as build_site_null).
        lexicon: dict mapping word → entry (confirmed/probable readings).
            Typically built from lexicon.json['entries'] keyed by 'word'.
        n_permutations: number of shuffle iterations.
        seed: RNG seed.

    Returns:
        {
            "observed_rate": float,
            "null_mean": float,
            "null_std": float,
            "p_value": float,
            "n_permutations": int,
        }

    Edge cases:
        - word not in corpus_index or has no neighbors → observed_rate = 0.0,
          p_value = 1.0.
    """
    attestations = corpus_index.get(word, [])

    # Count ALL neighbor occurrences (with duplicates) and only count
    # CONFIRMED/PROBABLE lexicon entries — matches hypothesis_test.py's
    # test_neighbor_coherence() counting method.
    anchor_adjacent = 0
    total_neighbors = 0
    for att in attestations:
        for nb in att.get("neighbors", []):
            if nb != word:
                total_neighbors += 1
                if nb in lexicon:
                    entry = lexicon[nb]
                    if entry.get("confidence") in ("CONFIRMED", "PROBABLE"):
                        anchor_adjacent += 1

    if total_neighbors == 0:
        return {
            "observed_rate": 0.0,
            "null_mean": 0.0,
            "null_std": 0.0,
            "p_value": 1.0,
            "n_permutations": n_permutations,
        }

    observed_rate = anchor_adjacent / total_neighbors

    # Build corpus word list and per-word neighbor stats for the null
    # (same counting: all occurrences, CONFIRMED/PROBABLE only)
    corpus_words = [w for w in corpus_index if w != word]
    if not corpus_words:
        return {
            "observed_rate": round(observed_rate, 4),
            "null_mean": round(observed_rate, 4),
            "null_std": 0.0,
            "p_value": 1.0,
            "n_permutations": n_permutations,
        }

    # Precompute per-word neighbor rates (all occurrences, CONFIRMED/PROBABLE)
    corpus_neighbor_rates: dict[str, float] = {}
    for w, atts in corpus_index.items():
        if w == word:
            continue
        w_total = 0
        w_hits = 0
        for att in atts:
            for nb in att.get("neighbors", []):
                if nb != w:
                    w_total += 1
                    if nb in lexicon:
                        entry = lexicon[nb]
                        if entry.get("confidence") in ("CONFIRMED", "PROBABLE"):
                            w_hits += 1
        corpus_neighbor_rates[w] = w_hits / w_total if w_total > 0 else 0.0

    rng = random.Random(seed)
    null_rates: list[float] = []

    for _ in range(n_permutations):
        rand_word = rng.choice(corpus_words)
        null_rates.append(corpus_neighbor_rates.get(rand_word, 0.0))

    null_mean = sum(null_rates) / n_permutations
    variance = sum((r - null_mean) ** 2 for r in null_rates) / n_permutations
    null_std = variance ** 0.5
    p_value = (sum(1 for r in null_rates if r >= observed_rate) + 1) / (n_permutations + 1)

    return {
        "observed_rate": round(observed_rate, 4),
        "null_mean": round(null_mean, 4),
        "null_std": round(null_std, 4),
        "p_value": round(p_value, 4),
        "n_permutations": n_permutations,
    }


def compute_all_null_pvalues(
    candidates: list[dict],
    corpus_index: dict[str, list[dict]],
    propagation_results: list[dict],
    word_roles: dict[str, Any],
    lexicon: dict[str, Any],
    n_permutations: int = 1000,
    seed: int = 42,
    decomposed_roles: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Run all three null models for each candidate word.

    Args:
        candidates: List of propagation result dicts (each must have 'word' key).
            Typically a subset of run_propagation()['results'].
        corpus_index: Attestation index mapping word → list of attestation dicts.
        propagation_results: Full propagation results list (used as null pool for slot).
        word_roles: dict mapping word → role entry (from WORD_ROLE_DOSSIER).
        lexicon: dict mapping word → lexicon entry (from lexicon.json).
        n_permutations: permutation count for each test.
        seed: base seed; each test type uses a derived offset to ensure
            independent null draws while remaining reproducible.

    Returns:
        {
            word: {
                "site": { ... },      # from build_site_null
                "slot": { ... },      # from build_slot_null (or None if inapplicable)
                "neighbor": { ... },  # from build_neighbor_null
            },
            ...
        }
    """
    results: dict[str, dict] = {}

    for candidate in candidates:
        word = candidate.get("word")
        if not word:
            continue

        if word in results:
            continue  # deduplicate if word appears multiple times

        # Use offset seeds per axis so site/slot/neighbor permutations are independent
        site_result = build_site_null(
            word, corpus_index,
            n_permutations=n_permutations,
            seed=seed,
        )

        meaning = candidate.get("best_meaning", "")
        language = _lang_family(candidate) or ""
        slot_result = build_slot_null(
            word, meaning, language,
            propagation_results, word_roles,
            n_permutations=n_permutations,
            seed=seed + 1,
            decomposed_roles=decomposed_roles,
        )

        neighbor_result = build_neighbor_null(
            word, corpus_index, lexicon,
            n_permutations=n_permutations,
            seed=seed + 2,
        )

        results[word] = {
            "site": site_result,
            "slot": slot_result,
            "neighbor": neighbor_result,
        }

    return results
