---
name: data/linear-a/protocol-c/builds
title: Protocol C blind builds
desc: The six blind inventories of phase C1, one per arm, each with its builder's kit, probe, redacted log, blindness audit, notes and hashes, and the C1 manifest.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C blind builds

[[data/linear-a/protocol-c/_index|..]]

[[data/linear-a/protocol-c/builds/BRIEF|BRIEF]]: The brief every blind builder of Protocol C was given, copied into each kit unchanged.

[[data/linear-a/protocol-c/builds/C1-MANIFEST|C1-MANIFEST]]: The C1 manifest of Protocol C: the six blind builds with their entry counts, probes, audits and inventory hashes, the blindness record, what is not part of C1, and the review points before rendering.

[[data/linear-a/protocol-c/builds/cs/_index|cs/]]: The Central Semitic build from Huehnergard 2019, Huehnergard 2005 and Huehnergard and Rubin 2011: 183 entries, 91 morphemes, 125 distinct realizations.

[[data/linear-a/protocol-c/builds/egyptian/_index|egyptian/]]: The Middle Egyptian build from Allen 2014: 116 entries, 56 morphemes, 53 distinct realizations.

[[data/linear-a/protocol-c/builds/greek/_index|greek/]]: The Mycenaean Greek build from Bartoněk 2003, with its one-entry correction: 382 entries, 112 morphemes, 166 distinct realizations.

[[data/linear-a/protocol-c/builds/hurrian/_index|hurrian/]]: The Hurrian build from Wegner 2000: 303 entries, 120 morphemes, 152 distinct realizations.

[[data/linear-a/protocol-c/builds/luwian/_index|luwian/]]: The Luwian build from Yakubovich 2015: 87 entries, 50 morphemes, 70 distinct realizations.

[[data/linear-a/protocol-c/builds/yd/_index|yd/]]: The build from Ya Diktu, the grammar under test: 52 entries, 35 morphemes, 36 distinct realizations.

***

Each inventory was written by a fresh, sandboxed OpenAI Codex CLI session (model gpt-6-astra, reasoning effort high)
with no skills, plugins, web search or user configuration; it holds only its kit; the C1 manifest gives the probe and
the audit. `run_builder.sh <arm> --codex` (in `tools/core/frozen/protocol_c/scripts/`) made each kit (the arm's
grammar, `units.md`, `schema.json`, `BRIEF.md`, the protocol extract), ran the probe, ran the session and the
blindness audit, and copied the kit out with its `SHA256SUMS`; `check_inventory.py` checked each `inventory.json`
(schema, blindness, coverage) and wrote `inventory.filled.json`. Distinct realizations count (side, segments) pairs,
as the checker does. The builds name their sources by the builders' citations; the grammars themselves are cited, not
shipped.

Blindness here means no corpus, no lexicon, no sign list and no thesis, not ignorance of the test's purpose: the kit's
protocol extract names Linear A and *Ya Diktu*. Writes were confined to the kit; reads were audited, not prevented,
and each audit found no command path outside the kit. Every `stderr.txt` logs Codex's startup skill scan reaching its
traversal limit and failing to load one nested file, `linear-a-decipherment/references/linear-b/SKILL.md` (it has no
frontmatter): the disable list then covered top-level `SKILL.md` files only, so that file was scanned. It did not
load, and the probe answered NONE. The runner shipped here disables `SKILL.md` at any depth. In the shipped
`stderr.txt` the Codex home is written `CODEX_HOME` and the skill path starts at the skill's folder.

Each build's log is shipped as `transcript.redacted.jsonl` (amendment A4): every event of the session's `--json`
log, with each command's output replaced by its sha256 (`output_sha256`) and byte length (`output_bytes`), and the kit
folder written `$KIT`. Commands, file changes and the builder's messages are whole. The full logs carry the grammars'
text and local paths and are kept privately; their sha256 are in each build's `SHA256SUMS` and in `PORT-LEDGER.json`,
and `protocol_c.py reproduce` reruns the blindness audit on the redacted logs. `inventory.filled.json` names the full
log (`transcript.jsonl`) as its transcript.

Not shipped: the grammar copies in each kit (`kit.sha256` hashes them), the *Ya Diktu* PDF and its text layer
([the published PDF](https://www.minoanmystery.org/linear-a/ya-diktu-grammar-tom-di-mino.pdf); amendment A3 pins its
sha256), the page renders the hurrian builder made (`hurrian/page_renders.sha256` hashes them), the full logs, and
three folders that are not part of C1 and that the manifest describes: the Claude Code Luwian pilot, the first Codex
Luwian pilot (not blind: it listed the user's skills), and the first `yd` build, set aside under amendment A3.
