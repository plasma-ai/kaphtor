---
name: models/cypro-minoan-kernel/README
title: "Cypro-Minoan Deterministic Statistical Kernel Suite (CM-G, CM-E, CM-O, CM-B)"
desc: "Zero-LLM, T5-compliant statistical kernel suite for Cypro-Minoan running strictly on shipped kaphtor datasets with V-vs-CV permutation nulls, 3-regime 013/008 sensitivity, and CM 3 / Linear B controls."
tags: [cypro-minoan, probabilistic-model, eteocypriot, readme]
created: 2026-11-25T13:25:00Z
updated: 2026-11-25T18:21:23Z
---

# Cypro-Minoan Deterministic Statistical Kernel Suite (CM-G, CM-E, CM-O, CM-B)

Using **zero LLMs**, **zero external folders**, and **zero Linear A inputs** (strict T3 isolation—no file under `data/linear-a/` is ever read), `models/cypro-minoan-kernel/cm_kernel.py` runs four deterministic, seed-locked statistical kernels directly on shipped `kaphtor` datasets (`data/ane/cypro-minoan/`, `data/ane/ig-xv-1-cypriot/records.jsonl`, and `data/share-alike/linear-b/linear_b_tokens.jsonl`).

All inputs are T5-compliant (published CC BY 4.0 readings and metadata only; zero raw Valério 2016 Appendix A sign-group transcriptions and zero canonical §7 held-out texts).

## Scoreboard (Pinned Ledger: `runs/cm-kernel-2026-11-25.json`, `B = 2,000`, `seed = 20261125`)

| Kernel | Test & Corpus | Observed | Strict Null (`p_vcv` / exact) | Controls & Sensitivity |
| --- | --- | --- | --- | --- |
| **CM-G** | Subcorpus word-final cosine vs. *IG XV 1* Amathus EC (`92` confirmed types) | CM 1+2 `0.7906`; CM 1 `0.7297`; CM 2 `0.6043` | CM 1+2 **`p_vcv = 0.0005`**; CM 2 `p_vcv = 0.0125`; CM 1 `p_vcv = 0.0740` | CM 3 (Ugarit) `0.3655` (`p_vcv = 0.3498`); Linear B Greek `0.370` (`median p_vcv = 0.2834`) |
| **CM-E** | 3-regime `013`/`008` alignment vs. Amathus EC (`92` confirmed / `66` undotted) | Valério: `3` exact (`a-na`, `ta-na`, `ta-ra-wo`), `9` `suf2`, `2` `csk` stems (`3` forms); Davis: `11` `suf2`, `end1_cos = 0.8147` | Valério undotted: `suf2` **`p_vcv = 0.0285`**, `csk_forms` **`p_vcv = 0.0135`**, `end1_cos` **`p_vcv = 0.0010`**; Davis confirmed: `suf2` **`p_vcv = 0.0110`**, `end1_cos` **`p_vcv = 0.0005`** | HoChyMin unsplit (`013 = to`) collapses (`end1_cos = 0.6473, p_vcv = 0.0580`; `csk_stems = 1, p_vcv = 0.4073`; `exact = 1`); CM 3 `0` stems (`p = 1.0`); Linear B `suf2` `median p_vcv = 0.5070`, `csk_stems` `1.0000` |
| **CM-O** | Orthographic glide enrichment (`-Ci-jV-`, `-Cu-wV-`) & bare-vowel final rate | Pan-CM: `Ci→jV` `23.50%`, `Cu→wV` `14.91%`, bare `V` final `2.47%` vs. `CV` `36.76%` | Exact binomial vs. non-`i`/non-`u`: **`p = 3.152e-26`** (`Ci→jV`), **`p = 4.440e-7`** (`Cu→wV`) | CM 2 only: `Ci→jV` `26.67%` (`p = 4.328e-13`), `Cu→wV` `23.19%` (`p = 4.597e-6`), bare `V` final `0.00%` |
| **CM-B** | Unsupervised 1-syllable stem-extension containment (`N = 299` attested CM 1+2 types) | `27` suffix-extension pairs vs. `10` prefix-extension pairs (top suffixes: `-na`, `-no`, `-ti` [4 each], `-ta`, `-to` [2 each]) | Position-preserving initial/medial/final shuffle (`B = 1,000`): **`p_suffix = 0.0010`** (null `12.08`) vs. `p_prefix = 0.3167` (null `8.37`) | Confirms suffixing morphological typology independent of Eteocypriot comparanda |

