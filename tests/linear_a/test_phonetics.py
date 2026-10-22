"""Regression tests for phonetics.py — canonicalization and distance tables.

Contact-lexicon entries written with non-canonical characters (θ, ġ, đ, Syriac,
etc.) must map to the canonical letters, or they never match.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.phonetics import (
    EGYPTIAN_DISTANCES,
    GUTTURAL_PHONEMES,
    SEMITIC_DISTANCES,
    guttural_transparent_levenshtein,
    normalize_phonemes,
    weighted_levenshtein,
)


class TestCanonicalMapping:
    """_TO_CANONICAL maps contact-lexicon encoding variants to canonical phonemes."""

    def test_greek_theta_to_interdental(self):
        assert normalize_phonemes("θ") == "ṯ"

    def test_cyrillic_theta_to_interdental(self):
        assert normalize_phonemes("ө") == "ṯ"

    def test_g_variants_to_ghain(self):
        assert normalize_phonemes("ġ") == "ġ"
        assert normalize_phonemes("ǵ") == "ġ"
        assert normalize_phonemes("ḡ") == "ġ"

    def test_ipa_gamma_to_ghain(self):
        assert normalize_phonemes("ɣ") == "ġ"

    def test_d_stroke_to_interdental(self):
        assert normalize_phonemes("đ") == "ḏ"

    def test_greek_delta_to_interdental(self):
        assert normalize_phonemes("δ") == "ḏ"

    def test_s_cedilla_to_emphatic(self):
        assert normalize_phonemes("ş") == "ṣ"

    def test_t_variants_to_emphatic(self):
        assert normalize_phonemes("ṱ") == "ṭ"
        assert normalize_phonemes("ț") == "ṭ"

    def test_h_stroke_to_pharyngeal(self):
        assert normalize_phonemes("ħ") == "ḥ"

    def test_ayin_variants(self):
        assert normalize_phonemes("ˁ") == "ʿ"

    def test_aleph_variants(self):
        assert normalize_phonemes("ʼ") == "ʾ"
        assert normalize_phonemes("’") == "ʾ"

    def test_syriac_basic(self):
        assert normalize_phonemes("ܫ") == "š"
        assert normalize_phonemes("ܬ") == "t"
        assert normalize_phonemes("ܩ") == "q"

    def test_syriac_full_word(self):
        assert normalize_phonemes("ܟܬܒ") == "ktb"

    def test_h_macron_below_both_cases(self):
        assert normalize_phonemes("H̱") == "ḫ"
        assert normalize_phonemes("ẖ") == "ḫ"

    def test_existing_canonicals_preserved(self):
        assert normalize_phonemes("š") == "š"
        assert normalize_phonemes("ṣ") == "ṣ"
        assert normalize_phonemes("ṯ") == "ṯ"
        assert normalize_phonemes("ḏ") == "ḏ"
        assert normalize_phonemes("ḥ") == "ḥ"
        assert normalize_phonemes("ḫ") == "ḫ"

    def test_multi_char_still_works(self):
        assert normalize_phonemes("sh") == "š"
        assert normalize_phonemes("ts") == "ṣ"


class TestGhainDistances:
    """ġ (PS voiced velar fricative) has distance entries in all tables."""

    def test_ghain_in_semitic(self):
        assert ("ġ", "g") in SEMITIC_DISTANCES
        assert ("ġ", "ʿ") in SEMITIC_DISTANCES
        assert ("ġ", "k") in SEMITIC_DISTANCES
        assert ("ġ", "ḫ") in SEMITIC_DISTANCES
        assert ("ġ", "q") in SEMITIC_DISTANCES

    def test_ghain_in_egyptian(self):
        assert ("ġ", "g") in EGYPTIAN_DISTANCES
        assert ("ġ", "ʿ") in EGYPTIAN_DISTANCES

    def test_ghain_is_guttural(self):
        assert "ġ" in GUTTURAL_PHONEMES

    def test_ghain_g_closer_than_ghain_k(self):
        assert SEMITIC_DISTANCES[("ġ", "g")] < SEMITIC_DISTANCES[("ġ", "k")]

    def test_ghain_ayin_closer_than_ghain_q(self):
        assert SEMITIC_DISTANCES[("ġ", "ʿ")] < SEMITIC_DISTANCES[("ġ", "q")]


class TestMixedEncodingRegression:
    """Mixed-encoding regressions."""

    def test_tdr_exact(self):
        """Skeleton ṯdr vs Ugaritic ṯdr — d=0.0 full mode."""
        d = weighted_levenshtein("ṯdr", "ṯdr")
        assert d == 0.0

    def test_theta_encoded_tdr_exact(self):
        """The actual bug: θdr (DULAT encoding) must now match ṯdr at d=0.0."""
        d = weighted_levenshtein("ṯdr", "θdr")
        assert d == 0.0

    def test_ktn_exact(self):
        """Skeleton kṯn vs Ugaritic kṯn — d=0.0 full mode."""
        d = weighted_levenshtein("kṯn", "kṯn")
        assert d == 0.0

    def test_ghain_encoded_glmt(self):
        """Skeleton rmt vs ġlmt — guttural-transparent d should be low."""
        d = guttural_transparent_levenshtein("rmt", "ġlmt")
        assert d < 0.5

    def test_ghain_guttural_transparent(self):
        """ġ in a root should cost 0.1 insertion (guttural transparency)."""
        d = guttural_transparent_levenshtein("mr", "mġr")
        assert abs(d - 0.1) < 0.01

    def test_mixed_encoding_equivalence(self):
        """θdr and ṯdr must produce identical distance to any target."""
        target = "šdr"
        d1 = weighted_levenshtein(target, "θdr")
        d2 = weighted_levenshtein(target, "ṯdr")
        assert d1 == d2


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
