"""Shared corpus word-extraction utilities."""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from ..paths import LINEAR_A_DATA, require
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import LINEAR_A_DATA, require

DATA_DIR = LINEAR_A_DATA
CORPUS_PATH = DATA_DIR / "corpus.json"


def load_corpus() -> dict:
    return json.loads(require(CORPUS_PATH, "corpus.json").read_text(encoding="utf-8"))


def extract_words(corpus: dict) -> list[dict]:
    """Extract word records from GORILA corpus.

    Returns list of dicts with keys: word, signs, doc_id, site, support.
    Filters out non-hyphenated tokens, newlines, and stray Unicode.
    """
    results = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        support = doc.get("support", "")
        for token in doc.get("transliteratedWords", []):
            if not isinstance(token, str) or not token.strip() or token == "\n":
                continue
            if len(token) == 1 and ord(token) > 127:
                continue
            word = token.upper()
            if "-" in word:
                results.append({
                    "word": word,
                    "signs": word.split("-"),
                    "doc_id": doc_id,
                    "site": site,
                    "support": support,
                })
    return results


def extract_word_tuples(corpus: dict) -> list[tuple[str, str, str]]:
    """Extract (word, site, doc_id) tuples from corpus.

    Lighter-weight variant used by ventris_paradigms.py.
    """
    results = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        for token in doc.get("transliteratedWords", []):
            if not isinstance(token, str) or not token.strip() or token == "\n":
                continue
            if len(token) == 1 and ord(token) > 127:
                continue
            word = token.upper()
            if "-" in word:
                results.append((word, site, doc_id))
    return results
