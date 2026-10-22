---
name: data/linear-a/translations
title: Linear A translations
desc: Translations of Linear A inscriptions, keyed by inscription id, each with a word-by-word analysis.
tags: [data, linear-a, translations]
license: CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

`translations.json` holds `schema_version`, `description`, `dialect_notes` (the dialect and chronology summary) and
`translations`, an object keyed by inscription id (`HT13`, `IOZa2`). One key, `LMP-Spell33`, is the Keftiu spell of
the London Medical Papyrus (BM 10059), which the Linear A corpus does not hold.

| Field | Content |
| --- | --- |
| `site`, `support`, `genre`, `period`, `findspot`, `scribe` | the object and its context, where recorded |
| `words` | the word-by-word analysis, a list in reading order |
| `translation` | the composite translation |
| `confidence` | the inscription's overall tier |
| `status` | "complete", "incomplete", "fragmentary" and the like, on some entries |
| `coverage` | the share of the text read, on a few entries |
| `notes` | context and commentary |
| `source` | the works the text and its readings rest on: one work as a string (`"GORILA"`, the edition, on most entries), or an object mapping each work or scholar to the words or aspects it supplies (`{"Gordon 1966": ["JA-SA-SA-RA-ME"], "di Mino": […]}`); absent where none is recorded |

Translations and readings are di Mino's unless `source` credits another scholar.

Each item in `words`:

| Field | Content |
| --- | --- |
| `linear_a` | the sign group |
| `reading`, `reading_type` | phonetic reconstruction; `reading_type` marks the other kinds (IDEOGRAM, NUMERAL, OPAQUE, FRAGMENT) |
| `gloss`, `meaning`, `translation` | English sense |
| `root`, `layer`, `morphology`, `dialect_variant_of`, `isogloss` | analysis, where given |
| `position`, `quantity` | place in the text and the number it carries, on accounts |
| `confidence`, `confidence_score` | the word's tier |
| `note`, `notes` | evidence; a legible word with no reading ends "No reading." |

A translation counts as complete when `translation` is non-empty and `status` is not "incomplete". The lexicon is
`lexicon.json`; the texts themselves are in the corpus.
