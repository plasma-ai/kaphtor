---
name: docs/corpora/proper-name-and-place-authorities
title: Proper names and place authorities
desc: ORACC QPN, PNM v6, the Egyptian foreign-name witnesses and the place authorities, and why a place match identifies a place but never counts as linguistic evidence.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Proper names and place authorities

This layer separates textual attestations from aggregated name entities and from modern identity authorities. A Pleiades, Trismegistos, or iDAI match can identify a place; it cannot supply a historical spelling or count as linguistic evidence.

## Local datasets

This repository ships only the sets under `data/`; each folder's index lists them.

| Layer | Scope | Local output |
|---|---:|---|
| ORACC QPN occurrences | 222,959 edition-token rows; 215,483 canonical-token signatures; 30,599 name-form aggregates | `data/ane/oracc/` (not in this repository) |
| PNM v6 | 60,488 attestations; 7,933 names; 3,828 person dossiers; 21,700 spellings; 4,689 titles | `data/ane/pnm-v6/` |
| Place authorities | 42,388 Pleiades; 65,130 TM Geo | `data/ane/place-authorities/` (Trismegistos in `data/share-alike/trismegistos/`) |

Mutable counts and hashes are authoritative only in each `MANIFEST.json`.

## ORACC QPN

`occurrences.jsonl` preserves the project, archive, edition, object, line, token reference, language, written form, normalized form, damage flag, period, genre, and provenience. Its 222,959 rows are edition-token records, **not independent witnesses**: parallel ORACC projects can edit the same object token. The 215,483 `canonical_token_key` signatures are duplicate-control candidates, not automatic identity adjudications. `entities.jsonl` is a name-form aggregate search layer and never replaces the occurrence rows.

QPN labels remain intact. The broad place total is the sum of `GN`, `SN`, `TN`, `WN`, `QN`, and `FN`; those categories remain independently queryable. `PN` and `RN` likewise remain distinct.

## PNM version 6

The source is the official Zenodo record, DOI `10.5281/zenodo.15806808`, CC BY 4.0. The downloaded SQL matches the published MD5 `fb705737c7b27456e9b50d578c3ea1f5`. Coverage runs from Mentuhotep II through Amenhotep III.

The extractor retains all 32 populated `INSERT ... VALUES` tables in the v6 dump, including primary keys, alternative readings, name types, interpersonal bonds, title relations, workshops, attestations, names, spellings, persons/dossiers, titles, inscriptions, objects, inventory numbers, bibliography, collections, and places. `attestations_enriched.jsonl` is a convenience join; `tables/*.jsonl` remains the source-faithful layer.

## Egyptian foreign-name witnesses

An index of Egyptian foreign-name witnesses (43 locus-aware rows from the Execration Texts, the Kom el-Hetan PWN V
Aegean list, BM EA 5647 and Rekhmire TT 100) is not in this repository.

## Place authorities

- Pleiades: current full JSON-LD dump, CC BY 3.0.
- Trismegistos Geo: official table-dump form with all currently offered fields, CC BY-SA 4.0.
- iDAI.gazetteer: bounded cached `/search.json` queries through `tools/ane/query_idai_gazetteer.py`; no bulk crawl.
  It publishes no licence for its place data, so no iDAI records ship; the cache stays in the user's cache folder.

The place crosswalks, identifiers that link PNM places to Pleiades and Trismegistos, are not in this repository.

`query_proper_names.py` distinguishes `attestations`, `name_forms`, and PNM `persons`; the older `occurrences` and `entities` spellings remain aliases. Every result carries `entity_scope`. With `--source all`, results are interleaved across matching datasets before applying the global limit.

## Queries

```bash
python3 tools/ane/query_proper_names.py Idrimi --source oracc
python3 tools/ane/query_proper_names.py sbk-ḥtp --source pnm --layer entities --json
python3 tools/ane/query_proper_names.py 'PD 769' --source pnm --layer persons --json

python3 tools/ane/query_idai_gazetteer.py Knossos --limit 10
python3 tools/ane/query_idai_gazetteer.py Knossos Amnisos Phaistos --limit 10
python3 tools/ane/query_place_authorities.py Knossos --authority all
```

For SQL-style searches, use DuckDB directly over `data/ane/place-authorities/*.jsonl` and
`data/share-alike/trismegistos/trismegistos_places.jsonl`. Do not join historical evidence to an external place solely by normalized-name equality.
