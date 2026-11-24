---
name: models/language-id-kernel/kernels/f-acrophony
title: "Kernel F: Commodity Ligature Acrophony"
desc: "Tests whether Linear A commodity adjunct signs (GRA/OLE/VIN) match initial CV acrophones of Semitic qualifiers, calibrated on Linear B."
tags: [linear-a, kernel-f, acrophony, ligatures]
created: 2026-11-23T19:35:00Z
updated: 2026-11-23T19:35:00Z
---

# Kernel F: Commodity Ligature Acrophony

[[models/language-id-kernel/kernels/_index|..]]

***

## 1. Role & Reproduction

- **Script:** `models/language-id-kernel/acrophony_f.py`
- **Unit Test:** `models/language-id-kernel/tests/test_acrophony_f.py`
- **Channel Classification:** Auxiliary consonant-specific phonetic channel
- **Command:** `uv run --no-sync python models/language-id-kernel/acrophony_f.py --calibrate --run-linear-a --n-perm 10000`

## 2. Method & Statistic

Tests whether single-sign syllabic adjuncts ligatured onto `GRA` (grain), `OLE` (oil), `VIN` (wine), and `TELA` (textile) logograms match the initial CV syllable (acrophone) of attested commodity qualifiers across Semitic, Greek, Anatolian, and Hurrian under $B = 10{,}000$ consonant-series grid permutations.

## 3. Data Called Upon

- **Linear A Target (`n = 10`):** `GRA+KU`, `GRA+PA`, `GRA+QE`, `OLE+KI`, `OLE+MI`, `OLE+DI`, `OLE+TA`, `OLE+NE`, `OLE+RI`, `VIN+RA`.
- **Linear B Calibration Target (`n = 6`):** `OLE+PA`, `OLE+WE`, `OLE+A`, `GRA+PE`, `TELA+TE`, `TELA+PU`.
- **Reference:** Self-contained bounded commodity-qualifier synsets + frozen `render/series.json` (zero external files required).

## 4. Calibration Gate (Linear B Ligatures, `B = 10,000`)

- **PASS:**
  - **Greek:** `LL = -9.414`, **`Z_perm = +4.31`**, **`p_perm = 0.00070`**
  - Anatolian: `LL = -22.808` (`Z_perm = +1.62, p = 0.06029`)
  - Hurrian: `LL = -24.272` (`Z_perm = +0.54, p = 0.28057`)
  - **Semitic (rejected):** `LL = -27.853` (`Z_perm = +0.45, p = 0.36196`)

## 5. Linear A Results (`B = 10,000`)

| Language | `LL` | `Z_perm` | `p_perm` |
| --- | ---: | ---: | ---: |
| **Semitic** | **`-20.367`** | **`+5.53`** | **`0.00010`** (`0/10,000`, $\Delta\text{LL} = +28.17$) |
| Hurrian | `-48.533` | `-0.32` | `0.58304` |
| Greek | `-51.520` | `-0.09` | `0.51035` |
| Anatolian | `-53.227` | `-1.10` | `0.89431` |

## 6. What It Proves & Honest Limits

Shows strong consonant-specific acrophonic alignment on Linear A commodity adjuncts. However, Kernel J's `--ligatures` check demonstrated that single-syllable acrophones saturate a large uncapped open dictionary (Greek hits 46–48 of ~55 CV syllables, causing Linear B to miss its Greek gate at `p = 0.348`). Kernel F is therefore classified as an **auxiliary** channel behind multi-syllable anchors ([[models/language-id-kernel/kernels/d-anchors|D]] + [[models/language-id-kernel/kernels/j-auto-anchors|J]]) and morphology ([[models/language-id-kernel/kernels/i-morphology|I]]).
