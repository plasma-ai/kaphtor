#!/usr/bin/env python3
"""Retrieve and parse one public RSTI/OCHRE UUID response.

This is an exact-record client, not a crawler or full-text search service. It
performs one OCHRE request for the supplied UUID, parses that response only,
does not follow linked UUIDs, and caches the normalized result.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from query_portal_common import (
    cache_path,
    load_cache,
    now,
    request_bytes,
    save_cache,
)

BASE = "https://ochre.lib.uchicago.edu"
API = f"{BASE}/ochre"
SITE = f"{BASE}/RSTI/"
MENU_UUID = "039d2cf0-a2a0-44c7-bbfa-93930e8d87bd"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import CACHE as USER_CACHE

CACHE = USER_CACHE / "rsti"
RATE_STATE = CACHE / ".last-live-request"
MIN_DELAY = 1.0
DEFAULT_DELAY = 1.5

RIGHTS_NOTE = (
    "The RSTI site states CC BY-NC-ND 4.0; individual OCHRE responses may carry "
    "a different record-level availability statement. Preserve the response's "
    "license and do not automatically traverse linked UUIDs."
)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def parse_property(element: ET.Element) -> dict[str, Any]:
    label = text_of(element.find("label"))
    value = element.find("value")
    row: dict[str, Any] = {
        "label": label,
        "value": text_of(value),
    }
    if value is not None and value.attrib:
        row["value_attributes"] = dict(value.attrib)
    nested = [parse_property(child) for child in element.findall("property")]
    if nested:
        row["properties"] = nested
    return row


def parse_item(element: ET.Element) -> dict[str, Any]:
    identification = element.find("identification")
    label = text_of(identification.find("label")) if identification is not None else ""
    if not label:
        direct = (element.text or "").strip()
        label = direct or text_of(element.find("label"))
    return {
        "type": local_name(element.tag),
        "uuid": element.attrib.get("uuid", ""),
        "label": label,
        "description": text_of(element.find("description")),
        "publication_datetime": element.attrib.get("publicationDateTime", ""),
    }


def parse_response(payload: bytes, requested_uuid: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise RuntimeError(f"RSTI/OCHRE returned malformed XML: {exc}") from exc
    ochre = root.find("ochre") if local_name(root.tag) == "result" else root
    if ochre is None:
        raise RuntimeError("RSTI/OCHRE response changed: ochre element not found")
    entities = [child for child in ochre if local_name(child.tag) != "metadata"]
    if not entities:
        raise RuntimeError("RSTI/OCHRE returned no public entity for that UUID")
    entity = entities[0]
    identification = entity.find("identification")
    label = text_of(identification.find("label")) if identification is not None else ""
    if not label:
        label = (entity.text or "").strip()
    aliases = []
    if identification is not None:
        aliases = [
            {"language": alias.attrib.get("language", ""), "value": text_of(alias)}
            for alias in identification.findall("alias")
        ]
    context = entity.find("context")
    availability = entity.find("availability")
    license_node = availability.find("license") if availability is not None else None
    properties = [parse_property(node) for node in entity.findall(".//properties/property")]
    items_node = entity.find("items")
    items = [parse_item(child) for child in list(items_node)] if items_node is not None else []
    notes = [text_of(node) for node in entity.findall(".//notes") if text_of(node)]
    return {
        "requested_uuid": requested_uuid,
        "entity_type": local_name(entity.tag),
        "entity_uuid": entity.attrib.get("uuid", ""),
        "publication_datetime": entity.attrib.get("publicationDateTime", ""),
        "label": label,
        "aliases": aliases,
        "description": text_of(entity.find("description")),
        "context_path": context.attrib.get("displayPath", "") if context is not None else "",
        "license": {
            "label": text_of(license_node),
            "url": license_node.attrib.get("target", "") if license_node is not None else "",
        },
        "properties": properties,
        "notes": notes,
        "item_count": len(items),
        "items": items,
        "persistent_url": f"https://pi.lib.uchicago.edu/1001/org/ochre/{requested_uuid}",
        "request_url": f"{API}?uuid={requested_uuid}",
    }


def run_query(uuid: str, refresh: bool, delay: float) -> dict[str, Any]:
    parameters = {"uuid": uuid}
    cached = cache_path(CACHE, "record", parameters)
    prior = load_cache(cached, refresh)
    if prior is not None:
        return prior
    url = f"{API}?uuid={uuid}"
    payload = request_bytes(
        "RSTI/OCHRE",
        url,
        rate_state=RATE_STATE,
        delay=delay,
        accept="application/xml,text/xml;q=0.9",
    )
    result = {
        "source": "Ras Shamra Tablet Inventory / OCHRE",
        "mode": "record",
        "fetched_at": now(),
        "query": parameters,
        "request_url": url,
        "source_request_count": 1,
        "network_request_count": 1,
        "site_url": SITE,
        "rights_note": RIGHTS_NOTE,
        "scope_note": "One exact UUID response only; linked UUIDs were not followed.",
        "cache_hit": False,
        "response": parse_response(payload, uuid),
    }
    save_cache(cached, result)
    return result


def print_human(result: dict[str, Any]) -> None:
    response = result["response"]
    cache = "hit" if result.get("cache_hit") else "new"
    print(
        f"RSTI {response['entity_type']} · {response['label'] or response['entity_uuid']}"
    )
    print(response["persistent_url"])
    if response["description"]:
        print(response["description"])
    if response["context_path"]:
        print(f"Context: {response['context_path']}")
    if response["license"]["label"]:
        print(f"License: {response['license']['label']} · {response['license']['url']}")
    print(
        f"Properties: {len(response['properties'])}; immediate items: "
        f"{response['item_count']}; cache {cache}"
    )
    print("Linked UUIDs followed: no")
    for row in response["items"][:25]:
        detail = " · ".join(value for value in (row["label"], row["description"]) if value)
        print(f"  {row['uuid']}\t{detail}")
    if response["item_count"] > 25:
        print(f"  … {response['item_count'] - 25} more immediate items in --json output")


def filter_immediate_items(result: dict[str, Any], term: str) -> dict[str, Any]:
    """Filter items already present in this one response; never dereference them."""
    folded = term.casefold()
    response = result["response"]
    matches = [
        row
        for row in response["items"]
        if folded in f"{row['label']} {row['description']} {row['uuid']}".casefold()
    ]
    response["local_item_filter"] = term
    response["unfiltered_item_count"] = response["item_count"]
    response["items"] = matches
    response["item_count"] = len(matches)
    result["scope_note"] += " The returned immediate items were filtered locally."
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uuid", nargs="?", help="one public OCHRE UUID")
    parser.add_argument(
        "--menu",
        action="store_true",
        help="retrieve the one documented RSTI TEO menu UUID",
    )
    parser.add_argument(
        "--find",
        help="filter immediate items in that one response locally; linked UUIDs remain unfetched",
    )
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.delay < MIN_DELAY:
        parser.error(f"--delay cannot be less than {MIN_DELAY:g} second")
    if args.menu and args.uuid:
        parser.error("--menu cannot be combined with a UUID")
    uuid = MENU_UUID if args.menu else args.uuid
    if not uuid:
        parser.error("one UUID is required; unfiltered traversal is disabled")
    if not UUID_RE.fullmatch(uuid):
        parser.error("UUID must use canonical 8-4-4-4-12 hexadecimal form")
    try:
        result = run_query(uuid.lower(), args.refresh, args.delay)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.find:
        result = filter_immediate_items(result, args.find)
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
