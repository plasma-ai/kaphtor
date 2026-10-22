"""Shared data cache for Ventris Engine modules.

Loads corpus.json, lexicon.json, sign_values.json, morphemes.json, and
root databases once and caches them for reuse across pipeline phases.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from ..paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, require
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, require

_cache: dict[str, object] = {}


def data_path(name: str) -> Path:
    """Where `name`.json lives: the Semitic roots in data/semitic-roots/, everything else in data/linear-a/."""
    return (SEMITIC_ROOTS_DATA if name == "semitic_roots" else LINEAR_A_DATA) / f"{name}.json"


def _load(name: str) -> dict | list:
    if name not in _cache:
        path = require(data_path(name), f"{name}.json")
        _cache[name] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[name]


def corpus() -> dict:
    return _load("corpus")


def lexicon() -> dict:
    return _load("lexicon")


def sign_values() -> dict:
    return _load("sign_values")


def sign_value_entries(summary: dict, kind: str) -> list[str]:
    """Every "SIGN=VALUE" entry of one kind ("phonemic", "logograms", "fractions") in a sign_values
    resolution_summary: the resolved entries, then the proposed ones (objects whose `entry` holds the string)."""
    proposed = summary.get("proposed", {}).get(kind, [])
    return list(summary.get(kind, [])) + [p["entry"] for p in proposed]


def morphemes() -> dict:
    return _load("morphemes")


def semitic_roots() -> list:
    """The roots as records (Number, Proto-Semitic, Meaning, Analogues, Notes); see semitic_root_schema.roots_records."""
    try:
        from .semitic_root_schema import roots_records
    except ImportError:
        from tools.core.semitic_root_schema import roots_records
    return roots_records(_load("semitic_roots"))


def egyptian_roots() -> list:
    return _load("egyptian_roots")


def luwian_roots() -> list:
    return _load("luwian_roots")


def hurrian_roots() -> list:
    return _load("hurrian_roots")


def clear():
    _cache.clear()
