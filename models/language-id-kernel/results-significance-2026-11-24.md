---
name: models/language-id-kernel/results-significance-2026-11-24
title: "Significance & Interpretation of Kernels K & L and the Twelve-Kernel Suite (2026-11-24)"
desc: "Timestamped analytical report covering Kernel K (Corazza–Ferrara 2021 fraction verification and blind KU-RO discovery), Kernel L (backward-projection stress-testing and calibrated negative controls), and the twelve-kernel synthesis."
tags: [linear-a, probabilistic-model, analysis, significance, 2026-11-24]
created: 2026-11-24T21:18:00Z
updated: 2026-11-25T15:35:00Z
---

# Significance & Interpretation of Kernels K & L and the Twelve-Kernel Suite (2026-11-24)

[[models/language-id-kernel/_index|..]]

***

**Snapshot:** `kaphtor v1.3.2` (`2026-11-24`), evaluated strictly under agreed Linear B syllabogram values (`--strict-lb-only`), zero LLMs, zero project-lexicon inputs, and fixed PRNG seed (`20261124`). Every figure below is verified verbatim against [`runs/kernels-kl-2026-11-24.json`](runs/kernels-kl-2026-11-24.json) and supplements the ten-kernel baseline in [`results-significance-2026-11-23.md`](results-significance-2026-11-23.md).

---

## 1. What Kernels K & L Add to the Suite

The `2026-11-23` ten-kernel baseline ([`results-significance-2026-11-23.md`](results-significance-2026-11-23.md)) left two concrete methodological objections an epigrapher could still raise:

1. **Metrology-first entry without pre-selecting vessels or grains:** Can the corpus's own arithmetic and fraction equations surface the accounting vocabulary completely blind—and emit an epigraphic conflict ledger for 3D/RTI re-examination—before any dictionary is touched? **Kernel K** tests this directly using Corazza, Ferrara, Montecchi, Tamburini & Valério (2021, *JAS* 125: 105214).
2. **Backward-projection fragility and negative controls:** If 10%–30% of Linear B→Linear A homomorph sign values are wrong (Steele & Meißner 2017; Salgarella 2020), or if contested consonant series (`Q, Z, W, J`) are dropped entirely, does the Semitic signal survive—and where do our methods honestly fail? **Kernel L** stress-tests Kernels D, I, and J across four adversarial stages and formalizes three calibrated negative controls.

---

## 2. Kernel K — Corazza–Ferrara (2021) Fractions & Blind Accounting (`fractions_k.py`)

### Results (`runs/kernels-kl-2026-11-24.json` → `kernel_k`)

- **Stage K0–K1 (100% language-free, `1,719` records):**
  - **Compound-fraction properness (`55` compound fractions):** **Corazza et al. (2021) produces `0` strict `> 1` violations** (resolving `HT 27a` `JE+B` = `3/4 + 1/5 = 19/20 < 1`), whereas **Bennett legacy (`B = 1/3`) fails strictly `> 1`** on `HT 27a` (`13/12 > 1`).
  - **Blind sum-word discovery:** **`KU-RO` surfaces at rank #1 with `9` exact single-face suffix sums** (`HT104`, `HT117a`, `HT11b`, `HT127b`, `HT25b`, `HT88`, `HT89`, `HT94b`, `HT9b`—totals `95, 10, 180, 292, 52, 6, 87, 5, 24`) against `<= 1` hit for any other token (including damaged `KU-RO[` on `HT85a`, total `66`), invariant across Corazza (`9`) and Bennett (`9`) because all 9 intact sums are integer totals, alongside the 5-item epigraphic conflict ledger (`HT 123+124a` `*308`-column `H = A + 1/4`, `HT 123+124a` `KI-RO 6` `X`, `KH 7a` Row 5 / `HT 89` `A732 = 3/4` & `L2 = 1/20`, `MA 10b` `*405+OMEGA`, and `A709/L` statistical exclusion).
