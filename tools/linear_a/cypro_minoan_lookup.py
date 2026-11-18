#!/usr/bin/env python3
"""Query the Cypro-Minoan catalogue: one record per text, keyed by siglum, with its site and object type decoded from
Valério's key to the sigla (2016, 36-37), its edition of record, and the metadata statements of held works, each with
its work and page.

The catalogue carries no transcription: the corpus is transcribed in Valério 2016's Appendix A, a thesis whose terms
allow private research use only, and the record names the pages. A statement in its source's own words is a pointer
to the page. Cypro-Minoan is a comparandum for Linear A; nothing here enters the Linear A corpus.

Examples:
  cypro_minoan_lookup.py --doc "ENKO Atab 004"      # one text: siglum, ## number, museum or object number
  cypro_minoan_lookup.py --doc "RS 20.25"
  cypro_minoan_lookup.py --site KITI --type Avas    # the texts by site and HoChyMin type codes (Kition's vessels)
  cypro_minoan_lookup.py --stats
  cypro_minoan_lookup.py --doc 209 --format json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import ANE_DATA, NotInCheckout, require

CATALOGUE_FILE = ANE_DATA / "cypro-minoan" / "catalogue.json"
FIELDS = ("identity", "museum_no", "editions", "findspot", "date", "dimensions", "object", "document_form", "hand",
          "visual_evidence")
POINTER = "[the source's own words, not reproduced]"


def load_catalogue() -> dict:
    return json.loads(require(CATALOGUE_FILE, "cypro-minoan/catalogue.json").read_text(encoding="utf-8"))


def _key(text: str) -> str:
    """'ENKO Atab 004' and 'enko atab 4' -> 'ENKOATAB4': case, spaces and leading zeros dropped."""
    return re.sub(r"(?<!\d)0+(?=\d)", "", re.sub(r"\s+", "", text)).upper()


def _unmarked(text: str) -> str:
    return re.sub(r"[?*]", "", _key(text))


def resolve(query: str, catalogue: dict) -> tuple[str, dict] | None:
    """A text by its siglum ('ENKO Atab 004', 'enko atab 4'; 'CYPR Psce 003' for 'CYPR? Psce 003' when nothing answers
    with the mark), its number ('##209', 'cm:##209', '209', 'ADD##221', or '##221' as Donnelly writes it), the key of
    a text without a siglum, a number a held source gives the object ('RS 20.25', or either side of 'ENKO Atab 002a =
    ##207A = no. 20.01'), or its museum number, whole, after its last comma or as the number after 'inv.' or 'no.'
    ('DO 5288', 'inv. 1885', '1885'). Bare digits are a ## number first ('209'), then a museum number ('1193'). None
    when no text answers, or more than one does."""
    q = re.sub(r"^\s*cm:", "", query.strip(), flags=re.IGNORECASE)
    if not q:
        return None

    def names(key: str, r: dict) -> list[str]:
        number = r["record_id"].removeprefix("cm:")
        return [key, number, number.removeprefix("ADD")]

    def identities(key: str, r: dict) -> list[str]:
        stated = [st["text"] for st in r["identity"] if st["text"]]
        museum = [st["text"] for st in r["museum_no"] if st["text"]]
        parts = [side.strip() for text in stated for side in text.split(" = ")] + [m.rsplit(", ", 1)[-1] for m in museum]
        numbers = [m.group(1) for p in parts if (m := re.search(r"\b(?:inv|no)\.\s*([\w.]+)$", p, re.IGNORECASE))]
        return stated + museum + parts + numbers

    passes = ((_key, names), (_unmarked, names), (_key, identities))
    for candidate in ([f"##{q}", q] if q.isdigit() else [q]):
        for fold, field in passes:
            found = [(key, r) for key, r in catalogue.items() if fold(candidate) in map(fold, field(key, r))]
            if found:
                return found[0] if len(found) == 1 else None
    return None


def _where(cites: list[dict]) -> str:
    return "; ".join(f"{c['work']}, {c['page']}" for c in cites)


def _cite(c: dict) -> str:
    where = c["work"] + (f" ({c['chapter']})" if c.get("chapter") else "") + (f", {c['page']}" if c.get("page") else "")
    where += f", fig. {c['figure']}" if c.get("figure") else ""
    return where + (f", table {c['table']}" if c.get("table") else "")


def format_doc(key: str, r: dict) -> str:
    number = f"{r['corpus_no']} ({r['record_id']})" if r["corpus_no"] else r["record_id"]
    lines = ["=" * 60, f"  {r['siglum'] or key}  —  {number}", "=" * 60]
    sources = r["field_sources"]
    lines.append(f"  Status: {r['inclusion_status'] or 'outside Valério 2016, Appendix A'}; text: {r['text_status']}")
    if r["site_code"]:
        queried = "?" if r["site_queried"] else ""
        lines.append(f"  Site: {r['site']} ({r['site_code']}{queried}; {_where(sources.get('site', []))})"
                     if r["site"] else f"  Site: {r['site_code']}{queried}, not decoded")
    a = r["site_authorities"]
    if a:
        ids = ", ".join(f"{name} {a[k]}" for k, name in (("pleiades", "Pleiades"), ("tm", "Trismegistos")) if a.get(k))
        lines.append(f"    identity controls, never attestations: {ids or 'none'} (match: {a['match']})"
                     + (f"; {a['note']}" if a.get("note") else ""))
    t = r["hochymin_type"]
    if t:
        lines.append(f"  Type: {r['type_code']}, {t['gloss']} ({_where(sources.get('hochymin_type', []))})"
                     + (f"; {t['note']}" if t.get("note") else ""))
    if r["traditional_subcorpus"]:
        lines.append(f"  Subcorpus: {r['traditional_subcorpus']}")
    e = r["edition"]
    if e["of_record"]:
        pages = e["appendix_a_pages"]
        span = (f", Appendix A, {pages[0]}–{pages[-1]}" if len(pages) > 1 else f", Appendix A, {pages[0]}") \
            if pages else ""
        state = "verified" if e["verified"] else f"unverified: {e['verification_note']}"
        lines.append(f"  Edition: {e['of_record']}, transcribed in Valério 2016{span}; {state}")
        lines += [f"    {e['edition_note']}"] if e.get("edition_note") else []
    for block, text in ((r["siglum_note"], "note"), (r["siglum_exception"], "reason")):
        if block:
            lines.append(f"  Siglum: {block[text]}")
            lines += [f"      {_cite(c)}" for c in block["cites"]]
    w = r["witness"]
    if w:
        lines.append(f"  Witness outside Appendix A ({w['kind']}): {w['what']}")
        lines += [f"      {_cite(c)}" for c in w["cites"]]

    lines += ["", "  Metadata, each statement with its source"]
    empty = []
    for field in FIELDS:
        if not r[field]:
            empty.append(field)
            continue
        lines.append(f"  {field}")
        for st in r[field]:
            lines.append(f"    {POINTER if st.get('pointer') else st['text']}"
                         + (f" [{st['basis']}]" if st.get("basis") else "")
                         + (f" (relayed from {st['relayed_from']})" if st.get("relayed_from") else ""))
            lines += [f"      note: {st['note']}"] if st.get("note") else []
            lines += [f"      {_cite(c)}" for c in st["cites"]]
    if empty:
        lines.append(f"  No held source states: {', '.join(empty)}")
    lines += ["", ("  No transcription ships in this repository; the edition line names the pages of Valério 2016 that "
                   "transcribe the text.")]
    return "\n".join(lines)


def _codes(value: str | None) -> list[str]:
    return [c.strip() for c in (value or "").split(",") if c.strip()]


def text_filter(args: argparse.Namespace, catalogue: dict):
    """--site and --type, comma lists matched without case, as a test on a record. A code no text has exits 1."""
    wanted = {}
    for field, value, name in (("site_code", args.site, "site"), ("type_code", args.type, "type")):
        codes = _codes(value)
        known = {(r[field] or "").casefold() for r in catalogue.values()}
        unknown = [c for c in codes if c.casefold() not in known]
        if unknown:
            print(f"no text has {name} {', '.join(unknown)}", file=sys.stderr)
            sys.exit(1)
        if codes:
            wanted[field] = {c.casefold() for c in codes}

    def keep(r: dict) -> bool:
        return all((r[field] or "").casefold() in codes for field, codes in wanted.items())
    return keep


def format_list(texts: list[tuple[str, dict]], args: argparse.Namespace) -> str:
    what = ", ".join(f"{name} {' or '.join(_codes(value))}" for name, value in (("site", args.site), ("type", args.type))
                     if value)
    if not texts:
        return f"No text for {what}."
    rows = [(r["siglum"] or key, r["corpus_no"] or "", (r["hochymin_type"] or {}).get("gloss") or "",
             r["inclusion_status"] or "outside Appendix A") for key, r in texts]
    width = [max(len(row[i]) for row in rows) for i in range(3)]
    return "\n".join([f"{len(texts)} text{'s' if len(texts) != 1 else ''}, {what}", ""] +
                     ["  " + "  ".join(f"{cell:<{width[i]}}" for i, cell in enumerate(row[:3])) + f"  {row[3]}"
                      for row in rows])


def stats(catalogue: dict) -> dict:
    return {
        "records": len(catalogue),
        "witnesses_outside_appendix_a": sum(1 for r in catalogue.values() if r["witness"]),
        "inclusion_counts": dict(Counter(r["inclusion_status"] for r in catalogue.values() if r["inclusion_status"])),
        "sites": len({r["site_code"] for r in catalogue.values() if r["site_code"]}),
        "types": len({r["type_code"] for r in catalogue.values() if r["type_code"]}),
        "statements": {f: sum(len(r[f]) for r in catalogue.values()) for f in FIELDS},
        "pointers": {f: n for f in FIELDS
                     if (n := sum(1 for r in catalogue.values() for st in r[f] if st.get("pointer")))},
    }


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when the catalogue is not in the checkout."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--doc", metavar="TEXT", help="One text: siglum, ## number, museum or object number")
    parser.add_argument("--site", help="Site codes, comma-separated (e.g., KITI)")
    parser.add_argument("--type", help="HoChyMin type codes, comma-separated (e.g., Avas,Mvas)")
    parser.add_argument("--stats", action="store_true", help="Counts of texts, statements and pointers")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    if not (args.doc or args.site or args.type or args.stats):
        parser.print_help()
        return 0

    if args.stats and (args.doc or args.site or args.type):
        print("--stats takes no --doc, --site or --type", file=sys.stderr)
        return 1
    catalogue = load_catalogue()
    if args.stats:
        counts = stats(catalogue)
        print(json.dumps(counts, ensure_ascii=False, indent=2) if args.format == "json" else "\n".join(
            f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in counts.items()))
        return 0
    if args.site or args.type:
        if args.doc:
            print("--doc takes a text or a filter (--site, --type), not both", file=sys.stderr)
            return 1
        keep = text_filter(args, catalogue)
        texts = sorted(((key, r) for key, r in catalogue.items() if keep(r)), key=lambda kr: kr[0])
        if args.format == "json":
            print(json.dumps({"site": _codes(args.site), "type": _codes(args.type), "texts": [
                {"siglum": r["siglum"] or key, "key": key, "record_id": r["record_id"], "corpus_no": r["corpus_no"],
                 "site": r["site"], "type": (r["hochymin_type"] or {}).get("gloss"),
                 "inclusion_status": r["inclusion_status"]} for key, r in texts]}, ensure_ascii=False, indent=2))
        else:
            print(format_list(texts, args))
        return 0
    found = resolve(args.doc, catalogue)
    if found is None:
        print(f"No Cypro-Minoan text {args.doc!r} in the catalogue, or more than one answers", file=sys.stderr)
        return 1
    key, record = found
    if args.format == "json":
        print(json.dumps({"query": args.doc, "key": key, "record": record}, ensure_ascii=False, indent=2))
    else:
        print(format_doc(key, record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
