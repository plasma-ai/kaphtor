---
name: docs/lexicon-api
title: Linear A Lexicon API & MCP
desc: Reference for the read-only Linear A Lexicon REST API (api.linear-a.ai), MCP server (mcp.linear-a.ai/mcp), and Markdown/llms.txt endpoints exported from kaphtor, including live probabilistic kernel endpoints.
tags: [docs, linear-a, api, mcp, probabilistic-model]
authors: "di Mino"
created: 2026-11-23T00:00:00Z
updated: 2026-11-24T00:00:00Z
---

# Linear A Lexicon API & MCP

The Linear A Lexicon at [linear-a.ai](https://linear-a.ai/) exposes the committed `kaphtor` research record—words, names, corpus documents, Proto-Semitic roots, signs, research wiki, and live deterministic probabilistic language-identification kernels—through a read-only **REST API**, a **Model Context Protocol (MCP)** server, and plain **Markdown / `llms.txt`** endpoints.

## Base Endpoints

| Interface | URL | Notes |
| --- | --- | --- |
| **REST API index** | `https://api.linear-a.ai/v1` | JSON index of all 18 `GET` routes, `lexicon_version`, `standing`, `/v1/health`, and the MCP address |
| **Health & edition** | `https://api.linear-a.ai/v1/health` | Returns `lexicon_version`, record count, and deployment provenance (`site_commit`, `kaphtor_commit`, `input_sha256`) |
| **MCP server** | `https://mcp.linear-a.ai/mcp` | Streamable HTTP JSON-RPC (`linear-a-lexicon`, contract `1.2.2`), 18 read-only idempotent tools |
| **Web & Markdown** | `https://linear-a.ai/` | Append `.md` or `/index.md` to any page (e.g. `https://linear-a.ai/lexicon/KU-RO.md`) |
| **LLM discovery** | `https://linear-a.ai/llms.txt` | Concise site guide and Confirmed-tier summary; full catalog at `https://linear-a.ai/llms-full.txt` |

## Access, Caching & Errors

- **No authentication required:** Both the REST API and MCP server are open and read-only (`securitySchemes: [{ type: "noauth" }]`, `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`).
- **Methods & CORS:** REST accepts `GET`, `HEAD`, and `OPTIONS` with `Access-Control-Allow-Origin: *` and `X-Content-Type-Options: nosniff`.
- **Caching:** Successful responses return `Cache-Control: public, max-age=300, s-maxage=86400`; health checks and `not_found` responses cache for `max-age=60, s-maxage=300`.
- **Errors:** Invalid inputs (`400`), missing routes or records (`404`), non-`GET` methods (`405`), and temporary unavailability (`503`) return RFC 9457 `application/problem+json` bodies typed under `https://api.linear-a.ai/problems/`. Missing lookups (`not_found`) return `404` along with nearest-name suggestions.

## Endpoints & MCP Tools (18 Routes)

Every REST route maps one-to-one to an MCP tool with identical input and output schemas.

### 1. Live Probabilistic Language-ID Kernels

Backed by the zero-LLM, deterministic twelve-kernel suite in [`models/language-id-kernel/`](../models/language-id-kernel/README.md) under strict Linear B sign values:

| REST Route (`GET`) | MCP Tool | Parameters | Purpose |
| --- | --- | --- | --- |
| `/v1/kernel/summary` | `kernel_summary` | *(none)* | Signed twelve-kernel scoreboard (`Kernels A–L`), calibration gates, Bayes factors, backward-projection stress-tests, and permutation p-values |
| `/v1/kernel/anchors` | `run_anchor_kernel` | `subset` (`full_8`, `drop_3_trade_loans`, `arithmetic_only_2`, `linear_b_cal`), `drop` (comma-separated words), `perms`, `seed`, `beta` | Runs live **Kernel D** consonant-series grid permutations on Linear A pre-linguistic anchors, custom leave-any-out ablations, or the Mycenaean Linear B Greek calibration control |
| `/v1/kernel/ligatures` | `run_ligature_kernel` | `target` (`linear_a`, `linear_b_cal`), `perms`, `seed`, `beta` | Runs live **Kernel F** commodity ligature acrophony permutations (`GRA`/`OLE`/`VIN`) or the Linear B Greek calibration control |

### 2. Direct Record Lookups

| REST Route (`GET`) | MCP Tool | Parameters | Purpose |
| --- | --- | --- | --- |
| `/v1/overview` | `get_lexicon_overview` | *(none)* | Edition counts, confidence-tier rules, standing notice, and source provenance |
| `/v1/words/{word}` | `get_word` | `word` (path, e.g. `KU-RO`) | Full lexicon entry: Linear A signs, proposed reading/meaning, tier, compared forms, rivals, attestations, and bibliography |
| `/v1/names/{name}` | `get_name` | `name` (path, e.g. `A-DU`) | Onomasticon record: personal name, place, god, or title with language layer, tier, and attestations |
| `/v1/texts/{number}` | `get_text` | `number` (path, e.g. `HT109`, `IOZa2`) | Corpus document with Linear A signs, transliteration, proposed translation, word glosses, and edition metadata |
| `/v1/roots/{root}` | `get_root` | `root` (path, id or radical form) | Proto-Semitic root reconstruction, reflexes across the five Semitic branches, citations, and linked Linear A words |
| `/v1/signs/{sign}` | `get_sign` | `sign` (path, e.g. `KU`, `*21F`) | Sign record: Linear B / conventional or proposed value, evidence, and linked entries |

### 3. Search, Filtered Lists & Discovery

| REST Route (`GET`) | MCP Tool | Parameters | Purpose |
| --- | --- | --- | --- |
| `/v1/search` | `search` | `query` *(required)* | Full-text search across words, names, texts, roots, meanings, scholars, and wiki pages; returns `id` values for `fetch` |
| `/v1/records` | `fetch` | `id` *(required)* | Reads the full text of a record returned by `search` (paginates long pages via chained next IDs) |
| `/v1/words` | `list_words` | `tier` (`Confirmed`, `Probable`, `Candidate`, `Speculative`), `word_type`, `language_family`, `compared_with`, `site`, `first_proposed_by`, `min_occurrences`, `text`, `page` | Filtered, paginated lexicon entries |
| `/v1/texts` | `list_texts` | `site`, `object`, `scribe`, `has_translation` (bool), `text`, `page` | Filtered, paginated corpus documents |
| `/v1/names` | `list_names` | `name_type`, `language`, `site`, `text`, `page` | Filtered, paginated onomasticon records |
| `/v1/compared` | `find_words_compared_with` | `form` *(required)*, `language`, `page` | Linear A entries compared with a given Semitic, Egyptian, Anatolian, Hurrian, or Greek form |
| `/v1/by-signs` | `find_words_by_signs` | `signs` *(required)*, `position` *(required: `start`, `end`, `anywhere`, `whole`)*, `page` | Structural sign-sequence search across the lexicon |
| `/v1/occurrences/{word}` | `list_occurrences` | `word` (path), `page` | Every inscription line where a Linear A word occurs, with context and gloss |
| `/v1/values` | `list_values` | `tool` (`list_words`, `list_texts`, `list_names`), `field` (`word_type`, `language_family`, `compared_with`, `site`, `first_proposed_by`, `object`, `scribe`, `name_type`, `language`) | Enumerates valid filter values for the list endpoints |

## Quick Examples

### `curl`

```bash
# Discover all 18 routes and edition metadata
curl -s https://api.linear-a.ai/v1 | jq .

# Look up KU-RO ("total")
curl -s https://api.linear-a.ai/v1/words/KU-RO | jq '{word, reading, meaning, tier}'

# Read the twelve-kernel probabilistic scoreboard
curl -s https://api.linear-a.ai/v1/kernel/summary | jq .

# Run a live Kernel D permutation test dropping trade-loan suspects
curl -s 'https://api.linear-a.ai/v1/kernel/anchors?subset=drop_3_trade_loans&perms=1000' | jq .

# Verify the Linear B Greek calibration control on Kernel D
curl -s 'https://api.linear-a.ai/v1/kernel/anchors?subset=linear_b_cal&perms=1000' | jq .

# Fetch a clean Markdown page directly
curl -s https://linear-a.ai/lexicon/KU-RO.md
```

### MCP Client Configuration

The Linear A Lexicon plugin sets this up for Claude and ChatGPT and adds a skill; see
[[docs/lexicon-plugin|lexicon-plugin]]. Otherwise, point any Streamable HTTP MCP client (Claude, Codex, Cursor, or
custom agent) at:

```json
{
  "mcpServers": {
    "linear-a-lexicon": {
      "type": "http",
      "url": "https://mcp.linear-a.ai/mcp"
    }
  }
}
```

## Provenance, Standing & Licences

- **Source of truth:** All API and MCP data is exported deterministically from committed `kaphtor` snapshots (`data/linear-a/` and `data/semitic-roots/`). Check `GET /v1/health` to inspect the exact `kaphtor_commit` and `input_sha256` served by a deployment. Note that `linear-a.ai` omits entries attested exclusively in the London Medical Papyrus (`LMP-…`), so `kaphtor`'s total word count is slightly higher.
- **Epistemic standing:** Every reading returned by the API or MCP server is Tom di Mino's proposal (unless an earlier proposer is cited) carrying its confidence tier (`Confirmed`, `Probable`, `Candidate`, `Speculative`) and recorded rival readings; `Confirmed` fixes corpus function, not etymology. See [`docs/confidence.md`](confidence.md).
- **Licences:** Lexicon, names, translations, commentary, and Proto-Semitic roots are **CC BY 4.0**; underlying SigLA corpus transcriptions retain **CC BY-NC-SA 4.0**.
