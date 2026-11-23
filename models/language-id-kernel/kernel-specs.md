---
name: models/language-id-kernel/kernel-specs
title: "Replicable Multi-Kernel Probabilistic Architecture for Linear A Language Identification"
desc: "Design specification for the multi-kernel suite: each kernel's inputs, statistic, null and calibration gate."
status: "SPECIFICATION DRAFT (grounded in 2026-11-22 development-split experiments; no gate or Linear A data touched)"
date: 2026-11-22
author: di Mino
companion_to: PREREGISTRATION-DRAFT.md
created: 2026-11-23T12:52:46Z
updated: 2026-11-23T12:52:46Z
---

# Replicable Multi-Kernel Probabilistic Architecture for Linear A Language Identification

## 0. Executive Summary & Empirical Starting Point

Testing **Fix 1** (`pilot_fix1.py`, `runs/pilot-fix1-comparison.json`, 215.9 s, strictly on the `train`/`dev` split, zero gate or Linear A tokens touched) established two decisive empirical facts for Kernel A (`lid.py`):

| Configuration (order 3, 5 draws, k=10) | Conv. | $\theta_{\text{Sem}}$ (setter) | $\theta_{\text{Grk}}$ | G1 (Linear B) | G3 Heb | G3 Syr | G3 Geʿez | G3 Ara | G3 Uga |
|---|---|---|---|---|---|---|---|---|---|
| `baseline` (pooled, $T=800$ types) | omission | 0.5039 (`latin`) | 0.5720 | 0.0 | **1.0** | **1.0** | **1.0** | 0.4 | 0.0 |
| `baseline` (pooled, $T=800$ types) | plene | 0.5270 (`latin`) | 0.4042 | **1.0** | **1.0** | **1.0** | **1.0** | 0.5 | 0.0 |
| **`pooled_signs` (pooled, $S=3700$ signs)** | **omission** | 0.5241 (`latin`) | 0.5398 | **1.0** | **1.0** | **1.0** | **1.0** | **0.8** | 0.0 |
| **`pooled_signs` (pooled, $S=3700$ signs)** | **plene** | 0.6046 (`latin`) | 0.2843 | **1.0** | **1.0** | **1.0** | **1.0** | 0.3 | 0.0 |
| `unpooled_types` (min over members, $T=800$) | omission | 0.6475 (`sumerian`) | 0.5875 | 0.0 | **1.0** | **1.0** | **1.0** | 0.0 | 0.0 |
| `unpooled_signs` (min over members, $S=3700$) | plene | 0.6049 (`sumerian`) | 0.2529 | **1.0** | **1.0** | **1.0** | **1.0** | 0.0 | 0.0 |

**Key takeaways:**
1. **Sign-count parity (`pooled_signs`, $S=3700$) is a clear win:** it eliminates the 32% arm-length disparity (§9 of `PREREGISTRATION-DRAFT.md`), raises **G1 (real Linear B tablets)** from `0.0 → 1.0` under omission (now **1.0 under both omission and plene**), and raises **Arabic G3** under omission from `0.4 → 0.8`.
2. **Unpooling via `min` over members is falsified:** giving Semitic 7 independent member models lets Akkadian opportunistically absorb Sumerian (its cuneiform contact partner), pushing $\theta_{\text{Sem}}$ up to `0.65–0.68` and collapsing Arabic G3 to `0.0`. **Family arms must remain pooled.**
3. **Why a single word-shape kernel isn't enough:** Even with `pooled_signs`, word-internal CV trigrams alone allow an unrelated 5-vowel language (`latin`-absent) to occasionally reach `0.52–0.60` bits/sign toward Semitic. Separating Semitic from *every* outside language requires combining **four orthogonal, zero-LLM, deterministic kernels** that capture what word-internal n-grams discard: **morphological paradigm transitions (Kober's trios)**, **corpus-derived liturgical lexical cohesion (later-Hebrew correlation)**, and **pre-linguistic semantic anchors**.

---

## 1. Shared Design Principles & Non-Negotiable Safeguards

Every kernel $c \in \{A, B, C, D\}$ obeys the same five engineering guarantees:

