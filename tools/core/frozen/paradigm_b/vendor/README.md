# tools/core/frozen/paradigm_b/vendor

The two library modules the frozen package imports as top-level names (`scripts/common/paths.py` puts this folder on
`sys.path`), listed in the freeze's SHA256SUMS. They are earlier copies of `tools/core/skeleton.py` and
`tools/core/phonetics.py` and differ from them.

| File | Purpose |
|---|---|
| `__init__.py` | Empty package marker |
| `skeleton.py` | The sign table: each syllabogram's consonant and vowel (`*301` = na, `*86` = ṇa) |
| `phonetics.py` | The phoneme tokenizer and the weighted distance tables |
