"""The shared counts behind the counts page, the index summary and the README badges (`tools/views/counts.py`), and
`tools/views/stats.py`, which writes them to `data/linear-a/stats.json` for sites outside the repository.

The counts fixtures are inline. The stats fixture is the data fixture of `test_views.py` with each count of a block
made distinct from the others (three more lexicon entries, a third complete translation, and sign lists of 2, 3, 7 and
11 values), so a swapped or misread count fails, and a `semitic-roots/` folder of three roots beside it; the tool
checks by default and writes only `stats.json`. The live test reads `data/linear-a/` and the root database, and is
skipped, as the README badge test is, when they are not in the checkout.
"""
from __future__ import annotations

import copy
import importlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_readme_counts import LIVE_FILES, computed
from test_views import FILES, snapshot

from tools.paths import LINEAR_A_DATA, REPO, SEMITIC_ROOTS_DATA
from tools.views import counts

SUMMARY = {"total": 5, "phonemic_count": 2, "logogram_count": 3, "fraction_count": 1,
           "proposed": {"phonemic_count": 7, "logogram_count": 11, "fraction_count": 4}}
EXPECTED = {
    "schema_version": 1,
    "description": "Headline counts of the Linear A record, computed from the data files.",
    "corpus": {"records": 16, "documents": 13},
    "lexicon": {"entries": 6, "tiers": {"CONFIRMED": 0, "PROBABLE": 1, "CANDIDATE": 2, "SPECULATIVE": 3}},
    "translations": {"complete": 3, "incomplete": 2},
    "sign_values": {"total": 23, "resolved": 5, "phonemic": 9, "logographic": 14},
    "names": 1,
    "semitic_roots": 3,
}
# A README badge (test_readme_counts.computed) -> the key of stats.json that holds the same count.
BADGE_KEYS = {"corpus": "corpus.records", "translations": "translations.complete", "lexicon": "lexicon.entries",
              "names": "names", "Semitic roots": "semitic_roots", "sign values": "sign_values.total"}


def stats():
    return importlib.import_module("tools.views.stats")


def test_the_tiers_count_each_confidence_label():
    entries = [{"confidence": "CONFIRMED"}, {"confidence": "CANDIDATE"}, {"confidence": "CANDIDATE"}]
    assert counts.lexicon_tiers(entries) == {"CONFIRMED": 1, "CANDIDATE": 2}


def test_the_sign_values_count_resolved_and_proposed_values_and_leave_the_fractions_out():
    assert counts.sign_value_counts(SUMMARY) == {"total": 23, "resolved": 5, "phonemic": 9, "logographic": 14}


@pytest.fixture(autouse=True)
def backups(tmp_path: Path, monkeypatch) -> Path:
    """Every copy goes to the test's folder, never the user's state folder."""
    folder = tmp_path / "backups"
    monkeypatch.setattr(stats(), "BACKUPS", folder)
    return folder


def stats_files() -> dict:
    """FILES with the counts of each block distinct: the tiers 0, 1, 2 and 3 (three SPECULATIVE entries added),
    3 complete translations and 2 incomplete (KNZg57 added), and the sign values resolved 2 + 3 and proposed 7 + 11,
    each counter the length of its list."""
    files = copy.deepcopy(FILES)
    files["lexicon.json"]["entries"] += [{"word": f"SPEC-{i}", "confidence": "SPECULATIVE"} for i in range(3)]
    files["translations.json"]["translations"]["KNZg57"] = {"translation": "A jar.", "site": "Knossos", "notes": "",
                                                            "words": []}
    summary = files["sign_values.json"]["resolution_summary"]
    summary.update(phonemic=[f"P{i}=p{i}" for i in range(2)], logograms=[f"L{i}=l{i}" for i in range(3)],
                   total=5, phonemic_count=2, logogram_count=3)
    summary["proposed"].update(phonemic=[{"entry": f"PP{i}=pp{i}"} for i in range(7)],
                               logograms=[{"entry": f"PL{i}=pl{i}"} for i in range(11)],
                               phonemic_count=7, logogram_count=11)
    return files


