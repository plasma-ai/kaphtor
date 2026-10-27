---
name: data/linear-a/lexicon
title: Linear A lexicon
desc: One entry per Linear A word, logogram or sign group, with its reading, meaning, root, cognates, tier and attestations.
tags: [data, linear-a, lexicon]
license: CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

`lexicon.json` holds `schema_version`, `description`, `confidence_levels` (the four tiers, defined in words) and
`entries`, a list keyed by `word`. Readings are di Mino's unless `source` names another scholar.

| Field | Content |
| --- | --- |
| `word` | the sign group as written, signs joined by hyphens (`KU-NI-SU`, `*23M`) |
| `reading` | phonetic reconstruction, or null where none is proposed |
| `meaning` | English gloss |
| `root` | consonantal root, where one is proposed |
| `cognates` | cognate forms by language (an object), or a sentence |
| `tier`, `confidence` | 4 CONFIRMED, 3 PROBABLE, 2 CANDIDATE, 1 SPECULATIVE |
| `confidence_score` | a score from 0 to 1 that ranks entries within a tier |
| `semantic_field`, `category`, `language_layer` | classification; `language_layer` names the language the reading draws on |
| `language_family` | the family over `language_layer`, on every entry: `Semitic` (NWS, Akkadian, Eblaite and the mixed Semitic labels), `Hurro-Urartian` (Hurrian), `Egyptian`, `Indo-European` (Anatolian, Indo-Aryan), `Afroasiatic` (NWS or Egyptian), or null for logograms, Aegean and substrate words, contact words and unresolved labels |
| `attestations` | inscription ids, always a list |
| `sites` | site names, where recorded |
| `note` | evidence, rivals and parallels; sections are separated by ` \|\| ` |
| `source` | who proposed the reading: "di Mino", another scholar's work, or both |
| `reviewer`, `outside_scholar` | on CONFIRMED entries: the reviewer, and the outside scholar whose published reading matches |
| `alternative_readings`, `related_forms`, `corpus_forms`, `root_meaning`, `phonological_notes`, `parallels`, `cross_references` | present on a few entries |

Inscription ids match `translations.json` and the corpus, except `LMP-Spell33`, the Keftiu spell of the London
Medical Papyrus (BM 10059), which the Linear A corpus does not hold. REJECTED readings are not shipped.
