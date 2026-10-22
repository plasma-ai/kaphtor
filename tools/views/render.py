"""The record wiki's pages, rendered from a loaded model: one per word form, one per inscription, one per sign.

Each function returns (path, text) for a fresh page; `build.py` splices it into the page on disk. Output is sorted
and carries no dates, so the same data gives the same bytes. Data text renders verbatim, escaped; Linear A Unicode
goes in code blocks.
"""
from __future__ import annotations

from .markdown import escape as esc
from .markdown import link, page, table
from .model import (
    SUBSCRIPTS,
    Model,
    attestation_base,
    doc_path,
    natural,
    series,
    sign_keys,
    sign_parts,
    sign_path,
    sign_records,
    word_path,
)

TIER_NAME = {4: "CONFIRMED", 3: "PROBABLE", 2: "CANDIDATE", 1: "SPECULATIVE"}
STATUS_TEXT = {
    "resolved": "Listed among the resolved values of the sign table.",
    "proposed": "A proposed value.",
    "speculative": "A speculative value.",
    "conventional": "The conventional value carried over from Linear B.",
}
# Every frontmatter key the builder writes; `splice` replaces these and keeps any other. `name`, `sources` and the
# timestamps belong to `wiki update`, which derives `name` from the path and keeps an authored `sources` list.
OWNED_KEYS = frozenset({
    "title", "desc", "tags", "kind", "form", "datasets", "tier", "confidence", "confidence_score", "reading",
    "attestations", "id", "site", "support", "period", "translation", "words", "sign_kind", "sign", "sign_number",
    "status", "value",
})


def _page(path: str, fields: dict, body: list[str]) -> tuple[str, str]:
    parent = path.rsplit("/", 1)[0]
    return path, page(fields, fields["title"], [link(parent + "/_index", "..")], ["", *body])


def _words(text: str) -> str:
    return text.replace("_", " ")


def has_page(model: Model, form: str) -> bool:
    """Whether a form has a word page: an entry in the lexicon, the onomasticon or the unread words."""
    return form in model.lexicon or form in model.onomasticon or form in model.unread


def translation_label(model: Model, key: str) -> str:
    t = model.translations.get(key)
    if not t:
        return "none"
    return "complete" if t["complete"] else "incomplete"


def sign_links(model: Model, form: str) -> str:
    records = sign_records(model.sign_values)
    keys = {kind: sign_keys(records[kind]) for kind in ("syllabic", "logograms")}
    out = []
    for part in sign_parts(form):
        folded = part.translate(SUBSCRIPTS)
        kind = next((k for k in keys if folded in keys[k]), None)
        out.append(link(sign_path(kind, keys[kind][folded]), esc(part)) if kind else esc(part))
    return " · ".join(out)


def _alternate(value) -> str:
    return f"/{value.get('consonant') or ''}{value.get('vowel') or ''}/" if isinstance(value, dict) else str(value)


# ---------------------------------------------------------------- words

BASIS_LABEL = {"published": "Published by", "reviewed": "Reviewed by"}


def _review(e: dict) -> list[str]:
    """Who stakes a tier-4 reading, and the outside scholar who published or reviewed the same reading."""
    lines = []
    if e.get("reviewer"):
        lines.append(f"- **Reviewer:** {esc(e['reviewer'])}")
    outside = e.get("outside_scholar")
    if outside:
        sections = ", ".join(outside.get("sections") or [])
        lines.append(f"- **{BASIS_LABEL[outside['basis']]}:** {esc(outside['scholar'])}, *{esc(outside['work'])}*"
                     f" ({outside['year']})" + (f", {esc(sections)}" if sections else ""))
    return ["### Review", "", *lines, ""] if lines else []


