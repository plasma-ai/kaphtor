"""The Linear A records as the wiki reads them: loaded from a data folder, translations normalized, page paths and
sign status worked out, and the reverse indexes built. Read-only.

Page paths start at the kaphtor root and carry no extension; file names are ASCII identifiers, and the page's title
keeps the original form.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..paths import require
from . import counts

# Translation word items: each normalized field, and the item keys that may supply it (one at most).
ITEM_ALIASES = {"form": ("linear_a",), "gloss": ("gloss", "meaning", "translation"), "note": ("note", "notes")}
ITEM_KEYS = {"reading", "confidence", "reading_type", "root", "layer", "position", "quantity", "confidence_score",
             "dialect_variant_of", "resolved", "morphology", "isogloss", "sigla_contested", "sigla_note"}

# resolution_summary's kinds -> the wiki's sign folders.
SIGN_KINDS = {"phonemic": "syllabic", "logograms": "logograms", "fractions": "fractions"}
LABEL = re.compile(r"[A-Z][A-Z_]{2,}:")  # evidence that opens "STRONG:" carries a verdict, which is never shown
LINEAR_B_SYLLABLE = re.compile(r"[a-z]+[₀-₉]*")  # pa, ra₂; not "talent (L)"

OVERRIDES = json.loads(Path(__file__).with_name("overrides.json").read_text(encoding="utf-8"))

SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
SERIES = re.compile(r"([A-Z]+?)(?:\(\?\))?((?:W|Z)[a-z]?)?(?=[0-9<(]|$)")


def natural(key: str) -> list:
    """Sort key that orders HT2 before HT10."""
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", key)]


# ---------------------------------------------------------------- slugs and paths

def slug(form: str) -> str:
    """An ASCII identifier for a form or key: subscripts become digits, marks drop, `*` reads `star`, `+` reads
    `_plus_`, and a damage bracket at either end becomes a suffix, so `]KU-ME-TA` and `KU-ME-TA` stay apart.
    `overrides.json` can name a file outright."""
    if form in OVERRIDES["slugs"]:
        return OVERRIDES["slugs"][form]
    s = unicodedata.normalize("NFC", form).translate(SUBSCRIPTS)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    start, end = s[:1] in "[]" and s != "", s[-1:] in "[]" and s != ""
    s = s.strip("[]")
    s = s.replace("[?]", "_q_").replace("(?)", "_q_").replace("?", "_q").replace("…", "_etc_")
    s = s.replace("*", "star").replace("+", "_plus_")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    if start and end:
        s += "_broken_both"
    elif start:
        s += "_broken_start"
    elif end:
        s += "_broken_end"
    if not s or s[0].isdigit():
        s = "n_" + s
    return s


def word_path(form: str) -> str:
    name = slug(form)
    shard = "star" if name.startswith("star") else name[0].upper()
    return f"wiki/linear-a/words/{shard}/{name}"


def series(key: str) -> tuple[str, str]:
    """(site, GORILA series) of a corpus key: HTWa1146 -> (HT, HTWa); `overrides.json` places the keys the pattern
    cannot read, and any other goes to misc."""
    if key in OVERRIDES["series"]:
        site, ser = OVERRIDES["series"][key]
        return site, ser
    m = SERIES.match(key)
    if m:
        return m.group(1), m.group(1) + (m.group(2) or "")
    m = re.match(r"[A-Z]+", key)
    return (m.group(0) if m else "misc"), "misc"


def doc_path(key: str) -> str:
    """The page of a corpus key; an override with an empty series files the key directly under its site."""
    site, ser = series(key)
    return f"wiki/linear-a/inscriptions/{site}/" + (f"{ser}/" if ser else "") + slug(key)


def sign_path(kind: str, key: str) -> str:
    if kind not in SIGN_KINDS.values():
        raise ValueError(f"unknown sign kind {kind!r}")
    return f"wiki/linear-a/signs/{kind}/{slug(key)}"


# ---------------------------------------------------------------- translations

def _item(doc: str, item: dict) -> dict:
    out: dict = {}
    used: set[str] = set()
    for name, keys in ITEM_ALIASES.items():
        present = [k for k in keys if k in item]
        if len(present) > 1:
            raise ValueError(f"{doc}: word item {item.get('linear_a')!r} has both {present}")
        out[name] = item[present[0]] if present else None
        used.update(present)
    unknown = sorted(set(item) - used - ITEM_KEYS)
    if unknown:
        raise ValueError(f"{doc}: word item {item.get('linear_a')!r} has unknown keys {unknown}")
    out.update((k, item[k]) for k in sorted(ITEM_KEYS) if k in item)
    out.setdefault("reading", None)
    out.setdefault("confidence", None)
    return out


def normalize_translation(doc: str, entry: dict) -> dict:
    """One translations.json entry in one shape, from either schema: the list of word items keyed `linear_a`, or the
    dict keyed by form. `status` is the raw value; `complete` follows the count rule. ValueError on an unknown item
    key, or on two keys for one field."""
    words = entry.get("words") or []
    if isinstance(words, dict):
        words = [{**value, "linear_a": form} for form, value in words.items()]
    return {
        "id": doc,
        "text": entry.get("translation") or entry.get("composite_translation") or "",
        "status": entry.get("status"),
        "complete": counts.is_complete(entry),
        "confidence": entry.get("confidence"),
        "source": entry.get("source"),
        "notes": entry.get("notes") or "",
        "words": [_item(doc, item) for item in words],
        "raw": entry,
    }


# ---------------------------------------------------------------- signs

def sign_records(sign_values: dict) -> dict[str, dict]:
    """Wiki kind -> {key: record}; pseudo-records such as `_note` are left out."""
    return {
        "syllabic": dict(sign_values["signs"]),
        "logograms": {k: v for k, v in sign_values["logograms"].items() if not k.startswith("_")},
        "fractions": dict(sign_values["fractions"]["signs"]),
    }


def sign_parts(form: str) -> list[str]:
    """The signs a form is written with, as written and without damage brackets: `]KU-PA₃-NU` -> KU, PA₃, NU."""
    return [p.strip("[]") for p in re.split(r"[-+ ]", form) if p.strip("[]")]


def sign_keys(records: dict) -> dict[str, str]:
    """Record key by its spelling with subscripts read as digits, so a form's `TA₂` finds the record `TA2` and `PA3`
    finds `PA₃`. ValueError when two keys differ only so."""
    out: dict[str, str] = {}
    for key in records:
        folded = key.translate(SUBSCRIPTS)
        if folded in out:
            raise ValueError(f"sign keys {out[folded]!r} and {key!r} differ only in subscripts")
        out[folded] = key
    return out


def sign_status(sign_values: dict) -> dict[tuple[str, str], tuple[str, str]]:
    """(kind, key) -> (status, evidence), from resolution_summary alone; record fields are not read for status.

    resolved: in the summary's resolved lists. proposed: in its proposed lists, with its evidence if any.
    conventional: a syllabic sign whose Linear B counterpart has a syllabic value, and no other status. speculative:
    any other value held in its record. ValueError on evidence that opens with a label such as "STRONG:".
    """
    summary = sign_values["resolution_summary"]
    status: dict[tuple[str, str], tuple[str, str]] = {}
    for kind, folder in SIGN_KINDS.items():
        for entry in summary.get(kind, []):
            status.setdefault((folder, entry.split("=", 1)[0]), ("resolved", ""))
        for proposal in summary["proposed"].get(kind, []):
            key, evidence = proposal["entry"].split("=", 1)[0], proposal.get("evidence") or ""
            if LABEL.match(evidence):
                raise ValueError(f"{key}: evidence opens with a label: {evidence[:40]!r}")
            status.setdefault((folder, key), ("proposed", evidence))
    for folder, records in sign_records(sign_values).items():
        for key, record in records.items():
            value = (record.get("linear_b") or {}).get("value") or ""
            conventional = folder == "syllabic" and bool(LINEAR_B_SYLLABLE.fullmatch(value))
            status.setdefault((folder, key), ("conventional", "") if conventional else ("speculative", ""))
    return status


# ---------------------------------------------------------------- the loaded model

def _read(folder: Path, name: str):
    return json.loads(require(folder / name, name).read_text(encoding="utf-8"))


def attestation_base(attestation: str, corpus: dict) -> str:
    """The corpus key of an attestation: `HT27a(*307)` -> `HT27a`."""
    return attestation if attestation in corpus else attestation.split("(", 1)[0]


@dataclass
class Model:
    corpus: dict
    lexicon: dict[str, dict]
    onomasticon: dict[str, dict]
    unread: dict[str, dict]
    unread_statuses: dict[str, str]
    translations: dict[str, dict]
    sign_values: dict
    census_classes: dict
    sign_status: dict = field(default_factory=dict)
    attested_in: dict = field(default_factory=dict)       # corpus key -> lexicon forms citing it
    in_translations: dict = field(default_factory=dict)   # form -> [(translation id, normalized item)]

    def forms(self) -> list[str]:
        """Every form with a word page: lexicon, onomasticon and unread words together."""
        return sorted(set(self.lexicon) | set(self.onomasticon) | set(self.unread), key=natural)


def load(folder: Path) -> Model:
    """Read the Linear A data files in `folder` and build the indexes."""
    folder = Path(folder)
    unread = _read(folder, "unread_words.json")
    sign_values = _read(folder, "sign_values.json")
    model = Model(
        corpus=_read(folder, "corpus.json"),
        lexicon={e["word"]: e for e in _read(folder, "lexicon.json")["entries"]},
        onomasticon={o["token"]: o for o in _read(folder, "onomasticon.json")["entries"]},
        unread={u["word"]: u for u in unread["entries"]},
        unread_statuses=unread.get("statuses", {}),
        translations={doc: normalize_translation(doc, entry)
                      for doc, entry in _read(folder, "translations.json")["translations"].items()},
        sign_values=sign_values,
        census_classes=_read(folder, "census_classes.json"),
        sign_status=sign_status(sign_values),
    )
    attested_in = defaultdict(set)
    for form, entry in model.lexicon.items():
        for attestation in entry.get("attestations") or []:
            attested_in[attestation_base(attestation, model.corpus)].add(form)
    model.attested_in = {k: sorted(v, key=natural) for k, v in attested_in.items()}
    in_translations = defaultdict(list)
    for doc in sorted(model.translations, key=natural):
        for item in model.translations[doc]["words"]:
            in_translations[item["form"]].append((doc, item))
    model.in_translations = dict(in_translations)
    return model
