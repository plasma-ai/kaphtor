---
name: models/language-id-kernel/kernels/b-kober-trios
title: "Kernel B: Unsupervised Kober Trios"
desc: "Unsupervised extraction and hierarchical Witten-Bell modeling of stem-sharing paradigm transitions (Kober pairs and trios) over strict-Linear-B words."
tags: [linear-a, kernel-b, kober-trios, typology]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel B: Unsupervised Kober Trios

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/kober_b.py` (invoked via `kaphtor_kernel.py run`)
- **Unit Test:** `models/language-id-kernel/tests/test_kober_b.py`
- **Run Ledger:** `runs/kaphtor-kernel-linear-a-20261122T222434Z.json`
- **Channel Classification:** Primary macro-typology (contributes to the `A+B+D` Stouffer aggregate)

## 2. Method & Statistic

Automatically extracts stem-sharing word pairs and connected components ("Kober trios") from distinct word types via `render/c_align.align` (shared contiguous run $\ge 2$ signs, affix residue $\le 2$ signs per side, plus stem-final consonant-series vowel alternations) without hand-picking any paradigm. Trains a hierarchical Witten-Bell model $P_L(\text{pol}, e_1, e_2) = P_L(\text{pol}) P_L(e_1, e_2 \mid \text{pol})$ equalized at $N_{\text{tr}} = 2{,}900$ transitions per arm, scored in mean bits per extracted transition against consonant-series grid permutations.

## 3. Data Called Upon

- **Target:** Unsupervised transitions extracted from the 505 distinct undamaged strict-Linear-B Linear A word types (`data/linear-a/corpus.json`).
- **Training arms:** The same 6 shipped family arms (`MIN_ARM = 800`) and DAMOS-verified Linear B control described in [[models/language-id-kernel/kernels/a-word-shape|Kernel A]].

## 4. Calibration Gate (`pilot_kober_b.py`, `plene`, $N_{\text{tr}} = 2{,}900$)

- **Own-arm accuracy:** **62 / 62 (100%)** across all 14 dev languages, including real Linear B tablets (`+1.12` Greek, `-1.12` Semitic).
- **Sister recovery (without self):** Hebrew `+3.88`, Aramaic `+3.46`, Syriac `+3.27`, Geʿez `+2.70`, Arabic `+1.56`, Ugaritic `+0.75`, Luwian `+1.53`, Urartian `+1.00`, vs. Sumerian isolate `+0.27`.

## 5. Linear A Results (`runs/kaphtor-kernel-linear-a-20261122T222434Z.json`)

| Family Arm | Bits / Transition (Lower = Better) | Margin / Null |
| --- | ---: | --- |
| **Semitic** | **`22.3622`** | `M = +2.2880`, `perm_mean = +2.7696`, `Z_perm = -1.087`, `p_perm = 0.84577` |
| Hurrian | `24.6502` | Runner-up |
| Anatolian | `25.8817` | — |
| Greek | `26.7289` | — |
| Hattic | `27.0365` | — |
| Latin | `27.4343` | — |

## 6. What It Proves & Honest Limits

Kernel B confirms that Linear A's unsupervised stem-alternation profile aligns best with Semitic in raw bits per transition, while its consonant-grid null (`Z_perm = -1.087`) shows that this broad transition statistic captures vowel/length typology rather than consonant-specific affix identity (which is isolated by [[models/language-id-kernel/kernels/i-morphology|Kernel I]]).
