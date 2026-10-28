---
name: data/linear-a/paradigm-b/freeze-record
title: Paradigm B freeze record
desc: The record the option B freeze appended to the research package's PROTOCOL.md, copied verbatim; the run refuses to start without it.
tags: [data, linear-a, paradigm-b]
license: CC BY 4.0
authors: "di Mino"
created: 2026-10-29T00:00:00Z
updated: 2026-10-29T00:00:00Z
---

The third freeze record of the research package's `PROTOCOL.md` (lines 142–148), copied byte for byte between the
markers below. `freeze_protocol.py --refreeze "option B freeze"` wrote it; `run_paradigm.py` refuses a production
run unless `PROTOCOL.md` carries its `refreeze_reason`, so `tools/linear_a/validation/paradigm_b.py` writes this
block as `PROTOCOL.md` into the package it rebuilds. `sha256sums_sha256` is the sha256 of
[SHA256SUMS](SHA256SUMS), which `paradigm_b.py verify` checks.

<!-- freeze-record:begin -->
## Freeze record

- frozen_at: 2026-10-09T19:44:46.441569+00:00
- repo_head: 545179bef80d2d4be349f624fb8525d51302b16b
- files_hashed: 89
- sha256sums_sha256: f5d6733fbf922c951b5e690725cdedf6fda4bf52747c59e284807efc351cd7ca
- refreeze_reason: option B freeze
<!-- freeze-record:end -->
