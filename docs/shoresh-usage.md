---
name: docs/shoresh-usage
title: "Shoresh: Using the Root-Match Engine"
desc: How to build Shoresh's index, run the root-match command and read its output, from the statistic and verdicts to the gold guard and exit codes.
tags: [docs]
authors: "di Mino"
created: 2026-10-25T23:10:00Z
updated: 2026-10-25T23:30:00Z
---

# Shoresh: Using the Root-Match Engine

`cognate_search.py` ranks candidates. `tools/linear_a/root_match.py` asks whether a word's best distance d\* to a Semitic root cluster beats decoys built from the word itself. The statistic, decoys, thresholds and amendments are pre-registered in `shoresh-preregistration.md`, which binds wherever this guide differs; `tools/core/SHORESH.md` says what each § and A the code cites fixes. The usage lines are at the head of `root_match.py`.

Report-only: the command prints and never writes. Every result enters at SPECULATIVE; promotion stays with `hypothesis_test.py` and the tests in `confidence.md`.

## The index

Build it first: `uv run tools/linear_a/build_root_index.py --allow-missing` writes `root_index.sqlite` to the user cache (`$XDG_CACHE_HOME/kaphtor/`, else `~/.cache/kaphtor/`), never into the repository. `--allow-missing` records each contact lexicon this checkout does not ship as missing, and that file's arrival makes the index stale. Five of the eleven lexica the index reads ship, two of them (Syriac, Akkadian) open lexica in place of the private ones, so this index is not the one the pre-registration's baseline was measured on (its note says which are left out or replaced). `uv run tools/linear_a/fetch_sedra.py` puts Sedra's Syriac lexicon in the Syriac slot on your own machine: it downloads Sedra's weekly release (CC BY-NC 4.0), builds the lexicon and a data overlay under `CACHE/sedra/<release>/`, and prints the two commands that build and query an index on the overlay (`KAPHTOR_DATA=… build_root_index.py --out …`, `root_match.py --index …`), so the default index stays as the checkout builds it.

## The statistic and the decoys

