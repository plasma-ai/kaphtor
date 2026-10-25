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

## Method: compound names

To find names in `data/linear-a/onomasticon.json` that split like DA-MI-NU (ḏā "he of" + MI-NU):

1. Take names of 3+ signs with no reading or no root; split each at every sign boundary and count each part alone
   and inside other words in `corpus.json`.
2. Keep a split when both parts recur, or one part is a known morpheme: DA/DU/DI ḏā/ḏū/ḏī "he of", JA-/I- prefix,
   A- 1cs, -JA hypocoristic, -TE/-TI feminine, or a theonym (A-DU, NA-SI, MI-NU).
3. Rank by the tablet's company (the same list or heading slot as a read compound), twin spellings, and a
   sign-for-sign match in a name catalogue (Gelb AS 21 by name number, Huffmon, NPN, DULAT, Pagan's Ebla names),
   for each part or for the whole name word for word (Ebla i-du na-sa yidu-naḥša for I-DU-NE-SI).
4. Give each part its root and meaning under every parse. The lexicon entry carries the root, its
   `semitic_roots.json` id, one to three spelling analogs and the rivals, never the full reflex set.
5. Read a tail as a title when a source writes name + title (Minaean lwʾtn S¹lmy "the priestess Salmay" for
   TI-MA-RU-WI-TE Tīmar-lēwīt). A coda may go unwritten at the join: the r of Tīmar before the l of lēwīt.
6. A catalogue's own spelling licenses a sign value: Gelb writes ṭaybatum DA-BA-TUM, so DA writes ṭ in DA-I-PI-TA.
7. Vocalize the reading as spoken, gemination and length restored: Ṭayyibat, not Ṭaybat.
8. Confirm every cited form against its catalogue row or page image, an agent's citations included, before it
   enters the data.

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
