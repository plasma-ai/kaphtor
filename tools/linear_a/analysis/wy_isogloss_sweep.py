#!/usr/bin/env python3
"""Null-calibrated Linear A initial *w/*y isogloss sweep.

The analysis is read-only over kaphtor's ``data/`` directory. It inventories
SED *w-/*y- reconstructions, classifies them from daughter-branch evidence,
searches the Linear A corpus under both glide reflexes, audits existing
lexicon claims, and calibrates the observed match counts against a
radical-permutation null. It writes only ``wy_matrix.json`` and ``REPORT.md``
under the required ``--out`` directory.

Usage:
    uv run python tools/linear_a/analysis/wy_isogloss_sweep.py --out /path/to/outdir --quick
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.phonetics import SEMITIC_DISTANCES, weighted_levenshtein
from ...core.semitic_root_schema import roots_records
from ...core.skeleton import extract_skeleton
from ...paths import CONTACT_DATA, DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

SCRIPT_VERSION = "1.0.0"
DEFAULT_SEED = 1961
CANDIDATE_MAX = 0.3
SPECULATIVE_MAX = 0.5
CONTACT_FILES = (
    "hebrew_lexicon.jsonl",
    "ugaritic_lexicon.jsonl",
    "aramaic_lexicon.jsonl",
    "phoenician_lexicon.jsonl",
)

LANG_BRANCH: dict[str, str] = {
    "Akkadian": "EAST", "Eblaitic": "EAST", "Assyro-Babylonian": "EAST",
    "East Semitic": "EAST", "Palaeosyrian": "EAST",
    "Arabic": "ARABIC", "Modern Arabic": "ARABIC",
    "Classical Arabic": "ARABIC", "Pre-Islamic North Arabian": "ARABIC",
    "Lihyanite": "ARABIC",
    "Geez": "SOUTH", "Ge'ez": "SOUTH", "Ethiopic": "SOUTH",
    "Tigre": "SOUTH", "Tigrinya": "SOUTH", "Amharic": "SOUTH",
    "Old Amharic": "SOUTH", "Gurage": "SOUTH", "Harari": "SOUTH",
    "East Ethiopic": "SOUTH", "Argobba": "SOUTH", "Gafat": "SOUTH",
    "Mehri": "SOUTH", "Jibbali": "SOUTH", "Soqotri": "SOUTH",
    "Harsusi": "SOUTH", "Modern South Arabian": "SOUTH",
    "Epigraphic South Arabian": "ESA", "Sabaic": "ESA",
    "Old Sabaean": "ESA",
    "Hebrew": "NWS", "Ugaritic": "NWS", "Phoenician": "NWS",
    "Punic": "NWS", "Canaanite": "NWS", "Amorite": "NWS",
    "Moabite": "NWS", "Aramaic": "NWS", "Syrian Aramaic": "NWS",
    "Judaic Aramaic": "NWS", "Mandaic Aramaic": "NWS",
    "Biblical Aramaic": "NWS", "Modern Aramaic": "NWS",
    "Nabataean": "NWS", "Syriac": "NWS",
}
NON_NWS_BRANCHES = frozenset({"EAST", "SOUTH", "ESA", "ARABIC"})

VOWELS = frozenset("aeiouāēīōūăĕĭŏŭəǝâêîôûäëïöüáéíóúàèìòù")
ROOT_TRANSLATION = str.maketrans({
    "ʕ": "ʿ", "ʾ": "ʔ", "’": "ʔ", "‘": "ʿ",
    "ḳ": "q", "Ḳ": "q", "ḵ": "k", "Ḵ": "k",
    "ṱ": "ṭ", "ț": "ṭ", "ş": "ṣ",
    "ỉ": "y", "ꞽ": "y",
})
VERBAL_RE = re.compile(
    r"\b(verb|imperfect|perfect|jussive|volitive|participle|imperative|"
    r"yaqtul|he |she |it |they |I |you )", re.IGNORECASE
)
CLAIM_RE = re.compile(
    r"(?<![A-Za-zʿʔ])([wy](?:-[A-Za-zʿʔḥḫġṣṭṯḏẓśḍq]+){1,4})",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def normalized_ps_string(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).strip())


def _fold_root_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value).translate(ROOT_TRANSLATION)
    for source, target in (
        ("sh", "š"), ("th", "ṯ"), ("kh", "ḫ"),
        ("gh", "ġ"), ("dh", "ḏ"), ("ṣ", "ṣ"),
        ("ṭ", "ṭ"), ("ḥ", "ḥ"), ("ḳ", "q"),
    ):
        value = value.replace(source, target)
    return unicodedata.normalize("NFC", value)


def consonantal_skeleton(value: str) -> str:
    """Extract a canonical consonantal string from a Semitic form/root."""
    value = _fold_root_text(value)
    value = re.sub(r"\([^)]*\)", "", value)
    out: list[str] = []
    # Iterate in NFC so precomposed Semitic consonants (ṣ, ṭ, ḥ, ṯ, ḏ...)
    # remain phonemes rather than collapsing to their unmarked base letters.
    for ch in unicodedata.normalize("NFC", value):
        if unicodedata.combining(ch):
            continue
        low = ch.lower()
        if low in VOWELS or ch in "*Vv0123456789-_/~{}.,;:[]'\" ":
            continue
        if ch.isalpha() or ch in "ʔʿ":
            out.append(low if ch not in "ʔʿ" else ch)
    return "".join(out)


def collapse_geminates(value: str) -> str:
    if not value:
        return value
    out = [value[0]]
    for ch in value[1:]:
        if ch != out[-1]:
            out.append(ch)
    return "".join(out)


def ps_skeleton_variants(ps: str) -> list[str]:
    """Expand slash/tilde initial variants, then return *w/*y skeletons."""
    text = normalized_ps_string(ps)
    variants: list[str] = []
    initial_pair = re.match(r"^\*?([wy])/([wy])(.*)$", text, re.IGNORECASE)
    if initial_pair:
        variants.extend(
            initial + initial_pair.group(3)
            for initial in (initial_pair.group(1), initial_pair.group(2))
        )
    else:
        variants.extend(re.split(r"\s*~\s*|/\*", text))
    out: list[str] = []
    for variant in variants:
        skel = consonantal_skeleton(variant)
        if skel.startswith(("w", "y")) and skel not in out:
            out.append(skel)
    return out


def claim_skeletons(root_field: str) -> list[str]:
    """Return w/y-initial alternatives from the root field's first component.

    A medial glide in ``n-w-y`` is not an initial-*w claim, and a second
    compound member such as ``p-ʔ-r + y-ṣ-ʔ`` does not make the entry itself
    y-initial.  Slash alternatives inside the first component are retained.
    """
    out: list[str] = []
    primary = (root_field or "").split("+", 1)[0].strip()
    primary = primary.lstrip("√*").strip()
    for alternative in re.split(r"\s*/\s*", primary):
        match = re.match(
            r"^([wy](?:-[A-Za-zʿʔḥḫġṣṭṯḏẓśḍq]+){1,4})(?:\b|$)",
            alternative.strip(), re.IGNORECASE,
        )
        if not match:
            continue
        skel = consonantal_skeleton(match.group(1))
        if skel.startswith(("w", "y")) and skel not in out:
            out.append(skel)
    return out


