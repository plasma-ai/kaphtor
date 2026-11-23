"""Unit tests for Shoresh Amendment A24 (tools/core/shoresh_cv.py)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.core import shoresh_cv as scv


def test_cv_from_syllables_and_distance():
    kuro = scv.cv_from_syllables("KU-RO")
    kuru = scv.cv_from_syllables("KU-RU")
    pati = scv.cv_from_syllables("PA-TI")
    assert kuro == (("K", "u"), ("R", "o"))
    assert scv.cv_distance(kuro, kuro) == 0.0
    assert 0.0 < scv.cv_distance(kuro, kuru) < scv.cv_distance(kuro, pati)


def test_bayesian_marginal_ll_penalizes_dictionary_padding():
    q = scv.cv_from_syllables("KU-RO")
    hit = scv.cv_from_syllables("KU-RU")
    noise = [scv.cv_from_syllables("PA-TI"), scv.cv_from_syllables("MA-NA"), scv.cv_from_syllables("DE-SO")]
    ll_tight, d1 = scv.bayesian_marginal_ll(q, [hit])
    ll_padded, d2 = scv.bayesian_marginal_ll(q, [hit, *noise])
    assert d1 == d2
    assert ll_tight > ll_padded  # padding with non-matching synonyms strictly reduces marginal LL


def test_rescues_two_consonant_anchors_over_grid_permutation():
    # KU-RO (total) + KI-RO (deficit) + SU-PU (bowl) — all 2-consonant words previously UNINFORMATIVE under §3
    items = [
        (
            scv.cv_from_syllables("KU-RO"),
            {
                "semitic": [scv.cv_from_syllables("KU-RU"), scv.cv_from_syllables("KA-MA-RU")],
                "greek": [scv.cv_from_syllables("TO-SO"), scv.cv_from_syllables("O-RO")],
                "anatolian": [scv.cv_from_syllables("TA-NI-MA"), scv.cv_from_syllables("PU-NA-TA")],
                "hurrian": [scv.cv_from_syllables("SU-A"), scv.cv_from_syllables("TU-PI")],
            },
        ),
        (
            scv.cv_from_syllables("KI-RO"),
            {
                "semitic": [scv.cv_from_syllables("KI-RU"), scv.cv_from_syllables("MA-TU")],
                "greek": [scv.cv_from_syllables("O-PE-RO"), scv.cv_from_syllables("RO-I-PO")],
                "anatolian": [scv.cv_from_syllables("KA-RU"), scv.cv_from_syllables("I-PA")],
                "hurrian": [scv.cv_from_syllables("NI-RI"), scv.cv_from_syllables("A-RI")],
            },
        ),
        (
            scv.cv_from_syllables("SU-PU"),
            {
                "semitic": [scv.cv_from_syllables("SU-PU"), scv.cv_from_syllables("KA-DU")],
                "greek": [scv.cv_from_syllables("DI-PA"), scv.cv_from_syllables("TI-RI-PO")],
                "anatolian": [scv.cv_from_syllables("PA-RI"), scv.cv_from_syllables("KU-KU-PI")],
                "hurrian": [scv.cv_from_syllables("KA-ZI"), scv.cv_from_syllables("TU-RI")],
            },
        ),
    ]
    res = scv.score_vocalic_set(items, n_perm=500, seed=20261122)
    assert res["winner"] == "semitic"
    assert res["semitic_delta_ll"] > 3.0
    assert res["languages"]["semitic"]["p_perm"] <= 0.01


def test_shoresh_cv_isolated_stdlib_import():
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); import tools.core.shoresh_cv as m; assert m.cv_distance(m.cv_from_syllables('KU-RO'), m.cv_from_syllables('KU-RO')) == 0.0"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
