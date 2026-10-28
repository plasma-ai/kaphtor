---
name: data/linear-a/protocol-c/builds/hurrian
title: "Protocol C build: hurrian"
desc: The Hurrian build from Wegner 2000: 303 entries, 120 morphemes, 152 distinct realizations.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C build: hurrian

[[data/linear-a/protocol-c/builds/_index|..]]

[[data/linear-a/protocol-c/builds/hurrian/BRIEF|BRIEF]]: The builder brief in the hurrian kit, the text of builds/BRIEF.md.

[[data/linear-a/protocol-c/builds/hurrian/SHA256SUMS|SHA256SUMS]]: The sha256 of every file the build left, the full log included, as the runner wrote them.

[[data/linear-a/protocol-c/builds/hurrian/blindness_audit.txt|blindness_audit.txt]]: The audit of every command the session ran: 21 commands, no path outside the kit.

[[data/linear-a/protocol-c/builds/hurrian/builder_model.txt|builder_model.txt]]: The model and Codex CLI version the runner launched.

[[data/linear-a/protocol-c/builds/hurrian/grammar_files.txt|grammar_files.txt]]: The two grammar files in the kit, the PDF first.

[[data/linear-a/protocol-c/builds/hurrian/inventory.filled.json|inventory.filled.json]]: The checked inventory, with the runner's fields filled; its sha256 is in the C1 manifest.

[[data/linear-a/protocol-c/builds/hurrian/inventory.json|inventory.json]]: The inventory as the builder wrote it.

[[data/linear-a/protocol-c/builds/hurrian/kit.sha256|kit.sha256]]: The sha256 of every file in the kit, the grammar copies included.

[[data/linear-a/protocol-c/builds/hurrian/notes|notes]]: The hurrian builder's notes on the units, forms, segmentations and doubts, as written.

[[data/linear-a/protocol-c/builds/hurrian/page_renders.sha256|page_renders.sha256]]: The sha256 of the 53 page images the builder rendered from the grammar, which the runner deleted.

[[data/linear-a/protocol-c/builds/hurrian/probe.txt|probe.txt]]: The probe's answer before the build: no skills, no mention of the thesis, no email address.

[[data/linear-a/protocol-c/builds/hurrian/protocol|protocol]]: The protocol extract in the hurrian kit: §5.2–5.3 and amendments A1–A2, cut from the protocol by run_builder.sh.

[[data/linear-a/protocol-c/builds/hurrian/schema.json|schema.json]]: The kit's copy of the inventory schema.

[[data/linear-a/protocol-c/builds/hurrian/session_started_utc.txt|session_started_utc.txt]]: When the session started (2026-10-29T18:20:36Z).

[[data/linear-a/protocol-c/builds/hurrian/stderr.txt|stderr.txt]]: The session's error stream: the startup skill scan.

[[data/linear-a/protocol-c/builds/hurrian/transcript.redacted.jsonl|transcript.redacted.jsonl]]: The session's event log with every command output replaced by its sha256 and length.

[[data/linear-a/protocol-c/builds/hurrian/units|units]]: The hurrian unit list as given to the builder: tables/hurrian.md with its folder prefixes stripped.

[[data/linear-a/protocol-c/builds/hurrian/work/_index|work/]]: The hurrian builder's scratch, as left in its kit: the script that wrote its inventory and its coverage count.

***

The kit held Wegner's *Einführung in die hurritische Sprache* (2000) as PDF, which has no text layer, and its OCR
text; the builder rendered page images from the PDF to check the OCR, and the runner hashed and deleted them, since
they are copies of the book. Wegner's Tabelle 1–2 order (Suffixaufnahme) needs `s_pronoun` and `s_gender_number`
twice, and amendment A2 allows each slot once: the builder kept the template order and said so in `notes.md`. The
template therefore under-generates Hurrian suffix stacking; null L prices each arm against its own slots, so the
effect falls on Hurrian's power, not its calibration (the C1 manifest).
