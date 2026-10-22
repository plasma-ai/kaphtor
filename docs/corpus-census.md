---
name: docs/corpus-census
title: "Linear A Corpus Census: GORILA, RILA-S1 and the Working Corpus"
desc: How many Linear A documents GORILA and RILA-S1 publish, which of them corpus.json holds and under which keys, and why the corpus holds more.
tags: [docs, linear-a, corpus]
authors: "di Mino"
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Linear A Corpus Census: GORILA, RILA-S1 and the Working Corpus

How many Linear A documents exist, which of them `corpus.json` holds, and under which keys. The published census is GORILA plus its first supplement, RILA-S1; the working corpus descends from lineara.xyz (Hogan 2019–), built on George Douros's tabulations, enriched from SigLA (Salgarella & Castellan 2021) and reconciled against both editions.

This document gives sigla, counts, corpus keys and page references only. Readings, inventory numbers, findspots, dates and bibliographies belong to the editions themselves and are not reproduced here. Every count drawn from the data sits in a block generated from `corpus.json` and `census_classes.json`; the editions' own figures are given as published.

## 1. The published census

| Source | Documents | Signs | Scope |
|---|---:|---:|---|
| GORILA I–V (Godart & Olivier 1976–1985) | 1,427 | 7,147 | Consolidated figure after vol. V's addenda and joins (GORILA V, p. xv; RILA-S1, p. xvii) |
| RILA-S1 (Del Freo & Zurbach 2024) | 107 | 427 | Documents found or completed since GORILA, published by the end of 2023 |
| **Published census to end 2023** | **1,534** | **7,574** | RILA-S1, p. xvii; EFA publisher page; CNR announcement |

GORILA's volume totals before consolidation: I, 190 tablets and fragments (p. xvii); II, 913 sealed documents (p. xv); III, 228 (p. xii); IV, 76 non-administrative inscriptions (p. xx); V, 23 new documents and 3 revised joins (pp. 8–10). Volume V's general concordance (pp. 83–113) is the authoritative GORILA list.

RILA-S1's concordance (pp. xxvii–xxxv) lists every post-GORILA item by site, with its summary by class and site at pp. xxxvii–xxxix and by repository at pp. xli–xlii. Its sigla carry three marks:

- **bold, unbracketed**: an accepted document, counted in the 107;
- **(…)** with "Cf. D n": a doubtful inscription, edited in the separate list D1–D26 (pp. 142–175, concordance pp. xlv–xlvii); without a D number, an isolated sign, not counted;
- **{…}**: an uninscribed object (mostly roundels from Hallager 1996, *Minoan Roundel* II), listed and not counted.

