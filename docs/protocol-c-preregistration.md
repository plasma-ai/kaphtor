---
name: docs/protocol-c-preregistration
title: "Protocol C: Blind-Inventory Prediction of Unseen Linear A Forms"
desc: "Protocol C, the blind-inventory prediction test of unseen Linear A word edges: its pre-registration as signed on 2026-10-29, with amendments A1–A4; not yet frozen or run."
tags: [docs]
authors: "di Mino"
status: "SIGNED 2026-10-29 (SIGNATURE.txt 5a7b442c…); amendments A1–A4; phases C0 and C1 built and hashed; not frozen, no Linear A form rendered or scored"
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C: Blind-Inventory Prediction of Unseen Linear A Forms

> [!NOTE]
> This is the signed text with its amendments A1–A4, kept as written but for five changes: the private source ids
> after citations are cut, the maintainer is named di Mino throughout, the *Ya Diktu* PDF is named by its public
> address, the list of drafting scripts at the end is cut to one line, and this note is added. The text as signed,
> before the amendments, is
> `data/linear-a/protocol-c/PROTOCOL-C-SIGNED-2026-10-29.md`, at the sha256 `SIGNATURE.txt` records.
> `tools/linear_a/validation/protocol_c.py verify --key`, given the maintainer's key, undoes the changes to both files
> and checks them against their hashes. Phases C0 and C1 are built and hashed; nothing is frozen, and no Linear A form has been rendered or scored.
> The text names files by their paths in the research package it was written in. In this repository they are:
>
> | Named here | In this repository |
> |---|---|
> | `protocol-c/` (§11 item 1) | split as amendment A4 sets out, in the rows below |
> | `protocol-c/inventories/` (`TABLES.md`, `tables/<arm>.md`, `schema.json`) | `data/linear-a/protocol-c/inventories/`, same layout, `TABLES.md` as `TABLES-C0.md` |
> | `protocol-c/render/series.json` | `data/linear-a/protocol-c/render/series.json` |
> | the builder transcripts and the six C1 builds | `data/linear-a/protocol-c/builds/<arm>/`, each log as `transcript.redacted.jsonl` (A4) |
> | `protocol-c/scripts/` (`run_builder.sh`, `check_inventory.py`) | `tools/core/frozen/protocol_c/scripts/` |
> | `SIGNATURE.txt` | `data/linear-a/protocol-c/SIGNATURE.txt` |
> | `data/formula_family.json` | `data/linear-a/paradigm-b/formula_family.json` (the same bytes) |
> | `PROTOCOL-B.md`, `STAGE-B-REPORT.md` | [paradigm-b-preregistration.md](paradigm-b-preregistration.md), [paradigm-b-result.md](paradigm-b-result.md) |
>
> Not in this repository: `data/family_additions.json`, `DECISIONS.md`, `campaign_workspace.json`, `artifacts/`
> (the Option B review and the statistical battery, with the review's `null_r.py` and `rand_inv.py`), the drafting
> scripts and their outputs under `scratchpad/protocol-c/`, the research tree's `corpus.json`, `lexicon.json`,
> `translations.json`, `onomasticon.json` and `unread_words.json` (the repository's own, in `data/linear-a/`, have
> changed since the counts in §3 were made), the grammars and the *Ya Diktu* PDF (their sha256 are in each build's
> `kit.sha256`), and the builders' full logs (their sha256 are in each build's `SHA256SUMS`). Not yet written: the
> phase C2–C6 scripts (`null_r.py`, `null_inventory.py`, `score_c.py`), the own-language selftest, `inputs/`,
> `predictions/`, `controls/`, `power/`, `runs/`, the freeze's `SHA256SUMS` and the tag. `protocol_c.py reproduce`
> reruns the C1 checks ([reproduce.md](reproduce.md)).

## 0. Status

Signed 2026-10-29. di Mino's rulings are in §15. From here a change is a dated amendment. Nothing is built, frozen or run. No arm, null or statistic has been computed on any Linear A form
for this protocol. The only operations performed on Linear A data while drafting were counting legible tokens and
auditing prior use (§3), and pool-size counts with no inventory or null attached (§3.5). The scratch scripts that
produced those counts are listed under "Scratch files" at the end. Once signed, the build follows the phases of §12 and stops at each gate.

## 1. The demand

> "Can your proposed Semitic grammar predict previously unexamined Linear A sequences using fixed sign values, and
> survive independent sign-value reconstruction without retrofitting phonetics or meanings? Identify a specific
> reproducible test."

The demand has three parts, and each needs a separate design guarantee:

1. **Unexamined sequences.** The forms scored were never used to build, tune or check the predictor (§3).
2. **Fixed sign values.** Every sign reads a value fixed by Linear B, which is independent of the hypothesis.
   Contested values enter a secondary run only (§4).
3. **No retrofitting.** The morphology that predicts is compiled from grammars of the candidate languages by a
   builder who never sees Linear A. It is frozen and hashed before any Linear A token is scored (§5). Meanings never
   enter the statistic.

What the protocol tests is **affix shape at word edges**. It does not test word meanings, syntax or the
individual readings of *Ya Diktu*. §14 fixes what each outcome allows the project to say in public.

## 2. What Option B got wrong, and where C fixes it

Option B (`PROTOCOL-B.md`, run 2026-10-09, `STAGE-B-REPORT.md`) and the review of 2026-10-29
(`artifacts/optionb-review-2026-10-29/README.md`) found the defects below. The older statistical battery
(`artifacts/peak-sanctuary-statistical-validation/`) found the last four.

