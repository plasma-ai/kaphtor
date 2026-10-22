---
name: data/linear-a/onomasticon
title: Linear A onomasticon
desc: One entry per Linear A name, toponym, theonym, gentilic or title, with its type, its linguistic affiliation and the evidence for it, and every document where it appears.
tags: [data, linear-a, onomasticon]
license: CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

`onomasticon.json` holds `schema_version`, `description`, the closed lists `affiliation_classes`, `types` and
`provenance_levels`, `stats` (counts by type, affiliation and provenance) and `entries`, a list keyed by `token`. It
holds names only: a word the lexicon reads as a commodity, a verb or a phrase has no entry here, and neither has a
group no one can read. Readings are di Mino's unless the note names another scholar.

| Field | Content |
| --- | --- |
| `token` | the sign group as written, signs joined by hyphens (`KU-PA₃-NU`) |
| `normalized` | the token in lower case without hyphens or asterisks, subscripts as digits, for matching |
| `type`, `type_confidence` | personal name, toponym, theonym, gentilic, toponym or gentilic (`toponym_gentilic`) or title, and the tier of that classification |
| `affiliation`, `affiliation_confidence` | the language the name belongs to (`semitic`, `hurrian`, `egyptian`, `unknown`…), and its tier |
| `affiliation_evidence` | what sets the affiliation: `lexicon_reading`, `contact_hit` or `none` |
| `lexicon_ref` | the lexicon entry that reads the name, or the base word of a derived form, where there is one |
| `reading`, `meaning` | the lexicon's reading and sense, copied onto the entry; on an entry with no lexicon link, di Mino's reading, with affiliation `unknown` |
| `contact_ref` | the id of the contact-language record the name matches (`am_gelb_n_04148`, `ug_dulat_0229`) |
| `frequency`, `attestations`, `sites`, `cross_site` | occurrences, inscription ids (always a list), site names, and whether it crosses sites |
| `genre_supports` | occurrences by kind of object (`Tablet`, `Roundel`, `Stone vessel`…) |
| `position_summary` | where the token stands in its documents: what precedes it, and how often it heads one |
| `co_occurring_known` | lexicon words found in the same documents, with their readings |
| `weak_cognates` | root comparisons too weak to set the affiliation: `root`, `language` and `distance` (0 to 1), with `meaning` and `source` where given |
| `linear_b_comparanda` | the same or a near name in Linear B, with its tablets |
| `provenance` | how the entry entered the file: `manual` by hand, `auto` from the corpus |
| `bucket` | how the corpus sort classed the token: `onomastic`, `ambiguous` or `lexical` |
| `note` | evidence, rivals and parallels |

The tiers are those of the lexicon: CONFIRMED, PROBABLE, CANDIDATE and SPECULATIVE. An entry's affiliation follows
the language layer of its lexicon reading and never stands above that reading's tier. An entry with no reading is
`unknown`; `stats.by_affiliation.unknown` counts those entries by the state of their witnesses (intact, fragmentary,
edge-damaged, no witness).

Inscription ids match [corpus.json](corpus.json) and [translations.json](translations.json), and `lexicon_ref`
matches `word` in [lexicon.json](lexicon.json). A word read only on broken groups appears here while the lexicon
keeps it; the broken groups themselves are recorded with the unread words.
