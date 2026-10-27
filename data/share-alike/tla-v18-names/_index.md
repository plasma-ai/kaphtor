---
name: data/share-alike/tla-v18-names
title: TLA v18 names
desc: The 9,186 proper-name tokens of the Thesaurus Linguae Aegyptiae's Original Earlier Egyptian sentences (corpus v18), with their hieroglyphs and dates, under 1,644 lemmas, CC BY-SA 4.0.
tags: [data, egyptian, onomastics]
license: CC BY-SA 4.0
created: 2026-10-27T17:22:41Z
updated: 2026-10-27T17:22:41Z
---

# TLA v18 names

[[data/share-alike/_index|..]]

[[data/share-alike/tla-v18-names/MANIFEST.json|MANIFEST.json]]: The dataset version, licence and citation, the name-set, alignment and join rules, counts and checksums.

[[data/share-alike/tla-v18-names/lemmas.jsonl|lemmas.jsonl]]: 1,644 name lemmas, with their forms and hieroglyphic spellings counted, date span, Wikidata class and PNM v6 names.

[[data/share-alike/tla-v18-names/occurrences.jsonl|occurrences.jsonl]]: 9,186 name tokens, each with its form, hieroglyphs, gloss, date range, sentence transliteration and German translation.

***

The source is the TLA's Original Earlier Egyptian sentences, corpus v18 (premium, dataset card v1.1, 2024-02-16;
ed. T. S. Richter and D. A. Werning, BBAW, and H.-W. Fischer-Elfert and P. Dils, SAW): 12,773 sentences dated from
−3350 to −1539. A token is a name when the dataset tags it UPOS PROPN. Nouns glossed as royal or divine names
(nṯr-ꜥꜣ, nswt-bꞽ.tꞽ, ḫnt.ꞽ-ꞽmn.tꞽw) are epithets and are left out, and the MANIFEST counts them.

Lemma ids are the TLA's own (`tla:<lemma id>`). A token's id is `tla18:<row>:<token>`, its row of the dataset file
and its place in the sentence, because the dataset carries no text ids. The joins are all on the lemma id:

- Wikidata classes come from TLA Lemmata in Wikidata 2024 (263 lemmas).
- The part of speech, glosses and reference come from the TLA's January 2018 extract (aed-tei, CC BY-SA 4.0).
- `pnm_name_ids` names the PNM v6 names whose own `tla` field gives the lemma.

TLA writes yod as ꞽ (U+A7BD). One token the dataset tags as a name, `tla18:12615:10`, is the noun nṯr, as its
sentence's token 5 is. It is left out, and the MANIFEST gives the basis.
