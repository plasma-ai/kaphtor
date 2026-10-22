#!/usr/bin/env python3
"""Analyze single-sign logographic abbreviation candidates in Linear A.

v3 pipeline (17 sections): pictographic ancestry, configurational category,
Linear B cross-script, contextual attestation, root skeleton matching,
site prior, contact lexicon, phrase role, multilingual roots, successor
entropy, positional grammar, diachronic, LB slot validation, phonetic
complement, graphic disambiguation, complementary distribution, commodity
community → composite verdict.

v2 pipeline (15 sections): as above minus configurational_category and
graphic_disambiguation. v1 pipeline (4 sections): pictographic, linear_b,
context, root.

Configurational category taxonomy: Salgarella 2022, "Mix and Match:
A Combinatory (Re-)Classification of Linear A Signs," TALANTA 54.
Graphic disambiguation principle: Salgarella, Bellinato & Ferrara 2025,
"On Aegean Spices," Kadmos 64.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core import data_cache
from ..core.phonetics import EGYPTIAN_DISTANCES, LUWIAN_DISTANCES, weighted_levenshtein
from ..core.skeleton import SIGN_DECOMPOSITION, extract_skeleton
from ..paths import LINEAR_A_DATA, NotInCheckout

try:
    from ..core.site_profiles import get_site_prior, load_site_profiles
except ImportError:  # pragma: no cover - defensive fallback for standalone use
    load_site_profiles = None  # type: ignore[assignment]
    get_site_prior = None  # type: ignore[assignment]

try:
    from ..core.contact_lexicon import load_all_contact_indexes, match_contact_term
except ImportError:  # pragma: no cover - defensive fallback for standalone use
    load_all_contact_indexes = None  # type: ignore[assignment]
    match_contact_term = None  # type: ignore[assignment]

try:
    from ..core.phrase_grammar import PhraseGrammar, load_phrase_grammar
except ImportError:  # pragma: no cover - defensive fallback for standalone use
    PhraseGrammar = None  # type: ignore[assignment]
    load_phrase_grammar = None  # type: ignore[assignment]

try:
    from ..core.linear_b_slots import load_slot_model, validate_candidate
except ImportError:  # pragma: no cover - defensive fallback for standalone use
    load_slot_model = None  # type: ignore[assignment]
    validate_candidate = None  # type: ignore[assignment]

DATA_DIR = LINEAR_A_DATA

SEPARATORS = {"", "\n", "\U00010101", "—", "–", "-", "𐝫"}
FRACTION_CHARS = frozenset("¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞⁄")

COMMODITY_KEYWORDS = frozenset({
    "grain", "oil", "wine", "fig", "garlic", "wheat", "barley", "bull",
    "sheep", "goat", "honey", "beer", "flax", "linen", "date", "fruit",
    "salt", "spice", "herb", "onion", "sesame", "olive", "measure",
    "vessel", "bowl", "jar", "cup", "pot", "cloth", "wool", "bronze",
    "copper", "silver", "gold", "tin", "cattle", "ox", "cow", "milk",
    "butter", "cheese", "bread", "flour", "meat", "fish", "plant",
    "seed", "reed", "wood", "ivory", "purple", "dye", "incense",
    "myrrh", "saffron", "almond", "pistachio", "terebinth",
})

CONTACT_COMMODITY_FIELDS = frozenset({
    "commodity", "agriculture", "food", "flora", "fauna", "pottery_vessel",
})

MULTILINGUAL_LANGUAGES = ("NWS", "Egyptian", "Luwian", "Hurrian")

FUNCTION_WORD_CATEGORIES = {"particle", "conjunction", "preposition",
                             "demonstrative", "presentative"}

MULTI_SIGN_LOGOGRAMS = {"GRA", "OLE", "VIN", "FIC", "CYP", "AROM",
                         "OLIV", "CAP", "SUS", "BOS", "OVI", "CER",
                         "EQU", "VIR"}

ROOT_VOWELS = frozenset("aeiouāēīōūVăĕĭŏŭáéíóúàèìòù")

SECTION_CALIBRATION_KEY: dict[str, str] = {
    "context": "standalone_count",
    "successor_entropy": "window_class_entropy",
    "site_prior": "site_concentration",
    "positional_grammar": "std_position",
}
DEFAULT_SECTION_WEIGHT = 1.0
CALIBRATED_PROBABLE_THRESHOLD = 4.0
CALIBRATED_CANDIDATE_THRESHOLD = 2.0

V1_SECTIONS = frozenset({"pictographic", "linear_b", "context", "root"})
V2_SECTIONS = frozenset({
    "pictographic", "linear_b", "context", "root",
    "site_prior", "contact", "phrase_role", "multilingual_roots",
    "successor_entropy", "positional_grammar", "diachronic", "lb_slot",
    "phonetic_complement", "complementary_dist", "commodity_community",
})

_AUTO: object = object()


# ── Data loading ──────────────────────────────────────────────────────

def load_registry() -> dict:
    path = DATA_DIR / "sign-registry.json"
    if not path.exists():
        return {"signs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def build_indices(signs: list[dict]) -> tuple[dict, dict]:
    by_ab: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for sign in signs:
        ab = sign.get("ab_number", "")
        by_ab[ab] = sign
        name = sign.get("name", "").upper()
        if name:
            # On name collisions prefer the AB syllabogram over A-series signs
            # (fraction sign A701 is named "A" and must not shadow AB08 /a/)
            prev = by_name.get(name)
            if prev is None or (ab.startswith("AB") and not prev.get("ab_number", "").startswith("AB")):
                by_name[name] = sign
    return by_ab, by_name


def load_lb_undeciphered() -> dict:
    path = DATA_DIR / "linear_b_undeciphered_signs.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signs", {})


def load_lexicon_entries() -> dict[str, dict[str, Any]]:
    lex = data_cache.lexicon()
    entries: dict[str, dict[str, Any]] = {}
    for entry in lex.get("entries", []):
        word = entry.get("word")
        if isinstance(word, str) and word:
            entries[word] = entry
    return entries


def load_calibration() -> dict | None:
    path = DATA_DIR / "lb_calibration_thresholds.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: lb_calibration_thresholds.json exists but failed to parse: {exc}",
              file=sys.stderr)
        return None
    if not isinstance(data.get("features"), dict):
        print("warning: lb_calibration_thresholds.json missing 'features' dict",
              file=sys.stderr)
        return None
    return data


def calibration_weight(section_name: str, calibration: dict) -> float:
    feature_key = SECTION_CALIBRATION_KEY.get(section_name)
    if feature_key is None:
        return DEFAULT_SECTION_WEIGHT
    feat = calibration.get("features", {}).get(feature_key)
    if feat is None:
        return DEFAULT_SECTION_WEIGHT
    return feat.get("weight", DEFAULT_SECTION_WEIGHT)


def is_numeral(word: str) -> bool:
    compact = word.strip()
    if not compact:
        return False
    if any(ch.isalpha() for ch in compact):
        return False
    if compact.isdigit():
        return True
    return any(ch.isdigit() or ch in FRACTION_CHARS - {"⁄"} for ch in compact) and all(
        ch.isdigit() or ch in FRACTION_CHARS for ch in compact
    )


def has_fraction(word: str) -> bool:
    return any(ch in FRACTION_CHARS - {"⁄"} for ch in word)


def is_separator(word: Any) -> bool:
    return not isinstance(word, str) or word.strip() in SEPARATORS


def is_multi_sign_logogram(word: str) -> bool:
    base = word.split("+")[0].strip()
    return base in MULTI_SIGN_LOGOGRAMS


def resolve_sign_name(target: str, by_ab: dict, by_name: dict) -> tuple[str, str, dict | None]:
    """Return (display_name, ab_number, sign_entry)."""
    upper = target.upper().strip()
    if upper.startswith("*"):
        ab = "AB" + upper[1:]
        for candidate_ab in [ab, ab.replace("AB", "AB0"), ab.replace("AB", "AB00")]:
            if candidate_ab in by_ab:
                entry = by_ab[candidate_ab]
                name = entry.get("name", "").upper() or upper
                return name, candidate_ab, entry
        return upper, ab, None
    if upper in by_name:
        entry = by_name[upper]
        return upper, entry.get("ab_number", ""), entry
    for ab_num, entry in by_ab.items():
        if entry.get("name", "").upper() == upper:
            return upper, ab_num, entry
    sv = data_cache.sign_values()
    sv_entry = sv.get("signs", {}).get(upper)
    if isinstance(sv_entry, dict):
        ab = sv_entry.get("ab_number") or sv_entry.get("sign_number", "")
        if ab:
            reg_entry = by_ab.get(ab)
            return upper, ab, reg_entry
    return upper, "", None


def get_resolved_consonant(sign_name: str) -> str | None:
    sv = data_cache.sign_values()
    signs = sv.get("signs", {})
    upper = sign_name.upper()
    if upper in signs:
        entry = signs[upper]
        if isinstance(entry, dict) and entry.get("consonant"):
            return entry["consonant"]
    decomp = SIGN_DECOMPOSITION.get(upper)
    if decomp and decomp[0]:
        return decomp[0]
    return None


# ── Step 1: Pictographic Evidence ─────────────────────────────────────

BOTANICAL_WORDS = {"plant", "bulb", "garlic", "onion", "grain", "wheat",
                    "barley", "tree", "branch", "leaf", "flower", "seed",
                    "fruit", "fig", "olive", "vine", "reed"}
ANIMAL_WORDS = {"bull", "ox", "cow", "cattle", "goat", "sheep", "ram",
                 "pig", "horse", "donkey", "fish", "bird", "deer"}
VESSEL_WORDS = {"vessel", "cup", "bowl", "jar", "pot", "jug", "vase",
                 "amphora", "pithos", "tripod", "measure"}
HUMAN_WORDS = {"man", "woman", "person", "human", "figure", "head",
                "hand", "arm", "leg", "foot", "eye"}

def classify_pictograph(text: str | None) -> tuple[str, str]:
    """Return (classification, verdict) for a pictograph description."""
    if not text:
        return "none", "NEUTRAL"
    lower = text.lower()
    if any(w in lower for w in BOTANICAL_WORDS):
        return "botanical", "SUPPORTS"
    if any(w in lower for w in ANIMAL_WORDS):
        return "animal", "SUPPORTS"
    if any(w in lower for w in VESSEL_WORDS):
        return "vessel/measure", "SUPPORTS"
    if any(w in lower for w in HUMAN_WORDS):
        return "personnel", "WEAKENS"
    return "abstract/other", "NEUTRAL"


def analyze_pictographic(sign_entry: dict | None) -> dict:
    result: dict[str, Any] = {"verdict": "NEUTRAL", "score": 0}
    if not sign_entry:
        result["note"] = "Sign not found in registry"
        return result

    evo = sign_entry.get("evolution", {})
    sem = sign_entry.get("semantic_context", {})

    ch_data = evo.get("cretan_hieroglyphic", {})
    ancestor = ch_data.get("pictographic_ancestor")
    pictograph = sem.get("pictograph")
    cultic = sem.get("cultic_significance")

    result["ch_ancestor"] = ancestor
    result["pictograph"] = pictograph
    result["cultic"] = cultic

    text = pictograph or ancestor
    if not text:
        result["note"] = "No pictographic data in registry"
        return result

    classification, verdict = classify_pictograph(text)
    result["classification"] = classification
    result["verdict"] = verdict
    result["score"] = 1 if verdict == "SUPPORTS" else (-1 if verdict == "WEAKENS" else 0)
    return result


# ── Step 1b: Configurational Category (Salgarella 2022) ──────────────

CONFIGURATIONAL_LABELS = {
    "juxtaposed_different_size": "Juxtaposed, different size",
    "juxtaposed_same_size": "Juxtaposed, same size",
    "ligatured_incorporated": "Ligatured, incorporated",
    "ligatured_fused": "Ligatured, fused",
}

KNOWN_COMPOSITE_CATEGORIES: dict[str, dict[str, str]] = {
    "A646": {
        "category": "ligatured_incorporated",
        "base": "A341",
        "acrophonic": "PI",
        "source": "Salgarella et al. 2025",
    },
    "A559": {
        "category": "ligatured_fused",
        "base": "MA",
        "acrophonic": "RU",
        "source": "Salgarella 2022",
    },
}


def _parse_plus_components(sign_name: str) -> tuple[str, str] | None:
    upper = sign_name.upper()
    if "+" not in upper:
        return None
    parts = upper.split("+", 1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return None


def _is_gorila_composite(sign_name: str) -> bool:
    upper = sign_name.upper()
    if upper.startswith("A") and upper[1:].isdigit():
        num = int(upper[1:])
        return 500 <= num <= 664
    return False


def analyze_configurational_category(sign_name: str) -> dict[str, Any]:
    """Classify composite sign structure per Salgarella 2022 taxonomy."""
    upper = sign_name.upper()

    if upper in KNOWN_COMPOSITE_CATEGORIES:
        known = KNOWN_COMPOSITE_CATEGORIES[upper]
        cat = known["category"]
        return {
            "is_composite": True,
            "category": cat,
            "category_label": CONFIGURATIONAL_LABELS.get(cat, cat),
            "base": known.get("base"),
            "acrophonic": known.get("acrophonic"),
            "source": known.get("source", ""),
            "verdict": "SUPPORTS",
            "score": 1,
            "note": f"Known composite: {known.get('base', '?')}+{known.get('acrophonic', '?')} ({CONFIGURATIONAL_LABELS.get(cat, cat)})",
        }

    plus_parts = _parse_plus_components(upper)
    if plus_parts:
        base, attached = plus_parts
        if base in MULTI_SIGN_LOGOGRAMS:
            return {
                "is_composite": True,
                "category": "ligatured_incorporated",
                "category_label": CONFIGURATIONAL_LABELS["ligatured_incorporated"],
                "base": base,
                "acrophonic": attached,
                "source": "corpus notation",
                "verdict": "SUPPORTS",
                "score": 1,
                "note": f"Plus-notation composite: {base}+{attached}",
            }
        return {
            "is_composite": True,
            "category": "unknown",
            "category_label": "Unknown (plus-notation)",
            "base": base,
            "acrophonic": attached,
            "source": "corpus notation",
            "verdict": "NEUTRAL",
            "score": 0,
            "note": f"Plus-notation but base {base} not a known logogram",
        }

    sv = data_cache.sign_values()
    logograms = sv.get("logograms", {})
    if upper in logograms:
        entry = logograms[upper]
        lv = entry.get("logographic_value", {})
        reading = lv.get("reading", entry.get("commodity", ""))
        if isinstance(reading, str) and "+" in reading:
            parts = reading.split("+", 1)
            return {
                "is_composite": True,
                "category": "ligatured_incorporated",
                "category_label": CONFIGURATIONAL_LABELS["ligatured_incorporated"],
                "base": parts[0].strip(),
                "acrophonic": parts[1].strip() if len(parts) > 1 else None,
                "source": "sign_values.json",
                "verdict": "SUPPORTS",
                "score": 1,
                "note": f"Composite reading from sign_values: {reading}",
            }

    if _is_gorila_composite(upper):
        return {
            "is_composite": True,
            "category": "unclassified",
            "category_label": "GORILA composite (unclassified)",
            "base": None,
            "acrophonic": None,
            "source": "GORILA range A500-A664",
            "verdict": "NEUTRAL",
            "score": 0,
            "note": f"{upper} is in GORILA composite range but decomposition unknown",
        }

    return {
        "is_composite": False,
        "category": None,
        "category_label": None,
        "base": None,
        "acrophonic": None,
        "verdict": "NEUTRAL",
        "score": 0,
        "note": "Not a composite sign",
    }


# ── Step 2: Linear B Cross-Script ─────────────────────────────────────

def analyze_linear_b(sign_entry: dict | None, ab_number: str) -> dict:
    result: dict[str, Any] = {"verdict": "NEUTRAL", "score": 0}
    lb_signs = load_lb_undeciphered()

    lb_num = None
    if sign_entry:
        evo = sign_entry.get("evolution", {})
        lb_data = evo.get("linear_b", {})
        lb_num = lb_data.get("sign_number")

    if not lb_num and ab_number:
        num = ab_number.replace("AB", "").strip()
        lb_num = f"*{num}"

    if not lb_num:
        result["note"] = "No Linear B cognate identified"
        return result

    result["lb_sign"] = lb_num

    if lb_num in lb_signs:
        lb_entry = lb_signs[lb_num]
        attests = lb_entry.get("total_attestations", 0)
        result["lb_undeciphered"] = True
        result["lb_attestations"] = attests
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = f"Undeciphered in LB ({attests} attestations) — phoneme absent from Greek"
    else:
        result["lb_undeciphered"] = False
        result["note"] = f"LB {lb_num} is deciphered (standard syllabary)"
    return result


# ── Step 3: Contextual Attestation ────────────────────────────────────

def analyze_context(sign_name: str, lexicon: dict[str, dict]) -> dict:
    corpus = data_cache.corpus()
    upper = sign_name.upper()

    known_logograms: set[str] = set()
    for word, entry in lexicon.items():
        if "-" not in word and len(word) <= 3 and not word.isdigit():
            cat = entry.get("category", "") or entry.get("semantic_field", "")
            if cat not in FUNCTION_WORD_CATEGORIES:
                known_logograms.add(word.upper())

    hits: list[dict] = []
    site_counter: Counter[str] = Counter()
    tablet_counter: Counter[str] = Counter()
    logogram_neighbors: Counter[str] = Counter()
    numeric_followers = 0
    fraction_followers = 0

    for tid, tablet in corpus.items():
        words = tablet.get("transliteratedWords", [])
        site = tablet.get("site", "unknown")
        for i, w in enumerate(words):
            if not isinstance(w, str):
                continue
            ws = w.strip()
            if ws.upper() != upper:
                continue
            if "-" in ws or "+" in ws:
                continue
            if is_numeral(ws) or is_separator(ws) or is_multi_sign_logogram(ws):
                continue

            hit: dict[str, Any] = {"tablet": tid, "position": i, "site": site}
            window = []
            for j in range(max(0, i - 3), min(len(words), i + 4)):
                if j != i:
                    token = words[j] if isinstance(words[j], str) else str(words[j])
                    window.append(token.strip())
            hit["window"] = window

            next_token = None
            for j in range(i + 1, min(len(words), i + 4)):
                t = words[j] if isinstance(words[j], str) else ""
                t = t.strip()
                if is_separator(t) or not t:
                    continue
                next_token = t
                break

            if next_token and is_numeral(next_token):
                numeric_followers += 1
                if has_fraction(next_token):
                    fraction_followers += 1

            for j in range(max(0, i - 3), min(len(words), i + 4)):
                if j == i:
                    continue
                t = words[j] if isinstance(words[j], str) else ""
                t = t.strip().upper()
                if t in known_logograms and t != upper:
                    logogram_neighbors[t] += 1

            hits.append(hit)
            site_counter[site] += 1
            tablet_counter[tid] += 1

    total = len(hits)
    result: dict[str, Any] = {
        "total": total,
        "tablets": len(tablet_counter),
        "sites": len(site_counter),
        "site_distribution": dict(site_counter.most_common()),
        "tablet_list": sorted(tablet_counter.keys()),
        "numeric_followers": numeric_followers,
        "fraction_followers": fraction_followers,
        "logogram_neighbors": dict(logogram_neighbors.most_common(10)),
        "hits": hits,
    }

    if total < 3:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = f"Only {total} standalone occurrence(s) — insufficient data"
    elif fraction_followers > 0:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = "Fractional quantities rule out personnel — commodity confirmed"
    elif total > 0 and numeric_followers / total >= 0.7:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = f"{numeric_followers}/{total} ({numeric_followers*100//total}%) followed by numerals"
    elif len(logogram_neighbors) >= 2:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = f"Co-occurs with {len(logogram_neighbors)} other logograms"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Standalone but weak contextual signal"

    return result


# ── Step 4: Root Skeleton Matching ────────────────────────────────────

def analyze_roots(sign_name: str, lexicon: dict[str, dict], top_n: int = 5) -> dict:
    consonant = get_resolved_consonant(sign_name)
    if not consonant:
        skeleton = extract_skeleton(sign_name.upper())
        consonant = skeleton if skeleton else None

    result: dict[str, Any] = {"consonant": consonant, "candidates": []}

    if not consonant:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Could not extract consonant from sign"
        return result

    result["single_consonant"] = len(consonant) == 1

    assigned_roots: set[str] = set()
    for word, entry in lexicon.items():
        if "-" not in word and len(word) <= 3:
            root = entry.get("root", "")
            if root:
                assigned_roots.add(root)

    roots = data_cache.semitic_roots()
    candidates: list[dict] = []

    for root_entry in roots:
        root_str = root_entry.get("root", root_entry.get("Proto-Semitic", ""))
        if not root_str:
            continue

        root_clean = root_str.strip("*- ")
        root_consonants = "".join(ch for ch in root_clean if ch not in ROOT_VOWELS)
        if not root_consonants or root_consonants[0] != consonant[0]:
            continue

        if root_str in assigned_roots or root_clean in assigned_roots:
            continue

        meaning = root_entry.get("meaning", root_entry.get("Meaning", "")).lower().strip("'\"")
        if not any(kw in meaning for kw in COMMODITY_KEYWORDS):
            continue

        dist = weighted_levenshtein(consonant, root_consonants, guttural_transparent=True)

        candidates.append({
            "root": root_str,
            "meaning": root_entry.get("meaning", root_entry.get("Meaning", "")),
            "language": root_entry.get("language", "Proto-Semitic"),
            "distance": round(dist, 2),
        })

    candidates.sort(key=lambda c: c["distance"])
    result["candidates"] = candidates[:top_n]

    if candidates:
        best = candidates[0]
        if len(consonant) == 1:
            result["verdict"] = "NEUTRAL"
            result["score"] = 0
            result["note"] = "Single-consonant skeleton — weak discriminator"
        elif best["distance"] <= 0.3:
            result["verdict"] = "SUPPORTS"
            result["score"] = 1
            result["note"] = f"Best match: {best['root']} \"{best['meaning']}\" (d={best['distance']})"
        else:
            result["verdict"] = "NEUTRAL"
            result["score"] = 0
            result["note"] = f"Best match distant: {best['root']} (d={best['distance']})"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "No commodity-relevant roots found"

    return result


def _neutral(note: str, **extra: Any) -> dict:
    result: dict[str, Any] = {"verdict": "NEUTRAL", "score": 0}
    result.update(extra)
    result["note"] = note
    return result


def analyze_site_prior(site_distribution: dict[str, int]) -> dict:
    result: dict[str, Any] = {
        "verdict": "NEUTRAL",
        "score": 0,
        "weighted_nws_prior": 0.0,
        "site_priors": {},
    }
    if not site_distribution:
        result["note"] = "No site distribution available"
        return result
    if load_site_profiles is None or get_site_prior is None:
        result["note"] = "Site profile loader unavailable"
        return result

    try:
        profiles = load_site_profiles()
        total = sum(count for count in site_distribution.values() if count > 0)
        if total <= 0:
            result["note"] = "No positive site attestation counts"
            return result
        weighted = 0.0
        site_priors: dict[str, float] = {}
        for site, count in site_distribution.items():
            if count <= 0:
                continue
            prior = float(get_site_prior(site, "NWS", profiles))
            site_priors[site] = prior
            weighted += prior * count
        weighted_nws_prior = weighted / total
    except Exception as exc:  # noqa: BLE001 — a section degrades to neutral, never stops the report
        result["note"] = f"Site profiles unavailable: {exc}"
        return result

    result["weighted_nws_prior"] = round(weighted_nws_prior, 3)
    result["site_priors"] = site_priors
    if weighted_nws_prior >= 0.45:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = "Weighted site distribution favors NWS"
    elif weighted_nws_prior < 0.25:
        result["verdict"] = "WEAKENS"
        result["score"] = -1
        result["note"] = "Weighted site distribution is weak for NWS"
    else:
        result["note"] = "Weighted site distribution is neutral"
    return result


def _semantic_fields(entry: dict[str, Any] | None) -> list[str]:
    if not entry:
        return []
    raw = (
        entry.get("semantic_field")
        or entry.get("semantic_domain")
        or entry.get("Category")
        or []
    )
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, list):
        return [str(part).strip() for part in raw if str(part).strip()]
    return []


def _build_contact_id_index(
    indexes: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, dict[str, Any]]:
    return {
        e.get("id"): e
        for idx in indexes.values()
        for entries in idx.values()
        for e in entries
        if e.get("id")
    }


def _find_contact_entry(
    indexes: dict[str, dict[str, list[dict[str, Any]]]],
    entry_id: str,
    _cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if _cache is not None:
        return _cache.get(entry_id)
    for index in indexes.values():
        for entries in index.values():
            for entry in entries:
                if entry.get("id") == entry_id:
                    return entry
    return None


def analyze_contact_lexicon(sign_name: str) -> dict:
    consonant = get_resolved_consonant(sign_name)
    if not consonant:
        skeleton = extract_skeleton(sign_name.upper())
        consonant = skeleton if skeleton else None
    if not consonant:
        return _neutral("Could not extract consonant from sign", matches=[])
    if load_all_contact_indexes is None or match_contact_term is None:
        return _neutral("Contact lexicon loader unavailable", matches=[])

    try:
        indexes = load_all_contact_indexes()
    except Exception as exc:  # noqa: BLE001 — a section degrades to neutral, never stops the report
        return _neutral(f"Contact lexicons unavailable: {exc}", matches=[])

    language_names = {
        "egyptian": "Egyptian",
        "anatolian": "Anatolian",
        "hurrian": "Hurrian",
        "canaanite": "Canaanite",
    }
    id_index = _build_contact_id_index(indexes)
    matches: list[dict[str, Any]] = []
    commodity_match = False
    for key in sorted(indexes):
        language = language_names.get(key, key.title())
        try:
            match = match_contact_term(consonant, language, indexes)
        except Exception:  # noqa: BLE001, S112 — one language's matcher failing leaves the others
            continue
        if not match.get("matched"):
            continue
        entry = _find_contact_entry(indexes, match.get("entry_id", ""), _cache=id_index)
        fields = _semantic_fields(entry)
        match_record = dict(match)
        match_record["semantic_field"] = fields
        matches.append(match_record)
        if CONTACT_COMMODITY_FIELDS & {field.lower() for field in fields}:
            commodity_match = True

    if commodity_match:
        return {
            "verdict": "SUPPORTS",
            "score": 1,
            "matches": matches,
            "note": "Commodity-relevant contact lexicon match found",
        }
    return {
        "verdict": "NEUTRAL",
        "score": 0,
        "matches": matches,
        "note": "No commodity-relevant contact lexicon match found",
    }


def analyze_phrase_role(sign_name: str) -> dict:
    if PhraseGrammar is None or load_phrase_grammar is None:
        return _neutral("Phrase grammar unavailable", role=None)

    try:
        grammar = load_phrase_grammar(DATA_DIR)
    except Exception:  # noqa: BLE001 — no phrase grammar data: an empty grammar
        # No phrase grammar data files yet — stub with empty grammar
        grammar = PhraseGrammar({}, [])

    try:
        role = grammar.get_role(sign_name.upper())
    except Exception as exc:  # noqa: BLE001 — a section degrades to neutral, never stops the report
        return _neutral(f"Phrase grammar unavailable: {exc}", role=None)

    if not role:
        return _neutral("No known phrase role for sign", role=None)
    if role in {"ACCOUNTING_TOTAL", "VERB_ACTION"}:
        return {
            "verdict": "WEAKENS",
            "score": -1,
            "role": role,
            "note": "Known function-word phrase role",
        }
    if role == "COMMODITY_LABEL":
        return {
            "verdict": "SUPPORTS",
            "score": 1,
            "role": role,
            "note": "Known commodity-label phrase role",
        }
    return {
        "verdict": "NEUTRAL",
        "score": 0,
        "role": role,
        "note": "Phrase role is not diagnostic for logographic commodity status",
    }


def _root_consonants(root_str: str) -> str:
    root_clean = root_str.strip("*- ")
    return "".join(ch for ch in root_clean if ch not in ROOT_VOWELS)


def _meaning(entry: dict[str, Any]) -> str:
    return str(entry.get("meaning", entry.get("Meaning", "")))


def _root_value(entry: dict[str, Any], language: str) -> str:
    if language == "NWS":
        return str(entry.get("root", entry.get("Proto-Semitic", "")))
    return str(
        entry.get("Consonantal_Root")
        or entry.get("root")
        or entry.get("Proto-Luwian")
        or entry.get("Middle_Egyptian")
        or entry.get("Hurrian")
        or ""
    )


def _lemma(entry: dict[str, Any], language: str) -> str:
    fields = {
        "NWS": ("Proto-Semitic", "root"),
        "Egyptian": ("Middle_Egyptian", "Transliteration_Unicode"),
        "Luwian": ("Proto-Luwian",),
        "Hurrian": ("Hurrian",),
    }.get(language, ())
    for field in fields:
        value = entry.get(field)
        if value:
            return str(value)
    return ""


def _search_language_roots(
    consonant: str,
    roots: list[dict[str, Any]],
    language: str,
    distances: dict[tuple[str, str], float] | None,
    guttural_transparent: bool,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for root_entry in roots:
        root_str = _root_value(root_entry, language)
        if not root_str:
            continue
        root_consonants = _root_consonants(root_str)
        if not root_consonants or root_consonants[0] != consonant[0]:
            continue
        meaning = _meaning(root_entry).lower().strip("'\"")
        if not any(kw in meaning for kw in COMMODITY_KEYWORDS):
            continue
        dist = weighted_levenshtein(
            consonant,
            root_consonants,
            distances=distances,
            guttural_transparent=guttural_transparent,
        )
        candidates.append({
            "root": root_str,
            "lemma": _lemma(root_entry, language),
            "meaning": _meaning(root_entry),
            "language": language,
            "distance": round(dist, 2),
        })
    candidates.sort(key=lambda c: c["distance"])
    return candidates[:top_n]


def _weighted_language_posterior(site_distribution: dict[str, int]) -> dict[str, float]:
    posterior = {language: 0.0 for language in MULTILINGUAL_LANGUAGES}
    if not site_distribution or load_site_profiles is None or get_site_prior is None:
        return posterior
    try:
        profiles = load_site_profiles()
        total = sum(count for count in site_distribution.values() if count > 0)
        if total <= 0:
            return posterior
        profile_keys = {
            "NWS": "NWS",
            "Egyptian": "Egyptian",
            "Luwian": "Luwian",
            "Hurrian": "Hurrian_name",
        }
        for site, count in site_distribution.items():
            if count <= 0:
                continue
            for language, profile_key in profile_keys.items():
                posterior[language] += float(get_site_prior(site, profile_key, profiles)) * count
        for language, weight in posterior.items():
            posterior[language] = round(weight / total, 3)
    except (FileNotFoundError, ValueError, KeyError, TypeError):
        return {language: 0.0 for language in MULTILINGUAL_LANGUAGES}
    return posterior


def analyze_multilingual_roots(
    sign_name: str,
    site_distribution: dict[str, int] | None = None,
) -> dict:
    consonant = get_resolved_consonant(sign_name)
    if not consonant:
        skeleton = extract_skeleton(sign_name.upper())
        consonant = skeleton if skeleton else None

    language_posterior = _weighted_language_posterior(site_distribution or {})
    if not consonant:
        return _neutral(
            "Could not extract consonant from sign",
            candidates=[],
            language_posterior=language_posterior,
        )

    try:
        semitic_best = _search_language_roots(
            consonant,
            data_cache.semitic_roots(),
            "NWS",
            None,
            True,
            top_n=1,
        )
        search_specs = [
            ("Egyptian", data_cache.egyptian_roots(), EGYPTIAN_DISTANCES, True),
            ("Luwian", data_cache.luwian_roots(), LUWIAN_DISTANCES, False),
            ("Hurrian", data_cache.hurrian_roots(), None, False),
        ]
        candidates: list[dict[str, Any]] = []
        for language, roots, distances, guttural_transparent in search_specs:
            candidates.extend(_search_language_roots(
                consonant,
                roots,
                language,
                distances,
                guttural_transparent,
            ))
    except Exception as exc:  # noqa: BLE001 — a section degrades to neutral, never stops the report
        return _neutral(
            f"Multilingual root databases unavailable: {exc}",
            candidates=[],
            language_posterior=language_posterior,
        )

    candidates.sort(key=lambda c: c["distance"])
    semitic_distance = semitic_best[0]["distance"] if semitic_best else float("inf")
    supporting = [
        c for c in candidates
        if c["distance"] < semitic_distance
        and language_posterior.get(c["language"], 0.0) >= language_posterior.get("NWS", 0.0)
        and language_posterior.get(c["language"], 0.0) > 0.0
    ]
    if supporting:
        best = supporting[0]
        return {
            "verdict": "SUPPORTS",
            "score": 1,
            "candidates": candidates[:9],
            "language_posterior": language_posterior,
            "note": (
                f"{best['language']} match out-scores NWS and is supported by site prior"
            ),
        }
    return {
        "verdict": "NEUTRAL",
        "score": 0,
        "candidates": candidates[:9],
        "language_posterior": language_posterior,
        "note": "No non-Semitic commodity match out-scores NWS with supporting site prior",
    }


TOKEN_CLASSES = ("numeral", "fraction", "logogram", "syllabic_word", "separator", "end")
PERIOD_ORDER = ("MMII", "MMIII", "LMIA", "LMIB")
FRACTION_VALUES = {
    "¼": 0.25,
    "½": 0.5,
    "¾": 0.75,
    "⅐": 1 / 7,
    "⅑": 1 / 9,
    "⅒": 0.1,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "⅕": 0.2,
    "⅖": 0.4,
    "⅗": 0.6,
    "⅘": 0.8,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
    "⅛": 0.125,
    "⅜": 0.375,
    "⅝": 0.625,
    "⅞": 0.875,
}


def _token_text(token: Any) -> str:
    if isinstance(token, str):
        return token.strip()
    return str(token).strip()


def _classify_token(token: Any, is_end: bool = False) -> str:
    if is_end:
        return "end"
    if is_separator(token):
        return "separator"
    text = _token_text(token)
    if has_fraction(text):
        return "fraction"
    if is_numeral(text):
        return "numeral"
    if is_multi_sign_logogram(text):
        return "logogram"
    return "syllabic_word"


def _entropy(distribution: Counter[str]) -> float:
    total = sum(distribution.values())
    if total <= 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total)
                for count in distribution.values() if count > 0)


def _numeric_value(token: Any) -> float | None:
    text = _token_text(token)
    if not is_numeral(text):
        return None
    if "⁄" in text:
        numerator, denominator = text.split("⁄", 1)
        numerator_digits = _unicode_digits(numerator)
        denominator_digits = _unicode_digits(denominator)
        if numerator_digits and denominator_digits and int(denominator_digits) != 0:
            return int(numerator_digits) / int(denominator_digits)
    digit_part = _unicode_digits(text)
    value = float(digit_part) if digit_part else 0.0
    for ch in text:
        value += FRACTION_VALUES.get(ch, 0.0)
    return value


def _unicode_digits(text: str) -> str:
    digits: list[str] = []
    for ch in text:
        if not ch.isdigit():
            continue
        try:
            digits.append(str(unicodedata.digit(ch)))
        except (TypeError, ValueError):
            continue
    return "".join(digits)


def _tablet_words(
    corpus: dict[str, dict[str, Any]],
    tablet_id: str,
) -> list[Any]:
    tablet = corpus.get(tablet_id)
    if not isinstance(tablet, dict):
        return []
    words = tablet.get("transliteratedWords", [])
    if not isinstance(words, list):
        return []
    return words


def _following_numeric_value(words: list[Any], start: int) -> float | None:
    for token in words[start + 1:]:
        if is_separator(token):
            continue
        return _numeric_value(token)
    return None


def _preceding_numeric_values(words: list[Any], end: int) -> list[float]:
    values: list[float] = []
    for token in words[:end]:
        value = _numeric_value(token)
        if value is not None:
            values.append(value)
    return values


def analyze_successor_entropy(
    hits: list[dict[str, Any]],
    corpus: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not hits:
        return _neutral(
            "No context hits available for entropy analysis",
            successor_entropy=0.0,
            predecessor_entropy=0.0,
            successor_distribution={},
            predecessor_distribution={},
        )

    successor_distribution: Counter[str] = Counter()
    predecessor_distribution: Counter[str] = Counter()
    usable_hits = 0

    for hit in hits:
        tablet_id = str(hit.get("tablet", ""))
        position = hit.get("position")
        if not isinstance(position, int):
            continue
        words = _tablet_words(corpus, tablet_id)
        if not words or position < 0 or position >= len(words):
            continue
        usable_hits += 1
        if position + 1 >= len(words):
            successor_distribution["end"] += 1
        else:
            successor_distribution[_classify_token(words[position + 1])] += 1
        if position == 0:
            predecessor_distribution["end"] += 1
        else:
            predecessor_distribution[_classify_token(words[position - 1])] += 1

    if usable_hits == 0:
        return _neutral(
            "No usable tablet positions for entropy analysis",
            successor_entropy=0.0,
            predecessor_entropy=0.0,
            successor_distribution={},
            predecessor_distribution={},
        )

    successor_entropy = _entropy(successor_distribution)
    predecessor_entropy = _entropy(predecessor_distribution)
    numeral_ratio = successor_distribution.get("numeral", 0) / usable_hits

    result: dict[str, Any] = {
        "successor_entropy": round(successor_entropy, 3),
        "predecessor_entropy": round(predecessor_entropy, 3),
        "successor_distribution": dict(successor_distribution),
        "predecessor_distribution": dict(predecessor_distribution),
    }
    if successor_entropy < 1.0 and numeral_ratio > 0.5:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = "Low successor entropy with numeral-dominated following class"
    elif successor_entropy > 2.0:
        result["verdict"] = "WEAKENS"
        result["score"] = -1
        result["note"] = "High successor entropy suggests unconstrained syntactic behavior"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Successor class entropy is not diagnostic"
    return result


def analyze_positional_grammar(
    hits: list[dict[str, Any]],
    corpus: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not hits:
        return _neutral(
            "No context hits available for positional analysis",
            mean_position=0.0,
            std_position=0.0,
            position_class="mixed",
            summation_matches=0,
            summation_mismatches=0,
        )

    positions: list[float] = []
    total_hits: list[tuple[list[Any], int, float]] = []
    for hit in hits:
        tablet_id = str(hit.get("tablet", ""))
        position = hit.get("position")
        if not isinstance(position, int):
            continue
        words = _tablet_words(corpus, tablet_id)
        if not words or position < 0 or position >= len(words):
            continue
        normalized = position / max(len(words) - 1, 1)
        positions.append(normalized)
        if normalized > 0.75:
            total_hits.append((words, position, normalized))

    if not positions:
        return _neutral(
            "No usable tablet positions for positional analysis",
            mean_position=0.0,
            std_position=0.0,
            position_class="mixed",
            summation_matches=0,
            summation_mismatches=0,
        )

    mean_position = sum(positions) / len(positions)
    variance = sum((pos - mean_position) ** 2 for pos in positions) / len(positions)
    std_position = math.sqrt(variance)

    if mean_position < 0.15:
        position_class = "header"
    elif 0.15 <= mean_position <= 0.75 and std_position < 0.3:
        position_class = "commodity"
    elif mean_position > 0.75:
        position_class = "total"
    else:
        position_class = "mixed"

    summation_matches = 0
    summation_mismatches = 0
    for words, position, _normalized in total_hits:
        following = _following_numeric_value(words, position)
        preceding = _preceding_numeric_values(words, position)
        if following is None or not preceding:
            continue
        preceding_average = sum(preceding) / len(preceding)
        if following > preceding_average:
            summation_matches += 1
        else:
            summation_mismatches += 1

    result: dict[str, Any] = {
        "mean_position": round(mean_position, 3),
        "std_position": round(std_position, 3),
        "position_class": position_class,
        "summation_matches": summation_matches,
        "summation_mismatches": summation_mismatches,
    }
    if position_class == "commodity" and std_position < 0.25:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = "Positions cluster in commodity slots"
    elif position_class in ("header", "total"):
        result["verdict"] = "WEAKENS"
        result["score"] = -1
        result["note"] = f"Positions cluster as {position_class} rather than commodity entries"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Positions are mixed or weakly clustered"
    return result


def analyze_diachronic(tablet_list: list[str]) -> dict[str, Any]:
    if not tablet_list:
        return _neutral(
            "No tablet attestations available for diachronic analysis",
            period_distribution={},
            lifespan_start=None,
            lifespan_end=None,
            dated_tablets=0,
            undated_tablets=0,
        )

    try:
        metadata = data_cache._load("inscription_dating_metadata")
    except Exception as exc:  # noqa: BLE001 — a section degrades to neutral, never stops the report
        return _neutral(
            f"Dating metadata unavailable: {exc}",
            period_distribution={},
            lifespan_start=None,
            lifespan_end=None,
            dated_tablets=0,
            undated_tablets=len(tablet_list),
        )
    if not isinstance(metadata, dict):
        return _neutral(
            "Dating metadata has unexpected structure",
            period_distribution={},
            lifespan_start=None,
            lifespan_end=None,
            dated_tablets=0,
            undated_tablets=len(tablet_list),
        )

    period_distribution: Counter[str] = Counter()
    dated_tablets = 0
    undated_tablets = 0
    for tablet_id in tablet_list:
        entry = metadata.get(tablet_id)
        period = ""
        if isinstance(entry, dict):
            period = str(entry.get("best_period_code", "")).strip()
        if period:
            dated_tablets += 1
            period_distribution[period] += 1
        else:
            undated_tablets += 1

    period_indexes = [
        PERIOD_ORDER.index(period)
        for period in period_distribution
        if period in PERIOD_ORDER
    ]
    lifespan_start = PERIOD_ORDER[min(period_indexes)] if period_indexes else None
    lifespan_end = PERIOD_ORDER[max(period_indexes)] if period_indexes else None

    result: dict[str, Any] = {
        "period_distribution": dict(period_distribution),
        "lifespan_start": lifespan_start,
        "lifespan_end": lifespan_end,
        "dated_tablets": dated_tablets,
        "undated_tablets": undated_tablets,
    }
    if dated_tablets < 2:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Insufficient dated attestations for diachronic signal"
    elif len(period_distribution) >= 2:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = "Attested across multiple periods"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Attested in a single dated period"
    return result


def analyze_lb_slot_validation(sign_name: str, ctx_hits: list[dict]) -> dict:
    """Validate candidate against Linear B administrative slot expectations."""
    if load_slot_model is None or validate_candidate is None:
        return {"verdict": "NEUTRAL", "score": 0, "note": "LB slot model unavailable"}

    ref_paths_file = DATA_DIR / "linear_b_reference_paths.json"
    corpus_path = None
    if ref_paths_file.exists():
        refs = json.loads(ref_paths_file.read_text(encoding="utf-8"))
        for key in ("documents_jsonl", "liber_documents"):
            if key in refs and Path(refs[key]).exists():
                corpus_path = Path(refs[key])
                break
    if corpus_path is None:
        fallbacks = [
            DATA_DIR / "linear_b_corpus" / "liber_linear_b_documents.jsonl",  # where linear_b_query.py reads it
            DATA_DIR / "liber_linear_b_documents.jsonl",
        ]
        for fb in fallbacks:
            if fb.exists():
                corpus_path = fb
                break
    if corpus_path is None:
        return {"verdict": "NEUTRAL", "score": 0, "note": "LB corpus file not found"}

    try:
        slot_model = load_slot_model(corpus_path)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        return {"verdict": "NEUTRAL", "score": 0, "note": f"Failed to build slot model: {exc}"}

    la_role = "COMMODITY_LABEL"
    positions = [
        h.get("position")
        for h in ctx_hits
        if isinstance(h.get("position"), (int, float))
    ]
    la_position = int(sorted(positions)[len(positions) // 2]) if positions else None
    if la_position is not None:
        la_position = min(la_position, 7)

    result = validate_candidate(
        word=sign_name,
        la_role=la_role,
        la_formula_family=None,
        la_position=la_position,
        slot_model=slot_model,
    )

    verdict_map = {
        "CONVERGENT": "SUPPORTS",
        "DIVERGENT": "WEAKENS",
        "NEUTRAL": "NEUTRAL",
        "INSUFFICIENT_DATA": "NEUTRAL",
    }
    score_map = {"SUPPORTS": 1, "WEAKENS": -1, "NEUTRAL": 0}
    mapped_verdict = verdict_map.get(result.get("verdict", "NEUTRAL"), "NEUTRAL")

    return {
        "verdict": mapped_verdict,
        "score": score_map[mapped_verdict],
        "lb_verdict": result.get("verdict", ""),
        "lb_domain": result.get("lb_domain", ""),
        "lb_position": result.get("lb_position"),
        "lb_rate": result.get("lb_rate_at_position"),
        "lb_bg_rate": result.get("lb_background_rate"),
        "strength": result.get("strength", ""),
        "note": result.get("explanation", ""),
    }


# ── Step 13: Phonetic Complement ─────────────────────────────────────

def _extract_root_onset(root_result: dict) -> str | None:
    candidates = root_result.get("candidates", [])
    if not candidates:
        return None
    root_str = candidates[0].get("root", "")
    root_clean = root_str.strip("*- ")
    consonants = "".join(ch for ch in root_clean if ch not in ROOT_VOWELS)
    return consonants[0] if consonants else None


def _is_compound_with_sign(token: str, sign: str) -> tuple[bool, str | None]:
    upper_sign = sign.upper()
    for sep in ("+", "-"):
        if sep not in token:
            continue
        parts = token.split(sep)
        if len(parts) != 2:
            continue
        left, right = parts[0].strip(), parts[1].strip()
        if left.upper() == upper_sign and right and right[0].isalpha():
            return True, right.upper()
        if right.upper() == upper_sign and left and left[0].isalpha():
            return True, left.upper()
    return False, None


def analyze_phonetic_complement(
    sign_name: str,
    root_result: dict,
    ctx_hits: list[dict],
    corpus: dict,
) -> dict[str, Any]:
    upper = sign_name.upper()
    root_onset = _extract_root_onset(root_result)

    lexicon = data_cache.lexicon()
    lex_consonant: str | None = None
    for entry in lexicon.get("entries", []):
        word = entry.get("word", "")
        if isinstance(word, str) and word.upper() == upper:
            reading = entry.get("reading", "")
            if reading:
                for ch in reading:
                    if ch.isalpha() and ch.lower() not in ROOT_VOWELS:
                        lex_consonant = ch.lower()
                        break
            break

    onset = root_onset or lex_consonant
    if not onset:
        return _neutral(
            "No root onset available for phonetic complement test",
            compounds=[], match_count=0, mismatch_count=0,
        )

    compounds: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for tid, tablet in corpus.items():
        for w in tablet.get("transliteratedWords", []):
            if not isinstance(w, str):
                continue
            ws = w.strip()
            is_compound, attached = _is_compound_with_sign(ws, upper)
            if not is_compound or not attached:
                continue
            key = (tid, ws)
            if key in seen:
                continue
            seen.add(key)

            decomp = SIGN_DECOMPOSITION.get(attached)
            syl_consonant = decomp[0] if decomp and decomp[0] else None
            if syl_consonant is None:
                continue

            match = syl_consonant.lower() == onset.lower()
            compounds.append({
                "tablet_id": tid,
                "compound_token": ws,
                "syllabogram": attached,
                "syllabogram_consonant": syl_consonant,
                "root_onset": onset,
                "match": match,
            })

    if not compounds:
        return _neutral(
            "No phonetic-complement compounds found in corpus",
            compounds=[], match_count=0, mismatch_count=0,
        )

    match_count = sum(1 for c in compounds if c["match"])
    mismatch_count = sum(1 for c in compounds if not c["match"])

    result: dict[str, Any] = {
        "compounds": compounds,
        "match_count": match_count,
        "mismatch_count": mismatch_count,
    }

    if match_count > 0 and mismatch_count == 0:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = f"{match_count} phonetic complement(s) confirm root onset /{onset}/"
    elif mismatch_count > match_count:
        result["verdict"] = "WEAKENS"
        result["score"] = -1
        result["note"] = f"{mismatch_count} mismatch(es) vs {match_count} match(es) — falsification signal"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = f"{match_count} match(es), {mismatch_count} mismatch(es) — inconclusive"
    return result


# ── Step 13b: Graphic Disambiguation (Salgarella et al. 2025) ────────

def analyze_graphic_disambiguation(
    sign_name: str,
    config_result: dict[str, Any],
    corpus: dict,
) -> dict[str, Any]:
    """Check if composite's full-spelling equivalent exists with different meaning.

    Salgarella et al. 2025: when the same phonetic string exists as both
    full-spelling and monogram/ligature, they denote different commodities.
    """
    if not config_result.get("is_composite"):
        return _neutral(
            "Not a composite — graphic disambiguation not applicable",
            full_spelling_found=False, composite_tablets=[], full_spelling_tablets=[],
        )

    base = config_result.get("base")
    acrophonic = config_result.get("acrophonic")
    if not base or not acrophonic:
        return _neutral(
            "Composite components unknown — cannot search for full-spelling equivalent",
            full_spelling_found=False, composite_tablets=[], full_spelling_tablets=[],
        )

    upper = sign_name.upper()
    composite_form = f"{base}+{acrophonic}".upper()
    composite_tablets: set[str] = set()
    full_spelling_tablets: set[str] = set()

    base_up = base.upper()
    acro_up = acrophonic.upper()
    full_spell_hyph = f"{base_up}-{acro_up}"

    for tid, tablet in corpus.items():
        words = tablet.get("transliteratedWords", [])
        for i, w in enumerate(words):
            if not isinstance(w, str):
                continue
            ws = w.strip().upper()
            if ws == upper or ws == composite_form:
                composite_tablets.add(tid)
            elif ws == full_spell_hyph:
                full_spelling_tablets.add(tid)
            elif ws == acro_up and i > 0:
                prev = words[i - 1]
                if isinstance(prev, str) and prev.strip().upper() == base_up:
                    full_spelling_tablets.add(tid)

    if not composite_tablets:
        return _neutral(
            f"Composite form {composite_form} not found in corpus",
            full_spelling_found=False,
            composite_tablets=sorted(composite_tablets),
            full_spelling_tablets=sorted(full_spelling_tablets),
        )

    if full_spelling_tablets:
        overlap = composite_tablets & full_spelling_tablets
        return {
            "verdict": "SUPPORTS",
            "score": 1,
            "full_spelling_found": True,
            "composite_tablets": sorted(composite_tablets),
            "full_spelling_tablets": sorted(full_spelling_tablets),
            "overlap_tablets": sorted(overlap),
            "note": (
                f"Both composite ({len(composite_tablets)} tablets) and full-spelling "
                f"({len(full_spelling_tablets)} tablets) coexist — "
                f"graphic disambiguation implies distinct commodities"
            ),
        }

    return _neutral(
        f"No full-spelling equivalent found for {base} {acrophonic}",
        full_spelling_found=False,
        composite_tablets=sorted(composite_tablets),
        full_spelling_tablets=[],
    )


# ── Step 14: Complementary Distribution ─────────────────────────────

def _fisher_exact_left(a: int, b: int, c: int, d: int) -> float:
    """One-tailed Fisher's exact test (left tail: P(X <= a))."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d
    p = 0.0
    lo = max(0, col1 - row2)
    hi = min(row1, col1)
    for x in range(lo, min(a, hi) + 1):
        lp = (
            math.lgamma(row1 + 1) + math.lgamma(row2 + 1)
            + math.lgamma(col1 + 1) + math.lgamma(col2 + 1)
            - math.lgamma(n + 1)
            - math.lgamma(x + 1) - math.lgamma(row1 - x + 1)
            - math.lgamma(col1 - x + 1) - math.lgamma(row2 - col1 + x + 1)
        )
        p += math.exp(lp)
    return min(p, 1.0)


