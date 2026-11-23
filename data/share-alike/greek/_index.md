---
name: data/share-alike/greek
title: LSJ headwords and Diodorus Siculus, Books 1–5
desc: The 117,130 headwords of Liddell, Scott and Jones's Greek lexicon, each with its spelling in Linear B signs, and the 2,465 sections of Diodorus Siculus, Books 1–5, in the Perseus text, CC BY-SA 4.0.
tags: [data, greek, linear-b]
license: CC BY-SA 4.0
created: 2026-11-23T15:30:00Z
updated: 2026-11-23T15:30:00Z
---

# LSJ headwords and Diodorus Siculus, Books 1–5

[[data/share-alike/_index|..]]

[[data/share-alike/greek/diodorus_1_5.jsonl|diodorus_1_5.jsonl]]: One row per Perseus TEI section of Diodorus Siculus, *Bibliotheca Historica* Books 1–5 (2,465 sections; 81,026 clean Linear-B-spelled Greek words), CC BY-SA 4.0.

[[data/share-alike/greek/lsj_lb_keys.jsonl|lsj_lb_keys.jsonl]]: One row per LSJ entry: its id, its headword and the headword spelled in Linear B signs (117,130).

***

`lsj_lb_keys.jsonl` holds 117,130 rows, one per entry of the lexicon, in the lexicon's order. The language
identification suite in `models/language-id-kernel/` reads it as training material for its Greek arm: the headwords
as a Mycenaean scribe's signs would write them.

| Field | Content |
| --- | --- |
| `id` | `gk_lsj_` and the entry's running number |
| `form_original` | the headword, in Greek script |
| `lb_key` | the headword in Linear B spelling, written as one run of open syllables (`kuruso` for χρυσός), by the rules of `tools/core/greek_spelling.py`; empty on 23 entries |

The spelling is a derived field: it applies the Linear B spelling rules to the alphabetic headword and is no
attested Mycenaean form. Glosses, citations and the rest of each entry are not in this file.

**Source.** Liddell, Scott and Jones, *A Greek–English Lexicon*, 9th edition (1940), in the text edited for Logeion
at the University of Chicago by Helma Dik (https://github.com/helmadik/LSJLogeion), which builds on the Perseus
Digital Library's digitization (Tufts University). CC BY-SA 4.0, as the repository's licence file states. Anything
derived from this file carries the same terms.

`diodorus_1_5.jsonl` holds 2,465 rows, one per section of Books 1–5 of the *Bibliotheca Historica*, in the order of
the text. The suite reads it as running Greek prose.

| Field | Content |
| --- | --- |
| `doc_id` | `diodorus:` and the book, chapter and section (`diodorus:1.arg.0`) |
| `text` | the section's Greek text, without markup |

**Source.** Diodorus Siculus, *Bibliotheca Historica*, Books 1–5, in the Perseus Digital Library's TEI edition
`tlg0060.tlg001.perseus-grc5` (https://www.perseus.tufts.edu/), CC BY-SA 4.0.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --lsj` cuts the lexicon file from the full lexicon
and `--diodorus` cuts the sections from the Perseus XML; with `--check` each compares the two and writes nothing.
