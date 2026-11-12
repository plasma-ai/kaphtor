"""The record wiki's names section: every name of `onomasticon.json`, filed by the language layer the record reads
it through, with the roots the names are built from.

A name page gives the name's kind, reading, root, cognates, documents and the read words on the same documents; the
reading, root, note and cognates come from the lexicon entry the name points to (`lexicon_ref`). A root page lists
the names that share a root; roots are filed inside their layer, so the same consonants under two layers are two
pages, and a compound name stands under each of its roots. The guide cuts across the layers: one list per kind of
name, one ledger of every name, and a page on how to read the rest.

The section links only to itself, so it can be lifted out whole as a wiki of its own. A name with no reading shows
no comparison: its page gives the kind, the documents and the company, and nothing else. Folder names are ASCII.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from .markdown import escape as esc
from .markdown import link, paragraphs, table
from .model import Model, natural, slug
from .render import _page, collect

ROOT = "wiki/names"
GUIDE = f"{ROOT}/guide"
# affiliation -> (folder, the layer's name)
LAYERS = {
    "semitic": ("semitic", "Semitic"),
    "hurrian": ("hurrian", "Hurrian"),
    "egyptian": ("egyptian", "Egyptian"),
    "aegean": ("aegean", "Aegean"),
    "anatolian": ("anatolian", "Anatolian"),
    "indo_european": ("indo-european", "Indo-European"),
    "sumerian": ("sumerian", "Sumerian"),
    "unknown": ("unread", "Unread"),
}
# onomasticon type -> (page name, singular, plural, the title of its list)
KINDS = {
    "personal_name": ("people", "personal name", "personal names", "People"),
    "toponym": ("places", "place name", "place names", "Places"),
    "theonym": ("gods", "divine name", "divine names", "Gods"),
    "title": ("titles", "title", "titles", "Titles"),
    "gentilic": ("peoples", "gentilic", "gentilics", "Peoples"),
    "toponym_gentilic": ("places_and_peoples", "place name or gentilic", "place names or gentilics",
                         "Places or peoples"),
}
LAYER_NOTE = {
    "semitic": "Names read through a Semitic root or a name in a Semitic catalogue.",
    "hurrian": "Names read through a Hurrian name or name element.",
    "egyptian": "Names read through an Egyptian name.",
    "aegean": ("Names read through a Linear B name or place, or an Egyptian list of Keftiu names, with no Semitic "
               "root."),
    "anatolian": "Names read through an Anatolian name or word.",
    "indo_european": "Names read through an Indo-European form.",
    "sumerian": "Names read through a Sumerian word or name.",
    "unknown": "Names the tablets mark as names, with no reading yet.",
}
# letters of a root's label that have no ASCII base letter, as a page name spells them
ROOT_ASCII = {"ʾ": "alef", "ʔ": "alef", "ʿ": "ayin", "ʕ": "ayin", "ꜥ": "ayin", "ꜣ": "aleph3", "ḥ": "hh", "ḫ": "kh",
              "ṭ": "tt", "ṣ̂": "dd", "ṣ": "ss", "š": "sh", "ś": "sl", "ŝ": "sl", "ṯ": "th", "ḏ": "dh", "ɣ": "gh",
              "ẓ": "zz", "ḳ": "q"}
HOW_TO = """## Kinds

The record sorts each name by what it names: a person, a place, a god, a title or a people. A few stand between
place and people. {kinds} lists each kind.

## Layers

Each name is filed under the language the record reads it through. A layer is set only by a positive match: a name
in a catalogue of that language, or an identified reading. Likeness of sound alone never sets a layer. Every layer
is a hypothesis and carries its own standing.

## Roots

A root page gathers the names that share a root. A compound name has two roots and appears under both. Roots are
filed inside their layer, so the same consonants under two layers are two pages.

## Standing

- **Reading's standing** is the lexicon's tier for the reading: CONFIRMED, PROBABLE, CANDIDATE or SPECULATIVE, the
  strongest first.
- **Standing as a personal name** (or place name, divine name, title, gentilic) says how sure the kind is: that the
  word names a person and not a place, a god or a common thing.
- **Standing of the layer** says how sure the language is, with the kind of evidence in brackets.

Rival readings stay on the page, in the note.

## Attestations and company

Documents use the GORILA sigla (HT 122a is Haghia Triada tablet 122, side a). Company lists the read words that
stand on the same documents; a name's company is part of the case for it.

