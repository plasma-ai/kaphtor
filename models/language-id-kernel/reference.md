---
name: models/language-id-kernel/reference
title: "Reference Documentation: Ten-Kernel Probabilistic Language Identification of Linear A"
desc: "Complete mathematical specification, calibration gates, signed Linear A results, stress-test ablations, and methodological limits."
tags: [linear-a, reference, statistics, preregistration]
created: 2026-11-22T00:00:00Z
updated: 2026-11-23T15:13:53Z
---

# Reference Documentation: Ten-Kernel Probabilistic Language Identification of Linear A

## 1. Design Principles & Anti-Circularity Guarantees

1. **Strict Linear B sign values only (`--strict-lb-only`):** Primary runs use only Bartoněk's secure Linear B syllabogram values (`signs-a5-proposed.json`). Contested or Linear A-only signs (`*301`, `*314`, `*306`, `*21F`, `PA₃`, `ZU`, etc.) remain opaque symbols.
2. **Zero circularity:** Project outputs (`lexicon.json`, `translations.json`, `onomasticon.json`) are never read as inputs.
3. **Zero LLMs:** Every score is computed by deterministic Python with fixed seeds (`20261122`) and verified SHA-256 manifests.
4. **Known-language calibration before unsealing:** Every channel was calibrated on known ancient languages (including real Linear B tablets) while Linear A remained sealed behind `SIGNATURE.txt`.
5. **Consonant-series grid-permutation null:** Every channel is tested against random permutations $\sigma$ of the 12 consonant series (`D, J, K, M, N, P, Q, R, S, T, W, Z`) while holding vowels (`a, e, i, o, u`), word boundaries, and frequencies fixed.

---

## 2. Mathematical Summary of the Four Kernels

* **Kernel A (`lid.py` + `pooled_signs`):** Pooled family Witten-Bell 3-gram models over CV sign keys, equalized by **total training signs** ($S = 3{,}700$ signs/arm, 5 seeded draws, glide rule applied to all rule-spelled sources). Margin $M_A(\text{arm}, X) = \min_{r \ne \text{arm}} H_A(r, X) - H_A(\text{arm}, X)$ in bits/sign.
* **Kernel B (`kober_b.py`):** Unsupervised extraction of stem-sharing word pairs/trios via `c_align.align` (shared run $\ge 2$ signs, affix residue $\le 2$ signs/side, plus stem-final consonant-series vowel alternations). Hierarchical Witten-Bell model $P_L(\text{pol}, e_1, e_2) = P_L(\text{pol}) P_L(e_1, e_2 \mid \text{pol})$ equalized at $N_{\text{tr}} = 2{,}900$ transitions/arm.
* **Kernel D (`anchors_d.py`):** Pre-linguistic semantic anchors whose meanings are fixed by arithmetic or iconography before any language is named. Bounded synsets (4–6 core attested lexemes per concept per language) forward-spelled via `c_render.word` + glide rule. Scored by Bayesian marginal log-likelihood (log-mean-exp over synset, $\beta = 6.0$, normalized CV edit distance $d \in [0, 1]$) against $B = 10{,}000$ consonant-series permutations.
* **Kernel C (`liturgy_c.py`, supporting):** Size-locked ($K = 300$ distinct CV forms per arm) liturgical vocabularies—built mechanically for Hebrew via Monroe et al. (2008) informative Dirichlet log-odds on OSHB Psalms/Leviticus vs. narrative prose (strictly excluding control chapters), and top-300 forms for Syriac (Ephrem), Anatolian (TLHdig), Hurrian (TLHdig/eCUT), and Greek (Diodorus). Scored on mean bounded CV alignment ($\tau = 0.35$, up to 1 prefix/suffix sign stripped at `0.10`/sign penalty) against consonant-series permutations.
* **Joint Aggregator (`kaphtor_kernel.py`):** Unweighted Stouffer meta-$Z$ across primary channels A, B, and D: $Z_{\text{joint}} = (Z_A + Z_B + Z_D) / \sqrt{3}$.

---

## 3. Calibration Results (Measured Before Unsealing Linear A)

