---
name: models/language-id-kernel/results-significance-2026-11-23
title: "Significance & Interpretation of the Ten-Kernel Suite (2026-11-23)"
desc: "Timestamped analytical report explaining what each of the ten probabilistic kernels (A–J) establishes, why its null model matters, how rival languages behaved, and where the honest methodological limits stand."
tags: [linear-a, probabilistic-model, analysis, significance, 2026-11-23]
created: 2026-11-23T21:05:00Z
updated: 2026-11-23T21:06:55Z
---

# Significance & Interpretation of the Ten-Kernel Suite (2026-11-23)

[[models/language-id-kernel/_index|..]]

***

**Snapshot:** `kaphtor v1.3.0` (`2026-11-23`), evaluated strictly under agreed Linear B syllabogram values (`--strict-lb-only`), zero LLMs, zero project-lexicon inputs, and fixed PRNG seeds (`20261122` / `20261123`). Every figure below is verified verbatim against the scripts and JSON ledgers in `models/language-id-kernel/runs/`.

---

## 1. How to Read the Ten Kernels Together

A common failure mode in undeciphered-script statistics is treating every positive score as equal proof. In a CV syllabary like Linear A, **surface fit alone is ambiguous**: an unrelated language that happens to share an `/a, i, u/`-dominant vowel inventory or short CV word lengths can beat Greek or Anatolian in raw perplexity even when its consonants are scrambled.

The ten-kernel suite is therefore organized around a **strict hierarchy of evidential specificity**:

1. **Primary Consonant-Specific Proofs (Kernels D, J, and I):** Independent lexical (**D**), zero-curation dictionary (**J**), and lexicon-free grammatical (**I**) tests that all pass real Linear B → Greek calibration gates and survive consonant-series and/or concept-label permutations on Linear A.
2. **Supporting & Auxiliary Consonant-Specific Channels (Kernels F, G, and C on `IO Za 2`):** Independent acrophonic, dialectal, and cultic-register tests that reinforce the primary channels while carrying narrower sample sizes or known boundary conditions.
3. **Macro-Typological, Exploratory, and Cultural-Milieu Diagnostics (Kernels A, B, E, and H):** Corpus-wide phonotactic, paradigm-transition, votive edge-frame, and personal-name tests that constrain Linear A's structural profile and Aegean cultural context without claiming consonant-specific proof on their own.

---

## 2. Kernel-by-Kernel Significance Analysis

### Kernel D — Pre-Linguistic Semantic Anchors (`anchors_d.py`)
- **Result:** Semitic wins `FULL_8` (`LL = -19.072` vs Hurrian `-32.656`, **`ΔLL = +13.585`**, **~794,000 : 1 Bayes factor**, **`Z_perm = +7.37`, `p = 0.00010`** over 10,000 swaps). Linear B calibrates cleanly as Greek (`Z = +7.97, p = 0.00010`; Semitic rejected at `p = 0.111`).
- **Why it matters:** This is the strongest single phonetic channel in the suite because the meanings of all eight Linear A anchors (`KU-RO`, `KI-RO`, `A-KA-NU`, `SU-PU`, `PA-TA-QE`, `KA-DI`, `KU-NI-SU`, `PA-RA`) are fixed by **tablet arithmetic or adjacent commodity/vessel pictograms** before any language is named — the same non-circular anchor logic that confirmed Ventris's Linear B decipherment on the Pylos tripod tablet (`TA 641`).
- **Why loanwords and single outliers cannot explain it away:** Across all 11 stress-test ablations (`runs/stress-test-cd-2026-11-22.json`), every single leave-one-anchor-out subset hits `p = 0.00010` (`Z = +6.45` to `+7.67`). Dropping all three Mediterranean trade-loan suspects (`A-KA-NU`, `KU-NI-SU`, `KA-DI`) still leaves a **~1,860 : 1 Bayes factor** (`ΔLL = +7.534, Z = +6.22, p = 0.00010`), and pure administrative arithmetic (`KU-RO`, `KI-RO`) alone remains significant (`ΔLL = +2.610, Z = +4.59, p = 0.00640`).
- **Residual critique addressed by Kernel J:** Because Kernel D uses curated 4–6 word synsets per concept, a skeptic could ask whether synset selection biased the result. Kernel J directly removes that degree of freedom.

