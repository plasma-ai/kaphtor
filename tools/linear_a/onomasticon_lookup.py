#!/usr/bin/env python3
"""Query the Linear A corpus onomasticon (data/linear-a/onomasticon.json).

The onomasticon is the corpus-attested name/toponym/theonym registry, partitioned by
linguistic affiliation. It is hand-edited.

Examples:
  onomasticon_lookup.py --stats                  # affiliation/type/provenance breakdown
  onomasticon_lookup.py --token A-RI             # one token
  onomasticon_lookup.py --affiliation hurrian    # all Hurrian-affiliated names
  onomasticon_lookup.py --type toponym           # all toponyms
  onomasticon_lookup.py --provenance manual      # hand-adjudicated / lexicon-linked only
  onomasticon_lookup.py --unknown                # the unaffiliated residual
  onomasticon_lookup.py --affiliation semitic --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

DATA_FILE = LINEAR_A_DATA / "onomasticon.json"
DISCLAIMER = "⚠ All affiliations are hypothetical and evidence-gated. NAME-LIKELY ≠ identified; `auto` provenance (hapax) is un-reviewed."


def load() -> dict:
    return json.loads(require(DATA_FILE, DATA_FILE.name).read_text(encoding="utf-8"))


def print_stats(d: dict) -> None:
    s = d["stats"]
    total = s["total"]
    print(f"Corpus Onomasticon — {total} entries")
    print("=" * 60)
    print("By affiliation:")
    count = lambda v: v["total"] if isinstance(v, dict) else v
    for k, v in sorted(s["by_affiliation"].items(), key=lambda x: -count(x[1])):
        n = count(v)
        print(f"  {k:<12} {n:>4}  ({100*n/total:.0f}%)")
        if isinstance(v, dict):
            for c, m in v.items():
                if c not in ("total", "note"):
                    print(f"    {c:<12} {m:>4}")
    print("By type:")
    for k, v in sorted(s["by_type"].items(), key=lambda x: -x[1]):
        print(f"  {k:<14} {v:>4}")
    print("By provenance:")
    for k, v in sorted(s["by_provenance"].items(), key=lambda x: -x[1]):
        print(f"  {k:<8} {v:>4}")
    print(f"Excluded (not names): {s.get('excluded', {})}")
    print()
    print(DISCLAIMER)


def fmt_entry(e: dict) -> str:
    ref = []
    if e.get("lexicon_ref"):
        ref.append(f"lex:{e['lexicon_ref']}")
    if e.get("contact_ref"):
        ref.append(f"contact:{e['contact_ref']}")
    reading = f" = {e['reading']}" if e.get("reading") else ""
    return (f"  {e['token']:<18}{reading:<22} [{e['type']}/{e['affiliation']}] "
            f"f={e['frequency']} {e['provenance']} ({e['affiliation_evidence']}) {' '.join(ref)}")


def main() -> int:
    """Exit 2 with the file's name when the onomasticon is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser(description="Query the Linear A corpus onomasticon.")
    ap.add_argument("--token", help="look up a single token")
    ap.add_argument("--affiliation", help="filter by affiliation class")
    ap.add_argument("--type", dest="type_", help="filter by type (personal_name/toponym/theonym/title/gentilic)")
    ap.add_argument("--provenance", choices=["manual", "auto"], help="filter by provenance")
    ap.add_argument("--unknown", action="store_true", help="the unaffiliated residual")
    ap.add_argument("--stats", action="store_true", help="affiliation/type/provenance breakdown")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--format", choices=["table", "json"], default="table")
    ap.add_argument("--json", action="store_true", help="alias for --format json")
    args = ap.parse_args()
    as_json = args.json or args.format == "json"

    d = load()
    entries = d["entries"]

    if args.stats:
        if as_json:
            print(json.dumps(d["stats"], ensure_ascii=False, indent=2))
        else:
            print_stats(d)
        return 0

    if args.token:
        hit = [e for e in entries if e["token"] == args.token]
        if not hit:
            print(f"No onomasticon entry for {args.token}", file=sys.stderr)
            return 1
        print(json.dumps(hit[0], ensure_ascii=False, indent=2) if as_json else fmt_entry(hit[0]))
        return 0

    sel = entries
    if args.affiliation:
        sel = [e for e in sel if e["affiliation"] == args.affiliation]
    if args.unknown:
        sel = [e for e in sel if e["affiliation"] == "unknown"]
    if args.type_:
        sel = [e for e in sel if e["type"] == args.type_]
    if args.provenance:
        sel = [e for e in sel if e["provenance"] == args.provenance]

    if as_json:
        print(json.dumps(sel, ensure_ascii=False, indent=2))
        return 0

    print(f"{len(sel)} entries" + (f" (showing {args.limit})" if len(sel) > args.limit else ""))
    print("=" * 60)
    for e in sel[:args.limit]:
        print(fmt_entry(e))
    print()
    print(DISCLAIMER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
