"""The record wiki's Aegean pages: the Eteocretan inscriptions with their word analyses, the Phaistos Disc with a
page per sign, and the Cypro-Minoan catalogue (data/ane/cypro-minoan/) with a page per text and its indexes by site
and object type; it carries no transcription, and a statement in its source's own words shows as a pointer.

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


# ---------------------------------------------------------------- Cypro-Minoan

CM = "wiki/aegean/cypro-minoan"
CM_FIELDS = (("identity", "Identity"), ("museum_no", "Museum number"), ("editions", "Editions"),
             ("findspot", "Findspot"), ("date", "Date"), ("dimensions", "Dimensions"), ("object", "Object"),
             ("document_form", "Document form"), ("hand", "Hand"), ("visual_evidence", "Visual evidence"))
CM_POINTER = "*the source's own words, not reproduced*"
CM_OTHER = "other"
# the key prints "Metal base" for Mvas, so its object decodes to "vas"; the texts under it are bowls (its type note)
CM_OBJECTS = {"vas": "vessel"}


def _cm_catalogue(folder: Path) -> dict | None:
    """The catalogue beside the Linear A folder, in the repository's layout: data/ane/cypro-minoan/."""
    return _read(Path(folder).parent / "ane" / "cypro-minoan", "catalogue.json")


def _cm_path(key: str, r: dict) -> str:
    return f"{CM}/{r['site_code'] or CM_OTHER}/{slug(key)}"


def _cm_where(cites: list[dict]) -> str:
    return "; ".join(c["work"] + (f" ({c['chapter']})" if c.get("chapter") else "")
                     + (f", {c['page']}" if c.get("page") else "") + (f", fig. {c['figure']}" if c.get("figure") else "")
                     + (f", table {c['table']}" if c.get("table") else "") for c in cites)


def _cm_name(key: str, r: dict) -> str:
    return r["siglum"] or key


def _cm_page(key: str, r: dict) -> tuple[str, str]:
    sources, t, e = r["field_sources"], r["hochymin_type"] or {}, r["edition"]
    number = r["corpus_no"] or ("none, outside Valério 2016, Appendix A" if r["witness"] else "none")
    rows = [["## number", esc(number)]]
    if r["site_code"]:
        place = f"{r['site']} ({r['site_code']}{'?' if r['site_queried'] else ''})" if r["site"] else r["site_code"]
        rows.append(["Site", esc("; ".join(filter(None, (place, _cm_where(sources.get("site", []))))))])
    a = r["site_authorities"]
    if a:
        ids = ", ".join(f"{name} {a[k]}" for k, name in (("pleiades", "Pleiades"), ("tm", "Trismegistos")) if a.get(k))
        rows.append(["Identity controls", esc(f"{ids or 'none'} (match: {a['match']})"
                                              + (f"; {a['note']}" if a.get("note") else ""))])
    if t:
        rows.append(["Object type", esc(f"{r['type_code']}, {t['gloss']}; {_cm_where(sources.get('hochymin_type', []))}"
                                        + (f". {t['note']}" if t.get("note") else ""))])
    if r["traditional_subcorpus"]:
        rows.append(["Subcorpus", esc(r["traditional_subcorpus"])])
    rows.append(["Status", esc(_words(r["inclusion_status"] or "outside Appendix A"))])
    if e["of_record"]:
        pages = e["appendix_a_pages"]
        span = (f", Appendix A, {pages[0]}–{pages[-1]}" if len(pages) > 1 else f", Appendix A, {pages[0]}") \
            if pages else ""
        rows.append(["Edition of record", esc(f"{e['of_record']}, transcribed in Valério 2016{span}; "
                                              + ("verified" if e["verified"] else "unverified"))])
    body = ["## Record", ""] + table(["Field", "Value"], rows) + [""]
    if e["of_record"] and not e["verified"] and e.get("verification_note"):
        body += [esc(e["verification_note"]), ""]
    if e.get("edition_note"):
        body += [esc(e["edition_note"]), ""]
    if r["siglum_note"]:
        body += [f"Siglum: {esc(r['siglum_note']['note'])} ({esc(_cm_where(r['siglum_note']['cites']))})", ""]
    if r["siglum_exception"]:  # its reason opens "No siglum: ..."
        x = r["siglum_exception"]
        body += [f"{esc(x['reason'])} ({esc(_cm_where(x['cites']))})", ""]
    if r["witness"]:
        w = r["witness"]
        body += [f"Outside Appendix A: {esc(w['what'])} ({esc(_cm_where(w['cites']))})", ""]
    present = [(field, label) for field, label in CM_FIELDS if r[field]]
    if present:
        body += ["## Metadata", ""]
        for field, label in present:
            body += [f"### {label}", ""] + table(["Statement", "Source", "Note"], [
                [(CM_POINTER if st.get("pointer") else esc(st["text"]))
                 + (esc(f" [{st['basis']}]") if st.get("basis") else "")
                 + (esc(f" (relayed from {st['relayed_from']})") if st.get("relayed_from") else ""),
                 esc(_cm_where(st["cites"])), esc(st.get("note") or "")] for st in r[field]]) + [""]
    missing = [label.lower() for field, label in CM_FIELDS if not r[field]]
    if missing:
        body += ["No held source states its " + ", ".join(missing) + ".", ""]
    body += [("No transcription is reproduced here: Valério 2016, Appendix A transcribes the corpus under terms that "
              "allow private research use only, and the edition row names its pages."), ""]
    what = (t.get("object") or "").strip()
    what = CM_OBJECTS.get(what, what) or "object not decoded"
    place = f", {'perhaps ' if r['site_queried'] else ''}from {r['site']}" if r["site"] else ""
    number = r["corpus_no"] or ("outside Appendix A" if r["witness"] else _cm_name(key, r))
    fields = {"title": _cm_name(key, r),
              "desc": f"Cypro-Minoan text {number}, {what}{place}.",
              "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_text", "id": key,
              "site_code": r["site_code"], "type_code": r["type_code"]}
    return _page(_cm_path(key, r), fields, body)


