#!/usr/bin/env python3
"""Query the local ORACC, PNM, Prosopographia Memphitica, TLA v18, Gauthier DNG and Kassite concordance
proper-name layers."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from ane_keys import expand, fold_pattern, loose_key, marks_kept, parse_query

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import ANE_DATA, SHARE_ALIKE

SOURCE_DIRS = {
    "oracc": ANE_DATA / "oracc",
    "pnm": ANE_DATA / "pnm-v6",
    "prom": ANE_DATA / "prosopographia-memphitica",
    "tla": SHARE_ALIKE / "tla-v18-names",
    "gauthier": ANE_DATA / "gauthier-dng",
    "kassite-concordances": ANE_DATA / "kassite-concordances",
}


def fold(value) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).casefold()


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


SEARCH_FIELDS = {
    "name", "display_name", "personal_name", "transcription", "transliteration",
    "translation", "translation_en", "translation_de", "written_form",
    "normalized_form", "citation_form", "spelling", "spelling_norm", "place_name",
    "title", "title_string", "dossier_title",
    "line_text", "context", "name_occurrence", "element", "structure", "ranke",
}
# Fields searched in one source only: a Kassite concordance entry's headword, and its entry_ocr, which holds the
# spellings printed after the headword.
SOURCE_FIELDS = {"kassite-concordances": frozenset({"headword", "entry_ocr"}),
                 # A ProM person or name in Unicode (read from Umschrift_TTn by its sign list), its titles,
                 # ProM's English rendering and its Ranke references as normalized (I, 231.4).
                 "prom": frozenset({"name_unicode", "title_unicode", "translit_english", "normalized"}),
                 # A TLA name: its lemma, each form and hieroglyphic spelling, the Wikidata transliteration and
                 # sense, the 2018 extract's glosses and the reference it cites (RPN I 37.19, LGG, Beckerath).
                 "tla": frozenset({"lemma", "form", "hieroglyphs", "transliteration_lut", "senses",
                                   "extract_gloss_en", "extract_gloss_de", "extract_bibl"}),
                 # A Gauthier DNG entry: the further spellings of its head, its French gloss and its description,
                 # which names the modern place (aujourd'hui El-Achmounein).
                 "gauthier": frozenset({"form", "gloss_fr", "description_fr"})}
# ORACC entities aggregate their forms as {form: count}; the forms are the keys.
FORM_MAPS = {"citation_forms", "normalized_forms", "written_forms"}
# ProM keeps a person's other names as a list of strings.
STRING_LISTS = {"other_names", "other_names_unicode"}
# A layer whose rows carry no kind because every row is of one kind.
SOURCE_KIND = {"prom": "person"}
# Sources stored in a notation other than the one a scholar types (ane_keys.VIEW_NOTATION).
# ProM's Unicode names write yod j and the suffix ⸗, as PNM does, so a query is spelled for both alike.
NOTATION_VIEW = {"pnm": "pnm", "tla": "tla", "prom": "pnm"}


def search_values(value, extra: frozenset[str] = frozenset()) -> list[str]:
    """Return onomastically relevant scalar fields and ORACC form-map keys, including nested PNM joins;
    `extra` adds the source's own fields (SOURCE_FIELDS)."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if (key in SEARCH_FIELDS or key in extra) and child not in (None, "") and not isinstance(child, (dict, list)):
                found.append(str(child))
            if key in FORM_MAPS and isinstance(child, dict):
                found.extend(str(form) for form in child)
            if key in STRING_LISTS and isinstance(child, list):
                found.extend(str(form) for form in child if isinstance(form, str))
            if isinstance(child, (dict, list)):
                found.extend(search_values(child, extra))
    elif isinstance(value, list):
        for child in value:
            found.extend(search_values(child, extra))
    return found


def needles(query: str, source: str) -> list[str]:
    """The folded query, then its spellings in the source's stored notation; empty for no query."""
    out = [fold(query)] if fold(query) else []
    if out and source in NOTATION_VIEW:
        out += [fold(key) for key in sorted(expand(parse_query(query), NOTATION_VIEW[source]))]
    return list(dict.fromkeys(out))


# Match basis, as aneq ranks it: the whole name as typed, in the source's notation, folded; then the query
# inside a longer name (Samas inside Kirsamas).
EXACT, NOTATION, FOLDED, SUBSTRING = 0, 1, 2, 4


def folding(query: str):
    """The query's folded key and compiled fold pattern (ane_keys), or None when nothing is left to fold."""
    key = loose_key(query)
    return (key, re.compile(fold_pattern(query))) if key else None


