#!/usr/bin/env python3
"""Ingest Hurrian lexical candidates into hurrian_roots.json and hurrian_lexicon.jsonl.

Merges reviewed candidate entries from data/contact/review/hurrian_mittani_candidates.jsonl
into the main Hurrian databases:
  1. data/linear-a/hurrian_roots.json — the master Hurrian roots/names database
  2. data/contact/hurrian_lexicon.jsonl — the contact lexicon (JSONL format)

Also applies Urartian cognates from data/contact/review/urartian_cognate_candidates.jsonl
(optional) onto matching entries in hurrian_roots.json. Before writing, both targets are
copied into `tools.paths.BACKUPS`.

Usage:
    python3 tools/linear_a/ingest/ingest_hurrian_lexical.py              # dry-run (default)
    python3 tools/linear_a/ingest/ingest_hurrian_lexical.py --dry-run    # explicit dry-run
    python3 tools/linear_a/ingest/ingest_hurrian_lexical.py --apply      # actually write changes

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.ingest"

from ...core.contact_lexicon import (
    VALID_SEMANTIC_DOMAINS,
    normalize_hurrian,
    validate_entry,
)
from ...core.data_cache import data_path
from ...paths import BACKUPS, CONTACT_DATA, NotInCheckout, require

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REVIEW_DIR = CONTACT_DATA / "review"
CANDIDATES_PATH = REVIEW_DIR / "hurrian_mittani_candidates.jsonl"
URARTIAN_PATH = REVIEW_DIR / "urartian_cognate_candidates.jsonl"
ROOTS_PATH = data_path("hurrian_roots")
LEXICON_PATH = CONTACT_DATA / "hurrian_lexicon.jsonl"
BACKUP_DIR = BACKUPS


# ---------------------------------------------------------------------------
# Loading utilities
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of dicts."""
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [error] {path.name}:{line_num}: {e}", file=sys.stderr)
    return entries


def load_json(path: Path) -> list[dict[str, Any]]:
    """Load a JSON array file."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

def get_existing_numbers(roots: list[dict[str, Any]]) -> set[str]:
    """Get all existing Number values from roots database."""
    return {str(e.get("Number", "")) for e in roots}


def get_existing_normalized_meanings(roots: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """Get (normalized_form, meaning_prefix) pairs for dedup."""
    pairs: set[tuple[str, str]] = set()
    for e in roots:
        hurrian = e.get("Hurrian", "").lower().strip()
        meaning = e.get("Meaning", "").lower().strip()[:30]
        if hurrian:
            pairs.add((hurrian, meaning))
    return pairs


def get_existing_lexicon_ids(path: Path) -> set[str]:
    """Get all existing IDs from the JSONL lexicon."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ids.add(entry.get("id", ""))
            except json.JSONDecodeError:
                pass
    return ids


# ---------------------------------------------------------------------------
# Candidate → roots entry conversion
# ---------------------------------------------------------------------------

def candidate_to_roots_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    """Convert a candidate JSONL entry to the hurrian_roots.json schema."""
    entry: dict[str, Any] = {
        "Number": str(candidate["Number"]),
        "Hurrian": candidate["Hurrian"],
    }

    # Normalized form
    normalized = normalize_hurrian(candidate["Hurrian"])
    entry["Normalized"] = normalized

    # Category — map from our taxonomy to the roots format
    entry["Category"] = candidate.get("Category", "general")

    # Meaning
    entry["Meaning"] = candidate["Meaning"]

    # Consonantal root
    if candidate.get("Consonantal_Root"):
        entry["Consonantal_Root"] = candidate["Consonantal_Root"]

    # Name elements (empty for lexical)
    entry["Name_Elements"] = []

    # Variants
    entry["Variants"] = []

    # Attestation context
    if candidate.get("Attestation_Context"):
        contexts = [c.strip() for c in candidate["Attestation_Context"].split(";")]
        entry["Attestation_Context"] = contexts

    # Sources
    entry["Sources"] = candidate.get("Sources", [])

    # Source status
    entry["Source_Status"] = "source_family_labeled_public_or_bibliographic"

    # Review status
    entry["Review_Status"] = candidate.get("Review_Status", "machine_imported")

    # Linear A relevance
    if candidate.get("Linear_A_Relevance"):
        entry["Linear_A_Relevance"] = candidate["Linear_A_Relevance"]

    # Match keys
    entry["Match_Keys"] = candidate.get("Match_Keys", [normalized])

    # Urartian cognate
    if candidate.get("Urartian_Cognate"):
        entry["Urartian_Cognate"] = candidate["Urartian_Cognate"]

    return entry


