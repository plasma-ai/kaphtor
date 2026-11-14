---
name: data/share-alike/oracc-levant
title: ORACC editions of the Late Bronze Age Levant
desc: The 2,583 ORACC editions of Ugarit's Akkadian texts, the Amarna letters and the Statue of Idrimi, with 7,122 translation units, 1,153 find numbers and 11,155 proper-name occurrences, CC BY-SA 3.0.
tags: [data, cuneiform, ugarit, amarna]
license: CC BY-SA 3.0
created: 2026-11-13T18:40:00Z
updated: 2026-11-13T18:40:00Z
---

# ORACC editions of the Late Bronze Age Levant

[[data/share-alike/_index|..]]

[[data/share-alike/oracc-levant/MANIFEST.json|MANIFEST.json]]: The licence as each project states it, the credits, the sources, the one change made to the rows, counts and checksums.

[[data/share-alike/oracc-levant/name_occurrences.jsonl|name_occurrences.jsonl]]: 11,155 proper-name tokens of the four projects, each with its written form, line, ORACC name class and edition.

[[data/share-alike/oracc-levant/oracc_documents.jsonl|oracc_documents.jsonl]]: 2,583 editions (aemw/ugarit 1,900, aemw/myamarna 376, aemw/amarna 305, aemw/alalakh/idrimi 2), each with its transliteration, lines and lemmatised tokens.

[[data/share-alike/oracc-levant/oracc_excavation_numbers.jsonl|oracc_excavation_numbers.jsonl]]: 1,153 find numbers of aemw/ugarit texts, from the project's catalogue, joined by text id.

[[data/share-alike/oracc-levant/oracc_translations.jsonl|oracc_translations.jsonl]]: 7,122 translation units of 1,376 texts, one per translation cell of a text page, with its label, lines, notes and page URL.

***

The four projects are ORACC's: the AEMW Ugarit Corpus, The Amarna Letters (edition by Jacob Lauinger and Tyler
Yoder, on Shlomo Izre'el's electronic transliterations), the later aemw/myamarna edition, and the Statue of Idrimi
(Jacob Lauinger). Their pages release them under CC BY-SA; their JSON archives say CC0. The pages' terms are
followed here, and each edition keeps the archive's sentence in `archive_license`.

An edition is one project's reading of one text. 303 Amarna letters stand under both Amarna projects, so cite the
project with the text. A translation is the project's reading too: cite the project and the page URL with it.

```bash
uv run --no-sync python -m tools.ane.aneq cuneiform "RS 16.156"                 # P503399, however the number is typed
uv run --no-sync python -m tools.ane.aneq cuneiform "RS 16.156" --translation   # its translation, unit by unit
uv run --no-sync python -m tools.ane.aneq cuneiform "pair of horses" --translation
uv run --no-sync python tools/ane/query_proper_names.py Niqmaddu --source oracc-levant
```

Translations cover every text the catalogues of aemw/ugarit, aemw/amarna and aemw/alalakh/idrimi flag as
translated. The find numbers are those of aemw/ugarit, which designates many tablets by publication and keeps the
RS number in its catalogue.
