---
name: data/linear-a/protocol-c
title: Protocol C data
desc: The phase C0 and C1 record of Protocol C, the pre-registered blind-inventory test, with the signature and the port ledger; nothing rendered or scored.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C data

[[data/linear-a/_index|..]]

[[data/linear-a/protocol-c/PORT-LEDGER.json|PORT-LEDGER.json]]: Every shipped file's research path and sha256, what pins it, and the port's substitutions; every redacted log with the sha256 of its full log; every hashed file not shipped, with the reason.

[[data/linear-a/protocol-c/PROTOCOL-C-SIGNED-2026-10-29|PROTOCOL-C-SIGNED-2026-10-29]]: The Protocol C pre-registration as signed on 2026-10-29, before amendments A1–A4; SIGNATURE.txt records its sha256.

[[data/linear-a/protocol-c/SIGNATURE.txt|SIGNATURE.txt]]: The signature record: who signed, when, and the sha256 of the protocol at signature (5a7b442c…).

[[data/linear-a/protocol-c/builds/_index|builds/]]: The six blind inventories of phase C1, one per arm, each with its builder's kit, probe, redacted log, blindness audit, notes and hashes, and the C1 manifest.

[[data/linear-a/protocol-c/inventories/_index|inventories/]]: The phase C0 unit tables the blind builders transcribe, and the inventory schema.

[[data/linear-a/protocol-c/render/_index|render/]]: The renderer's phoneme-to-series table, fixed at C0.

***

Protocol C asks whether a grammar compiled blind, from a grammar book by a builder who never sees Linear A, predicts
the edges of Linear A word forms that no reading has used. The test, its nulls, its calibration gate and the wording
each outcome permits are set out in [the pre-registration](../../../docs/protocol-c-preregistration.md). These files
are its first two phases: C0 (the signed protocol, the unit tables, the schema and the renderer table) and C1 (the
six blind inventories). Phases C2–C6 are not built: no Linear A form has been rendered, no null drawn, nothing scored,
and the record is not frozen or tagged (§11). The frozen C1 scripts are in `tools/core/frozen/protocol_c/`.

`PROTOCOL-C-SIGNED-2026-10-29.md` is the text as signed; the protocol in `docs/` is that text with amendments A1–A4.
Each file is kept as the research tree holds it, but for the port's literal substitutions (private paths, private
source ids, the maintainer's first name, and frontmatter on the Markdown files). `PORT-LEDGER.json` records the text
each one wrote; the strings they replaced are in the maintainer's key, not shipped.
`tools/linear_a/validation/protocol_c.py verify` checks every file's shipped sha256, the research sha256 of every file
the port left unchanged, the build files against each build's `SHA256SUMS` and `kit.sha256`, and the inventories
against the C1 manifest; with `--key` it undoes the substitutions and checks every file against its research sha256
and the signed text against `SIGNATURE.txt`. `protocol_c.py reproduce` reruns the C1 checker and the blindness audit
([reproduce.md](../../../docs/reproduce.md)).

## Licences

| File | Licence |
| --- | --- |
| the protocol texts, `SIGNATURE.txt`, `PORT-LEDGER.json`, `inventories/TABLES-C0.md`, `inventories/schema.json`, `render/` | CC BY 4.0 |
| `inventories/tables/*.md` | CC BY 4.0: unit lists that cite the grammars by section and page |
| `builds/*/inventory*.json` | CC BY 4.0: the bound forms and short function labels transcribed from the cited grammars, which are cited, not quoted |
| `builds/*/notes.md`, `builds/hurrian/work/` | CC BY 4.0: the builders' own notes and scratch |
| `builds/*/*.redacted.jsonl` | CC BY 4.0: the builders' commands, file changes and messages; every command output is cut |
| every other file in `builds/` | CC BY 4.0 |
