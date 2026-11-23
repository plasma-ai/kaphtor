"""Unit tests for Kernel F (Commodity Ligature Acrophony)."""
from __future__ import annotations

import acrophony_f as af
import c_align as a
import c_render as r


def test_linear_b_ligatures_calibrate_as_greek():
    tables = r.load_tables()
    sign_table = a.load_signs()
    res = af.run_battery(af.LINEAR_B_LIGATURES, tables, sign_table, n_perm=500, seed=42)
    assert res["winner"] == "greek"
    assert res["languages"]["greek"]["p_perm"] <= 0.01
    assert res["languages"]["semitic"]["p_perm"] > 0.05


def test_linear_a_ligatures_identify_semitic():
    tables = r.load_tables()
    sign_table = a.load_signs()
    res = af.run_battery(af.LINEAR_A_LIGATURES, tables, sign_table, n_perm=500, seed=42)
    assert res["winner"] == "semitic"
    runner_ll = max(v["ll"] for k, v in res["languages"].items() if k != "semitic")
    assert res["languages"]["semitic"]["ll"] - runner_ll > 10.0
    assert res["languages"]["semitic"]["p_perm"] <= 0.01
