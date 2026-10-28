# tools/core/frozen/protocol_c

The phase C1 scripts of Protocol C, the pre-registered blind-inventory test, as the research tree held them when the
port pinned them; nothing in Protocol C is frozen yet (the freeze is phase C5). Its pre-registration is
[docs/protocol-c-preregistration.md](../../../../docs/protocol-c-preregistration.md); its C0 and C1 record is in
`data/linear-a/protocol-c/`.

| Folder | Holds |
|---|---|
| `scripts/` | the runner that built each blind inventory and the checker that checked it ([its README](scripts/README.md)) |

Nothing here is run in place. `tools/linear_a/validation/protocol_c.py` checks each script against its shipped
sha256, imports the checker and runs the blindness audit cut from the runner, in a temporary folder. Kept byte for
byte but for literal substitutions of private paths, each recorded in `data/linear-a/protocol-c/PORT-LEDGER.json`;
the strings they replaced are in the maintainer's key, with which `protocol_c.py verify --key` checks each script
against its pinned sha256.

`run_builder.sh` keeps its kit folder, `pcb/<arm>` under the macOS system temporary folder: the one absolute path left
in the shipped tree, kept because it is the builder's environment as recorded, a neutral folder outside any
repository and with no user name in it. The redacted logs write it `$KIT`. Its other paths are
written `research-tree` and `minoanmystery-astro`, the two checkouts it read, and its own refusal test for a local
path in `units.md` is written `"/Users" "/"`, the same string. `check_inventory.py` names its corpus
`linear-a-decipherment/data/corpus.json`; `protocol_c.py` points it at this repository's `data/linear-a/corpus.json`,
which yields the same 1,070 hyphenated words.
