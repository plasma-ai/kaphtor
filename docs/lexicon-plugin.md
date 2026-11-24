---
name: docs/lexicon-plugin
title: Linear A Lexicon plugin
desc: The plugin that connects Claude and ChatGPT to the Linear A Lexicon's public MCP server, the repository it lives in, how to install it, what it sends, and how it differs from the kaphtor plugin.
tags: [docs, linear-a, mcp, plugin]
authors: "di Mino"
created: 2026-11-24T00:00:00Z
updated: 2026-11-24T00:00:00Z
---

# Linear A Lexicon plugin

The Linear A Lexicon plugin pairs the Lexicon's public MCP server with one skill, `reading-linear-a`, which tells the
model how to give a reading: as a proposal, with its confidence tier, beside any rival reading on record. The server
and its 18 tools are described in [[docs/lexicon-api|lexicon-api]].

The plugin lives in its own repository,
[plasma-ai/linear-a-lexicon-plugin](https://github.com/plasma-ai/linear-a-lexicon-plugin), and this repository's
plugin marketplace lists it. It is kept apart because the plugin directories of Claude and
ChatGPT read a plugin from a small repository: Claude's refuses one with Git LFS rules or 10,000 files, and this
repository has both. The plugin holds no data and no site code.

## Install

In Claude Code, add this repository as a plugin marketplace and install the plugin:

```
/plugin marketplace add plasma-ai/kaphtor
/plugin install linear-a-lexicon@plasma
```

Any other client that speaks Streamable HTTP MCP needs only the server's address, with no key and no sign-in:

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

For ChatGPT, each release of the plugin's repository carries the zip it takes.

## Two plugins

| | `linear-a-lexicon` | `kaphtor` |
|---|---|---|
| Lives in | `plasma-ai/linear-a-lexicon-plugin` | this repository |
| Holds | a connector to the public server and one skill | two research skills over this repository |
| Needs | nothing but the network | a clone, Python and `uv` |
| Answers from | the published Lexicon at linear-a.ai | the files in `data/` and the `kaphtor` command |
| Use it to | look up a word, a name, a document, a root or a sign in conversation | run searches, tests and checks on the record itself |

## What it sends

The plugin sends the words, names, document numbers and search text of a question to `mcp.linear-a.ai`, which
answers from the published Lexicon. Every tool reads only. It needs no account and stores nothing about the user.

## Checking and release

The plugin's repository holds its tests, a copy of the server's contract and a script that compares that copy with
the running server. The plugin carries its own version, apart from this repository's, and its files are under the
Apache License 2.0. Here, `tests/test_plugin.py` holds the marketplace entry to the plugin's repository and folder.