def analyze_complementary_distribution(
    sign_name: str,
    corpus: dict,
) -> dict[str, Any]:
    upper = sign_name.upper()
    lexicon = data_cache.lexicon()

    full_forms: list[dict[str, Any]] = []
    for entry in lexicon.get("entries", []):
        word = entry.get("word", "")
        if not isinstance(word, str) or "-" not in word:
            continue
        parts = word.split("-")
        if parts[0].upper() != upper:
            continue
        if len(parts) < 2:
            continue
        full_forms.append({
            "word": word,
            "meaning": entry.get("meaning", ""),
            "reading": entry.get("reading", ""),
        })

    if not full_forms:
        return _neutral(
            "No multi-syllable lexicon forms starting with sign",
            full_forms=[], total_full_forms=0,
            significant_disjoint_count=0, co_occurrence_count=0,
        )

    sign_tablets: set[str] = set()
    for tid, tablet in corpus.items():
        for w in tablet.get("transliteratedWords", []):
            if not isinstance(w, str):
                continue
            ws = w.strip()
            if ws.upper() == upper and "-" not in ws and "+" not in ws:
                sign_tablets.add(tid)
                break

    all_tablet_ids = set(corpus.keys())
    results: list[dict[str, Any]] = []
    significant_disjoint = 0
    total_co_occurrence = 0

    for ff in full_forms:
        form_word = ff["word"]
        form_upper = form_word.upper()
        form_tablets: set[str] = set()
        for tid, tablet in corpus.items():
            for w in tablet.get("transliteratedWords", []):
                if not isinstance(w, str):
                    continue
                if w.strip().upper() == form_upper:
                    form_tablets.add(tid)
                    break

        if not form_tablets:
            continue

        co_occurrence = sign_tablets & form_tablets
        a = len(sign_tablets - form_tablets)
        b = len(co_occurrence)
        c = len(form_tablets - sign_tablets)
        d = len(all_tablet_ids) - len(sign_tablets | form_tablets)

        p_value = _fisher_exact_left(b, a, c, d)
        disjoint = b == 0 and p_value < 0.05

        total_co_occurrence += len(co_occurrence)
        if disjoint:
            significant_disjoint += 1

        results.append({
            "word": form_word,
            "meaning": ff["meaning"],
            "sign_tablet_count": len(sign_tablets),
            "form_tablet_count": len(form_tablets),
            "co_occurrence_count": len(co_occurrence),
            "p_value": round(p_value, 4),
            "disjoint": disjoint,
        })

    result: dict[str, Any] = {
        "full_forms": results,
        "total_full_forms": len(results),
        "significant_disjoint_count": significant_disjoint,
        "co_occurrence_count": total_co_occurrence,
    }

    if significant_disjoint > 0:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = (
            f"{significant_disjoint} full-form(s) show significant disjointness "
            f"(abbreviation signature)"
        )
    elif total_co_occurrence > significant_disjoint and results:
        result["verdict"] = "WEAKENS"
        result["score"] = -1
        result["note"] = (
            f"Sign and full-form co-occur on {total_co_occurrence} tablet(s) "
            f"— not an abbreviation"
        )
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "No significant abbreviation pattern detected"
    return result


