"""The lexicon's language layers and families and the onomasticon's affiliations keep to their closed lists.

`language_layer` is the language a word reached Linear A through, `language_family` the family of its origin. The
two agree except under `Anatolian`, where the route and the origin can part. An onomasticon name takes its linked
lexicon entry's layer as its affiliation. Nothing here writes.
"""
import json
from collections import Counter

import pytest

from tools.paths import LINEAR_A_DATA

pytestmark = pytest.mark.data

LAYERS = ("Semitic", "Hurrian", "Middle Egyptian", "Anatolian", "Indo-European", "Sumerian", "Aegean", "logogram")
FAMILY_OF_LAYER = {"Semitic": {"Semitic"}, "Hurrian": {"Hurro-Urartian"}, "Middle Egyptian": {"Egyptian"},
                   "Indo-European": {"Indo-European"}, "Anatolian": {"Semitic", "Indo-European"},
                   "Sumerian": {"Sumerian"}, "Aegean": {None}, "logogram": {None}}
AFFILIATION_OF_LAYER = {"Semitic": "semitic", "Hurrian": "hurrian", "Middle Egyptian": "egyptian",
                        "Anatolian": "anatolian", "Indo-European": "indo_european", "Sumerian": "sumerian",
                        "Aegean": "aegean", "logogram": "unknown"}
AFFILIATIONS = ("semitic", "hurrian", "egyptian", "anatolian", "indo_european", "sumerian", "aegean", "unknown")


def load(name):
    path = LINEAR_A_DATA / name
    if not path.exists():
        pytest.skip(f"{name} is not in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


def layer_errors(entries):
    return [(e["word"], e.get("language_layer")) for e in entries if e.get("language_layer") not in LAYERS]


def family_errors(entries):
    return [(e["word"], e.get("language_layer"), e.get("language_family")) for e in entries
            if e.get("language_layer") in FAMILY_OF_LAYER
            and e.get("language_family") not in FAMILY_OF_LAYER[e["language_layer"]]]


def affiliation_errors(names, entries):
    layer = {e["word"]: e.get("language_layer") for e in entries}
    errors = [(n["token"], n["affiliation"]) for n in names if n["affiliation"] not in AFFILIATIONS]
    for n in names:
        ref = n.get("lexicon_ref")
        if ref in layer and AFFILIATION_OF_LAYER.get(layer[ref]) != n["affiliation"]:
            errors.append((n["token"], n["affiliation"], ref, layer[ref]))
    return errors


def test_every_lexicon_entry_has_a_layer_from_the_list():
    assert layer_errors(load("lexicon.json")["entries"]) == []


def test_each_layer_takes_its_family():
    assert family_errors(load("lexicon.json")["entries"]) == []


def test_each_name_takes_its_lexicon_entrys_layer():
    names = load("onomasticon.json")
    assert names["affiliation_classes"] == list(AFFILIATIONS)
    assert affiliation_errors(names["entries"], load("lexicon.json")["entries"]) == []


def test_the_onomasticon_counts_its_affiliations():
    names = load("onomasticon.json")
    counted = names["stats"]["by_affiliation"]
    stated = {k: v["total"] if isinstance(v, dict) else v for k, v in counted.items()}
    assert stated == dict(Counter(n["affiliation"] for n in names["entries"]))
