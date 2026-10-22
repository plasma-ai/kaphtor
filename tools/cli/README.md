# tools/cli

The `kaphtor` command (`main.py`), installed by `uv sync` from `[project.scripts]` in `pyproject.toml`.

| Command | What it does |
|---|---|
| `kaphtor gate` | runs the repository's checks in order (tests, pre-commit, the generated pages, the census blocks, `wiki lint`, and the checks not yet built), then prints one line per step; exits 0 only when every step is built and passes |
| `kaphtor gate --list` | names each step and whether it is built, and runs none |
| `kaphtor empty-folders` | lists every folder that holds nothing yet, by the marker line its index or README carries (`EMPTY` in `main.py`); exits 1 while any remains, so no empty folder ships (a gate step) |
| `kaphtor reproduce [--quick]` | reruns the headline numbers; not built yet, so it stops with exit status 2 and names `docs/reproduce.md` |

Tests: `tests/test_cli.py`.
