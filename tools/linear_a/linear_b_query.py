#!/usr/bin/env python3
"""Query the locally staged Linear B reference corpus (LiBER).

The corpus is read from data/linear-a/linear_b_corpus/; set LINEAR_B_CORPUS_DIR to read it from elsewhere.

When present, the contextual layer in data/linear-a/ adds document, token occurrence, and ideogram occurrence
indexes built from the same LiBER package.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout

DEFAULT_DIRS = [
    Path(os.environ.get("LINEAR_B_CORPUS_DIR", "")) if os.environ.get("LINEAR_B_CORPUS_DIR") else None,
    LINEAR_A_DATA / "linear_b_corpus",
]

DATA_DIR = LINEAR_A_DATA
CONTEXT_DOCUMENTS = DATA_DIR / "linear_b_document_contexts.json"
CONTEXT_TOKEN_OCCURRENCES = DATA_DIR / "linear_b_token_occurrences.jsonl"
CONTEXT_TOKEN_INDEX = DATA_DIR / "linear_b_token_context_index.json"
CONTEXT_IDEOGRAM_OCCURRENCES = DATA_DIR / "linear_b_ideogram_contexts.jsonl"
CONTEXT_DOMAIN_MODEL = DATA_DIR / "linear_b_administrative_domain_model.json"


def corpus_dir() -> Path:
    for path in DEFAULT_DIRS:
        if path and (path / "liber_linear_b_documents.jsonl").exists():
            return path
    searched = [str(p) for p in DEFAULT_DIRS if p]
    raise NotInCheckout(f"liber_linear_b_documents.jsonl is not in this checkout (looked in {', '.join(searched)})")


def load_docs() -> Iterable[dict]:
    path = corpus_dir() / "liber_linear_b_documents.jsonl"
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_manifest() -> dict:
    path = corpus_dir() / "liber_linear_b_manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    docs = list(load_docs())
    return {
        "status": "partial_no_manifest",
        "document_records": len(docs),
        "documents_with_extracted_text": sum(1 for d in docs if d.get("tokens")),
        "extracted_token_count": sum(len(d.get("tokens", [])) for d in docs),
    }


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def token_key(s: str) -> str:
    return norm(s).lower()


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def contextual_layer_status() -> dict:
    files = {
        "documents": CONTEXT_DOCUMENTS,
        "token_occurrences": CONTEXT_TOKEN_OCCURRENCES,
        "token_index": CONTEXT_TOKEN_INDEX,
        "ideogram_occurrences": CONTEXT_IDEOGRAM_OCCURRENCES,
        "domain_model": CONTEXT_DOMAIN_MODEL,
    }
    status = {
        "available": all(path.exists() for key, path in files.items() if key != "domain_model"),
        "files": {key: {"path": str(path), "exists": path.exists()} for key, path in files.items()},
        "source_status": "DAMOS_NOT_YET_VERIFIED",
        "source_system": "LiBER fallback contextual layer",
    }
    if CONTEXT_DOCUMENTS.exists():
        docs = load_json(CONTEXT_DOCUMENTS, [])
        status["document_contexts"] = len(docs)
    if CONTEXT_TOKEN_INDEX.exists():
        index = load_json(CONTEXT_TOKEN_INDEX, {})
        status["token_context_forms"] = len(index)
    if CONTEXT_TOKEN_OCCURRENCES.exists():
        status["token_occurrences"] = sum(1 for _ in iter_jsonl(CONTEXT_TOKEN_OCCURRENCES))
    if CONTEXT_IDEOGRAM_OCCURRENCES.exists():
        status["ideogram_occurrences"] = sum(1 for _ in iter_jsonl(CONTEXT_IDEOGRAM_OCCURRENCES))
    if CONTEXT_DOMAIN_MODEL.exists():
        status["domain_model"] = load_json(CONTEXT_DOMAIN_MODEL, {})
    return status


def token_match(token: str, query: str) -> bool:
    q = query.lower()
    t = token.lower()
    return q == t or q in t


def cmd_status(_: argparse.Namespace) -> None:
    root = corpus_dir()
    manifest = load_manifest()
    docs = list(load_docs())
    site_counts = Counter(d.get("site") or "" for d in docs)
    series_counts = Counter(d.get("series") or "" for d in docs)
    payload = {
        "corpus_dir": str(root),
        "contextual_layer": contextual_layer_status(),
        "manifest": manifest,
        "observed_document_records": len(docs),
        "observed_documents_with_text": sum(1 for d in docs if d.get("tokens")),
        "observed_token_count": sum(len(d.get("tokens", [])) for d in docs),
        "top_sites": site_counts.most_common(20),
        "top_series": series_counts.most_common(20),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_source_status(_: argparse.Namespace) -> None:
    status = contextual_layer_status()
    source_counts: Counter[str] = Counter()
    if CONTEXT_TOKEN_OCCURRENCES.exists():
        for row in iter_jsonl(CONTEXT_TOKEN_OCCURRENCES):
            source_counts[row.get("source_status") or "UNKNOWN"] += 1
    status["token_occurrence_source_status_counts"] = dict(source_counts)
    print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_search(args: argparse.Namespace) -> None:
    rows = []
    for d in load_docs():
        tokens = d.get("tokens") or []
        text = d.get("transliteration") or " ".join(tokens)
        if any(token_match(t, args.query) for t in tokens) or args.query.lower() in text.lower():
            rows.append({
                "id": d.get("id"),
                "document": d.get("document"),
                "site": d.get("site"),
                "series": d.get("series"),
                "source_url": d.get("source_url"),
                "tokens": tokens[: args.context_tokens],
                "transliteration": text[: args.max_chars],
            })
            if len(rows) >= args.limit:
                break
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_document(args: argparse.Namespace) -> None:
    wanted = str(args.document).lower()
    for d in load_json(CONTEXT_DOCUMENTS, []):
        identifiers = {
            str(d.get("source_record_id", "")).lower(),
            str(d.get("document_id", "")).lower(),
            str(d.get("tablet_number", "")).lower(),
        }
        if wanted in identifiers:
            print(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True))
            return
    for d in load_docs():
        if str(d.get("id")) == wanted or str(d.get("document", "")).lower() == wanted:
            print(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True))
            return
    raise SystemExit(f"Document not found: {args.document}")


def cmd_ideogram(args: argparse.Namespace) -> None:
    query = args.query.upper()
    if getattr(args, "contexts", False) and CONTEXT_IDEOGRAM_OCCURRENCES.exists():
        rows = []
        for row in iter_jsonl(CONTEXT_IDEOGRAM_OCCURRENCES):
            raw = str(row.get("token_raw") or "")
            normalized = str(row.get("token_normalized") or "")
            if query in raw.upper() or query in normalized.upper():
                rows.append(row)
                if len(rows) >= args.limit:
                    break
        print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
        return
    rows = []
    for d in load_docs():
        tokens = d.get("tokens") or []
        hits = [i for i, tok in enumerate(tokens) if query in tok.upper()]
        for idx in hits:
            left = tokens[max(0, idx - args.window):idx]
            right = tokens[idx + 1:idx + 1 + args.window]
            rows.append({
                "id": d.get("id"),
                "document": d.get("document"),
                "site": d.get("site"),
                "series": d.get("series"),
                "hit": tokens[idx],
                "left": left,
                "right": right,
                "source_url": d.get("source_url"),
            })
            if len(rows) >= args.limit:
                print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
                return
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_tokens(args: argparse.Namespace) -> None:
    counter: Counter[str] = Counter()
    doc_counter: Counter[str] = Counter()
    for d in load_docs():
        seen = set()
        for tok in d.get("tokens") or []:
            counter[tok] += 1
            seen.add(tok)
        for tok in seen:
            doc_counter[tok] += 1
    rows = [
        {"token": tok, "count": count, "documents": doc_counter[tok]}
        for tok, count in counter.most_common(args.limit)
    ]
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_token(args: argparse.Namespace) -> None:
    query = token_key(args.query)
    index = load_json(CONTEXT_TOKEN_INDEX, {})
    if not index:
        # Fallback to old corpus search if the contextual layer is not installed.
        args.query = query
        args.context_tokens = 80
        args.max_chars = 500
        cmd_search(args)
        return

    exact_keys = [query] if query in index else []
    related_keys = []
    if args.related or not exact_keys:
        related_keys = []
        for key in index:
            related_key = token_key(key)
            if not query or not related_key:
                continue
            if query in related_key:
                related_keys.append(key)
        related_keys = sorted(
            set(related_keys) - set(exact_keys),
            key=lambda k: index[k].get("occurrence_count", 0),
            reverse=True,
        )[: args.limit]

    selected = exact_keys + related_keys
    summary = {
        "query": args.query,
        "contextual_layer_available": True,
        "source_status": "DAMOS_NOT_YET_VERIFIED",
        "exact_matches": {key: index[key] for key in exact_keys},
        "related_matches": {key: index[key] for key in related_keys},
        "occurrences": [],
    }
    if args.contexts and selected:
        selected_set = set(selected)
        for row in iter_jsonl(CONTEXT_TOKEN_OCCURRENCES):
            if token_key(row.get("token_normalized") or row.get("token_raw") or "") in selected_set:
                summary["occurrences"].append(row)
                if len(summary["occurrences"]) >= args.limit:
                    break
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_domain(args: argparse.Namespace) -> None:
    query = token_key(args.domain).replace("-", "_")
    domain_model = load_json(CONTEXT_DOMAIN_MODEL, {})
    rows = []
    token_counts: Counter[str] = Counter()
    ideogram_counts: Counter[str] = Counter()
    for row in iter_jsonl(CONTEXT_TOKEN_OCCURRENCES):
        if token_key(row.get("administrative_domain", "")).replace("-", "_") == query:
            tok = row.get("token_normalized") or row.get("token_raw") or ""
            token_counts[tok] += 1
            if row.get("token_type") == "ideogram":
                ideogram_counts[tok] += 1
            if len(rows) < args.limit:
                rows.append(row)
    payload = {
        "domain": args.domain,
        "source_status": "DAMOS_NOT_YET_VERIFIED",
        "domain_model": domain_model,
        "occurrence_count": sum(token_counts.values()),
        "top_tokens": token_counts.most_common(50),
        "top_ideograms": ideogram_counts.most_common(50),
        "sample_occurrences": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show corpus manifest and counts").set_defaults(func=cmd_status)
    sub.add_parser("source-status", help="Show contextual layer source and install status").set_defaults(func=cmd_source_status)

    p = sub.add_parser("search", help="Search tokens/transliteration text")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--context-tokens", type=int, default=80)
    p.add_argument("--max-chars", type=int, default=500)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("document", help="Show one document by LiBER id, contextual source id, or document label")
    p.add_argument("document")
    p.add_argument("--json", action="store_true", help="Accepted for compatibility; output is always JSON")
    p.set_defaults(func=cmd_document)

    p = sub.add_parser("ideogram", help="Search token windows around an ideogram/logogram string")
    p.add_argument("query")
    p.add_argument("--window", type=int, default=5)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--contexts", action="store_true", help="Use installed contextual ideogram occurrence layer")
    p.set_defaults(func=cmd_ideogram)

    p = sub.add_parser("token", help="Query installed contextual token occurrence layer")
    p.add_argument("query")
    p.add_argument("--contexts", action="store_true", help="Return occurrence rows, not just index summaries")
    p.add_argument("--related", action="store_true", help="Include normalized forms containing or contained by the query")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_token)

    p = sub.add_parser("domain", help="Summarize contextual occurrences by administrative domain")
    p.add_argument("domain")
    p.add_argument("--json", action="store_true", help="Accepted for compatibility; output is always JSON")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_domain)

    p = sub.add_parser("tokens", help="List most common tokens")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_tokens)

    args = parser.parse_args()
    try:
        args.func(args)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