# ── Step 15: Commodity Community ─────────────────────────────────────

def _build_logogram_cooccurrence(corpus: dict) -> dict[str, dict[str, float]]:
    tablet_tokens: dict[str, set[str]] = {}
    for tid, tablet in corpus.items():
        tokens: set[str] = set()
        for w in tablet.get("transliteratedWords", []):
            if not isinstance(w, str):
                continue
            ws = w.strip()
            if "-" in ws or "+" in ws:
                continue
            if is_numeral(ws) or is_separator(ws) or is_multi_sign_logogram(ws):
                continue
            if not ws.isalpha() or len(ws) > 3:
                continue
            tokens.add(ws.upper())
        if len(tokens) >= 2:
            tablet_tokens[tid] = tokens

    adjacency: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for tokens in tablet_tokens.values():
        token_list = sorted(tokens)
        for i, t1 in enumerate(token_list):
            for t2 in token_list[i + 1:]:
                adjacency[t1][t2] += 1.0
                adjacency[t2][t1] += 1.0

    pruned: dict[str, dict[str, float]] = {}
    for node, neighbors in adjacency.items():
        strong = {nb: w for nb, w in neighbors.items() if w >= 2.0}
        if strong:
            pruned[node] = strong
    return pruned


def _greedy_modularity(adjacency: dict[str, dict[str, float]]) -> dict[str, int]:
    nodes = sorted(adjacency)
    if not nodes:
        return {}
    total_weight = sum(sum(nb.values()) for nb in adjacency.values()) / 2.0
    if total_weight <= 0:
        return {n: i for i, n in enumerate(nodes)}

    community: dict[str, int] = {n: i for i, n in enumerate(nodes)}
    degree: dict[str, float] = {n: sum(adjacency.get(n, {}).values()) for n in nodes}

    comm_internal: Counter[int] = Counter()
    comm_total: Counter[int] = Counter()
    for n in nodes:
        comm_total[community[n]] += degree[n]
        for nb, w in adjacency.get(n, {}).items():
            if community[n] == community[nb]:
                comm_internal[community[n]] += w
    for c in comm_internal:
        comm_internal[c] /= 2.0

    improved = True
    iterations = 0
    while improved and iterations < 30:
        improved = False
        iterations += 1
        for node in nodes:
            cur = community[node]
            ki = degree[node]
            neighbor_comms: dict[int, float] = defaultdict(float)
            for nb, w in adjacency.get(node, {}).items():
                neighbor_comms[community[nb]] += w
            neighbor_comms.setdefault(cur, 0.0)

            ki_in_cur = neighbor_comms.get(cur, 0.0)
            sigma_cur = comm_total[cur] - ki
            remove_cost = ki_in_cur / total_weight - (sigma_cur * ki) / (2.0 * total_weight ** 2)

            best_comm = cur
            best_gain = 0.0
            for c, ki_in_c in neighbor_comms.items():
                if c == cur:
                    continue
                sigma_c = comm_total[c]
                gain = ki_in_c / total_weight - (sigma_c * ki) / (2.0 * total_weight ** 2) - remove_cost
                if gain > best_gain:
                    best_gain = gain
                    best_comm = c

            if best_comm != cur:
                comm_internal[cur] -= neighbor_comms.get(cur, 0.0)
                comm_total[cur] -= ki
                community[node] = best_comm
                comm_internal[best_comm] += neighbor_comms.get(best_comm, 0.0)
                comm_total[best_comm] += ki
                improved = True

    label_map: dict[int, int] = {}
    for n in nodes:
        c = community[n]
        if c not in label_map:
            label_map[c] = len(label_map)
        community[n] = label_map[c]
    return community


