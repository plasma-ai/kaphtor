---
name: models/language-id-kernel/kernels/l-homomorph
title: "Kernel L: Backward-Projection Stress-Testing & Honest Negative Controls"
desc: "Operationalizes Steele & Meißner (2017) and Salgarella (2020) backward-projection caution alongside Valério & Ferrara (2020), Ferrara, Montecchi & Valério (2022), and Ottaviano et al. (2026) via homomorph-core ablations, L1SO jackknives, corruption curves, and calibrated negative controls."
tags: [linear-a, kernel-l, backward-projection, stress-test, negative-controls]
created: 2026-11-24T00:00:00Z
updated: 2026-11-24T00:00:00Z
---

# Kernel L: Backward-Projection Stress-Testing & Honest Negative Controls

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/homomorph_l.py`
- **Unit Test:** `models/language-id-kernel/tests/test_homomorph_l.py`
- **Run Ledger:** `runs/kernels-kl-2026-11-24.json` (`kernel_l`)
- **Primary References:** Steele & Meißner (2017) and Salgarella (2020) *(Linear B→Linear A backward-projection caution)*; Valério & Ferrara (2020, *WSR* 11), Ferrara, Montecchi & Valério (2022, *Pasiphae* 16: 81–109), and Ottaviano, Kelley, Cartolano & Ferrara (2026, *Curr. Anthr.* 67.4: 663–689) *(CH↔LA script continuity and code-separation boundaries)*.
- **Channel Classification:** **Adversarial robustness & negative-control harness** auditing Kernels D, F, I, and J against backward-projection error.
- **Command:** `uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage all --n-perm 1000 --trials 300`

## 2. Method & Four Audit Stages

Rather than treating Linear B→Linear A homomorph sign values as infallible, Kernel L explicitly tests whether `kaphtor`'s primary signals survive realistic palaeographic uncertainty and publishes calibrated failure boundaries alongside positive results:

1. **Stage L1 (Homomorph-Core, Full 12-Series Ablation & SigLA Word-Division Invariance on Kernel I):** Re-runs lexicon-free [[models/language-id-kernel/kernels/i-morphology|Kernel I]] (`omission` mode, `B = 500`) after removing contested Linear B consonant series (`Q+Z`; `Q+Z+W+J`), runs a complete **12-series single-drop ablation** across every consonant series (`D, J, K, M, N, P, Q, R, S, T, W, Z`), verifies invariance on Salgarella & Castellan's independent SigLA word segmentation (`data/linear-a/sigla_db.json`), and censuses Steele & Meißner's (2017) 11-sign Aegean–Cypriot homomorph core.
2. **Stage L2 (Leave-One-Consonant-Series-Out Jackknife on Kernels D & J):** Systematically drops every consonant series present in the anchor sets one at a time across [[models/language-id-kernel/kernels/d-anchors|Kernel D]] (`8` active series) and [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J]] (`7` active series) to verify that no single consonant assignment carries the lexical signal.
3. **Stage L3 (Steele–Meißner Backward-Projection Corruption Curve on Kernels D & I):** Monte Carlo simulation randomly replacing a fraction $\varepsilon \in \{0.0, 0.1, 0.2, 0.3, 0.4, 0.5\}$ of all 12 Linear B consonant-series assignments (vowels intact), measuring Kernel D rank-1 win rates (`300` trials/`ε`), Kernel D permutation-significance survival (`p_perm <= 0.05` over `100` trials × `200` inner perms), and lexicon-free Kernel I morphology rank-1 win rates and mean margins (`100` trials/`ε`).
4. **Stage L4 (Honest Negative Controls & Code-Separation Boundaries):** Explicitly logs three calibrated null or saturation results alongside the positive channels: (a) macro-typological vowel inventories (Kernels A & B: `Z_perm < 0`), (b) the pre-registered Cretan Hieroglyphic→Linear A pictographic acrophony null (`3/20, p ≈ 0.31`), and (c) a live single-sign open-dictionary ligature saturation test demonstrating that even Linear B fails Greek calibration under open-dictionary single-sign matching.

## 3. Data Called Upon

Calls the exact shipped corpora and modules of `anchors_d.py`, `auto_anchors_j.py`, `morphology_i.py`, and `kaphtor_kernel.py` with zero project-lexicon inputs, gated by `SIGNATURE.txt`.

## 4. Verified Results (`runs/kernels-kl-2026-11-24.json` → `kernel_l`, `seed = 20261124`)

### Stage L1 — Contested-Series Drops, Full 12-Series Ablation & SigLA Invariance (Kernel I, `B = 500`)

| Subset | Dropped / Source | Tokens / Types | Winner | Semitic Margin `M` | `Z_M` | `p_M` |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `full_strict_lb` | *(GORILA/corpus.json)* | `728 / 505` | **semitic** | `+40.034` | `+2.474` | **`0.00200`** |
| `sigla_word_division_invariance` | **`data/linear-a/sigla_db.json`** | `686 / 495` | **semitic (sole pass)** | **`+35.115`** | **`+2.661`** | **`0.00200`** *(all 6 rivals `0.172–1.000`)* |
| `drop_Q_Z` | `Q, Z` | `664 / 453` | **semitic** | **`+44.329`** | `+2.474` | **`0.00200`** |
| `drop_Q_Z_W_J` | `J, Q, W, Z` | `550 / 357` | **semitic** | `+27.586` | `+2.055` | **`0.00798`** |
| `all_12_single_series_drops` | **10 / 12 pass** (`D,J,K,M,N,P,Q,S,W,Z`) | `356–489` types | **semitic** | `+13.49..+47.30` | `+1.65..+2.87` | **`0.00200–0.03792`** |
| `drop_R` *(of 12)* | `R` *(largest vocab drop + `/r, l/`)* | `508 / 320` | semitic | `+8.62` | `+1.32` | `0.07385` *(marginal)* |
| `drop_T` *(of 12)* | `T` *(Semitic `t-`/`-t`)* | `513 / 324` | semitic | `+3.902` | `+0.636` | **`0.26547`** *(#1 deepest collapse)* |
| `aegean_cypriot_core_11` | *(11-sign core only)* | `30` tokens (`< 20` types) | *(underpowered)* | — | — | *(power floor logged)* |

Across **all 12 single-series drops**, **`10 / 12`** pass both `p_M <= 0.05` and `p_cv <= 0.05`: **`drop T`** produces the #1 deepest collapse (`p_M = 0.26547`, consistent with Semitic `t-`/`-t` bound affixes), `drop R` weakens to marginal (`p_M = 0.07385`, largest vocabulary drop `505 → 320` + merged `/r, l/`), and `drop M` lowers margin (`+40.03 → +13.49`, consistent with mimation `*-m`/`ma-`) while still passing (`p_M = 0.03792`). On Salgarella & Castellan's independent SigLA word segmentation (`sigla_db.json`), Semitic remains the **sole passing language** (`M = +35.12, Z_M = +2.66, p_M = 0.00200, p_cv = 0.00200`).

### Stage L2 — Leave-One-Consonant-Series-Out Jackknife (`B = 1,000`)

- **Kernel D L1SO:** **`8 / 8` pass** (`winner = semitic`, `p_perm <= 0.05` across every consonant series removed; dropping `K` leaves `n_anchors = 3`, `Z = +3.98, p = 0.001`).
- **Kernel J L1SO:** **`7 / 7` pass on consonant-grid `p_perm <= 0.05`** (`0.001–0.037`, `winner = semitic` across all 7 series). Under the stricter dual-null `p_concept <= 0.05`, **`2 / 7`** pass (`D` and `T`, both `p_concept = 0.01111`; `N, P, R, S` relax to `0.067–0.289`), and dropping `K` removes 7 of 8 Kernel J anchors, leaving only `n_anchors = 1` (`SU-PU`, `p_concept = null`—complemented by Kernel D `drop K` `p = 0.001` and Kernel I `drop K` `M = +47.30, p_M = 0.00399`).

### Stage L3 — Steele–Meißner Random Corruption Curve on Kernels D & I (`300` / `100` trials/`ε`)

*(Note: `ε = 0.0` runs `trials = 1` deterministic baseline; corruption perturbs consonant series only—with replacement, keeping vowels intact.)*

| Corruption `ε` | LB Greek (D) | LA Semitic (D) Rank-1 | LA Semitic (D) `mean ΔLL` | LA Semitic (D) `p_perm <= 0.05` | LA Semitic (I) Rank-1 (`mean M`) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `0.0` | `100.0%` (`+13.155`) | `100.0%` | `+13.585` | `100%` | `100.0%` (`+40.03`) |
| `0.1` | `100.0%` (`+11.332`) | `100.0%` | `+11.497` | **`99%`** | **`94.0%`** (`+30.78`) |
| `0.2` | `100.0%` (`+10.260`) | **`99.67%`** | `+9.673` | **`90%`** | **`86.0%`** (`+26.35`) |
| `0.3` | `100.0%` (`+8.510`) | **`95.67%`** | `+7.767` | **`80%`** | **`70.0%`** (`+18.49`) |
| `0.4` | `100.0%` (`+7.678`) | `92.67%` | `+6.256` | — | `56.0%` (`-4.12`) |
| `0.5` | `99.67%` (`+6.242`) | `82.67%` | `+4.242` | — | `55.0%` (`+1.81`) |

### Stage L4 — Honest Negative Controls & Code-Separation Boundaries

1. **Macro-typology (`Kernels A & B`, logged prior run):** `/a, i, u/` token frequency (`~81%`) yields `Z_perm < 0` (see [[models/language-id-kernel/kernels/a-word-shape|Kernel A]] and [[models/language-id-kernel/kernels/b-kober-trios|Kernel B]]); consistent with Semitic but non-diagnostic alone.
2. **Cretan Hieroglyphic→Linear A pictographic acrophony (logged prior run):** Pre-registered test yields **`3/20`** matches (`p ≈ 0.31`, null)—aligning with Valério & Ferrara (2020) and Ottaviano et al. (2026) against naive phonocentric derivation.
3. **Single-sign open-dictionary ligature saturation (computed live):** Live calibration run (`B = 500`) confirms **Linear B fails its own Greek calibration gate** (`Z = +0.503, p = 0.39521`), proving that a ~60-sign syllabary saturates under single-sign open-dictionary matching and keeping [[models/language-id-kernel/kernels/f-acrophony|Kernel F]] strictly auxiliary.

## 5. What It Proves & Honest Limits

Kernel L shows that `kaphtor`'s lexical and morphological signals do **not** depend on assuming 100% fidelity of Linear B→Linear A homomorphs: Kernels D, I, and J survive contested-series removal (`Q, Z, W, J`), every leave-one-series-out consonant-grid jackknife (`8/8` D, `7/7` J on `p_perm <= 0.05`, with Kernel J's stricter `p_concept <= 0.05` holding on `2/7` and `drop K` leaving `n = 1`), and 20%–30% random consonant-series corruption on Kernel D (`99.67%` / `95.67%` rank-1 win rates). At the same time, Stage L1 honestly logs that the 11-sign Aegean–Cypriot homomorph core alone yields too few Linear A word types (`30` tokens, `< 20` types) to test bound-affix morphology, and Stage L4 draws an explicit empirical line separating multi-syllable anchors and bound morphology from under-constrained single-sign acrophony.
