#!/usr/bin/env python3
"""Tag root-database entries with an explicit semantic_field list.

Adds an additive, optional `semantic_field: [str]` field to entries in
data/semitic_roots.json, data/egyptian_roots.json, and data/luwian_roots.json,
derived from word-boundary keyword matching on the Meaning gloss. Entries with
no domain match receive no field. Existing semantic_field values are replaced
only when --retag is passed (default: left untouched).

The taxonomy below supersedes the 8-domain browsing heuristic in
generate_semitic_root_indexes.py; that script prefers explicit semantic_field
when present. Domain names align with lib/contact_lexicon.py conventions where
the two overlap (maritime, metrology, month_name).

Dry-run by default; pass --apply to rewrite the databases.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SKILL = Path(__file__).resolve().parents[2]

DATABASES = {
    "semitic": SKILL / "data" / "semitic_roots.json",
    "egyptian": SKILL / "data" / "egyptian_roots.json",
    "luwian": SKILL / "data" / "luwian_roots.json",
}

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "maritime": [
        "ship", "boat", "sea", "sail", "sailor", "harbor", "harbour", "port",
        "oar", "anchor", "mast", "fleet", "island", "wave", "shore", "coast",
        "rope", "cable", "fishing", "ferry", "raft",
    ],
    "textile": [
        "cloth", "clothing", "weave", "woven", "weaver", "linen", "wool",
        "thread", "garment", "fabric", "textile", "robe", "spin", "loom",
        "flax", "tunic", "veil", "sew", "embroider", "felt", "carded",
    ],
    "metallurgy": [
        "copper", "bronze", "iron", "gold", "silver", "tin", "lead", "metal",
        "smith", "forge", "smelt", "ore", "ingot", "cast", "alloy",
    ],
    "administrative": [
        "scribe", "seal", "tablet", "record", "account", "tax", "tribute",
        "official", "governor", "overseer", "servant", "slave", "king",
        "queen", "ruler", "lord", "palace", "decree", "document", "register",
        "inventory", "steward", "herald", "messenger",
    ],
    "ritual_cultic": [
        "offering", "sacrifice", "temple", "altar", "holy", "sacred",
        "ritual", "priest", "priestess", "purify", "libation", "incense",
        "anoint", "bless", "curse", "oath", "pray", "prayer", "vow",
        "shrine", "consecrate", "sanctuary", "omen", "divination",
    ],
    "deity": ["god", "goddess", "deity", "divine", "demon", "spirit"],
    "kinship": [
        "father", "mother", "son", "daughter", "brother", "sister", "uncle",
        "aunt", "kin", "clan", "family", "wife", "husband", "bride", "heir",
        "widow", "orphan", "ancestor", "grandfather", "grandmother",
    ],
    "fauna": [
        "ox", "oxen", "bull", "cow", "sheep", "goat", "lamb", "ram", "ewe",
        "donkey", "ass", "horse", "mare", "pig", "swine", "dog", "lion",
        "bird", "eagle", "falcon", "snake", "serpent", "wolf", "bear",
        "deer", "gazelle", "cattle", "calf", "animal", "fish", "insect",
        "locust", "bee", "scorpion", "mouse", "camel", "leopard", "hyena",
        "fox", "hare", "dove", "raven", "owl", "frog", "worm",
    ],
    "flora": [
        "tree", "plant", "seed", "flower", "leaf", "leaves", "fruit", "vine",
        "cedar", "oak", "palm", "reed", "grass", "herb", "thorn", "wood",
        "cypress", "juniper", "tamarisk", "acacia", "myrtle", "shrub",
        "bush", "branch", "twig",
    ],
    "body": [
        "hand", "foot", "feet", "head", "eye", "ear", "mouth", "tongue",
        "heart", "blood", "bone", "flesh", "hair", "arm", "leg", "knee",
        "tooth", "teeth", "nose", "face", "neck", "belly", "breast", "womb",
        "skin", "liver", "shoulder", "finger", "thigh", "throat", "rib",
        "kidney", "skull", "forehead", "beard",
    ],
    "agriculture": [
        "field", "grain", "barley", "wheat", "emmer", "harvest", "plow",
        "plough", "furrow", "sow", "reap", "thresh", "sickle", "granary",
        "olive", "fig", "vineyard", "orchard", "pasture", "fodder", "hoe",
        "irrigate", "irrigation", "fallow", "winnow",
    ],
    "food_drink": [
        "bread", "wine", "beer", "oil", "honey", "milk", "eat", "drink",
        "food", "meal", "flour", "butter", "cheese", "meat", "salt",
        "dough", "broth", "fat", "feast", "hunger", "thirst",
    ],
    "warfare": [
        "war", "battle", "weapon", "sword", "spear", "bow", "arrow",
        "shield", "army", "soldier", "fight", "slay", "kill", "conquer",
        "fortress", "chariot", "helmet", "armor", "armour", "siege",
        "captive", "plunder", "booty", "warrior",
    ],
    "metrology": [
        "measure", "weigh", "weight", "shekel", "talent", "mina", "cubit",
        "span", "homer", "ephah", "hin", "log",
    ],
    "month_name": ["month", "calendar", "new moon"],
    "toponym": [
        "city", "town", "village", "land", "country", "region", "river",
        "mountain", "hill", "valley", "spring", "well", "desert", "steppe",
        "plain", "border", "road", "path",
    ],
    "numeral": [
        "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "hundred", "thousand", "half", "pair", "twenty", "number",
    ],
    "color_dye": [
        "purple", "red", "blue", "dye", "color", "colour", "crimson",
        "scarlet", "white", "black", "green", "yellow",
    ],
    "pottery_vessel": [
        "pot", "jar", "vessel", "cup", "bowl", "jug", "pithos", "amphora",
        "flask", "basin", "pitcher", "ladle", "cauldron",
    ],
    "building": [
        "house", "wall", "door", "gate", "roof", "pillar", "foundation",
        "build", "brick", "stone", "courtyard", "window", "threshold",
        "beam", "tower", "dwelling", "tent", "hut",
    ],
}

_COMPILED = {
    domain: re.compile(r"\b(?:" + "|".join(re.escape(kw) for kw in kws) + r")\b", re.IGNORECASE)
    for domain, kws in DOMAIN_KEYWORDS.items()
}

# Egyptian Period scaffold: only explicit statements count; never guess.
_PERIOD_PATTERNS = [
    ("Old Egyptian", re.compile(r"\bOld Egyptian\b", re.IGNORECASE)),
    ("Middle Egyptian", re.compile(r"\bMiddle Egyptian\b", re.IGNORECASE)),
    ("Late Egyptian", re.compile(r"\bLate Egyptian\b", re.IGNORECASE)),
    ("Demotic", re.compile(r"\bDemotic\b", re.IGNORECASE)),
]


def classify(meaning: str) -> list[str]:
    gloss = (meaning or "").strip().strip("'\"")
    if not gloss:
        return []
    return sorted(domain for domain, rx in _COMPILED.items() if rx.search(gloss))


def explicit_period(entry: dict[str, Any]) -> str | None:
    blob = " ".join([
        str(entry.get("Meaning", "")),
        " ".join(str(s) for s in entry.get("Sources", []) or []),
        str(entry.get("Review_Notes", "")),
    ])
    for label, rx in _PERIOD_PATTERNS:
        if rx.search(blob):
            return label
    return None


def tag_database(path: Path, *, is_egyptian: bool, retag: bool) -> tuple[list[dict[str, Any]], Counter, int, int]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    domain_counts: Counter[str] = Counter()
    tagged = 0
    periods_set = 0
    for entry in entries:
        if retag or "semantic_field" not in entry:
            fields = classify(str(entry.get("Meaning", "")))
            if fields:
                entry["semantic_field"] = fields
                tagged += 1
                domain_counts.update(fields)
            elif retag:
                entry.pop("semantic_field", None)
        if is_egyptian and "Period" not in entry:
            period = explicit_period(entry)
            if period:
                entry["Period"] = period
                periods_set += 1
    return entries, domain_counts, tagged, periods_set


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run report)")
    parser.add_argument("--retag", action="store_true", help="recompute tags even where semantic_field exists")
    args = parser.parse_args()

    report: dict[str, Any] = {"mode": "apply" if args.apply else "dry-run", "databases": {}}
    results = {}
    for name, path in DATABASES.items():
        entries, counts, tagged, periods = tag_database(path, is_egyptian=(name == "egyptian"), retag=args.retag)
        results[name] = entries
        report["databases"][name] = {
            "entries": len(entries),
            "tagged": tagged,
            "periods_set": periods if name == "egyptian" else None,
            "domains": dict(counts.most_common()),
        }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.apply:
        for name, path in DATABASES.items():
            path.write_text(json.dumps(results[name], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
