---
name: ancient-near-east-research
description: Query the ancient Near East corpora and place and name authorities that kaphtor reads, locally where the data ships and one cited page at a time where it does not. Use for an Akkadian, Ugaritic, Aramaic or other ancient Near East personal or divine name, an ancient place (Pleiades, Trismegistos, iDAI.gazetteer), a DEAPS, DiCoNab, Elephantine or RSTI record, or which corpus holds a text and under what licence.
---

# Ancient Near East research

Every path here is relative to the kaphtor repository, the folder two levels above this file; in a Claude Code
plugin install that folder is `${CLAUDE_PLUGIN_ROOT}`. A plugin install does not download Git LFS files, so the
`.jsonl` datasets arrive as pointers (a file that begins `version https://git-lfs`); query them from a clone made
with Git LFS installed.

Use the query clients in `tools/ane/`; `tools/ane/README.md` lists each one, the source it reads and whether it runs
locally or fetches. Run a client from the repository root, with `--help` for its options, for example:

```sh
python3 tools/ane/query_place_authorities.py Knossos --authority pleiades --limit 3
```

The corpus guides in `docs/corpora/` say what each corpus holds, its licence and its gaps. Cite every record with
the citation its source gives. The remote clients fetch one page per call: never loop over result pages or treat the
cache as a corpus.

A dataset that cannot be redistributed is not in the repository. Its client says so and names the path it looked for,
and its corpus guide says where the corpus comes from.