| Defect | Evidence | Fix in C |
|---|---|---|
| The Central Semitic lead rested on one morpheme, `cs_c_e` (dual oblique -ē, Ugaritic only), absent from B's own §4.2 list | `scripts/build_paradigm.py:174`, `scripts/selftest_b.py:180` checks the family's -RE-MA residue with it. Without it, cs 23/57 against Egyptian 17/57 | Exhaustive table rule, a builder who never sees Linear A, no check against Linear A residues (§5) |
| Not unseen data: held out inside the 33 inscriptions the grammar was built on, 57 tokens = 27 distinct forms | review README | Test pool excludes every form *Ya Diktu* cites and every formula form. The unit is the distinct type. Training excludes every document holding the type (§3, §6) |
| Damage scored as morphology | U-NA-KA-NA (TL Za 1), JA-SA-SA (PK Za 14), I-PI (PK Za 8), SI-RU (PK Za 11), SE-KA-NA-SI (SY Za 3), PK Za 12 joined across lacunae, IO Za 16 split at a line break | Mechanical damage rule from corpus markers, written before scoring (§7) |
| Null D too weak | A stem-keeping null R gives p ≈ 0.11 on undamaged tokens | Null R is the primary structure null (§8.1) |
| "200 random inventories" had no script | review README | Shape-matched language null with a named script, run count and seed (§8.2). No number is reported without a committed script and run file (§11) |
| A frozen input drifted after the freeze. The folder is untracked in git | `data/snapshot/lexicon.json` ef66e205… → 8862ac15… on 2026-10-18 | Public repository, annotated tag, SHA-256 manifest, a runner that refuses on any mismatch, inputs copied rather than symlinked (§11) |
| G2 failed on one Linear B window (shared feminine -t), decided by a median of ties | B-NEG-02, band median 0.00 with 16 of 29 windows at Δ = 0 | Rate criteria over 20 full-size pseudo-corpora per language, no medians, a Mycenaean Greek rival arm (§9) |
| Battery: an optimized pick scored against one random draw | battery folder | One pre-registered inventory per arm, compared with the full distribution of random inventories of its own shape (§8.2) |
| Battery: a branch bonus only Semitic could earn | battery folder | No costs, bonuses or priced innovations in any primary arm (§5.4) |
| Battery: leave-one-site-out tested recurrence, not language | battery folder | Identity excluded, type-level folds, a stem-keeping null (§6, §8.1) |
| Battery: contested sign values in inputs | battery folder | Secure Linear B values only in the primary (§4) |

What held in B and carries over: the observed run reproduces exactly, and *301's value changes no score.

## 3. Held-out data

### 3.1 Eligibility rule

A form is **eligible** as held-out data when all of the following hold:

1. It passes the damage rule (§7).
2. It is not named in *Ya Diktu* (the canonical PDF, `https://www.minoanmystery.org/linear-a/ya-diktu-grammar-tom-di-mino.pdf`,
   commit `3204dd2`, read through `pdftotext -layout`).
3. It is not a token of the formula family (`data/formula_family.json`) or of `data/family_additions.json`.
4. It played no part in the inventory build, its selftests or any calibration step.

An **inscription** is eligible for a formula-level test when its formula tokens are eligible forms and the
inscription is not read in `translations.json` or attested in `lexicon.json`.

Prior use in `lexicon.json`, `translations.json`, `onomasticon.json`, `unread_words.json` or
`campaign_workspace.json` disqualifies a form from the formula-level test (§3.2). It does not disqualify a form
from the corpus-wide test (§3.5), whose predictors never read those files. The *Ya Diktu* arm is held out only
against the forms the published grammar cites (§13, limit 3).

### 3.2 Audit of the formula candidates

The six candidates of `data/family_additions.json`, plus every other inscription found by the formula criterion.
The criterion: a non-administrative support (not tablet, nodule, roundel, lame, sealing or bar) and a token sharing
a contiguous run of at least 3 signs with a family slot form. Scan: `scratchpad/protocol-c/scan_eligibility.py`
over `corpus.json` (1,719 records). The scan found 31 of the 33 family inscriptions, the six candidates and three
more inscriptions (IO Za 8, IO Zb 10, PO Zc 1). "Legible" applies the §7 rule. "2 of 3 (1)" reads: 2 of the
inscription's 3 syllabic words are legible, 1 of them the formula token. "Ident." means the form equals a
training form at the CV level, which makes it unscorable under B's amendment 9, kept in C.

