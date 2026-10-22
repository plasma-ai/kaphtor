# kaphtor: agent guide

kaphtor is an open record of Linear A (corpus, signs, lexicon, translations) with a Semitic root database and
query tools for the ancient Near East corpora. Python 3.11+, managed with uv; the
tools run on the standard library. The README says what the record holds; [docs/anatomy.md](docs/anatomy.md) says
how it is laid out and named.

## Commands

Run from the repository root.

- Set up: `uv sync --all-groups`, then `uv run --no-sync pre-commit install`
- Gate (everything): `uv run --no-sync kaphtor gate`; `kaphtor gate --list` names each step and whether it is built
- Tests: `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -m pytest` (`-m unit` for inline-input tests only)
- Check the generated pages: `uv run --no-sync python -m tools.views.build --data data/linear-a --out wiki`
  (`--write` writes them, after a backup)
- Check the census blocks: `uv run --no-sync python -m tools.views.census_doc --data data/linear-a`
- Lint the wiki: `uv run --no-sync wiki lint`
- Query an ANE corpus: `python3 tools/ane/<client>.py --help` (the clients are listed in `tools/ane/README.md`)

## Structure

- `data/`: the datasets, each with a datasheet `<name>.md` or a manifest giving its licence (the gate checks it)
- `wiki/`: pages generated from `data/` by `tools/views/`
- `docs/`: rules, methods and corpus guides
- `tools/`: the `tools` package behind `kaphtor`: `tools/core/` (the shared library), `tools/ane/` (the query
  clients), `tools/views/` (the page builder), `tools/cli/` (the command); data paths in `tools/paths.py`
- `skills/`: the two agent skills; `.claude-plugin/`: their Claude Code plugin manifests
- `tests/`: `tests/linear_a/`, `tests/ane/`, `tests/views/`, and the repository checks at the top level

## Conventions

- Readings carry their tier and their rivals; the tiers and promotion tests are in
  [docs/confidence.md](docs/confidence.md).
- Corpus prose is timeless: no as-of dates, change logs or run logs.
- The project's own readings and notes are attributed to "di Mino".
- Cite a closed source by siglum and page, in your own words.

## Boundaries

- **Always:** run the gate before opening a pull request; start a bug fix with a test that reproduces it, and show a
  new test failing before the change that makes it pass.
- **Ask the maintainer first:** before adding a dataset or a dependency, changing a reading's tier, changing an
  expected count or generated page in a test (name the cause), or touching `tools/core/frozen/` (pinned by sha256).
- **Never edit `wiki/` by hand:** change the data or the builder, and rebuild.
- **Never copy copyrighted text:** cite it by siglum and page; a dataset enters `data/` only under a licence that
  allows it, named in its datasheet's `license` key.
- **Never write into `data/` from a test:** use `tmp_path`; `tests/conftest.py` fails the run on any change there.
- **Never weaken a test to pass a run:** fix the code, or show that the expectation is wrong.
- **Never put an absolute or home-folder path in the tree:** use `tools/paths.py`, or `KAPHTOR_DATA` for data kept
  elsewhere (a pre-commit hook rejects such paths).
- **Never let a reading skip a tier:** it rises one tier at a time, by that tier's test.

## Troubleshooting

- A command prints `stopped: <file> is not in this checkout` and exits 2: that dataset is not shipped or not yet
  added; its corpus guide in `docs/corpora/` says where it comes from, and `KAPHTOR_DATA` points the tools at
  another folder.
- A data file begins `version https://git-lfs`: it is a Git LFS pointer. Install Git LFS, then `git lfs pull`.
- `wiki` is not found: run `uv sync --all-groups` (it comes with the `lint` group) and call it through `uv run`.
- The `maintainer` tests skip: they need data that is not shipped.
