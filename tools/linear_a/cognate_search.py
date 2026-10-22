#!/usr/bin/env python3
"""Search for Semitic cognates of a Linear A transliteration.

Pipeline: transliteration → consonantal skeleton → Gordon direct match →
YasharMana match → Proto-Semitic distance search.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.greek_spelling import lb_token_to_key
from ..core.normalization import lookup_in
from ..core.phonetics import (
    EGYPTIAN_DISTANCES,
    GUTTURAL_PHONEMES,
    LUWIAN_DISTANCES,
    SEMITIC_DISTANCES,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from ..core.semitic_root_schema import roots_records
from ..core.skeleton import extract_full, extract_skeleton, extract_skeleton_polyphonic
from ..core.verb_morphology import VerbParse, verbal_parses
from ..paths import ANE_DATA, CACHE, CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout

# A local lashon-ha-kretan checkout, the source of the Gordon lexicon when gordon.json is not here.
LASHON_DIR = Path(os.environ["LASHON_HA_KRETAN_DIR"]) if os.environ.get("LASHON_HA_KRETAN_DIR") else None
DATA_DIR = LINEAR_A_DATA
CACHE_FILE = CACHE / "linear-a" / "cognate_cache.json"

# Geminate-orthography rule: stops only until the null-model audit clears
# sibilants (JA-SA-SA-RA-ME, CONFIRMED with doubled SA, shows the risk).
GEMINABLE_STOPS = {"t", "d", "k", "q", "p", "b"}

# Sonorant-metathesis rules for --historical-lens (Semitic searches only,
# never Luwian/Egyptian/Greek). A registered pair must rest on documented
# evidence — an attested alternation (both members on stone, e.g. qml~qlm)
# or a published derivation proposal carried with its provenance (e.g. brṯ,
# whose intermediates are reconstructed) — merely conceivable transpositions
# are inadmissible, which is why weighted_levenshtein has no transposition op.
# Every penalty sits at ≥ 0.35, above the CANDIDATE gate (d < 0.3), so a lens
# match can never promote on lexical resemblance alone.
# Each rule lists the adjacent phoneme pairs it fires on (either order, one
# swap per variant). The ṯr rule also fires on surface (t, r) — an ENGINE
# inference from the T-series' underdifferentiation of /t ṭ ṯ/, not a claim
# in Rendsburg — with the t~ṯ substitution cost pricing that extra
# uncertainty when the swapped skeleton meets a ṯ-bearing lexicon form.
HISTORICAL_METATHESIS_RULES = [
    {"pairs": [("ṯ", "r"), ("t", "r")], "rule": "metathesis_tr_rt", "penalty": 0.35,
     "source": "Rendsburg 2022:322–327, 332–333 (proposed: brṯ < b-ʾaṯr; ʾrṯt < *ʾaṯirt-)"},
    {"pairs": [("m", "l")], "rule": "metathesis_ml_lm", "penalty": 0.35,
     "source": "Rendsburg 2022:324 n.35 (attested doublet qml~qlm; Aramaic Sefire I A 31)"},
    {"pairs": [("w", "l")], "rule": "metathesis_wl_lw", "penalty": 0.40,
     "source": "Rendsburg 2022:324 n.36 (attested doublet ʾwld~ʾlwd; Radman per Stein, cf. Ricks 51)",
     "dialect": "Radman"},
]

# Linear A writes no final consonant, so a name key's case-ending -m (TABIN-UM →
# tbnm) is also scored without it, at the final_n_loss_restoration price.
MIMATION_PENALTY = 0.20
_MIMATION_NAME = re.compile(r"-[AIU]M$")

# Akkadian has no ḫ sign in Linear A: ḫ is written with the K series (ref-semitic-to-
# minoan-spelling.md §3, Akkadian rule 5). Scoped to the opt-in Akkadian path; the
# correspondence control finds K for ḫ lifts no more than a sham rewrite elsewhere.
AKKADIAN_DISTANCES = {**SEMITIC_DISTANCES, ("k", "ḫ"): 0.15}

# Harding 1971, System of Transliteration (p. 6): th = ṯ, dh = ḏ, kh = ḫ, sh = š.
# sh already reads as š in phonetics; the other three would read as two letters.
_HARDING_DIGRAPHS = (("th", "ṯ"), ("dh", "ḏ"), ("kh", "ḫ"))


def _lashon_lexicon(section: str) -> dict[str, dict[str, Any]]:
    """One section of lashon-ha-kretan's semiticLexicon.js, the source gordon.json is extracted from."""
    if LASHON_DIR is None or not (LASHON_DIR / "semiticLexicon.js").exists():
        raise NotInCheckout(f"gordon.json is not in this checkout (looked for {DATA_DIR / 'gordon.json'}; or set "
                            "LASHON_HA_KRETAN_DIR to a lashon-ha-kretan checkout)")
    from ..core.js_parser import parse_lexicon
    return parse_lexicon(LASHON_DIR / "semiticLexicon.js", section)


def load_gordon() -> dict[str, dict[str, Any]]:
    """Load Gordon lexicon from extracted JSON or source JS."""
    cached = DATA_DIR / "gordon.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return data.get("gordon", data)
    return _lashon_lexicon("gordon")


def load_yashar_mana() -> dict[str, dict[str, Any]]:
    """Load YasharMana lexicon."""
    cached = DATA_DIR / "gordon.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return data.get("yasharMana", {})
    return _lashon_lexicon("yasharMana")


def load_scholarly() -> dict[str, dict[str, Any]]:
    """Load scholarly lexicon (post-Gordon readings from other scholars)."""
    cached = DATA_DIR / "gordon.json"
    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        return data.get("scholarly", {})
    return _lashon_lexicon("scholarly")


def load_compound_morphemes() -> list[dict[str, Any]]:
    """Load compound word morpheme registry."""
    path = DATA_DIR / "compound_morphemes.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("compounds", [])
    return []


def load_semitic_roots() -> list[dict[str, Any]]:
    """Load Proto-Semitic roots, as the records the matcher keys on (semitic_root_schema.roots_records)."""
    cached = SEMITIC_ROOTS_DATA / "semitic_roots.json"
    if cached.exists():
        return roots_records(json.loads(cached.read_text(encoding="utf-8")))

    src = LASHON_DIR / "etymology" / "Semitic.json" if LASHON_DIR else None
    if src and src.exists():
        return json.loads(src.read_text(encoding="utf-8"))
    return []


def load_luwian_roots() -> list[dict[str, Any]]:
    """Load Luwian root database."""
    path = DATA_DIR / "luwian_roots.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def load_egyptian_roots() -> list[dict[str, Any]]:
    """Load Egyptian root database."""
    path = DATA_DIR / "egyptian_roots.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def load_ugaritic_roots() -> list[dict[str, Any]]:
    """Load Ugaritic contact lexicon JSONL."""
    path = CONTACT_DATA /"ugaritic_lexicon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_amorite_roots() -> list[dict[str, Any]]:
    """Load Amorite contact lexicon JSONL (Gelb AS 21 + Howard 2023)."""
    path = CONTACT_DATA /"amorite_onomasticon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_arabian_names() -> list[dict[str, Any]]:
    """Load the Pre-Islamic Arabian onomasticon (Harding 1971).

    Read from the ANE data (data/ane/arabian_onomasticon.jsonl); empty when it is not in the checkout.
    """
    path = ANE_DATA / "arabian_onomasticon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


_GREEK_ROOTS_CACHE: tuple[float, list[dict[str, Any]]] | None = None


def load_greek_roots() -> list[dict[str, Any]]:
    """Load Ancient Greek contact lexicon JSONL (LSJ 9th ed., Logeion TEI).

    Cached against the file's mtime so a re-ingest is picked up without a
    process restart.
    """
    global _GREEK_ROOTS_CACHE
    path = CONTACT_DATA /"greek_lexicon.jsonl"
    if not path.exists():
        return []
    mtime = path.stat().st_mtime
    if _GREEK_ROOTS_CACHE is not None and _GREEK_ROOTS_CACHE[0] == mtime:
        return _GREEK_ROOTS_CACHE[1]
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    _GREEK_ROOTS_CACHE = (mtime, entries)
    return entries


