#!/usr/bin/env python3
"""Palmyra lookups over the shipped open data: an inscription under its other numbers, and the personal names
that hold a divine name.

    python3 tools/ane/query_palmyra.py sigla "PAT 291"        # PAT 291 = IGLS 56 = CIS 3945; zeros and spacing aside
    python3 tools/ane/query_palmyra.py sigla "IGLS 56" --json
    python3 tools/ane/query_palmyra.py element bol            # names of the dataset that hold Bôl
    python3 tools/ane/query_palmyra.py element --list         # the divine names and their written forms, with pages

`sigla` reads `data/ane/palmyra-public-inscriptions/concordance.jsonl`: the PAT, IGLS, CIS and RES numbers that
one row of Public Inscriptions from Palmyra carries (CC BY 4.0). A number matches whole: PAT 24 does not find PAT
246. The IGLS numbers are those of IGLS XVII/1; the concordance printed in that volume (Yon 2012, pp. 473-490)
lists the other publications of each inscription and is not shipped.

`element` reads `data/ane/palmyrene-theonym-elements/elements.json`, a hand-made table of divine names with the
forms the sources print, and finds each name's vocalised form inside the dataset's personal names, compared without
accents or case. The dataset holds no consonantal spelling, so the table's Aramaic and Greek forms are for reading
the editions. A hit is a substring match: a lead to check, not an analysis of the name. Bēl and Bôl are both
written `bl` in Palmyrene; the table's note on that is this project's rule.
Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import ANE_DATA, require

CONCORDANCE = ANE_DATA / "palmyra-public-inscriptions/concordance.jsonl"
NAMES = ANE_DATA / "palmyra-public-inscriptions/names.jsonl"
ELEMENTS = ANE_DATA / "palmyrene-theonym-elements/elements.json"


def rows(path: Path, dataset: str) -> list[dict]:
    with require(path, dataset).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def typed_key(text: str) -> str | None:
    """The key of a siglum as typed: 'PAT 0246', 'pat246', 'CIS II 3950', 'IGLS XVII/1 56', 'RES 1040'."""
    m = re.match(r"^(pat|cis|res|igls)\s*(?:ii\s+|xvii/1\s+|xvii\s+)?0*(\d+)\s*([a-z]*|\.\d+)$",
                 re.sub(r"\s+", " ", text.strip()), re.IGNORECASE)
    return f"{m.group(1).lower()}:{m.group(2)}{m.group(3).lower()}" if m else None


def sigla(siglum: str) -> list[dict]:
    key = typed_key(siglum)
    if key is None:
        raise ValueError(f"not a PAT, CIS, RES or IGLS number: {siglum}")
    return [r for r in rows(CONCORDANCE, "the Palmyra sigla concordance") if key in r["keys"]]


def bare(text: str) -> str:
    """Lower case, no accents or vowel marks; ʾ and ʿ kept."""
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(c))


def table() -> list[dict]:
    return json.loads(require(ELEMENTS, "the Palmyrene divine-name table").read_text(encoding="utf-8"))["elements"]


def element(name: str) -> list[dict]:
    elements = table()
    if name not in {e["id"] for e in elements}:
        raise ValueError(f"no element {name!r}; --list shows them")
    keys = {e["id"]: [bare(f["form"]) for f in e["vocalised"]] for e in elements}
    found, seen = [], set()
    for row in rows(NAMES, "the Palmyra public inscriptions"):
        if row.get("kind") != "person" or row["name"] in seen:
            continue
        text = bare(row["name"])
        held = sorted(e for e, forms in keys.items() if any(f in text for f in forms))
        if name in held:
            seen.add(row["name"])
            found.append({"name": row["name"], "id": row["id"], "record_id": row["record_id"],
                          "matched": next(f for f in keys[name] if f in text), "also": [e for e in held if e != name],
                          "match_basis": "substring"})
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sigla", help="an inscription's PAT, IGLS, CIS and RES numbers")
    p.add_argument("siglum")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("element", help="personal names that hold a divine name")
    p.add_argument("name", nargs="?")
    p.add_argument("--list", action="store_true")
    p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "sigla":
            found = sigla(args.siglum)
        elif args.list or not args.name:
            for e in table():
                print(f"{e['id']:11} {e['deity']}" + (f"  (built on {e['built_on']})" if e.get("built_on") else ""))
                for script in ("aramaic", "greek", "vocalised"):
                    for f in e.get(script, []):
                        tag = " [ambiguous]" if f.get("ambiguous") else f" [{f['position']}]" if f.get("position") else ""
                        print(f"    {script:9} {f['form']}{tag}: {f['source']}")
            return 0
        else:
            found = element(args.name)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
    elif args.cmd == "sigla":
        for r in found:
            print(f"{' = '.join(r['sigla'])}   ({r['record_id']})")
    else:
        for r in found:
            also = f" [also {', '.join(r['also'])}]" if r["also"] else ""
            print(f"{r['name']}  ({r['matched']}){also}  {r['record_id']}")
    if not found:
        print("no row", file=sys.stderr)
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
