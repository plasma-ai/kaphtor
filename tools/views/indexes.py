"""Descs for the folders the builder fills: an inscription site, its series, and a word's first sign.

`wiki update` owns every `_index.md`. The builder writes one key of it, `desc`, and only where the index has none or
still holds `wiki update`'s placeholder, so a desc someone wrote is never replaced. A desc written once is never
refreshed, so none holds a count. Site names come from the records' `site` field (the most common, when a folder
holds more than one), never from the siglum alone; a name ending in "(?)" reads as a doubtful attribution.
`overrides.json` can give a folder its desc by hand; an override whose folder the data does not fill is left out.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from .model import OVERRIDES, Model, series, sign_parts, word_path
from .render import doc_keys

PLACEHOLDER = "..."  # the desc `wiki update` gives a new index
INSCRIPTIONS = "wiki/linear-a/inscriptions"


def _site(model: Model, key: str) -> str:
    rec = model.corpus.get(key) or (model.translations.get(key) or {}).get("raw") or {}
    return rec.get("site") or ""


def _from(names: Counter, siglum: str) -> str:
    """"from Haghia Triada", or "doubtfully attributed to Kophinas" for `Kophinas(?)`."""
    named = Counter({n: c for n, c in names.items() if n})
    name = min(named, key=lambda n: (-named[n], n)) if named else siglum
    if name.endswith("(?)"):
        return f"doubtfully attributed to {name.removesuffix('(?)').strip()}"
    return f"from {name}"


def descs(model: Model) -> dict[str, str]:
    """Folder (as a page path, `wiki/…`) -> desc, for every folder above a word or inscription page."""
    out: dict[str, str] = {}
    sites: dict[str, Counter] = defaultdict(Counter)
    sers: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for key in doc_keys(model):
        site, ser = series(key)
        sites[site][_site(model, key)] += 1
        if ser:
            sers[(site, ser)][_site(model, key)] += 1
    for site, names in sites.items():
        out[f"{INSCRIPTIONS}/{site}"] = f"Inscriptions {_from(names, site)}."
    for (site, ser), names in sers.items():
        place = _from(names, site)
        out[f"{INSCRIPTIONS}/{site}/{ser}"] = (f"Inscriptions {place}, filed outside a series." if ser == "misc"
                                               else f"Inscriptions {place}, series {ser}.")
    firsts: dict[str, Counter] = defaultdict(Counter)
    for form in model.forms():
        parts = sign_parts(form)
        firsts[word_path(form).rsplit("/", 1)[0]][parts[0] if parts else ""] += 1
    for folder, signs in firsts.items():
        letter = folder.rsplit("/", 1)[1]
        if letter == "star":
            example = min(signs, key=lambda s: (-signs[s], s))
            out[folder] = f"Words that open with a sign known by its number, such as {example}."
            continue
        illegible = any(not s.upper().startswith(letter) for s in signs)
        out[folder] = (f"Words whose first sign begins with {letter}"
                       + (", and words that open with an illegible sign." if illegible else "."))
    out.update((folder, desc) for folder, desc in OVERRIDES.get("descs", {}).items() if folder in out)
    return dict(sorted(out.items()))
