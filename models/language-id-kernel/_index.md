---
name: models/language-id-kernel
title: "Linear A Multi-Kernel Probabilistic Language Identification Suite"
desc: "Replicable, zero-LLM twelve-kernel probabilistic framework (Kernels A–L: word-shape LID, Kober trios, liturgical cohesion, pre-linguistic anchors, verbal frames, ligature acrophony, dialect coherence, roster onomastics, bound-affix morphology, zero-curation dictionary audit, Corazza–Ferrara fractions, and backward-projection stress-testing) with permutation and corruption controls."
tags: [linear-a, probabilistic-model, language-identification, preregistration]
created: 2026-11-22T00:00:00Z
updated: 2026-11-25T02:30:26Z
---

# Linear A Multi-Kernel Probabilistic Language Identification Suite

[[models/_index|..]]

[[models/language-id-kernel/README|README]]: Executive summary, full twelve-kernel scoreboard, fresh-clone replication guide, Bologna adversarial vetting protocol, and index to all per-kernel specifications.

[[models/language-id-kernel/SIGNATURE.txt|SIGNATURE.txt]]: ...

[[models/language-id-kernel/acrophony_f.py|acrophony_f.py]]: ...

[[models/language-id-kernel/anchors_d.py|anchors_d.py]]: ...

[[models/language-id-kernel/auto_anchors_j.py|auto_anchors_j.py]]: ...

[[models/language-id-kernel/build_shipped_inputs.py|build_shipped_inputs.py]]: ...

[[models/language-id-kernel/dialect_g.py|dialect_g.py]]: ...

[[models/language-id-kernel/ferrara-vetting-guide|ferrara-vetting-guide]]: Five-command zero-LLM adversarial workbench enabling epigraphers to test, ablate, and attempt to falsify kaphtor's twelve-kernel Linear A suite in under two minutes.

[[models/language-id-kernel/fractions_k.py|fractions_k.py]]: ...

[[models/language-id-kernel/homomorph_l.py|homomorph_l.py]]: ...

[[models/language-id-kernel/kaphtor_kernel.py|kaphtor_kernel.py]]: ...

[[models/language-id-kernel/kernel-specs|kernel-specs]]: Design specification for the multi-kernel suite: each kernel's inputs, statistic, null and calibration gate.

[[models/language-id-kernel/kernels/_index|kernels/]]: Per-kernel technical specifications covering method, corpora called, calibration gates, verified Linear A ledgers, and honest limits for all twelve probabilistic kernels (A–L).

[[models/language-id-kernel/kober_b.py|kober_b.py]]: ...

[[models/language-id-kernel/lid.py|lid.py]]: ...

[[models/language-id-kernel/liturgy_c.py|liturgy_c.py]]: ...

[[models/language-id-kernel/morphology_i.py|morphology_i.py]]: ...

[[models/language-id-kernel/onomastics_h.py|onomastics_h.py]]: ...

[[models/language-id-kernel/pilot.py|pilot.py]]: ...

[[models/language-id-kernel/pilot_fix1.py|pilot_fix1.py]]: ...

[[models/language-id-kernel/preregistration-draft|preregistration-draft]]: Pre-registration draft for language identification by forward spelling: hypothesis, corpora, statistic, null and decision rule.

[[models/language-id-kernel/reference|reference]]: Complete mathematical specification, calibration gates, signed Linear A results, stress-test ablations, and methodological limits.

[[models/language-id-kernel/render/_index|render/]]: Frozen Linear B syllabary tables and the forward-spelling and alignment helpers the kernels read.

[[models/language-id-kernel/replication-guide|replication-guide]]: Master scoreboard, objectivity audit, shipped reference inputs, and fresh-clone reproduction instructions for all ten probabilistic language-identification kernels.

[[models/language-id-kernel/results-significance-2026-11-23|results-significance-2026-11-23]]: Timestamped analytical report explaining what each of the ten probabilistic kernels (A–J) establishes, why its null model matters, how rival languages behaved, and where the honest methodological limits stand.

[[models/language-id-kernel/results-significance-2026-11-24|results-significance-2026-11-24]]: Timestamped analytical report covering Kernel K (Corazza–Ferrara 2021 fraction verification and blind KU-RO discovery), Kernel L (backward-projection stress-testing and calibrated negative controls), and the twelve-kernel synthesis.

[[models/language-id-kernel/runs/_index|runs/]]: Timestamped JSON ledgers of the signed Linear A multi-kernel run, Kernel C and D stress-test ablations, and Kernels I, J, K, and L runs.

