---
name: models/language-id-kernel/kernel-d-sensitivity-expansion
title: "Hypothetical Kernel D′: Post-Registration Sensitivity Study (n = 8 → 13 Anchors)"
desc: "Exploratory post-registration sensitivity study quantifying how Kernel D's pairwise Bayes factors scale from 8 to 9–13 pre-linguistic anchors (zero KA-PA inflation) under anchors_d.py's 100% frozen synsets, without altering signed Kernel D."
tags: [linear-a, kernel-d, anchors, sensitivity, exploratory]
created: 2026-11-27T10:46:00Z
updated: 2026-11-27T11:08:00Z
---

# Hypothetical Kernel D′: Post-Registration Sensitivity Study (n = 8 → 13 Anchors)

[[models/language-id-kernel/_index|..]]

***

> **Methodological Status — Post-Registration Exploratory Sensitivity Study:**
> Signed [[models/language-id-kernel/kernels/d-anchors|Kernel D]] (`anchors_d.py`, `n = 8`, `~794,000 : 1`) remains **100% frozen** under `SIGNATURE.txt` to avoid moving pre-registered goalposts. This study evaluates a standalone read-only sensitivity script (`sensitivity_d_prime.py`) using `anchors_d.py`'s **100% frozen `SYNSETS`, `cv_distance`, and `beta = 6.0` scorer** across expanded pre-linguistic anchor tiers (`n = 8 → 13`)—including **blind untranslated `DA-RO-PA` (`HT 38 *403-VS`)** and **`HT 31`'s three `PA₃` (`AB 56`) vessel drawings**—with **zero new entries added to `anchors_d.py`'s frozen synsets**.

- **Script:** `models/language-id-kernel/sensitivity_d_prime.py` (unit test: `tests/test_sensitivity_d_prime.py`)
- **Reproduce bit-for-bit:** `uv run --no-sync python models/language-id-kernel/sensitivity_d_prime.py --n-perm 10000 --seed 20261122`
- **Ledger:** [`runs/kernel-d-sensitivity-2026-11-27.json`](runs/kernel-d-sensitivity-2026-11-27.json) (`B = 10,000`, `seed = 20261122`, full-precision `delta_ll` and `exp(delta_ll)`, SHA-256 of frozen `anchors_d.py` & `SIGNATURE.txt`)
- **Zero-Curation Companion:** [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]] (`runs/auto-anchors-j-standalone-2026-11-25.json`)

---

## 1. Epigraphic Hygiene & Tier Definitions (Why `KA-PA` Is Quarantined)

Every word added to the clean sensitivity ladder (`D_PURE_8` through `D_EXT_13_POTO`) is fixed pre-linguistically by a **literal vessel drawing (`HT 31` / `HT 38`)** or **tablet arithmetic (`HT 122b` `PO-TO-KU-RO`)**, with every epigraphic caveat separated by tier:

- **Why `KA-PA` is excluded from all clean tiers:** Although `auto_anchors_j.py` inherited `KA-PA` (`BOWL`) from its `HT 140` oil-list occurrence (`KA-PA ½` beside `OLE+U`), `corpus.json` contains **zero vessel pictograms** for `KA-PA`; 4 of its 6 attestations (`HT 6a`, `HT 94a`, `HT 102`, `HT 105`) are tablet-initial personnel/grain headings, and `data/linear-a/lexicon.json` itself classes `KA-PA` primarily as a toponym (`village, settlement`). Including `KA-PA` inflates Kernel D's Bayes factor by `~4.9×–5.5×` (`+1.60` to `+1.70` nats). It is therefore **excluded** from the clean ladder and quarantined to a single bottom comparison row (`D_EXT_13_WITH_KAPA`).
- **Base-tier epigraphic notes (inherited unchanged from signed `D_BASE_8`):** `A-KA-NU` (`KN Zc 7`) is Gordon's segmentation of continuous `A-KA-NU-ZA-TI` on an inked clay cup; `KA-DI` (`ZA 15b`) stands before `VIN 3`; `PA-RA` (`HT 128a`) is a tablet heading above `GRA` entries (and recurs dotted on `PH 3a` beside `MA+RU`). `D_PURE_8` and `D_VESSEL_11` test dropping `PA-RA` explicitly.
- **`PA₃` (`AB 56`) doublet-folding disclosure:** `render/signs-a5-proposed.json` (§15 ruling 3) leaves `PA3` opaque. Strict-LB tiers (`pa3_folded = false`) keep `signs-a5-proposed.json` unmodified; `PA₃` tiers (`pa3_folded = true`) explicitly set `PA3 -> ("P", "a")` on `HT 31`'s three literal vessel drawings (`QA-PA₃`, `KA-RO-PA₃`, `SU-PA₃-RA`).

