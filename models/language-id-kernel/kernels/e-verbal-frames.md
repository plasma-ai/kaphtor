---
name: models/language-id-kernel/kernels/e-verbal-frames
title: "Kernel E: Verbal Edge-Frames"
desc: "Equal-budget Witten-Bell word-edge model (pre1, pre2, suf1, suf2) comparing Semitic finite verbs against long-word rivals on 46 Linear A votive words."
tags: [linear-a, kernel-e, morphology, votive]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel E: Verbal Edge-Frames

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/verbs_e.py`
- **Channel Classification:** Exploratory verbal-morphology channel
- **Command:** `uv run --no-sync python models/language-id-kernel/verbs_e.py --n-perm 500`

## 2. Method & Statistic

Trains equal-budget Witten-Bell edge-frame models $P_L(\text{pre}_1, \text{pre}_2, \text{suf}_1, \text{suf}_2)$ over `>=4`-sign words (`budget = 1,986` distinct `>=4`-sign types per arm), using exclusively finite Biblical Hebrew verbs (`morphology` starting with `HV`) for Semitic against `>=4`-sign words in inflected Greek, Hittite, Hurrian, and Latin. Tested against consonant-series grid permutations.

## 3. Data Called Upon

- **Target:** 46 undamaged `>=4`-sign words on non-administrative Linear A supports (`Za`, `Zb`, `Zc`, `Zf`, `Zg`; `data/linear-a/corpus.json`).
- **Shipped training arms:** `data/share-alike/hebrew/oshb_words.jsonl` (`HV*` verbs; CC BY 4.0), `data/share-alike/greek/diodorus_1_5.jsonl` (CC BY-SA 4.0), `data/share-alike/anatolian/tlhdig_docs.jsonl` (`Hit`, `Hur`; CC BY 4.0), `data/share-alike/latin/latinf_forms.jsonl` (CC BY-SA 4.0).

## 4. Calibration Gate (`dev` Splits, `plene`, `budget = 1,986`)

- **5 / 5 (100%) PASS:** every dev split (`semitic_verbs`, `greek`, `anatolian`, `hurrian`, `latin`) identifies its own arm cleanly.

## 5. Linear A Results (`n = 46`, `B = 500`, `plene`)

| Arm | Bits / Word (Lower = Better) | Margin / Null |
| --- | ---: | --- |
| **`semitic_verbs`** | **`25.059`** | `M = +1.0561`, `perm_mean = +0.1620`, `Z_perm = +0.85`, `p_perm = 0.20758` |
| `hurrian` | `26.115` | Runner-up |
| `anatolian` | `26.536` | — |
| `greek` | `29.117` | — |
| `latin` | `29.657` | — |

## 6. What It Proves & Honest Limits

Directionally consistent with Semitic prefix+suffix verbal frames on long votive words, but statistically underpowered at `n = 46` types (`p = 0.208`). Treated as exploratory rather than decisive; corpus-wide bound-affix grammar is tested with far higher statistical power by [[models/language-id-kernel/kernels/i-morphology|Kernel I]].
