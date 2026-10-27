---
name: docs/corpora/proper-name-and-place-authorities
title: Proper names and place authorities
desc: ORACC QPN, PNM v6, Prosopographia Memphitica, the TLA v18 names, Gauthier's DNG, the Kassite name concordances, the Egyptian foreign-name witnesses and the place authorities, and why a place match identifies a place but never counts as linguistic evidence.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-27T17:50:48Z
---

# Proper names and place authorities

This layer separates textual attestations from aggregated name entities and from modern identity authorities. A Pleiades, Trismegistos, or iDAI match can identify a place; it cannot supply a historical spelling or count as linguistic evidence.

## Local datasets

This repository ships only the sets under `data/`; each folder's index lists them.

| Layer | Scope | Local output |
|---|---:|---|
| ORACC QPN occurrences | 222,959 edition-token rows; 215,483 canonical-token signatures; 30,599 name-form aggregates | `data/ane/oracc/` (not in this repository) |
| PNM v6 | 60,488 attestations; 7,933 names; 3,828 person dossiers; 21,700 spellings; 4,689 titles | `data/ane/pnm-v6/` |
| Prosopographia Memphitica | 2,409 New Kingdom Memphite persons; 1,574 name rows; 992 titles; 30,743 relations | `data/ane/prosopographia-memphitica/` |
| TLA v18 names | 9,186 proper-name tokens with hieroglyphs; 1,644 lemmas | `data/share-alike/tla-v18-names/` |
| Gauthier's DNG, t. 1–6 | 7,497 entries, cross-references and addenda; page finder, no hieroglyphs | `data/ane/gauthier-dng/` |
| Kassite name concordances | 9,621 index entries of seven volumes, 1906–1912 | `data/ane/kassite-concordances/` |
| Place authorities | 42,388 Pleiades; 65,130 TM Geo | `data/ane/place-authorities/` (Trismegistos in `data/share-alike/trismegistos/`) |

Mutable counts and hashes are authoritative only in each `MANIFEST.json`.

## ORACC QPN

`occurrences.jsonl` preserves the project, archive, edition, object, line, token reference, language, written form, normalized form, damage flag, period, genre, and provenience. Its 222,959 rows are edition-token records, **not independent witnesses**: parallel ORACC projects can edit the same object token. The 215,483 `canonical_token_key` signatures are duplicate-control candidates, not automatic identity adjudications. `entities.jsonl` is a name-form aggregate search layer and never replaces the occurrence rows.

QPN labels remain intact. The broad place total is the sum of `GN`, `SN`, `TN`, `WN`, `QN`, and `FN`; those categories remain independently queryable. `PN` and `RN` likewise remain distinct.

## PNM version 6

The source is the official Zenodo record, DOI `10.5281/zenodo.15806808`, CC BY 4.0. The downloaded SQL matches the published MD5 `fb705737c7b27456e9b50d578c3ea1f5`. Coverage runs from Mentuhotep II through Amenhotep III.

The extractor retains all 32 populated `INSERT ... VALUES` tables in the v6 dump, including primary keys, alternative readings, name types, interpersonal bonds, title relations, workshops, attestations, names, spellings, persons/dossiers, titles, inscriptions, objects, inventory numbers, bibliography, collections, and places. `attestations_enriched.jsonl` is a convenience join; `tables/*.jsonl` remains the source-faithful layer.

## Prosopographia Memphitica

ProM (Anne Herzberg-Beiersdorf, Humboldt-Universität zu Berlin; Zenodo concept DOI `10.5281/zenodo.3856410`), release
2024-11-15, stated as CC BY 4.0 and ODC-By 1.0, covers New Kingdom persons of Memphis. Its eleven tables are kept
whole under `tables/`; `persons.jsonl` gathers each person's names, titles, dating and objects, and `names.jsonl` each
name's persons and Ranke references. ProM types its transliteration in the Umschrift_TTn font, so the `_unicode`
fields convert it by that font's sign list, whose x and X are the reverse of the Manuel de Codage. A name joins PNM v6
only where its normalized Ranke reference matches exactly one PNM name (647 references); `pnm_ids` keeps the PNM
records ProM names itself.

## TLA v18 names

