"""Tests for tools/linear_a/validation/meaning_shuffle_power.py. The index is built in tmp_path from hand-written
records; the corpus, lexicon, rival-language files and family B's word list are hand-written too, so no test reads the
user's index, the shipped corpus or the lexica (the gold set is read, never written). The runs key their records
through the shipped correspondence table and read words through the sign registry, so they are `data` tests; the
helpers are `unit` tests."""
from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from shoresh_inputs import SHORESH

from tools.core.competitors import COMPETITORS
from tools.core.root_index import LEXICA, write_index
from tools.linear_a.validation import meaning_shuffle_power as power
from tools.linear_a.validation.root_match_checks import eligible_records, lb_series, plant
from tools.linear_a.validation.root_match_phase0 import sign_group_key

FOOD, ADMIN = frozenset({"food_drink"}), frozenset({"administrative"})
RECORDS = [
    {"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'wine'",
     "Analogues": {"Hebrew": "kns 'wine'", "Akkadian": "kanāsu 'wine'"}},
    {"Number": "2", "Proto-Semitic": "*mVlk-", "Meaning": "'king'",
     "Analogues": {"Hebrew": "mlk 'king'", "Akkadian": "malku 'king'"}},
    {"Number": "3", "Proto-Semitic": "*šVkar-", "Meaning": "'beer'",
     "Analogues": {"Hebrew": "škr 'beer'", "Arabic": "sakar 'wine'"}},
    {"Number": "4", "Proto-Semitic": "*ṭVpVr-", "Meaning": "'scribe'",
     "Analogues": {"Hebrew": "ṭpsr 'scribe'", "Akkadian": "ṭupšarru 'scribe'"}},
]


def _doc(support: str, *tokens: str) -> dict:
    return {"support": support, "transliteratedWords": list(tokens)}


CORPUS = {
    "d1": _doc("Tablet", "KA-NA-SI", "VIN", "1"),
    "d2": _doc("Tablet", "MA-RU-KU", "VIR", "2"),
    "d3": _doc("Tablet", "DA-ME", "VIN", "3"),
    "d4": _doc("Tablet", "SI-RU", "VIR", "4"),
    "d5": _doc("Tablet", "KU-NI-SU", "GRA", "5"),          # a gold-set word: set aside
    "d6": _doc("Tablet", "TA-NA-TI", "VIN", "6"),
}
SIGNS = ["KA", "NA", "SI", "MA", "RU", "KU", "DA", "ME", "TA", "TI", "PA", "RE", "SA", "NE"]
WORDS = ["-".join(p) for n in (2, 3) for p in itertools.islice(itertools.permutations(SIGNS, n), 0, None, 7)]


def _rivals(d: Path, gloss: bool = True) -> Path:
    for s in COMPETITORS:
        rows = [{"Number": "R1", "Consonantal_Root": "k-n-s", **({"Meaning": "wine"} if gloss else {})},
                {"Number": "R2", "Consonantal_Root": "m-r-k", **({"Meaning": "king"} if gloss else {})},
                {"Number": "R3", "Consonantal_Root": "t-p-r", **({"Meaning": "scribe"} if gloss else {})}]
        (d / s.file).write_text(json.dumps(rows), encoding="utf-8")
    return d


@pytest.fixture
def setup(tmp_path, monkeypatch):
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS, ensure_ascii=False), encoding="utf-8")
    lexica = tuple(replace(lx, path=tmp_path / f"{lx.name}.jsonl") for lx in LEXICA[:1])
    for lx in lexica:
        lx.path.write_text("", encoding="utf-8")
    index = tmp_path / "root_index.sqlite"
    write_index(index, roots, lexica)
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps(CORPUS), encoding="utf-8")
    lexicon = tmp_path / "lexicon.json"
    lexicon.write_text(json.dumps({"entries": []}), encoding="utf-8")
    rivals = tmp_path / "rivals"
    rivals.mkdir()
    monkeypatch.setattr(power, "CORPUS", corpus)
    monkeypatch.setattr(power, "ROOTS", roots)
    monkeypatch.setattr(power, "LEXICON", lexicon)
    monkeypatch.setattr(power, "RIVALS", _rivals(rivals))
    monkeypatch.setattr(power, "CORPUS_WORDS", WORDS)
    measured: list[str] = []
    for name in ("semitic_distance", "competitor_distance"):
        real = getattr(power.ms, name)

        def spying(*a, real=real):
            dist = real(*a)
            return lambda w, c: (measured.append(w), dist(w, c))[1]
        monkeypatch.setattr(power.ms, name, spying)
    small = ["--index", str(index), "--null-per-slot", "4", "--plants-per-pool", "3", "--calib-runs", "30",
             "--calib-perm", "19", "--runs", "6", "--n-perm", "19", "--k", "1,2", "--tau", "0,0.5", "--cap", "1"]
    return {"small": small, "measured": measured, "tmp": tmp_path, "rivals": rivals}