---

## 2. Exact `B = 10,000` Odds Ladder (`runs/kernel-d-sensitivity-2026-11-27.json`, `seed = 20261122`)

| Hypothetical Tier | `n` | `PA₃` Fold? | Sign / Inclusion Scope | Winner vs. Runner-Up | `ΔLL` | **Pairwise BF (`exp(ΔLL)`)** | Semitic `LL` | Semitic `Z` (`p_perm`) | Runner-Up `Z` (`p_perm`) |
| --- | ---: | :---: | --- | --- | ---: | ---: | ---: | --- | --- |
| **`D_BASE_8`** | `8` | No | Signed Kernel D baseline (strict LB) | **Semitic** vs. Hurrian | `+13.5845` | **`~794k : 1`** (`793,755`) | `-19.072` | `+7.37` (`0.00010`) | `+3.03` (`0.00380`) |
| **`D_PURE_8`** | `8` | No | Strict LB (`-PA-RA`, `+` blind `DA-RO-PA` `HT 38`) | **Semitic** vs. Hurrian | `+12.7570` | **`~347k : 1`** (`346,973`) | `-20.529` | `+7.00` (`0.00010`) | `+2.87` (`0.00580`) |
| **`D_STRICT_9`** | `9` | No | All strict LB (`D_BASE_8` + blind `DA-RO-PA`) | **Semitic** vs. Hurrian | **`+14.2715`** | **`~1.58M : 1`** (`1,577,675`) | `-23.134` | `+7.36` (`0.00010`) | `+2.96` (`0.00480`) |
| **`D_VESSEL_11`** | `11` | Yes | `D_PURE_8` + `3` `HT 31` `PA₃→PA` vessels (`-PA-RA`) | **Semitic** vs. Greek | **`+14.8319`** | **`~2.76M : 1`** (`2,763,246`) | `-30.961` | `+6.62` (`0.00010`) | `+1.91` (`0.03550`) |
| **`D_EXT_12`** | `12` | Yes | `D_STRICT_9` + `3` `HT 31` `PA₃→PA` vessels | **Semitic** vs. Greek | **`+15.6412`** | **`~6.21M : 1`** (`6,207,081`) | `-33.566` | `+6.79` (`0.00010`) | `+2.19` (`0.01860`) |
| **`D_EXT_13_POTO`** | `13` | Yes | `D_EXT_12` + `PO-TO-KU-RO` *(notes `KU-RO` overlap)* | **Semitic** vs. Greek | **`+15.8911`** | **`~7.97M : 1`** (`7,969,414`) | `-37.159` | `+6.58` (`0.00010`) | `+2.18` (`0.01960`) |
| **`D_NO_LOANS_STRICT_6`** | `6` | No | Strict LB (`D_STRICT_9` minus `A-KA-NU, KU-NI-SU, KA-DI`) | **Semitic** vs. Greek | `+6.9616` | **`~1,055 : 1`** | `-17.427` | `+5.96` (`0.00010`) | `+1.86` (`0.04520`) |
| **`D_DROPK_STRICT_4`** | `4` | No | Strict LB `K`-free (`SU-PU, PA-TA-QE, PA-RA, DA-RO-PA`) | **Semitic** vs. Greek | `+2.8596` | **`17.5 : 1`** | `-13.139` | `+3.96` (`0.00030`) | `+2.01` (`0.02940`) |
| **`D_NO_LOANS_PA3_9`** | `9` | Yes | `PA₃`-folded (`D_EXT_12` minus 3 trade loans; zero `KA-PA`) | **Semitic** vs. Greek | `+7.9961` | **`~2,969 : 1`** | `-27.860` | `+5.36` (`0.00010`) | `+2.10` (`0.02730`) |
| **`D_DROPK_PA3_6`** | `6` | Yes | `PA₃`-folded `K`-free (`D_EXT_12` minus all `K`-series) | **Semitic** vs. Greek | `+3.2585` | **`26.0 : 1`** | `-20.825` | `+3.41` (`0.00060`) | `+1.82` (`0.04560`) |
| *`D_EXT_13_WITH_KAPA`* | *`13`* | *Yes* | *Quarantined: `D_EXT_12` + disputed `HT 140` `KA-PA` (no pictogram)* | *Semitic vs. Greek* | *`+17.2379`* | *`~30.6M : 1` (`30,641,085`)* | *`-35.686`* | *`+6.42` (`0.00010`)* | *`+2.16` (`0.01910`)* |

