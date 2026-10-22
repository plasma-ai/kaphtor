#!/usr/bin/env python3
"""Bounded, cached lookup client for the public iDAI.gazetteer API."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE

DEFAULT_CACHE = CACHE / "idai"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5
BASE = "https://gazetteer.dainst.org"
USER_AGENT = "kaphtor/1.0 (bounded scholarly lookup)"


def cache_path(cache: Path, query: str) -> Path:
    slug = "".join(ch.casefold() if ch.isalnum() else "-" for ch in query).strip("-")[:60]
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
    return cache / f"{slug or 'query'}-{digest}.json"


def request_json(url: str, retries: int = 4) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="+")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not 1 <= args.limit <= 100:
        ap.error("--limit must be between 1 and 100")
    if args.delay < MIN_DELAY:
        ap.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    args.cache.mkdir(parents=True, exist_ok=True)

    output = []
    for index, query in enumerate(args.query):
        target = cache_path(args.cache, query)
        url = BASE + "/search.json?" + urllib.parse.urlencode(
            {"q": query, "limit": args.limit, "noPolygons": "true", "pretty": "true"}
        )
        if target.exists() and not args.refresh:
            payload = json.loads(target.read_text(encoding="utf-8"))
        else:
            if index:
                time.sleep(args.delay)
            response = request_json(url)
            payload = {
                "query": query,
                "request_url": url,
                "retrieved_with": USER_AGENT,
                "response": response,
            }
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output.append(payload)

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for payload in output:
            response = payload.get("response", payload)
            print(f"{payload.get('query', '')}\t{response.get('total', 0)}")
            for row in response.get("result", [])[: args.limit]:
                print(f"  {row.get('gazId')}\t{(row.get('prefName') or {}).get('title')}\t{row.get('@id')}")


if __name__ == "__main__":
    main()
