#!/usr/bin/env python3
"""Query the Lexicon of Greek Personal Names (Oxford) — cached thin client.

LGPN's beta TEI-Publisher interface (search.lgpn.ox.ac.uk) accepts name
patterns in Greek or transliteration, case- and accent-insensitive, with
? (one char) and * (any) wildcards. No bulk dump is offered and none is
taken — this client is for on-demand onomastic checks, one pattern at a
time, cached under the user cache (CACHE/lgpn/), never in the repository.

Usage:
    uv run tools/linear_a/fetch_lgpn.py "alexandra"          # exact-ish pattern
    uv run tools/linear_a/fetch_lgpn.py "d?mo*" --raw        # wildcard, raw dump
    uv run tools/linear_a/fetch_lgpn.py "titan*" --no-cache
    uv run tools/linear_a/fetch_lgpn.py --probe              # endpoint health check

The beta service intermittently returns 504; results are cached forever
once obtained (LGPN data changes on publication timescales). Failures are
NEVER cached, and a failed query returns status LGPN_UNAVAILABLE with
per-endpoint diagnostics — a consumer must mark affected rows
LGPN_CHECK_PENDING, never treat unavailability as a pass.

Service state when this client was written: the main TEI-Publisher API (/api/search) returns
an eXist-db roaster 401 even after a successful guest login (auth.xql
misconfiguration upstream — the frontend's own pb-login fails the same way).
The Egypt sub-app API (/egypt/api/search) answers unauthenticated and is the
primary endpoint. COVERAGE CAVEAT: the Egypt sub-app searches the LGPN Egypt
volume only — a hit is positive evidence, but a miss is NOT a full-LGPN pass;
consumers must still mark non-Egypt coverage LGPN_CHECK_PENDING. LGPN-Ling
(lgpn-ling.huma-num.fr) is alive but its api/search returns a browse template
regardless of query, so it is excluded. www.lgpn.ox.ac.uk (Drupal) is up;
legacy clas-lgpn2.classics.ox.ac.uk refuses connections. Retry with --probe
before assuming the endpoint list is stale.

The Egypt API paginates at 10 result cards per response, so hit_count is a
first-page count, not a total — presence/absence is the reliable signal.
A 200 with an empty body is its zero-hit response and is cached as
hit_count 0, a genuine negative, distinct from LGPN_UNAVAILABLE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import CACHE

CACHE_DIR = CACHE / "lgpn"

BASE = "https://search.lgpn.ox.ac.uk"
# Candidate endpoints, tried in order. Egypt sub-app first (the only one that
# answered when this was written); the main API stays listed in case Oxford fixes
# its guest auth. HTML page shells (search.html, index.html) are deliberately
# excluded: they return 200 without results (pb-load fills them client-side),
# which this client would cache as a false success.
ENDPOINTS = [
    BASE + "/egypt/api/search?query={q}",
    BASE + "/api/search?query={q}",
    BASE + "/api/persons?name={q}",
]

UA = {"User-Agent": "kaphtor/1.0 (scholarly onomastic lookups)"}


def _fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001 — network layer, report and move on
        return 0, str(e)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def query(pattern: str, use_cache: bool = True) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(pattern.encode()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{key}.json"
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    q = urllib.parse.quote(pattern)
    diagnostics = []
    for template in ENDPOINTS:
        url = template.format(q=q)
        status, body = _fetch(url, timeout=20)
        if status != 200:
            diagnostics.append({"endpoint": url, "status": status or "connect/timeout",
                                "detail": (body or "")[:120]})
            continue
        if not body.strip():
            # 200 with empty body is the Egypt sub-app's zero-hit response —
            # a genuine negative result, not an outage.
            payload = {"pattern": pattern, "endpoint": url, "format": "html_text",
                       "hit_count": 0, "hits": [], "data": ""}
            if "/egypt/" in url:
                payload["coverage"] = ("LGPN Egypt volume only — a miss is not a "
                                       "full-LGPN pass; mark non-Egypt coverage "
                                       "LGPN_CHECK_PENDING")
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
            return payload
        if body.lstrip().startswith(("{", "[")):
            payload = {"pattern": pattern, "endpoint": url, "format": "json",
                       "data": json.loads(body)}
        else:
            # TEI-Publisher paper-cards: <div class="count">N</div> per match,
            # matched form highlighted as <a class="hi" ...>Name</a>.
            hits = re.findall(r'<a class="hi"[^>]*>([^<]+)</a>', body)
            payload = {"pattern": pattern, "endpoint": url, "format": "html_text",
                       "hit_count": len(re.findall(r'<div class="count">', body)),
                       "hits": sorted(set(hits)),
                       "data": _strip_html(body)[:20000]}
        if "/egypt/" in url:
            payload["coverage"] = ("LGPN Egypt volume only — a miss is not a "
                                   "full-LGPN pass; mark non-Egypt coverage "
                                   "LGPN_CHECK_PENDING")
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        return payload

    return {"pattern": pattern, "endpoint": None, "format": "error",
            "status": "LGPN_UNAVAILABLE",
            "data": "all endpoints failed — consumers must mark rows LGPN_CHECK_PENDING, not pass",
            "diagnostics": diagnostics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern", nargs="?", help="Name pattern (Greek or translit; ?/* wildcards)")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--raw", action="store_true", help="Dump full payload JSON")
    parser.add_argument("--probe", action="store_true", help="Check endpoint availability")
    args = parser.parse_args()

    if args.probe:
        for template in ENDPOINTS:
            url = template.format(q="alexandra")
            status, _ = _fetch(url, timeout=15)
            print(f"{status or 'ERR':>4}  {url}")
        return 0

    if not args.pattern:
        parser.error("pattern required (or --probe)")

    result = query(args.pattern, use_cache=not args.no_cache)
    if args.raw or result["format"] == "json":
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print(f"[{result['format']}] via {result['endpoint']}")
        print(result["data"][:4000] if isinstance(result["data"], str) else result["data"])
    return 0 if result["format"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