def analogue_initial(value: Any) -> str:
    """Conservatively call W/Y from the leading cited daughter form."""
    if not isinstance(value, str):
        return "UNKNOWN"
    text = _fold_root_text(value).strip()
    if not text or text.startswith("--"):
        return "UNKNOWN"
    text = re.sub(r"^\s*\(\?\)\s*", "", text)
    # Only inspect the form-side of a dictionary citation, before its gloss.
    text = re.split(r"['\"\[]", text, maxsplit=1)[0]
    tokens = re.findall(r"[A-Za-zʔʿḥḫġṣṭṯḏẓśḍqāēīōūăĕĭŏŭəǝ]+", text)
    for token in tokens[:5]:
        if token.isupper() and len(token) <= 7:
            continue
        low = token.lower()
        if low in {"cf", "do", "id", "off", "pal", "urm", "nab", "sam"}:
            continue
        first = low[0]
        if first in {"w", "v"}:
            return "W"
        if first in {"y", "j", "i"}:
            return "Y"
        return "OTHER"
    return "UNKNOWN"


def classify_branch_pattern(evidence: list[dict[str, Any]]) -> tuple[str, str]:
    informative = [e for e in evidence if e["initial"] in {"W", "Y"}]
    non_nws = [e for e in informative if e["branch"] in NON_NWS_BRANCHES]
    non_nws_w = [e for e in non_nws if e["initial"] == "W"]
    non_nws_y = [e for e in non_nws if e["initial"] == "Y"]
    any_w = any(e["initial"] == "W" for e in informative)
    if non_nws_w and not non_nws_y:
        return "W_CLASS", "non-NWS w-reflex evidence; NWS may show y or w"
    if non_nws_y and not any_w:
        return "Y_CLASS", "all informative branches show y; non-NWS y control present"
    if non_nws_w and non_nws_y:
        return "AMBIGUOUS", "mixed w/y evidence inside non-NWS branches"
    if informative:
        return "AMBIGUOUS", "informative reflexes lack a decisive non-NWS control"
    return "AMBIGUOUS", "insufficient parseable Analogue coverage"


class ContactIndex:
    """Exact normalized/match-key index over the NWS contact lexicons."""

    def __init__(self, contact_dir: Path):
        self.rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.hashes: dict[str, str] = {}
        for filename in CONTACT_FILES:
            path = require(contact_dir / filename, f"contact/{filename}")
            language = filename.replace("_lexicon.jsonl", "").replace("_glossary.jsonl", "")
            by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    raw_keys: set[str] = set()
                    for field in (
                        "normalized", "headword_normalized", "root", "root_normalized",
                    ):
                        value = row.get(field)
                        if isinstance(value, str) and value:
                            raw_keys.add(value)
                    raw_keys.update(k for k in row.get("match_keys", []) if isinstance(k, str))
                    sample = {
                        "id": row.get("id"),
                        "form": row.get("form_original") or row.get("headword"),
                        "normalized": row.get("normalized") or row.get("headword_normalized"),
                        "root": row.get("root") or row.get("root_normalized"),
                        "meaning": (row.get("meaning") or "")[:160],
                    }
                    for raw_key in raw_keys:
                        key = consonantal_skeleton(raw_key)
                        if not key:
                            continue
                        bucket = by_key[key]
                        if len(bucket) < 3 and sample not in bucket:
                            bucket.append(sample)
            self.rows[language] = dict(by_key)
            self.hashes[filename] = sha256(path)

    def verify_y_reflex(self, root_variants: list[str]) -> dict[str, Any]:
        expected: set[str] = set()
        for skeleton in root_variants:
            if skeleton.startswith(("w", "y")):
                base = "y" + skeleton[1:]
                expected.update({base, collapse_geminates(base)})
        hits: dict[str, Any] = {}
        for language, index in self.rows.items():
            samples: list[dict[str, Any]] = []
            matched_keys = sorted(expected & set(index))
            for key in matched_keys:
                samples.extend(index[key])
            hits[language] = {
                "hit": bool(matched_keys),
                "matched_keys": matched_keys,
                "samples": samples[:3],
            }
        return {
            "expected_y_keys": sorted(expected),
            "languages_with_hit": sorted(k for k, v in hits.items() if v["hit"]),
            "by_language": hits,
        }


