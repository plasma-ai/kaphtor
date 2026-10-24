"""cognate_search, analyze and context_search take a word's known reading from data/linear-a/lexicon.json.

The unit tests point KAPHTOR_DATA at a folder written inline, with the run cache in the test's own folder. The
cognate_search test reads the shipped data. No network.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "linear_a"
SCRIPTS = ("cognate_search.py", "analyze.py", "context_search.py")

CORPUS = {"HT1": {"site": "Haghia Triada", "transliteratedWords": ["KU-RO", "\n", "DA-RE", "10", "¹⁄₂"]},
          "HT2": {"site": "Haghia Triada", "transliteratedWords": ["KU-RO", "𐄁", "SA-RA₂", "\U0001076b", "TA"]}}
LEXICON = {"entries": [{"word": "KU-RO", "reading": "kullu", "meaning": "total", "confidence": "CONFIRMED",
                        "category": "vocabulary"}]}


def run(script: str, *args: str, data: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "KAPHTOR_DATA": str(data),
           "XDG_CACHE_HOME": str(data / "cache")}
    env.pop("LASHON_HA_KRETAN_DIR", None)
    return subprocess.run([sys.executable, str(TOOLS / script), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=300)


def fixture(tmp_path: Path) -> Path:
    folder = tmp_path / "linear-a"
    folder.mkdir()
    (folder / "corpus.json").write_text(json.dumps(CORPUS, ensure_ascii=False), encoding="utf-8")
    (folder / "lexicon.json").write_text(json.dumps(LEXICON, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_the_cognate_tools_read_no_gordon_lexicon():
    from tools.linear_a import analyze, cognate_search, context_search
    loaders = ("load_gordon", "load_scholarly")
    assert [(m.__name__, n) for m in (cognate_search, analyze, context_search) for n in loaders if hasattr(m, n)] == []
    assert [s for s in SCRIPTS if "gordon.json" in (TOOLS / s).read_text(encoding="utf-8")] == []


def test_a_lexicon_lookup_keeps_subscripts_and_a_logograms_lone_complement_apart():
    from tools.core.normalization import lookup_in
    lexicon = {"NA": "na", "SU-PU": "su-pu", "KU-RO": "ku-ro", "JA-SA-RA": "ja-sa-ra"}
    assert lookup_in(lexicon, "*301-NA") is None          # a logogram and its complement, not the word NA
    assert lookup_in(lexicon, "SU-PU₂") is None           # PU₂ is another sign
    assert lookup_in(lexicon, "*188-KU-RO") == "ku-ro"    # a sign group remains after the logogram
    assert lookup_in(lexicon, "YA-SA-RA") == "ja-sa-ra"
    assert lookup_in(lexicon, "𐄁") is None


def test_dividers_numerals_fractions_and_damage_marks_are_not_words():
    from tools.core.normalization import is_word
    assert [t for t in ("KU-RO", "TA", "*301", "CYP+D", "]-NE", "\n", "𐄁", "10", "¹⁄₂", "\U0001076b", "")
            if is_word(t)] == ["KU-RO", "TA", "*301", "CYP+D", "]-NE"]


def test_context_search_annotates_from_the_lexicon(tmp_path):
    done = run("context_search.py", "KU-RO", "--kind", "word", "--json", data=fixture(tmp_path))
    assert done.returncode == 0, done.stderr
    words = {w["word"]: w for t in json.loads(done.stdout)["tablets"] for w in t["words"]}
    assert (words["KU-RO"]["source"], words["KU-RO"]["reading"]) == ("lexicon", "kullu")
    assert words["DA-RE"]["source"] is None


def test_analyze_counts_words_only_and_knows_a_word_by_its_lexicon_entry(tmp_path):
    data = fixture(tmp_path)
    single = run("analyze.py", "single", "HT1", "--format", "json", data=data)
    assert single.returncode == 0, single.stderr
    result = json.loads(single.stdout)
    assert [w["word"] for w in result["words"]] == ["KU-RO", "DA-RE"]
    assert result["words"][0]["matches"][0] == {"method": "lexicon", "reading": "kullu", "meaning": "total",
                                                "confidence": "CONFIRMED"}
    promising = run("analyze.py", "batch", "--mode", "promising", "--format", "json", data=data)
    assert promising.returncode == 0, promising.stderr
    assert {r["name"]: r["total_words"] for r in json.loads(promising.stdout)} == {"HT1": 2, "HT2": 3}
    unknowns = run("analyze.py", "batch", "--mode", "unknowns", "--min-count", "1", "--format", "json", data=data)
    assert unknowns.returncode == 0, unknowns.stderr
    assert {row["word"] for row in json.loads(unknowns.stdout)} == {"DA-RE", "SA-RA₂", "TA"}


def test_a_reading_without_a_value_prints_no_empty_slot():
    from tools.linear_a.cognate_search import reading_text
    assert reading_text({"reading": "kull", "meaning": "total", "confidence": "CONFIRMED"}) == \
        'kull "total" (CONFIRMED)'
    assert reading_text({"meaning": "figs", "confidence": "PROBABLE"}) == '"figs" (PROBABLE)'


def test_cognate_search_gives_the_words_lexicon_reading_first():
    entry = next(e for e in json.loads((ROOT / "data/linear-a/lexicon.json").read_text(encoding="utf-8"))["entries"]
                 if e["word"] == "KU-RO")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    done = subprocess.run([sys.executable, str(TOOLS / "cognate_search.py"), "KU-RO", "--json", "--no-cache"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    first = json.loads(done.stdout)["matches"][0]
    assert (first["method"], first["root"], first["meaning"], first["distance"]) == \
        ("lexicon", entry["reading"], entry["meaning"], 0.0)


def test_root_match_names_a_missing_competitor_lexicon_and_the_way_round_it(tmp_path):
    (tmp_path / "linear-a").mkdir()
    done = run("root_match.py", "I-DA-MI", data=tmp_path)
    assert done.returncode == 2
    assert "Traceback" not in done.stderr and "--no-competitors" in done.stderr
