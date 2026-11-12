---
name: data/linear-a/unread_signs
title: Linear A unread signs
desc: Every single sign or combination of signs that stands as an entry in the Linear A corpus and has no entry in the lexicon, each with its attestations and what is on file for it.
tags: [data, linear-a, unread]
license: CC BY 4.0
created: 2026-11-10T18:44:01Z
updated: 2026-11-10T18:44:01Z
---

`unread_signs.json` holds `schema_version`, `description`, `statuses` and `kinds` (the closed lists with their
meanings), `stats` (counts over the file), `excluded` (corpus tokens deliberately left out, each with the reason) and
`entries`, a list keyed by `sign`. It is the sister of [unread_words.json](unread_words.json), which holds words of
two or more signs: a sign standing alone on a sealing, a ligature, a vessel sign or a logogram is listed here until
[lexicon.json](lexicon.json) reads it. A proposed reading is entered in the lexicon at its tier, and the sign then
leaves this file.

| Field | Content |
| --- | --- |
| `sign` | the token as written in the corpus: one sign (`I`, `*164`), a ligature (`*301+*311`), a vessel sign (`*409-VS`), a logogram (`GAL`) or a logogram joined to a sign (`SA-VIN`) |
| `kind` | `syllabogram`, `sign` (a starred sign), `ligature`, `vessel`, `logogram` or `compound` |
| `status` | `unread` (nothing on file), `component_read` (a combined sign with a component the lexicon reads) or `value_on_file` (a value in `sign_values.json` or in a translation, but no lexicon entry) |
| `components`, `read_components` | the parts of a combined sign, and those the lexicon reads |
| `on_file` | where a value stands: the file, the translation record where there is one, the value, and its standing where the file gives one |
| `frequency`, `attestations`, `sites`, `cross_site` | undamaged occurrences, inscription ids (always a list), site names, and whether it crosses sites |
| `note` | the sign's contexts in the corpus and what the files hold for it, most ending "No reading." or "No lexicon entry."; written for the signs that hold back the most records and for the ligatures with an unnamed component, empty on the rest |

A token counts only when it is undamaged and yields no run of two or more syllabic signs. `on_file` leaves out a
translation gloss that only restates the components ("cyperus with K") or labels the sign's place ("section
heading").

Inscription ids match [corpus.json](corpus.json). `tools/linear_a/validation/check_unread_signs.py` reports where
the file and the corpus disagree, and with `--rank` lists the signs by the untranslated records each one alone
leaves unread.
