"""Unit tests for Kernel C (liturgy_c.py). Pure synthetic data; touches no corpora or Linear A."""
from __future__ import annotations

import collections

import liturgy_c as lc


def _w(*sylls: str) -> tuple:
    return tuple(("", s.lower()) if len(s) == 1 else (s[:-1].upper(), s[-1].lower()) for s in sylls)


def test_dirichlet_log_odds_ranks_enriched_words_first():
    fg = collections.Counter({_w("SI", "RU"): 20, _w("KA", "NA"): 15, _w("MA", "NA"): 2})
    bg = collections.Counter({_w("SI", "RU"): 1, _w("KA", "NA"): 1, _w("MA", "NA"): 50})
    z = lc.dirichlet_log_odds(fg, bg)
    assert z[_w("SI", "RU")] > z[_w("KA", "NA")] > 0 > z[_w("MA", "NA")]


def test_perm_z_score_detects_matching_vocabulary():
    vocab = [
        _w("PI", "NA", "MA"),
        _w("SI", "RU", "TE"),
        _w("KA", "NA", "SI"),
        _w("SA", "RA", "ME"),
        _w("DI", "KI", "TU"),
    ]
    prayer = [
        _w("I", "PI", "NA", "MA"),
        _w("SI", "RU", "TE"),
        _w("U", "KA", "NA", "SI"),
        _w("JA", "SA", "RA", "ME"),
        _w("JA", "DI", "KI", "TU"),
    ]
    res = lc.perm_z_score(prayer, vocab, n_perm=200, seed=7)
    assert res["score"] > 0.5
    assert res["z_perm"] > 3.0
    assert res["p_perm"] <= 0.01
