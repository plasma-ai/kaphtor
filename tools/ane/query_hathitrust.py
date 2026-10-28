#!/usr/bin/env python3
"""Find the pages of a HathiTrust volume that hold a word.

Search-only (in-copyright) volumes cannot be read, and HathiTrust's own
search-inside sits behind a challenge page. This client reads the volume's
HTRC Extracted Features file instead: every token on every scan page, with its
count (CC BY 4.0). It fetches at most one catalog record and one features
file per volume, caches the file, and searches it locally. A hit names a page
to read; it is not a quotation of the book.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_portal_common import (
    atomic_write,
    now,
    request_bytes,
)

CATALOG = "https://catalog.hathitrust.org/api/volumes/brief"
EF_BASE = "https://data.analytics.hathitrust.org/features-2020.03"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE as USER_CACHE

CACHE = USER_CACHE / "hathitrust-ef"
RATE_STATE = CACHE / ".last-live-request"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5
HTID_RE = re.compile(r"^[a-z0-9]+\.\S+$")

RIGHTS_NOTE = (
    "HTRC Extracted Features 2.0, CC BY 4.0: Jett et al. (2020), The HathiTrust "
    "Research Center Extracted Features Dataset (2.0), "
    "https://doi.org/10.13012/R2TE-C227. Token counts only; cite the book after "
    "reading the page itself."
)


def clean_volid(volid: str) -> str:
    """Pairtree clean form: ':' → '+', '/' → '=', '.' → ','."""
    return volid.replace(":", "+").replace("/", "=").replace(".", ",")


def ef_relative_path(htid: str) -> str:
    """HTRC's stubbytree layout: <lib>/<every third char of the clean id>/<file>."""
    libid, volid = htid.split(".", 1)
    clean = clean_volid(volid)
    return f"{libid}/{clean[::3]}/{libid}.{clean}.json.bz2"


def parse_catalog(payload: bytes) -> list[dict[str, str]]:
    data = json.loads(payload)
    return [
        {
            "htid": item.get("htid", ""),
            "rights": item.get("rightsCode", ""),
            "us_rights": item.get("usRightsString", ""),
            "holder": item.get("orig", ""),
            "enumeration": item.get("enumcron") or "",
        }
        for item in data.get("items", [])
    ]


def resolve_oclc(oclc: str, delay: float) -> list[dict[str, str]]:
    url = f"{CATALOG}/oclc/{oclc}.json"
    payload = request_bytes(
        "HathiTrust catalog", url, rate_state=RATE_STATE, delay=delay, accept="application/json"
    )
    return parse_catalog(payload)


