"""Unit tests for Kernel L (homomorph_l.py): L1SO jackknife, corruption curve, and L4 negative controls."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import homomorph_l as hl  # noqa: E402


def test_filter_words_drop_series_removes_target_series():
    words = [(("K", "u"), ("R", "o")), (("Q", "a"), ("P", "a")), (("T", "a"), ("N", "a"))]
    kept = hl.filter_words_drop_series(words, {"Q", "Z"})
    assert len(kept) == 2
    assert all(k[0] not in {"Q", "Z"} for w in kept for k in w)


def test_l3_corruption_curve_robust_at_20pct_error():
    res = hl.run_l3_corruption_curve(eps_grid=(0.0, 0.2), n_trials=60, seed=42, include_morphology=False, sig_trials=20)
    la_20 = [r for r in res["linear_a_semitic"] if r["eps"] == 0.2][0]
    lb_20 = [r for r in res["linear_b_greek"] if r["eps"] == 0.2][0]
    assert lb_20["target_win_rate"] >= 0.90
    assert la_20["target_win_rate"] >= 0.90
    assert la_20["p_perm_le_005_rate"] >= 0.80


def test_sigla_loader_extracts_strict_lb_words():
    words = hl.load_sigla_strict_words()
    assert len(words) >= 600


def test_l4_single_sign_open_dict_ligatures_fail_linear_b_greek_gate():
    nc = hl.run_l4_negative_controls(n_perm=300, seed=42)
    sat = nc["single_sign_open_dict_ligature_saturation"]
    assert sat["linear_b_greek_p"] > 0.05