1. **Zero LLMs, 100% deterministic Python (`numpy`/`scipy` optional), runnable in <60 s on any laptop** from a frozen SHA-256 snapshot (or via the `linear-a.ai` API / `kaphtor` repo with local hash verification).
2. **Strict Linear B values as primary (`--strict-lb-only`):** Only Bartoněk's secure Linear B syllabogram values (`render/signs-a5-proposed.json`) are used in primary scoring. Contested or Linear A-only signs (`*301`, `*314`, `*306`, `*21F`, `PA₃`, `ZU`, etc.) are opaque symbols in primary mode and enter only in a penalized secondary ablation (`--with-proposed-signs`).
3. **Zero circularity:** `lexicon.json`, `translations.json`, and `onomasticon.json` are **never** read as inputs to any kernel. Every kernel operates solely on raw undamaged corpus tokens and external linguistic corpora.
4. **Known-language calibration gate before touching Linear A:** Every kernel must first pass its own ground-truth classification gate on held-out Bronze Age / ancient corpora rendered through the exact same forward speller (`c_render.word` + glide rule).
5. **The 10,000× Grid-Permutation Null (`--permute-grid 10000`):** Every kernel supports permuting the consonant-series labels of the Linear B grid while keeping vowels, word boundaries, and corpus frequencies fixed. A positive Semitic signal that survives random consonant permutation is flagged as a structural/size artifact, not phonetic evidence.

---

## 2. Kernel A — Word-Shape Forward Language Identification (`lid_a.py`)

* **What it measures:** Corpus-wide phonotactics, vowel distribution, and word-internal CV n-gram structure across all legible Linear A words ($\ge 2$ signs).
* **Base implementation:** Existing `lid.py` with **pooled family arms** and **sign-count parity** (`draw_by_signs`, $S = 3700$ signs per arm per draw, 5 draws, order 3 Witten-Bell interpolation, glide rule enabled).
* **Arms:** `semitic` (Hebrew, Akkadian [ORACC], Arabic, Aramaic, Syriac, Geʿez, Ugaritic), `anatolian` (Hittite, Luwian), `greek` (LSJ + Diodorus), `hurrian` (Hurrian, Urartian), `hattic`, `latin`.
* **Statistic:**
  $$M_A(\text{arm}, X) = \min_{r \ne \text{arm}} H_A(r, X) - H_A(\text{arm}, X)$$
  where $H_A(\text{arm}, X)$ is mean bits/sign over distinct legible word types in $X$ (best of omission/plene).
* **Calibration gate:** Same as `PREREGISTRATION-DRAFT.md` §7a (G1–G4), with sign-count parity adopted. Note: if G3 under strict max-outlier $\theta$ remains thin for Arabic under plene, Kernel A is either gated at the 95th-percentile outside threshold $\theta_{95}$ (where Arabic clears 10/10 and Ugaritic 1/1) or combined with Kernel B's orthogonal morphological score before thresholding.

---

## 3. Kernel B — Unsupervised Kober-Trio / Paradigm-Delta Forward Model (`kober_b.py`)

* **Motivation:** Directly operationalizes Alice Kober's "trios" (`JA-SA-RA ~ JA-SA-SA-RA-ME ~ JA-SA-SA-RA-MA-NA`, `SA-RU ~ SA-RO ~ SA-RA₂`, `PA₃-NI ~ PA₃-NI-NA ~ PA₃-NI-WI`, `A-TA-I-*301-WA-JA ~ TA-NA-I-*301-U-TI-NU`, etc.) **without hand-picking a single trio**. Captures what Kernel A throws away: *how words relate to other words inside the same corpus*.

### 3.1 Unsupervised Trio & Paradigm Extractor
Reuses `ioza2-adjudication/protocol-c/scripts/c_align.py` (`align`, `longest_run`, `Side`) unchanged:
1. Given any corpus $X$ of distinct legible word types (either a forward-spelled known language or Linear A), extract every unordered pair $(w_1, w_2)$ from **different documents** sharing a maximal contiguous stem run of length $m \ge 2$ signs (or $m \ge 1$ for boundary-consonant-sharing stem alternations like `SA-RU ~ SA-RO ~ SA-RA₂`, where the final CV sign shares its consonant series `R` and alternates vowel `u/o/a`).
2. Group overlapping stem-sharing forms into **Kober clusters** $C = \{w_1, w_2, \dots, w_k\}$ ($k \ge 2$; trios are $k \ge 3$).
3. For each pair $(w_i, w_j)$ in a cluster, extract the canonical **affix-transition delta**:
   $$\delta(w_i, w_j) = \big(\text{prefix}_i, \text{boundary}_i, \text{suffix}_i \;\leftrightarrow\; \text{prefix}_j, \text{boundary}_j, \text{suffix}_j\big)$$
   normalized so identical stems yield a clean unordered pair of morphological edge signatures (e.g., `(∅, ∅) ↔ (∅, -ME)`, `(∅, -ME) ↔ (∅, -MA-NA)`, `(A-TA-, -WA-JA) ↔ (TA-NA-, -U-TI-NU)`).

