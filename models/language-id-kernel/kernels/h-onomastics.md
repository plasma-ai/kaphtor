---
name: models/language-id-kernel/kernels/h-onomastics
title: "Kernel H: Structurally-Gated Roster Onomastics"
desc: "Compares 57 structurally-identified Linear A personal-name slots (WORD 1) against shipped Bronze Age onomastic pools without dictionary peeking."
tags: [linear-a, kernel-h, onomastics, names]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel H: Structurally-Gated Roster Onomastics

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/onomastics_h.py`
- **Unit Test:** `models/language-id-kernel/tests/test_onomastics_h.py`
- **Channel Classification:** Cultural and onomastic milieu diagnostic
- **Command:** `uv run --no-sync python models/language-id-kernel/onomastics_h.py --n-perm 1000`

## 2. Method & Statistic

Extracts putative Linear A personal names **purely by tablet syntax** — undamaged `>=3`-sign syllabic words immediately followed by the numeral `1` on administrative tablets (`n = 57` unique types) — without consulting any dictionary or onomasticon. Scores those 57 name slots against size-equalized (`budget = 1,314` types per arm) 3-gram CV models of Bronze Age onomastica under $B = 1{,}000$ consonant-series grid permutations.

## 3. Data Called Upon (Shipped Defaults in `v1.3.0`)

- **Target:** 57 structurally-gated `WORD 1` roster names (`data/linear-a/corpus.json`).
- **Comparison pools:**
  - `levant_semitic`: `data/share-alike/oracc-levant/name_occurrences.jsonl` (Ugarit, Amarna, Alalakh personal/royal names; `1,314` clean `>=3`-sign names; CC BY-SA 3.0)
  - `kassite`: `data/ane/kassite-concordances/entries.jsonl` (`3,795` clean `>=3`-sign personal names; Public Domain)
  - `mycenaean_lb`: `data/share-alike/linear-b/linear_b_tokens.jsonl` (DAMOS-verified PY/KN `>=3`-sign words; CC BY-NC-SA 4.0)
  - `hurrian` & `anatolian`: `data/share-alike/anatolian/tlhdig_docs.jsonl` (`Hur`, `Hit`; CC BY 4.0)
  - *(Optional `KAPHTOR_AMORITE_ONOMASTICON` adds Gelb/Huffmon Amorite personal names.)*

## 4. Calibration & Equalization

All five pools are down-sampled with fixed seed `20261122` to the exact size of the smallest pool (`budget = 1,314` distinct `>=3`-sign types per arm) so larger corpora gain zero vocabulary advantage.

## 5. Linear A Results (`v1.3.0` Standalone, `n = 57`, `budget = 1,314`/arm, `B = 1,000`)

| Onomastic Pool | Bits / Sign (Lower = Better) | Rank / Notes |
| --- | ---: | --- |
| **`mycenaean_lb`** | **`5.8791`** | #1 (shared Cretan personal names in Knossos Linear B) |
| **`levant_semitic`** | **`6.1407`** | #2 (`M = -0.2617`, `perm_mean = -0.7662`, `Z_perm = +1.56, p = 0.06494`) |
| `kassite` | `6.9268` | #3 |
| `hurrian` | `7.1879` | #4 |
| `anatolian` | `7.4262` | #5 |

## 6. What It Proves & Honest Limits

Confirms a shared Bronze Age Cretan personal-name layer carried over from Linear A into Knossos Mycenaean Linear B (`#1`), with LBA Levantine Semitic personal names placing `#2` — `0.79–1.29` bits/sign ahead of Kassite, Hurrian, and Anatolian — without claiming personal-name rosters alone prove genetic affiliation.
