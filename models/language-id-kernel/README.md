---
name: models/language-id-kernel/README
title: "Twelve-Kernel Probabilistic Language Identification Suite (Kernels A–L)"
desc: "Executive summary, full twelve-kernel scoreboard, fresh-clone replication guide, Bologna adversarial vetting protocol, and index to all per-kernel specifications."
tags: [linear-a, probabilistic-model, language-identification, readme]
created: 2026-11-23T20:42:00Z
updated: 2026-11-25T15:35:00Z
---

# Twelve-Kernel Probabilistic Language Identification Suite (Kernels A–L)

<p align="center">
  <img src="../../assets/language-id-kernel-banner.png" width="100%"
       alt="Kaphtor Twelve-Kernel Linear A suite (Kernels A–L): 10/11 scoring kernels rank Semitic #1 plus Kernel L backward-projection stress-testing and negative controls using strict Linear B values and zero LLMs (Kernel D 794,000:1, Kernel J p=0.025 vs ePSD2 Sumerian 0.64 &amp; LSJ Greek 0.59, Kernel I p=0.0036, Kernel K blind KU-RO p=0.0128). All calibrated kernels pick Greek on Linear B.">
</p>

## Executive Summary (Run Snapshot: `2026-11-25`, `kaphtor v1.3.2`)

Using **agreed Linear B sign values alone**, **zero LLMs**, and **zero project-lexicon inputs** (`lexicon.json`, `translations.json`, and `onomasticon.json` are never read), this twelve-kernel suite tests Linear A (`data/linear-a/corpus.json`) against seven ancient language families and isolates (**Semitic, Greek, Anatolian, Hurrian, Hattic, Sumerian, Latin**, plus **Kassite** onomastics). Every kernel runs end-to-end from a fresh `git clone` with zero external folders.

### Headline Findings