## Source

The pages are generated from `data/linear-a/onomasticon.json` for the names and `data/linear-a/lexicon.json` for
readings, roots, cognates and notes. The project's own readings and notes are di Mino's; other scholars are cited
in each note by siglum and page."""


def aff(n: dict) -> str:
    """A name's layer, as a key of LAYERS: the record's `affiliation`, whatever its case; ValueError for one the
    section has no folder for."""
    key = str(n.get("affiliation") or "unknown").lower().replace("-", "_").replace(" ", "_")
    if key not in LAYERS:
        raise ValueError(f"{n['token']}: no names folder for the affiliation {n.get('affiliation')!r}")
    return key


def _count(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else many or one + 's'}"


def root_slug(label: str) -> str:
    """An ASCII page name for a root's label: `ʿ-b-r` -> `ayin-b-r`."""
    s = label
    for letter, spelt in sorted(ROOT_ASCII.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(letter, spelt)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower() or "root"


def root_parts(root: str | None) -> list[tuple[str, str]]:
    """A lexicon root as (label, remark) parts: `ḏ + š-n-ṭ` is two; a remark in brackets and anything after a comma
    leave the label; an affix (`-ān-`) is no root."""
    out = []
    for part in (root or "").split(" + "):
        label, opened, rest = part.partition("(")
        remark = rest.rpartition(")")[0].strip() if opened else ""
        label = label.split(",", 1)[0].strip()
        if label and not label.startswith("-"):
            out.append((label, remark))
    return out


class Names:
    """The names with their lexicon entries, paths and roots, worked out once."""

    def __init__(self, model: Model):
        self.lexicon = model.lexicon
        self.names = sorted(model.onomasticon.values(), key=lambda n: natural(slug(n["token"])))
        self.by_token = {n["token"]: n for n in self.names}
        self.entry = {n["token"]: model.lexicon.get(n.get("lexicon_ref") or "") or {} for n in self.names}
        self.parts = {t: root_parts(e.get("root")) for t, e in self.entry.items()}
        self.roots: dict[tuple[str, str], dict] = {}   # (layer folder, label) -> root
        for n in self.names:
            folder = LAYERS[aff(n)][0]
            ps = self.entry[n["token"]].get("proto_semitic")
            for label, remark in self.parts[n["token"]]:
                r = self.roots.setdefault((folder, label), {"label": label, "folder": folder, "remarks": [],
                                                            "names": [], "ps": []})
                if remark and remark not in r["remarks"]:
                    r["remarks"].append(remark)
                if n not in r["names"]:
                    r["names"].append(n)
                # a root's Proto-Semitic form is known only from a name built on that root alone
                if isinstance(ps, dict) and len(self.parts[n["token"]]) == 1 and ps not in r["ps"]:
                    r["ps"].append(ps)
        taken: set[tuple[str, str]] = set()
        for (folder, label), r in sorted(self.roots.items()):
            name = base = root_slug(label)
            i = 2
            while (folder, name) in taken:
                name, i = f"{base}-{i}", i + 1
            taken.add((folder, name))
            r["path"] = f"{ROOT}/{folder}/roots/{name}"

    def path(self, n: dict) -> str:
        return f"{ROOT}/{LAYERS[aff(n)][0]}/names/{slug(n['token'])}"

    def link(self, n: dict) -> str:
        return link(self.path(n), esc(n["token"]))

    def root_links(self, n: dict) -> str:
        folder = LAYERS[aff(n)][0]
        return " + ".join(link(self.roots[(folder, label)]["path"], esc(label)) for label, _ in self.parts[n["token"]])

    def of_layer(self, affiliation: str) -> list[dict]:
        return [n for n in self.names if aff(n) == affiliation]

    def roots_of(self, folder: str) -> list[dict]:
        return sorted((r for (f, _), r in self.roots.items() if f == folder),
                      key=lambda r: (-len(r["names"]), r["label"]))


def gloss(n: dict) -> str:
    return ": ".join(b for b in (n.get("reading"), n.get("meaning")) if b) or "no reading"


def _ps(ps) -> str:
    forms = ps if isinstance(ps, list) else [ps]
    return ", ".join(esc(f"{p.get('form')} (#{p.get('id')})") for p in forms)


def name_page(names: Names, n: dict) -> tuple[str, str]:
    folder, layer = LAYERS[aff(n)]
    kind_page, kind, _, _ = KINDS[n["type"]]
    e = names.entry[n["token"]]
    fields = {"title": n["token"],
              "desc": f"{gloss(n)}. {layer}" + (f", {e['confidence']}." if e.get("confidence") else "."),
              "tags": ["names", kind.replace(" ", "-"), folder], "kind": "name", "form": n["token"],
              "reading": n.get("reading") or "", "attestations": n["attestations"]}
    body = ([f"**{esc(n['reading'])}** · {esc(n.get('meaning') or '')}", ""] if n.get("reading")
            else [f"No reading. The record files this word as a {kind}.", ""])
    rows = [["Kind", link(f"{GUIDE}/kinds/{kind_page}", kind.capitalize())]]
    if n.get("reading"):
        rows.append(["Reading", esc(n["reading"])])
    if n.get("meaning"):
        rows.append(["Meaning", esc(n["meaning"])])
    rows.append(["Language layer", link(f"{ROOT}/{folder}/_index", layer)])
    if names.parts[n["token"]]:
        rows.append(["Root", names.root_links(n)])
    elif e.get("root"):
        rows.append(["Root", esc(e["root"])])
    if e.get("proto_semitic"):
        rows.append(["Proto-Semitic", _ps(e["proto_semitic"])])
    if e.get("confidence"):
        rows.append(["Reading's standing", esc(e["confidence"])])
    rows.append([f"Standing as a {kind}", esc(n.get("type_confidence") or "")])
    evidence = f" ({n['affiliation_evidence']})" if n.get("affiliation_evidence") else ""
    rows.append(["Standing of the layer", esc(f"{n.get('affiliation_confidence') or ''}{evidence}")])
    if e.get("source"):
        rows.append(["Source", esc(e["source"])])
    body += table(["Field", "Value"], rows) + [""]

    note, as_name = (e.get("note") or "").strip(), (n.get("note") or "").strip()
    if note:
        body += ["## Note", "", paragraphs(note), ""]
    if as_name and as_name != note:
        body += ["## As a name", "", paragraphs(as_name), ""]
    cognates = e.get("cognates")
    if isinstance(cognates, dict) and cognates:
        body += ["## Cognates", ""] + table(["Language", "Comparison"],
                                           [[esc(k), esc(v)] for k, v in cognates.items()]) + [""]
    elif isinstance(cognates, str) and cognates.strip():
        body += ["## Cognates", "", paragraphs(cognates), ""]
    if n.get("linear_b_comparanda"):
        body += ["## Linear B", "", paragraphs(n["linear_b_comparanda"]), ""]

    docs = len(n["attestations"])
    rows = [["Occurrences", f"{n['frequency']} in {_count(docs, 'document')}"],
            ["Documents", esc(", ".join(n["attestations"]))],
            ["Sites", esc(", ".join(n["sites"])) or "none recorded"]]
    if n.get("genre_supports"):
        rows.append(["Supports", esc(", ".join(f"{k} {v}" for k, v in n["genre_supports"].items()))])
    position = n.get("position_summary") or {}
    if position.get("follows"):
        rows.append(["Stands after", esc(", ".join(f"a {k} {v}×" for k, v in position["follows"].items()))])
    if position.get("heads_document"):
        rows.append(["Heads a document", f"{position['heads_document']}×"])
    body += ["## Attestations", ""] + table(["Field", "Value"], rows) + [""]

    rows = []
    for c in n.get("co_occurring_known") or []:
        if isinstance(c, str):
            known = names.lexicon.get(c) or {}
            c = {"word": c, "reading": known.get("reading"), "meaning": known.get("meaning")}
        if c.get("word") == n["token"]:
            continue
        other = names.by_token.get(c["word"])
        rows.append([names.link(other) if other else esc(c["word"]), esc(c.get("reading") or ""),
                     esc(c.get("meaning") or "")])
    if rows:
        body += ["## Company", "", "Read words on the same documents.", ""]
        body += table(["Word", "Reading", "Meaning"], rows) + [""]
    return _page(names.path(n), fields, body)


def root_page(names: Names, r: dict) -> tuple[str, str]:
    layer = next(title for folder, title in LAYERS.values() if folder == r["folder"])
    tokens = [n["token"] for n in r["names"]]
    desc = f"{_count(len(tokens), 'name')}: " + ", ".join(tokens[:6])
    desc += f" and {len(tokens) - 6} more." if len(tokens) > 6 else "."
    fields = {"title": r["label"], "desc": desc, "tags": ["names", "root", r["folder"]], "kind": "name_root",
              "id": f"{r['folder']}:{r['label']}"}
    rows = [["Language layer", link(f"{ROOT}/{r['folder']}/_index", layer)]]
    if r["ps"]:
        rows.append(["Proto-Semitic", _ps(r["ps"])])
    rows += [["Remark", esc(remark)] for remark in r["remarks"]]
    rows.append(["Names", str(len(tokens))])
    body = table(["Field", "Value"], rows) + ["", "## Names from this root", ""]
    body += table(["Name", "Reading", "Meaning", "Documents"],
                  [[names.link(n), esc(n.get("reading") or ""), esc(n.get("meaning") or ""),
                    str(len(n["attestations"]))] for n in r["names"]]) + [""]
    return _page(r["path"], fields, body)


def _guide(name: str, title: str, desc: str, tag: str, body: list[str], folder: str = GUIDE) -> tuple[str, str]:
    return _page(f"{folder}/{name}", {"title": title, "desc": desc, "tags": ["names", tag], "kind": "ledger"}, body)


def ledger(names: Names) -> tuple[str, str]:
    rows = [[names.link(n), esc(gloss(n)), f"{LAYERS[aff(n)][1]} {KINDS[n['type']][1]}",
             names.root_links(n), esc(names.entry[n["token"]].get("confidence") or ""), str(len(n["attestations"]))]
            for n in names.names]
    return _guide("ledger", "Ledger", "Every name in one table: reading, layer, kind, root, standing and documents.",
                  "ledger", table(["Name", "Reading and meaning", "Layer and kind", "Root", "Standing", "Docs"], rows))


def kind_pages(names: Names) -> list[tuple[str, str]]:
    out = []
    for kind, (name, one, many, title) in KINDS.items():
        mine = [n for n in names.names if n["type"] == kind]
        if not mine:
            continue
        rows = [[names.link(n), esc(n.get("reading") or ""), esc(n.get("meaning") or ""),
                 link(f"{ROOT}/{LAYERS[aff(n)][0]}/_index", LAYERS[aff(n)][1]),
                 str(len(n["attestations"]))] for n in mine]
        out.append(_guide(name, title, f"The {many}, across every layer.", "kind",
                          table(["Name", "Reading", "Meaning", "Layer", "Documents"], rows), f"{GUIDE}/kinds"))
    return out


def how_to() -> tuple[str, str]:
    body = HOW_TO.format(kinds=link(f"{GUIDE}/kinds/_index", "Kinds of name")).split("\n")
    return _guide("how_to", "How to read a page",
                  "What the layers, roots and standings mean, and where the record comes from.", "guide", body)


def pages(model: Model) -> dict[str, str]:
    """Path -> text for every name page, root page and guide page, or nothing when the record holds no name."""
    names = Names(model)
    if not names.names:
        return {}
    from . import names_map  # the map builds on this module's names and links
    return collect([*(name_page(names, n) for n in names.names),
                    *(root_page(names, r) for _, r in sorted(names.roots.items())),
                    ledger(names), *kind_pages(names), how_to(), names_map.page(names)])


def assets(model: Model) -> dict[str, str]:
    """Path (with its extension) -> text of each file the section ships beside its pages: the map of Crete."""
    from . import names_map
    names = Names(model)
    return {f"{GUIDE}/{names_map.IMAGE}": names_map.svg(names)} if names.names else {}


def descs(model: Model) -> dict[str, str]:
    """The desc of the names folder and of each folder its pages fill. None holds a count: a desc is written once."""
    names = Names(model)
    if not names.names:
        return {}
    out = {ROOT: ("The names of the Linear A tablets (people, places, gods, titles, peoples), filed by language "
                  "layer, with the roots beneath them."),
           GUIDE: ("Ways across the whole record: how to read a page, the map of Crete by find site, the kinds of name, and "
                  "every name in one ledger."),
           f"{GUIDE}/kinds": ("People, places, gods, titles and peoples: each kind of name in one list, across the "
                              "layers.")}
    for affiliation, (folder, layer) in LAYERS.items():
        if not names.of_layer(affiliation):
            continue
        out[f"{ROOT}/{folder}"] = LAYER_NOTE[affiliation]
        out[f"{ROOT}/{folder}/names"] = f"The {layer} names, one page each."
        if names.roots_of(folder):
            out[f"{ROOT}/{folder}/roots"] = f"The roots under the {layer} names, each with the names it carries."
    return dict(sorted(out.items()))


def titles(model: Model) -> dict[str, str]:
    """The title of the names folder and of each folder under it, which an index would otherwise take from its
    path: `Indo-European`, not `indo-european`."""
    names = Names(model)
    if not names.names:
        return {}
    out = {ROOT: "Linear A Names", GUIDE: "Guide", f"{GUIDE}/kinds": "Kinds of name"}
    for affiliation, (folder, layer) in LAYERS.items():
        if not names.of_layer(affiliation):
            continue
        out[f"{ROOT}/{folder}"] = layer
        out[f"{ROOT}/{folder}/names"] = f"{layer} names"
        if names.roots_of(folder):
            out[f"{ROOT}/{folder}/roots"] = f"{layer} roots"
    return dict(sorted(out.items()))


def _sites(mine: list[dict], top: int | None = None) -> str:
    return esc(", ".join(f"{s} {c}" for s, c in Counter(s for n in mine for s in n["sites"]).most_common(top)))


def _layer_summary(names: Names, affiliation: str) -> str:
    folder, _ = LAYERS[affiliation]
    mine, roots = names.of_layer(affiliation), names.roots_of(folder)
    kinds = Counter(n["type"] for n in mine)
    standing = Counter(names.entry[n["token"]].get("confidence") or "no reading" for n in mine)
    rows = [["Names", str(len(mine))],
            ["Kinds", ", ".join(f"{KINDS[k][2 if c != 1 else 1]} {c}" for k, c in kinds.most_common())]]
    if roots:
        rows.append(["Roots", str(len(roots))])
    rows += [["Sites", _sites(mine)], ["Standing", esc(", ".join(f"{k} {v}" for k, v in standing.most_common()))]]
    body = table(["Field", "Value"], rows)
    shared = [r for r in roots if len(r["names"]) > 1]
    if shared:
        body += ["", "## Roots that carry more than one name", ""]
        body += table(["Root", "Names"], [[link(r["path"], esc(r["label"])),
                                           ", ".join(names.link(n) for n in r["names"])] for r in shared])
    return "\n".join(body)


def summaries(model: Model) -> dict[str, str]:
    """Folder -> the summary under its index's rows: the whole record's counts by layer and by kind, and each
    layer's own. The numbers are counted from the data at every build."""
    names = Names(model)
    if not names.names:
        return {}
    kinds = Counter(n["type"] for n in names.names)
    layers = [(a, folder, layer, names.of_layer(a)) for a, (folder, layer) in LAYERS.items() if names.of_layer(a)]
    intro = (f"The tablets of Minoan Crete carry {_count(len(names.names), 'name')}: "
             + ", ".join(_count(kinds[k], one, many) for k, (_, one, many, _) in KINDS.items() if kinds[k])
             + ". Each name is filed here under the language it is read through, and under each language lie the "
             "roots the names are built from. A root page shows every name that grows from it; a name page shows "
             "its reading, its root, its cognates, the documents it stands on and the words that keep it company.")
    by_layer = table(["Layer", "Names", "Roots", "Chief sites"],
                     [[link(f"{ROOT}/{folder}/_index", layer), str(len(mine)), str(len(names.roots_of(folder)) or ""),
                       _sites(mine, 3)] for _, folder, layer, mine in layers])
    by_kind = table(["Kind", "Names", "Layers"],
                    [[link(f"{GUIDE}/kinds/{name}", title), str(kinds[k]),
                      ", ".join(f"{LAYERS[a][1]} {c}" for a, c in Counter(
                          aff(n) for n in names.names if n["type"] == k).most_common())]
                     for k, (name, _, _, title) in KINDS.items() if kinds[k]])
    start = (f"Start with the {link(f'{GUIDE}/_index', 'Guide')}: {link(f'{GUIDE}/how_to', 'how to read a page')}, "
             f"the {link(f'{GUIDE}/map', 'map of Crete by find site')}, the "
             f"{link(f'{GUIDE}/kinds/_index', 'kinds of name')} and the {link(f'{GUIDE}/ledger', 'ledger')} of all "
             "names.")
    out = {ROOT: "\n".join([intro, "", *by_layer, "", *by_kind, "", start])}
    for affiliation, folder, _, _ in layers:
        out[f"{ROOT}/{folder}"] = _layer_summary(names, affiliation)
    return out
