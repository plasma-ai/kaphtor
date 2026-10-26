---
name: data/contact/amarna_canaanite
title: Amarna Canaanite
desc: The Canaanite words, place names and divine names of the Amarna letters, from ORACC's aemw/amarna glossaries.
tags: [data, contact, canaanite, amarna]
license: CC0 1.0 (ORACC's data) AND CC BY 4.0 (our changes)
created: 2026-10-25T22:00:00Z
updated: 2026-10-25T22:45:00Z
---

`amarna_canaanite.jsonl` holds 247 entries drawn from the glossaries of ORACC's aemw/amarna project: 103 Canaanite
words from the `qca` glossary, and from the `qpn` glossary 136 place names and 8 divine names.

| Field | Content |
| --- | --- |
| `id` | `amarna:`, the kind (`qca`, `places`, `divine`), the normalized form and a running number |
| `form` | for a word, the form as transliterated in the letters (`a-ba-da-at`); for a name, ORACC's citation form, the same as `cf` |
| `form_original` | the cuneiform spelling, on one entry (ᵈIŠTAR) |
| `cf`, `normalized`, `match_keys` | ORACC's citation form; for a word its consonants (`ʾbd`), for a name the name lowercased with its vowels (`amon`); and the keys the root index matches on |
| `meaning`, `pos` | ORACC's gloss and part of speech (`N`, `V`, `GN`, `DN`, …); where ORACC gives a name no gloss, `meaning` repeats the name |
| `instance_count` | ORACC's count of lemmatized instances of the citation form across the corpus |
| `semantic_domain`, `source_corpus`, `source_refs`, `review_status` | domain tags, the project and glossary, and the row's review state; every row is `machine_imported` |

ORACC writes some names as alternatives joined by "OR" (`AdduORBaʿluORTeššub`). One entry, the divine name written
ᵈIŠTAR, was restructured by hand from ORACC's `AstarteORIštarORŠauška`: its `meaning`, its `normalized` form
(`ištar`, so its id no longer matches it), its match keys (`ʿaštart`, `astarte`, `ištar`, `šauška` and their plain
spellings, in place of ORACC's `{d}udar`) and its `form_original` are ours, and its `notes` field says so.

**Source.** The aemw/amarna Project, ORACC, 2014– (oracc.museum.upenn.edu/aemw/amarna). The project's web pages
carry CC BY-SA 3.0; the open-data download this file is built from (glossaries `qca` and `qpn`, 2024-07-05) states
"This data is released under the CC0 license", so ORACC's rows here are CC0 and our changes are CC BY 4.0. Credit
the project all the same. `tools/linear_a/ingest/ingest_oracc_amarna.py` gives the same 247 entries, with the same
counts, from that download. Two things differ in the private build: a second `semantic_domain` tag on 103 entries
(by keyword where one matches, otherwise from the part of speech), and the hand changes to the ᵈIŠTAR entry.

**Not included.** Seven rows the private build takes from Anchor Bible commentaries, and one note drawn from them,
with the review status it gave its row.
