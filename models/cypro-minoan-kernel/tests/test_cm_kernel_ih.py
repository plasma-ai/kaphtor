"""Unit tests for models/cypro-minoan-kernel/cm_kernel_ih.py (Kernels CM-I1, CM-I2, CM-H)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

KERNEL_DIR = Path(__file__).resolve().parents[1]
if str(KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(KERNEL_DIR))

import cm_kernel_ih


def test_parse_ig_cypriot_greek_yields_calibration_corpus() -> None:
    cgk = cm_kernel_ih.parse_ig_cypriot_greek()
    assert len(cgk) >= 180
    assert all(len(w) >= 2 for w in cgk)


def test_manifest_strictly_t3_isolated() -> None:
    m = cm_kernel_ih.build_manifest()
    assert m["t5_compliant"] is True
    assert len(m["inputs"]) == 13
    for info in m["inputs"].values():
        assert "data/linear-a/" not in info["path"]
        assert "language-id-kernel" not in info["path"]


def test_phoneme_normalizers_handle_hebrew_matres_and_sumerian_ng() -> None:
    # Medial mater lectionis yod must not emit a phantom 'j' before the next consonant+vowel
    assert cm_kernel_ih.hebrew_to_segs("שִׂ֣יחַ") == ["s", "i", "k", "a"]
    # Geminated consonantal vav (dagesh + following vowel) must emit 'w', not shuruq 'u'
    assert cm_kernel_ih.hebrew_to_segs("חַוָּ֑ה") == ["k", "a", "w", "a"]
    assert cm_kernel_ih.hebrew_to_segs("צִוָּ֥ה") == ["z", "i", "w", "a"]
    # True shuruq and holam male remain pure vowels without consonantal 'w'
    assert cm_kernel_ih.hebrew_to_segs("מוּת") == ["m", "u", "t"]
    assert cm_kernel_ih.hebrew_to_segs("אוֹר") == ["o", "r"]
    # Sumerian velar nasal ŋ / ĝ must map to 'n' rather than being silently dropped
    assert cm_kernel_ih.latin_cuneiform_to_segs("ursaŋ") == ["u", "r", "s", "a", "n"]
    assert cm_kernel_ih.latin_cuneiform_to_segs("diŋir") == ["t", "i", "n", "i", "r"]
    assert cm_kernel_ih.latin_cuneiform_to_segs("saĝ") == ["s", "a", "n"]


def test_suite_ih_deterministic_and_calibrated() -> None:
    r1 = cm_kernel_ih.run_suite_ih(n_perm_i=100, n_perm_h=100, seed=20261125)
    r2 = cm_kernel_ih.run_suite_ih(n_perm_i=100, n_perm_h=100, seed=20261125)
    assert r1 == r2

    # In-script Cypriot Syllabic Greek calibration must pick Greek in both I1 and I2 (cypriot_plene)
    plene = r1["kernel_cm_i"]["cypriot_plene"]
    assert plene["train_counts"]["latin"] == 2500
    assert 300 <= plene["train_counts"]["sumerian"] <= 700
    assert plene["kernel_cm_i1_rival_exclusion"]["calib_cypriot_greek_ig_xv_1"]["winner"] == "greek"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["winner"] == "greek"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm12_valerio_emended"]["winner"] == "amathus_ec"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm2_only_valerio"]["winner"] == "amathus_ec"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm3_ugarit_control"]["winner"] != "amathus_ec"

    # Kernel H polarity reversal: CM 3 RASH Atab 004 favors ANE over Cypriot/Aegean; CM 1 clay balls favor Amathus EC
    kh = r1["kernel_cm_h_clay_balls"]
    rash_b = kh["onomastics"]["ctrl_rash_atab_004_cm3"]["bits_per_sign"]
    seq1_b = kh["onomastics"]["cm1_clay_ball_seq1"]["bits_per_sign"]
    assert kh["onomastics"]["ctrl_rash_atab_004_cm3"]["winner"] in ("levant_semitic", "kassite")
    assert rash_b["levant_semitic"] + 0.5 < rash_b["cypriot_greek"]
    assert kh["onomastics"]["cm1_clay_ball_seq1"]["winner"] == "amathus_ec"
    assert seq1_b["amathus_ec"] + 0.5 < seq1_b["levant_semitic"]
    assert kh["acrophony"]["delta_ll_init_minus_fin"] > 0.0
    assert kh["acrophony"]["p_vs_final_pool"] < 0.01


def test_check_cli_detects_stale_ledger(tmp_path: Path) -> None:
    manifest = cm_kernel_ih.build_manifest()
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"manifest": manifest}), encoding="utf-8")
    assert cm_kernel_ih.main(["check", "--ledger", str(good)]) == 0

    bad_m = json.loads(json.dumps(manifest))
    bad_m["inputs"]["cm_lexicon"]["sha256"] = "0" * 64
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"manifest": bad_m}), encoding="utf-8")
    assert cm_kernel_ih.main(["check", "--ledger", str(bad)]) == 1
