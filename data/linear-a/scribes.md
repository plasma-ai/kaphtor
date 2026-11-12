---
name: data/linear-a/scribes
title: Linear A scribes
desc: One entry per scribe to whom an edition assigns Linear A documents, with the site, the class of document, whose numbering the label follows and its source.
tags: [data, linear-a, corpus, scribes]
license: CC BY 4.0
created: 2026-11-13T14:57:38Z
updated: 2026-11-13T14:57:38Z
---

`scribes.json` holds `schema_version`, `description`, `compiled_by` and `scribes`, an object keyed by the scribe's
label (`HT Scribe 9`, `KH Wc Scribe 54`, `ZA Scribe 1`). The label is the value of the `scribe` field of
[corpus.json](corpus.json), and of `scribe_also` where two scribes wrote one record. The file lists no records: a
scribe's documents are the corpus records that carry the label.

| Field | Content |
| --- | --- |
| `site` | the site whose documents the scribe wrote, as the corpus names it |
| `class` | `tablet`, or the series of the documents (`Wa` nodules, `Wc` roundels, `Za`, `Zd`, `Zf`) |
| `numbering` | whose numbers the label follows: `GORILA V` or `Militello 1989` |
| `source` | where the attribution is printed, by siglum and page |
| `gorila_v` | on the Haghia Triada tablet scribes: the cells GORILA V prints for the same tablets (`14 HT`, `9 HT (?)`) |
| `note` | what the source says of a divided document, and where a page was not checked |

## Two numberings

GORILA V prints a scribe for each document in the column "Scribe" of its Concordance générale (pp. 82–113; the
identifications are L. Godart's). A scribe is numbered within one site and one class of document: `1 ZA` wrote
Zakros tablets, `54 KH Wc` Khania roundels. Outside the Haghia Triada tablets the labels here are GORILA V's.

For the Haghia Triada tablets Younger 2023 gives the attributions "revised by Militello 1989", and that revision
renumbers some scribes: GORILA V's `14 HT` (HT 28) is `HT Scribe 13`, its `16 HT` (HT 91) is `HT Scribe 15`, and
scribes 19 to 24 are Militello's additions. The corpus keeps Militello's number in `scribe` and GORILA V's cell,
as printed, in `scribe_gorila`; Montecchi 2010 (Table 2) follows GORILA V's numbers. Five tablets to which GORILA V
assigns a scribe and Younger none (HT 15, 22, 23, 137, 146) carry `scribe_gorila` alone.

## In the corpus

| Field | Content |
| --- | --- |
| `scribe` | the scribe's label, empty where no edition assigns one |
| `scribe_doubt` | `true` where the edition prints the attribution with a question mark; the label never carries the mark |
| `scribe_part`, `scribe_also` | where two scribes wrote one record: the part the first wrote (`lines 1–3`, `fragment a`), and the others as `[{"scribe": label, "part": "lines 4–6"}]` (HT 6b, PS Za 2) |
| `scribe_gorila` | on Haghia Triada tablets, the cell GORILA V prints |

Eight nodules on p. 93 of GORILA V (HT Wa 1296, 1297, 1302, 1307–1310, 1313) were not checked against it and stand
as Younger 2023 gives them; the scribes concerned say so in `note`.

`uv run tools/linear_a/lq.py scribe` lists the scribes with their record counts, and with a label
(`lq.py scribe "HT 9"`) that scribe's records and the words they share. `tools/linear_a/validation/check_scribes.py`
checks the corpus fields against this file and writes nothing. The wiki's
[by_scribe](../../wiki/linear-a/by_scribe.md) ledger lists every scribe with the documents.
