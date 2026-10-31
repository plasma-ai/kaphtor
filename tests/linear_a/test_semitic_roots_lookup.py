"""Tests for tools/linear_a/semitic_roots_lookup.py, the read-only check for whether a root is already in
semitic_roots.json. Every index is built in tmp_path from four made-up records; the command is called in-process and
must write nothing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from shoresh_inputs import SHORESH

from tools.core.root_index import write_index
from tools.linear_a import semitic_roots_lookup as cli

pytestmark = SHORESH

RECORDS = [
    {"Number": "3789", "Proto-Semitic": "*turs-", "Meaning": "'shield' 1, 'door-bar' 2",
     "Analogues": {"Arabic": "turs 'a shield' (Lane 302)"}},
    {"Number": "3614", "Proto-Semitic": "*trṣ", "Meaning": "'to be straight'", "Analogues": {}},
    {"Number": "1231", "Proto-Semitic": "*kurus-", "Meaning": "'belt'", "Analogues": {}},
    {"Number": "2240", "Proto-Semitic": "*labVʾ-", "Meaning": "'lion(ess)'", "Analogues": {}},
]


@pytest.fixture
def built(tmp_path) -> tuple[Path, Path]:
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(tmp_path / "x.sqlite", roots, lexica=())
    return roots, tmp_path / "x.sqlite"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestTiers:
    def test_the_root_itself_is_exact(self, built):
        _, index = built
        report, status = cli.run(index, ["t-r-s"], [])
        assert status == 0
        rows = report[0]["rows"]
        assert rows[0]["number"] == "3789" and rows[0]["tier"] == "exact" and rows[0]["distance"] == 0
        assert report[0]["keys"] == ["t-r-s"]

    def test_a_spelling_variant_is_same_class_and_ranked_by_distance(self, built):
        _, index = built
        rows = {r["number"]: r for r in cli.run(index, ["t-r-s"], [])[0][0]["rows"]}
        assert rows["3614"]["tier"] == "same class" and rows["3614"]["distance"] == 0.5
        assert "2240" not in rows       # l-b-ʾ shares no class with t-r-s

    def test_meaning_alone_lists_only_records_whose_meaning_has_the_word(self, built):
        _, index = built
        report, status = cli.run(index, [], ["lion"])
        assert status == 0 and report[0]["query"] is None
        assert [(r["number"], r["tier"], r["meaning_match"]) for r in report[0]["rows"]] == [("2240", "meaning", True)]


class TestCommand:
    def test_json_rows_carry_the_documented_fields(self, built, capsys):
        _, index = built
        assert cli.main(["t-r-s", "--json", "--index", str(index)]) == 0
        report = json.loads(capsys.readouterr().out)
        assert set(report[0]) == {"query", "keys", "shadows", "meaning", "rows"}
        row = report[0]["rows"][0]
        assert set(row) == {"number", "tier", "distance", "ps", "meaning", "meaning_match", "via"}
        assert set(row["via"][0]) == {"kind", "language", "form", "radicals"}

    def test_an_empty_query_exits_1(self, built, capsys):
        _, index = built
        assert cli.main(["", "--index", str(index)]) == 1
        assert "no radicals read" in capsys.readouterr().err

    def test_a_stale_index_exits_2(self, built, capsys):
        roots, index = built
        roots.write_text(json.dumps(RECORDS[:3], ensure_ascii=False), encoding="utf-8")
        assert cli.main(["t-r-s", "--index", str(index)]) == 2
        assert "root index unusable" in capsys.readouterr().err

    def test_a_missing_index_exits_2(self, tmp_path):
        assert cli.main(["t-r-s", "--index", str(tmp_path / "none.sqlite")]) == 2

    def test_writes_nothing(self, built):
        roots, index = built
        before = (_sha(roots), _sha(index), sorted(p.name for p in index.parent.iterdir()))
        cli.main(["t-r-s", "--meaning", "lion", "--index", str(index)])
        assert (_sha(roots), _sha(index), sorted(p.name for p in index.parent.iterdir())) == before
