#!/usr/bin/env python3
"""Consult one public Elephantine query, object, or text page.

Quick search is the site's object-catalogue search, not a full-text concordance.
Each invocation performs at most one live request, never follows result pages,
never downloads images, and exposes but does not automatically fetch TEI links.
"""

from __future__ import annotations

import argparse
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

BASE = "https://elephantine.smb.museum"
SEARCH_URL = f"{BASE}/objects/index.php"
LEGAL_URL = f"{BASE}/project/legal_notice.html"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE as USER_CACHE

CACHE = USER_CACHE / "elephantine"
RATE_STATE = CACHE / ".last-live-request"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5

RIGHTS_NOTE = (
    "Object-level dataset licenses and media rights vary. Preserve the license "
    "and citation shown on the consulted record; this client does not fetch media "
    "or turn record pages into a collection dump."
)


def parse_search_results(source: str) -> dict[str, Any]:
    count_match = re.search(
        r">([\d,]+) Results of ([\d,]+) Data Sets<", source, flags=re.DOTALL
    )
    if not count_match:
        raise RuntimeError("Elephantine result page changed: result-count marker not found")
    total = int(count_match.group(1).replace(",", ""))
    catalogue_size = int(count_match.group(2).replace(",", ""))
    records: list[dict[str, Any]] = []
    for fragment in re.findall(r"<tr>(.*?)</tr>", source, flags=re.DOTALL):
        object_match = re.search(
            r'href="object\.php\?o=(\d+)"[^>]*>(.*?)</a>', fragment, flags=re.DOTALL
        )
        if not object_match:
            continue
        object_id = int(object_match.group(1))
        text_match = re.search(r"\.\./texts/view\.php\?t=(\d+)", fragment)
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", fragment, flags=re.DOTALL)
        records.append(
            {
                "object_id": object_id,
                "name": clean(object_match.group(2)),
                "title": clean(cells[2]) if len(cells) > 2 else "",
                "summary": clean(cells[3]) if len(cells) > 3 else "",
                "object_url": f"{BASE}/objects/object.php?o={object_id}",
                "text_id": int(text_match.group(1)) if text_match else None,
                "text_url": (
                    f"{BASE}/texts/view.php?t={text_match.group(1)}" if text_match else ""
                ),
            }
        )
    if total and not records:
        raise RuntimeError(
            "Elephantine reported matches but no result rows were parsed; the page shape may have changed"
        )
    return {
        "total_results": total,
        "catalogue_size": catalogue_size,
        "shown_on_page": len(records),
        "pagination_followed": False,
        "records": records,
    }


