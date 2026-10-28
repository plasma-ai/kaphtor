---
name: docs/paradigm-b-preregistration
title: "Paradigm B: Pre-Registration"
desc: The held-out paradigm-prediction test's pre-registration as frozen on 2026-10-09, with the logged amendments that bind it.
tags: [docs]
authors: "di Mino"
status: "FROZEN 2026-10-09T19:44:46Z (option B freeze, SHA256SUMS f5d6733f…); run, G2 failed, no posterior"
created: 2026-10-29T00:00:00Z
updated: 2026-10-29T16:13:43Z
---

# Paradigm B: Pre-Registration

> [!NOTE]
> This is the frozen text, kept as written but for three changes: the private source ids after citations are cut,
> the attribution is "di Mino", and no private path is given. The status line below is the draft's; the protocol
> was approved, built, frozen and run (§14, the freeze record at the end, and
> [paradigm-b-result.md](paradigm-b-result.md)). The amendments logged in the decisions log that bind it follow
> §14, verbatim. The text names files by their paths in the research package it was written in. In this
> repository they are:
>
> | Named here | In this repository |
> |---|---|
> | `scripts/` (`run_paradigm.py`, `render_la.py`, `build_paradigm.py`, `build_windows_b.py`, `selftest_b.py`, `freeze_protocol.py`), `scripts/common/` (`paradigm.py`, `nulls.py`, `stats.py`, `matcher.py`, `paths.py`), `vendor/` (`skeleton.py`, `phonetics.py`) | `tools/core/frozen/paradigm_b/`, same layout |
> | `data/paradigm/<arm>.json`, `data/formula_family.json`, `data/snapshot/corpus.json`, `controls/controls_b.jsonl`, `SHA256SUMS` | `data/linear-a/paradigm-b/` (`paradigm/`, `formula_family.json`, `snapshot/`, `controls_b.jsonl`, `SHA256SUMS`) |
> | `runs/<ts>-paradigm-*` (the five production runs) | `data/linear-a/paradigm-b/runs/<run>.results.json`, `.manifest.json`, `.null_vectors.npy` |
> | `PROTOCOL.md`'s option B freeze record | `data/linear-a/paradigm-b/freeze-record.md` |
> | `STAGE-B-REPORT.md` | [paradigm-b-result.md](paradigm-b-result.md) |
> | `DECISIONS.md` | its rows that amend this protocol, after §14 |
>
> Not in this repository: `PROTOCOL.md` (the stage 1–3 protocol), the stage 1–3 code, snapshots and controls,
> `STAGE3-REPORT.md`, the B2 and B3 reports, `reviews/`, `controls/sources.md`, `controls/render_log_b.json`,
> `data/snapshot/b2_control_tokens.jsonl`, `data/snapshot/lexicon.json` (changed after the freeze),
> `run_manifest.json` (its results hashes are in `data/linear-a/paradigm-b/PORT-LEDGER.json`),
> `sources/sources_database.json` and `campaign_workspace.json`. `tools/linear_a/validation/paradigm_b.py` checks
> the shipped files against the freeze and reruns the runs ([reproduce.md](reproduce.md)).

Pre-registration for the second-stage statistic, written 2026-09-08 after the stage-3 gate of `PROTOCOL.md` failed under both freezes (STAGE3-REPORT.md and its two addenda). Status: **draft for Tom's sign-off; no code written, nothing frozen.** Once approved, the build proceeds through the phases in §12 and stops at the B gate (§9) for Tom's review, exactly as `PROTOCOL.md` §9 stopped at stage 3. Everything in `PROTOCOL.md` §§1–2 (target, family, hypotheses, prior grid, operational definition of prayer) carries over unless amended below.

Attribution: di Mino.

## 1. Why a new statistic

The stage-3 statistic T scored each word by dictionary reach: a word is explained if some entry in an arm's database sits within budget of its consonant skeleton. Both gate runs showed that T measures database coverage and word length, not language (`reviews/METHOD_REVIEW.md` §1–2; STAGE3-REPORT.md second addendum). Linear B outscored Ugaritic prayer because the NWS database is 7–19× larger than any rival and short skeletons saturate it.

Option B drops the dictionary from the statistic. It asks a question the family's own structure poses: the 33 inscriptions repeat a small number of word types with variant forms at fixed slots (§3). Under H1 those variants are inflection: one morphological paradigm, shared across slots, generates them. Under H_ISO they are a transmitted formula with copying noise. Under H2 they are inflection in a language whose paradigm looks different. The statistic is therefore **how well a fixed morphological inventory predicts the variants of a held-out inscription from the variants of the others**. No lexicon enters; word length enters only as the number of scorable pairs, which the controls are matched on.

What B does not test: lexical identity, meaning, or genre. It decides language shape. Genre (prayer against non-prayer) stays with the lineup (`PROTOCOL.md` §7) and the ordering claims in the claims battery (C04, C11). The posterior B can support is P(H0 = not Semitic | D, C); the headline question, P(not a Semitic liturgical prayer), is bounded below by it and is not equal to it (§10).

## 2. Hypotheses and arms (amended)

H1 is stated as **Central Semitic** (Tinitic: an archaic branch sister to Northwest Semitic and Arabic; Tom, 2026-09-08, `DECISIONS.md`). Arms for B:

