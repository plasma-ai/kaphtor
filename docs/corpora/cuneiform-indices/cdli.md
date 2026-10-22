---
name: docs/corpora/cuneiform-indices/cdli
title: CDLI corpus index and table of contents
desc: Catalogue artifacts and ATF text versions in the local CDLI snapshot, by language, period, genre, provenience and archive.
tags: [corpora, cuneiform, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# CDLI corpus index and table of contents

## Scope

This index describes the local 2026-10-09 CDLI text-only snapshot. It counts catalogue artifacts separately from text versions. Eight canonical P-numbers have two distinct ATF versions, and both versions are retained. Catalogue labels and target slices overlap; their counts are not additive.

## Corpus baseline

| Measure | Count |
|---|---|
| Catalogue artifacts | 426,703 |
| ATF text versions | 150,220 |
| Unique text-bearing P-numbers | 150,212 |
| Catalogue artifacts with a matched text | 150,210 |
| Matched artifact coverage | 35.202% |
| Versions with numbered transliteration lines | 139,780 |
| Versions with a translation directive | 5,664 |
| Versions with a lemma directive | 104 |

The catalogue is therefore much broader than the available transliteration corpus. Translation and lemma coverage are sparse; neither should be treated as a corpus-wide absence of meaning or lexical annotation.

## Akkadian coverage

| Evidence tier | Text versions |
|---|---|
| ATF primary language begins `akk` | 23,687 |
| Catalogue-only Akkadian additions | 866 |
| ATF-or-catalogue union | 24,553 |
| Union with numbered lines | 24,294 |
| Catalogue artifacts labelled Akkadian | 145,558 |

`P361281` contains two language declarations, first `akk` and then `sux`. The current derived JSONL retains only the final scalar value. The index should retain the declaration array and use the first declaration as the primary language, matching the source audit.

## Dimension overview

| Facet | Labels | Unlabelled artifacts | Multi-labelled artifacts | Assignments |
|---|---|---|---|---|
| Language | 36 | 103,367 | 3,872 | 327,406 |
| Period | 32 | 56,684 | 0 | 370,019 |
| Genre | 63 | 77,813 | 526 | 349,430 |
| Provenience | 464 | 92,306 | 0 | 334,397 |
| Archive | 149 | 416,085 | 0 | 10,618 |

Language and genre are semicolon-delimited multi-value fields. Their raw strings and normalized arrays must both be retained. Period, provenience, and archive are single-valued in this snapshot. Empty values remain explicit availability states, not inferred categories.

## Language table of contents

| Label | Catalogue artifacts | Artifacts with text | Text versions | Akkadian versions | Translated versions |
|---|---|---|---|---|---|
| Akkadian | 145,558 | 18,290 | 18,293 | 18,293 | 904 |
| Sumerian | 143,785 | 99,148 | 99,152 | 898 | 3,729 |
| Hittite | 14,688 | 5 | 5 | 3 | 2 |
| undetermined | 8,522 | 7,659 | 7,659 | 1 | 133 |
| Eblaite | 6,871 | 1,391 | 1,391 | 0 | 3 |
| Elamite | 3,231 | 141 | 141 | 47 | 80 |
| Ugaritic | 2,015 | 2 | 2 | 0 | 1 |
| Middle Babylonian | 873 | 2 | 2 | 2 | 0 |
| Middle Assyrian | 605 | 11 | 11 | 11 | 1 |
| Persian | 316 | 78 | 78 | 45 | 3 |
| Aramaic | 255 | 15 | 15 | 13 | 0 |
| Egyptian | 217 | 7 | 7 | 6 | 2 |
| no linguistic content | 176 | 23 | 23 | 0 | 0 |
| Hurrian | 82 | 3 | 3 | 1 | 1 |
| Old Assyrian | 72 | 8 | 8 | 8 | 1 |
| Old Babylonian | 30 | 1 | 1 | 1 | 0 |
| Greek | 23 | 0 | 0 | 0 | 0 |
| Middle Babylonian peripheral | 15 | 8 | 8 | 8 | 0 |
| Standard Babylonian | 12 | 0 | 0 | 0 | 0 |
| Qatabanian | 11 | 0 | 0 | 0 | 0 |

Shown: 20 of 36 normalized labels. The JSON index retains all 36.

## Period table of contents

| Label | Catalogue artifacts | Artifacts with text | Text versions | Akkadian versions | Translated versions |
|---|---|---|---|---|---|
| Ur III (ca. 2100-2000 BC) | 110,686 | 81,928 | 81,930 | 149 | 2,218 |
| Old Babylonian (ca. 1900-1600 BC) | 73,030 | 16,906 | 16,906 | 10,415 | 1,328 |
| Neo-Assyrian (ca. 911-612 BC) | 36,946 | 4,462 | 4,464 | 3,610 | 65 |
| Neo-Babylonian (ca. 626-539 BC) | 28,496 | 881 | 882 | 584 | 83 |
| Middle Babylonian (ca. 1400-1100 BC) | 16,486 | 976 | 976 | 805 | 61 |
| Achaemenid (547-331 BC) | 15,596 | 296 | 296 | 67 | 75 |
| Middle Hittite (ca. 1500-1100 BC) | 14,708 | 4 | 4 | 2 | 2 |
| Old Akkadian (ca. 2340-2200 BC) | 11,175 | 8,454 | 8,454 | 1,796 | 288 |
| Old Assyrian (ca. 1950-1850 BC) | 9,929 | 4,986 | 4,986 | 4,757 | 69 |
| Early Old Babylonian (ca. 2000-1900 BC) | 9,202 | 4,870 | 4,871 | 1,428 | 508 |
| Ebla (ca. 2350-2250 BC) | 7,112 | 1,617 | 1,617 | 74 | 3 |
| Uruk III (ca. 3200-3000 BC) | 5,931 | 5,439 | 5,439 | 0 | 8 |
| Middle Assyrian (ca. 1400-1000 BC) | 5,458 | 458 | 458 | 276 | 12 |
| ED IIIb (ca. 2500-2340 BC) | 5,420 | 4,912 | 4,913 | 153 | 501 |
| Lagash II (ca. 2200-2100 BC) | 4,706 | 4,357 | 4,357 | 14 | 224 |
| Hellenistic (323-63 BC) | 4,074 | 49 | 49 | 36 | 2 |
| ED IIIa (ca. 2600-2500 BC) | 2,153 | 1,178 | 1,178 | 2 | 22 |
| ED I-II (ca. 2900-2700 BC) | 2,072 | 903 | 903 | 5 | 15 |
| Uruk IV (ca. 3350-3200 BC) | 1,892 | 1,836 | 1,836 | 0 | 5 |
| Proto-Elamite (ca. 3100-2900 BC) | 1,755 | 1,586 | 1,586 | 0 | 119 |
| Neo-Elamite (ca. 770-539 BC) | 1,114 | 38 | 38 | 2 | 4 |
| Middle Elamite (ca. 1500-1100 BC) | 847 | 14 | 14 | 0 | 4 |
| Pre-Writing (ca. 8500-3500 BC) | 357 | 224 | 224 | 0 | 0 |
| Early Neo-Babylonian (ca. 1150-730 BC) | 253 | 13 | 14 | 7 | 7 |
| Uruk V (ca. 3500-3350 BC) | 200 | 142 | 142 | 0 | 1 |
| Egyptian 0 (ca. 3300-3000 BC) | 186 | 0 | 0 | 0 | 0 |
| modern | 100 | 1 | 1 | 1 | 0 |
| Sassanian (224-641 AD) | 61 | 1 | 1 | 0 | 0 |
| Linear Elamite (ca. 2200 BC) | 48 | 10 | 10 | 0 | 0 |
| Parthian (247 BC - 224 AD) | 22 | 6 | 6 | 0 | 0 |
| Harappan (ca. 2200-1900 BC) | 2 | 1 | 1 | 0 | 0 |
| Old Elamite (c. 2600-1500 BC) | 2 | 0 | 0 | 0 | 0 |

## Genre table of contents

| Label | Catalogue artifacts | Artifacts with text | Text versions | Akkadian versions | Translated versions |
|---|---|---|---|---|---|
| Administrative | 235,368 | 117,262 | 117,263 | 7,605 | 2,752 |
| Legal | 23,447 | 4,119 | 4,119 | 2,986 | 164 |
| Official or display | 22,780 | 12,295 | 12,302 | 4,266 | 1,636 |
| Letter | 18,485 | 4,862 | 4,862 | 4,020 | 113 |
| Lexical | 10,162 | 2,448 | 2,448 | 224 | 67 |
| Literary | 9,708 | 1,488 | 1,488 | 185 | 482 |
| Astral sciences | 3,849 | 5 | 5 | 4 | 1 |
| Business / Contracts | 3,808 | 983 | 983 | 547 | 32 |
| Divination | 3,571 | 73 | 73 | 72 | 3 |
| Account | 2,353 | 32 | 32 | 1 | 0 |
| Receipt | 2,320 | 123 | 123 | 21 | 30 |
| Mathematical | 2,274 | 139 | 139 | 27 | 30 |
| Medical | 1,661 | 841 | 841 | 738 | 3 |
| Incantation | 1,133 | 32 | 32 | 15 | 10 |
| Purchase and sale contracts | 1,070 | 82 | 82 | 64 | 9 |
| Prayer | 1,045 | 38 | 38 | 17 | 13 |
| Wisdom or proverb | 756 | 166 | 166 | 2 | 137 |
| Seals and sealings | 712 | 113 | 113 | 2 | 1 |
| Ritual | 409 | 7 | 7 | 1 | 1 |
| Astrology | 396 | 0 | 0 | 0 | 0 |
| Sign list | 392 | 0 | 0 | 0 | 0 |
| Ritual and liturgical | 390 | 7 | 7 | 5 | 4 |
| Commentary | 303 | 4 | 4 | 4 | 0 |
| Literary letter and letter-prayer | 302 | 150 | 150 | 2 | 19 |
| Omens | 284 | 1 | 1 | 1 | 0 |

Shown: 25 of 63 normalized labels. The JSON index retains all 63.

## Provenience table of contents

| Label | Catalogue artifacts | Artifacts with text | Text versions | Akkadian versions | Translated versions |
|---|---|---|---|---|---|
| Girsu (mod. Tello) | 38,428 | 26,027 | 26,027 | 141 | 982 |
| Umma (mod. Tell Jokha) | 37,110 | 32,033 | 32,033 | 38 | 681 |
| Nippur (mod. Nuffar) | 28,042 | 7,106 | 7,106 | 478 | 383 |
| Nineveh (mod. Kuyunjik) | 26,805 | 2,493 | 2,493 | 2,449 | 9 |
| uncertain (mod. uncertain) | 23,101 | 11,402 | 11,403 | 1,092 | 426 |
| Puzriš-Dagan (mod. Drehem) | 17,868 | 16,405 | 16,405 | 4 | 471 |
| Sippar-Yahrurum (mod. Tell Abu Habbah) | 16,469 | 3,171 | 3,171 | 3,011 | 210 |
| Uruk (mod. Warka) | 15,371 | 5,268 | 5,269 | 221 | 75 |
| Ḫattusa (mod. Boğazkale) | 14,521 | 11 | 11 | 10 | 1 |
| Ur (mod. Tell Muqayyar) | 12,839 | 7,198 | 7,200 | 334 | 906 |
| Mari (mod. Tell Hariri) | 9,867 | 2,214 | 2,214 | 2,192 | 110 |
| Kanesh (mod. Kültepe) | 9,240 | 4,673 | 4,673 | 4,672 | 60 |
| Babylon (mod. Bābil) | 8,717 | 265 | 265 | 222 | 30 |
| Ebla (mod. Tell Mardikh) | 6,925 | 1,395 | 1,395 | 0 | 3 |
| Assur (mod. Qalat Sherqat) | 6,742 | 912 | 912 | 830 | 19 |
| Gasur/Nuzi (mod. Yorgan Tepe) | 4,627 | 347 | 347 | 308 | 1 |
| Susa (mod. Shush) | 4,503 | 2,141 | 2,141 | 264 | 164 |
| Ugarit (mod. Ras Shamra) | 3,898 | 558 | 558 | 9 | 1 |
| Irisagrig (mod. uncertain) | 3,166 | 3,059 | 3,059 | 30 | 46 |
| Adab (mod. Bismaya) | 2,967 | 2,678 | 2,679 | 88 | 54 |
| Larsa (mod. Tell as-Senkereh) | 2,813 | 1,110 | 1,110 | 680 | 88 |
| Kalhu (mod. Nimrūd) | 2,794 | 408 | 410 | 276 | 25 |
| Borsippa (mod. Birs Nimrud) | 2,610 | 18 | 18 | 15 | 6 |
| Pārśa (mod. Persepolis) | 2,581 | 100 | 100 | 20 | 69 |
| Kish (mod. Tell Uhaimir) | 2,313 | 329 | 329 | 209 | 24 |

Shown: 25 of 464 normalized labels. The JSON index retains all 464.

## Archive table of contents

| Label | Catalogue artifacts | Artifacts with text | Text versions | Akkadian versions | Translated versions |
|---|---|---|---|---|---|
| Ebabbar | 3,868 | 5 | 5 | 5 | 3 |
| Egibi | 1,413 | 0 | 0 | 0 | 0 |
| Babylon N1 | 500 | 1 | 1 | 1 | 0 |
| Eanna | 366 | 0 | 0 | 0 | 0 |
| Nappahu | 289 | 0 | 0 | 0 | 0 |
| Ea-Ilûta-Bâni | 263 | 0 | 0 | 0 | 0 |
| Persepolis Fortification Archive | 207 | 2 | 2 | 0 | 2 |
| Marduk-remanni | 199 | 0 | 0 | 0 | 0 |
| Bel-remanni | 188 | 0 | 0 | 0 | 0 |
| Aradmu | 164 | 164 | 164 | 0 | 0 |
| Wullu | 139 | 0 | 0 | 0 | 0 |
| Babylon N13 | 124 | 6 | 6 | 6 | 0 |
| Nurshamash | 121 | 121 | 121 | 116 | 0 |
| Shulgi-simti | 119 | 119 | 119 | 0 | 0 |
| Šāt-Eštar | 110 | 109 | 109 | 0 | 0 |
| Assur M6 | 108 | 107 | 107 | 106 | 0 |
| Babylon M6 | 95 | 2 | 2 | 0 | 0 |
| Babylon A2 | 84 | 12 | 12 | 11 | 0 |
| Babylon M8 | 84 | 0 | 0 | 0 | 0 |
| Assur N1 | 81 | 11 | 11 | 5 | 1 |
| Duri-Aššur | 72 | 0 | 0 | 0 | 0 |
| Babylon N9 | 62 | 1 | 1 | 0 | 0 |
| Babylon N15 | 60 | 6 | 6 | 6 | 0 |
| Assur M7 | 58 | 3 | 3 | 3 | 0 |
| Assur N4 | 58 | 45 | 45 | 24 | 0 |

Shown: 25 of 149 normalized labels. The JSON index retains all 149.

## Research-target slices

| Slice | Catalogue | Akkadian-labelled catalogue | Artifacts with text | Text versions | Akkadian versions | Translations |
|---|---|---|---|---|---|---|
| Mari | 9,867 | 9,626 | 2,214 | 2,214 | 2,192 | 110 |
| Old Babylonian | 73,030 | 32,206 | 16,906 | 16,906 | 10,415 | 1,328 |
| Early Old Babylonian | 9,202 | 1,319 | 4,870 | 4,871 | 1,428 | 508 |
| Old Babylonian Family | 82,232 | 33,525 | 21,776 | 21,777 | 11,843 | 1,836 |
| Old Assyrian | 9,929 | 9,391 | 4,986 | 4,986 | 4,757 | 69 |
| Neo Assyrian | 36,946 | 32,440 | 4,462 | 4,464 | 3,610 | 65 |
| Administrative | 235,368 | 57,109 | 117,262 | 117,263 | 7,605 | 2,752 |
| Letters | 18,485 | 16,096 | 4,862 | 4,862 | 4,020 | 113 |
| Legal | 23,447 | 15,776 | 4,119 | 4,119 | 2,986 | 164 |
| Mari Old Babylonian Family | 9,589 | 9,479 | 2,045 | 2,045 | 2,040 | 58 |
| Mari Administrative | 6,645 | 6,579 | 1,437 | 1,437 | 1,425 | 9 |
| Mari Letters | 2,811 | 2,810 | 610 | 610 | 609 | 43 |
| Mari Legal | 104 | 104 | 7 | 7 | 7 | 0 |
| Old Babylonian Family Administrative | 38,783 | 19,287 | 9,477 | 9,477 | 5,248 | 456 |
| Old Babylonian Family Letters | 8,676 | 8,612 | 2,557 | 2,557 | 2,550 | 64 |
| Old Babylonian Family Legal | 8,678 | 3,428 | 3,253 | 3,253 | 2,655 | 139 |
| Old Assyrian Administrative | 958 | 716 | 706 | 706 | 483 | 39 |
| Old Assyrian Letters | 2,415 | 2,403 | 1,319 | 1,319 | 1,317 | 9 |
| Old Assyrian Legal | 535 | 490 | 248 | 248 | 247 | 5 |
| Neo Assyrian Administrative | 2,366 | 946 | 804 | 804 | 39 | 9 |
| Neo Assyrian Letters | 3,283 | 3,273 | 0 | 0 | 0 | 0 |
| Neo Assyrian Legal | 2,034 | 2,010 | 1 | 1 | 1 | 1 |

Mari uses the exact provenience label `Mari (mod. Tell Hariri)`. A substring search for `mari` would incorrectly include Burmarina, Samerina, and Abu-Maria. “Old Babylonian family” is an explicit union of Early Old Babylonian and Old Babylonian; those two source period labels are disjoint in this snapshot.

## Recommended index structure

- Artifact index: one row per canonical P-number, preserving all raw catalogue fields and normalized label arrays.
- Edition index: one row per content-hashed ATF version. Do not collapse the eight duplicated P-numbers.
- Availability facets: `has_text`, `has_numbered_text`, `has_translation`, and `has_lemma_annotation`.
- Language facets: retain every ATF declaration in source order; classify Akkadian evidence as ATF-primary (tier A), catalogue-only (tier B), or neither.
- Research facets: exact Mari, period, genre, provenience, and archive labels plus documented intersection slices. Do not use free substring matching for controlled labels.
- Major TOC entry: at least 1,000 catalogue artifacts or 100 text versions. Secondary entry: at least 100 catalogue artifacts or 10 text versions.
- Archive thresholds: major at 100 artifacts or 25 text versions; secondary at 25 artifacts or 5 text versions. Keep the sparse tail machine-searchable.

## Validation

All 426,703 catalogue rows have unique IDs. All 150,220 JSONL records parsed, and their generated record IDs and content hashes are unique. 150,218 versions join to 150,210 catalogue artifacts. Two malformed seven-digit source IDs—`P2757983` and `P5196323`—do not join and remain in the exception set.

The eight P-numbers with two distinct versions are: `P222242`, `P226743`, `P331271`, `P423568`, `P428300`, `P461401`, `P466003`, `P468708`.

Machine-readable full distributions and exact criteria are in `data/ingest/cuneiform/indices/cdli-stats.json`.
