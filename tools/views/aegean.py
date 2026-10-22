"""The record wiki's Aegean pages: the Eteocretan inscriptions with their word analyses, and the Phaistos Disc with a
page per sign.

Each set is optional: a data folder without its files gets no pages. Transcriptions go in code blocks, since a
combining dot after `|` would attach to a table pipe. The disc's readings are EXPLORATORY, below the decipherment's
tiers, and say so. Process fields (`campaign_*`) and the files' own metadata (authors, versions, dates of editing)
are not rendered.
"""
from __future__ import annotations

import json
from pathlib import Path

from .markdown import escape as esc
from .markdown import link, table
from .model import natural, slug
from .render import _page, _words, collect

# relationship_to_linear_a -> (the desc's name, the tag) of the control texts the Eteocretan file also holds.
CONTROLS = {"eteocypriote_control_only": ("Eteocypriot control", "eteocypriot")}
DISC_FIELDS = (("Site", "site"), ("Date", "date_range"), ("Other dates", "date_range_alternatives"),
               ("Material", "material"), ("Diameter (cm)", "dimensions_cm"), ("Technique", "technique"),
               ("Reading direction", "reading_direction"), ("Within a group", "within_group_direction"),
               ("Found", "discovery"), ("Held at", "current_location"), ("Signs", "total_signs"),
               ("Sign occurrences", "total_occurrences"), ("Groups", "group_count"), ("Licence", "data_license"))


def _read(folder: Path, name: str):
    path = folder / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _value(value) -> str:
    if isinstance(value, (str, int, float)):
        return esc(value)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return esc("; ".join(value))
    if isinstance(value, dict) and all(isinstance(v, (str, int, float)) for v in value.values()):
        return esc("; ".join(f"{_words(k)} {v}" for k, v in value.items()))
    return esc(json.dumps(value, ensure_ascii=False))


# ---------------------------------------------------------------- Eteocretan

def eteocretan(folder: Path) -> dict[str, str]:
    inscriptions = _read(folder, "eteocretan_inscriptions.json")
    if not inscriptions:
        return {}
    analyses = (_read(folder, "eteocretan_word_analysis.json") or {}).get("words", [])
    out = []
    for r in inscriptions["inscriptions"]:
        path = f"wiki/aegean/eteocretan/{slug(r['id'])}"
        status = r.get("status") or ""
        name, tag = CONTROLS.get(r.get("relationship_to_linear_a"), ("Eteocretan", "eteocretan"))
        fields = {"title": r.get("common_name") or r["id"],
                  "desc": f"{name} inscription, {r.get('site')}, {r.get('date')}; {_words(status).lower()}.",
                  "tags": ["aegean", tag, status.lower()], "kind": "eteocretan_inscription", "id": r["id"],
                  "site": r.get("site"), "status": status}
        rows = [[name, esc(r.get(key) or "")] for name, key in (
            ("Site", "site"), ("Object", "object_type"), ("Date", "date"), ("Script", "script"),
            ("Direction", "direction"), ("Relation to Linear A", "relationship_to_linear_a"), ("Status", "status"))]
        body = ["## Record", ""] + table(["Field", "Value"], rows) + [""]
        body += ["## Text", "", "```text", *(r.get("current_transliteration") or []), "```", ""]
        if r.get("greek_parallel_text"):
            body += ["Greek: " + esc(r["greek_parallel_text"]), ""]
        if r.get("gordon_transliteration"):
            body += ["Gordon's transliteration:", "", "```text", *r["gordon_transliteration"], "```", ""]
        readings = r.get("gordon_word_readings") or []
        if readings:
            body += ["## Gordon's readings", ""] + table(["Form", "Meaning", "Basis", "Constraint"], [
                [esc(w.get("form") or ""), esc(w.get("meaning") or ""), esc(w.get("basis") or ""),
                 esc(w.get("constraint") or "")] for w in readings]) + [""]
        words = [w for w in analyses if w.get("inscription_id") == r["id"]]
        if words:
            body += ["## Word analysis", ""] + table(["Form", "Gordon's meaning", "Root", "Basis", "Constraint",
                                                      "Status"], [
                [esc(w.get("form") or ""), esc(w.get("gordon_meaning") or ""), esc(w.get("root") or ""),
                 esc(w.get("basis") or ""), esc(w.get("constraint_type") or ""), esc(w.get("status") or "")]
                for w in words]) + [""]
        if r.get("source_refs"):
            body += ["## Sources", ""] + [f"- {esc(s)}" for s in r["source_refs"]] + [""]
        out.append(_page(path, fields, body))
    return collect(out)


# ---------------------------------------------------------------- Phaistos Disc

def sign_name(key: str, sign: dict) -> str:
    return f"PD{sign['number']:02d}" if isinstance(sign.get("number"), int) else slug(key)


