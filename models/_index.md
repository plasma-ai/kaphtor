---
name: models
title: Models
desc: Replicable computational and probabilistic models for Linear A language identification and Cypro-Minoan statistical analysis.
tags: [models, linear-a, cypro-minoan]
created: 2026-11-22T00:00:00Z
updated: 2026-11-25T18:21:23Z
---

# Models

[[_index|..]]

[[models/cypro-minoan-kernel/_index|cypro-minoan-kernel/]]: Zero-LLM, T5-compliant six-kernel statistical suite (CM-G, CM-E, CM-O, CM-B, CM-I, CM-H) testing Cypro-Minoan subcorpora, IG XV 1 Amathus Eteocypriot continuity vs. 7 ancient language families, orthographic glide laws, stem productivity, and clay-ball onomastics strictly from shipped kaphtor files.

[[models/language-id-kernel/_index|language-id-kernel/]]: Replicable, zero-LLM twelve-kernel probabilistic framework (Kernels A–L: word-shape LID, Kober trios, liturgical cohesion, pre-linguistic anchors, verbal frames, ligature acrophony, dialect coherence, roster onomastics, bound-affix morphology, zero-curation dictionary audit, Corazza–Ferrara fractions, and backward-projection stress-testing) with permutation and corruption controls.

***

Deterministic, zero-LLM probabilistic and statistical model suites for Linear A (`language-id-kernel/`) and Cypro-Minoan (`cypro-minoan-kernel/`), kept strictly isolated under T3 so Linear A models never read Cypro-Minoan data and Cypro-Minoan models never read Linear A data.