def word_page(model: Model, form: str) -> tuple[str, str]:
    e, o, u = model.lexicon.get(form), model.onomasticon.get(form), model.unread.get(form)
    datasets = [name for name, rec in (("lexicon", e), ("onomasticon", o), ("unread_words", u)) if rec]
    if e:
        desc = ((f"{e['reading']}: " if e.get("reading") else "") + f"{e.get('meaning') or 'no meaning recorded'}. "
                f"Lexicon, {e['confidence']} (tier {e['tier']}).")
    elif u:
        desc = (f"Unread ({_words(u['status'])}): {_words(u.get('role') or 'no role')}; "
                f"{u.get('frequency', 0)} occurrence(s).")
    else:
        desc = f"Onomasticon {_words(o.get('type') or 'entry')}, no reading."
    attestations = list(dict.fromkeys(a for rec in (e, o, u) if rec for a in rec.get("attestations") or []))
    fields = {"title": form, "desc": desc,
              "tags": ["linear-a", "word"] + ([f"tier-{e['tier']}", e.get("category") or "uncategorised"] if e else [])
              + (["unread"] if u else []),
              "kind": "word", "form": form, "datasets": datasets}
    if e:
        fields |= {"tier": e["tier"], "confidence": e["confidence"], "confidence_score": e.get("confidence_score"),
                   "reading": e.get("reading")}
    fields["attestations"] = attestations

    body = [f"**Signs.** {sign_links(model, form)}", ""]
    if e:
        score = e.get("confidence_score")
        body += ["## Lexicon", "",
                 f"**{e['confidence']}**, tier {e['tier']} of 4" + (f", score {score:.2f}" if score is not None else "")
                 + (" · anchor" if e.get("is_anchor") else ""), ""]
        rows = [[name, esc(value)] for name, value in (
            ("Reading", e.get("reading")), ("Meaning", e.get("meaning")), ("Root", e.get("root")),
            ("Language layer", e.get("language_layer")), ("Category", e.get("category")),
            ("Semantic field", e.get("semantic_field"))) if value]
        body += table(["Field", "Value"], rows) + [""]
        if e.get("note"):
            body += ["### Note", "", esc(e["note"]), ""]
        cognates = e.get("cognates")
        if isinstance(cognates, dict) and cognates:
            body += ["### Cognates", ""] + table(["Language", "Comparison"],
                                                 [[esc(k), esc(v)] for k, v in cognates.items()]) + [""]
        elif cognates:
            body += ["### Cognates", "", esc(cognates), ""]
        parallels = e.get("parallels")
        if isinstance(parallels, dict) and parallels:
            body += ["### Parallels", ""] + table(["Tradition", "Parallel"],
                                                  [[esc(_words(k)), esc(v)] for k, v in parallels.items()]) + [""]
        elif parallels:
            body += ["### Parallels", "", esc(parallels), ""]
        if e.get("source"):
            body += ["### Source", "", esc(e["source"]), ""]
        body += _review(e)

    body += ["## Attestations", ""]
    rows = []
    for attestation in attestations:
        base = attestation_base(attestation, model.corpus)
        rec = model.corpus.get(base)
        if rec is None and attestation in model.translations:
            site = model.translations[attestation]["raw"].get("site") or ""
            rows.append([link(doc_path(attestation), esc(attestation)), esc(site), "",
                         translation_label(model, attestation) + "; no corpus record"])
            continue
        if rec is None:
            rows.append([esc(attestation), "", "", "not in corpus"])
            continue
        label = esc(attestation) if attestation == base else f"{esc(base)} ({esc(attestation[len(base):].strip('()'))})"
        present = form in (rec.get("transliteratedWords") or [])
        rows.append([link(doc_path(base), label), esc(rec.get("site") or ""), esc(rec.get("support") or ""),
                     translation_label(model, base) + ("" if present else "; form not in transliteration")])
    body += table(["Document", "Site", "Support", "Translation"], rows) + [""]

    hits = model.in_translations.get(form, [])
    if hits:
        rows = [[link(doc_path(doc), esc(doc)), esc(item["reading"] or ""), esc(item["gloss"] or ""),
                 esc(item["confidence"] or "")] for doc, item in hits]
        body += ["## In translations", ""] + table(["Document", "Reading there", "Gloss there", "Confidence"], rows)
        body += [""]

    if o:
        rows = [["Type", f"{esc(_words(o.get('type') or ''))} ({esc(o.get('type_confidence') or '')})"],
                ["Affiliation", f"{esc(o.get('affiliation') or '')} ({esc(o.get('affiliation_confidence') or '')})"],
                ["Evidence", esc(o.get("affiliation_evidence") or "")],
                ["Entry", esc(o.get("provenance") or "")],
                ["Occurrences", f"{o.get('frequency', 0)} in {len(o.get('attestations') or [])} documents"],
                ["Sites", esc(", ".join(o.get("sites") or []))],
                ["Supports", esc(", ".join(f"{k} {v}" for k, v in (o.get("genre_supports") or {}).items()))]]
        if o.get("contact_ref"):
            rows.append(["Contact reference", esc(o["contact_ref"])])
        body += ["## Onomasticon", ""] + table(["Field", "Value"], rows) + [""]
        if o.get("note"):
            body += ["### Note", "", esc(o["note"]), ""]
        known = (c.get("word") if isinstance(c, dict) else c for c in o.get("co_occurring_known") or [])
        co = sorted({w for w in known if w} - {form}, key=natural)
        if co:
            live = [(link(word_path(w), esc(w)) if has_page(model, w) else esc(w))
                    + (f" {esc(model.lexicon[w]['reading'])}" if model.lexicon.get(w, {}).get("reading") else "")
                    for w in co]
            body += ["### Co-occurring lexicon words", "",
                     "Readings from the lexicon as it stands: " + ", ".join(live) + ".", ""]

    if u:
        meaning = model.unread_statuses.get(u["status"], "")
        body += ["## Unread", "",
                 f"Status **{_words(u['status'])}**" + (f" ({esc(meaning)})" if meaning else "")
                 + (f"; role {esc(_words(u['role']))}" if u.get("role") else "") + ".", ""]
        if u.get("note"):
            body += [esc(u["note"]), ""]
    return _page(word_path(form), fields, body)


