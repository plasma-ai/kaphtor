---
name: data/linear-a/protocol-c/builds/luwian
title: "Protocol C build: luwian"
desc: The Luwian build from Yakubovich 2015: 87 entries, 50 morphemes, 70 distinct realizations.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C build: luwian

[[data/linear-a/protocol-c/builds/_index|..]]

[[data/linear-a/protocol-c/builds/luwian/BRIEF|BRIEF]]: The builder brief in the luwian kit, the text of builds/BRIEF.md.

[[data/linear-a/protocol-c/builds/luwian/SHA256SUMS|SHA256SUMS]]: The sha256 of every file the build left, the full log included, as the runner wrote them.

[[data/linear-a/protocol-c/builds/luwian/blindness_audit.txt|blindness_audit.txt]]: The audit of every command the session ran: 12 commands, no path outside the kit.

[[data/linear-a/protocol-c/builds/luwian/builder_model.txt|builder_model.txt]]: The model and Codex CLI version the runner launched.

[[data/linear-a/protocol-c/builds/luwian/grammar_files.txt|grammar_files.txt]]: The two grammar files in the kit, the PDF first.

[[data/linear-a/protocol-c/builds/luwian/inventory.filled.json|inventory.filled.json]]: The checked inventory, with the runner's fields filled; its sha256 is in the C1 manifest.

[[data/linear-a/protocol-c/builds/luwian/inventory.json|inventory.json]]: The inventory as the builder wrote it.

[[data/linear-a/protocol-c/builds/luwian/kit.sha256|kit.sha256]]: The sha256 of every file in the kit, the grammar copies included.

[[data/linear-a/protocol-c/builds/luwian/notes|notes]]: The luwian builder's notes on the units, forms, segmentations and doubts, as written.

[[data/linear-a/protocol-c/builds/luwian/probe.txt|probe.txt]]: The probe's answer before the build: no skills, no mention of the thesis, no email address.

[[data/linear-a/protocol-c/builds/luwian/protocol|protocol]]: The protocol extract in the luwian kit: §5.2–5.3 and amendments A1–A2, cut from the protocol by run_builder.sh.

[[data/linear-a/protocol-c/builds/luwian/schema.json|schema.json]]: The kit's copy of the inventory schema.

[[data/linear-a/protocol-c/builds/luwian/session_started_utc.txt|session_started_utc.txt]]: When the session started (2026-10-29T18:20:04Z).

[[data/linear-a/protocol-c/builds/luwian/stderr.txt|stderr.txt]]: The session's error stream: the startup skill scan.

[[data/linear-a/protocol-c/builds/luwian/transcript.redacted.jsonl|transcript.redacted.jsonl]]: The session's event log with every command output replaced by its sha256 and length.

[[data/linear-a/protocol-c/builds/luwian/units|units]]: The luwian unit list as given to the builder: tables/luwian.md with its folder prefixes stripped.

***

The kit held Yakubovich's *The Luwian Language* (2015 manuscript) as PDF and text layer. The builder read Tables 2,
3, 5, 7 and 8; the participle and infinitive are prose under "6.5 Verb" and stay out (`TABLES.md`). Its scratch
folder `.review/` was not copied out (the runner then skipped dot-folders). The Claude Code pilot that tested the
format, not part of C1, matches this build in 69 of its 70 distinct forms (the C1 manifest).