## Methodological & Epigraphic Controls

1. **Amathus *IG XV 1* strict filter (`parse_ig_amathus`):** Selects strictly Amathus Eteocypriot parts from `data/ane/ig-xv-1-cypriot/records.jsonl`, excludes non-Amathus sites (Kurion, Marion, unprovenanced `IG XV 1, 16`), excludes tentative attributions (`IG XV 1, 12`, `language_label_basis == "tentative"`) and direction-doubtful inscriptions (`←?` / `→?`), rejects lacuna-adjacent fragments (`]` / `[`), and restores EpiDoc `<lb/>` boundaries to yield exactly **`92` confirmed** (`90` `L >= 2`, `71` `L >= 3`) and **`66` strictly undotted** (`64` `L >= 2`, `50` `L >= 3`) word types.
2. **V-vs-CV class-preserving + vowel-preserving null (`p_vcv`):** Keeps bare vowels (`a, e, i, o, u`) separate from `CV` signs within each vowel row during permutation, preventing word-initial bare-vowel enrichment from inflating false-positive significance.
3. **Synthetic-stem exclusion & `013`/`008` regime sensitivity:** Excludes synthetic `paradigm_stem` rows (`entry_kind == "paradigm_stem"`) so every counted CM type is a genuinely attested read word, and tests all three `013`/`008` regimes (Valério emended, Davis unsplit `013 = na`, HoChyMin unsplit `013 = to` on CM 2 emendations).
4. **Honest ceiling:** Under the strict `V`-vs-`CV` null, deduplicated `L >= 3` consonant-skeleton stems (`csk_stems = 2` on **`ta-ra-*`** [`ta-ra-we`, `ta-ra-wo`] and **`a-sa-*`** [`a-sa-na` ↔ Amathus `a-so-na`]) do not reach `p < 0.05` (`p_vcv = 0.1144` confirmed / `0.0920` undotted). The strongest statistically calibrated CM 1+2 ↔ Amathus Eteocypriot continuity lies in **word-final morphology** (`end1_cos = 0.7906, p_vcv = 0.0005`; undotted `shared_suf2 = 9, p_vcv = 0.0285`) paired with the **negative collapse** of HoChyMin unsplit, CM 3 (Ugarit), and DAMOS Linear B Greek.

## Quick Reproduction (Fresh Clone, Zero External Folders)

```bash
# 1. Verify shipped input SHA-256 manifest and pinned run ledger
PYTHONDONTWRITEBYTECODE=1 python3 models/cypro-minoan-kernel/cm_kernel.py manifest
PYTHONDONTWRITEBYTECODE=1 python3 models/cypro-minoan-kernel/cm_kernel.py check --ledger models/cypro-minoan-kernel/runs/cm-kernel-2026-11-25.json

# 2. Run unit tests + CI guard tests
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -m pytest -q models/cypro-minoan-kernel/tests/ tests/linear_a/test_cypro_minoan_kernel.py

# 3. Re-run the full 4-kernel suite from scratch (cross-process deterministic, seed=20261125)
PYTHONDONTWRITEBYTECODE=1 python3 models/cypro-minoan-kernel/cm_kernel.py run --perms 2000 --lb-draws 20 --out models/cypro-minoan-kernel/runs/cm-kernel-2026-11-25.json
```
