"""Unit tests for models/cypro-minoan-kernel/cm_kernel.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

KERNEL_DIR = Path(__file__).resolve().parents[1]
if str(KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(KERNEL_DIR))

import cm_kernel


def test_parse_ig_amathus_exact_audited_counts() -> None:
    """Amathus IG XV 1 parser must match the audited 92 confirmed / 66 undotted word-type counts."""
    conf = cm_kernel.parse_ig_amathus(exclude_dotted=False)
    undot = cm_kernel.parse_ig_amathus(exclude_dotted=True)
    assert len(conf) == 92
    assert len(undot) == 66
    assert set(undot).issubset(set(conf))
    # Verify line-wrap-joined & glued-<lb/> tokens are recovered cleanly
    conf_strs = {"-".join(w) for w in conf}
    assert "a-pi-ma" in conf_strs
    assert "tu-ka-i-mi-no-na" in conf_strs
    assert "ka-i-li-po-ti" in conf_strs
    assert "o-ra-ko-ti" in conf_strs
    # Tentative IG XV 1, 12 and direction-doubtful IG XV 1, 8/9/13 must be excluded
    assert "pi-la-i-ni" not in conf_strs
    assert "ta-ra-na" not in conf_strs
    assert "u-tu-mu-ta" not in conf_strs


def test_load_cm_word_types_excludes_synthetic_stems_and_splits_regimes() -> None:
    val = cm_kernel.load_cm_word_types(regime="valerio")
    dav = cm_kernel.load_cm_word_types(regime="davis")
    hoc = cm_kernel.load_cm_word_types(regime="hochymin")
    assert len(val["CM 1+2"]) >= 250
    assert len(val["CM 3"]) >= 40
    # Regimes must actually produce distinct word sets on 013/008
    assert set(val["CM 1+2"]) != set(dav["CM 1+2"])
    assert set(val["CM 1+2"]) != set(hoc["CM 1+2"])


def test_kernel_o_glides_and_bare_vowel_laws() -> None:
    res = cm_kernel.run_kernel_o_glides()
    pan = res["pan_cm"]
    assert pan["ci_jv_enrichment_p_vs_non_i"] < 1e-6
    assert pan["cu_wv_enrichment_p_vs_non_u"] < 1e-4
    assert pan["bare_vowel_final_rate"] < 0.05
    assert pan["cv_final_rate"] > 0.30


def test_kernel_b_stem_productivity_suffix_over_prefix() -> None:
    cm_val = cm_kernel.load_cm_word_types(regime="valerio")
    res = cm_kernel.run_kernel_b_stem_productivity(cm_val["CM 1+2"], n_perm=200, seed=20261125)
    assert res["null_model"] == "position_preserving_init_med_fin_shuffle"
    assert res["suffix_extension_pairs"] > res["prefix_extension_pairs"]
    assert res["p_suffix"] < 0.05
    # Verify deterministic alphabetical tie-breaking independent of PYTHONHASHSEED
    items = list(res["top_productive_suffixes"].items())
    assert items == sorted(items, key=lambda kv: (-kv[1], kv[0]))


def test_run_suite_deterministic_and_t3_isolated() -> None:
    r1 = cm_kernel.run_suite(n_perm=100, lb_draws=5, seed=20261125)
    r2 = cm_kernel.run_suite(n_perm=100, lb_draws=5, seed=20261125)
    assert r1 == r2
    # Strict T3 firewall: zero Linear A lexicon/translations/sign_values inputs
    for info in r1["manifest"]["inputs"].values():
        assert "data/linear-a/" not in info["path"]


def test_check_cli_detects_stale_and_valid_ledger(tmp_path: Path) -> None:
    manifest = cm_kernel.build_manifest()
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"manifest": manifest}), encoding="utf-8")
    assert cm_kernel.main(["check", "--ledger", str(good)]) == 0

    bad_manifest = json.loads(json.dumps(manifest))
    bad_manifest["inputs"]["cm_lexicon"]["sha256"] = "0" * 64
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"manifest": bad_manifest}), encoding="utf-8")
    assert cm_kernel.main(["check", "--ledger", str(bad)]) == 1
