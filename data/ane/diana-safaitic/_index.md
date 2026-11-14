---
name: data/ane/diana-safaitic
title: DIANA I, Safaitic
desc: The 1,546 entries of Al-Jallad's Dictionary of the Inscriptions of Ancient North Arabia I (Safaitic), the dictionary and the toponym glossary, each with its gloss, notes, compared forms, attestations and printed page, and the 340 group and divine names of its two lists, CC BY-NC-ND 4.0.
tags: [data, safaitic, ancient-north-arabian, dictionary]
license: CC BY-NC-ND 4.0
created: 2026-11-16T17:45:00Z
updated: 2026-11-16T18:42:45Z
---

# DIANA I, Safaitic

[[data/ane/_index|..]]

[[data/ane/diana-safaitic/MANIFEST.json|MANIFEST.json]]: The work and its DOI, the PDF's checksum, the pages read, the notation, the licence, counts by kind, section and language, and the output's checksum.

[[data/ane/diana-safaitic/records.jsonl|records.jsonl]]: 1,886 rows: 1,439 headwords of the dictionary (pp. 2–177) and 107 of the Glossary of Toponyms (pp. 178–183), each with its root, part of speech, gloss, the inscriptions it quotes, its Etymological Notes and ANA parallels as printed, the forms they compare with their languages, and its printed page; then the 282 names of the Group Names list (pp. 184–185, `section` group_names, "(nisbah)" as its part of speech) and the 58 of the Divine Names list (pp. 186–187, `section` divine_names, its "(also …)" spellings as variant forms, the description as gloss, the one inscription quoted).

***

Ahmad Al-Jallad, *Dictionary of the Inscriptions of Ancient North Arabia, Volume I: Safaitic*, version 2026.1,
OCIANA, Columbus, Ohio 2026, doi:10.5281/zenodo.23847496, © 2026 Ahmad Al-Jallad, CC BY-NC-ND 4.0, for
non-commercial use. Read from the PDF's own text layer; the printed page is the PDF page less 31. Each entry's text is
as the book prints it, in another format (CC BY-NC-ND 4.0 §2(a)(4)); `forms` and `match_keys` are an index added
beside it. The book prints s¹ s² as s ś; a homograph is an integer, typed as printed (ʿhnt²). The Grammatical Tables
(p. 188 ff.) are not in the file. The Semitic roots cite this book as Al-Jallad 2026, by page.

```bash
uv run --no-sync python -m tools.ane.aneq diana q-b-r --cognate Hebrew
uv run --no-sync python -m tools.ane.aneq diana drought
uv run --no-sync python -m tools.ane.aneq diana lt --section divine_names
```
