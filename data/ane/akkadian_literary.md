---
name: data/ane/akkadian_literary
title: Akkadian literary glossary
desc: 6,233 Akkadian words and proper nouns from ORACC's CAMS/GKAB glossary, with their meanings, parts of speech and match keys; CC0 1.0.
tags: [data, ane, akkadian]
license: CC0 1.0
created: 2026-10-22T19:27:15Z
updated: 2026-10-22T19:27:15Z
---

`akkadian_literary.jsonl` holds one record per glossary entry of ORACC's CAMS/GKAB project (The Geography of
Knowledge in Assyria and Babylonia: first-millennium scholarly and literary tablets), 6,233 in all: 2,979 nouns, 711 verbs, 632 adjectives, 629 divine names, 518
personal names and the rest. `akkadian_literary.index.json` maps each match key to the ids of the entries it matches;
it is derived from the glossary and holds nothing else.

| Field | Content |
| --- | --- |
| `id` | `oracc:cams-gkab:` and the ORACC entry id |
| `language`, `source_corpus` | `Akkadian`, `ORACC cams/gkab` |
| `form_original`, `cf` | the citation form as ORACC gives it |
| `normalized` | the citation form in lower case without diacritics, for matching |
| `match_keys` | the normalized citation form and the attested spellings, for lookup |
| `meaning` | ORACC's guide word and sense |
| `pos` | ORACC's part of speech (`N`, `V`, `AJ`, `DN`, `PN`…) |
| `semantic_domain` | a coarse domain label |
| `source_refs` | the source, `ORACC CAMS/GKAB` |
| `review_status` | `machine_imported`: read from ORACC's glossary without hand review |
| `frequency` | the entry's attestations in the project's texts |

ORACC releases its project data under CC0 1.0, recorded in each package's metadata; cite the project as ORACC asks.
`tools/ane/aneq.py` reads this file.