The Thesaurus Linguae Aegyptiae's Original Earlier Egyptian sentences, corpus v18 (CC BY-SA 4.0), give 12,773 sentences
dated −3350 to −1539. The tokens tagged UPOS PROPN are the name set, 9,186 once one mistagged noun is set aside: each keeps its form, hieroglyphs,
gloss, date range, sentence transliteration and German translation. The 1,644 lemma rows count each lemma's forms and
spellings, and add its Wikidata class (TLA Lemmata in Wikidata 2024), the TLA's January 2018 extract's part of speech,
glosses and reference, and the PNM v6 names whose `tla` field gives the lemma. Royal and divine epithets glossed as
names but tagged as nouns stay out.

## Gauthier's Dictionnaire des noms géographiques

Gauthier's *Dictionnaire* t. 1–6 (Le Caire 1925–1929, public domain) is read from the archive.org scans' OCR text
layer, entry by entry, under the volume and printed page each entry opens on. It is a page finder: the hieroglyphs are
not in the text layer, the transcriptions keep the OCR's slips (ḥ as `l;l` or `J:i`), and 2,625 rows carry flags. Read
the printed page before quoting a form. No row is joined to any place authority.

## Kassite name concordances

The name indexes of seven volumes of Kassite-period and kudurru texts, published 1906–1912 (Clay's YOS 1, BE A 14, BE A 15 and PBS 2/2,
Hinke's BE D 4, Radau's BE A 17/1 and King's *Babylonian Boundary-Stones*), give 9,621 entries. A row is an OCR lead to
the printed page, not a reading. `ocr_status` gives what it was compared with: the page scan (814), Acrobat's
rendering of BE A 14 and BE A 15 (575), or nothing (8,232). Read the form off the page image before citing it.

## Egyptian foreign-name witnesses

An index of Egyptian foreign-name witnesses (locus-aware rows from the Execration Texts, the Kom el-Hetan PWN V Aegean
list, BM EA 5647, Rekhmire TT 100 and the secondary editions of Levantine and Nubian names) is not in this repository:
most of its rows quote editions that are in copyright.

## Place authorities

- Pleiades: current full JSON-LD dump, CC BY 3.0.
- Trismegistos Geo: official table-dump form with all currently offered fields, CC BY-SA 4.0.
- iDAI.gazetteer: bounded cached `/search.json` queries through `tools/ane/query_idai_gazetteer.py`; no bulk crawl.
  It publishes no licence for its place data, so no iDAI records ship; the cache stays in the user's cache folder.

The place crosswalks, identifiers that link PNM places to Pleiades and Trismegistos, are not in this repository.

`query_proper_names.py` searches ORACC, PNM, ProM, the TLA v18 names, Gauthier and the Kassite concordances (`--source oracc`, `pnm`, `prom`, `tla`, `gauthier`, `kassite-concordances`). It distinguishes `attestations`, `name_forms`, and the PNM and ProM `persons`; the older `occurrences` and `entities` spellings remain aliases. Every result carries `entity_scope`. With `--source all`, results are interleaved across matching datasets before applying the global limit.

## Queries

```bash
python3 tools/ane/query_proper_names.py Idrimi --source oracc
python3 tools/ane/query_proper_names.py sbk-ḥtp --source pnm --layer entities --json
python3 tools/ane/query_proper_names.py 'PD 769' --source pnm --layer persons --json
python3 tools/ane/query_proper_names.py Ra.w-ms --source prom --layer persons --exact
python3 tools/ane/query_proper_names.py imn-m-HA.t --source tla --layer name_forms
python3 tools/ane/query_proper_names.py El-Achmounein --source gauthier
python3 tools/ane/query_proper_names.py A-gi-ia --source kassite-concordances --exact

python3 tools/ane/query_idai_gazetteer.py Knossos --limit 10
python3 tools/ane/query_idai_gazetteer.py Knossos Amnisos Phaistos --limit 10
python3 tools/ane/query_place_authorities.py Knossos --authority all
```

A Gauthier row prints its volume and page, a Kassite concordance row its volume's key and printed page: read the
page before citing the form.

For SQL-style searches, use DuckDB directly over `data/ane/place-authorities/*.jsonl` and
`data/share-alike/trismegistos/trismegistos_places.jsonl`. Do not join historical evidence to an external place solely by normalized-name equality.
