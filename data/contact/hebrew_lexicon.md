---
name: data/contact/hebrew_lexicon
title: Hebrew lexicon
desc: The lexemes of STEPBible's TBESH, Hebrew with its Biblical Aramaic, with Brown–Driver–Briggs's glosses and the cognates it names.
tags: [data, contact, hebrew]
license: CC BY 4.0
created: 2026-10-25T22:00:00Z
updated: 2026-10-26T04:00:00Z
---

`hebrew_lexicon.jsonl` holds 8,763 entries, one per extended Strong's number of STEPBible's Translators Brief lexicon
of Extended Strongs for Hebrew (TBESH): the first row of each number, with TBESH's "Aramaic of" and "Part of" rows
left out. 1,126 ids carry a letter (H0899a, H0899b), where TBESH splits one Strong's number into several words. 8,312
entries are joined to the Brown–Driver–Briggs entry for the same Strong's number. Besides Hebrew words, the file
holds 128 entries TBESH marks as Aramaic, 11 prefixes and suffixes, 30 pronominal suffixes and 6 punctuation marks.

| Field | Content |
| --- | --- |
| `id` | `heb:tbesh:` and the extended Strong's number |
| `language`, `language_family` | `Hebrew`, `Northwest Semitic`, the Aramaic entries (morph code `A:`) included |
| `form_original`, `vocalization` | the pointed headword, and TBESH's transliteration lowercased, without its dots and spaces, between slashes |
| `normalized`, `match_keys` | the consonantal form and the keys the root index matches on |
| `meaning` | BDB's gloss (6,632 entries): the words after the grammatical labels at the head of the entry ("father"; "way, road, distance, journey, manner"; "interpret, translate" after "verb quadriliteral"; "ninety" after "noun indeclinable"), or for a name its description ("in Judah", "a Levite"). Where a BDB number holds several homonyms (I., II.), the one whose gloss shares a word with TBESH's brief gloss is taken. Empty on 2,131: 451 with no BDB entry, and 1,680 where the head gives no gloss (BDB glosses אֱלֹהִים only in its senses), gives only a label, a cross-reference or shorthand, or where no homonym of a lettered number matches (471). A sample of 50 glosses was all correct; expect a few per cent of fragments |
| `pos` | read from TBESH's morph code: a compound code by its first part, a pronominal suffix as `pronoun`, a prefix or suffix as `particle`; `unknown` on the 6 punctuation marks |
| `semantic_domain` | read from the morph code: `nominal_root`, `verbal_root`, `adjective`, a name type (`personal_name`, `toponym`, `ethnonym`, `title`), `grammatical_morpheme` or `general` |
| `root` | on 1,194 verbs: the first three consonants left once ʾ and ʿ are dropped. Not a lexicographer's root: a verb with a guttural radical can come out wrong or with none, and no noun has one |
| `cognates` | from the head of the BDB entry, the homonym's own: a language and the form BDB gives, in Hebrew script or, for Assyrian, in transliteration ("Phoenician אב", "Assyrian abu"); at most five per entry; 2,028 on 1,438 entries. The digitization drops Arabic, Syriac and Ethiopic script, so those cognates are mostly missing, and a few Targum forms after a dropped Arabic or Syriac word carry that language's label |
| `source_refs`, `review_status` | the sources of the row, `TBESH (STEPBible)` and, on the 8,312 joined entries, `BDB (Eliran Wong, unabridged)`; every row is `machine_imported` |

**Sources.** TBESH, STEPBible Data, Tyndale House, Cambridge (CC BY 4.0). Brown, Driver and Briggs, *A Hebrew and
English Lexicon of the Old Testament* (1906), public domain, in Eliran Wong's unabridged digitization.

**Not included.** TBESH's own meanings are Online Bible's Abridged BDB (© Larry Pierce), which TBESH says need
Online Bible's permission before use in a project; the glosses here are BDB's, and TBESH's brief gloss only chooses
among BDB's homonyms. The private build also joins each row to the BHSA lexicon of the ETCBC (frequency, stems,
gender, gloss and root); the BHSA is under CC BY-NC 4.0, so this file is built without it, and a noun has no root.
