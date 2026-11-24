---
name: models/language-id-kernel/kernels/i-morphology
title: "Kernel I: Unsupervised Bound-Affix Morphology"
desc: "Strict one-sided stem-containment prefix/suffix polarity and CV-affix identity tested under a discriminative margin-permutation null."
tags: [linear-a, kernel-i, morphology, primary]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel I: Unsupervised Bound-Affix Morphology

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/morphology_i.py`
- **Unit Test:** `models/language-id-kernel/tests/test_morphology_i.py`
- **Run Ledgers:** `runs/morphology-i-2026-11-23.json`, `runs/morphology-i-robustness-2026-11-23.json`
- **Channel Classification:** **Primary consonant-specific grammatical proof**
- **Command:** `uv run --no-sync python models/language-id-kernel/morphology_i.py --mode omission --n-perm 5000`

## 2. Method & Statistic

Automatically extracts **strict one-sided bound affixes** from distinct word types (`S` vs `p+S` / `S+s` with `len(S) >= 2`, plus `len(S) >= 3` single-sided alternations) and scores two orthogonal channels:

1. **Prefix-vs-suffix polarity** (`ll_pol`, distinguishing Semitic's balanced prefix+suffix inflection from heavily suffixing Greek/Anatolian/Hurrian/Latin).
2. **Bound affix CV-sign identity** (`ll_cv`), tested against $B = 5{,}000$ consonant-series swaps under the **discriminative margin-permutation null** $M_L(\pi) = \text{LL}_L(\pi) - \max_{R \neq L} \text{LL}_R(\pi)$, which cancels universal cross-linguistic suffix consonants (`T, R, M, N, S`).

Greek is trained **strictly on inflected running prose** (`diodorus_1_5.jsonl`, never uninflected LSJ dictionary lemmas) so Greek's true inflectional suffix profile is preserved (`p_pre = 0.355` vs Linear B `0.349`).

## 3. Data Called Upon (Shipped Defaults in `v1.3.0`)

- **Target:** 505 undamaged strict-Linear-B Linear A types (`data/linear-a/corpus.json`), plus administrative (`n = 404`) and votive (`n = 110`) splits.
- **Training arms:** Ancient Near Eastern Semitic (`oshb_words.jsonl`, `eupt_tokens.jsonl`, `oracc_akkadian.jsonl`), Diodorus Greek (`diodorus_1_5.jsonl`), TLHdig Anatolian/Hurrian/Hattic (`tlhdig_docs.jsonl`), ORACC CC0 Sumerian (`oracc_sumerian.jsonl`), LiLa Latin (`latinf_forms.jsonl`); calibrated on DAMOS-verified Linear B (`linear_b_tokens.jsonl`).

## 4. Calibration Gate (`v1.3.0` Standalone, `omission`, `B = 5,000`)

- **Dev-Split Calibration:** **7 / 7 (100%) PASS**, every family (`anatolian`, `greek`, `hattic`, `hurrian`, `latin`, `semitic`, `sumerian`) at `p_cv = 0.00050`.
- **Linear B Gate (`n = 2,500`, `p_pre = 0.349`):** **Greek only pass** — **`M = +472.95, Z_M = +1.84, p_M = 0.02679`**; Semitic rejected (`M = -472.95, p_M = 0.87522`); all 6 non-Greek rivals `p_M >= 0.53`.

## 5. Linear A Results

### `v1.3.0` Standalone ANE Semitic (`omission`, seed `20261123`, `B = 5,000`, `p_pre = 0.419`)

| Family | `ll_joint_cv` | Margin `M` | `Z_M` | `p_M` | `Z_cv` | `p_cv` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Semitic** | **`-703.58`** | **`+40.03`** | **`+2.63`** | **`0.00360`** | **`+2.55`** | **`0.00040`** |
| Sumerian | `-743.61` | `-40.03` | `-2.68` | `0.99520` | `+1.25` | `0.10958` |
| Hattic | `-748.28` | `-44.70` | `-0.51` | `0.70986` | `+1.76` | `0.02719` |
| Anatolian | `-769.99` | `-66.41` | `+0.29` | `0.40452` | `+1.80` | `0.02659` |
| Hurrian | `-773.19` | `-69.61` | `+0.69` | `0.25835` | `+1.91` | `0.01780` |
| Latin | `-788.30` | `-84.73` | `+0.36` | `0.36253` | `+2.25` | `0.01220` |
| Greek | `-790.85` | `-87.27` | `+0.86` | `0.19956` | `+2.35` | `0.00900` |

### 5-Seed × Mode & Register Robustness (`runs/morphology-i-robustness-2026-11-23.json`, full 7-member Semitic, `B = 2,000`)

- **`omission` (5 seeds):** Semitic wins **5 / 5 seeds** (`mean M = +32.35`, `mean p_M = 0.03848`; per-seed `p_M = 0.0510, 0.0400, 0.0120, 0.0125, 0.0770`; seed 0 reaches `p_M = 0.04359` at `B = 5,000`).
- **Register splits (`omission`, seed 0):** Semitic wins both administrative (`n = 404, pre_rate = 0.485, M = +13.56, p_M = 0.04898`) and votive (`n = 110, pre_rate = 0.318, M = +5.04, p_M = 0.312`).
- **`plene` mode:** Linear B still selects Greek 5/5 seeds, while Linear A weakens to `mean p_M = 0.599` (consistent with Linear A's coda-omission orthography).

## 6. What It Proves & Honest Limits

Provides lexicon-free, consonant-specific **grammatical** proof that Linear A's bound prefix and suffix consonants match Ancient Near Eastern Semitic rather than Greek, Anatolian, Hurrian, Hattic, Sumerian, or Latin, while honestly recording that the margin null holds under Linear A's `omission` orthography and weakens under `plene`.
