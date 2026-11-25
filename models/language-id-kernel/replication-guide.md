---
name: models/language-id-kernel/replication-guide
title: "Replication & Objectivity Guide (Kernels A–L)"
desc: "Master scoreboard, objectivity audit, shipped reference inputs, and fresh-clone reproduction instructions for all twelve probabilistic language-identification kernels."
tags: [linear-a, probabilistic-model, replication, preregistration]
created: 2026-11-23T00:00:00Z
updated: 2026-11-25T15:47:00Z
---

# Replication & Objectivity Guide (Kernels A–L)

[[models/language-id-kernel/_index|..]]

This guide documents how to replicate every kernel in `models/language-id-kernel/` from a fresh `kaphtor` clone with zero external folders, which optional environment variables override or extend the shipped corpora, and the exact objectivity and calibration boundaries of all twelve kernels.

---

## 1. Anti-Circularity & Objectivity Guarantees

1. **Zero project-lexicon leakage:** No script in `models/language-id-kernel/` reads `lexicon.json`, `translations.json`, or `onomasticon.json`. Every Linear A target is read strictly from `data/linear-a/corpus.json` (GORILA/SigLA transliterations) using only agreed Linear B sign values (`render/series.json`, `render/signs-a5-proposed.json`; any sensitivity tier folding GORILA doublet `AB 56 / PA₃` is explicitly flagged).
2. **Zero LLMs & 100% deterministic:** All twelve kernels run in pure Python with fixed PRNG seeds (`seed = 20261122` / `20261123` / `20261124` / `20261125`). Rerunning any command reproduces the JSON ledgers in `runs/` bit-for-bit.
3. **Mandatory known-language calibration gates:** Every primary or high-impact kernel is first calibrated on known ancient languages (including real Linear B tablets, where **Greek** must win and **Semitic** must be rejected) before scoring Linear A.
4. **Honest negative/weak reporting:** Kernels whose raw-bit lead is driven by `/a, i, u/` vowel-core macro-typology rather than consonant identity (**A, B**) are explicitly labeled as typological (`Z_perm < 0`), not consonant-specific proof.

---

## 2. Twelve-Kernel Master Scoreboard (Strict Linear B Values Only)