def _compute_modularity(
    adjacency: dict[str, dict[str, float]],
    community: dict[str, int],
) -> float:
    total_weight = sum(sum(nb.values()) for nb in adjacency.values()) / 2.0
    if total_weight <= 0:
        return 0.0
    q = 0.0
    for node, neighbors in adjacency.items():
        ki = sum(neighbors.values())
        for nb, w in neighbors.items():
            if community.get(node) == community.get(nb):
                kj = sum(adjacency.get(nb, {}).values())
                q += w - (ki * kj) / (2.0 * total_weight)
    return q / (2.0 * total_weight)


KNOWN_COMMODITY_BASES = {s.split("+")[0] for s in MULTI_SIGN_LOGOGRAMS}


def analyze_commodity_community(
    sign_name: str,
    ctx_hits: list[dict],
    corpus: dict,
) -> dict[str, Any]:
    upper = sign_name.upper()

    adjacency = _build_logogram_cooccurrence(corpus)

    if upper not in adjacency:
        return _neutral(
            "Sign has no co-occurrence edges (< 2 shared tablets with any sign)",
            community_id=None, community_members=[], community_size=0,
            known_commodity_members=[], modularity=0.0, total_communities=0,
        )

    community = _greedy_modularity(adjacency)
    modularity = _compute_modularity(adjacency, community)

    sign_comm = community.get(upper)
    if sign_comm is None:
        return _neutral(
            "Sign not in community graph after optimization",
            community_id=None, community_members=[], community_size=0,
            known_commodity_members=[], modularity=round(modularity, 4),
            total_communities=len(set(community.values())),
        )

    members = sorted(n for n, c in community.items() if c == sign_comm)
    known_commodity = [m for m in members if m in KNOWN_COMMODITY_BASES]
    total_communities = len(set(community.values()))

    result: dict[str, Any] = {
        "community_id": sign_comm,
        "community_members": members,
        "community_size": len(members),
        "known_commodity_members": known_commodity,
        "modularity": round(modularity, 4),
        "total_communities": total_communities,
    }

    if len(known_commodity) >= 2:
        result["verdict"] = "SUPPORTS"
        result["score"] = 1
        result["note"] = (
            f"Clusters with {len(known_commodity)} known commodity logograms: "
            f"{', '.join(known_commodity)}"
        )
    elif len(members) < 3:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = "Community too small for diagnostic signal"
    else:
        result["verdict"] = "NEUTRAL"
        result["score"] = 0
        result["note"] = (
            f"Community of {len(members)} signs, "
            f"{len(known_commodity)} known commodity logogram(s)"
        )
    return result