def _sign_link(number: int, names: dict[int, str]) -> str:
    return link(f"wiki/aegean/phaistos_disc/signs/{names[number]}", str(number)) if number in names else str(number)


def phaistos(folder: Path) -> dict[str, str]:
    disc = _read(folder, "phaistos_disc.json")
    if not disc:
        return {}
    bridge = {b["pd_sign"]: b for b in (_read(folder, "phaistos_disc_sign_map.json") or {}).get("sign_bridge", [])
              if isinstance(b.get("pd_sign"), int)}
    signs = disc.get("signs") or {}
    names = {s["number"]: sign_name(k, s) for k, s in signs.items() if isinstance(s.get("number"), int)}
    groups = [g for side in ("side_A", "side_B") for g in (disc.get("transcription") or {}).get(side, [])]
    meta = disc.get("metadata") or {}
    out = []

    rows = [[name, _value(meta[key])] for name, key in DISC_FIELDS if meta.get(key) not in (None, "", [], {})]
    body = ["## Record", ""] + table(["Field", "Value"], rows) + [""]
    body += ["## Groups", "", ("The partial readings are EXPLORATORY: below the decipherment's confidence tiers, read "
                               "through the Phaistos and Linear A sign correspondences given, with their sources, on "
                               "each sign page."), ""]
    body += table(["Group", "Signs", "Oblique stroke", "Partial reading", "Coverage", "Confidence"], [
        [esc(g["group"]), " ".join(_sign_link(n, names) for n in g.get("signs") or []),
         "yes" if g.get("has_oblique_stroke") else "",
         esc((g.get("proposed_readings") or {}).get("partial_transliteration") or ""),
         f"{(g.get('proposed_readings') or {}).get('coverage_pct', 0)}%",
         esc((g.get("proposed_readings") or {}).get("confidence") or "")] for g in groups]) + [""]
    fields = {"title": "Phaistos Disc", "desc": f"The Phaistos Disc: {len(groups)} sign groups, readings EXPLORATORY.",
              "tags": ["aegean", "phaistos-disc"], "kind": "phaistos_disc"}
    out.append(_page("wiki/aegean/phaistos_disc/disc", fields, body))

    for key in sorted(signs, key=natural):
        sign = signs[key]
        name = sign_name(key, sign)
        number = sign.get("number")
        corr, b = sign.get("la_correspondence") or {}, bridge.get(number) or {}
        fields = {"title": f"PD {number}" if isinstance(number, int) else _words(key),
                  "desc": f"Phaistos Disc sign {number if isinstance(number, int) else _words(key)}, "
                          f"{(sign.get('name') or '').lower()}.",
                  "tags": ["aegean", "phaistos-disc", "sign"], "kind": "phaistos_sign", "sign": key,
                  "sign_number": number}
        unicode = str(sign.get("unicode", ""))
        glyph = chr(int(unicode[2:], 16)) if unicode.startswith("U+") else ""  # noqa: FURB166 (the prefix is "U+")
        rows = [["Name", esc(sign.get("name") or "")], ["Description", esc(sign.get("description") or "")],
                ["Unicode", esc(sign.get("unicode") or "")]]
        body = ["## Sign", ""] + table(["Field", "Value"], rows) + [""]
        if glyph:
            body += ["```text", glyph, "```", ""]
        bridge_rows = [[label, esc(value)] for label, value in (
            ("Linear A sign", corr.get("la_sign") or b.get("la_correspondent")),
            ("Linear A value", corr.get("la_value") or b.get("la_phonetic_value")),
            ("Cretan Hieroglyphic", corr.get("ch_intermediary") or b.get("ch_correspondent")),
            ("Confidence", corr.get("bridge_confidence") or b.get("bridge_confidence")),
            ("Basis", corr.get("bridge_basis") or b.get("bridge_basis"))) if value]
        if bridge_rows:
            body += ["## Bridge to Linear A", ""] + table(["Field", "Value"], bridge_rows) + [""]
        alternatives = corr.get("alternative_readings") or b.get("alternative_readings") or []
        if alternatives:
            body += ["### Other readings", ""] + table(["Source", "Value", "Basis"], [
                [esc(a.get("source") or ""), esc(a.get("value") or ""), esc(a.get("basis") or "")]
                for a in alternatives]) + [""]
        found = [g["group"] for g in groups if number in (g.get("signs") or [])]
        if found:
            body += ["## Groups", "", f"In {len(found)} group(s): " + ", ".join(esc(g) for g in found) + ".", ""]
        out.append(_page(f"wiki/aegean/phaistos_disc/signs/{name}", fields, body))
    return collect(out)


def pages(folder: Path) -> dict[str, str]:
    """Path -> text for every Aegean page the folder's files support."""
    return collect([*eteocretan(Path(folder)).items(), *phaistos(Path(folder)).items()])