def load_hebrew_roots() -> list[dict[str, Any]]:
    """Load Hebrew contact lexicon JSONL (STEPBible TBESH + Open Scriptures BDB)."""
    path = CONTACT_DATA /"hebrew_lexicon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_aramaic_roots() -> list[dict[str, Any]]:
    """Load Aramaic contact lexicon JSONL (Aramaic Root Atlas)."""
    path = CONTACT_DATA /"aramaic_lexicon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_geez_roots() -> list[dict[str, Any]]:
    """Load Geʿez contact lexicon JSONL (Dillmann 1865 TEI + Leslau CDG 1987)."""
    path = CONTACT_DATA /"geez_lexicon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_south_arabian_roots() -> list[dict[str, Any]]:
    """Load South Arabian contact lexicon JSONL (DASI forms, Beeston/Biella
    glosses via enrich_sa_glosses.py)."""
    path = CONTACT_DATA /"south_arabian_lexicon.jsonl"
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _search_greek_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against the LSJ Greek lexicon.

    No guttural transparency — that accommodation is Semitic-specific;
    Greek forms compete on plain weighted distance.
    """
    entries = load_greek_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        # Score against the precomputed LB spelling (khrusos → kuruso) and
        # the plain transliteration; keep whichever is closer.
        forms = [f for f in (entry.get("lb_key"), entry.get("normalized"))
                 if f and 2 <= len(_tokenize_phonemes(f)) <= 10]
        if not forms:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=False), f)
            for f in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Ancient Greek",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "greek_distance",
                "source": entry["source_refs"][0].get("source", "") if entry.get("source_refs") else "",
            }
            if entry.get("lb_key"):
                result["lb_spelling"] = entry["lb_key"]
            if entry.get("pos"):
                result["pos"] = entry["pos"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_amorite_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against the Amorite onomasticon (guttural-transparent, NWS).

    Scores match_keys (element normalizations included for catalog names),
    keeping the best key per entry; skips whole-name keys longer than 8
    tokens so multi-element names match via their elements, not their
    concatenations.
    """
    entries = load_amorite_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [(f, 0.0) for f in entry.get("match_keys", []) if 2 <= len(_tokenize_phonemes(f)) <= 8]
        if _MIMATION_NAME.search(entry.get("form_original", "")):
            forms += [(f[:-1], MIMATION_PENALTY) for f, _ in forms
                      if f.endswith("m") and len(_tokenize_phonemes(f)) >= 3]
        if not forms:
            continue
        dist, form, penalty = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True) + p, f, p)
            for f, p in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Amorite",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "amorite_distance",
                "source": entry["source_refs"][0].get("source", "") if entry.get("source_refs") else "",
            }
            if penalty:
                result["mimation_stripped"] = True
            if entry["source_refs"][0].get("page"):
                result["gelb_no"] = entry["source_refs"][0]["page"]
            if entry.get("pos"):
                result["pos"] = entry["pos"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _harding_key(key: str) -> str:
    """Read Harding's th/dh/kh digraphs as the single consonants they stand for."""
    for digraph, consonant in _HARDING_DIGRAPHS:
        key = key.replace(digraph, consonant)
    return key


def _search_arabian_names(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search the Pre-Islamic Arabian onomasticon (Harding 1971) —
    same scoring as the Amorite onomasticon: match_keys distance with
    guttural transparency, whole-name keys capped at 8 tokens."""
    entries = load_arabian_names()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [_harding_key(f) for f in entry.get("match_keys", [])]
        forms = [f for f in forms if 2 <= len(_tokenize_phonemes(f)) <= 8]
        if not forms:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f)
            for f in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            counts = entry.get("dialect_counts") or {}
            dialects = "".join(d for d in ("L", "S", "T", "H", "M", "Q", "Sa")
                               if counts.get(d))
            result: dict[str, Any] = {
                "root": entry.get("normalized", form),
                "language": f"Pre-Islamic Arabian ({dialects})" if dialects
                            else "Pre-Islamic Arabian",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "arabian_distance",
                "source": "Harding 1971, p. "
                          + str(entry["source_refs"][0].get("page", "?"))
                          if entry.get("source_refs") else "Harding 1971",
            }
            if entry.get("theophoric"):
                result["theophoric"] = entry["theophoric"]
            if entry.get("root_xref"):
                result["root_xref"] = entry["root_xref"]
            if entry.get("doubtful"):
                result["doubtful"] = True
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_arabian_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Arabian search across skeleton variants with penalties (cf. Amorite)."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_arabian_names(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def _search_amorite_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Amorite search across skeleton variants with penalties (cf. Ugaritic)."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_amorite_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def _search_hebrew_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against Hebrew contact lexicon (guttural-transparent, NWS)."""
    entries = load_hebrew_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [
            f.replace("√", "").strip()
            for f in (entry.get("match_keys") or [entry.get("normalized", "")])
        ]
        forms = [f for f in forms if len(f) >= 2]
        if not forms:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f)
            for f in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Hebrew",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "hebrew_distance",
            }
            if entry.get("root"):
                result["semitic_root"] = entry["root"]
            if entry.get("pos"):
                result["pos"] = entry["pos"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_hebrew_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Hebrew search across skeleton variants with penalties."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_hebrew_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def _search_aramaic_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against Aramaic contact lexicon (guttural-transparent, NWS)."""
    entries = load_aramaic_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [
            f.replace("√", "").strip()
            for f in (entry.get("match_keys") or [entry.get("normalized", "")])
        ]
        forms = [f for f in forms if len(f) >= 2]
        if not forms:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f)
            for f in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Aramaic",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "aramaic_distance",
            }
            if entry.get("root"):
                result["semitic_root"] = entry["root"]
            if entry.get("pos"):
                result["pos"] = entry["pos"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_aramaic_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Aramaic search across skeleton variants with penalties."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_aramaic_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def _search_geez_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against Geʿez contact lexicon (guttural-transparent, South Semitic)."""
    entries = load_geez_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [
            f.replace("√", "").strip()
            for f in (entry.get("match_keys") or [entry.get("normalized", "")])
        ]
        forms = [f for f in forms if len(f) >= 2]
        if not forms:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f)
            for f in forms
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Geʿez",
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "geez_distance",
            }
            if entry.get("root"):
                result["semitic_root"] = entry["root"]
            if entry.get("pos"):
                result["pos"] = entry["pos"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_geez_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Geʿez search across skeleton variants with penalties."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_geez_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


# ASA sibilant indices → Proto-Semitic values for distance matching
# (s¹ = PS *š, s² = PS *ś, s³ = PS *s; see lib/contact_lexicon.normalize_south_arabian)
_SA_SIBILANTS = {"s1": "š", "s2": "ś", "s3": "s"}


def _search_south_arabian_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against the South Arabian contact lexicon (guttural-transparent,
    South Semitic). Glossed rows carry Beeston/Biella meanings + citations."""
    entries = load_south_arabian_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        forms = [entry.get("normalized", "")] + list(entry.get("match_keys") or [])
        expanded = set()
        for f in forms:
            if len(f) < 2:
                continue
            for idx, ps in _SA_SIBILANTS.items():
                f = f.replace(idx, ps)
            expanded.add(f)
        if not expanded:
            continue
        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f)
            for f in expanded
        )
        form_len = len(_tokenize_phonemes(form))
        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "South Arabian"
                            + (f" ({entry['language_variety']})" if entry.get("language_variety") else ""),
                "meaning": entry.get("meaning", ""),
                "distance": round(dist, 3),
                "method": "south_arabian_distance",
            }
            if entry.get("review_status") == "gloss_enriched":
                result["gloss_source"] = "; ".join(sorted({
                    r.get("source", "") for r in entry.get("source_refs", [])
                    if r.get("source", "").startswith(("Beeston", "Biella"))}))
            scored.append((dist, result))

    # glossed rows outrank unglossed ties — the Beeston/Biella citation is the payload
    scored.sort(key=lambda x: (x[0], 0 if x[1].get("meaning") else 1))
    return [s[1] for s in scored[:top_n]]


def _search_south_arabian_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """South Arabian search across skeleton variants with penalties."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_south_arabian_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0] or (
                    effective == prev[0] and match.get("meaning") and not prev[1].get("meaning")):
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def load_akkadian_roots() -> list[dict[str, Any]]:
    """Load the Akkadian contact files: the Anchor Bible lexicon and the CAD headwords.

    Single words only: phrases, ghost words and hypothetical headwords are left out.
    """
    rows: list[dict[str, Any]] = []
    for name, field in (("akkadian_lexicon.jsonl", "form"), ("cad_headwords.jsonl", "headword")):
        path = CONTACT_DATA /name
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                form = (entry.get(field) or "").strip()
                if not form or " " in form or entry.get("ghost") or entry.get("hypothetical") or entry.get("phrase"):
                    continue
                rows.append({"id": entry["id"], "form": form,
                             "meaning": entry.get("meaning") or entry.get("gloss") or "",
                             "source_refs": entry.get("source_refs") or []})
    return rows


_AKKADIAN_VOWELS = set("aeiouāēīūâêîû")


def _akkadian_consonants(form: str) -> str:
    """Consonants of a normalized Akkadian form: da'āmu → dʾm, qaqqaru(m) → qqr (the bracketed mimation dropped)."""
    s = unicodedata.normalize("NFC", form.lower()).replace("(m)", "").replace("'", "ʾ").replace("’", "ʾ")
    s = re.sub(r"[\d₀-₉]", "", s)
    return "".join(ch for ch in s if ch not in _AKKADIAN_VOWELS and (ch.isalpha() or ch == "ʾ"))


def _search_akkadian_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search the Akkadian contact files (guttural-transparent, K for ḫ, case-ending -m scored both ways)."""
    entries = load_akkadian_roots()
    if not entries:
        return []

    skel_len = len(_tokenize_phonemes(skeleton))
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        key = _akkadian_consonants(entry["form"])
        forms = [(key, 0.0)]
        if re.search(r"[aiu]m$", entry["form"].lower()) and len(_tokenize_phonemes(key)) >= 3:
            forms.append((key[:-1], MIMATION_PENALTY))
        forms = [(f, p) for f, p in forms if 2 <= len(_tokenize_phonemes(f)) <= 8]
        if not forms:
            continue
        dist, form, penalty = min(
            (weighted_levenshtein(skeleton, f, distances=AKKADIAN_DISTANCES, guttural_transparent=True) + p, f, p)
            for f, p in forms
        )
        if dist <= max_dist * max(skel_len, len(_tokenize_phonemes(form)), 1):
            ref = entry["source_refs"][0] if entry["source_refs"] else {}
            result: dict[str, Any] = {
                "root": entry["form"],
                "language": "Akkadian",
                "meaning": entry["meaning"],
                "distance": round(dist, 3),
                "method": "akkadian_distance",
                "source": " ".join(str(ref[k]) for k in ("source", "work", "page", "ref") if ref.get(k)),
            }
            if penalty:
                result["mimation_stripped"] = True
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_akkadian_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Akkadian search across skeleton variants with penalties (cf. Amorite)."""
    best_per_root: dict[str, tuple[float, dict]] = {}
    for skel, penalty, rule in skeleton_candidates:
        for match in _search_akkadian_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)
    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def _search_luwian_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against Luwian root database using LUWIAN_DISTANCES."""
    roots = load_luwian_roots()
    if not roots:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in roots:
        root_str = entry.get("Consonantal_Root", "")
        if not root_str or len(root_str) < 2:
            continue

        root_tokens = _tokenize_phonemes(root_str)
        root_len = len(root_tokens)

        dist = weighted_levenshtein(skeleton, root_str, distances=LUWIAN_DISTANCES)

        if dist <= max_dist * max(skel_len, root_len, 1):
            scored.append((dist, {
                "root": root_str,
                "lemma": entry.get("Proto-Luwian", ""),
                "language": "Luwian",
                "meaning": entry.get("Meaning", ""),
                "distance": round(dist, 2),
                "method": "luwian_distance",
            }))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_egyptian_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against Egyptian root database using EGYPTIAN_DISTANCES + guttural transparency."""
    roots = load_egyptian_roots()
    if not roots:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in roots:
        root_str = entry.get("Consonantal_Root", "")
        if not root_str or len(root_str) < 2:
            continue

        root_tokens = _tokenize_phonemes(root_str)
        visible_root_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)

        dist = weighted_levenshtein(
            skeleton, root_str,
            distances=EGYPTIAN_DISTANCES,
            guttural_transparent=True,
        )

        if dist <= max_dist * max(skel_len, visible_root_len, 1):
            scored.append((dist, {
                "root": root_str,
                "lemma": entry.get("Middle_Egyptian", ""),
                "language": "Egyptian",
                "meaning": entry.get("Meaning", ""),
                "distance": round(dist, 2),
                "method": "egyptian_distance",
            }))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


