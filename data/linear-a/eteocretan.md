---
name: data/linear-a/eteocretan
title: Eteocretan inscriptions
desc: The Eteocretan inscriptions (Dreros, Praisos), one proven fake and one Eteocypriote control, with Gordon's word readings and word analyses.
tags: [data, eteocretan, aegean]
license: CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

Two files, joined by inscription id.

`eteocretan_inscriptions.json` holds `schema_version`, `description`, `provenance` and `inscriptions`, a list of 10
records:

| Field | Content |
| --- | --- |
| `id` | the record id (`ETEOCRETAN_DREROS_1`) |
| `common_name`, `site`, `object_type`, `date`, `script`, `direction` | the object and its text |
| `current_transliteration` | the text, one string per line, in the Greek alphabet with the editors' sigla |
| `greek_parallel_text` | the Greek of a bilingual, or what is known of it |
| `gordon_transliteration`, `gordon_word_readings` | Gordon's text (1966) and his reading of each word, with its basis and constraint |
| `relationship_to_linear_a` | `comparandum_only`, `none_established` or `eteocypriote_control_only` |
| `status` | `SOURCE_BACKED`, `PARTIAL`, `SOURCE_BLOCKED` (known from Gordon alone), `UNCERTAIN_ETEOCRETAN` or `PROVEN_FAKE` |
| `source_refs`, `notes` | the editions, and what the text has not yet been checked against |
| `forgery_evidence` | on the Psychro stone only: who showed it a modern fake, where, and which word analyses it affects |

`eteocretan_word_analysis.json` holds `constraint_type_key` (what each constraint type means) and `words`, 27
analyses keyed by `inscription_id` and `form`: `gordon_meaning`, `root`, `basis`, `constraint_type` and `status`.
The 4 words from the Psychro stone have status `CONTAMINATED_FORGERY` and a `forgery_note`; they are kept so the
record of the forgery is complete, and are not evidence for Eteocretan.
