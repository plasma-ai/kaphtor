# tools/ane

Query clients for the ancient Near East corpora: local indexes, and single-page lookups against public databases.
The remote clients fetch one bounded page per call, cache it, and send a project user agent with no contact details.

| Script | Purpose | Source |
|---|---|---|
| `ane_keys.py` | Query notation: parses a typed root or form and spells it in each view's stored notation | — |
| `aneq.py` | DuckDB queries over the local corpora: Egyptian documents, the Akkadian glossary and the other views as their data is added; `stats` lists what is present | local |
| `etymon.py` | A root dossier: the root's reconstruction, Linear A words and names, and its reflexes in each local corpus; `--out DIR` or `--stdout` | local |
| `name_elements.py` | Splits a name into the elements of a name-element table given with `--table` | local |
| `query_deaps.py` | One DEAPS search page or textual-object record | remote |
| `query_diconab.py` | One public DiCoNab query page or inscription record | remote |
| `query_elephantine.py` | One public Elephantine query, object or text page | remote |
| `query_hathitrust.py` | The pages of a HathiTrust volume (search-only ones included) that hold a token, from its HTRC Extracted Features file (CC BY 4.0, doi:10.13012/R2TE-C227); `docs/corpora/hathitrust-search-only-volumes.md` | remote |
| `query_idai_gazetteer.py` | Bounded, cached lookup in the public iDAI.gazetteer API | remote |
| `query_place_authorities.py` | Pleiades and Trismegistos place records (iDAI records are not shipped) | local |
| `query_portal_common.py` | Shared safeguards for the remote clients | — |
| `query_proper_names.py` | ORACC, PNM, Prosopographia Memphitica, TLA v18, Gauthier DNG and Kassite concordance proper-name layers | local |
| `query_rsti.py` | One public RSTI/OCHRE UUID response | remote |

Each remote client caches its responses under the user cache, `$XDG_CACHE_HOME/kaphtor/<portal>/` (else
`~/.cache/kaphtor/`), never inside the repository. Data paths come from `tools/paths.py`; a client whose dataset is
not in the checkout names the path it looked for.
A cache is the source's data, not ours to redistribute.

## DiCoNab: rights and citation

DiCoNab (<https://diconab.huma-num.fr/info/terms>) may be used freely for academic research and reproduced in part,
with proper citation and the stable URL of each inscription cited. Reproduction and distribution rights in its
texts and media are reserved, and fuller access is granted to scholars on request. So:

- use `query_diconab.py` for specific questions and cited records;
- cite each inscription with the citation given on its record page;
- do not loop over result pages, enumerate record ids, or treat the cache as a corpus;
- ask the project for access or an export before any comprehensive reuse.

The client makes one query or record request per call (a search needs one form request first), never follows
pagination, never requests images or media, and waits at least one second between requests.

## Notes

`aneq.py`, `query_place_authorities.py` and `query_proper_names.py` import `ane_keys` for its notation. `etymon.py`
reads the Linear A lexicon and onomasticon through `tools/linear_a/lq.py`. A command whose corpus is not in the
checkout names the path it looked for and exits 2.

No corpus `aneq.py` reads is shipped beyond those under `data/`; the others are a user's own downloads, under their
sources' terms. The SEAL (CC BY-NC-ND) and DAPCA views read non-commercial data: query it for research, and do not
redistribute it or what is derived from it.
