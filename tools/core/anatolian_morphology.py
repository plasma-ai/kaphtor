"""Conservative fuzzy Anatolian (Luwian/Hittite) morphology matching.

Strips known derivational suffixes from normalized Anatolian forms and checks
the reduced form against an Anatolian root index. Suffix-only — Anatolian
prefixes are not productive in derivational morphology.

Confidence tiers are one level lower than equivalent Semitic matches
(the engine treats Anatolian as a contact language).
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

MIN_SKELETON_LENGTH = 3
MAX_DB_HITS = 5

ANATOLIAN_SUFFIX_RULES: tuple[AffixRule, ...] = (
    AffixRule("adjective_iya", "iya", "suffix"),
    AffixRule("toponym_assa", "assa", "suffix"),
    AffixRule("denominative_alli", "alli", "suffix"),
    AffixRule("denominative_assi", "assi", "suffix"),
    AffixRule("possessive_wanni", "wanni", "suffix"),
    AffixRule("abstract_atar", "atar", "suffix"),
)

TOPONYM_SUFFIXES: frozenset[str] = frozenset({"assa", "anda", "issos"})


def _strip_suffix(form: str, rule: AffixRule) -> str | None:
    if form.endswith(rule.affix) and len(form) > len(rule.affix):
        reduced = form[: -len(rule.affix)]
        if len(reduced) >= MIN_SKELETON_LENGTH:
            return reduced
    return None


def _confidence_for_hits(method: StrippingMethod, n_hits: int) -> ConfidenceTier:
    """One tier lower than Semitic equivalents."""
    if method == "suffix_stripped":
        return "medium" if n_hits == 1 else "low_review"
    return "low_review"


def anatolian_fuzzy_candidates(
    form: str,
    root_index: dict[str, list[str]],
) -> list[FuzzyCandidate]:
    """Try suffix stripping against an Anatolian root index.

    Suffix-only (no productive prefixes in Anatolian derivational morphology).
    Returns candidates sorted by confidence.
    """
    if len(form) < MIN_SKELETON_LENGTH:
        return []

    candidates: list[FuzzyCandidate] = []

    for rule in ANATOLIAN_SUFFIX_RULES:
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

    best: dict[str, FuzzyCandidate] = {}
    tier_order = {"high": 0, "medium": 1, "low_review": 2}
    for c in candidates:
        existing = best.get(c.reduced_skeleton)
        if not existing or tier_order[c.confidence] < tier_order[existing.confidence]:
            best[c.reduced_skeleton] = c

    return sorted(best.values(), key=lambda c: tier_order[c.confidence])
