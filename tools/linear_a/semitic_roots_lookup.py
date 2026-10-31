#!/usr/bin/env python3
"""Is a root already in semitic_roots.json, or one close to it? Read-only: prints, never writes.

A query is a root or headword in any notation the PS parser reads (ʔ-s-d, *ʔasad-, ś-r-ʕ, knš, *-ka). Its radical
keys are looked up in the Shoresh root index (CACHE/root_index.sqlite, built by build_root_index.py), whose keys
come from every record's PS headword, its weak variants and every reflex form. Hits are grouped by record, best
tier first:

  exact        a key with the same radicals (a PS headword, a weak variant, or a daughter form)
  same class   the same shadow key: the consonant classes match, so ś/š/s, ḳ/k/g, ḥ/ḫ/ʿ spellings meet here
  one off      one consonant class added or dropped (a weak radical, a biradical, a prefix); a superset, so read it
  meaning      with --meaning: records whose meaning carries the word (--glosses: also the reflexes' quoted glosses)

Within a tier, rows run by d, an edit distance over the actual radicals (0 same, 0.5 same base letter or two
gutturals, 1 otherwise), so ś-r-ʕ for š-r-ʿ sits above s-d for ʔ-s-d. ★ marks a --meaning match.

Usage:
  uv run tools/linear_a/semitic_roots_lookup.py ʔ-s-d
  uv run tools/linear_a/semitic_roots_lookup.py '*ʔasad-' --meaning lion
  uv run tools/linear_a/semitic_roots_lookup.py k-n-s g-n-b --limit 10
  uv run tools/linear_a/semitic_roots_lookup.py --meaning naphtha
  uv run tools/linear_a/semitic_roots_lookup.py t-r-s --json

The index must be current (build_root_index.py --check); a stale or missing index exits 2 and is never read.
Contact-lexicon edits do not make it stale: only semitic_roots.json and the key-logic files are checked. Only
reflexes whose source licence lets the gloss ship carry one, so --glosses reads fewer glosses than the full data.

Exit status: 0; 1 if a query gave no radicals; 2 if the index is stale or missing.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.root_index import DEFAULT_INDEX, GUTTURALS, IndexStale, RootIndex, _base_letter, _ro, shadow_key
from ..core.semitic_root_schema import ps_radical_keys

TIERS = ("exact", "same class", "one off", "meaning")
KIND_ORDER = {"ps": 0, "weak": 1, "reflex": 2}


def radical_cost(a: str, b: str) -> float:
    """0 for the same radical; 0.5 for the same base letter (s/ś/š, h/ḥ, t/ṭ) or two gutturals; 1 otherwise."""
    if a == b:
        return 0.0
    if _base_letter(a) == _base_letter(b) or (a in GUTTURALS and b in GUTTURALS):
        return 0.5
    return 1.0


def distance(q: tuple[str, ...], k: tuple[str, ...]) -> float:
    """Edit distance over radicals, substitutions weighted by radical_cost: how far a hit is from the query."""
    prev = [float(j) for j in range(len(k) + 1)]
    for i, a in enumerate(q, 1):
        cur = [float(i)]
        for j, b in enumerate(k, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + radical_cost(a, b)))
        prev = cur
    return prev[-1]


def index_records(path: Path) -> tuple[dict[str, tuple[str, str]], dict[str, dict[str, str]]]:
    """(Number → (PS headword, meaning), Number → {language: Analogues text}) from the index's own tables."""
    conn = _ro(path)
    try:
        roots = {n: (ps or "", meaning or "") for n, ps, meaning in conn.execute("SELECT number, ps, meaning FROM roots")}
        analogues: dict[str, dict[str, str]] = {}
        for n, language, text in conn.execute("SELECT number, language, text FROM analogues"):
            analogues.setdefault(n, {})[language] = text or ""
    finally:
        conn.close()
    return roots, analogues


def meaning_hits(words: list[str], roots: dict[str, tuple[str, str]],
                 analogues: dict[str, dict[str, str]], glosses: bool) -> set[str]:
    """Numbers whose Meaning carries any of the words (word start, case-insensitive); with glosses, also the quoted
    Analogues glosses, which catch a daughter's sense and also every passing mention."""
    pats = [re.compile(rf"\b{re.escape(w)}", re.IGNORECASE) for w in words]
    out = set()
    for n, (_, meaning) in roots.items():
        text = meaning
        if glosses:
            text += " " + " ".join(re.findall(r"'([^']*)'", " ".join(analogues.get(n, {}).values())))
        if any(p.search(text) for p in pats):
            out.add(n)
    return out