def write_data(tmp_path: Path, files: dict) -> Path:
    folder = tmp_path / "linear-a"
    folder.mkdir()
    for name, content in files.items():
        (folder / name).write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    roots = tmp_path / "semitic-roots"
    roots.mkdir()
    (roots / "semitic_roots.json").write_text(json.dumps({"roots": [{}, {}, {}]}), encoding="utf-8")
    return folder


@pytest.fixture
def data(tmp_path: Path) -> Path:
    return write_data(tmp_path, stats_files())


def test_the_counts_hold_every_key_of_schema_1_with_the_data_s_values(data):
    assert stats().compute(data) == EXPECTED


@pytest.mark.data
@pytest.mark.skipif(not all((LINEAR_A_DATA / name).exists() for name in LIVE_FILES)
                    or not (SEMITIC_ROOTS_DATA / "semitic_roots.json").exists(),
                    reason="the Linear A data or the root database is not in this checkout")
def test_the_live_counts_agree_with_the_readme_badges_own_computation():
    flat = stats().flatten(stats().compute(LINEAR_A_DATA))
    assert {badge: flat[key] for badge, key in BADGE_KEYS.items()} == computed()


def test_a_confidence_outside_the_four_tiers_is_refused(tmp_path):
    files = stats_files()
    files["lexicon.json"]["entries"][0]["confidence"] = "REJECTED"
    with pytest.raises(ValueError, match="REJECTED"):
        stats().compute(write_data(tmp_path, files))


def test_a_resolved_total_that_is_not_its_phonemic_values_and_logograms_is_refused(tmp_path):
    files = stats_files()
    files["sign_values.json"]["resolution_summary"]["total"] += 1
    with pytest.raises(ValueError, match="resolved"):
        stats().compute(write_data(tmp_path, files))


@pytest.mark.parametrize("block, counter", [
    ("resolution_summary", "phonemic_count"), ("resolution_summary", "logogram_count"),
    ("resolution_summary.proposed", "phonemic_count"), ("resolution_summary.proposed", "logogram_count"),
])
def test_a_sign_counter_that_is_not_the_length_of_its_list_is_refused_naming_its_block(tmp_path, block, counter):
    files = stats_files()
    summary = files["sign_values.json"]["resolution_summary"]
    (summary["proposed"] if block.endswith(".proposed") else summary)[counter] += 1
    summary["total"] = summary["phonemic_count"] + summary["logogram_count"]  # the total holds; only a list is short
    with pytest.raises(ValueError, match=re.escape(f"{block}: {counter}")):
        stats().compute(write_data(tmp_path, files))


def test_a_missing_data_file_stops_with_its_name_and_no_traceback(data, capsys):
    (data / "onomasticon.json").unlink()
    assert stats().main(["--data", str(data)]) == 2
    assert "onomasticon.json is not in this checkout" in capsys.readouterr().err


def test_a_missing_root_database_stops_with_its_name_and_no_traceback(data, tmp_path, capsys):
    (tmp_path / "semitic-roots" / "semitic_roots.json").unlink()
    assert stats().main(["--data", str(data)]) == 2
    assert "semitic_roots.json is not in this checkout" in capsys.readouterr().err


def _not_json(path: Path) -> None:
    path.write_text("{not json", encoding="utf-8")


def _sign_values_without_proposed(data: Path) -> None:
    sign_values = stats_files()["sign_values.json"]
    del sign_values["resolution_summary"]["proposed"]
    (data / "sign_values.json").write_text(json.dumps(sign_values, ensure_ascii=False), encoding="utf-8")


