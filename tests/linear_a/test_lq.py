"""lq, the SQL views over the Linear A data: what each command shows, and a dataset not in the checkout named.

lq runs as a user would run it (a subprocess from the repo root). The unit tests point KAPHTOR_DATA at a folder
written inline; the data test reads the shipped lexicon. Nothing here writes to data/.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("duckdb")

ROOT = Path(__file__).resolve().parents[2]
LQ = ROOT / "tools" / "linear_a" / "lq.py"

LEXICON = {"entries": [
    {"word": "KU-RO", "reading": "kullu", "root": "k-l-l", "meaning": "total", "confidence": "CONFIRMED",
     "category": "administrative", "language_layer": "semitic", "semantic_field": "administrative",
     "attestations": ["HT13"]},
    {"word": "KI-RO", "reading": "kīlu", "root": "k-y-l", "meaning": "deficit", "confidence": "PROBABLE",
     "category": "administrative", "language_layer": "semitic", "semantic_field": "administrative",
     "attestations": []},
]}
ONOMASTICON = {"entries": [
    {"token": "KU-PA₃-NU", "type": "personal_name", "affiliation": "semitic", "reading": "Kubānu",
     "meaning": "a name", "frequency": 4},
]}
CORPUS = {"HT13": {"name": "HT13", "site": "Haghia Triada", "support": "Tablet", "context": "LMIB",
                   "transliteratedWords": ["KA-U-DE-TA", "KU-RO"]}}
TRANSLATIONS = {"translations": {"HT13": {
    "translation": "Wine from Kaudeta; total 130.", "confidence": "PROBABLE",
    "words": [{"linear_a": "KA-U-DE-TA", "meaning": "a place name"}, {"linear_a": "KU-RO", "gloss": "total"}],
}}}
UNREAD = {"entries": [
    {"word": "A-DA-KI", "note": "Legible. No reading.", "status": "unread", "attestations": ["HT85a"]},
    {"word": "]-TI", "note": "Not readable: the first sign is lost.", "status": "unread", "attestations": ["HT9"]},
]}


def run(*args: str, data: Path | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    if data is not None:
        env["KAPHTOR_DATA"] = str(data)
    return subprocess.run([sys.executable, str(LQ), *args], cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=120)


def json_documents(text: str) -> list:
    """The JSON arrays lq prints one after another."""
    decoder, out, i = json.JSONDecoder(), [], 0
    while (i := text.find("[", i)) != -1:
        value, i = decoder.raw_decode(text, i)
        out.append(value)
    return out


@pytest.fixture
def data(tmp_path):
    folder = tmp_path / "linear-a"
    folder.mkdir()
    for name, content in [("lexicon", LEXICON), ("onomasticon", ONOMASTICON), ("corpus", CORPUS),
                          ("translations", TRANSLATIONS), ("unread_words", UNREAD)]:
        (folder / f"{name}.json").write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_word_searches_the_lexicon_and_the_onomasticon(data):
    done = run("--json", "word", "KU", data=data)
    assert done.returncode == 0, done.stderr
    lexicon, onomasticon = json_documents(done.stdout)
    assert [r["word"] for r in lexicon] == ["KU-RO"]
    assert [r["token"] for r in onomasticon] == ["KU-PA₃-NU"]


def test_raw_sql_runs_without_the_sql_command(data):
    done = run("SELECT count(*) AS n FROM lexicon WHERE confidence = 'PROBABLE'", "--json", data=data)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [{"n": 1}]


def test_inscription_shows_the_confidence_and_each_word(data):
    done = run("inscription", "ht13", data=data)
    assert done.returncode == 0, done.stderr
    assert "Confidence:  PROBABLE" in done.stdout
    assert "KA-U-DE-TA" in done.stdout and "→ a place name" in done.stdout and "→ total" in done.stdout


def test_unread_counts_each_verdict(data):
    done = run("unread", "--verdict", "all", data=data)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[0].startswith("no_reading 1 | not_readable 1 | not_a_word 0")


def test_a_view_whose_file_is_not_in_the_checkout_is_named(data):
    for query, dataset in [("SELECT * FROM signs", "sign_values.json"),
                           ("SELECT * FROM semitic_roots", "semitic_roots.json")]:
        done = run("sql", query, data=data)
        assert done.returncode == 2, (query, done.stdout, done.stderr)
        assert f"{dataset} is not in this checkout" in done.stderr, done.stderr


def test_a_missing_lexicon_is_named(tmp_path):
    done = run("word", "KU", data=tmp_path)
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert "lexicon.json is not in this checkout" in done.stderr


@pytest.mark.data
def test_lq_reads_the_shipped_lexicon():
    entries = json.loads((ROOT / "data" / "linear-a" / "lexicon.json").read_text(encoding="utf-8"))["entries"]
    done = run("--json", "sql", "SELECT count(*) AS n FROM lexicon")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [{"n": len(entries)}]


@pytest.mark.data
def test_lq_reads_one_row_per_shipped_root():
    roots = json.loads((ROOT / "data" / "semitic-roots" / "semitic_roots.json").read_text(encoding="utf-8"))["roots"]
    done = run("--json", "sql", "SELECT count(*) AS n, count(DISTINCT id) AS ids FROM semitic_roots")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [{"n": len(roots), "ids": len(roots)}]
