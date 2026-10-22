"""Tests for lib/anatolian_morphology.py — Anatolian affix stripping."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.core.anatolian_morphology import (
    TOPONYM_SUFFIXES,
    anatolian_fuzzy_candidates,
)


@pytest.fixture
def anat_idx():
    """Minimal Anatolian root index for testing."""
    return {
        "millawand": ["100"],
        "parh": ["200"],
        "massanal": ["300"],
        "tarhu": ["400"],
        "tarhunt": ["500"],
        "hass": ["600"],
    }


# --- Suffix stripping ---

class TestSuffixStripping:
    def test_adjective_iya(self, anat_idx):
        results = anatolian_fuzzy_candidates("millawandiya", anat_idx)
        assert any(r.reduced_skeleton == "millawand" and "adjective_iya" in r.rule_names for r in results)

    def test_toponym_assa(self, anat_idx):
        results = anatolian_fuzzy_candidates("parhassa", anat_idx)
        assert any(r.reduced_skeleton == "parh" and "toponym_assa" in r.rule_names for r in results)

    def test_denominative_alli(self, anat_idx):
        results = anatolian_fuzzy_candidates("massanalalli", anat_idx)
        assert any(r.reduced_skeleton == "massanal" and "denominative_alli" in r.rule_names for r in results)

    def test_denominative_assi(self, anat_idx):
        results = anatolian_fuzzy_candidates("tarhuassi", anat_idx)
        assert any(r.reduced_skeleton == "tarhu" and "denominative_assi" in r.rule_names for r in results)

    def test_possessive_wanni(self, anat_idx):
        results = anatolian_fuzzy_candidates("tarhuntwanni", anat_idx)
        assert any(r.reduced_skeleton == "tarhunt" and "possessive_wanni" in r.rule_names for r in results)

    def test_abstract_atar(self, anat_idx):
        results = anatolian_fuzzy_candidates("hassatar", anat_idx)
        assert any(r.reduced_skeleton == "hass" and "abstract_atar" in r.rule_names for r in results)


# --- Confidence downgrade ---

class TestConfidenceDowngrade:
    def test_suffix_single_hit_is_medium(self, anat_idx):
        results = anatolian_fuzzy_candidates("millawandiya", anat_idx)
        best = results[0]
        assert best.confidence == "medium"

    def test_suffix_multiple_hits_is_low_review(self):
        idx = {"abcde": ["1", "2", "3"]}
        results = anatolian_fuzzy_candidates("abcdeiya", idx)
        if results:
            assert results[0].confidence == "low_review"

    def test_never_returns_high(self, anat_idx):
        results = anatolian_fuzzy_candidates("millawandiya", anat_idx)
        for r in results:
            assert r.confidence != "high"


# --- No prefix stripping ---

class TestNoPrefixes:
    def test_no_prefix_stripping(self, anat_idx):
        results = anatolian_fuzzy_candidates("xmillawand", anat_idx)
        assert all(r.method != "prefix_stripped" for r in results)

    def test_no_prefix_suffix_combined(self, anat_idx):
        results = anatolian_fuzzy_candidates("xmillawandiya", anat_idx)
        assert all(r.method != "prefix_suffix_stripped" for r in results)


# --- Guards ---

class TestGuards:
    def test_min_length_guard(self, anat_idx):
        results = anatolian_fuzzy_candidates("ab", anat_idx)
        assert results == []

    def test_min_length_after_stripping(self):
        idx = {"ab": ["1"]}
        results = anatolian_fuzzy_candidates("abiya", idx)
        assert results == []

    def test_max_hits_guard(self):
        idx = {"abcde": [str(i) for i in range(10)]}
        results = anatolian_fuzzy_candidates("abcdeiya", idx)
        assert results == []


# --- Deduplication ---

class TestDeduplication:
    def test_best_confidence_wins(self, anat_idx):
        results = anatolian_fuzzy_candidates("millawandiya", anat_idx)
        skels = [r.reduced_skeleton for r in results]
        assert skels.count("millawand") == 1

    def test_sorted_by_confidence(self):
        idx = {"abcde": ["1"], "abcd": ["2"]}
        results = anatolian_fuzzy_candidates("abcdeiya", idx)
        if len(results) >= 2:
            tier_order = {"high": 0, "medium": 1, "low_review": 2}
            confidences = [tier_order[r.confidence] for r in results]
            assert confidences == sorted(confidences)


# --- Toponym constants ---

class TestToponymConstants:
    def test_toponym_suffixes_defined(self):
        assert "assa" in TOPONYM_SUFFIXES
        assert "anda" in TOPONYM_SUFFIXES
        assert "issos" in TOPONYM_SUFFIXES
