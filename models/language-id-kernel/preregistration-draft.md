---
title: "Language identification by forward spelling: a test of what language Linear A's sign sequences fit"
status: "DRAFT, unsigned. Controls on the development split only. No Linear A word is read or scored."
date: 2026-11-22
author: di Mino
replaces: every test archived in artifacts/probabilistic-model-exchange-2026-11-21/RESULTS-LEDGER.md (archive note of 2026-11-22)
---

# Language identification by forward spelling

## 1. Question

Do the sign sequences of Linear A's words fit a Semitic language better than they fit Greek, Anatolian, Hurrian
and Hattic, by more than any text known not to be Semitic does?

## 2. Why this design

Every archived test worked backward: from a Linear A word to the nearest root in a dictionary. About 90% of any
consonant sequence finds a Semitic root, so those tests had to narrow to a few dozen words to recover power, and
none found a known language at Linear A's size.

This test works forward. Known languages are spelled into the syllabary by fixed rules, a model of sign
sequences is trained on each, and a text is scored under every model. Each arm gets the same treatment, so a
high chance rate cancels: only the difference between arms counts. Every legible word is used.

The requirement comes from di Mino (2026-11-22): a protocol that detects Hebrew as Hebrew and Greek as Greek.
§7 makes that the gate.

## 3. Units and spelling

- **Word:** a tuple of sign keys, (consonant series, vowel), of two signs or more. The keys and the sign table
  are Protocol C's `render/series.json`, `series-a5-proposed.json` and `signs-a5-proposed.json`, read in place and
  unchanged. Linear B's values are the only values used.
- **Left out and counted, in training and in test alike:** a word with a damage mark, a logogram, a sign with no
  secure Linear B value, a segment the tables do not map, or a key no sign writes (ji, wu, zi and the like).
- **Spelling a known language:** Protocol C's renderer (`c_render.word`), under both of its conventions:
  Linear B's omission rules, and plene spelling with echo vowels. Linear B tablets are taken as written. LSJ's
  lemmas are taken in the Linear B spelling the skill already holds (`lb_key`), one convention.
- **The glide rule** (added on the development part, `PILOT-2026-11-22.md`): in every rule-spelled source a vowel
  sign after i is written with j, and after u with w, where such a sign exists. It is a rule of the script and
  names no language.
- **Document:** the unit of every split and every resample. Hebrew: a chapter. Arabic: a sura. Cuneiform texts
  and Linear B: the tablet.

## 4. Arms and sources

| Arm | Members | Training source | Test text |
|---|---|---|---|
| Semitic | Hebrew, Akkadian, Arabic | OSHB, pointed; TLHdig 0.3 bound transcription (Akk); the Quran, Uthmani text, vocalised | the same sources, other documents |
| Anatolian | Hittite, Luwian | TLHdig 0.3 bound transcription | the same, other documents |
| Greek | Greek | LSJ's lemmas in Linear B spelling (117,107) | Linear B tablets, Pylos and Knossos, clean and DAMOS-verified |
| Hurrian | Hurrian | TLHdig 0.3 | the same, other documents |
| Hattic | Hattic | TLHdig 0.3 | the same, other documents |

**The arms after the second development round** (`PILOT-2026-11-22.md`), which replace the table above:

| Arm | Members | Training source |
|---|---|---|
| Semitic | Hebrew, Akkadian, Arabic, Aramaic, Geʿez, Ugaritic | OSHB (Hebrew and Biblical Aramaic, by its morphology mark); ORACC's normalised Old and Standard Babylonian; the Quran; TraCES; EUPT, KTU 1.14 to 1.16 |
| Anatolian | Hittite, Luwian | TLHdig 0.3 |
| Greek | Greek | LSJ's lemmas in Linear B spelling; tested on Linear B tablets |
| Hurrian | Hurrian, Urartian | TLHdig 0.3; ORACC eCUT |
| Hattic | Hattic | TLHdig 0.3 |
| Latin | Latin | LiLa's LatInfLexi paradigm forms, the lexeme as the document |

- Ugaritic is a member of the Semitic arm, on di Mino's word (2026-11-22). Its share is small: 281 training
  types are held.
- Aramaic and Geʿez are in the arm so that the prefixed tG stem is in its training.
- A family that holds fewer than 800 training types is no arm (Sumerian, 295). Its text is scored as a text of a
  language outside every arm.
- The Akkadian of Boğazköy (TLHdig) trains nothing and is a test text.
- A family arm is trained on equal shares of its members; a member that holds less than its share gives all it
  has and the others make up the difference.
- **Ugaritic** (EUPT, KTU 1.14 to 1.16, vocalised; about 1,200 words) is never in training. It is a test text
  only, one corpus, reported beside the gate and counted in no share.