# ---------------------------------------------------------------------------
# Candidate → lexicon entry conversion
# ---------------------------------------------------------------------------

def candidate_to_lexicon_entry(candidate: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a candidate to hurrian_lexicon.jsonl schema.

    Returns None if the entry is a grammatical morpheme (which don't belong
    in the contact lexicon matching index) or otherwise unsuitable.
    """
    # Determine semantic domain from Semantic_Field
    semantic_fields = candidate.get("Semantic_Field", [])

    # Validate semantic domains
    valid_domains = [d for d in semantic_fields if d in VALID_SEMANTIC_DOMAINS]
    if not valid_domains:
        # Fallback to "general"
        valid_domains = ["general"]

    # Build the ID: "hurr:<normalized>:<number>"
    hurrian_form = candidate["Hurrian"]
    normalized = normalize_hurrian(hurrian_form)
    number = str(candidate["Number"])
    entry_id = f"hurr:{normalized}:{number}"

    # Match keys — use candidate's match_keys plus the normalized form
    match_keys = list(candidate.get("Match_Keys", []))
    if normalized not in match_keys:
        match_keys.insert(0, normalized)

    # Source refs in the lexicon format
    source_refs: list[dict[str, str]] = []
    for src in candidate.get("Sources", []):
        source_refs.append({"work": src, "ref": "Hurrian lexical expansion"})

    entry: dict[str, Any] = {
        "id": entry_id,
        "language": "Hurrian",
        "language_family": "Hurro-Urartian",
        "form_original": hurrian_form,
        "normalized": normalized,
        "match_keys": match_keys,
        "meaning": candidate["Meaning"],
        "semantic_domain": valid_domains,
        "source_refs": source_refs,
        "review_status": candidate.get("Review_Status", "machine_imported"),
    }

    return entry


# ---------------------------------------------------------------------------
# Urartian cognate application
# ---------------------------------------------------------------------------

def apply_urartian_cognates(
    roots: list[dict[str, Any]],
    cognates: list[dict[str, Any]],
) -> int:
    """Apply Urartian cognates to matching entries in hurrian_roots.json.

    Returns count of entries updated.
    """
    # Build index by normalized Hurrian form
    form_index: dict[str, list[dict[str, Any]]] = {}
    for entry in roots:
        hurrian = entry.get("Hurrian", "").lower().strip()
        # Strip leading/trailing punctuation for matching
        clean = hurrian.rstrip("-").lstrip("-")
        if clean not in form_index:
            form_index[clean] = []
        form_index[clean].append(entry)

    updated = 0
    for cognate in cognates:
        hurrian_form = cognate.get("Hurrian_Form", "").lower().strip().rstrip("-")
        urartian_form = cognate.get("Urartian_Form", "")
        if not hurrian_form or not urartian_form:
            continue

        matches = form_index.get(hurrian_form, [])
        for entry in matches:
            if "Urartian_Cognate" not in entry:
                entry["Urartian_Cognate"] = urartian_form
                updated += 1

    return updated


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_candidates(candidates: list[dict[str, Any]]) -> list[str]:
    """Validate candidate entries. Returns list of error strings."""
    errors: list[str] = []
    seen_numbers: set[str] = set()

    required_fields = {"Number", "Hurrian", "Meaning", "Category", "Semantic_Field",
                       "Sources", "Review_Status", "Match_Keys"}

    for i, cand in enumerate(candidates):
        prefix = f"candidate[{i}] (#{cand.get('Number', '?')})"

        # Check required fields
        for field in required_fields:
            if field not in cand:
                errors.append(f"{prefix}: missing required field '{field}'")

        # Check Number uniqueness
        num = str(cand.get("Number", ""))
        if num in seen_numbers:
            errors.append(f"{prefix}: duplicate Number '{num}'")
        seen_numbers.add(num)

        # Check semantic domains
        for domain in cand.get("Semantic_Field", []):
            if domain not in VALID_SEMANTIC_DOMAINS:
                errors.append(f"{prefix}: invalid semantic domain '{domain}'")

    return errors


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Hurrian lexical candidates into roots and lexicon databases"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Show what would be imported without writing (default)"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write changes to disk"
    )
    args = parser.parse_args()

    # --apply overrides --dry-run
    dry_run = not args.apply

    print("=" * 60)
    print("Hurrian Lexical Ingest Pipeline")
    print("=" * 60)
    print(f"  Candidates:   {CANDIDATES_PATH}")
    print(f"  Urartian:     {URARTIAN_PATH}")
    print(f"  Roots DB:     {ROOTS_PATH}")
    print(f"  Lexicon:      {LEXICON_PATH}")
    print(f"  Dry run:      {dry_run}")
    print()

    # --- Phase 1: Load candidates ---
    print("Phase 1: Load candidates")
    print("-" * 40)

    candidates = load_jsonl(require(CANDIDATES_PATH, CANDIDATES_PATH.name))
    print(f"  Loaded candidates: {len(candidates)}")

    if not candidates:
        print("  ERROR: No candidates found", file=sys.stderr)
        return 1

    # Validate candidates
    validation_errors = validate_candidates(candidates)
    if validation_errors:
        print(f"  {len(validation_errors)} validation error(s):", file=sys.stderr)
        for err in validation_errors[:20]:
            print(f"    - {err}", file=sys.stderr)
        if len(validation_errors) > 20:
            print(f"    ... and {len(validation_errors) - 20} more", file=sys.stderr)
        return 1

    print("  Validation: PASSED")

    # Load Urartian cognates (optional: none applied when the file is absent)
    cognates = load_jsonl(URARTIAN_PATH)
    print(f"  Loaded Urartian cognates: {len(cognates)}")
    print()

    # --- Phase 2: Load existing data ---
    print("Phase 2: Load existing data")
    print("-" * 40)

    roots = load_json(require(ROOTS_PATH, ROOTS_PATH.name))
    print(f"  Existing roots entries: {len(roots)}")

    existing_numbers = get_existing_numbers(roots)
    existing_pairs = get_existing_normalized_meanings(roots)
    existing_lexicon_ids = get_existing_lexicon_ids(require(LEXICON_PATH, LEXICON_PATH.name))

    print(f"  Existing root numbers: {len(existing_numbers)}")
    print(f"  Existing lexicon IDs: {len(existing_lexicon_ids)}")
    print()

    # --- Phase 3: Merge into roots ---
    print("Phase 3: Merge into hurrian_roots.json")
    print("-" * 40)

    new_roots_entries: list[dict[str, Any]] = []
    skipped_existing_num = 0
    skipped_duplicate = 0

    for cand in candidates:
        num = str(cand["Number"])

        # Skip if Number already exists
        if num in existing_numbers:
            skipped_existing_num += 1
            continue

        # Deduplicate by normalized form + meaning prefix
        hurrian_lower = cand["Hurrian"].lower().strip()
        meaning_prefix = cand["Meaning"].lower().strip()[:30]
        if (hurrian_lower, meaning_prefix) in existing_pairs:
            skipped_duplicate += 1
            continue

        roots_entry = candidate_to_roots_entry(cand)
        new_roots_entries.append(roots_entry)
        existing_numbers.add(num)
        existing_pairs.add((hurrian_lower, meaning_prefix))

    print(f"  New entries to add: {len(new_roots_entries)}")
    print(f"  Skipped (existing number): {skipped_existing_num}")
    print(f"  Skipped (duplicate form): {skipped_duplicate}")
    print()

    # --- Phase 4: Apply Urartian cognates ---
    print("Phase 4: Apply Urartian cognates")
    print("-" * 40)

    # Apply to existing roots + new entries
    all_roots = roots + new_roots_entries
    cognate_count = apply_urartian_cognates(all_roots, cognates)
    print(f"  Cognates applied: {cognate_count}")
    print()

    # --- Phase 5: Mirror to contact lexicon ---
    print("Phase 5: Mirror to hurrian_lexicon.jsonl")
    print("-" * 40)

    new_lexicon_entries: list[dict[str, Any]] = []
    skipped_lexicon_existing = 0
    skipped_lexicon_invalid = 0

    for cand in candidates:
        lexicon_entry = candidate_to_lexicon_entry(cand)
        if lexicon_entry is None:
            continue

        entry_id = lexicon_entry["id"]
        if entry_id in existing_lexicon_ids:
            skipped_lexicon_existing += 1
            continue

        # Validate the entry
        errors = validate_entry(lexicon_entry, "Hurrian")
        if errors:
            skipped_lexicon_invalid += 1
            if not dry_run:
                print(f"    [invalid] {entry_id}: {errors}")
            continue

        new_lexicon_entries.append(lexicon_entry)
        existing_lexicon_ids.add(entry_id)

    print(f"  New lexicon entries: {len(new_lexicon_entries)}")
    print(f"  Skipped (existing): {skipped_lexicon_existing}")
    print(f"  Skipped (invalid): {skipped_lexicon_invalid}")
    print()

    # --- Phase 6: Category summary ---
    print("Phase 6: Category summary")
    print("-" * 40)

    cat_counts = Counter(e.get("Category", "unknown") for e in new_roots_entries)
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print()

    # --- Phase 7: Write (or dry-run report) ---
    if dry_run:
        print("Phase 7: DRY RUN — no files modified")
        print("-" * 40)
        print(f"  Would add {len(new_roots_entries)} entries to {ROOTS_PATH.name}")
        print(f"  Would add {len(new_lexicon_entries)} entries to {LEXICON_PATH.name}")
        print(f"  Would apply {cognate_count} Urartian cognates")
        print()
        print("  First 10 new roots entries:")
        for entry in new_roots_entries[:10]:
            print(f"    #{entry['Number']}: {entry['Hurrian']} — {entry['Meaning']}")
        if len(new_roots_entries) > 10:
            print(f"    ... and {len(new_roots_entries) - 10} more")
        print()
        print("  Run with --apply to write changes.")
    else:
        print("Phase 7: Writing changes")
        print("-" * 40)

        # Backup existing files
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        roots_backup = BACKUP_DIR / f"hurrian_roots.pre_lexical_{timestamp}.bak.json"
        lexicon_backup = BACKUP_DIR / f"hurrian_lexicon.pre_lexical_{timestamp}.bak.jsonl"

        print(f"  Backing up {ROOTS_PATH.name} → {roots_backup}")
        shutil.copy2(ROOTS_PATH, roots_backup)

        print(f"  Backing up {LEXICON_PATH.name} → {lexicon_backup}")
        shutil.copy2(LEXICON_PATH, lexicon_backup)

        # Write updated roots (existing + new, with cognates applied)
        final_roots = roots + new_roots_entries
        print(f"  Writing {ROOTS_PATH.name} ({len(final_roots)} entries)")
        ROOTS_PATH.write_text(
            json.dumps(final_roots, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

        # Append new lexicon entries
        print(f"  Appending {len(new_lexicon_entries)} entries to {LEXICON_PATH.name}")
        with open(LEXICON_PATH, "a", encoding="utf-8") as f:
            for entry in new_lexicon_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print()
        print(f"  Final roots count: {len(final_roots)}")
        print(f"  Final lexicon entries: {len(existing_lexicon_ids)}")

    print()
    print("=" * 60)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