_UGARITIC_ALEPHS = str.maketrans({"a": "ʾ", "i": "ʾ", "u": "ʾ", "?": "ʾ"})


def _ugaritic_plain(s: str) -> str:
    return re.sub(r"[√\s/:()\-]", "", s).replace("ʔ", "ʾ").replace("ʕ", "ʿ")


def _ugaritic_key(key: str, form_original: str = "") -> str:
    """Strip the root marker; in an alphabetic key, read the aleph letters (a i u) and ? as ʾ.

    The alphabet writes no vowels: ib is ʾib, and √?bd an aleph of unknown vowel. A key is alphabetic when it is the
    entry's own form; vocalized keys added beside it (kptr → kaptaru) keep their vowels.
    """
    key = key.replace("√", "").strip()
    if _ugaritic_plain(key) == _ugaritic_plain(form_original):
        key = key.translate(_UGARITIC_ALEPHS)
    return key


def _search_ugaritic_roots(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Search against the Ugaritic contact lexicon (guttural-transparent, NWS)."""
    entries = load_ugaritic_roots()
    if not entries:
        return []

    skel_tokens = _tokenize_phonemes(skeleton)
    skel_len = len(skel_tokens)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in entries:
        # Score against match_keys (e.g. ["√ntk", "ntk"]), stripping the root
        # marker — scoring the raw normalized form makes every √-prefixed
        # verbal root pay a full edit unit for the glyph.
        forms = [
            _ugaritic_key(f, entry.get("form_original", ""))
            for f in (entry.get("match_keys") or [entry.get("normalized", "")])
        ]
        forms = [f for f in forms if len(f) >= 2]
        if not forms:
            continue

        dist, form = min(
            (weighted_levenshtein(skeleton, f, guttural_transparent=True), f) for f in forms
        )

        form_tokens = _tokenize_phonemes(form)
        form_len = len(form_tokens)

        if dist <= max_dist * max(skel_len, form_len, 1):
            result: dict[str, Any] = {
                "root": entry.get("form_original", form),
                "language": "Ugaritic",
                "meaning": entry.get("meaning", ""),
                # 3 decimals, matching the PS path — the multi-variant merger
                # adds penalties on top of this value, so pre-rounding to 2
                # decimals would leak into effective-distance ranking.
                "distance": round(dist, 3),
                "method": "ugaritic_distance",
            }
            if entry.get("cuc_freq"):
                result["cuc_freq"] = entry["cuc_freq"]
            if entry.get("vocalization"):
                result["vocalization"] = entry["vocalization"]
            scored.append((dist, result))

    scored.sort(key=lambda x: x[0])
    return [s[1] for s in scored[:top_n]]


def _search_ugaritic_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Ugaritic contact search across skeleton variants with penalties.

    Mirrors _search_proto_semitic_multi: for each form the best-scoring
    variant wins; surface beats a restored variant at equal distance because
    it is compared first with a strict less-than.
    """
    best_per_root: dict[str, tuple[float, dict]] = {}

    for skel, penalty, rule in skeleton_candidates:
        for match in _search_ugaritic_roots(skel, top_n * 3):
            effective = match["distance"] + penalty
            key = match["root"]
            prev = best_per_root.get(key)
            if prev is None or effective < prev[0]:
                result = dict(match)
                result["distance"] = round(effective, 3)
                if rule != "surface":
                    result["morphophonological_rule"] = rule
                    result["skeleton_used"] = skel
                    result["base_distance"] = round(match["distance"], 3)
                best_per_root[key] = (effective, result)

    ranked = sorted(best_per_root.values(), key=lambda x: x[0])
    return [r for _, r in ranked[:top_n]]


def search_cognates(
    transliteration: str,
    top_n: int = 5,
    use_cache: bool = True,
    include_luwian: bool = False,
    include_egyptian: bool = False,
    include_ugaritic: bool = False,
    include_amorite: bool = False,
    include_greek: bool = False,
    include_hebrew: bool = False,
    include_aramaic: bool = False,
    include_geez: bool = False,
    include_south_arabian: bool = False,
    include_arabian: bool = False,
    verb_lens: bool = False,
    historical_lens: bool = False,
    include_akkadian: bool = False,
) -> dict[str, Any]:
    """Full cognate search pipeline for a transliteration.

    verb_lens adds a VERBAL PARSES section (template-licensed affix strips
    searched for hidden roots), computed independently of the bare-stem
    pipeline — enabling it never changes results["matches"], cached or live.
    build_cache never passes verb_lens, so lens variants can never poison
    the persistent cache.

    historical_lens extends the Semitic searches (Proto-Semitic, Ugaritic,
    Amorite, Arabian, Hebrew, Aramaic, Geʿez, South Arabian, Akkadian — never Luwian,
    Egyptian, or Greek) with HISTORICAL_METATHESIS_RULES skeleton variants.
    Report-only: every rule penalty ≥ 0.35 keeps lens matches above the
    CANDIDATE distance gate. Bypasses the Proto-Semitic cache (cached rows
    are surface-only) and is likewise excluded from build_cache.
    """
    skeleton = extract_skeleton(transliteration)
    full_cv = extract_full(transliteration)
    results: dict[str, Any] = {
        "transliteration": transliteration,
        "skeleton": skeleton,
        "cv_decomposition": [(c or "", v) for c, v in full_cv],
        "matches": [],
    }

    # Step 1: Gordon direct match
    gordon = load_gordon()
    match = lookup_in(gordon, transliteration)
    if match:
        results["matches"].append({
            "root": match.get("semitic", ""),
            "language": "Semitic (Gordon)",
            "meaning": match.get("meaning", ""),
            "distance": 0.0,
            "method": "gordon_direct",
            "source": match.get("source", ""),
        })

    # Step 2: YasharMana match
    ym = load_yashar_mana()
    ym_match = lookup_in(ym, transliteration)
    if ym_match:
        results["matches"].append({
            "root": ym_match.get("semitic", ""),
            "language": "Semitic (YasharMana)",
            "meaning": ym_match.get("meaning", ""),
            "distance": 0.0,
            "method": "yashar_mana",
            "source": ym_match.get("source", ""),
        })

    # Step 2.5: Scholarly match (post-Gordon readings from other scholars)
    scholarly = load_scholarly()
    sch_match = lookup_in(scholarly, transliteration)
    if sch_match:
        results["matches"].append({
            "root": sch_match.get("semitic", ""),
            "language": "Semitic (Scholarly)",
            "meaning": sch_match.get("meaning", ""),
            "distance": 0.0,
            "method": "scholarly",
            "source": sch_match.get("source", ""),
        })

    # Morphophonological skeleton variants (surface + nun restorations,
    # III-weak strip, geminate rules) — shared by the Proto-Semitic
    # and Ugaritic distance searches.
    skel_candidates: list[tuple[str, float, str]] = []
    if skeleton:
        skel_candidates = _generate_morphophonological_skeletons(
            transliteration, skeleton, full_cv,
        )
        results["skeleton_variants"] = [
            {"skeleton": s, "penalty": p, "rule": r}
            for s, p, r in skel_candidates
        ]

    # Historical lens: attested-metathesis variants extend the SEMITIC
    # candidate list only — Luwian/Egyptian/Greek always search the base.
    semitic_candidates = skel_candidates
    if historical_lens and skeleton:
        hist_variants = _generate_historical_skeletons(skeleton)
        if hist_variants:
            semitic_candidates = skel_candidates + hist_variants
            results["skeleton_variants"].extend(
                {"skeleton": s, "penalty": p, "rule": r}
                for s, p, r in hist_variants
            )
            fired = {r for _, _, r in hist_variants}
            results["historical_lens_rules"] = {
                rule["rule"]: rule["source"]
                + (f"; {rule['dialect']} dialect" if rule.get("dialect") else "")
                for rule in HISTORICAL_METATHESIS_RULES
                if rule["rule"] in fired
            }

    # Step 3: Proto-Semitic distance search (with morphophonological variants).
    # The lens bypasses the cache: cached rows are surface-only.
    if skeleton:
        if use_cache and CACHE_FILE.exists() and not historical_lens:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            cached_matches = cache.get(transliteration, [])
            for m in cached_matches[:top_n]:
                results["matches"].append({**m, "method": "proto_semitic"})
        else:
            ps_matches = _search_proto_semitic_multi(semitic_candidates, top_n)
            results["matches"].extend(ps_matches)

    # Step 4: Luwian distance search
    if include_luwian and skeleton:
        luwian_matches = _search_luwian_roots(skeleton, top_n)
        results["matches"].extend(luwian_matches)

    # Step 5: Egyptian distance search
    if include_egyptian and skeleton:
        egyptian_matches = _search_egyptian_roots(skeleton, top_n)
        results["matches"].extend(egyptian_matches)

    # Step 6: Ugaritic contact lexicon search (with morphophonological variants)
    if include_ugaritic and skeleton:
        ugaritic_matches = _search_ugaritic_multi(semitic_candidates, top_n)
        results["matches"].extend(ugaritic_matches)

    # Step 7: Amorite onomasticon search (with morphophonological variants)
    if include_amorite and skeleton:
        amorite_matches = _search_amorite_multi(semitic_candidates, top_n)
        results["matches"].extend(amorite_matches)

    # Step 7b: Pre-Islamic Arabian onomasticon (Harding 1971, cross-skill)
    if include_arabian and skeleton:
        arabian_matches = _search_arabian_multi(semitic_candidates, top_n)
        results["matches"].extend(arabian_matches)

    # Step 8: Greek lexicon search (LSJ). Greek is not a consonantal-root
    # language — score the full CV string, not the skeleton, so vowels
    # count as lexical (kuruso ~ khrusos, not krs ~ ks). Attested LB
    # tokens render through the LB syllabary into the same neutralized
    # space as the precomputed lb_keys (a2/a3/pu2/jo/wo/qo... covered);
    # queries the LB syllabary refuses (LA-specific signs) fall back to
    # the Linear A decomposition.
    if include_greek:
        full_str = lb_token_to_key(transliteration)
        if full_str is None and full_cv and len(full_cv) == len(transliteration.split("-")):
            # Complete LA coverage only — a decomposition that silently
            # skipped a syllable must never reach the distance metric.
            full_str = "".join(f"{c or ''}{v}" for c, v in full_cv)
        if full_str:
            greek_matches = _search_greek_roots(full_str, top_n)
            results["matches"].extend(greek_matches)

    # Step 9: Hebrew contact lexicon search (with morphophonological variants)
    if include_hebrew and skeleton:
        hebrew_matches = _search_hebrew_multi(semitic_candidates, top_n)
        results["matches"].extend(hebrew_matches)

    # Step 10: Aramaic contact lexicon search (with morphophonological variants)
    if include_aramaic and skeleton:
        aramaic_matches = _search_aramaic_multi(semitic_candidates, top_n)
        results["matches"].extend(aramaic_matches)

    # Step 11: Geʿez contact lexicon search (with morphophonological variants)
    if include_geez and skeleton:
        geez_matches = _search_geez_multi(semitic_candidates, top_n)
        results["matches"].extend(geez_matches)

    # Step 12: South Arabian contact lexicon search (with morphophonological variants)
    if include_south_arabian and skeleton:
        sa_matches = _search_south_arabian_multi(semitic_candidates, top_n)
        results["matches"].extend(sa_matches)

    # Step 12b: Akkadian contact files (opt-in; the only path that reads K for ḫ)
    if include_akkadian and skeleton:
        results["matches"].extend(_search_akkadian_multi(semitic_candidates, top_n))

    # Step 13: verb lens — separate section, never mixed into bare-stem matches
    if verb_lens and skeleton:
        results["verbal_parses"] = _verb_lens_search(
            transliteration, top_n,
            include_ugaritic=include_ugaritic,
            include_hebrew=include_hebrew,
            include_aramaic=include_aramaic,
            include_geez=include_geez,
            include_amorite=include_amorite,
        )

    return results


def _search_proto_semitic(skeleton: str, top_n: int) -> list[dict[str, Any]]:
    """Brute-force search against Proto-Semitic roots."""
    roots = load_semitic_roots()
    if not roots:
        return []

    skel_len = len(skeleton)
    max_dist = 0.5 if skel_len <= 3 else 0.3

    scored: list[tuple[float, dict]] = []
    for entry in roots:
        root_str = entry.get("Proto-Semitic", "")
        root_consonants = _extract_root_consonants(root_str)
        if not root_consonants:
            continue

        dist = weighted_levenshtein(skeleton, root_consonants, guttural_transparent=True)
        root_tokens = _tokenize_phonemes(root_consonants)
        visible_root_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)
        if dist <= max_dist * max(skel_len, visible_root_len, 1):
            scored.append((dist, {
                "root": root_str,
                "language": "Proto-Semitic",
                "meaning": entry.get("Meaning", ""),
                "distance": round(dist, 3),
                "method": "proto_semitic",
            }))

    scored.sort(key=lambda x: x[0])
    return [m for _, m in scored[:top_n]]


