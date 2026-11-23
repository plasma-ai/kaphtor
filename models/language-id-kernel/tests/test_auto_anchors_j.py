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
