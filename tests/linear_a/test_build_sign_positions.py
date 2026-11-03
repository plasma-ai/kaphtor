"""tools/linear_a/build_sign_positions.py: one row per sign position, keyed doc/i/j.

Every input is inline or written under tmp_path; main() runs with --out and --backups in tmp_path, so nothing reads
or writes data/ or the user cache.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.sign_crosswalk import Crosswalk
from tools.linear_a import build_sign_positions as bsp
from tools.linear_a.build_sign_positions import (
    assign_glyphs,
    attach_sigla,
    changed_keys,
    match_class,
    record_rows,
    report,
    sigla_positions,
    split_signs,
)

D = "\U0001076B"          # 𐝫
NA, SI, JA, A, KI, TE, NE, WA = ("\U00010605", "\U00010624", "\U00010631", "\U00010607", "\U00010641",
                                 "\U00010603", "\U00010617", "\U00010637")
REGISTRY = [
    {"ab_number": "AB06", "name": "na", "unicode_glyph": NA},
    {"ab_number": "AB41", "name": "si", "unicode_glyph": SI},
    {"ab_number": "AB57", "name": "ja", "unicode_glyph": JA},
    {"ab_number": "AB08", "name": "a", "unicode_glyph": A},
    {"ab_number": "AB67", "name": "ki", "unicode_glyph": KI},
    {"ab_number": "AB04", "name": "te", "unicode_glyph": TE},
    {"ab_number": "AB24", "name": "ne", "unicode_glyph": NE},
    {"ab_number": "AB54", "name": "wa", "unicode_glyph": WA},
    {"ab_number": "A402VAS", "name": "vessel ideogram (VAS series)", "unicode_glyph": None},
    {"ab_number": "AB120", "name": "GRA", "unicode_glyph": None},
    {"ab_number": "AB100", "name": "VIR", "unicode_glyph": None},
    {"ab_number": "AB131", "name": "VIN", "unicode_glyph": None},
    {"ab_number": "AB131A", "name": "VIN", "unicode_glyph": None},
    {"ab_number": "A709", "name": "L", "unicode_glyph": None},
    {"ab_number": "A709-2", "name": "L2", "unicode_glyph": None},
]


@pytest.fixture
def cw():
    return Crosswalk(REGISTRY, [], overrides={})


def _labels(token):
    return [(s["j"], s["label"]) for s in split_signs(token)]


# -- split_signs: j follows positional's _bare(token).split("-") ---------------------------

def test_plain_word():
    assert _labels("KA-U-DE-TA") == [(0, "KA"), (1, "U"), (2, "DE"), (3, "TA")]


def test_vessel_takes_the_number_index_and_skips_the_vs_slot():
    assert _labels("*402-VS-QA-PA₃") == [(0, "*402-VS"), (2, "QA"), (3, "PA₃")]


def test_break_segment_keeps_its_slot_and_marks_the_neighbour():
    signs = split_signs("]-NE")
    assert [(s["j"], s["label"]) for s in signs] == [(1, "NE")]
    assert signs[0]["beside_break"] and not signs[0]["lost"]


def test_trailing_break_marks_the_last_sign():
    signs = split_signs("A-TA-I-*301-WA-[")
    assert signs[-1]["label"] == "WA" and signs[-1]["beside_break"]


def test_bracket_inside_a_segment_is_beside_break_not_damage():
    signs = split_signs("]NA-SI")
    assert signs[0]["beside_break"] and not signs[0]["restored"]


def test_restored_signs_inside_brackets():
    signs = split_signs("[U-NA-KA-NA]-SI")
    assert [s["restored"] for s in signs] == [True, True, True, True, False]


def test_token_opening_inside_a_break():
    signs = split_signs("KA]-NA")
    assert signs[0]["restored"] and not signs[1]["restored"]


def test_lost_sign_is_one_sign_but_ellipsis_is_a_break():
    assert [s["lost"] for s in split_signs("A-[?]-JU")] == [False, True, False]
    assert _labels("A-[…]-JU") == [(0, "A"), (2, "JU")]


def test_attached_ellipsis_is_stripped_and_marks_a_break():
    signs = split_signs("SI…-NA")
    assert signs[0]["label"] == "SI" and signs[0]["beside_break"]


def test_erased_token_strips_double_brackets():
    signs = split_signs("[[TE]]")
    assert signs[0]["label"] == "TE" and not signs[0]["restored"]


def test_underdot_marks_dotted():
    assert split_signs("*301̣")[0]["dotted"]


# -- assign_glyphs ---------------------------------------------------------------

def test_aligned_glyphs():
    assert [g["glyph"] for g in assign_glyphs(split_signs("NA-SI"), NA + SI)] == [NA, SI]


def test_lost_sign_consumes_a_damage_mark():
    out = assign_glyphs(split_signs("A-[?]-JA"), A + D + JA)
    assert [g["glyph"] for g in out] == [A, None, JA]


def test_damage_beside_a_glyph_is_beside_break():
    out = assign_glyphs(split_signs("JA"), D + JA + D)
    assert out[0]["glyph"] == JA and out[0]["beside_break"]


def test_break_segment_does_not_eat_the_neighbours_glyph():
    out = assign_glyphs(split_signs("]-NE"), D + NE)
    assert out[0]["glyph"] == NE and out[0]["beside_break"]


def test_mismatch_assigns_no_glyph_at_all():
    assert [g["glyph"] for g in assign_glyphs(split_signs("NA-SI-KI"), NA + SI)] == [None, None, None]


# -- record_rows ---------------------------------------------------------------

RECORD = {
    "transliteratedWords": ["]NA-SI", "\U00010101", "GRA", "5", "\n", "A-[?]-KI", "[[TE]]", D, "]-NE", "3000"],
    "words": [D + NA + SI, "\U00010101", "\U00010648", "5", "\n", A + D + KI, TE, D, D + NE, "3000"],
}


@pytest.fixture
def rows(cw):
    return {r["key"]: r for r in record_rows("X1", RECORD, cw)}


def test_keys(rows):
    assert list(rows) == ["X1/0/0", "X1/0/1", "X1/1/0", "X1/2/0", "X1/3/0", "X1/5/0", "X1/5/1", "X1/5/2",
                          "X1/6/0", "X1/7/0", "X1/8/1", "X1/9/0"]


def test_kinds_damage_and_marks(rows):
    assert rows["X1/0/0"]["codes"] == ["AB06"] and rows["X1/0/0"]["damage"] == "none"
    assert "beside_break" in rows["X1/0/0"]["marks"]
    assert rows["X1/1/0"]["kind"] == "divider"
    assert rows["X1/2/0"]["codes"] == ["AB120"]
    assert rows["X1/5/1"]["kind"] == "lacuna" and rows["X1/5/1"]["damage"] == "lost"
    assert rows["X1/6/0"]["erased"] is True and "erased" in rows["X1/6/0"]["marks"]
    assert rows["X1/7/0"]["kind"] == "break"
    assert rows["X1/8/1"]["label"] == "NE" and rows["X1/8/1"]["glyph"] == NE


def test_numerals_carry_thousands_and_strokes(rows):
    assert rows["X1/3/0"]["numeral"] == {"value": 5, "thousands": 0, "hundreds": 0, "tens": 0, "units": 5,
                                         "strokes": 5}
    assert rows["X1/9/0"]["numeral"]["thousands"] == 3 and rows["X1/9/0"]["numeral"]["hundreds"] == 0


def test_entry_line(rows):
    assert rows["X1/0/0"]["entry_line"] == 1 and rows["X1/5/0"]["entry_line"] == 2


def test_partly_bracketed_numeral_is_beside_break_not_restored(cw):
    by = {r["key"]: r for r in record_rows("N", {"transliteratedWords": ["3[", "[20]"], "words": ["3", "20"]}, cw)}
    assert by["N/0/0"]["damage"] == "none" and "beside_break" in by["N/0/0"]["marks"]
    assert by["N/1/0"]["damage"] == "restored"


def test_ligature_with_lost_component_is_partial(cw):
    r = record_rows("L", {"transliteratedWords": ["VIR+[?]"], "words": [""]}, cw)[0]
    assert r["kind"] == "ligature" and r["codes"] == ["AB100", "?"] and r["damage"] == "partial"


def test_unresolved_component_is_not_partial(cw):
    r = record_rows("U", {"transliteratedWords": ["ZZZ+TE"], "words": [""]}, cw)[0]
    assert r["kind"] == "ligature" and r["damage"] == "none"


def test_restored_sign_gets_no_beside_break_from_the_glyph(cw):
    r = record_rows("R", {"transliteratedWords": ["[NA]"], "words": [D + NA]}, cw)[0]
    assert r["damage"] == "restored" and "beside_break" not in r["marks"]


def test_all_klasma_ligature_is_a_fraction():
    reg = REGISTRY + [{"ab_number": "A707", "name": "J", "unicode_glyph": None}]
    r = record_rows("J", {"transliteratedWords": ["J+L2"], "words": [""]}, Crosswalk(reg, [], {}))[0]
    assert r["kind"] == "fraction" and r["codes"] == ["A707", "A709-2"]


def test_fraction_branch(cw):
    r = record_rows("F", {"transliteratedWords": ["¹⁄₂"], "words": [""]}, cw)[0]
    assert r["kind"] == "fraction" and r["fraction_value"] == "1/2"


def test_sign_like_token_with_no_sign_is_a_break_row(cw):
    r = record_rows("H", {"transliteratedWords": ["-"], "words": [""]}, cw)
    assert [(x["key"], x["kind"]) for x in r] == [("H/0/0", "break")]


# -- attach_sigla ---------------------------------------------------------------

def _row(key, kind, codes, **extra):
    return {"key": key, "kind": kind, "codes": codes, "label": "x", "erased": False, **extra}


def _sp(pos, code, **extra):
    return {"doc": "d", "pos": pos, "code": code, "read": code is not None, "certain": True,
            "erased": False, "hidden": False, **extra}


def test_alignment_classes(cw):
    rows = record_rows("X1", RECORD, cw)
    sigla = [_sp(1, "AB06"), _sp(2, "AB41"), _sp(3, "AB120"), _sp(4, "AB08"), _sp(5, None), _sp(6, "AB04"),
             _sp(7, "AB04", erased=True), _sp(8, "AB24")]
    stats = attach_sigla(rows, sigla)
    by = {r["key"]: r for r in rows}
    assert by["X1/0/0"]["sigla"][0]["match"] == "equal"
    assert by["X1/5/1"]["sigla"][0]["match"] == "both_lost"
    assert by["X1/5/2"]["sigla"][0]["match"] == "substitution"
    assert by["X1/6/0"]["sigla"][0]["pos"] == 7 and by["X1/6/0"]["sigla"][0]["match"] == "equal"
    assert "sigla" not in by["X1/3/0"] and "sigla" not in by["X1/7/0"]   # numerals and breaks never align
    assert stats["equal"] == 6 and stats["both_lost"] == 1 and stats["substitution"] == 1


def test_variant_lacuna_and_distinct_klasma():
    rows = [_row("d/0/0", "sign", ["AB131A"]), _row("d/1/0", "lacuna", []), _row("d/2/0", "fraction", ["A709-2"])]
    attach_sigla(rows, [_sp(1, "AB131"), _sp(2, "AB24"), _sp(3, "A709")])
    assert [r["sigla"][0]["match"] for r in rows] == ["variant", "lacuna", "substitution"]


def test_lettered_syllabogram_is_not_a_variant():
    rows = [_row("d/0/0", "sign", ["AB28B"])]
    attach_sigla(rows, [_sp(1, "AB28")], distinct_letters=frozenset({"AB28B"}))
    assert rows[0]["sigla"][0]["match"] == "substitution"


def test_unresolved_on_either_side_is_open():
    rows = [_row("d/0/0", "unresolved", [], label="*809"), _row("d/1/0", "sign", ["AB24"])]
    stats = attach_sigla(rows, [_sp(1, None, read=True, unresolved="N800"), _sp(2, "AB24")])
    assert rows[0]["sigla"][0]["match"] == "open" and stats["open"] == 1


def test_erased_sigla_trace_is_skipped_cheaply():
    rows = [_row("d/0/0", "sign", ["AB24"]), _row("d/1/0", "sign", ["AB67"])]
    stats = attach_sigla(rows, [_sp(1, "AB24"), _sp(2, "AB04", erased=True), _sp(3, "AB67")])
    assert stats["equal"] == 2 and stats["sigla_unpaired"] == 1


def test_ligature_with_lost_component_against_its_surviving_part_is_partial():
    rows = [_row("d/0/0", "ligature", ["AB100", "?"]), _row("d/1/0", "ligature", ["AB302", "?"])]
    stats = attach_sigla(rows, [_sp(1, "AB100"), _sp(2, "A618")])
    assert [r["sigla"][0]["match"] for r in rows] == ["partial", "substitution"]
    assert stats["partial"] == 1


def test_lost_sign_against_erased_unread_trace_is_both_lost():
    rows = [_row("d/0/0", "lacuna", [])]
    attach_sigla(rows, [_sp(1, None, erased=True)])
    assert rows[0]["sigla"][0]["match"] == "both_lost"


def test_ambiguous_row_matching_an_alternative():
    rows = [_row("d/0/0", "sign", ["A559"], ambiguous=True, alternatives=[["A559"], ["A561"]])]
    stats = attach_sigla(rows, [_sp(1, "A561")])
    assert rows[0]["sigla"][0]["match"] == "alternative" and stats["alternative"] == 1


def test_live_sign_against_erased_trace_of_the_same_sign_is_erasure():
    rows = [_row("d/0/0", "sign", ["AB24"])]
    attach_sigla(rows, [_sp(1, "AB24", erased=True)])
    assert rows[0]["sigla"][0]["match"] == "erasure"


def test_live_sign_is_not_forced_onto_a_different_erased_trace():
    rows = [_row("d/0/0", "sign", ["AB24"])]
    stats = attach_sigla(rows, [_sp(1, "AB04", erased=True)])
    assert "sigla" not in rows[0] and stats["corpus_unpaired"] == 1 and stats["sigla_unpaired"] == 1


def test_fraction_compound_aligns_one_klasmatogram_per_position():
    rows = [_row("d/0/0", "sign", ["AB08"]), _row("d/1/0", "fraction", ["A707", "A704"])]
    stats = attach_sigla(rows, [_sp(1, "AB08"), _sp(2, "A707"), _sp(3, "A704")])
    assert stats["equal"] == 3 and [p["pos"] for p in rows[1]["sigla"]] == [2, 3]


COMPONENTS = {"A717": ("A703", "A703"), "A732": ("A707", "A704")}


@pytest.mark.parametrize("a, b, cls", [
    ("A717", "A703", "component"),          # DD against one D: a part of the composite
    ("A703", "A717", "component"),
    ("A732", "A707+A704", "component"),     # JE against J+E written apart
    ("A717", "A702", "substitution"),       # B is no part of DD
    ("A732", "A707+A701", "substitution"),  # one foreign part spoils it
])
def test_composite_against_its_parts_is_component(a, b, cls):
    assert match_class(a, b, components=COMPONENTS) == cls


def test_without_component_data_a_composite_is_a_substitution():
    assert match_class("A717", "A703") == "substitution"


def test_fraction_composite_aligns_part_by_part():
    # SigLA records JE as J and E in two positions; the corpus's single A732 glyph expands to meet them.
    rows = [_row("d/0/0", "sign", ["AB08"]), _row("d/1/0", "fraction", ["A732"])]
    stats = attach_sigla(rows, [_sp(1, "AB08"), _sp(2, "A707"), _sp(3, "A704")], components=COMPONENTS)
    assert stats["equal"] == 3 and stats["sigla_unpaired"] == 0
    assert [p["pos"] for p in rows[1]["sigla"]] == [2, 3]


def test_composite_stays_whole_where_sigla_writes_it_whole():
    rows = [_row("d/0/0", "fraction", ["A717"])]
    stats = attach_sigla(rows, [_sp(1, "A717")], components=COMPONENTS)
    assert stats["equal"] == 1 and stats["component"] == 0 and len(rows[0]["sigla"]) == 1


def test_sigla_composite_against_corpus_parts_is_component():
    rows = [_row("d/0/0", "sign", ["AB08"]), _row("d/1/0", "fraction", ["A703", "A703"])]
    stats = attach_sigla(rows, [_sp(1, "AB08"), _sp(2, "A717")], components=COMPONENTS)
    assert rows[1]["sigla"][0]["match"] == "component" and stats["component"] == 1


def test_fractions_left_out_when_sigla_has_none():
    rows = [_row("d/0/0", "sign", ["AB08"]), _row("d/1/0", "fraction", ["A707"])]
    stats = attach_sigla(rows, [_sp(1, "AB08")])
    assert stats["corpus_unpaired"] == 0 and "sigla" not in rows[1]


# -- sigla_positions ---------------------------------------------------------------

def _doc(sid, codes, **pos_extra):
    return {"sigla_id": sid, "positions": [
        {"position": i + 1, "read": c is not None, "certain": True, "erased": False, "hidden": False,
         "signs": [] if c is None else [c]} for i, c in enumerate(codes)]}


def test_sigla_positions_use_sign_id(cw):
    docs = [_doc("d", [{"code": "AB131", "variant": "a", "sign_id": "AB131A"}])]
    assert sigla_positions(docs, "d", cw)[0]["code"] == "AB131A"


def test_sigla_positions_join_order_and_fragment_dedupe(cw):
    docs = [_doc("HT Zd 156", [{"code": "AB08"}]), _doc("HT Zd 157", [{"code": "AB24"}]),
            _doc("HT Zd 157+156", [{"code": "AB67"}])]
    out = sigla_positions(docs[:2], "HTZd157+156", cw)
    assert [p["doc"] for p in out] == ["HT Zd 157", "HT Zd 156"]
    joined = sigla_positions([_doc("KH 79", [{"code": "AB08"}]), _doc("KH 79+89", [{"code": "AB24"}])], "KH79+89", cw)
    assert [p["doc"] for p in joined] == ["KH 79+89"]


def test_sigla_unresolved_code_is_kept(cw):
    out = sigla_positions([_doc("d", [{"code": "N800"}])], "d", cw)
    assert out[0]["code"] is None and out[0]["unresolved"] == "N800" and out[0]["read"]


# -- guards, report, main -------------------------------------------------------------

def test_changed_keys():
    old = {"a": ("T1", "KA"), "b": ("T2", "NA")}
    new = {"a": ("T1", "KA"), "b": ("T2", "SI"), "c": ("T3", "TE")}
    assert changed_keys(old, new) == ["b"]


def test_report_handles_empty_input():
    text = report([], {}, {"built": "t", "sources": {k: None for k in
                                                     ("corpus.json", "sigla_db.json", "sign-registry.json")}})
    assert "0 rows" in text


def test_report_disagreement_table_has_a_cell_per_column():
    rows = [_row("d/0/0", "sign", ["AB24"], token="x", token_class="word", damage="none", marks=[], glyph=None)]
    stats = attach_sigla(rows, [_sp(1, "AB67")])
    per_doc = {"d": {"rows": 1, "sigla_docs": 1, "align": stats, "unaligned": False, "sigla_unresolved": []}}
    text = report(rows, per_doc, {"built": "t", "sources": {}})
    table = text.split("### Records with the most disagreements")[1].strip().splitlines()
    header, row = table[0], table[2]
    assert header.count("|") == row.count("|") and row.startswith("| d |")


@pytest.fixture
def sandbox(tmp_path, monkeypatch, cw):
    corpus = {"X1": {"transliteratedWords": ["NA-SI"], "words": [NA + SI]}}
    data = tmp_path / "data"
    data.mkdir()
    (data / "corpus.json").write_text(json.dumps(corpus), encoding="utf-8")
    (data / "sigla_db.json").write_text(json.dumps({"documents": {}}), encoding="utf-8")
    (data / "sign-registry.json").write_text(json.dumps({"signs": REGISTRY}), encoding="utf-8")
    out_dir, backups = tmp_path / "cache", tmp_path / "backups"
    out_dir.mkdir()
    real = tmp_path / "real.jsonl"
    link = out_dir / "sign_positions.jsonl"
    monkeypatch.setattr(bsp, "CORPUS", data / "corpus.json")
    monkeypatch.setattr(bsp, "SIGLA_DB", data / "sigla_db.json")
    monkeypatch.setattr(bsp, "REGISTRY", data / "sign-registry.json")
    monkeypatch.setattr(bsp, "default_crosswalk", lambda: cw)
    monkeypatch.delenv("LASHON_HA_KRETAN_DIR", raising=False)
    args = ["--out", str(out_dir), "--backups", str(backups)]
    return {"data": data, "out_dir": out_dir, "out": link, "real": real, "corpus": corpus, "backups": backups,
            "args": args}


def test_dry_run_writes_nothing(sandbox):
    assert bsp.main(["--dry-run", *sandbox["args"]]) == 0
    assert not sandbox["out"].exists()


def test_write_then_rebuild_backs_up_and_keeps_a_symlink(sandbox):
    sandbox["real"].write_text("", encoding="utf-8")
    sandbox["out"].symlink_to(sandbox["real"])
    assert bsp.main(sandbox["args"]) == 0
    assert sandbox["out"].is_symlink()
    lines = sandbox["real"].read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["key"] for x in lines] == ["X1/0/0", "X1/0/1"]
    index = json.loads((sandbox["out_dir"] / "sign_positions.index.json").read_text())
    assert index["rows"] == 2 and index["sources"]["ideograms.js"] is None
    assert bsp.main(sandbox["args"]) == 0
    assert list(sandbox["backups"].glob("sign_positions.jsonl.bak-*")), "the rows file must be backed up"
    assert not list(sandbox["out_dir"].glob("*.bak-*")), "backups go to --backups, never beside the output"


def test_old_rows_file_with_blank_lines_reads(sandbox):
    assert bsp.main(sandbox["args"]) == 0
    text = sandbox["out"].read_text(encoding="utf-8")
    sandbox["out"].write_text(text + "\n\n", encoding="utf-8")
    assert bsp.main(["--dry-run", *sandbox["args"]]) == 0


def test_refuses_dropped_and_changed_keys(sandbox):
    assert bsp.main(sandbox["args"]) == 0
    sandbox["corpus"]["X1"] = {"transliteratedWords": ["NA"], "words": [NA]}
    (sandbox["data"] / "corpus.json").write_text(json.dumps(sandbox["corpus"]), encoding="utf-8")
    assert bsp.main(sandbox["args"]) == 2
    sandbox["corpus"]["X1"] = {"transliteratedWords": ["KI-SI"], "words": [KI + SI]}
    (sandbox["data"] / "corpus.json").write_text(json.dumps(sandbox["corpus"]), encoding="utf-8")
    assert bsp.main(sandbox["args"]) == 2
    assert bsp.main(["--allow-change", *sandbox["args"]]) == 0


def test_report_refuses_an_existing_path(sandbox, tmp_path):
    rep = tmp_path / "r.md"
    rep.write_text("keep", encoding="utf-8")
    assert bsp.main(["--dry-run", "--report", str(rep), *sandbox["args"]]) == 2
    assert rep.read_text(encoding="utf-8") == "keep"


def test_missing_input_stops_with_its_name(sandbox, capsys):
    (sandbox["data"] / "sigla_db.json").unlink()
    assert bsp.main(["--dry-run", *sandbox["args"]]) == 2
    assert "sigla_db.json" in capsys.readouterr().err


def test_default_output_is_the_cache_not_the_repository():
    from tools.paths import CACHE, REPO
    assert bsp.OUT_DIR == CACHE / "linear-a"
    assert REPO not in bsp.OUT_DIR.parents