def _a_rejected_entry(data: Path) -> None:
    lexicon = stats_files()["lexicon.json"]
    lexicon["entries"][0]["confidence"] = "REJECTED"
    (data / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize("damage, named", [
    (lambda data: _not_json(data / "lexicon.json"), "lexicon.json: "),
    (lambda data: _not_json(data.parent / "semitic-roots" / "semitic_roots.json"), "semitic_roots.json: "),
    (_sign_values_without_proposed, "'proposed'"),
    (_a_rejected_entry, "lexicon.json: "),
], ids=["data file not JSON", "root database not JSON", "missing key", "refused tier"])
def test_data_that_cannot_be_counted_stops_with_exit_2_naming_the_file_or_the_cause(data, capsys, damage, named):
    damage(data)
    assert stats().main(["--data", str(data)]) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("stopped: ") and named in captured.err and not captured.out


def test_data_given_as_the_current_folder_finds_the_roots_beside_it(data, monkeypatch):
    monkeypatch.chdir(data)
    assert stats().main(["--data", ".", "--write"]) == 0
    assert stats().main(["--data", "."]) == 0


def test_check_reports_a_file_that_is_not_json_as_stale_whole(data, capsys):
    (data / "stats.json").write_text("{not json", encoding="utf-8")
    assert stats().main(["--data", str(data)]) == 1
    assert "the whole file (not JSON)" in capsys.readouterr().out


def test_check_reports_a_missing_file_and_writes_nothing(data, tmp_path, capsys):
    before = snapshot(tmp_path)
    assert stats().main(["--data", str(data)]) == 1
    assert snapshot(tmp_path) == before
    assert "stats.json: stale: the whole file (missing)" in capsys.readouterr().out


def test_check_names_a_difference_of_formatting_only(data, capsys):
    (data / "stats.json").write_text(json.dumps(EXPECTED), encoding="utf-8")
    assert stats().main(["--data", str(data)]) == 1
    assert "stats.json: stale: formatting only" in capsys.readouterr().out


def test_the_fix_command_names_the_data_folder_from_the_repository_root():
    assert stats().fix_command(REPO / "data" / "linear-a") == "python -m tools.views.stats --data data/linear-a --write"


def test_write_makes_the_file_and_check_then_finds_it_current(data):
    assert stats().main(["--data", str(data), "--write"]) == 0
    text = (data / "stats.json").read_text(encoding="utf-8")
    assert json.loads(text) == EXPECTED and text.endswith("}\n")
    assert stats().main(["--data", str(data)]) == 0


def test_check_names_each_stale_count_and_the_fix_and_write_copies_the_old_file_first(data, tmp_path, capsys):
    stale = copy.deepcopy(EXPECTED)
    stale["lexicon"]["entries"], stale["semitic_roots"] = 2, 9
    (data / "stats.json").write_text(json.dumps(stale), encoding="utf-8")
    assert stats().main(["--data", str(data)]) == 1
    out = capsys.readouterr().out
    assert "lexicon.entries" in out and "semitic_roots" in out and "corpus.records" not in out
    assert f"python -m tools.views.stats --data {data.resolve()} --write" in out
    backups = tmp_path / "bk"
    assert stats().main(["--data", str(data), "--write", "--backups", str(backups)]) == 0
    assert json.loads((data / "stats.json").read_text(encoding="utf-8")) == EXPECTED
    [saved] = backups.iterdir()
    assert json.loads(saved.read_text(encoding="utf-8")) == stale


def test_two_writes_in_one_second_keep_both_old_files(data, tmp_path):
    backups = tmp_path / "bk"
    for entries in (2, 4):
        stale = copy.deepcopy(EXPECTED)
        stale["lexicon"]["entries"] = entries
        (data / "stats.json").write_text(json.dumps(stale), encoding="utf-8")
        assert stats().main(["--data", str(data), "--write", "--backups", str(backups)]) == 0
    assert sorted(json.loads(p.read_text(encoding="utf-8"))["lexicon"]["entries"] for p in backups.iterdir()) == [2, 4]


def test_print_shows_the_counts_and_touches_no_file(data, tmp_path, capsys):
    before = snapshot(tmp_path)
    assert stats().main(["--data", str(data), "--print"]) == 0
    assert json.loads(capsys.readouterr().out) == EXPECTED
    assert snapshot(tmp_path) == before
