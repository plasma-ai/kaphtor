"""Unit tests for Kernel J (Zero-Curation Automated Dictionary Audit)."""
from __future__ import annotations

import auto_anchors_j as aj
import c_align as a
import c_render as r
import lid


def test_vocalize_egyptian_maps_consonantal_roots():
    segs = aj._vocalize_egyptian("kftiw")
    assert segs is not None
    assert "k" in segs and "f" in segs and "t" in segs and "i" in segs and "u" in segs
    assert aj._vocalize_egyptian("a") is None


def test_gloss_specificity_prefers_earlier_and_shorter_gloss():
    pat = aj.CONCEPT_PATTERNS["TOTAL"]
    direct = aj._gloss_specificity("total, sum", pat)
    buried = aj._gloss_specificity("a long ceremonial phrase referring to the total amount", pat)
    assert direct < buried


def test_run_battery_identifies_matching_language_on_synthetic_synsets():
    tables, signs = r.load_tables(), lid.sign_keys()
    sign_table = a.load_signs()
    # Synthetic minimal synsets (independent of external JSONL files)
    synsets = {
        "TOTAL": {
            "semitic": [tuple(a.keys("KU-RO", sign_table))],
            "greek": [tuple(a.keys("TO-SO", sign_table))],
            "anatolian": [tuple(a.keys("PA-TA", sign_table))],
            "hurrian": [tuple(a.keys("SU-NE", sign_table))],
            "egyptian": [tuple(a.keys("NE-PA", sign_table))],
        },
        "DEFICIT": {
            "semitic": [tuple(a.keys("KI-RO", sign_table))],
            "greek": [tuple(a.keys("O-PE-RO", sign_table))],
            "anatolian": [tuple(a.keys("MA-KU", sign_table))],
            "hurrian": [tuple(a.keys("TA-RI", sign_table))],
            "egyptian": [tuple(a.keys("SA-PA", sign_table))],
        },
    }
    lb = aj.run_battery([("TO-SO", "TOTAL"), ("O-PE-RO", "DEFICIT")], synsets, sign_table, n_perm=200, seed=42)
    assert lb["winner"] == "greek"
    assert lb["languages"]["greek"]["p_perm"] <= 0.05

    la = aj.run_battery([("KU-RO", "TOTAL"), ("KI-RO", "DEFICIT")], synsets, sign_table, n_perm=200, seed=42)
    assert la["winner"] == "semitic"
    assert la["languages"]["semitic"]["p_perm"] <= 0.05
    assert la["languages"]["semitic"]["p_concept"] is None  # 2! = 2 < 12


def test_exact_concept_shuffle_enumerates_distinct_labelings():
    sign_table = a.load_signs()
    synsets = {
        "TOTAL": {"semitic": [tuple(a.keys("KU-RO", sign_table))]},
        "DEFICIT": {"semitic": [tuple(a.keys("KI-RO", sign_table))]},
        "BOWL": {"semitic": [tuple(a.keys("A-KA-NU", sign_table))]},
        "JAR": {"semitic": [tuple(a.keys("KA-DI", sign_table))]},
    }
    parsed = [
        (tuple(a.keys("KU-RO", sign_table)), "TOTAL"),
        (tuple(a.keys("KI-RO", sign_table)), "DEFICIT"),
        (tuple(a.keys("A-KA-NU", sign_table)), "BOWL"),
        (tuple(a.keys("KA-DI", sign_table)), "JAR"),
    ]
    res = aj.exact_concept_shuffle(parsed, synsets, "semitic")
    assert res["n_concept_perms"] == 24  # 4!
    assert res["p_concept"] == round(1 / 24, 5)
    assert res["z_concept"] > 2.0


def test_dedup_and_expanded_prelinguistic_tiers_are_well_formed():
    sign_table = a.load_signs()
    assert len(aj.LA_DEDUP_7) == 7
    assert all(w != "PO-TO-KU-RO" for w, _ in aj.LA_DEDUP_7)
    assert len(aj.LA_DEDUP_9) == 9
    assert any(w == "DA-RO-PA" for w, _ in aj.LA_DEDUP_9)
    assert len(aj.LA_DEDUP_12) == 12
    assert len(aj.LA_DEDUP_11) == 11
    assert len(aj.LA_DEDUP_14) == 14
    assert len(aj.LA_DROPK_5) == 5
    assert len(aj.LB_ANCHORS_EXT9) == 9
    for tier in (aj.LA_DEDUP_7, aj.LA_DEDUP_9, aj.LA_DEDUP_12, aj.LA_DEDUP_11, aj.LA_DEDUP_14, aj.LA_DROPK_5, aj.LB_ANCHORS_EXT9):
        for w, concept in tier:
            assert concept in aj.CONCEPT_PATTERNS
            ks = a.keys(aj._normalize_doublet(w), sign_table)
            assert len(ks) >= 2
            assert all(isinstance(k, tuple) and len(k) == 2 for k in ks)
    # LA_DEDUP_9 must be 100% strict signs-a5-proposed.json without doublet folding
    for w, _ in aj.LA_DEDUP_9:
        ks = a.keys(w, sign_table)
        assert all(isinstance(k, tuple) and len(k) == 2 for k in ks)
    # LA_DROPK_5 must contain zero K-series signs
    for w, _ in aj.LA_DROPK_5:
        assert all(k[0] != "K" for k in a.keys(w, sign_table))


def test_expanded_dedup_tiers_pass_live_on_shipped_dictionaries():
    tables, signs = r.load_tables(), lid.sign_keys()
    sign_table = a.load_signs()
    synsets, _ = aj.extract_auto_synsets(tables, signs, max_per_concept=40)

    lb9 = aj.run_battery(aj.LB_ANCHORS_EXT9, synsets, sign_table, n_perm=500, seed=42)
    assert lb9["winner"] == "greek"
    assert lb9["languages"]["greek"]["p_perm"] <= 0.01
    assert lb9["languages"]["greek"]["p_concept"] <= 0.01
    assert lb9["languages"]["semitic"]["p_concept"] > 0.05

    la9 = aj.run_battery(aj.LA_DEDUP_9, synsets, sign_table, n_perm=500, seed=42)
    assert la9["winner"] == "semitic"
    assert la9["languages"]["semitic"]["p_perm"] <= 0.01
    assert la9["languages"]["semitic"]["p_concept"] <= 0.01
    assert la9["languages"]["greek"]["p_concept"] > 0.25
    assert la9["languages"]["sumerian"]["p_concept"] > 0.25

    la12 = aj.run_battery(aj.LA_DEDUP_12, synsets, sign_table, n_perm=500, seed=42)
    assert la12["winner"] == "semitic"
    assert la12["languages"]["semitic"]["p_perm"] <= 0.01
    assert la12["languages"]["semitic"]["p_concept"] <= 0.01

    dropk = aj.run_battery(aj.LA_DROPK_5, synsets, sign_table, n_perm=500, seed=42)
    assert dropk["winner"] == "semitic"
    assert dropk["languages"]["semitic"]["p_perm"] <= 0.05
