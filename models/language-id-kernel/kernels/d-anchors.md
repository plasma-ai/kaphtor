---
name: models/language-id-kernel/kernels/d-anchors
title: "Kernel D: Pre-Linguistic Semantic Anchors"
desc: "Bayesian marginal log-likelihood over eight arithmetic, vessel, and grain anchors fixed before any language is named, with 11-way ablations."
tags: [linear-a, kernel-d, anchors, primary]
created: 2026-11-23T19:35:00Z
updated: 2026-11-27T11:08:00Z
---

# Kernel D: Pre-Linguistic Semantic Anchors

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/anchors_d.py` + `stress_test_cd.py`
- **Unit Test:** `models/language-id-kernel/tests/test_anchors_d.py`
- **Run Ledgers:** `runs/kaphtor-kernel-linear-a-20261122T222434Z.json`, `runs/stress-test-cd-2026-11-22.json`
- **Channel Classification:** **Primary consonant-specific phonetic proof** (core phonetic driver of `A+B+D`)
- **Command:** `uv run --no-sync python models/language-id-kernel/anchors_d.py --calibrate --run-linear-a --n-perm 10000`

## 2. Method & Statistic

Scores **eight Linear A words whose meanings are fixed pre-linguistically** by tablet arithmetic or adjacent vessel/grain logograms before any language is named. Each modeled language supplies a bounded synset (4–6 core attested lexemes per concept), forward-spelled through `render/c_render.word` + glide rule and scored by Bayesian marginal log-likelihood (log-mean-exp over synset, $\beta = 6.0$, normalized CV edit distance $d \in [0, 1]$) against $B = 10{,}000$ consonant-series grid permutations.

## 3. Data Called Upon

- **Target (`LINEAR_A_ANCHORS_STRICT`):** `KU-RO` (`TOTAL`), `KI-RO` (`DEFICIT`), `A-KA-NU`, `SU-PU`, `PA-TA-QE`, `KA-DI` (`VESSEL_CUP`), `KU-NI-SU`, `PA-RA` (`GRAIN`).
- **Calibration target (`LINEAR_B_ANCHORS`):** `TO-SO` (`TOTAL`), `O-PE-RO` (`DEFICIT`), `TI-RI-PO` (`VESSEL_CUP`), `DI-PA` (`VESSEL_CUP`), `SI-TO` (`GRAIN`), `WO-NO` (`WINE`).
- **Reference:** Self-contained bounded synsets for Semitic, Greek, Anatolian, and Hurrian + frozen `render/series.json` (zero external files required; audited blind without hand-curation by [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]]).

## 4. Calibration Gate (`B = 10,000`)

- **Linear B Gate:** **PASS**
  - **Greek:** `LL = -11.321`, **`Z_perm = +7.97`**, **`p_perm = 0.00010`** (`0/10,000`)
  - Anatolian (IE cousin): `LL = -24.476` (`Z_perm = +3.29`, $\Delta\text{LL} = -13.15$)
  - Hurrian: `LL = -28.086` (`Z_perm = +1.40, p = 0.097`)
  - **Semitic (rejected):** `LL = -28.598` (`Z_perm = +1.28, p = 0.111`)

## 5. Linear A Results & 11-Way Ablations (`runs/stress-test-cd-2026-11-22.json`, `B = 10,000`)

| Subset | $n$ | Winner | Semitic `LL` | $\Delta\text{LL}$ vs. Runner-Up | `Z_perm` | `p_perm` |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| **`FULL_8`** | **8** | **Semitic** | **`-19.072`** | **`+13.585`** (~794,000 : 1) | **`+7.37`** | **`0.00010`** |
| `DROP_KU-RO` | 7 | Semitic | `-16.907` | `+11.161` | `+7.55` | `0.00010` |
| `DROP_KI-RO` | 7 | Semitic | `-16.948` | `+13.035` | `+7.65` | `0.00010` |
| `DROP_A-KA-NU` | 7 | Semitic | `-17.409` | `+10.875` | `+7.48` | `0.00010` |
| `DROP_SU-PU` | 7 | Semitic | `-17.362` | `+10.527` | `+6.45` | `0.00010` |
| `DROP_PA-TA-QE` | 7 | Semitic | `-14.310` | `+13.232` | `+7.40` | `0.00010` |
| `DROP_KA-DI` | 7 | Semitic | `-16.611` | `+12.242` | `+7.67` | `0.00010` |
| `DROP_KU-NI-SU` | 7 | Semitic | `-17.489` | `+11.587` | `+6.59` | `0.00010` |
| `DROP_PA-RA` | 7 | Semitic | `-16.467` | `+12.070` | `+6.88` | `0.00010` |
| **`DROP_3_TRADE_LOANS`** (`A-KA-NU`, `KU-NI-SU`, `KA-DI`) | **5** | **Semitic** | **`-13.365`** | **`+7.534`** (~1,860 : 1) | **`+6.22`** | **`0.00010`** |
| **`ARITHMETIC_ONLY_2`** (`KU-RO`, `KI-RO`) | **2** | **Semitic** | **`-4.288`** | **`+2.610`** (~13.6 : 1) | **`+4.59`** | **`0.00640`** |

## 6. What It Proves & Honest Limits

Kernel D provides strong consonant-specific lexical evidence for Semitic on pre-linguistic vocabulary that survives all 8 leave-one-out drops, removal of all three trade-loan suspects (`~1,860 : 1`), and pure arithmetic (`KU-RO`/`KI-RO`) alone. Because its bounded synsets are curated, [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]] independently audits the anchor class with zero hand-selection over open JSONL dictionaries. For an exploratory post-registration sensitivity study scaling the same frozen synsets to `n = 8 → 13` zero-`KA-PA` anchors (`~1.58M : 1` strict-LB, `~2.76M–7.97M : 1` with `HT 31 PA₃` vessels) without altering signed Kernel D, see [[models/language-id-kernel/kernel-d-sensitivity-expansion|Hypothetical Kernel D′ (`n = 8 → 13`)]].