def _run(setup, *extra):
    out = setup["tmp"] / "out" / "power.json"
    rc = power.main(["--out", str(out), *setup["small"], *extra])
    return rc, (json.loads(out.read_text(encoding="utf-8")) if rc == 0 else None), out


class TestRun:
    pytestmark = SHORESH

    def test_no_real_word_ever_gets_a_distance(self, setup):
        rc, _, _ = _run(setup)
        assert rc == 0
        real = {sign_group_key(w) for d in CORPUS.values() for w in d["transliteratedWords"]}
        assert setup["measured"]
        assert not {w for w in setup["measured"] if sign_group_key(w) in real}

    def test_the_report_holds_calibration_and_power_for_every_reader(self, setup):
        _, rep, _ = _run(setup)
        assert rep["slots"]["n"] == 5 and rep["slots"]["gold_set_aside"] == 1
        tests = ["semitic", "luwian", "egyptian", "hurrian"]
        strata = ("none", "length", "fine")
        assert set(rep["calibration"]) == {f"{t} / {s}" for t in tests for s in strata}
        cal = rep["calibration"]["semitic / none"]
        assert set(cal) == {"rank", "count_0", "count_0.5", "cap_1"}
        assert 0 <= cal["rank"]["type_i"] <= 1 and 0 <= cal["rank"]["ks_p"] <= 1
        expected = {f"semitic plants / {t} test / {s}" for t in tests for s in strata}
        expected |= {f"{a} plants / {t} test / {s}" for a in tests[1:] for t in ("semitic", a) for s in strata}
        assert set(rep["power"]) == expected
        curve = rep["power"]["semitic plants / semitic test / none"]
        assert set(curve["curves"]["rank"]["power"]) == {"1", "2"}
        assert curve["plantable_slots"] == 4 and curve["planted"] == {"1": 1, "2": 2}
        assert rep["pools"]["semitic"] == {"0 2": 1, "0 3": 1, "1 3": 2}       # (context, shape) → plants
        assert rep["power"]["luwian plants / luwian test / none"]["plantable_slots"] == 3
        assert rep["sha256"]["tagger"] and rep["sha256"]["semitic_roots"]

    def test_conventional_values_unmap_a_slot_and_its_decoys(self, setup, monkeypatch):
        corpus = setup["tmp"] / "s306.json"
        corpus.write_text(json.dumps({**CORPUS, "d7": _doc("Tablet", "KU-*306-NU", "VIN", "7")}), encoding="utf-8")
        monkeypatch.setattr(power, "CORPUS", corpus)
        monkeypatch.setattr(power, "CORPUS_WORDS", [*WORDS, "*306-KA", "KA-*306-NA", "*118-NA", "NA-*118-SI"])
        rc, rep, _ = _run(setup, "--no-competitors")
        assert rc == 0 and rep["sign_values"] == "all" and rep["slots"]["unmapped"] == []
        assert rep["slots"]["n"] == 6 and "KU-*306-NU" not in setup["measured"]
        out = setup["tmp"] / "out" / "conv.json"
        setup["measured"].clear()
        assert power.main(["--out", str(out), *setup["small"], "--no-competitors", "--conventional-values"]) == 0
        rep = json.loads(out.read_text(encoding="utf-8"))
        assert rep["sign_values"] == "conventional" and rep["slots"]["unmapped"] == ["KU-*306-NU"]
        assert rep["slots"]["n"] == 5
        assert not {s for w in setup["measured"] for s in w.split("-")} & {"*306", "*118"}   # no decoy, no plant

    def _plant_words(self):
        eligible, _ = eligible_records(RECORDS, set(), {})
        return [plant(n, key, power.SEED, lb_series())["word"] for n, key in eligible]

    def test_a_plant_spelled_as_a_corpus_word_is_dropped_unmeasured(self, setup, monkeypatch):
        clash = self._plant_words()[0]
        corpus = setup["tmp"] / "clash.json"
        corpus.write_text(json.dumps({**CORPUS, "d9": _doc("Tablet", clash)}), encoding="utf-8")   # no logogram
        monkeypatch.setattr(power, "CORPUS", corpus)
        rc, rep, _ = _run(setup)
        assert rc == 0 and rep["dropped"]["semitic: a corpus or gold word"] >= 1
        assert sign_group_key(clash) not in {sign_group_key(w) for w in setup["measured"]}

    def test_a_plant_spelled_as_a_gold_word_is_dropped_unmeasured(self, setup, monkeypatch):
        clash = self._plant_words()[0]
        real_guard = power.gold_guard

        def guard(path, **kw):
            g = real_guard(path, **kw)
            return lambda w: w == clash or g(w)
        monkeypatch.setattr(power, "gold_guard", guard)
        rc, rep, _ = _run(setup)
        assert rc == 0 and rep["dropped"]["semitic: a corpus or gold word"] >= 1
        assert clash not in setup["measured"]

    def test_the_plants_are_spelled_in_the_run_s_mode(self, setup, monkeypatch):
        seen, real = [], power.lb_series
        monkeypatch.setattr(power, "lb_series", lambda **kw: seen.append(kw) or real(**kw))
        assert _run(setup, "--no-competitors")[0] == 0
        assert power.main(["--out", str(setup["tmp"] / "out" / "conv.json"), *setup["small"], "--no-competitors",
                           "--conventional-values"]) == 0
        assert seen == [{"conventional": False}, {"conventional": True}]

    def test_the_gold_guard_reads_in_the_run_s_mode(self, setup, monkeypatch):
        seen, real = [], power.gold_guard
        monkeypatch.setattr(power, "gold_guard", lambda path, **kw: seen.append(kw) or real(path, **kw))
        assert _run(setup, "--no-competitors")[0] == 0
        assert power.main(["--out", str(setup["tmp"] / "out" / "conv.json"), *setup["small"], "--no-competitors",
                           "--conventional-values"]) == 0
        assert seen == [{"conventional": False}, {"conventional": True}]

    def test_the_length_strata_reach_simulate(self, setup, monkeypatch):
        seen = []
        real = power.ms.simulate

        def spy(*a, **kw):
            seen.append(kw.get("strata"))
            return real(*a, **kw)
        monkeypatch.setattr(power.ms, "simulate", spy)
        assert _run(setup, "--no-competitors")[0] == 0
        shapes = sorted(str(power.shape(w)) for w in ("DA-ME", "KA-NA-SI", "MA-RU-KU", "SI-RU", "TA-NA-TI"))
        assert None in seen and sorted(next(s for s in seen if s is not None)) == shapes

    def test_the_shipped_roots_schema_gives_the_same_plants(self, setup, monkeypatch):
        v2 = {"schema_version": 2, "roots": [
            {"id": r["Number"], "ps": r["Proto-Semitic"], "meaning": r["Meaning"],
             "reflexes": [{"lang": lang, "text": t} for lang, t in r["Analogues"].items()]} for r in RECORDS]}
        path = setup["tmp"] / "semitic_roots_v2.json"
        path.write_text(json.dumps(v2, ensure_ascii=False), encoding="utf-8")
        _, listed, out = _run(setup, "--no-competitors")
        out.unlink()
        monkeypatch.setattr(power, "ROOTS", path)
        rc, shipped, _ = _run(setup, "--no-competitors")
        assert rc == 0
        assert (shipped["semitic_eligible"], shipped["pools"]) == (listed["semitic_eligible"], listed["pools"])

    def test_a_plant_is_its_word_across_pools(self, setup, monkeypatch):
        """A word fitting two contexts sits in two pools ('wine steward' fits the wine and the men tablets); simulate
        is told it is one plant, so it fills one slot. Each plant's name is the word whose row stands beside it."""
        roots, index = setup["tmp"] / "roots_steward.json", setup["tmp"] / "index_steward.sqlite"
        steward = {"Number": "5", "Proto-Semitic": "*sVkVn-", "Meaning": "'wine steward'",
                   "Analogues": {"Hebrew": "skn 'steward'", "Akkadian": "šaknu 'wine steward'"}}
        roots.write_text(json.dumps([*RECORDS, steward], ensure_ascii=False), encoding="utf-8")
        write_index(index, roots, tuple(replace(lx, path=setup["tmp"] / f"{lx.name}.jsonl") for lx in LEXICA[:1]))
        monkeypatch.setattr(power, "ROOTS", roots)
        seen, by_word = [], {}
        real_sim, real_dist = power.ms.simulate, power.ms.semitic_distance

        def spy(*a, **kw):
            if a[3]:
                seen.append((a[2], kw.get("plant_ids")))
            return real_sim(*a, **kw)

        def recording(*a):
            dist = real_dist(*a)
            return lambda w, c: (by_word.setdefault(w, []).append(d := dist(w, c)), d)[1]
        monkeypatch.setattr(power.ms, "simulate", spy)
        monkeypatch.setattr(power.ms, "semitic_distance", recording)
        rc, _, _ = _run(setup, "--no-competitors", "--index", str(index))
        assert rc == 0 and seen
        for rows, ids in seen:
            assert ids is not None and set(ids) == set(rows)
            assert all(len(ids[key]) == len(rows[key]) for key in rows)
            assert all(row == by_word[w][:len(row)] for key in rows for w, row in zip(ids[key], rows[key]))
            named = [w for ws in ids.values() for w in ws]
            assert len(named) > len(set(named))                                      # a word sits in two pools
            assert set(named) <= set(setup["measured"])

    def test_fine_strata_split_a_sign_count_by_skeleton(self, setup, monkeypatch):
        """A-NA-SI and A-RU-KU have three signs and a skeleton of two: the fine strata set them apart from KA-NA-SI,
        MA-RU-KU and TA-NA-TI, which the length strata keep together. QA-NA-SI's QA has two readings, so it stands
        alone and falls back to its length."""
        corpus = setup["tmp"] / "vowel.json"
        corpus.write_text(json.dumps({**CORPUS, "d7": _doc("Tablet", "A-NA-SI", "VIN", "7"),
                                      "d8": _doc("Tablet", "A-RU-KU", "VIR", "8"),
                                      "d9": _doc("Tablet", "QA-NA-SI", "VIN", "9")}), encoding="utf-8")
        monkeypatch.setattr(power, "CORPUS", corpus)
        monkeypatch.setattr(power, "CORPUS_WORDS", [*WORDS, "A-KA-NA", "A-SI-RU", "A-TA-MA", "A-ME-PA", "A-NE-RE",
                                                    "QA-KA-RE", "QA-TA-MA", "QA-RU-PA", "QA-ME-NE", "QA-SA-TI"])
        seen = []
        real = power.ms.simulate

        def spy(*a, **kw):
            seen.append(kw.get("strata"))
            return real(*a, **kw)
        monkeypatch.setattr(power.ms, "simulate", spy)
        rc, rep, _ = _run(setup, "--no-competitors")
        assert rc == 0 and rep["slots"]["n"] == 8
        assert {"semitic / fine", "semitic plants / semitic test / fine"} <= {*rep["calibration"], *rep["power"]}
        assert rep["slots"]["per_fine_stratum"] == {"3|2|1": 2, "2|2|1": 2, "3|3|1": 3, "3": 1}
        assert ["3|2|1", "3|2|1", "2|2|1", "3|3|1", "3|3|1", "3", "2|2|1", "3|3|1"] in seen       # sorted words
        assert ["3", "3", "2", "3", "3", "3", "2", "3"] in seen

    def test_fresh_null_reaches_every_simulate_and_is_reported(self, setup, monkeypatch):
        seen = []
        real = power.ms.simulate

        def spy(*a, **kw):
            seen.append(kw.get("fresh_null"))
            return real(*a, **kw)
        monkeypatch.setattr(power.ms, "simulate", spy)
        rc, rep, _ = _run(setup, "--no-competitors")
        assert rc == 0 and rep["fresh_null"] is False and set(seen) == {False}
        seen.clear()
        rc, _, _ = _run(setup, "--no-competitors", "--fresh-null", "--out", str(setup["tmp"] / "fresh.json"))
        rep = json.loads((setup["tmp"] / "fresh.json").read_text(encoding="utf-8"))
        assert rc == 0 and rep["fresh_null"] is True and seen and set(seen) == {True}
        per_slot = rep["null"]["per_slot"]
        assert rep["null"]["pools_below_runs"] == sum(n < 30 for n in per_slot) == len(per_slot)   # 4 decoys, 30 runs

    def test_a_k_past_the_plants_is_marked_plant_limited(self, setup):
        """Four slots can take a Semitic plant, so k = 5 plants at most four: its row is marked, and k80 counts
        plants, not k."""
        rc, rep, _ = _run(setup, "--no-competitors", "--k", "1,5")
        cell = rep["power"]["semitic plants / semitic test / none"]
        assert rc == 0 and cell["plant_limited"] == [5] and cell["planted_range"]["5"][1] <= 4
        assert all(c["k80"] in (None, *cell["planted"].values()) for c in cell["curves"].values())

    def test_the_seed_fixes_the_report(self, setup):
        _, a, out = _run(setup)
        out.unlink()
        _, b, _ = _run(setup)
        a.pop("seconds"), b.pop("seconds")
        assert a == b

    def test_an_existing_out_is_never_overwritten(self, setup):
        out = setup["tmp"] / "kept.json"
        out.write_text("kept", encoding="utf-8")
        assert power.main(["--out", str(out), *setup["small"]]) == 2
        assert out.read_text(encoding="utf-8") == "kept" and not setup["measured"]       # refused before any work

    def test_no_competitors_runs_the_semitic_side_alone(self, setup):
        rc, rep, _ = _run(setup, "--no-competitors")
        assert rc == 0
        assert set(rep["calibration"]) == {"semitic / none", "semitic / length", "semitic / fine"}


