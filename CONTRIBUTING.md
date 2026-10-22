# Contributing

Readings, rival analyses, falsifications, sources, corrections and tools are welcome, from people or agents.

## Issues

Report a misread sign or a failed reading as an issue. The templates cover a reading, a falsification, a rival
hypothesis and a rights concern.

## Pull requests

A new reading enters at tier 1 and rises only by passing the tests in [docs/confidence.md](docs/confidence.md). A
rival analysis sits beside the reading it contests; it does not replace it.

Change the data, not the pages: everything in `wiki/` is generated from `data/` (see
[docs/anatomy.md](docs/anatomy.md)).

## Copyright

No copyrighted work enters verbatim. Cite a closed source by siglum and page, and say what it holds in your own
words. A dataset is added to `data/` only when its licence allows redistribution, and its datasheet's `license` key
names that licence.

*Not yet written:* the full rights rules, and how to attribute a correction drawn from a published edition.

## Checks

Before opening a pull request, run:

```sh
uv sync --all-groups
uv run --no-sync pre-commit install
uv run --no-sync kaphtor gate
```

`uv run --no-sync kaphtor gate --list` names each check and whether it is built yet.
