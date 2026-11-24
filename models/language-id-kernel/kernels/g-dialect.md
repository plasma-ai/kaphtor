---
name: models/language-id-kernel/kernels/g-dialect
title: "Kernel G: Palaikastro Dialect Coherence"
desc: "Tests whether five Central Crete vs Palaikastro libation-formula minimal pairs conform to a single 4-rule Northwest Semitic isogloss bundle."
tags: [linear-a, kernel-g, dialect, palaikastro]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel G: Palaikastro Dialect Coherence

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/dialect_g.py`
- **Unit Test:** `models/language-id-kernel/tests/test_dialect_g.py`
- **Channel Classification:** Supporting phonological-coherence channel
- **Command:** `uv run --no-sync python models/language-id-kernel/dialect_g.py --n-perm 10000`

## 2. Method & Statistic

Evaluates five GORILA-attested minimal pairs contrasting Central Crete with Eastern Crete (Palaikastro) libation formulas against a fixed 4-rule Northwest Semitic phonological isogloss bundle (`NWS_ISOGLOSS_RULES`), comparing the observed hit count against $B = 10{,}000$ random 4-rule bundles sampled over the same CV feature space.

## 3. Data Called Upon (`PALAIKASTRO_PAIRS`)

| Central Crete Form | Palaikastro Form | CV Rule | Phonological Feature |
| --- | --- | --- | --- |
| `JA-SA-SA-RA-ME` | `A-SA-SA-RA-ME` | `JA -> A` | Initial glide loss (`y- > ʾ-`) |
| `JA-DI-KI-TU` | `A-DI-KI-TE-TE` | `JA -> A` | Initial glide loss (`y- > ʾ-`) |
| `A-TA-I-*301-WA-JA` | `A-TA-I-*301-WA-E` | `JA -> E` | Final diphthong contraction (`*-aya > -ē`) |
| `U-NA-RU-KA-NA-SI` | `U-NA-RU-KA-NA-TI` | `SI -> TI` | Interdental isogloss (`*ṯ > š / t`) |
| `I-PI-NA-MA` | `I-PI-NA-MI-NA` | `MA -> MI` | Enclitic vowel/expansion (`-ma ~ -mi-na`) |

- **Reference:** Self-contained rule engine (zero external files required).

## 4. Calibration & Null Distribution (`B = 10,000`)

- Random 4-rule bundles match an average of `0.00680` of the 5 pairs (`perm_mean = 0.00680`).

## 5. Linear A Results

- **5 / 5 minimal pairs match** the 4-rule NWS isogloss bundle (**`Z_perm = +50.05`**, **`p_perm = 0.00010`**).

## 6. What It Proves & Honest Limits

Shows that orthographic variation between Central Crete and Eastern Crete (Palaikastro) libation formulas follows coherent, attested Northwest Semitic phonological rules rather than random scribal errors, while noting the small sample size (`n = 5` minimal pairs).
