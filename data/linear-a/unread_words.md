---
name: data/linear-a/unread_words
title: Linear A unread words
desc: Every Linear A word of two or more signs with no reading in the lexicon, translations or onomasticon, each with its attestations and a note on the edition's text.
tags: [data, linear-a, unread]
license: CC BY 4.0
created: 2026-10-22T18:30:05Z
updated: 2026-10-22T18:30:05Z
---

`unread_words.json` holds `schema_version`, `description`, `statuses` (the closed list of statuses with their
meanings), `stats` (counts over the corpus and the file), `excluded` (corpus words deliberately left out, each with
the reason) and `entries`, a list keyed by `word`. It is the complement of the lexicon: a corpus word with a reading
in [lexicon.json](lexicon.json), [translations.json](translations.json) or [onomasticon.json](onomasticon.json) has
no entry here. The notes are di Mino's.

| Field | Content |
| --- | --- |
| `word` | the sign group as written in the corpus, signs joined by hyphens; a broken group keeps its brackets (`]A-PA-[`) and a lost sign is `[?]` |
| `signs` | the number of signs |
| `status` | `unread` (nothing known), `role_only` (classed by role only, no reading) or `edge_overlap` (a lexicon word sits at one edge) |
| `role` | the role a `role_only` word plays in its document (`personal_name`, `toponym`, `administrative heading`…) |
| `translation_label` | the label the translations give the word, where they give one |
| `edge_overlap` | the lexicon word at the edge (`lexicon_word`) and its tier |
| `frequency`, `attestations`, `sites`, `cross_site` | occurrences, inscription ids (always a list), site names, and whether it crosses sites |
| `surface_damage` | for each attestation whose Unicode word carries the damage marker, where it sits: `start`, `interior`, `end` |
| `note` | the edition's text of the word, with its dotted signs, breaks and rivals |

A note ends with its verdict: "No reading." for a legible word that no one reads, "Not readable." for a word that is
broken or illegible, and "Not a word." for a run of signs that is no sign group. A broken group may be part of a
longer word, so its note says what it fits without reading it. `surface_damage` records damaged surface, not
necessarily lost signs.

Inscription ids match [corpus.json](corpus.json). `tools/linear_a/validation/check_unread_words.py` reports where
the file and the corpus disagree.