### Kernel J — Zero-Curation Automated Dictionary Audit (`auto_anchors_j.py`)
- **Result (`v1.3.0` standalone, `runs/auto-anchors-j-standalone-2026-11-23.json`):** Semitic (shipped open Akkadian + Hebrew alone) is the **only language passing both orthogonal nulls** on Linear A `FULL_8`: **`ΔLL = +4.054`** (~57.6 : 1), **`Z_perm = +3.75, p_perm = 0.00010`** (10,000 consonant-grid swaps) and **`Z_concept = +1.93, p_concept = 0.02520`** (exact enumeration over all 5,040 distinct concept-label assignments). Both dense rivals collapse completely under concept shuffling: **CC0 ePSD2 Sumerian** (`3,589` lemmas) falls to **`p_concept = 0.63651`** (`Z = -0.50`), and **LSJ Greek** (`101,410` glosses) falls to **`p_concept = 0.58849`** (`Z = -0.26`). On the pre-Sumerian 5-language full set (`runs/auto-anchors-j-2026-11-23.json`), Semitic is again the only dual-null pass (`p_perm = 0.00010, p_concept = 0.00893` vs Hurrian `0.103`, Greek `0.548`, Anatolian `0.635`, Egyptian `0.911`). On Linear B, **Greek is the only dual-null pass** (`p_perm = 0.00010, p_concept = 0.01389`; Sumerian fails `p_perm = 0.0608`; Semitic rejected at `0.170 / 0.775`).
- **Why it matters:** Kernel J closes the researcher-degrees-of-freedom objection. No human selects candidate words; every dictionary is queried by identical English regexes, and marginal log-likelihood penalizes bloated synsets by $1/|C|$. Even more importantly, the **exact concept-label shuffle** holds Linear B sign values fixed and asks whether the words actually match *their assigned meanings* rather than simply sounding broadly Semitic or Sumerian. Both Greek and Sumerian pass weak consonant-grid swaps (`p_perm = 0.0055–0.0107`) through generic phonotactic proximity, then **collapse completely** (`p_concept > 0.58`) when concepts are shuffled — proving that only Semitic tracks the actual pre-linguistic meanings.
- **Honest boundary:** Running `--ligatures` on single-syllable adjuncts saturates an open 40-word dictionary (Linear B fails its Greek gate at `p = 0.348`), establishing multi-syllable anchors as the decisive open-dictionary test.

