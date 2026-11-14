---
name: data/linear-a/stats
title: Linear A headline counts
desc: The headline counts of the Linear A record as one JSON file, for sites that print them: records and documents, lexicon entries by tier, translations, sign values, names and Semitic roots.
tags: [data, linear-a, counts]
license: CC BY 4.0
created: 2026-11-16T18:18:44Z
updated: 2026-11-16T18:18:44Z
---

`stats.json` holds `schema_version` (1), `description` and the counts below, computed from the data files by
`python -m tools.views.stats --data data/linear-a --write`. The gate checks every count against the data. The file
holds counts only, with no date and no commit, so it changes only when a count does.

| Key | Count |
| --- | --- |
| `corpus.records` | the records of `corpus.json` |
| `corpus.documents` | the documents those records group into: the sides of one object are one document |
| `lexicon.entries` | the entries of `lexicon.json` |
| `lexicon.tiers` | the entries by confidence: `CONFIRMED`, `PROBABLE`, `CANDIDATE`, `SPECULATIVE` |
| `translations.complete` | the translations with text whose status is not `incomplete` |
| `translations.incomplete` | the other translations of `translations.json` |
| `sign_values.total` | the resolved and proposed values of `sign_values.json`, fractions apart |
| `sign_values.resolved` | the resolved values among them |
| `sign_values.phonemic` | the phonemic values, resolved and proposed |
| `sign_values.logographic` | the logogram values, resolved and proposed |
| `names` | the entries of `onomasticon.json` |
| `semitic_roots` | the roots of `semitic-roots/semitic_roots.json` |

## Invariants

The tool refuses to write a file that breaks one, so a consumer may check each:

- the four `lexicon.tiers` sum to `lexicon.entries`: a confidence outside the four tiers is refused;
- `sign_values.phonemic` + `sign_values.logographic` = `sign_values.total`;
- each phonemic and logogram counter of `resolution_summary` in `sign_values.json`, resolved and proposed, equals the
  length of its list, and the resolved counters sum to its `total`.

A count added keeps `schema_version`; a count renamed or removed raises it. The four tiers are a closed set, so a tier
label added raises it too.

## Consumers

Sites outside the repository read this file at `data/linear-a/stats.json`, at a commit on `main` whose GitHub
Actions check named `gate` succeeded. Moving or renaming the file, or renaming the check, stops their sync.
