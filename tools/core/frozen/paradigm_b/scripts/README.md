# tools/core/frozen/paradigm_b/scripts

| File | Pinned by | Purpose |
|---|---|---|
| `run_paradigm.py` | PROTOCOL-B freeze record | The runner: `null` (D, D2, D2×2 replicates), `observed` (the family and the control windows), `gate` (G1–G3, and the posterior only if G1 and G2 pass) |
| `render_la.py` | the port | The forward renderer of phonemic forms into Linear A signs, used by the inventories and the control windows |
| `selftest_b.py` | PROTOCOL-B freeze record | The option B selftest (PROTOCOL-B §8) |
| `build_paradigm.py` | PROTOCOL-B freeze record | Build time: wrote the inventories in `data/linear-a/paradigm-b/paradigm/` and enforced the blindness and parity rules |
| `build_windows_b.py` | PROTOCOL-B freeze record | Build time: cut the control windows of `controls_b.jsonl` from sources outside the package |
| `freeze_protocol.py` | the port | Build time: wrote SHA256SUMS and the freeze record |

The build-time scripts read files the port does not ship and are not run here. Each script's hash and the
substitutions made in it are in `data/linear-a/paradigm-b/PORT-LEDGER.json`.
