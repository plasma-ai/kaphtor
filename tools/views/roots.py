"""The record wiki's Semitic root pages: one per record of `semitic_roots.json`, filed by first radical.

The set is optional: a folder without the file gets no pages. A page shows what the file ships and nothing more: the
reconstruction and meaning with where each comes from, each reflex's form as shipped and its sources, and the
project's note. A reflex whose gloss or text the file withholds says so. No Linear A entry is linked: a key match is
a lead for review, never identity, and links wait for an explicit field in the lexicon.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from ..core.semitic_root_schema import ps_radical_keys
from .markdown import escape as esc
from .markdown import table
from .model import slug
from .render import _page, collect

FILE = "semitic_roots.json"
ROOT = "wiki/semitic-roots"
OTHER = "other"          # the folder of a record whose headword gives no radical
SLUG_LENGTH = 48
BASIS = {"sed": "SED", "sed_edited": "SED, corrected", "project": "project"}
WITHHELD = {"gloss_withheld": "gloss withheld", "text_withheld": "source's text withheld"}


def _read(folder: Path) -> dict | None:
    path = Path(folder) / FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def radical(ps: str) -> str:
    """The first radical of a headword's first key (NFC), or OTHER."""
    keys = ps_radical_keys(ps)
    return unicodedata.normalize("NFC", keys[0][0]) if keys and keys[0] else OTHER


def path(root: dict) -> str:
    name = slug(root["meaning"] or "")[:SLUG_LENGTH].rstrip("_")
    stem = f"{root['id']}_{name}" if name else root["id"]
    return f"{ROOT}/{radical(root['ps'])}/{stem}"


def _cites(cites: list[dict]) -> str:
    return "; ".join(esc(f"{c['siglum']} {c['loc']}".strip()) for c in cites)


def _basis(value: str) -> str:
    return BASIS.get(value, value)


def page(root: dict) -> tuple[str, str]:
    ps, meaning = root["ps"], root["meaning"]
    sa = root["id"].startswith("SA")
    kind = "Epigraphic South Arabian headword" if sa else "Proto-Semitic"
    langs = [r["lang"] for r in root["reflexes"]]
    fields = {"title": f"{ps}: {meaning}",
              "desc": f"{kind} {ps}, {meaning}: reflexes in {len(langs)} language(s).",
              "tags": ["semitic-roots", "root"], "kind": "semitic_root", "id": root["id"]}
    rows = [["Reconstruction" if not sa else "Headword", esc(ps)], ["Meaning", esc(meaning)],
            ["Basis", esc(_basis(root["basis"]["ps"]) if root["basis"]["ps"] == root["basis"]["meaning"] else
                          f"reconstruction {_basis(root['basis']['ps'])}; meaning {_basis(root['basis']['meaning'])}")]]
    if "sed" in root:
        rows.append(["SED", esc(f"{root['sed']['siglum']} {root['sed']['loc']}")])
    body = ["## Root", ""] + table(["Field", "Value"], rows) + [""]
    if root["reflexes"]:
        body += ["## Reflexes", ""] + table(["Language", "Form", "Sources", "Note"], [
            [esc(r["lang"]), esc(r.get("text", "")), _cites(r["cite"]),
             next((label for key, label in WITHHELD.items() if r.get(key)), "")] for r in root["reflexes"]]) + [""]
        body += ["A form keeps its source's gloss only when the source is public domain or openly licensed.", ""]
    if root.get("notes"):
        body += ["## Notes", "", esc(root["notes"]), ""]
    return _page(path(root), fields, body)


def pages(folder: Path) -> dict[str, str]:
    """Path -> text for every root page, or nothing when the folder has no semitic_roots.json."""
    doc = _read(folder)
    return collect(page(r) for r in doc["roots"]) if doc else {}


def descs(folder: Path) -> dict[str, str]:
    """The desc of each radical folder the pages fill."""
    doc = _read(folder)
    if not doc:
        return {}
    out = {}
    for r in doc["roots"]:
        rad = radical(r["ps"])
        out[f"{ROOT}/{rad}"] = ("Semitic roots whose headword gives no radical." if rad == OTHER
                                else f"Semitic roots whose first radical is {rad}.")
    return dict(sorted(out.items()))
