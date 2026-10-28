# tools/core/frozen/paradigm_b

The code of Paradigm B, the pre-registered held-out paradigm-prediction test, as frozen on 2026-10-09 in the research
package it was built in, in that package's layout. Its pre-registration is
[docs/paradigm-b-preregistration.md](../../../../docs/paradigm-b-preregistration.md) and its outcome
[docs/paradigm-b-result.md](../../../../docs/paradigm-b-result.md); its frozen data and runs are in
`data/linear-a/paradigm-b/`.

| Folder | Holds |
|---|---|
| `scripts/` | the runner, the renderer, the selftest, and the build-time scripts shipped for transparency |
| `scripts/common/` | the statistic, the nulls, the statistics helpers, the sign matcher and the package paths |
| `vendor/` | the frozen sign table and phoneme tokenizer |

Nothing here is run in place. `tools/linear_a/validation/paradigm_b.py` rebuilds the frozen package in a temporary
folder (code and data at their frozen paths) and runs it there, so `scripts/common/paths.py` resolves as it did at
the freeze. Kept byte for byte but for literal substitutions of the attribution and of private paths in docstrings
and constants, each recorded in `data/linear-a/paradigm-b/PORT-LEDGER.json`; the package runs them as shipped, its
SHA256SUMS giving their shipped sha256. The strings they replaced are in the maintainer's key, with which
`paradigm_b.py --key` restores every file to its frozen sha256.

`vendor/skeleton.py` is the sign table the runs used (`*86` = ṇa, no `*324`); it is not
`tools/core/skeleton.py`, and swapping one for the other changes the null vectors. `scripts/render_la.py` is pinned
at the port: neither SHA256SUMS nor PROTOCOL-B's freeze record hashes it.
