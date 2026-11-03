---
name: data/linear-a/rival-roots
title: Rival-language root keys
desc: The Egyptian, Luwian, Hurrian and Hattic root keys the competitor null rescores every Semitic match against, each with its form and its citations or source labels.
tags: [data, linear-a, competitors, egyptian, luwian, hurrian, hattic]
license: CC BY-SA 4.0 AND CC BY 4.0, with the ACLT, TIED and Brill terms set out below
created: 2026-10-25T22:00:00Z
updated: 2026-11-02T22:00:00Z
---

Four files of keys for the competitor null (§2, A15 and, for Hattic, A23 of
[the pre-registration](../../docs/shoresh-preregistration.md)), which `tools/core/competitors.py` reads. Each holds the entries that the default run uses: those that give a key under
A15 and that A15's name test does not flag. The private files these are exported from give the same key spaces, key
for key and entry number for entry number, which `tests/linear_a/test_rival_roots.py` pins along with each file's
exact content.

| File | Entries | Keys | Fields |
| --- | --- | --- | --- |
| `egyptian_roots.json` | 3,053 | 3,011 | `Number`, `Middle_Egyptian`, `Consonantal_Root`, `Sources` |
| `luwian_roots.json` | 1,677 | 1,441 | `Number`, `Proto-Luwian`, `Consonantal_Root`, `Analogue_Labels` |
| `hurrian_roots.json` | 129 | 94 | `Number`, `Hurrian`, `Consonantal_Root`, `Category`, `Sources` |
| `hattic_roots.json` | 299 | 232 | `Number`, `Hattic`, `Consonantal_Root`, `Category`, `Sources` |

No entry carries its meaning: the files give the form, the key and where the form is cited.

**Names.** The name test reads an entry's meaning, name elements and semantic field, which are not shipped, so here it
flags nothing and `--names` changes nothing. In the private run `--names` adds the flagged entries (245 Egyptian,
369 Luwian, 562 Hurrian and 23 Hattic keys); that run cannot be reproduced from these files. The test misses some names, and
they are in both key spaces: the 726 Persons and Names of the Middle Kingdom entries, 14 Egyptian royal names written
"(PN/RN; …)" (Thutmose, Amenhotep, Ramesses, Hatshepsut) and about ten Luwian ruler and place names (Warpalawa,
Muwatalli, Karkamiš). Five Hurrian entries sit at the edge: 51–54 are kinship words (father, mother, brother, wife)
that also serve as name elements, and 90 is the title maryannu. Ethnics count as names for every competitor under
A23, so 89, the ethnic Ḫurri, is no longer shipped.

**Egyptian.** 2,202 entries come from Wiktionary's Egyptian lemmas (through kaikki.org), CC BY-SA 4.0, so this file
is under CC BY-SA 4.0. 726 come from the first release of Persons and Names of the Middle Kingdom (2018, Zenodo
10.5281/zenodo.1411392, CC BY 4.0), each with its `personal_names_id` and Ranke reference. That release predates
version 6 in `data/ane/pnm-v6/`: 16 of its ids are not in version 6, and 153 forms differ from version 6's. The
other 125 cite Faulkner's *Concise Dictionary*, Gardiner's *Egyptian Grammar* and sign list, Allen, Erman and
Grapow's *Wörterbuch*, the TLA and Ranke, and works on Egyptian onomastics and loanwords (Jones 1988, Takács, Noonan
2016, Cerqueglini 2022, Astour, Albright, Bernal); 60 of these give no page, section or sign, and three (2338–2340)
name only a group of sources ("TLA/Wb source family", "Egyptian group-writing source family").

**Luwian.** 1,539 entries cite the vocabularies of the Annotated Corpus of Luwian Texts (ACLT, Ilya Yakubovich,
web-corpora.net/LuwianCorpus), 110 the Luwian and Common Anatolian glossary of The Indo-European Database
(tied.verbix.com), 20 of them both; 3 cite Wiktionary. Of the 45 that cite none of these, 16 cite Hawkins's *Corpus
of Hieroglyphic Luwian Inscriptions*, Melchert's *Cuneiform Luwian Lexicon*, Beckman, Bryce and Cline's *Ahhiyawa
Texts*, the Karatepe bilingual or a group of Hittite and Anatolian sources, and 29 carry only the language of an analogue ("Hittite", "Cuneiform Luwian"). `Analogue_Labels` gives these labels: a source (ACLT1 with
its script, Verbix TIED, Wiktionary, Hawkins CHLI, Melchert CLL) or the language of an analogue (Hittite, PIE, Lycian,
Palaic). Terms: ACLT states no licence; it describes itself as a work in progress whose interpretations are not
recommended for direct citation, and asks to be credited with its URL. TIED describes itself as a non-commercial
project and states no licence. Wiktionary's entries are CC BY-SA 4.0, so the file carries that licence for them, and
the entries give only the form, its consonantal key and these labels.

**Hurrian.** 120 of the 129 entries cite Laroche's *Glossaire de la langue hourrite* by page. Others cite Wegner's
*Einführung* by section (68), Richter's *Bibliographisches Glossar* by headword (38), Campbell's grammar by glossary
or chapter (32), Wilhelm (17), Gelb's *Nuzi Personal Names* (12), Neu (6) or ORACC's proper-noun annotation (5). A
few section references carry a note on the form ("§3.2 (causative prefix tu-)"). Entries 51–54 and 90 cite Gelb,
Purves and MacRae and a group of sources, with no locator. The `Consonantal_Root` of a few entries leaves out a
suffix (794 ḫawurni → hwr, 906 tānōšše → tn), and that of 51–54 and 90 is the whole form. The selection, keys and
citations are ours, under CC BY 4.0.

**Hattic.** All 299 entries cite Oğuz Soysal, *Hattischer Wortschatz in hethitischer Textüberlieferung* (Brill
2004), by page in its glossed list (Kapitel IV, pp. 274–330). Each form is Soysal's printed head, his marks kept:
determinatives (LÚ, D), brackets for a restored form, "*" for a reconstructed one, "?" for a doubtful one. The
`Consonantal_Root` is the head as a key: the determinative dropped, geminates kept as printed, and the W-sign
(waₐ, wiᵢ, wuᵤ, u̯) written f, one letter for each phoneme, so the key is read without digraphs (A23). The 361
lemmas of the list less 29 names (16 divine names, 9 epithets, 4 ethnics), 31 lemmas of one consonant and two
fragments with a gap in the text (za[...]awe, [...]zin), which give no key, leave these 299. The name test reads
`Category`, which ships here, so it flags nothing in this file. Five entries sit at the edge: the titles (I)
Tabarna "ruler" and (MUNUS) Tawananna, (D) Kašku "moon (god)", and two words Soysal writes with the divine
determinative, DWaašul and (D) Wuᵤrunkatte. Two keys, karam and kusim, are Semitic loans (Kassian 2015, 41) and
stay in, as the Hurrian file keeps its Akkadian loans.

*Terms.* Soysal 2004 is © Koninklijke Brill NV, all rights reserved. Nothing of its text ships: no gloss,
translation, analysis or note, and no meaning drawn from them. The file takes from it only the head forms, recast as
keys, and their page numbers. The selection, keys and citations are ours, under CC BY 4.0.