- **10 of 11 scoring kernels rank Semitic #1** (the eleventh, Kernel H on personal-name rosters, ranks shared Cretan Mycenaean Linear B #1 and LBA Levantine Semitic #2 ahead of Kassite, Hurrian, and Anatolian), while **Kernel L** audits the suite against backward-projection error and logs honest negative controls.
- **Seven scoring channels pass consonant-specific nulls** (where vowels, word lengths, and frequencies stay fixed while the 12 consonant series or concept labels are scrambled—note that **Kernels D, J, and K** are nested/alternative audits over overlapping pre-linguistic anchors alongside disjoint channels **I, F, G, and C**), while **every calibrated instrument first identifies real Mycenaean Linear B tablets as Greek and rejects Semitic**:
  1. **Kernel D—Pre-Linguistic Anchors (`anchors_d.py`):** **Semitic wins at ~794,000 : 1 Bayes factor** (`ΔLL = +13.585`, `Z_perm = +7.37`, `p = 0.00010`, `0/10,000` swaps). Survives all 8 leave-one-out drops (`p = 0.00010`), dropping all 3 trade-loan suspects (`~1,860 : 1`, `Z = +6.22`), and pure arithmetic `KU-RO`/`KI-RO` alone (`p = 0.00640`). *Linear B gate:* Greek `Z = +7.97, p = 0.00010`; Semitic rejected (`p = 0.111`).
  2. **Kernel J—Zero-Curation Dictionary Audit (`auto_anchors_j.py`):** Eliminates all hand-picked synsets by running fixed English concept regexes over shipped open dictionaries (Akkadian/Hebrew, 101,410-entry LSJ Greek, and 3,589-lemma CC0 ePSD2 Sumerian isolate). **Semitic is the only language passing both orthogonal nulls** across every primary tier: signed `FULL_8` (`ΔLL = +4.054`, `57.6:1`, `p_perm = 0.00010`, exact `p_concept = 0.02520` standalone / `0.00893` pre-Sumerian 5-lang), deduplicated `LA_DEDUP_7` (`ΔLL = +4.342`, `76.9:1`, `p_concept = 0.01111`), and purest strict-`signs-a5-proposed.json` `LA_DEDUP_9` (`+ PA-TA-QE` on `HT 31 *402-VS` and **blind untranslated `DA-RO-PA`** on `HT 38 *403-VS`: **`ΔLL = +3.863`, `47.6:1`, `p_perm = 0.00010`, `p_concept = 0.00390`**; Greek `0.626`, Sumerian `0.663`). Sensitivity tiers: folding GORILA doublet `AB 56` (`PA₃ → PA`, kept opaque in `signs-a5-proposed.json` §15 ruling 3) on `HT 31`'s three `PA₃` vessel drawings sharpens `LA_DEDUP_12` to **`ΔLL = +4.200`, `66.7:1`, `p_perm = 0.00010`, `p_concept = 0.00180`** (Greek `0.633`, Sumerian `0.856`); adding `PA-RA` (`HT 128a` header) and the `MA+RU` (`LANA`) wool monogram yields `LA_DEDUP_11` (`72.6:1`, `p_perm = 0.00010`, `p_concept = 0.01560`) and `LA_DEDUP_14` (`+ PA₃` fold: `101.8:1`, `p_perm = 0.00020`, `p_concept = 0.00920`), while `K`-free `LA_DROPK_5` passes consonant-grid permutation (`p_perm = 0.01640`, underpowered on concept-shuffle `p_concept = 0.217` at `n = 5`). *Linear B gate:* Greek only dual-null pass (`n = 6`: `0.00010 / 0.01389`; `EXT9`: `ΔLL = +6.177`, `481:1`, `0.00010 / 0.00020`; Semitic rejected `0.115 / 0.293`).
  3. **Kernel I—Unsupervised Bound-Affix Morphology (`morphology_i.py`):** Lexicon-free stem-containment grammar (`S` vs `p+S`/`S+s`) scored under a discriminative margin-permutation null that cancels universal suffix consonants. **Semitic is the only pass** on shipped ANE Semitic (`M = +40.03`, `Z_M = +2.63`, `p_M = 0.00360`, `p_cv = 0.00040`; 5/5 seeds `mean p_M = 0.0385` on the full 7-member arm). *Linear B gate:* Greek only pass (`M = +472.95, p_M = 0.02679`; Semitic `0.875`); 7/7 dev splits pass (`p_cv = 0.00050`).
  4. **Kernel K—Corazza–Ferrara Fractions & Blind Accounting (`fractions_k.py`):** Applies Corazza et al. (2021, *JAS* 125: 105214) `A700` fraction values directly to raw Aegean Unicode numerals (`data/linear-a/corpus.json`): verifies **`0` strict `> 1` compound-fraction violations** across `55` compound fractions (resolving `HT 27a` `JE+B = 19/20`, vs Bennett legacy `13/12 > 1`), emits a 5-item language-free 3D/RTI conflict ledger (`HT 123+124a`, `KH 7a`/`HT 89`, `MA 10b`, `A709/L`), blindly discovers **`KU-RO` at rank #1 (`9` exact integer sums vs `<= 1` for any other token)**, and scores *only* accounting words against Kernel J's open dictionaries—on the deduplicated pair (`KU-RO`, `KI-RO`), **Semitic wins cleanly (`Z = +3.15, p = 0.01480, ΔLL = +1.190`) and rejects LSJ Greek (`p = 0.05439`)** (full triad `KU-RO/PO-TO-KU-RO/KI-RO` also ranks Semitic #1 at `Z = +2.86, p = 0.01280, ΔLL = +0.551`). *Linear B gate (`TO-SO`, `O-PE-RO`):* Greek `Z = +2.48, p = 0.01440`; Semitic rejected (`p = 0.40132`).
  5. **Kernel F—Commodity Ligature Acrophony (`acrophony_f.py`):** **Semitic wins** (`ΔLL = +28.17`, `Z_perm = +5.53`, `p = 0.00010`). *Linear B gate:* Greek `Z = +4.31, p = 0.00070`; Semitic `p = 0.362`. *(Auxiliary channel; see Stage L4 saturation boundary.)*
  6. **Kernel G—Palaikastro Dialect Coherence (`dialect_g.py`):** **5 / 5** Central Crete ↔ Palaikastro minimal pairs match a 4-rule NWS isogloss bundle (`Z_perm = +50.05`, `p = 0.00010` vs 10,000 random 4-rule bundles).
  7. **Kernel C—Size-Locked Liturgical Cohesion (`liturgy_c.py`):** On `IO Za 2`, **`hebrew_lit` ranks #1** (`Z = +3.04, p = 0.02697`) and sister Semitic **`akkadian_lit` ranks #2** (`Z = +1.67, p = 0.06294`), ahead of Hurrian, Anatolian, and Greek.
