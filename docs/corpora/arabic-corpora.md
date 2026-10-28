---
name: docs/corpora/arabic-corpora
title: Arabic & Quranic Corpora
desc: Acquisition routes, file formats and APIs for the Quran text and morphology, the classical Arabic lexica, pre-Islamic Arabian epigraphy and the sources on pagan Arabia.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Arabic & Quranic Corpora

Acquisition routes, file formats, and API references for the Arabic layer:
Quran text + morphology, classical lexica, pre-Islamic Arabian epigraphy,
and pagan-Arabia primary sources.

## Local corpora

The files below are not in this repository: each is a user's own build from the source named. The repository ships
only the sets under `data/`, and each folder's index lists them.

| File | Rows | Source |
|---|---|---|
| `data/quran_roots.jsonl` | 1,651 roots | QAC 0.4 morphology |
| `data/quran_text.jsonl` | 6,236 ayahs | Tanzil Uthmani |
| `data/arabian_epigraphy.jsonl` | 74 inscriptions | OCIANA (OSU) |
| `data/south_arabian_epigraphy.jsonl` | 187 curated entries | DASI (CNR), from the DASI lexicon, which is not in this repository |

Not in this repository, for rights: the Faris 1952 Kitāb al-Aṣnām index, the Beeston and Biella Sabaic
dictionaries, and Harding 1971, with the name-element search and theonym list built from Harding and the Aṣnām.

## Quran text & morphology

### Quranic Arabic Corpus (QAC) morphology

- Canonical home: https://corpus.quran.com; the download page gates
  `quranic-corpus-morphology-0.4.txt` behind an email form (GPL, Kais Dukes,
  academic use with attribution).
- **Acquired route:** the `mustafa0x/quran-morphology` GitHub mirror
  (`quran-morphology.txt`), which converts roots/lemmas from Buckwalter to Arabic
  script and carries documented fixes. Cached at
  `data/ingest/quran/quran-morphology-mustafa0x.txt` (130,030 morpheme rows,
  50,269 with ROOT tags).
- Row format: `surah:ayah:word:morpheme <TAB> form <TAB> tag <TAB> feat|feat|…`
  with `ROOT:` and `LEM:` features in Arabic script.
- The raw QAC 0.4 file (if ever needed) uses Buckwalter transliteration, a
  deterministic 1:1 ASCII↔Arabic mapping.

### Arabic → Semitic romanization

Arabic root letters map to the project's Semitic conventions so `match_keys` align with its consonant folding:

```
ء أ إ آ ؤ ئ ا → ʔ    ث → ṯ    ج → ǧ    ح → ḥ    خ → ḫ    ذ → ḏ
ش → š    ص → ṣ    ض → ḍ    ط → ṭ    ظ → ẓ    ع → ʿ    غ → ġ    ة → t    ى → y
```

Consonant-folding additions for this layer: `ḍ→d`, `ǧ→g` (regular ǧīm ↔ gimel
correspondence: recall over precision for deep cognate hunting).

### Tanzil

- https://tanzil.net/download/: bulk Quran text, no auth, <5 MB.
- Direct form URL: `https://tanzil.net/pub/download/index.php?quranType=uthmani&outType=txt-2&agree=true`
  (`txt-2` = `surah|ayah|text` lines; `txt` = bare text).
- Cached: `data/ingest/quran/quran-uthmani-numbered.txt` (6,236 ayahs).

### APIs (no key required)

| API | Base | Use |
|---|---|---|
| alquran.cloud | `https://api.alquran.cloud/v1` | `/ayah/{s}:{a}/editions/quran-uthmani,en.sahih`; `/search/{kw}/all/{edition}`; `/quran/{edition}` (whole Quran, one call) |
| quran.com v4 | `https://api.quran.com/api/v4` | `/verses/by_key/{s}:{a}?words=true` (word-by-word + transliteration); `/verses/by_page/{1–604}?words=true` (gloss enrichment); **requires a real User-Agent header; default python-urllib UA gets 403** |
| quranenc.com | `https://quranenc.com` | per-translation SQLite/Excel bulk: `/en/home/download/sqlite/{slug}` |

## Classical Arabic lexica

- **arabiclexicon.hawramani.com**: a live aggregator of 50+ classical dictionaries
  (Lane's *Arabic-English Lexicon*, *Lisān al-ʿArab*, al-Zabīdī, …). WordPress
  WP-JSON API.
- **lexicon.quranic-research.net**: offline (broken SSL).
- **SabaWeb (sabaweb.uni-jena.de)**: the Sabaic dictionary, offline. The print dictionaries are Beeston et al.,
  *Sabaic Dictionary* (1982) and Biella, *Dictionary of Old South Arabic* (1982).
- **SEDonline (http://sed-online.ru)**: the Semitic Etymological Database, live (HSE University; L. Kogan,
  I. Arkhipov), about 2,060 reconstructions and 24,500 forms. The old host sed-online.uni-jena.de is gone. No
  licence, API or export. Print SED I–II remain the reference.

## Pre-Islamic Arabian epigraphy

### OCIANA: Ancient North Arabian

- **Current home: https://ociana.osu.edu** (relaunched Sept 2024 at Ohio State
  under Al-Jallad). The old Oxford host `krc.orient.ox.ac.uk/ociana` is gone.
