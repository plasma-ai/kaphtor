#!/usr/bin/env python3
"""Build a source-only positional profile for Linear A word sequences.

The output records distributions and transitions; it does not assign meanings,
parts of speech, language affiliation, or sign values.

Usage:
    uv run python tools/linear_a/analysis/slot_grammar.py --output /path/to/slot_grammar.json
    uv run python tools/linear_a/analysis/slot_grammar.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import CACHE, DATA, LINEAR_A_DATA, NotInCheckout, require

SOURCE = LINEAR_A_DATA / "corpus.json"
# The shipped profile, which --check validates against the corpus.
DATASET = LINEAR_A_DATA / "comparative_corpora" / "linear_a" / "slot_grammar.json"
# Where a build writes when no --output is given: outside the repository.
OUTPUT = CACHE / "linear-a" / "slot_grammar.json"
DIVIDERS = {"", "·", "𐄀", "𐄁", "\n"}
NONWORD = re.compile(r"^(?:\d+(?:[./]\d+)?|[𐝀-𐝕]+)$")
DAMAGE_MARKS = set("[]?⸢⸣")
LOGOGRAMS = {
    "GRA", "VIN", "CYP", "OLE", "OLIV", "FIC", "BOS", "CAP", "OVIS",
    "SUS", "TELA", "AROM", "LANA", "PUG", "VIR", "MUL",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_quantity(token: str) -> bool:
    if NONWORD.fullmatch(token):
        return True
    meaningful = [char for char in token if not char.isspace()]
    return bool(meaningful) and all(
        char in ".,/" or unicodedata.category(char).startswith("N")
        or unicodedata.numeric(char, None) is not None
        for char in meaningful
    )


def token_class(token: str) -> str:
    if token in DIVIDERS or token in {"—", "–", "-"}:
        return "separator"
    if is_quantity(token):
        return "quantity_or_isolated_sign"
    if token in LOGOGRAMS or "+" in token:
        return "logogram"
    if re.fullmatch(r"\*\d+[A-Za-z]?", token) or not any(char.isalnum() for char in token):
        return "unresolved_sign_or_mark"
    return "syllabic_word"


def content_sequences(record: dict) -> tuple[list[list[str]], Counter]:
    sequences: list[list[str]] = []
    current: list[str] = []
    classes = Counter()
    for raw in record.get("transliteratedWords") or []:
        token = str(raw).strip()
        kind = token_class(token)
        classes[kind] += 1
        if kind == "syllabic_word":
            current.append(token)
        elif current:
            sequences.append(current)
            current = []
    if current:
        sequences.append(current)
    return sequences, classes


def slot(index: int, length: int) -> str:
    if length == 1:
        return "singleton"
    if index == 0:
        return "initial"
    if index == length - 1:
        return "final"
    if index == 1:
        return "second"
    if index == length - 2:
        return "penultimate"
    return "medial"


def build() -> dict:
    corpus = json.loads(require(SOURCE, SOURCE.name).read_text(encoding="utf-8"))
    profiles: dict[str, dict] = {}
    slot_counts = Counter()
    preserved_slot_counts = Counter()
    transitions = Counter()
    preserved_transitions = Counter()
    sequence_count = token_count = preserved_count = 0
    inscriptions_with_sequences = 0
    token_classes = Counter()

    for inscription_id, record in sorted(corpus.items()):
        sequences, record_classes = content_sequences(record)
        token_classes.update(record_classes)
        if not sequences:
            continue
        inscriptions_with_sequences += 1
        sequence_count += len(sequences)
        site = record.get("site") or None
        support = record.get("support") or None
        for words in sequences:
            for index, token in enumerate(words):
                token_count += 1
                position = slot(index, len(words))
                is_preserved = not any(mark in token for mark in DAMAGE_MARKS)
                slot_counts[position] += 1
                if is_preserved:
                    preserved_count += 1
                    preserved_slot_counts[position] += 1
                row = profiles.setdefault(token, {
                    "token": token,
                    "frequency": 0,
                    "preserved_frequency": 0,
                    "inscriptions": set(),
                    "sites": set(),
                    "supports": set(),
                    "slots": Counter(),
                    "preserved_slots": Counter(),
                })
                row["frequency"] += 1
                row["preserved_frequency"] += int(is_preserved)
                row["inscriptions"].add(inscription_id)
                if site:
                    row["sites"].add(site)
                if support:
                    row["supports"].add(support)
                row["slots"][position] += 1
                if is_preserved:
                    row["preserved_slots"][position] += 1
            for left, right in pairwise(words):
                transitions[(left, right)] += 1
                if not any(mark in left or mark in right for mark in DAMAGE_MARKS):
                    preserved_transitions[(left, right)] += 1

    normalized_profiles = []
    for token, row in profiles.items():
        frequency = row["frequency"]
        normalized_profiles.append({
            "token": token,
            "frequency": frequency,
            "preserved_frequency": row["preserved_frequency"],
            "inscriptions": sorted(row["inscriptions"]),
            "sites": sorted(row["sites"]),
            "supports": sorted(row["supports"]),
            "slots": dict(row["slots"]),
            "preserved_slots": dict(row["preserved_slots"]),
            "initial_rate": round(row["slots"].get("initial", 0) / frequency, 6),
            "final_rate": round(row["slots"].get("final", 0) / frequency, 6),
        })
    normalized_profiles.sort(key=lambda row: (-row["frequency"], row["token"]))

    def transition_rows(counter: Counter) -> list[dict]:
        return [
            {"left": left, "right": right, "frequency": frequency}
            for (left, right), frequency in sorted(
                counter.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_root": "kaphtor",
        "source": SOURCE.relative_to(DATA).as_posix(),
        "source_sha256": sha256(SOURCE),
        "method": (
            "Observed syllabic-word position within source-bounded runs. Newlines, dividers, quantities, "
            "logograms, and unresolved signs terminate a run; no linguistic labels inferred."
        ),
        "evidence_policy": (
            "Descriptive target-corpus evidence only. Position may test a hypothesis but cannot establish a "
            "language identification."
        ),
        "counts": {
            "inscriptions_total": len(corpus),
            "inscriptions_with_content_sequence": inscriptions_with_sequences,
            "source_bounded_sequences": sequence_count,
            "tokens": token_count,
            "preserved_tokens": preserved_count,
            "unique_tokens": len(profiles),
        },
        "source_token_class_counts": dict(token_classes),
        "slot_counts": dict(slot_counts),
        "preserved_slot_counts": dict(preserved_slot_counts),
        "token_profiles": normalized_profiles,
        "transitions": transition_rows(transitions),
        "preserved_transitions": transition_rows(preserved_transitions),
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
    parser.add_argument("--check", action="store_true",
                        help=f"Validate a profile against the corpus (default: {DATASET.relative_to(DATA)})")
    parser.add_argument("--output", type=Path,
                        help=f"Profile to write, or with --check to validate (build default: {OUTPUT})")
    args = parser.parse_args()
    if args.check:
        target = args.output or DATASET
        payload = json.loads(require(target, "comparative_corpora/linear_a/slot_grammar.json").read_text(
            encoding="utf-8"))
        assert payload["source_sha256"] == sha256(require(SOURCE, SOURCE.name))
        assert payload["counts"]["tokens"] == sum(payload["slot_counts"].values())
        assert payload["counts"]["unique_tokens"] == len(payload["token_profiles"])
        print(json.dumps({"valid": True, **payload["counts"]}, indent=2))
        return 0
    output = args.output or OUTPUT
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **payload["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
