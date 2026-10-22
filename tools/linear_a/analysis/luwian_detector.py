#!/usr/bin/env python3
"""Luwian Detector — identifies Linear A corpus words closer to Luwian than NWS.

Part of a bilingual contact-zone model for the Linear A decipherment.
Scores every polysyllabic corpus word against both the NWS (Semitic) and Luwian
(Anatolian) root inventories using weighted Levenshtein distance with
language-specific phonological cost tables. Words whose Luwian distance is both
below a threshold and lower than their NWS distance are flagged as candidate
Anatolian elements in the corpus.

Usage:
    uv run tools/linear_a/analysis/luwian_detector.py
    uv run tools/linear_a/analysis/luwian_detector.py --json
    uv run tools/linear_a/analysis/luwian_detector.py --out luwian_identifications.json
    uv run tools/linear_a/analysis/luwian_detector.py --threshold 0.4 --min-advantage -0.1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.phonetics import (
    LUWIAN_DISTANCES,
    SEMITIC_DISTANCES,
    weighted_levenshtein,
)
from ...core.semitic_root_schema import roots_records
from ...core.skeleton import extract_skeleton
from ...paths import CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
SEMITIC_ROOTS_PATH = SEMITIC_ROOTS_DATA / "semitic_roots.json"
LUWIAN_ROOTS_PATH = LINEAR_A_DATA / "luwian_roots.json"
ANATOLIAN_LEXICON_PATH = CONTACT_DATA / "anatolian_lexicon.jsonl"


# ---------------------------------------------------------------------------
# Root extraction
# ---------------------------------------------------------------------------

def _extract_consonantal_root(form: str) -> str:
    """Extract consonantal root from a proto-form string.

    Strips reconstructive markers (*), parenthetical glosses, trailing digits,
    alternate forms (/*), slashes, hyphens, underscores, and all vowels.
    """
    s = form.strip()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"^\*", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\d+$", "", s)
    s = s.split(",")[0].split(" ")[0]
    if "/*" in s:
        s = s.split("/*")[0]
    s = s.replace("/", "").replace("-", "").replace("_", "")
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    root = "".join(c for c in s if c.lower() not in vowels and c not in "* V")
    return root.lower()


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_corpus() -> dict[str, dict[str, Any]]:
    """Load the Linear A inscription corpus."""
    return json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))


def extract_unique_words(corpus: dict[str, dict[str, Any]]) -> dict[str, dict]:
    """Extract unique polysyllabic words with frequency and site metadata.

    Returns {word: {"frequency": int, "sites": set[str], "positions": list[str]}}
    where positions tracks whether the word appears in header vs body.
    """
    word_info: dict[str, dict] = {}
    for insc_id, inscription in corpus.items():
        # Use site prefix from inscription_id (e.g. "HT" from "HT1")
        site_prefix = re.match(r"[A-Z]+", insc_id)
        site = site_prefix.group() if site_prefix else ""

        words = inscription.get("transliteratedWords", [])
        for idx, w in enumerate(words):
            if not isinstance(w, str):
                continue
            # Polysyllabic words only: has "-", not starting "*", not all digits
            if "-" not in w:
                continue
            if w.startswith("*"):
                continue
            if w.replace("-", "").isdigit():
                continue

            if w not in word_info:
                word_info[w] = {"frequency": 0, "sites": set(), "positions": []}
            word_info[w]["frequency"] += 1
            word_info[w]["sites"].add(site)
            # Rough header detection: first non-newline word in the tablet
            non_meta = [x for x in words[:idx] if isinstance(x, str) and x != "\n" and "-" in x]
            if len(non_meta) == 0:
                word_info[w]["positions"].append("header")
            else:
                word_info[w]["positions"].append("body")

    return word_info


def load_nws_roots() -> list[str]:
    """Load NWS (Semitic) consonantal roots."""
    data = json.loads(require(SEMITIC_ROOTS_PATH, SEMITIC_ROOTS_PATH.name).read_text(encoding="utf-8"))
    roots = []
    for entry in roots_records(data):
        form = entry.get("Proto-Semitic", "")
        if form:
            root = _extract_consonantal_root(form)
            if root and 1 <= len(root) <= 5:
                roots.append(root)
    return sorted(set(roots))


def load_luwian_roots() -> list[str]:
    """Load Luwian consonantal roots."""
    data = json.loads(require(LUWIAN_ROOTS_PATH, LUWIAN_ROOTS_PATH.name).read_text(encoding="utf-8"))
    roots = []
    for entry in data:
        form = entry.get("Consonantal_Root", "")
        if form:
            root = form.strip().lower()
            if root and 1 <= len(root) <= 5:
                roots.append(root)
    return sorted(set(roots))


def load_anatolian_lexicon() -> list[dict]:
    """Load the Anatolian reference lexicon (known Anatolian forms); [] when it is not in the checkout."""
    if not ANATOLIAN_LEXICON_PATH.exists():
        return []
    entries = []
    for line in ANATOLIAN_LEXICON_PATH.read_text(encoding="utf-8").strip().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def load_existing_identifications(path: Path) -> dict:
    """Load an identifications file written by an earlier run, or an empty one."""
    if not path.exists():
        return {"metadata": {}, "identifications": []}
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def best_root_match(
    skeleton: str,
    roots: list[str],
    distances: dict[tuple[str, str], float],
) -> tuple[str, float]:
    """Find the root with the lowest weighted Levenshtein distance to a skeleton.

    Returns (best_root, best_distance).
    """
    best_root = ""
    best_dist = float("inf")
    for root in roots:
        d = weighted_levenshtein(skeleton, root, distances=distances)
        if d < best_dist:
            best_dist = d
            best_root = root
    return best_root, best_dist


def check_anatolian_lexicon(skeleton: str, lexicon: list[dict]) -> dict | None:
    """Check if a skeleton directly matches any anatolian_lexicon entry.

    Returns the matching entry or None.
    """
    for entry in lexicon:
        for key in entry.get("match_keys", []):
            # Extract consonantal skeleton from the match key
            key_skel = _extract_consonantal_root(key)
            if key_skel and key_skel == skeleton:
                return entry
    return None


def classify_word(
    word: str,
    word_meta: dict,
    lexicon_match: dict | None,
) -> str:
    """Classify a flagged word by type.

    - hapax in header position -> likely anthroponym
    - Direct anatolian_lexicon match -> use that entry's semantic_domain
    - Otherwise -> unclassified
    """
    if lexicon_match:
        domains = lexicon_match.get("semantic_domain", [])
        if domains:
            return domains[0]
        return "unclassified"

    freq = word_meta["frequency"]
    positions = word_meta["positions"]
    if freq == 1 and "header" in positions:
        return "anthroponym"

    return "unclassified"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_detector(
    threshold: float = 0.5,
    min_advantage: float = 0.0,
) -> list[dict]:
    """Run the Luwian detector pipeline.

    Args:
        threshold: Maximum Luwian distance to flag a word.
        min_advantage: Minimum (luwian_dist - nws_dist) gap. Negative values
            mean "Luwian must be at least this much closer than NWS."
            Default 0.0 means any word where Luwian distance < NWS distance.

    Returns list of identification dicts, sorted by Luwian distance ascending.
    """
    corpus = load_corpus()
    word_info = extract_unique_words(corpus)
    nws_roots = load_nws_roots()
    luwian_roots = load_luwian_roots()
    lexicon = load_anatolian_lexicon()

    flagged: list[dict] = []

    for word, meta in sorted(word_info.items()):
        skeleton = extract_skeleton(word)
        if not skeleton or len(skeleton) < 2:
            continue

        # Score against both root inventories
        nws_root, nws_dist = best_root_match(skeleton, nws_roots, SEMITIC_DISTANCES)
        luw_root, luw_dist = best_root_match(skeleton, luwian_roots, LUWIAN_DISTANCES)

        # Flag condition: Luwian closer than NWS AND below threshold
        advantage = luw_dist - nws_dist  # negative means Luwian is closer
        if luw_dist < nws_dist and luw_dist <= threshold and advantage <= min_advantage:
            lexicon_match = check_anatolian_lexicon(skeleton, lexicon)
            classification = classify_word(word, meta, lexicon_match)

            evidence_parts = []
            if lexicon_match:
                evidence_parts.append(
                    f"Direct anatolian_lexicon match: {lexicon_match.get('form_original', '')} "
                    f"({lexicon_match.get('meaning', '')})"
                )
            if meta["frequency"] == 1:
                evidence_parts.append("Hapax legomenon")
            if "header" in meta["positions"]:
                evidence_parts.append("Appears in tablet header position")

            entry = {
                "word": word,
                "skeleton": skeleton,
                "classification": classification,
                "confidence": "CANDIDATE",
                "luwian_match": {
                    "root": luw_root,
                    "distance": round(luw_dist, 4),
                    "distance_table": "LUWIAN_DISTANCES",
                },
                "nws_match": {
                    "root": nws_root,
                    "distance": round(nws_dist, 4),
                    "distance_table": "SEMITIC_DISTANCES",
                },
                "corpus_frequency": meta["frequency"],
                "sites": sorted(meta["sites"]),
                "tablet_positions": sorted(set(meta["positions"])),
                "evidence_notes": "; ".join(evidence_parts) if evidence_parts else "",
                "status": "proposed",
                "added": datetime.now(UTC).strftime("%Y-%m-%d"),
            }
            flagged.append(entry)

    # Sort by Luwian distance ascending
    flagged.sort(key=lambda e: e["luwian_match"]["distance"])
    return flagged


def merge_identifications(existing: dict, new_entries: list[dict]) -> tuple[dict, int]:
    """Merge new identifications into existing file, avoiding duplicates.

    Duplicates are detected by matching on the 'word' field. New entries for
    words already present are skipped (existing entries preserved).
    """
    existing_words = {e["word"] for e in existing.get("identifications", [])}
    merged = list(existing.get("identifications", []))
    added = 0
    for entry in new_entries:
        if entry["word"] not in existing_words:
            merged.append(entry)
            existing_words.add(entry["word"])
            added += 1

    result = dict(existing)
    result["identifications"] = merged
    result["metadata"]["updated"] = datetime.now(UTC).strftime("%Y-%m-%d")
    return result, added


def format_table(entries: list[dict]) -> str:
    """Format flagged entries as a human-readable table."""
    if not entries:
        return "No words flagged as Luwian candidates."

    lines = []
    # Header
    lines.append(
        f"{'Word':<22} {'Skel':<8} {'Luw Root':<10} {'Luw Dist':>8} "
        f"{'NWS Root':<10} {'NWS Dist':>8} {'Freq':>4} {'Sites':<10} {'Class':<14}"
    )
    lines.append("-" * 104)

    for e in entries:
        lm = e["luwian_match"]
        nm = e["nws_match"]
        lines.append(
            f"{e['word']:<22} {e['skeleton']:<8} {lm['root']:<10} {lm['distance']:>8.4f} "
            f"{nm['root']:<10} {nm['distance']:>8.4f} {e['corpus_frequency']:>4} "
            f"{','.join(e['sites']):<10} {e['classification']:<14}"
        )

    lines.append("")
    lines.append(f"Total candidates: {len(entries)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

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
        description="Identify Linear A corpus words closer to Luwian than NWS roots.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Write the identifications to this file, merged into what it already holds.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Max Luwian distance to flag (default: 0.5).",
    )
    parser.add_argument(
        "--min-advantage",
        type=float,
        default=0.0,
        help="Min (luwian - nws) gap; negative means Luwian must be closer by at least this much (default: 0.0).",
    )
    args = parser.parse_args()

    flagged = run_detector(
        threshold=args.threshold,
        min_advantage=args.min_advantage,
    )

    if args.json:
        print(json.dumps(flagged, indent=2, ensure_ascii=False))
    else:
        print(format_table(flagged))

    if args.out:
        existing = load_existing_identifications(args.out)
        merged, added = merge_identifications(existing, flagged)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nSaved to {args.out} ({added} new entries added, "
              f"{len(merged['identifications'])} total)")


if __name__ == "__main__":
    sys.exit(main())