- ~40,000 inscriptions: Safaitic, Hismaic, Dadanitic, Taymanitic. Transliteration,
  translation, commentary, bibliography, provenance, photos.
- No API, no bulk export → **targeted harvest only** (probe-gated, ≥3 s delay, cached, resumable). Deity query set:
  mnt, lt, ʿzy, rḍw, bʿlsmn.
- **Scrape mechanics:** Rails app, server-rendered. Search:
  `GET /inscriptions?search[transliterated_text]=<q>&search[last_updated]=0&per_page=48&search[layout]=list`,
  pagination via `page=`. Records at `/inscriptions/<id>` as dt/dd pairs (Siglum,
  Transliteration, Translation, Language and Script, Site, Subjects). The harvest holds
  74 inscriptions (mnt 10, lt 25, ʿzy 14, rḍw 25, bʿlsmn 0, likely spelled bʿls¹mn
  in OCIANA's conventions). Among them is **RWQ 319** (Wādī Salmā, Jordan), a
  Safaitic prayer invoking three deities, "h ds²r w mnt w lt s¹lm": Dushara, Manāt,
  and Allāt together.

### DASI: Ancient South Arabian

For the complete cross-layer inventory—including Geʿez and the explicit Modern
South Arabian gap—see [south-semitic-corpora.md](south-semitic-corpora.md).

- https://dasi.cnr.it: 9,000+ texts: Sabaic, Minaic, Qatabanic, Hadramitic
  (CSAI), plus DiCoNab (Nabataean/Developing Arabic).
- Public OAI-PMH is verified at `https://dasi.cnr.it/oai`. On 2026-10-11 it
  reported 9,127 epigraphs and 9,783 linked object records. Epigraphs support
  EpiDoc; objects support Dublin Core. The separate Hydra/JSON-LD API remains
  JWT-gated.
- Bulk `ListRecords` currently fails server-side; records are reached by paginating `ListIdentifiers` and retrieving
  each one individually, serially, with a two-second cooldown, `Retry-After` honoured, and no image retrieval.
- The OAI EpiDoc layer is the preferred source for text-level ingestion.
- Deity query set: mnt, ʾṯrt (Athirat, in Minaic and Qatabanic), lt, ʿzy, partially
  covered by the 187-entry curated `south_arabian_epigraphy.jsonl` (85 divine names).

### DiCoNab: Nabataean and Developing Arabic

- Public records and word/root attestations can be consulted case by case with
  `tools/ane/query_diconab.py`; for example, `query_diconab.py mlk` or
  `query_diconab.py --inscription 3287`.
- A word/root search establishes the public Symfony form session, submits one
  substantive filter, and returns only the explicitly requested result page.
  The client never follows pagination or requests media. Identical requests are
  cached under `$XDG_CACHE_HOME/kaphtor/diconab/` (else `~/.cache/kaphtor/diconab/`).
- DiCoNab permits academic consultation and partial reproduction with proper
  citation, but reserves reproduction and distribution rights. Full database
  access requires a scholarly request; the query cache is not a corpus.
- Rights and citation rules: the DiCoNab section of `tools/ane/README.md`.

## Pagan & classical Arabic literature

- **Kitāb al-Aṣnām** (Ibn al-Kalbī, d. 819): the primary source for pre-Islamic
  Arabian religion. Arabic originals free on archive.org
  (identifiers: `KitabalAsnamLiKalbi`, `KitabAlAsnam`,
  `the-book-of-idols-by-hisham-ibn-al-kalbi`; JSON search:
  `https://archive.org/advancedsearch.php?q=kitab+al-asnam&output=json`).
- **OpenITI**: machine-readable Islamicate corpus on GitHub
  (`github.com/OpenITI`, RELEASE repo ~10+ GB). Never clone; fetch single texts
  by raw URL (e.g. Ibn al-Kalbī's Aṣnām, Ibn Hishām's Sīra).
- **shamela.ws**: a large Arabic library, web-only, no API.
- **aldiwan.net**: Jahili poetry (Imruʾ al-Qays, Zuhayr, …), web-only,
  Cloudflare-fronted.
- **sunnah.com**: hadith; API needs a requested key.
