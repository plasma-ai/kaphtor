---
name: data/linear-a/protocol-c/builds/greek
title: "Protocol C build: greek"
desc: The Mycenaean Greek build from Bartoněk 2003, with its one-entry correction: 382 entries, 112 morphemes, 166 distinct realizations.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C build: greek

[[data/linear-a/protocol-c/builds/_index|..]]

[[data/linear-a/protocol-c/builds/greek/BRIEF|BRIEF]]: The builder brief in the greek kit, the text of builds/BRIEF.md.

[[data/linear-a/protocol-c/builds/greek/SHA256SUMS|SHA256SUMS]]: The sha256 of every file the build and its correction left, both full logs included, as the runner wrote them.

[[data/linear-a/protocol-c/builds/greek/blindness_audit.txt|blindness_audit.txt]]: The audit of every command the build session ran: 35 commands, no path outside the kit.

[[data/linear-a/protocol-c/builds/greek/builder_model.txt|builder_model.txt]]: The model and Codex CLI version the runner launched.

[[data/linear-a/protocol-c/builds/greek/correction-stderr.txt|correction-stderr.txt]]: The correction session's error stream: the startup skill scan.

[[data/linear-a/protocol-c/builds/greek/correction-transcript.redacted.jsonl|correction-transcript.redacted.jsonl]]: The correction session's event log with every command output replaced by its sha256 and length.

[[data/linear-a/protocol-c/builds/greek/correction_blindness_audit.txt|correction_blindness_audit.txt]]: The audit of every command the correction session ran: 10 commands, no path outside the kit.

[[data/linear-a/protocol-c/builds/greek/grammar_files.txt|grammar_files.txt]]: The three grammar files in the kit, the OCR text first.

[[data/linear-a/protocol-c/builds/greek/inventory.filled.json|inventory.filled.json]]: The checked inventory, with the runner's fields filled; its sha256 is in the C1 manifest.

[[data/linear-a/protocol-c/builds/greek/inventory.json|inventory.json]]: The inventory after the correction session restated one function string.

[[data/linear-a/protocol-c/builds/greek/inventory.v1.json|inventory.v1.json]]: The builder's first inventory, which the checker refused.

[[data/linear-a/protocol-c/builds/greek/kit.sha256|kit.sha256]]: The sha256 of every file in the kit, the grammar copies included.

[[data/linear-a/protocol-c/builds/greek/notes|notes]]: The greek builder's notes on the units, forms, segmentations and doubts, as written.

[[data/linear-a/protocol-c/builds/greek/probe.txt|probe.txt]]: The probe's answer before the build: no skills, no mention of the thesis, no email address.

[[data/linear-a/protocol-c/builds/greek/protocol|protocol]]: The protocol extract in the greek kit: §5.2–5.3 and amendments A1–A2, cut from the protocol by run_builder.sh.

[[data/linear-a/protocol-c/builds/greek/schema.json|schema.json]]: The kit's copy of the inventory schema.

[[data/linear-a/protocol-c/builds/greek/session_started_utc.txt|session_started_utc.txt]]: When the build session started (2026-10-29T18:20:04Z).

[[data/linear-a/protocol-c/builds/greek/stderr.txt|stderr.txt]]: The build session's error stream: the startup skill scan.

[[data/linear-a/protocol-c/builds/greek/transcript.redacted.jsonl|transcript.redacted.jsonl]]: The build session's event log with every command output replaced by its sha256 and length.

[[data/linear-a/protocol-c/builds/greek/units|units]]: The greek unit list as given to the builder: tables/greek.md with its folder prefixes stripped.

***

The kit held Bartoněk's *Handbuch des mykenischen Griechisch* (2003) as OCR text and as two PDFs. The checker refused
the first inventory: `greek_274`'s function string quoted Bartoněk's syllabic spelling "-A-I", which is also a Linear A
corpus word (§5.3 item 2). A fresh correction session, sandboxed and probed the same way, restated that one function
from p. 167 and changed nothing else (`inventory.v1.json` against `inventory.json`). 92 entries carry Bartoněk's
syllabic spelling in `form` beside the phonemic segments he pairs with it; they collapse into the shapes of their
phonemic twins and add no realization. The builder's scratch folder `.work/` was not copied out (the runner then
skipped dot-folders).
