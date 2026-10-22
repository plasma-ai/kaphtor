# Fixtures

| File | What it is |
|---|---|
| `root_match_gold.v3.json` | The Shoresh gold set (§6 A13): positives, negatives, controls, Linear B negatives, loans and shuffles, the excluded rows, and A4's frozen `primary_index_exclusions`. sha256 `c00d7c2f9d475be5cc4d3beb184b1738e19e0c5b5c6fb8279d1adc767ebf4b81` |
| `root_match_baseline.v3.json` | The earlier matcher's baseline on that gold set (§5, A13), the reference the gold run is measured against. sha256 `4cde03c7d000e655c23b4c9edffe4406438f46488e46bd8faa147ad5d8167706` |

Both are the deposited files, byte for byte (A16: "gold v3 stays as built and hashed"). Their field names, notes and
`provenance` (generator paths, input hashes, git head) are those of the build that produced them and are never
edited here; `root_match.py` stamps every report with the gold set's sha256. `root_match_phase0.py gold-v3` and
`baseline-v3` would rewrite them: never run those commands in this repository.