| Inscription | Formula token | Legible words (formula) | Prior use | Eligible |
|---|---|---|---|---|
| PR Za 1 (Prassa) | A-SA-SA-RA-ME (RA drawn reversed, *802 form) | 2 of 3 (1). TA-NA-SU-TE[ ]-KE damaged | *Ya Diktu* p. 42 (`A-SA-SA-RA-ME: … PR Za 1c`). `lexicon.json:1558, 6611, 11951` (A-SA-SA-RA-ME CONFIRMED, TA-NA-SU-TE-KE, SE-TO-I-JA). `translations.json:4150` (full translation). `family_additions.json` with reading. `DECISIONS.md:12` | no |
| ZA Zb 3 (Zakros) | A-TA-I-*301-DE-KA | 6 of 6 (1) | *Ya Diktu* p. 19 (read as tG √ʿ-n-y), p. 42, p. 43 (TI-TI-KU). `lexicon.json:1506, 8119, 9201, 10535` and 11 more hits. `translations.json:4732` (full translation) | no |
| PK Za 15 (Palaikastro) | JA-DI-KI-TE-TE-DU-PU₂-RE | 0 of 1. Lacuna at both edges | *Ya Diktu* pp. 19, 21, 43 (`JA-DI-KI-TE-TE: PK Za 15`). `lexicon.json:2192` (A-DI-KI-TE-TE, DU-PU₂-RE, JA-DI-KI-TU). `translations.json:1232` | no |
| KH Zc 106 (Knossos) | SA-SA-RA-ME | 1 of 1 (1), ident. to PK Za 11 slot 3 | Bare form absent from *Ya Diktu*, which reads its type JA-SA-SA-RA-ME (pp. 8, 18, 43). `translations.json:12312` (cited in the PO Zg 1 note). Form used in `selftest_b.py:203` | no |
| NE Za 1 (Nerokourou) | I-DA | 0 of 1. Lacuna at both edges | *Ya Diktu* reads I-DA-[ and I-DA-A as ʾIda (pp. 16, 19). `lexicon.json:2338` (I-DA PROBABLE) | no |
| PK Za 17 (Palaikastro) | ]I-DA | 0 of 1 | As NE Za 1. `lexicon.json:2339` | no |
| IO Za 8 (Iouktas) | ]A-NA-TI-*301-WA-JA[ | 0 of 1 | *Ya Diktu* p. 41. `translations.json:13286` | no |
| IO Zb 10 (Iouktas) | A-SA-SA-RA-ME | 0 of 1 | *Ya Diktu* p. 42. `lexicon.json:1557`. `translations.json:6055` | no |
| PO Zc 1 (Poros) | RI-QE-TI-A-SA-SA-RA-[·] | 0 of 1 | `lexicon.json:5787`. `translations.json:12294, 12312` | no |

Additional facts from the audit:

- **Every candidate is disqualified twice over**: by prior reading, and in seven of nine cases by damage.
- **Scorable count.** Two legible, non-identical formula tokens exist outside the family: A-SA-SA-RA-ME (PR Za 1)
  and A-TA-I-*301-DE-KA (ZA Zb 3). Both are read in *Ya Diktu*.
- **Retrospective time-split.** The skill's tracked history of `corpus.json` begins 2026-08-05 (commit `167579f6`).
  Nine records entered afterwards, and none carries a formula type. No retrospective time-split exists.
- **Accrual rate.** Twelve formula-bearing inscriptions were published after GORILA (IO Za 11, 12, 14, 15, 16,
  PK Za 20, 27, SY Za 4, 8, KH Zc 106, NE Za 1, PO Zc 1). Together they yield no legible variant token that
  differs from a form attested elsewhere. Their one candidate, IO Za 16's JA-SA-SA-RA, is split at a line break.
- **A family input discrepancy.** The family records PK Za 11 slot 3 as SA-SA-RA-ME, while *Ya Diktu* p. 8 reads
  A-SA-SA-RA-ME there. In `corpus.json` the A stands alone at a line end, and §7 rule D4 excludes both tokens.

### 3.3 Verdict on formula-level held-out data

**No eligible held-out formula inscription exists.** Under a looser rule that ignores prior reading, the pool is two
tokens. With two tokens, a hits-count test cannot reach α = 0.05 once the per-token null hit rate is 0.35 or more:
the floor is p = q² = 0.12 at q = 0.35 and 0.25 at q = 0.5 (`scratchpad/protocol-c/binom_power.txt`). Null R
put the family's undamaged-token rate near 0.5. No formula-internal test of the published grammar on unseen
inscriptions can be powered now, or in the coming decades at the post-GORILA accrual rate.

### 3.4 Consequence for the design

Protocol C therefore registers three tests:

- **C1, corpus-wide blind prediction (primary).** The held-out unit is any eligible legible form in the whole corpus.
  "Unexamined" is guaranteed at the predictor: the language inventories never saw Linear A, the sign values come
  from Linear B, and the *Ya Diktu* arm is scored only on forms the grammar never cites. §6 specifies it.
- **C2, prospective formula registration (report-only).** The predicted form set for every formula slot is
  published at the freeze. It is scored on formula inscriptions first published after the tag date (§6.6).
  C2 is the only test of the published grammar on genuinely new inscriptions. Its power is near zero for decades.
- **C3, alternatives considered and rejected as evidence** (§6.7): positional and arithmetic families (KU-RO and
  KI-RO lines, commodity rows, sealing formulae), and a retrospective score of the six candidates.

### 3.5 C1 pool size (counted, not scored)

`scratchpad/protocol-c/c1_pool_count.py` counted the following with the §7 rule approximated (D1, D2, D4):

- 846 legible syllabic word tokens (≥ 2 signs).
- 651 of those are outside *Ya Diktu*'s cited forms and the formula forms: 473 types.
- 315 of those types (434 tokens, 224 documents) have a partner in another document sharing a contiguous run of at
  least 2 signs.
- At a run of at least 3 signs, 1 type remains.

The alignment threshold is therefore m = 2. A minimum of 3 leaves no test. The frozen code produces the
registered count, which is reported beside this one.

## 4. Sign values

| Run | Values | Status |
|---|---|---|
| **Primary** | Secure Linear B values: the core CV grid and the doublets Linear B transliterates without query (A₂, A₃, AU, DWE, DWO, NWA, PTE, PU₂, RA₂, RA₃, RO₂, TA₂, TWE, TWO and the rest of the secure list in Bartoněk, *Handbuch des mykenischen Griechisch*, the syllabary chapter). Every other sign, including *301, *314, *802, *306, *21F, *86, PA₃, JU, ZU and every Linear A–only sign, is an **opaque symbol**. Opaque symbols align by identity and never render from a morpheme | registered |
| Secondary 1 | Primary plus Linear B's tentative values (PA₃ pa₃, JU ju, ZU zu, as in Shoresh A20's `--conventional-values`) | reported, never in place of the primary |
| Secondary 2 | The project's contested values: *301 = na, TE = ṣ beside t, *86 = ṇa, ZU = ṯ/z/ḏ/ẓ, *306 = ʿa, *21F = ha, PA₃ = ba, and every `resolution_summary.proposed` value in `sign_values.json` at the freeze | reported, never in place of the primary |
| Secondary 3 | Value permutation: consonant values permuted among the secure grid's consonant series (vowels kept), 1,000 permutations, seed 20261107 | tests whether a primary result depends on the phonetics (§8.4) |

A primary result that Secondary 3 reproduces under permuted values licenses no phonetic claim (§14).

## 5. Blind inventories

### 5.1 Arms

