---
name: data/linear-a/protocol-c/builds/hurrian/BRIEF
title: "Builder brief"
desc: "The builder brief in the hurrian kit, the text of builds/BRIEF.md."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Builder brief

You are transcribing one grammar's bound morphology into a JSON inventory. Work only from the files in your working
directory:

- The grammar files listed in `grammar_files.txt` and named in `units.md` (a PDF, EPUB-derived Markdown, OCR
  Markdown, or a PDF's text layer as `.txt`; where a PDF and a text file are the same book, the PDF governs where
  they differ).
- `units.md`: the list of units (tables, lists, headed sections) you must transcribe, with section and page.
- `schema.json`: the format your output must follow.
- `protocol.md`: the rules this inventory is built under (§5.2 categories, §5.3 blindness, §16 amendments A1 and A2).

## The task

1. Read every unit listed in `units.md`, in the grammar, at the page given. Read the whole unit.
2. For each unit, transcribe every realization of every bound form in the §5.2 categories (nominal, pronominal,
   verbal, clitic). A realization is one written form: a morpheme the grammar gives in two shapes is two entries
   that share a `morpheme_id`.
3. Take nothing from outside the listed units, and add nothing from your own knowledge of this or any other
   language. If the grammar prints a form, it goes in; if it does not, it stays out, however certain you are that it
   exists.
4. Free words stay out: independent, demonstrative and interrogative pronouns, numerals, free particles. A form the
   grammar itself calls bound, clitic or enclitic goes in.
5. Copy each `form` exactly as printed (hyphens, equals signs, asterisks, parentheses). Split it into `segments`, one
   phoneme per string, in the grammar's own symbols. Where the grammar marks an optional segment with parentheses,
   enter both realizations (the same printed `form`, different `segments`). Do not enter zero endings (Ø); list
   them in `notes.md`. Where the grammar uses a cover symbol (a capital letter standing for two sounds), keep it as
   one segment and say so in `notes.md`.
6. File each entry under a `slot` by the category the grammar gives it (protocol.md, A2). Use the template order in
   `class_order` unless the grammar states a different order among the slots; then use the grammar's order and cite
   the statement in `class_order.basis`.
7. `function` states what the grammar says the form does, in the grammar's own language and terms.
8. `source` gives the unit label as it appears in `units.md`, the section and the printed page.
9. List every unit you read in `units_read`. Put any unit that yielded no entry in `units_without_entries` with the
   reason.

## Output

- Write `inventory.json`, valid against `schema.json`. In `builder`, write `"model": "runner"`,
  `"session_started_utc": "1970-01-01T00:00:00Z"` and `"transcript_file": "runner"`; in `grammar.file_sha256`, write
  64 zeros. The runner fills these in.
- Write `notes.md`: forms you could not read, segmentations you were unsure of, any place the grammar's own tables
  disagree with each other, and any rule in this brief you found hard to apply. Do not resolve a doubt by guessing:
  record it here.

## Never

- Never write the words Linear A, Minoan, a Linear A sign value or a Linear A word anywhere in your output.
- Never compare a form with any other language, and never choose a reading because it resembles one.
- Never edit `units.md`, `schema.json`, `protocol.md` or the grammar.
