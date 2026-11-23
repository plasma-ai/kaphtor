"""Unit tests for Kernel D (anchors_d.py): distance metric, permutation invariance, and Linear B calibration."""
from __future__ import annotations

import anchors_d as ad
import c_align as a
import c_render as r


def test_cv_distance_properties():
    w1 = (("K", "u"), ("R", "o"))
    w2 = (("K", "u"), ("R", "u"))
    w3 = (("P", "a"), ("T", "i"))
    assert ad.cv_distance(w1, w1) == 0.0
    assert 0.0 < ad.cv_distance(w1, w2) < ad.cv_distance(w1, w3)


def test_linear_b_calibration_identifies_greek():
    tables = r.load_tables()
    sign_table = a.load_signs()
    signs = {k for k in sign_table.values() if isinstance(k, tuple)}
    res = ad.run_battery(ad.LINEAR_B_ANCHORS, tables, sign_table, signs, n_perm=500, seed=42)
    assert res["winner"] == "greek"
    assert res["languages"]["greek"]["p_perm"] <= 0.01
    runner_up_ll = max(res["languages"][l]["ll"] for l in ("semitic", "anatolian", "hurrian"))
    runner_up_z = max(res["languages"][l]["z_perm"] for l in ("semitic", "anatolian", "hurrian"))
    assert res["languages"]["greek"]["ll"] - runner_up_ll >= 5.0
    assert res["languages"]["greek"]["z_perm"] - runner_up_z >= 2.0
    assert res["languages"]["semitic"]["p_perm"] > 0.05
    assert res["languages"]["hurrian"]["p_perm"] > 0.05
