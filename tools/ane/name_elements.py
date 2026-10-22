#!/usr/bin/env python3
"""Split a Pre-Islamic Arabian personal name into a divine element and the rest, against a theonym table.
Runs at query time; no data is rewritten.

The table is a JSON file the user supplies (--table): `theonyms`, each with a `name`, its `skeletons`, the
`basis` for listing it, optional `final_only` / `initial_only` skeletons and an optional `also_common` note; and
`rules` with `min_remainder` and `default_suffixes`. No table ships with this repository.

A name matches a theonym when one of its skeletons is the whole name, or stands at its start or end with at
least `min_remainder` letters left (a final_only skeleton only at the end, an initial_only one only at the start;
both ends when it stands at both). Names and skeletons are compared through ane_keys.marks_kept, so ʾ, ʿ and '
are one letter and every other mark is kept; a match that needed that fold says so (`guttural_folded`), and the
matched part and the remainder are given in the name's own letters. Each match is a lead: a theonym that is also
a common word carries `also_common`.

A name that matches nothing is tried once more without its last letter when that letter is one of the table's
default suffixes (mimation -m) or of --suffixes (hypocoristic -n, -t, -y, -w…, off unless asked). A theonym
inside a name is not searched for: a medial search flags far more names than it explains.

Usage:
  python3 tools/ane/name_elements.py --table THEONYMS.json ʿbdmnt ʾlʿzr
  python3 tools/ane/name_elements.py --table THEONYMS.json --suffixes ntyw šmsy

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.ane"

from .ane_keys import INDEX, SEPARATOR, SIGNS, digraph_readings, loose_key, marks_kept


def key(s: str) -> str:
    return marks_kept(unicodedata.normalize("NFC", s))


def pieces(s: str) -> list[tuple[str, str]]:
    """`s` cut into (original, folded) pieces whose folded parts join to key(s): marks_kept applied piece by
    piece (a sibilant index pair is one piece, a separator folds to nothing), so a match on the folded key maps
    back onto the name's own letters."""
    s, out, i = unicodedata.normalize("NFC", s), [], 0
    while i < len(s):
        if INDEX.fullmatch(s[i:i + 2].lower()):
            out.append((s[i:i + 2], "s"))
            i += 2
            continue
        c = s[i]
        out.append((c, "" if SEPARATOR.fullmatch(c) else "'" if SIGNS.fullmatch(c) else c.lower()))
        i += 1
    return out


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def elements(table: dict[str, Any]) -> list[tuple[str, str, bool, bool, dict[str, Any]]]:
    """(folded skeleton, skeleton as listed, final only, initial only, theonym) for every skeleton of the
    table."""
    return [(key(s), s, s in t.get("final_only", []), s in t.get("initial_only", []), t)
            for t in table["theonyms"] for s in t["skeletons"]]


def name_key(s: str) -> str:
    return loose_key(s).replace("'", "")


def theonyms_for(query: str, table: dict[str, Any]) -> list[dict[str, Any]]:
    """The theonyms a query names: one of their skeletons (mnt, ʿttr), or a name they go by with marks, ʾ, ʿ
    and the article folded (Manāt, manat, Uzza, Il); English-keyboard digraphs are also read as their letter
    (Athtar, Shams)."""
    readings = {query} | digraph_readings(query.casefold())
    keys, names = {key(r) for r in readings}, {name_key(r) for r in readings}
    return [t for t in table["theonyms"]
            if keys & {key(s) for s in t["skeletons"]}
            or names & {name_key(part) for part in re.split(r"[/()]", t["name"].replace("al-", "")) if part.strip()}]


def positions(form: str, skeleton: str, final_only: bool, initial_only: bool, min_remainder: int) -> list[str]:
    """Where the skeleton stands in the form: the whole of it, or its start and its end (both, in ʾlḥnʾl)."""
    if form == skeleton:
        return ["whole"]
    if len(form) - len(skeleton) < min_remainder:
        return []
    return ([] if final_only or not form.startswith(skeleton) else ["initial"]) + \
        ([] if initial_only or not form.endswith(skeleton) else ["final"])


def split(name: str, table: dict[str, Any], suffixes: str = "") -> list[dict[str, Any]]:
    """Every theonym the name holds at its whole, start or end; the name without one final suffix letter (the
    table's default_suffixes plus `suffixes`) only when the name itself holds none."""
    min_remainder = table["rules"]["min_remainder"]
    parts = pieces(name)
    folded = "".join(f for _, f in parts)
    owner = [i for i, (_, f) in enumerate(parts) for _ in f]   # folded position → piece

    def original(start: int, stop: int) -> str:
        """The name's own letters behind folded[start:stop]."""
        return "".join(o for o, _ in parts[owner[start]:owner[stop - 1] + 1]) if start < stop else ""

    ends = [len(folded)]
    if folded and folded[-1] in key(table["rules"]["default_suffixes"] + suffixes):
        ends.append(len(folded) - 1)
    for end in ends:
        found = []
        for skeleton, listed, _, _, theonym, where in (
                (*element, where) for element in elements(table)
                for where in positions(folded[:end], element[0], element[2], element[3], min_remainder)):
            start = end - len(skeleton) if where == "final" else 0
            stop = start + len(skeleton)
            matched = original(start, stop)
            found.append({
                "theonym": theonym["name"], "skeleton": listed, "position": where, "matched": matched,
                "remainder": original(stop, end) if where == "initial" else original(0, start),
                "suffix_stripped": original(end, len(folded)),
                # the name's ʾ/ʿ differ from the skeleton's: the match rests on the fold alone
                "guttural_folded": any(a.lower() != b for (a, f), (b, _) in zip(pieces(matched), pieces(listed))
                                       if f == "'"),
                "basis": theonym["basis"],
                **({"also_common": theonym["also_common"]} if "also_common" in theonym else {})})
        if found:
            # one theonym once per position: the longest of its skeletons there (ʿshʿlh is -ʾlh, not -lh too)
            return [m for m in found if not any(o["theonym"] == m["theonym"] and o["position"] == m["position"]
                                                and len(o["matched"]) > len(m["matched"]) for o in found)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Split names into a theonym and the rest.")
    ap.add_argument("names", nargs="+")
    ap.add_argument("--table", type=Path, required=True, help="the theonym table (JSON); none ships here")
    ap.add_argument("--suffixes", default="",
                    help="final letters a name may also lose when it matches nothing (mimation -m always)")
    args = ap.parse_args()
    if not args.table.is_file():
        print(f"stopped: no theonym table at {args.table}", file=sys.stderr)
        return 2
    table = load(args.table)
    print(json.dumps({name: split(name, table, args.suffixes) for name in args.names}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
