"""Tests for tools/linear_a/validation/root_match_checks.py: the A9 speller, eligibility and power summary, A12's
report writer, and one planted query on a tmp index. Neither check is run for real here: the end-to-end tests stub
the queries, read the shipped roots, lexicon and rival-language files read-only, and pin the input hashes so a change
to those files cannot fail them."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest
from shoresh_inputs import SHORESH

from tools.core import root_match as rm
from tools.core.root_index import record_keys
from tools.linear_a.validation import root_match_checks as chk

pytestmark = SHORESH

SERIES = chk.lb_series()


def _ps(form: str):
    rec = {"Number": "9", "Proto-Semitic": form, "Meaning": "'x'", "Analogues": {}}
    return next(k for k in record_keys(rec) if k.kind == "ps")


def _spell(form: str, seed: int = 0) -> str:
    key = _ps(form)
    fitted = chk.headword_pattern(key.form, key.radicals)
    pattern, trailing = fitted if fitted else chk.open_pattern(key.radicals)
    return chk.spell(pattern, trailing, random.Random(seed), SERIES)


class TestSeries:
    def test_linear_b_values_and_zu_s_full_series(self):
        assert SERIES["k"]["a"] == "KA" and SERIES["y"]["a"] == "JA"
        assert "l" not in SERIES                                  # RA₂ and JU carry campaign or fitted values
        assert "u" not in SERIES["y"]
        for c in ("ṯ", "ḏ", "ẓ"):                                 # A21: ZU writes them before every vowel
            assert SERIES[c] == {v: "ZU" for v in "aeiou"}
        assert SERIES["z"]["a"] == "ZA" and SERIES["z"]["u"] == "ZU" and "i" not in SERIES["z"]   # zu alone

    def test_a_conventional_series_has_zu_as_zu_alone(self):
        conv = chk.lb_series(conventional=True)
        assert not {"ṯ", "ḏ", "ẓ"} & set(conv) and conv["z"]["u"] == "ZU"
        assert chk.series_consonant("ṯ", conv) == "z"

    @pytest.mark.parametrize("c, written", [("b", "p"), ("g", "k"), ("ṭ", "t"), ("š", "s"), ("ṣ", "z"), ("l", "r"),
                                            ("f", "p"), ("k", "k"), ("ṯ", "ṯ")])
    def test_unwritten_consonants_take_the_nearest_series(self, c, written):
        assert chk.series_consonant(c, SERIES) == written


class TestHeadwordPattern:
    def test_vowels_from_the_headword_radicals_from_the_key(self):
        assert chk.headword_pattern("*kanVs-", ("k", "n", "s")) == (
            [("C", "k"), ("V", "a"), ("C", "n"), ("V", "V"), ("C", "s")], True)

    def test_first_alternative_slash_and_optional_parts(self):
        slots, trailing = chk.headword_pattern("*ʾarg(a)w/mānu", ("ʾ", "r", "g", "w", "n"))
        assert [x for k, x in slots if k == "C"] == ["ʾ", "r", "g", "w", "n"] and not trailing
        assert chk.headword_pattern("*zibl- {} *ʒibl-", ("z", "b", "l"))[0][0] == ("C", "z")

    @pytest.mark.parametrize("form, radicals", [("*tmm", ("t", "m", "m")), ("*pi/uʾ-at-", ("p", "ʾ"))])
    def test_unfit_headwords_fall_back(self, form, radicals):
        assert chk.headword_pattern(form, radicals) is None


class TestSpell:
    def test_open_syllables_and_the_ending_vowel(self):
        assert re.fullmatch(r"KA-N[AIU]-S[AIU]", _spell("*kanVs-"))

    def test_codas_are_omitted(self):
        assert re.fullmatch(r"KA-P[AIU]", _spell("*kalb-"))          # l is a coda; b written with P
        assert _spell("*bann") == "PA"                               # both n are codas, no ending vowel

    def test_glottal_and_pharyngeal_onsets_are_bare_vowels(self):
        assert re.fullmatch(r"A-P[AIU]", _spell("*ʾab-"))
        assert re.fullmatch(r"A-DO-M[AIU]", _spell("*hadōm-"))

    def test_kh_is_written_or_not_by_seed(self):
        firsts = {_spell("*ḫVṣ̂ib-", s).split("-")[0] for s in range(60)}
        assert firsts & {"KA", "KI", "KU"} and firsts & {"A", "I", "U"}

    def test_zu_writes_the_interdentals_before_any_vowel(self):
        assert re.fullmatch(r"ZU-R[AIU]", _spell("*ṯawr-"))
        assert re.fullmatch(r"ZU-KA-R[AIU]", _spell("*ḏakar-"))

    def test_missing_vowel_takes_one_the_series_has(self):
        assert re.fullmatch(r"Q[AE]-R[AIU]", _spell("*qir-"))

    def test_same_seed_same_spelling(self):
        assert _spell("*ŝVrVḫ-", 7) == _spell("*ŝVrVḫ-", 7)

    def test_open_fallback_writes_every_radical(self):
        assert re.fullmatch(r"T[AIU]-M[AIU]-M[AIU]", _spell("*tmm"))   # every vowel is a V slot

    def test_spellings_read_back_through_the_engine(self):
        for form in ("*kanVs-", "*ʾarg(a)w/mānu", "*šVmVn-", "*ṭayb-", "*w/nVpVt_-"):
            word = _spell(form)
            assert all(rm.sign_options(s) for s in word.split("-")), word


class TestEligibility:
    def test_lexicon_keys_take_compounds_and_fold_gutturals(self):
        keys = chk.lexicon_keys([{"root": "b-ṭ-n + š-m-n"}, {"root": "ḫ-y-y + ʿ-d-d"},
                                 {"root": "ṭ-m-n (or d-m + -ina)"}, {"root": "to gather"}, {}])
        assert keys == {("b", "ṭ", "n"), ("š", "m", "n"), ("y", "y"), ("d", "d"), ("ṭ", "m", "n"), ("d", "m")}

    def test_branches_links_and_exclusions(self):
        recs = [
            {"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'gather'",
             "Analogues": {"Hebrew": "knš 'gather'", "Akkadian": "kanāšu 'submit'"}},
            {"Number": "2", "Proto-Semitic": "*mVlk-", "Meaning": "'king'", "Analogues": {"Ugaritic": "mlk id."}},
            {"Number": "3", "Proto-Semitic": "*ṭayb-", "Meaning": "'good'",
             "Analogues": {"Hebrew": "ṭwb 'good'", "Arabic": "ṭayyib 'good'"}},
            {"Number": "2970", "Proto-Semitic": "*tnt-", "Meaning": "'Tanit'",
             "Analogues": {"Hebrew": "tnt", "Arabic": "tnt"}},
        ]
        eligible, why = chk.eligible_records(recs, {("ṭ", "y", "b")}, {"2970": "campaign_addition"})
        assert [n for n, _ in eligible] == ["1"]
        assert why == {"under_two_branches": 1, "lexicon_linked": 1, "campaign_addition": 1}


class TestPower:
    def test_buckets_and_the_underpowered_label(self):
        rows = [{"consonants": 3, "detected": d, "recovered": d, "verdict": "x"} for d in (True, False)] + \
               [{"consonants": 4, "detected": d, "recovered": False, "verdict": "x"} for d in (True, False, False)]
        s = chk.power_summary(rows)
        assert s["3"]["power"] == 0.5 and not s["3"]["underpowered"]
        assert s["4"]["power"] == round(1 / 3, 4) and s["4"]["underpowered"]


class TestPlantedQuery:
    def test_a_planted_root_is_detected_and_recovered(self, tmp_path, monkeypatch):
        import test_root_match as trm
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        from tools.core.root_index import RootIndex, write_index
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        engine = rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"), corpus_words=trm.CORPUS)
        monkeypatch.setattr(chk, "_ENGINE", engine)
        row = chk.a9_one(({"number": "1", "word": "KA-NA-SI"}, 100, rm.SEED))
        assert row["recovered"] and row["detected"] and row["verdict"] == "PHONOLOGICAL_ONLY"
        miss = chk.a9_one(({"number": "2", "word": "KA-NA-SI"}, 100, rm.SEED))
        assert not miss["recovered"]

    def test_recovery_sees_every_cluster_tied_at_d_star(self, tmp_path, monkeypatch):
        import test_root_match as trm
        recs = [{"Number": str(n), "Proto-Semitic": "*kanVs-", "Meaning": "'gather'", "Analogues": {}}
                for n in range(10, 22)]                                 # 12 ties; "21" sorts last
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
        from tools.core.root_index import RootIndex, write_index
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        monkeypatch.setattr(chk, "_ENGINE", rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"),
                                                         corpus_words=trm.CORPUS))
        row = chk.a9_one(({"number": "21", "word": "KA-NA-SI"}, 20, rm.SEED))
        assert row["recovered"] and row["uniqueness"] == 12

    def test_a_planted_cluster_beaten_by_another_is_not_recovered(self, tmp_path, monkeypatch):
        import test_root_match as trm
        recs = [{"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'gather'", "Analogues": {}},
                {"Number": "7", "Proto-Semitic": "*kanVš-", "Meaning": "'sweep'", "Analogues": {}}]   # s ~ š 0.15
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
        from tools.core.root_index import RootIndex, write_index
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        monkeypatch.setattr(chk, "_ENGINE", rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"),
                                                         corpus_words=trm.CORPUS))
        row = chk.a9_one(({"number": "7", "word": "KA-NA-SI"}, 20, rm.SEED))
        assert row["d_star"] == 0.0 and row["best"] == "1" and not row["recovered"]


class TestCompetitorPower:
    """A15: competitor power both ways."""

    def _space(self, keys, distances):
        from tools.core import competitors as cp
        return cp.CompetitorSpace("egyptian", {tuple(rm._tokenize_phonemes(k)): [str(i)] for i, k in enumerate(keys)},
                                  distances)

    def test_series_and_writability_on_the_competitors_own_table(self):
        from tools.core.phonetics import EGYPTIAN_DISTANCES
        sub = self._space(["jmn"], EGYPTIAN_DISTANCES).sub
        assert chk.series_consonant("j", SERIES, sub) == "y" and chk.series_consonant("j", SERIES) != "y"
        assert chk.writable(("j", "m", "n"), SERIES, sub) and chk.writable(("ꜥ", "n"), SERIES, sub)
        assert not chk.writable(("x", "n"), SERIES, sub)

    def test_a_competitor_plant_is_spelled_open_and_seeded(self):
        from tools.core.phonetics import EGYPTIAN_DISTANCES
        space = self._space(["jmn", "rꜥ"], EGYPTIAN_DISTANCES)
        p = chk.plant_competitor(space, ("j", "m", "n"), ["4", "7"], rm.SEED, SERIES)
        assert p["competitor"] == "egyptian" and p["number"] == "4" and p["numbers"] == ["4", "7"]
        assert re.fullmatch(r"J[AE]-M[AIU]-N[AIU]", p["word"]) and p["spelled_from"] == "open"
        assert p == chk.plant_competitor(space, ("j", "m", "n"), ["4", "7"], rm.SEED, SERIES)
        assert re.fullmatch(r"R[AIU]-[AIU]", chk.plant_competitor(space, ("r", "ꜥ"), ["2"], rm.SEED, SERIES)["word"])
        keys = [("p", "t", "r"), ("m", "n", "r"), ("s", "d", "m"), ("n", "p", "r"), ("t", "m", "s"), ("k", "m", "t")]
        vowels = {re.sub(r"[^AEIOU-]", "", chk.plant_competitor(space, k, ["1"], rm.SEED, SERIES)["word"]) for k in keys}
        assert len(vowels) > 1                                  # each key draws from its own stream

    def test_a_competitor_s_t_and_d_are_not_spelled_with_zu(self):
        from tools.core.phonetics import EGYPTIAN_DISTANCES
        space = self._space(["ṯp", "ḏr"], EGYPTIAN_DISTANCES)
        assert chk.competitor_series(SERIES) == chk.lb_series(conventional=True)    # the grid and zu, A21's rows out
        for seed in range(20):
            assert re.fullmatch(r"T[AEIOU]-P[AEIOU]", chk.plant_competitor(space, ("ṯ", "p"), ["1"], seed, SERIES)["word"])
            assert re.fullmatch(r"Z[AEIOU]-R[AEIOU]", chk.plant_competitor(space, ("ḏ", "r"), ["2"], seed, SERIES)["word"])

    def test_a9_rows_carry_the_competitors_both_ways(self, tmp_path, monkeypatch):
        import test_root_match as trm

        from tools.core.phonetics import LUWIAN_DISTANCES
        from tools.core.root_index import RootIndex, write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        from tools.core import competitors as cp
        space = self._space(["kns", "prt"], LUWIAN_DISTANCES)
        far = cp.CompetitorSpace("far", {("g", "g", "g"): ["1"]}, LUWIAN_DISTANCES)
        engine = rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"), corpus_words=trm.CORPUS, competitors=[space, far])
        monkeypatch.setattr(chk, "_ENGINE", engine)
        semitic = chk.a9_one(({"number": "1", "word": "KA-NA-SI"}, 100, rm.SEED))
        assert semitic["competitor_fired"] == ["egyptian"] and semitic["recovered"]
        assert semitic["competitors"]["egyptian"] < rm.P_SIGNAL <= semitic["competitors"]["far"]
        assert "own_detected" not in semitic
        own = chk.a9_one(({"competitor": "egyptian", "number": "1", "word": "KA-NA-SI"}, 100, rm.SEED))
        assert own["own_detected"] and own["own_d_star"] == 0.0
        assert not own["recovered"]                 # a competitor's Number is no semitic_roots Number
        only = chk.a9_one(({"competitor": "egyptian", "number": "2", "word": "PA-RA-TA"}, 100, rm.SEED))
        assert only["own_detected"] and not only["detected"]        # its own null, not the Semitic one

    def test_summaries(self):
        rows = [{"consonants": 3, "detected": True, "recovered": True, "verdict": "x", "competitor_fired": ["luwian"]},
                {"consonants": 3, "detected": True, "recovered": True, "verdict": "x", "competitor_fired": []}]
        s = chk.power_summary(rows)["3"]
        assert s["blocked"] == 1 and s["blocked_share"] == 0.5 and s["competitor_fired"] == {"luwian": 1}
        own = [{"consonants": 2, "own_detected": d, "detected": sd} for d, sd in ((True, False), (True, False),
                                                                                (False, True))]
        c = chk.competitor_power_summary(own)["2"]
        assert c == {"n": 3, "detected": 2, "power": round(2 / 3, 4), "underpowered": False, "semitic_detected": 1}

    def test_run_a9_queries_both_kinds_on_an_engine_with_the_competitors(self, tmp_path, monkeypatch, capsys):
        import argparse

        import test_root_match as trm

        from tools.core.root_index import write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())

        def stub_plant_all(el, k, s, ser, gold, make=None):
            return ([{"number": "1", "word": "KA-NA-SI", "spelled_from": "open"}] if make is None else
                    [{**make(el[0]), "word": "PA-RA-TA"}]), []

        def stub_a9_one(job):
            p = job[0]
            row = {**p, "consonants": 3, "detected": "competitor" in p, "recovered": False, "verdict": "x"}
            return {**row, "own_detected": True} if "competitor" in p else row

        monkeypatch.setattr(chk, "plant_all", stub_plant_all)
        monkeypatch.setattr(chk, "a9_one", stub_a9_one)
        monkeypatch.setattr(chk, "_ENGINE", None)                     # run_a9 sets it; restored afterwards
        monkeypatch.setattr(chk, "_hashes", lambda index: {"pinned": "x"})   # another session's write cannot fail it
        chk.run_a9(argparse.Namespace(index=str(tmp_path / "x.sqlite"), n=10, seed=rm.SEED, names=False, workers=1,
                                      planted=1, out=str(tmp_path / "a9.json")))
        capsys.readouterr()
        assert [s.name for s in chk._ENGINE.competitors] == ["luwian", "egyptian", "hurrian"]
        summary = json.loads((tmp_path / "a9.json").read_text())["summary"]
        assert summary["planted"] == 1 and summary["power_by_consonants"]["3"]["detected"] == 0
        for c in summary["competitor_power"].values():
            assert c["planted"] == 1 and c["by_consonants"]["3"]["detected"] == 1


class TestGoldSkip:
    """A14: neither check queries a gold-set sign group before the gold run."""

    def test_a12_sample_skips_gold_words_and_counts_them(self, tmp_path):
        import test_root_match as trm
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        from tools.core.root_index import RootIndex, write_index
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        engine = rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"), corpus_words=trm.CORPUS)
        every, _ = chk.sample_words(trm.CORPUS, 100, rm.SEED, engine, set())
        gold = {chk.sign_group_key(w.lower()) for w in every[:3]}
        out, skipped = chk.sample_words(trm.CORPUS, 100, rm.SEED, engine, gold)
        assert out == every[3:] and skipped["gold"] == 3
        filled, _ = chk.sample_words(trm.CORPUS, len(every) - 3, rm.SEED, engine, gold)
        assert len(filled) == len(every) - 3 and not {chk.sign_group_key(w) for w in filled} & gold

    def test_a9_sets_aside_a_gold_spelling_and_plants_the_next_record(self):
        forms = ["*kanVs-", "*mVlk-", "*ṭayb-", "*šVmVn-", "*dabar-", "*rVʾš-"]
        eligible = [(str(n), _ps(f)) for n, f in enumerate(forms, 1)]
        every, none = chk.plant_all(eligible, len(eligible), rm.SEED, SERIES, set())
        assert not none and len({p["word"] for p in every}) == len(every)
        target = every[2]
        gold = {chk.sign_group_key(target["word"])}
        planted, skipped = chk.plant_all(eligible, len(eligible), rm.SEED, SERIES, gold)
        assert skipped == [target] and planted == [p for p in every if p is not target]
        short, _ = chk.plant_all(eligible, len(eligible) - 1, rm.SEED, SERIES, gold)
        assert len(short) == len(eligible) - 1 and target not in short

    def test_a_reading_twin_of_a_gold_word_is_skipped_too(self, tmp_path):
        import test_root_match as trm

        from tools.core.root_index import RootIndex, write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        engine = rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"), corpus_words=trm.CORPUS)
        words = ["KA-*301-SI", "MA-RU-KU", "DA-ME"]                 # *301 reads as NA: KA-*301-SI is KA-NA-SI
        out, skipped = chk.sample_words(words, 10, rm.SEED, engine, {("KA", "NA", "SI")})
        assert "KA-*301-SI" not in out and skipped["gold"] == 1
        twin = {"number": "1", "word": "KA-*301-SI"}
        planted, aside = chk.plant_all([("1", None)], 1, rm.SEED, SERIES, {("KA", "NA", "SI")}, make=lambda _: twin)
        assert planted == [] and aside == [twin]

    def test_the_checks_count_every_consonant(self, tmp_path):
        import test_root_match as trm

        from tools.core.root_index import RootIndex, write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        chk._ENGINE = rm.Shoresh(RootIndex.load(tmp_path / "x.sqlite"), corpus_words=trm.CORPUS)
        try:
            assert chk.a12_one("TA-SA-RE")["consonants"] == 3
        finally:
            chk._ENGINE = None

    def test_a9_draws_by_seed_and_lists_by_number(self):
        eligible = [(str(n), _ps("*kanVs-")) for n in range(10, 22)]
        draws = {tuple(p["number"] for p in chk.plant_all(eligible, 3, seed, SERIES, set())[0]) for seed in range(10)}
        assert len(draws) > 1 and all(list(d) == sorted(d) for d in draws)

    def test_both_checks_hand_the_gold_set_on_and_a9_reports_what_it_set_aside(self, tmp_path, monkeypatch, capsys):
        import argparse
        from collections import Counter

        import test_root_match as trm
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        from tools.core.root_index import write_index
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        seen = {"a9": []}
        set_aside = [{"number": "9", "word": "KU-RO", "key": "kr"}]
        monkeypatch.setattr(chk, "sample_words", lambda w, n, s, e, gold: (seen.update(a12=gold), ([], Counter()))[1])
        monkeypatch.setattr(chk, "plant_all",
                            lambda el, k, s, ser, gold, make=None: (seen["a9"].append(gold), ([], set_aside))[1])
        args = {"index": str(tmp_path / "x.sqlite"), "n": 10, "seed": rm.SEED, "names": False, "workers": 1,
                "planted": 5}
        monkeypatch.setattr(chk, "_hashes", lambda index: {"pinned": "x"})   # another session's write cannot fail it
        chk.run_a12(argparse.Namespace(**args, out=str(tmp_path / "a12.json")))
        chk.run_a9(argparse.Namespace(**args, out=str(tmp_path / "a9.json")))
        capsys.readouterr()
        handed = [seen["a12"], *seen["a9"]]
        assert len(seen["a9"]) == 4                                                 # Semitic, then 3 competitors
        assert all(g("KU-RO") and g("KU2-RO") and not g("KA-NA-SI") for g in handed)   # by name and by reading
        summary = json.loads((tmp_path / "a9.json").read_text())["summary"]
        assert summary["gold_skipped"] == [{"number": "9", "word": "KU-RO"}]
        assert list(summary["competitor_power"]) == ["luwian", "egyptian", "hurrian"]
        assert all(c["gold_skipped"] == [{"key": "kr", "word": "KU-RO"}] and c["keys"]
                   for c in summary["competitor_power"].values())

    def test_the_gold_set_is_a_report_input(self, tmp_path):
        index = tmp_path / "x.sqlite"
        index.write_bytes(b"")
        assert chk._hashes(index)["tests/fixtures/root_match_gold.v3.json"]


def _die(job) -> dict:
    import os
    os._exit(3)                     # a worker killed mid-run (OOM, SIGKILL)


def _a12_row(word: str) -> dict:
    return {"word": word, "miss": False, "paths_agree": True, "consonants": len(word.split("-"))}


class TestPool:
    """--workers > 1: rows come back in input order, and a worker that dies raises instead of hanging."""

    @pytest.fixture
    def a12_args(self, tmp_path, monkeypatch):
        import argparse
        from collections import Counter

        import test_root_match as trm

        from tools.core.root_index import write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        words = ["KA-NA-SI", "MA-RA-KU", "PA-RA-TA", "DA-ME", "SI-KI-NE", "KA-PA"]
        monkeypatch.setattr(chk, "sample_words", lambda w, n, s, e, gold: (words, Counter()))
        monkeypatch.setattr(chk, "_ENGINE", None)
        monkeypatch.setattr(chk, "_hashes", lambda index: {"pinned": "x"})   # another session's write cannot fail it
        return argparse.Namespace(index=str(tmp_path / "x.sqlite"), n=10, seed=rm.SEED, names=False, workers=2,
                                  out=str(tmp_path / "a12.json")), words

    def test_a12_rows_keep_input_order(self, a12_args, monkeypatch, capsys):
        args, words = a12_args
        monkeypatch.setattr(chk, "a12_one", _a12_row)
        chk.run_a12(args)
        capsys.readouterr()
        assert [r["word"] for r in json.loads(Path(args.out).read_text())["rows"]] == words

    def test_a12_dead_worker_raises_instead_of_hanging(self, a12_args, monkeypatch):
        from concurrent.futures.process import BrokenProcessPool
        args, _ = a12_args
        monkeypatch.setattr(chk, "a12_one", _die)
        with pytest.raises(BrokenProcessPool):
            chk.run_a12(args)
        assert not Path(args.out).exists()

    def test_a9_dead_worker_raises_instead_of_hanging(self, a12_args, monkeypatch):
        import argparse
        from concurrent.futures.process import BrokenProcessPool
        args, _ = a12_args

        def stub_plant_all(el, k, s, ser, gold, make=None):
            return ([{"number": "1", "word": "KA-NA-SI", "spelled_from": "open"}] if make is None else
                    [{**make(el[0]), "word": "PA-RA-TA"}]), []

        monkeypatch.setattr(chk, "plant_all", stub_plant_all)
        monkeypatch.setattr(chk, "a9_one", _die)
        out = Path(args.out).with_name("a9.json")
        with pytest.raises(BrokenProcessPool):
            chk.run_a9(argparse.Namespace(**{**vars(args), "out": str(out)}, planted=1))
        assert not out.exists()


class TestFrozenA4:
    def test_a9_reads_the_frozen_list_and_reports_absent_numbers(self, tmp_path, monkeypatch, capsys):
        import argparse

        import test_root_match as trm

        from tools.core.root_index import write_index
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        gold = tmp_path / "gold.json"
        gold.write_text(json.dumps({"primary_index_exclusions": {"1": "campaign_addition", "9999": "x"}}),
                        encoding="utf-8")
        seen = {}

        def stub_eligible(records, keys, exclusions):
            seen["exclusions"] = exclusions
            return [], Counter()

        from collections import Counter
        monkeypatch.setattr(chk, "GOLD_V3_PATH", gold)
        monkeypatch.setattr(chk, "eligible_records", stub_eligible)
        monkeypatch.setattr(chk, "plant_all", lambda el, k, s, ser, gold, make=None: ([], []))
        monkeypatch.setattr(chk, "_ENGINE", None)
        monkeypatch.setattr(chk, "_hashes", lambda index: {"pinned": "x"})   # another session's write cannot fail it
        chk.run_a9(argparse.Namespace(index=str(tmp_path / "x.sqlite"), n=10, seed=rm.SEED, names=False, workers=1,
                                      planted=1, out=str(tmp_path / "a9.json")))
        capsys.readouterr()
        assert seen["exclusions"] == {"1": "campaign_addition", "9999": "x"}
        assert chk._ENGINE.exclude == frozenset({"1", "9999"})
        assert json.loads((tmp_path / "a9.json").read_text())["summary"]["a4_absent"] == ["9999"]


class TestReport:
    def test_an_existing_report_is_never_overwritten(self, tmp_path):
        out = tmp_path / "a12.json"
        out.write_text("keep")
        index = tmp_path / "x.sqlite"
        index.write_bytes(b"")
        with pytest.raises(FileExistsError):
            chk.write_report(out, {"index": str(index)}, chk._hashes(index), rm.SEED)
        assert out.read_text() == "keep"
        assert not list(tmp_path.glob("a12.json.tmp-*"))