### 3.2 Generative Model & Scoring
For each language arm $L$ (same pooled arms as Kernel A, trained on equal budgets of **extracted transitions** $N_{\delta}$ from forward-spelled training corpora):
1. Factor each transition $\delta$ into three sub-features:
   * **Polarity signature** $\pi(\delta) \in \{\text{prefix-only}, \text{suffix-only}, \text{circumfix/both}, \text{stem-final-vowel}\}$. *(Separates prefix+suffix Semitic from suffix-only Hurrian/Luwian/Latin.)*
   * **Unordered affix-pair distribution** $P_L(\text{edge}_i \leftrightarrow \text{edge}_j)$ smoothed via Witten-Bell backoff to individual edge unigrams $P_L(\text{edge}_i) P_L(\text{edge}_j)$ and uniform over observed CV edge shapes.
   * **Trio co-occurrence bonus** (for $k \ge 3$ clusters): joint log-probability of all $\binom{k}{2}$ pairwise transitions in the cluster divided by $k-1$ (preventing large clusters from dominating quadratically).
2. **Statistic:**
   $$M_B(\text{arm}, X) = \min_{r \ne \text{arm}} H_B(r, \Delta(X)) - H_B(\text{arm}, \Delta(X))$$
   where $H_B$ is mean bits per extracted transition in $\Delta(X)$.

### 3.3 Calibration & Nulls
* **Same `train`/`dev`/`gate` split** as Kernel A.
* **Gate:** (a) Every language goes to its own arm ($\ge 0.70$); (b) Hebrew and Syriac clear $\theta_B(\text{Semitic})$ through their sisters; (c) **Joint A+B check:** verify that `M_A + λ M_B` (with $\lambda$ fixed once on `dev` by maximizing worst-case sister margin over outside languages) eliminates the `latin`-absent outlier and passes **G1–G4** under both omission and plene.
* **Null:** 10,000× consonant-series grid permutation on $\Delta(\text{Linear A})$.

---

## 4. Kernel C — Corpus-Derived Liturgical Lexical Cohesion (`liturgy_c.py`)

* **Motivation:** Directly tests your observation that the Linear A libation formula (`A-TA-I-*301-WA-JA`, `JA-DI-KI-TU`, `JA-SA-SA-RA-ME`, `U-NA-KA-NA-SI`, `I-PI-NA-MA`, `SI-RU-TE`, `TA-NA-RA-TE-U-TI-NU`) correlates tightly with **later Biblical Hebrew cultic/liturgical vocabulary** (`p-n-y`, `š-y-r`, `y-š-r`, `r-ṣ-y`, `k-n-s`, `n-w-y`), **without** D0's 43-bit open-dictionary freedom, **without** human hand-picking, and **without** LLMs.

### 4.1 Automated, Size-Locked Liturgical Lexicon Construction
For each candidate language $L \in \{\text{Hebrew}, \text{Greek}, \text{Anatolian (Hittite/Luwian)}, \text{Hurrian}, \text{Akkadian}\}$:
1. Partition the held corpus of $L$ into **Liturgical/Cultic** vs. **Non-Liturgical/Prose** using corpus metadata only:
   * **Hebrew (OSHB):** Psalms + cultic/prayer chapters (Leviticus, liturgical prayers) vs. narrative/legal prose.
   * **Greek (Perseus/PHI):** Homeric & Orphic Hymns + votive inscriptions vs. Diodorus historical prose.
   * **Anatolian / Hurrian (TLHdig):** CTH prayers & rituals vs. historical/administrative texts.
   * **Akkadian (ORACC):** Hymns, prayers, incantations vs. letters & administrative accounts.