| Kernel | Script | Runs on Fresh Clone? | Calibration Gate | Null Model(s) | Linear A Result | Honest Scope / Caveat |
|---|---|---|---|---|---|---|
| **A. Word-Shape LID** | `lid.py` + `pilot_fix1.py` | **YES** | Linear B → Greek (1.0/1.0) | Consonant-grid swaps | Semitic #1 (`M = +0.623` bits/sign, `Z_perm = -0.21`) | Vowel-core `/a, i, u/` typology |
| **B. Unsupervised Kober Trios** | `kober_b.py` | **YES** | 62/62 (100%) dev accuracy | Consonant-grid swaps | Semitic #1 (`M = +2.288` bits/tr, `Z_perm = -1.09`) | Vowel-core `/a, i, u/` typology |
| **C. Liturgical Cohesion** | `liturgy_c.py` | **YES** | 104 Protocol D v3 controls (Heb +2.15, FAB 0/10) | Size-locked `K=300` + consonant swaps | `IO Za 2`: Heb #1 (`Z = +3.04`, `p = 0.02697`); 33-vessel family (`n=41`): Heb #1 (`p = 0.231`) | Strong on `IO Za 2`, weaker diluted across all 41 formula words |
| **D. Pre-Linguistic Anchors** | `anchors_d.py` | **YES** | **PASS** (Linear B → Greek `Z = +7.97, p = 0.00010`; Semitic `p = 0.111`) | 10,000 consonant-grid swaps + 11-way ablations | **Semitic wins** (`ΔLL = +13.58`, **~794,000:1 BF**, `Z = +7.37`, `p = 0.00010`; `NO_LOANS_5` ~1,860:1; `ARITH_2` `p = 0.00640`) | Curated equal-size synsets (audited blind by Kernel J) |
| **E. Verbal Edge-Frames** | `verbs_e.py` | **YES** | 5/5 (100%) dev calibration | Consonant-grid swaps | Semitic verbs #1 (`M = +1.056`, `Z = +0.85`, `p = 0.208`) | Positive direction, underpowered at `n = 46` votive words |
| **F. Ligature Acrophony** | `acrophony_f.py` | **YES** | **PASS** (Linear B → Greek `Z = +4.31, p = 0.00070`; Semitic `p = 0.362`) | 10,000 consonant-grid swaps | **Semitic wins** (`ΔLL = +28.17`, `Z = +5.53`, `p = 0.00010`) | Curated single-syllable qualifier synsets; auxiliary channel |
| **G. Palaikastro Dialect** | `dialect_g.py` | **YES** | 10,000 random 4-rule bundles | Random 4-rule phonological bundles | **5/5 pairs match** NWS isogloss bundle (`p = 0.00010`) | Small sample (`n = 5` minimal pairs) |
| **H. Roster Onomastics** | `onomastics_h.py` | **YES** | Size-equalized (`1,314`/arm) | Consonant-grid swaps | Mycenaean LB #1 (`5.88`), **ORACC Levant Semitic #2** (`6.14`, `Z = +1.56, p = 0.065`, ahead of Kassite `6.93`, Hurr `7.19`, Anat `7.43`) | Shared Cretan onomastic layer carried into Knossos Linear B |
| **I. Bound Affix Morphology** | `morphology_i.py` | **YES** | **PASS** (7/7 dev `p = 0.00050`; Linear B → Greek `M = +472.95, p_M = 0.02679`, Semitic `p_M = 0.875`) | 5,000 **discriminative margin** consonant-grid swaps + 5-seed × (`omission`, `plene`) sweep | **Semitic wins** (standalone ANE Semitic: **`M = +40.03, Z_M = +2.63, p_M = 0.00360, p_cv = 0.00040`**; full 7-member Semitic 5/5 seeds `mean p_M = 0.0385`) | Uses inflected Diodorus Greek; `plene` mode weakens `p_M` (consistent with Linear A's coda-omission orthography) |
| **J. Zero-Curation Dict Audit** | `auto_anchors_j.py` | **YES** | **PASS** (LB `n=6`: Greek `0.00010/0.01389`; `EXT9`: `481:1`, `0.00010/0.00020`; Sem `0.115/0.293`) | 10,000 consonant-grid swaps **AND** concept-label shuffle (`5,040` exact / `10k` MC) | **Semitic wins** (`FULL_8` `p_c=0.02520`; `DEDUP_7` `0.01111`; **purest strict-LB `DEDUP_9` incl. blind `DA-RO-PA`: `47.6:1, p_perm=0.00010, p_c=0.00390`**; sensitivity `+PA₃` `DEDUP_12` `66.7:1, p_c=0.00180` & `DEDUP_14` `101.8:1, p_perm=0.00020, p_c=0.00920`; `K`-free `5` `p_perm=0.01640`, `p_c=0.217`; Greek `0.63–0.79`, Sumerian `0.62–0.86`) | `DEDUP_12`/`14` explicitly fold opaque GORILA doublet `AB 56/PA₃`; single-syllable `--ligatures` saturates open dicts |
| **K. Corazza–Ferrara Fractions** | `fractions_k.py` | **YES** | **PASS** (LB `TO-SO/O-PE-RO` Greek `Z=+2.48, p=0.01440`; Sem `0.401`) | 5,000 consonant-grid swaps + language-free metrology (`1,719` recs) | `0` Corazza `>1` violations (`55` compounds); blind `KU-RO` #1 (`9` sums); **dedup `KU-RO/KI-RO` Semitic #1** (`Z=+3.15, p=0.01480, ΔLL=+1.190`; LSJ Greek rejected `0.0544`) | Targeted `n=2–3` accounting bridge + 5-item 3D/RTI conflict ledger |
| **L. Backward-Projection Audit** | `homomorph_l.py` | **YES** | **PASS** (LB L3 `100%` at `ε=0.2–0.3`; L4 LB ligatures fail `p=0.395`) | SigLA invariance, 12 single-series drops, D/J L1SO, `ε=0.1–0.5` corruption, L4 nulls | **SigLA sole pass** (`p_M=0.0020`); **`10/12`** I single drops (`drop T` #1 collapse `p=0.265`); `8/8` D & `7/7` J L1SO `p_perm<=0.05`; at `ε=0.2` D `99.67%` (`90% p<=0.05`) & I `86%` | Logs 11-sign core power floor (`30` tokens) & 3 calibrated negative controls |

---

## 3. Running Out-of-the-Box on Any Fresh `kaphtor` Clone

All twelve kernels run directly from the shipped, open-licensed inputs in `data/` with zero external folders:

```bash
# 1. Full kernel unit test suite (32) + shipped-input count guards (8) = 40 total
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=models/language-id-kernel uv run --no-sync python -m pytest -q models/language-id-kernel/tests/ tests/test_kernel_shipped_inputs.py

# 2. Unified Kernels A + B + C + D (manifest, calibration gate, signed Linear A run)
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py manifest
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py calibrate --n-perm 10000
uv run --no-sync python models/language-id-kernel/liturgy_c.py --run-linear-a --n-perm 1000

# 3. Kernels D, F, G (Anchors, Ligature Acrophony, Palaikastro Dialect)
uv run --no-sync python models/language-id-kernel/anchors_d.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/acrophony_f.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/dialect_g.py --n-perm 10000

# 4. Kernels E, H, I, J, K, L (Verbal Frames, Onomastics, Bound Morphology, Zero-Curation Dicts, Fractions, Stress-Test)
uv run --no-sync python models/language-id-kernel/verbs_e.py --n-perm 500
uv run --no-sync python models/language-id-kernel/onomastics_h.py --n-perm 1000
uv run --no-sync python models/language-id-kernel/morphology_i.py --mode omission --n-perm 5000
uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000 --seed 20261125
uv run --no-sync python models/language-id-kernel/fractions_k.py --n-perm 5000
uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage all --n-perm 1000 --trials 300
```

### Shipped Inputs & Optional Override Environment Variables

| Environment Variable | Shipped Default | Used By | Purpose |
|---|---|---|---|
| `KAPHTOR_CORPUS_JSON` | `data/linear-a/corpus.json` *(CC BY-NC-SA 4.0)* | `kaphtor_kernel.py`, `verbs_e.py`, `onomastics_h.py` | GORILA/SigLA Linear A corpus |
| `KAPHTOR_LSJ_JSONL` | `data/share-alike/greek/lsj_lb_keys.jsonl` *(CC BY-SA 4.0)* | `lid.py` | LSJ Greek headwords in Linear B spelling (117,130) |
| `KAPHTOR_LSJ_GLOSSES_JSONL` | `data/share-alike/greek/lsj_glosses.jsonl` *(CC BY-SA 4.0)* | `auto_anchors_j.py` | LSJ Linear B keys + primary glosses (101,410) |
| `KAPHTOR_DIODORUS_XML` | `data/share-alike/greek/diodorus_1_5.jsonl` *(CC BY-SA 4.0)* | `lid.py`, `liturgy_c.py`, `verbs_e.py`, `morphology_i.py` | Perseus inflected running Greek text (Diodorus Books 1–5) |
| `KAPHTOR_LINEAR_B_JSONL` | `data/share-alike/linear-b/linear_b_tokens.jsonl` *(CC BY-NC-SA 4.0)* | `render/c_texts.py`, `lid.py`, `onomastics_h.py`, `morphology_i.py` | Pylos/Knossos syllabic tokens verified against DAMOS |
| `KAPHTOR_OSHB_JSONL` | `data/share-alike/hebrew/oshb_words.jsonl` *(CC BY 4.0)* | `render/c_texts.py`, `lid.py`, `liturgy_c.py`, `verbs_e.py` | Open Scriptures Hebrew Bible pointed Hebrew/Aramaic words |
| `KAPHTOR_EUPT_JSONL` | `data/share-alike/ugaritic/eupt_tokens.jsonl` *(CC BY-SA 4.0)* | `render/c_texts.py`, `lid.py` | EUPT vocalized Ugaritic tokens |
| `KAPHTOR_LATIN_CSV` | `data/share-alike/latin/latinf_forms.jsonl` *(CC BY-SA 4.0)* | `lid.py`, `verbs_e.py`, `morphology_i.py` | LiLa LatInfLexi inflected Latin control |
| `KAPHTOR_TLHDIG_JSONL` | `data/share-alike/anatolian/tlhdig_docs.jsonl` *(CC BY 4.0)* | `render/c_texts.py`, `lid.py`, `liturgy_c.py`, `verbs_e.py`, `onomastics_h.py`, `morphology_i.py` | TLHdig 0.3 Hittite, Luwian, Hurrian, Hattic and Boğazköy Akkadian documents |
| `KAPHTOR_ORACC_DIR` | `data/share-alike/cuneiform` *(CC0 1.0)* | `lid.py`, `liturgy_c.py`, `morphology_i.py` | ORACC CC0 Old/Standard Babylonian Akkadian and Sumerian documents |
| `KAPHTOR_SUMERIAN_LEXICON_JSONL` | `data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl` *(CC0 1.0)* | `auto_anchors_j.py` | Clean vocalized Sumerian ePSD2 glossed lexicon (3,589 lemmas) |
| `KAPHTOR_CONTACT_DIR` | `data/contact` *(open Semitic lexica)* | `auto_anchors_j.py` | Akkadian and Hebrew open lexica (override to add private Ugaritic/Anatolian/Hurrian/Egyptian JSONLs) |
| `KAPHTOR_ORACC_LEVANT_NAMES` | `data/share-alike/oracc-levant/name_occurrences.jsonl` *(CC BY-SA 3.0)* | `onomastics_h.py` | LBA Levant personal/royal names (Ugarit, Amarna, Alalakh) |
| `KAPHTOR_KASSITE_NAMES` | `data/ane/kassite-concordances/entries.jsonl` *(Public Domain)* | `onomastics_h.py` | Kassite-period personal names (Clay/Hinke/Radau/King) |
| `KAPHTOR_ANE_DIR` | *(optional — unset by default)* | `lid.py`, `liturgy_c.py` | Optional non-shipped extras (TraCES Geʿez CC BY-NC-ND, Quran, Ephrem Syriac, Urartian) |
| `KAPHTOR_AMORITE_ONOMASTICON` | *(optional — unset by default)* | `onomastics_h.py` | Optional Gelb/Huffmon Amorite personal-name list |
