"""The record wiki's Pre-Greek pages: one per word of `pregreek_lexicon.json`, filed by the initial of its key, and two
ledgers, `by_feature` (Beekes 2014's features and the words that cite them) and `semitic` (the words with a Semitic
comparison, by language and by the work's verdict).

The set is optional: a folder without the lexicon gets no pages. A page shows what the lexicon ships and nothing
more: the headword and its keys, each work that treats it with its place, verdict and features, and each Semitic
comparison with its dictionary citations, proposer and verdict. No gloss of a closed work is shown, and a comparison
whose gloss the lexicon withholds says so. The one gloss a page shows is Wiktionary's, from the share-alike sidecar,
and every page that shows one carries its attribution and licence; the ledgers show none. A word links to a Semitic
root only through `proto_semitic`, set by hand review: a matching key is a lead, never a link.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from . import roots
from .markdown import escape as esc
from .markdown import link, table
from .model import natural
from .render import _page, collect

FILE = "pregreek_lexicon.json"
FEATURES = "pregreek_features.json"
GLOSSES = "pregreek_wiktionary_glosses.json"
ROOT = "wiki/pre-greek"
BASIS = {"lsj": "LSJ's spelling", "first_lane": "the first work's spelling"}
REVIEW = {"machine_compiled": "compiled from the works' indexes, not reviewed by hand"}
LICENCE = "CC BY-SA 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
ATTRIBUTION = (f"The gloss is Wiktionary's, under {LICENCE} ({LICENCE_URL}): attribute it to the Wiktionary "
               "contributors and share any adaptation alike.")
COMPARISONS_NOTE = ("A comparison is a proposal on record, with the verdict of the work that lists it; no gloss of a "
                    "closed work is shown.")
FEATURES_NOTE = ("The features are the numbered sections of Beekes 2014, chapters 2–3, by id and the affix or letters "
                 "each treats; their headings are withheld. A word names a feature when its entry in the book's "
                 "lexicon cites it, and is an example when the section cites the word.")
SEMITIC_NOTE = ("Each Semitic comparison the lexicon records, by language and by the verdict of the work that lists "
                "it. A rejected proposal keeps its form and proposer. No gloss of a closed work is shown.")


def _read(folder: Path, name: str):
    path = Path(folder) / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stem(entry: dict) -> str:
    """The page name: the folded key, with `#` (a homograph's number) and spaces as `_`."""
    return re.sub(r"[^\w]+", "_", entry["key"]).strip("_")


def path(entry: dict) -> str:
    return f"{ROOT}/{entry['key'][0]}/{stem(entry)}"


def title(entry: dict) -> str:
    """The headword, with a homograph's number: κίλλιξ (2)."""
    number = entry["id"].partition("#")[2]
    return f"{entry['lemma']} ({number})" if number else entry["lemma"]


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def _feature(fid: str, features: dict) -> str:
    notation = (features.get(fid) or {}).get("notation")
    return f"{fid} {notation}" if notation else fid


def _cites(cites: list[dict]) -> str:
    return "; ".join(esc(f"{c['siglum']} {c['loc']}".strip()) for c in cites)


def _form(c: dict) -> str:
    return esc(", ".join([c["form"], *c.get("variants", [])]))


def _lang(c: dict) -> str:
    return esc(f"{c['lang']} ({c['variety']})" if c.get("variety") else c["lang"])


def _work(c: dict) -> str:
    """The work that lists a comparison and its page: "Rosół 2013, 21"."""
    return esc(f"{c['work']}, {c['loc']}")


def _note(c: dict) -> str:
    return "; ".join(label for key, label in (("cf", "for comparison"), ("gloss_withheld", "gloss withheld"))
                     if c.get(key))


def _source_row(s: dict, features: dict) -> list[str]:
    detail = []
    if s.get("features"):
        detail.append(", ".join(_feature(f, features) for f in s["features"]))
    if s.get("example_of"):
        detail.append("example of " + _feature(s["example_of"], features))
    if s.get("toponym"):
        detail.append("a toponym")
    return [esc(s["work"]), esc(s.get("loc") or s.get("url") or ""), esc(s.get("section", "")),
            esc(s.get("verdict", "")), esc("; ".join(detail))]


class Lexicon:
    """The lexicon, its features and glosses, and the root records `proto_semitic` names, read once."""

    def __init__(self, folder: Path, roots_folder: Path | None = None):
        doc = _read(folder, FILE)
        self.entries: list[dict] = doc["entries"] if doc else []
        self.works: dict = doc["works"] if doc else {}
        self.by_id = {e["id"]: e for e in self.entries}
        features = _read(folder, FEATURES)
        self.features: dict = {f["id"]: f for f in features["features"]} if features else {}
        self.feature_order = list(self.features)
        glosses = _read(folder, GLOSSES)
        self.glosses: dict = glosses["glosses"] if glosses else {}
        root_doc = _read(roots_folder, roots.FILE) if roots_folder else None
        self.roots: dict = {r["id"]: r for r in root_doc["roots"]} if root_doc else {}
        self.variants = defaultdict(list)   # headword id -> ids recorded as its variants
        for e in self.entries:
            if e.get("variant_of"):
                self.variants[e["variant_of"]].append(e["id"])

    def word_link(self, wid: str) -> str:
        entry = self.by_id[wid]
        return link(path(entry), esc(title(entry)))

    def root_cell(self, ps: dict) -> str:
        """The root `proto_semitic` names, linked to its page; ValueError when the root file lacks it."""
        if not self.roots:
            return esc(f"{ps['id']} {ps.get('form', '')}".strip())
        if ps["id"] not in self.roots:
            raise ValueError(f"proto_semitic {ps['id']!r} names no root in {roots.FILE}")
        return link(roots.path(self.roots[ps["id"]]), esc(ps.get("form") or self.roots[ps["id"]]["ps"]))


def page(lex: Lexicon, entry: dict) -> tuple[str, str]:
    works = sorted({s["work"] for s in entry["sources"]})
    comparisons = entry.get("semitic_comparisons", [])
    with_comparisons = f", with {_count(len(comparisons), 'Semitic comparison')}" if comparisons else ""
    fields = {"title": title(entry),
              "desc": (f"Greek {entry['lemma']} ({entry['translit_key']}), in the Pre-Greek lexicon: treated by "
                       f"{_count(len(works), 'work')}{with_comparisons}."),
              "tags": ["pre-greek", "word"], "kind": "pregreek_word", "id": entry["id"]}
    rows = [["Headword", esc(entry["lemma"])], ["Key", esc(entry["key"])],
            ["Transliteration", esc(entry["translit_key"])],
            ["Headword from", esc(BASIS.get(entry["lemma_basis"], entry["lemma_basis"]))]]
    if entry["variants"]:
        rows.append(["Variants", esc(", ".join(entry["variants"]))])
    if entry.get("variant_of"):
        rows.append(["Variant of", lex.word_link(entry["variant_of"])])
    if lex.variants.get(entry["id"]):
        rows.append(["Variants with a record", ", ".join(lex.word_link(v) for v in sorted(lex.variants[entry["id"]]))])
    if entry.get("proto_semitic"):
        rows.append(["Proto-Semitic root", lex.root_cell(entry["proto_semitic"])])
    rows.append(["Review", esc(REVIEW.get(entry["review_status"], entry["review_status"]))])
    body = ["## Word", ""] + table(["Field", "Value"], rows) + [""]
    body += ["## Sources", ""] + table(["Work", "Place", "Section", "Verdict", "Features"],
                                       [_source_row(s, lex.features) for s in entry["sources"]]) + [""]
    if comparisons:
        body += ["## Semitic comparisons", ""] + table(
            ["Language", "Form", "Cited", "Proposer", "Work", "Verdict", "Note"],
            [[_lang(c), _form(c), _cites(c.get("cite", [])), esc(c.get("by", "")),
              _work(c), esc(c["verdict"]), _note(c)] for c in comparisons]) + [""]
        body += [COMPARISONS_NOTE, ""]
    gloss = lex.glosses.get(entry["id"])
    if gloss:
        body += ["## Wiktionary gloss", ""] + table(["Field", "Value"], [
            ["Gloss", esc(gloss["gloss"])], ["Source", esc(gloss["url"])], ["Licence", LICENCE]]) + [""]
        body += [ATTRIBUTION, ""]
    return _page(path(entry), fields, body)


def _ledger(name: str, title_: str, desc: str, body: list[str]) -> tuple[str, str]:
    fields = {"title": title_, "desc": desc, "tags": ["pre-greek", "ledger"], "kind": "ledger"}
    return _page(f"{ROOT}/{name}", fields, body)


def _links(lex: Lexicon, ids) -> str:
    return ", ".join(lex.word_link(i) for i in sorted(set(ids), key=lambda i: lex.by_id[i]["key"]))


def by_feature(lex: Lexicon) -> tuple[str, str]:
    naming, examples = defaultdict(list), defaultdict(list)
    for e in lex.entries:
        for s in e["sources"]:
            for f in s.get("features", []):
                naming[f].append(e["id"])
            if s.get("example_of"):
                examples[s["example_of"]].append(e["id"])
    rows = [[esc(fid), esc(f.get("notation", "")), esc(f["kind"]), esc(f["printed_page"]),
             _links(lex, naming.get(fid, [])), _links(lex, examples.get(fid, []))]
            for fid, f in sorted(lex.features.items(), key=lambda kv: natural(kv[0]))]
    body = [FEATURES_NOTE, ""] + table(["Feature", "Notation", "Kind", "Page", "Words naming it", "Examples"], rows) + [""]
    return _ledger("by_feature", "Pre-Greek features",
                   "Beekes 2014's Pre-Greek features, each with the words whose entry names it and the words its "
                   "section cites as examples.", body)


def semitic(lex: Lexicon) -> tuple[str, str]:
    groups = defaultdict(lambda: defaultdict(list))   # lang -> verdict -> [(entry, comparison)]
    for e in lex.entries:
        for c in e.get("semitic_comparisons", []):
            groups[c["lang"]][c["verdict"]].append((e, c))
    body = [SEMITIC_NOTE, ""]
    for lang in sorted(groups):
        body += [f"## {esc(lang)}", ""]
        for verdict in sorted(groups[lang]):
            pairs = groups[lang][verdict]
            meanings = sorted({f"{c['work']}: {lex.works.get(c['work'], {}).get('verdicts', {})[verdict]}"
                               for _, c in pairs if verdict in lex.works.get(c["work"], {}).get("verdicts", {})})
            body += [f"### {esc(verdict)}", ""]
            if meanings:
                body += [esc("; ".join(meanings)) + ".", ""]
            body += table(["Word", "Form", "Cited", "Proposer", "Work"], [
                [lex.word_link(e["id"]), _form(c) + (f" ({esc(c['variety'])})" if c.get("variety") else ""),
                 _cites(c.get("cite", [])), esc(c.get("by", "")), _work(c)]
                for e, c in sorted(pairs, key=lambda p: (p[0]["key"], p[1]["form"]))]) + [""]
    return _ledger("semitic", "Pre-Greek words with a Semitic comparison",
                   "The Pre-Greek words with a Semitic comparison on record, grouped by language and by the verdict "
                   "of the work that lists each.", body)


def pages(folder: Path, roots_folder: Path | None = None) -> dict[str, str]:
    """Path -> text for every word page and the two ledgers, or nothing when the folder has no lexicon."""
    lex = Lexicon(folder, roots_folder)
    if not lex.entries:
        return {}
    return collect([*(page(lex, e) for e in lex.entries), by_feature(lex), semitic(lex)])


def by_root(folder: Path) -> dict[str, list[tuple[str, str]]]:
    """Root id -> (page path, title) of each word whose `proto_semitic` names it, for the root pages."""
    out = defaultdict(list)
    for e in Lexicon(folder).entries:
        if e.get("proto_semitic"):
            out[e["proto_semitic"]["id"]].append((path(e), title(e)))
    return {k: sorted(v) for k, v in out.items()}


def descs(folder: Path) -> dict[str, str]:
    """The desc of the Pre-Greek folder and of each initial folder the pages fill."""
    entries = Lexicon(folder).entries
    if not entries:
        return {}
    out = {ROOT: ("Greek words classed as Pre-Greek or as early Semitic loans: one generated page per word, filed by "
                  "initial, with the feature and Semitic comparison ledgers.")}
    for e in entries:
        out[f"{ROOT}/{e['key'][0]}"] = f"Pre-Greek words whose key begins with {e['key'][0]}."
    return dict(sorted(out.items()))