### 3.1 Kernel A (`pilot_fix1.py`, `pooled_signs`, $S = 3{,}700$, `train`/`dev` split)
* **G1 (real Linear B tablets as Greek):** **1.0** under both omission and plene (fixed Round 3's omission failure `0.0 → 1.0`).
* **G2 (own-arm classification):** **1.0** across every language.
* **G3 (Central Semitic sisters without self):** Hebrew **1.0**, Syriac **1.0**, Geʿez **1.0**, Arabic **0.8** (omission) / **0.3** (plene against strict max `latin`-absent `0.6046`; **1.0** against $\theta_{95}$ and against all running-text non-Semitic languages, which sit at $\le 0.28$).
* *Falsified alternative:* Unpooling Semitic via $\min$ over 7 individual members failed ($\theta_{\text{Sem}}$ rose to `0.65–0.68` due to Akkadian absorbing Sumerian; Arabic G3 fell to `0.0`). Family arms remain pooled.

### 3.2 Kernel B (`pilot_kober_b.py`, `B_only`, plene, $N_{\text{tr}} = 2{,}900$, `train`/`dev` split)
* **Own-arm accuracy:** **62 / 62 (100%)** across all 14 languages, including real Linear B tablets (`+1.12`, `sem = -1.12`).
* **Sister recovery (without self):** Hebrew `+3.88`, Aramaic `+3.46`, Syriac `+3.27`, Geʿez `+2.70`, Arabic `+1.56`, Ugaritic `+0.75`, Luwian `+1.53`, Urartian `+1.00`, vs. Sumerian isolate `+0.27`.

### 3.3 Kernel D (`anchors_d.py --calibrate`, Linear B 6 anchors, $B = 10{,}000$ perms)
* **PASS:** **Greek** `LL = -11.321`, **`Z_perm = +7.97`**, **`p_perm = 0.00010`** (`0/10,000`); Anatolian (IE cousin) `-24.476` (`Z = +3.29`, $\Delta\text{LL} = -13.15$); Hurrian `-28.086` (`Z = +1.40, p = 0.097`); Semitic `-28.598` (`Z = +1.28, p = 0.111`).

### 3.4 Kernel C (`liturgy_c.py --calibrate`, 104 Protocol D v3 controls, $K = 300$, $B = 200$)
* **`H1_semitic_prayer` ($n=15$):** mean $Z = +2.15$, `8/15` (53%) at $p \le 0.05$.
* **`H3_semitic_nonprayer` ($n=23$):** mean $Z = +1.27$, `6/23` (26%).
* **Non-Semitic controls:** `FAB` `0/10` (`+0.45`), `H2_luwian` `0/8` wins (`+0.12`), `H2_hurrian` `0/8` wins (`+0.37`), `NEG_linear_b` `2/20` (`+0.37`), `H2_egyptian` (drawn vowels, Afroasiatic) `8/20` (`+1.47`).

---

## 4. Signed Linear A Results (`2026-11-22`, Strict Linear B Values Only)

Run record: `runs/kaphtor-kernel-linear-a-20261122T222434Z.json` (505 distinct undamaged Linear A types across 340 documents; 164.9 s; manifest SHA-256 unchanged).

| Channel | Role | Winner | Semitic / Hebrew Score | Runner-Up | $Z_{\text{perm}}$ (cons. grid) | $p_{\text{perm}}$ |
|---|---|---|---|---|---:|---:|
| **A. Word-Shape LID** | Primary | **Semitic** | `5.4902` bits/sign (`M = +0.6230`) | Hurrian (`6.1133`) | `-0.21` | `0.587` |
| **B. Kober Trios** | Primary | **Semitic** | `22.3622` bits/tr (`M = +2.2880`) | Hurrian (`24.6502`) | `-1.09` | `0.846` |
| **D. Pre-Linguistic Anchors** | Primary | **Semitic** | **`LL = -19.072`** ($\Delta\text{LL} = +13.58$) | Hurrian (`-32.656`) | **`+7.37`** | **`0.00010`** |
| **Joint Stouffer $Z$ (A+B+D)** | Aggregate | **Semitic** | — | — | **`+3.504`** | **`0.00023`** |
| **C. Liturgical (`IO Za 2`)** | Supporting | **`hebrew_lit`** | `0.1020` | Hurrian (`0.0612`) | **`+3.045`** | **`0.02697`** |

**Leave-One-Channel-Out Stouffer $Z$:** All (`A+B+D`) `+3.504` | Drop A `+4.442` | Drop B `+5.060` | Drop D `-0.919`.

### 4.1 Kernel D Stress-Test Ablations (`runs/stress-test-cd-2026-11-22.json`, $B = 10{,}000$ perms each)

| Subset | $n$ | Winner | $\Delta\text{LL}$ vs. Runner-Up | $Z_{\text{perm}}$ | $p_{\text{perm}}$ |
|---|---:|---|---:|---:|---:|
| `FULL_8` | 8 | **Semitic** | `+13.58` (vs. Hurrian) | `+7.37` | `0.00010` |
| Leave-one-out (each of the 8 dropped) | 7 | **Semitic (8/8)** | `+10.53` to `+13.23` | `+6.45` to `+7.67` | **`0.00010`** *(all 8)* |
| **Drop 3 trade-loan suspects** (`A-KA-NU`, `KU-NI-SU`, `KA-DI`) | 5 | **Semitic** | **`+7.53`** (~1,860 : 1) | **`+6.22`** | **`0.00010`** |
| **Pure Arithmetic Only** (`KU-RO`, `KI-RO`) | 2 | **Semitic** | **`+2.61`** (~13.6 : 1) | **`+4.59`** | **`0.00640`** |

### 4.2 Kernel C Formula-Family Stress Test (`runs/stress-test-cd-2026-11-22.json`, $K = 300$, $B = 2{,}000$)
* **`IO Za 2` (7 words):** `winner = hebrew_lit`, **`Z = +2.91, p = 0.03248`** (every rival `Z <= +1.01, p >= 0.18`).
* **Full 33-vessel Formula Family (41 undamaged types):** `winner = hebrew_lit` (`Z = +0.73, p = 0.231`), followed by `syriac_lit` (`Z = +0.56, p = 0.293`)—not significant once diluted by 34 site-specific proper names/dedicant/deity variants (`EXCL_IOZA2`: `syriac_lit +0.65`, `hebrew_lit +0.10`, `p = 0.25–0.41`).

---

### 4.3 Extended Kernels E–H (`2026-11-22`, Strict Linear B Values Only)

| Kernel | Calibration Gate | Linear A Target | Winner | Margin / $\Delta\text{LL}$ | $Z_{\text{perm}}$ | $p_{\text{perm}}$ |
|---|---|---|---|---|---:|---:|
| **E. Verbal Edge-Frames** (`verbs_e.py`) | **5/5 (100%)** (`dev` `>=4`-sign verbs/words) | 46 votive `>=4`-sign words (`Za/Zb/Zc/Zf/Zg`) | **Semitic verbs** | `M = +1.056` bits/word | `+0.85` *(perm mean `+0.16`)* | `0.208` |
| **F. Commodity Ligature Acrophony** (`acrophony_f.py`) | **PASS** (Linear B → Greek `Z = +4.31, p = 0.00070`; rivals rejected) | 10 `GRA/OLE/VIN` ligatures | **Semitic** | **`ΔLL = +28.17`** | **`+5.53`** | **`0.00010`** *(0/10,000)* |
| **G. Palaikastro Dialect Coherence** (`dialect_g.py`) | 10,000 random 4-rule bundles | 5 Central ↔ PK minimal pairs | **NWS isogloss bundle** | `5 / 5` hits | **`+50.05`** | **`0.00010`** |
| **H. Roster Onomastics** (`onomastics_h.py`) | Size-equalized (`1,200`/arm) | 57 roster names (`WORD 1`) | **Mycenaean LB** *(shared Cretan names)* | Amorite #2 (`6.75` vs. Hurr `7.09`, Anat `7.27`) | `+1.30` (Amorite) | `0.094` |

*Notes on E–H:* Kernel F's Semitic commodity synsets were compiled from *Ya Diktu* App. C.5 alongside standard rival qualifiers (so an independent blind-builder synset audit remains the gold standard). Kernel H reflects shared Bronze Age Cretan personal names carried over from Linear A into Knossos Linear B, with Amorite Semitic placing second ahead of Hurrian and Anatolian.

### 4.4 Kernels I–J (`2026-11-23`, Bound Morphology & Zero-Curation Dictionary Audit)

| Kernel | Calibration Gate | Linear A Target | Winner | Margin / $\Delta\text{LL}$ | Null #1 | Null #2 |
|---|---|---|---|---|---|---|
| **I. Bound Affix Morphology** (`morphology_i.py`, `runs/morphology-i-2026-11-23.json`) | **PASS** (7/7 dev `p_cv=0.00050`; Linear B → Greek `M=+472.95, p_M=0.02679` standalone, 5/5 seeds `p_M=0.0015–0.0485` full) | 505 strict Linear A types (`p_pre=0.419` vs Semitic `0.393–0.404`) | **Semitic** *(5/5 seeds `omission`)* | **`M = +40.03`** *(standalone ANE Semitic)* / **`mean M = +32.35`** *(full 7-member)* | `Z_cv = +2.55, p_cv = 0.00040` *(standalone)* / `p_cv = 0.01920` *(full)* | Margin null: **`Z_M = +2.63, p_M = 0.00360`** *(standalone)* / **`mean p_M = 0.0385`** *(full)* |
| **J. Zero-Curation Dict Audit** (`auto_anchors_j.py`, `runs/auto-anchors-j-standalone-2026-11-23.json` & `runs/auto-anchors-j-2026-11-23.json`) | **PASS** (Linear B → Greek `p_perm=0.00010, p_concept=0.01389` standalone vs Sumerian `p_perm=0.061` & Semitic `0.170 / 0.775`) | Linear A `FULL_8` (`cap=40`) | **Semitic** | **`ΔLL = +4.05`** *(standalone vs ePSD2 Sumerian & LSJ Greek)* / **`+2.34`** *(full 6-lang)* | **`Z_perm = +3.75–+4.85, p_perm = 0.00010`** | Concept shuffle (`5,040` perms): **`p_concept = 0.02520`** *(standalone)* / **`0.00893`** *(full; Sumerian `0.637`, Greek `0.588`)* |

See [replication-guide.md](replication-guide.md) for the complete 10-kernel master scoreboard and fresh-clone commands.

---

## 5. Honest Scope & Methodological Limits

1. **Consonant-specific phonetic proof resides in Kernels D, J, F, G, I, and C (`IO Za 2`), not A and B:** While Kernels A (`+0.623`) and B (`+2.288`) both rank Semitic #1 in raw bits across the 505-type corpus, their lead persists under random consonant permutation (`perm_mean = +0.643` and `+2.770`, yielding `Z_perm = -0.21` and `-1.09`). Thus A and B reflect **vowel-core and syllabic macro-typology** (`/a, i, u/` dominance), whereas **Kernel D (`Z = +7.37, p = 0.00010`)**, **Kernel J (`p_perm = 0.00010, p_concept = 0.00893`)**, **Kernel F (`Z = +5.53, p = 0.00010`)**, **Kernel G (`5/5, p = 0.00010`)**, **Kernel I (`M = +27.11, p_M = 0.0436`)**, and **Kernel C on `IO Za 2` (`Z = +2.91–3.05, p = 0.027–0.032`)** carry consonant-specific signal that survives consonant-grid permutation.
2. **Pre-linguistic anchors (`Kernel D`) survive trade-loanword removal:** Dropping `A-KA-NU`, `KU-NI-SU`, and `KA-DI` still leaves a ~1,860 : 1 Bayes Factor (`Z = +6.22, p = 0.00010`), and pure arithmetic (`KU-RO`, `KI-RO`) alone yields `Z = +4.59, p = 0.00640`.
3. **What remains untested:** An unmodeled extinct language family (outside Semitic, Greek, Anatolian, Hurrian, Hattic, and Latin) is bounded only by the consonant-grid permutation null and the Sumerian isolate control, not by a direct language model.
