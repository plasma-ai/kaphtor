"""Every count the wiki prints, computed from the data files: documents, the census classes, complete translations.

A document groups the records that differ only in a side suffix (HT9a/HT9b, GO2r/GO2v, KNWc<24a>/<24b>). HT 154 A–N
are separate fragments in GORILA I, so HT154a…n stay apart, and HT154ja/jb are the two sides of fragment J. Keys
ending `.`, `ter` or `bis` are documents of their own.

The census sorts every document into one class against the published census (GORILA 1,427 + RILA-S1 107), using the
hand-curated sets in `census_classes.json`. The classes are taken in the order of CLASSES, first match wins.
"""
from __future__ import annotations

import collections
import re

SIDE = re.compile(r"^(.*\d)([a-h]|r|v)$")
FRAGMENT_SIDE = re.compile(r"^(HT154[a-n])([ab])$")
SLOT_SIDE = re.compile(r"^(.*<\d+)[a-h]>$")

CLASSES = (
    "outside the Linear A area", "RILA-S1 accepted", "RILA-S1 doubtful", "RILA-S1 listed, not counted",
    "published after 2023", "outside both editions", "GORILA, labelled", "GORILA, unlabelled", "unresolved",
)
DOCUMENT_SETS = ("published_after_2023", "outside_editions", "gorila_unlabelled", "unresolved")


def doc_id(key: str) -> str:
    """The document a corpus key belongs to."""
    if key.startswith("HT154"):
        m = FRAGMENT_SIDE.match(key)
        return m.group(1) if m else key
    m = SLOT_SIDE.match(key)
    if m:
        return m.group(1) + ">"
    m = SIDE.match(key)
    return m.group(1) if m else key


def documents(corpus: dict) -> dict[str, list[str]]:
    """Document id -> its corpus keys, in corpus order."""
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for key in corpus:
        groups[doc_id(key)].append(key)
    return dict(groups)


def _rila_keys(table: dict) -> set[str]:
    return {k for value in table.values() for k in (value["keys"] if isinstance(value, dict) else value)}


def classify(corpus: dict, classes: dict) -> dict[str, str]:
    """Document id -> census class. ValueError if the class file does not fit the corpus or a document fits no class."""
    groups = documents(corpus)
    accepted = _rila_keys(classes["rila_s1_accepted"])
    doubtful = _rila_keys(classes["rila_s1_doubtful"])
    listed = _rila_keys(classes["rila_s1_listed_not_counted"])
    missing = sorted((accepted | doubtful | listed) - set(corpus))
    if missing:
        raise ValueError(f"RILA-S1 keys not in the corpus: {missing}")
    sets = {name: set(classes[name]) for name in DOCUMENT_SETS}
    for i, a in enumerate(DOCUMENT_SETS):
        not_documents = sorted(sets[a] - set(groups))
        if not_documents:
            raise ValueError(f"{a}: not documents of the corpus: {not_documents}")
        for b in DOCUMENT_SETS[i + 1:]:
            if sets[a] & sets[b]:
                raise ValueError(f"{a} and {b} share {sorted(sets[a] & sets[b])}")
    for drop, keeper in classes["merged"].items():
        if drop in corpus or doc_id(keeper) not in groups:
            raise ValueError(f"merged record {drop} -> {keeper}: the second record is still held, or its keeper is not")
    outside_sites = set(classes["outside_area_sites"])

    def klass(document: str, keys: list[str]) -> str:
        if any(corpus[k].get("site") in outside_sites for k in keys):
            return "outside the Linear A area"
        for name, held in (("RILA-S1 accepted", accepted), ("RILA-S1 doubtful", doubtful),
                           ("RILA-S1 listed, not counted", listed)):
            if any(k in held for k in keys):
                return name
        if document in sets["published_after_2023"]:
            return "published after 2023"
        if document in sets["outside_editions"]:
            return "outside both editions"
        if any(corpus[k].get("source_provenance") == "GORILA" for k in keys):
            return "GORILA, labelled"
        if document in sets["gorila_unlabelled"]:
            return "GORILA, unlabelled"
        if document in sets["unresolved"]:
            return "unresolved"
        raise ValueError(f"document {document} ({', '.join(keys)}) fits no census class")

    return {document: klass(document, keys) for document, keys in groups.items()}


def census(corpus: dict, classes: dict) -> collections.Counter:
    """Documents per census class."""
    return collections.Counter(classify(corpus, classes).values())


def is_complete(entry: dict) -> bool:
    """A translation counts as complete when it has text and its status is not "incomplete"."""
    text = entry.get("translation") or entry.get("composite_translation") or ""
    return bool(str(text).strip()) and entry.get("status") != "incomplete"


def translation_counts(translations: dict) -> tuple[int, int]:
    """(complete, incomplete) over the `translations` sub-dict of translations.json."""
    complete = sum(1 for entry in translations.values() if is_complete(entry))
    return complete, len(translations) - complete
