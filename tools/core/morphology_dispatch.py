"""Language-aware morphology dispatcher.

Routes fuzzy affix stripping to the appropriate language-specific engine.
Re-exports shared types for convenience.
"""
from __future__ import annotations

try:
    from .anatolian_morphology import anatolian_fuzzy_candidates
    from .egyptian_morphology import egyptian_fuzzy_candidates
    from .semitic_morphology import (
        AffixRule,
        ConfidenceTier,
        FuzzyCandidate,
        StrippingMethod,
        fuzzy_skeleton_candidates,
    )
except ImportError:
    from anatolian_morphology import anatolian_fuzzy_candidates
    from egyptian_morphology import egyptian_fuzzy_candidates
    from semitic_morphology import (
        AffixRule,
        ConfidenceTier,
        FuzzyCandidate,
        StrippingMethod,
        fuzzy_skeleton_candidates,
    )

__all__ = [
    "AffixRule",
    "ConfidenceTier",
    "FuzzyCandidate",
    "StrippingMethod",
    "fuzzy_candidates",
]


def fuzzy_candidates(
    form: str,
    language: str,
    index: dict[str, list[str]],
) -> list[FuzzyCandidate]:
    """Route to the appropriate morphology engine by language.

    Supported languages: "Semitic", "Egyptian", "Anatolian".
    Unknown languages return an empty list.
    """
    lang = language.lower()
    if lang == "semitic":
        return fuzzy_skeleton_candidates(form, index)
    if lang == "egyptian":
        return egyptian_fuzzy_candidates(form, index)
    if lang == "anatolian":
        return anatolian_fuzzy_candidates(form, index)
    return []
