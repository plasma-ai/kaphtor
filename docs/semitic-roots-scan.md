---
name: docs/semitic-roots-scan
title: "Semitic Roots: The Dictionary Scan"
desc: How the Semitic roots grow from the dictionaries they cite, entry by entry: the units and the coverage measure, the seven verdicts, the rules for joining a row or adding one, the cell form, and the gold sets that test a reader before a full scan.
tags: [docs, semitic-roots]
authors: "di Mino"
created: 2026-11-02T23:00:00Z
updated: 2026-11-04T13:30:00Z
---

# Semitic Roots: The Dictionary Scan

[[docs/_index|..]]

`semitic_roots.json` ([[data/semitic-roots/semitic_roots|semitic_roots]]) grows by reading a dictionary entry by entry and giving each entry the database does not yet cite one verdict. A reader, a language model working from the printed page's image and its transcription, proposes the verdict and the cells. The database is edited by hand, one batch at a time, after a backup; every batch reruns the provenance sidecar, the tests and the export before it reaches this repository.

## Units and coverage

A dictionary's units are its printed entries. A cite is one locator in a cell or in Notes: the siglum and the printed page ("HALOT 827", "DULAT 917", "Krahmalkov 397"). Each cite resolves to the units printed on its pages: the only one there; the one the cell's forms name by consonant skeleton; the one its quoted gloss, or failing that the record's Meaning, shares the most words with; or, when none of these settles it, the page's candidates, counted as ambiguous. A cite followed by "apud" was taken from the work named after it (SEDonline citing HALOT), and never counts as coverage: that entry is still to be read.

Coverage is covered units over units. An entry with a verdict is dispositioned; an entry with neither a cite nor a verdict is open. every HALOT and DULAT entry is cited or carries a verdict:

| Dictionary | Units | Covered | Ambiguous | Verdict only | Open |
| --- | --- | --- | --- | --- | --- |
| HALOT | 9,393 | 2,328 | 1,450 | 5,615 | 0 |
| DULAT | 4,790 | 814 | 331 | 3,645 | 0 |

## Verdicts

| Verdict | When |
| --- | --- |
| `present_uncited` | A row already holds the word in the entry's language, in this sense or one its Meaning covers. Nothing is added. |
| `proposed` | The entry adds a cell to a row of the same root, or a new row. |
| `no_second_branch` | The entry states no cognate outside its own language, or only guesses it marks as uncertain. |
| `onomastic` | A personal, divine, gentilic or place name. |
| `loan` | The entry derives the word from another language (Akkadian, Aramaic into Hebrew, Hurrian, Egyptian, Sumerian, Greek). |
| `cross_reference` | The entry only sends the reader elsewhere. |
| `unreadable` | The page is too broken to read a meaning. |

## Joining a row, or adding one

- **Join before adding.** A row is the entry's root when its consonants answer the entry's by the regular correspondences (Ug. ṯ = Heb. š = Ar. ṯ; Ug. ḏ = Heb. z = Ar. ḏ; Ug. ṣ = Heb. ṣ = Ar. ṣ, ḍ or ẓ) and its Meaning is the entry's sense or one that sense derives from. The same letters with an unrelated meaning are a homonym, with a row of its own.
- **A new sense** joins a row, with a sense numeral, when it derives from the row's sense or a source sets the two in one root. Two roots a dictionary numbers apart (HALOT I and II, DULAT (I) and (II)) stay apart, unless the cognate it gives for one is the other row's own word or a stem of it.
- **A derived word** (<, from, Der. of, by-form of, aphaeresis of, a base and a suffix) joins the row of its base: `present_uncited` when that row's cell in the entry's language holds the base, `proposed` with the derived word's cell when it does not.
- **A new row** needs a second branch the entry itself states. Hebrew alone beside Phoenician is Canaanite only and makes no row; a Modern Yemeni word counts as a branch only when it is not the Sabaic word surviving. A comparison printed under "Cf." never carries a cell. A personal name whose root the source gives can back a cell.
- **Same root, one row.** A proposal whose root a row already holds is consolidated into that row, and two rows found to hold one root are merged; Notes never point from one row to another ("Cf. N") or say what a row is not.

## Cells

One cell per language: the form as printed, its gloss in single quotes, the source and printed page in parentheses, as `ṯrm 'to break, cut, carve' (DULAT 917)`. A cell adds only what the source adds; a new sense carries its numeral. No "?" and no hedge on a reading or a gloss: a word too uncertain to cite is not cited. A second branch for a new row goes in Notes in the source's own terms ("Krahmalkov 397 compares …"). Attribution in every record is "di Mino".

## Candidate rows

The reader sees, for each entry, up to five candidate rows chosen by consonants and gloss, every cell and Note of each in full, and decides among them. Rows are keyed by their radicals with marks kept (ṯ is not t); one letter's transliterations are one letter (ʔ ˀ ʾ, ʕ ˁ ˤ ʿ, ɣ ġ, ḳ q). A looser key then folds s/š/ś/ŝ, ḥ/ḫ, ẓ/ṯ̣, ṣ/ṣ̂, a weak w or y after the first radical and a doubled radical, and, for a Hebrew or Aramaic headword only, the mergers its script writes (ṯ/š, ḏ/z, ʿ/ġ) and a final h for a weak third radical (rʾh beside rʾy). A Ugaritic headword keeps those apart, as Ugaritic does.

## Gold sets

Before a dictionary is scanned in full, a reader is scored on a gold set: 60 entries per dictionary, drawn from the open entries by stratum (verbs, nouns, words, names, places, and entries that cross a page), with a fixed seed, and given verdicts, rows and cells by hand. Lookalike rows, the same consonants with an unrelated meaning, are added to an entry's candidates as decoys, in Number order so their place tells nothing.

| Gold set | Present, uncited | Proposed (new rows) | No second branch | Onomastic | Loan | Cross-reference | Unreadable | Decoys (entries, rows) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HALOT | 21 | 11 (6) | 8 | 15 | 2 | 3 | 0 | 34, 46 |
| DULAT | 28 | 9 (3) | 5 | 13 | 2 | 2 | 1 | 35, 47 |

A reader passes when it accepts a decoy for at most 5% of entries and at least 90% of its `proposed` verdicts are right; agreement on verdicts and cells, and between two runs, is recorded beside them. A reader's verdicts are proposals: nothing reaches the database until it is read against the page and applied by hand.

## What the scan has added

The scan has read Tomback, Krahmalkov and Benz's personal names (Phoenician and Punic), DIANA and Al-Jallad and Jaworska's Safaitic dictionary (Ancient North Arabian), Biella (Sabaic), Leslau's Geʿez dictionary, Hoftijzer and Jongeling's DNWSI, SED, DULAT and HALOT. Its rows run 3871–4687, with gaps where drafts merged or a row left with one branch was withdrawn. A proposal whose root a row already held was consolidated into that row, most as a new sense, and cells were added across the rest.
