"""The record wiki's Aegean pages: the Eteocretan inscriptions with their word analyses, the Phaistos Disc with a
page per sign, and the Cypro-Minoan catalogue (data/ane/cypro-minoan/) with a page per text and its indexes by site
and object type; it carries no transcription, and a statement in its source's own words shows as a pointer. A
translated text's page (translations.json) adds the reading word by word, with the sign group, line and Appendix A
page of each word read and no group for a word left unread, and an index lists the texts translated. Analytical
indexes render the read-word grammar hypotheses (grammar.md), lexicon (lexicon.md), onomasticon (onomasticon.md), and
72-sign aggregate syllabary grid (grid.md).

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


def _cm_translations(folder: Path) -> dict:
    """The translated texts beside the catalogue, keyed by siglum; none without the file."""
    return (_read(Path(folder).parent / "ane" / "cypro-minoan", "translations.json") or {}).get("translations") or {}


def _cm_file(folder: Path, name: str) -> dict | None:
    """Read an optional Cypro-Minoan analytical JSON file beside catalogue.json."""
    return _read(Path(folder).parent / "ane" / "cypro-minoan", name)


def _cm_grammar_page(grammar: dict, catalogue: dict) -> tuple[str, str]:
    hyps = grammar.get("hypotheses") or []
    rows = []
    for h in hyps:
        sigs = []
        seen: set[str] = set()
        for ev in h.get("structural_evidence") or []:
            s = ev.get("siglum")
            if s and s not in seen:
                seen.add(s)
                sigs.append(link(_cm_path(s, catalogue[s]), esc(_cm_name(s, catalogue[s]))) if s in catalogue else esc(s))
        rows.append([
            esc(h["id"]),
            esc(h["area"]),
            esc(h["tier"]),
            esc(h["text_basis"]),
            esc(h["label"]),
            ", ".join(sigs),
            esc(h["proposed_function"]),
        ])
    body = [
        (f"{len(hyps)} tiered Cypro-Minoan grammatical, morphological, syntactic, phonological, orthographic, and "
         "subcorpus-isogloss hypotheses attested exclusively by ruled signs (T5 compliant; unvalued-sign hypotheses "
         "stay outside this repository). Strictly isolated from Linear A."),
        "",
        *table(["ID", "Area", "Tier", "Text basis", "Hypothesis", "Key texts", "Proposed function"], rows),
        "",
    ]
    return _page(f"{CM}/grammar", {
        "title": "Cypro-Minoan grammar hypotheses",
        "desc": "Tiered, falsifiable Cypro-Minoan morphological, syntactic, phonological, and orthographic hypotheses.",
        "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"}, body)


def _cm_lexicon_page(lexicon: dict, catalogue: dict) -> tuple[str, str]:
    entries = lexicon.get("entries") or []
    stems = [e for e in entries if e["entry_kind"] == "paradigm_stem"]
    lexical = [e for e in entries if e["entry_kind"] == "lexical"]
    names = [e for e in entries if e["entry_kind"] == "name_ref"]
    phonetic = [e for e in entries if e["entry_kind"] == "phonetic_entry"]

    def _att_links(atts: list[dict]) -> str:
        out_s: list[str] = []
        seen: set[str] = set()
        for a in atts:
            s = a.get("siglum")
            if s and s not in seen:
                seen.add(s)
                out_s.append(link(_cm_path(s, catalogue[s]), esc(_cm_name(s, catalogue[s]))) if s in catalogue else esc(s))
        return ", ".join(out_s[:4]) + (f" (+{len(out_s) - 4})" if len(out_s) > 4 else "")

    body = [
        (f"Language-neutral Cypro-Minoan lexicon covering {len(entries)} entries built exclusively from ruled signs: "
         f"{len(stems)} paradigm stems (`gloss: null` permitted), {len(lexical)} curated lexical entries, "
         f"{len(names)} onomastic references (see {link(f'{CM}/onomasticon', 'Cypro-Minoan onomasticon')}), "
         f"and {len(phonetic)} phonetic-only word types. Strictly isolated from Linear A."),
        "",
        "## Paradigm stems",
        "",
        *table(
            ["Stem", "Values", "Tier", "Affiliation", "Members", "Grammar refs", "Texts"],
            [[esc(e["reading"]), esc(e["values"]), esc(e["tier"] or ""), esc(e["language_affiliation"]),
              esc(", ".join(m["reading"] for m in e["paradigm_members"])),
              esc(", ".join(e["grammar_hypothesis_refs"])), _att_links(e["attestations"])] for e in stems],
        ),
        "",
        "## Curated lexical entries",
        "",
        *table(
            ["Reading", "Group", "Values", "Tier", "Affiliation", "Gloss", "Texts"],
            [[esc(e["reading"]), esc(e["cypro_minoan"]), esc(e["values"]), esc(e["tier"] or ""),
              esc(e["language_affiliation"]), esc(e["gloss"] or ""), _att_links(e["attestations"])] for e in lexical],
        ),
        "",
    ]
    return _page(f"{CM}/lexicon", {
        "title": "Cypro-Minoan lexicon",
        "desc": "Language-neutral Cypro-Minoan lexicon covering paradigm stems, curated lexical items, onomastic links, and read word types.",
        "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"}, body)


def _cm_onomasticon_page(onom: dict, lexicon: dict) -> tuple[str, str]:
    lex_by_id = {e["entry_id"]: e for e in (lexicon.get("entries") or [])}
    entries = onom.get("entries") or []
    rows = []
    for o in entries:
        le = lex_by_id.get(o["lexicon_ref"]) or {}
        rows.append([
            esc(o["normalized_name"]),
            esc(le.get("cypro_minoan") or ""),
            esc(le.get("values") or ""),
            esc(o["name_type"]),
            esc(o["language_affiliation"]),
            esc(", ".join(o["attestation_sites"])),
            esc(o["syntax_context"]),
            esc(o["caveats"]),
        ])
    body = [
        (f"Non-duplicating Cypro-Minoan onomasticon overlay ({len(entries)} names linked 1-to-1 to "
         f"{link(f'{CM}/lexicon', 'Cypro-Minoan lexicon')}), separating CM 3 Ugarit prosopography (`RASH Atab 004`) "
         "from Cyprus CM 1 clay balls, vessels, seals, cylinders, and CM 2 candidates."),
        "",
        *table(["Name", "Group", "Values", "Type", "Affiliation", "Sites", "Syntax context", "Caveats"], rows),
        "",
    ]
    return _page(f"{CM}/onomasticon", {
        "title": "Cypro-Minoan onomasticon",
        "desc": "Cypro-Minoan personal names, patronymics, gentilics, and toponym candidates linked 1-to-1 to the lexicon.",
        "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"}, body)


def _cm_grid_page(grid: dict) -> tuple[str, str]:
    sub_rows = []
    for sub, info in sorted((grid.get("subcorpus_grids") or {}).items()):
        filled = info.get("filled_cells") or {}
        empty = info.get("empty_cells") or []
        sub_rows.append([esc(sub), str(info.get("attested_ruled_signs", 0)), str(len(filled)),
                         str(len(empty)), esc(", ".join(empty))])
    allo_rows = [
        [esc(a["value"]), esc(", ".join(a["cm1_signs"])), esc(", ".join(a["cm2_signs"])),
         esc(", ".join(a["cm3_signs"])), esc(a["split_evidence"])]
        for a in (grid.get("allograph_pairs") or [])
    ]
    body = [
        f"Aggregate Cypro-Minoan syllabary coverage: **{grid['ruled_sign_count']} ruled signs** and "
        f"**{grid['unvalued_sign_count']} unvalued signs** (`{len(grid.get('global_empty_cells') or [])}` global "
        "empty `C x V` cells: " + esc(", ".join(grid.get("global_empty_cells") or [])) + "). "
        "Unvalued sign sequences stay outside this repository under T5.",
        "",
        "## Subcorpus grid coverage",
        "",
        *table(["Subcorpus", "Ruled signs", "Filled cells", "Empty cells", "Empty cell list"], sub_rows),
        "",
        "## Regional allograph splits",
        "",
        *table(["Value", "CM 1", "CM 2", "CM 3", "Split evidence"], allo_rows),
        "",
    ]
    return _page(f"{CM}/grid", {
        "title": "Cypro-Minoan syllabary grid",
        "desc": "Aggregate Cypro-Minoan C x V grid coverage across CM 1–3, global empty cells, and regional allograph pairs.",
        "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"}, body)


def _cm_rival(v: dict) -> str:
    """A rival of a word left unread ships without its reading, which would spell the group."""
    return (f"{v['proposer']}" + (f", {v['reading']}" if v.get("reading") else "")
            + (f", {v['gloss']}" if v.get("gloss") else "")
            + f" ({v['work']}, {v['page']})" + (f" [{v['note']}]" if v.get("note") else ""))


def _cm_reading(rec: dict) -> list[str]:
    """The Translation section: the translation, its source, tier and state, a row per word, then the notes."""
    words = rec["words"]
    rows = []
    for w in words:
        kind = ", ".join(filter(None, (w["reading_type"] and w["reading_type"].lower(), w["confidence"],
                                       "emended text" if w["text"] == "emended" else None)))
        rows.append([esc(w["line"] or ""), esc(w["page"]), esc(w["cypro_minoan"]) if w["cypro_minoan"] else "*not reproduced*",
                     esc("-".join(v or "?" for v in w["values"])), esc(w["reading"] or ""), esc(w["gloss"] or ""),
                     esc(kind), esc("; ".join(_cm_rival(v) for v in w["rivals"])), esc(w["note"] or "")])
    state = f"{rec['source']}'s reading, {rec['confidence']}, {rec['status'] or 'complete'}; {len(words)} words."
    body = ["## Translation", "", esc(rec["translation"]), "", esc(state), ""]
    body += table(["Line", "Page", "Group", "Values", "Reading", "Gloss", "Tier", "Rivals", "Note"], rows) + [""]
    for paragraph in (rec.get("notes") or "").split("\n\n"):
        body += [esc(paragraph), ""] if paragraph else []
    return body


def _cm_path(key: str, r: dict) -> str:
    return f"{CM}/{r['site_code'] or CM_OTHER}/{slug(key)}"


def _cm_where(cites: list[dict]) -> str:
    return "; ".join(c["work"] + (f" ({c['chapter']})" if c.get("chapter") else "")
                     + (f", {c['page']}" if c.get("page") else "") + (f", fig. {c['figure']}" if c.get("figure") else "")
                     + (f", table {c['table']}" if c.get("table") else "") for c in cites)


def _cm_name(key: str, r: dict) -> str:
    return r["siglum"] or key


def _cm_years(rng: list[int] | None) -> str:
    return f"{rng[0]}–{rng[1]} BCE" if rng else ""


def _cm_said(st: dict) -> str:
    return CM_POINTER if st.get("pointer") else esc(f"\"{st['text']}\"")


def _cm_dating(r: dict) -> tuple[list[list[str]], list[str]]:
    """The Date, Script and Subcorpus rows of the record table, a null field with its reason, a cite or a statement
    with its note; then the statements set against the lead, as a table of their own."""
    why, sources = r["null_reasons"], r["field_sources"]
    if r["period_code"] is None:
        rows = [["Date", esc(f"none: {why['period_code']}")]]
    else:
        years = (f"{_cm_years(r['date_range_bce'])} (Valério 2016, 39)" if r["date_range_bce"]
                 else f"no years: {why['date_range_bce']}")
        b = r["dating_basis"]
        rows = [["Date", esc(f"{r['period_code']} ({r['period_label']}), {years}; {r['dating_status']}, certainty "
                             f"{r['date_certainty']}; lead statement: {b['source']}, ") + _cm_said(b)
                 + esc(f" ({_cm_where(b['cites'])})" + (f"; {b['note']}" if b.get("note") else ""))]]
    for field, label in (("script", "Script"), ("subcorpus", "Subcorpus")):
        refs = "; ".join(_cm_where([c]) + (f" ({c['note']})" if c.get("note") else "")
                         for c in sources.get(field, []))
        rows.append([label, esc(f"none: {why[field]}" if r[field] is None
                                else "; ".join(filter(None, (r[field], refs))))])
    against = []
    if r["conflicts"]:
        against = ["Set against the lead statement:", ""] + table(["Statement", "Period", "Relation", "Source"], [
            [_cm_said(c) + (esc(f" ({c['note']})") if c.get("note") else ""),
             esc(", ".join(filter(None, (c["period_code"], _cm_years(c["date_range_bce"]))))),
             esc(c["relation"]), esc(f"{c['source']}; {_cm_where(c['cites'])}")] for c in r["conflicts"]]) + [""]
    return rows, against


def _cm_page(key: str, r: dict, reading: dict | None = None) -> tuple[str, str]:
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
    dating, against = _cm_dating(r)
    rows += dating
    rows.append(["Status", esc(_words(r["inclusion_status"] or "outside Appendix A"))])
    if e["of_record"]:
        pages = e["appendix_a_pages"]
        span = (f", Appendix A, {pages[0]}–{pages[-1]}" if len(pages) > 1 else f", Appendix A, {pages[0]}") \
            if pages else ""
        rows.append(["Edition of record", esc(f"{e['of_record']}, transcribed in Valério 2016{span}; "
                                              + ("verified" if e["verified"] else "unverified"))])
    body = ["## Record", ""] + table(["Field", "Value"], rows) + [""] + against
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
    if reading:
        body += _cm_reading(reading)
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
    beyond = " beyond the sign groups of the words read" if reading else ""
    body += [(f"No transcription is reproduced here{beyond}: Valério 2016, Appendix A transcribes the corpus under terms "
              "that allow private research use only, and the edition row names its pages."), ""]
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
    translations = _cm_translations(folder)
    out = [_cm_page(key, r, translations.get(key)) for key, r in catalogue.items()]
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
    if translations:
        rows = [[link(_cm_path(k, catalogue[k]), esc(_cm_name(k, catalogue[k]))), esc(rec["confidence"]),
                 esc(rec["status"] or "complete"), str(len(rec["words"])), esc(rec["translation"])]
                for k, rec in sorted(translations.items(), key=lambda kr: natural(kr[0])) if k in catalogue]
        out.append(_page(f"{CM}/translated", {
            "title": "Cypro-Minoan texts translated",
            "desc": "The Cypro-Minoan texts with di Mino's reading, each with its tier, state, words and translation.",
            "tags": ["aegean", "cypro-minoan"], "kind": "cypro_minoan_index"},
            table(["Text", "Tier", "State", "Words", "Translation"], rows) + [""]))
    grammar = _cm_file(folder, "grammar_hypotheses.json")
    if grammar:
        out.append(_cm_grammar_page(grammar, catalogue))
    lexicon = _cm_file(folder, "lexicon.json")
    if lexicon:
        out.append(_cm_lexicon_page(lexicon, catalogue))
    onomasticon = _cm_file(folder, "onomasticon.json")
    if onomasticon and lexicon:
        out.append(_cm_onomasticon_page(onomasticon, lexicon))
    grid = _cm_file(folder, "grid.json")
    if grid:
        out.append(_cm_grid_page(grid))
    return collect(out)


def descs(folder: Path) -> dict[str, str]:
    """Folder -> the desc its `_index.md` takes when the build makes it."""
    catalogue = _cm_catalogue(folder)
    if not catalogue:
        return {}
    out = {CM: "The Cypro-Minoan texts, one catalogue page per text with its site, object type, edition of record "
               "and the statements of held works with their pages, translated readings word by word, and indexes by "
               "site, object type, grammar hypotheses, lexicon, onomasticon, and 72-sign grid."}
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
