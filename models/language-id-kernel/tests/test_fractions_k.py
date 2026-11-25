"""Unit tests for Kernel K (fractions_k.py): Corazza-Ferrara fraction arithmetic, blind KU-RO, and accounting LID."""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fractions_k as fk  # noqa: E402


def test_parse_aegean_quantity_corazza_values():
    # 45 + J (1/2) = 91/2
    raw = "\U00010113\U0001010b\U00010746"  # 40 + 5 + A707(J=1/2)
    assert fk.parse_aegean_quantity(raw, fk.CORAZZA_2021) == Fraction(91, 2)
    # Corazza B (A702) = 1/5 vs legacy Bennett B = 1/3
    assert fk.parse_aegean_quantity("\U00010741", fk.CORAZZA_2021) == Fraction(1, 5)
    assert fk.parse_aegean_quantity("\U00010741", fk.BENNETT_LEGACY) == Fraction(1, 3)


def test_stage_k1_blindly_discovers_kuro_rank_one():
    res = fk.run_stage_k0_k1()
    assert res["top_discovered_sum_word"] == "KU-RO"
    assert res["corazza_kuro_exact_sums"] >= 8
    assert res["runner_up_exact_sums"] <= 2
    assert any(c["tablet"] == "HT 123+124a" for c in res["autopsy_conflicts"])
    prop = res["compound_fraction_properness"]
    assert prop["corazza_2021_strict_gt1_violations"] == 0
    assert prop["bennett_legacy_strict_gt1_violations"] >= 1


def test_stage_k2_linear_b_calibrates_greek_and_linear_a_selects_semitic():
    k2 = fk.run_stage_k2(cap=40, n_perm=1000, seed=42)
    lb = k2["calibration_linear_b"]
    assert lb["winner"] == "greek"
    assert lb["languages"]["greek"]["p_perm"] <= 0.05
    assert lb["languages"]["semitic"]["p_perm"] > 0.10
    if "linear_a_accounting_pair_dedup" in k2:
        la2 = k2["linear_a_accounting_pair_dedup"]
        assert la2["winner"] == "semitic"
        assert la2["delta_ll"] >= 1.0
        assert la2["languages"]["semitic"]["p_perm"] <= 0.05
        assert la2["languages"]["semitic"]["z_perm"] > la2["languages"]["greek"]["z_perm"]
    if "linear_a_accounting_triad" in k2:
        la = k2["linear_a_accounting_triad"]
        assert la["winner"] == "semitic"
        assert la["languages"]["semitic"]["p_perm"] <= 0.05