[[models/language-id-kernel/stress_test_cd.py|stress_test_cd.py]]: ...

[[models/language-id-kernel/tests/_index|tests/]]: Unit tests for Kernels B, C, D, F, G, H, I, J, K, and L and for the unified kaphtor_kernel.py command line.

[[models/language-id-kernel/verbs_e.py|verbs_e.py]]: ...

***

## 1. How This Was Developed (Lineage)

This folder supersedes the earlier standalone computational tests previously housed in `kaphtor` (preserved in `kaphtor` git history: `meaning_shuffle`, `paradigm_b`, `protocol_c`, and `d7_structural`; `shoresh` / `root_match` remains active alongside this suite with Amendments A24–A25) and the LLM-reader adjudication trials (`ioza2-adjudication` Protocols A–E).

Two empirical findings drove this redesign:
1. **The open-dictionary freedom wall (`D0-INFORMATION-BUDGET.md`):** Working *backward* from a Linear A word to a 62,201-entry Semitic dictionary gives ~43 bits of reader freedom against ~1 bit of evidence, and ~90% of arbitrary consonant skeletons find a match.
2. **LLM cost & pretraining contamination (Protocols D–E):** Language-model readers are expensive, non-deterministic, and retain prior exposure to published Linear A proposals.

In response, we built a **100% deterministic, zero-LLM, forward-spelled twelve-kernel suite (Kernels A–L)** that anyone can run locally, calibrated first on known ancient languages (including real Linear B tablets) before touching Linear A, and paired with **consonant-series grid-permutation**, **exact concept-label shuffle**, and **backward-projection corruption** controls.

## 2. Architecture: What Each Module Calls Upon and Tests

