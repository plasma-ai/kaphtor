# Tests

The test suite: unit, data and maintainer tiers.

- [ane/](ane/README.md): offline tests for the `tools/ane/` query clients and the data paths (6 files, 192 tests)
- [linear_a/](linear_a/README.md): tests for the `tools/core/` library (16 files, 211 tests, 5 of them on the shipped
  data)
- [views/](views/README.md): tests for the record wiki's builder in `tools/views/` (3 files, 114 tests, 6 of them on
  the live Linear A data and 1 that runs plasma-wiki's `wiki`)
- [fixtures/](fixtures/README.md): the Shoresh gold set and its baseline, byte for byte as deposited

- `test_data_guard.py`: the data guard below, each case a small pytest session on its own data folder (7 tests)
- `test_lfs.py`: every PDF and every data file over 1 MB matches a Git LFS rule in `.gitattributes` (2 tests)
- `test_network_guard.py`: the network guard below, each case a small pytest session (5 tests)
- `test_plugin.py`: the plugin manifests against `pyproject.toml`, the README's install lines and the skills (4 tests)
- `test_cli.py`: the `kaphtor` command's gate and reproduce, on stand-in steps; the index-coverage and licence checks
  on scratch trees; the gate's pre-commit stage runs no fixer, and its local hooks, run in a scratch repository, flag
  each whitespace defect and rewrite no file (18 tests)
- `test_markers.py`: every test carries exactly one marker, and none that skips without data is a unit test (2 tests)

All of them run with `uv sync --all-groups`, then `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -m pytest`; the 8
live tests skip until the Linear A files they read are in `data/linear-a/` (the 6 view tests need all seven), and the
`wiki` test without the `wiki` command.

[`conftest.py`](conftest.py) fails the run if any entry under `data/` is added, changed or removed during it, a
symlink or a same-size rewrite included (it compares ctime), or if a folder there cannot be read, and names each; a
test that writes uses `tmp_path`. It also fails any test that connects to, or looks up, a host other than this
machine, and names the address; a test of a remote client stubs its request.

Markers (registered in `pyproject.toml`; `--strict-markers` refuses any other):

- `data`: reads the datasets shipped under `data/` (the five ANE client runs in `ane/test_data_paths.py`, the
  notation census on the shipped `egytext` and `pnm` views in `ane/test_ane_keys.py`, the LFS scan). With `data/` removed, every `unit` test still passes. `-m "unit or data"` is what a fresh clone can run.
- `maintainer`: needs a dataset not yet shipped, and skips without it: the 8 live tests (`LIVE` in
  `views/test_views.py` and `linear_a/test_skeleton_status.py`), and the notation census of the 7 ANE views whose
  data is a user's own download (29 tests in `ane/test_ane_keys.py`, each naming the path it looked for). Each
  becomes `data` when its files ship.
- `unit`: everything else, inline inputs only; `conftest.py` gives it to any test marked neither of the other two.