def _search_proto_semitic_multi(
    skeleton_candidates: list[tuple[str, float, str]], top_n: int,
) -> list[dict[str, Any]]:
    """Search PS roots against multiple skeleton candidates with penalties.

    Each candidate is (skeleton, penalty, rule_name). The penalty is added to
    the raw Levenshtein distance. For each root, only the best-scoring
    candidate is kept; if a root matches via both surface and I-nun, surface wins.
    """
    roots = load_semitic_roots()
    if not roots:
        return []

    best_per_root: dict[str, tuple[float, dict]] = {}

    for skel, penalty, rule in skeleton_candidates:
        skel_len = len(skel)
        max_dist = 0.5 if skel_len <= 3 else 0.3

        for entry in roots:
            root_str = entry.get("Proto-Semitic", "")
            root_variants = _extract_root_consonant_variants(root_str)
            if not root_variants:
                continue

            for rc in root_variants:
                dist = weighted_levenshtein(skel, rc, guttural_transparent=True)
                root_tokens = _tokenize_phonemes(rc)
                visible_root_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)
                if dist <= max_dist * max(skel_len, visible_root_len, 1):
                    effective_dist = dist + penalty
                    key = root_str
                    prev = best_per_root.get(key)
                    if prev is None or effective_dist < prev[0]:
                        result = {
                            "root": root_str,
                            "language": "Proto-Semitic",
                            "meaning": entry.get("Meaning", ""),
                            "distance": round(effective_dist, 3),
                            "method": "proto_semitic",
                        }
                        if rule != "surface":
                            result["morphophonological_rule"] = rule
                            result["skeleton_used"] = skel
                            result["base_distance"] = round(dist, 3)
                        best_per_root[key] = (effective_dist, result)

    scored = sorted(best_per_root.values(), key=lambda x: x[0])
    return [m for _, m in scored[:top_n]]


def _extract_root_consonants(ps_root: str) -> str:
    """Extract consonants from Proto-Semitic notation.

    *ʔab- → ʔb, *θalaθ- → θlθ, *ḥabl- → ḥbl
    """
    variants = _extract_root_consonant_variants(ps_root)
    return variants[0] if variants else ""


# SED's macron-below letters typed with an underscore (t_ = ṯ, d_ = ḏ, h_ = ẖ = ḫ, t_̣ = ṯ̣ = ẓ). Read at search time;
# the semitic_roots records keep their notation until their own audit.
_SED_UNDERSCORES = (("t_̣", "ẓ"), ("ṭ_", "ẓ"), ("t_", "ṯ"), ("d_", "ḏ"), ("h_", "ḫ"))


def _sed_underscores(ps_root: str) -> str:
    s = unicodedata.normalize("NFD", ps_root)
    for typed, letter in _SED_UNDERSCORES:
        s = s.replace(typed, letter)
    return unicodedata.normalize("NFC", s)


def _extract_root_consonant_variants(ps_root: str) -> list[str]:
    """Extract consonant variants from PS notation, splitting on ~ separators.

    "*ytn ~ *ntn" → ["ytn", "ntn"]
    "*ʔab-" → ["ʔb"]
    "*(ʔi-)nVš-" → ["ʔnš"]
    "*aVbVb-" → ["ʾbb", "bb"]  (Kogan K-series: initial bare vowel = lost ʾ)

    A word-initial bare vowel in a PS root string (Kogan K-series V-placeholder
    notation and vocalized Akkadian forms) reflects an unwritten glottal onset —
    Semitic roots never begin with a true vowel. The ʾ-prefixed skeleton is the
    primary variant; the plain vowel-dropped skeleton is retained as fallback.
    """
    parts = re.split(r'\s*~\s*', _sed_underscores(ps_root))
    variants = []
    for part in parts:
        s = part.strip("*- ()")
        s = re.sub(r'[\d\s]', '', s)
        s = re.sub(r'[-(){}*?\[\]/,;:.]', '', s)
        initial_bare_vowel = bool(s) and s[0] in "aiuāīū"
        consonants = []
        for ch in s:
            if ch in "aiueoāīūēōVv":
                continue
            consonants.append(ch)
        result = "".join(consonants)
        if initial_bare_vowel and result:
            guttural_form = "ʾ" + result
            if guttural_form not in variants:
                variants.append(guttural_form)
        if result and result not in variants:
            variants.append(result)
    return variants


def _generate_morphophonological_skeletons(
    transliteration: str, surface_skeleton: str, full_cv: list[tuple],
) -> list[tuple[str, float, str]]:
    """Generate skeleton variants from regular NWS morphophonological rules.

    Returns list of (skeleton, penalty, rule_name) tuples.
    The surface skeleton is always first with penalty 0.
    """
    candidates = [(surface_skeleton, 0.0, "surface")]

    if not full_cv:
        return candidates

    starts_with_vowel = full_cv[0][0] is None
    skel_tokens = _tokenize_phonemes(surface_skeleton)

    # I-nun assimilation: when initial syllable is vowel-only and skeleton has ≥2
    # consonants, restore a root-initial n (nātanā → āt(t)anā → A-TA-NA)
    if starts_with_vowel and len(skel_tokens) >= 2:
        candidates.append(("n" + surface_skeleton, 0.15, "i_nun_assimilation"))

    # III-weak suffix strip: final t/s/n may be a NWS nominal suffix masking
    # a lost final -y/-w of a III-weak root (*bny → bnt with fem. -t)
    if len(skel_tokens) >= 3 and skel_tokens[-1] in ("t", "s", "n"):
        truncated = "".join(skel_tokens[:-1])
        candidates.append((truncated, 0.20, "iii_weak_suffix_strip"))

    # Final-n loss: Aegean orthography never writes a word-final consonant,
    # and Greek receiving forms shed a Semitic final nun before it could be
    # spelled (ktn → ki-to/khitōn; ššmn → sa-sa-ma/sāsama), so a borrowed
    # root's final -n is invisible on the surface. Restore it as a variant.
    if len(skel_tokens) >= 2 and skel_tokens[-1] != "n":
        candidates.append((surface_skeleton + "n", 0.20, "final_n_loss_restoration"))

    # Geminate orthography: a doubled sign (TI-TI, DI-DI, KU-KU...)
    # spells a geminate consonant, and NWS geminates commonly continue *-nC-
    # (ntk > ttk; *mantant > mattatt). Restore the nun; also offer the plain
    # collapse for D-stem gemination on a shorter root. Detection is
    # orthographic — same consonant AND same vowel in consecutive signs —
    # so accidental consonant repeats across different vowels never trigger.
    seen = {c[0] for c in candidates}
    skel_idx = 0
    for i, (c, v) in enumerate(full_cv):
        if c is None:
            continue  # vowel-only sign occupies no skeleton slot
        if (
            i + 1 < len(full_cv)
            and (c, v) == full_cv[i + 1]
            and c in GEMINABLE_STOPS
            and skel_idx + 1 < len(skel_tokens)
        ):
            restored = skel_tokens[:]
            restored[skel_idx] = "n"
            variant = "".join(restored)
            if variant not in seen:
                candidates.append((variant, 0.15, "geminate_nun_restoration"))
                seen.add(variant)
            collapsed = skel_tokens[:skel_idx] + skel_tokens[skel_idx + 1:]
            if len(collapsed) >= 2:
                variant = "".join(collapsed)
                if variant not in seen:
                    candidates.append((variant, 0.25, "degemination"))
                    seen.add(variant)
        skel_idx += 1

    return candidates