class TestStops:
    pytestmark = SHORESH

    def test_rival_files_without_glosses_stop_with_exit_2(self, setup, monkeypatch, capsys):
        monkeypatch.setattr(power, "RIVALS", _rivals(setup["rivals"], gloss=False))
        assert _run(setup)[0] == 2
        assert capsys.readouterr().err.splitlines()[-1].startswith("stopped: ")      # after the progress lines

    def test_the_shipped_rival_files_carry_no_glosses_so_the_arm_stops(self, setup, monkeypatch):
        monkeypatch.setattr(power, "RIVALS", power.DATA_DIR)
        assert _run(setup)[0] == 2
        assert _run(setup, "--no-competitors")[0] == 0

    def test_a_missing_rival_file_stops_with_exit_2(self, setup, capsys):
        next(setup["rivals"].glob("*.json")).unlink()
        rc, _, out = _run(setup)
        assert rc == 2 and not out.exists()
        assert "stopped: " in capsys.readouterr().err

    def test_a_corrupt_rival_file_stops_with_exit_2(self, setup):
        next(setup["rivals"].glob("*.json")).write_text("{bad", encoding="utf-8")
        assert _run(setup)[0] == 2

    @pytest.mark.parametrize("name", ["CORPUS", "ROOTS", "LEXICON"])
    def test_a_missing_input_stops_as_not_in_this_checkout(self, setup, monkeypatch, capsys, name):
        monkeypatch.setattr(power, name, setup["tmp"] / "missing.json")
        assert _run(setup)[0] == 2
        assert "is not in this checkout" in capsys.readouterr().err

    @pytest.mark.parametrize("name", ["CORPUS", "ROOTS", "LEXICON"])
    def test_a_corrupt_input_stops_with_exit_4(self, setup, monkeypatch, name):
        bad = setup["tmp"] / "bad.json"
        bad.write_text("{bad", encoding="utf-8")
        monkeypatch.setattr(power, name, bad)
        assert _run(setup)[0] == 4

    def test_a_roots_file_of_another_schema_stops_with_exit_4(self, setup, monkeypatch):
        bad = setup["tmp"] / "roots_v9.json"
        bad.write_text(json.dumps({"schema_version": 9, "records": []}), encoding="utf-8")
        monkeypatch.setattr(power, "ROOTS", bad)
        assert _run(setup)[0] == 4

    @pytest.mark.parametrize("corpus", [[1, 2], {"d1": "KA-NA-SI"}, {"d1": {"transliteratedWords": "KA"}},
                                        {"d1": {"transliteratedWords": [1]}},
                                        {**CORPUS, "d9": {"transliteratedWords": "KA-NA"}}])    # one bad document
    def test_a_corpus_of_the_wrong_shape_stops_with_exit_4(self, setup, monkeypatch, corpus):
        path = setup["tmp"] / "bad.json"
        path.write_text(json.dumps(corpus), encoding="utf-8")
        monkeypatch.setattr(power, "CORPUS", path)
        assert _run(setup)[0] == 4

    def test_an_unreadable_gold_set_stops_with_exit_3(self, setup, monkeypatch):
        monkeypatch.setattr(power, "GOLD", setup["tmp"] / "missing.json")
        assert _run(setup)[0] == 3

    def test_a_missing_index_stops_as_not_in_this_checkout(self, setup, capsys):
        out = setup["tmp"] / "out.json"
        argv = ["--out", str(out), *setup["small"]]
        argv[argv.index("--index") + 1] = str(setup["tmp"] / "none.sqlite")
        assert power.main(argv) == 2
        assert "is not in this checkout" in capsys.readouterr().err

    def test_an_index_changed_while_loading_stops_with_exit_2(self, setup, monkeypatch):
        index = Path(setup["small"][1])
        load = power.RootIndex.load

        def changing(path, **kw):
            idx = load(path, **kw)
            with open(index, "ab") as f:
                f.write(b"\0")
            return idx
        monkeypatch.setattr(power.RootIndex, "load", staticmethod(changing))
        rc, _, out = _run(setup)
        assert rc == 2 and not out.exists()

    def test_the_report_stamps_the_index_as_loaded(self, setup):
        before = hashlib.sha256(Path(setup["small"][1]).read_bytes()).hexdigest()
        assert _run(setup)[1]["sha256"]["index"] == before

    @pytest.mark.parametrize(("name", "doc"), [("ROOTS", 5), ("ROOTS", [1, 2]), ("LEXICON", {"entries": 5}),
                                               ("LEXICON", {"entries": [1]}), ("LEXICON", [])])
    def test_roots_or_a_lexicon_of_the_wrong_shape_stops_with_exit_4(self, setup, monkeypatch, name, doc):
        path = setup["tmp"] / "shape.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        monkeypatch.setattr(power, name, path)
        rc, _, _ = _run(setup, "--allow-stale")
        assert rc == 4 and not setup["measured"]

    def test_a_changed_tagger_stops_with_exit_4_before_any_distance(self, setup, monkeypatch):
        def changed():
            raise power.sg.TaggerChanged("tag_semantic_fields.py sha256 00000000 is not the frozen one")
        monkeypatch.setattr(power.sg, "tagger", changed)
        assert _run(setup)[0] == 4 and not setup["measured"]

    def test_a_rival_file_of_the_wrong_shape_stops_with_exit_2(self, setup):
        next(setup["rivals"].glob("*.json")).write_text("[1]", encoding="utf-8")
        assert _run(setup)[0] == 2 and not setup["measured"]

    def test_a_stale_index_stops_with_exit_2_unless_allowed(self, setup):
        roots = setup["tmp"] / "semitic_roots.json"
        roots.write_text(roots.read_text(encoding="utf-8") + "\n", encoding="utf-8")   # an input the index hashed
        assert _run(setup)[0] == 2
        assert _run(setup, "--allow-stale")[0] == 0

    def test_a_corrupt_index_stops_with_exit_2(self, setup):
        Path(setup["small"][1]).write_bytes(b"not a database")
        assert _run(setup)[0] == 2

    def test_a_corpus_with_no_slot_stops_with_exit_4(self, setup, monkeypatch):
        path = setup["tmp"] / "bare.json"
        path.write_text(json.dumps({"d1": _doc("Tablet", "KA-NA-SI", "1")}), encoding="utf-8")      # no logogram
        monkeypatch.setattr(power, "CORPUS", path)
        rc, _, out = _run(setup)
        assert rc == 4 and not out.exists()

    @pytest.mark.parametrize("bad", [["--k", "abc"], ["--k", ""], ["--k", "0"], ["--tau", "x"], ["--tau", ""],
                                     ["--runs", "0"], ["--calib-runs", "0"], ["--n-perm", "0"], ["--calib-perm", "0"],
                                     ["--null-per-slot", "0"], ["--plants-per-pool", "0"], ["--alpha", "0"],
                                     ["--alpha", "1"], ["--cap", "x"], ["--cap", ""], ["--cap", "0"]])
    def test_bad_arguments_are_refused_before_any_work(self, setup, bad):
        with pytest.raises(SystemExit) as e:
            _run(setup, *bad)
        assert e.value.code == 2 and not setup["measured"]

    def test_an_out_that_cannot_be_written_stops_before_any_distance(self, setup):
        blocker = setup["tmp"] / "a_file"
        blocker.write_text("", encoding="utf-8")
        assert power.main(["--out", str(blocker / "power.json"), *setup["small"]]) == 2
        assert not setup["measured"]

    def test_the_report_stamps_the_bytes_that_were_loaded(self, setup, monkeypatch):
        corpus = setup["tmp"] / "corpus.json"
        before = hashlib.sha256(corpus.read_bytes()).hexdigest()
        real = power.ms.anchored

        def editing(*a, **kw):
            out = real(*a, **kw)
            corpus.write_text(json.dumps({**CORPUS, "d9": _doc("Tablet", "PA-RE")}), encoding="utf-8")
            return out
        monkeypatch.setattr(power.ms, "anchored", editing)
        assert _run(setup)[1]["sha256"]["corpus"] == before

    def test_decoys_spelled_as_corpus_words_are_dropped_and_counted(self, setup, monkeypatch):
        real = power.rm.Shoresh.family_b

        def with_a_real_word(self, w, n, seed):
            fabs, g = real(self, w, n, seed)
            return [*fabs, ["KA", "NA", "SI"]], g
        monkeypatch.setattr(power.rm.Shoresh, "family_b", with_a_real_word)
        rc, rep, _ = _run(setup)
        assert rc == 0 and rep["dropped"]["null: a corpus or gold word"] >= 5      # one per slot

    def test_a_slot_with_no_decoy_stops_with_exit_5(self, setup, monkeypatch):
        monkeypatch.setattr(power.rm.Shoresh, "family_b", lambda self, w, n, seed: ([], 0))
        rc, _, out = _run(setup)
        assert rc == 5 and not out.exists()