def _cm_index(path: str, title: str, desc: str, head: list[str], groups: dict, cells) -> tuple[str, str]:
    rows = [[*cells(code, texts), str(len(texts)),
             ", ".join(link(_cm_path(k, r), esc(_cm_name(k, r))) for k, r in sorted(texts, key=lambda kr: natural(kr[0])))]
            for code, texts in sorted(groups.items(), key=lambda g: (g[0] is None, g[0] or ""))]
    fields = {"title": title, "desc": desc, "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"}
    return _page(path, fields, table([*head, "Texts", "Sigla"], rows) + [""])


def cypro_minoan(folder: Path) -> dict[str, str]:
    catalogue = _cm_catalogue(folder)
    if not catalogue:
        return {}
    out = [_cm_page(key, r) for key, r in catalogue.items()]
    sites, types = {}, {}
    for key, r in catalogue.items():
        sites.setdefault(r["site_code"], []).append((key, r))
        types.setdefault(r["type_code"], []).append((key, r))

    def site_cells(code, texts):
        return [code or "(none)", esc(next((r["site"] for _, r in texts if r["site"]), ""))]

    def type_cells(code, texts):
        t = next((r["hochymin_type"] for _, r in texts if r["hochymin_type"]), None) or {}
        return [code or "(none)", esc(t.get("gloss") or ""), esc(t.get("material") or "")]
    out.append(_cm_index(f"{CM}/by_site", "Cypro-Minoan texts by site",
                         "The Cypro-Minoan texts grouped by the site code of their siglum, with the site it decodes to.",
                         ["Code", "Site"], sites, site_cells))
    out.append(_cm_index(f"{CM}/by_type", "Cypro-Minoan texts by object type",
                         "The Cypro-Minoan texts grouped by the HoChyMin type code of their siglum, with its object "
                         "and material.", ["Code", "Object", "Material"], types, type_cells))
    return collect(out)


def descs(folder: Path) -> dict[str, str]:
    """Folder -> the desc its `_index.md` takes when the build makes it."""
    catalogue = _cm_catalogue(folder)
    if not catalogue:
        return {}
    out = {CM: "The Cypro-Minoan texts, one catalogue page per text with its site, object type, edition of record "
               "and the statements of held works with their pages, and the indexes by site and by object type."}
    for r in catalogue.values():
        code = r["site_code"]
        if code:
            place = next((x["site"] for x in catalogue.values() if x["site_code"] == code and x["site"]), None)
            out[f"{CM}/{code}"] = f"The Cypro-Minoan texts of {place}, site code {code}." if place else \
                f"The Cypro-Minoan texts under the site code {code}."
        else:
            out[f"{CM}/{CM_OTHER}"] = ("The Cypro-Minoan texts with no site code, keyed by find name or by another "
                                       "script's siglum.")
    return out


def pages(folder: Path) -> dict[str, str]:
    """Path -> text for every Aegean page the folder's files support."""
    return collect([*eteocretan(Path(folder)).items(), *phaistos(Path(folder)).items(),
                    *cypro_minoan(Path(folder)).items()])
