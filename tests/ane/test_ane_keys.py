"""ane_keys, the query-side notation: parsing, each view's spellings, the folded key and pattern, and a census of
the keys each view stores.

The parse, expand and fold tests use inline inputs. The census reads each view's stored data and skips, view by
view, when that view's files are not in the checkout; it is a `data` test for the views whose files this repository
ships and a `maintainer` test for the rest. No network.
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import duckdb
import pytest

from tools.ane import ane_keys as keys
from tools.ane import aneq
from tools.paths import REPO

# Views whose files ship under data/; the others read corpora built locally (data/ingest/) or not yet shipped.
SHIPPED = {"egytext", "pnm"}


def nfd(s):
    return unicodedata.normalize("NFD", s)


def view_paths(view: str) -> list[Path]:
    """The files or glob patterns `view` searches: aneq's constants, named in VIEW_NOTATION, or a path given there."""
    out: list[Path] = []
    for name in keys.VIEW_NOTATION[view]["paths"]:
        value = name if isinstance(name, Path) else getattr(aneq, name)
        out += list(value) if isinstance(value, (list, tuple)) else [value]
    return out


def view_files(view: str) -> list[Path]:
    """The files of `view` in this checkout, globs expanded."""
    out: list[Path] = []
    for path in view_paths(view):
        out += sorted(path.parent.glob(path.name)) if "*" in path.name else [path] if path.exists() else []
    return out


def shown(path: Path) -> str:
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def with_data(view: str, *values):
    """A parameter for `view`, skipped when none of its files is in the checkout."""
    looked = ", ".join(shown(p) for p in view_paths(view))
    return pytest.param(*(values or (view,)), id=view if not values else None, marks=[
        pytest.mark.data if view in SHIPPED else pytest.mark.maintainer,
        pytest.mark.skipif(not view_files(view), reason=f"{view} is not in this checkout (looked for {looked})"),
    ])


CENSUS_VIEWS = [with_data(view) for view in sorted(keys.VIEW_NOTATION)]


