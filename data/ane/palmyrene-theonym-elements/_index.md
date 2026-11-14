---
name: data/ane/palmyrene-theonym-elements
title: Palmyrene divine names in personal names
desc: Thirteen divine names of Palmyra with the Aramaic, Greek and vocalised forms in which the sources write them, each form with the work and page that prints it, for finding the names built on them, CC BY 4.0.
tags: [data, palmyra, aramaic, onomastics]
license: CC BY 4.0
created: 2026-11-14T22:18:40Z
updated: 2026-11-14T22:18:40Z
---

# Palmyrene divine names in personal names

[[data/ane/_index|..]]

[[data/ane/palmyrene-theonym-elements/elements.json|elements.json]]: Bēl, Bôl, Yarḥibôl, ʿAglibôl, Malakbēl, Baalshamin, Allat, ʾArṣû, Nabû, Shamash, ʿAtē, Atargatis and Gad, each with its written forms, their sources and the notes on how to read a match.

***

A search table made by hand (di Mino), CC BY 4.0. Each form is a divine name as a source prints it, cited by work
and page: Yon 2012 (IGLS XVII/1), Du Mesnil du Buisson 1960, and the spellings of Public Inscriptions from Palmyra.
The two books are cited and not shipped.

Finding a form inside a personal name is a substring match and a lead: it is no analysis of the name. Palmyrene
writes both Bēl and Bôl as `bl`; the table marks that form ambiguous, and its note on deciding by the Greek form of
the same name is this project's rule, not a source's.

```bash
uv run --no-sync python tools/ane/query_palmyra.py element --list
uv run --no-sync python tools/ane/query_palmyra.py element bol
```
