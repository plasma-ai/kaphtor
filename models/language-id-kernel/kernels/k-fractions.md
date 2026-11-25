---
name: models/language-id-kernel/kernels/k-fractions
title: "Kernel K: Corazza–Ferrara Fractions & Blind Accounting Discovery"
desc: "Applies Corazza, Ferrara, Montecchi, Tamburini & Valério (2021) A700 fraction values to raw Unicode glyphs to emit a 3D/RTI conflict ledger, blindly discover KU-RO at rank #1, and score only the accounting triad under Linear B Greek calibration."
tags: [linear-a, kernel-k, metrology, fractions, corazza-2021]
created: 2026-11-24T00:00:00Z
updated: 2026-11-24T00:00:00Z
---

# Kernel K: Corazza–Ferrara Fractions & Blind Accounting Discovery

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/fractions_k.py`
- **Unit Test:** `models/language-id-kernel/tests/test_fractions_k.py`
- **Run Ledger:** `runs/kernels-kl-2026-11-24.json` (`kernel_k`)
- **Primary Reference:** Corazza, M., S. Ferrara, B. Montecchi, F. Tamburini, & M. Valério (2021), "The mathematical values of fraction signs in the Linear A script: A computational, statistical and typological approach", *Journal of Archaeological Science* 125: 105214 (`10.1016/j.jas.2020.105214`).
- **Channel Classification:** **Independent accounting-only channel** bridging language-free Aegean metrology to [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]]'s zero-curation open dictionaries.
- **Commands:**
  ```bash
  uv run --no-sync python models/language-id-kernel/fractions_k.py --no-lid
  uv run --no-sync python models/language-id-kernel/fractions_k.py --autopsy-conflicts
  uv run --no-sync python models/language-id-kernel/fractions_k.py --n-perm 5000
  ```

## 2. Method & Statistic

Kernel K separates language-free epigraphic arithmetic from probabilistic language identification into three strictly insulated stages:

1. **Stage K0 (Language-Free Arithmetic & 3D Autopsy Ledger):** Parses raw Aegean Unicode numerals (`U+10107..U+1012A`) and Linear A fraction glyphs (`U+10740..U+10755`) directly from `data/linear-a/corpus.json` using Corazza et al. (2021) Table 4 optimal values (`J=1/2, E=1/4, F=1/8, D=1/6, B=1/5, K=1/10, H=1/16, A=1/24, L2=1/20, L3=1/30, L4=1/40, L6=1/60, X=1/12, W=2/5, JE=3/4, DD=1/3`), compares exact sum balances against the older Bennett/GORILA convention, and emits a machine-readable conflict ledger (`--autopsy-conflicts`) targeting residual epigraphic anomalies for 3D/RTI re-examination.
2. **Stage K1 (Blind Sum-Word Discovery):** Scans all 1,719 Linear A records with zero lexicon, etymology, or linguistic assumptions for any token followed by a numeral ($\ge 4$) equal to the exact contiguous sum of two or more preceding quantities.
3. **Stage K2 (Calibrated Accounting-Register LID):** Strips every cult text, vessel word, grain word, and ligature, evaluating *only* the mathematically discovered accounting triad (`KU-RO`, `PO-TO-KU-RO`, `KI-RO`) against [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]]'s zero-curation open JSONL dictionaries (`cap = 40`, `B = 5,000` consonant-series grid permutations), gated by `SIGNATURE.txt` and calibrated first on Mycenaean Linear B's accounting pair (`TO-SO`, `O-PE-RO`).

## 3. Data Called Upon

- **Primary corpus (Stages K0–K1):** `data/linear-a/corpus.json` (`1,719` records; raw `words` Unicode glyphs and `transliteratedWords` tokens only).
- **Shipped open dictionaries (Stage K2, via `auto_anchors_j.py`):**
  - `semitic`: `data/contact/akkadian_lexicon.jsonl` (CC0 1.0) + `data/contact/hebrew_lexicon.jsonl` (CC BY 4.0 / PD)
  - `greek`: `data/share-alike/greek/lsj_glosses.jsonl` (`101,410` glossed LSJ entries; CC BY-SA 4.0)
  - `sumerian`: `data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl` (`3,589` clean vocalized ePSD2 lemmas; CC0 1.0)
- **Linear B calibration targets:** `TO-SO` (`TOTAL`), `O-PE-RO` (`DEFICIT`).
- **Linear A accounting triad:** `KU-RO` (`TOTAL`), `PO-TO-KU-RO` (`TOTAL`), `KI-RO` (`DEFICIT`).

## 4. Stage K0–K1 Language-Free Output

- **Compound-fraction properness (`55` compound fractions across `1,719` records):** **Corazza et al. (2021) produces `0` strict `> 1` violations** (resolving `HT 27a` `JE+B` = `3/4 + 1/5 = 19/20 < 1`, leaving only two adjacent `J J` = `1` entries on `PH 9b` and `PH 22a`), whereas **Bennett legacy (`B = 1/3`) fails strictly `> 1`** on `HT 27a` (`3/4 + 1/3 = 13/12 > 1`).
- **Blind sum-word discovery (`1,719` records):** **`KU-RO` surfaces at rank #1 with `9` exact single-face suffix sums** (`HT104`, `HT117a`, `HT11b`, `HT127b`, `HT25b`, `HT88`, `HT89`, `HT94b`, `HT9b`—totals `95, 10, 180, 292, 52, 6, 87, 5, 24`), against `<= 1` hit for any other token (including damaged `KU-RO[` on `HT85a`, total `66`). Because all 9 intact single-face sums are integer totals, blind `KU-RO` discovery is invariant across Corazza (`9`) and Bennett legacy (`9`), while Corazza et al.'s fractional values both eliminate the `HT 27a` improper fraction and govern the 5-item epigraphic conflict ledger below.
- **3D/RTI Epigraphic Conflict Ledger (`5` logged targets):**
  1. `HT 123+124a` (`*308` column): `H = A + 1/4` incompatible with Corazza Table 4 (`H = 1/16, A = 1/24`) under current GORILA reading.
  2. `HT 123+124a` (`KI-RO 6` column): `A711 (X)` fails to balance `KI-RO 6` for any `X < 1` under current reading.
  3. `KH 7a` Row 5 & `HT 89`: `A732 (JE = 3/4, 31x across 24 docs)` and `L2 = 1/20` fracture margins (`1.80` ration vs `[ ]18` worker count on `KH 7a`; `CYP 2 JE + NI 2 E = 5.0` on `HT 89`).
  4. `MA 10b`: Early Neopalatial MM IIIB 4-sided bar `*405+OMEGA (A713)` vessel-capacity ligature (`0` intact sum equations; cross-check against Cretan Hieroglyphic klasmatograms).
  5. `A709 (L)` exclusion (`8` corpus tokens across `6` docs): statistically rejected as an independent fraction sign by Corazza et al. (2021 fn. 2); check for damaged `L2`–`L6` strokes at fracture edges.

## 5. Stage K2 Calibration & Linear A Results (`cap = 40`, `B = 5,000`, `seed = 20261124`)

### Linear B Calibration Gate (`TO-SO`, `O-PE-RO`)

| Language | `LL` | `Z_perm` | `p_perm` | Outcome |
| --- | ---: | ---: | ---: | --- |
| **Greek (LSJ)** | **`-7.801`** | **`+2.48`** | **`0.01440`** | **PASS (#1, `ΔLL = +0.280`)** |
| Sumerian (ePSD2) | `-8.081` | `+1.23` | `0.10778` | Rejected |
| Semitic (Akk+Heb) | `-10.233` | `+0.14` | `0.40132` | Rejected |

### Linear A Deduplicated Accounting Pair (`KU-RO`, `KI-RO`—matching Linear B's 2-word pair)

| Language | `LL` | `Z_perm` | `p_perm` | Outcome |
| --- | ---: | ---: | ---: | --- |
| **Semitic (Akk+Heb)** | **`-6.807`** | **`+3.15`** | **`0.01480`** | **PASS (#1, `ΔLL = +1.190` vs Greek, `+1.892` vs Sumerian)** |
| Greek (LSJ) | `-7.996` | `+1.75` | `0.05439` | Rejected |
| Sumerian (ePSD2) | `-8.698` | `+2.29` | `0.03079` | #3 (`ΔLL = -1.892`) |

### Linear A Full Accounting Triad (`KU-RO`, `PO-TO-KU-RO`, `KI-RO`)

| Language | `LL` | `Z_perm` | `p_perm` | Outcome |
| --- | ---: | ---: | ---: | --- |
| **Semitic (Akk+Heb)** | **`-11.239`** | **`+2.86`** | **`0.01280`** | **#1 (`ΔLL = +0.551` vs Greek, `+1.603` vs Sumerian)** |
| Greek (LSJ) | `-11.790` | `+2.80` | `0.00840` | #2 *(shared `K–R` double-counted via `PO-TO-KU-RO`)* |
| Sumerian (ePSD2) | `-12.842` | `+2.75` | `0.01660` | #3 *(shared `K–R` double-counted via `PO-TO-KU-RO`)* |

## 6. What It Proves & Honest Limits

Even when every cult inscription, vessel name, grain word, and commodity ligature is stripped from the test—retaining only accounting words whose mathematical role follows directly from Corazza et al.'s language-independent fraction equations—Linear B calibrates cleanly as **Greek** (`p = 0.01440`, Semitic rejected at `p = 0.40132`) while Linear A's deduplicated accounting pair (`KU-RO`, `KI-RO`, removing the double-counting of `KU-RO` inside `PO-TO-KU-RO`) ranks **Semitic #1** at **`Z = +3.15, p = 0.01480, ΔLL = +1.190`** (~3.29:1 BF) and **rejects LSJ Greek (`p = 0.05439`)**. Including `PO-TO-KU-RO` keeps Semitic #1 (`LL = -11.239, Z = +2.86, p = 0.01280, ΔLL = +0.551`) while inflating Greek (`p = 0.00840`) and Sumerian (`p = 0.01660`) through repeated `K–R`. Because Stage K2 tests only 2–3 accounting words (2 concepts), it serves as a targeted metrology-to-accounting bridge alongside [[models/language-id-kernel/kernels/d-anchors|Kernel D]], [[models/language-id-kernel/kernels/i-morphology|Kernel I]], and [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]].