# ---------------------------------------------------------------- inscriptions

def doc_keys(model: Model) -> list[str]:
    """Every inscription page: the corpus records, and translations with no corpus record."""
    return sorted(set(model.corpus) | set(model.translations), key=natural)


def doc_page(model: Model, key: str) -> tuple[str, str]:
    rec, t = model.corpus.get(key) or {}, model.translations.get(key)
    status = translation_label(model, key)
    words = model.attested_in.get(key, [])
    site, support, period = rec.get("site") or (t or {}).get("raw", {}).get("site") or "", rec.get("support") or "", \
        rec.get("context") or ""
    fields = {"title": key,
              "desc": ", ".join(x for x in (support, site, period) if x) + f". Translation: {status}"
              + (f" ({t['confidence']})." if t and t.get("confidence") else "."),
              "tags": ["linear-a", "inscription", f"translation-{status}"]
              + ([support.lower().replace(" ", "-")] if support else []),
              "kind": "inscription", "id": key, "site": site, "support": support, "period": period,
              "translation": status, "words": words}
    body: list[str] = []
    if rec:
        edition = (rec.get("source_provenance") or "") + (f" {rec['gorila_volume']}" if rec.get("gorila_volume") else "")
        rows = [["Site", esc(site)], ["Findspot", esc(rec.get("findspot") or "")], ["Support", esc(support)],
                ["Period", esc(period)], ["Scribe", esc(rec.get("scribe") or "")], ["Edition", esc(edition)],
                ["Series", esc(series(key)[1])]]
        sigla = rec.get("sigla")
        if isinstance(sigla, dict) and sigla.get("id"):
            rows.append(["SigLA", f"[{esc(sigla['id'])}]({sigla['url']})" if sigla.get("url") else esc(sigla["id"])])
        rows.append(["Images", esc(rec.get("imageRights") or "")])
        body += ["## Record", ""] + table(["Field", "Value"], rows) + [""]
        lines = [ln.strip() for ln in " ".join(rec.get("transliteratedWords") or []).split("\n")]
        body += ["## Text", "", "Transliteration, line by line:", ""]
        body += [f"{n}. {esc(ln)}" for n, ln in enumerate((ln for ln in lines if ln), 1)] + [""]
        unicode_text = rec.get("parsedInscription")
        if isinstance(unicode_text, str) and unicode_text.strip():
            body += ["Unicode (Linear A block):", "", "```text", unicode_text, "```", ""]
    else:
        body += ["No corpus record holds this text; the page carries its translation only.", ""]
    if t:
        body += ["## Translation", "", f"**{esc(t['confidence'] or 'no confidence given')}**, {status}"
                 + (f" (status: {esc(t['status'])})" if t["status"] else "") + ".", ""]
        if t["text"]:
            body += ["> " + esc(t["text"]), ""]
        rows = []
        for item in t["words"]:
            w = item["form"] or ""
            tier = (f"{model.lexicon[w]['confidence']} (lexicon)" if w in model.lexicon
                    else "unread" if w in model.unread else "")
            rows.append([link(word_path(w), esc(w)) if has_page(model, w) else esc(w), esc(item["reading"] or ""),
                         esc(item["gloss"] or ""),
                         esc(item["confidence"] or ""), tier])
        if rows:
            body += table(["Word", "Reading", "Gloss", "Confidence", "Lexicon"], rows) + [""]
        if t["notes"]:
            body += ["### Notes", "", esc(t["notes"]), ""]
        source = t["source"]
        if isinstance(source, dict) and source:
            body += ["### Source", ""] + [f"- {esc(k)}: {esc(', '.join(map(str, v)) if isinstance(v, list) else v)}"
                                          for k, v in source.items()] + [""]
        elif source:
            body += ["### Source", "", esc(source), ""]
    if words:
        body += ["## Lexicon words citing this document", "",
                 ", ".join(link(word_path(w), esc(w)) for w in words) + ".", ""]
    diffs = rec.get("sigla_vs_gorila") or []
    if diffs:
        body += ["## Edition differences", ""] + table(["Kind", "SigLA", "GORILA"], [
            [esc(_words(d.get("kind") or "")), esc(d.get("sigla") or ""), esc(d.get("gorila") or "")] for d in diffs])
        body += [""]
    if rec.get("notes"):
        body += ["## Corpus note", "", esc(rec["notes"]), ""]
    return _page(doc_path(key), fields, body)


# ---------------------------------------------------------------- signs

