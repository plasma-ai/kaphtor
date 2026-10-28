---
name: data/linear-a/protocol-c/builds/hurrian/protocol
title: "Protocol C: the rules this inventory is built under (extract)"
desc: "The protocol extract in the hurrian kit: §5.2–5.3 and amendments A1–A2, cut from the protocol by run_builder.sh."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C: the rules this inventory is built under (extract)

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
