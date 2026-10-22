---
name: docs/corpora/cuneiform-indices/oracc
title: ORACC local corpus index and table of contents
desc: Archives, editions and tokens in the local ORACC snapshot, by family, project, period, genre and language.
tags: [corpora, cuneiform, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# ORACC local corpus index and table of contents

Generated from the locally acquired ORACC ZIP archives and the edition-aware derived JSONL. This is an inventory of the local holding, not a claim about all texts published by ORACC.

## At a glance

- **117 acquired archives**: 102 contain locally parsed direct editions; 15 are catalogue/proxy umbrella packages.
- **19,365 parsed editions**, representing **19,031 distinct P/Q object IDs**. Edition identity is preserved; repeated object IDs are not collapsed.
- **416,778 lines** and **1,893,023 tokens**; 1,814,163 tokens (95.8%) carry at least one lemma/normalization/gloss/POS field.
- **19,116 editions** (98.7%) contain parsed transliteration/tokens.
- **14,018 editions** (72.4%) have some translation flag in the catalogue of the same archive; **13,808** explicitly include English. This is availability, not translation completeness.
- **303 object IDs** have multiple local editions: 272 occur twice and 31 three times, yielding 334 editions beyond the distinct-object count. All 303 repeated IDs have more than one raw JSON hash; none is an exact byte-identical edition duplicate.

## Family table of contents

| Family | Direct editions | Objects | Projects | Tokens | With text | Any translation flag | Principal periods | Principal genres |
|---|---:|---:|---:|---:|---:|---:|---|---|
| AEMW — Amarna, Ugarit, and Alalakh | 2,207 | 2,207 | 3 | 131,007 | 2,206 | 1,370 | Middle Babylonian (1,173); Unknown (753); Middle Assyrian (3) | letter (305); Royal Inscription (2) |
| ATAE — Archival Texts of the Assyrian Empire | 2,309 | 2,305 | 23 | 139,850 | 2,254 | 1,873 | Neo-Assyrian (2,107); Neo-Babylonian (4) | Legal Transaction (1,238); Administrative Record (429); Legal (117); Administrative Letter (97) |
| BabCity — Babylonian urban landscape texts | 224 | 224 | 1 | 28,350 | 224 | 214 | Achaemenid (82); Neo-Babylonian (55); Neo-Assyrian (33) | Legal (162); Administrative (53); plan (1) |
| BALT — Babylonian administrative and legal texts | 2,990 | 2,990 | 1 | 185,175 | 2,989 | 406 | Neo-Babylonian (2,263); Achaemenid (466); Hellenistic (163) | Administrative (1,535); Legal (909); Letter (228); Receipt (7) |
| Borsippa — priestly archive | 224 | 224 | 1 | 25,436 | 224 | 224 | Achaemenid (155); Neo-Babylonian (50); Uncertain (17) | Legal (177); Administrative (46); Uncertain (1) |
| CAMS/GKAB — Akkadian literary and scholarly compositions | 585 | 585 | 1 | 95,849 | 475 | 579 | Seleucid (227); Neo-Assyrian (187); Achaemenid (122) | Omen (154); Incantation-Ritual (102); Legal (70); Literary (48) |
| DCCLT/Ebla — Ebla school and lexical texts | 109 | 109 | 1 | 5,388 | 109 | 9 | ED IIIb (86); ED IIIa (23) | Lexical (109) |
| HBTIN — Hellenistic Babylonian legal/administrative texts | 485 | 485 | 1 | 123,646 | 484 | 311 | Hellenistic (482) | Legal (471); Administrative (8); Letter (3) |
| NERE — Near Eastern royal epics (local holding: Zimri-Lim epic) | 1 | 1 | 1 | 718 | 1 | 1 | Old Babylonian (1) | Literary (1) |
| OBEL — Old Babylonian Emesal liturgies | 704 | 704 | 1 | 100,580 | 700 | 3 | Old Babylonian (690); Middle Babylonian (9); Neo-Babylonian (3) | — |
| OBMC — Old Babylonian model contracts | 201 | 201 | 1 | 11,886 | 201 | 196 | Old Babylonian (201) | School (201) |
| OBTA — Old Babylonian tabular accounts | 35 | 35 | 1 | 5,972 | 35 | 35 | Old Babylonian (35) | Administrative (35) |
| RIBo — Royal Inscriptions of Babylonia online | 411 | 411 | 8 | 60,592 | 393 | 392 | Neo-Babylonian (269); Neo-Assyrian (99); Middle Babylonian (39) | Royal Inscription (411) |
| Rīm-Anum — House of Prisoners archive | 338 | 338 | 1 | 10,261 | 338 | 338 | Old Babylonian (337); Unknown (1) | — |
| RINAP — Royal Inscriptions of the Neo-Assyrian Period | 1,174 | 1,034 | 6 | 241,683 | 1,128 | 1,130 | Neo-Assyrian (1,173) | Royal Inscription (1,173) |
| SAAo — State Archives of Assyria Online | 5,055 | 5,054 | 22 | 547,680 | 5,042 | 5,019 | Neo-Assyrian (5,052) | Administrative Letter (2,002); Legal Transaction (829); Astrological Report (567); Administrative Record (452) |
| TCMA — Archival Texts of the Middle Assyrian Period | 2,313 | 2,267 | 29 | 178,950 | 2,313 | 1,918 | Middle Assyrian (2,273); Old Assyrian (16); Neo-Assyrian (12) | — |

## What the holding is strongest in

- **Neo-Assyrian archives and letters:** SAAo contributes 5,055 editions, including 2,002 administrative letters, 567 astrological reports, 452 administrative records, 387 scholarly letters, 276 extispicy queries, 210 priestly letters, and 829 legal transactions. ATAE adds 2,309 direct site-archive editions; its umbrella also resolves proxy records into SAAo and other staged packages.
- **Middle Assyrian archives:** TCMA contributes 2,313 editions from Aššur, Dūr-Katlimmu, Kār-Tukultī-Ninurta, Tell Rimah, Ugarit, and 24 other direct subprojects.
- **First-millennium Babylonian administration and law:** BALT contributes 2,990 editions, Borsippa 224, BabCity 224, and HBTIN 485 parsed editions.
- **Royal inscriptions:** RINAP contributes 1,174 project editions over 1,034 objects; RIBo contributes 411 editions.
- **Old Babylonian controls:** OBEL 704, Rīm-Anum 338 parsed editions, OBMC 201, OBTA 35, and NERE one Zimri-Lim epic. These are selective, not a comprehensive Old Babylonian or Mari archive.
- **Literary/scholarly Akkadian:** CAMS/GKAB contributes 585 catalogue editions, 475 with parsed text, especially omen, ritual/incantation, medical, literary, astronomical, prayer, and lexical material.
- **Ugarit:** AEMW/Ugarit contributes 1,900 valid editions, including 839 KTU 4 administrative texts and 955 documents whose tokens are entirely alphabetic Ugaritic; it also supplies the large syllabic Akkadian archive.
- **Ebla:** DCCLT/Ebla contributes 109 valid structured school and lexical editions; broader administrative coverage remains in the separate CDLI and EbDA layers.
- **Second-millennium international Akkadian:** AEMW/Amarna contributes 305 Middle Babylonian peripheral letters; AEMW/Ugarit and TCMA add Ugarit, Mitanni, Hatti, Alalakh, and other peripheral archives.

## Period, genre, and language profile

Periods are catalogue metadata attached to editions; token language is the language code attached to individual annotated tokens.

### Periods

| Period | Editions |
|---|---:|
| Neo-Assyrian | 8,691 |
| Neo-Babylonian | 2,651 |
| Middle Assyrian | 2,277 |
| Old Babylonian | 1,264 |
| Middle Babylonian | 1,221 |
| Achaemenid | 828 |
| Unknown | 754 |
| Hellenistic | 646 |
| Seleucid | 227 |
| ED IIIb | 86 |
| Uncertain | 53 |
| ED IIIa | 23 |
| Old Assyrian | 16 |
| Mitanni | 8 |
| Standard Babylonian | 6 |
| Neo Assyrian | 2 |
| Neo Babylonian | 1 |
| Sealand Dynasty | 1 |

### Genres

| Genre | Editions |
|---|---:|
| Administrative Letter | 2,099 |
| Legal Transaction | 2,067 |
| Legal | 1,906 |
| Administrative | 1,692 |
| Royal Inscription | 1,591 |
| Administrative Record | 881 |
| Astrological Report | 567 |
| Scholarly Letter | 387 |
| letter | 305 |
| Extispicy Query | 276 |
| Letter | 234 |
| Priestly Letter | 210 |
| School | 206 |
| Omen | 154 |
| Lexical | 119 |
| Incantation-Ritual | 102 |
| Extispicy Report | 76 |
| Grant | 69 |
| Royal Ritual | 58 |
| Literary Work | 56 |
| Uncertain | 55 |
| Literary | 51 |
| Medical | 45 |
| Astronomical | 31 |
| Hymn-Prayer | 24 |
| Astrological | 21 |
| Hemerological | 18 |
| Scholarly | 18 |
| Mathematical | 15 |
| Treaty | 15 |
| Decree | 14 |
| Eponym Chronicle | 13 |
| Votive Donation | 13 |
| Eponym List | 12 |
| Prophecy | 11 |
| Historical | 8 |
| Receipt | 7 |
| Lexical Text | 6 |
| Appointment | 4 |
| Prayer | 3 |
| Ritual Text | 3 |
| Incantation | 2 |
| Literary Text | 2 |
| Scholarly or scientific | 2 |
| Blessings | 1 |
| Gift | 1 |
| Historical Text | 1 |
| Official or display | 1 |
| plan | 1 |
| School Text | 1 |

### Token languages

| ORACC language code | Tokens |
|---|---:|
| `akk-x-neoass` | 506,678 |
| `akk-x-neobab` | 379,544 |
| `akk` | 299,020 |
| `akk-x-midass` | 173,173 |
| `akk-x-ltebab` | 130,639 |
| `akk-x-stdbab` | 129,199 |
| `sux` | 108,588 |
| `akk-x-mbperi` | 95,779 |
| `uga-040` | 34,998 |
| `akk-x-oldbab` | 16,564 |
| `sux-x-emesal` | 13,482 |
| `arc` | 1,723 |
| `akk-x-earakk` | 941 |
| `akk-x-midbab` | 786 |
| `akk-x-oldass` | 695 |
| `uga` | 440 |
| `qca` | 200 |
| `qcu-949` | 176 |
| `akk-949` | 142 |
| `qcu` | 75 |
| `xhu` | 37 |
| `hit` | 36 |
| `xhu-040` | 28 |
| `akk-x-neoass-949` | 27 |
| `egy-020` | 16 |
| `akk-x-neobab-949` | 10 |
| `sux-x-syll` | 10 |
| `hit-040` | 7 |
| `hit-946` | 4 |
| `xhu-946` | 4 |
| `arc-949` | 2 |

## Complete direct-project table of contents

Each row is a direct source project that produced at least one parsed edition. Counts retain alternate project editions of the same P/Q object.

### AEMW — Amarna, Ugarit, and Alalakh

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `aemw/alalakh/idrimi` | 2 | 2 | 547 | 2 | Middle Babylonian (2) | Royal Inscription (2) | Alalakh (2) |
| `aemw/amarna` | 305 | 305 | 34,346 | 305 | Middle Babylonian (305) | letter (305) | Byblos (71); Unknown location (44) |
| `aemw/ugarit` | 1,900 | 1,900 | 96,114 | 1,063 | Middle Babylonian (866); Unknown (753) | — | Ugarit (mod. Ras Shamra) (1,120); Unknown (753) |

### ATAE — Archival Texts of the Assyrian Empire

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `atae/assurmisc` | 7 | 7 | 444 | 7 | Neo-Assyrian (7) | Legal Transaction (5); Administrative Record (2) | Qalat Sherqat (Assur) (7) |
| `atae/burmarina` | 44 | 44 | 962 | 44 | Neo-Assyrian (44) | Legal Transaction (44) | Tell Shiukh Fawqani (Burmarina) (44) |
| `atae/ctn1` | 33 | 33 | 3,911 | 33 | Neo-Assyrian (33) | Administrative Record (33) | Nimrud (Kalhu) (33) |
| `atae/ctn2` | 273 | 273 | 12,869 | 243 | Neo-Assyrian (273) | Legal Transaction (122); Administrative Record (96); Administrative Letter (40) | Nimrud (Kalhu) (273) |
| `atae/ctn3` | 153 | 153 | 12,644 | 145 | Neo-Assyrian (153) | Administrative Record (81); Legal Transaction (57); Administrative Letter (8) | Nimrud (Kalhu) (153) |
| `atae/ctn6` | 120 | 120 | 7,611 | 117 | Neo-Assyrian (120) | Legal (117); Uncertain (3) | Nimrud (Kalhu) (120) |
| `atae/durkatlimmu` | 408 | 408 | 22,840 | 210 | Neo-Assyrian (210) | Legal Transaction (204); Administrative Record (4); Lexical Text (1) | Tell Sheikh Hamad (Dur-Katlimmu) (210) |
| `atae/edubba10` | 55 | 55 | 6,165 | 55 | Neo-Assyrian (55) | Legal Transaction (52); Administrative Record (2); Administrative Letter (1) | Nimrud (Kalhu) (55) |
| `atae/guzana` | 212 | 212 | 6,600 | 103 | Neo-Assyrian (208); Neo-Babylonian (4) | Administrative Record (63); Administrative Letter (19); Legal Transaction (17) | Tell Halaf (Guzana) (212) |
| `atae/huzirina` | 19 | 19 | 4,895 | 17 | Neo-Assyrian (19) | Administrative (6); Literary Work (5); Royal Ritual (3) | Sultantepe (Huzirina) (19) |
| `atae/imgurenlil` | 30 | 30 | 1,864 | 30 | Neo-Assyrian (30) | Legal Transaction (30) | Balawat (Imgur-Enlil) (30) |
| `atae/mallanate` | 74 | 74 | 4,613 | 48 | Neo-Assyrian (74) | Legal Transaction (42); Administrative Record (5); Letter (2) | unknown (Ma'allanate) (74) |
| `atae/marqasu` | 46 | 46 | 2,889 | 44 | Neo-Assyrian (46) | Legal Transaction (43); Administrative Record (1) | Kahramanmaraş  (Marqasu) (46) |
| `atae/rfdn17` | 34 | 34 | 2,569 | 34 | Neo-Assyrian (34) | Legal Transaction (32); Administrative Letter (1); Administrative Record (1) | Qalat Sherqat (Assur) (34) |
| `atae/saab0509` | 142 | 142 | 10,173 | 91 | Neo-Assyrian (142) | Legal Transaction (137); Administrative Record (5) | Qalat Sherqat (Assur) (142) |
| `atae/samal` | 2 | 2 | 159 | 2 | Neo-Assyrian (2) | Legal Transaction (2) | Zinčirli (Samal) (2) |
| `atae/stat1` | 52 | 52 | 2,416 | 52 | Neo-Assyrian (52) | Legal Transaction (33); Administrative Record (10); Administrative Letter (6) | Qalat Sherqat (Assur) (52) |
| `atae/stat2` | 328 | 328 | 18,387 | 328 | Neo-Assyrian (328) | Legal Transaction (262); Administrative Record (36); Uncertain (17) | Qalat Sherqat (Assur) (328) |
| `atae/stat3` | 112 | 112 | 8,666 | 110 | Neo-Assyrian (112) | Legal Transaction (88); Administrative Record (17); Uncertain (6) | Qalat Sherqat (Assur) (112) |
| `atae/szibaniba` | 22 | 22 | 2,294 | 22 | Neo-Assyrian (22) | Administrative Record (21); Legal Transaction (1) | Tell Billa (Šibaniba) (22) |
| `atae/tilbarsip` | 22 | 22 | 838 | 20 | Neo-Assyrian (22) | Legal Transaction (15); Administrative Record (3) | Tell Ahmar (Til Barsip) (22) |
| `atae/tuszhan` | 33 | 33 | 1,526 | 33 | Neo-Assyrian (33) | Administrative Record (13); Legal Transaction (12); Uncertain (6) | Ziyaret Tepe (Tušhan) (33) |
| `atae/wvdog152` | 88 | 88 | 4,515 | 85 | Neo-Assyrian (88) | Legal Transaction (40); Administrative Record (36); Administrative Letter (8) | Qalat Sherqat (Assur) (88) |

### BabCity — Babylonian urban landscape texts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `babcity` | 224 | 224 | 28,350 | 214 | Achaemenid (82); Neo-Babylonian (55) | Legal (162); Administrative (53); plan (1) | Bābili (mod. Babylon) (72); Sippar-Yahrurum (mod. Tell Abu Habbah) (63) |

### BALT — Babylonian administrative and legal texts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `balt` | 2,990 | 2,990 | 185,175 | 406 | Neo-Babylonian (2,263); Achaemenid (466) | Administrative (1,535); Legal (909); Letter (228) | Uruk (mod. Warka) (1,507); unclear (910) |

### Borsippa — priestly archive

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `borsippa` | 224 | 224 | 25,436 | 224 | Achaemenid (155); Neo-Babylonian (50) | Legal (177); Administrative (46); Uncertain (1) | Borsippa (mod. Birs Nimrud) (224) |

### CAMS/GKAB — Akkadian literary and scholarly compositions

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `cams/gkab` | 585 | 585 | 95,849 | 579 | Seleucid (227); Neo-Assyrian (187) | Omen (154); Incantation-Ritual (102); Legal (70) | Uruk (393); Huzirina (111) |

### DCCLT/Ebla — Ebla school and lexical texts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `dcclt/ebla` | 109 | 109 | 5,388 | 9 | ED IIIb (86); ED IIIa (23) | Lexical (109) | Ebla (85); Fara (12) |

### HBTIN — Hellenistic Babylonian legal/administrative texts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `hbtin` | 485 | 485 | 123,646 | 311 | Hellenistic (482) | Legal (471); Administrative (8); Letter (3) | Uruk (460); unclear (13) |

### NERE — Near Eastern royal epics (local holding: Zimri-Lim epic)

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `nere` | 1 | 1 | 718 | 1 | Old Babylonian (1) | Literary (1) | Mari (1) |

### OBEL — Old Babylonian Emesal liturgies

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `obel` | 704 | 704 | 100,580 | 3 | Old Babylonian (690); Middle Babylonian (9) | — | Sippar (201); Nippur (173) |

### OBMC — Old Babylonian model contracts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `obmc` | 201 | 201 | 11,886 | 196 | Old Babylonian (201) | School (201) | Nippur (146); uncertain (48) |

### OBTA — Old Babylonian tabular accounts

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `obta` | 35 | 35 | 5,972 | 35 | Old Babylonian (35) | Administrative (35) | Larsa (32); unknown (3) |

### RIBo — Royal Inscriptions of Babylonia online

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `ribo/babylon10` | 1 | 1 | 220 | 1 | Hellenistic (1) | Royal Inscription (1) | Borsippa (1) |
| `ribo/babylon2` | 38 | 38 | 3,682 | 38 | Middle Babylonian (29); Neo-Assyrian (6) | Royal Inscription (38) | Luristan (9); Babylon (6) |
| `ribo/babylon3` | 4 | 4 | 265 | 4 | Middle Babylonian (3); Neo-Babylonian (1) | Royal Inscription (4) | Luristan (3); Babylonia (1) |
| `ribo/babylon4` | 6 | 6 | 93 | 6 | Middle Babylonian (6) | Royal Inscription (6) | Luristan (5); Uruk (1) |
| `ribo/babylon5` | 1 | 1 | 4 | 1 | Middle Babylonian (1) | Royal Inscription (1) | Luristan (1) |
| `ribo/babylon6` | 126 | 126 | 15,721 | 125 | Neo-Assyrian (93); Neo-Babylonian (33) | Royal Inscription (126) | Babylon (34); Uruk (18) |
| `ribo/babylon7` | 232 | 232 | 39,894 | 214 | Neo-Babylonian (232) | Royal Inscription (232) | Babylon (113); Sippar (26) |
| `ribo/babylon8` | 3 | 3 | 713 | 3 | Achaemenid (3) | Royal Inscription (3) | Babylon (1); Ur (1) |

### Rīm-Anum — House of Prisoners archive

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `rimanum` | 338 | 338 | 10,261 | 338 | Old Babylonian (337); Unknown (1) | — | Uruk (mod. Warka) (337); Unknown (1) |

### RINAP — Royal Inscriptions of the Neo-Assyrian Period

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `rinap/rinap1` | 93 | 93 | 11,273 | 85 | Neo-Assyrian (93) | Royal Inscription (93) | Nimrud (Kalhu) (69); Qalat Sherqat (Assur) (13) |
| `rinap/rinap2` | 151 | 151 | 39,026 | 151 | Neo-Assyrian (151) | Royal Inscription (151) | Khorsabad (Dur-Šarrukin) (67); Kuyunjik (Nineveh) (23) |
| `rinap/rinap3` | 261 | 261 | 45,639 | 238 | Neo-Assyrian (261) | Royal Inscription (261) | Kuyunjik (Nineveh) (188); Qalat Sherqat (Assur) (48) |
| `rinap/rinap4` | 183 | 183 | 28,829 | 177 | Neo-Assyrian (183) | Royal Inscription (183) | Kuyunjik (Nineveh) (89); Qalat Sherqat (Assur) (23) |
| `rinap/rinap5` | 346 | 346 | 73,514 | 343 | Neo-Assyrian (346) | Royal Inscription (346) | Kuyunjik (Nineveh) (273); Qalat Sherqat (Assur) (16) |
| `rinap/rinap5p1` | 140 | 140 | 43,402 | 136 | Neo-Assyrian (139) | Royal Inscription (139) | Kuyunjik (Nineveh) (75); Tell Muqayyar (Ur) (16) |

### SAAo — State Archives of Assyria Online

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `saao/saa01` | 265 | 265 | 25,390 | 264 | Neo-Assyrian (265) | Administrative Letter (265) | Kuyunjik (Nineveh) (253); Nimrud (Kalhu) (12) |
| `saao/saa02` | 15 | 15 | 11,824 | 15 | Neo-Assyrian (15) | Treaty (15) | Kuyunjik (Nineveh) (10); Qalat Sherqat (Assur) (2) |
| `saao/saa03` | 52 | 52 | 20,200 | 51 | Neo-Assyrian (51) | Literary Work (51) | Kuyunjik (Nineveh) (38); Qalat Sherqat (Assur) (8) |
| `saao/saa04` | 352 | 352 | 46,947 | 348 | Neo-Assyrian (352) | Extispicy Query (276); Extispicy Report (76) | Kuyunjik (Nineveh) (352) |
| `saao/saa05` | 300 | 300 | 25,855 | 298 | Neo-Assyrian (300) | Administrative Letter (300) | Kuyunjik (Nineveh) (293); Nimrud (Kalhu) (5) |
| `saao/saa06` | 350 | 350 | 31,936 | 350 | Neo-Assyrian (350) | Legal Transaction (350) | Kuyunjik (Nineveh) (349); Khorsabad (Dur-Šarrukin) (1) |
| `saao/saa07` | 218 | 218 | 22,287 | 218 | Neo-Assyrian (218) | Administrative Record (218) | Kuyunjik (Nineveh) (218) |
| `saao/saa08` | 568 | 568 | 33,725 | 566 | Neo-Assyrian (567) | Astrological Report (567) | Kuyunjik (Nineveh) (567) |
| `saao/saa09` | 11 | 11 | 3,027 | 11 | Neo-Assyrian (11) | Prophecy (11) | Kuyunjik (Nineveh) (11) |
| `saao/saa10` | 387 | 387 | 40,808 | 387 | Neo-Assyrian (387) | Scholarly Letter (387) | Kuyunjik (Nineveh) (387) |
| `saao/saa11` | 234 | 234 | 16,086 | 234 | Neo-Assyrian (234) | Administrative Record (234) | Kuyunjik (Nineveh) (230); Khorsabad (Dur-Šarrukin) (4) |
| `saao/saa12` | 98 | 98 | 20,618 | 98 | Neo-Assyrian (98) | Grant (67); Decree (14); Votive Donation (12) | Kuyunjik (Nineveh) (75); Qalat Sherqat (Assur) (16) |
| `saao/saa13` | 210 | 210 | 18,564 | 210 | Neo-Assyrian (210) | Priestly Letter (210) | Kuyunjik (Nineveh) (207); Qalat Sherqat (Assur) (3) |
| `saao/saa14` | 479 | 479 | 34,196 | 479 | Neo-Assyrian (479) | Legal Transaction (479) | Kuyunjik (Nineveh) (479) |
| `saao/saa15` | 390 | 390 | 36,234 | 389 | Neo-Assyrian (390) | Administrative Letter (390) | Kuyunjik (Nineveh) (388); Nimrud (Kalhu) (2) |
| `saao/saa16` | 246 | 246 | 23,719 | 246 | Neo-Assyrian (246) | Administrative Letter (246) | Kuyunjik (Nineveh) (246) |
| `saao/saa17` | 207 | 207 | 29,108 | 207 | Neo-Assyrian (207) | Administrative Letter (207) | Kuyunjik (Nineveh) (207) |
| `saao/saa18` | 205 | 205 | 28,968 | 203 | Neo-Assyrian (204) | Administrative Letter (204) | Kuyunjik (Nineveh) (204) |
| `saao/saa19` | 229 | 229 | 26,128 | 229 | Neo-Assyrian (229) | Administrative Letter (229) | Nimrud (Kalhu) (229) |
| `saao/saa20` | 55 | 55 | 25,706 | 55 | Neo-Assyrian (55) | Royal Ritual (55) | Kuyunjik (Nineveh) (26); Qalat Sherqat (Assur) (24) |
| `saao/saa21` | 161 | 161 | 20,618 | 161 | Neo-Assyrian (161) | Administrative Letter (161) | Kuyunjik (Nineveh) (161) |
| `saao/saas2` | 23 | 23 | 5,736 | 0 | Neo-Assyrian (23) | Eponym Chronicle (12); Eponym List (11) | Kuyunjik (Nineveh) (19); Qalat Sherqat (Assur) (2) |

### TCMA — Archival Texts of the Middle Assyrian Period

| Project | Editions | Objects | Tokens | Translation flag | Main period(s) | Main genre(s) | Main provenience(s) |
|---|---:|---:|---:|---:|---|---|---|
| `tcma/ali1` | 24 | 24 | 1,036 | 24 | Middle Assyrian (24) | — | Atmannu (mod. Tell Ali) (24) |
| `tcma/amarna` | 3 | 3 | 317 | 3 | Middle Assyrian (3) | — | Akhetaten (Mod. Amarna) (2); Grave of Psusennes I (1) |
| `tcma/assur` | 1,464 | 1,464 | 98,390 | 1,225 | Middle Assyrian (1,445); Old Assyrian (16) | — | Aššur (mod. Qalʿat Sherqat) (1,464) |
| `tcma/barri` | 4 | 4 | 187 | 3 | Middle Assyrian (4) | — | Kahat (mod. Tell Barri) (4) |
| `tcma/bazmusian` | 7 | 7 | 333 | 4 | Middle Assyrian (7) | — | Mod. Tell Bazmusian (7) |
| `tcma/billa` | 66 | 66 | 2,840 | 57 | Middle Assyrian (66) | — | Šibaniba (mod. Tell Billa) (66) |
| `tcma/brak` | 5 | 5 | 274 | 4 | Mitanni (5) | — | Nagar (Mod. Tell Brak) (5) |
| `tcma/chuera` | 97 | 97 | 5,119 | 78 | Middle Assyrian (97) | — | Ḫarbe (mod. Tell Chuera) (97) |
| `tcma/emar` | 2 | 2 | 117 | 2 | Middle Assyrian (2) | — | Emar? (mod. Tell Meskene?) (2) |
| `tcma/fekheriye` | 14 | 14 | 516 | 12 | Middle Assyrian (14) | — | Waššukanni? (mod. Tell Fekheriye) (14) |
| `tcma/giricano` | 15 | 15 | 836 | 15 | Middle Assyrian (15) | — | Dunnu-ša-Uzībi (mod. Giricano) (15) |
| `tcma/hana` | 3 | 3 | 214 | 3 | Middle Assyrian (3) | — | Hana (mod. uncertain) (2); Sippar-Yahrurum (mod. Tell Abu Habbah) (1) |
| `tcma/haradum` | 2 | 2 | 90 | 2 | Middle Assyrian (2) | — | Haradum (modern Khirbit ed-Diniye) (2) |
| `tcma/hatti` | 12 | 12 | 1,337 | 8 | Middle Assyrian (12) | — | Ḫattusa (mod. Boğazkale) (12) |
| `tcma/kalhu` | 1 | 1 | 597 | 1 | Middle Assyrian (1) | — | Kalhu (mod. Nimrud) (1) |
| `tcma/kartn` | 64 | 64 | 13,425 | 60 | Middle Assyrian (64) | — | Kār-Tukultī-Ninurta (mod. Tulul ul-Aqar) (64) |
| `tcma/kulishinas` | 15 | 15 | 700 | 14 | Middle Assyrian (15) | — | Kulišhinaš (mod. Amuda?) (15) |
| `tcma/laws` | 48 | 48 | 11,377 | 43 | Middle Assyrian (47); Neo Assyrian (1) | — | Aššur (mod. Qalʿat Sherqat) (48) |
| `tcma/miscellaneous` | 24 | 24 | 1,140 | 23 | Middle Assyrian (24) | — | Uncertain (mod. uncertain) (24) |
| `tcma/nineveh` | 16 | 16 | 5,056 | 12 | Neo-Assyrian (10); Middle Assyrian (6) | — | Ninua (mod. Nineveh) (16) |
| `tcma/nippur` | 4 | 4 | 158 | 4 | Middle Assyrian (4) | — | Nippur (mod. Nuffar) (4) |
| `tcma/nuzi` | 1 | 1 | 45 | 1 | Middle Assyrian (1) | — | Nuzi? (mod. Yorghan Tepe?) (1) |
| `tcma/qitar` | 1 | 1 | 114 | 1 | Middle Assyrian (1) | — | Mod. El-Qitar (1) |
| `tcma/rimah` | 124 | 124 | 5,554 | 98 | Middle Assyrian (122); Mitanni (2) | — | Qaṭṭara (mod. Tell Rimah) (124) |
| `tcma/suri` | 6 | 6 | 349 | 6 | Middle Assyrian (6) | — | Šūru (mod. Savur?) (6) |
| `tcma/taban` | 17 | 17 | 1,287 | 14 | Middle Assyrian (14); Mitanni (1) | — | Ṭabete (mod. Tell Taban) (15) |
| `tcma/tsa1` | 17 | 17 | 712 | 12 | Middle Assyrian (17) | — | Dunni-Aššur (mod. Tell Sabi Abyad) (17) |
| `tcma/tsh1` | 252 | 252 | 26,076 | 185 | Middle Assyrian (252) | — | Dūr-Katlimmu (mod. Tell Sheikh Hamad) (252) |
| `tcma/ugarit` | 5 | 5 | 754 | 4 | Middle Assyrian (5) | — | Ugarit (mod. Ras Shamra) (5) |

## Catalogue/proxy umbrella packages

These 15 acquired ZIPs supply catalogue organization or proxy maps but no additional direct `corpusjson` editions. Their proxy targets are represented by direct subproject editions where resolved. They must not be added to direct-edition counts.

| Archive | Internal project | Catalogue records | Proxies | Name |
|---|---|---:|---:|---|
| `atae-assur.zip` | `atae/assur` | 820 | 819 | Neo-Assyrian Archival Texts from Assur |
| `atae-durszarrukin.zip` | `atae/durszarrukin` | 8 | 8 | Neo-Assyrian Archival Texts from Dur-Šarrukin |
| `atae-kalhu.zip` | `atae/kalhu` | 873 | 873 | Neo-Assyrian Archival Texts from Kalhu |
| `atae-kunalia.zip` | `atae/kunalia` | 1 | 1 | Neo-Assyrian Archival Texts from Kunalia/Kunulua/Kullania |
| `atae-nineveh.zip` | `atae/nineveh` | 4,726 | 4,726 | Neo-Assyrian Archival Texts from Nineveh |
| `atae-saao.zip` | `atae/saao` | 5,055 | 5,058 | atae/SAAo |
| `atae-saaoassur.zip` | `atae/saaoassur` | 56 | 56 | SAAo Texts from Assur |
| `atae-saaokalhu.zip` | `atae/saaokalhu` | 254 | 254 | SAAo Texts from Kalhu |
| `atae.zip` | `atae` | 7,069 | 7,285 | Archival Texts of the Assyrian Empire |
| `ribo.zip` | `ribo` | 391 | 391 | Royal Inscriptions of Babylonia online |
| `rinap.zip` | `rinap` | 1,037 | 1,037 | Royal Inscriptions of the Neo-Assyrian Period |
| `saao-aebp.zip` | `saao/aebp` | 1,755 | 1,769 | SAAo/Assyrian Empire Builders |
| `saao-knpp.zip` | `saao/knpp` | 2,014 | 2,033 | SAAo/Knowledge and Power project |
| `saao.zip` | `saao` | 5,055 | 5,058 | State Archives of Assyria Online |
| `tcma.zip` | `tcma` | 2,278 | 2,278 | Archival Texts of the Middle Assyrian Period |

## Coverage and integrity cautions

- The acquired archives contain 19,470 `corpusjson` members. The parser produced 19,365 editions; the remaining 105 members are preserved in `oracc_invalid.jsonl` as empty/non-JSON upstream members.
- 249 parsed edition records contain no tokens. They remain useful as catalogue/edition records but must not enter token-frequency denominators.
- Genre labels are not normalized: for example, `letter` and `Letter`, or `Administrative Letter` and `Administrative`, are separate publisher values. A future normalized facet should retain the raw label beside the normalized value.
- Provenience strings likewise contain synonymous forms such as Aššur/Qalat Sherqat/Assur and Uruk/Warka. Normalize with an explicit equivalence ledger, never by destructive replacement.
- The translation flag means the archive catalogue lists a translation; it does not measure translated lines or guarantee that every broken line has an English equivalent.
- Token counts include Sumerian, Aramaic, and other embedded/adjacent language material. Akkadian research should filter on token language codes beginning `akk` rather than infer language from project membership.
- The local holding is extensive but selective. In particular it is not a comprehensive Mari archive, comprehensive Old Babylonian administrative/legal archive, or the entire ORACC universe.

## Recommended persistent index design

Build the navigation layer as linked tables rather than one flattened file:

1. **Package** — archive name, ORACC project, parent family, source URL, retrieval/build dates, checksum, license, proxy count, and raw-member counts.
2. **Catalogue object** — P/Q object ID plus designation, language, period, genre/subgenre, provenience, collection, museum number, publication, and translation flag. Retain raw publisher strings.
3. **Edition** — stable edition ID, object ID, direct source project, archive checksum, line/token totals, text/annotation/translation coverage flags, and review status.
4. **Line** — edition ID, line sequence, ORACC reference, label, transliteration, optional translation alignment.
5. **Token** — edition ID, line/reference, token sequence, surface form, normalized form, citation form, guide word/sense, POS, language/dialect, and damage state.
6. **Alternate-edition link** — object ID, all edition IDs, project/archive provenance, content hashes, and later token/line difference summaries. Never choose a canonical edition silently.
7. **Normalized facets** — controlled period, genre, provenience, and language labels linked to raw values by an auditable mapping table.

The human-facing TOC should permit the path `family → project/archive → period/genre/provenience → edition → line/token`, plus reverse faceting by root/lemma and P/Q identifier.

## Local evidence used

- `data/ingest/cuneiform/derived/oracc_documents.jsonl` — parsed edition, line, and token layer.
- `data/ingest/cuneiform/derived/oracc_invalid.jsonl` — rejected empty/non-JSON members.
- `data/ingest/cuneiform/oracc/raw/*.zip` and `raw/subprojects/*.zip` — original catalogue, corpus, and edition JSON.
- `data/ingest/cuneiform/oracc/MANIFEST.jsonl` — acquisition, format, license, and checksum metadata.
- `data/ingest/cuneiform/oracc/DUPLICATES.jsonl` — pre-CAMS repeated-object audit.
- `data/ingest/cuneiform/indices/oracc-stats.json` — complete computed machine-readable index statistics.