| arm | inventory | role |
|---|---|---|
| `cs` | Central Semitic morphological inventory: morphemes attested in Ugaritic, Canaanite (Amarna, Phoenician, Hebrew), Amorite, Classical Arabic, Ancient North Arabian (Safaitic, Hismaic, Dadanitic), and Ancient South Arabian (Sabaic) | H1, primary |
| `nws_floor` | the `cs` inventory restricted to morphemes attested in Northwest Semitic | H1, conservative floor, reported alongside |
| `luwian` | Luwian (cuneiform and hieroglyphic) | H2 |
| `hurrian` | Hurrian | H2 |
| `egyptian` | Middle Egyptian | H2 |
| `free` | no language: the inventory is learned from the training fold (§5.2) | the H_ISO-versus-paradigm test only |

H3 (Semitic names, no verbal paradigm) and H4 (mixed) have no arm in B: H3 enters as a control class (§7) and as the weight scheme's alternative, H4 is not separately modeled at the structural level and its weight in the `archaeology` scheme (0.05) is folded into H_ISO. `nws_onomastic`, `mixed` and the dictionary arms of `PROTOCOL.md` are not used by any B statistic.

The classification behind `cs` follows Huehnergard and Rubin 2011 and Huehnergard 2019; the position of Ancient South Arabian inside Central Semitic is contested (Rubin 2008), so every retention count (§4) is recorded with and without the Sabaic witness and both variants are reported.

## 3. The data B scores

Family as frozen 2026-09-08: 33 inscriptions, 129 tokens (68 damaged), mean 3.59 signs per word (IO Za 2: 4.38). Slot occupancy and distinct surface forms:

| slot | filled | distinct forms | forms |
|---|---|---|---|
| 1 | 15 | 5 | A-TA-I-*301-WA-JA ×11, A-TA-I-*301-WA-E, JA-TA-I-*301-U-JA, TA-NA-I-*301-U-TI-NU, TA-NA-I-*301-TI |
| 2 | 7 | 9 | JA-DI-KI-TU, A-DI-KI-TE, A-DI-KI-TE-TE, I-DA, I-DA-A, I-DA-MI, O-SU-QA-RE, TU-RU-SA, DU-*314-RE |
| 3 | 10 | 5 | JA-SA-SA-RA-ME ×6, SA-SA-RA-ME, JA-SA-SA-RA, JA-SA-SA, JA-SA-SA-RA-MA |
| 4 | 9 | 6 | U-NA-KA-NA-SI ×4, U-NA-RU-KA-NA-SI, U-NA-RU-KA-NA-TI, U-NA-RU-KA-JA-SI, U-NA-KA-NA, SE-KA-NA-SI |
| 5 | 9 | 3 | I-PI-NA-MA ×6, I-PI-NA-MI-NA ×2, I-PI |
| 6 | 8 | 2 | SI-RU-TE ×7, SI-RU |
| 7 | 1 | 1 | TA-NA-RA-TE-U-TI-NU |

The table describes the frozen input; it is not used to build any inventory (§4 forbids it). Slot 7 has one form and is unscorable in every fold. IO Za 2's scorable tokens when it is held out are its slot-1, -2, -3, -4, -5 and -6 words.

## 4. Morphological inventories (`data/paradigm/<arm>.json`, built by `scripts/build_paradigm.py`)

One file per arm. A morpheme entry:

```json
{"id": "cs_pref_person_ya", "arm": "cs", "kind": "prefix" | "suffix",
 "position": 2,                          // order class within its side (§4.2)
 "phonemic": [["y","a"]],                // CV slots; consonant-final morphemes end with [C, null]
 "function": "3ms prefix-conjugation person marker",
 "attested_in": ["ugaritic", "hebrew", "arabic", "safaitic", "sabaic"],
 "citations": ["Huehnergard 2012 §…", "Al-Jallad 2019 §…", "Beeston 1984 §…"],
 "cost": 0.0,                            // 0 = retention; > 0 = priced innovation (§4.3)
 "innovation_id": null}
```

### 4.1 Sources and the blindness rule

Every entry is encoded from a grammar of the language, cited by section, and **no entry may cite, quote, or be motivated by any Linear A form**. `build_paradigm.py` refuses to write an arm whose `citations` or `function` strings match any token of `data/formula_family.json`, any lexicon.json headword, or the strings "Linear A", "Minoan", "Ya Diktu". This is stronger than stage 3's `blind` mode, which repriced target-citing templates but kept them; B's inventories cannot contain them. The four `verb_templates.json` chains of stage 3 (`gt_ata_prefix`, `gt_ja_ta_infix`, `tana_3fs_n`, `suffix_utinu`) do not exist as entries; whatever they described must be re-derived from the grammars as ordinary morphemes plus an ordering rule, or it is absent.

Grammars (records to be added to `sources/sources_database.json` before REPORT-B cites them; those already present are marked):

