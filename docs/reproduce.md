---
name: docs/reproduce
title: Reproduce
desc: What `kaphtor reproduce` reruns, what each headline number rests on, and the tolerance a rerun must meet.
tags: [docs]
authors: "di Mino"
created: 2026-10-22T18:14:10Z
updated: 2026-11-03T00:00:00Z
---

# Reproduce

`kaphtor reproduce` reruns the programs behind the headline numbers and compares each result with the recorded one.
`--quick` runs the short form of each. Until the harness is built, the command stops with exit status 2 and names this
page.

*Not yet written:* the numbers, each with the data and program it rests on, its recorded value and its tolerance.

## Paradigm B

The held-out paradigm-prediction test ([pre-registration](paradigm-b-preregistration.md),
[result](paradigm-b-result.md)) reruns from its frozen package with `tools/linear_a/validation/paradigm_b.py`, which
needs the `paradigm` extra (numpy, scipy; Python 3.12 or later):

```
uv run tools/linear_a/validation/paradigm_b.py verify
uv run --extra paradigm tools/linear_a/validation/paradigm_b.py reproduce --quick
uv run --extra paradigm tools/linear_a/validation/paradigm_b.py reproduce --full [--workers N]
uv run --extra paradigm tools/linear_a/validation/paradigm_b.py selftest
```

`verify` checks every shipped file against its sha256 and every file the port left unchanged against its frozen
sha256, SHA256SUMS against the freeze record (`f5d6733f…`), the four scripts PROTOCOL-B pins against its freeze
record, and each run's results against the run manifest's hash; it lists the 74 withheld files and does not fail on
them. `reproduce` rebuilds the frozen package in a temporary folder and runs it there; nothing is written under
`data/`. The 14 files the port changed (credit and private paths) run as shipped, the package's SHA256SUMS giving
their shipped sha256. The strings the port replaced are in the maintainer's key, not shipped; with it, `--key KEY`
restores every file to its frozen sha256 and rebuilds the package byte for byte.

| Run | Rests on | Recorded value | `--quick` | `--full` |
|---|---|---|---|---|
| observed family and 128 controls | `runs/…194551Z-paradigm-observed-strict-base.results.json` | A_free 0.860, A_cs 0.890, A_nws_floor 0.890, A_luwian 0.110, A_hurrian 0.311, A_egyptian 0.263, Δ 0.579, 57 scorable | rerun | rerun |
| gate | `runs/…194557Z-paradigm-gate-strict-base.results.json`, from the shipped observed run and null vectors | G1 pass (D mean 0.292, p95 0.500, r 0/10,000); G2 fail: AUC(Δ) 0.904 [0.809, 0.975] on 782 pairs, AUC(A_cs) 0.931 [0.844, 0.989], B-NEG-mycenaean_greek-02 Δ 0.25 against a band median of 0.00; G3: D2 Δ p95 0.187, mean −0.022, r 0; D2×2 r 0 | recomputed | recomputed |
| null D, seed 20260913 | `runs/…194512Z-…-null-D-…null_vectors.npy` | 10,000 × 8 | rows 0–199, one worker | all rows, and its results.json |
| null D2, seed 20260914 | `runs/…194527Z-…-null-D2-…null_vectors.npy` | 10,000 × 8 | rows 0–199, one worker | all rows, and its results.json |
| null D2×2, seed 20260915 | `runs/…194546Z-…-null-D2x2-…null_vectors.npy` | 10,000 × 8 | — | all rows, and its results.json |

Tolerance: every string, integer and boolean equal; every float within 1e-12 of the recorded value, NaN matching NaN,
on any platform; `wall_s` ignored. The report also says whether each result is bitwise identical; `--quick` is
bitwise identical on the machine that made the runs under Python 3.12 with numpy 2.5 and Python 3.13 with numpy 2.3. A replicate's seed fixes its result
whatever the number of workers. `--quick` takes under half a minute; `--full` about 15 s per null on 12 workers.

## Protocol C

