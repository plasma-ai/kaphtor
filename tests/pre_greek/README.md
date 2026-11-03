# Pre-Greek tests

Tests for the Pre-Greek lexicon in `data/pre-greek/`. Each check is a function; the `data` tests run it on the shipped
files, and the `unit` tests hand it one planted defect, written inline, and show it reports that defect.

| Test | Covers |
|---|---|
| `test_pregreek_lexicon.py` | (data) unique ids; every feature id resolves in `pregreek_features.json`; every `proto_semitic` id resolves in `semitic_roots.json`, and a bad one planted in a copy of the shipped lexicon in `tmp_path` is reported; every work is in `docs/bibliography.md` or carries a full reference, and every proposer key (`by`) and siglum (`cite`) is listed there; the index rebuilds from the lexicon through `ane_keys.pregreek_index`; no key outside the datasheet's fields, and every `variety` one the datasheet names; Wiktionary glosses only on Wiktionary's words, twelve words or fewer; no quoted gloss in an entry, no private path, source id or email, no engine key or `PG_` verdict. (unit) each of those checks on a planted defect, and the Greek fold and consonant skeleton |