- Central Semitic: Huehnergard 2012 (Ugaritic); Tropper 2000; Rainey 1996 (Amarna); Huehnergard 2019 (Proto-Semitic); Lipiński 1997; Al-Jallad 2019 (historical grammar of Arabic); Al-Jallad 2015, *An Outline of the Grammar of the Safaitic Inscriptions* (to add); Beeston 1984, *Sabaic Grammar* (to add); Streck 2000, *Das amurritische Onomastikon* (to add).
- Luwian: Melchert 2003 (in *The Luwians*), Payne 2010 (*Hieroglyphic Luwian*), Yakubovich 2010 (to add); the project's `ref-luwian-grammar-reference.md` is a secondary pointer only.
- Hurrian: Wegner 2007 (*Einführung in die hurritische Sprache*), Giorgieri 2000 (to add).
- Egyptian: Allen 2014 (*Middle Egyptian*, 3rd ed.), Gardiner 1957 (to add).

### 4.2 Order classes

Each side of the stem carries ordered position classes; a residue is generated by choosing at most one morpheme per class in class order (empty classes allowed). Central Semitic:

- prefix classes: (1) proclitic conjunction/particle {wa-/u-, pa-, la-, ka-}; (2) person prefix {ʾa-, ta-, ya-, na-, ni-/yi- variants as attested}; (3) stem prefix {N na-/n-, tG ta-/t-, Š ša-/sa-, nominal ma-/mu-/mi-}.
- suffix classes: (1) stem/gender {-t, -at, -āt, -ān, -ay/-ī nisba, -ūt}; (2) number/case {-u, -i, -a, -ā, -ū, -ī, -ūna, -īna, -m mimation, -n nunation}; (3) pronominal {-ī, -nī, -ka, -ki, -hu, -ha, -na, -kum, -hum}; (4) energic {-n, -an, -anna}; (5) enclitic {-ma, -mi, -ya}.

Luwian: no prefix classes except the sentence-initial particle chain {a-, pa-, wa-, -ha, -tta, -ta, -du} treated as one class; suffix classes: stem/derivational {-alli-, -assi-, -wanni-, -ahi-, -ai-}, number/case {-s, -n, -i, -a, -ati, -anza, -nzi, -za}, verbal person {-wi, -si, -ti, -mi, -nti, -ha, -ta, -nta, -tu, -ntu}. Hurrian: no prefixes; suffix classes: root complements {-an-, -ol-, -ošt-, -ug-, -ill-}, valence/tense {-a, -i, -o, -ož, -ed-}, agreement {-b, -m, -ll-, -a, -nna, -nni}, nominal {-ne, -na, -we, -wa, -da, -ni, -ffe, -iffe}, enclitics {-ma, -an, -nna}. Egyptian: prefix classes {s- causative, m- nominal, particle jw/mk/jn}; suffix classes: gender/number {-t, -w, -wj, -tj, -wt}, verbal endings {-n, -w, -t, -jn, -ḥr, -kꜣ, -tw passive}, suffix pronouns {-j, -k, -ṯ, -f, -s, -n, -ṯn, -sn}.

Parity, enforced by the builder (exit 3 otherwise): the count of **distinct realizations** (kind × phonemic shape, collapsing a morpheme listed in several order classes) of every H2 arm is within 1.5× of `cs`. The count of one-sign realizations (the strip depth the method review flagged) is reported per arm and capped at a 2.0 ratio. Amended at B1 (2026-09-08, before any run, logged in `DECISIONS.md`): the draft put the 1.5 bound on both counts; at build the distinct counts were cs 69, Luwian 59, Hurrian 62, Egyptian 60, and the one-sign counts cs 55, Luwian 37, Hurrian 40, Egyptian 29 with the prepositions still to add. The one-sign gap is typological, not an encoding shortfall: twelve of the Central Semitic one-sign prefixes are the person prefixes of the prefix conjugation, which Egyptian and Hurrian lack and Luwian lacks, and the Egyptian inventory is exhaustive for Allen 2014. Forcing equality would mean omitting attested Semitic morphology or inventing rival morphology. The check that the extra strips do not over-explain rival text is the leakage matrix (§8.2, red flag 2), and the calibration gate (§9 G2) measures the consequence directly on known-language windows. `nws_floor` is a subset of `cs` and is exempt from parity.

### 4.3 Costs: retentions and innovations (Tom, 2026-09-08)

Corrected before B1 (2026-09-08, logged in `DECISIONS.md`): the first draft priced any morpheme attested in fewer than two branches, which would have charged ordinary Ugaritic morphology (the Š-causative, the Hebrew article) because Arabic lacks it. The rule as built: **a morpheme attested as productive morphology in at least one Central Semitic language costs 0** and enters `cs`; the headline `cs` inventory takes its morphemes from Northwest Semitic and Arabic (Classical and Ancient North Arabian), and morphemes attested only in Ancient South Arabian enter the with-Sabaic variant (§2) and are reported alongside. `attested_in` records every language each morpheme is cited from, so the branch count is available for the report. The energic suffix, the t-stem, the feminine and abstract -t suffixes, the person prefixes ʾa-/ta-/ya-/na-, the N-stem (assimilated in Ugaritic and Hebrew, unassimilated in Arabic VII), mimation/nunation and the pronominal suffixes are therefore all at 0. Only claims attested in no Central Semitic language are priced, carried over from `data/innovations.json` with the same citations and moved into the inventory as ordering or membership rules:

