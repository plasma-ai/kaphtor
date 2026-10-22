#!/usr/bin/env python3
"""Database Composition Audit.

Reports structural differences between the four language root databases
(NWS, Luwian, Egyptian, Hurrian): total entries, onomastic count,
consonantal-length distribution.

Usage:
    uv run tools/linear_a/validation/db_composition_audit.py
    uv run tools/linear_a/validation/db_composition_audit.py --json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core.phonetics import _tokenize_phonemes
from ...core.semitic_root_schema import roots_records
from ...paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require
from .null_model_audit import LANGUAGE_CONFIGS, MAX_ROOT_LEN, _extract_consonantal_root, _is_onomastic


def audit_language(language: str) -> dict:
    config = LANGUAGE_CONFIGS[language]
    if language == "nws":
        path = require(SEMITIC_ROOTS_DATA / config["file"], config["file"])
        raw = roots_records(json.loads(path.read_text(encoding="utf-8")))
    else:
        path = require(LINEAR_A_DATA / config["file"], config["file"])
        raw = json.loads(path.read_text(encoding="utf-8"))

    total = len(raw)
    onomastic = {"PN": 0, "GN": 0, "DN": 0}
    length_dist = Counter()
    usable = 0

    field = config["field"]
    for entry in raw:
        if _is_onomastic(entry):
            m = entry.get("Meaning", "")
            if "(PN)" in m:
                onomastic["PN"] += 1
            elif "(GN)" in m:
                onomastic["GN"] += 1
            elif "(DN)" in m:
                onomastic["DN"] += 1
            else:
                for v in entry.get("Analogues", {}).values():
                    s = str(v)
                    if "(PN)" in s:
                        onomastic["PN"] += 1
                        break
                    elif "(GN)" in s:
                        onomastic["GN"] += 1
                        break
                    elif "(DN)" in s:
                        onomastic["DN"] += 1
                        break

        val = entry.get(field, "")
        if not val:
            continue
        cons = _extract_consonantal_root(val)
        tokens = _tokenize_phonemes(cons)
        if not tokens or len(tokens) < 2 or len(tokens) > MAX_ROOT_LEN:
            continue
        usable += 1
        length_dist[len(tokens)] += 1

    onomastic_total = sum(onomastic.values())
    return {
        "language": language,
        "label": config["label"],
        "total_entries": total,
        "usable_roots": usable,
        "onomastic": onomastic,
        "onomastic_total": onomastic_total,
        "onomastic_pct": round(onomastic_total / total * 100, 1) if total else 0,
        "length_distribution": {str(k): length_dist.get(k, 0) for k in range(2, 6)},
        "triconsonantal_pct": round(length_dist.get(3, 0) / usable * 100, 1) if usable else 0,
    }


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Database Composition Audit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = {lang: audit_language(lang) for lang in LANGUAGE_CONFIGS}

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print("Database Composition Audit")
    print("=" * 78)
    print()

    # Summary table
    print(f"{'Language':<24} {'Total':>7} {'Usable':>7} {'Onomastic':>10} {'Ono %':>7} {'Tricons %':>10}")
    print("-" * 78)
    for r in results.values():
        print(f"{r['label']:<24} {r['total_entries']:>7} {r['usable_roots']:>7} "
              f"{r['onomastic_total']:>10} {r['onomastic_pct']:>6.1f}% "
              f"{r['triconsonantal_pct']:>9.1f}%")
    print()

    # Onomastic breakdown
    print("Onomastic Breakdown:")
    print(f"{'Language':<24} {'PN':>6} {'GN':>6} {'DN':>6} {'Total':>7}")
    print("-" * 55)
    for r in results.values():
        o = r["onomastic"]
        print(f"{r['label']:<24} {o['PN']:>6} {o['GN']:>6} {o['DN']:>6} {r['onomastic_total']:>7}")
    print()

    # Length distribution
    print("Consonantal Length Distribution (usable roots, 2-5 consonants):")
    print(f"{'Language':<24} {'2-cons':>8} {'3-cons':>8} {'4-cons':>8} {'5-cons':>8}")
    print("-" * 60)
    for r in results.values():
        ld = r["length_distribution"]
        u = r["usable_roots"]
        pcts = [f"{int(ld.get(str(n), 0))/u*100:.1f}%" if u else "0%" for n in range(2, 6)]
        counts = [ld.get(str(n), 0) for n in range(2, 6)]
        print(f"{r['label']:<24} {counts[0]:>4} ({pcts[0]:>5}) {counts[1]:>4} ({pcts[1]:>5}) "
              f"{counts[2]:>4} ({pcts[2]:>5}) {counts[3]:>4} ({pcts[3]:>5})")
    print()

    luw = results["luwian"]
    nws = results["nws"]
    print("Luwian against NWS:")
    print(f"  Luwian onomastic entries: {luw['onomastic_total']}/{luw['total_entries']} ({luw['onomastic_pct']}%)")
    print(f"  NWS onomastic entries:    {nws['onomastic_total']}/{nws['total_entries']} ({nws['onomastic_pct']}%)")
    print(f"  Luwian triconsonantal:    {luw['triconsonantal_pct']}%")
    print(f"  NWS triconsonantal:       {nws['triconsonantal_pct']}%")
    print()
    print("  A database with more onomastic content and a flatter length distribution has a")
    print("  structural advantage in the null model that says nothing about the language of Linear A.")


if __name__ == "__main__":
    sys.exit(main())