| Arm | Role | Source grammar (one per arm) | Held |
|---|---|---|---|
| `cs` | H1, blind, co-primary | Huehnergard, "Proto-Semitic," in *The Semitic Languages*, 2nd ed., ch. 3 (2019): noun, pronoun and verb paradigm tables. Central Semitic innovations from Huehnergard, "Features of Central Semitic" (2005, `sources/huehnergard/`, record to add) and Huehnergard and Rubin, "Phyla and Waves" | yes |
| `yd` | H1, the published grammar, co-primary | di Mino, *Ya Diktu* (commit `3204dd2`): every affix and clitic the grammar states, from its grammar sections and paradigm tables | yes |
| `luwian` | H2 | Yakubovich, *The Luwian Language* (2015 manuscript), tables of nominal and verbal endings | yes |
| `hurrian` | H2 | Wegner, *Einführung in die hurritische Sprache* (2000), suffix-chain tables | yes |
| `egyptian` | H2 | Allen, *Middle Egyptian*, 3rd ed. (2014), suffix pronoun, gender-number and verbal ending tables | yes (3rd ed. EPUB, ruling 6) |
| `greek` | H2, new | Bartoněk, *Handbuch des mykenischen Griechisch* (2003), nominal and verbal inflection tables | yes |
| `free` | no language | residues learned from each fold's training pairs (B §5.2) | — |
| L null | a language that is none of these | random inventories of each arm's exact shape (§8.2) | — |

Section numbers of every table used are read off the held copy at phase C0 and listed in
`protocol-c/inventories/TABLES.md`, which di Mino signs before the builder starts. This draft names the categories, and
the signed table list binds.

`greek` is added because Linear B's values were fitted to Greek. Greek is therefore the rival with a home
advantage, and it absorbs the shared typology (feminine -t, case vowels) that failed B's G2.

### 5.2 Categories (pre-listed)

Every arm takes **every realization in its named tables** for these categories, and nothing outside them:

- **Nominal:** gender and number markers, case endings, state markers (Semitic mimation and nunation), the
  definite article where the grammar lists it as bound.
- **Pronominal:** bound possessive and object pronouns.
- **Verbal:** person, number and gender affixes of every finite paradigm the grammar tabulates, derived-stem
  prefixes and infixes written at a word edge, participial and infinitival affixes.
- **Clitics:** bound conjunctions, prepositions and enclitic particles that the grammar writes as one word.

Duals, energics and other rare categories enter if, and only if, the named table lists them. The rule takes the
choice out of the builder's hands. The selection is the grammar's, not the tester's.

### 5.3 Blindness

1. **Builder.** A fresh agent session in a sandbox holding only the arm's grammar PDF, `TABLES.md`, the JSON schema
   and this section. It has no repository access, no `corpus.json`, no *Ya Diktu* (except for the `yd` builder, who
   holds the PDF only) and no Linear A sign list. The full transcript is saved and hashed. di Mino does not edit
   entries. A correction goes back to the builder with the table reference.
2. **Refusal.** The build script refuses an entry whose citation or function string names Linear A, Minoan,
   *Ya Diktu* (except in `yd`), a Linear A sign value or any corpus form. This carries over B §4.1.
3. **No Linear A selftest.** The only selftest is own-language: each arm's inventory, rendered, must generate the
   affixes of 40 forms taken from a text of its own language outside the grammar's tables (Ugaritic KTU 1.14, a
   Luwian KARATEPE section, a Hurrian EA 24 passage, an Egyptian Coffin Text spell, a Pylos tablet), at ≥ 90%.
   No inventory entry is ever checked against a Linear A residue.
4. **Freeze order.** Inventories are committed and hashed (phase C1) before the renderer is run on any Linear A form,
   and before the calibration gate.
5. **The `yd` arm** is non-blind by construction: it is the grammar under test. Its builder extracts the grammar's
   stated affixes mechanically, every bound morpheme the grammar names in its grammar sections, with page.
   Morphemes the grammar writes only with a contested sign value render only in Secondary 2. The primary reports how
   many drop.

### 5.4 Parity

Parity is stated up front, with no caps:

- Distinct realizations (kind × rendered shape) and one-sign realizations are counted per arm and reported.
- **No cap, ratio rule or pruning** applies after the build. Size differences are priced by comparing each arm with
  random inventories of its own exact shape (§8.2). Arms are compared by their excess over that null (§8.3), never
  by raw hits.
- No costs, priced innovations or `ext` inventories enter any primary arm.

### 5.5 Rendering

One renderer serves every arm, the controls and the nulls:

1. **Phoneme to series.** One articulatory table, fixed in `protocol-c/render/series.json` at C0:
   - labial stops → P, dental and alveolar stops (emphatics and interdentals included) → T, except voiced d → D,
   - velar and uvular stops → K, labiovelars → Q,
   - all sibilants → S, z → Z, liquids → R,
   - nasals → M or N, glides → J or W,
   - laryngeals and pharyngeals → zero onset.
2. **Spelling.** The union of two conventions, each also run alone as a sensitivity:
   - Linear B omission rules: final consonants unwritten, and the first member of s + stop, liquid + stop and
     nasal + stop clusters unwritten (Bartoněk 2003, spelling rules).
   - Plene echo-vowel rules: a consonant without a following vowel takes the next vowel inside a cluster and the
     preceding vowel at word end.
3. **Vowels.** Strict: consonant and vowel must both match.

## 6. C1: statistic and predictions

### 6.1 Units

The **test set** T is every distinct eligible type (§3.1) with ≥ 2 syllabic signs. Each type is scored once,
whatever its token count. This answers B's 57-tokens-as-27-forms inflation.

### 6.2 Training and partners

For a test type x:

- **Training** is every legible token in documents that do not contain x. Forms cited by *Ya Diktu* may serve as
  training stems.
- **Partners** P(x) are the training forms g ≠ x at the CV level (opaque symbols by identity) whose longest common
  contiguous run with x has at least 2 signs (m = 2, §3.5).

### 6.3 Hit rule