- **Adversarial Stress-Testing & Negative Controls (`Kernel L`, `homomorph_l.py`):** Operationalizes Steele & Meißner (2017) and Salgarella (2020) backward-projection caution alongside Valério & Ferrara (2020) and Ferrara, Montecchi & Valério (2022) on CH↔LA continuity: on Salgarella & Castellan's independent **SigLA word segmentation (`sigla_db.json`)**, Semitic is the **sole pass** (`M = +35.12, Z_M = +2.66, p_M = 0.00200`; all 6 rivals `0.172–1.000`); across **all 12 single-series drops** on Kernel I, **`10/12` pass `p_M <= 0.05`** (`drop T` is the #1 deepest collapse at `p_M = 0.26547`—Semitic `t-`/`-t`); dropping contested `Q+Z` strengthens Kernel I (`M = +44.33, p_M = 0.00200`); **`8/8`** Kernel D and **`7/7`** Kernel J L1SO drops pass `p_perm <= 0.05` (Kernel J dual-null `p_concept` `2/7`, `drop K` leaves `n = 1` in J vs `n = 3` in D and `M = +47.30` in I); under `20%` / `30%` random consonant-series corruption, Kernel D Semitic holds **`99.67%`** / **`95.67%`** rank-1 (**`90%`** / **`80%`** `p_perm <= 0.05`) and lexicon-free Kernel I holds **`86%`** / **`70%`** rank-1; and Stage L4 explicitly logs calibrated nulls (Kernels A/B `Z_perm < 0`, CH→LA acrophony `3/20, p ≈ 0.31`, and live Linear B single-sign open-dictionary ligature saturation `p = 0.39521`).
- **Joint Primary Stouffer Meta-Z (`A + B + D`):** **`+3.504` (`p = 0.00023`)**, while honestly classifying **Kernels A & B** as `/a, i, u/` vowel-core macro-typology (`Z_perm < 0`) rather than consonant-specific proof.

For more—including the `2026-11-24` Kernel K & L analysis, a five-command adversarial vetting protocol, and the full ten-kernel baseline—see **[Significance & Interpretation (`2026-11-24`)](results-significance-2026-11-24.md)**, **[Bologna Adversarial Vetting Guide](ferrara-vetting-guide.md)**, and **[Baseline Significance Report (`2026-11-23`)](results-significance-2026-11-23.md)**.

### All Twelve Kernel Scores at a Glance (`2026-11-24`)

