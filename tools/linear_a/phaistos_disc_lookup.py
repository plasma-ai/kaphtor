#!/usr/bin/env python3
"""Query the Phaistos Disc corpus (data/linear-a/phaistos_disc.json).

Examples:
  phaistos_disc_lookup.py --stats                # summary statistics
  phaistos_disc_lookup.py --frequency            # sign frequency table
  phaistos_disc_lookup.py --sign 2               # sign info + occurrences
  phaistos_disc_lookup.py --group A1             # show group with sign names
  phaistos_disc_lookup.py --side A               # all groups on Side A
  phaistos_disc_lookup.py --search-pattern 2,12  # groups containing these signs, in any order
  phaistos_disc_lookup.py --search-sequence 2,12 # groups containing 02 then 12, adjacent
  phaistos_disc_lookup.py --positions 8          # initial/medial/final/sole counts (or: all)
  phaistos_disc_lookup.py --neighbours 12        # left and right neighbours with sign-map tiers
  phaistos_disc_lookup.py --frequency --json     # machine-readable output

Positions and neighbours follow the stored order of each group, the order the sign map's positional counts use.
Sign 0 (the damaged slot in A8) is never counted, paired or matched, but it keeps its slot: the sign before it is
medial, not final.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

DATA_FILE = LINEAR_A_DATA / "phaistos_disc.json"
SIGN_MAP_FILE = DATA_FILE.with_name("phaistos_disc_sign_map.json")
DAMAGED = 0


def _disclaimer(d: dict) -> str:
    status = d.get("metadata", {}).get("verification_status", "UNKNOWN")
    if status == "VERIFIED":
        return "Transcription VERIFIED against hp4k1h5/phaistos-disc (MIT, Achterberg/Evans/GORILA standard)."
    return "Transcription status: NEEDS_CROSS_CHECK — verify against published GORILA/Evans standard before citing."


def load() -> dict:
    return json.loads(require(DATA_FILE, DATA_FILE.name).read_text(encoding="utf-8"))


def all_groups(d: dict) -> list[dict]:
    return d["transcription"]["side_A"] + d["transcription"]["side_B"]


def sign_name(d: dict, n: int) -> str:
    if n == 0:
        return "UNKNOWN/DAMAGED"
    key = f"{n:02d}"
    s = d["signs"].get(key)
    return s["name"] if s else f"PD{n:02d}"


def count_occurrences(d: dict) -> Counter:
    c: Counter = Counter()
    for g in all_groups(d):
        for s in g["signs"]:
            c[s] += 1
    return c


def print_stats(d: dict) -> None:
    m = d["metadata"]
    groups = all_groups(d)
    occ = count_occurrences(d)
    total_occ = sum(occ.values())
    total_groups = len(groups)
    signs_total = m["total_signs"]
    stroke_groups = [g for g in groups if g["has_oblique_stroke"]]

    print(f"Phaistos Disc Corpus — {signs_total} sign types, {total_occ} occurrences")
    print("=" * 60)
    print(f"  Date range:       {m['date_range']}")
    print(f"  Discovery:        {m['discovery']['date']} by {m['discovery']['excavator']}")
    print(f"  Site:             {m['site']}")
    print(f"  Location:         {m['current_location']}")
    print(f"  Dimensions:       {m['dimensions_cm']} cm diameter")
    print(f"  Technique:        {m['technique']}")
    print(f"  Reading:          {m['reading_direction']}")
    print(f"  Within-group:     {m['within_group_direction']}")
    print()
    real_signs = {s for s in occ if s > 0}
    print(f"  Sign types:       {len(real_signs)} of {signs_total} used")
    print(f"  Total occurrences:{total_occ}")
    print(f"  Groups:           {total_groups} (A:{m['group_count']['A']}, B:{m['group_count']['B']})")
    print(f"  Oblique strokes:  {len(stroke_groups)} group(s)")
    print(f"  Mean group size:  {total_occ / total_groups:.1f} signs")
    print()
    print(f"  Verification:     {m['verification_status']}")
    print()
    print(_disclaimer(d))


def print_frequency(d: dict) -> None:
    occ = count_occurrences(d)
    total = sum(occ.values())
    print(f"Sign Frequency — {total} total occurrences")
    print("=" * 60)
    print(f"  {'#':<4} {'Name':<20} {'Count':>5}  {'%':>5}")
    print(f"  {'─'*4} {'─'*20} {'─'*5}  {'─'*5}")
    for sign_num, count in occ.most_common():
        if sign_num == 0:
            name = "UNKNOWN/DAMAGED"
        else:
            name = sign_name(d, sign_num)
        print(f"  {sign_num:>02}   {name:<20} {count:>5}  {100*count/total:>5.1f}")


def print_sign(d: dict, n: int) -> None:
    key = f"{n:02d}"
    s = d["signs"].get(key)
    if not s:
        print(f"No sign with number {n} (valid range: 1-45)", file=sys.stderr)
        sys.exit(1)

    occ = count_occurrences(d)
    groups_with = [g["group"] for g in all_groups(d) if n in g["signs"]]

    print(f"PD Sign {n:02d}: {s['name']}")
    print("=" * 40)
    print(f"  Unicode:      {s['unicode']}")
    print(f"  Description:  {s['description']}")
    print(f"  Occurrences:  {occ.get(n, 0)}")
    print(f"  Groups ({len(groups_with)}):  {', '.join(groups_with)}")


def print_group(d: dict, group_id: str) -> None:
    group_id = group_id.upper()
    groups = all_groups(d)
    hit = [g for g in groups if g["group"] == group_id]
    if not hit:
        print(f"No group {group_id}", file=sys.stderr)
        sys.exit(1)
    g = hit[0]
    names = [f"{s:02d}:{sign_name(d, s)}" for s in g["signs"]]
    stroke = ""
    if g["has_oblique_stroke"]:
        stroke = f"  (oblique stroke on position {g['stroke_on_sign']})"
    print(f"Group {g['group']}: [{', '.join(names)}]{stroke}")


def print_side(d: dict, side: str) -> None:
    side = side.upper()
    key = f"side_{side}"
    if key not in d["transcription"]:
        print(f"Invalid side: {side} (use A or B)", file=sys.stderr)
        sys.exit(1)
    groups = d["transcription"][key]
    print(f"Side {side} — {len(groups)} groups")
    print("=" * 60)
    for g in groups:
        names = [f"{s:02d}:{sign_name(d, s)}" for s in g["signs"]]
        stroke = " [STROKE]" if g["has_oblique_stroke"] else ""
        print(f"  {g['group']:<4} [{', '.join(names)}]{stroke}")


def search_pattern(d: dict, pattern: list[int]) -> list[dict]:
    results = []
    for g in all_groups(d):
        if all(p in g["signs"] for p in pattern):
            results.append(g)
    return results


def search_sequence(d: dict, seq: list[int]) -> list[dict]:
    """Groups holding `seq` in this order, adjacent."""
    k = len(seq)
    return [g for g in all_groups(d)
            if any(g["signs"][i:i + k] == seq for i in range(len(g["signs"]) - k + 1))]


def positions(d: dict) -> dict[int, dict]:
    """Per sign: initial/medial/final/sole counts and the groups behind each."""
    out = {n: {"sign": n, "name": sign_name(d, n), "initial": 0, "medial": 0, "final": 0, "sole": 0,
               "groups": {"initial": [], "medial": [], "final": [], "sole": []}}
           for n in range(1, d["metadata"]["total_signs"] + 1)}
    for g in all_groups(d):
        s = g["signs"]
        for i, n in enumerate(s):
            if n == DAMAGED:
                continue
            slot = "sole" if len(s) == 1 else "initial" if i == 0 else "final" if i == len(s) - 1 else "medial"
            out[n][slot] += 1
            out[n]["groups"][slot].append(g["group"])
    return out


def sign_tiers() -> dict[int, str]:
    return {r["pd_sign"]: r["bridge_confidence"]
            for r in json.loads(require(SIGN_MAP_FILE, SIGN_MAP_FILE.name).read_text(encoding="utf-8"))["sign_bridge"]}


def neighbours(d: dict, n: int) -> dict:
    """Signs immediately before (left) and after (right) `n` in stored order; the damaged slot breaks adjacency."""
    left: Counter = Counter()
    right: Counter = Counter()
    for g in all_groups(d):
        s = g["signs"]
        for a, b in pairwise(s):
            if DAMAGED in (a, b):
                continue
            if b == n:
                left[a] += 1
            if a == n:
                right[b] += 1
    tier = sign_tiers()
    rows = lambda c: [{"sign": x, "name": sign_name(d, x), "count": k, "tier": tier.get(x)}
                      for x, k in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {"sign": n, "name": sign_name(d, n), "tier": tier.get(n), "left": rows(left), "right": rows(right)}


def parse_signs(ap: argparse.ArgumentParser, d: dict, text: str) -> list[int]:
    try:
        signs = [int(x.strip()) for x in text.split(",")]
    except ValueError:
        ap.error(f"sign numbers must be integers: {text!r}")
    bad = [n for n in signs if not 1 <= n <= d["metadata"]["total_signs"]]
    if bad:
        ap.error(f"no Disc sign {bad[0]} (valid range: 1-{d['metadata']['total_signs']})")
    return signs


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser(description="Query the Phaistos Disc corpus.")
    ap.add_argument("--sign", type=int, help="show sign info (1-45)")
    ap.add_argument("--group", help="show group (e.g. A1, B15)")
    ap.add_argument("--side", help="show all groups on a side (A or B)")
    ap.add_argument("--search-pattern",
                    help="find groups containing these sign numbers in any order (unordered; comma-separated)")
    ap.add_argument("--search-sequence", help="find groups containing these signs in this order, adjacent (e.g. 2,12)")
    ap.add_argument("--positions", metavar="N|all", help="initial/medial/final/sole counts for a sign, or all")
    ap.add_argument("--neighbours", type=int, metavar="N", help="left and right neighbours of a sign, with tiers")
    ap.add_argument("--frequency", action="store_true", help="sign frequency table")
    ap.add_argument("--stats", action="store_true", help="summary statistics")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    d = load()

    if args.stats:
        if args.json:
            occ = count_occurrences(d)
            total = sum(occ.values())
            out = {
                "total_sign_types": d["metadata"]["total_signs"],
                "signs_used": len([s for s in occ if s != DAMAGED]),
                "total_occurrences": total,
                "canonical_occurrences": total - occ.get(DAMAGED, 0),
                "damaged_occurrences": occ.get(DAMAGED, 0),
                "group_count": d["metadata"]["group_count"],
                "total_groups": sum(d["metadata"]["group_count"].values()),
                "mean_group_size": round(total / sum(d["metadata"]["group_count"].values()), 1),
                "oblique_stroke_groups": len([g for g in all_groups(d) if g["has_oblique_stroke"]]),
                "verification_status": d["metadata"]["verification_status"],
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print_stats(d)
        return 0

    if args.frequency:
        if args.json:
            occ = count_occurrences(d)
            out = [{"sign": n, "name": sign_name(d, n), "count": c} for n, c in occ.most_common()]
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print_frequency(d)
        return 0

    if args.sign is not None:
        if args.json:
            key = f"{args.sign:02d}"
            s = d["signs"].get(key)
            if not s:
                print(f"No sign with number {args.sign}", file=sys.stderr)
                return 1
            occ = count_occurrences(d)
            groups_with = [g["group"] for g in all_groups(d) if args.sign in g["signs"]]
            out = {**s, "occurrences": occ.get(args.sign, 0), "groups": groups_with}
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print_sign(d, args.sign)
        return 0

    if args.group:
        if args.json:
            group_id = args.group.upper()
            hit = [g for g in all_groups(d) if g["group"] == group_id]
            if not hit:
                print(f"No group {group_id}", file=sys.stderr)
                return 1
            g = hit[0]
            g["sign_names"] = [sign_name(d, s) for s in g["signs"]]
            print(json.dumps(g, ensure_ascii=False, indent=2))
        else:
            print_group(d, args.group)
        return 0

    if args.side:
        side = args.side.upper()
        key = f"side_{side}"
        if key not in d["transcription"]:
            print(f"Invalid side: {side} (use A or B)", file=sys.stderr)
            return 1
        groups = d["transcription"][key]
        if args.json:
            for g in groups:
                g["sign_names"] = [sign_name(d, s) for s in g["signs"]]
            print(json.dumps(groups, ensure_ascii=False, indent=2))
        else:
            print_side(d, args.side)
        return 0

    if args.search_pattern:
        pattern = [int(x.strip()) for x in args.search_pattern.split(",")]
        results = search_pattern(d, pattern)
        if args.json:
            for g in results:
                g["sign_names"] = [sign_name(d, s) for s in g["signs"]]
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            pattern_names = [f"{p:02d}:{sign_name(d, p)}" for p in pattern]
            print(f"Groups containing [{', '.join(pattern_names)}]: {len(results)} found")
            print("=" * 60)
            for g in results:
                names = [f"{s:02d}:{sign_name(d, s)}" for s in g["signs"]]
                print(f"  {g['group']:<4} [{', '.join(names)}]")
        return 0

    if args.search_sequence:
        seq = parse_signs(ap, d, args.search_sequence)
        results = search_sequence(d, seq)
        if args.json:
            for g in results:
                g["sign_names"] = [sign_name(d, s) for s in g["signs"]]
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            seq_names = [f"{p:02d}:{sign_name(d, p)}" for p in seq]
            print(f"Groups containing the sequence [{', '.join(seq_names)}]: {len(results)} found")
            print("=" * 60)
            for g in results:
                names = [f"{s:02d}:{sign_name(d, s)}" for s in g["signs"]]
                print(f"  {g['group']:<4} [{', '.join(names)}]")
        return 0

    if args.positions:
        table = positions(d)
        if args.positions.lower() == "all":
            rows = list(table.values())
        else:
            rows = [table[n] for n in parse_signs(ap, d, args.positions)]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print(f"  {'#':<4} {'Name':<20} {'Init':>4} {'Med':>4} {'Fin':>4} {'Sole':>4}")
            for r in rows:
                print(f"  {r['sign']:02d}   {r['name']:<20} {r['initial']:>4} {r['medial']:>4} "
                      f"{r['final']:>4} {r['sole']:>4}")
        return 0

    if args.neighbours is not None:
        n = parse_signs(ap, d, str(args.neighbours))[0]
        nb = neighbours(d, n)
        if args.json:
            print(json.dumps(nb, ensure_ascii=False, indent=2))
        else:
            print(f"PD {n:02d} {nb['name']} ({nb['tier']})")
            for side in ("left", "right"):
                cells = [f"{x['sign']:02d}:{x['name']}×{x['count']} ({x['tier']})" for x in nb[side]]
                print(f"  {side + ':':<7}{', '.join(cells) or '—'}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
