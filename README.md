<h1 align="center">
  <img src="assets/banner.png" width="100%"
       alt="kaphtor: an open record of Linear A, and a toolkit for comparative Semitics. Four Linear A tablets glow on a black ground beside the libation formula in Linear A script.">
</h1>

<p align="center">
  <a href="wiki/linear-a/inscriptions/_index.md"><img alt="corpus: 1,719 records" src="https://img.shields.io/badge/corpus-1,719%20records-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <a href="wiki/linear-a/inscriptions/_index.md"><img alt="translations: 531" src="https://img.shields.io/badge/translations-531-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <a href="wiki/linear-a/words/_index.md"><img alt="lexicon: 736 entries" src="https://img.shields.io/badge/lexicon-736%20entries-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <a href="wiki/linear-a/words/_index.md"><img alt="names: 382" src="https://img.shields.io/badge/names-382-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <a href="wiki/semitic-roots/_index.md"><img alt="Semitic roots: 5,189" src="https://img.shields.io/badge/Semitic%20roots-5,189-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <a href="wiki/linear-a/signs/_index.md"><img alt="sign values: 42" src="https://img.shields.io/badge/sign%20values-42-e8d9bd?style=flat-square&labelColor=0b0a08"></a>
  <br>
  <a href="https://github.com/plasma-ai/kaphtor/actions/workflows/gate.yml"><img alt="gate" src="https://github.com/plasma-ai/kaphtor/actions/workflows/gate.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="code: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-3a3229?style=flat-square&labelColor=0b0a08"></a>
  <a href="LICENSE-CC-BY-4.0"><img alt="data: CC BY 4.0" src="https://img.shields.io/badge/data-CC%20BY%204.0-3a3229?style=flat-square&labelColor=0b0a08"></a>
  <a href="https://doi.org/10.5281/zenodo.24375016"><img alt="DOI: 10.5281/zenodo.24375016" src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.24375016-3a3229?style=flat-square&labelColor=0b0a08"></a>
</p>

**An open record of Linear A, and a toolkit for comparative Semitics.** The name is Caphtor (כַּפְתּוֹר), the Hebrew
Bible's name for Crete.

kaphtor holds a reconciled record of the Linear A inscriptions, proposed readings for their words and signs, and tools
for testing those readings against the corpus. Beside it sit a database of Semitic roots and query tools for the
corpora of the ancient Near East.

Browse an inscription, trace a proposed reading to its evidence, or run the comparative tools on your own questions.
The datasets and tools work independently of the proposed decipherment.