Arm a hits x when some g ∈ P(x) leaves residues on both x and g, prefix and suffix, that a's inventory generates.
Generation follows class order with at most one morpheme per class, and realizations come from §5.5. This is B's
§5.3 rule with the training restricted as above. The free arm hits x when x's residues lie in the training residue
inventory (B §5.2), and an empty residue always counts as in.

H_a is the number of hit types.

### 6.4 Committed predictions

Before scoring, the following are committed and hashed:

- **Affix lexicon per arm.** The finite set of rendered prefix chains and suffix chains each arm generates.
- **Training cores per fold.** Each fold's partner list, every training form with its ≥ 2-sign runs. It is computed
  from training documents alone, by a script that is never passed the held-out type.

The predicted form set for a fold is the product of the affix lexicon and the training cores. The scorer tests
membership without materializing the product. Scoring is a lookup against committed objects, and no step after the
freeze can change what counts as a hit.

### 6.5 Folds

- **Primary:** leave-one-type-out, with every document containing the type removed from training.
- **Sensitivity:** leave-one-site-out, which leaves Haghia Triada (about 54% of legible types) as one fold.

### 6.6 C2: prospective formula registration

- **Training** is every legible formula token now held: the family, the six candidates and the three further
  inscriptions.
- **Committed sets.** For each slot and arm, the full predicted form set (core runs of ≥ 2 signs from the slot's
  forms × the arm's affix lexicon) is published as `protocol-c/predictions/formula/<arm>.tsv`, with per-arm sizes.
- **Eligible inscription:** first published after the tag date (the edition's date of publication), on a
  non-administrative support, with a token sharing a ≥ 3-sign run with a slot form. The slot is the one of maximal
  run.
- **Hit:** the token passes §7, is not identical to a training form, and its CV key lies in the arm's set.
- **Report-only** until 20 scorable tokens accrue. At that point the test is the exact Poisson-binomial
  hits-count test against per-token null probabilities q_i. Each q_i is the probability that random same-length
  edges, drawn from the corpus unigram distribution, land in the set. One-sided, α = 0.05.

### 6.7 C3: alternatives rejected as evidence

- **Positional and arithmetic families.** The KU-RO and KI-RO lines, commodity rows and sealing formulae fix a
  word's function by arithmetic or position, so every reading of KU-RO predicts the same totals. They test the
  machinery, not the language. They may serve as a positive control for the pairing code, outside the gate.
- **Retrospective score of PR Za 1 and ZA Zb 3.** Two tokens, both read in *Ya Diktu*. Even two hits give
  p ≥ 0.12 at q = 0.35. They are not scored.

## 7. Damage rule (mechanical, before scoring)

Decided from `corpus.json` fields alone. Nothing is read from photographs or commentary at scoring time.

- **D1.** Exclude a token whose `transliteratedWords` entry contains `[`, `]`, `…`, `?` or `·`.
- **D2.** Exclude a token whose `words` entry contains the lacuna glyph U+1076B.
- **D3.** Exclude every token of a document flagged `needs_visual_review: true`.
- **D4.** At a line break (`\n`) with no divider (𐄁) on either side: if the token across the break is a single
  syllabic sign, exclude both it and its neighbour. This catches IO Za 16 (JA-SA-SA-RA / ME) and PK Za 11
  (A / SA-SA-RA-ME).
- **D5.** Exclude a token whose immediate neighbour, with no divider between, is a lacuna-only element.
- **D6.** Exclude logograms, numerals, fractions and ligatures. Signs without a secure Linear B value stay in as
  opaque symbols (§4).

The rule applies identically to the training pool, the test set, C2 and the pseudo-corpora where markers exist. The
counts excluded under each clause are reported.

## 8. Nulls and tests (C1)

All tests are one-sided, at α = 0.05. p = (1 + #{null ≥ observed}) / (1 + B), with ties counted against H1. Zero
exceedances are reported as p < 1/B.

### 8.1 T1, structure: null R (primary structure null)

- Each test type x keeps its **core**: the union of positions covered by maximal ≥ 2-sign runs with its partners.
- Every other position is redrawn i.i.d. from the unigram distribution of the fold's training signs, opaque symbols
  included, at the same length.
- Partners and hits are recomputed by the same code.
- B = 10,000, seed 20261101. Script: `protocol-c/scripts/null_r.py`, built from the review's `null_r.py` and
  generalized to C1.
- p_R(a) tests whether arm a explains the real edges more often than random edges on the same stems.

### 8.2 T2, language: null L (shape-matched random inventories)

- For arm a, each random inventory has exactly a's order classes, its morpheme count per class and each morpheme's
  CV-slot pattern (onset, vowel, coda).
- Consonants and vowels are redrawn from **a's own phoneme pool**, the stricter null because it keeps a's phoneme
  frequencies, and are rendered by §5.5.
- B_L = 2,000, seed 20261102. Script: `protocol-c/scripts/null_inventory.py`, built from the review's
  `rand_inv.py`, with the pool and seed stated in its header.
- A uniform-pool variant (the secure grid's consonant series plus zero onset, five vowels) is reported beside it.
- p_L(a) is the share of random inventories with H ≥ H_a. No best-of-many pick enters: one pre-registered inventory
  is compared with the full distribution.

### 8.3 T3, rivals: excess over the shape-matched null

- For each type x, π_a(x) is the share of a's random inventories (from 8.2) that hit x.
- The excess is e_a(x) = hit_a(x) − π_a(x).
- For H1 arm h and rival r: D_hr = Σ_x [e_h(x) − e_r(x)].
- The test is a one-sided sign-flip permutation over types: 10,000 flips, seed 20261103, Holm across the four
  rivals. Raw hits and exact McNemar counts are reported beside it.

### 8.4 Secondary and reported

- **S1, D2c** (reported). Test types rebuilt as core plus one draw from a random shared affix inventory, sized as the
  free arm's training inventory. Seed 20261106. B's D2, adapted to slotless data.
- **S2, value permutation** (§4, Secondary 3). It decides the phonetic wording in §14.
- The free arm's p_R, which tests whether unseen Linear A edges recur as a paradigm at all.

### 8.5 Decision rule

- **Arms and order.** The two co-primary H1 arms, `cs` and `yd`, are each tested on T1, T2 and T3. Holm's
  correction runs across the two arms at each test.
- **When an arm passes.** An arm passes when T1, T2 and T3 against every rival all reject after correction.
- **Not a gate.** Other arms' results do not gate an H1 arm. They are reported with the same prominence, and a
  rival that passes its own T1 and T2 is reported as passing.

## 9. Calibration gate (before any Linear A scoring)

### 9.1 Pseudo-corpora

Known-language texts are rendered by the frozen renderer from edition transliteration and cut into
pseudo-documents matched to the Linear A pool's document-size distribution. Each pseudo-corpus holds the registered
number of test types, with mean signs per word within 0.5 of T's mean. K = 20 pseudo-corpora per language, seed
20261104, disjoint where the text suffices, with overlap reported otherwise.

| Language | Source (held snapshots of B2 where they exist) |
|---|---|
| Ugaritic | Copenhagen Ugaritic Corpus, KTU 1.x and 2.x |
| Hebrew | OSHB |
| Mycenaean Greek | DAMOS, every verified PY and KN tablet |
| Luwian | ACLT |
| Egyptian | ORAEC / TLA sentences |
| Hurrian | TLHdig and EA 24. C1 needs no lemmatization, so Hurrian is now buildable |

### 9.2 Criteria

These are fixed now, before any control result is seen. Each criterion is a count over 20 full-size pseudo-corpora,
with no medians and no ties.

- **G-a (sensitivity).** `cs` passes §8.5 on at least 14 of 20 Ugaritic and at least 14 of 20 Hebrew
  pseudo-corpora.
- **G-b (specificity).** `cs` passes §8.5 on at most 2 of 20 pseudo-corpora of each non-Semitic language (Greek,
  Luwian, Egyptian, Hurrian).
- **G-c (free arm).** The free arm's T1 rejects on at most 2 of 20 shuffled-edge corpora (every pseudo-corpus with
  its edges redrawn as in 8.1).
- **Rival own-power** (reported, not gated). Each rival's pass rate on its own language. A rival below 14 of 20 is
  worded "unable to detect its own language" in §14.

No single window can decide the gate. A window is one of 20 independent full-size replicates, and every criterion is
a count.

**If the gate fails**, nothing is scored on Linear A. The failure is reported. Any change is a dated amendment
followed by a new gate run on fresh seeds.

The `yd` arm is not gated on controls. It has no own-language text. Its interpretation rests on the `cs` gate and
on T2.

## 10. Power study (before the freeze)

### 10.1 Analytic bound (computed for this draft, no Linear A data)

The minimal planted share ρ\* detectable at 80% power, exact binomial test, α = 0.05, null per-type hit rate q
(`scratchpad/protocol-c/mde.txt`):

| n types | q = 0.20 | q = 0.35 | q = 0.50 | q = 0.65 |
|---|---|---|---|---|
| 2 (formula candidates) | none (α unreachable for q ≥ 0.35) | — | — | — |
| 20 (C2 threshold) | 0.34 | 0.48 | 0.60 | 0.67 |
| 57 (Option B's tokens) | 0.20 | 0.26 | 0.35 | 0.45 |
| 315 (C1, counted) | 0.08 | 0.11 | 0.14 | 0.20 |

Here ρ is the share of test types whose edges are genuine inflection with a genuine partner. At m = 2 most
partners are chance, so ρ in a real language sits well below 1.

### 10.2 Synthetic plant study (registered, run at phase C4)

- **Synthetic corpora.** They take the frozen pool's shape: the registered n, the length distribution, document
  sizes and the partner-count distribution. Forms come from the corpus bigram model. No real Linear A residue is
  scored.
- **Plants.** A share ρ ∈ {0, 0.05, 0.10, 0.15, 0.20, 0.30} of test types is built as a shared stem plus an affix
  chain drawn from arm a's inventory, with the partner built the same way.
- **Size.** 1,000 corpora per (ρ, arm), with R at B = 500 and L at B = 200 per corpus, seed 20261105.
- **Reported:**
  - type I at ρ = 0 per test, which must be ≤ 0.064 (α plus two standard errors at 1,000 runs), or nothing is
    frozen until a dated amendment,
  - power of the §8.5 decision per arm and ρ,
  - the cross-talk matrix (plants in arm r passing as `cs` or `yd`).
- **Registered wording.** If the power of `cs` at ρ = 0.20 is below 0.5, the result page states the test as
  underpowered in its first sentence, and a negative result is worded as uninformative below the detectable ρ.

## 11. Freeze mechanics

di Mino commits and tags. This section describes what he commits.

1. **Location.** The public kaphtor repository, directory `protocol-c/`. Its contents:
   - this protocol (signed),
   - `inventories/` (JSON, `TABLES.md`, builder transcripts),
   - `render/`,
   - `scripts/`,
   - `inputs/`: `corpus.json` and the *Ya Diktu* forms list as **copies, never symlinks**, with the PDF's SHA-256,
   - `predictions/`: affix lexica, training cores per fold and the C2 formula sets,
   - `controls/`: pseudo-corpora and the gate output,
   - `power/`.
2. **Manifest.** `protocol-c/SHA256SUMS` covers every file above.
3. **Tag.** An annotated tag `protocol-c-freeze`, whose message carries the SHA-256 of `SHA256SUMS`. The push to the
   public remote dates the freeze externally. An archival snapshot (Software Heritage or Zenodo) is di Mino's option.
4. **Runner.** `protocol-c/scripts/score_c.py` refuses to start unless:
   - the working tree is clean,
   - HEAD equals the tag's commit,
   - `SHA256SUMS` matches the hash in the tag message,
   - every listed file matches its hash,
   - no input path is a symlink.

   It stamps the tag, commit and hashes into `runs/<timestamp>/manifest.json`.
5. **Order.** C0 to C4 run before the tag and are included in it. None of them scores a Linear A form under any arm.
   The scoring run (C6) happens once, after the tag.
6. **Amendments** are dated, committed and tagged before C6. None is made after.
7. **No orphan numbers.** Every figure in the result page cites a committed script and a run directory. A figure
   without both is withdrawn.

## 12. Phases

| Phase | Deliverable | Gate |
|---|---|---|
| C0 | Signed protocol, `TABLES.md` with section numbers, `series.json` | di Mino signs |
| C1 | Blind inventories (six arms), own-language selftest, parity report | own-language ≥ 90% per arm. Inventories hashed |
| C2 | Renderer, aligner, generator, nulls, with unit tests on synthetic strings only | tests pass |
| C3 | Pseudo-corpora and calibration gate (§9) | G-a, G-b, G-c |
| C4 | Power study (§10.2), registered n counted by frozen code | type I ≤ 0.064 |
| C5 | Commit and tag (§11), C2 predictions published | hashes |
| C6 | One scoring run, result page published whichever way it falls | — |

## 13. Known limits

1. **Word edges only.** C1 tests affix shape at word edges. It does not test meanings, syntax or any single reading.
2. **The pool is administrative.** Haghia Triada supplies about 54% of legible types, mostly names and commodity
   words. Administrative vocabulary carries less inflection than prayer, so ρ is low in any language.
3. **Held out against citation, not memory.** The `yd` arm is held out against what *Ya Diktu* cites, not against
   its author's knowledge of the corpus. The project's lexicon and campaign files name nearly every legible form
   (592 types counted, 10 unnamed). The blind arms are held out against both.
4. **Chance partners.** m = 2 admits many chance partners. Null R prices them, at the cost of power.
5. **Linear B values are a convention.** They are fitted to Greek, and backward projection has its own problems
   (Steele and Meissner, "From Linear B to Linear A," 2017). They under-write Semitic gutturals and
   emphatics, and Egyptian and Hurrian phonology likewise. The `greek` arm holds the home advantage.
6. **Renderer choices bind every arm alike,** but they are choices: the series table and the spelling union.
7. **Control corpora** are rendered from transliteration and carry no scribal noise. Egyptian stems carry a filler
   vowel.
8. **The predictions are generators, not lists.** C1's committed predictions are generators (affix lexicon ×
   training cores), not enumerated lists. The commitment is exact but not human-readable form by form.
9. **C2 will not reach its threshold** in any foreseeable span at the post-GORILA accrual rate (§3.2).

## 14. Public wording each outcome permits

| Outcome | Permitted wording |
|---|---|
| Gate fails (§9) | "The pre-registered instrument failed calibration on texts of known language. No Linear A result from it is evidence." |
| `cs` passes §8.5, and S2 shows the result depends on the Linear B values | "Under a pre-registered test with Linear B sign values, a Central Semitic affix inventory compiled from Huehnergard's grammar by a builder who never saw Linear A predicted the edges of [n] Linear A word forms not cited in *Ya Diktu* better than random edges on the same stems (p = …), better than random inventories of the same shape (p = …), and better than Luwian, Hurrian, Egyptian and Mycenaean Greek inventories built the same way (p = …). The test measures affix shape. It does not test meanings or the readings of *Ya Diktu*." |
| `cs` passes, S2 does not depend on the values | As above, ending: "The result does not depend on the phonetic values. It shows patterned word edges that a Central Semitic inventory fits, not a phonetic decipherment." |
| `yd` passes §8.5 | "The affixes stated in *Ya Diktu* (2026), rendered with Linear B values, predicted the edges of [n] Linear A word forms the grammar never cites, beyond stem-preserving random edges, random inventories of the same shape and four rival languages (p = …). The grammar was written with knowledge of the corpus. The forms scored are absent from it." |
| T1 passes, T2 or T3 fails | "Unseen Linear A word edges recur as a paradigm, but a Central Semitic inventory [the grammar's affixes] does not predict them better than random inventories of its shape [or than rival languages]." |
| T1 fails | "Under fixed Linear B values, no inventory tested, Central Semitic included, predicted the edges of unseen Linear A forms beyond random edges on the same stems." With power below 0.5 at ρ = 0.20, add: "The test could not detect an effect smaller than ρ = [ρ\*]." |
| A rival passes §8.5 | Reported in the same sentence form, with the same prominence, beside any H1 result. |
| C2, before 20 scorable tokens | "Predictions for the formula's slots were published on [tag date]. [k] scorable tokens have since appeared, with [h] hits. No test is computed below 20." |

No other wording is licensed by this protocol.

## 15. Rulings (di Mino, 2026-10-29)

1. No internal held-out formula test exists. C1 is the primary.
2. `cs` and `yd` are co-primary, with Holm's correction across the two (§8.5).
3. Linear B's tentative values (PA₃, JU, ZU) are opaque in the primary. Secondary 1 reads them, as Shoresh A20 does
   (§4).
4. Spelling: the union of the two conventions is primary, each alone a sensitivity (§5.5).
5. The `greek` arm is added (§5.1).
6. The Egyptian grammar is Allen, *Middle Egyptian*, 3rd ed. (2014). No substitute.
7. Gate thresholds: 14 of 20 and 2 of 20, as in §9.2.
8. Builder: a fresh sandboxed agent session, its full transcript published with the freeze (§5.3).
9. The C2 predictions are published at the freeze (§6.6).

These rulings fix the choices this draft offered. The protocol binds only once signed below.

## 16. Amendments

**A1 (2026-10-29, after signature, while compiling `TABLES.md`, before any inventory is built or any Linear A form
is rendered).** §5.2's "named tables" reads: every (a) numbered or boxed table, (b) itemised list of forms, and (c)
section whose own heading names a §5.2 category (gender, number, state and definiteness, case, person endings or
inflection, non-finite forms, participle, infinitive, derived stems, bound pronouns, prepositions, conjunctions,
enclitics and particles), in the arm's named grammar. A form named only in running prose under a heading that names
no category stays out. Free pronouns (independent, demonstrative, interrogative) stay out in every arm; a form the
grammar itself calls bound enters. The `cs` arm's innovation sources (§5.1: Huehnergard 2005, Huehnergard and Rubin
2011) add the Central Semitic innovations they state in prose; areal features they list as non-diagnostic stay out.
This is an asymmetry in coverage, and §8.2's shape-matched null prices it, since each arm is compared with random
inventories of its own shape. The `yd` arm takes every bound morpheme *Ya Diktu* states (§5.3 item 5). Reason: the
grammars set their paradigms in different forms (Bartoněk states Mycenaean person endings only in prose under the
heading "Personalendungen"; Wegner gives the infinitive its own section; Allen's tables carry no captions), so a
tables-only rule would have measured typesetting, not grammar.

**A2 (2026-10-29, adopted under di Mino's delegation, "use your judgement here", after a Luwian pilot build that is not
part of C1; before any C1 inventory is built or any Linear A form is rendered).** §6.3 and §8.2 use each arm's order classes, but no section sets them, and B's classes were written by
the protocol's author, not by a blind builder. One slot template serves every arm. The builder files each realization
under the slot its grammar's category gives it, in `protocol-c/inventories/schema.json`:

- Prefix side, outer edge to stem: `p_clitic` (bound conjunctions and particles), `p_preposition`, `p_article`
  (a bound prefixed article), `p_person` (finite person, number and gender prefixes), `p_stem` (derived-stem
  prefixes, edge infixes, nominal-pattern, participle and infinitive prefixes).
- Suffix side, stem to outer edge: `s_stem` (derivational and stem-forming suffixes, participle, infinitive and
  verbal-adjective suffixes, tense, aspect and valence markers placed before person endings), `s_gender_number`
  (with a suffixed article), `s_case_person` (case, state, fused number-case, finite person endings), `s_mood`
  (mood and energic endings placed after person endings), `s_pronoun` (bound possessive and object pronouns),
  `s_enclitic`. One further slot, `s_enclitic_inner`, holds enclitics a grammar places before the bound pronouns;
  it is used only with a cited order statement (Luwian Table 8 puts conjunctions and =wa before the pronominal
  clitics and the locative particles after them).

That is the default order. Where an arm's grammar states a different order among these slots, the stated order binds
for that arm, and the builder cites it (section, page) in the file's `class_order.basis`. A fused ending enters once:
under `s_case_person` when it carries case or person (finite endings that also mark tense, mood or voice included),
otherwise under the slot of the category the grammar names first. Zero endings (Ø) are not entered: choosing no
morpheme from a class already generates them. Null L keeps each arm's slots and counts (§8.2), so the
template's size is priced arm by arm. Reason: without it the hit rule is undefined, and leaving order to the builder
would let the number of classes vary by builder, not by grammar.

**A3 (2026-10-29, on di Mino's instruction to use the latest *Ya Diktu*; before any Linear A form is rendered).** Every
reference to *Ya Diktu* at commit `3204dd2` (§3 criterion 2, §5.1 `yd` row) reads commit `d9a3f93` of
`https://www.minoanmystery.org/linear-a/ya-diktu-grammar-tom-di-mino.pdf` (46 pp., SHA-256
`d111b8dbb196b2aaf4b8d50412a1106b7ca29cb531200f6a42a8b64c4c24be9d`, identical to di Mino's desktop copy of
2026-10-29). Reason: `3204dd2` is a 42-page edition fourteen PDF updates old; `tables/yd.md` had been drafted from the
current edition, and the first `yd` build paired that units list with the old PDF (its energic NU and 34 morphemes
came from the old text). That build is set aside. For §3 the newer edition is the stricter pin: it names more forms
(PS Za 2 TA-NA-I-*301-TI, n. 23), so more types are excluded.

**A4 (2026-10-29, di Mino's ruling on the kaphtor port plan; after C1, before any Linear A form is rendered).** Two changes:

1. *Location.* §11 item 1 reads: the record lives under kaphtor's layout, not a top-level `protocol-c/` folder (the
   repository admits no new top-level folder). This text is `docs/protocol-c-preregistration.md`; `inventories/`,
   `render/`, `builds/` and later `inputs/`, `predictions/`, `controls/`, `power/` and `runs/` are under
   `data/linear-a/protocol-c/`; `scripts/` is under `tools/core/frozen/protocol_c/`; `SHA256SUMS` lists
   repository-relative paths.
2. *Transcripts.* §5.3 item 1 and ruling 8 ("full transcript published") read: each builder's event log is published
   with every command's output replaced by its SHA-256 and byte length (`transcript.redacted.jsonl`). The outputs are
   where the copyrighted grammars, local paths and user names appear; commands, file changes and the builder's
   messages are kept whole. The full logs are kept privately, their hashes are in each build's `SHA256SUMS`, and they
   are open to reviewers on request. The blindness audit reruns byte for byte on the redacted logs.

The signed text is kept: `protocol-c/PROTOCOL-C-SIGNED-2026-10-29.md` hashes to the SHA-256 in `SIGNATURE.txt`
(rebuilt exactly from the session's edit record); every later change is an amendment in this section.

## Scratch files (drafting only, not part of the freeze)

The drafting scripts behind the counts in §3 and §10.1 stay in the research tree; none of them computes an arm, inventory or null on Linear A.

## Freeze and signature

Signed: di Mino    Date: 2026-10-29 (given in session, recorded by instruction)

SHA-256 of this file at signature: see `protocol-c/SIGNATURE.txt`.