def records_at(path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def records(view):
    for path in view_files(view):
        yield from records_at(path)


def stored(record_id, view):
    r = next(r for r in records(view) if r["id"] == record_id)
    return set(r.get("match_keys") or []) | {r.get("normalized"), r.get("root")} - {None}


def stored_values(view):
    """Every string a view stores in the field aneq searches (match_keys unless the row names another)."""
    row = keys.VIEW_NOTATION[view]
    name = row.get("field", "match_keys")
    for path in view_files(view):
        if path.suffix == ".duckdb":
            con = duckdb.connect(str(path), read_only=True)
            values = [v for (v,) in con.execute(f"SELECT {name} FROM {row['table']} WHERE {name} IS NOT NULL").fetchall()]
            con.close()
        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            values = [r.get(name) for r in (data[row["json_list"]] if "json_list" in row else [data])]
        else:
            values = [r.get(name) for r in records_at(path)]
        for v in values:
            for s in (v if isinstance(v, list) else [v]):
                if isinstance(s, str):
                    yield s.casefold() if row.get("census_casefold") else s


class TestParseQuery:
    def test_decomposed_input_is_composed(self):
        assert keys.parse_query(nfd("ṣdq")).radicals == ["ṣ", "d", "q"]

    def test_root_sign_and_star_are_stripped_and_mean_root(self):
        p = keys.parse_query("√kns")
        assert p.radicals == ["k", "n", "s"] and p.mode == "root"
        assert keys.parse_query("*kns").radicals == ["k", "n", "s"]

    def test_hyphens_and_dotted_letters_mean_root(self):
        assert keys.parse_query("m-n-y").mode == "root"
        assert keys.parse_query("m.n.y").mode == "root"
        assert keys.parse_query("mny").mode == "form"

    def test_latin_is_casefolded(self):
        assert keys.parse_query("MNY").radicals == ["m", "n", "y"]
        assert keys.parse_query("ṢDQ").radicals == ["ṣ", "d", "q"]

    def test_hebrew_and_arabic_letters_are_kept(self):
        assert keys.parse_query("שושנה").radicals == list("שושנה")
        assert keys.parse_query("مني").radicals == list("مني")

    @pytest.mark.parametrize("q", ["ʾ-n-s¹", "ʾ-n-s₁", "ʾ-n-s1", "ʾns¹"])
    def test_an_indexed_sibilant_is_one_radical(self, q):
        assert keys.parse_query(q).radicals == ["ʾ", "n", "s1"]

    def test_a_mark_stays_on_its_letter(self):
        assert keys.parse_query(nfd("ʔṯr")).radicals == ["ʾ", "ṯ", "r"]

    def test_an_arabic_hamza_letter_is_one_radical(self):
        assert keys.parse_query("أثر").radicals == ["أ", "ث", "ر"]


class TestExpandQuran:
    def test_aleph_is_written_as_the_glottal_stop_sign(self):
        assert {"ʔṯr", "ʔ-ṯ-r"} <= keys.expand(keys.parse_query("ʾ-ṯ-r"), "quran")

    def test_ipa_ayin_is_written_as_ayin(self):
        assert "ʿlm" in keys.expand(keys.parse_query("ʕlm"), "quran")

    def test_root_sign_case_and_hyphens_reach_the_same_keys(self):
        for q in ("m-n-y", "√mny", "MNY", nfd("m-n-y")):
            assert {"mny", "m-n-y"} <= keys.expand(keys.parse_query(q), "quran")

    def test_spaced_arabic_is_joined(self):
        assert "مني" in keys.expand(keys.parse_query("م ن ي"), "quran")


class TestExpandOthers:
    def test_hebrew_points_are_dropped_before_romanising(self):
        assert "šwšnh" in keys.expand(keys.parse_query("שׁוֹשַׁנָּה"), "ahi")

    def test_epi_takes_its_declared_signs(self):
        assert "ʿttr" in keys.expand(keys.parse_query("ʕttr"), "epi")

    def test_an_unknown_view_is_refused(self):
        with pytest.raises(KeyError):
            keys.expand(keys.parse_query("mny"), "nonesuch")


class TestExpandHebrew:
    @pytest.mark.parametrize("q", ["וַיִּשְׁמְעוּ", nfd("וַיִּשְׁמְעוּ"), "וַ֠יִּשְׁמְע֞וּ"])
    def test_points_and_accents_are_dropped_for_the_consonantal_field(self, q):
        assert keys.expand(keys.parse_query(q), "hebrew") == {"וישמעו"}

    def test_an_unpointed_word_is_kept_with_its_final_letter(self):
        assert keys.expand(keys.parse_query("שלום"), "hebrew") == {"שלום"}


class TestExpandEgytext:
    def test_h_with_line_below_is_spelled_both_ways_the_data_stores_it(self):
        assert {"ẖnw", "ẖnw"} <= keys.expand(keys.parse_query("ẖnw"), "egytext")

    def test_decomposed_input_reaches_the_composed_key(self):
        assert "ꜣḫ-m-rʾf" in keys.expand(keys.parse_query(nfd("ꜣḫ-m-rʾf")), "egytext")

    @pytest.mark.parametrize("q,key", [
        ("Xnw", "ẖnw"),
        ("smw-n-Xnmw-Htpw", "smw-n-ẖnmw-ḥtpw"),
        ("anx", "ꜥnḫ"),
        ("Axt", "ꜣḫt"),
        ("Dd-mdw", "ḏd-mdw"),
        ("iTi", "jṯj"),
        ("Xnmw-Hzi̯f", "ẖnmw-ḥzi̯f"),    # TLA's i̯ is a letter of its own, not MdC i
    ])
    def test_manuel_de_codage_is_read(self, q, key):
        assert key in keys.expand(keys.parse_query(q), "egytext")

    def test_the_query_as_typed_is_kept_beside_its_mdc_reading(self):
        out = keys.expand(keys.parse_query("Htp"), "egytext")
        assert {"htp", "ḥtp"} <= out

    @pytest.mark.parametrize("q,key", [("ʿnḫ", "ꜥnḫ"), ("ȝḫ", "ꜣḫ"), ("ỉmn", "jmn")])
    def test_typed_stand_ins_for_egyptian_letters(self, q, key):
        assert key in keys.expand(keys.parse_query(q), "egytext")

    def test_hyphens_are_kept_as_typed(self):
        out = keys.expand(keys.parse_query("tʾ-nb-nfr"), "egytext")
        assert "tʾ-nb-nfr" in out


class TestExpandAramaic:
    @pytest.mark.parametrize("q,key", [
        ("ʕqb", "ʿqb"),
        ("rwj", "rwy"),
        ("√bʾr", "bʾr"),
        (nfd("m-ḥ-j"), "mḥy"),
        ("גלל", "gll"),
        ("סגי", "sgy"),
        ("עקב", "ʿqb"),
    ])
    def test_the_query_reaches_the_etcbc_root_notation(self, q, key):
        assert key in keys.expand(keys.parse_query(q), "aramaic")

    def test_a_typed_j_is_read_as_yod_only(self):
        out = keys.expand(keys.parse_query("rwj"), "aramaic")
        assert "rwy" in out and "rwj" not in out

    def test_an_unpointed_shin_is_read_both_ways(self):
        assert {"šbʿ", "śbʿ"} <= keys.expand(keys.parse_query("שבע"), "aramaic")

    def test_a_pointed_sin_is_read_as_sin_only(self):
        out = keys.expand(keys.parse_query("שׂרף"), "aramaic")
        assert "śrp" in out and "šrp" not in out


class TestExpandSubstringViews:
    def test_dasi_ipa_aleph_and_superscript_sibilant(self):
        assert "ʾwṣng" in keys.expand(keys.parse_query("ʔwṣng"), "dasi")
        assert "ʿs¹mn" in keys.expand(keys.parse_query("ʿs₁mn"), "dasi")

    def test_ahi_romanises_hebrew_script(self):
        assert "brk" in keys.expand(keys.parse_query("ברך"), "ahi")
        assert "šmʿ" in keys.expand(keys.parse_query("שמע"), "ahi")

    def test_ahi_ipa_signs(self):
        assert "ʾḥyʾ" in keys.expand(keys.parse_query("ʔḥyʔ"), "ahi")


class TestExpandRegistries:
    def test_term_roots_are_hyphenated_with_ipa_signs(self):
        assert "ʔ-š-r" in keys.expand(keys.parse_query("ʾšr"), "term")
        assert "b-ʕ-l" in keys.expand(keys.parse_query("b-ʿ-l"), "term")


class TestAsciiDigraphs:
    @pytest.mark.parametrize("view,q,key", [
        ("epi", "shrd", "šrd"),
        ("quran", "shkk", "škk"),
        ("quran", "jww", "ǧww"),
        ("dasi", "s2dhwdh", "s²ḏwḏ"),
        ("dasi", "qrdhdh", "qrḏḏ"),
        ("epi", "khlq", "ḫlq"),
        ("epi", "ghfr", "ġfr"),
        ("quran", "thwr", "ṯwr"),
    ])
    def test_a_digraph_is_read_as_its_letter(self, view, q, key):
        assert key in keys.expand(keys.parse_query(q), view)

    def test_each_digraph_is_also_kept_as_two_letters(self):
        assert {"šḏ", "šdh", "shḏ", "shdh"} <= keys.expand(keys.parse_query("shdh"), "epi")

    def test_hyphenated_letters_are_not_a_digraph(self):
        assert "šr" not in keys.expand(keys.parse_query("s-h-r"), "quran")

    def test_views_read_by_mdc_take_no_digraphs(self):
        assert "šm" not in keys.expand(keys.parse_query("shm"), "egytext")
        assert "šm" not in keys.expand(keys.parse_query("shm"), "pnm")


class TestLooseKey:
    @pytest.mark.parametrize("a,b", [
        ("mḥṣ", "mhs"),
        (nfd("mḥṣ"), "mhs"),
        ("Mayyašum", "mayyasum"),
        ("ẖnw", "hnw"),
        ("ʿdd", "ʾdd"),
        ("ʔdd", "'dd"),
        ("ʕdd", "`dd"),
        ("s²ḏwḏ", "s₂dwd"),
        ("s1mn", "smn"),
        ("jw-sbk-ḥtp", "jwsbkḥtp"),
        ("smn.t-jmn", "smntjmn"),
        ("wr.n⸗f-n⸗s (?)", "wrnfns(?)"),
        ("s^arr-i:", "sarri"),
        ("√ʾ-ṯ-r", "ʾtr"),
        ("אֲשֵׁרָה", "אשרה"),
    ])
    def test_both_spellings_fold_to_one_key(self, a, b):
        assert keys.loose_key(a) == keys.loose_key(b)

    @pytest.mark.parametrize("a,b", [("ꜥnḫ", "ʿnḫ"), ("ꜣḫ", "ḫ"), ("ṣdq", "ṣdk"), ("bʿl", "bl")])
    def test_letters_stay_distinct(self, a, b):
        assert keys.loose_key(a) != keys.loose_key(b)


class TestFoldPattern:
    """A bare letter in the query stands for any marked form of it; a marked letter means itself."""

    @pytest.mark.parametrize("q,stored", [
        ("mhs", "mḥṣ"),
        ("hnw", "ẖnw"),
        ("hnw", "ẖnw"),     # stored decomposed
        ("ʿdd", "ʾdd"),
        ("'tr", "ʔṯr"),
        ("ʕṯr", "ʔ-ṯ-r"),
        ("smn", "s¹mn"),
        ("Mayyasum", "Mayyašum"),
        ("jwsbkḥtp", "jw-sbk-ḥtp"),
        ("sarri", "s^arr-i:"),
        ("אשרה", "אֲשֵׁרָה"),
        (nfd("mḥṣ"), "mḥṣ"),            # typed decomposed
    ])
    def test_the_query_reaches_the_stored_spelling(self, q, stored):
        assert re.fullmatch(keys.fold_pattern(q), keys.marks_kept(stored))

    @pytest.mark.parametrize("q,stored", [("mwṯ", "mwt"), ("hḏmm", "hdmm"), ("bʿś", "bʿš"), ("ṣdq", "sdq"),
                                          ("mḥṣ", "mhs")])
    def test_a_typed_mark_is_not_dropped(self, q, stored):
        assert not re.fullmatch(keys.fold_pattern(q), keys.marks_kept(stored))

    def test_regex_signs_in_the_query_are_literal(self):
        assert re.fullmatch(keys.fold_pattern("sapaqu(?)"), keys.marks_kept("s^apaqu(?)"))
        assert not re.fullmatch(keys.fold_pattern("ab?"), keys.marks_kept("a"))


class TestExpandProperNames:
    @pytest.mark.parametrize("q,key", [
        ("Hb-aA", "ḥb-ꜥꜣ"),
        ("tx.i-wbn⸗s", "tḫ.j-wbn⸗s"),
        ("SbAw", "šbꜣw"),
        ("snb-anx", "snb-ꜥnḫ"),
        ("iti=i-nfr", "jtj⸗j-nfr"),
        ("sSn.ii", "sšn.jj"),
    ])
    def test_pnm_reads_manuel_de_codage(self, q, key):
        assert key in keys.expand(keys.parse_query(q), "pnm")

    @pytest.mark.parametrize("q,key", [("snb-ꜥnḫ", "snb-ꜥnḫ"), ("ʿnḫ", "ꜥnḫ"), ("ʾḫ", "ꜣḫ"), ("ȝḫ", "ꜣḫ")])
    def test_pnm_transliteration_and_stand_ins(self, q, key):
        assert key in keys.expand(keys.parse_query(q), "pnm")


class TestCuratedMisses:
    """A curated query that once reached no stored key."""

    @pytest.mark.parametrize("view,query,record_id", [
        with_data("quran", "quran", "ʾ-ṯ-r", "quran:root:أثر"),
    ])
    def test_the_query_expands_to_a_stored_key(self, view, query, record_id):
        assert keys.expand(keys.parse_query(query), view) & stored(record_id, view)


class TestNotationCensus:
    """Every character a view stores in its keys is declared. A rebuild that changes a convention, or a new stray
    character, fails here."""

    @pytest.mark.parametrize("view", CENSUS_VIEWS)
    def test_stored_keys_use_only_the_declared_alphabet(self, view):
        row = keys.VIEW_NOTATION[view]
        seen = Counter(ch for k in stored_values(view) for ch in k)
        assert seen, f"{view}: no keys read"
        undeclared = {ch: n for ch, n in seen.items() if not keys.declared(view, ch)}
        assert undeclared == row.get("known_strays", {})

    @pytest.mark.parametrize("view", CENSUS_VIEWS)
    def test_no_other_aleph_or_ayin_sign_is_stored(self, view):
        row = keys.VIEW_NOTATION[view]
        signs = set(keys.ALEPHS) | set(keys.AYINS)
        allowed = set(row["aleph"]) | set(row["ayin"])
        found = {ch for k in stored_values(view) for ch in k if ch in signs}
        assert found <= allowed, f"{view} stores {sorted(found - allowed)}"

    @pytest.mark.parametrize("view", CENSUS_VIEWS)
    def test_aneq_s_sql_fold_is_loose_key(self, view):
        values = sorted(set(stored_values(view)))
        assert values, f"{view}: no keys read"
        con = duckdb.connect()
        folded = dict(con.execute(f"SELECT v, {aneq.sql_loose('v')} FROM (SELECT unnest(?) AS v)",
                                  [values]).fetchall())
        differ = {v: (folded[v], keys.loose_key(v)) for v in values if folded[v] != keys.loose_key(v)}
        assert not differ, f"{view}: {len(differ)} differ, e.g. {list(differ.items())[:5]}"

    @pytest.mark.parametrize("view", CENSUS_VIEWS)
    def test_aneq_s_sql_marks_kept_is_marks_kept(self, view):
        values = sorted(set(stored_values(view)))
        con = duckdb.connect()
        kept = dict(con.execute(f"SELECT v, {aneq.sql_marks_kept('v')} FROM (SELECT unnest(?) AS v)",
                                [values]).fetchall())
        differ = {v: (kept[v], keys.marks_kept(v)) for v in values if kept[v] != keys.marks_kept(v)}
        assert not differ, f"{view}: {len(differ)} differ, e.g. {list(differ.items())[:5]}"

    def test_the_view_paths_are_aneq_s_own(self):
        assert view_paths("epi") == list(aneq.EPIGRAPHY)
        assert view_paths("aramaic") == [aneq.ARAMAIC_DB]
        assert view_paths("term") == [aneq.TERMS_GLOB]
        assert view_paths("egytext") == [aneq.EGY_SENTS, aneq.EGY_DOCS]
        for view, row in keys.VIEW_NOTATION.items():
            for name in row["paths"]:
                assert isinstance(name, Path) or hasattr(aneq, name), (view, name)

    def test_the_field_and_substring_views_are_declared(self):
        assert {"hebrew", "egytext", "aramaic", "dasi", "ahi", "term"} <= set(keys.VIEW_NOTATION)

    @pytest.mark.parametrize("q,stored", [("mhs", "mḥṣ"), ("hnw", "ẖnw"), ("mwṯ", "mwt"), ("bʿś", "bʿš"),
                                          ("ʿdd", "ʾdd"), ("sapaqu(?)", "s^apaqu(?)"), ("אשרה", "אֲשֵׁרָה")])
    def test_duckdb_reads_the_fold_pattern_as_python_does(self, q, stored):
        sql = duckdb.connect().execute("SELECT regexp_full_match(?, ?)",
                                       [keys.marks_kept(stored), keys.fold_pattern(q)]).fetchone()[0]
        assert sql == bool(re.fullmatch(keys.fold_pattern(q), keys.marks_kept(stored)))

    def test_the_proper_name_path_is_the_script_s_own(self):
        from tools.ane import query_proper_names as names
        assert view_paths("pnm") == [names.SOURCE_DIRS["pnm"] / "tables" / "personal_names.jsonl"]
