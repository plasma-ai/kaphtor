---
name: data/ane/palmyra-public-inscriptions
title: Public Inscriptions from Palmyra
desc: The 1,135 public inscriptions of Palmyra in Raja, Steding, Yon and Romanowska's dataset, with their PAT, IGLS, CIS and RES numbers, dates, buildings, gods and the persons named, and a concordance of those numbers, CC BY 4.0.
tags: [data, palmyra, aramaic, epigraphy, onomastics]
license: CC BY 4.0
created: 2026-11-14T22:18:40Z
updated: 2026-11-14T22:18:40Z
---

# Public Inscriptions from Palmyra

[[data/ane/_index|..]]

[[data/ane/palmyra-public-inscriptions/MANIFEST.json|MANIFEST.json]]: The dataset and its DOI, the three source spreadsheets with their checksums, the rules for cells, ids, names and the concordance, the columns left out, counts and the outputs' checksums.

[[data/ane/palmyra-public-inscriptions/buildings.jsonl|buildings.jsonl]]: The dataset's 90 buildings, each with its date range.

[[data/ane/palmyra-public-inscriptions/concordance.jsonl|concordance.jsonl]]: The 355 inscriptions that carry more than one siglum, each with its PAT, IGLS, CIS and RES numbers as the dataset gives them and a lookup key for each.

[[data/ane/palmyra-public-inscriptions/names.jsonl|names.jsonl]]: 5,443 names, one row each: 892 founders and 2,912 individuals of the Names sheet, 1,220 individuals of the main sheet with the function it gives, and 419 entries of the Gods column.

[[data/ane/palmyra-public-inscriptions/records.jsonl|records.jsonl]]: 1,135 inscriptions, each with its sigla, year range, language, medium, topic, object, building, context, gods and places.

***

Rubina Raja, Julia Steding, Jean-Baptiste Yon and Iza Romanowska, *Public Inscriptions from Palmyra* (Zenodo
2026, doi:10.5281/zenodo.18934260), CC BY 4.0. The data paper is Steding, Romanowska, Yon and Raja 2026, *Journal of
Open Archaeology Data* (doi:10.5334/joad.189).

The rows are catalogue data. The dataset holds no inscription text, and its names are the editors' vocalised
romanisation (Ḥaîran, Bôlḥazaî), with no consonantal spelling: a query in consonants (`bwlḥzy`) finds nothing. The
two sheets spell some names differently; each form stands under its own sheet. An id is the row's PAT number, else
its IGLS, CIS or RES number, else its sheet row (25 rows carry no siglum).

The concordance equates numbers only as one row of the dataset does. Its IGLS numbers are those of IGLS XVII/1 (Yon
2012), whose own concordance of publications (pp. 473–490) lists every earlier edition of each inscription; that
volume is cited here and not shipped.

```bash
uv run --no-sync python -m tools.ane.aneq palmyra "PAT 8"
uv run --no-sync python -m tools.ane.query_proper_names Bôlḥazaî --source palmyra-public
uv run --no-sync python tools/ane/query_palmyra.py sigla "PAT 291"
```