# ── Step 5: Verdict ───────────────────────────────────────────────────

def compute_verdict(
    sections: dict[str, dict],
    sign_name: str,
    lexicon: dict,
    calibration: dict | None = None,
) -> dict:
    scores = {name: sec.get("score", 0) for name, sec in sections.items()}
    supports = sum(1 for v in scores.values() if v > 0)
    weakens = sum(1 for v in scores.values() if v < 0)

    if calibration is not None:
        composite = 0.0
        for name, score in scores.items():
            composite += score * calibration_weight(name, calibration)
        # Count-based guard: any weakening evidence blocks top tiers regardless of weight.
        # A zero-weight feature (e.g. std_position) still counts as weakening evidence.
        if composite >= CALIBRATED_PROBABLE_THRESHOLD and weakens == 0:
            tier = "PROBABLE"
        elif composite >= CALIBRATED_CANDIDATE_THRESHOLD and weakens == 0:
            tier = "CANDIDATE"
        elif composite > 0 or weakens > 0:
            tier = "SPECULATIVE"
        else:
            tier = "NO CANDIDATE"
    else:
        composite = None
        if supports >= 3 and weakens == 0:
            tier = "PROBABLE"
        elif supports >= 2 and weakens == 0:
            tier = "CANDIDATE"
        elif supports >= 1 or weakens > 0:
            tier = "SPECULATIVE"
        else:
            tier = "NO CANDIDATE"

    existing = lexicon.get(sign_name.upper())
    root_sec = sections.get("root", {})
    best_root = root_sec.get("candidates", [{}])[0] if root_sec.get("candidates") else None

    result: dict[str, Any] = {
        "tier": tier,
        "supports": supports,
        "weakens": weakens,
        "scores": scores,
    }
    if composite is not None:
        result["composite_score"] = round(composite, 4)
        result["calibrated"] = True

    if best_root:
        result["proposed_root"] = best_root["root"]
        result["proposed_meaning"] = best_root["meaning"]
        result["proposed_distance"] = best_root["distance"]

    if existing:
        result["existing_entry"] = {
            "reading": existing.get("reading", ""),
            "meaning": existing.get("meaning", ""),
            "confidence": existing.get("confidence", ""),
        }

    blockers = []
    if root_sec.get("single_consonant"):
        blockers.append("Single-consonant skeleton")
    ctx = sections.get("context", {})
    if ctx.get("total", 0) < 3:
        blockers.append(f"Only {ctx.get('total', 0)} standalone occurrence(s)")
    if blockers:
        result["blockers"] = blockers

    upper = sign_name.upper()
    cat = ""
    if upper in lexicon:
        cat = lexicon[upper].get("category", "") or lexicon[upper].get("semantic_field", "")
    if cat in FUNCTION_WORD_CATEGORIES:
        result["warning"] = f"Sign is a function word ({cat}) — standalone occurrences may be grammatical"

    return result


