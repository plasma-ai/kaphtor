"""CI guard tests for models/cypro-minoan-kernel/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
KERNEL_DIR = REPO / "models" / "cypro-minoan-kernel"
LEDGER_PATH = KERNEL_DIR / "runs" / "cm-kernel-2026-11-25.json"
LEDGER_IH_PATH = KERNEL_DIR / "runs" / "cm-kernel-ih-2026-11-25.json"

if str(KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(KERNEL_DIR))

import cm_kernel
import cm_kernel_ih


@pytest.mark.data
def test_cypro_minoan_kernel_ledger_matches_shipped_inputs() -> None:
    """Pinned run ledger must match SHA-256 hashes of all shipped kaphtor input files."""
    assert LEDGER_PATH.exists(), f"Missing pinned run ledger: {LEDGER_PATH}"
    assert cm_kernel.main(["check", "--ledger", str(LEDGER_PATH)]) == 0


@pytest.mark.data
def test_cypro_minoan_kernel_t3_firewall_and_counts() -> None:
    """Kernel manifest must never touch Linear A data and must match audited Amathus IG XV 1 counts."""
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert ledger["manifest"]["t5_compliant"] is True
    for info in ledger["manifest"]["inputs"].values():
        assert "linear-a" not in info["path"]
    assert ledger["corpora_counts"]["ec_amathus_confirmed_types"] == 92
    assert ledger["corpora_counts"]["ec_amathus_undotted_types"] == 66
    # Orthographic glide laws must hold strongly in shipped data (positive exact p-values)
    pan = ledger["kernel_cm_o_glides"]["pan_cm"]
    assert 0.0 < pan["ci_jv_enrichment_p_vs_non_i"] < 1e-6
    assert 0.0 < pan["cu_wv_enrichment_p_vs_non_u"] < 1e-4
    # Suffix containment must significantly beat position-preserving syllable-shuffled null
    assert ledger["kernel_cm_b_stems"]["p_suffix"] <= 0.01
    # Verify deterministic alphabetical tie-breaking in top_productive_suffixes
    items = list(ledger["kernel_cm_b_stems"]["top_productive_suffixes"].items())
    assert items == sorted(items, key=lambda kv: (-kv[1], kv[0]))


@pytest.mark.data
def test_cypro_minoan_kernel_ih_ledger_matches_shipped_inputs() -> None:
    """Pinned Track 6 CM-I/CM-H ledger must match all 13 shipped input SHA-256 pins."""
    assert LEDGER_IH_PATH.exists(), f"Missing pinned IH ledger: {LEDGER_IH_PATH}"
    assert cm_kernel_ih.main(["check", "--ledger", str(LEDGER_IH_PATH)]) == 0


@pytest.mark.data
def test_cypro_minoan_kernel_ih_calibration_and_t3_firewall() -> None:
    """CM-I and CM-H must preserve T3 isolation and pass in-script Greek and CM 3 controls."""
    ledger = json.loads(LEDGER_IH_PATH.read_text(encoding="utf-8"))
    assert ledger["manifest"]["t5_compliant"] is True
    for info in ledger["manifest"]["inputs"].values():
        assert "linear-a" not in info["path"]
        assert "language-id-kernel" not in info["path"]
    plene = ledger["kernel_cm_i"]["cypriot_plene"]
    omit = ledger["kernel_cm_i"]["omission"]
    # In-script Cypriot Syllabic Greek & Linear B calibration gates
    assert plene["kernel_cm_i1_rival_exclusion"]["calib_cypriot_greek_ig_xv_1"]["winner"] == "greek"
    assert plene["kernel_cm_i1_rival_exclusion"]["calib_damos_linear_b"]["winner"] == "greek"
    assert plene["kernel_cm_i1_rival_exclusion"]["calib_damos_linear_b"]["winner_p_margin"] <= 0.05
    assert omit["kernel_cm_i1_rival_exclusion"]["calib_damos_linear_b"]["winner"] == "greek"
    assert omit["kernel_cm_i1_rival_exclusion"]["calib_damos_linear_b"]["winner_p_margin"] <= 0.05
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["winner"] == "greek"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["winner_p_margin"] <= 0.01
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["amathus_ec_p_margin"] >= 0.90
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["winner"] == "greek"
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["calib_cypriot_greek_ig_xv_1"]["winner_p_margin"] <= 0.05
    # CM 1+2 beats all 7 vocalized ancient families under Amathus EC arm in all 4 mode x tier combinations
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm12_valerio_emended"]["winner"] == "amathus_ec"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm12_valerio_emended"]["winner_p_margin"] <= 0.01
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm12_davis_unsplit"]["winner_p_margin"] <= 0.01
    assert plene["kernel_cm_i2_amathus_undotted_8way"]["cm12_valerio_emended"]["winner_p_margin"] <= 0.05
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["cm12_valerio_emended"]["winner"] == "amathus_ec"
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["cm12_valerio_emended"]["winner_p_margin"] <= 0.01
    assert omit["kernel_cm_i2_amathus_undotted_8way"]["cm12_valerio_emended"]["winner_p_margin"] <= 0.05
    # Under true Cypriot plene spelling both CM 1 alone and CM 2 alone rank Amathus EC #1; in omission CM 2 EC margin stays significant
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm1_only_valerio"]["winner"] == "amathus_ec"
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm2_only_valerio"]["winner"] == "amathus_ec"
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["cm2_only_valerio"]["amathus_ec_p_margin"] <= 0.05
    # HoChyMin unsplit collapses to non-significance; CM 3 Ugarit negative control rejects Amathus EC
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm12_hochymin_unsplit"]["winner_p_margin"] > 0.05
    assert omit["kernel_cm_i2_amathus_confirmed_8way"]["cm12_hochymin_unsplit"]["winner_p_margin"] > 0.10
    assert plene["kernel_cm_i2_amathus_confirmed_8way"]["cm3_ugarit_control"]["winner"] != "amathus_ec"
    # Kernel H polarity reversal: RASH Atab 004 favors ANE; CM 1 clay balls favor Amathus EC
    kh = ledger["kernel_cm_h_clay_balls"]
    rash_b = kh["onomastics"]["ctrl_rash_atab_004_cm3"]["bits_per_sign"]
    seq1_b = kh["onomastics"]["cm1_clay_ball_seq1"]["bits_per_sign"]
    assert kh["onomastics"]["ctrl_rash_atab_004_cm3"]["winner"] in ("levant_semitic", "kassite")
    assert rash_b["levant_semitic"] + 0.5 < rash_b["cypriot_greek"]
    assert kh["onomastics"]["cm1_clay_ball_seq1"]["winner"] == "amathus_ec"
    assert seq1_b["amathus_ec"] + 0.5 < seq1_b["levant_semitic"]
    assert kh["acrophony"]["p_vs_final_pool"] <= 0.01
