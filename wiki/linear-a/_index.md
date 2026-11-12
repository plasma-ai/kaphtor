---
name: wiki/linear-a
title: Linear A
desc: Inscriptions, words and signs, with the generated ledgers.
created: 2026-10-22T18:14:10Z
updated: 2026-11-13T15:03:19Z
---

# Linear A

[[wiki/_index|..]]

[[wiki/linear-a/by_root|by_root]]: Lexicon entries grouped by a consonantal browse key of their root.

[[wiki/linear-a/by_scribe|by_scribe]]: Every scribe to whom an edition assigns documents, with the records and the source.

[[wiki/linear-a/by_sign|by_sign]]: Every syllabic and logographic sign with the lexicon words that use it.

[[wiki/linear-a/by_site|by_site]]: Records, documents, translations and lexicon words for every site.

[[wiki/linear-a/counts|counts]]: Headline counts of the Linear A record, computed from the data files.

[[wiki/linear-a/inscriptions/_index|inscriptions/]]: One generated page per corpus record, filed by site and GORILA series.

[[wiki/linear-a/signs/_index|signs/]]: The syllabic signs, logograms and fractions, each with its value and the evidence for it.

[[wiki/linear-a/standing|standing]]: Every reading in the lexicon, by confidence tier, with its score.

[[wiki/linear-a/unread_signs|unread_signs]]: The single and combined signs with no lexicon entry, by the untranslated records each one alone leaves unread.

[[wiki/linear-a/words/_index|words/]]: One generated page per form, joining the lexicon, the onomasticon and the unread words, filed by first sign.

***

<!-- BEGIN kaphtor:summary -->
The Kaphtor Lexicon sets out the Linear A record as read in kaphtor: 680 words drawn from 1,719 corpus records
at 59 sites, each with its reading, the evidence for it, its tier and its rivals. The readings follow the Semitic
decipherment of Cyrus Gordon and Tom di Mino, in which Minoan is Tinitic, an archaic branch of Central Semitic written
in the syllabary whose values Linear B inherited. 599 words read as Semitic, 36 as Hurrian, 14 as
Egyptian and 9 as Aegean loans or names, and 572 derive their Proto-Semitic root from its associated
database, so a reading runs from the tablet to its cognates.

The tier carries the doubt. 19 readings are CONFIRMED, where logogram, sound and arithmetic agree; 75
are PROBABLE, 252 CANDIDATE and 334 SPECULATIVE, and a reading rises one tier at a time, on new
evidence. The words are filed by field: personal names (243), commodities (96), administrative
terms (68), personnel (62), ritual (65), toponyms (47) and divine names
(32). Beside them stand one page for every inscription, 509 of 591 translations, the
380 names of the onomasticon, the signs with their 37 resolved and proposed values, and the 373
legible words that have no reading yet, each with its witnesses. 100 of them are undamaged in every
witness.
<!-- END kaphtor:summary -->

Each page is generated from the files in `data/linear-a/` by `tools/views/`: the inscription, word and sign pages by
`render.py`, and the ledgers (`counts`, `standing`, `by_site`, `by_root`, `by_sign`) by `ledgers.py`, which computes
every number from the data.
