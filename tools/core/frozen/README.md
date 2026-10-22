# tools/core/frozen

Code that Shoresh pre-registered and froze. Each file is kept byte for byte; its user checks the sha256 before
running it and stops on any change. A change needs an amendment to the pre-registration (see
[`SHORESH.md`](../SHORESH.md)) and a new pinned hash.

| File | Pinned by | Purpose |
|---|---|---|
| `tag_semantic_fields.py` | `semantic_gate.TAGGER_SHA256` (A18) | The domain tagger: keyword rules that give a root's gloss its semantic domains |

`semantic_gate.py` executes the tagger's source after the hash check and uses its functions; the file is not run as a
script in this repository, so the paths and the `--apply` option in its docstring describe the project it came from.