def table_fields(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for label, value in re.findall(
        r"<td\b[^>]*class=\"zelle\"[^>]*>(.*?)</td>\s*"
        r"<td\b[^>]*class=\"zelle\"[^>]*>(.*?)</td>",
        source,
        flags=re.DOTALL,
    ):
        key = clean(label)
        if key and key not in fields:
            fields[key] = clean(value)
    return fields


def exact_table_field(source: str, label: str) -> str:
    match = re.search(
        rf"<td\b[^>]*>\s*{re.escape(label)}\s*</td>\s*<td\b[^>]*>(.*?)</td>",
        source,
        flags=re.DOTALL,
    )
    return clean(match.group(1)) if match else ""


def parse_object(source: str, object_id: int) -> dict[str, Any]:
    title_match = re.search(r"<h1>(?!&nbsp;)(.*?)</h1>", source, flags=re.DOTALL)
    if not title_match:
        raise RuntimeError("Elephantine object page changed or the object is unavailable")
    tei_match = re.search(r"TEI-XML-File:\s*(https?://[^<\s]+)", source)
    fields = table_fields(source)
    return {
        "object_id": object_id,
        "name": clean(title_match.group(1)),
        "metadata": fields,
        "dataset_license": fields.get("Dataset License", ""),
        "dataset_citation": fields.get("Data set citation", ""),
        "tei_url": tei_match.group(1) if tei_match else "",
        "object_url": f"{BASE}/objects/object.php?o={object_id}",
    }


def parse_text(source: str, text_id: int) -> dict[str, Any]:
    name_match = re.search(
        r"<td[^>]*><strong>(.*?)</strong>.*?More information about the Object",
        source,
        flags=re.DOTALL,
    )
    if not name_match:
        raise RuntimeError("Elephantine text page changed or the text is unavailable")
    fields = table_fields(source)
    publication_number = exact_table_field(source, "Publication No.")
    modern_title = exact_table_field(source, "Modern Title")
    summary = exact_table_field(source, "Summary")
    tei_match = re.search(r"TEI-XML-File</td>\s*<td[^>]*>(https?://[^<\s]+)", source)
    blocks: list[dict[str, str]] = []
    for language, fragment in re.findall(
        r'<ab xml:lang="([^"]+)">(.*?)</ab>', source, flags=re.DOTALL
    ):
        text = clean(fragment, preserve_lines=True)
        if text:
            blocks.append({"language": language, "text": text})
    entities: list[dict[str, str]] = []
    seen_entities: set[tuple[str, str, str]] = set()
    for kind, attrs, fragment in re.findall(
        r"<(persName|placeName)\b([^>]*)>(.*?)</\1>", source, flags=re.DOTALL
    ):
        ref_match = re.search(r'\bref="([^"]+)"', attrs)
        row = {
            "type": "person_or_deity" if kind == "persName" else "place",
            "value": clean(fragment),
            "source_ref": ref_match.group(1) if ref_match else "",
        }
        identity = (row["type"], row["value"], row["source_ref"])
        if row["value"] and identity not in seen_entities:
            seen_entities.add(identity)
            entities.append(row)
    return {
        "text_id": text_id,
        "name": clean(name_match.group(1)),
        "publication_number": publication_number or fields.get("Publication No.", ""),
        "modern_title": modern_title or fields.get("Modern Title", ""),
        "summary": summary or fields.get("Summary", ""),
        "text_blocks": blocks,
        "named_entities": entities,
        "tei_url": tei_match.group(1) if tei_match else "",
        "text_url": f"{BASE}/texts/view.php?t={text_id}",
        "object_url": f"{BASE}/objects/object.php?o={text_id}",
    }


def base_wrapper(mode: str, query: dict[str, Any], url: str, response: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "Texts & Scripts from Elephantine",
        "mode": mode,
        "fetched_at": now(),
        "query": query,
        "request_url": url,
        "source_request_count": 1,
        "network_request_count": 1,
        "legal_url": LEGAL_URL,
        "rights_note": RIGHTS_NOTE,
        "scope_note": (
            "One object-catalogue query, object page, or text page only; no "
            "pagination, linked TEI, or media were fetched."
        ),
        "cache_hit": False,
        "response": response,
    }


def run_query(mode: str, parameters: dict[str, Any], refresh: bool, delay: float) -> dict[str, Any]:
    cached = cache_path(CACHE, mode, parameters)
    prior = load_cache(cached, refresh)
    if prior is not None:
        return prior
    if mode == "search":
        url = SEARCH_URL
        body = urllib.parse.urlencode({"searchtext": parameters["query"]}).encode("utf-8")
        source = request_bytes(
            "Elephantine", url, rate_state=RATE_STATE, delay=delay, data=body
        ).decode("utf-8", "replace")
        parsed = parse_search_results(source)
    elif mode == "object":
        object_id = int(parameters["object_id"])
        url = f"{BASE}/objects/object.php?o={object_id}"
        source = request_bytes(
            "Elephantine", url, rate_state=RATE_STATE, delay=delay
        ).decode("utf-8", "replace")
        parsed = parse_object(source, object_id)
    else:
        text_id = int(parameters["text_id"])
        url = f"{BASE}/texts/view.php?t={text_id}"
        source = request_bytes(
            "Elephantine", url, rate_state=RATE_STATE, delay=delay
        ).decode("utf-8", "replace")
        parsed = parse_text(source, text_id)
    result = base_wrapper(mode, parameters, url, parsed)
    save_cache(cached, result)
    return result


def print_human(result: dict[str, Any]) -> None:
    response = result["response"]
    cache = "hit" if result.get("cache_hit") else "new"
    if result["mode"] == "search":
        print(
            f"Elephantine objects: {response['total_results']}; "
            f"shown: {response['shown_on_page']}"
        )
        print("Pagination followed: no; linked TEI/media fetched: no")
        for row in response["records"]:
            print(f"\n{row['name']}\n  {row['object_url']}")
            if row["title"]:
                print(f"  {row['title']}")
        print(f"Cache: {cache}")
        return
    identifier = response.get("object_id", response.get("text_id"))
    print(f"Elephantine {identifier} · {response['name']}")
    print(response.get("object_url") or response.get("text_url"))
    if response.get("publication_number"):
        print(f"Publication: {response['publication_number']}")
    metadata = response.get("metadata", {})
    for label in ("Language, Primary", "Script, Primary", "Dataset License"):
        if metadata.get(label):
            print(f"{label}: {metadata[label]}")
    if response.get("tei_url"):
        print(f"TEI (not fetched): {response['tei_url']}")
    print(f"Cache: {cache}; media requested: no")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="one object-catalogue search string")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--object", type=int, help="retrieve one public object record")
    mode.add_argument("--text", type=int, help="retrieve one public text/edition page")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.delay < MIN_DELAY:
        parser.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    if args.object is not None or args.text is not None:
        if args.query:
            parser.error("record lookup cannot be combined with a search term")
        identifier = args.object if args.object is not None else args.text
        if identifier is None or identifier < 1:
            parser.error("record identifier must be positive")
        mode = "object" if args.object is not None else "text"
        parameters = {f"{mode}_id": identifier}
    else:
        if not args.query or not args.query.strip():
            parser.error("a substantive query is required; unfiltered browsing is disabled")
        if len(args.query) > 300:
            parser.error("query is unexpectedly long (maximum 300 characters)")
        mode = "search"
        parameters = {"query": args.query.strip()}
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
