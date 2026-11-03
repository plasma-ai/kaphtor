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
| `proto_semitic` | the `semitic_roots.json` record the reading rests on, `{"id", "form"}`, or a list of them for a compound; absent where no record fits and on grammatical endings |
| `cognates` | cognate forms by language (an object), or a sentence |
| `tier`, `confidence` | 4 CONFIRMED, 3 PROBABLE, 2 CANDIDATE, 1 SPECULATIVE |
| `confidence_score` | a score from 0 to 1 that ranks entries within a tier |
| `semantic_field`, `language_layer` | classification: `semantic_field` is the word's subject area, one value on every entry; `language_layer` is the language the word reached Linear A through, on every entry: `Semitic`, `Hurrian`, `Middle Egyptian`, `Anatolian`, `Indo-European`, `Sumerian`, `Aegean` or `logogram` |
| `tags` | the dictionary filter, on every entry: a list of values from one fixed vocabulary for word class, name type and form (`noun`, `personal_name`, `hapax`, `compound`…); `loanword` marks a word borrowed whole, `loanblend` a native derivative on a borrowed base, whose root names the base's language (KU-PA₃-NU Kubānu, Semitic -ān- on Sumerian Kubaba) |
| `language_family` | the family of the word's origin, on every entry: `Semitic`, `Hurro-Urartian`, `Egyptian`, `Indo-European` or `Sumerian`, or null under `Aegean` and `logogram`. It follows the layer (`Semitic`, `Hurrian` Hurro-Urartian, `Middle Egyptian` Egyptian, `Indo-European`, `Sumerian`) except under `Anatolian`, where the route and the origin can part, and the family is `Semitic` or `Indo-European` |
| `attestations` | inscription ids, always a list |
| `sites` | site names, where recorded |
| `note` | evidence, rivals and parallels; sections are separated by ` \|\| ` |
| `source` | who proposed the reading: "di Mino", another scholar's work, or both |
| `reviewer`, `outside_scholar` | on CONFIRMED entries: the reviewer, and the outside scholar whose published reading matches |
| `alternative_readings`, `related_forms`, `corpus_forms`, `root_meaning`, `phonological_notes`, `cross_references`, `sigla_contested` and `sigla_note` | present on a few entries |

Inscription ids match `translations.json` and the corpus, except `LMP-Spell33`, the Keftiu spell of the London
Medical Papyrus (BM 10059), which the Linear A corpus does not hold. REJECTED readings are not shipped.
