---
name: data/linear-a/paradigm-b/runs
title: Paradigm B runs
desc: The five production runs Paradigm B made under its freeze, the observed family and controls, nulls D, D2 and D2×2 at 10,000 replicates and the gate, each with its manifest.
tags: [data, linear-a, paradigm-b]
sources: []
license: CC BY 4.0
created: 2026-10-29T15:12:45Z
updated: 2026-10-29T15:12:45Z
---

# Paradigm B runs

[[data/linear-a/paradigm-b/_index|..]]

[[data/linear-a/paradigm-b/runs/20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.manifest.json|20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.manifest.json]]: Null D's command line, time and SHA256SUMS hash.

[[data/linear-a/paradigm-b/runs/20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.null_vectors.npy|20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.null_vectors.npy]]: Null D, a copied formula with noise: 10,000 replicates × the eight statistics, seed 20260913.

[[data/linear-a/paradigm-b/runs/20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.results.json|20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913.results.json]]: Null D's per-statistic mean, sd, 95th percentile and NaN count.

[[data/linear-a/paradigm-b/runs/20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.manifest.json|20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.manifest.json]]: Null D2's command line, time and SHA256SUMS hash.

[[data/linear-a/paradigm-b/runs/20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.null_vectors.npy|20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.null_vectors.npy]]: Null D2, a formula with a random shared affix inventory: 10,000 replicates, seed 20260914.

[[data/linear-a/paradigm-b/runs/20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.results.json|20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914.results.json]]: Null D2's summary, with the residue inventory it drew from (k = 8, k′ = 32).

[[data/linear-a/paradigm-b/runs/20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.manifest.json|20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.manifest.json]]: Null D2×2's command line, time and SHA256SUMS hash.

[[data/linear-a/paradigm-b/runs/20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.null_vectors.npy|20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.null_vectors.npy]]: Null D2×2, D2 with both inventories doubled: 10,000 replicates, seed 20260915.

[[data/linear-a/paradigm-b/runs/20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.results.json|20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915.results.json]]: Null D2×2's summary.

[[data/linear-a/paradigm-b/runs/20261009T194551Z-paradigm-observed-strict-base.manifest.json|20261009T194551Z-paradigm-observed-strict-base.manifest.json]]: The observed run's command line, time and SHA256SUMS hash.

[[data/linear-a/paradigm-b/runs/20261009T194551Z-paradigm-observed-strict-base.results.json|20261009T194551Z-paradigm-observed-strict-base.results.json]]: The family's A per arm, Δ, per-fold hits, and every control window's statistics.

[[data/linear-a/paradigm-b/runs/20261009T194557Z-paradigm-gate-strict-base.manifest.json|20261009T194557Z-paradigm-gate-strict-base.manifest.json]]: The gate's command line, naming the four runs it read.

[[data/linear-a/paradigm-b/runs/20261009T194557Z-paradigm-gate-strict-base.results.json|20261009T194557Z-paradigm-gate-strict-base.results.json]]: G1, G2 and G3, the class means, and no posterior.

***

Each run was a folder `runs/<run>/` in the research package; here its files are `<run>.<file>`. All five ran in the
gate configuration (strict vowels, base inventories, leave-one-site-out folds) under SHA256SUMS f5d6733f…, which each
manifest records. The eight columns of a null array are `A_free`, `A_cs`, `A_nws_floor`, `A_luwian`, `A_hurrian`,
`A_egyptian`, `delta` and `delta_floor`. The run manifest's `results_sha256` for each results file is in
`PORT-LEDGER.json`.
