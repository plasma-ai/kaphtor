# Tests

The test suite: unit, data and maintainer tiers.

- [ane/](ane/README.md): offline tests for the `tools/ane/` query clients, the data paths and the name layers (9 files, 238 tests)
- [linear_a/](linear_a/README.md): tests for the `tools/core/` library, the Shoresh engine and commands, and the corpus
  analyses (43 files, 1,299 tests, 628 of them on the shipped data)
- [pre_greek/](pre_greek/README.md): tests of the Pre-Greek lexicon in `data/pre-greek/` (1 file, 33 tests, 10 of them
  on the shipped data)
- [views/](views/README.md): tests for the record wiki's builder in `tools/views/` (6 files, 165 tests, 9 of them on
  the live Linear A data, 1 on the shipped Pre-Greek lexicon and 1 that runs plasma-wiki's `wiki`)
- [fixtures/](fixtures/README.md): the Shoresh gold set and its baseline, byte for byte as deposited

- `test_data_guard.py`: the data guard below, each case a small pytest session on its own data folder (7 tests)
- `test_lfs.py`: every PDF and every data file over 1 MB matches a Git LFS rule in `.gitattributes` (2 tests)
- `test_network_guard.py`: the network guard below, each case a small pytest session (5 tests)
- `test_plugin.py`: the plugin manifests against `pyproject.toml`, the README's install lines and the skills (4 tests)
- `test_cli.py`: the `kaphtor` command's gate and reproduce, on stand-in steps; the index-coverage and licence checks
  on scratch trees; the gate's pre-commit stage runs no fixer, and its local hooks, run in a scratch repository, flag
  each whitespace defect and rewrite no file (18 tests)
- `test_markers.py`: every test carries exactly one marker, and none that skips without data is a unit test (2 tests)
- `test_metadata.py`: `codemeta.json` names the package and version `pyproject.toml` gives (1 test)
- `test_readme_counts.py`: the README's count badges match the counts computed from the data, and a label's escaped
  hyphen (`Pre--Greek`) reads as one (2 tests)

All of them run with `uv sync --all-groups`, then `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -m pytest`; the 8
live tests run on the shipped Linear A files (the 6 view tests read all eight `model.load` reads), and the `wiki` test
skips without the `wiki` command.

[`conftest.py`](conftest.py) fails the run if any entry under `data/` is added, changed or removed during it, a
symlink or a same-size rewrite included (it compares ctime), or if a folder there cannot be read, and names each; a
test that writes uses `tmp_path`. It also fails any test that connects to, or looks up, a host other than this
machine, and names the address; a test of a remote client stubs its request.

Markers (registered in `pyproject.toml`; `--strict-markers` refuses any other):

- `data`: reads the datasets shipped under `data/` (the five ANE client runs in `ane/test_data_paths.py`, the
  notation census on the shipped `egytext`, `pnm` and `tla` views in `ane/test_ane_keys.py`, the checks of the four
  name layers in `ane/test_name_layers.py` and their searches in `ane/test_query_name_layers.py`, the LFS scan, the README's count badges (`test_readme_counts.py`), the Pre-Greek lexicon checks in
  `pre_greek/` and its pages in `views/test_pregreek.py`, the four rival-language root files, the Syriac and Akkadian contact lexica, `cognate_search` on the shipped lexicon,
  and most of the Shoresh tests, which read the 10 files `linear_a/shoresh_inputs.py` names). With `data/`
  removed, every `unit` test still passes. `-m "unit or data"` is what a fresh clone can run.
- `maintainer` (42 tests): the 8 live tests (`LIVE` in `views/test_views.py`, used again by
  `views/test_census_doc.py`, and in `linear_a/test_skeleton_status.py`), which run on the shipped Linear A files and
  await their move to `data`; the notation census of the 7 ANE views whose data is a user's own download (29 tests in
  `ane/test_ane_keys.py`, each naming the path it looked for); and the 5 that need the maintainer's key or a checkout
  (`test_paradigm_b.py` 1, `test_protocol_c.py` 3, `test_sign_crosswalk.py` 1).
- `unit`: everything else, inline inputs only; `conftest.py` gives it to any test marked neither of the other two.

`live_contexts`, registered beside them, is not a tier: it marks a Shoresh test that keeps the engine's default
contexts, which `linear_a/conftest.py` otherwise stubs.
