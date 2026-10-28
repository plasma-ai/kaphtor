# tools/core/frozen/paradigm_b/scripts/common

Every file here is listed in the freeze's SHA256SUMS (`data/linear-a/paradigm-b/SHA256SUMS`).

| File | Purpose |
|---|---|
| `__init__.py` | The package marker |
| `paths.py` | The package root and hash-checked loading: a listed file whose sha256 differs from SHA256SUMS fails to load |
| `paradigm.py` | Pair alignment, the inventories and their explanation of residues, and the statistic A per arm and Δ (PROTOCOL-B §§4–5) |
| `nulls.py` | The observed family as inscriptions, the corpus sign model, and nulls D and D2 (PROTOCOL-B §6) |
| `stats.py` | Monte Carlo p-values with Clopper–Pearson intervals, length-matched AUC and its bootstrap, the posterior grid |
| `matcher.py` | Sign helpers `nulls.py` imports (`syllabic_signs`, `base_consonant_map`); the rest is stage 1–3 lookup code |