**Explore it live at [linear-a.ai](https://linear-a.ai/):** the Linear A Lexicon, an interactive dictionary of Minoan
built from this repository, where every word, name and Semitic root opens with its cognates, citations, and commentary.
Design by [Maxim Kuznetsov](https://github.com/mkuznetsov_plasma) and
[Vittorio Retrivi](https://github.com/vretrivi_plasma).

The case for the readings is set out in [Opening Linear A](https://plasma.ai/research/linear-a) and in
[*Ya Diktu*](https://www.minoanmystery.org/linear-a/ya-diktu-grammar-tom-di-mino.pdf), the grammar of the peak
sanctuary libation formula.

> I opened this record so that anyone can test the decipherment, inscription by inscription and root by root. Every
> reading stands beside its evidence, its tier and its rivals.
>
> —Tom di Mino

## Start here: the libation formula

The fullest copy of the peak sanctuary prayer runs in two lines around the four faces of a stone libation table from
Mount Iouktas, IO Za 2. Brackets mark the signs GORILA restores from the parallel copies.

> A-TA-I-\*301-WA-JA · JA-DI-KI-TU · JA-SA-SA-RA-\[ME\] · \[U-NA-KA-NA\]-SI · I-PI-NA-MA · SI-RU-TE ·
> TA-NA-RA-TE-U-TI-NU · I-DA-\[?\]
>
> *I make myself a dwelling—O Diqqitu!—in righteousness. So, behold my gathering in the presence of sacred song. May
> you be favorable toward us.*

[Read it word by word](wiki/linear-a/inscriptions/IO/IOZa/IOZa2.md): each word links to its reading, its tier and
every inscription where it recurs.

## Getting started

- **Read an inscription:** [IO Za 2](wiki/linear-a/inscriptions/IO/IOZa/IOZa2.md), or browse
  [all inscriptions](wiki/linear-a/inscriptions/_index.md) by site and GORILA series.
- **Look up a word:** [KU-RO, "total"](wiki/linear-a/words/K/KU_RO.md), or browse [all words](wiki/linear-a/words/_index.md)
  by first sign. The forms that open with an unvalued sign are under `star/`.
- **Look up a Semitic root:** [\*kanVs- "to gather, assemble"](wiki/semitic-roots/k/2763_to_gather_assemble.md), or
  browse [all roots](wiki/semitic-roots/_index.md) by first radical.
- **Learn how the corpus is organized:** [docs/anatomy.md](docs/anatomy.md).
- **Run a query:** [Run your first query](#run-your-first-query).
- **Contribute a reading, a rival analysis, a source or a correction:** [CONTRIBUTING.md](CONTRIBUTING.md).

## What's inside

| Part | What it holds | Browse |
|---|---|---|
| Inscriptions | One page per corpus record, with its transliteration, its Unicode text, its translation and a table linking each word | [inscriptions](wiki/linear-a/inscriptions/_index.md) |
| Words | One page per form, joining the lexicon, the onomasticon, the unread words and the unread signs, with every inscription where the form appears | [words](wiki/linear-a/words/_index.md) |
| Signs | The syllabic signs, logograms and fractions, each with its value and the evidence for it | [signs](wiki/linear-a/signs/_index.md) |
| Reading status | Every reading with its tier and score | `wiki/linear-a/standing.md` |
| Signs left to read | The single and combined signs with no lexicon entry, by the untranslated inscriptions each one alone leaves unread | `wiki/linear-a/unread_signs.md` |
| Scribes | Every scribe to whom an edition assigns documents, with the records each wrote and the source of the attribution | `wiki/linear-a/by_scribe.md` |
| Names | Every name on the tablets (people, places, gods, titles, peoples), filed by the language it is read through, with the roots the names are built from and a guide across the layers | [names](wiki/names/_index.md) |
| Semitic roots | One page per root, with its reconstruction and its reflexes across the Semitic languages, each with its sources | [roots](wiki/semitic-roots/_index.md) |
| Pre-Greek words | One page per Greek word classed as Pre-Greek or as an early Semitic loan, with the works that treat it, its Pre-Greek features and the Semitic comparisons proposed for it | [Pre-Greek](wiki/pre-greek/_index.md) |
| Aegean scripts | The Eteocretan inscriptions and the analysis of their words, and one catalogue page per Cypro-Minoan text with its site, object type, date, script, edition of record and sources, and a translated text's reading word by word | [Aegean](wiki/aegean/_index.md) |
| Corpus guides | What each ancient Near East corpus holds, its licence and its gaps, and how to query it | [guides](docs/corpora/_index.md) |

The pages are built from the [data](data/_index.md), where each dataset has a datasheet or manifest naming its
licence. [Repository guidance](docs/_index.md) covers how to read, contribute to and verify the record.

## Run your first query

The query tools need Python 3.11 or later and nothing else. The datasets are stored with Git LFS, so install
[Git LFS](https://git-lfs.com/) before cloning:

```sh
git lfs install
git clone https://github.com/plasma-ai/kaphtor.git
cd kaphtor
python3 tools/ane/query_place_authorities.py Knossos --authority pleiades --limit 3
```

This searches the Pleiades gazetteer in `data/ane/place-authorities/` and prints one place per line: the authority,
the place's id, its name and its Pleiades URL.

```
pleiades	238779098	Minoan Palatial Center (Knossos)	https://pleiades.stoa.org/places/238779098
pleiades	589872	Knosos/Col. Iulia Nobilis Cnosos	https://pleiades.stoa.org/places/589872
pleiades	229296321	Neolithic Settlement at Knossos	https://pleiades.stoa.org/places/229296321
```

Leave out `--authority` to search every local authority (Pleiades and Trismegistos; iDAI, which does not ship, is
named on stderr), and add `--json` for the full records.
iDAI.gazetteer publishes no licence for its data, so it is queried live, one page at a time.
[tools/ane/README.md](tools/ane/README.md) lists the other query tools.

## How readings are graded

Every proposed reading carries a confidence tier, and moves up a tier only by passing that tier's test:

- **4, CONFIRMED:** passes all four corpus tests and is staked by the project's author, recorded on the reading's
  page as its reviewer. Where a scholar outside the project published the same reading first, most often Cyrus H.
  Gordon in *Evidence for the Minoan Language* (1966), the page also names that work and its sections.
- **3, PROBABLE:** passes the crossword and inscription tests, or shows complementary distribution between a full
  spelling and its abbreviation.
- **2, CANDIDATE:** attested in two or more independent contexts.
- **1, SPECULATIVE:** a proposal on record that has not yet met the CANDIDATE test.

No reading skips a tier. A rejected reading leaves the record for the archive, with the reason it was rejected.

> [!NOTE]
> These tiers describe support under this project's evaluation criteria. They do not imply scholarly consensus on the
> decipherment.

A sign value counts as resolved only on support that does not depend on a Semitic match: a Linear B value, a scribe's
arithmetic, or a spelling variant of the same word. Every other value is listed as proposed, with its evidence where
given. The record holds 42 sign values: 5 resolved (2 phonemic, 3 logograms) and 37 proposed (16 phonemic, 21
logograms). The fraction signs are counted apart: 3 resolved and 11 proposed.

Linear A has no deductive proof kernel, though [`models/language-id-kernel/`](#probabilistic-language-identification) provides a deterministic probabilistic language-identification suite. Counts, distributions, arithmetic and reproducibility are checked mechanically.
Segmentation, sound correspondence and meaning stay graded and open to revision. When the four rival-language files
(the Luwian, Egyptian, Hurrian and Hattic roots) are in the checkout, every Semitic match is rescored against them and,
where each rival gives a p-value, the margin is reported. Without them `root_match.py` stops and names the first
missing file, and under `--no-competitors` no word can reach `CONVERGENT`. [Confidence](docs/confidence.md) gives
the tiers and the rule for a resolved sign value.

## Using the skills

The two skills in `skills/`, Linear A research and ancient Near East research, run the research from an agent session
in Claude Code or Codex. [skills/README.md](skills/README.md) describes what each skill does and the commands it runs.

In Claude Code, add this repository as a plugin marketplace, then install the plugin:

```
/plugin marketplace add plasma-ai/kaphtor
/plugin install kaphtor@plasma
```

The skills load when a request fits them. To call one by name, prefix it with the plugin:

```
/kaphtor:linear-a-decipherment Read IO Za 2 and list the rival readings of each word.
```

In Codex, link the two skill folders into `~/.agents/skills/` from your clone:

```sh
mkdir -p ~/.agents/skills
ln -s "$PWD/skills/linear-a-decipherment" "$PWD/skills/ancient-near-east-research" ~/.agents/skills/
```

Then mention a skill with `$`:

```
$linear-a-decipherment Read IO Za 2 and list the rival readings of each word.
```

## Development

<details>
<summary>Set up the environment, run the gate, and find your way around the repository.</summary>

The tooling requires [uv](https://docs.astral.sh/uv/) and Python 3.11 or later. All PDFs, every `.jsonl` data file
and the JSON data files over 1 MB are stored with Git LFS (the rules are in `.gitattributes`): in a clone made
before Git LFS was installed, run `git lfs install`, then `git lfs pull`.

From the repository root, set up the environment and the pre-commit hooks, then run the repository gate:

```sh
uv sync --all-groups
uv run --no-sync pre-commit install
uv run --no-sync kaphtor gate
```

The gate runs the tests, the pre-commit hooks, the index and licence checks, and the structure checks, and rebuilds
the generated pages, failing if they differ from what is committed. It only checks and changes no tracked file: it
runs the hooks' manual stage, where the whitespace fixers and `ruff --fix` that run at commit are replaced by checks.
GitHub Actions runs the same gate on every push and pull request.

The `ane` tools read local corpora. A corpus that cannot be redistributed is not in the repository, and its tool says
so and names the path it looked for; its corpus guide says where the corpus comes from. Set `KAPHTOR_DATA` to read
the data from another folder.

[AGENTS.md](AGENTS.md) gives the full check sequence and the conventions for agents.

## Probabilistic Language Identification

Using strict Linear B sign values alone, zero LLMs, and zero project-lexicon inputs, the ten-kernel suite
(`models/language-id-kernel/`) establishes consonant-specific phonetic matches to Semitic across independent
pre-linguistic channels: standalone arithmetic/vessel/grain anchors at a **~794,000 : 1 Bayes Factor** (`ΔLL = +13.58`,
`Z_perm = +7.37`, `p = 0.00010`, 0/10,000 consonant-grid permutations—holding across all eight leave-one-out
ablations, after dropping the three trade-loan suspects at `~1,860 : 1`, and on pure arithmetic `KU-RO`/`KI-RO` alone
at `p = 0.00640`), commodity ligature acrophony (`Z_perm = +5.53`, `p = 0.00010`), Palaikastro dialectal sound-law
coherence (`5/5` minimal pairs, `p = 0.00010`), and an automated size-locked (`K = 300`) Biblical Hebrew liturgical
match on `IO Za 2` (`Z = +2.91` to `+3.05`, `p = 0.027`–`0.032`). The same anchor and ligature instruments first
identify Linear B as Greek (`Z = +7.97` and `+4.31`) and reject Semitic (`p = 0.11` and `0.36`). Corpus-wide
word-shape, unsupervised Kober-trio, and votive verbal-frame models likewise rank Semitic first (joint primary
Stouffer `Z = +3.504`, `p = 0.00023`).

The repository ships two complementary, zero-LLM, deterministic frameworks:

- **`models/language-id-kernel/`** ([index](models/language-id-kernel/_index.md),
  [reference](models/language-id-kernel/reference.md),
  [replication guide](models/language-id-kernel/replication-guide.md)): self-contained ten-kernel suite (`Kernels A–J`)
  under strict Linear B sign values with consonant-grid and concept-label permutation nulls and known-language
  calibration gates:
  - **A (Word-Shape LID)** & **B (Unsupervised Kober Trios):** rank Semitic first across 505 undamaged Linear A types
    (`M = +0.623` bits/sign; `M = +2.288` bits/transition), capturing `/a, i, u/` vowel-core typology.
  - **C (Liturgical Cohesion):** size-locked (`K = 300`) Dirichlet log-odds Psalms/Leviticus vocabulary on `IO Za 2`
    (`Z = +2.91`–`+3.05`, `p = 0.027`–`0.032`).
  - **D (Pre-Linguistic Anchors):** 8 arithmetic/logogram anchors (`Z = +7.37`, `p = 0.00010`; Linear B gate: Greek
    `Z = +7.97`).
  - **E (Verbal Edge-Frames):** Semitic verbs first on 46 votive `>=4`-sign words (`M = +1.056`, `Z = +0.85`; 5/5 dev
    calibration).
  - **F (Ligature Acrophony):** 10 `GRA/OLE/VIN` commodity ligatures (`Z = +5.53`, `p = 0.00010`; Linear B gate: Greek
    `Z = +4.31`).
  - **G (Dialect Coherence):** 5 Central Crete ↔ Palaikastro minimal pairs match a 4-rule NWS isogloss bundle
    (`p = 0.00010`).
  - **H (Roster Onomastics):** 57 structurally-gated `WORD 1` roster names match shared Knossos/Pylos Linear B first
    and Amorite Semitic second (`Z = +1.30`, ahead of Hurrian and Anatolian).
  - **I (Bound Affix Morphology):** unsupervised strict stem-containment affixes (`S` vs `p+S`/`S+s`) scored under a
    discriminative margin-permutation null ($B = 5{,}000$) that cancels universal suffix consonants; 7/7 dev pass;
    Linear B picks Greek (`M = +480.6`, `p_M = 0.048`, only pass; Semitic `0.919`) and Linear A picks Semitic
    (`M = +27.1`, `p_M = 0.0436`, `p_cv = 0.0192`, only pass; `p_pre = 0.419` vs Semitic `0.404`, Linear B `0.349` vs
    Greek `0.355`).
  - **J (Zero-Curation Dictionary Audit):** replaces hand-curated anchor synsets with automated regex extraction over
    independent open dictionaries (`cap = 40` and uncapped) under two orthogonal nulls—10,000 consonant-grid swaps and
    exact concept-label shuffling; calibrates Linear B as Greek (`p_perm = 0.00010`, `p_concept = 0.01250`; Semitic
    rejected at `0.231` / `0.693`) and identifies Linear A as Semitic on `FULL_8` (`Z_perm = +4.85`, `p_perm = 0.00010`;
    `Z_concept = +2.51`, `p_concept = 0.00893` over all 5,040 concept assignments—the only language passing both nulls,
    with Greek at `p_concept = 0.548`).
- **Shoresh (`tools/core/root_match.py`, `shoresh_cv.py`, `shoresh_kernel_bridge.py`):** the per-word root matcher
  used by the skill, upgraded with fast O(1) exact-match retrieval, vocalized CV distance and Bayesian marginal
  log-likelihood (`ΔLL`, Amendment A24), and Kober-cluster / Kernel C–D domain tagging (Amendment A25).

```bash
PYTHONPATH=models/language-id-kernel pytest -q models/language-id-kernel/tests/
python3 models/language-id-kernel/kaphtor_kernel.py calibrate --n-perm 10000
```

### Repository layout

- `wiki/`: the record, generated from the data. Nothing in it is written by hand.
  - `linear-a/`: `inscriptions/<site>/<series>/`, `words/<initial>/` and `signs/{syllabic,logograms,fractions}/`,
    with the generated ledgers (`standing.md`, `counts.md`, `by_site.md`, `by_root.md`, `by_sign.md`,
    `unread_signs.md`, `by_scribe.md`)
  - `names/`: one page per name, `<layer>/names/<name>.md`, and per root, `<layer>/roots/<root>.md`, with the
    guide (`guide/ledger.md`, `guide/kinds/`, `guide/how_to.md`, `guide/map.md` with its map of Crete, `guide/crete.svg`)
  - `semitic-roots/`: one page per root, `<radical>/<id>_<slug>.md`
  - `pre-greek/`: one page per word, `<initial>/<key>.md`, with the ledgers `by_feature.md` and `semitic.md`
  - `aegean/`: `eteocretan/`, and `cypro-minoan/<site code>/<siglum>.md` with `by_site.md`, `by_type.md` and
    `translated.md`
- `data/`: the datasets, each with a datasheet or manifest giving its licence and sources
  - `linear-a/`: the corpus, sign values, lexicon, onomasticon, translations, unread words, the Eteocretan sets and
    the rival-language root keys
  - `semitic-roots/`: the root database
  - `pre-greek/`: the Pre-Greek lexicon, Beekes's Pre-Greek features and a sidecar of Wiktionary glosses
  - `contact/`: the open contact lexica the root index links to the roots (Hebrew, Aramaic, Amarna Canaanite,
    Syriac, Akkadian)
  - `ane/`: open-licence and public-domain ancient Near East datasets, such as the ORACC Akkadian literary glossary,
    PNM v6, Prosopographia Memphitica, Gauthier's DNG, the Kassite name concordances, the Ugarit Texts Database's
    catalogue, the ELiSiR Eblaite lexicon, the Cypriot syllabic inscriptions of IG XV 1, a catalogue of the
    Cypro-Minoan texts with di Mino's readings (no transcription beyond the sign groups of the words read), I.Sicily's
    Semitic inscriptions, the public inscriptions of Palmyra
    (catalogue rows and names), Marcato's Hatra names and Al-Jallad's DIANA, Safaitic and Taymanitic
    (non-commercial)
  - `share-alike/`: CC BY-SA datasets, such as the ORAEC/TLA Egyptian texts, the TLA v18 names, Trismegistos Geo and
    ORACC's editions and translations of the Ugarit, Amarna and Idrimi texts, kept apart
- `docs/`: the repository's rules and methods, and the corpus guides, starting with [docs/anatomy.md](docs/anatomy.md)
- `models/`: replicable probabilistic models, starting with [models/language-id-kernel/_index.md](models/language-id-kernel/_index.md)
- `assets/`: Noto Sans fonts for the Aegean scripts (OFL 1.1) and the README banner
- `tools/`: the Python package (`import tools`) behind the `kaphtor` command, described in
  [tools/README.md](tools/README.md)
  - `core/`: skeletons, morphology, phonetics, null models, and the Shoresh root matcher (`root_match.py`, vocalized CV `shoresh_cv.py`, and kernel bridge `shoresh_kernel_bridge.py`)
  - `linear_a/`: the Linear A tools (search, paradigms, accounting, sign tests)
  - `ane/`: query clients for the ancient Near East corpora
  - `views/`: the builder that writes `wiki/` from `data/`
- `skills/`: two agent skills, Linear A research and ancient Near East research, whose commands call `kaphtor`
- `tests/`: the tests for the tools, the data and the generated views

</details>

## Contributing

Readings, rival analyses, falsifications, sources, corrections and tools are welcome, from people or agents. Report a
misread sign or a failed reading as an issue: the templates cover a reading, a falsification, a rival hypothesis and a
rights concern. To submit a rival analysis or an addition, open a pull request following
[CONTRIBUTING.md](CONTRIBUTING.md), which covers copyright, page structure and the checks to run. A new reading enters
at tier 1 and rises only by passing the tests above.

## Citing

To cite this record, use [CITATION.cff](CITATION.cff). GitHub's "Cite this repository" button reads it.

Zenodo archives each release. [10.5281/zenodo.24375016](https://doi.org/10.5281/zenodo.24375016) cites the record in
all its versions, and each release has a DOI of its own, listed on the record (1.0.0:
[10.5281/zenodo.24375017](https://doi.org/10.5281/zenodo.24375017)).

## Acknowledgments

The corpus builds on Louis Godart and Jean-Pierre Olivier's *Recueil des inscriptions en linéaire A* (GORILA) and its
supplement RILA-S1, on [SigLA](https://sigla.phis.me), built by Ester Salgarella and Simon Castellan, and on Rob
Hogan's [lineara.xyz](https://github.com/mwenge/lineara.xyz). Its readings were checked against GORILA, John Younger's
*Linear A Texts* and the other primary editions, and many were corrected. GORILA's photographs and drawings are ©
École française d'Athènes and are not reproduced here.

The root database builds on the standard dictionaries of the Semitic languages, cited by siglum and page on every
cell, and the corpus guides credit each digital corpus the `ane` tools read.

## License

The code (`tools/`, `tests/` and `skills/`) is licensed under the [Apache License 2.0](LICENSE). Unless otherwise
noted, our original data and writing (`data/`, `wiki/`, `docs/` and the other documentation) are licensed under
[Creative Commons Attribution 4.0 International](LICENSE-CC-BY-4.0). Third-party material keeps its own terms, set
out below and in the `license` key of each datasheet:

- **Protected dictionaries.** The root database gives the cited form, the source's siglum and the page, so a reader
  can find the entry in the original. A reflex quotes a gloss only when its cited source is in the public domain or
  under an open licence. The reconstructions of 2,647 records and the English meanings of 2,644 come from the Semitic
  Etymological Dictionary (SEDonline, SED I and SED II), a closed source, and each record cites its SED entry. The Pre-Greek lexicon
  takes from Beekes, Rosół and Furnée only headwords, the Semitic forms they cite with their dictionary references,
  pages, sections and verdicts recast as our codes, none of their text.
- **The Linear A corpus.** `data/linear-a/corpus.json` builds on SigLA, whose data is under CC BY-NC-SA 4.0, and on
  lineara.xyz, which states no licence. Our corrections and added layers are CC BY 4.0. The underlying texts keep
  their sources' terms. `data/linear-a/sigla-sign-map.json` is SigLA's sign list and stays under CC BY-NC-SA 4.0.
  `data/linear-a/sigla/database.js` is SigLA's database file, unchanged, and `data/linear-a/sigla_db.json` decodes
  it; both stay under CC BY-NC-SA 4.0, apart from the `corpus_key` and `corpus_match` fields and
  `sigla/corpus_key_overrides.json`, which are CC BY 4.0. The screenshots in `docs/human-review/` show SigLA's
  drawings and sign crops and carry its CC BY-NC-SA 4.0 terms.
- **Share-alike data.** The files in `data/share-alike/` remain under CC BY-SA 4.0 (`oracc-levant/` under CC BY-SA
  3.0), and anything derived from them carries the same terms. Four more files under CC BY-SA 4.0 sit outside that folder, where the tools read them:
  `data/linear-a/egyptian_roots.json` and `luwian_roots.json`, which hold entries from Wiktionary,
  `data/contact/syriac_lexicon.jsonl`, drawn from Wiktionary's Classical Syriac entries, and
  `data/pre-greek/pregreek_wiktionary_glosses.json`, short glosses from Wiktionary's Pre-Greek category. A Pre-Greek
  word page that shows one of those glosses names its licence beside it.
- **Rival-language keys and contact lexica.** The Egyptian, Luwian, Hurrian and Hattic root files give each form, its
  key and its source labels, with no meaning; the Hattic forms and page numbers come from Soysal 2004 (Brill), none
  of its text. Most Luwian forms come from the Annotated Corpus of Luwian Texts and The
  Indo-European Database, which state no licence; `data/linear-a/rival-roots.md` sets out their terms. The contact
  lexica in `data/contact/` hold only rows and fields from open sources, among them ORACC's Amarna and CAMS/GKAB
  glossaries, which its open-data download releases under CC0; their datasheets name what the private build adds, why it is not here,
  and the known limits of each source.
- **Non-commercial data.** `data/ane/diana-safaitic/` and `data/ane/diana2-taymanitic/` hold the entries of
  Al-Jallad's *Dictionary of the Inscriptions of Ancient North Arabia*, Volume I: Safaitic (CC BY-NC-ND 4.0) and
  Volume II: Taymanitic (CC BY-NC 4.0), both 2026. Neither may be used commercially. Each entry's text is as the
  book prints it, in another format, with an index (`forms`, `match_keys`) beside it; Volume I's entries may not be
  shared in adapted form. The Semitic roots cite both volumes by page, without their glosses.
- **Public-domain sources.** `data/ane/gauthier-dng/` (Gauthier's *Dictionnaire des noms géographiques*, 1925–1929)
  and `data/ane/kassite-concordances/` (seven name indexes, 1906–1912) are read from the OCR of public-domain books;
  the OCR and the files add no rights.
- **The fonts.** The fonts in `assets/fonts/` are under the SIL Open Font License 1.1.
- **Withheld material.** Sources that cannot be redistributed are not shipped; the tools that read them name the path
  they looked for. Scanned books are not included.

Copyright © Tom di Mino. Published by Plasma AI.
