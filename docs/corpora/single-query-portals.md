---
name: docs/corpora/single-query-portals
title: Bounded external-corpus queries
desc: The one-query clients for DiCoNab, DEAPS, Elephantine and RSTI, what each request may fetch, and what the parsers keep.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Bounded external-corpus queries

These clients support case-by-case scholarly consultation where a public,
stable request mechanism has been verified. They are not harvesters. Each
invocation requires a substantive query or exact identifier, caches the parsed
response, and does not follow pagination, media, TEI links, or linked records.

## Capability matrix

| Resource | Single-query status | Command / boundary |
|---|---|---|
| DiCoNab | Supported case by case | `query_diconab.py`: one occurrence page, suggestion call, or exact inscription; the full corpus still requires permission |
| DEAPS | Supported | `query_deaps.py`: one public search page or exact textual object |
| Elephantine | Supported | `query_elephantine.py`: one object-catalogue query, object page, or text page; exposed TEI links are not followed |
| RSTI | Supported by exact identifier | `query_rsti.py`: one public OCHRE UUID response; linked UUIDs are not followed |
| Mari / ARCHIBAB | No client | Its terms prohibit massive use to build or enrich a database; consult it on its own site |
| CAL Old/Official Aramaic | Not automated | CAL's interface may be consulted manually, but this project does not scrape it; request a tagged-text export for systematic work |
| CIP / PhDB | Not possible | The official project description is public, but no public query database or supported endpoint was reachable or licensed when checked |

## Commands

```bash
python3 tools/ane/query_diconab.py mlk --field root --match exact
python3 tools/ane/query_diconab.py --inscription 3287

# DEAPS: object/title/text/translation/collection/language/script fields
python3 tools/ane/query_deaps.py 'TAD D.17.1' --field name
python3 tools/ane/query_deaps.py 'ברזמדנא' --field text --language Aramaic
python3 tools/ane/query_deaps.py --object 11076

# Elephantine: the quick search covers object-catalogue metadata, not editions
python3 tools/ane/query_elephantine.py 'Cairo EM JdE 36448'
python3 tools/ane/query_elephantine.py --object 309606
python3 tools/ane/query_elephantine.py --text 309606

# RSTI: exact public OCHRE UUID only
python3 tools/ane/query_rsti.py 98ef62eb-5eea-4b82-83a9-ff52cfef76f1
python3 tools/ane/query_rsti.py --menu
python3 tools/ane/query_rsti.py 2a414954-e077-496b-8b06-a9d0cd417eba --find 'RS 1.001'
```

All clients accept `--json` and `--refresh`. Identical calls use the cache under `$XDG_CACHE_HOME/kaphtor/` unless
refreshed. Live calls have a one-second minimum delay; the default is 1.5 seconds.

## What the parsers retain

- DEAPS: record identity, title, public metadata, displayed edition/translation
  blocks, and record citation. Search can target Unicode text and translation;
  it is therefore useful for personal and place names when the spelling is
  already known.
- Elephantine: object identity, metadata, record-level license and citation,
  displayed edition/translation blocks, TEI URL, and explicitly tagged
  `persName` / `placeName` values with their source references. The TEI link is
  reported but not fetched automatically.
- RSTI: entity identity and type, context path, description, record license,
  properties, notes, immediate items, and linked UUID values. No linked UUID is
  dereferenced.

## Rights and citation boundary

- ARCHIBAB prohibits massive use to build or enrich a database without the
  publication director's agreement.
- DiCoNab permits scholarly consultation and partial reproduction with
  citation; comprehensive acquisition or redistribution requires supported
  access. Its rules are in `tools/ane/README.md`.
- DEAPS publishes a selected web layer but does not state a corpus-data license.
- Elephantine licenses datasets and media item by item; retain the record's
  own license and do not infer that an image license follows the dataset.
- RSTI's site states CC BY-NC-ND 4.0, while an OCHRE response may include its
  own availability license. Preserve both and prefer the narrower applicable
  condition.
- CAL and CIP remain manual/request-only for systematic use.
