"""Tests for lib/egyptian_morphology.py — Egyptian affix stripping."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.core.egyptian_morphology import (
    egyptian_fuzzy_candidates,
)


@pytest.fixture
def egy_idx():
    """Minimal Egyptian root index for testing."""
    return {
        "nfr": ["100"],
        "kfti": ["200"],
        "mn": ["300"],
        "ḥr": ["400"],
        "ḥqꜣ": ["500"],
        "nsw": ["600"],
        "ḥꜣwnbw": ["700"],
    }


# --- Suffix stripping ---

class TestSuffixStripping:
    def test_feminine_t(self, egy_idx):
        results = egyptian_fuzzy_candidates("nfrt", egy_idx)
        assert any(r.reduced_skeleton == "nfr" and "feminine_t" in r.rule_names for r in results)

    def test_plural_w(self, egy_idx):
        results = egyptian_fuzzy_candidates("kftiw", egy_idx)
        assert any(r.reduced_skeleton == "kfti" and "plural_w" in r.rule_names for r in results)

    def test_nisbe_j(self, egy_idx):
        results = egyptian_fuzzy_candidates("ḥqꜣj", egy_idx)
        assert any(r.reduced_skeleton == "ḥqꜣ" and "nisbe_j" in r.rule_names for r in results)

    def test_nisbe_y(self, egy_idx):
        results = egyptian_fuzzy_candidates("ḥqꜣy", egy_idx)
        assert any(r.reduced_skeleton == "ḥqꜣ" and "nisbe_y" in r.rule_names for r in results)

    def test_abstract_wt(self, egy_idx):
        results = egyptian_fuzzy_candidates("ḥꜣwnbwwt", egy_idx)
        assert any(r.reduced_skeleton == "ḥꜣwnbw" and "abstract_wt" in r.rule_names for r in results)

    def test_nisbe_tj(self, egy_idx):
        results = egyptian_fuzzy_candidates("nswtj", egy_idx)
        assert any(r.reduced_skeleton == "nsw" and "nisbe_tj" in r.rule_names for r in results)


# --- Prefix stripping ---

class TestPrefixStripping:
    def test_m_locative(self, egy_idx):
        results = egyptian_fuzzy_candidates("mnfr", egy_idx)
        assert any(r.reduced_skeleton == "nfr" and "m_locative" in r.rule_names for r in results)

    def test_prefix_confidence_low_review(self, egy_idx):
        results = egyptian_fuzzy_candidates("mnfr", egy_idx)
        prefix_results = [r for r in results if r.method == "prefix_stripped"]
        assert all(r.confidence == "low_review" for r in prefix_results)


# --- Prefix + suffix ---

class TestPrefixSuffix:
    def test_prefix_suffix_combined(self, egy_idx):
        results = egyptian_fuzzy_candidates("mnfrt", egy_idx)
        assert any(r.method == "prefix_suffix_stripped" for r in results)

    def test_prefix_suffix_always_low_review(self, egy_idx):
        results = egyptian_fuzzy_candidates("mnfrt", egy_idx)
        combined = [r for r in results if r.method == "prefix_suffix_stripped"]
        assert all(r.confidence == "low_review" for r in combined)


# --- Confidence downgrade ---

class TestConfidenceDowngrade:
    def test_suffix_single_hit_is_medium(self, egy_idx):
        results = egyptian_fuzzy_candidates("nfrt", egy_idx)
        best = results[0]
        assert best.confidence == "medium"

    def test_suffix_multiple_hits_is_low_review(self):
        idx = {"abc": ["1", "2", "3"]}
        results = egyptian_fuzzy_candidates("abct", idx)
        if results:
            assert results[0].confidence == "low_review"

    def test_never_returns_high(self, egy_idx):
        results = egyptian_fuzzy_candidates("nfrt", egy_idx)
        for r in results:
            assert r.confidence != "high"


# --- Guards ---

class TestGuards:
    def test_min_length_guard(self, egy_idx):
        results = egyptian_fuzzy_candidates("x", egy_idx)
        assert results == []

    def test_min_length_after_stripping_biconsonantal(self):
        idx = {"mn": ["1"]}
        results = egyptian_fuzzy_candidates("mnt", idx)
        assert any(r.reduced_skeleton == "mn" for r in results)

    def test_min_length_blocks_single_char(self):
        idx = {"a": ["1"]}
        results = egyptian_fuzzy_candidates("at", idx)
        assert results == []

    def test_max_hits_guard(self):
        idx = {"abc": [str(i) for i in range(10)]}
        results = egyptian_fuzzy_candidates("abct", idx)
        assert results == []


# --- Deduplication ---

class TestDeduplication:
    def test_best_confidence_wins(self, egy_idx):
        results = egyptian_fuzzy_candidates("nfrt", egy_idx)
        skels = [r.reduced_skeleton for r in results]
        assert skels.count("nfr") == 1

    def test_sorted_by_confidence(self, egy_idx):
        results = egyptian_fuzzy_candidates("mnfrt", egy_idx)
        if len(results) >= 2:
            tier_order = {"high": 0, "medium": 1, "low_review": 2}
            confidences = [tier_order[r.confidence] for r in results]
            assert confidences == sorted(confidences)