def sign_page(model: Model, kind: str, key: str) -> tuple[str, str]:
    record = sign_records(model.sign_values)[kind][key]
    status, evidence = model.sign_status[(kind, key)]
    value = ""
    if kind == "syllabic" and isinstance(record.get("primary"), dict):
        value = (record["primary"].get("consonant") or "") + (record["primary"].get("vowel") or "")
    elif kind == "fractions":
        value = str(record.get("value") or "")
    elif kind == "logograms":
        value = str(record.get("gloss") or record.get("commodity") or "")
    fields = {"title": key, "desc": f"Linear A {kind.rstrip('s')} {key}, {status}" + (f": {value}" if value else "") + ".",
              "tags": ["linear-a", "sign", kind, status], "kind": "sign", "sign_kind": kind, "sign": key,
              "sign_number": record.get("sign_number") or record.get("a_number"), "status": status,
              "value": value or None}
    body = [f"**Status: {status}.** {STATUS_TEXT[status]}", ""]
    if evidence:
        body += [f"Evidence: {esc(evidence)}", ""]
    if kind == "syllabic":
        lb, alternates = record.get("linear_b") or {}, record.get("alternates") or []
        rows = [["Value", f"/{esc(value)}/" if value else ""],
                ["Alternates", esc(", ".join(_alternate(a) for a in alternates) or "none")],
                ["Linear B", esc(f"{lb.get('sign_number')}, value {lb.get('value')}") if lb
                 else "no Linear B counterpart recorded"]]
        if lb.get("unicode"):
            rows.append(["Linear B Unicode", esc(f"{lb['unicode']} {lb.get('unicode_name') or ''}".strip())])
        if lb.get("note"):
            rows.append(["Linear B note", esc(lb["note"])])
        rows.append(["Neutralization class", esc(record.get("neutralization_class") or "none")])
        body += ["## Phonetic value", ""] + table(["Field", "Value"], rows) + [""]
        described = [a for a in alternates if isinstance(a, dict)]
        if described:
            body += ["### Alternate values", ""] + table(["Value", "Confidence", "Evidence"], [
                [esc(_alternate(a)), "" if a.get("confidence") is None else f"{a['confidence']:.2f}",
                 esc("; ".join([*(a.get("evidence") or []), *([a["note"]] if a.get("note") else [])]))]
                for a in described]) + [""]
        if record.get("confirmed_by"):
            body += ["### Forms cited for the value", ""] + [f"- {esc(x)}" for x in record["confirmed_by"]] + [""]
    elif kind == "logograms":
        rows = [[name, esc(record[f])] for name, f in (("Gloss", "gloss"), ("Commodity", "commodity"),
                                                       ("Semitic term", "semitic_term"), ("Root", "root"))
                if record.get(f)]
        if rows:
            body += ["## Logogram", ""] + table(["Field", "Value"], rows) + [""]
    else:
        body += ["## Fraction", ""] + table(["Field", "Value"], [["Value", esc(value)]]) + [""]
    if record.get("note"):
        body += ["### Note", "", esc(record["note"]), ""]
    other = "logograms" if kind == "syllabic" else "syllabic" if kind == "logograms" else None
    if other and key in sign_records(model.sign_values)[other]:
        body += [f"## Also in {other}", "", link(sign_path(other, key), esc(key)) + f" has a {other} record.", ""]
    if kind != "fractions":
        folded = key.translate(SUBSCRIPTS)
        words = sorted((w for w in model.lexicon if folded in {p.translate(SUBSCRIPTS) for p in sign_parts(w)}),
                       key=natural)
        if words:
            rows = [[link(word_path(w), esc(w)), esc(model.lexicon[w].get("reading") or ""),
                     model.lexicon[w]["confidence"]] for w in words]
            body += ["## Lexicon words written with this sign", ""] + table(["Word", "Reading", "Confidence"], rows)
            body += [""]
    return _page(sign_path(kind, key), fields, body)


def collect(items) -> dict[str, str]:
    """Path -> text from (path, text) pairs, in path order. ValueError when two pages share a path, case aside: on a
    disk that does not tell case apart, one would overwrite the other."""
    out: dict[str, str] = {}
    seen: dict[str, str] = {}
    for path, text in items:
        folded = path.casefold()
        if folded in seen:
            raise ValueError(f"two pages at one path: {seen[folded]!r} and {path!r}")
        seen[folded] = path
        out[path] = text
    return dict(sorted(out.items()))


def pages(model: Model) -> dict[str, str]:
    """Path -> text for every page, in path order."""
    from . import ledgers  # ledgers builds on this module's page helpers
    records = sign_records(model.sign_values)
    return collect([*(word_page(model, form) for form in model.forms()), *ledgers.pages(model),
                    *(doc_page(model, key) for key in doc_keys(model)),
                    *(sign_page(model, kind, key) for kind in records for key in records[kind])])
