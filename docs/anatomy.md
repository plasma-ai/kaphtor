---
name: docs/anatomy
title: Anatomy of the record
desc: How the repository is laid out, how its pages are named, and which pages are generated.
tags: [docs]
authors: "di Mino"
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Anatomy of the record

## Layout

The top-level folders are listed in the README's "Repository layout". Writing lives in `wiki/`, `docs/` and `data/`;
code lives in `tools/`, `tests/` and `skills/`. Every folder with two or more files has an `_index.md` (or, in the
code folders, a `README.md`) that names what it holds; the gate checks it.

## Naming

- An inscription: `wiki/linear-a/inscriptions/<site>/<series>/<key>.md`, by its corpus key.
- A word: `wiki/linear-a/words/<initial>/<FORM>.md`, hyphens written as underscores (`K/KU_RO.md`); a form that opens
  with an unvalued sign is under `star/`.
- A sign: `wiki/linear-a/signs/{syllabic,logograms,fractions}/`.
- A Semitic root: `wiki/semitic-roots/<radical>/<id>_<slug>.md`.
- A dataset: `data/<set>/<name>.json`, with its datasheet beside it as `<name>.md`, or a `MANIFEST.json` for a
  third-party set.

## Generated pages

Nothing in `wiki/` is written by hand. `tools/views/` builds it from `data/`, and `kaphtor gate` rebuilds it and fails
if the result differs from what is committed. To change a page, change the data or the builder.

## Prose

Corpus prose is timeless: no as-of dates, change logs or run logs. No copyrighted work enters verbatim.

*Not yet written:* the `_index.md` frontmatter keys and the `***` rule between generated and authored text.
