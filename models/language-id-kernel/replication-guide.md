---
name: models/language-id-kernel/replication-guide
title: "Replication & Objectivity Guide (Kernels A–J)"
desc: "Master scoreboard, objectivity audit, external-corpus environment variables, and zero-dependency reproduction instructions for all ten probabilistic language-identification kernels."
tags: [linear-a, probabilistic-model, replication, preregistration]
created: 2026-11-23T00:00:00Z
updated: 2026-11-23T14:36:00Z
---

# Replication & Objectivity Guide (Kernels A–J)

[[models/language-id-kernel/_index|..]]

This guide documents how to replicate every kernel in `models/language-id-kernel/`, what runs with zero external dependencies on a fresh `kaphtor` clone, which environment variables configure optional external reference corpora, and the exact objectivity and calibration boundaries of all ten kernels.

---

## 1. Anti-Circularity & Objectivity Guarantees

1. **Zero project-lexicon leakage:** No script in `models/language-id-kernel/` reads `lexicon.json`, `translations.json`, or `onomasticon.json`. Every Linear A target is read strictly from `data/linear-a/corpus.json` (GORILA/SigLA transliterations) using only agreed Linear B sign values (`render/series.json`).
2. **Zero LLMs & 100% deterministic:** All ten kernels run in pure Python with fixed PRNG seeds (`seed = 20261122` / `20261123`). Rerunning any command reproduces the JSON ledgers in `runs/` bit-for-bit.
3. **Mandatory known-language calibration gates:** Every primary or high-impact kernel is first calibrated on known ancient languages (including real Linear B tablets, where **Greek** must win and **Semitic** must be rejected) before scoring Linear A.
4. **Honest negative/weak reporting:** Kernels whose raw-bit lead is driven by `/a, i, u/` vowel-core macro-typology rather than consonant identity (**A, B**) are explicitly labeled as typological (`Z_perm < 0`), not consonant-specific proof.

---

## 2. Ten-Kernel Master Scoreboard (Strict Linear B Values Only)