| innovation | cost | how it enters B |
|---|---|---|
| energic after the object suffix (`energic_after_object`) | 0.40 | class order (3) pronominal → (4) energic is the rule; the reversed order is generated only in the `ext` inventory (§5.4) and charged |
| archaic *-t- object suffix (`archaic_t_object_suffix`) | 0.40 | a pronominal-class member {-ti, -ta} present only in `ext`; no Central Semitic branch attests it as an object suffix, so the ≥ 2-branch rule leaves it priced. **Tom to confirm**: the 2026-09-08 note said "archaic -t- suffixes" cost 0; this protocol reads that as the feminine/abstract -t set, not the object series |
| N-stem nun unassimilated before /r/ (`n_stem_na_before_r`) | 0.25 → 0 | attested unassimilated in Arabic VII (yanfaʿilu); an attested Central Semitic morpheme under the corrected rule |
| tG -ta- vocalization (`tG_ta_vocalization`) | 0.25 → 0 | the prefixed t-stem (Ugaritic tD, Arabic V/VI, Hebrew hitpaʿel, Sabaic t-) is attested; its vowel is a rendering choice (§4.4) and not a morphological claim |

Egyptian morphemes carry reconstructed vowels (Loprieno 1995 §4; Allen 2014 §2.8) rather than the Egyptological /e/ filler, so that the Egyptian arm is not restricted to E-vowel signs on the family; the B2 Egyptian control windows render their affixes with the same reconstruction and their stems with the filler, and the convention is recorded in `controls/sources.md`.

Rival arms carry the same rule: any rival morpheme the builder cannot anchor in the cited grammar is excluded, not priced (a rival arm has no `ext` inventory).

### 4.4 Rendering morphemes to signs

A residue is a sign string. Each morpheme's realizations are produced by the frozen renderer (`scripts/render_la.py`, function `render_morpheme(phonemic, prev_vowel, arm) -> set[str]`, to be added): CV morphemes render sign by sign; a consonant-final morpheme takes a dead vowel by the spelling reference's rule (echo of the preceding vowel, alternatives enumerated as the renderer already does for control words); script neutralizations (T-series for t/d/ṭ/ṯ/ṣ, K-series, P-series, S-series, unwritten gutturals, y/w) are those of `data/transducer_rules.json`, applied identically to every arm. A case vowel that is written on the stem's final sign (-u/-i/-a) is a zero-sign morpheme that constrains that sign's vowel; the pairwise alignment (§5.1) exposes stem-final vowel alternations as residues of the form `(C, v₁) → (C, v₂)`.

Vowel strictness: `strict` requires consonant and vowel to match the realization; `cons` matches consonants only. `strict` is primary (Astra: "exact does not mean syllable-for-syllable"); `cons` is an ablation.

## 5. Statistics

### 5.1 Pairs and residues (arm-independent)

For a slot s and two forms f, g at s, let r(f, g) be their longest common contiguous sign run (leftmost on ties). The pair is **scorable** if |r| ≥ 2 signs. Its residues are the sign strings of f and g outside r: prefix residue and suffix residue for each. Pairs are formed within a slot only. For a held-out inscription X and each of its slot tokens x, the **prediction set** is {g : g a training-fold form at the same slot, (x, g) scorable}. A token with an empty prediction set is unscorable and enters no denominator.

### 5.2 A_free: is there a shared paradigm at all?

Training inventory = the set of prefix residues and the set of suffix residues over all scorable training pairs (whole residues, not signs). Held-out token x is **predicted** if some g in its prediction set gives residues of x that are both in the training inventory (empty residue always counts as in). A_free(fold) = predicted / scorable held-out tokens. A_free = mean over folds.

Under a formula copied with noise (null D) residues are single random signs and recur across slots at chance; under a shared paradigm they recur because they are the same morphemes. A_free is the H_ISO-versus-paradigm test and says nothing about which language.

### 5.3 A_arm: does a named language's paradigm predict the variants?

Held-out token x is predicted by arm a if some g in its prediction set gives residues for x **and** for g that are both generated by a's inventory (class order respected, ≤ 1 morpheme per class, realizations per §4.4). A_a(fold), A_a as above. Nothing is fitted on the training fold for arm a except the prediction set; the inventory is fixed before the run. The comparative statistic:

Δ = A_cs − max(A_luwian, A_hurrian, A_egyptian), with Δ_floor using `nws_floor`.

Both A_cs and Δ are gate statistics (§9); single-arm AUCs are reported because the stage-3 max-over-rivals lost information (`METHOD_REVIEW.md` §2).

### 5.4 Variants

- `strict` / `cons` vowel handling (§4.4).
- `base` / `ext` inventory: `ext` adds the priced innovations; A_cs^ext counts a token predicted through a priced morpheme as predicted and reports the innovation charge separately (sum of costs over predicted tokens), never subtracted from A.
- Folds: **leave-one-site-out** (10 sites: Iouktas 11, Palaikastro 9, Syme 5, Apodoulou 2, Troullos, Kophinas, Vrysinas, Platanos, Psykhro, Knossos 1 each) is primary, because every inscription informed the hypothesis and site is the coarsest grouping (Astra memo §5 step 7). Secondary: 1,000 random 25/8 splits, seed 20260908 + 11. Identical folds are applied to every null replicate.

## 6. Nulls