def lookup(idx: RootIndex, query: str) -> tuple[list[tuple[str, ...]], dict[str, dict]]:
    """(the query's radical keys, Number → {tier, keys}) over every key of the query."""
    keys = list(ps_radical_keys(query))
    found: dict[str, dict] = {}
    for radicals in keys:
        shadow = shadow_key(radicals)[0]
        exact = [k for k in idx.candidates(shadow, 0) if k.radicals == radicals]
        same = [k for k in idx.candidates(shadow, 0) if k.radicals != radicals]
        near = [k for k in idx.candidates(shadow, 1) if k.shadow != shadow] if len(shadow) >= 2 else []
        for tier, hits in (("exact", exact), ("same class", same), ("one off", near)):
            for k in hits:
                if k.number is None:
                    continue
                d = distance(radicals, k.radicals)
                rec = found.setdefault(k.number, {"tier": tier, "keys": [], "distance": d})
                if TIERS.index(tier) < TIERS.index(rec["tier"]):
                    rec["tier"], rec["keys"], rec["distance"] = tier, [], d
                if rec["tier"] == tier:
                    rec["keys"].append(k)
                    rec["distance"] = min(rec["distance"], d)
    return keys, found


def run(index_path: Path, queries: list[str], words: list[str], glosses: bool = False) -> tuple[list[dict], int]:
    """(one report per query, exit status). Raises IndexStale or FileNotFoundError when the index is unusable."""
    idx = RootIndex.load(index_path, include_lexemes=False)
    roots, analogues = index_records(index_path)
    by_meaning = meaning_hits(words, roots, analogues, glosses) if words else set()

    status, report = 0, []
    for q in queries or [None]:
        if q is None:
            keys, found = [], {}
        else:
            keys, found = lookup(idx, q)
            if not keys:
                print(f"{q}: no radicals read", file=sys.stderr)
                status = 1
                continue
        for n in by_meaning - set(found):
            found[n] = {"tier": "meaning", "keys": [], "distance": None}
        rows = []
        for n, hit in found.items():
            ks = sorted(hit["keys"], key=lambda k: (KIND_ORDER.get(k.kind, 3), k.language))
            ps, meaning = roots.get(n, ("", ""))
            rows.append({"number": n, "tier": hit["tier"], "distance": hit["distance"], "ps": ps, "meaning": meaning,
                         "meaning_match": n in by_meaning,
                         "via": [{"kind": k.kind, "language": k.language, "form": k.form,
                                  "radicals": "-".join(k.radicals)} for k in ks]})
        rows.sort(key=lambda r: (TIERS.index(r["tier"]), not r["meaning_match"], r["distance"] or 0,
                                 min((KIND_ORDER.get(v["kind"], 3) for v in r["via"]), default=4), r["number"]))
        report.append({"query": q, "keys": ["-".join(k) for k in keys],
                       "shadows": sorted({shadow_key(k)[0] for k in keys}), "meaning": words, "rows": rows})
    return report, status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("query", nargs="*", help="root or headword: ʔ-s-d, *ʔasad-, knš")
    ap.add_argument("--meaning", action="append", default=[],
                    help="word to match in Meaning (repeatable, or comma-separated)")
    ap.add_argument("--glosses", action="store_true", help="--meaning also searches the quoted Analogues glosses")
    ap.add_argument("--limit", type=int, default=15, help="records shown per tier (0: all)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX, help="the root index to read")
    args = ap.parse_args(argv)
    words = [w.strip() for m in args.meaning for w in m.split(",") if w.strip()]
    if not args.query and not words:
        ap.error("give a root, --meaning, or both")
    try:
        report, status = run(args.index, args.query, words, args.glosses)
    except (IndexStale, FileNotFoundError) as exc:
        print(f"root index unusable: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return status
    for r in report:
        head = f"{r['query']} → {', '.join(r['keys'])} (shadow {', '.join(r['shadows'])})" if r["query"] else ""
        if r["meaning"]:
            head += f"{'  ' if head else ''}meaning: {', '.join(r['meaning'])}"
        print(head)
        for tier in TIERS:
            rows = [x for x in r["rows"] if x["tier"] == tier]
            if not rows:
                continue
            shown = rows if args.limit == 0 else rows[: args.limit]
            print(f"  {tier.upper()} ({len(rows)})")
            for x in shown:
                star = "★ " if x["meaning_match"] else "  "
                d = "" if x["distance"] is None else f"d={x['distance']:g} "
                via = "; ".join(list(dict.fromkeys(
                    f"{v['language']} {v['form']}" if v["kind"] == "reflex" else f"{v['kind']} {v['form']}"
                    for v in x["via"]))[:3])
                print(f"   {star}{d}{x['number']:>6}  {x['ps']}  {x['meaning']}" + (f"   ← {via}" if via else ""))
            if len(rows) > len(shown):
                print(f"     … {len(rows) - len(shown)} more (--limit 0)")
        print()
    return status


if __name__ == "__main__":
    sys.exit(main())
