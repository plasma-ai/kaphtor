---
name: data/ane/cypro-minoan
title: Cypro-Minoan catalogue
desc: The 263 Cypro-Minoan texts, the records of Valério's Appendix A and nine witnesses outside it, keyed by siglum where a text has one, each with its site and object type, edition of record, date, script and subcorpus, and the metadata of held works, every statement with its work and page, and di Mino's readings of translated texts with the sign groups of the words read; no other transcription, CC BY 4.0.
tags: [data, cypriot, aegean, cypro-minoan, epigraphy]
license: CC BY 4.0
created: 2026-11-18T19:45:50Z
updated: 2026-11-18T19:46:25Z
---

# Cypro-Minoan catalogue

[[data/ane/_index|..]]

[[data/ane/cypro-minoan/MANIFEST.json|MANIFEST.json]]: The licence, the rules on text and quotation, the works cited with their references, the counts and the checksums of the catalogue and the translations.

[[data/ane/cypro-minoan/catalogue.json|catalogue.json]]: One record per text, keyed by siglum, or by the name a text without one is published under: its ## number, site and HoChyMin type, Pleiades and Trismegistos ids, the edition of record with its Appendix A pages, and the statements of held works on its identity, museum number, editions, findspot, date, dimensions, object, document form, hand and visual evidence; then its period with its years on Valério's chronology, the lead statement and those set against it, its script and subcorpus, each null field with its reason.

[[data/ane/cypro-minoan/translations.json|translations.json]]: di Mino's readings of whole texts, keyed by siglum: each word read with its sign group in Olivier's numbers, its line and Appendix A page, its value for each sign, gloss, tier and the published readings it rivals with their work and page; then the values the readings take, each with its tier and evidence.

***

Cypro-Minoan, the undeciphered syllabic script of Late Bronze Age Cyprus, is a comparandum for Linear A. The
catalogue holds the 254 records of Valério's Appendix A (2016, 451–566), which numbers the texts by Olivier's ## and
names each by a siglum of site, medium and serial, and nine texts outside it: the earliest tablet, a bowl listed by
Corazza et al. 2022, finds published since, and a Linear A siglum that Donnelly reads as Cypro-Minoan. A record's
site and object type are decoded from Valério's key to the sigla (2016, 36–37); APLI and KALO stand outside the key.

No Cypro-Minoan text is here beyond the sign groups of the words the translations read. Valério's Appendix A, the
corpus's critical transcription, is a doctoral thesis whose notice allows private research and teaching use and no
redistribution beyond its own repositories. A record's `edition` names the edition of record (*HoChyMin*, *CMI* II or
the first publication) and the Appendix A pages, for a reader with the thesis in hand.

The translations are di Mino's readings of whole texts. Each word read gives its sign group in Olivier's numbers, its
line and the Appendix A page that prints it, as scholarship quotes the groups it discusses; a word left unread keeps
its line, page and note and shows no group. Each word credits the published readings it rivals to their proposers,
with work and page, and each value it takes stands in `sign_values` with its tier and evidence. The readings are never
counted with Linear A and never evidence for a Linear A sign value.

Each metadata statement names its work and page. A table cell (Donnelly's appendices, Valério's Appendix C) gives its
datum as printed, and a remark in the cell becomes a note in our words. A statement whose text is its source's own
sentence is a pointer: `text` is null, `pointer` is true, and the
cites name the page. `relayed_from` names the work a source reports (*HoChyMin*, *CMI* II), and `basis` says whether a
join of siglum and object is stated or made through a figure credit or a citation. The notes are di Mino's.

A record's date fields come from its date statements. The lead is *CMI* II's (Ferrara), then *HoChyMin*'s
(Vandenabeele), both as Valério's Appendix C relays them, then Donnelly's, then the rest in record order; its period
takes its years from Valério's Table I.1, or Table I.2 for a Minoan period (2016, 39), and each source's own years stay
in its statement. A choice of periods takes no single span. `dating_status` says whether the other statements agree
with the lead, overlap it or conflict with it; `conflicts` lists those set against it with their relation, a
`chronology` naming the same years on either side of the LC IIC/IIIA boundary, which Table I.1 sets at 1190 and the
Enkomi and Kition excavations c. 1230, and counting as an overlap. `date_certainty` is LOW where a source sets the find
out of context, and Donnelly 2021's chronology column, which relays Ferrara's, counts as *CMI* II where the two agree.
A lead or conflicting statement ships as its date statement does: a pointer where that is one, with its note. `script`
is Cypro-Minoan, or Cypro-Greek for the three texts Valério rejects as such, with a note where a held source doubts the
writing; `subcorpus` is Masson's CM 1, 2 or 3 as Appendix A heads the text, or CM 0 for ##001. `null_reasons` gives
the reason for every field left null.

Pleiades and Trismegistos ids identify a site and never attest a word.

```bash
uv run --no-sync python tools/linear_a/cypro_minoan_lookup.py --doc "ENKO Atab 004"
uv run --no-sync python tools/linear_a/cypro_minoan_lookup.py --doc "RS 20.25"    # RASH Atab 004, with its reading
uv run --no-sync python tools/linear_a/cypro_minoan_lookup.py --site KITI --type Avas
```

The selection, decoding, notes and citations are di Mino's, CC BY 4.0. The facts come from the works the MANIFEST
lists, cited by work and page; their table data stand as printed and none of their prose is reproduced. Pleiades ids, and the Pleiades descriptions quoted in
three site notes, are CC BY 3.0. Trismegistos ids are references to its records, whose data carry their own terms
(`data/share-alike/trismegistos/`). Nothing here enters the Linear A corpus or supports a sign value.