def build_root_inventory(
    rows: list[dict[str, Any]], contact_index: ContactIndex,
) -> list[dict[str, Any]]:
    """Group *w-/*y- records by their Proto-Semitic form.

    ``rows`` are records in the shape of ``semitic_root_schema.roots_records``:
    Number, Proto-Semitic, Meaning, and Analogues (language → cited text).
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ps = normalized_ps_string(str(row.get("Proto-Semitic", "")))
        if re.match(r"^\*[wy]", ps, re.IGNORECASE):
            grouped[ps].append(row)

    inventory: list[dict[str, Any]] = []
    for ps, duplicates in sorted(grouped.items()):
        skeletons = ps_skeleton_variants(ps)
        if not skeletons:
            continue
        evidence: list[dict[str, Any]] = []
        seen_evidence: set[tuple[str, str]] = set()
        for row in duplicates:
            for language, form in (row.get("Analogues") or {}).items():
                if language == "Notes" or not isinstance(form, str):
                    continue
                key = (language, form)
                if key in seen_evidence:
                    continue
                seen_evidence.add(key)
                evidence.append({
                    "language": language,
                    "branch": LANG_BRANCH.get(language, "OTHER"),
                    "form": form,
                    "initial": analogue_initial(form),
                })
        root_class, rationale = classify_branch_pattern(evidence)
        root_id = "sed:" + hashlib.sha1(ps.encode("utf-8")).hexdigest()[:12]
        inventory.append({
            "root_id": root_id,
            "numbers": sorted({str(row.get("Number")) for row in duplicates}),
            "ps": ps,
            "normalized_ps": ps,
            "meanings": sorted({str(row.get("Meaning", "")) for row in duplicates}),
            "deduplicated_rows": len(duplicates),
            "skeleton_variants": skeletons,
            "canonical_skeleton": skeletons[0],
            "ps_initial": skeletons[0][0].upper(),
            "class": root_class,
            "class_rationale": rationale,
            "analogue_evidence": sorted(evidence, key=lambda e: (e["branch"], e["language"])),
            "nws_contact_verification": contact_index.verify_y_reflex(skeletons),
        })
    return inventory


def load_sign_inventory(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    signs = data["signs"]
    w_signs: list[str] = []
    j_signs: list[str] = []
    excluded_j_named: list[dict[str, Any]] = []
    for name, record in signs.items():
        consonant = (record.get("primary") or {}).get("consonant")
        if consonant == "w":
            w_signs.append(name)
        if consonant == "y":
            j_signs.append(name)
        if name.startswith("J") and consonant != "y":
            excluded_j_named.append({"sign": name, "current_value": consonant})
    # Corpus/lexicon displays may render *28B directly as JI.
    aliases = {"JI": "*28B"} if "*28B" in j_signs else {}
    return {
        "w_series": sorted(w_signs),
        "j_series": sorted(j_signs),
        "display_aliases": aliases,
        "excluded_j_named_signs": excluded_j_named,
        "u_vocalic": ["U"],
        "i_vocalic": ["I"],
        "w_drop_before_rounded_vowel": {
            "enabled": False,
            "reason": "the Semitic-to-Linear A spelling rules do not license initial w-loss",
        },
    }


def _normalize_word(word: str) -> str:
    return unicodedata.normalize("NFC", word.strip()).upper()


def word_initial_class(word: str, sign_inventory: dict[str, Any]) -> str:
    first = _normalize_word(word).split("-")[0]
    alias = sign_inventory["display_aliases"].get(first, first)
    if alias in sign_inventory["w_series"]:
        return "W"
    if alias in sign_inventory["j_series"]:
        return "J"
    if first == "U":
        return "U_VOCALIC"
    if first == "I":
        return "I_VOCALIC"
    return "OTHER"


def word_skeleton(word: str) -> str:
    parts = _normalize_word(word).split("-")
    normalized_parts = ["*28B" if part == "JI" else part for part in parts]
    return consonantal_skeleton(extract_skeleton("-".join(normalized_parts)))


def residual_skeleton(word: str, initial_class: str) -> str:
    skeleton = word_skeleton(word)
    if initial_class == "W" and skeleton.startswith("w"):
        return skeleton[1:]
    if initial_class == "J" and skeleton.startswith("y"):
        return skeleton[1:]
    # In I-JA-PA-ME-type spellings, I carries the initial glide while the
    # following JA supplies its vowel; do not count that JA as a second radical.
    if initial_class == "I_VOCALIC" and skeleton.startswith("y"):
        return skeleton[1:]
    return skeleton


def plausible_word(word: str) -> bool:
    if not word or any(ch in word for ch in "\n\r\t"):
        return False
    if re.fullmatch(r"[\d¼½¾⅓⅔⅛⅜⅝⅞.]+", word):
        return False
    return bool(re.fullmatch(r"[A-Z*0-9₁₂₃₄₅ʿʾḤḪĠṢṬṮḎẒŚḌQ]+(?:-[A-Z*0-9₁₂₃₄₅ʿʾḤḪĠṢṬṮḎẒŚḌQ]+)*", word))


def build_word_inventory(
    lexicon: list[dict[str, Any]], corpus: dict[str, dict[str, Any]],
    sign_inventory: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    lex_by_word: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources: dict[str, set[str]] = defaultdict(set)
    attestations: dict[str, set[str]] = defaultdict(set)
    frequencies: Counter[str] = Counter()
    for entry in lexicon:
        word = _normalize_word(str(entry.get("word", "")))
        if word and entry.get("confidence") != "REJECTED":
            lex_by_word[word].append(entry)
            sources[word].add("lexicon")
            attestations[word].update(entry.get("attestations") or [])
    for inscription, record in corpus.items():
        for raw_word in record.get("transliteratedWords") or []:
            if not isinstance(raw_word, str):
                continue
            word = _normalize_word(raw_word)
            if not plausible_word(word):
                continue
            sources[word].add("corpus")
            attestations[word].add(inscription)
            frequencies[word] += 1

    words: list[dict[str, Any]] = []
    for word in sorted(sources):
        initial = word_initial_class(word, sign_inventory)
        if initial == "OTHER":
            continue
        residual = residual_skeleton(word, initial)
        if not residual:
            continue
        words.append({
            "word": word,
            "initial_spelling": initial,
            "headline_column": "VOCALIC" if initial.endswith("VOCALIC") else initial,
            "skeleton": word_skeleton(word),
            "residual_skeleton": residual,
            "sources": sorted(sources[word]),
            "frequency": frequencies[word],
            "attestations": sorted(attestations[word]),
            "lexicon_entries": [
                {
                    "root": e.get("root"), "reading": e.get("reading"),
                    "meaning": e.get("meaning"), "confidence": e.get("confidence"),
                    "category": e.get("category"), "note": e.get("note"),
                }
                for e in lex_by_word.get(word, [])
            ],
        })
    stats = {
        "unique_all_words": len(sources),
        "eligible_initial_words": len(words),
        "initial_counts": dict(Counter(w["initial_spelling"] for w in words)),
        "source_counts": dict(Counter(s for w in words for s in w["sources"])),
    }
    return words, lex_by_word, stats


def distance_to_remainder(word_remainder: str, root_remainder: str) -> dict[str, Any]:
    """Best match against the root's radicals 2+, allowing a trailing affix/compound."""
    root_forms = {root_remainder, collapse_geminates(root_remainder)} - {""}
    if not root_forms or not word_remainder:
        return {"distance": float("inf")}
    word_forms: list[tuple[str, str]] = []
    for length in range(1, min(len(word_remainder), max(map(len, root_forms)) + 1) + 1):
        prefix = word_remainder[:length]
        word_forms.append((prefix, word_remainder[length:]))
        collapsed = collapse_geminates(prefix)
        if collapsed != prefix:
            word_forms.append((collapsed, word_remainder[length:]))
    best: dict[str, Any] = {"distance": float("inf")}
    for root_form in root_forms:
        for word_form, trailing in word_forms:
            distance = weighted_levenshtein(
                word_form,
                root_form,
                SEMITIC_DISTANCES,
                guttural_transparent=True,
                insert_costs={"w": 0.25, "y": 0.25},
            )
            if distance < best["distance"]:
                best = {
                    "distance": round(distance, 4),
                    "matched_word_radicals": word_form,
                    "matched_root_radicals": root_form,
                    "trailing_skeleton": trailing,
                }
    return best


