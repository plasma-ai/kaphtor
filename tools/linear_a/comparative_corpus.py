#!/usr/bin/env python3
"""Inspect isolated comparative corpora without promoting their analyses."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import ANE_DATA, LINEAR_A_DATA, NotInCheckout, require

BASE = LINEAR_A_DATA / "comparative_corpora"
MANIFEST = BASE / "manifest.json"
# A record's `root` names the collection its `path` is relative to; the path's leading `data/` is that dataset's
# folder here.
ROOTS = {
    "linear-a-decipherment": LINEAR_A_DATA,
    "ancient-near-east-research": ANE_DATA,
}


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def resolve_path(record: dict) -> Path:
    """Resolve schema-v2 root-relative references; accept legacy absolute rows read-only."""
    value = record["path"]
    if record.get("root"):
        return ROOTS[record["root"]] / value.removeprefix("data/")
    path = Path(value)
    if path.is_absolute():
        return path
    raise ValueError(f"path reference has no registered root: {record}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list registered corpora")
    parser.add_argument("--stats", action="store_true", help="show registry statistics")
    parser.add_argument("--corpus", help="restrict by corpus_id")
    parser.add_argument("--search", help="search source transcription and metadata")
    parser.add_argument("--include-hypotheses", action="store_true", help="also search explicitly labeled interpretive annotations")
    parser.add_argument("--include-excluded", action="store_true", help="include fakes and separated controls")
    parser.add_argument("--preserved-only", action="store_true", help="exclude external rows explicitly marked unpreserved")
    parser.add_argument("--limit", type=int, default=100, help="maximum matching rows")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(require(MANIFEST, "comparative_corpora/manifest.json").read_text(encoding="utf-8"))
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    corpora = manifest["corpora"]
    if args.list or args.stats or not args.search:
        result = corpora if args.list else {
            "corpora": len(corpora),
            "indexed": sum(row["status"].startswith("indexed") for row in corpora),
            "blocked_or_incomplete": sum(row["status"] in {"export_required", "not_indexed", "partially_indexed"} for row in corpora),
            "known_gaps": len(manifest["known_gaps"]),
            "policy": manifest["policy"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
        if not args.search:
            return 0
    query = args.search.casefold()
    paths = [("eteocretan", BASE / "eteocretan/records.jsonl")]
    if args.include_excluded:
        paths.append(("eteocypriot-control", BASE / "eteocretan/separated_controls.jsonl"))
    for corpus in corpora:
        if args.corpus and corpus["corpus_id"] != args.corpus:
            continue
        for index in corpus.get("search_indexes") or []:
            paths.append((corpus["corpus_id"], resolve_path(index)))
    hits = []
    for registry_corpus, path in paths:
        if not path.exists():
            continue
        for row in read_jsonl(path):
            row_corpus = row.get("corpus_id", registry_corpus)
            if args.corpus and row_corpus != args.corpus and registry_corpus != args.corpus:
                continue
            if not args.include_excluded and not row.get("include_by_default", True):
                continue
            if args.preserved_only and row.get("preserved") is not True:
                continue
            source_haystack = json.dumps({k: v for k, v in row.items() if k != "interpretive_annotations"}, ensure_ascii=False).casefold()
            hypothesis_haystack = json.dumps(row.get("interpretive_annotations", []), ensure_ascii=False).casefold()
            if query in source_haystack or (args.include_hypotheses and query in hypothesis_haystack):
                hits.append({"_registry_corpus": registry_corpus, **row})
                if len(hits) >= args.limit:
                    break
        if len(hits) >= args.limit:
            break
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        print("\n".join(
            f"{row['_registry_corpus']}\t{row.get('record_id') or row.get('document_id') or row.get('id') or '?'}\t"
            f"{row.get('site') or row.get('place') or row.get('document') or row.get('title') or ''}"
            for row in hits
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
