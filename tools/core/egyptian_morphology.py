"""Conservative fuzzy Egyptian morphology matching via affix stripping.

Strips known Egyptian derivational affixes from normalized forms and checks
the reduced form against an Egyptian root index. Each candidate carries a
confidence tier one level lower than equivalent Semitic matches (the engine
treats Egyptian as a contact language).
"""
from __future__ import annotations

try:
    from .semitic_morphology import (
        AffixRule,
        ConfidenceTier,
        FuzzyCandidate,
        StrippingMethod,
    )
except ImportError:
    from semitic_morphology import (
        AffixRule,
        ConfidenceTier,
        FuzzyCandidate,
        StrippingMethod,
    )

MIN_SKELETON_LENGTH = 2
MAX_DB_HITS = 5

EGYPTIAN_SUFFIX_RULES: tuple[AffixRule, ...] = (
    AffixRule("feminine_t", "t", "suffix"),
    AffixRule("plural_w", "w", "suffix"),
    AffixRule("nisbe_j", "j", "suffix"),
    AffixRule("nisbe_y", "y", "suffix"),
    AffixRule("abstract_wt", "wt", "suffix"),
    AffixRule("nisbe_tj", "tj", "suffix"),
)

EGYPTIAN_PREFIX_RULES: tuple[AffixRule, ...] = (
    AffixRule("m_locative", "m", "prefix"),
)


def _strip_suffix(form: str, rule: AffixRule) -> str | None:
    if form.endswith(rule.affix) and len(form) > len(rule.affix):
        reduced = form[: -len(rule.affix)]
        if len(reduced) >= MIN_SKELETON_LENGTH:
            return reduced
    return None


def _strip_prefix(form: str, rule: AffixRule) -> str | None:
    if form.startswith(rule.affix) and len(form) > len(rule.affix):
        reduced = form[len(rule.affix) :]
        if len(reduced) >= MIN_SKELETON_LENGTH:
            return reduced
    return None


def _confidence_for_hits(method: StrippingMethod, n_hits: int) -> ConfidenceTier:
    """One tier lower than Semitic equivalents."""
    if method == "suffix_stripped":
        return "medium" if n_hits == 1 else "low_review"
    return "low_review"


def egyptian_fuzzy_candidates(
    form: str,
    root_index: dict[str, list[str]],
) -> list[FuzzyCandidate]:
    """Try progressive affix stripping against an Egyptian root index.

    Order: suffix only (Tier 1) -> prefix only (Tier 2) -> both (Tier 3).
    Returns candidates sorted by confidence.
    """
    if len(form) < MIN_SKELETON_LENGTH:
        return []

    candidates: list[FuzzyCandidate] = []

    for rule in EGYPTIAN_SUFFIX_RULES:
        reduced = _strip_suffix(form, rule)
        if reduced:
            hits = root_index.get(reduced, [])
            if 0 < len(hits) <= MAX_DB_HITS:
                candidates.append(FuzzyCandidate(
                    reduced_skeleton=reduced,
                    confidence=_confidence_for_hits("suffix_stripped", len(hits)),
                    method="suffix_stripped",
                    stripped_affixes=(rule.affix,),
                    rule_names=(rule.name,),
                    entry_numbers=tuple(hits),
                ))

    for rule in EGYPTIAN_PREFIX_RULES:
        reduced = _strip_prefix(form, rule)
        if reduced:
            hits = root_index.get(reduced, [])
            if 0 < len(hits) <= MAX_DB_HITS:
                candidates.append(FuzzyCandidate(
                    reduced_skeleton=reduced,
                    confidence=_confidence_for_hits("prefix_stripped", len(hits)),
                    method="prefix_stripped",
                    stripped_affixes=(rule.affix,),
                    rule_names=(rule.name,),
                    entry_numbers=tuple(hits),
                ))

    for pre_rule in EGYPTIAN_PREFIX_RULES:
        pre_reduced = _strip_prefix(form, pre_rule)
        if not pre_reduced:
            continue
        for suf_rule in EGYPTIAN_SUFFIX_RULES:
            reduced = _strip_suffix(pre_reduced, suf_rule)
            if reduced:
                hits = root_index.get(reduced, [])
                if 0 < len(hits) <= MAX_DB_HITS:
                    candidates.append(FuzzyCandidate(
                        reduced_skeleton=reduced,
                        confidence="low_review",
                        method="prefix_suffix_stripped",
                        stripped_affixes=(pre_rule.affix, suf_rule.affix),
                        rule_names=(pre_rule.name, suf_rule.name),
                        entry_numbers=tuple(hits),
                    ))

    best: dict[str, FuzzyCandidate] = {}
    tier_order = {"high": 0, "medium": 1, "low_review": 2}
    for c in candidates:
        existing = best.get(c.reduced_skeleton)
        if not existing or tier_order[c.confidence] < tier_order[existing.confidence]:
            best[c.reduced_skeleton] = c

    return sorted(best.values(), key=lambda c: tier_order[c.confidence])