def load_features(htid: str, ef_file: Path | None, refresh: bool, delay: float) -> tuple[dict[str, Any], dict[str, Any]]:
    if ef_file is not None:
        raw = ef_file.read_bytes()
        origin = {"path": str(ef_file), "url": None, "network_request_count": 0}
    else:
        cached = CACHE / Path(ef_relative_path(htid)).name
        url = f"{EF_BASE}/{ef_relative_path(htid)}"
        if cached.exists() and not refresh:
            raw = cached.read_bytes()
            origin = {"path": str(cached), "url": url, "network_request_count": 0}
        else:
            raw = request_bytes(
                "HTRC Extracted Features", url, rate_state=RATE_STATE, delay=delay,
                accept="application/octet-stream",
            )
            atomic_write(cached, raw)
            origin = {"path": str(cached), "url": url, "network_request_count": 1, "fetched_at": now()}
    origin["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        features = json.loads(bz2.decompress(raw))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"not an Extracted Features file: {exc}") from exc
    if features.get("htid") != htid:
        raise RuntimeError(f"features file is for {features.get('htid')!r}, not {htid!r}")
    return features, origin


def page_tokens(page: dict[str, Any]) -> dict[str, int]:
    """Token counts for a page's header, body and footer; POS tags summed."""
    counts: dict[str, int] = {}
    for section in ("header", "body", "footer"):
        part = page.get(section) or {}
        for token, by_pos in (part.get("tokenPosCount") or {}).items():
            counts[token] = counts.get(token, 0) + sum(by_pos.values())
    return counts


def search(features: dict[str, Any], pattern: re.Pattern[str], offset: int | None) -> list[dict[str, Any]]:
    hits = []
    for page in features["features"]["pages"]:
        tokens = {t: n for t, n in page_tokens(page).items() if pattern.search(t)}
        if tokens:
            seq = int(page["seq"])
            hits.append({
                "seq": seq,
                "printed_page": seq - offset if offset is not None else None,
                "tokens": dict(sorted(tokens.items())),
            })
    return hits


def volume_summary(features: dict[str, Any]) -> dict[str, Any]:
    meta = features.get("metadata", {})
    contributor = meta.get("contributor") or {}
    if isinstance(contributor, list):
        contributor = contributor[0] if contributor else {}
    return {
        "htid": features.get("htid"),
        "title": meta.get("title"),
        "contributor": contributor.get("name"),
        "pub_date": meta.get("pubDate"),
        "access_rights": meta.get("accessRights"),
        "page_count": features["features"].get("pageCount"),
        "catalog": f"https://hdl.handle.net/2027/{features.get('htid')}",
    }


def print_human(result: dict[str, Any]) -> None:
    vol = result["volume"]
    print(f"{vol['htid']} · {vol['contributor']}, {vol['title']} ({vol['pub_date']})")
    print(f"Rights: {vol['access_rights']} · {vol['page_count']} scan pages · {result['source']['path']}")
    offset = result["query"]["offset"]
    print(f"Pattern {result['query']['pattern']!r}: {len(result['hits'])} pages"
          + (f" (printed = scan - {offset})" if offset is not None else " (scan pages; give --offset for printed)"))
    for hit in result["hits"]:
        where = f"p. {hit['printed_page']}" if hit["printed_page"] is not None else ""
        tokens = ", ".join(f"{t}×{n}" if n > 1 else t for t, n in hit["tokens"].items())
        print(f"  scan {hit['seq']:>4}  {where:<8} {tokens}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("volume", help="HathiTrust volume id (mdp.39015008689583) or oclc:NUMBER")
    parser.add_argument("pattern", nargs="?", help="regular expression, matched case-insensitively against each token")
    parser.add_argument("--exact", action="store_true", help="match the whole token, not a part of it")
    parser.add_argument("--offset", type=int, help="printed page = scan page - OFFSET (calibrate on a cited page)")
    parser.add_argument("--ef-file", type=Path, help="read a features file already on disk; no request is made")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="fetch the features file again")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.delay < MIN_DELAY:
        parser.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    try:
        if args.volume.startswith("oclc:"):
            oclc = args.volume.removeprefix("oclc:")
            if not oclc.isdigit():
                parser.error("oclc: takes a number")
            items = resolve_oclc(oclc, args.delay)
            if len(items) != 1 or args.pattern is None:
                for item in items:
                    print(f"{item['htid']}\t{item['rights']}\t{item['us_rights']}\t{item['holder']}\t{item['enumeration']}")
                if not items:
                    print(f"no HathiTrust volume for OCLC {oclc}", file=sys.stderr)
                    return 1
                if len(items) > 1 and args.pattern is not None:
                    print("several volumes: pass one htid", file=sys.stderr)
                    return 2
                return 0
            htid = items[0]["htid"]
        else:
            htid = args.volume
            if not HTID_RE.fullmatch(htid):
                parser.error("volume must be an htid (lib.id) or oclc:NUMBER")
        if args.pattern is None:
            parser.error("a pattern is required; the client does not dump whole volumes")
        try:
            body = args.pattern if not args.exact else f"^(?:{args.pattern})$"
            pattern = re.compile(body, re.IGNORECASE)
        except re.error as exc:
            parser.error(f"bad pattern: {exc}")
        features, origin = load_features(htid, args.ef_file, args.refresh, args.delay)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    result = {
        "source": origin,
        "rights_note": RIGHTS_NOTE,
        "query": {"volume": args.volume, "pattern": args.pattern, "exact": args.exact, "offset": args.offset},
        "volume": volume_summary(features),
        "hits": search(features, pattern, args.offset),
    }
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
