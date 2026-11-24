---
name: models/language-id-kernel/kernels/c-liturgy
title: "Kernel C: Size-Locked Liturgical Cohesion"
desc: "Dirichlet log-odds Biblical Hebrew cultic vocabulary and shipped CC0 Akkadian vs size-locked K=300 rival vocabularies scored on IO Za 2 and the 33-vessel formula family."
tags: [linear-a, kernel-c, liturgy, io-za-2]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel C: Size-Locked Liturgical Cohesion

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/liturgy_c.py` (+ `stress_test_cd.py`)
- **Unit Test:** `models/language-id-kernel/tests/test_liturgy_c.py`
- **Run Ledgers:** `runs/kaphtor-kernel-linear-a-20261122T222434Z.json`, `runs/stress-test-cd-2026-11-22.json`
- **Channel Classification:** Supporting consonant-specific channel (votive libation register)
- **Command:** `uv run --no-sync python models/language-id-kernel/liturgy_c.py --run-linear-a --n-perm 1000 --conv plene`

## 2. Method & Statistic

Mechanically builds exact **size-locked (`K = 300` distinct CV word types per arm)** vocabularies from `train` splits only:

- `hebrew_lit`: Monroe et al. (2008) informative Dirichlet log-odds contrasting OSHB Psalms/Leviticus/Lamentations/Joel/Habakkuk/Song against narrative prose (strictly excluding calibration control chapters).
- `akkadian_lit` *(shipped in `v1.3.0`)*: Top-300 CC0 ORACC Old/Standard Babylonian forms.
- `anatolian_lit`, `hurrian_lit`, `greek_lit` *(plus optional `syriac_lit` when `KAPHTOR_ANE_DIR` holds Ephrem)*: Top-300 `train` forms.

Scores any prayer inscription on mean bounded CV alignment ($\tau = 0.35$, up to 1 prefix/suffix sign stripped at `0.10`/sign penalty) against consonant-series grid permutations.

## 3. Data Called Upon

- **Target:** `IO Za 2` (7 strict-LB words, `*301` kept opaque) and the full 33-vessel libation formula family (`n = 41` undamaged types).
- **Shipped corpora:** `data/share-alike/hebrew/oshb_words.jsonl` (CC BY 4.0), `data/share-alike/cuneiform/oracc_akkadian.jsonl` (CC0 1.0), `data/share-alike/anatolian/tlhdig_docs.jsonl` (CC BY 4.0), `data/share-alike/greek/diodorus_1_5.jsonl` (CC BY-SA 4.0).

## 4. Calibration Gate (104 Protocol D v3 Controls, `K = 300`, `B = 200`)

- `H1_semitic_prayer` (`n = 15`): mean `Z = +2.15`, `8/15` (53%) at `p <= 0.05`.
- `H3_semitic_nonprayer` (`n = 23`): mean `Z = +1.27`, `6/23` (26%).
- Non-Semitic controls: `FAB` `0/10` (`+0.45`), `H2_luwian` `0/8` wins (`+0.12`), `H2_hurrian` `0/8` wins (`+0.37`), `NEG_linear_b` `2/20` (`+0.37`), `H2_egyptian` (Afroasiatic, drawn vowels) `8/20` (`+1.47`).

## 5. Linear A Results

### `IO Za 2` (`v1.3.0` Standalone, `K = 300`, `B = 1,000`, `plene`)

| Arm | Score | `Z_perm` | `p_perm` |
| --- | ---: | ---: | ---: |
| **`hebrew_lit`** | **`0.1020`** | **`+3.04`** | **`0.02697`** |
| **`akkadian_lit`** | `0.1088` | `+1.67` | `0.06294` |
| `hurrian_lit` | `0.0612` | `+1.03` | `0.18681` |
| `anatolian_lit` | `0.0136` | `-0.31` | `0.48052` |
| `greek_lit` | `0.0000` | `-0.66` | `1.00000` |

### 33-Vessel Formula-Family Stress Test (`runs/stress-test-cd-2026-11-22.json`, `B = 2,000`)

- `IO Za 2` (`n = 7`): `hebrew_lit` #1 (`Z = +2.908, p = 0.03248`); every rival `Z <= +1.01, p >= 0.18`.
- Full 33-vessel family (`n = 41` undamaged types): `hebrew_lit` #1 (`Z = +0.73, p = 0.231`), followed by `syriac_lit` (`Z = +0.56, p = 0.293`) — not significant once diluted by 34 site-specific proper names and dedicant/deity variants.

## 6. What It Proves & Honest Limits

Provides consonant-specific supporting evidence that the canonical peak-sanctuary inscription `IO Za 2` selectively matches automated Northwest Semitic cultic vocabulary (with East Semitic `akkadian_lit` placing second), while transparently documenting dilution across the wider proper-name-heavy libation corpus.