| null | what it preserves | what it tests | B | seed |
|---|---|---|---|---|
| D (as `nulls.null_d`, frozen) | slot occupancy, recurrence, missingness, one-sign variation at the observed rate; forms from the corpus bigram model | A_free above a copied formula with noise | 10,000 | 20260908 + 5 |
| D2 (new, `nulls.null_d2`) | as D, plus a **random shared affix inventory**: k prefix and k' suffix residues drawn from the bigram model with the observed residue-length distribution, k and k' equal to the observed training-inventory sizes; each variant form is stem + one random inventory prefix and/or suffix at the observed variation rate | A_cs and Δ above a formula that has a paradigm which is not any particular language's | 10,000 | 20260908 + 6 |
| D2×2 | D2 with k, k' doubled | sensitivity of D2 to inventory size | 10,000 | 20260908 + 7 |

D2 is the H_ISO likelihood source for B (§10); D is reported. p = (r+1)/(B+1) with Clopper–Pearson interval, zero exceedances as p < 3/B, never multiplied.

## 7. Controls (`controls/controls_b.jsonl`, built by `scripts/render_la.py --stage b`)

A B control is a **window family**: 6–12 forms of known language in which at least two word types recur with variants, rendered by the frozen renderer from the hand transliteration in `controls/sources.md` (extended in place, with edition and page for each). A window must yield ≥ 4 scorable pairs or it is dropped and the drop logged. Controls are matched to the family on two quantities, both reported per window: mean signs per word (the stage-3 band of 0.5 around the family's 3.59 applies to the length-matched AUC) and scorable-pair count (windows are cut to 6–12 pairs).

Classes:

- **H1 Central Semitic** (positive): Ugaritic ritual and prayer with recurring inflected stems (KTU 1.119, 1.40, 1.41 with its duplicate 1.87, 1.14, 1.23); Hebrew Psalms and blessings already in stage 3; **Safaitic and Hismaic invocations from OCIANA** (snapshot `arabian_epigraphy.jsonl`, 59 `deity_invocation` records: the *h lt s¹lm* / *h bʿls¹mn rwḥ* formula with its variant slots is the closest structural analogue to the Linear A family: short rock inscriptions repeating one invocation with lexical and inflectional variation); Sabaic dedications from `south_arabian_epigraphy.jsonl` where a recurring formula exists.
- **H3 Semitic non-prayer**: Amorite name windows (H3 has case, mimation, hypocoristic and theophoric variation but no verbal paradigm) from the withheld set; Ugaritic legal/letter windows of stage 3. H3 counts as Semitic in AUC(language).
- **H2 Luwian**: continuous text with paradigm variation, not the stage-3 paradigm lists: KARATEPE 1 §§1–20 (Payne 2010; its Phoenician twin KAI 26 is an H3 control), the Zarpiya ritual KUB 35.54, Kululu lead strips.
- **H2 Hurrian**: Mittani letter EA 24 windows, Boğazköy ritual windows, the Nikkal hymn.
- **H2 Egyptian**: the 377 ḥtp-dj-nswt sentences (`egyptian_htp_dj_nswt.jsonl`) cut into formula families (recurring *ḥtp dj nswt … dj.f prt-ḫrw …* with variant slots); Coffin Text spell duplicates.
- **NEG Linear B**: PY Tn 316, KN Fp 1, KN Fh series (theonym case alternation di-we / di-wo, po-se-da-o-ne / po-se-da-o), extended with the PY Es and Un series to reach the pair count; hand-transcribed from Docs² / DAMOS with citation.
- **H2 unknown**: Eteocretan, reported and not gated.

Target size: ≥ 12 windows per gated class (H1, H3, H2 each language, NEG). Power: at AUC 0.85 with 12 positives and 24 negatives the bootstrap 95% half-width is about 0.12, so the pass criterion uses the point estimate and the lower bound (§9). Existing stage-3 controls that meet the window definition are reused; the H3 Amorite windows stay withheld from nothing in B (no dictionary is used) but keep their hold-out file for the claims battery.

## 8. Selftest (`scripts/selftest_b.py`)

1. **Own-language parse:** each arm's inventory, applied to a fixed list of 40 attested inflected forms of its language (listed in the inventory file with citations: for `cs` from KTU 1.119 and 1.14, the Safaitic corpus, and Sabaic; for the rivals from the grammars' paradigm tables) rendered by the renderer, generates the form's affixes in ≥ 90% of cases. The stage-3 inventory could not analyse KTU 1.119's *nšqdš* or *tqrb*; this test fails the build if `cs` cannot.
2. **Cross-language leakage:** the same 40-form lists scored by every other arm; the matrix is printed and frozen. No pass threshold; a rival arm that explains ≥ 70% of Ugaritic forms, or `cs` that explains ≥ 70% of Luwian forms, is a red flag (§11).
3. **Blindness:** builder rejection of target-citing entries exercised on a deliberately bad entry.
4. **Pairs:** r(f, g) and residues on ten hand-computed pairs; slot 7 unscorable; empty residue counts as predicted.
5. **D2:** slot matrix preserved; inventory sizes as specified; determinism by seed.
6. **Parity:** counts and one-sign counts within 1.5×.
7. **Timing:** 1,000 D2 replicates with leave-one-site-out folds under 60 s on 12 workers.

## 9. Gate (blind by construction; stops for Tom's review)

