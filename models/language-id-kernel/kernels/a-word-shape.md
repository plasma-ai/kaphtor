---
name: models/language-id-kernel/kernels/a-word-shape
title: "Kernel A: Word-Shape Forward LID"
desc: "Pooled sign-parity Witten-Bell 3-gram CV language identification across all 505 undamaged strict-Linear-B Linear A word types."
tags: [linear-a, kernel-a, phonotactics, typology]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel A: Word-Shape Forward LID

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/lid.py` + `pilot_fix1.py` (invoked via `kaphtor_kernel.py run`)
- **Run Ledger:** `runs/kaphtor-kernel-linear-a-20261122T222434Z.json`
- **Channel Classification:** Primary macro-typology (contributes to the `A+B+D` Stouffer aggregate)
- **Command:** `uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py run --strict-lb-only`

## 2. Method & Statistic

Trains pooled family Witten-Bell 3-gram models over CV sign keys `(series, vowel)` with **sign-count parity** ($S = 3{,}700$ signs per arm, 5 seeded draws, glide rule applied to all rule-spelled sources). Every family arm is scored by mean bits per sign over distinct word types, with margin $M_A(\text{arm}, X) = \min_{r \neq \text{arm}} H_A(r, X) - H_A(\text{arm}, X)$, and tested against consonant-series grid permutations holding vowels and word boundaries fixed.

## 3. Data Called Upon

- **Target:** 505 distinct undamaged Linear A word types across 340 documents (`728` kept tokens of `8,491` total; `data/linear-a/corpus.json`, strict Linear B values only).
- **Trained family arms (6 arms meeting `MIN_ARM = 800` `train` types):**
  - `semitic`: `data/share-alike/hebrew/oshb_words.jsonl` (CC BY 4.0), `data/share-alike/ugaritic/eupt_tokens.jsonl` (CC BY-SA 4.0), `data/share-alike/cuneiform/oracc_akkadian.jsonl` (CC0 1.0) *(plus optional Arabic, Syriac and Geʿez when `KAPHTOR_ANE_DIR` is set)*
  - `greek`: `data/share-alike/greek/lsj_lb_keys.jsonl` and `diodorus_1_5.jsonl` (CC BY-SA 4.0)
  - `anatolian`: `data/share-alike/anatolian/tlhdig_docs.jsonl` (`Hit`, `Luw`; CC BY 4.0)
  - `hurrian`: `data/share-alike/anatolian/tlhdig_docs.jsonl` (`Hur`; CC BY 4.0)
  - `hattic`: `data/share-alike/anatolian/tlhdig_docs.jsonl` (`Hat`/`Hattian`; CC BY 4.0)
  - `latin`: `data/share-alike/latin/latinf_forms.jsonl` (CC BY-SA 4.0)
- **Outside-arm & calibration controls:** `data/share-alike/cuneiform/oracc_sumerian.jsonl` (CC0 1.0; `< 800` `train` types, held out as an outside-every-arm control) and `data/share-alike/linear-b/linear_b_tokens.jsonl` (CC BY-NC-SA 4.0; DAMOS-verified PY/KN tablets).

## 4. Calibration Gate (`pilot_fix1.py`)

- **G1 (real Linear B tablets as Greek):** `1.0 / 1.0` power under both `omission` and `plene`.
- **G2 (own-arm classification):** `1.0` across every language.
- **G3 (Central Semitic sisters without self):** Hebrew `1.0`, Syriac `1.0`, Geʿez `1.0`, Arabic `0.8` (`omission`) / `0.3` (`plene` against strict max; `1.0` against $\theta_{95}$).

## 5. Linear A Results (`runs/kaphtor-kernel-linear-a-20261122T222434Z.json`)

| Family Arm | Bits / Sign (Lower = Better) | Margin / Null |
| --- | ---: | --- |
| **Semitic** | **`5.4902`** | `M = +0.6230`, `perm_mean = +0.6430`, `Z_perm = -0.213`, `p_perm = 0.58706` |
| Hurrian | `6.1133` | Runner-up |
| Greek | `6.4638` | — |
| Latin | `6.4822` | — |
| Hattic | `6.6468` | — |
| Anatolian | `6.6671` | — |

## 6. What It Proves & Honest Limits

Kernel A establishes that Linear A's corpus-wide **syllabic and `/a, i, u/` vowel-core phonotactics** fit Semitic best among modeled families, while proving via the consonant-grid null (`Z_perm = -0.213`) that whole-corpus 3-gram fit alone reflects vowel-core macro-typology rather than consonant-specific identity.