def distance_band(distance: float) -> str | None:
    if distance < CANDIDATE_MAX:
        return "CANDIDATE"
    if distance < SPECULATIVE_MAX:
        return "SPECULATIVE"
    return None


def roots_compatible(claimed: str, variants: Iterable[str]) -> bool:
    claimed_forms = {claimed, collapse_geminates(claimed)}
    for variant in variants:
        variant_forms = {variant, collapse_geminates(variant)}
        for left in claimed_forms:
            for right in variant_forms:
                if left == right:
                    return True
                if weighted_levenshtein(
                    left, right, SEMITIC_DISTANCES, guttural_transparent=True,
                    insert_costs={"w": 0.25, "y": 0.25},
                ) < CANDIDATE_MAX:
                    return True
    return False


def roots_exactly_compatible(claimed: str, variants: Iterable[str]) -> bool:
    claimed_forms = {claimed, collapse_geminates(claimed)}
    return any(
        variant in claimed_forms or collapse_geminates(variant) in claimed_forms
        for variant in variants
    )


def match_words_to_roots(
    roots: list[dict[str, Any]], words: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for root in roots:
        remainder_variants = sorted({v[1:] for v in root["skeleton_variants"] if len(v) > 1})
        for word in words:
            best: dict[str, Any] = {"distance": float("inf")}
            best_root_remainder = None
            for remainder in remainder_variants:
                result = distance_to_remainder(word["residual_skeleton"], remainder)
                if result["distance"] < best["distance"]:
                    best = result
                    best_root_remainder = remainder
            band = distance_band(best["distance"])
            if band is None:
                continue
            claimed = [
                claim
                for entry in word["lexicon_entries"]
                for claim in claim_skeletons(entry.get("root") or "")
            ]
            agreement = any(roots_exactly_compatible(claim, root["skeleton_variants"]) for claim in claimed)
            conflict = bool(claimed) and not agreement
            lex_blob = " ".join(
                str(entry.get(key) or "")
                for entry in word["lexicon_entries"]
                for key in ("meaning", "category", "note")
            )
            ja_prefix = word["word"].startswith("JA-") and (
                not agreement or bool(VERBAL_RE.search(lex_blob)) or not word["lexicon_entries"]
            )
            matches.append({
                "root_id": root["root_id"],
                "root": root["ps"],
                "root_class": root["class"],
                "root_numbers": root["numbers"],
                "root_meanings": root["meanings"],
                "tested_root_remainder": best_root_remainder,
                "word": word["word"],
                "word_initial_spelling": word["initial_spelling"],
                "headline_column": word["headline_column"],
                "spelling_reflex": "W" if word["initial_spelling"] in {"W", "U_VOCALIC"} else "J",
                "distance": best["distance"],
                "band": band,
                "matched_word_radicals": best.get("matched_word_radicals"),
                "matched_root_radicals": best.get("matched_root_radicals"),
                "trailing_skeleton": best.get("trailing_skeleton"),
                "frequency": word["frequency"],
                "attestations": word["attestations"],
                "sources": word["sources"],
                "lexicon_entries": word["lexicon_entries"],
                "lexicon_root_agreement": agreement,
                "lexicon_root_conflict": conflict,
                "ja_prefix_contamination": ja_prefix,
            })
    return sorted(matches, key=lambda m: (m["root_class"], m["root"], m["distance"], m["word"]))


def join_claim_to_sed(
    claim: str, roots: list[dict[str, Any]], claim_meaning: str = "",
) -> list[dict[str, Any]]:
    candidates = [
        root for root in roots
        if claim in root["skeleton_variants"]
        or any(collapse_geminates(variant) == collapse_geminates(claim)
               for variant in root["skeleton_variants"])
    ]
    stop = {"the", "and", "one", "from", "with", "that", "this", "god", "goddess"}
    claim_terms = {
        term for term in re.findall(r"[a-z]+", claim_meaning.lower())
        if len(term) >= 3 and term not in stop
    }
    if claim_terms and candidates:
        scored = [
            (len(claim_terms & set(re.findall(r"[a-z]+", " ".join(root["meanings"]).lower()))), root)
            for root in candidates
        ]
        best_semantic = max(score for score, _root in scored)
        if best_semantic:
            candidates = [root for score, root in scored if score == best_semantic]
    decisive = [root for root in candidates if root["class"] != "AMBIGUOUS"]
    if decisive:
        candidates = decisive
    return sorted(candidates, key=lambda root: root["ps"])


def spelling_bucket(word: str, sign_inventory: dict[str, Any]) -> str:
    initial = word_initial_class(word, sign_inventory)
    if initial in {"U_VOCALIC", "I_VOCALIC"}:
        return "VOCALIC"
    if initial in {"W", "J"}:
        return initial
    if word in {"VIN"} or "-" not in word:
        return "LOGOGRAM_OR_OTHER"
    return "OTHER"


def audit_existing_claims(
    lexicon: list[dict[str, Any]], roots: list[dict[str, Any]],
    sign_inventory: dict[str, Any], words_by_name: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    control_matches: list[dict[str, Any]] = []
    table = {cls: {col: 0 for col in ("W", "J", "VOCALIC")} for cls in ("W_CLASS", "Y_CLASS")}
    for entry in lexicon:
        if entry.get("confidence") == "REJECTED":
            continue
        claims = claim_skeletons(entry.get("root") or "")
        if not claims:
            continue
        claim = claims[0]
        joined = join_claim_to_sed(claim, roots, entry.get("meaning") or "")
        classes = sorted({root["class"] for root in joined})
        sed_class = classes[0] if len(classes) == 1 else "AMBIGUOUS"
        bucket = spelling_bucket(entry["word"], sign_inventory)
        disagreement = (
            (claim.startswith("w") and sed_class == "Y_CLASS")
            or (claim.startswith("y") and sed_class == "W_CLASS")
        )
        row = {
            "word": entry["word"], "reading": entry.get("reading"),
            "claimed_root_field": entry.get("root"), "claimed_root": claim,
            "claimed_initial": claim[0].upper(), "meaning": entry.get("meaning"),
            "confidence": entry.get("confidence"), "spelling_bucket": bucket,
            "sed_root_ids": [root["root_id"] for root in joined],
            "sed_roots": [root["ps"] for root in joined],
            "sed_class": sed_class,
            "branch_pattern_disagrees_with_claim": disagreement,
            "branch_pattern_unresolved": sed_class == "AMBIGUOUS",
            "note": entry.get("note"),
        }
        if sed_class in table and bucket in table[sed_class]:
            table[sed_class][bucket] += 1
        rows.append(row)

        # Control lane for lexicon roots absent from the SED initial-root
        # inventory. It uses the same matcher but never enters headline/null counts.
        if not joined and entry["word"] in words_by_name:
            word = words_by_name[entry["word"]]
            result = distance_to_remainder(word["residual_skeleton"], claim[1:])
            band = distance_band(result["distance"])
            if band:
                control_matches.append({
                    "source": "LEXICON_CLAIM_CONTROL",
                    "headline_eligible": False,
                    "exclusion_reason": "claimed initial root absent from SED *w/*y inventory",
                    "word": entry["word"], "claimed_root": claim,
                    "word_initial_spelling": word["initial_spelling"],
                    "distance": result["distance"], "band": band,
                    "matched_word_radicals": result.get("matched_word_radicals"),
                    "matched_root_radicals": result.get("matched_root_radicals"),
                    "trailing_skeleton": result.get("trailing_skeleton"),
                })
    return sorted(rows, key=lambda r: r["word"]), table, control_matches


def observed_counts(matches: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for root_class in ("W_CLASS", "Y_CLASS"):
        output[root_class] = {}
        for band in ("CANDIDATE", "SPECULATIVE"):
            output[root_class][band] = {}
            for column in ("W", "J", "VOCALIC"):
                selected = [
                    match for match in matches
                    if match["root_class"] == root_class
                    and match["band"] == band
                    and match["headline_column"] == column
                ]
                output[root_class][band][column] = {
                    "roots_with_match": len({m["root_id"] for m in selected}),
                    "word_root_pairs": len(selected),
                    "ja_prefix_flagged_pairs": sum(m["ja_prefix_contamination"] for m in selected),
                }
                if column == "VOCALIC":
                    output[root_class][band][column]["subtypes"] = {
                        subtype: {
                            "roots_with_match": len({
                                m["root_id"] for m in selected
                                if m["word_initial_spelling"] == subtype
                            }),
                            "word_root_pairs": sum(
                                m["word_initial_spelling"] == subtype for m in selected
                            ),
                        }
                        for subtype in ("U_VOCALIC", "I_VOCALIC")
                    }
    return output


def _null_summary(observed: int, values: list[int], denominator: int) -> dict[str, Any]:
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    ordered = sorted(values)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    z_score = (observed - mean) / std if std else None
    return {
        "observed": observed,
        "observed_rate": round(observed / denominator, 6) if denominator else None,
        "null_mean": round(mean, 4),
        "null_mean_rate": round(mean / denominator, 6) if denominator else None,
        "null_std": round(std, 4),
        "null_p95": p95,
        "relation": "above" if observed > mean else ("equal" if observed == mean else "below"),
        "z_score": round(z_score, 3) if z_score is not None else None,
        "empirical_p": round((1 + sum(v >= observed for v in values)) / (len(values) + 1), 6),
        "enrichment": round(observed / mean, 3) if mean else None,
    }


def run_null_calibration(
    roots: list[dict[str, Any]], words: list[dict[str, Any]],
    observed: dict[str, Any], iterations: int, seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    class_roots = {
        root_class: [root for root in roots if root["class"] == root_class]
        for root_class in ("W_CLASS", "Y_CLASS")
    }
    residuals_by_column: dict[str, list[str]] = defaultdict(list)
    for word in words:
        residuals_by_column[word["headline_column"]].append(word["residual_skeleton"])
    for column, residuals in residuals_by_column.items():
        residuals_by_column[column] = sorted(set(residuals))

    cache: dict[tuple[str, str], str | None] = {}

    def best_band(root_remainder: str, column: str) -> str | None:
        key = (root_remainder, column)
        if key in cache:
            return cache[key]
        best = float("inf")
        for word_remainder in residuals_by_column[column]:
            best = min(best, distance_to_remainder(word_remainder, root_remainder)["distance"])
            if best == 0:
                break
        cache[key] = distance_band(best)
        return cache[key]

    null_values: dict[str, dict[str, dict[str, list[int]]]] = {
        root_class: {
            band: {column: [] for column in ("W", "J", "VOCALIC")}
            for band in ("CANDIDATE", "SPECULATIVE")
        }
        for root_class in ("W_CLASS", "Y_CLASS")
    }
    progress_every = max(1, iterations // 10)
    for iteration in range(iterations):
        for root_class, members in class_roots.items():
            remainders = [root["canonical_skeleton"][1:] for root in members]
            lengths = [len(remainder) for remainder in remainders]
            pool = [radical for remainder in remainders for radical in remainder]
            rng.shuffle(pool)
            cursor = 0
            synthetic: list[str] = []
            for length in lengths:
                synthetic.append("".join(pool[cursor:cursor + length]))
                cursor += length
            counts = {
                band: Counter() for band in ("CANDIDATE", "SPECULATIVE")
            }
            for remainder in synthetic:
                for column in ("W", "J", "VOCALIC"):
                    band = best_band(remainder, column)
                    if band:
                        counts[band][column] += 1
            for band in counts:
                for column in ("W", "J", "VOCALIC"):
                    null_values[root_class][band][column].append(counts[band][column])
        if (iteration + 1) % progress_every == 0 or iteration + 1 == iterations:
            print(f"null calibration: {iteration + 1}/{iterations}", file=sys.stderr)

    summaries: dict[str, Any] = {}
    for root_class, members in class_roots.items():
        summaries[root_class] = {}
        for band in ("CANDIDATE", "SPECULATIVE"):
            summaries[root_class][band] = {}
            for column in ("W", "J", "VOCALIC"):
                real = observed[root_class][band][column]["roots_with_match"]
                summaries[root_class][band][column] = _null_summary(
                    real, null_values[root_class][band][column], len(members)
                )
    return {
        "method": (
            "pool and permute radicals 2+ within each assigned class; preserve initial class and "
            "root-length distribution"
        ),
        "iterations": iterations,
        "seed": seed,
        "bands_are_exclusive": True,
        "thresholds": {"CANDIDATE": "d < 0.3", "SPECULATIVE": "0.3 <= d < 0.5"},
        "class_root_counts": {key: len(value) for key, value in class_roots.items()},
        "summaries": summaries,
        "cache_entries": len(cache),
    }


def control_gates(
    matches: list[dict[str, Any]], control_matches: list[dict[str, Any]],
) -> dict[str, Any]:
    def find_real(word: str, root_class: str | None = None, initial: str | None = None) -> list[dict[str, Any]]:
        return [
            match for match in matches
            if match["word"] == word
            and (root_class is None or match["root_class"] == root_class)
            and (initial is None or match["word_initial_spelling"] == initial)
        ]

    ja_mu = [
        match for match in find_real("JA-MU", "Y_CLASS", "J")
        if collapse_geminates(consonantal_skeleton(match["root"])) == "ym"
    ]
    checks: dict[str, Any] = {
        "JA-MU_Y_CLASS_J": {
            "passed": bool(ja_mu), "lane": "SED_INVENTORY",
            "matches": [{k: m[k] for k in ("root", "distance", "band")} for m in ja_mu],
        }
    }
    expected_sed = {
        "WI-DI-NA": "*wVdVd-",
        "WA-TE": "*wVdVd-",
        "U-QE-TI": "*y/wḳd",
        "WI-TE-JA-MU": None,
    }
    for word, expected_root in expected_sed.items():
        real = [
            match for match in find_real(word)
            if expected_root is not None and match["root"] == expected_root
        ]
        supplemental = [
            match for match in control_matches
            if match["word"] == word and match.get("claimed_root") == "wʿd"
        ]
        checks[f"W_SPOT_{word}"] = {
            "passed": bool(real or supplemental),
            "lane": "SED_INVENTORY" if real else "LEXICON_CLAIM_CONTROL",
            "matches": [
                {key: match.get(key) for key in ("root", "claimed_root", "distance", "band")}
                for match in (real or supplemental)
            ],
        }
    return {
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }


def interpretation(observed: dict[str, Any], null: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    w = observed["W_CLASS"]["CANDIDATE"]["W"]["roots_with_match"]
    j = observed["W_CLASS"]["CANDIDATE"]["J"]["roots_with_match"]
    vocalic = observed["W_CLASS"]["CANDIDATE"]["VOCALIC"]["roots_with_match"]
    yw = observed["Y_CLASS"]["CANDIDATE"]["W"]["roots_with_match"]
    yj = observed["Y_CLASS"]["CANDIDATE"]["J"]["roots_with_match"]
    yv = observed["Y_CLASS"]["CANDIDATE"]["VOCALIC"]["roots_with_match"]
    y_u = observed["Y_CLASS"]["CANDIDATE"]["VOCALIC"]["subtypes"]["U_VOCALIC"]["roots_with_match"]
    y_i = observed["Y_CLASS"]["CANDIDATE"]["VOCALIC"]["subtypes"]["I_VOCALIC"]["roots_with_match"]
    y_control_valid = (yj + y_i) > (yw + y_u) and gates["checks"]["JA-MU_Y_CLASS_J"]["passed"]
    w_null = null["summaries"]["W_CLASS"]["CANDIDATE"]["W"]
    j_null = null["summaries"]["W_CLASS"]["CANDIDATE"]["J"]
    if not y_control_valid:
        outcome = "METHOD_FAILED_CONTROL"
        strength = "none"
        rationale = "Y_CLASS does not skew toward J/I or the JA-MU control failed."
    elif w > j and w_null["empirical_p"] < 0.05:
        outcome = "W_PRESERVED"
        strength = "moderate"
        rationale = "W_CLASS has more W-series than J-series candidate-band root hits."
    elif j > w and j_null["empirical_p"] < 0.05:
        outcome = "Y_SHIFTED"
        strength = "moderate"
        rationale = "W_CLASS has more J-series than W-series candidate-band root hits."
    elif w and j and (w_null["empirical_p"] < 0.05 or j_null["empirical_p"] < 0.05):
        outcome = "MIXED"
        strength = "weak"
        rationale = "Both explicit glide spellings occur and at least one exceeds its null floor."
    else:
        outcome = "INCONCLUSIVE"
        strength = "none"
        rationale = (
            "Explicit W- and J-series candidate counts do not significantly exceed their asymmetric null floors."
        )
    return {
        "outcome": outcome, "strength": strength, "rationale": rationale,
        "y_class_control_valid": y_control_valid,
        "headline_candidate_band": {
            "W_CLASS": {"W": w, "J": j, "VOCALIC": vocalic},
            "Y_CLASS": {"W": yw, "J": yj, "VOCALIC": yv},
        },
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(map(clean, headers)) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    lines.extend("| " + " | ".join(map(clean, row)) + " |" for row in rows)
    return "\n".join(lines)


def render_report(matrix: dict[str, Any]) -> str:
    roots = matrix["root_inventory"]
    observed = matrix["observed"]
    null = matrix["null_calibration"]
    interp = matrix["interpretation"]
    class_counts = Counter(root["class"] for root in roots)
    source_rows = [
        [root_class, class_counts[root_class]]
        for root_class in ("W_CLASS", "Y_CLASS", "AMBIGUOUS")
    ]
    ja_mu_passed = matrix["verification"]["checks"]["JA-MU_Y_CLASS_J"]["passed"]
    lines = [
        "# Initial *w > y Isogloss Sweep",
        "",
        f"Generated `{matrix['manifest']['generated_at']}` by `wy_isogloss_sweep.py` v{SCRIPT_VERSION}.",
        "",
        ("The computation is mechanical and corpus-internal. Readings inherit the Gordon–di Mino framework's "
        "confidence taxonomy; matches are candidates, not decipherments."),
        "",
        "## 1. Root inventory",
        "",
        markdown_table(["Class", "Deduplicated roots"], source_rows),
        "",
        (f"The sweep selected {len(roots)} SED rows after deduplicating on the NFC-normalized `Proto-Semitic` "
        "string. Duplicate SED Numbers remain attached to each record in `wy_matrix.json`."),
        "",
        ("Classification uses the `Analogues` branch pattern, not the starred reconstruction alone. A W_CLASS call "
        "requires a parsed non-NWS w-reflex and no contradictory non-NWS y-reflex; a Y_CLASS call requires only "
        "y-reflexes including a non-NWS control. Everything else is AMBIGUOUS."),
        "",
        "### Ambiguous roots",
        "",
        markdown_table(
            ["PS form", "Number(s)", "Meaning", "Reason"],
            [[r["ps"], ", ".join(r["numbers"]), "; ".join(r["meanings"]), r["class_rationale"]]
             for r in roots if r["class"] == "AMBIGUOUS"],
        ),
        "",
        "## 2. Null calibration (reported before interpretation)",
        "",
        (f"The null uses {null['iterations']:,} permutations with seed `{null['seed']}`. It pools and permutes "
        "radicals 2+ within each assigned class, while preserving the initial class and each root's radical-count "
        "slot. CANDIDATE (`d < 0.3`) and SPECULATIVE (`0.3 ≤ d < 0.5`) are exclusive bands."),
        "",
    ]
    comparison_rows: list[list[Any]] = []
    for root_class in ("W_CLASS", "Y_CLASS"):
        for band in ("CANDIDATE", "SPECULATIVE"):
            for column in ("W", "J", "VOCALIC"):
                obs = observed[root_class][band][column]
                cal = null["summaries"][root_class][band][column]
                comparison_rows.append([
                    root_class, band, column, obs["roots_with_match"],
                    f"{cal['null_mean']:.2f}", cal["null_p95"], cal["relation"],
                    cal["empirical_p"], cal["enrichment"], obs["word_root_pairs"],
                ])
    lines.extend([
        markdown_table(
            ["Root class", "Band", "Spelling", "Observed roots", "Null mean", "Null p95", "Vs null",
             "Empirical p", "Enrichment", "Word-root pairs"],
            comparison_rows,
        ),
        "",
        ("Counts are unique roots with at least one match; the last column gives all word-root pairs. Vocalic "
        "combines U-carry for /w/ and I-carry for /y/. No initial *w-loss path was added because the spelling "
        "rules do not license one."),
        "",
        "## 3. Headline result",
        "",
        f"**Outcome: {interp['outcome']} ({interp['strength']}).** {interp['rationale']}",
        "",
        markdown_table(
            ["Class", "CANDIDATE W", "CANDIDATE J", "CANDIDATE vocalic", "SPECULATIVE W", "SPECULATIVE J",
             "SPECULATIVE vocalic"],
            [[root_class,
              observed[root_class]["CANDIDATE"]["W"]["roots_with_match"],
              observed[root_class]["CANDIDATE"]["J"]["roots_with_match"],
              observed[root_class]["CANDIDATE"]["VOCALIC"]["roots_with_match"],
              observed[root_class]["SPECULATIVE"]["W"]["roots_with_match"],
              observed[root_class]["SPECULATIVE"]["J"]["roots_with_match"],
              observed[root_class]["SPECULATIVE"]["VOCALIC"]["roots_with_match"]]
             for root_class in ("W_CLASS", "Y_CLASS")],
        ),
        "",
        (f"Y_CLASS control validity: **{'PASS' if interp['y_class_control_valid'] else 'FAIL'}**. "
        f"JA-MU ~ *yamm-: **{'PASS' if ja_mu_passed else 'FAIL'}**."),
        "",
        "### Candidate match ledger",
        "",
        markdown_table(
            ["Class", "Root", "Word", "Spelling", "d", "Band", "Lexicon", "JA-prefix flag"],
            [[m["root_class"], m["root"], m["word"], m["word_initial_spelling"], m["distance"], m["band"],
              "agree" if m["lexicon_root_agreement"] else ("conflict" if m["lexicon_root_conflict"] else "none"),
              "yes" if m["ja_prefix_contamination"] else "no"]
             for m in matrix["candidate_matches"] if m["root_class"] in {"W_CLASS", "Y_CLASS"}],
        ),
        "",
        "## 4. Existing-claims audit",
        "",
        ("The 2×3 table includes only claims that join to a decisive SED class and use W-series, J-series, or an "
        "initial U/I vocalic carry. Logograms and other initial spellings remain in the per-entry ledger but do "
        "not enter the 2×3 cells."),
        "",
        markdown_table(
            ["SED class", "W-series", "J-series", "Vocalic carry"],
            [[root_class,
              matrix["existing_claims"]["table_2x3"][root_class]["W"],
              matrix["existing_claims"]["table_2x3"][root_class]["J"],
              matrix["existing_claims"]["table_2x3"][root_class]["VOCALIC"]]
             for root_class in ("W_CLASS", "Y_CLASS")],
        ),
        "",
        markdown_table(
            ["Word", "Claimed root", "SED root(s)", "SED class", "Spelling", "Confidence", "Discrepancy"],
            [[r["word"], r["claimed_root"], ", ".join(r["sed_roots"]) or "unjoined", r["sed_class"],
              r["spelling_bucket"], r["confidence"],
              "claim/class conflict" if r["branch_pattern_disagrees_with_claim"]
              else ("unresolved" if r["branch_pattern_unresolved"] else "no")]
             for r in matrix["existing_claims"]["rows"]],
        ),
        "",
        ("The WI-TE-JA-MU control is reported in a separate lexicon-control lane: √w-ʿ-d is absent as an "
        "initial-*w/*y SED reconstruction (the related SED nominal is *mōʕēd-). It is matched mechanically but "
        "excluded from the inventory, headline, and null."),
        "",
        "## 5. Interpretation and caveats",
        "",
        ("All three outcomes remain logically available: a null-adjusted W excess supports w-preservation; a "
        "null-adjusted J excess among W_CLASS roots supports the NWS shift; appreciable support for both is a "
        "mixed/dialect-contact result. The outcome above follows only the explicit rule recorded in "
        "`wy_matrix.json`."),
        "",
        "Standing limitations:",
        "",
        ("- CV spelling underdetermines consonants and vowels; radical-2/3 matches are candidate generation, not "
        "lexical proof."),
        ("- Initial U can carry /w/ (U-QE-TI precedent), so vocalic evidence must not be silently counted as "
        "explicit W-series."),
        ("- JA- is also a productive verbal prefix. Every plausibly prefixal JA candidate is flagged in the ledger; "
        "the unfiltered counts remain directly comparable to the frequency-asymmetric null."),
        "- `sign_values.json` gives JU the value /lu/, so JU is not treated as J-series; *28B/JI supplies /yi/.",
        ("- Contact-lexicon joins verify daughter y-reflexes but do not override the SED `Analogues` "
        "classification."),
        "",
        "## 6. Verification gates",
        "",
        markdown_table(
            ["Gate", "Status", "Lane"],
            [[name, "PASS" if value["passed"] else "FAIL", value["lane"]]
             for name, value in matrix["verification"]["checks"].items()],
        ),
        "",
        "## Appendix A. Complete deduplicated root inventory",
        "",
        markdown_table(
            ["Class", "PS form", "Number(s)", "Meaning", "NWS contact y hits"],
            [[r["class"], r["ps"], ", ".join(r["numbers"]), "; ".join(r["meanings"]),
              ", ".join(r["nws_contact_verification"]["languages_with_hit"]) or "none"]
             for r in roots],
        ),
        "",
    ])
    return "\n".join(lines)


def write_outputs(out_dir: Path, matrix: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "wy_matrix.json"
    report_path = out_dir / "REPORT.md"
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(matrix), encoding="utf-8")


def run(out_dir: Path, iterations: int, seed: int) -> dict[str, Any]:
    input_paths = {
        name: require(path, name)
        for name, path in {
            "semitic_roots.json": SEMITIC_ROOTS_DATA / "semitic_roots.json",
            "lexicon.json": LINEAR_A_DATA / "lexicon.json",
            "corpus.json": LINEAR_A_DATA / "corpus.json",
            "sign_values.json": LINEAR_A_DATA / "sign_values.json",
            **{f"contact/{name}": CONTACT_DATA / name for name in CONTACT_FILES},
        }.items()
    }
    before_hashes = {name: sha256(path) for name, path in input_paths.items()}
    semitic_roots = roots_records(json.loads(input_paths["semitic_roots.json"].read_text(encoding="utf-8")))
    lexicon = json.loads(input_paths["lexicon.json"].read_text(encoding="utf-8"))["entries"]
    corpus = json.loads(input_paths["corpus.json"].read_text(encoding="utf-8"))
    sign_inventory = load_sign_inventory(input_paths["sign_values.json"])
    contact_index = ContactIndex(CONTACT_DATA)
    roots = build_root_inventory(semitic_roots, contact_index)
    words, _lex_by_word, word_stats = build_word_inventory(lexicon, corpus, sign_inventory)
    words_by_name = {word["word"]: word for word in words}
    matches = match_words_to_roots(roots, words)
    claims, table_2x3, claim_controls = audit_existing_claims(
        lexicon, roots, sign_inventory, words_by_name
    )
    observed = observed_counts(matches)
    null = run_null_calibration(roots, words, observed, iterations, seed)
    gates = control_gates(matches, claim_controls)
    after_hashes = {name: sha256(path) for name, path in input_paths.items()}
    if before_hashes != after_hashes:
        raise RuntimeError("input data changed during the read-only sweep")
    matrix: dict[str, Any] = {
        "manifest": {
            "generated_by": "wy_isogloss_sweep.py",
            "script_version": SCRIPT_VERSION,
            "generated_at": utc_now(),
            "data_dir": str(DATA),
            "out_dir": str(out_dir),
            "python": sys.version.split()[0],
            "input_hashes": before_hashes,
            "data_integrity_after_run": "UNCHANGED",
            "confidence_bands": {
                "CANDIDATE": "d < 0.3",
                "SPECULATIVE": "0.3 <= d < 0.5",
                "exclusive": True,
            },
            "counting_unit": "unique roots with >=1 match; word-root pairs also reported",
        },
        "sign_inventory": sign_inventory,
        "corpus_inventory": word_stats,
        "root_inventory_summary": dict(Counter(root["class"] for root in roots)),
        "root_inventory": roots,
        "candidate_matches": matches,
        "observed": observed,
        "existing_claims": {
            "table_2x3": table_2x3,
            "rows": claims,
            "lexicon_control_matches_excluded_from_headline": claim_controls,
        },
        "null_calibration": null,
        "verification": gates,
    }
    matrix["interpretation"] = interpretation(observed, null, gates)
    write_outputs(out_dir, matrix)
    return matrix


def concise_summary(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "root_inventory_summary": matrix["root_inventory_summary"],
        "headline_candidate_band": matrix["interpretation"]["headline_candidate_band"],
        "outcome": matrix["interpretation"]["outcome"],
        "strength": matrix["interpretation"]["strength"],
        "null_candidate_band": {
            root_class: matrix["null_calibration"]["summaries"][root_class]["CANDIDATE"]
            for root_class in ("W_CLASS", "Y_CLASS")
        },
        "verification": matrix["verification"],
    }


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="Output directory (outside the repository)")
    parser.add_argument("--iterations", type=int, default=1000, help="Null permutations (default: 1000)")
    parser.add_argument("--quick", action="store_true", help="Development calibration with 200 permutations")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Reproducible random seed")
    parser.add_argument("--json", action="store_true", help="Print a concise JSON summary")
    parser.add_argument(
        "--allow-failed-controls", action="store_true",
        help="Write diagnostics and exit successfully even if a required control fails",
    )
    args = parser.parse_args()
    iterations = 200 if args.quick else args.iterations
    if iterations < 2:
        parser.error("at least two null iterations are required")
    matrix = run(args.out.expanduser().resolve(), iterations, args.seed)
    summary = concise_summary(matrix)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"roots: {matrix['root_inventory_summary']}")
        print(f"headline: {matrix['interpretation']['headline_candidate_band']}")
        print(f"outcome: {matrix['interpretation']['outcome']} ({matrix['interpretation']['strength']})")
        print(f"controls: {'PASS' if matrix['verification']['passed'] else 'FAIL'}")
        print(f"wrote: {args.out / 'wy_matrix.json'}")
        print(f"wrote: {args.out / 'REPORT.md'}")
    if not matrix["verification"]["passed"] and not args.allow_failed_controls:
        raise SystemExit("required control gate failed; inspect wy_matrix.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
