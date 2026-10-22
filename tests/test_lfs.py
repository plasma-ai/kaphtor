"""Every PDF and every data file over 1 MB is stored with Git LFS, as the README says.

The rules are read from `.gitattributes` and matched as Git matches them: a pattern with no slash matches a file name
in any folder, `**/` matches any run of folders, and `*` stays inside one folder. Nothing here writes.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LIMIT = 1 << 20
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache"}


def rule(glob: str) -> re.Pattern:
    body = re.escape(glob.lstrip("/")).replace(r"\*\*/", "(?:.*/)?").replace(r"\*", "[^/]*")
    return re.compile(("(?:.*/)?" if "/" not in glob else "") + body + "$")


def lfs_rules(text: str) -> list[re.Pattern]:
    return [rule(parts[0]) for parts in (line.split() for line in text.splitlines())
            if parts and not parts[0].startswith("#") and "filter=lfs" in parts[1:]]


def needs_lfs() -> list[str]:
    files = (p for p in REPO.rglob("*") if p.is_file() and not SKIP & set(p.relative_to(REPO).parts))
    return sorted(p.relative_to(REPO).as_posix() for p in files
                  if p.suffix.lower() == ".pdf" or (p.relative_to(REPO).parts[0] == "data" and p.stat().st_size > LIMIT))


@pytest.mark.data
def test_every_pdf_and_large_data_file_has_an_lfs_rule():
    rules = lfs_rules((REPO / ".gitattributes").read_text(encoding="utf-8"))
    uncovered = [path for path in needs_lfs() if not any(r.match(path) for r in rules)]
    assert not uncovered, uncovered


def test_rules_match_as_git_matches():
    rules = lfs_rules("# a comment\ndata/**/*.jsonl filter=lfs diff=lfs\n*.pdf filter=lfs\n"
                      "data/linear-a/corpus.json filter=lfs\n*.txt text\n")
    hit = lambda path: any(r.match(path) for r in rules)
    assert hit("data/ane/pnm-v6/tables/persons.jsonl") and hit("data/a.jsonl")
    assert hit("library/x/y.pdf") and hit("y.pdf") and hit("data/linear-a/corpus.json")
    assert not hit("tools/x.jsonl") and not hit("data/linear-a/lexicon.json") and not hit("notes.txt")
