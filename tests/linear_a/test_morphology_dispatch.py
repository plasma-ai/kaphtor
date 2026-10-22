"""Tests for lib/morphology_dispatch.py — language routing."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.core.morphology_dispatch import (
    AffixRule,
    ConfidenceTier,
    FuzzyCandidate,
    fuzzy_candidates,
)


@pytest.fixture
def semitic_idx():
    return {"bʕl": ["100"], "qtl": ["200"]}


@pytest.fixture
def egyptian_idx():
    return {"nfr": ["100"], "kfti": ["200"]}


@pytest.fixture
def anatolian_idx():
    return {"millawand": ["100"], "parh": ["200"]}


class TestRouting:
    def test_semitic_routes_correctly(self, semitic_idx):
        results = fuzzy_candidates("bʕlt", "Semitic", semitic_idx)
        assert any(r.reduced_skeleton == "bʕl" for r in results)

    def test_egyptian_routes_correctly(self, egyptian_idx):
        results = fuzzy_candidates("nfrt", "Egyptian", egyptian_idx)
        assert any(r.reduced_skeleton == "nfr" for r in results)

    def test_anatolian_routes_correctly(self, anatolian_idx):
        results = fuzzy_candidates("millawandiya", "Anatolian", anatolian_idx)
        assert any(r.reduced_skeleton == "millawand" for r in results)

    def test_unknown_language_returns_empty(self, semitic_idx):
        results = fuzzy_candidates("bʕlt", "Sumerian", semitic_idx)
        assert results == []

    def test_case_insensitive_routing(self, egyptian_idx):
        results = fuzzy_candidates("nfrt", "EGYPTIAN", egyptian_idx)
        assert any(r.reduced_skeleton == "nfr" for r in results)

    def test_empty_form_returns_empty(self, semitic_idx):
        results = fuzzy_candidates("", "Semitic", semitic_idx)
        assert results == []


class TestReExports:
    def test_fuzzy_candidate_importable(self):
        assert FuzzyCandidate is not None

    def test_affix_rule_importable(self):
        assert AffixRule is not None

    def test_confidence_tier_is_literal(self):
        assert ConfidenceTier is not None
