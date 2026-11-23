"""Unit tests for Kernel B (kober_b.py). Pure synthetic words; touches no corpus or Linear A data."""
from __future__ import annotations

import kober_b as kb


def _w(*sylls: str) -> tuple:
    out = []
    for s in sylls:
        if len(s) == 1:
            out.append(("", s.lower()))
        else:
            out.append((s[:-1].upper(), s[-1].lower()))
    return tuple(out)


def test_extracts_kober_trio_suffix_and_stem_vowel():
    words = [
        _w("SA", "RU"),
        _w("SA", "RO"),
        _w("SA", "RA"),
        _w("JA", "SA", "RA"),
        _w("JA", "SA", "RA", "ME"),
        _w("JA", "SA", "RA", "MA", "NA"),
    ]
    trs = kb.extract_transitions(words)
    assert len(trs) >= 4
    # SA-RU ~ SA-RO ~ SA-RA should yield stem-final boundary vowel alternations
    pols = {tr[0] for tr in trs}
    assert (False, True, False) in pols
    # JA-SA-RA ~ JA-SA-RA-ME should yield suffix-only alternation
    assert (False, False, True) in pols


def test_extracts_prefix_and_circumfix():
    words = [
        _w("TA", "KA", "NA"),
        _w("JA", "KA", "NA"),
        _w("A", "KA", "NA", "TI"),
    ]
    trs = kb.extract_transitions(words)
    pols = {tr[0] for tr in trs}
    assert (True, False, False) in pols
    assert (True, False, True) in pols


def test_clusters_find_trios():
    words = [
        _w("SA", "RU"),
        _w("SA", "RO"),
        _w("SA", "RA"),
        _w("PI", "TO"),
    ]
    clusters = kb.extract_clusters(words)
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_model_prefers_own_polarity_and_edges():
    alphabet = [(c, v) for c in ("", "K", "N", "T", "J", "M", "S", "R") for v in "aeiou"]
    prefix_lang = [
        _w("JA", "KA", "NA"), _w("TA", "KA", "NA"),
        _w("JA", "SA", "RA"), _w("TA", "SA", "RA"),
        _w("JA", "MA", "NA"), _w("TA", "MA", "NA"),
    ]
    suffix_lang = [
        _w("KA", "NA"), _w("KA", "NA", "TI"),
        _w("SA", "RA"), _w("SA", "RA", "TI"),
        _w("MA", "NA"), _w("MA", "NA", "TI"),
    ]
    m_pre = kb.KoberModel(kb.extract_transitions(prefix_lang), alphabet)
    m_suf = kb.KoberModel(kb.extract_transitions(suffix_lang), alphabet)

    test_pre = kb.extract_transitions([_w("JA", "RA", "NA"), _w("TA", "RA", "NA")])
    test_suf = kb.extract_transitions([_w("RA", "NA"), _w("RA", "NA", "TI")])

    assert kb.bits_per_transition([m_pre], test_pre) < kb.bits_per_transition([m_suf], test_pre)
    assert kb.bits_per_transition([m_suf], test_suf) < kb.bits_per_transition([m_pre], test_suf)