- **G1 (structure).** A_free(family, leave-one-site-out, strict) exceeds the 95th percentile of A_free under null D. Failure: the family's variation is not distinguishable from copying noise, and no language statistic is interpretable; report and stop.
- **G2 (calibration).** On the controls, length-matched AUC(language) on Δ (H1∪H3 against H2∪NEG) ≥ 0.85 with bootstrap lower 95% bound > 0.50; the same on A_cs alone reported and required ≥ 0.75; no Linear B window's Δ above the median Δ of H1 windows in its length band. Failure: the structural statistic does not separate language on known texts; report and stop, no posterior.
- **G3 (family).** With G1 and G2 passed: Δ(family) exceeds the 95th percentile of Δ under D2; A_cs(family) ≥ the median A_cs of H1 windows; A_cs(family) > A_a(family) for every rival a. G3 passing or failing is a result, not a gate: both outcomes proceed to §10 and are reported with the same prominence.

Thresholds are those of `PROTOCOL.md` §5, unchanged. The gate is computed in the `strict` / `base` configuration; every other configuration is an ablation (§11).

## 10. Likelihoods and posterior

Conditional on G1 and G2 passing: p(Δ_obs | class) by Gaussian KDE (Silverman, ±50% bandwidth) on the control classes for H1 (H1 windows), H2 (each language's windows), H3 (H3 windows); H_ISO from the D2 replicate distribution at family scope. Bayes factor and posterior as `PROTOCOL.md` §2 (π ∈ {0.02, 0.05, 0.10, 0.25, 0.50}, headline 0.10; `uniform`, `archaeology`, `nws_skeptic` schemes with H4's weight folded into H_ISO). Where Δ_obs exceeds every sample of a class, the 1/(n+1) bound and a bounded Bayes factor.

Headline sentence of REPORT-B: "P(the family's language is not Semitic | D, C, modeled alternatives) = X [a, b] at π = 0.10, archaeology-weighted." The prayer question is stated as: P(not a Semitic liturgical prayer) ≥ X, with the genre component carried by the lineup and the claims battery and not by this statistic.

## 11. Ablations and red flags

Ablations, reported side by side and never combined: `cons` vowels; `ext` inventory (with its innovation charge); random 25/8 folds; `nws_floor` in place of `cs`; drop slot 1; drop slot 2; drop damaged tokens; D2×2; Sabaic in/out of the retention count; family with the six pending candidates in `data/family_additions.json` if Tom approves them before the B freeze (after the freeze they are excluded).

Red flags (any hit blocks the headline number): (1) A_cs(family) exceeds every H1 control; (2) the leakage matrix (§8.2) shows a rival arm explaining ≥ 70% of Ugaritic forms or `cs` explaining ≥ 70% of a rival's forms; (3) parity broken; (4) any inventory entry found to cite the target after the freeze; (5) A_cs under D2 has mean ≥ A_cs(family); (6) |AUC(Δ) − AUC(A_cs)| > 0.15 in either direction without a stated cause; (7) G3 passes only in `ext`.

## 12. Build phases (each ends with a report to Tom; no phase starts on a failed predecessor)

| phase | deliverable | files (new unless noted) | gate |
|---|---|---|---|
| B1 | inventories + selftest 1–3, 6 | `scripts/build_paradigm.py`, `data/paradigm/{cs,nws_floor,luwian,hurrian,egyptian}.json`, `scripts/selftest_b.py`, `render_la.render_morpheme` (edit) | own-language ≥ 90% for every arm; leakage matrix printed |
| B2 | control windows | `controls/sources.md` (append), `controls/controls_b.jsonl`, `controls/render_log_b.json`, new snapshots in `data/snapshot/` (`arabian_epigraphy.jsonl`, `south_arabian_epigraphy.jsonl`; Linear B, Luwian, Hurrian, Egyptian hand transcriptions) | ≥ 12 windows per gated class, ≥ 4 pairs each |
| B3 | statistic + nulls, debug | `scripts/common/paradigm.py` (pairs, residues, A), `scripts/common/nulls.py` (`null_d2`, edit), `scripts/run_paradigm.py`; selftest 4, 5, 7 | debug B = 1,000 under 60 s |
| B4 | freeze | this file's freeze record via `freeze_protocol.py --refreeze "option B freeze"`; `SHA256SUMS`, `run_manifest.json` | hashes |
| B5 | gate run | `runs/<ts>-paradigm-*` for family, controls, D, D2; `STAGE-B-REPORT.md` | **stop for Tom** |

`PROTOCOL.md` §9's file-count scope gate applies per phase. Nothing is committed and nothing is logged to `campaign_workspace.json` until Tom signs off on the B result. `data/snapshot/` grows by the files listed in B2 and by nothing else; the stage-3 snapshot files are untouched.

## 13. Decisions needed from Tom before B1 starts

