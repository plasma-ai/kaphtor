---
name: data/linear-a/protocol-c/builds/yd
title: "Protocol C build: yd"
desc: The build from Ya Diktu, the grammar under test: 52 entries, 35 morphemes, 36 distinct realizations.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C build: yd

[[data/linear-a/protocol-c/builds/_index|..]]

[[data/linear-a/protocol-c/builds/yd/BRIEF|BRIEF]]: The builder brief in the yd kit, the text of builds/BRIEF.md.

[[data/linear-a/protocol-c/builds/yd/SHA256SUMS|SHA256SUMS]]: The sha256 of every file the build left, the full log included, as the runner wrote them.

[[data/linear-a/protocol-c/builds/yd/blindness_audit.txt|blindness_audit.txt]]: The audit of every command the session ran: 21 commands, no path outside the kit.

[[data/linear-a/protocol-c/builds/yd/builder_model.txt|builder_model.txt]]: The model and Codex CLI version the runner launched.

[[data/linear-a/protocol-c/builds/yd/grammar_files.txt|grammar_files.txt]]: The Ya Diktu PDF and its text layer, the two grammar files in the kit.

[[data/linear-a/protocol-c/builds/yd/inventory.filled.json|inventory.filled.json]]: The checked inventory, with the runner's fields filled; its sha256 is in the C1 manifest.

[[data/linear-a/protocol-c/builds/yd/inventory.json|inventory.json]]: The inventory as the builder wrote it.

[[data/linear-a/protocol-c/builds/yd/kit.sha256|kit.sha256]]: The sha256 of every file in the kit, the PDF and its text layer included.

[[data/linear-a/protocol-c/builds/yd/notes|notes]]: The yd builder's notes on the units, forms, segmentations and doubts, as written.

[[data/linear-a/protocol-c/builds/yd/probe.txt|probe.txt]]: The probe's answer before the build: no skills, no mention of the thesis, no email address.

[[data/linear-a/protocol-c/builds/yd/protocol|protocol]]: The protocol extract in the yd kit: §5.2–5.3 and amendments A1–A3, cut from the protocol by run_builder.sh.

[[data/linear-a/protocol-c/builds/yd/schema.json|schema.json]]: The kit's copy of the inventory schema.

[[data/linear-a/protocol-c/builds/yd/session_started_utc.txt|session_started_utc.txt]]: When the session started (2026-10-29T19:09:13Z).

[[data/linear-a/protocol-c/builds/yd/stderr.txt|stderr.txt]]: The session's error stream: the startup skill scan and one refused edit.

[[data/linear-a/protocol-c/builds/yd/transcript.redacted.jsonl|transcript.redacted.jsonl]]: The session's event log with every command output replaced by its sha256 and length.

[[data/linear-a/protocol-c/builds/yd/units|units]]: The yd unit list as given to the builder: tables/yd.md with its folder prefixes stripped.

***

The `yd` arm is not blind: it is the grammar under test (§5.3 item 5). Its kit held the published *Ya Diktu* PDF at
commit `d9a3f93` (amendment A3; the runner refuses a PDF whose sha256 is not `d111b8db…`) and its `pdftotext -layout`
text; neither is shipped ([the published PDF](https://www.minoanmystery.org/linear-a/ya-diktu-grammar-tom-di-mino.pdf)).
Its 35 morphemes stand against the 36 of `TABLES.md`: the builder declined the statements that print no form, and
`notes.md` gives the disposition of every unit row. It labelled Appendix B collectively, since the appendix title
names what the brief forbids it to write, and accounted for rows 36–59 one by one in `notes.md`; the checker accepts
that table and fails if a row is missing from it. The log's largest commands write `inventory.json` whole. The error
in `stderr.txt` is one patch Codex refused (two operations on one file); the kit folder is written `$KIT` there.
