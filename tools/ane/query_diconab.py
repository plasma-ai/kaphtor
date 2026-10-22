#!/usr/bin/env python3
"""Consult one public DiCoNab query page or one inscription record.

This is deliberately a case-by-case research client, not a corpus harvester. A
search invocation initializes DiCoNab's public form session, submits one
substantive filter, and retrieves only the explicitly requested result page. It
never follows pagination or downloads images. Identical requests are cached.

Examples:
    python3 tools/ane/query_diconab.py mlk
    python3 tools/ane/query_diconab.py mlk --field root --match exact
    python3 tools/ane/query_diconab.py ml --match starts --page 2
    python3 tools/ane/query_diconab.py mlk --suggest
    python3 tools/ane/query_diconab.py --inscription 3287
    python3 tools/ane/query_diconab.py mlk --json
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import html as html_module
import http.cookiejar
import json
import os
import re
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE = "https://diconab.huma-num.fr"
SEARCH_URL = f"{BASE}/words/attestations"
SUGGEST_URL = f"{BASE}/indexed-search/words/ajax"
TERMS_URL = f"{BASE}/info/terms"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE as USER_CACHE

CACHE = USER_CACHE / "diconab"
USER_AGENT = "kaphtor/1.0 (case-by-case scholarly consultation)"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5
RATE_LIMIT_STATE = CACHE / ".last-live-request"

FIELDS = {
    "word": "valueNorm",
    "root": "wordRoot",
    "category": "tag",
    "commentary": "wordComment",
    "site": "inscriptionSite",
    "language": "inscriptionTextLanguage",
    "script": "inscriptionScript",
    "editor": "inscriptionEditor",
    "siglum": "inscriptionSiglum",
    "siglum-letter": "inscriptionSiglumLetter",
    "siglum-number": "inscriptionSiglumNumber",
    "source": "inscriptionSource",
    "date": "inscriptionDate",
    "reference": "readingReference",
    "reading-category": "readingCategory",
    "translation-category": "readingTranslationCategory",
}

MATCHES = {
    "starts": "1",
    "ends": "2",
    "contains": "3",
    "exact": "4",
}

RECORD_METADATA_FIELDS = {
    "Language of text",
    "Script",
    "Type",
    "In situ/not in situ",
    "Type of support",
    "Material of support",
    "Writing technique",
    "Associated motif(s)",
    "Absolute date",
}

RIGHTS_NOTE = (
    "Case-by-case scholarly consultation only. DiCoNab permits academic use "
    "and partial reproduction with proper citation; reproduction and "
    "distribution rights remain reserved. See the source terms."
)


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def opener() -> urllib.request.OpenerDirector:
    cookies = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies),
        urllib.request.HTTPSHandler(context=ssl_context()),
    )


def request_bytes(
    client: urllib.request.OpenerDirector,
    url: str,
    *,
    data: bytes | None = None,
    ajax: bool = False,
    accept: str = "text/html,application/xhtml+xml",
    delay: float = DEFAULT_DELAY,
) -> bytes:
    throttle_live_request(delay)
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if ajax:
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with client.open(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"DiCoNab returned HTTP {exc.code}: {detail[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"DiCoNab request failed: {exc}") from exc


def throttle_live_request(delay: float) -> None:
    """Serialize live calls and keep their start times at least ``delay`` apart."""
    CACHE.mkdir(parents=True, exist_ok=True)
    with RATE_LIMIT_STATE.open("a+", encoding="utf-8") as state:
        fcntl.flock(state.fileno(), fcntl.LOCK_EX)
        state.seek(0)
        raw = state.read().strip()
        previous = float(raw) if raw else 0.0
        wait = max(0.0, delay - (time.time() - previous))
        if wait:
            time.sleep(wait)
        started = time.time()
        state.seek(0)
        state.truncate()
        state.write(f"{started:.6f}\n")
        state.flush()
        fcntl.flock(state.fileno(), fcntl.LOCK_UN)


def clean(fragment: str) -> str:
    fragment = html_module.unescape(fragment)
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = re.sub(r"\s+", " ", html_module.unescape(fragment)).strip()
    return re.sub(r"\s+([,;:.])", r"\1", fragment)


def cache_path(mode: str, parameters: dict[str, Any]) -> Path:
    fingerprint = hashlib.sha256(
        json.dumps([mode, parameters], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    return CACHE / f"{mode}-{fingerprint}.json"


def from_cache(path: Path, refresh: bool) -> dict[str, Any] | None:
    if refresh or not path.exists():
        return None
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    if "source_request_count" not in wrapper:
        wrapper["source_request_count"] = wrapper.get(
            "network_request_count", len(wrapper.get("request_urls") or [])
        )
    wrapper["network_request_count"] = 0
    wrapper["cache_hit"] = True
    return wrapper


def save_cache(path: Path, wrapper: dict[str, Any]) -> None:
    stored = {**wrapper, "cache_hit": False}
    atomic_write(
        path,
        (json.dumps(stored, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def base_wrapper(mode: str, request_urls: list[str]) -> dict[str, Any]:
    return {
        "source": "DiCoNab",
        "mode": mode,
        "fetched_at": now(),
        "request_urls": request_urls,
        "source_request_count": len(request_urls),
        "network_request_count": len(request_urls),
        "terms_url": TERMS_URL,
        "rights_note": RIGHTS_NOTE,
        "scope_note": (
            "One case-by-case query or record only; pagination was not followed "
            "automatically and media were not requested."
        ),
        "cache_hit": False,
    }


def parse_csrf(source: str) -> str:
    match = re.search(
        r'name="word_attestation_filter_form\[_token\]"\s+value="([^"]+)"',
        source,
    )
    if not match:
        raise RuntimeError("DiCoNab search form changed: CSRF token not found")
    if 'name="word_attestation_filter_form[fbEntityField]"' not in source:
        raise RuntimeError("DiCoNab search form changed: field selector not found")
    return html_module.unescape(match.group(1))


def parse_search_results(source: str, page: int) -> dict[str, Any]:
    total_match = re.search(
        r'<div class="my-4"><strong>([\d,]+)</strong>\s*word occurrences found',
        source,
    )
    if not total_match:
        raise RuntimeError(
            "DiCoNab result page changed or an interstitial was returned: "
            "result-count marker not found"
        )
    total = int(total_match.group(1).replace(",", ""))
    pages = {
        int(value)
        for value in re.findall(
            r'/words/attestations\?ag=\d+&amp;p=(\d+)', source
        )
    }
    rows: list[dict[str, Any]] = []
    for fragment in re.findall(
        r'<tr class="border border-start-0 border-end-0">(.*?)</tr>',
        source,
        flags=re.DOTALL,
    ):
        word_match = re.search(
            r'<span class="fs-5 fw-bold text-nowrap">(.*?)</span>',
            fragment,
            flags=re.DOTALL,
        )
        category_match = re.search(
            r'<span class="text-muted small">(.*?)</span>',
            fragment,
            flags=re.DOTALL,
        )
        inscription_match = re.search(r'href="/inscriptions/(\d+)"', fragment)
        siglum_match = re.search(
            r'<span class="fw-bold text-nowrap small">(.*?)</span>',
            fragment,
            flags=re.DOTALL,
        )
        position_match = re.search(
            r'title="word position \(from the beginning\):\s*(\d+)"', fragment
        )
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", fragment, flags=re.DOTALL)
        left = clean(cells[-2]) if len(cells) >= 2 else ""
        right = clean(cells[-1]) if cells else ""
        inscription_id = inscription_match.group(1) if inscription_match else ""
        if not word_match and not inscription_id:
            continue
        rows.append(
            {
                "form": clean(word_match.group(1)) if word_match else "",
                "category": clean(category_match.group(1)) if category_match else "",
                "inscription_id": inscription_id,
                "siglum": clean(siglum_match.group(1)) if siglum_match else "",
                "word_position": int(position_match.group(1)) if position_match else None,
                "left_context": left,
                "right_context": right,
                "record_url": f"{BASE}/inscriptions/{inscription_id}" if inscription_id else "",
            }
        )
    if total and not rows:
        raise RuntimeError(
            "DiCoNab reported matches but the result rows could not be parsed; "
            "the page shape may have changed"
        )
    if not total and rows:
        raise RuntimeError(
            "DiCoNab reported zero matches but result rows were present; "
            "the page shape may have changed"
        )
    return {
        "total_occurrences": total,
        "shown_on_page": len(rows),
        "page": page,
        "available_pages_reported": max(pages) if pages else (1 if rows else 0),
        "pagination_followed": False,
        "automatic_pagination_followed": False,
        "explicit_page_requested": page > 1,
        "occurrences": rows,
    }


def parse_record(source: str, inscription_id: int) -> dict[str, Any]:
    title_match = re.search(
        r'<h2 class="display-6 fw-bold[^>]*>.*?</i>\s*(.*?)\s*<nav',
        source,
        flags=re.DOTALL,
    )
    title = clean(title_match.group(1)) if title_match else ""
    if not title:
        raise RuntimeError("DiCoNab record page changed or record is unavailable")

    site_match = re.search(
        r'<a href="/sites/(\d+)"[^>]*>(.*?)</a>', source, flags=re.DOTALL
    )
    citation_match = re.search(
        r'data-copy-content="([^"]*DiCoNab[^"]*)"', source, flags=re.DOTALL
    )
    metadata: dict[str, str] = {}
    for label, value in re.findall(
        r'<div class="col fs-5 mb-1 [^"]*">\s*'
        r'<div class="fw-bold[^>]*>.*?<span[^>]*>(.*?)</span></div>\s*'
        r'<div[^>]*>(.*?)</div>',
        source,
        flags=re.DOTALL,
    ):
        key = clean(label)
        if key in RECORD_METADATA_FIELDS and key not in metadata:
            metadata[key] = clean(value)

    marker = source.find("Reading and translation</div>")
    reading_section = source[marker : marker + 12000] if marker >= 0 else ""
    transliteration_match = re.search(
        r'<div class="fst-italic">(.*?)</div>', reading_section, flags=re.DOTALL
    )
    arabic_match = re.search(
        r'<div class="arabic">(.*?)</div>', reading_section, flags=re.DOTALL
    )
    last_change = re.search(r"<strong>last change</strong>:\s*([^<]+)", source)
    created = re.search(r"<strong>created on</strong>:\s*([^<]+)", source)
    site_id = site_match.group(1) if site_match else ""
    return {
        "inscription_id": inscription_id,
        "siglum": title,
        "record_url": f"{BASE}/inscriptions/{inscription_id}",
        "site_id": site_id,
        "site": clean(site_match.group(2)) if site_match else "",
        "site_url": f"{BASE}/sites/{site_id}" if site_id else "",
        "metadata": metadata,
        "transliteration_display": (
            clean(transliteration_match.group(1)) if transliteration_match else ""
        ),
        "arabic_display": clean(arabic_match.group(1)) if arabic_match else "",
        "citation": clean(citation_match.group(1)) if citation_match else "",
        "last_change": clean(last_change.group(1)) if last_change else "",
        "created_on": clean(created.group(1)) if created else "",
    }


def suggest(
    query: str, field: str, refresh: bool, delay: float = DEFAULT_DELAY
) -> dict[str, Any]:
    parameters = {"query": query, "field": field}
    cached = cache_path("suggest", parameters)
    wrapper = from_cache(cached, refresh)
    if wrapper is not None:
        return wrapper
    query_string = urllib.parse.urlencode(
        {"term": query, "field": FIELDS[field]}
    )
    url = f"{SUGGEST_URL}?{query_string}"
    payload = json.loads(
        request_bytes(
            opener(), url, ajax=True, accept="application/json", delay=delay
        ).decode("utf-8")
    )
    seen: set[tuple[str, str]] = set()
    candidates = []
    for row in payload.get("results") or []:
        key = (str(row.get("id", "")), str(row.get("text", "")))
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"id": key[0], "text": key[1]})
    wrapper = base_wrapper("suggest", [url])
    wrapper.update(
        {
            "query": parameters,
            "response": {"candidate_count": len(candidates), "candidates": candidates},
        }
    )
    save_cache(cached, wrapper)
    return wrapper


def search(
    query: str,
    field: str,
    match: str,
    page: int,
    delay: float,
    refresh: bool,
) -> dict[str, Any]:
    parameters = {"query": query, "field": field, "match": match, "page": page}
    cached = cache_path("search", parameters)
    wrapper = from_cache(cached, refresh)
    if wrapper is not None:
        return wrapper

    client = opener()
    form_url = f"{SEARCH_URL}?ag=1&p=1&rq=1"
    form = request_bytes(client, form_url, delay=delay).decode("utf-8", "replace")
    token = parse_csrf(form)
    body = urllib.parse.urlencode(
        {
            "word_attestation_filter_form[fbEntityField]": FIELDS[field],
            "word_attestation_filter_form[fbTermSearch]": MATCHES[match],
            "word_attestation_filter_form[fbTerm]": query,
            "word_attestation_filter_form[kwicSize]": "10",
            "word_attestation_filter_form[_token]": token,
        }
    ).encode("utf-8")
    result = request_bytes(client, form_url, data=body, delay=delay).decode(
        "utf-8", "replace"
    )
    request_urls = [form_url, form_url]
    if page > 1:
        page_url = f"{SEARCH_URL}?ag=1&p={page}"
        result = request_bytes(client, page_url, delay=delay).decode("utf-8", "replace")
        request_urls.append(page_url)

    wrapper = base_wrapper("search", request_urls)
    wrapper.update(
        {
            "query": parameters,
            "response": parse_search_results(result, page),
        }
    )
    if page > 1:
        wrapper["scope_note"] = (
            "One case-by-case query; the required form submission returned page 1, "
            f"then explicit page {page} was requested. Pagination was not followed "
            "automatically and media were not requested."
        )
    save_cache(cached, wrapper)
    return wrapper


def record(
    inscription_id: int, refresh: bool, delay: float = DEFAULT_DELAY
) -> dict[str, Any]:
    parameters = {"inscription_id": inscription_id}
    cached = cache_path("record", parameters)
    wrapper = from_cache(cached, refresh)
    if wrapper is not None:
        return wrapper
    url = f"{BASE}/inscriptions/{inscription_id}"
    source = request_bytes(opener(), url, delay=delay).decode("utf-8", "replace")
    wrapper = base_wrapper("record", [url])
    wrapper.update(
        {
            "query": parameters,
            "response": parse_record(source, inscription_id),
        }
    )
    save_cache(cached, wrapper)
    return wrapper


def print_human(wrapper: dict[str, Any]) -> None:
    mode = wrapper["mode"]
    response = wrapper["response"]
    cache = "hit" if wrapper.get("cache_hit") else "new"
    if mode == "suggest":
        print(
            f"DiCoNab suggestions: {response['candidate_count']} "
            f"({wrapper['query']['field']}; cache {cache})"
        )
        for row in response["candidates"]:
            print(f"  {row['text']}\t[{row['id']}]")
        return
    if mode == "record":
        row = response
        print(f"DiCoNab {row['inscription_id']} · {row['siglum']}")
        print(row["record_url"])
        if row["site"]:
            print(f"Site: {row['site']}")
        for label in ("Language of text", "Script", "Type", "Absolute date"):
            if row["metadata"].get(label):
                print(f"{label}: {row['metadata'][label]}")
        if row["transliteration_display"]:
            print(f"Reading: {row['transliteration_display']}")
        if row["citation"]:
            print(f"Citation: {row['citation']}")
        print(f"Cache: {cache}; media requested: no")
        return

    query = wrapper["query"]
    print(
        f"DiCoNab occurrences: {response['total_occurrences']}; "
        f"shown on page {response['page']}: {response['shown_on_page']}"
    )
    print(
        f"Query: {query['field']} {query['match']} {query['query']!r}; "
        f"cache {cache}"
    )
    print("Pagination followed automatically: no")
    if not response["occurrences"]:
        print("(no results)")
        return
    for row in response["occurrences"]:
        heading = " · ".join(
            value for value in (row["siglum"], row["form"], row["category"]) if value
        )
        print(f"\n{heading}")
        print(f"  {row['record_url']}")
        context = " ".join(
            value for value in (row["left_context"], row["right_context"]) if value
        )
        if context:
            print(f"  {context}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="one substantive search term")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--suggest",
        action="store_true",
        help="make one autocomplete call instead of an attestation search",
    )
    mode.add_argument(
        "--inscription",
        type=int,
        help="retrieve one public inscription record by numeric DiCoNab ID",
    )
    parser.add_argument("--field", choices=tuple(FIELDS), default="word")
    parser.add_argument("--match", choices=tuple(MATCHES), default="exact")
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="one explicitly selected result page; never auto-paginates (default 1)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=f"minimum seconds between all live requests; floor {MIN_DELAY:g}",
    )
    parser.add_argument("--json", action="store_true", help="print the audit wrapper as JSON")
    parser.add_argument("--refresh", action="store_true", help="replace only this exact cache entry")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.page < 1:
        parser.error("--page must be positive")
    if args.delay < MIN_DELAY:
        parser.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    if args.inscription is not None:
        if args.query:
            parser.error("--inscription cannot be combined with a search term")
        if args.inscription < 1:
            parser.error("--inscription must be positive")
    elif not args.query or not args.query.strip():
        parser.error("a substantive query is required; unfiltered browsing is disabled")
    elif len(args.query) > 200:
        parser.error("query is unexpectedly long (maximum 200 characters)")

    try:
        if args.inscription is not None:
            wrapper = record(args.inscription, args.refresh, args.delay)
        elif args.suggest:
            wrapper = suggest(args.query.strip(), args.field, args.refresh, args.delay)
        else:
            wrapper = search(
                args.query.strip(),
                args.field,
                args.match,
                args.page,
                args.delay,
                args.refresh,
            )
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        json.dump(wrapper, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_human(wrapper)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
