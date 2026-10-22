#!/usr/bin/env python3
"""Query local Pleiades, Trismegistos and iDAI place records."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from ane_keys import fold_pattern, loose_key, marks_kept

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import ANE_DATA, SHARE_ALIKE

ROOT = ANE_DATA / "place-authorities"
FILES = {
    "pleiades": ROOT / "pleiades_places.jsonl",
    "tm": SHARE_ALIKE / "trismegistos" / "trismegistos_places.jsonl",
    "idai": ROOT / "idai_places.jsonl",
}


def fold(value) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", str(value or "")).casefold()
        if not unicodedata.combining(char)
    )


def label_values(row: dict) -> list[str]:
    values = [
        row.get("title"), row.get("name_standard"), row.get("full_name"),
        row.get("name_latin"), row.get("unicode_greek"), row.get("unicode_egyptian"),
        row.get("unicode_coptic"), (row.get("preferred_name") or {}).get("title"),
    ]
    for name in row.get("names") or []:
        values.extend((name.get("title"), name.get("attested"), name.get("romanized")))
    return [str(value) for value in values if value]


# Match basis, as query_proper_names names it: the whole label as typed (marks stripped), the folded key, or
# part of a label.
EXACT, FOLDED, SUBSTRING = 0, 2, 4


def folding(query: str):
    """The query's folded key and compiled fold pattern (ane_keys), or None when nothing is left to fold."""
    key = loose_key(query)
    return (key, re.compile(fold_pattern(query))) if key else None


def folded_match(labels: list[str], folded, exact: bool) -> bool:
    """ane_keys' one-directional fold: separators and the aleph/ayin signs folded, a typed mark kept
    (Tell el Amarna finds Tell el-Amarna, 'Akko finds ʿAkko). The fold pattern is tested first: it is cheap,
    and loose_key, which must agree with it, is not."""
    key, pattern = folded
    for label in labels:
        kept = marks_kept(label)
        if exact and pattern.fullmatch(kept) and loose_key(label) == key:
            return True
        if not exact and pattern.search(kept) and key in loose_key(label):
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--authority", choices=("pleiades", "tm", "idai", "all"), default="all")
    ap.add_argument("--id")
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--loose", action="store_true",
                    help="also match with separators and aleph/ayin signs folded (otherwise only when nothing "
                         "matches strictly)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    needle = fold(args.query)

    selected = FILES if args.authority == "all" else {args.authority: FILES[args.authority]}
    # A missing authority is named; with --authority all the others are still searched.
    for authority, path in list(selected.items()):
        if not path.exists():
            message = f"{authority} is not in this checkout (looked for {path})"
            if args.authority != "all":
                raise SystemExit(message)
            print(message, file=sys.stderr)
            selected = {a: p for a, p in selected.items() if a != authority}

    folded = folding(args.query) if needle else None

    def scan() -> list[dict]:
        """Matching rows, in one pass. The folded tier joins when --loose asks for it, or when no label matches
        as a whole (a substring hit alone does not keep a folded whole name out), as in query_proper_names."""
        found, fold_only = [], []
        whole = False
        for authority, path in selected.items():
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    row = json.loads(line)
                    if args.id and str(row.get("authority_id")) != args.id:
                        continue
                    item = {"dataset": authority, **row}
                    if not needle:
                        if len(found) >= args.limit:
                            return found
                        found.append(item)
                        continue
                    labels = label_values(row)
                    matched = any(fold(label) == needle for label in labels) if args.exact else any(needle in fold(label) for label in labels)
                    if matched:
                        whole_label = args.exact or any(fold(label) == needle for label in labels)
                        whole = whole or whole_label
                        found.append({**item, "match_basis": EXACT if whole_label else SUBSTRING})
                    # The folded tier is needed only under --loose or until a label matches as a whole.
                    elif folded and (args.loose or not whole) and folded_match(labels, folded, args.exact):
                        fold_only.append({**item, "match_basis": FOLDED})
        return found + fold_only if args.loose or not whole else found

    results = scan()
    if needle:
        results.sort(key=lambda row: (
            row["match_basis"],
            not any(fold(label) == needle for label in label_values(row)),
            row["dataset"], str(row.get("authority_id")),
        ))
    results = results[: args.limit]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for row in results:
            label = (row.get("preferred_name") or {}).get("title") or row.get("title") or row.get("name_standard") or row.get("full_name")
            print(f"{row['dataset']}\t{row.get('authority_id')}\t{label or ''}\t{row.get('uri') or ''}")


if __name__ == "__main__":
    main()