| Kernel | Channel | Linear B / Dev Gate | Linear A Winner | Semitic Score & Margin | Null Test(s) | Signal Class | Deep Dive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A. Word-Shape LID** | 505 strict-LB types | LB → Greek `1.0/1.0` | **Semitic (#1)** | `5.490` bits/sign (`M = +0.623` vs Hurrian) | `Z_perm = -0.21, p = 0.587` | Vowel-core macro-typology | [a-word-shape.md](kernels/a-word-shape.md) |
| **B. Kober Trios** | Stem-sharing pairs/trios | `62/62` (100%) dev | **Semitic (#1)** | `22.362` bits/tr (`M = +2.288` vs Hurrian) | `Z_perm = -1.09, p = 0.846` | Syllabic macro-typology | [b-kober-trios.md](kernels/b-kober-trios.md) |
| **C. Liturgical Cohesion** | `IO Za 2` (`K=300`) | 104 Protocol D controls | **`hebrew_lit` (#1)**, `akkadian_lit` (#2) | `score = 0.1020` (`akk 0.1088`) | **`Z = +3.04, p = 0.02697`** (`akk p = 0.063`) | Supporting phonetic *(dilutes on 33-vessel `p = 0.231`)* | [c-liturgy.md](kernels/c-liturgy.md) |
| **D. Pre-Linguistic Anchors** | 8 arithmetic/vessel/grain words | **PASS** (LB Greek `Z = +7.97`; Sem `p = 0.111`) | **Semitic (#1)** | `LL = -19.072`, **`ΔLL = +13.585`** (~794,000:1 BF) | **`Z = +7.37, p = 0.00010`** *(11/11 ablations pass)* | **Primary phonetic proof** | [d-anchors.md](kernels/d-anchors.md) |
| **E. Verbal Edge-Frames** | 46 votive `>=4`-sign words | `5/5` (100%) dev | **`semitic_verbs` (#1)** | `25.059` bits/word (`M = +1.056` vs Hurrian) | `Z = +0.85, p = 0.208` | Exploratory *(underpowered `n = 46`)* | [e-verbal-frames.md](kernels/e-verbal-frames.md) |
| **F. Ligature Acrophony** | 10 `GRA/OLE/VIN` adjuncts | **PASS** (LB Greek `Z = +4.31`; Sem `p = 0.362`) | **Semitic (#1)** | `LL = -20.367`, **`ΔLL = +28.17`** | **`Z = +5.53, p = 0.00010`** | Auxiliary phonetic *(single-sign)* | [f-acrophony.md](kernels/f-acrophony.md) |
| **G. Palaikastro Dialect** | 5 Central ↔ PK pairs | 10,000 random 4-rule bundles | **NWS 4-rule bundle (#1)** | **`5 / 5` exact hits** (`perm_mean = 0.0068`) | **`Z = +50.05, p = 0.00010`** | Supporting phonological *(small `n = 5`)* | [g-dialect.md](kernels/g-dialect.md) |
| **H. Roster Onomastics** | 57 `WORD 1` admin names | Size-equalized (`1,314`/arm) | Mycenaean LB (#1), **Levant Semitic (#2)** | `6.141` vs LB `5.879` *(beats Kassite `6.93`, Hurr `7.19`, Anat `7.43`)* | `Z = +1.56, p = 0.06494` | Cultural milieu *(shared Cretan names)* | [h-onomastics.md](kernels/h-onomastics.md) |
| **I. Bound Affix Morphology** | 505 strict-LB types | **PASS** (7/7 dev; LB Greek `p_M = 0.02679`; Sem `0.875`) | **Semitic (#1, only pass)** | **`M = +40.03`** (standalone) / `+32.35` (5-seed full) | **`Z_M = +2.63, p_M = 0.00360`**, **`p_cv = 0.00040`** | **Primary grammatical proof** *(`omission` mode)* | [i-morphology.md](kernels/i-morphology.md) |
| **J. Zero-Curation Dict Audit** | `8` baseline; `7`/`9` pure strict LB; `12`/`11`/`14` sensitivity | **PASS** (LB `n=6`: `0.00010/0.0139`; `EXT9`: `481:1`, `0.00010/0.00020`; Sem `0.293`) | **Semitic (#1, only dual-null pass)** | `FULL_8` `+4.054`; **`DEDUP_9` `+3.863` (`47.6:1`)**; `DEDUP_12` *(PA₃ fold)* `+4.200` (`66.7:1`); `DEDUP_14` `+4.623` (`101.8:1`) | **`DEDUP_9` `p_c=0.0039`**; **`DEDUP_12` `0.0018`** (`p_perm=0.00010`; `DEDUP_14` `p_perm=0.00020, p_c=0.0092`; `K`-free `5` `p_perm=0.0164`, `p_c=0.217`) | **Primary anti-bias audit** | [j-auto-anchors.md](kernels/j-auto-anchors.md) |
| **K. Corazza–Ferrara Fractions** | Properness (`55`), blind `KU-RO` (`1,719` recs) + dedup pair | **PASS** (LB `TO-SO/O-PE-RO` Greek `Z = +2.48, p = 0.01440`; Sem `0.401`) | **Semitic (#1)** *(K0–K1 language-free)* | `0` Corazza `>1` violations (`HT 27a`); `KU-RO` #1 (`9`); dedup **`ΔLL = +1.190`** | **`Z = +3.15, p = 0.01480`** *(Grk rejected `0.0544`; triad `ΔLL = +0.551`)* | **Accounting-only confirmation + 3D ledger** | [k-fractions.md](kernels/k-fractions.md) |
| **L. Backward-Projection Audit** | SigLA, 12-series drops, L1SO, D+I corruption, L4 nulls | **PASS** (LB L3 `100%` at `ε=0.2–0.3`; L4 LB ligatures fail `p = 0.395`) | **Robust (`Semitic`) + 3 calibrated nulls** | SigLA sole pass **`p_M = 0.0020`**; `10/12` single-drops; `ε=0.2` D **`90%`** `p<=0.05` / I **`86%`** | **`8/8` D & `7/7` J `p_perm` pass** *(J `p_concept` `2/7`)*; `Drop T` #1 collapse (`0.265`) | **Adversarial stress-test & negative controls** | [l-homomorph.md](kernels/l-homomorph.md) |

### Replicate the Top Results in Minutes (Fresh Clone, Zero External Folders)

```bash
git lfs install
git clone https://github.com/plasma-ai/kaphtor.git
cd kaphtor
uv sync --all-groups

# 1. Verify all 32 kernel unit tests + 8 shipped-input count guards (40 total)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=models/language-id-kernel uv run --no-sync python -m pytest -q models/language-id-kernel/tests/ tests/test_kernel_shipped_inputs.py

# 2. Reproduce the primary consonant-specific proofs (Kernels D, J, I) & new Bologna audits (Kernels K, L)
uv run --no-sync python models/language-id-kernel/anchors_d.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000 --seed 20261125
uv run --no-sync python models/language-id-kernel/morphology_i.py --mode omission --n-perm 5000
uv run --no-sync python models/language-id-kernel/fractions_k.py --n-perm 5000
uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage all --n-perm 1000 --trials 300

# 3. Reproduce the remaining kernels (C, E, F, G, H) and A+B+D ablation manifest
uv run --no-sync python models/language-id-kernel/liturgy_c.py --run-linear-a --n-perm 1000
uv run --no-sync python models/language-id-kernel/verbs_e.py --n-perm 500
uv run --no-sync python models/language-id-kernel/acrophony_f.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/dialect_g.py --n-perm 10000
uv run --no-sync python models/language-id-kernel/onomastics_h.py --n-perm 1000
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py ablate models/language-id-kernel/runs/kaphtor-kernel-linear-a-20261122T222434Z.json
```

---

## Anti-Circularity Firewall

- **Zero project-lexicon leakage:** No script here reads `lexicon.json`, `translations.json`, or `onomasticon.json`. Every Linear A target comes strictly from `data/linear-a/corpus.json` (GORILA/SigLA transliterations).
- **Strict Linear B values only:** Only agreed Linear B syllabogram values (`render/series.json`, `render/signs-a5-proposed.json`) are used. None of the 37 proposed Linear A-only sign values enter the suite.
- **Known-language calibration gates:** Primary and high-impact kernels must first identify real Mycenaean Linear B tablets (Pylos and Knossos, DAMOS-verified) as **Greek** and reject **Semitic** before scoring Linear A behind `SIGNATURE.txt`.
- **Orthogonal nulls:** Every consonant-specific claim is tested against consonant-series grid swaps, discriminative margin permutations, exact concept-label shuffling, random 4-rule phonological bundles, or Monte Carlo sign-value corruption curves.

## Documentation & Ledgers

- **[results-significance-2026-11-24.md](results-significance-2026-11-24.md)**—Timestamped `2026-11-24` findings covering Kernels K & L, review caveats, and the twelve-kernel synthesis
- **[ferrara-vetting-guide.md](ferrara-vetting-guide.md)**—Five-command zero-LLM adversarial vetting workbench for epigraphers and Bologna (INSCRIBE / SAPIENCE) reviewers
- **[docs/lexicon-api.md](../../docs/lexicon-api.md)**—Reference for the read-only Linear A Lexicon REST API (`api.linear-a.ai/v1`), MCP server (`mcp.linear-a.ai/mcp`), and live probabilistic kernel endpoints (`/v1/kernel/summary`, `/v1/kernel/anchors`, `/v1/kernel/ligatures`)
- **[results-significance-2026-11-23.md](results-significance-2026-11-23.md)**—Timestamped baseline deep-dive explaining Kernels A–J, rival behavior, and methodological limits
- **[kernels/_index.md](kernels/_index.md)**—Individual technical specifications for Kernels A–L (`a-word-shape.md` … `l-homomorph.md`)
- **[replication-guide.md](replication-guide.md)**—Master scoreboard, objectivity audit, shipped inputs, and optional override environment variables
- **[reference.md](reference.md)**—Mathematical specification, calibration tables, and signed Linear A run ledgers
- **[kernel-specs.md](kernel-specs.md)** & **[preregistration-draft.md](preregistration-draft.md)**—Design specification and signed pre-registration (`SIGNATURE.txt`)
- **[runs/](runs/_index.md)**—Timestamped SHA-256-verified JSON run ledgers (including `kernels-kl-2026-11-24.json`)
- **[tests/](tests/_index.md)**—Unit tests for Kernels B, C, D, F, G, H, I, J, K, L and `kaphtor_kernel.py`
- `build_shipped_inputs.py`—Deterministic cut builder (`--check` verifies every shipped `.jsonl` bit-for-bit against upstream open corpora)