- **Stage K2 (accounting-only open-dictionary LID, `cap = 40`, `B = 5,000`):**
  - **Linear B calibration (`TO-SO`, `O-PE-RO`):** **Greek wins cleanly** (`LL = -7.801, Z = +2.48, p = 0.01440, ΔLL = +0.280`); Sumerian (`-8.081, Z = +1.23, p = 0.10778`) and Semitic (`-10.233, Z = +0.14, p = 0.40132`) are rejected.
  - **Linear A deduplicated accounting pair (`KU-RO`, `KI-RO`—matching Linear B's 2-word pair):** **Semitic wins cleanly** (`LL = -6.807, Z = +3.15, p = 0.01480, ΔLL = +1.190`, ~3.29:1 BF), **rejecting LSJ Greek (`-7.996, Z = +1.75, p = 0.05439`)** and outscoring ePSD2 Sumerian (`-8.698, ΔLL = +1.892`). *(Under the extended 6-language ANE contact panel with Ugaritic, Anatolian, Hurrian, and Egyptian, Semitic hits `Z = +3.13, p = 0.00720`, rejecting Greek `0.054`, Hurrian `0.089`, and Egyptian `0.168`.)*
  - **Linear A full accounting triad (`KU-RO`, `PO-TO-KU-RO`, `KI-RO`):** **Semitic stays #1** (`LL = -11.239, Z = +2.86, p = 0.01280, ΔLL = +0.551` vs Greek `-11.790` and `+1.603` vs Sumerian `-12.842`), while double-counting `KU-RO` inside `PO-TO-KU-RO` inflates Greek (`p = 0.00840`) and Sumerian (`p = 0.01660`) via shared `K–R`.

### What It Establishes & Honest Boundary

Even when every cult inscription, vessel word, grain word, and commodity ligature is stripped away, Linear B calibrates as Greek while Linear A's deduplicated accounting pair (`KU-RO`, `KI-RO`) selects **Semitic** (`Z = +3.15, p = 0.01480, ΔLL = +1.190`) and rejects LSJ Greek (`p = 0.05439`). Because Stage K2 tests only 2–3 words (2 concepts, `n_concept_perms = 2–3`), it functions as a targeted metrology-to-accounting bridge and 3D/RTI autopsy generator alongside Kernels D, I, and J.

---

## 3. Kernel L — Backward-Projection Stress-Testing & Negative Controls (`homomorph_l.py`)

### Results (`runs/kernels-kl-2026-11-24.json` → `kernel_l`)

1. **Stage L1 (Contested-Series Drops, Full 12-Series Ablation & SigLA Word-Division Invariance on Kernel I, `B = 500`):**
   - `full_strict_lb` (`728` tokens / `505` types): Semitic `M = +40.034, Z_M = +2.474, p_M = 0.00200`.
   - **`sigla_word_division_invariance` (`data/linear-a/sigla_db.json`, Salgarella & Castellan 2021, `686` words / `495` types):** **Semitic is the sole passing language** (`M = +35.115, Z_M = +2.661, p_M = 0.00200, p_cv = 0.00200`; all 6 rivals `p_M = 0.172–1.000`), refuting GORILA word-division artifact critiques.
   - `drop_Q_Z` (`664 / 453`): dropping contested labiovelars and `Z`-series **strengthens** Semitic (`M = +44.329, Z_M = +2.474, p_M = 0.00200`).
   - `drop_Q_Z_W_J` (`550 / 357`): dropping all four contested series still passes cleanly (`M = +27.586, Z_M = +2.055, p_M = 0.00798`).
   - **`all_12_single_series_drops`:** **`10 / 12` consonant series pass both `p_M <= 0.05` and `p_cv <= 0.05`** (`D, J, K, M, N, P, Q, S, W, Z`). **`drop T`** (`513 / 324`) produces the **#1 deepest collapse across all 12 series** (`M = +3.902, Z_M = +0.636, p_M = 0.26547, p_cv = 0.09381`—Semitic `t-`/`-t` bound affixes); `drop R` (`508 / 320`) is #2 marginal (`p_M = 0.07385`, largest vocab drop + merged `/r, l/`); `drop M` weakens margin (`+40.03 → +13.49`, mimation `*-m`/`ma-`) while still passing (`p_M = 0.03792`).
   - `aegean_cypriot_core_11`: Steele & Meißner's (2017) 11-sign core (`a, i, da, na, pa, po, ro, sa, se, ti, to`) yields `30` tokens (`< 20` types)—honestly logged as below the statistical power floor.
2. **Stage L2 (Leave-One-Consonant-Series-Out Jackknife, `B = 1,000`):**
   - **Kernel D L1SO:** **`8 / 8` pass** (`winner = semitic`, `p_perm = 0.001` across all 8 drops; `drop K` leaves `n = 3` anchors, `Z = +3.983`).
   - **Kernel J L1SO:** **`7 / 7` pass on consonant-grid `p_perm <= 0.05`** (`0.001–0.03696`). Under the stricter dual-null `p_concept <= 0.05`, **`2 / 7` pass** (`D` and `T`, both `p_concept = 0.01111`; `N, P, R, S` relax to `0.067–0.289`), and dropping `K` removes 7 of 8 Kernel J anchors, leaving `n = 1` (`SU-PU`, `p_concept = null`—complemented by Kernel D `drop K` `p = 0.001` and Kernel I `drop K` `M = +47.30, p_M = 0.00399`).
3. **Stage L3 (Steele–Meißner Random Consonant-Series Corruption on Kernels D & I, vowels intact):**
   - **Kernel D (`300` trials/`ε`, plus `p_perm <= 0.05` survival over `100` trials × `200` inner perms):** Linear B (Greek) rank-1 `100.0%` (`ε = 0.1–0.4`), `99.67%` (`ε = 0.5`); Linear A (Semitic) **`100.0%`** rank-1 / **`99%` `p_perm <= 0.05`** (`ε = 0.1`), **`99.67%`** rank-1 / **`90%` `p_perm <= 0.05`** (`ε = 0.2`, `mean ΔLL = +9.673`), **`95.67%`** rank-1 / **`80%` `p_perm <= 0.05`** (`ε = 0.3`, `+7.767`), `92.67%` (`ε = 0.4`), `82.67%` (`ε = 0.5`).
   - **Kernel I lexicon-free morphology (`100` trials/`ε`):** Semitic rank-1 win rate **`94%`** (`mean M = +30.78`) at `ε = 0.1`, **`86%`** (`+26.35`) at `ε = 0.2`, and **`70%`** (`+18.49`) at `ε = 0.3`—completely without dictionaries.
4. **Stage L4 (Calibrated Negative Controls & Code-Separation Boundaries):**
   - **Kernels A & B macro-typology (`logged_prior_run`):** `/a, i, u/` vowel frequency (`~81%`) yields `Z_perm < 0`—non-diagnostic alone.
   - **Cretan Hieroglyphic→Linear A pictographic acrophony (`logged_prior_run`):** `3/20` matches (`p ≈ 0.31`, null), aligning with Valério & Ferrara (2020) and Ottaviano et al. (2026) against naive phonocentric derivation.
   - **Single-sign open-dictionary ligature saturation (`computed_live`, `B = 500`):** Linear B **fails its own Greek calibration gate** (`Z = +0.503, p = 0.39521`), proving a ~60-sign syllabary saturates under single-sign open-dictionary matching and keeping Kernel F strictly auxiliary.

---

## 4. Updated Twelve-Kernel Synthesis (`2026-11-24`)

Across all twelve kernels (`A–L`), **10 of 11 scoring kernels rank Semitic #1** (Kernel H ranks shared Cretan Linear B #1 and LBA Levantine Semitic #2), every calibrated instrument selects Greek and rejects Semitic on real Mycenaean Linear B tablets, and **Kernel L confirms that the core lexical and morphological results do not depend on assuming 100% fidelity of Linear B→Linear A homomorph sign values**. At the same time, Kernels K and L sharpen the suite's honest boundaries: the accounting-only triad (`n = 3`) carries a modest Bayes factor (`ΔLL = +0.551`), Kernel J's original `FULL_8` concept-shuffle null relies on multiple active consonant series (`2/7` under L1SO), the 11-sign Aegean–Cypriot core is too sparse (`30` tokens) for morphological testing, and single-sign open-dictionary ligatures saturate the syllabary.

---

## 5. Addendum (`2026-11-25`): Kernel J Deduplicated & Expanded Pre-Linguistic Tiers

To close both the `PO-TO-KU-RO` double-counting caveat and the Kernel L `drop K` (`n = 1`) gap without introducing lexicon circularity, `auto_anchors_j.py` was extended (`runs/auto-anchors-j-standalone-2026-11-25.json`, `B = 10,000`, `seed = 20261125`) while keeping signed `FULL_8` intact:

- **Expanded Linear B calibration (`LB_ANCHORS_EXT9`, `+ DI-PA, WO-NO, E-RA-WO`):** Greek strengthens to **`ΔLL = +6.177` (~481 : 1), `Z_perm = +4.95, p_perm = 0.00010`, `p_concept = 0.00020`** (`10,000` concept shuffles); Semitic (`0.115 / 0.293`) and Sumerian (`0.148 / 0.104`) are rejected.
- **`LA_DEDUP_7` (drops `PO-TO-KU-RO` so `KU-RO` is never double-counted):** Semitic sharpens to **`ΔLL = +4.342` (`76.9 : 1`), `p_perm = 0.00010`, exact `p_concept = 0.01111`** (`1,260` perms; Greek `0.731`, Sumerian `0.578`).
- **`LA_DEDUP_9` (Tier 1a — purest 100% strict `signs-a5-proposed.json` inventory):** adds `PA-TA-QE` (`HT 31 *402-VS`) and **untranslated `DA-RO-PA` (`HT 38 *403-VS`, included blind and absent from `lexicon.json`)**—excluding `PA₃` doublet folding, `PA-RA` header inference, and the `MA+RU` monogram. Semitic wins cleanly at **`ΔLL = +3.863` (`47.6 : 1`), `Z_perm = +3.89, p_perm = 0.00010`, `Z_concept = +2.42, p_concept = 0.00390`** (`10,000` shuffles; Greek `0.626`, Sumerian `0.663`).
- **`LA_DEDUP_12` (Tier 2a — sensitivity tier folding GORILA doublet `AB 56` / `PA₃ → PA`, kept opaque in `signs-a5-proposed.json` §15 ruling 3):** adds `HT 31`'s three literal `PA₃` vessel drawings (`QA-PA₃, KA-RO-PA₃, SU-PA₃-RA`) to `LA_DEDUP_9`, sharpening Semitic to **`ΔLL = +4.200` (`66.7 : 1`), `Z_perm = +3.73, p_perm = 0.00010`, `Z_concept = +2.73, p_concept = 0.00180`** (Greek `0.633`, Sumerian `0.856`).
- **Extended sensitivity tiers (`LA_DEDUP_11`, `LA_DEDUP_14`, and `LA_DROPK_5`):** adding `PA-RA` (`HT 128a` tablet heading above `GRA` entries, header inference rather than direct ligature) and the `MA+RU` (`A558`/`LANA`) wool monogram (distinct from the `HT 117a` syllabic personal name `MA-RU`) yields `LA_DEDUP_11` (`ΔLL = +4.285`, `72.6 : 1`, `p_perm = 0.00010`, `p_concept = 0.01560`; Greek `0.791`, Sumerian `0.620`) and `LA_DEDUP_14` (`+ PA₃` fold: `ΔLL = +4.623`, `101.8 : 1`, `p_perm = 0.00020`, `p_concept = 0.00920`; Greek `0.794`, Sumerian `0.834`). The strictly `K`-free subset **`LA_DROPK_5`** (`SU-PU, PA-TA-QE, DA-RO-PA, PA-RA, MA+RU`) passes consonant-grid permutation (`ΔLL = +1.233, Z_perm = +2.19, p_perm = 0.01640`) while underpowered on concept-shuffle (`p_concept = 0.21667`, `60` exact perms).
- **Orthogonal 2-channel synthesis (Kernel J `p_concept` + zero-dictionary Kernel I `p_M = 0.00360`):**
  - **`LA_DEDUP_9` (purest strict-LB) + Kernel I:** Fisher combined null **`p = 0.00017`** (`~1 in 5,850`); pure Sellke–Bayarri–Berger upper bound $\text{SBB}_{\max}(p_{\text{comb}}) = (-e\,p\ln p)^{-1} = \mathbf{248 : 1}$ (1% prior → **71.5%**, 5% → **92.9%**, 10% → **96.5%**; hybrid $e^{\Delta\text{LL}_J}\times\text{SBB}_{\max}(p_{M,I}) = 864 : 1$).
  - **`LA_DEDUP_12` (`+ PA₃` fold) + Kernel I:** Fisher combined null **`p = 0.000084`** (`~1 in 11,920`); pure $\text{SBB}_{\max}(p_{\text{comb}}) = \mathbf{467 : 1}$ (1% prior → **82.5%**, 5% → **96.1%**, 10% → **98.1%**; hybrid $1{,}211 : 1$).
  - *(Baseline `FULL_8` + Kernel I: Fisher `p = 0.00094`, pure $\text{SBB}_{\max} = 56.4 : 1$.)*
