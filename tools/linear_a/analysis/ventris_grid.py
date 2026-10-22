#!/usr/bin/env python3
"""Sign-value confidence grid for the Ventris Engine.

For each sign, shows what phonetic value(s) we believe it has and why,
based on all confirmed/candidate readings in the lexicon. This is Ventris's
Step 2: organize signs into consonant-rows × vowel-columns.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
SIGN_VALUES_PATH = DATA_DIR / "sign_values.json"
LEXICON_PATH = DATA_DIR / "lexicon.json"


def load_sign_values() -> dict:
    return json.loads(require(SIGN_VALUES_PATH, SIGN_VALUES_PATH.name).read_text(encoding="utf-8"))


def load_lexicon() -> dict:
    return json.loads(require(LEXICON_PATH, LEXICON_PATH.name).read_text(encoding="utf-8"))


def _normalize_sign(s: str) -> str:
    """Normalize subscript variants: PA₃ → PA3 → PA."""
    _sub = str.maketrans("₂₃₄₅", "2345")
    return s.upper().translate(_sub)


def _base_sign(s: str) -> str:
    """Strip trailing digits to get base form: PA3 → PA."""
    return re.sub(r"\d+$", "", _normalize_sign(s))


def derive_constraints_from_lexicon(lexicon: dict) -> dict[str, list[dict]]:
    """For each sign, collect all readings that constrain its phonetic value.

    Returns: {sign_name: [{reading, word, value, confidence}, ...]}
    """
    constraints: dict[str, list[dict]] = defaultdict(list)

    for entry in lexicon.get("entries", []):
        word = entry.get("word", "")
        reading = entry.get("reading", "")
        confidence = entry.get("confidence", "SPECULATIVE")
        if not word or not reading:
            continue

        signs = word.split("-")
        # Try to align signs with reading syllables
        # This is approximate — we use the reading to infer what each sign contributes
        # For now, record that this sign appears in a word with this known reading
        for sign in signs:
            base = _base_sign(sign)
            constraints[base].append({
                "word": word,
                "reading": reading,
                "confidence": confidence,
                "is_anchor": entry.get("is_anchor", False),
            })

    return dict(constraints)


def build_grid(sign_values: dict, lexicon_constraints: dict) -> list[dict]:
    """Build the confidence grid combining sign_values.json with lexicon evidence."""
    signs_data = sign_values.get("signs", {})
    rows = []

    for sign_name, sv in sorted(signs_data.items()):
        primary = sv.get("primary", {})
        alternates = sv.get("alternates", [])
        confirmed_by = sv.get("confirmed_by", [])
        neut_class = sv.get("neutralization_class")

        # Count independent readings from lexicon
        constraints = lexicon_constraints.get(sign_name, [])
        anchor_count = sum(1 for c in constraints if c.get("is_anchor"))
        candidate_count = sum(1 for c in constraints if not c.get("is_anchor"))
        unique_words = len({c["word"] for c in constraints})

        rows.append({
            "sign": sign_name,
            "ab_number": sv.get("ab_number", ""),
            "consonant": primary.get("consonant"),
            "vowel": primary.get("vowel", ""),
            "confidence": primary.get("confidence", 0),
            "alternates": [
                {"consonant": a.get("consonant"), "vowel": a.get("vowel"),
                 "confidence": a.get("confidence", 0)}
                for a in alternates
            ],
            "neutralization_class": neut_class,
            "confirmed_by_count": len(confirmed_by),
            "anchor_readings": anchor_count,
            "candidate_readings": candidate_count,
            "unique_words": unique_words,
            "confirmed_by": confirmed_by,
        })

    return rows


def find_conflicts(grid: list[dict]) -> list[dict]:
    """Find signs where alternate readings have significant confidence."""
    conflicts = []
    for row in grid:
        for alt in row["alternates"]:
            if alt["confidence"] >= 0.3:
                conflicts.append({
                    "sign": row["sign"],
                    "primary": f"{row['consonant'] or ''}/{row['vowel']}",
                    "primary_conf": row["confidence"],
                    "alternate": f"{alt['consonant'] or ''}/{alt['vowel']}",
                    "alternate_conf": alt["confidence"],
                })
    return conflicts


def find_unconstrained(grid: list[dict]) -> list[dict]:
    """Find signs with no confirmed readings — unconstrained by evidence."""
    return [
        {"sign": r["sign"], "ab_number": r["ab_number"],
         "confidence": r["confidence"], "unique_words": r["unique_words"]}
        for r in grid
        if r["anchor_readings"] == 0
    ]


def format_grid(grid: list[dict], args) -> str:
    lines = []

    if args.conflicts:
        conflicts = find_conflicts(grid)
        lines.append(f"Sign-Value Conflicts ({len(conflicts)} signs with competing readings)")
        lines.append(f"{'='*70}")
        lines.append(f"{'Sign':<8} {'Primary':<10} {'Conf':>5} {'Alternate':<10} {'AltConf':>7}")
        lines.append(f"{'-'*70}")
        for c in conflicts:
            lines.append(
                f"  {c['sign']:<6} {c['primary']:<10} {c['primary_conf']:>4.2f}  "
                f"{c['alternate']:<10} {c['alternate_conf']:>5.2f}"
            )
        return "\n".join(lines)

    if args.unconstrained:
        uncon = find_unconstrained(grid)
        lines.append(f"Unconstrained Signs ({len(uncon)} signs with no anchor readings)")
        lines.append(f"{'='*50}")
        for u in uncon:
            lines.append(f"  {u['sign']:<8} {u['ab_number']:<8} conf={u['confidence']:.2f} words={u['unique_words']}")
        return "\n".join(lines)

    # Full grid
    lines.append("Sign-Value Confidence Grid")
    lines.append(f"{'='*80}")
    lines.append(
        f"{'Sign':<6} {'AB#':<7} {'Value':<8} {'Conf':>5} {'Alts':<16} "
        f"{'NClass':<6} {'Anchors':>7} {'Words':>6}"
    )
    lines.append(f"{'-'*80}")

    for r in sorted(grid, key=lambda x: -x["confidence"]):
        c = r["consonant"] or ""
        value = f"{c}/{r['vowel']}"
        alts = ", ".join(
            f"{a['consonant'] or ''}/{a['vowel']}({a['confidence']:.1f})"
            for a in r["alternates"][:2]
        ) if r["alternates"] else "—"
        lines.append(
            f"  {r['sign']:<5} {r['ab_number']:<7} {value:<8} {r['confidence']:>4.2f}  "
            f"{alts:<16} {r['neutralization_class'] or '—':<6} "
            f"{r['anchor_readings']:>5}   {r['unique_words']:>4}"
        )

    return "\n".join(lines)


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Sign-value confidence grid")
    parser.add_argument("--conflicts", action="store_true", help="Show value conflicts only")
    parser.add_argument("--unconstrained", action="store_true", help="Show signs with no confirmed readings")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    sv = load_sign_values()
    lex = load_lexicon()
    constraints = derive_constraints_from_lexicon(lex)
    grid = build_grid(sv, constraints)

    if args.json:
        if args.conflicts:
            print(json.dumps(find_conflicts(grid), indent=2))
        elif args.unconstrained:
            print(json.dumps(find_unconstrained(grid), indent=2))
        else:
            print(json.dumps(grid, indent=2))
    else:
        print(format_grid(grid, args))


if __name__ == "__main__":
    sys.exit(main())
