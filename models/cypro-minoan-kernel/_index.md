---
name: models/cypro-minoan-kernel
title: "Cypro-Minoan Deterministic Statistical Kernel Suite"
desc: "Zero-LLM, T5-compliant six-kernel statistical suite (CM-G, CM-E, CM-O, CM-B, CM-I, CM-H) testing Cypro-Minoan subcorpora, IG XV 1 Amathus Eteocypriot continuity vs. 7 ancient language families, orthographic glide laws, stem productivity, and clay-ball onomastics strictly from shipped kaphtor files."
tags: [cypro-minoan, probabilistic-model, eteocypriot]
created: 2026-11-25T13:25:00Z
updated: 2026-11-25T20:40:25Z
---

# Cypro-Minoan Deterministic Statistical Kernel Suite

[[models/_index|..]]

[[models/cypro-minoan-kernel/README|README]]: Zero-LLM, T5-compliant six-kernel statistical suite for Cypro-Minoan running strictly on shipped kaphtor datasets with V-vs-CV and consonant-series discriminative margin permutation nulls, in-script Cypriot Greek calibration, and CM 3 / Linear B controls.

[[models/cypro-minoan-kernel/cm_kernel.py|cm_kernel.py]]: Self-contained stdlib CLI (`manifest`, `run`, `check`) implementing Kernels CM-G, CM-E, CM-O, and CM-B strictly on shipped `kaphtor` datasets.

[[models/cypro-minoan-kernel/cm_kernel_ih.py|cm_kernel_ih.py]]: Self-contained stdlib CLI (`manifest`, `run`, `check`) implementing Kernels CM-I1 (7-family bound-affix rival exclusion), CM-I2 (8-way size-matched Amathus EC vs. 7 families), and CM-H (clay-ball roster onomastics & acrophony).

[[models/cypro-minoan-kernel/runs/_index|runs/]]: Timestamped SHA-256-verified JSON run ledgers for the deterministic Cypro-Minoan statistical kernel suite.

[[models/cypro-minoan-kernel/tests/_index|tests/]]: Unit tests for cm_kernel.py and cm_kernel_ih.py covering Amathus IG XV 1 parsing, Cypriot Greek calibration, regime sensitivity, orthographic glide laws, stem productivity, clay-ball onomastics, determinism, and T3 isolation.

***

Deterministic, zero-LLM six-kernel statistical suite for Cypro-Minoan (`CM-G`, `CM-E`, `CM-O`, `CM-B`, `CM-I`, `CM-H`) running strictly on shipped `kaphtor` datasets with zero Linear A inputs (`T3` firewall) and zero raw Valério 2016 Appendix A sign-group transcriptions (`T5` compliant). See `README.md` for the full scoreboard and reproduction commands.