# ── Output formatting ─────────────────────────────────────────────────

def format_human(sign_name: str, ab_number: str, sections: dict, verdict: dict,
                  verbose: bool = False) -> str:
    lines: list[str] = []
    w = 58
    lines.append("═" * w)
    lines.append(f"  LOGOGRAM ANALYSIS: {sign_name}")
    lines.append("═" * w)

    if "existing_entry" in verdict:
        ex = verdict["existing_entry"]
        lines.append(f"\n  ★ Existing lexicon entry: {ex['reading']} \"{ex['meaning']}\" ({ex['confidence']})")

    if "warning" in verdict:
        lines.append(f"\n  ⚠ {verdict['warning']}")

    # §1
    if "pictographic" in sections:
        lines.append("\n§1  PICTOGRAPHIC EVIDENCE")
        lines.append(f"    AB number:    {ab_number or '(unknown)'}")
        pic = sections["pictographic"]
        if pic.get("pictograph"):
            lines.append(f"    Pictograph:   {pic['pictograph']}")
        elif pic.get("ch_ancestor"):
            lines.append(f"    CH ancestor:  {pic['ch_ancestor']}")
        else:
            lines.append("    Pictograph:   [no data in registry]")
        if pic.get("classification"):
            lines.append(f"    Class:        {pic['classification']}")
        lines.append(f"    Verdict:      {pic['verdict']}" +
                     (f" ({pic.get('note', '')})" if pic.get("note") else ""))

    # §1b
    if "configurational_category" in sections:
        lines.append("\n§1b CONFIGURATIONAL CATEGORY (Salgarella 2022)")
        cfg = sections["configurational_category"]
        lines.append(f"    Composite:    {'yes' if cfg.get('is_composite') else 'no'}")
        if cfg.get("is_composite"):
            lines.append(f"    Category:     {cfg.get('category_label', 'unknown')}")
            if cfg.get("base"):
                lines.append(f"    Base:         {cfg['base']}")
            if cfg.get("acrophonic"):
                lines.append(f"    Acrophonic:   {cfg['acrophonic']}")
            if cfg.get("source"):
                lines.append(f"    Source:       {cfg['source']}")
        lines.append(f"    Verdict:      {cfg['verdict']}" +
                     (f" ({cfg.get('note', '')})" if cfg.get("note") else ""))

    # §2
    if "linear_b" in sections:
        lines.append("\n§2  LINEAR B CROSS-SCRIPT")
        lb = sections["linear_b"]
        if lb.get("lb_sign"):
            status = "UNDECIPHERED" if lb.get("lb_undeciphered") else "deciphered"
            attests = f", {lb['lb_attestations']} attestations" if lb.get("lb_attestations") else ""
            lines.append(f"    LB cognate:   {lb['lb_sign']} ({status}{attests})")
        else:
            lines.append("    LB cognate:   none identified")
        lines.append(f"    Verdict:      {lb['verdict']}" +
                     (f" ({lb.get('note', '')})" if lb.get("note") else ""))

    # §3
    if "context" in sections:
        lines.append("\n§3  CONTEXTUAL ATTESTATION")
        ctx = sections["context"]
        lines.append(f"    Standalone:   {ctx['total']} across {ctx['tablets']} tablet(s), {ctx['sites']} site(s)")
        if ctx["total"] > 0:
            lines.append(f"    Numeric:      {ctx['numeric_followers']}/{ctx['total']}"
                          f" ({ctx['numeric_followers']*100//max(ctx['total'],1)}%)")
            if ctx["fraction_followers"]:
                lines.append(f"    Fractions:    {ctx['fraction_followers']} occurrence(s) with fractional qty")
            if ctx["logogram_neighbors"]:
                pairs = ", ".join(f"{k} (×{v})" for k, v in
                                  list(ctx["logogram_neighbors"].items())[:5])
                lines.append(f"    Neighbors:    {pairs}")
        if verbose and ctx.get("hits"):
            lines.append("    Attestations:")
            for h in ctx["hits"]:
                lines.append(f"      {h['tablet']:12s} pos {h['position']:3d}  [{h['site']}]")
        lines.append(f"    Verdict:      {ctx['verdict']}" +
                     (f" ({ctx.get('note', '')})" if ctx.get("note") else ""))

    # §4
    if "root" in sections:
        lines.append("\n§4  ROOT SKELETON MATCHING")
        root = sections["root"]
        lines.append(f"    Skeleton:     /{root.get('consonant', '?')}/")
        if root.get("single_consonant"):
            lines.append("    ⚠ Single-consonant skeleton — weak discriminator")
        if root.get("candidates"):
            lines.append("    Candidates:")
            for i, c in enumerate(root["candidates"]):
                star = " ★" if i == 0 else ""
                lines.append(f"      {c['root']:10s} \"{c['meaning'][:45]}\"  d={c['distance']}{star}")
        else:
            lines.append("    Candidates:   none matching commodity semantics")
        lines.append(f"    Verdict:      {root['verdict']}" +
                     (f" ({root.get('note', '')})" if root.get("note") else ""))

    # §5
    if "site_prior" in sections:
        lines.append("\n§5  SITE PRIOR")
        site = sections["site_prior"]
        lines.append(f"    NWS prior:    {site.get('weighted_nws_prior', 0.0)}")
        if site.get("site_priors"):
            pairs = ", ".join(
                f"{k}: {v:.2f}" for k, v in list(site["site_priors"].items())[:5]
            )
            lines.append(f"    Sites:        {pairs}")
        lines.append(f"    Verdict:      {site['verdict']}" +
                     (f" ({site.get('note', '')})" if site.get("note") else ""))

    # §6
    if "contact" in sections:
        lines.append("\n§6  CONTACT LEXICON")
        contact = sections["contact"]
        if contact.get("matches"):
            lines.append("    Matches:")
            for m in contact["matches"][:5]:
                fields = ", ".join(m.get("semantic_field", [])) or "unclassified"
                lines.append(
                    f"      {m.get('language', '?'):10s} {m.get('entry_id', ''):18s} "
                    f"\"{m.get('meaning', '')[:36]}\" [{fields}]"
                )
        else:
            lines.append("    Matches:      none")
        lines.append(f"    Verdict:      {contact['verdict']}" +
                     (f" ({contact.get('note', '')})" if contact.get("note") else ""))

    # §7
    if "phrase_role" in sections:
        lines.append("\n§7  PHRASE ROLE")
        phrase = sections["phrase_role"]
        lines.append(f"    Role:         {phrase.get('role') or 'none'}")
        lines.append(f"    Verdict:      {phrase['verdict']}" +
                     (f" ({phrase.get('note', '')})" if phrase.get("note") else ""))

    # §8
    if "multilingual_roots" in sections:
        lines.append("\n§8  MULTILINGUAL ROOTS")
        multi = sections["multilingual_roots"]
        posterior = multi.get("language_posterior", {})
        if posterior:
            post = ", ".join(
                f"{lang}: {posterior.get(lang, 0.0):.2f}" for lang in MULTILINGUAL_LANGUAGES
            )
            lines.append(f"    Posterior:    {post}")
        if multi.get("candidates"):
            lines.append("    Candidates:")
            for c in multi["candidates"][:5]:
                lines.append(
                    f"      {c['language']:9s} {c['root']:10s} "
                    f"\"{c['meaning'][:34]}\"  d={c['distance']}"
                )
        else:
            lines.append("    Candidates:   none matching commodity semantics")
        lines.append(f"    Verdict:      {multi['verdict']}" +
                     (f" ({multi.get('note', '')})" if multi.get("note") else ""))

    # §9
    if "successor_entropy" in sections:
        lines.append("\n§9  SUCCESSOR ENTROPY")
        entropy = sections["successor_entropy"]
        succ = entropy.get("successor_distribution", {})
        pred = entropy.get("predecessor_distribution", {})
        succ_pairs = ", ".join(f"{k}: {v}" for k, v in succ.items()) or "none"
        pred_pairs = ", ".join(f"{k}: {v}" for k, v in pred.items()) or "none"
        lines.append(f"    Successor H:  {entropy.get('successor_entropy', 0.0):.2f}")
        lines.append(f"    Predecessor H:{entropy.get('predecessor_entropy', 0.0):.2f}")
        lines.append(f"    Successors:   {succ_pairs}")
        lines.append(f"    Predecessors: {pred_pairs}")
        lines.append(f"    Verdict:      {entropy['verdict']}" +
                     (f" ({entropy.get('note', '')})" if entropy.get("note") else ""))

    # §10
    if "positional_grammar" in sections:
        lines.append("\n§10 POSITIONAL GRAMMAR")
        pos = sections["positional_grammar"]
        lines.append(f"    Mean pos:     {pos.get('mean_position', 0.0):.2f}")
        lines.append(f"    Std pos:      {pos.get('std_position', 0.0):.2f}")
        lines.append(f"    Class:        {pos.get('position_class', 'mixed')}")
        lines.append(f"    Summation:    {pos.get('summation_matches', 0)} match(es), "
                     f"{pos.get('summation_mismatches', 0)} mismatch(es)")
        lines.append(f"    Verdict:      {pos['verdict']}" +
                     (f" ({pos.get('note', '')})" if pos.get("note") else ""))

    # §11
    if "diachronic" in sections:
        lines.append("\n§11 DIACHRONIC")
        dia = sections["diachronic"]
        periods = dia.get("period_distribution", {})
        period_pairs = ", ".join(f"{k}: {v}" for k, v in periods.items()) or "none"
        lifespan = "none"
        if dia.get("lifespan_start") and dia.get("lifespan_end"):
            lifespan = f"{dia['lifespan_start']}–{dia['lifespan_end']}"
        lines.append(f"    Periods:      {period_pairs}")
        lines.append(f"    Lifespan:     {lifespan}")
        lines.append(f"    Dated:        {dia.get('dated_tablets', 0)} dated, "
                     f"{dia.get('undated_tablets', 0)} undated")
        lines.append(f"    Verdict:      {dia['verdict']}" +
                     (f" ({dia.get('note', '')})" if dia.get("note") else ""))

    # §12
    if "lb_slot" in sections:
        lines.append("\n§12 LB SLOT VALIDATION")
        lb_slot = sections["lb_slot"]
        if lb_slot.get("lb_domain"):
            lines.append(f"    Domain:       {lb_slot['lb_domain']}")
        if lb_slot.get("lb_position") is not None:
            lines.append(f"    Position:     {lb_slot['lb_position']}")
        if lb_slot.get("lb_rate") is not None:
            lines.append(f"    Rate:         {lb_slot['lb_rate']:.2%} (bg: {lb_slot.get('lb_bg_rate', 0):.2%})")
        if lb_slot.get("strength"):
            lines.append(f"    Strength:     {lb_slot['strength']}")
        lines.append(f"    Verdict:      {lb_slot['verdict']}" +
                     (f" ({lb_slot.get('note', '')})" if lb_slot.get("note") else ""))

    # §13
    if "phonetic_complement" in sections:
        lines.append("\n§13 PHONETIC COMPLEMENT")
        pc = sections.get("phonetic_complement", {})
        compounds = pc.get("compounds", [])
        if compounds:
            lines.append(f"    Compounds:    {len(compounds)} found")
            for c in compounds[:5]:
                m = "✓" if c.get("match") else "✗"
                lines.append(
                    f"      {c['tablet_id']:12s} {c['compound_token']:16s} "
                    f"/{c['syllabogram_consonant']}/ vs /{c['root_onset']}/ {m}"
                )
            lines.append(f"    Matches:      {pc.get('match_count', 0)} match(es), "
                         f"{pc.get('mismatch_count', 0)} mismatch(es)")
        else:
            lines.append("    Compounds:    none found")
        lines.append(f"    Verdict:      {pc.get('verdict', 'NEUTRAL')}" +
                     (f" ({pc.get('note', '')})" if pc.get("note") else ""))

    # §13b
    if "graphic_disambiguation" in sections:
        lines.append("\n§13b GRAPHIC DISAMBIGUATION (Salgarella et al. 2025)")
        gd = sections["graphic_disambiguation"]
        if gd.get("composite_tablets"):
            lines.append(f"    Composite:    {len(gd['composite_tablets'])} tablet(s)")
        if gd.get("full_spelling_tablets"):
            lines.append(f"    Full-spell:   {len(gd['full_spelling_tablets'])} tablet(s)")
        if not gd.get("composite_tablets") and not gd.get("full_spelling_tablets"):
            lines.append("    Status:       no corpus matches")
        if gd.get("overlap_tablets"):
            lines.append(f"    Overlap:      {len(gd['overlap_tablets'])} tablet(s)")
        lines.append(f"    Verdict:      {gd.get('verdict', 'NEUTRAL')}" +
                     (f" ({gd.get('note', '')})" if gd.get("note") else ""))

    # §14
    if "complementary_dist" in sections:
        lines.append("\n§14 COMPLEMENTARY DISTRIBUTION")
        cd = sections["complementary_dist"]
        cd_forms = cd.get("full_forms", [])
        if cd_forms:
            lines.append(f"    Full forms:   {len(cd_forms)} lexicon entry/entries")
            for ff in cd_forms[:5]:
                disj = "DISJOINT" if ff.get("disjoint") else f"co-occur={ff.get('co_occurrence_count', 0)}"
                lines.append(
                    f"      {ff['word']:18s} sign={ff['sign_tablet_count']} "
                    f"form={ff['form_tablet_count']} p={ff['p_value']:.3f} {disj}"
                )
        else:
            lines.append("    Full forms:   none starting with sign")
        lines.append(f"    Verdict:      {cd.get('verdict', 'NEUTRAL')}" +
                     (f" ({cd.get('note', '')})" if cd.get("note") else ""))

    # §15
    if "commodity_community" in sections:
        lines.append("\n§15 COMMODITY COMMUNITY")
        cc = sections["commodity_community"]
        lines.append(f"    Community:    #{cc.get('community_id', '?')} "
                     f"({cc.get('community_size', 0)} members)")
        members = cc.get("community_members", [])
        if members:
            lines.append(f"    Members:      {', '.join(members[:15])}"
                         + ("..." if len(members) > 15 else ""))
        known = cc.get("known_commodity_members", [])
        if known:
            lines.append(f"    Commodity:    {', '.join(known)}")
        lines.append(f"    Modularity:   {cc.get('modularity', 0.0):.4f} "
                     f"({cc.get('total_communities', 0)} communities)")
        lines.append(f"    Verdict:      {cc.get('verdict', 'NEUTRAL')}" +
                     (f" ({cc.get('note', '')})" if cc.get("note") else ""))

    # §16
    lines.append("\n§16 VERDICT")
    if verdict.get("proposed_root"):
        lines.append(f"    Proposed:     √{verdict['proposed_root']} \"{verdict['proposed_meaning']}\"")
    conf_line = (f"    Confidence:   {verdict['tier']}"
                 f" ({verdict['supports']} SUPPORTS, {verdict['weakens']} WEAKENS)")
    if verdict.get("calibrated"):
        conf_line += f" [composite={verdict['composite_score']:.2f}]"
    lines.append(conf_line)
    if verdict.get("blockers"):
        lines.append(f"    Blockers:     {'; '.join(verdict['blockers'])}")

    lines.append("\n⚠ Readings follow di Mino's Semitic decipherment. Confidence tiers apply.")
    return "\n".join(lines)