### Kernel I — Unsupervised Bound-Affix Morphology (`morphology_i.py`)
- **Result (`v1.3.0` standalone, `omission`, `B = 5,000`):** Across all 7 modeled families (`anatolian`, `greek`, `hattic`, `hurrian`, `latin`, `semitic`, `sumerian`), dev-split calibration passes **7 / 7 (100%)** (`p_cv = 0.00050`). On real Linear B tablets, **Greek is the only pass** (`M = +472.95, Z_M = +1.84, p_M = 0.02679`; Semitic rejected at `p_M = 0.875`). On Linear A's 505 strict-LB types (`p_pre = 0.419` vs ANE Semitic `0.393`), **Semitic is the only pass** at **`M = +40.03, Z_M = +2.63, p_M = 0.00360`** and **`Z_cv = +2.55, p_cv = 0.00040`** (all 6 rivals `p_M = 0.200–0.995`). On the full 7-member Semitic arm across 5 seeds (`runs/morphology-i-robustness-2026-11-23.json`), Semitic wins **5 / 5 seeds** (`mean M = +32.35, mean p_M = 0.03848`) and wins both administrative (`p_M = 0.04898`) and votive (`M = +5.04`) splits.
- **Why it matters:** Kernel I touches **zero semantic anchors and zero dictionaries**. It extracts bound prefixes and suffixes strictly by one-sided stem containment (`S` vs `p+S` / `S+s`) across the entire corpus. Because coronal/sonorant consonants (`T, R, M, N, S`) dominate grammatical suffixes across unrelated language families, permuting absolute likelihood lets non-matching languages pass `p_cv < 0.05`. Permuting each family's **discriminative margin over its strongest rival** $M_L(\pi) = \text{LL}_L(\pi) - \max_{R \neq L}\text{LL}_R(\pi)$ strips out universal suffix consonants cleanly: Greek alone survives on Linear B, and Semitic alone survives on Linear A. Training Semitic strictly on Bronze/Iron Age Ancient Near Eastern Semitic (Hebrew, Ugaritic, Akkadian — dropping Late Antique Arabic/Syriac/Geʿez) sharpens `p_M` by ~12× (`0.0436 -> 0.00360`).
- **Honest boundary:** The margin null requires `omission` mode (matching Linear A/B's unwritten codas); under `plene` echo-vowel spelling, `mean p_M` weakens to `0.599`.

### Kernel F — Commodity Ligature Acrophony (`acrophony_f.py`)
- **Result:** Semitic wins across 10 `GRA/OLE/VIN` commodity ligatures at **`ΔLL = +28.17, Z_perm = +5.53, p = 0.00010`** (`0/10,000`; every rival `Z <= -0.09`). On 6 Linear B ligatures, Greek wins (`Z = +4.31, p = 0.00070`) and Semitic is rejected (`p = 0.362`).
- **Why it matters:** Commodity adjuncts written inside `GRA`, `OLE`, and `VIN` logograms represent an independent administrative domain from standalone words. Passing the Linear B → Greek calibration gate confirms that acrophonic initial syllables carry genuine language signal when qualifier sets are tightly bounded.
- **Honest boundary:** Because single CV syllables saturate an open 40-word dictionary (Kernel J `--ligatures`), Kernel F is treated as an **auxiliary** channel rather than a standalone proof.

### Kernel G — Palaikastro Dialect Sound-Law Coherence (`dialect_g.py`)
- **Result:** **5 / 5** Central Crete ↔ Palaikastro minimal pairs (`JA-SA-SA-RA-ME / A-SA-SA-RA-ME`, `JA-DI-KI-TU / A-DI-KI-TE-TE`, `A-TA-I-*301-WA-JA / A-TA-I-*301-WA-E`, `U-NA-RU-KA-NA-SI / U-NA-RU-KA-NA-TI`, `I-PI-NA-MA / I-PI-NA-MI-NA`) conform to one 4-rule NWS phonological bundle (`JA->A`, `JA->E`, `SI->TI`, `MA->MI`), yielding **`Z_perm = +50.05, p = 0.00010`** against 10,000 random 4-rule bundles (`perm_mean = 0.00680`).
- **Why it matters:** Internal dialectal variation within the Minoan libation formula is structured rather than random — the exact sound shifts distinguishing Eastern Crete from Central Crete map onto classic Northwest Semitic isoglosses (initial glide weakening, final diphthong contraction, interdental reflex split).
- **Honest boundary:** Small sample (`n = 5` minimal pairs), so it serves as supporting internal evidence rather than a stand-alone identification.

### Kernel C — Size-Locked Liturgical Cohesion (`liturgy_c.py`)
- **Result (`v1.3.0` standalone, `K = 300`, `B = 1,000`):** On the canonical Mount Iouktas libation table `IO Za 2` (7 strict-LB words, `*301` opaque), **`hebrew_lit` ranks #1 (`Z = +3.04, p = 0.02697`)** and shipped CC0 **`akkadian_lit` ranks #2 (`Z = +1.67, p = 0.06294`)**, ahead of Hurrian (`+1.03`), Anatolian (`-0.31`), and Greek (`-0.66`). Calibrated on 104 Protocol D v3 controls (zero false positives on fabricated controls `FAB 0/10`, Luwian `0/8`, Hurrian `0/8`).
- **Why it matters:** Tests whether the peak-sanctuary prayer register independently pulls toward an automatically constructed, exact-size (`K = 300`) Biblical Hebrew cultic vocabulary (via Dirichlet log-odds on Psalms/Leviticus vs. prose) without any hand-selected religious wordlist.
- **Honest boundary:** Across all 41 undamaged words of the wider 33-vessel formula family (`runs/stress-test-cd-2026-11-22.json`), `hebrew_lit` stays #1 (`Z = +0.73`) but drops to `p = 0.231` once diluted by 34 site-specific proper names and dedicant/deity variants.

### Kernels A & B — Word-Shape Forward LID (`lid.py`) and Unsupervised Kober Trios (`kober_b.py`)
- **Result (`runs/kaphtor-kernel-linear-a-20261122T222434Z.json`):** Both rank **Semitic #1** across all 505 undamaged strict-LB Linear A types (**A:** `5.4902` bits/sign, `M = +0.6230` vs Hurrian `6.1133`; **B:** `22.3622` bits/transition, `M = +2.2880` vs Hurrian `24.6502`) after passing strict calibration gates (**A:** Linear B → Greek `1.0/1.0`; **B:** `62/62` dev accuracy). Yet **both fail consonant-grid permutation** (**A:** `Z_perm = -0.213, p = 0.587`; **B:** `Z_perm = -1.087, p = 0.846`).
- **Why this negative null result is valuable:** Kernels A and B demonstrate why raw perplexity cannot be trusted without a consonant-permutation control. They prove that Linear A shares Semitic's **broad `/a, i, u/` vowel-core and syllabic macro-typology**, while simultaneously proving that consonant-specific genetic signal lives in **bound morphology (Kernel I)** and **pre-linguistic semantic anchors (Kernels D & J)** rather than whole-corpus n-grams.

### Kernel E — Verbal Edge-Frames (`verbs_e.py`)
- **Result:** Passes `5 / 5` (100%) dev calibration (`budget = 1,986` `>=4`-sign types/arm) and ranks **`semitic_verbs` #1** on 46 non-administrative votive `>=4`-sign words (`25.059` bits/word, `M = +1.0561` vs Hurrian `26.115`), with consonant scrambling collapsing the margin from `+1.06` to `+0.16` (`Z_perm = +0.85, p = 0.20758`).
- **Why it matters & boundary:** Directionally consistent with Semitic prefix+suffix verbal frames on long votive words, but underpowered at `n = 46`; corpus-wide affix grammar is instead established by **Kernel I**.

### Kernel H — Structurally-Gated Roster Onomastics (`onomastics_h.py`)
- **Result (`v1.3.0` standalone, `n = 57`, `budget = 1,314`/arm, `B = 1,000`):** On 57 undamaged `>=3`-sign words immediately followed by `1` on administrative tablets, **`mycenaean_lb` ranks #1 (`5.8791`)** and shipped **`levant_semitic` (ORACC Ugarit/Amarna/Alalakh) ranks #2 (`6.1407`, `Z_perm = +1.56, p = 0.06494`)**, well ahead of **Kassite (`6.9268`)**, **Hurrian (`7.1879`)**, and **Anatolian (`7.4262`)**.
- **Why it matters:** Personal names cross linguistic borders and persist across dynastic shifts. Ranking Knossos/Pylos Linear B #1 reflects the well-known continuity of Minoan personal names into Mycenaean Knossos tablets, while Levantine Semitic placing #2 (`0.79–1.29` bits/sign ahead of Kassite, Hurrian, and Anatolian) points to Bronze Age Eastern Mediterranean onomastic affinity rather than standalone genetic proof.

---

## 3. Synthesis: What the Evidence Collectively Permits

Taken together, the ten kernels show a coherent split that matches linguistic expectations for a genuine language match rather than cherry-picked noise:

- **Three independent, non-circular channels converge on Semitic under strict Linear B values:** pre-linguistic lexical anchors (**Kernel D**, `~794,000:1`, surviving loanword removal at `~1,860:1`), zero-curation open-dictionary dual-null audit against LSJ Greek and CC0 ePSD2 Sumerian (**Kernel J**, `p_perm = 0.00010, p_concept = 0.02520` / `0.00893`), and unsupervised bound-affix morphology under a discriminative margin null (**Kernel I**, `M = +40.03, p_M = 0.00360, p_cv = 0.00040`).
- **Every calibrated instrument rejects Semitic and selects Greek on Mycenaean Linear B**, showing that neither the forward renderer nor the statistical nulls are biased toward Semitic.
- **What remains open:** An unattested extinct Aegean isolate outside the seven modeled language families/isolates is bounded by our four orthogonal permutation nulls and the CC0 Sumerian ePSD2 isolate control, not by a direct generative model; and cross-script testing on zero-Linear-A-sign Minoan witnesses (such as the Keftiu transcriptions in the London Medical Papyrus) remains an open next test.
