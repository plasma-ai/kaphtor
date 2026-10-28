---
name: data/contact
title: Contact lexica
desc: The open Semitic contact lexica that the root index links to the Proto-Semitic roots: Hebrew, Aramaic, Amarna Canaanite, Syriac and Akkadian, each with a datasheet.
tags: [data, contact]
created: 2026-10-25T22:00:00Z
updated: 2026-10-26T00:26:00Z
---

# Contact lexica

[[data/_index|..]]

[[data/contact/akkadian_lexicon|akkadian_lexicon]]: ORACC's CAMS/GKAB Akkadian glossary in the root index's Akkadian slot, with ḫ restored in the keyed form and every ORACC name class marked as a name.

[[data/contact/akkadian_lexicon.jsonl|akkadian_lexicon.jsonl]]: The Akkadian entries (6,233); datasheet `akkadian_lexicon.md`; CC0 1.0.

[[data/contact/amarna_canaanite|amarna_canaanite]]: The Canaanite words, place names and divine names of the Amarna letters, from ORACC's aemw/amarna glossaries.

[[data/contact/amarna_canaanite.jsonl|amarna_canaanite.jsonl]]: The Amarna Canaanite entries (247); datasheet `amarna_canaanite.md`; CC0 1.0 (ORACC's data) and CC BY 4.0.

[[data/contact/aramaic_lexicon|aramaic_lexicon]]: Syriac roots from the Aramaic Root Atlas, with their glosses and the Hebrew and Arabic cognates it lists.

[[data/contact/aramaic_lexicon.jsonl|aramaic_lexicon.jsonl]]: The Aramaic entries (1,647); datasheet `aramaic_lexicon.md`; Apache-2.0.

[[data/contact/hebrew_lexicon|hebrew_lexicon]]: The lexemes of STEPBible's TBESH, Hebrew with its Biblical Aramaic, with Brown–Driver–Briggs's glosses and the cognates it names.

[[data/contact/hebrew_lexicon.jsonl|hebrew_lexicon.jsonl]]: The Hebrew entries (8,763); datasheet `hebrew_lexicon.md`; CC BY 4.0.

[[data/contact/syriac_lexicon|syriac_lexicon]]: The Classical Syriac words of English Wiktionary that name their root, with the root in Latin letters and the Wiktionary glosses.

[[data/contact/syriac_lexicon.jsonl|syriac_lexicon.jsonl]]: The Syriac entries (1,391); datasheet `syriac_lexicon.md`; CC BY-SA 4.0.

***

`tools/core/root_index.py` reads eleven contact lexica (`LEXICA`). These five ship. Two of them fill the Syriac and
Akkadian slots with open lexica in place of the private build's SEDRA Syriac and its Huehnergard-glossary and Anchor
Bible Akkadian, so their lexemes are not the private ones. The other six (Ugaritic, Geʿez, South Arabian,
Phoenician, Amorite, the Phoenician names) rest on dictionaries or databases whose terms bar redistribution or allow
only non-commercial use, so build the index with `--allow-missing`; each absent file is recorded as missing in the
index's provenance. The statistic runs on root clusters (A17 of
[the pre-registration](../../docs/shoresh-preregistration.md)), and a lexeme that joins a cluster brings its keys
into d\*, its language into branch breadth and its gloss into the semantic gate (A18). A missing lexicon therefore
can move d\*, p and the verdicts: a run on this checkout is not the private configuration the baseline was measured
on. On the 326 unread words the engine scored when the pre-registration measured them, the two gave the same
verdicts (its note has the counts).