def _generate_historical_skeletons(
    surface_skeleton: str,
) -> list[tuple[str, float, str]]:
    """Attested-metathesis variants of the surface skeleton (--historical-lens).

    Applies each HISTORICAL_METATHESIS_RULES pair to every adjacent occurrence,
    in either order, one swap per variant — never the powerset, never stacked
    on morphophonological or verb-lens variants. Returns (skeleton, penalty,
    rule_name) tuples, the same shape _generate_morphophonological_skeletons
    returns, so the _search_*_multi penalty plumbing applies unchanged.
    """
    tokens = _tokenize_phonemes(surface_skeleton)
    variants: list[tuple[str, float, str]] = []
    seen = {surface_skeleton}
    for rule in HISTORICAL_METATHESIS_RULES:
        for a, b in rule["pairs"]:
            for i in range(len(tokens) - 1):
                if {tokens[i], tokens[i + 1]} == {a, b}:
                    swapped = tokens[:i] + [tokens[i + 1], tokens[i]] + tokens[i + 2:]
                    variant = "".join(swapped)
                    if variant not in seen:
                        variants.append((variant, rule["penalty"], rule["rule"]))
                        seen.add(variant)
    return variants


# --- Verb lens (report-only): deparse verbal morphology, search residual roots ---

# Cross-product ceiling over all parses' skeleton candidates:
# polyphonic explosion on long formula words must not stall the search.
MAX_LENS_CANDIDATES = 24

# pos values that can plausibly realize a verbal parse (inventoried across
# the four contact lexica: only "verb" and "participle" exist as verb-like
# values). None and the literal string "unknown" (306 Geʿez entries) both
# mean "no analysis" — flagged, never silently dropped.
VERB_LIKE_POS = frozenset({"verb", "participle"})
UNKNOWN_POS = frozenset({None, "unknown"})

_UGARITIC_POS_CACHE: dict[str, set[str]] | None = None
_GEMINATE_TEMPLATE_IDS: frozenset[str] | None = None


def _ugaritic_pos_map() -> dict[str, set[str]]:
    """form_original → all attested pos values for the Ugaritic layer, whose
    search results don't carry pos through (unlike Hebrew/Aramaic/Geʿez).

    A set, not a single value: 57 form_original homographs carry conflicting
    pos, and last-write-wins would overwrite real verbs (hmt, dqt) with their
    noun homographs.
    """
    global _UGARITIC_POS_CACHE
    if _UGARITIC_POS_CACHE is None:
        pos_map: dict[str, set[str]] = {}
        for e in load_ugaritic_roots():
            form, pos = e.get("form_original"), e.get("pos")
            if form and pos:
                pos_map.setdefault(form, set()).add(pos)
        _UGARITIC_POS_CACHE = pos_map
    return _UGARITIC_POS_CACHE


def _geminate_template_ids() -> frozenset[str]:
    global _GEMINATE_TEMPLATE_IDS
    if _GEMINATE_TEMPLATE_IDS is None:
        from ..core.verb_morphology import load_templates
        _GEMINATE_TEMPLATE_IDS = frozenset(
            t.id for t in load_templates() if t.require_geminate
        )
    return _GEMINATE_TEMPLATE_IDS


def _verb_lens_candidates(parse: VerbParse) -> list[tuple[str, float, str]]:
    """Skeleton candidates for one verbal parse.

    The deparser runs first on the transliteration; the existing
    morphophonological rules then compose on the residual,
    except iii_weak_suffix_strip when the parse already stripped a verbal
    suffix — no double suffix-strip. Restored-radical variants skip the
    composition: their skeleton has no transliteration to re-derive from.
    """
    rule = "verb_lens:" + "+".join(parse.rules)
    if parse.restored_radical:
        return [(parse.residual_skeleton, parse.penalty, f"{rule}+{parse.restored_radical}_restored")]
    residual_translit = "-".join(parse.residual_signs)
    base = _generate_morphophonological_skeletons(
        residual_translit, parse.residual_skeleton, extract_full(residual_translit),
    )
    candidates = []
    for skel, pen, r in base:
        if r == "iii_weak_suffix_strip" and parse.stripped_suffix:
            continue
        composed = rule if r == "surface" else f"{rule}+{r}"
        candidates.append((skel, round(parse.penalty + pen, 4), composed))

    # Geminate-template parses (D/tD) claim the doubled R2 is morphology,
    # not root — so also offer the R2-collapsed skeleton, which the generic
    # degemination rule (stops-only) never produces for sibilants.
    # Mechanical candidate generation only, no lexical claim about the word.
    if any(r in _geminate_template_ids() for r in parse.rules):
        tokens = _tokenize_phonemes(parse.residual_skeleton)
        for i in range(len(tokens) - 1):
            if tokens[i] == tokens[i + 1]:
                collapsed = "".join(tokens[:i] + tokens[i + 1:])
                candidates.append((collapsed, parse.penalty, f"{rule}+r2_collapse"))
                break
    return candidates


