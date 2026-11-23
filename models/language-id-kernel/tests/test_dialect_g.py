"""Unit tests for Kernel G (Palaikastro Dialect Sound-Law Coherence)."""
from __future__ import annotations

import dialect_g as dg


def test_palaikastro_isogloss_bundle_matches_all_five_pairs():
    res = dg.run_dialect_test(n_perm=1000, seed=42)
    assert res["n_pairs"] == 5
    assert res["obs_hits"] == 5
    assert res["p_perm"] <= 0.005
