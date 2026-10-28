# tools/core/frozen/protocol_c/scripts

| File | Pinned by | Purpose |
|---|---|---|
| `run_builder.sh` | the port | Phase C1: makes an arm's kit, probes a fresh Codex session, runs the build, audits every command the session ran for paths outside the kit, and copies the kit out with its `SHA256SUMS` |
| `check_inventory.py` | the port | Phase C1: checks an inventory against the schema, the blindness rule (§5.3 item 2) and the unit list, and writes `inventory.filled.json` |

Neither script is pinned by a hash the research tree recorded: each is hashed by the port, at the version that stands
after C1. That `run_builder.sh` differs from the one the six builds ran under in three changes the C1 manifest
records: its skill-disable list reaches `SKILL.md` at any depth, it writes `builder_model.txt` (for the six builds
that file was written after the run), and its copy-out takes dot-folders. `check_inventory.py` reads
`builder_model.txt` and accepts unit rows a builder accounted for row by row in `notes.md`; the research session reran
it on all six builds, and `protocol_c.py reproduce` reruns it here and requires each `inventory.filled.json` byte for
byte.

`run_builder.sh` also holds a Claude Code path (`MODEL`, `TOKEN_FILE`, `run_claude`), used for the Luwian pilot and
for no C1 build. Each script's hash and the text each substitution wrote in it are in
`data/linear-a/protocol-c/PORT-LEDGER.json`.
