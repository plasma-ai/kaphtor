"""The record wiki's ledger pages: `counts` (the headline counts), `standing` (every reading by tier, with its
score), and the `by_site`, `by_root` and `by_sign` indexes.

Every number is computed here from the data, through `counts`; no stored `stats` block is printed. `by_root` groups
entries by a lossy consonantal browse key, which is a lead for review and never identity, so it links no root page.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from ..core.semitic_root_schema import normalize_root_browse_key
from . import counts
from .markdown import escape as esc
from .markdown import link, table
from .model import SUBSCRIPTS, Model, attestation_base, natural, sign_parts, sign_path, sign_records, word_path
from .render import _page, _words

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


def counts_page(model: Model) -> tuple[str, str]:
    complete, incomplete = counts.translation_counts({k: t["raw"] for k, t in model.translations.items()})
    summary = model.sign_values["resolution_summary"]
    body = ["## Headline", ""] + table(["Measure", "Count"], [
        ["Translated inscriptions (complete)", f"{complete:,}"],
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


def pages(model: Model) -> list[tuple[str, str]]:
    return [counts_page(model), standing(model), by_site(model), by_root(model), by_sign(model)]