def strict_basis(values: list[str], wanted: list[str], exact: bool) -> int | None:
    """How the row's values match without the folded key: wanted[0] is the query as typed, the rest its
    notation spellings. A whole value first, then, unless `exact`, the query inside a longer value."""
    held = {fold(value) for value in values}
    hits = [i for i, needle in enumerate(wanted) if needle in held]
    if hits:
        return min(hits[0], NOTATION)
    if exact:
        return None
    text = fold("\n".join(values))
    return SUBSTRING if any(needle in text for needle in wanted) else None


def folded_basis(values: list[str], folded, exact: bool) -> int | None:
    """The folded tier: a whole value under the folded key, or (unless `exact`) the key inside a longer one.
    The fold pattern is tested first: it is cheap, and loose_key, which must agree with it, is not."""
    key, pattern = folded
    inside = False
    for value in values:
        kept = marks_kept(value)
        if not pattern.search(kept):
            continue
        loose = loose_key(value)
        if loose == key and pattern.fullmatch(kept):
            return FOLDED
        inside = inside or key in loose
    return SUBSTRING if inside and not exact else None


def with_fold(strict: int | None, folded: int | None) -> int | None:
    """A row's basis once the folded tier joins: a whole value as typed or in notation, then a whole folded
    value, then the query or the key inside a longer value."""
    if strict is not None and strict <= NOTATION:
        return strict
    if folded == FOLDED:
        return FOLDED
    return SUBSTRING if SUBSTRING in (strict, folded) else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--source", choices=("oracc", "pnm", "prom", "tla", "gauthier", "kassite-concordances", "all"),
                    default="all")
    ap.add_argument(
        "--layer",
        choices=("occurrences", "attestations", "entities", "name_forms", "persons"),
        default="occurrences",
        help=(
            "attestations/occurrences = textual rows; name_forms/entities = "
            "name aggregates or lexemes; persons = identified PNM dossiers"
        ),
    )
    ap.add_argument("--kind")
    ap.add_argument("--pos")
    ap.add_argument("--language")
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--loose", action="store_true",
                    help="also match with marks, aleph/ayin and separators folded (otherwise only when "
                         "nothing matches strictly)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    attestation_layer = args.layer in {"occurrences", "attestations"}
    name_form_layer = args.layer in {"entities", "name_forms"}
    candidates = {
        "oracc": [SOURCE_DIRS["oracc"] / ("occurrences.jsonl" if attestation_layer else "entities.jsonl")]
        if args.layer != "persons" else [],
        "pnm": [
            SOURCE_DIRS["pnm"] / (
                "attestations_enriched.jsonl" if attestation_layer
                else "tables/personal_names.jsonl" if name_form_layer
                else "tables/persons.jsonl"
            )
        ],
        # Prosopographia Memphitica: its New Kingdom Memphite persons with their titles, dating and objects, or
        # its name rows.
        "prom": [SOURCE_DIRS["prom"] / ("names.jsonl" if name_form_layer else "persons.jsonl")],
        # TLA corpus v18: its proper-noun tokens, each with its hieroglyphs and date range, or one row per lemma.
        "tla": [SOURCE_DIRS["tla"] / ("occurrences.jsonl" if attestation_layer else "lemmas.jsonl")]
        if args.layer != "persons" else [],
        # Gauthier's Dictionnaire des noms géographiques t. 1-6 as the OCR text layer gives it: leads to the printed
        # page, one row per entry, cross-reference and addendum.
        "gauthier": [SOURCE_DIRS["gauthier"] / "entries.jsonl"] if args.layer != "persons" else [],
        # The printed name indexes of seven Kassite-period and kudurru volumes, as OCR leads to the page.
        "kassite-concordances": [SOURCE_DIRS["kassite-concordances"] / "entries.jsonl"]
        if args.layer != "persons" else [],
    }
    entity_scopes = {
        "oracc": "textual_attestation" if attestation_layer else "name_form_aggregate",
        "pnm": (
            "textual_attestation" if attestation_layer
            else "name_lexeme" if name_form_layer
            else "person_dossier"
        ),
        "prom": "name_form" if name_form_layer else "prosopography_entry",
        "tla": "textual_attestation" if attestation_layer else "name_lexeme",
        "gauthier": "toponym_lead",
        "kassite-concordances": "index_entry",
    }
    sources = candidates if args.source == "all" else {args.source: candidates[args.source]}
    for source, paths in sources.items():
        if not paths and args.source != "all":
            print(f"note: {source} has no {args.layer} layer", file=sys.stderr)
    folded = folding(args.query)

    def scan(source: str, paths: list[Path], wanted: list[str]) -> list[dict]:
        """Matching rows, closest first, up to the limit, in one pass. The folded key joins when --loose asks
        for it, or when no row matches as a whole name. Once the limit matches as typed, no row can rank
        higher, so the scan stops."""
        found: list[dict] = []
        scored: list[tuple[int | None, int | None, dict]] = []
        whole = typed = 0
        for path in paths:
            for row in iter_jsonl(path):
                if args.kind and row.get("kind", SOURCE_KIND.get(source)) != args.kind:
                    continue
                if args.pos and row.get("qpn_pos") != args.pos:
                    continue
                if args.language and fold(args.language) not in fold(row.get("language")):
                    continue
                item = {"dataset": source, "entity_scope": entity_scopes[source], **row}
                if not wanted:
                    if len(found) >= args.limit:
                        return found
                    found.append(item)
                    continue
                values = search_values(row, SOURCE_FIELDS.get(source, frozenset()))
                strict = strict_basis(values, wanted, args.exact)
                # The folded tier is needed only under --loose or until a whole name matches strictly.
                fold_basis = (folded_basis(values, folded, args.exact)
                              if folded and (args.loose or not whole) and (strict is None or strict > NOTATION)
                              else None)
                if strict is None and fold_basis is None:
                    continue
                scored.append((strict, fold_basis, item))
                whole += strict is not None and strict <= NOTATION
                typed += strict == EXACT
                if typed >= args.limit:
                    break
            if typed >= args.limit:
                break
        if not wanted:
            return found
        use_fold = folded is not None and (args.loose or not whole)
        for strict, fold_basis, item in scored:
            basis = with_fold(strict, fold_basis) if use_fold else strict
            if basis is not None:
                found.append({**item, "match_basis": basis})
        found.sort(key=lambda r: r["match_basis"])
        return found[:args.limit]

    found_by_source: dict[str, list[dict]] = {}
    for source, paths in sources.items():
        # A missing file is named; with --source all the other sources are still searched.
        missing = [path for path in paths if not path.exists()]
        if missing:
            message = f"{source} is not in this checkout (looked for {', '.join(map(str, missing))})"
            if args.source != "all":
                raise SystemExit(message)
            print(message, file=sys.stderr)
            found_by_source[source] = []
            continue
        found_by_source[source] = scan(source, paths, needles(args.query, source))

    if args.source == "all":
        # Fair round-robin keeps one prolific corpus from hiding matches in
        # later datasets while preserving a global result limit.
        found = []
        offset = 0
        ordered_sources = list(found_by_source)
        while len(found) < args.limit:
            added = False
            for source in ordered_sources:
                rows = found_by_source[source]
                if offset < len(rows):
                    found.append(rows[offset])
                    added = True
                    if len(found) >= args.limit:
                        break
            if not added:
                break
            offset += 1
    else:
        found = found_by_source.get(args.source, [])[:args.limit]

    if args.json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
    else:
        for row in found:
            name = row.get("name") or row.get("display_name") or row.get("personal_name") or row.get("transliteration") or row.get("spelling")
            ref = row.get("token_ref") or row.get("location") or row.get("source_row") or ""
            if row["dataset"] == "prom":
                name, ref = row.get("name_unicode") or row["name"], f"{row['id']}, {row.get('translit_english') or ''}"
            if row["dataset"] == "gauthier":
                name, ref = row.get("transcription"), f"Gauthier DNG t. {row['volume']}, p. {row['page']} ({row['id']})"
            if row["dataset"] == "tla":
                dates = f"{row['date_not_before']} to {row['date_not_after']}"
                name = row["lemma"]
                ref = (f"{row['id']}, {row['token_count']} tokens, {dates}" if "token_count" in row
                       else f"{row['id']} {row['form']}, {dates}")
            if row["dataset"] == "kassite-concordances":
                # The id is the work key, the PDF page and the row: the work key names the volume.
                name, ref = row["headword"], f"{row['id'].rsplit('-', 2)[0]} p. {row['printed_page']} ({row['id']})"
            kind = (row.get("kind") or row.get("qpn_pos") or row.get("wikidata_class")
                    or SOURCE_KIND.get(row["dataset"]) or "")
            print(f"{row['dataset']}\t{name or ''}\t{kind}\t{ref}")


if __name__ == "__main__":
    main()
