---
name: data/linear-a/rival-roots
title: Rival-language root keys
desc: The Egyptian, Luwian and Hurrian root keys the competitor null rescores every Semitic match against, each with its form and its citations or source labels.
tags: [data, linear-a, competitors, egyptian, luwian, hurrian]
license: CC BY-SA 4.0 AND CC BY 4.0, with the ACLT and TIED terms set out below
created: 2026-10-25T22:00:00Z
updated: 2026-10-25T22:45:00Z
---

Three files of keys for the competitor null (§2 and A15 of [the pre-registration](../../docs/shoresh-preregistration.md)),
which `tools/core/competitors.py` reads. Each holds the entries that the default run uses: those that give a key under
A15 and that A15's name test does not flag. The private files these are exported from give the same key spaces, key
for key and entry number for entry number, which `tests/linear_a/test_rival_roots.py` pins along with each file's
exact content.

| File | Entries | Keys | Fields |
| --- | --- | --- | --- |
| `egyptian_roots.json` | 3,053 | 3,011 | `Number`, `Middle_Egyptian`, `Consonantal_Root`, `Sources` |
| `luwian_roots.json` | 1,677 | 1,441 | `Number`, `Proto-Luwian`, `Consonantal_Root`, `Analogue_Labels` |
| `hurrian_roots.json` | 130 | 95 | `Number`, `Hurrian`, `Consonantal_Root`, `Category`, `Sources` |

No entry carries its meaning: the files give the form, the key and where the form is cited.

**Names.** The name test reads an entry's meaning, name elements and semantic field, which are not shipped, so here it
flags nothing and `--names` changes nothing. In the private run `--names` adds the flagged entries (245 Egyptian,
369 Luwian and 561 Hurrian keys); that run cannot be reproduced from these files. The test misses some names, and
they are in both key spaces: the 726 Persons and Names of the Middle Kingdom entries, 14 Egyptian royal names written
"(PN/RN; …)" (Thutmose, Amenhotep, Ramesses, Hatshepsut) and about ten Luwian ruler and place names (Warpalawa,
Muwatalli, Karkamiš). Six Hurrian entries sit at the edge: 51–54 are kinship words (father, mother, brother, wife)
that also serve as name elements, 89 is the ethnic Ḫurri and 90 the title maryannu.

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

**Hurrian.** 120 of the 130 entries cite Laroche's *Glossaire de la langue hourrite* by page. Others cite Wegner's
*Einführung* by section (68), Richter's *Bibliographisches Glossar* by headword (38), Campbell's grammar by glossary
or chapter (32), Wilhelm (18), Gelb's *Nuzi Personal Names* (13), Neu (6) or ORACC's proper-noun annotation (6). A
few section references carry a note on the form ("§3.2 (causative prefix tu-)"). Entries 51–54, 89 and 90 cite Gelb,
Purves and MacRae and a group of sources, with no locator. The `Consonantal_Root` of a few entries leaves out a
suffix (794 ḫawurni → hwr, 906 tānōšše → tn), and that of 51–54, 89 and 90 is the whole form. The selection, keys and
citations are ours, under CC BY 4.0.
