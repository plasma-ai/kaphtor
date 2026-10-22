"""`tools/views/census_doc.py`: the generated blocks of `docs/corpus-census.md`.

The census reference is prose with named blocks between `<!-- BEGIN kaphtor:census NAME -->` and
`<!-- END kaphtor:census NAME -->`; every number drawn from the data sits in a block. The tool checks by default
and writes only the blocks. The fixture is the census fixture of `test_views.py`; the live test reads
`data/linear-a/` and is skipped when the Linear A data is not in the checkout.
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from test_views import CLASSES, CORPUS, LIVE, snapshot

from tools.paths import LINEAR_A_DATA, REPO

DOC = REPO / "docs" / "corpus-census.md"


def census_doc():
    return importlib.import_module("tools.views.census_doc")


@pytest.fixture(autouse=True)
def backups(tmp_path: Path, monkeypatch) -> Path:
    """Every copy goes to the test's folder, never the user's state folder."""
    folder = tmp_path / "backups"
    monkeypatch.setattr(census_doc(), "BACKUPS", folder)
    return folder


@pytest.fixture
def data(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    for name, content in (("corpus.json", CORPUS), ("census_classes.json", CLASSES)):
        (folder / name).write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return folder


def skeleton(names, filled: dict | None = None) -> str:
    parts = ["# Census", "", "Prose someone wrote, 1,427 and all."]
    for name in names:
        parts += ["", f"<!-- BEGIN kaphtor:census {name} -->", *(filled or {}).get(name, ["stale"]),
                  f"<!-- END kaphtor:census {name} -->"]
    return "\n".join(parts) + "\n"


def test_a_missing_data_file_stops_with_its_name_and_no_traceback(data, tmp_path, capsys):
    (data / "census_classes.json").unlink()
    doc = tmp_path / "census.md"
    doc.write_text(skeleton(census_doc().BLOCKS), encoding="utf-8")
    assert census_doc().main(["--data", str(data), "--doc", str(doc)]) == 2
    assert "census_classes.json is not in this checkout" in capsys.readouterr().err


def test_check_reports_stale_blocks_and_writes_nothing(data, tmp_path):
    doc = tmp_path / "census.md"
    doc.write_text(skeleton(census_doc().BLOCKS), encoding="utf-8")
    before = snapshot(tmp_path)
    assert census_doc().main(["--data", str(data), "--doc", str(doc)]) == 1
    assert snapshot(tmp_path) == before


def test_write_fills_only_the_blocks_then_checks_current(data, tmp_path):
    doc = tmp_path / "census.md"
    doc.write_text(skeleton(census_doc().BLOCKS), encoding="utf-8")
    original = doc.read_text(encoding="utf-8")
    backups = tmp_path / "bk"
    assert census_doc().main(["--data", str(data), "--doc", str(doc), "--write", "--backups", str(backups)]) == 0
    text = doc.read_text(encoding="utf-8")
    assert text.startswith("# Census\n\nProse someone wrote, 1,427 and all.\n")
    assert "stale" not in text
    assert census_doc().main(["--data", str(data), "--doc", str(doc)]) == 0
    [saved] = backups.glob("*")
    assert saved.read_text(encoding="utf-8") == original


def test_write_copies_to_the_backups_folder_by_default(data, tmp_path, backups):
    doc = tmp_path / "census.md"
    doc.write_text(skeleton(census_doc().BLOCKS), encoding="utf-8")
    assert census_doc().main(["--data", str(data), "--doc", str(doc), "--write"]) == 0
    assert [p.name.startswith("census-") for p in backups.glob("*")] == [True]


def test_the_class_block_gives_every_class_and_the_total(data):
    lines = census_doc().blocks(json.loads((data / "corpus.json").read_text(encoding="utf-8")), CLASSES)["classes"]
    text = "\n".join(lines)
    assert "| GORILA, labelled | 5 |" in text and "| unresolved | 1 |" in text
    assert "| **Total** | **13** |" in text


def test_the_gorila_check_must_sum_to_gorila_v(data):
    corpus = json.loads((data / "corpus.json").read_text(encoding="utf-8"))
    assert "| **Total** | **6** |" in "\n".join(census_doc().blocks(corpus, CLASSES)["gorila-check"])
    broken = {**CLASSES, "gorila_v": {**CLASSES["gorila_v"], "documents": 7}}
    with pytest.raises(ValueError, match="gives 6, not 7"):
        census_doc().blocks(corpus, broken)


def test_a_doc_missing_a_block_or_naming_an_unknown_one_is_refused(data, tmp_path):
    doc = tmp_path / "census.md"
    names = list(census_doc().BLOCKS)
    for text in (skeleton(names[1:]), skeleton([*names, "no-such-block"])):
        doc.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError):
            census_doc().main(["--data", str(data), "--doc", str(doc), "--write"])


@LIVE
def test_live_doc_is_current_and_its_data_counts_sit_in_blocks():
    assert census_doc().main(["--data", str(LINEAR_A_DATA), "--doc", str(DOC)]) == 0
    text = DOC.read_text(encoding="utf-8")
    outside = re.sub(r"<!-- BEGIN kaphtor:census (\S+) -->.*?<!-- END kaphtor:census \1 -->", "", text, flags=re.DOTALL)
    for number in ("1,719", "1,603", "1,370", "1,376"):
        assert number not in outside, number


def test_the_doc_carries_no_model_name_or_private_path():
    text = DOC.read_text(encoding="utf-8")
    for trace in ("Claude", "Opus", "src_", "artifacts/", "~/", "document_count.py", "rila_s1_match.py",
                  "census_classes.py", "gorila_v_check.py", "The scan"):
        assert trace not in text, trace
    # The frontmatter's `updated:` timestamp is the wiki tool's; a dated status line in the prose is a trace.
    body = text.split("\n---\n", 1)[1]
    assert "updated:" not in body