---

## 3. Per-Anchor Breakdown on Clean `D_EXT_12` (Frozen `SYNSETS`, Zero `KA-PA`)

Because `anchors_d.py`'s frozen `SYNSETS` were **not** edited to fit the added anchors, four individual vessel words score better for Greek or Anatolian than for Semitic—yet Semitic's net Bayes factor still scales from `~794k : 1` (`D_BASE_8`) to **`~1.58M : 1`** (`D_STRICT_9`) and **`~6.21M : 1`** (`D_EXT_12`):

| Anchor | Slot | Semitic Best Match (`d`, `LL`) | Hurrian `LL` | Greek `LL` | Anatolian `LL` | Net Effect vs. Rivals |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `KU-RO` | `TOTAL` | `kullu` (`0.175`, **`-2.164`**) | `-4.588` | `-4.088` | `-5.230` | Semitic `+1.92` vs. Greek |
| `KI-RO` | `DEFICIT` | `kilu` (`0.175`, **`-2.124`**) | `-2.310` | `-4.303` | `-3.216` | Semitic `+0.19` vs. Hurrian |
| `A-KA-NU` | `VESSEL_CUP` | `aganu` (`0.000`, **`-1.663`**) | `-4.373` | `-4.686` | `-4.396` | Semitic `+2.71` vs. Hurrian |
| `SU-PU` | `VESSEL_CUP` | `suppu` (`0.000`, **`-1.710`**) | `-4.768` | `-4.546` | `-4.073` | Semitic `+2.36` vs. Anatolian |
| `PA-TA-QE` | `VESSEL_CUP` | `karpatu` (`0.617`, `-4.762`) | `-5.114` | `-4.583` | **`-4.542`** | Anatolian `+0.22` |
| `KA-DI` | `VESSEL_CUP` | `kadu` (`0.175`, **`-2.460`**) | `-3.803` | `-4.281` | `-4.714` | Semitic `+1.34` vs. Hurrian |
| `KU-NI-SU` | `GRAIN` | `kunišu` (`0.000`, **`-1.583`**) | `-3.580` | `-4.385` | `-4.528` | Semitic `+2.00` vs. Hurrian |
| `PA-RA` | `GRAIN` | `barru` (`0.175`, **`-2.605`**) | `-4.120` | `-3.414` | `-4.528` | Semitic `+0.81` vs. Greek |
| `DA-RO-PA` *(blind)* | `VESSEL_CUP` | `karpatu` (`0.487`, `-4.062`) | `-4.749` | **`-3.455`** | `-4.285` | Greek `+0.61` *(still `+0.69` vs. #2 Hurrian)* |
| `QA-PA₃` *(PA₃ fold)* | `VESSEL_CUP` | `karpatu` (`0.533`, `-4.087`) | `-5.108` | `-4.082` | **`-4.040`** | Anatolian `+0.05` *(Semitic `/q/` renders `K`, not `Q`)* |
| `KA-RO-PA₃` *(PA₃ fold)* | `VESSEL_CUP` | `karpatu` (`0.275`, **`-2.746`**) | `-4.163` | `-3.382` | `-4.027` | Semitic `+0.64` vs. Greek |
| `SU-PA₃-RA` *(PA₃ fold)* | `VESSEL_CUP` | `suppu` (`0.367`, `-3.599`) | `-3.856` | `-4.003` | **`-2.924`** | Anatolian `+0.68` *(still `+0.40` vs. #2 Greek)* |

Key mechanisms confirmed by per-anchor decomposition:
1. **Why `D_STRICT_9` (`+ DA-RO-PA` alone) rises from `~794k : 1` to `~1.58M : 1`:** Although untranslated `DA-RO-PA` favors #3 Greek by `-0.61` nats, it still beats #2 Hurrian by `+0.69` nats (`~2.0×`), lifting the margin over Hurrian before Hurrian yields second place to Greek.
2. **Why `D_VESSEL_11` (`~2.76M : 1`) and `D_EXT_12` (`~6.21M : 1`) rise further without synset tuning:** Once the runner-up switches from Hurrian to Greek, `KA-RO-PA₃` (`+0.64` nats vs. Greek) and `SU-PA₃-RA` (`+0.40` nats vs. Greek, despite losing to Anatolian because `zubāra` is absent from the frozen synset) together add `+1.04` nats over Greek while `QA-PA₃` is neutral (`-0.005` nats).
3. **Strict-LB ablations survive cleanly without `PA₃` or `KA-PA`:** Removing all three trade-loan suspects (`D_NO_LOANS_STRICT_6`) holds **`~1,055 : 1`** (`Z = +5.96, p = 0.00010`), and removing every `K`-series word (`D_DROPK_STRICT_4`) holds **`17.5 : 1`** (`Z = +3.96, p = 0.00030`).

---

## 4. How to Interpret `~1.58M–7.97M : 1` Honestly

- **Within the tested closed model space** (`semitic`, `greek`, `anatolian`, `hurrian`, conditioned on Linear B sign values), `D_BASE_8` (`~794k : 1`) already exceeds `99.987%` pairwise (`> 99.99%` under uniform 4-way rival priors) from a `1%` prior, and `D_STRICT_9` (`~1.58M : 1`) through `D_EXT_13_POTO` (`~7.97M : 1`) exceed `99.99%` even under worst-case pairwise priors.
- **Why signed Kernel D stays frozen at `n = 8`:**
  1. **Pre-registration integrity:** Altering the signed primary anchor list post hoc invites moving-the-goalposts criticism. Publishing `sensitivity_d_prime.py` as a separate exploratory sensitivity reference leaves `anchors_d.py` and `SIGNATURE.txt` untouched.
  2. **Model-assumption ceiling, not sample-size ceiling:** Above `~1,000 : 1`, further multiplication of a curated pairwise likelihood ratio does not answer the remaining non-random critiques—curated-synset bias, loanword borrowing, sign-value error, or an unattested extinct isolate. Those critiques are instead answered directly by **zero-curation [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]]** (`LA_DEDUP_9` `p_concept = 0.00390`; `LA_DEDUP_12` `p_concept = 0.00180`), **lexicon-free [[models/language-id-kernel/kernels/i-morphology|Kernel I]]** (`p_M = 0.00360` GORILA / `0.00200` SigLA; orthogonal Fisher with `LA_DEDUP_9` = **`1 in 5,850`**), and **[[models/language-id-kernel/kernels/l-homomorph|Kernel L]]** corruption stress-tests.