| File | Role | Inputs Called Upon | What It Tests |
|---|---|---|---|
| `kaphtor_kernel.py` | Unified CLI (`manifest`, `calibrate`, `run`, `ablate`) | All 4 kernels, `SIGNATURE.txt`, `corpus.json`, SHA-256 manifest | Runs primary channels A+B+D, supporting channel C, Stouffer meta-$Z$, and leave-one-channel-out ablations |
| `lid.py` (+ `pilot_fix1.py`) | **Kernel A** — Word-shape forward LID (`pooled_signs`, $S=3{,}700$, order 3) | OSHB (Hebrew/Aramaic), Quran (Arabic), ORACC (Akkadian/Sumerian/Urartian), TraCES (Geʿez), EUPT (Ugaritic), Ephrem (Syriac), TLHdig (Hittite/Luwian/Hurrian/Hattic), LSJ + Diodorus + DAMOS Linear B (Greek), LiLa LatInfLexi (Latin); Protocol C `c_render.py` + `c_align.py` | Corpus-wide phonotactics, vowel distribution, and CV n-gram fit across all 505 distinct legible strict-Linear-B Linear A word types |
| `kober_b.py` | **Kernel B** — Unsupervised Kober-trio / paradigm-delta model ($N_{\text{tr}}=2{,}900$) | Same forward-spelled training corpora + Protocol C `c_align.py` | Automatically extracted stem-sharing pairs/trios and prefix/suffix/stem-vowel transition distributions (Kober's "list of 3's") without hand-picking |
| `anchors_d.py` | **Kernel D** — Pre-linguistic semantic anchors ($B=10{,}000$ grid perms) | Bounded synsets (Semitic, Greek, Anatolian, Hurrian) + `c_render.py` + `c_align.py`; calibrated on Linear B's own 6 anchors (`TO-SO`, `O-PE-RO`, `TI-RI-PO`, `DI-PA`, `SI-TO`, `WO-NO`) | Words whose meanings are fixed by arithmetic or pictographic/container adjacency *before* any language is named (`KU-RO`, `KI-RO`, `A-KA-NU`, `SU-PU`, `PA-TA-QE`, `KA-DI`, `KU-NI-SU`, `PA-RA`) |
| `liturgy_c.py` | **Kernel C** *(Supporting)* — Size-locked liturgical lexical cohesion ($K=300$) | OSHB Psalms/Leviticus vs. prose (Dirichlet log-odds), shipped CC0 ORACC Akkadian, TLHdig rituals, Diodorus (plus optional Ephrem Syriac); calibrated on 104 Protocol D v3 controls | Whether `IO Za 2` (and the 33-vessel formula family) selectively matches an automated, size-locked Biblical Hebrew cultic vocabulary (`hebrew_lit` #1 `Z=+3.04, p=0.02697`; `akkadian_lit` #2 `Z=+1.67`) |
| `verbs_e.py` | **Kernel E** — Verbal edge-frame forward model (`>=4`-sign words) | OSHB `HV*` finite verbs vs. Diodorus Greek, TLHdig Hittite/Hurrian, LatInfLexi Latin; Linear A votive `>=4`-sign words (`Za/Zb/Zc/Zf/Zg`) | Whether non-administrative Linear A long words match Semitic prefix+suffix verbal frames better than suffixing Aegean/Anatolian rivals |
| `acrophony_f.py` | **Kernel F** — Commodity ligature acrophony ($B=10{,}000$ perms) | Bounded commodity-qualifier synsets (`OIL`, `GRAIN`, `WINE`, `TEXTILE`); calibrated on Linear B ligatures (`OLE+PA/WE/A`, `GRA+PE`, `TELA+TE/PU`) | Whether Linear A commodity adjuncts (`GRA+KU/PA/QE`, `OLE+KI/MI/DI/TA/NE/RI`, `VIN+RA`) match initial CV acrophones of Semitic qualifiers |
| `dialect_g.py` | **Kernel G** — Palaikastro dialect sound-law coherence ($B=10{,}000$) | 5 Central Crete ↔ Palaikastro minimal pairs (`GORILA`); 4-rule NWS phonological bundle (`JA->A`, `JA->E`, `SI->TI`, `MA->MI`) | Whether Eastern Crete formula shifts match attested NWS sound laws vs. random 4-rule bundles (`5/5`, `p=0.00010`) |
| `onomastics_h.py` | **Kernel H** — Structurally-gated roster onomastics ($B=1{,}000$) | Linear A `>=3`-sign words followed by `1` on admin tablets (`n=57`); shipped ORACC Levant LBA personal names (`1,314`), Kassite personal names (`3,795`), DAMOS Mycenaean LB, TLHdig Hurrian & Hittite | Cultural/onomastic milieu of structurally-identified personal-name slots without dictionary peeking (`mycenaean_lb` #1 `5.88`, `levant_semitic` #2 `6.14, Z=+1.56`) |
| `morphology_i.py` | **Kernel I** — Unsupervised bound-affix morphology & margin-permutation null ($B=5{,}000$) | Strict one-sided stem-containment affixes (`S` vs `p+S`/`S+s`) trained on shipped inflected corpora (Diodorus Greek, OSHB/EUPT/ORACC ANE Semitic, TLHdig, LatInfLexi) | Tests bound prefix/suffix polarity (`p_pre`) and CV-sign affix identity under a discriminative margin-permutation null ($M_L(\pi) = \text{LL}_L - \max_{R \neq L}\text{LL}_R$): 7/7 dev PASS; Linear B picks Greek (`M=+472.95, p_M=0.02679`); Linear A picks Semitic (`M=+40.03, Z_M=+2.63, p_M=0.00360, p_cv=0.00040` standalone; `5/5` seeds `mean p_M=0.0385` full) |
| `auto_anchors_j.py` | **Kernel J** — Zero-curation automated dictionary audit ($B=10{,}000$ grid perms + exact concept shuffle) | Shipped open JSONL lexica (`data/contact/{akkadian,hebrew}_lexicon.jsonl`, `lsj_glosses.jsonl` `101,410`, CC0 `sumerian_epsd2_lexicon.jsonl` `3,589`); fixed English concept regexes | Audits pre-linguistic anchors with zero hand-picked synsets under dual phonetic + semantic nulls: calibrates Linear B as Greek (`p_perm=0.00010, p_concept=0.01389`) and identifies Linear A as Semitic (`ΔLL=+4.05, p_perm=0.00010, p_concept=0.02520` standalone vs Sumerian `0.637` & Greek `0.588`; `0.00893` pre-Sumerian 5-lang) |
| `fractions_k.py` | **Kernel K** — Corazza–Ferrara (2021) fractions & blind accounting discovery ($B=5{,}000$) | Raw Aegean Unicode numerals & `A700` fraction glyphs in `data/linear-a/corpus.json`; Kernel J shipped open lexica | Language-free Stage K0–K1 emits 5-item 3D/RTI conflict ledger (`HT 123+124a`, `KH 7a`/`HT 89`, `MA 10b`, `A709/L`) and blindly surfaces `KU-RO` #1 (`9` exact integer sums); Stage K2 calibrates Linear B `TO-SO`/`O-PE-RO` as Greek (`p=0.01440`) and ranks Linear A `KU-RO`/`PO-TO-KU-RO`/`KI-RO` Semitic #1 (`Z=+2.86, p=0.01280, ΔLL=+0.551`) |
| `homomorph_l.py` | **Kernel L** — Backward-projection stress-testing & honest negative controls | `anchors_d.py`, `auto_anchors_j.py`, `morphology_i.py`, `kaphtor_kernel.py` | L1 homomorph-core & contested-series drops (`drop Q+Z M=+44.33 p=0.0020`, `drop T` collapses `p=0.265`), L2 L1SO jackknife (`8/8` D, `7/7` J on `p_perm`, J `p_concept` `2/7`), L3 Steele–Meißner corruption curve (`99.67%` Semitic rank-1 at `ε=0.2`), L4 calibrated nulls (A/B `Z_perm<0`, CH→LA acrophony `3/20`, live LB single-sign open-dict ligature saturation `p=0.395`) |
| `stress_test_cd.py` | Ablation & sensitivity runner | `anchors_d.py`, `liturgy_c.py`, `formula_family.json` | 11-way Kernel D leave-one-anchor-out + trade-loanword drop (110,000 perms) and Kernel C full-formula-family test |
| `build_shipped_inputs.py` | Reproducible corpus cut builder | Upstream open corpora (`--check` verifies bit-for-bit) | Cuts all 11 shipped Git LFS reference inputs under `data/share-alike/` |
| `kernels/` | Per-kernel reference specs (`a-word-shape.md` … `l-homomorph.md`) | All 12 kernels & `runs/*.json` ledgers | Dedicated technical page per kernel covering method, corpora called, calibration gate, results, and limits |
| `ferrara-vetting-guide.md` | Bologna adversarial vetting protocol | Kernels I, J, K, L | Five-command "Try to Break It" falsification workbench for INSCRIBE / SAPIENCE reviewers |
| `README.md` | GitHub landing guide | All 12 kernels & docs | Executive summary, full 12-kernel scoreboard, fresh-clone replication commands, and links to all docs |
| `results-significance-2026-11-24.md` | Timestamped `2026-11-24` findings | Kernels K & L & `runs/kernels-kl-2026-11-24.json` | Significance analysis of Kernels K & L, review caveats, and twelve-kernel synthesis |
| `results-significance-2026-11-23.md` | Timestamped baseline report | Kernels A–J & `runs/*.json` ledgers | Kernel-by-kernel statistical and linguistic interpretation, rival behavior, null analysis, and methodological limits |
| `reference.md` | Full technical reference | All calibration and signed Linear A run records | Equations, calibration gates, complete results ledger, permutation diagnostics, and scope/limits |
| `SIGNATURE.txt` | Freeze & authorization record | SHA-256 manifest of all 10 core files | Gates execution on Linear A (`kaphtor_kernel.py run` refuses without it) |

## 3. Quick Reproduction (Fresh Clone, Zero External Folders)

```bash
# 1. Run all kernel unit tests (29) + shipped-input count guards (8)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=models/language-id-kernel uv run --no-sync python -m pytest -q models/language-id-kernel/tests/ tests/test_kernel_shipped_inputs.py

# 2. Verify SHA-256 manifest, Linear B anchor calibration gate, and leave-one-channel-out ablation
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py manifest
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py calibrate --n-perm 10000
uv run --no-sync python models/language-id-kernel/kaphtor_kernel.py ablate models/language-id-kernel/runs/kaphtor-kernel-linear-a-20261122T222434Z.json

# 3. Run standalone Kernels C–L from shipped inputs
uv run --no-sync python models/language-id-kernel/liturgy_c.py --run-linear-a --n-perm 1000
uv run --no-sync python models/language-id-kernel/anchors_d.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/verbs_e.py --n-perm 500
uv run --no-sync python models/language-id-kernel/acrophony_f.py --calibrate --run-linear-a --n-perm 10000
uv run --no-sync python models/language-id-kernel/dialect_g.py --n-perm 10000
uv run --no-sync python models/language-id-kernel/onomastics_h.py --n-perm 1000
uv run --no-sync python models/language-id-kernel/morphology_i.py --mode omission --n-perm 5000
uv run --no-sync python models/language-id-kernel/auto_anchors_j.py --cap 40 --n-perm 10000
uv run --no-sync python models/language-id-kernel/fractions_k.py --n-perm 5000
uv run --no-sync python models/language-id-kernel/homomorph_l.py --stage all --n-perm 1000 --trials 300
```

See `README.md`, `kernels/_index.md`, `replication-guide.md` and `reference.md` for per-kernel specs, full calibration tables, signed results, and honest methodological boundaries.
