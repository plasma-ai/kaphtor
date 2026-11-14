---
name: data/ane/ig-xv-1-cypriot
title: IG XV 1, Cypriot syllabic inscriptions
desc: 311 inscriptions of Inscriptiones Graecae XV 1 (Inscriptiones Cypri syllabicae) in the Cypriot syllabary, Greek and Eteocypriot, with their editions, dates, findspots and German translations, CC BY 4.0.
tags: [data, cypriot, aegean, epigraphy]
license: CC BY 4.0
created: 2026-11-13T19:10:00Z
updated: 2026-11-13T19:10:00Z
---

# IG XV 1, Cypriot syllabic inscriptions

[[data/ane/_index|..]]

[[data/ane/ig-xv-1-cypriot/MANIFEST.json|MANIFEST.json]]: The source, its licence, the files read and the one recovered, counts and the output's checksum.

[[data/ane/ig-xv-1-cypriot/records.jsonl|records.jsonl]]: 311 inscriptions, each with its syllabic edition, language and script labels, place, date, support, translation and bibliography.

***

*Inscriptiones Graecae* XV 1, digital edition of the Berlin-Brandenburgische Akademie der Wissenschaften
(telota.bbaw.de/ig), whose pages are CC BY 4.0 unless marked otherwise. The text records are here; no image is.
The source lists 410 numbers and 311 had a file when this set was read, so the set is incomplete.

```bash
uv run --no-sync python -m tools.ane.aneq cypriot Amathus
```

The inscriptions are a control: a syllabary of the Linear A family writing a known language (Greek) and an unread
one (Eteocypriot). No reading here is this project's.