The blind-inventory test ([pre-registration](protocol-c-preregistration.md)) has run phases C0 and C1 only: its six
inventories are built and hashed, and no Linear A form has been rendered or scored. Its record checks and its C1
checks rerun with `tools/linear_a/validation/protocol_c.py`; `reproduce` needs the `protocol-c` extra (jsonschema):

```
uv run tools/linear_a/validation/protocol_c.py verify
uv run --extra protocol-c tools/linear_a/validation/protocol_c.py reproduce [--arm ARM]
```

`verify` checks every shipped file against its sha256 and every file the port left unchanged against its research
sha256; every line of each build's `SHA256SUMS` and `kit.sha256` as shipped, derived or withheld; each
`inventory.filled.json` against the C1 manifest; and each kit against C0. It lists the 16 withheld grammar files and
does not fail on them. `reproduce` reruns on the files as shipped, in a temporary folder; nothing is written under
`data/`. The strings the port replaced (private paths, private source ids, the maintainer's first name) are in the
maintainer's key, not shipped; with it, `--key KEY` restores every file to its research sha256, the signed text to
`5a7b442c…` (`SIGNATURE.txt`), and the yd audit, where the cut name shortens a truncated command, byte for byte.

| Check | Rests on | Recorded value | Rerun |
|---|---|---|---|
| blindness word list | `data/linear-a/protocol-c-c1-words.txt`, the hyphenated words of the `corpus.json` `check_inventory.py` read in C1 | 1,070 hyphenated words, sha256 `e60a13f0…` (the research corpus gives the same list) | `reproduce`, which also reports how far today's `corpus.json` has moved from it |
| the six inventories | `builds/<arm>/inventory.json` and its kit, through `check_inventory.py` | `inventory.filled.json`: cs `73266e62…` (183 entries), yd `82fc1ef1…` (52), luwian `df9ba92e…` (87), hurrian `aee54daf…` (303), egyptian `a38b7715…` (116), greek `557c3b43…` (382) | `reproduce`, byte for byte |
| greek refusal | `builds/greek/inventory.v1.json` | refused: `greek_274`, corpus word `a-i` | `reproduce` |
| blindness audits | the audit in `run_builder.sh`, on each `*.redacted.jsonl` | cs 30 commands, yd 21, luwian 12, hurrian 21, egyptian 24, greek 35 and its correction 10; no path outside the kit | `reproduce`, byte for byte |
| redaction | the full logs and the key (maintainer only) | the sha256 in each build's `SHA256SUMS` | `reproduce --key KEY --transcripts DIR` |

Tolerance: none; every output must equal the shipped file byte for byte. `reproduce` takes about half a minute.

## D7

The structural test of Schrijver 2019's Hattic claims ([pre-registration](d7-structural-preregistration.md),
[result](d7-structural-result.md)) reruns its S3 on Linear A with `tools/linear_a/validation/d7_s3_linear_a.py`,
which writes only `--out` and refuses a file already there:

```
uv run python tools/linear_a/validation/d7_s3_linear_a.py --out d7-s3.json
```

| Count | Rests on | Recorded value | Rerun |
|---|---|---|---|
| word set | the recorded run's `corpus.json` (not shipped), sha256 `e256ff11…` | 639 types; set aside 322 with a lost sign, 186 with a damage mark | the default run |
| narrow X-TE / X-RE | the word set, 10,000 permutations, seed 20261102 | 1 against 0.418, p 0.3497 | the default run |
| narrow X / X-TE | as above | 2 against 1.427, p 0.423 | the default run |
| broad X-TE~TI / X-RE~RI | as above | 1 against 1.586, p 0.8296 | the default run |
| broad X / X-TE~TI | as above | 4 against 2.072, p 0.1472 | the default run |

The recorded run read a `corpus.json` that does not ship; the shipped corpus marks more broken edges, so its word set
differs and every expected value and p moves, while the observed counts hold. The
output gives the sha256 of the corpus it read: a run on the recorded corpus (`--corpus`) matches every count and p. The controls (S1 and S3 on the
rival languages' own texts) read corpora that do not ship. The run takes about 5 s.
