"""Conservative fuzzy Semitic skeleton matching via affix stripping.

Strips known morphological affixes from consonantal skeletons and checks
the reduced form against the Proto-Semitic database index. Each candidate
carries a confidence tier and audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConfidenceTier = Literal["high", "medium", "low_review"]
StrippingMethod = Literal["suffix_stripped", "prefix_stripped", "prefix_suffix_stripped"]

MIN_SKELETON_LENGTH = 3
MIN_SKELETON_LENGTH_COMPLETION = 2
MAX_DB_HITS = 5


@dataclass(frozen=True)
class AffixRule:
    name: str
    affix: str
    position: Literal["suffix", "prefix"]


SUFFIX_RULES: tuple[AffixRule, ...] = (
    AffixRule("feminine_t", "t", "suffix"),
    AffixRule("feminine_at", "at", "suffix"),
    AffixRule("plural_m", "m", "suffix"),
    AffixRule("plural_n", "n", "suffix"),
    AffixRule("pronominal_h", "h", "suffix"),
    AffixRule("pronominal_hw", "hw", "suffix"),
    AffixRule("pronominal_hm", "hm", "suffix"),
)

PREFIX_RULES: tuple[AffixRule, ...] = (
    AffixRule("ma_nominal", "m", "prefix"),
    AffixRule("ta_prefix", "t", "prefix"),
    AffixRule("ya_prefix", "y", "prefix"),
    AffixRule("na_prefix", "n", "prefix"),
)

# Roots where the initial consonant looks like a prefix but is radical
RADICAL_EXCEPTIONS: frozenset[str] = frozenset({
    "mwt",   # √m-w-t "to die"
    "mnt",   # √m-n-t "to count/allot"
    "mny",   # √m-n-y "to allot"
    "mlk",   # √m-l-k "to rule"
    "ymm",   # √y-m-m "sea" (Yamm)
    "ym",    # √y-m "sea"
    "yld",   # √y-l-d "to give birth"
    "yšb",   # √y-š-b "to sit"
    "yšr",   # √y-š-r "to be straight"
    "tnn",   # √t-n-n "dragon/Tunnanu"
    "thm",   # √t-h-m "deep/Tehom"
    "nhr",   # √n-h-r "river"
    "ntn",   # √n-t-n "to give"
    "nšm",   # √n-š-m "breath"
})


@dataclass(frozen=True)
class FuzzyCandidate:
    reduced_skeleton: str
    confidence: ConfidenceTier
    method: StrippingMethod
    stripped_affixes: tuple[str, ...]
    rule_names: tuple[str, ...]
    entry_numbers: tuple[str, ...]


def _strip_suffix(skeleton: str, rule: AffixRule, min_len: int = MIN_SKELETON_LENGTH) -> str | None:
    """Strip a suffix from a skeleton. Returns reduced form or None."""
    if skeleton.endswith(rule.affix) and len(skeleton) > len(rule.affix):
        reduced = skeleton[:-len(rule.affix)]
        if len(reduced) >= min_len:
            return reduced
    return None


def _strip_prefix(skeleton: str, rule: AffixRule, min_len: int = MIN_SKELETON_LENGTH) -> str | None:
    """Strip a prefix from a skeleton. Returns reduced form or None."""
    if skeleton.startswith(rule.affix) and len(skeleton) > len(rule.affix):
        reduced = skeleton[len(rule.affix):]
        if len(reduced) >= min_len:
            return reduced
    return None


def _confidence_for_hits(method: StrippingMethod, n_hits: int) -> ConfidenceTier:
    if method == "suffix_stripped":
        return "high" if n_hits == 1 else "medium"
    if method == "prefix_stripped":
        return "medium" if n_hits == 1 else "low_review"
    return "low_review"


def fuzzy_skeleton_candidates(
    skeleton: str,
    skeleton_index: dict[str, list[str]],
    allow_biconsonantal: bool = False,
) -> list[FuzzyCandidate]:
    """Try progressive affix stripping to find database matches.

    Order: suffix only (Tier 1) → prefix only (Tier 2) → both (Tier 3).
    Returns all valid candidates sorted by confidence.

    When allow_biconsonantal=True, stripping may produce 2-consonant reduced
    forms (for downstream triconsonantal root completion).
    """
    min_len = MIN_SKELETON_LENGTH_COMPLETION if allow_biconsonantal else MIN_SKELETON_LENGTH
    if len(skeleton) < min_len:
        return []

    candidates: list[FuzzyCandidate] = []

    # Tier 1: suffix stripping (radical exceptions don't apply — they protect prefixes)
    for rule in SUFFIX_RULES:
        reduced = _strip_suffix(skeleton, rule, min_len)
        if reduced:
            hits = skeleton_index.get(reduced, [])
            if 0 < len(hits) <= MAX_DB_HITS:
                candidates.append(FuzzyCandidate(
                    reduced_skeleton=reduced,
                    confidence=_confidence_for_hits("suffix_stripped", len(hits)),
                    method="suffix_stripped",
                    stripped_affixes=(rule.affix,),
                    rule_names=(rule.name,),
                    entry_numbers=tuple(hits),
                ))

    # Tier 2: prefix stripping
    for rule in PREFIX_RULES:
        reduced = _strip_prefix(skeleton, rule, min_len)
        if reduced:
            if skeleton in RADICAL_EXCEPTIONS:
                continue
            hits = skeleton_index.get(reduced, [])
            if 0 < len(hits) <= MAX_DB_HITS:
                candidates.append(FuzzyCandidate(
                    reduced_skeleton=reduced,
                    confidence=_confidence_for_hits("prefix_stripped", len(hits)),
                    method="prefix_stripped",
                    stripped_affixes=(rule.affix,),
                    rule_names=(rule.name,),
                    entry_numbers=tuple(hits),
                ))

    # Tier 3: prefix + suffix
    for pre_rule in PREFIX_RULES:
        pre_reduced = _strip_prefix(skeleton, pre_rule, min_len)
        if not pre_reduced or skeleton in RADICAL_EXCEPTIONS:
            continue
        for suf_rule in SUFFIX_RULES:
            reduced = _strip_suffix(pre_reduced, suf_rule, min_len)
            if reduced:
                hits = skeleton_index.get(reduced, [])
                if 0 < len(hits) <= MAX_DB_HITS:
                    candidates.append(FuzzyCandidate(
                        reduced_skeleton=reduced,
                        confidence="low_review",
                        method="prefix_suffix_stripped",
                        stripped_affixes=(pre_rule.affix, suf_rule.affix),
                        rule_names=(pre_rule.name, suf_rule.name),
                        entry_numbers=tuple(hits),
                    ))

    # Deduplicate: keep best confidence per reduced skeleton
    best: dict[str, FuzzyCandidate] = {}
    tier_order = {"high": 0, "medium": 1, "low_review": 2}
    for c in candidates:
        existing = best.get(c.reduced_skeleton)
        if not existing or tier_order[c.confidence] < tier_order[existing.confidence]:
            best[c.reduced_skeleton] = c

    return sorted(best.values(), key=lambda c: tier_order[c.confidence])
