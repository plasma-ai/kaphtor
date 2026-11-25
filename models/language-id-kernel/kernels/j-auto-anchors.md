---
name: models/language-id-kernel/kernels/j-auto-anchors
title: "Kernel J: Zero-Curation Automated Dictionary Audit"
desc: "Audits pre-linguistic anchors with zero hand-picked synsets over shipped open JSONL lexica (including CC0 ePSD2 Sumerian) under dual phonetic and semantic nulls."
tags: [linear-a, kernel-j, anchors, zero-curation, primary]
created: 2026-11-23T19:35:00Z
updated: 2026-11-25T15:15:00Z
---

# Kernel J: Zero-Curation Automated Dictionary Audit

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/auto_anchors_j.py`
- **Unit Test:** `models/language-id-kernel/tests/test_auto_anchors_j.py`
- **Run Ledgers:** `runs/auto-anchors-j-standalone-2026-11-25.json` (`B = 10,000`, incl. deduplicated & expanded pre-linguistic tiers), `runs/auto-anchors-j-standalone-2026-11-23.json`, `runs/auto-anchors-j-2026-11-23.json`
- **Channel Classification:** **Primary anti-curation-bias audit** of [[models/language-id-kernel/kernels/d-anchors|Kernel D]]
- **Command:** `uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000 --seed 20261125`

## 2. Method & Statistic

Eliminates researcher degrees of freedom in synset curation by extracting **every matching headword automatically** from independent open JSONL dictionaries using fixed English concept regexes on the `meaning` field alone (zero hand-picked words, zero project-lexicon inputs), capped by gloss specificity (`cap = 40` and uncapped) and scored by Bayesian marginal log-likelihood (naturally penalizing bloated synsets via $1/|C|$).

Every language must pass **two orthogonal nulls simultaneously**:

1. **10,000 consonant-series grid permutations** (`p_perm`)
2. **Concept-label shuffle** holding real sign values fixed and shuffling which concept maps to which word (exact enumeration for `n <= 8`: `720` on Linear B `n = 6`, `5,040` on `FULL_8`, `1,260` on `DEDUP_7`; `10,000`-draw Monte Carlo for `n > 8`, `p_concept`)

## 3. Data Called Upon (Shipped Defaults)

- **Linear A `FULL_8` (`LA_ANCHORS`, untouched signed baseline):** `KU-RO`, `KI-RO`, `PO-TO-KU-RO` (`TOTAL`/`DEFICIT`), `A-KA-NU`, `KA-PA` (`BOWL`), `SU-PU`, `KA-DI` (`JAR`), `KU-NI-SU` (`WHEAT`).
- **Linear A `LA_DEDUP_7` (deduplicated baseline):** drops `PO-TO-KU-RO` so `KU-RO` is never double-counted.
- **Linear A `LA_DEDUP_9` (Tier 1a — purest 100% strict `signs-a5-proposed.json` inventory):** adds `PA-TA-QE` (`HT 31 *402-VS` vessel drawing) and **`DA-RO-PA` (`HT 38 *403-VS` vessel drawing, untranslated blind inclusion absent from the project lexicon)**—zero `PA₃` doublet folding, zero `PA-RA` header inference, zero `MA+RU` monogram.
- **Linear A `LA_DEDUP_12` (Tier 2a — full `HT 31` + `HT 38` literal vessel drawings, sensitivity tier):** adds `HT 31`'s three literal vessel drawings (`QA-PA₃`, `KA-RO-PA₃`, `SU-PA₃-RA`) by folding GORILA doublet `AB 56` (`PA₃ → PA`, kept opaque in `signs-a5-proposed.json` §15 ruling 3 and Tier 1).
- **Linear A `LA_DEDUP_11` & `LA_DEDUP_14` (extended sensitivity tiers):** add Kernel D's `PA-RA` (`HT 128a` tablet heading above `GRA` entries—header inference rather than direct ligature) and the `MA+RU` (`A558`/`LANA`) wool monogram (distinct from the `HT 117a` syllabic personal name `MA-RU`); `LA_DEDUP_14` additionally folds `PA₃` on the three `HT 31` vessels.
- **Linear A `LA_DROPK_5` (`K`-series-free subset of `LA_DEDUP_11`):** `SU-PU`, `PA-TA-QE`, `DA-RO-PA`, `PA-RA`, `MA+RU`—tests consonant-grid `p_perm` survival without `K`-series signs (`p_concept` is underpowered at `n = 5` / `60` perms).
- **Linear B Calibration (`LB_ANCHORS` `n = 6` & `LB_ANCHORS_EXT9` `n = 9`):** `TO-SO`, `O-PE-RO`, `TI-RI-PO`, `A-PI-PO-RE-WE`, `PA-KA-NA`, `SI-TO`, extended with `DI-PA` (`BOWL`), `WO-NO` (`WINE`), and `E-RA-WO` (`OIL`).
- **Shipped lexica:**
  - `semitic`: `data/contact/akkadian_lexicon.jsonl` (CC0 1.0) + `data/contact/hebrew_lexicon.jsonl` (CC BY 4.0 / PD)
  - `greek`: `data/share-alike/greek/lsj_glosses.jsonl` (`101,410` glossed LSJ entries; CC BY-SA 4.0)
  - `sumerian` *(Bronze Age isolate control)*: `data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl` (`3,589` clean vocalized ePSD2 lemmas; CC0 1.0)
  - *(Optional `KAPHTOR_CONTACT_DIR` adds private Ugaritic, Anatolian, Hurrian and Egyptian lexica.)*

## 4. Calibration Gate (Linear B `n = 6` & `n = 9`, `B = 10,000`)

| Run | Greek | Sumerian (ePSD2) | Semitic |
| --- | --- | --- | --- |
| **Standalone `n = 6`** | **`LL = -21.99, ΔLL = +3.88, p_perm = 0.00010, p_concept = 0.01389`** *(only pass)* | `LL = -25.86, p_perm = 0.06119` *(fails grid)* | `LL = -28.26, p_perm = 0.18378, p_concept = 0.77500` |
| **Standalone `EXT9` (`n = 9`)** | **`LL = -34.18, ΔLL = +6.18 (~481:1), p_perm = 0.00010, p_concept = 0.00020`** *(only pass)* | `LL = -40.36, p_perm = 0.14799, p_concept = 0.10419` | `LL = -41.70, p_perm = 0.11459, p_concept = 0.29317` |
| **Pre-Sumerian 5-lang (`n = 6`)** | **`LL = -22.09, ΔLL = +6.59, p_perm = 0.00010, p_concept = 0.01250`** *(only pass)* | — | `LL = -28.68, p_perm = 0.23148, p_concept = 0.69306` |

## 5. Linear A Results (`runs/auto-anchors-j-standalone-2026-11-25.json`, `B = 10,000`)

| Tier | `n` | Sign / Inclusion Scope | Winner | `ΔLL` (BF) | Semitic `Z_perm / p_perm` | Semitic `Z_concept / p_concept` | Greek `p_concept` | Sumerian `p_concept` |
| --- | ---: | --- | --- | ---: | --- | --- | ---: | ---: |
| **`FULL_8`** | `8` | Signed baseline (strict LB) | **Semitic** | `+4.054` (`57.6:1`) | `+3.75 / 0.00010` | **`+1.93 / 0.02520`** *(5,040 exact)* | `0.58849` | `0.63651` |
| **`LA_DEDUP_7`** | `7` | Drops `PO-TO-KU-RO` (strict LB) | **Semitic** | `+4.342` (`76.9:1`) | `+3.90 / 0.00010` | **`+2.06 / 0.01111`** *(1,260 exact)* | `0.73095` | `0.57778` |
| **`LA_DEDUP_9`** | `9` | Purest strict LB (`+PA-TA-QE`, blind `DA-RO-PA`) | **Semitic** | **`+3.863` (`47.6:1`)** | **`+3.89 / 0.00010`** | **`+2.42 / 0.00390`** *(10k MC)* | `0.62574` | `0.66343` |
| **`LA_DEDUP_12`** | `12` | `LA_DEDUP_9` + `3` `HT 31` `PA₃→PA` doublet vessels | **Semitic** | **`+4.200` (`66.7:1`)** | **`+3.73 / 0.00010`** | **`+2.73 / 0.00180`** *(10k MC)* | `0.63274` | `0.85551` |
| **`LA_DEDUP_11`** | `11` | `LA_DEDUP_9` + `PA-RA` header + `MA+RU` monogram | **Semitic** | `+4.285` (`72.6:1`) | `+3.89 / 0.00010` | **`+2.05 / 0.01560`** *(10k MC)* | `0.79052` | `0.61954` |
| **`LA_DEDUP_14`** | `14` | `LA_DEDUP_11` + `3` `HT 31` `PA₃→PA` doublet vessels | **Semitic** | `+4.623` (`101.8:1`) | `+3.66 / 0.00020` | **`+2.26 / 0.00920`** *(10k MC)* | `0.79352` | `0.83422` |
| **`LA_DROPK_5`** | `5` | `K`-free subset of `LA_DEDUP_11` | **Semitic** | `+1.233` (`3.4:1`) | **`+2.19 / 0.01640`** | `+0.97 / 0.21667` *(fails; 60 exact)* | `0.41667` | `0.66667` |

- **Additional ablations (standalone):** Semitic also wins `NO_LOANS_5` (`ΔLL = +2.534, p_perm = 0.00030`) and `ARITH_2` (`KU-RO`/`KI-RO`, `ΔLL = +1.190, p_perm = 0.01350`; LSJ Greek rejected `0.05019`).
- **Pre-Sumerian 5-language full set (`runs/auto-anchors-j-2026-11-23.json`):** Semitic is again the **only dual-null pass** (`LL = -27.447`, `ΔLL = +2.34` vs Hurrian, `+5.83` vs Greek; `Z_perm = +4.85, p_perm = 0.00010`; `Z_concept = +2.51, p_concept = 0.00893`; Hurrian `p_concept = 0.103`, Greek `0.548`, Anatolian `0.635`, Egyptian `0.911`).

## 6. What It Proves & Honest Limits

Confirms that the pre-linguistic anchor match to Semitic survives **zero human word curation**, **zero double-counting (`LA_DEDUP_7`)**, and **blind inclusion of untranslated vessel drawings (`DA-RO-PA` on `HT 38`, `LA_DEDUP_9` `p_concept = 0.00390`, `p_perm = 0.00010`)** strictly inside `signs-a5-proposed.json`. Folding GORILA doublet `AB 56` (`PA₃ → PA`, kept opaque in `signs-a5-proposed.json` §15 ruling 3) on `HT 31`'s three remaining vessel drawings sharpens `p_concept` further to **`0.00180`** (`LA_DEDUP_12`, `66.7:1`), while adding `PA-RA` (`HT 128a` header) and `MA+RU` (`LANA` monogram) yields `LA_DEDUP_11` (`72.6:1, p_concept = 0.01560`) and `LA_DEDUP_14` (`101.8:1, p_perm = 0.00020, p_concept = 0.00920`), with `K`-free `LA_DROPK_5` passing consonant-grid permutation (`p_perm = 0.01640`) while underpowered on concept-shuffle (`p_concept = 0.21667`). Running `--ligatures` on single-syllable adjuncts saturates a 40-word open dictionary (Linear B fails its Greek gate at `p = 0.348`), confirming multi-syllable anchors as primary.
