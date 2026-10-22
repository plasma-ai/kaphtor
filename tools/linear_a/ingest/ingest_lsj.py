#!/usr/bin/env python3
"""Ingest the LSJ 9th ed. (Logeion corrected TEI, helmadik/LSJLogeion) into
data/contact/greek_lexicon.jsonl.

Source: TEI XML split across greatscottNN.xml files; each entry is a
<div2 key="betacode"> with a <head> Unicode headword and <sense> bodies.
The first sense's running text (glosses lead as italics) becomes `meaning`.
The TEI is fetched separately; by default it is read from the user cache
(`CACHE/lsj-logeion`). An existing output is copied into `tools.paths.BACKUPS`
before it is rewritten.

Usage:
    python3 tools/linear_a/ingest/ingest_lsj.py [--source DIR] [--limit-files N] [--sample N]

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.ingest"

from ...core.contact_lexicon import _GREEK_TRANSLIT
from ...core.greek_spelling import greek_to_lb
from ...paths import BACKUPS, CACHE, CONTACT_DATA, NotInCheckout, require

DEFAULT_SOURCE = CACHE / "lsj-logeion"
OUT_PATH = CONTACT_DATA / "greek_lexicon.jsonl"

SOURCE_REF = {
    "source": "LSJ 9th ed. (Liddell-Scott-Jones 1940), Logeion corrected TEI (helmadik/LSJLogeion)",
    "page": None,
}

# Greek -> Latin transliteration for match keys: the table normalize_greek uses, so
# ingest-side and query-side keys stay in lockstep. Long/short vowel distinctions
# are folded (eta -> e, omega -> o) because match scoring works on consonantal
# skeletons + broad vowels, mirroring the other contact-DB normalizers.
_TRANSLIT = _GREEK_TRANSLIT

_MEANING_MAX = 220


def transliterate(greek: str) -> str:
    """Strip diacritics and map Greek letters to a Latin match key."""
    decomposed = unicodedata.normalize("NFD", greek.lower())
    out = []
    for ch in decomposed:
        if unicodedata.combining(ch):
            continue
        out.append(_TRANSLIT.get(ch, ch if ch.isalnum() or ch in " -" else ""))
    return "".join(out).strip()


def first_sense_text(div2) -> str:
    sense = div2.find(".//sense")
    if sense is None:
        return ""
    text = " ".join("".join(sense.itertext()).split())
    if len(text) > _MEANING_MAX:
        text = text[:_MEANING_MAX].rsplit(" ", 1)[0] + "…"
    return text


def pos_hint(div2) -> str | None:
    parts = []
    gen = div2.find("gen")
    if gen is not None and gen.text:
        parts.append(gen.text.strip())
    itype = div2.find("itype")
    if itype is not None and itype.text:
        parts.append(itype.text.strip())
    return " ".join(parts) or None


def iter_entries(xml_path: Path):
    import xml.etree.ElementTree as ET

    root = ET.parse(xml_path).getroot()
    for div2 in root.iter("div2"):
        head = div2.find("head")
        if head is None or not (head.text or "").strip():
            continue
        headword = head.text.strip()
        # Skip front-matter divs (abbreviation lists etc.): no betacode key,
        # or headwords written in Latin script.
        if not div2.get("key") or re.search(r"[A-Za-z]", headword):
            continue
        # Editorial hyphens mark compounds in heads; strip for the lemma.
        lemma = headword.replace("-", "")
        normalized = transliterate(lemma)
        if not normalized:
            continue
        yield {
            "headword": lemma,
            "betacode": div2.get("key", ""),
            "normalized": normalized,
            "meaning": first_sense_text(div2),
            "pos": pos_hint(div2),
        }


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--limit-files", type=int, default=None,
                        help="Only parse the first N XML files (validation runs)")
    parser.add_argument("--sample", type=int, default=0,
                        help="Print N sample entries instead of writing")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--backups", type=Path, default=BACKUPS,
                        help="where an existing output is copied first")
    args = parser.parse_args()

    source = require(args.source, "the LSJ Logeion TEI (helmadik/LSJLogeion)")
    xml_files = sorted(source.glob("greatscott*.xml"))
    if not xml_files:
        print(f"no greatscott*.xml under {source}", file=sys.stderr)
        return 1
    if args.limit_files:
        xml_files = xml_files[: args.limit_files]

    rows = []
    counter = 0
    for xml_path in xml_files:
        for entry in iter_entries(xml_path):
            counter += 1
            row = {
                "id": f"gk_lsj_{counter:06d}",
                "language": "Ancient Greek",
                "language_family": "Indo-European (Hellenic)",
                "form_original": entry["headword"],
                "betacode": entry["betacode"],
                "normalized": entry["normalized"],
                "lb_key": greek_to_lb(entry["normalized"]),
                "match_keys": [entry["normalized"]],
                "meaning": entry["meaning"],
                "pos": entry["pos"],
                "semantic_domain": ["general"],
                "source_refs": [SOURCE_REF],
                "review_status": "machine_imported",
            }
            rows.append(row)

    if args.sample:
        for row in rows[: args.sample]:
            print(json.dumps(row, ensure_ascii=False))
        # Show a few substantive entries (with glosses) too
        glossed = [r for r in rows if len(r["meaning"]) > 40]
        print(f"\n-- glossed sample ({len(glossed)}/{len(rows)} have >40-char meanings) --")
        for row in glossed[: args.sample]:
            print(json.dumps(row, ensure_ascii=False))
        return 0

    if args.out.exists():
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
        args.backups.mkdir(parents=True, exist_ok=True)
        dest = args.backups / f"{args.out.stem}-{stamp}{args.out.suffix}"
        shutil.copy2(args.out, dest)
        print(f"backup {dest}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} entries from {len(xml_files)} files -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
