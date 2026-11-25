---
name: models/language-id-kernel/kernels
title: "Individual Kernel Reference Docs (Kernels A–L)"
desc: "Per-kernel technical specifications covering method, corpora called, calibration gates, verified Linear A ledgers, and honest limits for all twelve probabilistic kernels (A–L)."
tags: [linear-a, probabilistic-model, kernels, reference]
created: 2026-11-23T19:35:00Z
updated: 2026-11-25T02:10:00Z
---

# Individual Kernel Reference Docs (Kernels A–L)

[[models/language-id-kernel/_index|..]]

[[models/language-id-kernel/kernels/a-word-shape|a-word-shape]]: Pooled sign-parity Witten-Bell 3-gram CV language identification across all 505 undamaged strict-Linear-B Linear A word types.

[[models/language-id-kernel/kernels/b-kober-trios|b-kober-trios]]: Unsupervised extraction and hierarchical Witten-Bell modeling of stem-sharing paradigm transitions (Kober pairs and trios) over strict-Linear-B words.

[[models/language-id-kernel/kernels/c-liturgy|c-liturgy]]: Dirichlet log-odds Biblical Hebrew cultic vocabulary and shipped CC0 Akkadian vs size-locked K=300 rival vocabularies scored on IO Za 2 and the 33-vessel formula family.

[[models/language-id-kernel/kernels/d-anchors|d-anchors]]: Bayesian marginal log-likelihood over eight arithmetic, vessel, and grain anchors fixed before any language is named, with 11-way ablations.

[[models/language-id-kernel/kernels/e-verbal-frames|e-verbal-frames]]: Equal-budget Witten-Bell word-edge model (pre1, pre2, suf1, suf2) comparing Semitic finite verbs against long-word rivals on 46 Linear A votive words.

[[models/language-id-kernel/kernels/f-acrophony|f-acrophony]]: Tests whether Linear A commodity adjunct signs (GRA/OLE/VIN) match initial CV acrophones of Semitic qualifiers, calibrated on Linear B.

[[models/language-id-kernel/kernels/g-dialect|g-dialect]]: Tests whether five Central Crete vs Palaikastro libation-formula minimal pairs conform to a single 4-rule Northwest Semitic isogloss bundle.

[[models/language-id-kernel/kernels/h-onomastics|h-onomastics]]: Compares 57 structurally-identified Linear A personal-name slots (WORD 1) against shipped Bronze Age onomastic pools without dictionary peeking.

[[models/language-id-kernel/kernels/i-morphology|i-morphology]]: Strict one-sided stem-containment prefix/suffix polarity and CV-affix identity tested under a discriminative margin-permutation null.

[[models/language-id-kernel/kernels/j-auto-anchors|j-auto-anchors]]: Audits pre-linguistic anchors with zero hand-picked synsets over shipped open JSONL lexica (including CC0 ePSD2 Sumerian) under dual phonetic and semantic nulls.

[[models/language-id-kernel/kernels/k-fractions|k-fractions]]: Applies Corazza, Ferrara, Montecchi, Tamburini & Valério (2021) A700 fraction values to raw Unicode glyphs to emit a 3D/RTI conflict ledger, blindly discover KU-RO at rank #1, and score only the accounting triad under Linear B Greek calibration.

[[models/language-id-kernel/kernels/l-homomorph|l-homomorph]]: Operationalizes Steele & Meißner (2017) and Salgarella (2020) backward-projection caution alongside Valério & Ferrara (2020), Ferrara, Montecchi & Valério (2022), and Ottaviano et al. (2026) via homomorph-core ablations, L1SO jackknives, corruption curves, and calibrated negative controls.

***

Each document below isolates one kernel in `models/language-id-kernel/`, recording its exact script, statistical model, shipped reference corpora, known-language calibration gate, verbatim Linear A run numbers, and methodological limits. All twelve kernels run deterministically with zero LLMs, zero project-lexicon inputs, and strict Linear B sign values alone.

| Channel Group | Kernel | Script | Role |
| --- | --- | --- | --- |
| Macro-Typology | [[models/language-id-kernel/kernels/a-word-shape|Kernel A: Word-Shape LID]] | `lid.py` + `pilot_fix1.py` | Primary macro-typology (`A+B+D`) |
| Macro-Typology | [[models/language-id-kernel/kernels/b-kober-trios|Kernel B: Unsupervised Kober Trios]] | `kober_b.py` | Primary macro-typology (`A+B+D`) |
| Register | [[models/language-id-kernel/kernels/c-liturgy|Kernel C: Liturgical Cohesion]] | `liturgy_c.py` | Supporting (`IO Za 2` & vessel family) |
| Lexical Anchors | [[models/language-id-kernel/kernels/d-anchors|Kernel D: Pre-Linguistic Anchors]] | `anchors_d.py` | **Primary phonetic proof** (`A+B+D`) |
| Morphology | [[models/language-id-kernel/kernels/e-verbal-frames|Kernel E: Verbal Edge-Frames]] | `verbs_e.py` | Exploratory (votive `>=4`-sign) |
| Lexical Anchors | [[models/language-id-kernel/kernels/f-acrophony|Kernel F: Ligature Acrophony]] | `acrophony_f.py` | Auxiliary phonetic |
| Dialect | [[models/language-id-kernel/kernels/g-dialect|Kernel G: Palaikastro Dialect]] | `dialect_g.py` | Supporting phonological coherence |
| Onomastics | [[models/language-id-kernel/kernels/h-onomastics|Kernel H: Roster Onomastics]] | `onomastics_h.py` | Cultural/onomastic milieu |
| Morphology | [[models/language-id-kernel/kernels/i-morphology|Kernel I: Bound Affix Morphology]] | `morphology_i.py` | **Primary grammatical proof** |
| Lexical Anchors | [[models/language-id-kernel/kernels/j-auto-anchors|Kernel J: Zero-Curation Dict Audit]] | `auto_anchors_j.py` | **Primary anti-bias audit** |
| Metrology | [[models/language-id-kernel/kernels/k-fractions|Kernel K: Corazza–Ferrara Fractions]] | `fractions_k.py` | **Accounting-only confirmation + 3D ledger** |
| Robustness | [[models/language-id-kernel/kernels/l-homomorph|Kernel L: Backward-Projection Audit]] | `homomorph_l.py` | **Adversarial stress-test & negative controls** |