- **Egyptian** is no arm in the primary run. Its texts write no vowels, and a filler vowel would decide every
  comparison. A second run on consonant series alone, with Egyptian in it, is reported beside the primary and
  gates nothing.
- The Greek arm is trained on a dictionary's citation forms spelled by rule, and tested on real tablets. That is
  the hardest condition in the table, and the one nearest to Linear A's: the spelling rules meet real scribal
  practice, and the tablets are mostly lists with many names that are not Greek.

## 5. The split

Each document goes to one of three parts by the first eight hex digits of `sha256(document id)`, read as a
number, mod 4: 0 is the gate part, 1 the development part, 2 and 3 the training part. The parts separate
documents, not word types: a word of a test document may also stand in a training document of its own language
(25% to 63% of development types do). The own condition is therefore a test with a shared vocabulary; the sister
and absent conditions, where the text's own language is in no training set, are the ones that stand for Linear A. Development work reads the training and development parts only. The code
refuses the gate part until a signature file stands beside this document. LSJ is training material only and is
not split.

## 6. Model and statistic

- **Model:** for each arm, an interpolated n-gram model (Witten-Bell) over sign keys within the word, with a
  word-end symbol, backing off to a uniform distribution over the 59 sign keys and the end symbol.
- **Parity:** every arm is trained on the same number T of distinct word types, drawn by seed from its training
  part. T is 1,000 if every arm of §4 holds that many, otherwise the largest multiple of 100 the smallest of
  them holds (800 on the development part, set by Hattic). A family arm without one member, as in the sister
  condition, draws up to T from what its other members hold. Training is repeated over R seeded draws and the
  scores are averaged.
- **Fit:** H(arm, text) = the bits the arm's model needs for the text's distinct word types, divided by their
  signs with each word's end counted as one sign. Where an arm is trained under two conventions, its fit is the
  better of the two; the Greek arm has one convention, which costs it up to 0.08 bits against its best rival.
- **Samples:** a pseudo-corpus cut after its text has run out and begun again is no new sample and is left out.
- **Statistic:** M(arm, text) = the best rival's H minus the arm's H. Positive means the arm fits best.
- **Order:** n is 2 or 3. It is chosen once, on the development part, as the order with the higher power in
  §7's sense, 2 on a tie, and is written here before signature.

## 7. The gate, on texts of known language at Linear A's size

Each test language's gate part is cut into K = 20 pseudo-corpora of Linear A's shape (Protocol C's `c_pseudo.cut`:
Linear A's own document sizes, filled until the corpus holds as many distinct word types as Linear A's pool
does under §3). A language too small for 20 corpora without overlap gives what it has, and the count is
reported.

Each corpus is scored under three conditions:

- **Own:** every arm as in §4.
- **Sister:** the text's own language removed from its family arm (Hebrew scored by a Semitic arm of Akkadian
  and Arabic; Luwian by an Anatolian arm of Hittite alone). This is the claimed language's condition: it has no
  texts of its own.
- **Absent:** the text's whole arm removed. This is the condition of an unknown language outside every arm.

**The threshold.** θ(Semitic) is the highest M(Semitic, text) reached by any corpus of a language that is not
Semitic, under the own and the absent conditions together. θ(Greek) is the same for the Greek arm.

**The gate passes when all of these hold, under each convention of the test text separately:**

| # | Criterion | Bar |
|---|---|---|
| G1 | Greek as Greek: Linear B corpora with M(Greek) above θ(Greek) | at least 0.70 |
| G2 | Hebrew as Hebrew: Hebrew corpora, own condition, with M(Semitic) above θ(Semitic) | at least 0.70 |
| G3 | A Semitic language without itself: Hebrew corpora, and Arabic corpora, sister condition, with M(Semitic) above θ(Semitic) | at least 0.70 each |
| G4 | No wrong language: by the definition of θ, no corpus that is not Semitic passes | 0 |

Akkadian under the sister condition (an East Semitic text scored by Central Semitic training) and the Ugaritic
corpus are reported and gate nothing. The bars are proposals until signed.

**State after the second development round (`PILOT-2026-11-22.md`):** with six arms, every language goes to its
own arm, and the threshold stands at 0.42 to 0.46, set by Latin with its arm removed. Hebrew, Arabic, Geʿez,
Aramaic and Ugaritic pass G3 through their sisters; Akkadian does not. G1 passes under plene and not under
omission. The margins over the threshold are thin for Arabic and Ugaritic, and the threshold was read off the
same texts. The criteria of this section are to be restated for six Semitic members before signature.

### 7a. The criteria restated for the arms as they now stand (third development round)

