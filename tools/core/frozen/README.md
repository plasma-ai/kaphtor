# tools/core/frozen

Code that a pre-registration froze or pinned: Shoresh's tagger, Paradigm B's package and Protocol C's phase C1
scripts. Each file is kept byte for byte (in `paradigm_b/` and `protocol_c/`, but for the ledgered substitutions their
verifiers undo with the maintainer's key); its user checks the sha256 before running it and stops on any change. A change needs an amendment to
the pre-registration (see [`SHORESH.md`](../SHORESH.md),
[the Paradigm B pre-registration](../../../docs/paradigm-b-preregistration.md) or
[the Protocol C pre-registration](../../../docs/protocol-c-preregistration.md)) and a new pinned hash.

| File | Pinned by | Purpose |
|---|---|---|
| `tag_semantic_fields.py` | `semantic_gate.TAGGER_SHA256` (A18) | The domain tagger: keyword rules that give a root's gloss its semantic domains |
| `paradigm_b/` | `data/linear-a/paradigm-b/PORT-LEDGER.json` (SHA256SUMS, PROTOCOL-B's freeze record) | Paradigm B's frozen package: runner, statistic, nulls, renderer and selftest ([its README](paradigm_b/README.md)) |
| `protocol_c/` | `data/linear-a/protocol-c/PORT-LEDGER.json` (pinned at the port; Protocol C is not yet frozen) | Protocol C's C1 runner and inventory checker ([its README](protocol_c/README.md)) |

`semantic_gate.py` executes the tagger's source after the hash check and uses its functions; the file is not run as a
script in this repository, so the paths and the `--apply` option in its docstring describe the project it came from.