def _sv(sections: dict, key: str) -> str:
    """Safely extract verdict string from a sections dict."""
    return sections.get(key, {}).get("verdict", "—")


def format_audit_table(results: list[dict]) -> str:
    results.sort(key=lambda r: (-r["verdict"]["supports"], r["verdict"]["weakens"]))
    v1 = all("site_prior" not in r.get("sections", {}) for r in results)
    lines: list[str] = []
    if v1:
        width = 95
        lines.append("═" * width)
        lines.append("  LOGOGRAM AUDIT — Single-Sign Candidates (v1)")
        lines.append("═" * width)
        lines.append(f"{'Sign':<8} {'AB':<8} {'Standalone':<12} {'Pictog':<9} {'LB':<9} "
                     f"{'Context':<9} {'Root':<9} {'Verdict':<12} {'Best Root'}")
        lines.append("─" * width)
        for r in results:
            v = r["verdict"]
            s = r["sections"]
            best = v.get("proposed_root", "—")
            lines.append(
                f"{r['sign']:<8} {r['ab']:<8} "
                f"{s.get('context', {}).get('total', 0):<12} "
                f"{_sv(s, 'pictographic'):<9} {_sv(s, 'linear_b'):<9} "
                f"{_sv(s, 'context'):<9} {_sv(s, 'root'):<9} "
                f"{v['tier']:<12} {best}"
            )
    else:
        width = 220
        lines.append("═" * width)
        lines.append("  LOGOGRAM AUDIT — Single-Sign Candidates (v3)")
        lines.append("═" * width)
        lines.append(f"{'Sign':<8} {'AB':<8} {'Standalone':<12} {'Pictog':<9} {'Config':<9} {'LB':<9} "
                     f"{'Context':<9} {'Root':<9} {'Site':<9} {'Contact':<9} {'Phrase':<9} "
                     f"{'Multi':<9} {'Entropy':<9} {'Position':<9} {'Diachr':<9} {'LBSlot':<9} "
                     f"{'PhonCpl':<9} {'GrDisam':<9} {'CplDist':<9} {'CommGrp':<9} "
                     f"{'Verdict':<12} {'Best Root'}")
        lines.append("─" * width)
        for r in results:
            v = r["verdict"]
            s = r["sections"]
            best = v.get("proposed_root", "—")
            lines.append(
                f"{r['sign']:<8} {r['ab']:<8} "
                f"{s.get('context', {}).get('total', 0):<12} "
                f"{_sv(s, 'pictographic'):<9} {_sv(s, 'configurational_category'):<9} {_sv(s, 'linear_b'):<9} "
                f"{_sv(s, 'context'):<9} {_sv(s, 'root'):<9} "
                f"{_sv(s, 'site_prior'):<9} {_sv(s, 'contact'):<9} "
                f"{_sv(s, 'phrase_role'):<9} {_sv(s, 'multilingual_roots'):<9} "
                f"{_sv(s, 'successor_entropy'):<9} "
                f"{_sv(s, 'positional_grammar'):<9} {_sv(s, 'diachronic'):<9} "
                f"{_sv(s, 'lb_slot'):<9} "
                f"{_sv(s, 'phonetic_complement'):<9} "
                f"{_sv(s, 'graphic_disambiguation'):<9} "
                f"{_sv(s, 'complementary_dist'):<9} "
                f"{_sv(s, 'commodity_community'):<9} "
                f"{v['tier']:<12} {best}"
            )
    lines.append("─" * width)
    lines.append(f"  {len(results)} signs analyzed")
    lines.append("\n⚠ Readings follow di Mino's Semitic decipherment. Confidence tiers apply.")
    return "\n".join(lines)