Joins count once: KH Wc 2059 [+] 2091 [+] 2092 is one roundel, as is KH Wc 2088 [+] 2089 [+] fr. Some RILA-S1 documents complete a GORILA entry (SY Za 3 + two fragments; KN Zb 27, GORILA's Zb <27>).

RILA-S1 states the base itself (p. xvii): GORILA's five volumes hold 1,427 documents and 7,147 signs, and the 107 add 427 signs, increases of 7.5% and 6%. The 107 include GORILA documents whose reading RILA-S1 changes (p. xvii n. 2), so the 1,534 counts these objects in both editions:

- new studies: KH Wc 2070 (a false join corrected), and KH Wc 2074, 2079, 2095 (formerly uninscribed);
- KN Zb 27, rediscovered;
- joins: KH Wc 2059 [+] 2091 [+] 2092, KH Wc 2088 [+] 2089 [+] fr., SY Za 3 + two fragments.

The 107 add one new sign and eight new ligatures (p. xxiv). Its sign index and sign plates cover the 107 only; the doubtful inscriptions are left out (p. xxiii).

An object counts as an inscription only when two of its signs are certain (p. xviii). The exceptions are isolated logograms on sealed documents and on vases (MA Zb 15, PK Zb 24) and isolated countermarks on sealed documents. Isolated syllabograms on vases and other objects are left to the study of potters', masons' and bronzesmiths' marks, KKH Zb 1 excepted (p. xviii n. 10). Objects not certainly in Linear A form the doubtful list D1–D26 (pp. xviii–xix). Claimed inscriptions not admitted even as doubtful are named at p. xix n. 12: Troy, signs reported at Knossos by Owens, the Peristeria marks, Ithaca, and the Zominthos libation table.

Texts published after 2023, such as the Anetaki ivory ring KN Zg 57 and handle KN Zg 58 (Kanta, Nakassis, Palaima & Perna 2024: 36–41), fall outside both editions.

## 2. The working corpus

A record is a catalogue entry; tablet sides (`HT9a`, `HT9b`), recto and verso (`GO2r`, `GO2v`) and separately catalogued faces are records of one object, and grouping them gives the documents. HT 154 A–N are separate fragments in GORILA I and stay separate; `HT154ja`/`HT154jb` are the sides of fragment J. Keys ending `.`, `ter` or `bis` are documents of their own.

<!-- BEGIN kaphtor:census corpus -->
`corpus.json` holds **1,719 records**, which group into **1,603 documents**. SigLA's per-face records are folded into the record they describe (`sigla_sides`, 46 records), and second records of an object into their keeper (`merged_records`, 20 records), each kept as a full snapshot.
<!-- END kaphtor:census corpus -->

<!-- BEGIN kaphtor:census labels -->
Every record carries `source_provenance` except `SKOZc2`. 1,376 documents carry the label `GORILA`.
<!-- END kaphtor:census labels -->

The labels follow lineara.xyz and undercount GORILA documents, and one labelled record, `THEZb5`, is not a GORILA document.

## 3. RILA-S1 accepted documents in the corpus

Keys that differ from RILA-S1's designation:

- `KNZb56` is **KN Zb <53>**, CTLA's KN Z 36; the record's own aliases give both. RILA-S1 edits it from Evans's notebooks: the object is lost (pp. xxi–xxii).
- `PSIZa1` is **PSE Zb 1** (Pseira), and `PSIZa2` is the isolated sign (PSE Zb 2). Both records are mislabelled as Psykhro stone vessels.
- `SAMWa1` is **SA We 3** (CMS V Suppl. 1B no. 327, which CMS calls "Wa 1").
- `PKZg22` is **PK Wy 22**, a sealed object in RILA-S1, catalogued as a stone object.
- `POZc1` is **PO Zg 1** (alias `PORZg1`), catalogued as an inked inscription.
- `PORZf2` is **PO Zf 2**.
- `KHZb98`, `KH99`, `KH100` are KH Zb 98, KH 99 and KH 100, which Andreadaki-Vlasaki & Hallager 2007 published as KH Zb 1, KH 98 and KH 99.
- `KN49` is KN 49 (lineara.xyz's former KN Wa 40).
- `PEWy5` is PE Wy 5 (formerly PE Zg 5) and `PE6` the tablet PE 6 (formerly PE Zg 6).
- `HTZb162` is HT Zb 162. RILA-S1 reads two signs, both very uncertain (p. 94); the corpus holds four. `HTZb162bis`, a single sign, is not part of the entry.

<!-- BEGIN kaphtor:census rila-accepted -->
107 of the 107 are held.

| RILA-S1 | Corpus key(s) | Note |
|---|---|---|
| ARKH Zc 8 | `ARKHZc8` |  |
| ARKH Zf 9 | `ARKHZf9` |  |
| CR (?) Zg 4 | `CRZg4` |  |
| GO 2 | `GO2r`, `GO2v` |  |
| GO Wc 3 | `GOWc3` |  |
| HT Zb 162 | `HTZb162` | HTZb162bis (DA) unexplained |
| HT Zg 163 | `HTZg163` |  |
| HT Wc 3024 | `HTWc3024` |  |
| IO Za 11 | `IOZa11` |  |
| IO Za 12 | `IOZa12` |  |
| IO Za 13 | `IOZa13` |  |
| IO Za 14 | `IOZa14` |  |
| IO Za 15 | `IOZa15` |  |
| IO Za 16 | `IOZa16` |  |
| KKH Zb 1 | `KKHZb1` |  |
| KE 6 | `KE6` |  |
| KH 92 | `KH92` |  |
| KH 93 | `KH93` |  |
| KH 94 | `KH94` |  |
| KH 95 | `KH95` |  |
| KH 96 | `KH96` |  |
| KH 101 | `KH101` |  |
| KH 102 | `KH102` |  |
| KH 103 | `KH103` |  |
| KH 104 | `KH104` |  |
| KH 105 | `KH105` |  |
| KH 97 | `KH97a`, `KH97b`, `KH97` | KH97a/b = faces a, b (Andreadaki-Vlasaki & Hallager 2007: 8–10; RILA-S1's sign index cites KH 97b, s.v. 306); KH97 is SigLA's 'KH 97' (fractions + BOS), which does not match the 2007 drawing: unresolved |
| KH Zb 98 | `KHZb98` | = KH Zb 1 of Andreadaki-Vlasaki & Hallager 2007 |
| KH 99 | `KH99` | = KH 98 of 2007 |
| KH 100 | `KH100` | = KH 99 of 2007 |
| KH Zc 106 | `KHZc106` |  |
| KH Wc 2059 [+] 2091 [+] 2092 | `KHWc2059`, `KHWc2091`, `KHWc2092` | one roundel, three records |
| KH Wc 2088 [+] 2089 [+] fr. | `KHWc2088`, `KHWc2089` | one roundel, two records |
| KH Wc 2070 | `KHWc2070` |  |
| KH Wc 2074 | `KHWc2074` |  |
| KH Wc 2079 | `KHWc2079` |  |
| KH Wc 2095 | `KHWc2095` |  |
| KH Wc 2121 | `KHWc2121` |  |
| KH Wc 2122 | `KHWc2122` |  |
| KH Wc 2123 | `KHWc2123` |  |
| KH Wc 2124 | `KHWc2124` |  |
| KN Zb 27 | `KNZb27` |  |
| KN Wc 42 | `KNWc42` |  |
| KN Wc 48 | `KNWc48` |  |
| KN 49 | `KN49` |  |
| KN Wa 50 | `KNWa50` | KNWb50 merged into it |
| KN Wa 51 | `KNWa51` | KNWb51 merged into it |
| KN Zb 52 | `KNZb52` |  |
| KN Zb <53> | `KNZb56` | held as KNZb56 (names KNZ36, KNZb<53>); CTLA KN Z 36 |
| KN 54 | `KN54` |  |
| KN Zg 55 | `KNZg55` |  |
| KY Za 2 | `KYZa2` |  |
| MA Zb 15 | `MAZb15` |  |
| MIL Zb 1 | `MILZb1` |  |
| MIL Zb 2 | `MILZb2` |  |
| MIL Zb 3 | `MILZb3` |  |
| MIL Zb 4 | `MILZb4` |  |
| MO Zf 1 | `MOZf1` |  |
| PK Zb 19 | `PKZb19` |  |
| PK Za 20 | `PKZa20` |  |
| PK Zb 21 | `PKZb21` |  |
| PK Wy 22 | `PKZg22` | held as Zg 'Stone object'; RILA-S1 classes it Wy (sealed object) |
| PK Zb 24 | `PKZb24` |  |
| PK Zb 25 | `PKZb25` |  |
| PK Zb 26 | `PKZb26` |  |
| PK Za 27 | `PKZa27` |  |
| PK Za 28 | `PKZa28` |  |
| PE 1 | `PE1` |  |
| PE 2 | `PE2` |  |
| PE Zb 3 | `PEZb3` |  |
| PE Zc <4> | `PEZc4` |  |
| PE Wy 5 | `PEWy5` |  |
| PE 6 | `PE6` |  |
| PE Zb 7 | `PEZb7` |  |
| PH Wa 52 | `PHWa52` |  |
| PH 54 | `PH54` |  |
| PO Zg 1 | `POZc1` | held as Zc 'Inked inscription' (alias PORZg1) |
| PO Zf 2 | `PORZf2` | key prefix PORZf |
| PSE Zb 1 | `PSIZa1` | held as PSIZa1 (names PSEZb1); site and support mislabelled Psykhro, stone vessel |
| PYR Wc 4 | `PYRWc4` |  |
| SA We 3 | `SAMWa1` | CMS V Suppl. 1B no. 327, 'Wa 1' in CMS; key superseded |
| SA We 4 | `SAMWe4` |  |
| SKO Zc 1 | `SKOZc1` |  |
| SKO Zc 2 | `SKOZc2` |  |
| SY Za 3 + frs (2) | `SYZa3` | GORILA V SY Za 3, completed with two fragments |
| SY Za 4 | `SYZa4` |  |
| SY Za 5 | `SYZa5` |  |
| SY Za 6 | `SYZa6` |  |
| SY Za 8 | `SYZa8` |  |
| SY Za 9 | `SYZa9` |  |
| SY Za 10 | `SYZa10` |  |
| SY Za 11 | `SYZa11` |  |
| SY Za 12 | `SYZa12` |  |
| SY Zb 7 | `SYZb7` |  |
| THE Zg 5 | `THEZg5` |  |
| THE Zb 6 | `THEZb6` |  |
| THE 7 | `THE7a`, `THE7b` |  |
| THE 8 | `THE8` |  |
| THE 9 | `THE9` |  |
| THE 10 | `THE10` |  |
| THE 11 | `THE11` |  |
| THE 12 | `THE12` |  |
| THE Zb 13 | `THEZb13` |  |
| ZA Zg 35 | `ZAZg35` |  |
| ZA Wa 36 | `ZAWa36` |  |
| ZA Wb 37 | `ZAWb37` |  |
| ZA Wa 38 | `ZAWa38` |  |
<!-- END kaphtor:census rila-accepted -->

## 4. RILA-S1 doubtful inscriptions (D1–D26) in the corpus

RILA-S1 edits these separately, does not count them and leaves them out of its sign index (p. xxiii). Each record that holds one is tagged `rila_s1.status: "doubtful"`.

<!-- BEGIN kaphtor:census rila-doubtful -->
The corpus holds 23 of the 26, as 24 records.

| RILA-S1 | Corpus key(s) |
|---|---|
| D 1 KN Wc 23 | `KNWc23` |
| D 2 KN Wc 43 | `KNWc43` |
| D 3 TY Wc 5 | `TYWc5` |
| D 4 NE Za 1 | `NEZa1` |
| D 5 LACH Za 1 | `LACHZa1` |
| D 6 VRY Za 4 | not held |
| D 7 INA Zb 1 | `INZb1` |
| D 8 KN Zb 36a-d (GORILA Zb <36>, <37>) | `KNZb36`, `KNZb37` |
| D 9 MI Zb 3 | `MIZb3` |
| D 10 PK Zb <23> | `PKZb23` |
| D 11 PH fr. vase (2017) | not held |
| D 12 PYR Zb 5 | `PYRZb5` |
| D 13 HAR Zb 1 | `TELZb1` |
| D 14 THE fr. vase (TE Z 4, THE Zb 14) | `THEZb7` |
| D 15 THE Zb 14 (formerly THE Zb 15) | `THEZb15` |
| D 16 TI Zb 1 | `TIZb1` |
| D 17 VRY Zb 2 | `VRYZb2` |
| D 18 VRY Zb 3 | `VRYZb3` |
| D 19 PH fr. vase (1965-66) | not held |
| D 20 KN Ze <56> | `KNZe56` |
| D 21 HT bronze figurine | `HTZf(HM767)` |
| D 22 ARM Zg 1 | `ARMZg1` |
| D 23 CR (?) Zg 3 | `CRZg3` |
| D 24 DRA Zg 1 | `DRAZg1` |
| D 25 KN amygdaloid seal (Cn 12) | `KNsceau` |
| D 26 THE Zg 15 | `THEZg15` |

Listed by RILA-S1 but not counted, held in the corpus: `HTWc3023` ({HT Wc 3023} uninscribed); `PEZb8` ((PE Zb 8) isolated sign); `PSIZa2` ((PSE Zb 2) isolated sign); `PHWb55` ({PH Wb 53} uninscribed (Minoan Roundel II: PH Wb 55)).
<!-- END kaphtor:census rila-doubtful -->

## 5. Why the corpus holds more documents than the published census

Each document of the corpus falls in exactly one class, taken in this order: outside the Linear A area (by site), RILA-S1 accepted, RILA-S1 doubtful, RILA-S1 listed but not counted, published after 2023, outside both editions, GORILA labelled, GORILA unlabelled, unresolved.

<!-- BEGIN kaphtor:census classes -->
| Class | Documents |
|---|---:|
| outside the Linear A area | 3 |
| RILA-S1 accepted | 110 |
| RILA-S1 doubtful | 24 |
| RILA-S1 listed, not counted | 4 |
| published after 2023 | 2 |
| outside both editions | 37 |
| GORILA, labelled | 1,370 |
| GORILA, unlabelled | 50 |
| unresolved | 3 |
| **Total** | **1,603** |

The 107 RILA-S1 documents count as 110 here, since KH Wc 2059 [+] 2091 [+] 2092 is held as 3 documents (`KHWc2059`, `KHWc2091`, `KHWc2092`); KH Wc 2088 [+] 2089 [+] fr. is held as 2 documents (`KHWc2088`, `KHWc2089`).
<!-- END kaphtor:census classes -->

### GORILA documents held without the label

<!-- BEGIN kaphtor:census gorila-unlabelled -->
GORILA V identifies 57 documents that lineara.xyz held without the label `GORILA`. 7 of them now carry it (`HT123+124`, `KNWb33`, `KO(?)Zf2`, `PH30`, `TY2`, `TY3`, `ZA1`), so the class counts 50.
<!-- END kaphtor:census gorila-unlabelled -->

Joins and sides keep GORILA's designation; `HTZd157+156` is one record for GORILA's separately catalogued HT Zd 156 and HT Zd 157.

| Volume | Sigla (corpus keys) |
|---|---|
| I | HT 42[+]59, HT 62[+]73, HT 79[+]83, HT 113ter, HT 123+124, HT 154 (`HT154.`), PH <29>, PH 30, PH(?) 31, PYR 1, TY 2, TY 3, ZA 1 |
| II | GO Wc 1; HT Wa <1021bis>, HT Wa 1146–1170 (from p. 18); HT Wc <3018>; KN Wb 33; MA Wc <5>; PH Wb 33–36. Reclassified since GORILA: HT Wa 1617 and 1663 (now Wd), PH Wc 42 (now Wy 42), PH Wc 45 (now Wg 45), PH Wc <47> (now Zb <47>) |
| III | KH 68+71 |
| IV | HT Zd 156, HT Zd 157; KO(?) Zf 2; LA Zb 1(bis) |
| V | HT(?) Wc 3022 |

### Check against GORILA V's general concordance

GORILA V's general concordance (pp. 83–113) lists exactly 1,427 documents, and every one is in the corpus. ZA 18a [+] 18b is one document. The 1,427 fall into the classes above as follows:

<!-- BEGIN kaphtor:census gorila-check -->
| Class | GORILA documents |
|---|---:|
| GORILA, labelled | 1,370 |
| GORILA, unlabelled | 50 |
| second sigla in one record (`HTZd157+156`) | 1 |
| RILA-S1 accepted (`KHWc2059`, `KHWc2070`, `KNZb27`, `SYZa3`) | 4 |
| RILA-S1 doubtful (`KNZb36`, `KNZb37`) | 2 |
| **Total** | **1,427** |
<!-- END kaphtor:census gorila-check -->

Four records that lineara.xyz or SigLA held as GORILA documents are not GORILA documents in their own right:

- `KH79` was SigLA's record of the fragment KH 79, which GORILA V counts only in the join KH 79 + 89; it is merged into `KH79+89`.
- GORILA V brackets KN (?) Wc <24> as withdrawn, "= HT Wc 3004" (p. 109); `KNWc<24a>`/`KNWc<24b>` are merged into `HTWc3004`, and SigLA's reading stays in the snapshot.
- GORILA V also withdraws KN Wc 25 (p. 109); `KNWc<25>` falls outside both editions.
- `THEZb5`, labelled GORILA, is not in GORILA V, which has THE Zb 1–4 only. It holds one sign and falls outside both editions. RILA-S1's THE Zb 6 is a different reading, held as `THEZb6`.

### Second records merged into their keeper

Some objects were catalogued twice, usually once from lineara.xyz and once from a later publication. Each second record sits in its keeper's `merged_records` as a full snapshot, its key among the keeper's `names`; where the readings differ, the keeper carries the edition's reading (RILA-S1 for the Thera tablets) and the snapshot keeps the other.

<!-- BEGIN kaphtor:census merged -->
15 second records of 14 objects:

| Second record | Keeper |
|---|---|
| `FOZc1` | `ARKHZc8` |
| `HTWa1845+1733` | `HTWa1733` |
| `KHWc2096` | `KHWc2044` |
| `KNWb50` | `KNWa50` |
| `KNWb51` | `KNWa51` |
| `MYZf1` | `MYZf2` |
| `THEfr.1` | `THE10` |
| `THEfr2` | `THE11` |
| `THEfr3` | `THE12` |
| `THEtab.4` | `THE7` |
| `THEtab.5` | `THE9` |
| `THEtab.6` | `THE8` |
| `KNWc<24a>`, `KNWc<24b>` | `HTWc3004` |
| `KH79` | `KH79+89` |
<!-- END kaphtor:census merged -->

On the keepers: Fourni is the Arkhanes cemetery (`ARKHZc8`); `HTWa1733` and `KH79+89` are GORILA V's joins, as is `KHWc2044` (KH Wc 2044+2096); `HTWc3004` follows GORILA V, p. 109; `KNWa50` and `KNWa51` take RILA-S1's class Wa.

### Outside both editions

<!-- BEGIN kaphtor:census outside-editions -->
These 37 documents fall outside both GORILA and RILA-S1: `ANZb1`, `ARGZg1`, `CRZf5`, `HTW231`, `HTWb229`, `HTZb162bis`, `HTZf163`, `HTZf164`, `HTZf165`, `HTZf166`, `HTZf167`, `HTZf168`, `HTZf169`, `IOZa<1>`, `KAMZb1`, `KANZa1`, `KEZb6`, `KEZb7`, `KNWc<25>`, `KNZd46`, `KNZe44`, `KNZe45`, `KNZe49`, `MOZb2?`, `MOZb3?`, `MYZf2`, `MYZg1`, `PK3`, `PKZbX`, `SEZf1`, `THEZb5`, `THEZg16`, `TRYZb1`, `ZAZb39`, `ZAZg34`, `ZO1`, `ZOZa1`.
<!-- END kaphtor:census outside-editions -->

They fall into four groups:

- **Isolated signs and marks**, excluded by RILA-S1's two-sign rule (p. xviii):
  - ingot marks HT Zf 163–169 (Younger calls HT Zf 169 "not Linear A");
  - single signs on vessels, ANZb1, HT Zb 162bis, KE Zb 6, KE Zb 7, and `THEZb5`;
  - CR Zf 5;
  - the six HT W 231 plaques (`HTW231`, held as one record);
  - the sealing HT Wb 229;
  - the Mycenae cauldron and stele (`MYZf2`, `MYZg1`).
- **Disputed as script:**
  - KAN Za 1, which GORILA IV excludes as a pseudo-inscription;
  - the Knossos architectural signs KN Zd 46 and KN Ze 44, 45, 49, read as mason's marks or early Linear B;
  - the Argos stele (`ARGZg1`);
  - the signs on the Zominthos offering table (`ZOZa1`), which RILA-S1 declines to admit (p. xix n. 12).
- **Known but outside both counts:**
  - IO Za <1>, lost and unseen by GORILA;
  - KAM Zb 1;
  - KN Wc 25 (`KNWc<25>`), withdrawn by GORILA V (p. 109);
  - PK 3;
  - SE Zf 1;
  - TRY Zb 1;
  - ZA Zg 34.
- **Announced or published after RILA-S1's coverage:**
  - MO Zb 2–3;
  - PK Zb (`PKZbX`);
  - ZA Zb <39>;
  - THE Zg 16 (excavated 2019);
  - the Zominthos tablet (`ZO1`), awaiting publication (RILA-S1, p. xvii n. 6).

### Unresolved

`PETSWc` (a Petsophas roundel), `PEWs` and `PEZb` (Petras) have no inventory number or publication behind them. They stay uncounted until a primary source establishes them.

## 6. Reproduction

- Documents and classes: `tools/views/counts.py` (`doc_id`, `classify`), reading the hand-curated sets in `data/linear-a/census_classes.json`.
- This file's blocks: `python -m tools.views.census_doc --data data/linear-a` checks them, and `--write` rewrites them from the data.
- The wiki's `counts` page carries the same class table.

## Sources

- Godart, L. & Olivier, J.-P. (1976–1985). *Recueil des inscriptions en linéaire A* (GORILA). 5 vols. Études Crétoises XXI. École française d'Athènes; Paris: Librairie orientaliste Paul Geuthner.
- Del Freo, M. & Zurbach, J. (2024). *Recueil des inscriptions en linéaire A. Vol. 6. Supplément 1* (RILA-S1). Études Crétoises XXI.6. Athens: École française d'Athènes. LXIV + 256 pp. ISBN 978-2-86958-642-0. Released May 2025 (CNR 2025).
- Hallager, E. (1996). *The Minoan Roundel and Other Sealed Documents in the Neopalatial Linear A Administration*. 2 vols. Aegaeum 14. Liège: Université de Liège.
- Andreadaki-Vlasaki, M. & Hallager, E. (2007). "New and unpublished Linear A and Linear B inscriptions from Khania." *Proceedings of the Danish Institute at Athens* V.
- Kanta, A., Nakassis, D., Palaima, T. G. & Perna, M. (2024). "An archaeological and epigraphical overview of some inscriptions found in the Cult Center of the city of Knossos (Anetaki plot)." In J. Bennet, A. Karnava & T. Meissner (eds.), *KO-RO-NO-WE-SA*, *Ariadne* Suppl. 5: 27–43. Rethymno: University of Crete.
- Salgarella, E. & Castellan, S. (2021). "SigLA: The Signs of Linear A. A Palæographical Database." In Y. Haralambous (ed.), *Grapholinguistics in the 21st Century 2020: Proceedings, Part 2*, pp. 945–962. Brest: Fluxus Editions. Database: sigla.phis.me.
- Hogan, R. (2019–). *Linear A Explorer*. lineara.xyz.
- Younger, J. G. *Linear A Texts in Phonetic Transcription* (archived).
