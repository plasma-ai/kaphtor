---
name: linear-a-decipherment
description: Read and check the kaphtor record of Linear A, covering its inscriptions, words, signs, the proposed readings with their confidence tiers, and the Semitic roots they cite. Use for a Linear A inscription (HT 13, IO Za 2, a GORILA or RILA-S1 number), a word such as KU-RO, a sign value, a reading's tier, evidence or rivals, or the Eteocretan inscriptions.
---

# Linear A research

Answer from the record in this repository, not from memory. Give every reading with its tier, and name the rival
readings the record lists beside it. The tiers and the tests behind them are in `docs/confidence.md`.

Every path here is relative to the kaphtor repository, the folder two levels above this file; in a Claude Code
plugin install that folder is `${CLAUDE_PLUGIN_ROOT}`. A plugin install does not download Git LFS files: if
`corpus.json` or `semitic_roots.json` begins `version https://git-lfs`, it is a pointer, and the data is read from a
clone made with Git LFS installed.

## Where the record is

| Question | Page | Data |
|---|---|---|
| An inscription | `wiki/linear-a/inscriptions/<site>/<series>/` | `data/linear-a/corpus.json`, `translations.json` |
| A word | `wiki/linear-a/words/<initial>/` | `data/linear-a/lexicon.json`, `onomasticon.json` |
| A sign | `wiki/linear-a/signs/` | `data/linear-a/sign_values.json` |
| Every reading by tier | `wiki/linear-a/standing.md` | `data/linear-a/lexicon.json` |
| A Semitic root | `wiki/semitic-roots/<radical>/` | `data/semitic-roots/semitic_roots.json` |
| What the corpus holds | `docs/corpus-census.md` | `data/linear-a/corpus.json` |

Each dataset has a datasheet beside it (`<name>.md`) with its schema, licence and counts.

## Commands

From the repository root, `uv run --no-sync kaphtor gate` checks the repository. The Linear A query tools (search,
paradigms, accounting and sign tests) are in `tools/linear_a/`, listed in its `README.md`; run one with `--help` for
its options.