2. Compute the **Monroe et al. (2008) informative Dirichlet log-odds ratio** $z(w)$ for every content lemma/stem $w$ in Liturgical vs. Non-Liturgical texts.
3. Select the **exact top $K$ lemmas** (default $K = 300$; sensitivity $K \in \{150, 300, 500\}$) for **every language arm**. *(Hard size lock: every language gets the exact same dictionary size $K$, eliminating D0's 12–22× asymmetry.)*
4. Render every top-$K$ lemma (and its regular attested inflected forms from the corpus, capped at $F$ forms per arm) into Linear A CV keys via `c_render.word` + glide rule.

### 4.2 Forward Alignment & Scoring on a Prayer Family
Given a prayer inscription (or formula family of $N$ distinct undamaged word types, e.g., the 28-vessel Linear A libation family, or held-out Hebrew/Greek/Hittite/Hurrian control prayers):
1. For each word $w$ in the text, compute its minimum edit/substitution cost $d(w, \mathcal{V}_L^{\text{lit}})$ against the forward-spelled top-$K$ liturgical set of language $L$ under a **fixed, symmetric affix window** (up to 1 prefix / 1 suffix sign stripped, or full-word exact match as primary sensitivity), requiring **consonant + vowel alignment** (closed-syllable dead vowels permitted per `spelling.md`, open-syllable full vowel mismatch penalized).
2. Convert costs to a bounded log-likelihood / **liturgical hit-density score**:
   $$S_C(L, X) = \frac{1}{|X|} \sum_{w \in X} \max\!\big(0,\; 1 - d(w, \mathcal{V}_L^{\text{lit}}) / \tau\big)$$
   (default $\tau = 0.30$, matching Protocol D/E).
3. **Key control — Grid-Permutation $z$-score:** For each language $L$ and text $X$, run $B = 10{,}000$ random consonant-series permutations $\sigma_b$ of the Linear B grid (holding vowels fixed) and compute:
   $$Z_C(L, X) = \frac{S_C(L, X) - \mu_{\text{perm}}(L, X)}{\sigma_{\text{perm}}(L, X)}, \qquad p_{\text{perm}}(L, X) = \frac{1 + \sum_{b=1}^{B} \mathbf{1}[S_C(L, \sigma_b(X)) \ge S_C(L, X)]}{B + 1}$$
   This automatically controls for any residual phonotactic density differences between the top-$K$ sets of Hebrew, Greek, Hittite, Hurrian, and Akkadian.

### 4.3 Calibration Gate (Zero Linear A Touched)
* Held-out prayers from **Hebrew** (20 disjoint Psalms/prayers), **Greek** (20 Hymns/votives), **Hittite** (10 CTH prayers), **Hurrian** (10 rituals), plus **25 fabricated/permuted control prayers** (`FAB-v2`, `PERM`).
* **Pass criterion:** Own-language liturgical arm wins $\ge 70\%$ of held-out prayers in each calibrated language, and $\le 5\%$ of fabricated/permuted prayers reach $p_{\text{perm}} \le 0.05$.

---

## 5. Kernel D — Pre-Linguistic Semantic Anchors (`anchors_d.py`)

* **Motivation:** The strongest non-circular channel in decipherment history (Ventris's tripod tablet; Bauer's Ugaritic ax). Meaning is fixed by **arithmetic or iconography before any language is named**.

### 5.1 Frozen Anchor Concept Table (Pre-Registered Before Scoring)
Only Linear A words whose semantic domain is established *independently of any Semitic reading* (cited to non-Semitic consensus in `BRIEF.html` §5 and *Ya Diktu* App. C.4–C.5):

| Anchor ID | Linear A Form(s) | Pre-Linguistic Evidence | Fixed Concept Slot |
|---|---|---|---|
| `ANC-01` | `KU-RO` | Sums entries above it on 9/16 testable faces (Davis 2026b, 8) | `TOTAL / ALL` |
| `ANC-02` | `PO-TO-KU-RO` | Sums two `KU-RO` totals on HT 122 (Schrijver 2014, 4) | `GRAND_TOTAL (EXTENT + TOTAL)` |
| `ANC-03` | `KI-RO` | Remainder / deficit outside `KU-RO` on HT 34, HT 123+124a (Schrijver 2014, 7) | `DEFICIT / OWED / REMAINDER` |
| `ANC-04` | `A-KA-NU` | Inked inside a cup/bowl (KN Zc 7) | `BOWL / CUP` |
| `ANC-05` | `SU-PU`, `SU-PA₃-RA`, `QA-PA₃`, `PA-TA-QE`, `KA-RO-PA₃` | Written directly beside vessel logograms on HT 31 | `VESSEL / CUP / BOWL / POT` |
| `ANC-06` | `KU-NI-SU`, `PA-RA` | Adjacent to / heading `GRA` (grain) entries | `GRAIN / WHEAT / EMMER / BARLEY` |
| `ANC-07` | `KA-DI` | Immediately precedes `VIN` (wine) on ZA 15b | `JAR / WINE_VESSEL` |

### 5.2 Bounded Synsets & Shared-Orthography Likelihood
1. For each concept slot $j$ and each candidate language $L \in \{\text{Semitic}, \text{Greek}, \text{Luwian/Hittite}, \text{Hurrian}, \text{Egyptian (cons-only)}\}$, a **blind builder** (or automated dictionary lookup on frozen standard glossaries: BDB/DULAT/CAD, LSJ, Kloekhorst/Melchert, Laroche, Erman-Grapow) extracts the **exact bounded synset** $\mathcal{S}_{L,j}$ of attested lexemes glossed with that concept (capped at $|\mathcal{S}_{L,j}| \le M$, e.g., $M = 10$ per slot, to guarantee equal degrees of freedom across languages).
2. Render every lexeme through `c_render.word` + glide rule with **one shared orthographic parameter vector** $\theta_{\text{ortho}}$ per language (e.g., `/l/ → R-series` is shared across `KU-RO` and `KI-RO` at zero extra parameter cost).
3. Compute the exact **anchor match log-likelihood** and test against **10,000 consonant-series grid permutations** $\sigma_b$:
   $$\text{LL}_D(L) = \sum_{j} \log \left(\frac{1}{|\mathcal{S}_{L,j}|} \sum_{u \in \mathcal{S}_{L,j}} \exp\!\big(-\beta \, d(x_j, \text{spell}(u; \theta_{\text{ortho}}))\big)\right)$$
4. **Calibration control:** Run the exact same anchor pipeline on **Linear B's own arithmetic/vessel anchors** (`to-so` = total, `o-pe-ro` = deficit, `ti-ri-po` = tripod, `di-pa` = vessel, `si-to` = grain, `wo-no` = wine) — the kernel must classify Linear B as **Greek** at $p_{\text{perm}} < 0.001$ and reject Semitic/Luwian/Hurrian!

---

## 6. Joint Aggregator, Output Ledger & Public CLI (`kaphtor-kernel`)

### 6.1 Hierarchical Combination Without Double-Counting
Because Kernels A, B, C, and D operate on **distinct, non-overlapping statistical summaries** (A: all-corpus word-internal CV n-grams; B: cross-document Kober stem-affix transitions; C: peak-sanctuary formula liturgical TF-IDF cohesion; D: arithmetic/vessel pre-linguistic anchors), we report:
1. **Each kernel's standalone margin, $Z_{\text{perm}}$, and permutation $p$-value** (so no single channel can hide behind an aggregate).
2. **Combined Fisher / Stouffer meta-statistic** across calibrated kernels that passed their own gate:
   $$Z_{\text{joint}}(L) = \frac{\sum_{c \in \mathcal{G}} Z_c(L)}{\sqrt{|\mathcal{G}|}}$$
   where $\mathcal{G} \subseteq \{A, B, C, D\}$ is the set of kernels that passed their pre-registered calibration gate before Linear A was unsealed.
3. **Conservative interpretation rule:** A joint Semitic claim is licensed only if (i) $\ge 2$ orthogonal calibrated kernels independently favor Semitic over every rival arm, (ii) the grid-permutation null rejects at $p_{\text{perm}} \le 0.01$ on each passing kernel, and (iii) leave-one-kernel-out and leave-one-site-out ablations are printed in full.

### 6.2 Reproducible Public CLI
Anyone can clone the repo (or point it at `linear-a.ai` API + frozen SHA-256 fallback) and run:
```bash
uv run kaphtor-kernel calibrate              # Runs G1-G4 + Linear B anchor control + prayer controls
uv run kaphtor-kernel run --strict-lb-only   # Primary run (secure Linear B values only, 10,000 grid perms)
uv run kaphtor-kernel ablate                 # Leave-one-kernel-out, omission vs. plene, proposed-signs sensitivity
```

---

## 7. Recommended Build Order

1. **Step 1 (Kernel A update — 30 min):** Adopt `pooled_signs` ($S = 3700$) in `lid.py` + update `test_lid.py` / `mutants.py`.
2. **Step 2 (Kernel B prototype — ~1 day):** Build `kober_b.py` on top of `c_align.py` and test `M_A + λ M_B` on the `dev` split to see if it kills the `latin`-absent outlier completely and passes G1–G4 under both omission and plene.
3. **Step 3 (Kernel D prototype — ~half day):** Build `anchors_d.py` with Linear B's own anchors (`to-so`, `o-pe-ro`, `ti-ri-po`, `di-pa`, `si-to`, `wo-no`) as the calibration gate and 10,000 grid permutations.
4. **Step 4 (Kernel C prototype — ~1 day):** Build `liturgy_c.py` using automated OSHB / Perseus / TLHdig / ORACC TF-IDF top-$K$ ($K=300$) liturgical lexicons and validate on held-out prayers before unsealing IO Za 2.
5. **Step 5 (Freeze, Sign, Unseal):** Hash all inputs/scripts, sign `SIGNATURE.txt`, run the gate split once, and—if all gates pass—run Linear A once and publish the complete bit-ledger regardless of outcome.
