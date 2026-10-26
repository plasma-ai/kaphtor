"""Tests for tools/core/root_index.py and tools/linear_a/build_root_index.py. Every index is built in tmp_path; the
shipped data is only ever read."""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from shoresh_inputs import SHORESH

import tools.core.root_index as ri
import tools.core.root_match as rm
from tools.core.root_index import (
    DEFAULT_ROOTS,
    LEXICA,
    IndexStale,
    RootIndex,
    branch_of,
    deletion_neighbours,
    diff_index,
    iter_lexemes,
    record_key_gaps,
    record_keys,
    shadow_key,
    stale_inputs,
    write_index,
)
from tools.linear_a import build_root_index

pytestmark = SHORESH

RECORDS = [
    {"Number": "1", "Proto-Semitic": "*ʾab-", "Meaning": "'father'",
     "Analogues": {"Hebrew": "ʔāb id. (HALOT, 1)", "Akkadian": "abu 'father' (CAD A1, 67)"}},
    {"Number": "2", "Proto-Semitic": "*kanVs-", "Meaning": "'to gather'",
     "Analogues": {"Hebrew": "knš 'gather'", "Moabite": "kns", "Egyptian": "kns (Wb.)"}},
    {"Number": "3", "Proto-Semitic": "*mVlk-", "Meaning": "'king'", "Analogues": {"Ugaritic": "mlk id."},
     "Notes": "first note"},
]


def _write_roots(path: Path, records: list[dict]) -> Path:
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def built(tmp_path):
    roots = _write_roots(tmp_path / "semitic_roots.json", RECORDS)
    out = tmp_path / "root_index.sqlite"
    write_index(out, roots, lexica=())
    return roots, out


# --- shadow keys ---

class TestShadowKey:
    def test_classes_merge_what_linear_a_merges(self):
        assert shadow_key(("k", "n", "s"))[0] == "KNS"
        assert shadow_key(("q", "n", "š"))[0] == "KNS"
        assert shadow_key(("g", "l", "d"))[0] == shadow_key(("k", "r", "ṭ"))[0] == "KRT"
        assert shadow_key(("b", "f", "p"))[0] == "PPP"

    def test_gutturals_are_optional_slots(self):
        assert shadow_key(("ʾ", "b"))[0] == "P"
        assert shadow_key(("ʿ", "ḥ", "ḫ", "h", "ġ"))[0] == ""

    def test_marked_letters_take_their_base_class(self):
        assert shadow_key(("ḇ", "ḵ", "p̄"))[0] == "PKP"     # spirantised begadkefat
        assert shadow_key(("s̃", "ẓ̂"))[0] == "SS"  # MSA laterals in SED notation

    def test_unclassed_radical_is_reported_not_dropped(self):
        shadow, unmapped = shadow_key(("k", "ν", "s"))
        assert shadow == "K?S" and unmapped == ("ν",)


class TestCandidates:
    def test_radius_one_covers_substitution_insertion_deletion(self, built):
        _, out = built
        idx = RootIndex.load(out)
        numbers = lambda shadow, r=1: {k.number for k in idx.candidates(shadow, r) if k.kind == "ps"}
        assert "2" in numbers("KNS", 0)
        assert "2" in numbers("KMS")      # substitution
        assert "2" in numbers("KS")       # Linear A dropped a coda n
        assert "2" in numbers("KNST")     # one extra consonant
        assert "2" not in numbers("PTM")
        assert "2" not in numbers("KMS", 0)

    def test_deletion_neighbours(self):
        assert deletion_neighbours("KNS") == {"KNS", "NS", "KS", "KN"}
        assert deletion_neighbours("") == {""}

    def test_radius_contract(self, built):
        _, out = built
        idx = RootIndex.load(out)
        assert {id(k) for k in idx.candidates("KNS", 0)} <= {id(k) for k in idx.candidates("KNS", 1)}
        assert idx.candidates("TTT", 0) == []
        with pytest.raises(ValueError, match="0 or 1"):
            idx.candidates("KNS", 2)
        with pytest.raises(ValueError, match="UNINFORMATIVE"):
            idx.candidates("K", 1)                 # every short key is one edit from a one-class shadow
        assert idx.candidates("K", 0) is not None
        assert idx.bucket_count == len(idx._buckets)


# --- keys from records ---

