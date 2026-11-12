"""The record wiki's ledger pages: `counts` (the headline counts), `standing` (every reading by tier, with its
score), the `by_site`, `by_root` and `by_sign` indexes, and `unread_signs` (the single and combined signs with no
lexicon entry, by the untranslated records each one alone leaves unread) when the data folder holds that file.
`by_scribe` lists every scribe with the records, when the data folder holds `scribes.json`.

Every number is computed here from the data, through `counts`; no stored `stats` block is printed. `by_root` groups
entries by a lossy consonantal browse key, which is a lead for review and never identity, so it links no root page.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from ..core import scribes
from ..core.semitic_root_schema import normalize_root_browse_key
from ..linear_a.validation import check_unread_signs as sign_check
from ..linear_a.validation import check_unread_words as word_check
from . import counts
from .markdown import escape as esc
from .markdown import link, table
from .model import (
    SUBSCRIPTS,
    Model,
    attestation_base,
    doc_path,
    natural,
    sign_parts,
    sign_path,
    sign_records,
    word_path,
)
from .render import BY_SCRIBE, _page, _words

TIERS = ("CONFIRMED", "PROBABLE", "CANDIDATE", "SPECULATIVE")
SIGN_STATUSES = ("resolved", "proposed", "speculative", "conventional")


def _ledger(name: str, title: str, desc: str, body: list[str]) -> tuple[str, str]:
    fields = {"title": title, "desc": desc, "tags": ["linear-a", "ledger"], "kind": "ledger"}
    return _page(f"wiki/linear-a/{name}", fields, ["Every number on this page is computed from the data files.", "",
                                                   *body])


def _site(rec: dict) -> str:
    return rec.get("site") or "(no site)"


def _sites(model: Model) -> list[tuple[str, int, int, int, int]]:
    """(site, records, documents, complete translations, lexicon words attested), most records first."""
    records = Counter(_site(r) for r in model.corpus.values())
    documents = Counter(_site(model.corpus[keys[0]]) for keys in counts.documents(model.corpus).values())
    translated = Counter(_site(model.corpus[k]) for k, t in model.translations.items()
                         if k in model.corpus and t["complete"])
    words = defaultdict(set)
    for form, entry in model.lexicon.items():
        for attestation in entry.get("attestations") or []:
            base = attestation_base(attestation, model.corpus)
            if base in model.corpus:
                words[_site(model.corpus[base])].add(form)
    return [(s, n, documents[s], translated[s], len(words[s]))
            for s, n in sorted(records.items(), key=lambda kv: (-kv[1], kv[0]))]


def _site_row(row: tuple[str, int, int, int, int]) -> list[str]:
    site, *numbers = row
    return [esc(site), *(f"{n:,}" for n in numbers)]


SEALINGS = ("Nodule", "Roundel", "Sealing")


def sealing_labels(model: Model) -> int:
    """Complete translations of a nodule, roundel or sealing whose whole text is one sign: numerals and separators
    aside, a single token that is no word of two or more signs (a vessel sign's `-VS` is part of the sign)."""
    def one_sign(key: str) -> bool:
        record = model.corpus.get(key) or {}
        tokens = [t.strip() for t in record.get("transliteratedWords") or [] if not sign_check.is_counted(t)]
        return (record.get("support") in SEALINGS and len(tokens) == 1
                and "-" not in tokens[0].removesuffix("-VS"))
    return sum(1 for key, t in model.translations.items() if counts.is_complete(t["raw"]) and one_sign(key))


def counts_page(model: Model) -> tuple[str, str]:
    complete, incomplete = counts.translation_counts({k: t["raw"] for k, t in model.translations.items()})
    summary = model.sign_values["resolution_summary"]
    body = ["## Headline", ""] + table(["Measure", "Count"], [
        ["Translated inscriptions (complete)", f"{complete:,}"],
        ["of which one-sign sealing labels", f"{sealing_labels(model):,}"],
        ["Translations incomplete", f"{incomplete:,}"],
        ["Corpus records", f"{len(model.corpus):,}"],
        ["Documents", f"{len(counts.documents(model.corpus)):,}"],
        ["Lexicon entries", f"{len(model.lexicon):,}"],
        ["Resolved signs (syllabic + logogram)",
         f"{summary['total']} ({summary['phonemic_count']} + {summary['logogram_count']})"],
        ["Fraction values resolved", f"{summary['fraction_count']}"],
        ["Onomasticon entries", f"{len(model.onomasticon):,}"],
        ["Unread words listed", f"{len(model.unread):,}"],
    ]) + [""]
    census = counts.census(model.corpus, model.census_classes)
    body += ["## Documents against the published census", "",
             ("GORILA 1,427 and RILA-S1 107 documents are published to the end of 2023 (1,534 in all). Each document "
              "of the corpus falls in one class:"), ""]
    body += table(["Class", "Documents"], [[c, f"{census[c]:,}"] for c in counts.CLASSES if census[c]]) + [""]
    tiers = Counter(e["confidence"] for e in model.lexicon.values())
    body += ["## Lexicon by tier", ""] + table(["Confidence", "Tier", "Entries"], [
        [c, str(next((e["tier"] for e in model.lexicon.values() if e["confidence"] == c), "")), str(tiers[c])]
        for c in (*TIERS, *sorted(set(tiers) - set(TIERS))) if tiers[c]]) + [""]
    records = sign_records(model.sign_values)
    by_kind = Counter((kind, status) for (kind, key), (status, _evidence) in model.sign_status.items()
                      if key in records[kind])
    body += ["## Signs by status", ""] + table(["Kind", *(s.capitalize() for s in SIGN_STATUSES)], [
        [kind, *(str(by_kind[(kind, s)]) for s in SIGN_STATUSES)] for kind in ("syllabic", "logograms", "fractions")])
    body += [""]
    types = Counter(o.get("type") or "(none)" for o in model.onomasticon.values())
    body += ["## Onomasticon by type", ""] + table(["Type", "Entries"], [
        [esc(_words(t)), str(n)] for t, n in sorted(types.items(), key=lambda kv: (-kv[1], kv[0]))]) + [""]
    statuses = Counter(u["status"] for u in model.unread.values())
    body += ["## Unread words by status", ""] + table(["Status", "Words", "Meaning"], [
        [esc(_words(s)), str(statuses[s]), esc(model.unread_statuses.get(s, ""))] for s in sorted(statuses)]) + [""]
    body += ["## By site", "", f"Sites with ten or more records; every site is in {link('wiki/linear-a/by_site', 'by site')}.",
             ""]
    body += table(["Site", "Records", "Documents", "Translated (complete)", "Lexicon words attested"],
                  [_site_row(row) for row in _sites(model) if row[1] >= 10]) + [""]
    return _ledger("counts", "Counts", "Headline counts of the Linear A record, computed from the data files.", body)


def standing(model: Model) -> tuple[str, str]:
    groups = defaultdict(list)
    for form, entry in model.lexicon.items():
        groups[entry["confidence"]].append(form)
    body = []
    for confidence in (*TIERS, *sorted(set(groups) - set(TIERS))):
        forms = sorted(groups.get(confidence, []), key=natural)
        if not forms:
            continue
        body += [f"## {confidence}", "", f"{len(forms)} entries.", ""]
        body += table(["Word", "Reading", "Meaning", "Score"], [
            [link(word_path(f), esc(f)), esc(model.lexicon[f].get("reading") or ""),
             esc(model.lexicon[f].get("meaning") or ""),
             "" if model.lexicon[f].get("confidence_score") is None else f"{model.lexicon[f]['confidence_score']:.2f}"]
            for f in forms]) + [""]
    return _ledger("standing", "Standing", "Every reading in the lexicon, by confidence tier, with its score.", body)


def by_site(model: Model) -> tuple[str, str]:
    body = table(["Site", "Records", "Documents", "Translated (complete)", "Lexicon words attested"],
                 [_site_row(row) for row in _sites(model)]) + [""]
    return _ledger("by_site", "By site", "Records, documents, translations and lexicon words for every site.", body)


def by_root(model: Model) -> tuple[str, str]:
    groups = defaultdict(list)
    for form, entry in model.lexicon.items():
        root = entry.get("root")
        key = normalize_root_browse_key(root) if isinstance(root, str) else ""
        groups[key or ("(no root)" if not root else "(no consonantal key)")].append(form)
    rows = []
    for key in sorted(groups, key=lambda k: (k.startswith("("), k)):
        forms = sorted(groups[key], key=natural)
        written = sorted({model.lexicon[f]["root"] for f in forms if model.lexicon[f].get("root")})
        rows.append([esc(key), esc("; ".join(written)), ", ".join(link(word_path(f), esc(f)) for f in forms)])
    body = [("Entries grouped by a consonantal key of their `root` field. The key is lossy: it is a lead for review, "
             "never an identity of roots."), ""] + table(["Key", "Roots as written", "Words"], rows) + [""]
    return _ledger("by_root", "By root", "Lexicon entries grouped by a consonantal browse key of their root.", body)


def by_sign(model: Model) -> tuple[str, str]:
    records = sign_records(model.sign_values)
    uses = defaultdict(set)  # by the spelling with subscripts read as digits, so TA₂ meets the record TA2
    for form in model.lexicon:
        for part in sign_parts(form):
            uses[part.translate(SUBSCRIPTS)].add(form)
    rows = []
    for kind in ("syllabic", "logograms"):
        for key in sorted(records[kind], key=natural):
            forms = sorted(uses.get(key.translate(SUBSCRIPTS), ()), key=natural)
            rows.append([link(sign_path(kind, key), esc(key)), kind, model.sign_status[(kind, key)][0], str(len(forms)),
                         ", ".join(link(word_path(f), esc(f)) for f in forms)])
    body = table(["Sign", "Kind", "Status", "Words", "Lexicon words written with it"], rows) + [""]
    return _ledger("by_sign", "By sign", "Every syllabic and logographic sign with the lexicon words that use it.", body)


def unread_signs(model: Model) -> tuple[str, str]:
    signs = model.unread_signs
    live = word_check.live_lexicon({"entries": list(model.lexicon.values())})
    lex_hit = word_check.make_lex_hit(live, {k for k in model.sign_values["signs"] if k.startswith("*")})
    named = {token for token, o in model.onomasticon.items() if o.get("reading")}
    blocked = sign_check.sole_blockers(model.corpus, model.translations, signs, lex_hit, named)
    statuses = Counter(s["status"] for s in signs.values())
    body = [(f"{len(signs):,} single and combined signs stand as entries in the corpus without a lexicon entry. "
             f"{sum(len(r) for r in blocked.values()):,} records with no translation wait on one of them alone: every "
             "other token there is a numeral, a lexicon entry or a name with a reading."), ""]
    body += ["## By status", ""] + table(["Status", "Signs", "Meaning"], [
        [esc(_words(s)), str(statuses[s]), esc(model.unread_sign_statuses.get(s, ""))] for s in sorted(statuses)]) + [""]

    def on_file(entry: dict) -> str:
        values = list(dict.fromkeys(o["value"] for o in entry.get("on_file") or []))
        if values:
            return esc("; ".join(values))
        read = entry.get("read_components") or []
        return esc("reads " + ", ".join(read)) if read else ""

    def records(sign: str) -> str:
        keys = blocked.get(sign, [])
        shown = ", ".join(link(doc_path(k), esc(k)) for k in keys[:8])
        return shown + (f" and {len(keys) - 8} more" if len(keys) > 8 else "")

    order = sorted(signs, key=lambda s: (-len(blocked.get(s, [])), -signs[s].get("frequency", 0), natural(s)))
    body += ["## The signs", "",
             "Ordered by the records each one alone leaves unread, then by occurrences.", ""]
    body += table(["Sign", "Kind", "Status", "Occurrences", "Records waiting on it alone", "Those records", "On file"], [
        [link(word_path(s), esc(s)), esc(_words(signs[s]["kind"])), esc(_words(signs[s]["status"])), str(signs[s].get("frequency", 0)),
         str(len(blocked.get(s, []))), records(s), on_file(signs[s])] for s in order]) + [""]
    return _ledger("unread_signs", "Unread signs",
                   "The single and combined signs with no lexicon entry, by the untranslated records each one alone "
                   "leaves unread.", body)


def by_scribe(model: Model) -> tuple[str, str]:
    index = scribes.scribe_index(model.corpus)
    assigned = {key for keys in index.values() for key in keys}
    doubted = sum(1 for key in assigned if model.corpus[key].get("scribe_doubt"))
    body = [(f"{len(index):,} scribes are assigned {len(assigned):,} records, {doubted:,} of them with a question "
             "mark in the edition. A scribe is numbered within one site and one class of document. A record that two "
             "scribes wrote stands under each, with the part each wrote."), "",
            ("The numbers are GORILA V's, except on the Haghia Triada tablets, which follow Militello 1989's "
             "numbering; for those the column GORILA V gives the cells GORILA V prints for the same tablets."), ""]

    def record(key: str, label: str) -> str:
        rec, part = model.corpus[key], scribes.scribe_part(model.corpus[key], label)
        return link(doc_path(key), esc(key)) + (" (?)" if scribes.doubtful(rec, label) else "") \
            + (f" ({esc(part)})" if part else "")

    def source(entry: dict) -> str:
        return esc(". ".join(x.rstrip(".") for x in (entry.get("source") or "", entry.get("note") or "") if x)
                   + ("." if entry.get("note") else ""))

    rows = []
    for label, keys in index.items():
        entry = model.scribes.get(label, {})
        rows.append([esc(label), esc(entry.get("site") or ""), esc(entry.get("class") or ""),
                     esc(entry.get("numbering") or ""), esc("; ".join(entry.get("gorila_v") or [])), str(len(keys)),
                     ", ".join(record(key, label) for key in keys), source(entry)])
    body += table(["Scribe", "Site", "Class", "Numbering", "GORILA V", "Records", "The records", "Source"], rows) + [""]
    return _ledger(BY_SCRIBE.rsplit("/", 1)[1], "By scribe",
                   "Every scribe to whom an edition assigns documents, with the records and the source.", body)


def pages(model: Model) -> list[tuple[str, str]]:
    ledgers = [counts_page(model), standing(model), by_site(model), by_root(model), by_sign(model)]
    return ledgers + ([unread_signs(model)] if model.unread_signs else []) + ([by_scribe(model)] if model.scribes else [])