- **d\*:** the minimum over spelling variants, readings of polyphonic signs and the keys retrieved within one class edit (A11, A12), on Shoresh's own table (`SEMITIC_DISTANCES` plus k ↔ ḫ at 0.3).
- **Tokens:** one per letter on every side (`rm.phonemes`): a key's radicals, a sign's consonant and a competitor's letters are never merged, so KU-WA-NA is k w n and Egyptian msḥ is m s ḥ. Sabaic subscripts drop (s₁ is s); x is ḫ, ʁ and γ are ġ, as the index classes them. Luwian and Hurrian keep their bare digraphs (ts, sh, kw, gw), since `LUWIAN_DISTANCES` prices kw and gw; Egyptian has none.
- **Ties:** every sum is compared on a 1e-9 grid, so 0.1 + 0.1 + 0.1 ties 0.3.
- **Decoys:** family A shuffles the signs, B fabricates position-matched words, C permutes the consonant map. p\_F = (1 + below + tied) / (1 + N), N = 1,000 by default; p\_max is the maximum over the families that count. A counts only from 100 distinct sign orders up (A1). A family that counts and built no decoy enters p\_max at p = 1 (A17). Family B keeps the OCP only if the real word does: a word with two identical consonants side by side gets decoys that may have them too. Family B also keeps the word's number of readings, so ZU's four count as two two-way slots. At most 8 readings of a polyphonic word are queried, those fewest steps from the primary, and the same ones wherever the signs stand; a word with more says so.
- **Batch:** two or more words get Benjamini–Hochberg q.
- **Key set:** the primary key set leaves out A4's frozen list of Numbers, read from the gold set (`primary_index_exclusions`), never recomputed; a listed Number the index no longer holds is reported as `a4_absent`. `--full-index` gives the secondary result. The statistic runs on root clusters only: a contact lexeme that joins no root (§8, A17) never enters d\*, p or breadth.
- **Sign values:** by default every sign reads its primary value, proposed values beyond Linear B included, and every alternate reading in `data/linear-a/sign-registry.json` (QA → q, z; ZU → ṯ, z, ḏ, ẓ, the interdental range with Linear B's zu, A20). `--conventional-values` reads every sign whose engine value is not its Linear B value (`tools/core/skeleton.py` `SIGN_STATUS`, and any sign off the Linear B grid that it does not list) by Linear B's value: PA₃, JU and ZU as pa₃, ju and zu (\*56, \*65, \*79, signs Linear B transliterates only tentatively; \*79 zu: Davis 2026, 174 n. 641; `LINEAR_B_VALUES`), so KU-PA₃-NU reads k p n. AU keeps its resolved /aw/. A word with a sign Linear B gives no value (\*306, \*118, \*86 and the rest) is unmapped (A5). Only alternates whose status is `conventional` are read (RA₂ → l, r; QA → q). All three decoy families are built the same way (family B draws no unmapped sign, family C permutes the Linear B values' consonants), so p moves even for a word with no such sign; the report carries `sign_values`. It is a report-only sensitivity analysis outside the registered statistic. It is not the pre-registration's "Linear B values only" stratum, which selects words and keeps the registered decoys. A result that stands under both readings rests on no value beyond Linear B but AU's resolved /aw/, granted the conventional equations the grid itself makes (QA, QE as q; the Z series as z). The meaning-shuffle commands take the same flag.

## Verdicts

| Verdict | When |
|---|---|
| UNINFORMATIVE | ≤ 2 consonants, or more than 90% of family-B decoys at d ≤ 0.3 |
| NO\_SIGNAL | p\_max ≥ 0.05 |
| PHONOLOGICAL\_ONLY | p\_max < 0.05, and not CONVERGENT |
| CONVERGENT | p\_max < 0.01, p on d\*\_sem < 0.01 in the same families, and the competitor null run with every competitor at p\_max ≥ 0.05 (POS holds vacuously). A run without the competitor null never gives it |

**POS (§3.2)** gates verbal-template parses only. No Shoresh variant is one (the verb lens is outside d\*), so the condition holds vacuously. Each cluster shows the POS it inherits from its joined contact lexemes.

**The semantic gate** (§3.1, A10, A18, A19; `tools/core/semantic_gate.py`). A word's context comes from its attestations in `data/linear-a/corpus.json`:

- **Per attestation:** the logogram after the word, past any line break or word divider, or fused onto it (X-VIN reads as X VIN; never \*118 or NI), by its conventional identification. Ligatures go by their base and spelling variants by their sign (\*OLIV as OLIV, VINb and VINc as \*131B and \*131C), and \*118 and NI count only when a number follows. Else the document type (formula objects: ritual\_cultic, deity; clay vessels: pottery\_vessel, food\_drink; tablets, sealings and the rest unknown).
- **Per word:** the union over its attestations. With no known context the word has no semantic evidence and is never CONVERGENT.
- **Controls:** a control has no attestation of its own; `query(..., context_of=W)` scores it under the context of W, the positive it was made from (§4, A19), and its notes say so.
- **A cluster's domains:** the frozen tagger (`tools/core/frozen/tag_semantic_fields.py`, sha-checked before it runs) over the record's Meaning and its joined lexemes' glosses, onomastica out. A cluster fits when the two share a domain.
- **The statistic:** d\*\_sem is the best distance over fitting clusters. Every decoy is scored over the same fitting clusters, so its p follows the §2 rules. The gate never moves d\*, p\_max or the phonological verdict.
- **Its inputs:** the command reads the contexts, the tagger and the clusters' Meanings once, before any word or worker, and stamps the corpus's and the tagger's sha256 on the report. A changed tagger or an unreadable corpus exits 4.

**Breadth** (A12) is the number of branches carrying the top cluster, gloss-gated and gloss-free, set against family-B decoys. Display only; it never moves p.

## The competitor null (§2, A15)

`tools/core/competitors.py` reruns the same statistic on the same decoys against Luwian (1,441 keys), Egyptian (3,011) and Hurrian (95) keys from the rival-language root lists: each file holds the entries that give a key and that the name test does not flag. The names the test misses stay in; `data/linear-a/rival-roots.md` lists them. Each result gets per-competitor d\* and p\_max, the margin (lowest competitor p\_max minus the Semitic p\_max) and `semitic_specific` (Semitic p\_max < 0.05, every competitor ≥ 0.05). Hurrian's 95 keys make its gate weak; A9 measures it. `--no-competitors` skips it. The Semitic result is byte-identical either way.

## Sound laws (`--explain`; on every shown cluster in `--json`)

Each radical of the cluster's nearest PS headword is aligned with the Linear A word on Shoresh's cost. Each branch's reflex (Huehnergard Table 3.2, `data/semitic-roots/semitic_correspondences.json`) is spelled as the script would spell it: the 13 consonants the Linear B grid writes (d k l m n p q r s t w y z) and the ṯ, ḏ and ẓ ZU writes before every vowel (A21; a conventional run has the 13 alone) as themselves, any other at A9's cheapest series, gutturals with no substitute under 1.0 unwritten.

- **diagnostic:** some branches match the sign and some do not;
- **not diagnostic:** every branch matches, so the script's choice says nothing;
- **unexplained:** no branch matches;
- **not in table:** the radical has no row.

The profile is the branches matching at every diagnostic radical. Most sibilant and interdental laws come out not diagnostic: the script cannot write the difference. Insertions, deletions and consonants the script does not write are skipped. Geers' law is not checked. Report-only, never in d\*, p or the verdict.

`--explain` also prints the record as indexed (headword, meaning, every Analogues row with its citation) and the contact lexemes that join the cluster (fk, or exact sound + gloss; onomastica only with `--names`). Every other lexeme linked to the cluster is a "possible cognate of N" (§8, A17): an exact sound link with no shared gloss, or a link made only through absorbed consonants, exact links first. Under each word come the unlinked lexemes, those with a key and no link to any root, at or under the word's d\*. The text lists 8 of each and counts the rest; `--json` carries all. None of them is a cluster, and none enters d\*, p or breadth.

## The unread sweep

`--sweep unread` queries every entry of `data/linear-a/unread_words.json`, sets gold-set words aside (counted, never queried) and ranks by q. `--top` is then the number of rows shown (0: every row); `--json` carries every row. `--workers N` forks a pool over one engine; every word's decoys come from its own seeded stream, so the result equals a serial run, and a worker that dies raises instead of hanging.

Every report, a sweep or not, carries the sha256 of the index, of the gold set (none under `--gold-run`), of `data/linear-a/corpus.json` and of the frozen tagger (§7.1); a sweep adds the word list's. Each is hashed from the bytes read, and an index that changes while it loads, or before its Meanings are read, is refused. Words are queried in canonical spelling (upper case, subscripts as digits), so `ka-na-si` and `KA-NA-SI` get the same decoys.

## The gold set

Never run the engine on a gold-set word (`tests/fixtures/root_match_gold.v3.json`) before the gold run: an engine number on gold freezes the §6 amendments. `root_match.py` refuses any batch holding one, in corpus or lexicon spelling, before the index loads (exit 3); a sweep sets them aside instead. The guard compares sign names and the engine's readings, so a spelling the engine reads as a gold word (KU2-RO, KU-RO9, KU-\*310-SU) is held back with it; under `--conventional-values` so is one that reads as a gold word by Linear B values (X-PA-Y as X-PA₃-Y). A gold file missing any of its seven sections, or with one empty, refuses every word. `--gold-run` lifts the guard for the gold run alone. `tools/linear_a/validation/root_match_checks.py` skips gold words in the A12 sample and sets aside any A9 spelling that is one, by name or by reading (A14). Direct `tools.core.root_match` calls carry no guard, and no test takes a number on a real gold word: the command's tests use a synthetic gold file.

## Running it

- **Exit status:** 0; 1 if a word had an unmapped sign (reported, never shortened); 2 if the index is stale (`--allow-stale` reads it anyway, every result marked `index_checked` false), missing, or changed while loading or before its Meanings were read, or a rival-language file is not in the checkout (`--no-competitors` runs without them); 3 for a gold-set word, an unreadable or malformed gold set, or one without A4's list (primary result only); 4 for an unreadable `data/linear-a/corpus.json` or a tagger that is not the one A18 froze, before any word is queried; 5 if `--sweep unread` finds no `data/linear-a/unread_words.json`.
- **Speed:** on this checkout's data the index builds in about 13 s, and a cold query with 1,000 decoys per family and the competitors takes about 5 s (two index hashes included).
- **Long runs** (sweeps, the pre-gold checks, `--calibrate`) read a frozen copy of the data (§7.7). The checks write their report once and refuse to overwrite it. With `--workers`, a worker that dies raises and no report is written.
- **The index goes stale on any edit to its key-logic files:** `data/semitic-roots/semitic_correspondences.json`, `tools/core/semitic_root_schema.py`, `tools/core/semitic_notation.py` and `tools/core/root_index.py`. An edit to one of them, even a display helper, stales every built index, frozen copies included. Display code belongs in `tools/core/root_match.py` or the command.
- **After a data change:** `tools/linear_a/build_root_index.py --check`, `--diff`, then `--force` (backs the old index up), per §7.6.
- **What a rebuild moves** (§7.3, items 3 and 4): `--diff --impact` builds the current inputs into a temporary index (nothing in the repository is written) and lists the corpus words, in canonical spelling, that retrieve a changed key under either index. A key is changed when its clusters differ or its root's domains do (a Meaning or joined-gloss edit, A19), and a word whose retrieved keys differ between the two indexes (a key-logic change) is listed too. Only for these can d\* and the clusters at d\* change; p, saturation and so the verdict can move for any word, since the decoys query the whole index. A second count gives the words whose retrieved keys belong to a root that gained or lost a branch or POS: breadth and the order of tied clusters only. `--preview` adds each impacted word's top cluster, d\*, verdict and p\_max on both indexes (`--n` decoys per family, default 1,000; families ABC; no competitors, so never CONVERGENT). The key set is the primary one, and gold-set words are set aside and counted before either index is queried.
