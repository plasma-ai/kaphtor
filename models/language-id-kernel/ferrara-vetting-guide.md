---
name: models/language-id-kernel/ferrara-vetting-guide
title: "Epigraphic & Statistical Vetting Guide for Bologna (INSCRIBE / SAPIENCE) Reviewers"
desc: "Five-command zero-LLM adversarial workbench enabling epigraphers to test, ablate, and attempt to falsify kaphtor's twelve-kernel Linear A suite in under two minutes."
tags: [linear-a, probabilistic-model, vetting, bologna, inscribe, sapience]
created: 2026-11-24T00:00:00Z
updated: 2026-11-24T00:00:00Z
---

# Epigraphic & Statistical Vetting Guide for Bologna (INSCRIBE / SAPIENCE) Reviewers

[[models/language-id-kernel/_index|..]]

***

**Purpose:** A five-command, zero-LLM adversarial workbench designed so epigraphers and computational linguists—including reviewers from the Bologna INSCRIBE and SAPIENCE projects—can attempt to **falsify** `kaphtor`'s Linear A language-identification signal in under two minutes, using strict Linear B values only (`*301`, `AB79`, `*314`, `*21F` excluded) and real Mycenaean Linear B (`DAMOS`) calibration gates.

---

## Five Challenges ("Try to Break It")

### Challenge 1 — Strip Every Cult Text, Vessel, and Grain Word: Run Strictly on Corazza et al. (2021) Fractions (**Kernel K**)

```bash
uv run --no-sync python models/language-id-kernel/fractions_k.py --no-lid
uv run --no-sync python models/language-id-kernel/fractions_k.py --autopsy-conflicts
uv run --no-sync python models/language-id-kernel/fractions_k.py --n-perm 5000
```

- **What to check:** Stages K0–K1 are 100% language-free: applying Corazza, Ferrara, Montecchi, Tamburini & Valério (2021, *JAS* 125: 105214) to raw Unicode `A700` glyphs yields **`0` strict `> 1` compound-fraction violations** across `55` compound fractions (resolving `HT 27a` `JE+B = 19/20`, whereas Bennett legacy fails at `13/12 > 1`), blindly discovers `KU-RO` at rank #1 (`9` exact integer sums vs `<= 1` for any other token), and outputs the 5-item `HT 123+124a` `*308`-column (`H = A + 1/4`) conflict ledger for 3D/RTI re-reading. Stage K2 scores *only* accounting words against open dictionaries: Linear B (`TO-SO / O-PE-RO`) selects **Greek** (`Z = +2.48, p = 0.01440`; Semitic rejected `p = 0.40132`), while Linear A's deduplicated pair (`KU-RO / KI-RO`) selects **Semitic** (`Z = +3.15, p = 0.01480, ΔLL = +1.190`) and **rejects LSJ Greek (`p = 0.05439`)** (full triad `KU-RO / PO-TO-KU-RO / KI-RO` also ranks Semitic #1 at `Z = +2.86, p = 0.01280, ΔLL = +0.551`).

### Challenge 2 — Delete Every Dictionary Completely: Test Bound-Affix Morphology Alone (**Kernel I**)

```bash
uv run --no-sync python models/language-id-kernel/morphology_i.py --mode omission --n-perm 5000
```

- **What to check:** Zero dictionaries, zero semantic anchors. Linear B selects **Greek** (`M = +472.95, p_M = 0.02679`, Semitic `0.875`); Linear A selects **Semitic** as the sole pass (`M = +40.03, Z_M = +2.63, p_M = 0.00360, p_cv = 0.00040`, all rivals `0.200–0.995`).

### Challenge 3 — Assume 20%–30% of Backward-Projected Linear B Values Are Wrong (**Kernel L**)

```bash
uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage all --n-perm 1000 --trials 300
```

- **What to check:** Operationalizes Steele & Meißner (2017) and Salgarella (2020) backward-projection caution alongside Valério & Ferrara (2020) and Ferrara, Montecchi & Valério (2022) on CH↔LA continuity: on Salgarella & Castellan's independent **SigLA word segmentation (`sigla_db.json`, `686` words / `495` types)**, Semitic is the **sole pass** (`M = +35.12, Z_M = +2.66, p_M = 0.00200`; all 6 rivals `0.172–1.000`); across **all 12 single-series drops** on Kernel I, **`10/12` pass `p_M <= 0.05`**, with `drop T` producing the #1 deepest collapse (`p_M = 0.26547`—Semitic `t-`/`-t`); dropping `Q+Z` raises Kernel I's margin (`M = +44.33, p_M = 0.00200`); **8/8** L1SO drops pass Kernel D (`p_perm <= 0.05`); **7/7** pass Kernel J on `p_perm <= 0.05` (`p_concept <= 0.05` on `2/7`, `drop K` leaves `n = 1` in J vs `n = 3` in D and `M = +47.30` in I); and at `ε = 0.2` / `ε = 0.3` random consonant-series corruption, Kernel D Semitic holds **`99.67%`** / **`95.67%`** rank-1 (**`90%`** / **`80%`** `p_perm <= 0.05`) while lexicon-free Kernel I holds **`86%`** / **`70%`** rank-1.

### Challenge 4 — Eliminate Researcher Curation and Add CC0 Sumerian + LSJ Greek (**Kernel J**)

```bash
uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000 --seed 20261125
```

- **What to check:** Every headword is auto-extracted by fixed English concept regexes from open JSONL lexica (including ePSD2 Sumerian `3,589` lemmas and LSJ Greek `101,410` glosses) and tested against both consonant-grid swaps (`p_perm`) and concept shuffles (`p_concept`). Semitic is the sole dual-null pass across signed `FULL_8` (`0.00010 / 0.02520`), deduplicated `LA_DEDUP_7` (`0.00010 / 0.01111`), purest strict-LB `LA_DEDUP_9` including blind untranslated `DA-RO-PA` (`HT 38 *403-VS`: **`0.00010 / 0.00390`**; Greek `0.626`, Sumerian `0.663`), and sensitivity tier `LA_DEDUP_12` folding `PA₃ → PA` on `HT 31`'s three `PA₃` vessels (**`0.00010 / 0.00180`**); `K`-free `LA_DROPK_5` passes consonant-grid permutation (`p_perm = 0.01640`, `p_concept = 0.217` underpowered at `n = 5`). Greek is the sole pass on Linear B (`n = 6`: `0.00010 / 0.01389`; `EXT9`: `481:1`, `0.00010 / 0.00020`; Semitic rejected `0.115 / 0.293`).

### Challenge 5 — Verify Our Honest Negative Controls (**Kernel L4**)

```bash
uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage l4 --n-perm 500
```

- **What to check:** We explicitly publish where statistical methods **fail**: (1) Kernels A & B (`/a, i, u/` vowels) are non-diagnostic (`Z_perm < 0`); (2) Cretan Hieroglyphic→Linear A pictographic acrophony tests **null** (`3/20, p ≈ 0.31`, aligning with Valério & Ferrara 2020 and Ottaviano et al. 2026); (3) single-sign open-dictionary ligatures saturate the ~60-sign syllabary so heavily that **even Linear B fails Greek calibration (`Z = +0.503, p = 0.39521`)**, keeping [[models/language-id-kernel/kernels/f-acrophony|Kernel F]] strictly auxiliary.