class TestHelpers:
    def test_the_file_runs_as_a_command(self, tmp_path):
        kept = tmp_path / "kept.json"
        kept.write_text("kept", encoding="utf-8")
        r = subprocess.run([sys.executable, str(Path(power.__file__)), "--out", str(kept)], capture_output=True,
                           text=True, check=False)
        assert r.returncode == 2 and "never overwritten" in r.stderr                 # refused before any data read

    def test_a_test_that_sets_no_corpus_reads_an_empty_one(self):
        assert power.CORPUS.read_text(encoding="utf-8") == "{}"         # conftest's stand-in

    def test_shape_caps_at_five(self):
        assert power.shape is power.ms.shape                     # the shapes the test command stratifies by
        assert [power.shape(w) for w in ("KA-NA", "KA-NA-SI", "A-B-C-D-E-F-G")] == [2, 3, 5]

    def test_the_capped_scorer_negates_the_capped_distance(self):
        sc = power.scorers([0.5], [1.0, 2.0])
        assert sc["cap_1"]([0.2, 3.0]) == pytest.approx([-0.2, -1.0])
        assert sc["cap_2"]([0.2, 3.0]) == pytest.approx([-0.2, -2.0])

    def test_fine_strata_key_on_what_family_b_keeps_and_fold_singletons(self):
        keys = [(3, 2, 1), (3, 2, 1), (3, 3, 1), (3, 3, 1), (2, 2, 1), (3, 3, 2)]
        assert power.ms.fine_strata(keys) ==["3|2|1", "3|2|1", "3|3|1", "3|3|1", "2", "3"]

    def test_k80_is_the_planted_count_at_the_least_k_at_eighty_percent(self):
        assert power.k80({5: 0.2, 10: 0.8, 20: 0.95}, {5: 5, 10: 10, 20: 20}) == 10
        assert power.k80({5: 0.2, 10: 0.8, 20: 0.95}, {5: 5, 10: 7.5, 20: 7.5}) == 7.5
        assert power.k80({5: 0.2, 10: 0.79}, {5: 5, 10: 10}) is None

    def test_pools_are_keyed_by_context_and_shape_and_capped(self):
        items = [("KA-NA", FOOD), ("KA-NA-SI", FOOD), ("MA-RU", ADMIN), ("SI-RU", FOOD | ADMIN), ("DA-ME", FOOD)]
        pools = power.pool_by_shape(items, [FOOD, ADMIN], cap=2, seed=1)
        assert set(pools) == {(0, 2), (0, 3), (1, 2)}
        assert len(pools[(0, 2)]) == 2 and set(pools[(0, 2)]) <= {"KA-NA", "SI-RU", "DA-ME"}
        assert pools[(1, 2)] == ["MA-RU", "SI-RU"]
        assert pools == power.pool_by_shape(items, [FOOD, ADMIN], cap=2, seed=1)
