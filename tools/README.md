# tools

The Python package behind the `kaphtor` command.

| Folder | Contents |
|---|---|
| `core/` | Shared library: skeletons, morphology, phonetics, null models, the Shoresh root matcher, data loaders |
| `ane/` | Query clients for the ancient Near East corpora |
| `linear_a/` | Linear A command-line tools, described in [linear_a/README.md](linear_a/README.md) |
| `views/` | The builder that writes `wiki/` from `data/`, and the generated blocks of `docs/corpus-census.md` |
| `cli/` | The `kaphtor` command: the gate and its index and licence checks |

`paths.py` names every data folder once (`DATA`, `ANE_DATA`, `SHARE_ALIKE`, `LINEAR_A_DATA`) and the query cache
(`CACHE`, under `$XDG_CACHE_HOME/kaphtor`). Set `KAPHTOR_DATA` to read the data from another folder. A tool whose
dataset is not in the checkout says so and names the path it looked for.