| Kernel | Script | Zero-Dep on Clone? | Calibration Gate | Null Model(s) | Linear A Result | Honest Scope / Caveat |
|---|---|---|---|---|---|---|
| **A. Word-Shape LID** | `lid.py` + `pilot_fix1.py` | Needs `KAPHTOR_ANE_DIR` | Linear B → Greek (1.0/1.0) | Consonant-grid swaps | Semitic #1 (`M = +0.623` bits/sign, `Z_perm = -0.21`) | Vowel-core `/a, i, u/` typology |
| **B. Unsupervised Kober Trios** | `kober_b.py` | Needs `KAPHTOR_ANE_DIR` | 62/62 (100%) dev accuracy | Consonant-grid swaps | Semitic #1 (`M = +2.288` bits/tr, `Z_perm = -1.09`) | Vowel-core `/a, i, u/` typology |
| **C. Liturgical Cohesion** | `liturgy_c.py` | Needs `KAPHTOR_ANE_DIR` | 104 Protocol D v3 controls (Heb +2.15, FAB 0/10) | Size-locked `K=300` + consonant swaps | `IO Za 2`: Heb #1 (`Z = +2.91–+3.05`, `p = 0.027–0.032`); 33-vessel family (`n=41`): Heb #1 (`p = 0.231`) | Strong on `IO Za 2`, weaker diluted across all 41 formula words |
| **D. Pre-Linguistic Anchors** | `anchors_d.py` | **YES** | **PASS** (Linear B → Greek `Z = +7.97, p = 0.00010`; Semitic `p = 0.111`) | 10,000 consonant-grid swaps + 11-way ablations | **Semitic wins** (`ΔLL = +13.58`, **~794,000:1 BF**, `Z = +7.37`, `p = 0.00010`; `NO_LOANS_5` ~1,860:1; `ARITH_2` `p = 0.00640`) | Curated equal-size synsets (audited blind by Kernel J) |
| **E. Verbal Edge-Frames** | `verbs_e.py` | Needs `KAPHTOR_ANE_DIR` | 5/5 (100%) dev calibration | Consonant-grid swaps | Semitic verbs #1 (`M = +1.056`, `Z = +0.85`, `p = 0.208`) | Positive direction, underpowered at `n = 46` votive words |
| **F. Ligature Acrophony** | `acrophony_f.py` | **YES** | **PASS** (Linear B → Greek `Z = +4.31, p = 0.00070`; Semitic `p = 0.362`) | 10,000 consonant-grid swaps | **Semitic wins** (`ΔLL = +28.17`, `Z = +5.53`, `p = 0.00010`) | Curated single-syllable qualifier synsets; auxiliary channel |
| **G. Palaikastro Dialect** | `dialect_g.py` | **YES** | 10,000 random 4-rule bundles | Random 4-rule phonological bundles | **5/5 pairs match** NWS isogloss bundle (`p = 0.00010`) | Small sample (`n = 5` minimal pairs) |
| **H. Roster Onomastics** | `onomastics_h.py` | Needs `KAPHTOR_AMORITE_ONOMASTICON` | Size-equalized (`1,200`/arm) | Consonant-grid swaps | Mycenaean LB #1 (`6.07`), **Amorite #2** (`6.75`, `Z = +1.30`, ahead of Hurr `7.09`, Anat `7.27`) | Shared Cretan onomastic layer |
| **I. Bound Affix Morphology** | `morphology_i.py` | Needs `KAPHTOR_ANE_DIR` + `KAPHTOR_DIODORUS_XML` | **PASS** (7/7 dev `p = 0.00050`; Linear B → Greek 5/5 seeds, `p_M = 0.0015–0.0485`; Semitic `p_M = 0.919`) | 5,000 **discriminative margin** consonant-grid swaps + 5-seed × (`omission`, `plene`) sweep | **Semitic wins 5/5 seeds (`omission`)** (`mean M = +32.35`, `mean p_M = 0.0385`; wins both votive `M = +5.04` and admin `M = +13.56, p_M = 0.049`) | Requires inflected Greek running text; `plene` mode weakens `p_M` (consistent with Linear A's coda-omission orthography) |
| **J. Zero-Curation Dict Audit** | `auto_anchors_j.py` | Needs `KAPHTOR_CONTACT_DIR` | **PASS** (Linear B → Greek `p_perm = 0.00010`, `p_concept = 0.01250`; Semitic `0.231` / `0.693`) | 10,000 consonant-grid swaps **AND** exact concept-label shuffle (`5,040` perms) | **Semitic wins** (`Z_perm = +4.85, p_perm = 0.00010`; `Z_concept = +2.51, p_concept = 0.00893`, **only pass**; Greek `p_concept = 0.548`) | Anatolian/Hurrian/Egyptian contact JSONLs are sparser than Semitic & Greek LSJ (complemented by Kernel D); single-syllable `--ligatures` saturates an open 40-word dictionary (confirming multi-syllable anchors as primary) |

---

## 3. Running Out-of-the-Box vs. External Reference Corpora

### Zero-Dependency Commands (Work on Any Fresh `kaphtor` Clone)

```bash
# 1. Full unit test suite (21 tests, <2 s, zero external corpora required)
PYTHONPATH=models/language-id-kernel uv run pytest -q models/language-id-kernel/tests/

# 2. Kernel D: Linear B calibration gate + Linear A FULL_8 + 11-way ablations (10,000 perms)
PYTHONPATH=models/language-id-kernel python3 models/language-id-kernel/anchors_d.py --calibrate --run-linear-a --n-perm 10000

# 3. Kernel F: Commodity ligature acrophony (Linear B gate + Linear A, 10,000 perms)
PYTHONPATH=models/language-id-kernel python3 models/language-id-kernel/acrophony_f.py --calibrate --run-linear-a --n-perm 10000

# 4. Kernel G: Palaikastro dialect sound-law coherence (10,000 random 4-rule bundles)
PYTHONPATH=models/language-id-kernel python3 models/language-id-kernel/dialect_g.py --n-perm 10000
```

### Environment Variables for External Reference Corpora

| Environment Variable | Default | Used By | Purpose |
|---|---|---|---|
| `KAPHTOR_CORPUS_JSON` | `data/linear-a/corpus.json` *(shipped)* | `kaphtor_kernel.py`, `verbs_e.py`, `onomastics_h.py` | GORILA/SigLA Linear A corpus |
| `KAPHTOR_CONTACT_DIR` | `data/contact` *(shipped subset)* | `auto_anchors_j.py` | Glossed contact JSONL lexica (Akkadian, Ugaritic, Hebrew, Greek LSJ, Anatolian, Hurrian, Egyptian) |
| `KAPHTOR_DIODORUS_XML` | `tlg0060.tlg001.perseus-grc5.xml` | `lid.py`, `morphology_i.py` | Perseus inflected running Greek text (Diodorus Siculus) |
| `KAPHTOR_ANE_DIR` | `~/.claude/skills/ancient-near-east-research/data` | `render/c_texts.py`, `lid.py`, `kober_b.py`, `liturgy_c.py`, `verbs_e.py`, `morphology_i.py` | OSHB Hebrew, EUPT Ugaritic, TLHdig Anatolian/Hurrian/Hattic, ORACC Akkadian/Sumerian, Quran, TraCES Geʿez, Ephrem Syriac |
| `KAPHTOR_LSJ_JSONL` | `~/.claude/skills/linear-a-decipherment/data/contact/greek_lexicon.jsonl` | `lid.py` | LSJ Greek headword lexicon |
| `KAPHTOR_LINEAR_B_JSONL` | `~/.claude/skills/linear-a-decipherment/data/linear_b_token_occurrences.jsonl` | `render/c_texts.py` | DAMOS Linear B tablet corpus |
| `KAPHTOR_AMORITE_ONOMASTICON` | `amorite_onomasticon.jsonl` | `onomastics_h.py` | Gelb/Huffmon Amorite personal names |
| `KAPHTOR_LATIN_CSV` | `LatInfLexi-forms.csv` | `lid.py` | LiLa LatInfLexi inflected Latin control |