class TestRecordKeys:
    def test_notation_variants_give_one_key(self):
        a = {"Number": "9", "Proto-Semitic": "*ʔab-", "Meaning": "", "Analogues": {}}
        b = {"Number": "9", "Proto-Semitic": "*ʾab-", "Meaning": "", "Analogues": {}}
        assert [k.radicals for k in record_keys(a)] == [k.radicals for k in record_keys(b)]

    def test_kseries_arabic_reads_buckwalter(self):
        rec = {"Number": "K9001", "Proto-Semitic": "*ḥṣd", "Meaning": "'reap'",
               "Analogues": {"Arabic": "HaSada[Reaped]"}}
        reflex = [k for k in record_keys(rec) if k.kind == "reflex"]
        assert ("ḥ", "ṣ", "d") in {k.radicals for k in reflex}

    def test_reflexes_weak_variants_and_branches(self):
        keys = record_keys(RECORDS[1])
        assert {k.kind for k in keys} == {"ps", "reflex"}      # k-n-s: no weak or geminate radical
        weak = {(k.label, k.radicals) for k in record_keys(RECORDS[0]) if k.kind == "weak"}
        assert ("geminate", ("ʾ", "b", "b")) in weak and ("hollow", ("ʾ", "w", "b")) in weak
        heb = next(k for k in keys if k.language == "Hebrew")
        assert heb.branch == "Hebrew" and heb.radicals == ("k", "n", "š") and heb.shadow == "KNS"

    def test_proxy_supplement_and_non_semitic(self):
        keys = {k.language: k for k in record_keys(RECORDS[1]) if k.kind == "reflex"}
        assert keys["Moabite"].branch == "Hebrew" and "proxy_supplement" in keys["Moabite"].flags
        assert "no_branch" not in keys["Moabite"].flags
        assert keys["Egyptian"].branch == "non_semitic"
        assert branch_of("Syrian Aramaic")[0] == "Aramaic"

    def test_deterministic(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        lexica = (_lex("hebrew", _write_jsonl(tmp_path / "hebrew.jsonl", HEBREW)),
                  _lex("phoenician", _write_jsonl(tmp_path / "phoenician.jsonl", PHOENICIAN)))
        tables = ("roots", "analogues", "lexemes", "root_keys", "lexeme_links", "record_hashes",
                  "unkeyed_analogues")
        dumps = []
        for name in ("a.sqlite", "b.sqlite"):
            write_index(tmp_path / name, roots, lexica)
            with sqlite3.connect(tmp_path / name) as c:
                dump = {t: c.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in tables}
                dump["provenance"] = c.execute("SELECT * FROM provenance WHERE key != 'built_at' ORDER BY key").fetchall()
            dumps.append(dump)
        assert dumps[0] == dumps[1] and dumps[0]["lexeme_links"]

    def test_duplicate_numbers_refused(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS + [RECORDS[0]])
        with pytest.raises(ValueError, match="duplicate Numbers"):
            write_index(tmp_path / "x.sqlite", roots, lexica=())


# --- staleness ---

class TestStaleness:
    def test_current_index_loads(self, built):
        _, out = built
        idx = RootIndex.load(out)
        assert idx.provenance["counts"]["roots"] == 3
        assert idx.provenance["counts"]["keys"] == len(idx.keys) > 3
        assert stale_inputs(out) == []

    def test_changed_input_refuses_to_load(self, built):
        roots, out = built
        _write_roots(roots, RECORDS[:2])
        assert str(roots.resolve()) in stale_inputs(out)
        with pytest.raises(IndexStale, match="build_root_index.py --diff"):
            RootIndex.load(out)
        RootIndex.load(out, check_inputs=False)  # explicit opt-out still reads


# --- diff ---

class TestDiff:
    def test_unchanged(self, built):
        roots, out = built
        d = diff_index(out, roots)
        assert d["records"] == {"added": [], "removed": [], "modified": {}, "notes_only": []}
        assert d["keys"] == {}

    def test_notes_only_never_rekeys(self, built):
        roots, out = built
        recs = json.loads(roots.read_text())
        recs[2]["Notes"] = "second note"
        _write_roots(roots, recs)
        d = diff_index(out, roots)
        assert d["records"]["modified"] == {"3": ["~Notes"]}
        assert d["records"]["notes_only"] == ["3"]
        assert d["keys"] == {}

    def test_new_analogue_gains_a_key(self, built):
        roots, out = built
        recs = json.loads(roots.read_text())
        recs[2]["Analogues"]["Akkadian"] = "šarru 'king'"
        _write_roots(roots, recs)
        d = diff_index(out, roots)
        assert d["records"]["modified"] == {"3": ["+Analogues/Akkadian"]}
        assert ("reflex", "Akkadian", "š r r", "SRR") in [tuple(k) for k in d["keys"]["3"]["gained"]]
        assert "SRR" in d["keys"]["3"]["shadow_gained"]

    def test_removed_record_and_merge(self, built):
        roots, out = built
        recs = json.loads(roots.read_text())
        merged = recs[1]
        recs = [r for r in recs if r["Number"] != "2"]
        recs[0]["Analogues"]["Phoenician"] = "kns 'gather'"   # record 1 absorbs 2's root
        recs[0]["Proto-Semitic"] = "*ʾab- ~ *kanVs-"
        _write_roots(roots, recs)
        d = diff_index(out, roots)
        assert d["records"]["removed"] == ["2"] and "1" in d["records"]["modified"]
        assert d["possible_merges"] == {"2": ["1"]}
        assert d["keys"]["2"]["lost"] and not any(k[0] == "ps" for k in d["keys"]["2"]["gained"])
        assert merged["Number"] == "2"

    def test_twin_merge_into_an_unchanged_survivor(self, tmp_path):
        twin = {"Number": "4", "Proto-Semitic": "*kanVs-", "Meaning": "'to assemble'", "Analogues": {}}
        roots = _write_roots(tmp_path / "r.json", RECORDS + [twin])
        out = tmp_path / "x.sqlite"
        write_index(out, roots, lexica=())
        _write_roots(roots, [r for r in RECORDS if r["Number"] != "2"] + [twin])
        d = diff_index(out, roots)
        assert d["records"]["modified"] == {} and d["possible_merges"] == {"2": ["4"]}

    def test_analogue_gain_alone_is_no_merge(self, built):
        roots, out = built
        recs = [r for r in json.loads(roots.read_text()) if r["Number"] != "2"]
        recs[1]["Analogues"]["Phoenician"] = "kns 'gather'"            # record 3 gains a k-n-s reflex only
        _write_roots(roots, recs)
        assert diff_index(out, roots)["possible_merges"] == {}

    def test_key_logic_change_rekeys_every_number(self, tmp_path, monkeypatch):
        logic = tmp_path / "logic.json"
        logic.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(ri, "KEY_LOGIC_FILES", (logic,))
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        out = tmp_path / "x.sqlite"
        write_index(out, roots, lexica=())
        assert diff_index(out, roots)["key_logic_changed"] == []
        logic.write_text('{"x": 1}', encoding="utf-8")
        d = diff_index(out, roots)
        assert d["key_logic_changed"] == [str(logic)] and d["keys"] == {}      # same keys: nothing to report
        monkeypatch.setattr(ri, "record_keys", lambda rec: [k for k in ri._record_keys(rec)[0] if k.kind != "reflex"])
        assert set(diff_index(out, roots)["keys"]) == {"1", "2", "3"}           # unmodified Numbers re-keyed too

    def test_nfc_only_edit(self, built):
        import unicodedata
        roots, out = built
        roots.write_text(unicodedata.normalize("NFD", roots.read_text(encoding="utf-8")), encoding="utf-8")
        d = diff_index(out, roots)
        assert d["roots_sha256_now"] != d["roots_sha256_built"] and d["records"]["modified"] == {}
        assert d["nfc_only"] is True

    def test_lexica_no_longer_specified_are_reported(self, with_lexica):
        roots, _, out, _ = with_lexica
        with sqlite3.connect(out) as c:
            (raw,) = c.execute("SELECT value FROM provenance WHERE key = 'lexica'").fetchone()
            lex = json.loads(raw) | {"retired": "data/contact/retired.jsonl"}
            c.execute("UPDATE provenance SET value = ? WHERE key = 'lexica'", (json.dumps(lex),))
        assert diff_index(out, roots)["lexica_unknown"] == ["retired"]


# --- build script ---

class TestBuildScript:
    def test_refuses_existing_without_force(self, built, capsys):
        roots, out = built
        before = out.read_bytes()
        assert build_root_index.build(out, roots, force=False, lexica=()) == 1
        assert out.read_bytes() == before
        assert "--force" in capsys.readouterr().err

    def test_force_backs_up_then_replaces(self, built):
        roots, out = built
        before = out.read_bytes()
        _write_roots(roots, RECORDS[:2])
        assert build_root_index.build(out, roots, force=True, lexica=()) == 0
        backups = list(out.parent.glob("root_index.sqlite.bak-*"))
        assert len(backups) == 1 and backups[0].read_bytes() == before
        assert RootIndex.load(out).provenance["counts"]["roots"] == 2
        assert not list(out.parent.glob("*.tmp-*"))

    def test_failed_build_leaves_old_index(self, built):
        roots, out = built
        before = out.read_bytes()
        _write_roots(roots, RECORDS + [RECORDS[0]])           # duplicate Number: build raises
        with pytest.raises(ValueError):
            build_root_index.build(out, roots, force=True, lexica=())
        assert out.read_bytes() == before
        assert not list(out.parent.glob("*.tmp-*")) and not list(out.parent.glob("*.bak-*"))
        assert not list(out.parent.glob("*.lock"))

    def test_two_force_builds_keep_both_backups(self, built):
        roots, out = built
        original = out.read_bytes()
        assert build_root_index.build(out, roots, force=True, lexica=()) == 0
        assert build_root_index.build(out, roots, force=True, lexica=()) == 0    # same second, as a rule
        backups = sorted(out.parent.glob("root_index.sqlite.bak-*"))
        assert len(backups) == 2 and backups[0].read_bytes() == original

    def test_rebuilds_keep_the_newest_backups_only(self, built):
        roots, out = built
        old = out.with_name(out.name + ".bak-20200101T000000Z")      # the first stamp format, no µs or pid
        old.write_bytes(b"old")
        other = out.with_name(out.name + ".bak-manual")              # not a build backup: never rotated
        other.write_bytes(b"keep")
        for _ in range(build_root_index.KEEP_BACKUPS + 1):
            assert build_root_index.build(out, roots, force=True, lexica=()) == 0
        stamped = sorted(p for p in out.parent.glob("root_index.sqlite.bak-2*"))
        assert len(stamped) == build_root_index.KEEP_BACKUPS and old not in stamped
        assert other.read_bytes() == b"keep"

    def test_lock_refuses_a_concurrent_build(self, built, capsys):
        roots, out = built
        before = out.read_bytes()
        out.with_name(out.name + ".lock").write_text("12345", encoding="utf-8")
        assert build_root_index.build(out, roots, force=True, lexica=()) == 1
        assert out.read_bytes() == before and "12345" in capsys.readouterr().err
        assert not list(out.parent.glob("*.bak-*"))

    def test_stale_result_is_never_installed(self, built, monkeypatch):
        roots, out = built
        before = out.read_bytes()

        def stale(path, **kw):
            raise IndexStale("inputs changed after the build")
        monkeypatch.setattr(build_root_index.RootIndex, "load", staticmethod(stale))
        with pytest.raises(IndexStale):
            build_root_index.build(out, roots, force=True, lexica=())
        assert out.read_bytes() == before
        assert not list(out.parent.glob("*.tmp-*")) and not list(out.parent.glob("*.bak-*"))

    def test_mid_build_change_via_main(self, built, monkeypatch, capsys):
        roots, out = built
        before = out.read_bytes()
        real = ri._record_keys
        edited = []

        def edit_once(rec):
            if not edited:
                edited.append(1)
                _write_roots(roots, RECORDS[:2])
            return real(rec)
        monkeypatch.setattr(ri, "_record_keys", edit_once)
        monkeypatch.setattr(build_root_index, "LEXICA", ())
        monkeypatch.setattr(sys, "argv", ["build_root_index.py", "--force", "--roots", str(roots), "--out", str(out)])
        assert build_root_index.main() == 1
        assert "changed while the index was being built" in capsys.readouterr().err
        assert out.read_bytes() == before and not list(out.parent.glob("*.tmp-*"))

    def test_index_appearing_during_a_first_build_is_not_replaced(self, tmp_path, monkeypatch, capsys):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        out = tmp_path / "root_index.sqlite"
        real = build_root_index.write_index

        def racing(tmp, *a, **kw):
            prov = real(tmp, *a, **kw)
            out.write_bytes(b"another build's index")
            return prov
        monkeypatch.setattr(build_root_index, "write_index", racing)
        assert build_root_index.build(out, roots, force=False, lexica=()) == 1
        assert out.read_bytes() == b"another build's index" and not list(tmp_path.glob("*.tmp-*"))
        assert "appeared" in capsys.readouterr().err

    def test_missing_lexicon_fails_unless_allowed(self, tmp_path, capsys):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        out = tmp_path / "root_index.sqlite"
        lexica = (_lex("hebrew", tmp_path / "absent.jsonl"),)
        with pytest.raises(FileNotFoundError):
            build_root_index.build(out, roots, force=False, lexica=lexica)
        assert not out.exists()
        assert build_root_index.build(out, roots, force=False, lexica=lexica, allow_missing=True) == 0
        assert "MISSING" in capsys.readouterr().out

    def test_check_exit_codes(self, built, tmp_path, capsys):
        roots, out = built
        assert build_root_index.check(out) == 0 and "current" in capsys.readouterr().out
        _write_roots(roots, RECORDS[:2])
        assert build_root_index.check(out) == 1 and "stale" in capsys.readouterr().out
        assert build_root_index.check(tmp_path / "none.sqlite") == 1 and "not built" in capsys.readouterr().out

    def test_diff_cli(self, built, monkeypatch, capsys):
        roots, out = built
        _write_roots(roots, RECORDS[:2])                       # stale: --diff still answers
        monkeypatch.setattr(sys, "argv", ["b", "--diff", "--json", "--roots", str(roots), "--out", str(out)])
        assert build_root_index.main() == 0
        assert json.loads(capsys.readouterr().out)["records"]["removed"] == ["3"]
        monkeypatch.setattr(sys, "argv", ["b", "--diff", "--out", str(out.with_name("none.sqlite"))])
        assert build_root_index.main() == 1

    @pytest.mark.parametrize("argv", [["--check", "--diff"], ["--json"], ["--check", "--force"]])
    def test_bad_flag_combinations(self, monkeypatch, argv):
        monkeypatch.setattr(sys, "argv", ["b", *argv])
        with pytest.raises(SystemExit) as e:
            build_root_index.main()
        assert e.value.code == 2

    def test_print_diff(self, capsys):
        d = {"built_at": "t", "roots_sha256_built": "a" * 64, "roots_sha256_now": "b" * 64, "nfc_only": False,
             "key_logic_changed": ["tools/core/root_index.py"],
             "records": {"added": [], "removed": ["2"], "modified": {"1": ["~Proto-Semitic"]}, "notes_only": []},
             "keys": {}, "possible_merges": {"2": ["1"]}, "lexica_unknown": ["retired"],
             "lexica": {"hebrew": {"added": [f"hebrew:h{i}" for i in range(25)], "removed": [], "modified": []}}}
        build_root_index._print_diff(d)
        out = capsys.readouterr().out
        assert "possible merge into 1" in out and "key logic changed" in out
        assert "... 5 more" in out and "retired" in out

    def test_print_diff_names_an_nfc_only_change(self, capsys):
        d = {"built_at": "t", "roots_sha256_built": "a" * 64, "roots_sha256_now": "b" * 64, "nfc_only": True,
             "key_logic_changed": [], "records": {"added": [], "removed": [], "modified": {}, "notes_only": []},
             "keys": {}, "possible_merges": {}, "lexica_unknown": [], "lexica": {}}
        build_root_index._print_diff(d)
        assert "NFC" in capsys.readouterr().out

    def test_default_index_must_watch_the_default_roots(self, tmp_path, monkeypatch):
        live, frozen = _write_roots(tmp_path / "live.json", RECORDS), _write_roots(tmp_path / "frozen.json", RECORDS)
        out = tmp_path / "root_index.sqlite"
        write_index(out, frozen, lexica=())
        monkeypatch.setattr(ri, "DEFAULT_INDEX", out)
        monkeypatch.setattr(ri, "DEFAULT_ROOTS", live)
        with pytest.raises(IndexStale, match="frozen.json"):
            RootIndex.load(out)
        RootIndex.load(out, check_inputs=False)


# --- lexemes ---

def _lex(name: str, path: Path):
    return replace(next(lx for lx in LEXICA if lx.name == name), path=path)


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


HEBREW = [
    {"id": "h1", "language": "Hebrew", "normalized": "kns", "root": "k-n-s", "meaning": "to gather", "pos": "verb"},
    {"id": "h2", "language": "Hebrew", "normalized": "mlk", "meaning": "king", "pos": "noun"},
    {"id": "h2", "language": "Hebrew", "normalized": "mlkh", "meaning": "queen", "pos": "noun"},
    {"id": "h3", "language": "Hebrew", "normalized": "ʾšdwd", "meaning": "Ashdod", "pos": "GN"},
]
PHOENICIAN = [
    {"id": "p1", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "assemble",
     "semitic_roots_ref": ["2"]},
    {"id": "p2", "language": "Phoenician", "root": "zbl", "normalized": "zbl", "meaning": "prince",
     "semitic_roots_ref": ["999"]},
]
AKKADIAN = [{"id": "a1", "language": "Akkadian", "normalized": "bitum", "root_consonants": None,
             "meaning": "house"}]


@pytest.fixture
def with_lexica(tmp_path):
    roots = _write_roots(tmp_path / "semitic_roots.json", RECORDS)
    lexica = (_lex("hebrew", _write_jsonl(tmp_path / "hebrew.jsonl", HEBREW)),
              _lex("phoenician", _write_jsonl(tmp_path / "phoenician.jsonl", PHOENICIAN)),
              _lex("akkadian", _write_jsonl(tmp_path / "akkadian.jsonl", AKKADIAN)))
    out = tmp_path / "root_index.sqlite"
    prov = write_index(out, roots, lexica)
    return roots, lexica, out, prov


class TestLexemes:
    def test_lexeme_keys_are_retrievable(self, with_lexica):
        *_, out, _ = with_lexica
        idx = RootIndex.load(out)
        hits = {k.lexeme_id for k in idx.candidates("KNS", 0) if k.kind == "lexeme"}
        assert hits == {"hebrew:h1", "phoenician:p1"}
        assert all(k.number is None for k in idx.keys if k.kind == "lexeme")

    def test_links_by_basis(self, with_lexica):
        *_, out, _ = with_lexica
        links = RootIndex.load(out).links
        assert ("2", "root_key_exact", True) in links["hebrew:h1"]       # sound + gloss 'gather'
        assert ("3", "root_key_exact", True) in links["hebrew:h2"]       # mlk 'king'
        assert links["phoenician:p1"] == [("2", "fk", False)]           # the lexicon's own ref wins
        assert links["phoenician:p2"] == [("999", "fk_dangling", False)]

    def test_duplicate_ids_kept_and_names_flagged(self, with_lexica):
        *_, out, prov = with_lexica
        idx = RootIndex.load(out)
        assert {"hebrew:h2", "hebrew:h2#2"} <= set(idx.lexemes)
        assert idx.lexemes["hebrew:h3"]["onomastic"] and not idx.lexemes["hebrew:h1"]["onomastic"]
        assert all("onomastic" in k.flags for k in idx.keys if k.lexeme_id == "hebrew:h3")
        assert prov["counts"]["lexica"]["hebrew"]["lexemes"] == 4

    def test_akkadian_noun_keyed_from_normalized(self, with_lexica):
        *_, out, _ = with_lexica
        rads = {k.radicals for k in RootIndex.load(out).keys if k.lexeme_id == "akkadian:a1"}
        assert ("b", "t") in rads                                         # bitum, mimation off

    def test_lexicon_edit_stales_only_the_lexeme_layer(self, with_lexica):
        _, lexica, out, _ = with_lexica
        _write_jsonl(lexica[0].path, HEBREW[:2])
        RootIndex.load(out, include_lexemes=False)                       # cognate_search's view: still current
        with pytest.raises(IndexStale):
            RootIndex.load(out)
        assert all(k.number for k in RootIndex.load(out, include_lexemes=False).keys)

    def test_diff_reports_lexicon_entries(self, with_lexica):
        roots, lexica, out, _ = with_lexica
        rows = [dict(HEBREW[0], meaning="to assemble"), HEBREW[1],
                {"id": "h9", "language": "Hebrew", "normalized": "šlm", "meaning": "peace"}]
        _write_jsonl(lexica[0].path, rows)
        d = diff_index(out, roots)                                        # lexica read from provenance
        assert d["lexica"] == {"hebrew": {"added": ["hebrew:h9"], "removed": ["hebrew:h2#2", "hebrew:h3"],
                                          "modified": ["hebrew:h1"]}}
        assert d["records"]["modified"] == {}

    def test_missing_lexicon_refused_unless_allowed(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        absent = tmp_path / "absent.jsonl"
        with pytest.raises(FileNotFoundError, match="absent.jsonl"):
            write_index(tmp_path / "x.sqlite", roots, (_lex("hebrew", absent),))
        assert not (tmp_path / "x.sqlite").exists()                        # nothing half-built left behind
        prov = write_index(tmp_path / "x.sqlite", roots, (_lex("hebrew", absent),), allow_missing=True)
        assert prov["counts"]["lexica"]["hebrew"] == {"missing": 1}
        assert prov["lexicon_sha256"][str(absent.resolve())] == "missing"

    def test_missing_lexicon_that_appears_makes_the_index_stale(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        absent = tmp_path / "absent.jsonl"
        out = tmp_path / "x.sqlite"
        write_index(out, roots, (_lex("hebrew", absent),), allow_missing=True)
        assert stale_inputs(out) == []
        RootIndex.load(out)
        _write_jsonl(absent, HEBREW)
        assert stale_inputs(out) == [str(absent.resolve())]
        with pytest.raises(IndexStale):
            RootIndex.load(out)
        assert diff_index(out, roots)["lexica"]["hebrew"]["added"]           # --check and --diff agree

    def test_deleted_lexicon_is_stale_and_all_removed(self, with_lexica):
        roots, lexica, out, _ = with_lexica
        lexica[0].path.unlink()
        assert str(lexica[0].path.resolve()) in stale_inputs(out)
        assert diff_index(out, roots)["lexica"]["hebrew"]["removed"] == [
            "hebrew:h1", "hebrew:h2", "hebrew:h2#2", "hebrew:h3"]

    def test_suffixed_ids_never_collide(self, tmp_path):
        rows = [{"id": "a", "normalized": "kns"}, {"id": "a", "normalized": "mlk"}, {"id": "a#2", "normalized": "bt"}]
        lx = _lex("hebrew", _write_jsonl(tmp_path / "h.jsonl", rows))
        ids = [x.id for x in iter_lexemes(lx)]
        assert len(set(ids)) == 3 and ids[:2] == ["hebrew:a", "hebrew:a#2"]

    def test_ghosts_and_keyless_lexemes_are_counted(self, tmp_path):
        rows = [{"id": "c1", "headword": "bītu", "meaning": "house"}, {"id": "c2", "ghost": True, "headword": "x"},
                {"id": "c3", "headword": "ū", "meaning": "or"}]
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        # the CAD headwords are not read here (not shipped), but a lexicon of their shape keeps its ghost rule
        cad = ri.Lexicon("cad", _write_jsonl(tmp_path / "c.jsonl", rows), "Akkadian", "akkadian", ("headword",))
        prov = write_index(tmp_path / "x.sqlite", roots, (cad,))
        c = prov["counts"]["lexica"]["cad"]
        assert (c["lexemes"], c["ghost"], c["keyless"]) == (2, 1, 1)

    def test_bad_json_names_file_and_line(self, tmp_path):
        p = tmp_path / "h.jsonl"
        p.write_text('{"id": "a", "normalized": "kns"}\n{broken\n', encoding="utf-8")
        with pytest.raises(ValueError, match=r"h\.jsonl:2"):
            list(iter_lexemes(_lex("hebrew", p)))


class TestLinks:
    """Linking a lexeme to a Number: fk first, then the best sound match over every form and every PS key the
    form's consonants can continue."""

    def _links(self, tmp_path, records, name, rows):
        roots = _write_roots(tmp_path / "r.json", records)
        out = tmp_path / "x.sqlite"
        write_index(out, roots, (_lex(name, _write_jsonl(tmp_path / f"{name}.jsonl", rows)),))
        return RootIndex.load(out).links

    @pytest.mark.parametrize("order", [("ʾ-b-h", "ʾb"), ("ʾb", "ʾ-b-h")])
    def test_exact_beats_reduced_in_either_field_order(self, tmp_path, order):
        row = {"id": "h1", "root": order[0], "normalized": order[1], "meaning": "father"}
        links = self._links(tmp_path, RECORDS, "hebrew", [row])
        assert ("1", "root_key_exact", True) in links["hebrew:h1"]

    def test_fk_is_never_overwritten_by_sound(self, tmp_path):
        row = {"id": "p1", "root": "kns", "normalized": "kns", "meaning": "assemble", "semitic_roots_ref": "2"}
        assert self._links(tmp_path, RECORDS, "phoenician", [row])["phoenician:p1"] == [("2", "fk", False)]

    @pytest.mark.parametrize("ref", ["", None, []])
    def test_empty_refs_are_no_fk(self, tmp_path, ref):
        row = {"id": "p1", "root": "kns", "normalized": "kns", "meaning": "assemble", "semitic_roots_ref": ref}
        assert self._links(tmp_path, RECORDS, "phoenician", [row])["phoenician:p1"] == [("2", "root_key_exact", False)]

    def test_sound_change_across_classes_links(self, tmp_path):
        records = [{"Number": "7", "Proto-Semitic": "*ṯalāṯ-", "Meaning": "'three'", "Analogues": {}},
                   {"Number": "8", "Proto-Semitic": "*walad-", "Meaning": "'to give birth'", "Analogues": {}}]
        (tmp_path / "a").mkdir(), (tmp_path / "b").mkdir()
        assert ("7", "root_key_exact", True) in self._links(          # Aramaic t < *ṯ: bucket TRT, PS key SRS
            tmp_path / "a", records, "aramaic", [{"id": "a1", "root": "tlt", "meaning": "three"}])["aramaic:a1"]
        assert ("8", "root_key_exact", True) in self._links(          # Hebrew y < *w: bucket YRT, PS key WRT
            tmp_path / "b", records, "hebrew", [{"id": "h1", "root": "yld", "meaning": "give birth"}])["hebrew:h1"]

    def test_absorbed_prefix_links_reduced(self, tmp_path):
        records = [{"Number": "5", "Proto-Semitic": "*katab-", "Meaning": "'to write'", "Analogues": {}}]
        links = self._links(tmp_path, records, "hebrew", [{"id": "h1", "normalized": "mktb", "meaning": "letter"}])
        assert links["hebrew:h1"] == [("5", "root_key_reduced", False)]

    def test_phrase_detection(self):
        from tools.core.root_index import _is_phrase
        assert _is_phrase("aban kitti") and _is_phrase("ʾḤR ʾŠ") and _is_phrase("אָבֵל הַשִּׁטִּים")
        assert not _is_phrase("ʾB II")                                    # homograph numeral
        assert not _is_phrase("ḤT ́M")                                    # a stray mark, one word
        assert not _is_phrase("אֲבִיגַ֫יִל, אֲבִיגַ֫ל")                        # two spellings of one name
        assert not _is_phrase("kns")

    def test_phrase_is_keyed_and_flagged_never_linked(self, tmp_path):
        row = {"id": "a1", "form": "ina qate", "normalized": "inaqate", "meaning": "in the hand of"}
        roots = _write_roots(tmp_path / "r.json", [{"Number": "6", "Proto-Semitic": "*naqat-", "Meaning": "'x'",
                                                    "Analogues": {}}])
        out = tmp_path / "x.sqlite"
        prov = write_index(out, roots, (_lex("akkadian", _write_jsonl(tmp_path / "a.jsonl", [row])),))
        idx = RootIndex.load(out)
        assert "akkadian:a1" not in idx.links and prov["counts"]["lexica"]["akkadian"]["phrase"] == 1
        assert all("phrase" in k.flags for k in idx.keys if k.lexeme_id == "akkadian:a1")

    def test_overlong_keys_are_flagged(self, tmp_path):
        row = {"id": "a1", "normalized": "militarycontingents", "meaning": "military contingents"}
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        out = tmp_path / "x.sqlite"
        prov = write_index(out, roots, (_lex("akkadian", _write_jsonl(tmp_path / "a.jsonl", [row])),))
        keys = [k for k in RootIndex.load(out).keys if k.lexeme_id == "akkadian:a1"]
        assert keys and all("overlong" in k.flags for k in keys if len(k.radicals) > 6)
        assert prov["counts"]["lexica"]["akkadian"]["overlong_keys"] >= 1


class TestUnkeyedAnalogues:
    def test_analogues_with_no_key_are_listed_with_a_reason(self, tmp_path):
        rec = {"Number": "40", "Proto-Semitic": "*ʾab-", "Meaning": "'father'",
               "Analogues": {"Hebrew": "(OLA80 §38.5)", "Mehri": "--", "Geez": ["ʾab"], "Arabic": "ʾab-"}}
        roots = _write_roots(tmp_path / "r.json", [rec])
        out = tmp_path / "x.sqlite"
        prov = write_index(out, roots, lexica=())
        with sqlite3.connect(out) as c:
            rows = sorted(c.execute("SELECT number, language, reason FROM unkeyed_analogues"))
        assert rows == [("40", "Geez", "not_a_string"), ("40", "Hebrew", "no_form"), ("40", "Mehri", "placeholder")]
        assert prov["counts"]["unkeyed_analogues"] == {"no_form": 1, "not_a_string": 1, "placeholder": 1}
        assert record_key_gaps(rec) == [("Hebrew", "no_form"), ("Mehri", "placeholder"), ("Geez", "not_a_string")]


class TestContracts:
    def test_write_index_refuses_an_existing_path(self, built):
        roots, out = built
        before = out.read_bytes()
        with pytest.raises(FileExistsError):
            write_index(out, roots, lexica=())
        assert out.read_bytes() == before

    def test_failed_write_index_removes_its_partial_file(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        broken = tmp_path / "h.jsonl"
        broken.write_text('{"id": "a", "normalized": "kns"}\n{broken\n', encoding="utf-8")
        with pytest.raises(ValueError):                                   # fails after the roots are written
            write_index(tmp_path / "x.sqlite", roots, (_lex("hebrew", broken),))
        assert not (tmp_path / "x.sqlite").exists()

    def test_uri_unsafe_path_loads(self, tmp_path):
        d = tmp_path / "a#b?c%d"
        d.mkdir()
        roots = _write_roots(d / "r.json", RECORDS)
        write_index(d / "x.sqlite", roots, lexica=())
        assert RootIndex.load(d / "x.sqlite").provenance["counts"]["roots"] == 3

    def test_other_schema_version_refused(self, built):
        _, out = built
        with sqlite3.connect(out) as c:
            c.execute("UPDATE provenance SET value = '1' WHERE key = 'schema_version'")
        with pytest.raises(IndexStale, match="schema"):
            RootIndex.load(out)

    def test_key_logic_edited_after_import_refuses_build(self, tmp_path, monkeypatch):
        stamp = dict(ri._KEY_LOGIC_AT_IMPORT)
        stamp[next(iter(stamp))] = "0" * 64
        monkeypatch.setattr(ri, "_KEY_LOGIC_AT_IMPORT", stamp)
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        with pytest.raises(IndexStale, match="fresh process"):
            write_index(tmp_path / "x.sqlite", roots, lexica=())

    def test_unchecked_load_is_marked(self, built):
        _, out = built
        assert RootIndex.load(out).checked and not RootIndex.load(out, check_inputs=False).checked

    def test_repository_paths_are_portable(self):
        p = ri.REPO / "data" / "contact" / "x.jsonl"
        assert ri._portable(p) == "data/contact/x.jsonl"
        assert ri._resolve(ri._portable(p)).resolve() == p.resolve()
        assert ri._portable(ri.DEFAULT_ROOTS) == "data/semitic-roots/semitic_roots.json"
        assert ri._portable(Path("/elsewhere/r.json")) == "/elsewhere/r.json"


# --- the shipped data (read-only) ---

def test_live_kns_bucket(tmp_path):
    out = tmp_path / "live.sqlite"
    write_index(out, DEFAULT_ROOTS, lexica=())
    idx = RootIndex.load(out)
    ps = {k.radicals for k in idx.candidates("KNS", 0) if k.kind == "ps"}
    assert ("k", "n", "s") in ps                              # *kanVs- 'to gather, assemble' (2763)


# --- impact set and preview (§7.3, items 3 and 4) ---

DRK = {"Number": "4", "Proto-Semitic": "*darVk-", "Meaning": "'way'", "Analogues": {"Hebrew": "drk 'way'"}}
IMPACT_WORDS = ["DA-RA-KU", "KA-NA-SI", "TO-ZE-PU", "KA-A303"]       # TO-ZE-PU: the gold word; KA-A303: unmapped
IMPACT_CORPUS = ["KA-NA-SI", "MA-RU-KU", "PA-I-TO", "SU-KI-RI-TA", "DI-KI-TE", "DA-ME", "TE-TU", "NA-DA-RE",
                 "MI-NU-TE", "SE-KI-NA", "TA-NA-TI", "KI-RO"]


def _not_gold(word: str) -> bool:
    return word == "TO-ZE-PU"


class TestImpact:
    def test_a_gained_record_impacts_the_words_that_retrieve_it(self, built):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        r = build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold)
        assert r["impacted"] == ["DA-RA-KU"] and r["unmapped"] == ["KA-A303"]
        assert (r["words"], r["gold_set_aside"]) == (4, 1)
        assert "preview" not in r

    def test_a_removed_record_impacts_the_words_that_retrieved_it(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS + [DRK])
        out = tmp_path / "root_index.sqlite"
        write_index(out, roots, lexica=())
        _write_roots(roots, RECORDS)                                           # only the old index holds 4
        assert build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold)["impacted"] == ["DA-RA-KU"]

    def test_nothing_changed_impacts_nothing(self, built):
        roots, out = built
        assert build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold)["impacted"] == []

    def test_a_lexeme_joining_a_cluster_impacts_its_words(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        rows = [{"id": "p5", "language": "Phoenician", "root": "mlk", "normalized": "mlk", "meaning": "counsel"}]
        lex = (_lex("phoenician", _write_jsonl(tmp_path / "p.jsonl", rows)),)
        out = tmp_path / "root_index.sqlite"
        write_index(out, roots, lex)
        assert ("3", "root_key_exact", False) in RootIndex.load(out).links["phoenician:p5"]   # linked, not joined
        _write_jsonl(lex[0].path, [dict(rows[0], meaning="king")])                    # now joins 3: a new branch
        r = build_root_index.impact(out, roots, lex, ["MA-RU-KU", "KA-NA-SI"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == ([], ["MA-RU-KU"])       # Ugaritic mlk already keyed 3

    def test_a_lexeme_bringing_a_new_key_into_a_cluster_is_an_impact(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        rows = [{"id": "p6", "language": "Phoenician", "root": "mlkt", "normalized": "mlkt", "meaning": "queen"}]
        lex = (_lex("phoenician", _write_jsonl(tmp_path / "p.jsonl", rows)),)
        out = tmp_path / "root_index.sqlite"
        write_index(out, roots, lex)
        _write_jsonl(lex[0].path, [dict(rows[0], semitic_roots_ref=["3"])])           # fk: mlkt now keys 3
        r = build_root_index.impact(out, roots, lex, ["MA-RU-KU-TA", "KA-NA-SI"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == (["MA-RU-KU-TA"], [])

    def test_a_meaning_edit_that_changes_a_roots_domains_is_an_impact(self, built):
        """A19: the semantic gate reads a root's domains, so a Meaning edit that moves them is a changed key."""
        roots, out = built
        recs = [dict(r) for r in RECORDS]
        recs[1]["Meaning"] = "'wine'"                                        # 2: no domain → food_drink
        _write_roots(roots, recs)
        r = build_root_index.impact(out, roots, (), ["KA-NA-SI", "MA-RU-KU"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == (["KA-NA-SI"], [])

    def test_a_meaning_edit_that_keeps_the_domains_changes_nothing(self, built):
        roots, out = built
        recs = [dict(r) for r in RECORDS]
        recs[1]["Meaning"] = "'to gather, collect'"                         # still no domain
        _write_roots(roots, recs)
        r = build_root_index.impact(out, roots, (), ["KA-NA-SI", "MA-RU-KU"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == ([], [])

    def test_a_joined_gloss_edit_that_changes_a_roots_domains_is_an_impact(self, tmp_path):
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        rows = [{"id": "p7", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "assembly",
                 "semitic_roots_ref": ["2"]}]                                # fk: joins 2
        lex = (_lex("phoenician", _write_jsonl(tmp_path / "p.jsonl", rows)),)
        out = tmp_path / "root_index.sqlite"
        write_index(out, roots, lex)
        _write_jsonl(lex[0].path, [dict(rows[0], meaning="wine")])           # the gloss now tags food_drink
        r = build_root_index.impact(out, roots, lex, ["KA-NA-SI", "MA-RU-KU"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == (["KA-NA-SI"], [])

    def test_a_key_logic_change_that_moves_retrieval_is_an_impact(self, tmp_path, monkeypatch):
        """Same tokens and clusters, but the old build stored other shadows: what a word retrieves moves."""
        roots = _write_roots(tmp_path / "r.json", RECORDS)
        out = tmp_path / "root_index.sqlite"
        with monkeypatch.context() as m:                                     # the old build's class table
            m.setitem(ri.SHADOW_CLASS, "m", "X")                             # two classes: past the radius of 1
            m.setitem(ri.SHADOW_CLASS, "l", "L")
            write_index(out, roots, lexica=())
        r = build_root_index.impact(out, roots, (), ["MA-RU-KU", "KA-NA-SI"], is_gold=_not_gold)
        assert (r["impacted"], r["breadth_only"]) == (["MA-RU-KU"], [])

    def test_words_are_queried_in_their_canonical_spelling(self, built, monkeypatch):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        seen = []
        real_q = rm.Shoresh.query
        monkeypatch.setattr(rm.Shoresh, "query", lambda self, w, **kw: seen.append(w) or real_q(self, w, **kw))
        r = build_root_index.impact(out, roots, (), ["da-ra-ku", "DA-RA-KU"], is_gold=_not_gold, preview_n=10,
                                    corpus_words=IMPACT_CORPUS)
        assert r["impacted"] == ["DA-RA-KU"] and r["words"] == 1 and set(seen) == {"DA-RA-KU"}

    def test_excluded_numbers_change_nothing(self, built):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        r = build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold, exclusions={"4"})
        assert r["impacted"] == []

    def test_preview_gives_the_top_cluster_and_verdict_before_and_after(self, built):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        r = build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold, preview_n=20,
                                    corpus_words=IMPACT_CORPUS)
        (row,) = r["preview"]
        assert row["word"] == "DA-RA-KU" and r["preview_n"] == 20
        assert (row["after"]["top"], row["after"]["d_star"]) == ("4", 0.0)
        assert row["before"]["top"] != "4" and row["before"]["d_star"] > 0
        assert {"verdict", "p_max"} <= set(row["before"]) and {"verdict", "p_max"} <= set(row["after"])

    def test_gold_words_never_reach_the_engine(self, built, monkeypatch):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        seen = []
        real_v, real_q = rm.Shoresh._variants_of, rm.Shoresh.query
        monkeypatch.setattr(rm.Shoresh, "_variants_of", lambda self, s: seen.append("-".join(s)) or real_v(self, s))
        monkeypatch.setattr(rm.Shoresh, "query", lambda self, w, **kw: seen.append(w) or real_q(self, w, **kw))
        r = build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=lambda w: w == "DA-RA-KU", preview_n=10,
                                    corpus_words=IMPACT_CORPUS)
        assert "DA-RA-KU" not in seen and r["impacted"] == [] and r["gold_set_aside"] == 1

    def test_writes_nothing(self, built):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        before = {p: p.read_bytes() for p in out.parent.iterdir()}
        build_root_index.impact(out, roots, (), IMPACT_WORDS, is_gold=_not_gold, preview_n=10,
                                corpus_words=IMPACT_CORPUS)
        assert {p: p.read_bytes() for p in out.parent.iterdir()} == before

    def test_main_flags(self, built, monkeypatch, capsys):
        roots, out = built
        _write_roots(roots, RECORDS + [DRK])
        monkeypatch.setattr(build_root_index, "LEXICA", ())
        monkeypatch.setattr(build_root_index, "impact_inputs",
                            lambda: (IMPACT_WORDS, _not_gold, {}, IMPACT_CORPUS))
        base = ["b", "--diff", "--roots", str(roots), "--out", str(out)]
        monkeypatch.setattr(sys, "argv", [*base, "--impact", "--json"])
        assert build_root_index.main() == 0
        d = json.loads(capsys.readouterr().out)
        assert d["impact"]["impacted"] == ["DA-RA-KU"] and "preview" not in d["impact"]
        monkeypatch.setattr(sys, "argv", [*base, "--preview", "--n", "10"])            # --preview implies --impact
        assert build_root_index.main() == 0
        text = capsys.readouterr().out
        assert "impact: 1 of 3 words retrieve a changed key (1 gold word set aside, 1 unmapped)" in text
        assert "0 more words retrieve a key whose root gained or lost a branch" in text
        assert ("note: only the impacted words can change d* and the clusters at d*; p, saturation and so the "
                "verdict can move for any word, since the decoys query the whole index") in text
        assert "families ABC, no competitors, so no CONVERGENT" in text
        assert "DA-RA-KU  before" in text and "after 4 d*=0" in text
        monkeypatch.setattr(sys, "argv", [*base])
        assert build_root_index.main() == 0 and "impact" not in capsys.readouterr().out       # off by default

    def test_print_impact_counts_and_lists(self, capsys):
        r = {"words": 9, "gold_set_aside": 2, "excluded": 59, "impacted": ["KA-PA"], "breadth_only": ["DA-ME", "TE-TU"],
             "unmapped": ["KA-A303"]}
        build_root_index._print_impact(r)
        out = capsys.readouterr().out
        assert "impact: 1 of 7 words retrieve a changed key (2 gold words set aside, 1 unmapped)" in out
        assert "  2 more words retrieve a key whose root gained or lost a branch or POS" in out
        assert "  KA-PA\n" in out and "DA-ME" not in out

    @pytest.mark.parametrize("argv", [["--impact"], ["--preview"], ["--check", "--impact"], ["--diff", "--n", "5"]])
    def test_impact_flags_go_with_diff(self, monkeypatch, argv):
        monkeypatch.setattr(sys, "argv", ["b", *argv])
        with pytest.raises(SystemExit) as e:
            build_root_index.main()
        assert e.value.code == 2
