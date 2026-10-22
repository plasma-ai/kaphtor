#!/usr/bin/env python3
"""Consult one DEAPS search page or one specified textual-object record.

The client mirrors DEAPS's public GET form. It requires a substantive filter,
requests only the selected page, never follows pagination, never requests
images, and caches only the parsed response for private scholarly use.
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_portal_common import (
    cache_path,
    clean,
    load_cache,
    now,
    request_bytes,
    save_cache,
)

BASE = "https://deaps.osu.edu"
SEARCH_URL = f"{BASE}/text_objects"
ABOUT_URL = f"{BASE}/about"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE as USER_CACHE

CACHE = USER_CACHE / "deaps"
RATE_STATE = CACHE / ".last-live-request"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5

FIELDS = {
    "name": "name",
    "number": "legacy_id",
    "title": "title",
    "keyword": "keywords",
    "text": "text_string",
    "translation": "translation_string",
    "collection": "collection",
    "language": "language",
    "script": "script",
}

RIGHTS_NOTE = (
    "Case-by-case consultation of the public DEAPS interface. No corpus-data "
    "license or supported bulk export has been verified; do not redistribute "
    "the cache as a corpus."
)


def parse_total(source: str) -> int:
    patterns = (
        r"Displaying\s*<b>all\s+([\d,]+)</b>\s+objects",
        r"Displaying objects\s*<b>.*?</b>\s+of\s+<b>([\d,]+)</b>\s+in total",
    )
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.DOTALL)
        if match:
            return int(match.group(1).replace(",", ""))
    if "No objects found" in source or "search returned no results" in source:
        return 0
    raise RuntimeError("DEAPS result page changed: result-count marker not found")


def parse_search_results(source: str, page: int) -> dict[str, Any]:
    total = parse_total(source)
    cards = re.findall(
        r"<div class='card mb-3' data-map-value='(\d+)'>(.*?)"
        r"(?=<div class='card mb-3' data-map-value=|"
        r"<div class='row'>\s*<div class='col' id='paging'>)",
        source,
        flags=re.DOTALL,
    )
    records: list[dict[str, Any]] = []
    for object_id, fragment in cards:
        name_match = re.search(
            rf'href="/text_objects/{object_id}">(.*?)</a>', fragment, flags=re.DOTALL
        )
        title_match = re.search(
            r"<div class='pb-2 fw-bold'>(.*?)</div>", fragment, flags=re.DOTALL
        )
        text_match = re.search(
            r"<span class=\"unicode\"[^>]*>(.*?)</span>", fragment, flags=re.DOTALL
        )
        records.append(
            {
                "object_id": int(object_id),
                "name": clean(name_match.group(1)) if name_match else "",
                "title": clean(title_match.group(1)) if title_match else "",
                "text_excerpt": clean(text_match.group(1)) if text_match else "",
                "record_url": f"{BASE}/text_objects/{object_id}",
            }
        )
    if total and not records:
        raise RuntimeError(
            "DEAPS reported matches but no result cards were parsed; the page shape may have changed"
        )
    pages = [int(value) for value in re.findall(r"[?&]page=(\d+)", source)]
    return {
        "total_objects": total,
        "shown_on_page": len(records),
        "page": page,
        "available_pages_reported": max(pages) if pages else (1 if records else 0),
        "pagination_followed": False,
        "records": records,
    }


def parse_record(source: str, object_id: int) -> dict[str, Any]:
    title_match = re.search(
        r"<h1 class='d-inline-block'>(.*?)</h1>", source, flags=re.DOTALL
    )
    if not title_match:
        raise RuntimeError("DEAPS record page changed or the object is unavailable")
    subtitle_match = re.search(r"<div class='fs 6'>(.*?)</div>", source, flags=re.DOTALL)
    metadata_match = re.search(
        r"<h2 id='metadata'>Metadata</h2>.*?<dl class='row'>(.*?)</dl>",
        source,
        flags=re.DOTALL,
    )
    metadata: dict[str, str] = {}
    if metadata_match:
        for label, value in re.findall(
            r"<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>",
            metadata_match.group(1),
            flags=re.DOTALL,
        ):
            metadata[clean(label)] = clean(value)

    text_region = re.search(
        r"<div aria-label='Text Editions'.*?id='text_grid'.*?>(.*?)"
        r"<div aria-label='Word Information'",
        source,
        flags=re.DOTALL,
    )
    text_blocks: list[dict[str, str]] = []
    if text_region:
        for attrs, fragment in re.findall(
            r"<div class='grid-text[^']*'([^>]*)>(.*?)</div>",
            text_region.group(1),
            flags=re.DOTALL,
        ):
            lang_match = re.search(r"\blang='([^']+)'", attrs)
            direction_match = re.search(r"\bdir='([^']+)'", attrs)
            tokens = re.findall(
                r"<button[^>]*class=\"unicode[^\"]*\"[^>]*>(.*?)</button>",
                fragment,
                flags=re.DOTALL,
            )
            text = " ".join(clean(token) for token in tokens) if tokens else clean(fragment)
            if text:
                text_blocks.append(
                    {
                        "language": lang_match.group(1) if lang_match else "",
                        "direction": direction_match.group(1) if direction_match else "",
                        "text": text,
                    }
                )

    citation_match = re.search(
        r"<span data-text-target='citation'>(.*?)</span>", source, flags=re.DOTALL
    )
    return {
        "object_id": object_id,
        "name": clean(title_match.group(1)),
        "title": clean(subtitle_match.group(1)) if subtitle_match else "",
        "metadata": metadata,
        "text_blocks": text_blocks,
        "citation": (
            html_module.unescape(clean(citation_match.group(1))) if citation_match else ""
        ),
        "record_url": f"{BASE}/text_objects/{object_id}",
    }


def wrapper(mode: str, query: dict[str, Any], url: str, response: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "DEAPS",
        "mode": mode,
        "fetched_at": now(),
        "query": query,
        "request_url": url,
        "source_request_count": 1,
        "network_request_count": 1,
        "about_url": ABOUT_URL,
        "rights_note": RIGHTS_NOTE,
        "scope_note": "One public search page or one specified record; pagination and media were not followed.",
        "cache_hit": False,
        "response": response,
    }


def run_query(mode: str, parameters: dict[str, Any], refresh: bool, delay: float) -> dict[str, Any]:
    cached = cache_path(CACHE, mode, parameters)
    prior = load_cache(cached, refresh)
    if prior is not None:
        return prior
    if mode == "record":
        object_id = int(parameters["object_id"])
        url = f"{BASE}/text_objects/{object_id}"
        source = request_bytes(
            "DEAPS", url, rate_state=RATE_STATE, delay=delay
        ).decode("utf-8", "replace")
        result = wrapper(mode, parameters, url, parse_record(source, object_id))
    else:
        pairs: list[tuple[str, str]] = []
        for key, value in parameters.items():
            if key in {"page", "per_page"}:
                continue
            if isinstance(value, list):
                pairs.extend((f"search[{key}][]", item) for item in value)
            elif value not in (None, ""):
                pairs.append((f"search[{key}]", str(value)))
        pairs.extend([("page", str(parameters["page"])), ("per_page", str(parameters["per_page"]))])
        url = f"{SEARCH_URL}?{urllib.parse.urlencode(pairs, doseq=True)}"
        source = request_bytes(
            "DEAPS", url, rate_state=RATE_STATE, delay=delay
        ).decode("utf-8", "replace")
        result = wrapper(
            mode, parameters, url, parse_search_results(source, int(parameters["page"]))
        )
    save_cache(cached, result)
    return result


def print_human(result: dict[str, Any]) -> None:
    response = result["response"]
    cache = "hit" if result.get("cache_hit") else "new"
    if result["mode"] == "record":
        print(f"DEAPS {response['object_id']} · {response['name']}")
        print(response["record_url"])
        if response["title"]:
            print(response["title"])
        for label in ("Language", "Script", "Date (Composition)", "Collection"):
            if response["metadata"].get(label):
                print(f"{label}: {response['metadata'][label]}")
        print(f"Text blocks: {len(response['text_blocks'])}; cache {cache}; media requested: no")
        return
    print(
        f"DEAPS objects: {response['total_objects']}; shown on page "
        f"{response['page']}: {response['shown_on_page']}"
    )
    print(f"Query: {result['request_url']}; cache {cache}")
    print("Pagination followed: no")
    for row in response["records"]:
        heading = " · ".join(value for value in (row["name"], row["title"]) if value)
        print(f"\n{heading}\n  {row['record_url']}")
        if row["text_excerpt"]:
            print(f"  {row['text_excerpt']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="one substantive search term")
    parser.add_argument("--field", choices=tuple(FIELDS), default="name")
    parser.add_argument("--object", type=int, help="retrieve one public DEAPS textual object")
    parser.add_argument("--language", help="optional exact DEAPS language filter")
    parser.add_argument("--script", help="optional exact DEAPS script filter")
    parser.add_argument("--page", type=int, default=1, help="one explicitly selected page")
    parser.add_argument("--per-page", type=int, choices=(12, 24, 48), default=12)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.delay < MIN_DELAY:
        parser.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    if args.page < 1:
        parser.error("--page must be positive")
    if args.object is not None:
        if args.object < 1:
            parser.error("--object must be positive")
        if args.query or args.language or args.script:
            parser.error("--object cannot be combined with search filters")
        mode = "record"
        parameters = {"object_id": args.object}
    else:
        if not args.query or not args.query.strip():
            parser.error("a substantive query is required; unfiltered browsing is disabled")
        if len(args.query) > 300:
            parser.error("query is unexpectedly long (maximum 300 characters)")
        mode = "search"
        parameters = {
            FIELDS[args.field]: args.query.strip(),
            "language": args.language or "",
            "script": args.script or "",
            "page": args.page,
            "per_page": args.per_page,
        }
    try:
        result = run_query(mode, parameters, args.refresh, args.delay)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
