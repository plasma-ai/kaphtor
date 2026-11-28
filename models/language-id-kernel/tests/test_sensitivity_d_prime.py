"""Unit tests for sensitivity_d_prime.py (exploratory Kernel D' sensitivity ladder)."""
from __future__ import annotations

import anchors_d as ad
import c_align as a
import sensitivity_d_prime as sd


def test_clean_tiers_exclude_kapa_and_respect_strict_lb():
    sign_table = a.load_signs()
    for name, anc, pa3_folded, _ in sd.TIERS:
        if name != "D_EXT_13_WITH_KAPA":
            assert all(w != "KA-PA" for w, _ in anc), f"KA-PA leaked into clean tier {name}"
        if not pa3_folded:
            for w, _ in anc:
                ks = a.keys(w, sign_table)
                assert all(isinstance(k, tuple) and len(k) == 2 for k in ks), f"Non-strict sign in {name}: {w}"
    # K-free subsets must hold zero K-series signs
    st_pa3 = dict(sign_table)
    st_pa3["PA3"] = ("P", "a")
    for w, _ in sd.D_DROPK_STRICT_4 + sd.D_DROPK_PA3_6:
        ks = a.keys(w.replace("₃", "3"), st_pa3)
        assert all(k[0] != "K" for k in ks), f"K-series sign leaked into {w}"


def test_sensitivity_ladder_reproduces_and_beats_rivals():
    res = sd.run_all(n_perm=200, seed=20261122)
    assert res["_meta"]["frozen_synsets"] is True
    assert len(res["_meta"]["anchors_d_sha256"]) == 64

    t = res["tiers"]
    # Exact match to signed Kernel D baseline
    assert t["D_BASE_8"]["winner"] == "semitic"
    assert abs(t["D_BASE_8"]["delta_ll"] - 13.5845) < 1e-3

    # Strict-LB D_STRICT_9 (incl. blind untranslated DA-RO-PA, zero KA-PA, zero PA3) exceeds 1.5M:1
    assert t["D_STRICT_9"]["winner"] == "semitic"
    assert t["D_STRICT_9"]["bf"] > 1_500_000
    assert t["D_STRICT_9"]["languages"]["semitic"]["p_perm"] <= 0.01

    # PA3-folded D_EXT_12 (zero KA-PA) exceeds 6M:1
    assert t["D_EXT_12"]["winner"] == "semitic"
    assert t["D_EXT_12"]["bf"] > 6_000_000

    # Strict-LB ablations pass cleanly without PA3 or KA-PA
    assert t["D_NO_LOANS_STRICT_6"]["winner"] == "semitic"
    assert t["D_NO_LOANS_STRICT_6"]["bf"] > 1000
    assert t["D_DROPK_STRICT_4"]["winner"] == "semitic"
    assert t["D_DROPK_STRICT_4"]["languages"]["semitic"]["p_perm"] <= 0.05
    # Signed anchors_d SYNSETS remain unchanged (4-6 entries per slot)
    assert len(ad.LINEAR_A_ANCHORS_STRICT) == 8
