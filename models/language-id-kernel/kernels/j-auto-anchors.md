---
name: models/language-id-kernel/kernels/j-auto-anchors
title: "Kernel J: Zero-Curation Automated Dictionary Audit"
desc: "Audits pre-linguistic anchors with zero hand-picked synsets over shipped open JSONL lexica (including CC0 ePSD2 Sumerian) under dual phonetic and semantic nulls."
tags: [linear-a, kernel-j, anchors, zero-curation, primary]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel J: Zero-Curation Automated Dictionary Audit

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/auto_anchors_j.py`
- **Unit Test:** `models/language-id-kernel/tests/test_auto_anchors_j.py`
- **Run Ledgers:** `runs/auto-anchors-j-standalone-2026-11-23.json`, `runs/auto-anchors-j-2026-11-23.json`
- **Channel Classification:** **Primary anti-curation-bias audit** of [[models/language-id-kernel/kernels/d-anchors|Kernel D]]
- **Command:** `uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000`

## 2. Method & Statistic

Eliminates researcher degrees of freedom in synset curation by extracting **every matching headword automatically** from independent open JSONL dictionaries using fixed English concept regexes on the `meaning` field alone (zero hand-picked words, zero project-lexicon inputs), capped by gloss specificity (`cap = 40` and uncapped) and scored by Bayesian marginal log-likelihood (naturally penalizing bloated synsets via $1/|C|$).

Every language must pass **two orthogonal nulls simultaneously**:

1. **10,000 consonant-series grid permutations** (`p_perm`)
2. **Exact concept-label shuffle** over all distinct concept assignments (`6! = 720` on Linear B; `8! / (2!·2!·2!) = 5,040` on Linear A `FULL_8`, `p_concept`)

## 3. Data Called Upon (Shipped Defaults in `v1.3.0`)

- **Linear A `FULL_8` (`LA_ANCHORS`):** `KU-RO`, `KI-RO`, `PO-TO-KU-RO` (`TOTAL`/`DEFICIT`), `A-KA-NU`, `KA-PA` (`BOWL`), `SU-PU`, `KA-DI` (`JAR`), `KU-NI-SU` (`WHEAT`) — sharing 6 anchors with [[models/language-id-kernel/kernels/d-anchors|Kernel D]] while splitting `VESSEL_CUP` into `BOWL`/`JAR` and substituting `PO-TO-KU-RO`/`KA-PA` for `PA-TA-QE`/`PA-RA`.
- **Linear B Calibration (`LB_ANCHORS`):** `TO-SO` (`TOTAL`), `O-PE-RO` (`DEFICIT`), `TI-RI-PO` (`TRIPOD`), `A-PI-PO-RE-WE` (`JAR`), `PA-KA-NA` (`SWORD`), `SI-TO` (`WHEAT`).
- **Shipped lexica:**
  - `semitic`: `data/contact/akkadian_lexicon.jsonl` (CC0 1.0) + `data/contact/hebrew_lexicon.jsonl` (CC BY 4.0 / PD)
  - `greek`: `data/share-alike/greek/lsj_glosses.jsonl` (`101,410` glossed LSJ entries; CC BY-SA 4.0)
  - `sumerian` *(Bronze Age isolate control)*: `data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl` (`3,589` clean vocalized ePSD2 lemmas; CC0 1.0)
  - *(Optional `KAPHTOR_CONTACT_DIR` adds private Ugaritic, Anatolian, Hurrian and Egyptian lexica.)*

## 4. Calibration Gate (Linear B `n = 6`, `B = 10,000`, `720` Concept Perms)

| Run | Greek | Sumerian (ePSD2) | Semitic |
| --- | --- | --- | --- |
| **Standalone (`v1.3.0`)** | **`LL = -21.99, ΔLL = +3.88, p_perm = 0.00010, p_concept = 0.01389`** *(only pass)* | `LL = -25.86, p_perm = 0.06079` *(fails grid)* | `LL = -28.26, p_perm = 0.16978, p_concept = 0.77500` |
| **Pre-Sumerian 5-lang** | **`LL = -22.09, ΔLL = +6.59, p_perm = 0.00010, p_concept = 0.01250`** *(only pass)* | — | `LL = -28.68, p_perm = 0.23148, p_concept = 0.69306` |

## 5. Linear A Results (`FULL_8`, `B = 10,000`, `5,040` Concept Perms)

### `v1.3.0` Standalone (`runs/auto-anchors-j-standalone-2026-11-23.json`)

| Language | `LL` | `Z_perm` | `p_perm` | `Z_concept` | `p_concept` |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Semitic (Akk+Heb)** | **`-29.187`** | **`+3.75`** | **`0.00010`** | **`+1.93`** | **`0.02520`** *(only dual-null pass)* |
| Sumerian (ePSD2) | `-33.241` | `+3.24` | `0.00550` | `-0.50` | `0.63651` |
| Greek (LSJ) | `-33.287` | `+2.50` | `0.01070` | `-0.26` | `0.58849` |

- **Ablations (standalone):** Semitic also wins `NO_LOANS_5` (`ΔLL = +2.534, p_perm = 0.00010`) and `ARITH_2` (`KU-RO`/`KI-RO`, `ΔLL = +1.190, p_perm = 0.01680`).
- **Pre-Sumerian 5-language full set (`runs/auto-anchors-j-2026-11-23.json`):** Semitic is again the **only dual-null pass** (`LL = -27.447`, `ΔLL = +2.34` vs Hurrian, `+5.83` vs Greek; `Z_perm = +4.85, p_perm = 0.00010`; `Z_concept = +2.51, p_concept = 0.00893`; Hurrian `p_concept = 0.103`, Greek `0.548`, Anatolian `0.635`, Egyptian `0.911`).

## 6. What It Proves & Honest Limits

Confirms that the pre-linguistic anchor match to Semitic survives **zero human word curation**, holds against both the full 101,410-entry LSJ Greek dictionary and a dense Bronze Age non-Semitic isolate (**Sumerian ePSD2**), and specifically tracks the words' pre-linguistic meanings (`p_concept`). Running `--ligatures` on single-syllable adjuncts saturates a 40-word open dictionary (Linear B fails its Greek gate at `p = 0.348`), confirming multi-syllable anchors as primary.
