"""tools/core/js_parser.parse_string_pairs: [key, value] string Maps such as lashon-ha-kretan's ideograms.js."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.js_parser import JSParseError, parse_string_pairs

SAMPLE = '''// lineara.xyz sign table
const ideogram_to_ascii = new Map([
["\U00010600","DA"],
["\U00010101","*900"], // word divider
/* block comment */
["\U00010600","DA2"],
["a\\"b","q"],
]);
const other = new Map([["x","y"]]);
'''


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ideograms.js"
    path.write_text(text, encoding="utf-8")
    return path


def test_pairs_in_file_order_with_duplicates_kept(tmp_path):
    pairs = parse_string_pairs(_write(tmp_path, SAMPLE), "ideogram_to_ascii")
    assert pairs == [
        ("\U00010600", "DA"),
        ("\U00010101", "*900"),
        ("\U00010600", "DA2"),
        ('a"b', "q"),
    ]


def test_selects_the_named_map_only(tmp_path):
    assert parse_string_pairs(_write(tmp_path, SAMPLE), "other") == [("x", "y")]


def test_missing_map_raises(tmp_path):
    with pytest.raises(JSParseError):
        parse_string_pairs(_write(tmp_path, SAMPLE), "absent")


def test_non_string_value_raises(tmp_path):
    with pytest.raises(JSParseError):
        parse_string_pairs(_write(tmp_path, 'const m = new Map([["k", {"a": 1}]]);'), "m")
