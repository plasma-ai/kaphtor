# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check corpus.json's scribe fields against the hand-edited scribes.json. Read-only: writes nothing.

A record's `scribe` is a scribe's label (`HT Scribe 9`, `KH Wc Scribe 54`), empty where no edition assigns one.
`scribe_doubt: true` marks an attribution the edition prints with a question mark. `scribe_gorila` holds the cell
GORILA V prints for a Haghia Triada tablet, whose label follows Militello 1989's numbering. The check reports:
  a label with no entry in scribes.json, and an entry no record carries
  doubt written into the label, and scribe_doubt beside no scribe
  a label that does not open with its record's site code
  scribe_gorila on anything but a Haghia Triada tablet
  scribe_also (a second scribe on the same record, `[{"scribe": label, "part": "lines 4–6"}]`) that is malformed,
  repeats the record's scribe or stands beside none; scribe_part (the part the first scribe wrote) beside no scribe
  a registry entry without site, class, numbering or source
Exit status 1 when anything is reported, 2 when a file it reads is not in the checkout.

    uv run tools/linear_a/validation/check_scribes.py [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...paths import LINEAR_A_DATA, NotInCheckout, require

REQUIRED = ("site", "class", "numbering", "source")


def problems(corpus: dict, registry: dict) -> list[str]:
    out: list[str] = []
    carried: set[str] = set()
    for name, rec in corpus.items():
        label = (rec.get("scribe") or "").strip()
        if rec.get("scribe_doubt") and not label:
            out.append(f"{name}: scribe_doubt stands beside no scribe")
        if rec.get("scribe_gorila") and not re.fullmatch(r"HT\d+(\+\d+)*[a-z]?", name):
            out.append(f"{name}: scribe_gorila belongs to Haghia Triada tablets only")
        also = rec.get("scribe_also")
        also_labels: list[str] = []
        if also:
            if not (isinstance(also, list) and all(isinstance(a, dict) and (a.get("scribe") or "").strip() for a in also)):
                out.append(f'{name}: scribe_also must be a list of {{"scribe", "part"}} objects')
            else:
                also_labels = [a["scribe"].strip() for a in also]
                if not label:
                    out.append(f"{name}: scribe_also stands beside no scribe")
                if label in also_labels:
                    out.append(f"{name}: scribe_also repeats the record's scribe")
        if rec.get("scribe_part") and not label:
            out.append(f"{name}: scribe_part stands beside no scribe")
        for lab in dict.fromkeys(([label] if label else []) + also_labels):
            if "?" in lab:
                out.append(f'{name}: scribe "{lab}" carries its doubt in the label; use scribe_doubt')
                continue
            carried.add(lab)
            if lab not in registry:
                out.append(f'{name}: scribe "{lab}" has no entry in scribes.json')
            if not name.startswith(lab.split()[0]):
                out.append(f'{name}: scribe "{lab}" does not open with the record\'s site code')
    for label, entry in registry.items():
        if label not in carried:
            out.append(f'scribes.json: "{label}" is carried by no corpus record')
        missing = [f for f in REQUIRED if not entry.get(f)]
        if missing:
            out.append(f'scribes.json: "{label}" lacks {", ".join(missing)}')
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    args = ap.parse_args()
    try:
        corpus, registry = (json.loads(require(LINEAR_A_DATA / name, name).read_text(encoding="utf-8"))
                            for name in ("corpus.json", "scribes.json"))
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    found = problems(corpus, registry["scribes"])
    if args.json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
    else:
        for line in found:
            print(line)
        assigned = sum(1 for r in corpus.values() if r.get("scribe") or r.get("scribe_also"))
        print(f"{len(registry['scribes'])} scribes, {assigned} attributed records, {len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