# ── Main pipeline ─────────────────────────────────────────────────────

def analyze_sign(
    sign_name: str,
    verbose: bool = False,
    as_json: bool = False,
    calibration: dict | None | object = _AUTO,
    v1_mode: bool = False,
    section_filter: set[str] | None = None,
) -> dict:
    if calibration is _AUTO:
        calibration = load_calibration()

    registry = load_registry()
    by_ab, by_name = build_indices(registry.get("signs", []))
    lexicon = load_lexicon_entries()

    display, ab, entry = resolve_sign_name(sign_name, by_ab, by_name)

    ctx = analyze_context(display, lexicon)
    root_result = analyze_roots(display, lexicon)
    config_result = analyze_configurational_category(display)
    sections = {
        "pictographic": analyze_pictographic(entry),
        "linear_b": analyze_linear_b(entry, ab),
        "context": ctx,
        "root": root_result,
    }

    if not v1_mode:
        sections["configurational_category"] = config_result
        sections["site_prior"] = analyze_site_prior(ctx.get("site_distribution", {}))
        sections["contact"] = analyze_contact_lexicon(display)
        sections["phrase_role"] = analyze_phrase_role(display)
        sections["multilingual_roots"] = analyze_multilingual_roots(
            display, ctx.get("site_distribution", {})
        )
        ctx_hits = ctx.get("hits", [])
        corpus_for_entropy = data_cache.corpus()
        sections["successor_entropy"] = analyze_successor_entropy(ctx_hits, corpus_for_entropy)
        sections["positional_grammar"] = analyze_positional_grammar(ctx_hits, corpus_for_entropy)
        sections["diachronic"] = analyze_diachronic(ctx.get("tablet_list", []))
        sections["lb_slot"] = analyze_lb_slot_validation(display, ctx_hits)
        sections["phonetic_complement"] = analyze_phonetic_complement(
            display, root_result, ctx_hits, corpus_for_entropy,
        )
        sections["graphic_disambiguation"] = analyze_graphic_disambiguation(
            display, config_result, corpus_for_entropy,
        )
        sections["complementary_dist"] = analyze_complementary_distribution(
            display, corpus_for_entropy,
        )
        sections["commodity_community"] = analyze_commodity_community(
            display, ctx_hits, corpus_for_entropy,
        )

    if section_filter:
        sections = {k: v for k, v in sections.items() if k in section_filter}

    verdict = compute_verdict(sections, display, lexicon, calibration=calibration)

    result = {
        "sign": display,
        "ab": ab,
        "sections": sections,
        "verdict": verdict,
    }

    if not as_json and not verbose:
        for sec in sections.values():
            sec.pop("hits", None)

    return result


def run_audit(calibration: dict | None | object = _AUTO, v1_mode: bool = False,
              section_filter: set[str] | None = None) -> list[dict]:
    if calibration is _AUTO:
        calibration = load_calibration()

    lexicon = load_lexicon_entries()
    corpus = data_cache.corpus()

    targets: set[str] = set()

    for word in lexicon:
        if "-" not in word and len(word) <= 3 and not word.isdigit():
            targets.add(word.upper())

    standalone_counts: Counter[str] = Counter()
    for tablet in corpus.values():
        for w in tablet.get("transliteratedWords", []):
            if not isinstance(w, str):
                continue
            ws = w.strip()
            if "-" in ws or "+" in ws:
                continue
            if is_numeral(ws) or is_separator(ws) or is_multi_sign_logogram(ws):
                continue
            if len(ws) <= 3:
                standalone_counts[ws.upper()] += 1

    for sign, count in standalone_counts.items():
        if count >= 3 and sign not in targets and sign.isalpha():
            targets.add(sign)

    results = []
    for sign in sorted(targets):
        r = analyze_sign(sign, verbose=False, as_json=True, calibration=calibration,
                         v1_mode=v1_mode, section_filter=section_filter)
        results.append(r)

    return results


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze single-sign logographic abbreviation candidates")
    parser.add_argument("sign", nargs="?", help="Sign name (ZU, SI, KU) or star number (*301)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--verbose", action="store_true", help="Include full attestation lines")
    parser.add_argument("--audit", action="store_true", help="Analyze all single-sign candidates")
    parser.add_argument("--sections", type=str, default=None,
                        help="Comma-separated section names to run (debugging)")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Minimum confidence for root candidates (default: 0.3)")
    cal_group = parser.add_mutually_exclusive_group()
    cal_group.add_argument("--calibrated", action="store_true", default=False,
                           help="Use LB-calibrated weights (default: auto-detect)")
    cal_group.add_argument("--no-calibrated", action="store_true",
                           help="Disable calibrated weighting")
    cal_group.add_argument("--v1", action="store_true",
                           help="Force v1 behavior (original 4-section counting)")
    cal_group.add_argument("--v2", action="store_true",
                           help="Force v2 behavior (15-section pipeline, no configurational/disambiguation)")
    args = parser.parse_args()

    v1_mode = bool(args.v1)
    v2_mode = bool(args.v2)
    section_filter = set(args.sections.split(",")) if args.sections else None
    if v2_mode and section_filter is None:
        section_filter = V2_SECTIONS
    if args.v1 or args.no_calibrated:
        calibration = None
    elif args.calibrated:
        calibration = load_calibration()
        if calibration is None:
            print("warning: --calibrated requested but lb_calibration_thresholds.json not found",
                  file=sys.stderr)
    else:
        calibration = load_calibration()

    if args.audit:
        results = run_audit(calibration=calibration, v1_mode=v1_mode,
                            section_filter=section_filter)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print(format_audit_table(results))
        return

    if not args.sign:
        parser.error("Sign name required (or use --audit)")

    result = analyze_sign(args.sign, verbose=args.verbose, as_json=args.json,
                          calibration=calibration, v1_mode=v1_mode,
                          section_filter=section_filter)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_human(
            result["sign"], result["ab"],
            result["sections"], result["verdict"],
            verbose=args.verbose,
        ))


if __name__ == "__main__":
    sys.exit(main())