def _pos_filter_lens_matches(
    matches: list[dict[str, Any]], ug_pos: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """Post-filter lens matches by part of speech.

    A verbal parse should resolve to a verbal root: layers with pos data
    (Hebrew, Aramaic, Geʿez, Ugaritic via lookup) keep verb-like entries
    (verb, participle); entries without a real analysis (missing pos, or
    the literal "unknown") are kept but flagged pos_unknown. Ugaritic
    homographs keep every attested pos, so a form that is both noun and
    verb survives. Proto-Semitic and onomastic layers pass through
    unfiltered — PS glosses carry no pos, and Amorite sentence-names are
    themselves inflected verbs.
    """
    kept: list[dict[str, Any]] = []
    for m in matches:
        method = m.get("method", "")
        if method in ("hebrew_distance", "aramaic_distance", "geez_distance"):
            pos_values = {m.get("pos")}
        elif method == "ugaritic_distance":
            pos_values = ug_pos.get(m.get("root", "")) or {None}
        else:
            kept.append(m)
            continue
        if pos_values & VERB_LIKE_POS:
            kept.append(m)
        elif pos_values <= UNKNOWN_POS:
            flagged = dict(m)
            flagged["pos_unknown"] = True
            kept.append(flagged)
    return kept


def _verb_lens_search(
    transliteration: str,
    top_n: int,
    include_ugaritic: bool = False,
    include_hebrew: bool = False,
    include_aramaic: bool = False,
    include_geez: bool = False,
    include_amorite: bool = False,
) -> list[dict[str, Any]]:
    """Run the verb-morphology deparser and search each residual root.

    Report-only — never writes affiliations or promotes entries. Returns one
    dict per surviving parse with its cognate matches, for the separate
    VERBAL PARSES output section (never mixed into bare-stem rows).
    """
    parses = verbal_parses(transliteration)
    if not parses:
        return []

    ug_pos = _ugaritic_pos_map() if include_ugaritic else {}
    sections: list[dict[str, Any]] = []
    budget = MAX_LENS_CANDIDATES
    for parse in parses:
        if budget <= 0:
            break
        candidates = _verb_lens_candidates(parse)[:budget]
        budget -= len(candidates)

        matches = _search_proto_semitic_multi(candidates, top_n)
        if include_ugaritic:
            matches += _search_ugaritic_multi(candidates, top_n)
        if include_hebrew:
            matches += _search_hebrew_multi(candidates, top_n)
        if include_aramaic:
            matches += _search_aramaic_multi(candidates, top_n)
        if include_geez:
            matches += _search_geez_multi(candidates, top_n)
        if include_amorite:
            matches += _search_amorite_multi(candidates, top_n)
        matches = _pos_filter_lens_matches(matches, ug_pos)
        matches.sort(key=lambda m: m["distance"])

        sections.append({
            "stem": parse.stem,
            "rules": list(parse.rules),
            "stripped": {
                "prefix": list(parse.stripped_prefix),
                "infix": parse.stripped_infix,
                "suffix": list(parse.stripped_suffix),
            },
            "residual": "-".join(parse.residual_signs),
            "residual_skeleton": parse.residual_skeleton,
            "restored_radical": parse.restored_radical,
            "penalty": parse.penalty,
            "vocalization": parse.vocalization,
            "matches": matches[:top_n],
        })
    return sections


def load_corpus() -> dict[str, dict[str, Any]]:
    """Load corpus from extracted JSON."""
    cached = DATA_DIR / "corpus.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    if LASHON_DIR is None or not (LASHON_DIR / "LinearAInscriptions.js").exists():
        raise NotInCheckout(f"corpus.json is not in this checkout (looked for {cached})")
    from ..core.js_parser import parse_inscriptions
    return parse_inscriptions(LASHON_DIR / "LinearAInscriptions.js")


def _normalize_root(root: str) -> str:
    """Strip formatting characters from a root, preserving phonemic consonants.

    Accepts 'y-r-h', 'yrh', 'y.r.h', etc. Gutturals (ʔ, ʿ, ʾ, ḥ, ḫ) are
    preserved so guttural-transparent Levenshtein can apply proper costs.
    """
    import re
    import unicodedata
    root = unicodedata.normalize("NFC", root)
    cleaned = re.sub(r"[-.'*_()/\d\s]", "", root)
    return cleaned.lower()


def reverse_root_search(
    root: str,
    max_distance: float | None = None,
    top_n: int = 20,
    distances: dict[tuple[str, str], float] | None = None,
    guttural_transparent: bool = True,
) -> dict[str, Any]:
    """Search the corpus for words whose skeletons match a root.

    Given a consonantal root like 'kns' or 'y-r-h', finds all corpus words
    with matching or similar skeletons. Works for both Semitic (default,
    guttural-transparent) and Luwian (pass distances=LUWIAN_DISTANCES,
    guttural_transparent=False).
    """
    root_lower = _normalize_root(root)
    if max_distance is None:
        max_distance = 0.5 if len(root_lower) <= 3 else 0.3
    corpus = load_corpus()
    gordon = load_gordon()
    ym = load_yashar_mana()
    scholarly = load_scholarly()

    word_inscriptions: dict[str, list[str]] = {}
    for name, entry in corpus.items():
        tw = entry.get("transliteratedWords", [])
        if isinstance(tw, list):
            for w in tw:
                if w and w not in ("𐄁", "\n", "") and "-" in w:
                    word_inscriptions.setdefault(w, []).append(name)

    scored: list[dict[str, Any]] = []

    for word, inscriptions in word_inscriptions.items():
        skeleton = extract_skeleton(word)
        if not skeleton:
            continue

        dist = weighted_levenshtein(
            skeleton, root_lower,
            distances=distances,
            guttural_transparent=guttural_transparent,
        )
        root_tokens = _tokenize_phonemes(root_lower)
        if guttural_transparent:
            visible_root_len = sum(1 for t in root_tokens if t not in GUTTURAL_PHONEMES)
        else:
            visible_root_len = len(root_tokens)
        if dist > max_distance * max(len(skeleton), visible_root_len, 1):
            continue

        # Check for Gordon/YasharMana/Scholarly reading
        known_reading = None
        g = lookup_in(gordon, word)
        if g:
            known_reading = f"Gordon: {g.get('meaning', '')} ({g.get('semitic', '')})"
        else:
            y = lookup_in(ym, word)
            if y:
                known_reading = f"YasharMana: {y.get('meaning', '')} ({y.get('semitic', '')})"
            else:
                s = lookup_in(scholarly, word)
                if s:
                    known_reading = f"Scholarly: {s.get('meaning', '')} ({s.get('source', '')})"

        # Get site info
        sites = set()
        for iname in inscriptions:
            entry = corpus.get(iname, {})
            site = entry.get("site", "")
            if site:
                sites.add(site)

        scored.append({
            "word": word,
            "skeleton": skeleton,
            "distance": round(dist, 3),
            "occurrences": len(inscriptions),
            "inscriptions": sorted(set(inscriptions)),
            "sites": sorted(sites),
            "known_reading": known_reading,
        })

    # Sort by distance, then by occurrence count (descending)
    scored.sort(key=lambda x: (x["distance"], -x["occurrences"]))

    # Check compound morphemes for embedded root matches
    compound_hits = []
    if len(root_lower) >= 2:
        compounds = load_compound_morphemes()
        for compound in compounds:
            for r in compound.get("roots", []):
                r_norm = _normalize_root(r)
                if not r_norm:
                    continue
                if r_norm == root_lower or (len(root_lower) >= 2 and r_norm.startswith(root_lower)) or (len(r_norm) >= 2 and root_lower.startswith(r_norm)):
                    compound_hits.append({
                        "word": compound.get("word", ""),
                        "reading": compound.get("reading", ""),
                        "meaning": compound.get("meaning", ""),
                        "root_match": r,
                        "source": compound.get("source", ""),
                        "note": compound.get("note", ""),
                    })
                    break

    return {
        "root": root,
        "root_consonants": root_lower,
        "total_matches": len(scored),
        "matches": scored[:top_n],
        "compound_hits": compound_hits,
    }


def syllabic_grep(
    patterns: str,
    top_n: int = 100,
) -> dict[str, Any]:
    """Search corpus transliteratedWords for raw syllabic patterns.

    Unlike --reverse, this does no skeleton reduction — it matches the literal
    syllable sequences (e.g., JA-RA, JA-RE) as substrings of corpus words.
    Preserves prefixes like ya- and i- that skeleton extraction strips.
    """
    corpus = load_corpus()
    pat_list = [p.strip().upper() for p in patterns.split(",")]

    hits: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for tablet_id, entry in corpus.items():
        words = entry.get("transliteratedWords", [])
        site = entry.get("site", "")
        support = entry.get("support", "")
        context = entry.get("context", "")
        if not isinstance(words, list):
            continue
        for w in words:
            if not isinstance(w, str) or "-" not in w:
                continue
            w_upper = w.upper()
            for pat in pat_list:
                if pat in w_upper:
                    key = (tablet_id, w)
                    if key not in seen:
                        seen.add(key)
                        hits.append({
                            "tablet": tablet_id,
                            "word": w,
                            "matched_pattern": pat,
                            "site": site,
                            "support": support,
                            "context": context,
                        })
                    break

    hits.sort(key=lambda x: (x["site"], x["tablet"]))
    return {
        "patterns": pat_list,
        "total_hits": len(hits),
        "hits": hits[:top_n],
    }


def format_syllabic_table(result: dict[str, Any]) -> str:
    """Format syllabic grep results as readable table."""
    lines = [
        f"Syllabic grep: {', '.join(result['patterns'])}",
        f"Total hits:    {result['total_hits']}",
        "",
    ]
    hits = result["hits"]
    if not hits:
        lines.append("No matches found.")
        return "\n".join(lines)

    lines.append(f"{'Tablet':<15} {'Word':<25} {'Pattern':<10} {'Site':<20} {'Support'}")
    lines.append("-" * 90)
    for h in hits:
        lines.append(
            f"{h['tablet']:<15} {h['word']:<25} {h['matched_pattern']:<10} "
            f"{h['site']:<20} {h['support']}"
        )
    return "\n".join(lines)


def _merge_reverse_results(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merge two reverse-search result sets, deduplicating by word.

    When the same word appears in both, keep the entry with the lower distance.
    The second result's compound_hits are appended (deduplicated by word).
    """
    by_word: dict[str, dict[str, Any]] = {}
    for m in base["matches"]:
        by_word[m["word"]] = m
    for m in extra["matches"]:
        existing = by_word.get(m["word"])
        if existing is None or m["distance"] < existing["distance"]:
            by_word[m["word"]] = m

    merged = sorted(by_word.values(), key=lambda x: (x["distance"], -x["occurrences"]))

    seen_compounds = {ch["word"] for ch in base.get("compound_hits", [])}
    merged_compounds = list(base.get("compound_hits", []))
    for ch in extra.get("compound_hits", []):
        if ch["word"] not in seen_compounds:
            seen_compounds.add(ch["word"])
            merged_compounds.append(ch)

    return {
        "root": base["root"],
        "root_consonants": base["root_consonants"],
        "total_matches": len(merged),
        "matches": merged,
        "compound_hits": merged_compounds,
    }


def format_reverse_table(result: dict[str, Any]) -> str:
    """Format reverse search results as readable table."""
    lines = [
        f"Root search:   {result['root']}",
        f"Consonants:    {result['root_consonants']}",
        f"Total matches: {result['total_matches']}",
        "",
    ]

    # Show compound morpheme hits first if any
    compound_hits = result.get("compound_hits", [])
    if compound_hits:
        lines.append(f"Known compounds containing √{result['root_consonants']}:")
        for ch in compound_hits:
            lines.append(
                f"  {ch['word']:<28} = {ch['reading']:<24} [{ch['source']}]"
            )
            if ch.get("note"):
                lines.append(f"    {ch['note']}")
        lines.append("")

    matches = result["matches"]
    if not matches:
        lines.append("No corpus words found matching this root.")
        return "\n".join(lines)

    metrics_present = {m.get("search_metric") for m in matches if m.get("search_metric")}
    multi_metric = len(metrics_present) > 1

    if multi_metric:
        lines.append(f"{'Word':<24} {'Skeleton':<10} {'Dist':>6} {'#':>4} {'Metric':<9} {'Sites':<16} {'Reading'}")
        lines.append("-" * 105)
    else:
        lines.append(f"{'Word':<24} {'Skeleton':<10} {'Dist':>6} {'#':>4} {'Sites':<20} {'Reading'}")
        lines.append("-" * 100)

    for m in matches:
        reading = m["known_reading"] or ""
        sites = ", ".join(m["sites"][:3])
        if len(m["sites"]) > 3:
            sites += f" +{len(m['sites']) - 3}"
        if multi_metric:
            metric = m.get("search_metric", "nws")
            lines.append(
                f"{m['word']:<24} {m['skeleton']:<10} {m['distance']:>6.3f} "
                f"{m['occurrences']:>4} {metric:<9} {sites:<16} {reading}"
            )
        else:
            lines.append(
                f"{m['word']:<24} {m['skeleton']:<10} {m['distance']:>6.3f} "
                f"{m['occurrences']:>4} {sites:<20} {reading}"
            )

    return "\n".join(lines)


CACHE_SCORER_VERSION = "2.0"  # 2026-07-20: variants, morphophonology, determinism


def _sha256_file(path: Path) -> str | None:
    import hashlib
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_cache(top_n: int = 5, output: str | None = None) -> None:
    """Build the precomputed cognate cache.

    Scorer v2.0: deterministic word/tie ordering (byte-identical rebuilds),
    all root consonant variants (incl. K-series ʾ-forms), morphophonological
    skeleton variants (I-nun, III-weak), and a provenance sidecar.

    With --output, writes to a staged path (exclusive create — never
    overwrites). Without it, snapshots the production cache before writing.
    """
    print(f"Building cognate cache (scorer v{CACHE_SCORER_VERSION})...", file=sys.stderr)
    # Same source as load_corpus(): curated data/linear-a/corpus.json (local corrections, SigLA-only
    # records), upstream LinearAInscriptions.js only when the extract is absent.
    corpus_source = DATA_DIR / "corpus.json"
    if not corpus_source.exists() and LASHON_DIR is not None:
        corpus_source = LASHON_DIR / "LinearAInscriptions.js"
    inscriptions = load_corpus()

    # Collect unique words
    words: set[str] = set()
    for entry in inscriptions.values():
        tw = entry.get("transliteratedWords", [])
        if isinstance(tw, list):
            words.update(tw)
        elif isinstance(tw, str):
            words.add(tw)

    # Filter to words with extractable skeletons — sorted for determinism
    searchable = {}
    for w in sorted(words):
        skel = extract_skeleton(w)
        if skel:
            searchable[w] = skel

    print(f"  {len(searchable)} words with extractable skeletons", file=sys.stderr)

    cache: dict[str, list[dict]] = {}
    roots = load_semitic_roots()
    total = len(searchable)
    for idx, (word, skeleton) in enumerate(searchable.items()):
        if (idx + 1) % 200 == 0:
            print(f"  {idx + 1}/{total}...", file=sys.stderr)

        full_cv = extract_full(word)
        skel_candidates = _generate_morphophonological_skeletons(
            word, skeleton, full_cv,
        )

        best_per_root: dict[str, tuple[float, dict]] = {}
        for skel, penalty, rule in skel_candidates:
            for entry in roots:
                root_str = entry.get("Proto-Semitic", "")
                for rc in _extract_root_consonant_variants(root_str):
                    dist = weighted_levenshtein(
                        skel, rc, guttural_transparent=True,
                    )
                    if dist >= len(skel):
                        continue
                    effective = dist + penalty
                    prev = best_per_root.get(root_str)
                    if prev is None or effective < prev[0]:
                        m = {
                            "root": root_str,
                            "language": "Proto-Semitic",
                            "meaning": entry.get("Meaning", ""),
                            "distance": round(effective, 3),
                        }
                        if rule != "surface":
                            m["morphophonological_rule"] = rule
                            m["skeleton_used"] = skel
                        best_per_root[root_str] = (effective, m)

        scored = sorted(
            best_per_root.items(), key=lambda kv: (kv[1][0], kv[0]),
        )
        if scored:
            cache[word] = [m for _, (_, m) in scored[:top_n]]

    body = json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "x", encoding="utf-8") as f:  # exclusive: no overwrite
            f.write(body)
    else:
        out_path = CACHE_FILE
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if CACHE_FILE.exists():
            from datetime import UTC
            from datetime import datetime as _dt
            bak = CACHE_FILE.with_name(
                CACHE_FILE.name + ".bak-" + _dt.now(UTC).strftime("%Y%m%d_%H%M%S"),
            )
            bak.write_bytes(CACHE_FILE.read_bytes())
            print(f"  Snapshotted old cache → {bak.name}", file=sys.stderr)
        CACHE_FILE.write_text(body, encoding="utf-8")

    provenance = {
        "scorer_version": CACHE_SCORER_VERSION,
        "built": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc,
        ).isoformat(),
        "top_n": top_n,
        "entries": len(cache),
        "corpus_source": (
            str(corpus_source.resolve().relative_to(DATA_DIR.parent.resolve()))
            if corpus_source.resolve().is_relative_to(DATA_DIR.parent.resolve())
            else str(corpus_source)
        ),
        "corpus_source_sha256": _sha256_file(corpus_source),
        "semitic_roots_sha256": _sha256_file(SEMITIC_ROOTS_DATA / "semitic_roots.json"),
        "roots_count": len(roots),
        "morphophonological_variants": True,
        "root_consonant_variants": True,
        "deterministic": "sorted words, sort_keys, (distance, root) tie-break",
    }
    prov_path = out_path.with_name(out_path.name + ".provenance.json")
    prov_path.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.0f}KB, {len(cache)} entries)", file=sys.stderr)
    print(f"Wrote {prov_path}", file=sys.stderr)


def proto_semitic_search(
    term: str,
    top_n: int = 20,
    max_distance: float | None = None,
) -> dict[str, Any]:
    """Search Proto-Semitic roots by meaning, then find corpus attestations.

    For each root matching the meaning keyword:
    1. Compute the "Linear A visible" form (gutturals stripped)
    2. Run reverse corpus search with guttural-transparent matching
    3. Report both full root and visible skeleton
    """
    roots = load_semitic_roots()
    term_lower = term.lower()
    matching_roots = []
    for entry in roots:
        meaning = entry.get("Meaning", "").lower()
        if term_lower in meaning:
            ps = entry.get("Proto-Semitic", "")
            root_consonants = _extract_root_consonants(ps)
            if root_consonants and len(root_consonants) >= 2:
                visible = "".join(c for c in root_consonants if c not in GUTTURAL_PHONEMES)
                matching_roots.append({
                    "proto_semitic": ps,
                    "meaning": entry.get("Meaning", ""),
                    "root_consonants": root_consonants,
                    "visible_skeleton": visible,
                    "gutturals_stripped": [c for c in root_consonants if c in GUTTURAL_PHONEMES],
                })

    results = []
    for root_info in matching_roots:
        corpus_hits = reverse_root_search(
            root_info["root_consonants"],
            max_distance=max_distance,
            top_n=top_n,
        )
        results.append({
            **root_info,
            "corpus_matches": corpus_hits["total_matches"],
            "top_hits": corpus_hits["matches"][:5],
            "compound_hits": corpus_hits.get("compound_hits", []),
        })

    results.sort(key=lambda x: -x["corpus_matches"])
    return {
        "search_term": term,
        "roots_found": len(matching_roots),
        "results": results,
    }


def format_proto_semitic_table(result: dict[str, Any]) -> str:
    """Format Proto-Semitic meaning search results."""
    lines = [
        f"Proto-Semitic search: \"{result['search_term']}\"",
        f"Roots found:          {result['roots_found']}",
        "",
    ]
    for r in result["results"]:
        gutturals = ", ".join(r["gutturals_stripped"]) if r["gutturals_stripped"] else "none"
        lines.append(f"  {r['proto_semitic']:<20} \"{r['meaning']}\"")
        lines.append(f"    Root: {r['root_consonants']:<8}  Visible: {r['visible_skeleton']:<8}  Gutturals: {gutturals}")
        lines.append(f"    Corpus matches: {r['corpus_matches']}")
        for hit in r["top_hits"]:
            reading = hit.get("known_reading") or ""
            lines.append(
                f"      {hit['word']:<24} skel={hit['skeleton']:<8} "
                f"dist={hit['distance']:.3f}  {reading}"
            )
        if r["compound_hits"]:
            for ch in r["compound_hits"]:
                lines.append(f"      [compound] {ch['word']} = {ch['reading']} [{ch['source']}]")
        lines.append("")
    if not result["results"]:
        lines.append("No matching roots found.")
    return "\n".join(lines)


def format_table(result: dict[str, Any]) -> str:
    """Format results as readable table."""
    lines = [
        f"Transliteration: {result['transliteration']}",
        f"Skeleton:         {result['skeleton']}",
        f"CV:               {' '.join(f'{c}{v}' for c, v in result['cv_decomposition'])}",
    ]

    skel_variants = result.get("skeleton_variants", [])
    non_surface = [sv for sv in skel_variants if sv["rule"] != "surface"]
    if non_surface:
        for sv in non_surface:
            lines.append(f"  + {sv['rule']}: {sv['skeleton']} (penalty {sv['penalty']})")

    hist_rules = result.get("historical_lens_rules")
    if hist_rules:
        for rule, source in hist_rules.items():
            lines.append(f"  historical lens: {rule} ({source}) — report-only")

    lines.append("")

    matches = result["matches"]
    if not matches:
        lines.append("No matches found.")
        # A word with no direct cognates can still carry verbal parses —
        # those are exactly the words the lens exists for.
        _append_verbal_parses(lines, result)
        return "\n".join(lines)

    lines.append(f"{'Method':<16} {'Root':<20} {'Meaning':<30} {'Dist':>6}  {'Rule'}")
    lines.append("-" * 90)
    for m in matches:
        rule = m.get("morphophonological_rule", "")
        lines.append(
            f"{m['method']:<16} {m['root']:<20} {m['meaning']:<30} {m['distance']:>6.3f}  {rule}"
        )

    _append_verbal_parses(lines, result)
    return "\n".join(lines)


def _append_verbal_parses(lines: list[str], result: dict[str, Any]) -> None:
    """Render the VERBAL PARSES section (present only when --verb-lens ran)."""
    parses = result.get("verbal_parses")
    if parses is None:
        return
    lines.append("")
    lines.append("VERBAL PARSES (verb lens — candidate generation only)")
    lines.append("-" * 90)
    if not parses:
        lines.append("No template-licensed verbal parse.")
        return
    for vp in parses:
        strips = []
        if vp["stripped"]["prefix"]:
            strips.append("-".join(vp["stripped"]["prefix"]) + "-")
        if vp["stripped"]["infix"]:
            strips.append(f"-{vp['stripped']['infix']}-")
        if vp["stripped"]["suffix"]:
            strips.append("-" + "-".join(vp["stripped"]["suffix"]))
        restored = f" (+{vp['restored_radical']} as R1)" if vp.get("restored_radical") else ""
        lines.append(
            f"{vp['stem']:<12} strip [{', '.join(strips)}] -> {vp['residual']} = "
            f"{'-'.join(vp['residual_skeleton'])}{restored}  penalty {vp['penalty']:.2f}"
        )
        lines.append(f"             {vp['vocalization']}")
        if not vp["matches"]:
            lines.append("             (no cognate match at current thresholds)")
            continue
        for m in vp["matches"]:
            flag = "  pos?" if m.get("pos_unknown") else ""
            rule = m.get("morphophonological_rule", "")
            lines.append(
                f"    {m['method']:<16} {m['root']:<20} {str(m['meaning'])[:36]:<36} "
                f"{m['distance']:>6.3f}  {rule}{flag}"
            )


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Search for Semitic cognates")
    parser.add_argument("transliteration", nargs="?", help="Linear A transliteration (e.g., KI-RE-TA)")
    parser.add_argument("--skeleton", action="store_true", help="Only show skeleton extraction")
    parser.add_argument("--top", "-n", type=int, default=5, help="Number of top matches")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--json", action="store_const", const="json", dest="format",
                        help="Alias for --format json")
    parser.add_argument("--no-cache", action="store_true", help="Skip precomputed cache")
    parser.add_argument("--build-cache", action="store_true", help="Build cognate cache")
    parser.add_argument("--output", default=None,
                        help="Staged output path for --build-cache (exclusive create, "
                             "never overwrites; provenance sidecar written alongside)")
    parser.add_argument("--reverse", metavar="ROOT",
                        help="Reverse search: find corpus words matching a Semitic root. "
                             "Use bare consonants (yrh) or hyphenated (y-r-h); both work.")
    parser.add_argument("--max-dist", type=float, default=None,
                        help="Max normalized distance for reverse search "
                             "(default: 0.5 for roots ≤3 consonants, 0.3 for longer)")
    parser.add_argument("--syllabic-grep", metavar="PATTERNS",
                        help="Raw syllable search: find corpus words containing these syllable "
                             "sequences (comma-separated, e.g., JA-RA,JA-RE,JA-RI)")
    parser.add_argument("--all-readings", action="store_true",
                        help="Search cognates for all polyphonic skeleton variants")
    parser.add_argument("--proto-semitic-search", metavar="TERM",
                        help="Search Proto-Semitic roots by meaning keyword, then find "
                             "corpus attestations with guttural-transparent matching")
    parser.add_argument("--luwian", "--include-luwian", action="store_true",
                        help="Include Luwian root database in search (Tier 4). "
                             "Works with both forward and --reverse modes.")
    parser.add_argument("--reverse-luwian", metavar="ROOT",
                        help="Reverse search: find corpus words matching a Luwian root")
    parser.add_argument("--egyptian", "--include-egyptian", action="store_true",
                        help="Include Egyptian root database in search (Tier 5). "
                             "Works with both forward and --reverse modes.")
    parser.add_argument("--reverse-egyptian", metavar="ROOT",
                        help="Reverse search: find corpus words matching an Egyptian root")
    parser.add_argument("--ugaritic", "--include-ugaritic", action="store_true",
                        help="Include Ugaritic contact lexicon in search (CUC + Huehnergard + DULAT + curated additions; see data/contact/)")
    parser.add_argument("--amorite", "--include-amorite", action="store_true",
                        help="Include Amorite onomasticon in search (Gelb AS 21 glossary + 6,662-name catalog + Howard 2023)")
    parser.add_argument("--arabian", "--include-arabian", action="store_true",
                        help="Include Pre-Islamic Arabian onomasticon in search (Harding 1971, 8.4K names; cross-skill read from the ANE skill)")
    parser.add_argument("--greek", "--include-greek", action="store_true",
                        help="Include Ancient Greek lexicon in search (LSJ 9th ed., Logeion TEI; 117K entries)")
    parser.add_argument("--hebrew", "--include-hebrew", action="store_true",
                        help="Include Hebrew contact lexicon in search (STEPBible TBESH + Open Scriptures BDB; 8.7K entries)")
    parser.add_argument("--aramaic", "--include-aramaic", action="store_true",
                        help="Include Aramaic contact lexicon in search (Aramaic Root Atlas; 1.6K entries)")
    parser.add_argument("--geez", "--include-geez", action="store_true",
                        help="Include Geʿez contact lexicon in search (Dillmann 1865 + Leslau CDG 1987; 4.9K entries)")
    parser.add_argument("--south-arabian", "--include-south-arabian", action="store_true",
                        help="Include South Arabian contact lexicon in search (DASI forms, 19.2K; "
                             "1.6K glossed from Beeston/Biella 1982)")
    parser.add_argument("--akkadian", "--include-akkadian", action="store_true",
                        help="Include the Akkadian contact files (Anchor Bible lexicon + CAD headwords); "
                             "the only search that reads K for ḫ")
    parser.add_argument("--verb-lens", action="store_true",
                        help="Deparse verbal morphology (data/verb_templates.json) and search each "
                             "residual for hidden roots; results render in a separate VERBAL PARSES "
                             "section. Skips the cognate cache. Candidate generation only.")
    parser.add_argument("--historical-lens", action="store_true",
                        help="Extend Semitic searches with attested-metathesis skeleton variants "
                             "(HISTORICAL_METATHESIS_RULES: ṯr↔rṯ, ml↔lm, wl↔lw per Rendsburg 2022, "
                             "each with source + penalty ≥ 0.35). Report-only: penalties keep lens "
                             "matches above the CANDIDATE distance gate. Never applies to "
                             "Luwian/Egyptian/Greek. Skips the Proto-Semitic cache.")

    args = parser.parse_args()

    if args.verb_lens and args.build_cache:
        parser.error("--verb-lens cannot combine with --build-cache: lens variants must never "
                     "enter the persistent cognate cache")
    if args.historical_lens and args.build_cache:
        parser.error("--historical-lens cannot combine with --build-cache: lens variants must "
                     "never enter the persistent cognate cache")
    if args.historical_lens and (args.reverse or args.reverse_luwian or args.reverse_egyptian):
        parser.error("--historical-lens applies to transliteration queries; it cannot combine "
                     "with --reverse searches (root → Linear A)")
    if args.verb_lens and (args.reverse or args.reverse_luwian or args.reverse_egyptian):
        parser.error("--verb-lens applies to transliteration queries; it cannot combine with "
                     "--reverse searches (root → Linear A)")
    reverse_mode = next((flag for flag, value in (
        ("--reverse", args.reverse), ("--reverse-luwian", args.reverse_luwian),
        ("--reverse-egyptian", args.reverse_egyptian)) if value), None)
    if reverse_mode:
        ignored = [flag for flag, value in (
            ("--ugaritic", args.ugaritic), ("--amorite", args.amorite),
            ("--greek", args.greek), ("--hebrew", args.hebrew),
            ("--aramaic", args.aramaic), ("--geez", args.geez),
            ("--south-arabian", args.south_arabian), ("--akkadian", args.akkadian))
            if value]
        if ignored:
            parser.error(f"{', '.join(ignored)} has no effect with {reverse_mode}: the reverse "
                         "searches match the root against the Linear A corpus and read no "
                         "contact lexicon (only --luwian, --egyptian and --arabian join --reverse)")
    if args.verb_lens and (args.skeleton or args.syllabic_grep or args.proto_semitic_search):
        parser.error("--verb-lens has no effect with --skeleton/--syllabic-grep/"
                     "--proto-semitic-search — these modes never run the cognate pipeline")

    if args.build_cache:
        build_cache(top_n=args.top, output=args.output)
        return

    if args.syllabic_grep:
        result = syllabic_grep(args.syllabic_grep, top_n=max(args.top, 100))
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_syllabic_table(result))
        return

    if args.proto_semitic_search:
        result = proto_semitic_search(args.proto_semitic_search, top_n=args.top, max_distance=args.max_dist)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_proto_semitic_table(result))
        return

    if args.reverse_luwian:
        top = max(args.top, 20)
        result = reverse_root_search(
            args.reverse_luwian, max_distance=args.max_dist, top_n=top,
            distances=LUWIAN_DISTANCES, guttural_transparent=False,
        )
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_reverse_table(result))
        return

    if args.reverse_egyptian:
        top = max(args.top, 20)
        result = reverse_root_search(
            args.reverse_egyptian, max_distance=args.max_dist, top_n=top,
            distances=EGYPTIAN_DISTANCES, guttural_transparent=True,
        )
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_reverse_table(result))
        return

    if args.reverse:
        top = max(args.top, 20)
        result = reverse_root_search(args.reverse, max_distance=args.max_dist, top_n=top)
        for m in result["matches"]:
            m.setdefault("search_metric", "nws")

        if args.luwian:
            luw_result = reverse_root_search(
                args.reverse, max_distance=args.max_dist, top_n=top,
                distances=LUWIAN_DISTANCES, guttural_transparent=False,
            )
            for m in luw_result["matches"]:
                m["search_metric"] = "luwian"
            result = _merge_reverse_results(result, luw_result)

        if args.egyptian:
            egy_result = reverse_root_search(
                args.reverse, max_distance=args.max_dist, top_n=top,
                distances=EGYPTIAN_DISTANCES, guttural_transparent=True,
            )
            for m in egy_result["matches"]:
                m["search_metric"] = "egyptian"
            result = _merge_reverse_results(result, egy_result)

        if args.arabian:
            # Harding 1971 names whose match_keys sit near the root skeleton
            root_skel = _normalize_root(args.reverse)
            arabian = _search_arabian_names(root_skel, top)
            for m in arabian:
                m["search_metric"] = "arabian"
                m.setdefault("word", m["root"])
            result.setdefault("contact_matches", {})["arabian"] = arabian

        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_reverse_table(result))
            for m in result.get("contact_matches", {}).get("arabian", []):
                theo = m.get("theophoric")
                theo_s = f"  theophoric: {theo['root']}+{theo['deity']}" if theo else ""
                gloss = f"  '{m['meaning']}'" if m.get("meaning") else ""
                print(f"  ARABIAN {m['root']:<14} d={m['distance']:<5} "
                      f"{m['language']:<28} {m['source']}{gloss}{theo_s}")
        return

    if not args.transliteration:
        parser.error("transliteration is required (or use --build-cache / --reverse)")

    if args.skeleton:
        skel = extract_skeleton(args.transliteration)
        cv = extract_full(args.transliteration)
        print(f"Skeleton: {skel}")
        cv_str = " ".join(f"{c or ''}{v}" for c, v in cv)
        print(f"CV:       {cv_str}")
        return

    result = search_cognates(
        args.transliteration, top_n=args.top, use_cache=not args.no_cache,
        include_luwian=args.luwian,
        include_egyptian=args.egyptian,
        include_ugaritic=args.ugaritic,
        include_amorite=args.amorite,
        include_greek=args.greek,
        include_hebrew=args.hebrew,
        include_aramaic=args.aramaic,
        include_geez=args.geez,
        include_south_arabian=args.south_arabian,
        include_arabian=args.arabian,
        verb_lens=args.verb_lens,
        historical_lens=args.historical_lens,
        include_akkadian=args.akkadian,
    )

    if args.all_readings:
        poly = extract_skeleton_polyphonic(args.transliteration)
        alt_results = []
        for alt_skel, notes in poly:
            if notes and alt_skel != result["skeleton"]:
                alt_search = _search_proto_semitic(alt_skel, args.top)
                alt_results.append({
                    "skeleton": alt_skel,
                    "notes": notes,
                    "matches": alt_search,
                })
            elif notes and alt_skel == result["skeleton"]:
                alt_results.append({
                    "skeleton": alt_skel,
                    "notes": notes,
                    "matches": [],
                })
        if alt_results:
            result["alternative_readings"] = alt_results

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_table(result))
        if args.all_readings and result.get("alternative_readings"):
            print()
            print("Alternative Readings:")
            print("-" * 76)
            for alt in result["alternative_readings"]:
                print(f"\n  Skeleton: {alt['skeleton']}")
                for n in alt["notes"]:
                    print(f"    → {n}")
                if alt["matches"]:
                    for m in alt["matches"]:
                        print(f"    {m['method']:<16} {m['root']:<20} {m['meaning']:<30} {m['distance']:>6.3f}")


if __name__ == "__main__":
    sys.exit(main())