These replace the table G1 to G4 above. The arms are Semitic (Hebrew, Akkadian, Arabic, Aramaic, Syriac, Geʿez,
Ugaritic), Anatolian (Hittite, Luwian), Greek (LSJ and Diodorus; tested on the tablets), Hurrian (Hurrian,
Urartian), Hattic and Latin. Sumerian and the Akkadian of Boğazköy are test texts that train nothing.

θ(Semitic) is the highest M(Semitic) reached by any sample of a text that is not Semitic, with its own arm
present or removed. θ(Greek) likewise. A language gates only where its gate part gives five samples or more
without overlap; a language with fewer is reported beside the gate.

| # | Criterion | Bar |
|---|---|---|
| G1 | Greek as Greek, on real tablets: samples with M(Greek) above θ(Greek) | at least 0.70 |
| G2 | Each language to its own arm: for every test language, samples in which its own arm fits best | at least 0.70 |
| G3 | Central Semitic through its sisters: Hebrew, Arabic and Syriac, each scored by a Semitic arm without it; samples with M(Semitic) above θ(Semitic) | at least 0.70 each |
| G4 | No wrong language: by the definition of θ, no sample that is not Semitic passes | 0 |

- G3 gates on the three Central Semitic languages with text enough for five samples, since the claim places the
  language in Central Semitic. Aramaic and Ugaritic (too little text for five samples), Geʿez and Akkadian are
  reported under the same condition and gate nothing.
- Each criterion must hold under omission and under plene. Consani (2021, 52) finds that Linear A writes
  syllable-final consonants where Linear B drops them, so plene is the convention nearer to Linear A; the run on
  Linear A reports both.
- **On the development part, as the draft stands, G3 fails for Arabic:** 4 of 10 samples under omission and 5 of
  10 under plene clear θ (0.50 and 0.53), which one Latin sample of ten sets; the next highest outside sample
  stands at 0.42. With θ at the 95th percentile of the outside samples (0.42 and 0.43) Arabic clears it in 10 of
  10 and Ugaritic in its one sample. Which rule stands is di Mino's ruling before signature; the draft keeps the
  stricter one until he rules.

A gate that fails is reported as failed, and the test is not run on Linear A. One repair is allowed, by a rule
that names no language, developed on the development part and gated once on fresh seeds. A second failure
retires the test.

## 8. The run on Linear A, after a passed gate and a signature

- The pool: every legible word of §3 in the corpus, by Protocol C's damage rule, with its document.
- One run, skills read in place, every input hashed at the start and the end; a changed hash writes no result.
- Reported: H for every arm in one table; M(Semitic) with a 95% interval by resampling documents (seed recorded);
  θ(Semitic) and the power measured at the gate.

| Outcome | Reading |
|---|---|
| M(Semitic) above θ(Semitic), interval and all | Linear A's sign sequences fit Semitic better than every rival arm, by more than any text known not to be Semitic did |
| M(Semitic) positive, not above θ | Semitic fits best among the arms; texts of other languages have done as well, so membership is not shown |
| Another arm fits best | That arm is named, with its margin and its own threshold |

## 9. What this does not show

- It shows resemblance of word shape: sign sequences, endings, vowel patterns. It does not show regular
  correspondences, and it reads no word.
- The threshold rests on five languages that are not Semitic. A language unlike all of them is outside it.
- Linear A's lists are mostly names. G1 measures what that costs on Linear B's tablets, which hold many names
  that are not Greek.
- The Hebrew points are Tiberian and late; the claimed language is archaic. The sister condition is the measure
  of that distance.
- The Greek arm sees citation forms only. Inflected Greek is held (Diodorus 1 to 5, 121,555 words) and is not
  yet read into the arm.
- It rests on Linear B's sign values.
- The renderer was written for affixes. On whole words it joins a few adjacent consonants into one (t and s into
  the z series, k and w into the q series: 229 Hebrew word types, 64 Arabic), and it drops every guttural, as its
  table says: that touches 58% of Hebrew and 57% of Arabic word types.
- Equal training size is equal in word types, not in signs: an arm's training set holds from 3,700 to 4,900
  signs.

## 10. Files

- `lid.py`: readers with document ids, the split, the model, the statistic. `test_lid.py`: its tests.
- `pilot.py`: the development-part pilot. Each run writes a new file under `runs/`, with the seed, the commits of
  both skills and the hashes of every input before and after.
- Reused in place, never edited: `ioza2-adjudication/protocol-c/scripts/c_render.py`, `c_align.py`, `c_texts.py`,
  `c_pseudo.py`; `ioza2-adjudication/protocol-d/scripts/pointed.py`.

## 11. Method lineage

Builds on n-gram language identification, a standard method (no source for it is held locally, so none is
cited), and on the known-answer rule of `CASE-AND-MODEL.md` §4.2. Departs from Ringe 1992 and Kessler 2001, which test word lists against a lexicon:
here no lexicon is searched.

## 12. Signature

Unsigned.
