---
name: models/cypro-minoan-kernel
title: "Cypro-Minoan Deterministic Statistical Kernel Suite"
desc: "Zero-LLM, T5-compliant statistical kernel suite (CM-G, CM-E, CM-O, CM-B) testing Cypro-Minoan subcorpora, IG XV 1 Amathus Eteocypriot continuity, orthographic glide laws, and stem productivity strictly from shipped kaphtor files."
tags: [cypro-minoan, probabilistic-model, eteocypriot]
created: 2026-11-25T13:25:00Z
updated: 2026-11-25T18:21:23Z
---

# Cypro-Minoan Deterministic Statistical Kernel Suite

[[models/_index|..]]

[[models/cypro-minoan-kernel/README|README]]: Zero-LLM, T5-compliant statistical kernel suite for Cypro-Minoan running strictly on shipped kaphtor datasets with V-vs-CV permutation nulls, 3-regime 013/008 sensitivity, and CM 3 / Linear B controls.

[[models/cypro-minoan-kernel/cm_kernel.py|cm_kernel.py]]: Self-contained stdlib CLI (`manifest`, `run`, `check`) implementing Kernels CM-G, CM-E, CM-O, and CM-B strictly on shipped `kaphtor` datasets.

[[models/cypro-minoan-kernel/runs/_index|runs/]]: Timestamped SHA-256-verified JSON run ledger for the deterministic Cypro-Minoan statistical kernel suite.

[[models/cypro-minoan-kernel/tests/_index|tests/]]: Unit tests for cm_kernel.py covering Amathus IG XV 1 parsing, regime sensitivity, orthographic glide laws, stem productivity, determinism, and T3 isolation.

***

Deterministic, zero-LLM statistical kernel suite for Cypro-Minoan (`CM-G`, `CM-E`, `CM-O`, `CM-B`) running strictly on shipped `kaphtor` datasets with zero Linear A inputs (`T3` firewall) and zero raw Valério 2016 Appendix A sign-group transcriptions (`T5` compliant). See `README.md` for the full scoreboard and reproduction commands.
