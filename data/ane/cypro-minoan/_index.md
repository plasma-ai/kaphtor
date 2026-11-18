---
name: data/ane/cypro-minoan
title: Cypro-Minoan catalogue
desc: The 263 Cypro-Minoan texts, the records of Valério's Appendix A and nine witnesses outside it, keyed by siglum where a text has one, each with its site and object type, edition of record and the metadata of held works, every statement with its work and page; no transcription, CC BY 4.0.
tags: [data, cypriot, aegean, cypro-minoan, epigraphy]
license: CC BY 4.0
created: 2026-11-18T19:45:50Z
updated: 2026-11-18T19:46:25Z
---

# Cypro-Minoan catalogue

[[data/ane/_index|..]]

[[data/ane/cypro-minoan/MANIFEST.json|MANIFEST.json]]: The licence, the rules on text and quotation, the works cited with their references, the counts and the catalogue's checksum.

[[data/ane/cypro-minoan/catalogue.json|catalogue.json]]: One record per text, keyed by siglum, or by the name a text without one is published under: its ## number, site and HoChyMin type, Pleiades and Trismegistos ids, the edition of record with its Appendix A pages, and the statements of held works on its identity, museum number, editions, findspot, date, dimensions, object, document form, hand and visual evidence.

***

Cypro-Minoan, the undeciphered syllabic script of Late Bronze Age Cyprus, is a comparandum for Linear A. The
catalogue holds the 254 records of Valério's Appendix A (2016, 451–566), which numbers the texts by Olivier's ## and
names each by a siglum of site, medium and serial, and nine texts outside it: the earliest tablet, a bowl listed by
Corazza et al. 2022, finds published since, and a Linear A siglum that Donnelly reads as Cypro-Minoan. A record's
site and object type are decoded from Valério's key to the sigla (2016, 36–37); APLI and KALO stand outside the key.

No Cypro-Minoan text is here. Valério's Appendix A, the corpus's critical transcription, is a doctoral thesis whose
notice allows private research and teaching use and no redistribution beyond its own repositories. A record's
`edition` names the edition of record (*HoChyMin*, *CMI* II or the first publication) and the Appendix A pages, for a
reader with the thesis in hand.

Each metadata statement names its work and page. A table cell (Donnelly's appendices, Valério's Appendix C) gives its
datum as printed, and a remark in the cell becomes a note in our words. A statement whose text is its source's own
sentence is a pointer: `text` is null, `pointer` is true, and the
cites name the page. `relayed_from` names the work a source reports (*HoChyMin*, *CMI* II), and `basis` says whether a
join of siglum and object is stated or made through a figure credit or a citation. The notes are di Mino's.

Pleiades and Trismegistos ids identify a site and never attest a word.

```bash
uv run --no-sync python tools/linear_a/cypro_minoan_lookup.py --doc "ENKO Atab 004"
uv run --no-sync python tools/linear_a/cypro_minoan_lookup.py --site KITI --type Avas
```

The selection, decoding, notes and citations are di Mino's, CC BY 4.0. The facts come from the works the MANIFEST
lists, cited by work and page; their table data stand as printed and none of their prose is reproduced. Pleiades ids, and the Pleiades descriptions quoted in
three site notes, are CC BY 3.0. Trismegistos ids are references to its records, whose data carry their own terms
(`data/share-alike/trismegistos/`). Nothing here enters the Linear A corpus or supports a sign value.
