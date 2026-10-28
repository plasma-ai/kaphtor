"""Protocol C, phase C1: check one builder's inventory (PROTOCOL-C §5.3).

Usage:
    uv run --with jsonschema python3 -I check_inventory.py <build folder>

The build folder is protocol-c/builds/<arm>/ as run_builder.sh leaves it. Checks, in order:

1. inventory.json validates against schema.json (the copy in the kit, which kit.sha256 pins).
2. Blindness (§5.3 item 2): no function, source or notes string names Linear A, Minoan, Ya Diktu (except in the
   yd arm), or any hyphenated corpus word of two or more signs. Forms and segments are not scanned: a Linear B
   Greek ending is itself a hyphenated syllable string and could match a corpus word by chance.
3. Coverage: every entry's source.unit is in units_read, and every unit row of units.md is in units_read.

On success it writes inventory.filled.json beside the builder's file (which it never touches), with the runner
fields filled from the transcript, session_started_utc.txt and kit.sha256. Refuses to overwrite that file.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import jsonschema

CORPUS = Path("linear-a-decipherment/data/corpus.json")
FORBIDDEN = ("linear a", "linear-a", "minoan", "ya diktu", "diktu", "libation formula", "peak sanctuary")


def corpus_needles() -> set[str]:
    docs = json.loads(CORPUS.read_text(encoding="utf-8"))
    needles: set[str] = set()
    for doc in docs.values():
        for w in doc.get("transliteratedWords") or []:
            if isinstance(w, str) and "-" in w:
                needles.add(w.lower())
    return needles


def mentions(text: str, needle: str) -> bool:
    return re.search(r"(?<![\w*])" + re.escape(needle) + r"(?![\w*])", text) is not None


def unit_labels(units_md: str) -> list[tuple[str, ...]]:
    """The cells of every data row in the first table of units.md (later tables, such as counts, are not units).

    A builder may label a unit by its section / table number or by its printed title; a row counts as read when any
    of its cells matches a units_read label."""
    labels, started = [], False
    for line in units_md.splitlines():
        if not line.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] in {"Nominal", "Pronominal", "Verbal", "Clitics"}:
            # Unit-type words, source names and a bare appendix name match too much to identify a row.
            generic = re.compile(r"^(table|list|headed section.*|stated innovation|appendix [a-z])$", re.I)
            labels.append(tuple(c for c in cells[1:5]
                                if len(c) > 3 and not generic.match(c) and not c.startswith("Huehnergard")))
    return labels


def main(folder: Path) -> int:
    inv = json.loads((folder / "inventory.json").read_text(encoding="utf-8"))
    schema = json.loads((folder / "schema.json").read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(inv), key=lambda e: list(e.path))
    for e in errors:
        print(f"[schema] {'/'.join(map(str, e.path))}: {e.message}")
    arm = inv.get("arm", "?")

    forbidden = [f for f in FORBIDDEN if not (arm == "yd" and "diktu" in f)]
    needles = corpus_needles()
    blind = []
    for r in inv.get("entries", []):
        src = r.get("source", {})
        text = " ".join([r.get("function", ""), src.get("unit", ""), src.get("section", ""),
                         r.get("notes", "")]).lower()
        blind += [f"{r['id']}: {f!r}" for f in forbidden if f in text]
        blind += [f"{r['id']}: corpus word {n!r}" for n in needles if mentions(text, n)]
    for b in blind:
        print(f"[blindness] {b}")

    read = set(inv.get("units_read", []))
    cover = [f"{r['id']}: unit {r['source']['unit']!r} not in units_read"
             for r in inv.get("entries", []) if r.get("source", {}).get("unit") not in read]
    labels = unit_labels((folder / "units.md").read_text(encoding="utf-8"))
    def norm(s: str) -> str:
        return s.strip().strip('"“”').lower()
    unmatched = [(k, " / ".join(cells)) for k, cells in enumerate(labels, 1)
                 if not any(norm(c) and (norm(c) in norm(u) or norm(u) in norm(c)) for c in cells for u in read)]
    by_row = [u for u in read if re.search(r"\brow \d+\]", u)]
    notes = (folder / "notes.md").read_text(encoding="utf-8") if (folder / "notes.md").exists() else ""
    in_notes = {int(m) for m in re.findall(r"^\|\s*(\d+)\s*\|", notes, flags=re.M)}
    if unmatched and len(by_row) == len(unmatched):
        # The builder labelled rows whose title column is not a unit name (yd Appendix B host words) by row number.
        print(f"coverage: {len(unmatched)} rows matched by row-number labels ({by_row[0]} … {by_row[-1]})")
    elif unmatched and all(k in in_notes for k, _ in unmatched):
        # The builder gave such rows one collective label and accounted for each, by data-row number, in a table in
        # notes.md.
        print(f"coverage: {len(unmatched)} rows accounted for row by row in notes.md "
              f"(rows {unmatched[0][0]}–{unmatched[-1][0]})")
    else:
        cover += [f"units.md row {k} {l!r} not in units_read" for k, l in unmatched]
    for c in cover:
        print(f"[coverage] {c}")

    entries = inv.get("entries", [])
    slots = Counter((r["side"], r["slot"]) for r in entries)
    distinct = {(r["side"], tuple(r["segments"])) for r in entries}
    print(f"arm {arm}: {len(entries)} entries, {len({r['morpheme_id'] for r in entries})} morphemes, "
          f"{len(distinct)} distinct (side, segments)")
    for (side, slot), n in sorted(slots.items()):
        print(f"  {side:6} {slot:16} {n}")
    print(f"class_order: {inv.get('class_order')}")

    if errors or blind or cover:
        print("FAIL")
        return 1

    filled = folder / "inventory.filled.json"
    if filled.exists():
        sys.exit(f"refuse: {filled} exists")
    model = None
    for line in (folder / "transcript.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            model = ev.get("model")
            break
    sums = {name.strip(): h for h, name in (l.split(None, 1) for l in (folder / "kit.sha256").read_text().splitlines())}
    listed = folder / "grammar_files.txt"
    grammar = (listed.read_text(encoding="utf-8").split()[0] if listed.exists()
               else next(k for k in sorted(sums) if k.startswith("grammar") and not k.endswith(".txt")))
    recorded = folder / "builder_model.txt"   # Codex runs: the runner's record (the --json log names no model)
    if model is None and recorded.exists():
        model = recorded.read_text(encoding="utf-8").strip()
    inv["builder"] = {"model": model or "unknown",
                      "session_started_utc": (folder / "session_started_utc.txt").read_text().strip(),
                      "transcript_file": "transcript.jsonl"}
    inv["grammar"]["file_sha256"] = sums[grammar]
    filled.write_text(json.dumps(inv, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"PASS; wrote {filled.name} (grammar file {grammar})")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