1. The archaic *-t- object suffix: priced at 0.40 in `ext` (this protocol's reading of the 2026-09-08 note) or a retention at 0.
2. Ancient South Arabian inside the Central Semitic retention count: both variants are reported; which is the headline.
3. The six pending family candidates (PR Za 1, ZA Zb 3, PK Za 15, KH Zc 106, NE Za 1, PK Za 17): approve any before the B freeze or leave them as the ablation.
4. Go for B1.

## 14. B3 amendments (2026-10-09, before any run on the family or controls)

- §5.1: the prediction set excludes training forms identical to the held-out form at the CV level (Tom; `DECISIONS.md` amendment 9).
- §5.2: an empty residue counts as in the training inventory whether or not training produced one (implementation corrected; amendment 10).
- §6 D2 as built, §9 G2 band and §10 bandwidths: `DECISIONS.md` amendment 10.

## Decisions log rows that amend this protocol

Verbatim from `DECISIONS.md` (Tom di Mino). Its first three rows concern the stage 1–3 protocol and are not repeated.

| date | decision | applied where |
|---|---|---|
| 2026-09-08 | H1 is Central Semitic (Tinitic, an archaic branch sister to NWS and Arabic), not NWS; NWS is the conservative floor. For option B: (1) state H1 as Central Semitic and rename the hypothesis arm; (2) comparanda witnesses = Ugaritic, Amorite, Proto-Semitic roots (already in) plus Arabic roots and Ancient North Arabian / Sabaic where snapshotted (ANE skill: 1,651 Quran roots, 74 OCIANA inscriptions; Sabaic lexicon not yet acquired); (3) H1 positive controls add Safaitic/Hismaic invocations (OCIANA) beside KTU and Psalms; (4) `data/innovations.json` re-priced: a morpheme attested in ≥ 2 Central Semitic branches (energic -n, tG stem, archaic -t- suffixes) is a retention at 0, not an innovation at 0.40; ordering claims (energic after object) stay priced. The failed stage-3 gate is unaffected: its failure is the instrument's, on texts of known language | B pre-registration (not started); PROTOCOL §2 wording at the B freeze |
| 2026-09-08 | Option B pre-registration approved (`PROTOCOL-B.md`); Tom delegated its §13 choices to the recommended settings: (1) the archaic *-t- object suffix stays a priced innovation (0.40) in the `ext` inventory; (2) headline `cs` inventory = morphemes attested in Northwest Semitic or Arabic (Classical/Ancient North Arabian); Sabaic-only morphemes enter the with-Sabaic variant, reported alongside. Corrected before B1 from the draft's "free only if in ≥ 2 branches", which would have priced ordinary Ugaritic morphology (Š-causative) for lacking an Arabic cognate; a morpheme attested in any one Central Semitic language costs 0, only claims attested nowhere are priced (PROTOCOL-B §4.3). B1 build amendment (before any run): parity 1.5× holds on distinct realizations (cs 69 vs 59–62); the one-sign ratio is reported with a 2.0 cap because the gap (cs 55 vs Egyptian ~31) is the prefix conjugation, which the rivals lack (PROTOCOL-B §4.2); (3) the six pending family candidates stay outside the family and enter as the ablation; (4) go for phase B1 | PROTOCOL-B.md §4.3, §2, §11; build phases B1–B5, stop at B5 |
| pending | Six further non-administrative inscriptions carry a formula type outside the frozen 32 (PR Za 1, ZA Zb 3, PK Za 15, KH Zc 106, NE Za 1, PK Za 17). Listed as `pending` in `data/family_additions.json`; each becomes part of the family by setting its status to `approved` and rerunning `freeze_inputs.py --rebuild-family` + `freeze_protocol.py --refreeze` | data/family_additions.json |
| 2026-10-09 | B2 build amendment, logged before any B2 build or run (for Tom's review in the B2 report). PROTOCOL-B §7 sizes a window (6–12 forms) but does not define the units, slots or folds that §5 needs. Fixed as follows. (1) **Unit**: one inscription (OCIANA, Sabaic, ḥtp-dj-nswt sentences, Linear B tablets), or one clause/§ as numbered by the edition (KTU, KARATEPE, KUB 35.54, EA 24). (2) **Slot**: the lemma assigned by the edition or a cited dictionary (ACLT lemmata; ORAEC lemma ids; the DULAT column of the Copenhagen Ugaritic Corpus, reviewed files first, with a token whose parses disagree on the lemma dropped; OSHB lemmata for Hebrew; a cited Safaitic dictionary; DAMOS or Docs² for Linear B), never by the forms' surface similarity. (3) **Window**: a contiguous, non-overlapping run of units in edition order whose recurring-lemma tokens (a lemma with ≥ 2 distinct surface forms inside the window) number 6–12. Only those tokens enter. (4) **Pairs**: the §5.1 rule after rendering. Fewer than 4 scorable pairs drops the window, logged. More than 12 drops trailing units until ≤ 12. (5) **Folds**: leave-one-unit-out, the analogue of the family's leave-one-site-out. A class with no edition lemmatization is not lemmatized by hand from its forms: Hurrian (TLHdig KBo 32 and Knudtzon 1902's EA 24 carry none) is reported as short under Tom's 2026-10-09 rule for the Hurrian class. The A1 acquisition lane's twelve Luwian windows (12 forms with 2 recurring lemmas each, so 2 pairs) fail (4) as cut and are re-cut under (3). | PROTOCOL-B §5.1, §7 at the B freeze; `controls/controls_b.jsonl` |
| 2026-10-09 | B2 build amendment, continued: corpus scope as built, before any B run. (6) KARATEPE 1 enters with the Hu. witness only (Ho. duplicates every clause). Hebrew H1 is OSHB Psalms (lemmatized), in place of stage 3's unlemmatized Sefaria windows. H3 is the Copenhagen corpus's KTU 2.x and 3.x prose. NEG is extended to every DAMOS-verified PY and KN tablet, under §7's "extended … to reach the pair count". A source contributes at most 24 windows, in edition order. Rendering conventions are stage 3's, unchanged: the Ugaritic /a/ filler with `NWS_OVERRIDES`, the Egyptian /e/ filler, and direct Linear B sign mapping. Not built: Amorite H3 (no lemmatization that groups case variants) and Safaitic H1 (no reachable open dictionary: Al-Jallad & Jaworska 2019 is embargoed, and Al-Jallad 2022's OAPEN copy is bot-walled). | `scripts/build_windows_b.py`; `B2-REPORT.md` |
| 2026-10-09 | B2 build amendment (7), Tom's choice for the NEG shortfall, before any B run. A repeated identical form (same lemma, same rendering) counts once per unit, in every class, matching the family, where each inscription carries one token per slot. Repeats in different units still count. All classes were rebuilt. NEG rose from 5 to 9 windows, still below 12. | `scripts/build_windows_b.py` (`once_per_unit`); `B2-REPORT.md` |
| 2026-10-09 | B2 build amendment (8), Tom's direction ("we have the full Linear B corpus"), before any B run. The NEG loader now reads every DAMOS-verified PY and KN tablet, as amendment (6) states; it had read only the 1,599 tablets with per-token DMic glosses. Lemma = DMic by attested form: the per-token gloss, or DMic's article for that form, with the same "V. en X" / "(+ -qe)" handling. A form with two lemmas is dropped, as is a bracketed headword. Where DMic has an article for a glossed form, it gives the same lemma as the per-token gloss in 3,913 of 3,917 tokens (the 4 are one bracketed OCR headword). NEG rose from 9 to 17 windows (13 in the length band). The other classes are unchanged (111 windows byte-identical). The B2 gate passes. | `scripts/build_windows_b.py` (`lb_form_lemmas`, `linear_b_tokens`); `B2-REPORT.md` |
| 2026-10-09 | B3 amendment (9), Tom's choice, before any run on the family or controls. A training form identical to the held-out form (same CV keys, so *301 = NA counts as identical) is not in its prediction set (§5.1). Under the text as drafted, 34 of the family's 57 scorable held-out slot tokens (leave-one-site-out; the 56 first stated read only the first of KO Za 1's three slot-2 forms) had an identical form at another site and were predicted by every arm and by null D, which keeps recurrence; A then measured recurrence. A token whose only match is identical is unscorable. Applies to the family, the controls and every null alike. | `scripts/common/paradigm.py` (`prediction_set`, `score`); PROTOCOL-B §5.1 at the B freeze |
| 2026-10-09 | B3 build amendment (10), spec as built, before any run on the family or controls. (1) **Empty residue:** `FreeInventory.explains` counted an empty prefix as in only if training had produced one; corrected to §5.2's "empty residue always counts as in" (selftest written failing first). (2) **Family tokens:** one token per form listed in a slot (61; KO Za 1 slot 2 lists three); fold group = site, 10 folds. (3) **A** = mean of per-fold rates over folds with ≥ 1 scorable token; a control window with no scorable token has no Δ and is counted, not scored. (4) **Arm charge:** the cheapest explaining pair. (5) **D2** read as "as D": one bigram form per word type, recurrence and positions kept; each occurrence of a recurring type is varied at D's observed rate (0.833) by type form + one inventory prefix and/or suffix. k = 8 prefix and k′ = 32 suffix residues = the distinct non-empty residues over every scorable distinct-form pair of the whole family (a boundary sign belongs to the suffix residue); lengths drawn from those residues; prefix-only / suffix-only / both drawn with the observed shares of varied sides (0.13 / 0.55 / 0.32). A fresh inventory per replicate. (6) **Gate:** G2's H1-median band for a Linear B window is the H1 windows within 0.5 signs of that window's mean. (7) **Posterior:** KDE bandwidth ×0.5, ×1.0, ×1.5 (§10's ±50%); H4's weight folded into H_ISO; Hurrian has no control windows and drops from the alternatives, which `stats.bayes_factor` renormalizes. (8) **Ablations:** `cons` applies to the arms; the free inventory compares residues exactly in every configuration; in `ext` the rivals stay base. | `scripts/common/paradigm.py`, `scripts/common/nulls.py` (`draw_affix_inventory`, `null_d2`), `scripts/run_paradigm.py`; `B3-REPORT.md` |

## Freeze record (option B)

- frozen by: `freeze_protocol.py --refreeze "option B freeze"` (record in PROTOCOL.md)
- SHA256SUMS: f5d6733fbf922c951b5e690725cdedf6fda4bf52747c59e284807efc351cd7ca
- scripts/run_paradigm.py: a53de76f5f796f043bb1453f3257c67f74445a595850cc2dee209ec9beabd941
- scripts/selftest_b.py: bb286bae44156692b5cad32c376a43431188451f7ec07266d73aecd3cc4113c2
- scripts/build_windows_b.py: 266318fccb490ed96d2516cc6674c86a8a3839f481bba891fc806b03536afbe4
- scripts/build_paradigm.py: ede9e39503272d4f95128f7a45e7e3264d0ca9c83db9edbeab17721f719bf7b6
