"""Unit tests for Kernel H (Structurally-Gated Roster Onomastics)."""
from __future__ import annotations

import c_render as r
import lid
import onomastics_h as oh


def test_structural_roster_extraction_returns_57_unique_names():
    names = oh.extract_structural_roster_names()
    assert len(names) == 57
    assert len(set(names)) == 57
    assert all(len(w) >= 3 for w in names)


def test_shipped_levant_and_kassite_onomastica_load_cleanly():
    tables, signs = r.load_tables(), lid.sign_keys()
    levant = oh.load_oracc_levant_names(tables, signs, max_n=200)
    kassite = oh.load_kassite_names(tables, signs, max_n=200)
    assert len(levant) == 200
    assert len(kassite) == 200
    assert all(len(w) >= 3 and lid.valid(w, signs) for w in levant)
    assert all(len(w) >= 3 and lid.valid(w, signs) for w in kassite)
