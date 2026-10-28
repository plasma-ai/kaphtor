"""Tests for tools/core/meaning_shuffle.py and tools/linear_a/validation/meaning_shuffle.py. Matrices and corpora
are hand-written; the one index is built in tmp_path from hand-written records, so no test reads the user's index or
the shipped corpus. The engine and command tests key their records through the shipped correspondence table and
read words through the sign registry, so they are `data` tests; the statistics, the null and the simulation are
`unit` tests."""
from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from shoresh_inputs import SHORESH

from tools.core import meaning_shuffle as ms
from tools.core import root_match as rm
from tools.core import semantic_gate as sg
from tools.core.competitors import COMPETITORS, CompetitorSpace
from tools.core.root_index import LEXICA, RootIndex, write_index
from tools.linear_a.validation import meaning_shuffle as cli

INF = rm.INF
FOOD, ADMIN, DEITY = frozenset({"food_drink"}), frozenset({"administrative"}), frozenset({"deity"})


# --- statistics ---

class TestTCount:
    def test_counts_words_within_tau_of_their_own_context(self):
        D = [[0.0, 1.0], [1.0, 0.3], [2.0, 2.0]]
        assert ms.t_count(D, [0, 1, 0], 0.3) == 2
        assert ms.t_count(D, [1, 0, 0], 0.3) == 0

    def test_tau_is_inclusive_and_inf_never_counts(self):
        assert ms.t_count([[0.5], [INF]], [0, 0], 0.5) == 1


class TestTRank:
    def test_a_word_nearer_its_own_context_than_every_other_scores_one(self):
        assert ms.t_rank([[0.0, 1.0, 2.0]], [0]) == 1.0

    def test_farther_than_every_other_scores_zero(self):
        assert ms.t_rank([[2.0, 1.0, 0.0]], [0]) == 0.0

    def test_ties_count_half(self):
        assert ms.t_rank([[1.0, 1.0, 2.0]], [0]) == 0.75

    def test_a_word_equally_near_everything_or_nothing_scores_half(self):
        assert ms.t_rank([[1.0, 1.0], [INF, INF]], [0, 1]) == 1.0

    def test_sums_over_words(self):
        assert ms.t_rank([[0.0, 1.0], [0.0, 1.0]], [0, 1]) == 1.0


class TestTCap:
    def test_sums_the_own_context_distances_capped_and_negated(self):
        assert ms.t_cap([[0.2, 0.0], [1.0, 0.5], [3.0, 0.0]], [0, 1, 0], 1.0) == pytest.approx(-(0.2 + 0.5 + 1.0))

    def test_a_near_match_beats_a_far_one_and_inf_costs_the_cap(self):
        assert ms.t_cap([[0.1, INF]], [0], 2.0) > ms.t_cap([[0.1, 1.5]], [1], 2.0) > ms.t_cap([[0.1, INF]], [1], 2.0)
        assert ms.t_cap([[INF]], [0], 2.0) == -2.0


class TestShape:
    def test_sign_counts_of_five_or_more_share_a_shape(self):
        assert [ms.shape(w) for w in ("KA-NA", "KA-NA-SI", "A-B-C-D-E", "A-B-C-D-E-F-G")] == [2, 3, 5, 5]


# --- the null ---

class TestPermutations:
    def test_each_shuffle_keeps_the_multiset(self):
        assign = [0, 0, 0, 1, 1, 2]
        for perm in ms.permutations(assign, 50, seed=7):
            assert Counter(perm) == Counter(assign)

    def test_the_seed_fixes_the_draws_and_draws_differ(self):
        assign = list(range(10))
        a = list(ms.permutations(assign, 5, seed=1))
        assert a == list(ms.permutations(assign, 5, seed=1))
        assert a != list(ms.permutations(assign, 5, seed=2))
        assert len({tuple(p) for p in a}) == 5

    def test_labels_move_only_inside_a_stratum(self):
        assign = [0, 1, 2, 3, 4, 5]
        strata = ["x", "x", "x", "y", "y", "y"]
        moved = set()
        for perm in ms.permutations(assign, 200, seed=3, strata=strata):
            assert sorted(perm[:3]) == [0, 1, 2] and sorted(perm[3:]) == [3, 4, 5]
            moved |= {i for i, (a, b) in enumerate(zip(assign, perm)) if a != b}
        assert moved == set(range(6))


class TestPValue:
    def test_the_observed_pairing_counts_among_the_permutations(self):
        assert ms.p_value(5, [1, 2, 3]) == 0.25
        assert ms.p_value(5, []) == 1.0

    def test_ties_with_the_observed_count_against_it(self):
        assert ms.p_value(3, [3, 3, 1, 1]) == 0.6


class TestShuffleTest:
    def test_a_planted_pairing_is_detected(self):
        rng = random.Random(0)
        assign = [rng.randrange(4) for _ in range(40)]
        D = [[0.0 if j == a else 1.0 for j in range(4)] for a in assign]
        out = ms.shuffle_test(D, assign, lambda D, a: ms.t_count(D, a, 0.3), n=999, seed=1)
        assert out["observed"] == 40
        assert out["p"] == 0.001
        assert out["null_mean"] < 20

    def test_a_word_equidistant_from_every_context_carries_no_evidence(self):
        D = [[0.4, 0.4, 0.4]] * 30
        out = ms.shuffle_test(D, [i % 3 for i in range(30)], ms.t_rank, n=99, seed=1)
        assert out["p"] == 1.0

    @pytest.mark.parametrize("stat", ["count", "rank"])
    def test_under_the_null_p_is_calibrated(self, stat):
        """D drawn without regard to the pairing: about 5% of runs reach p ≤ 0.05."""
        rng = random.Random(11)
        f = ms.t_rank if stat == "rank" else (lambda D, a: ms.t_count(D, a, 0.3))
        hits, runs = 0, 400
        for r in range(runs):
            assign = [rng.randrange(5) for _ in range(30)]
            D = [[rng.choice([0.0, 0.3, 0.6, 1.0, INF]) for _ in range(5)] for _ in range(30)]
            hits += ms.shuffle_test(D, assign, f, n=99, seed=r)["p"] <= 0.05
        assert 0.02 <= hits / runs <= 0.09


# --- the words and their contexts ---

def _doc(support: str, *tokens: str) -> dict:
    return {"support": support, "transliteratedWords": list(tokens)}


CORPUS = {
    "d1": _doc("Tablet", "KA-NA-SI", "VIN", "1"),
    "d2": _doc("Stone vessel", "JA-SA-SA-RA-ME"),
    "d3": _doc("Tablet", "KA-NA-SI", "GRA", "5"),
    "d4": _doc("Tablet", "MA-RU-KU", "VIR", "2"),
    "d5": _doc("Tablet", "DA-ME"),
}


class TestAnchored:
    def test_logogram_anchoring_leaves_document_type_words_out(self):
        out = ms.anchored(CORPUS, "logogram")
        assert set(out) == {"KA-NA-SI", "MA-RU-KU"}
        assert out["KA-NA-SI"] == frozenset({"food_drink", "agriculture"})
        assert out["MA-RU-KU"] == frozenset({"administrative", "kinship"})

    def test_all_adds_the_document_type_and_keeps_unknowns_out(self):
        out = ms.anchored(CORPUS, "all")
        assert set(out) == {"KA-NA-SI", "MA-RU-KU", "JA-SA-SA-RA-ME"}
        assert out["JA-SA-SA-RA-ME"] == frozenset({"ritual_cultic", "deity"})

    def test_an_unknown_source_is_refused(self):
        with pytest.raises(ValueError):
            ms.anchored(CORPUS, "support")


class TestContextMatrix:
    def test_rows_are_words_and_columns_contexts(self):
        D = ms.context_matrix(["a", "b"], [FOOD, ADMIN], lambda w, c: (w == "b") + 10 * (c == ADMIN))
        assert D == [[0, 10], [1, 11]]


# --- distances ---

RECORDS = [
    {"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'wine'", "Analogues": {}},
    {"Number": "2", "Proto-Semitic": "*mVlk-", "Meaning": "'king'", "Analogues": {}},
]


@pytest.fixture(scope="module")
def engine(tmp_path_factory) -> rm.Shoresh:
    d = tmp_path_factory.mktemp("meaning_shuffle")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS, ensure_ascii=False), encoding="utf-8")
    lexica = tuple(replace(lx, path=d / f"{lx.name}.jsonl") for lx in LEXICA[:1])
    for lx in lexica:
        lx.path.write_text("", encoding="utf-8")
    write_index(d / "root_index.sqlite", roots, lexica)
    return rm.Shoresh(RootIndex.load(d / "root_index.sqlite"), corpus_words=["KA-NA-SI", "MA-RU-KU", "DA-ME"],
                      contexts=sg.Contexts({}))


class TestSemiticDistance:
    pytestmark = SHORESH

    def test_a_fitting_context_gives_the_ungated_distance(self, engine):
        dist = ms.semitic_distance(engine)
        _, vs = engine.clusters("KA-NA-SI", top=0)
        assert dist("KA-NA-SI", FOOD) == engine.d_star(vs)
        assert dist("KA-NA-SI", FOOD) < INF

    def test_the_gate_keeps_other_domains_out(self, engine):
        dist = ms.semitic_distance(engine)
        assert dist("KA-NA-SI", ADMIN) > dist("KA-NA-SI", FOOD)
        assert dist("MA-RU-KU", ADMIN) < dist("MA-RU-KU", FOOD)

    def test_a_context_no_root_fits_is_inf(self, engine):
        assert ms.semitic_distance(engine)("KA-NA-SI", DEITY) == INF


class TestCompetitorDistance:
    pytestmark = SHORESH

    def test_only_keys_whose_numbers_fit_are_searched(self, engine):
        spec = SimpleNamespace(distances={}, guttural_transparent=True)
        space = CompetitorSpace("toy", {("k", "n", "s"): ["L1"], ("m", "l", "k"): ["L2"]}, spec.distances)
        doms = {"L1": FOOD, "L2": ADMIN}
        dist = ms.competitor_distance(space, spec, doms, engine)
        vs = rm.variants(engine.word_readings("KA-NA-SI"), "KA-NA-SI")
        assert dist("KA-NA-SI", FOOD) == space.d_star(vs)
        assert dist("KA-NA-SI", ADMIN) > dist("KA-NA-SI", FOOD)
        assert dist("KA-NA-SI", DEITY) == INF


class TestCompetitorDomains:
    def test_domains_come_from_the_meaning_gloss(self, tmp_path):
        (tmp_path / "toy_roots.json").write_text(json.dumps(
            [{"Number": "L1", "Meaning": "wine"}, {"Number": "L2", "Meaning": "king"}, {"Number": "L3"}]),
            encoding="utf-8")
        doms = ms.competitor_domains(SimpleNamespace(file="toy_roots.json"), tmp_path)
        assert doms == {"L1": FOOD, "L2": ADMIN, "L3": frozenset()}

    def test_an_entry_without_a_number_is_refused(self, tmp_path):
        (tmp_path / "toy_roots.json").write_text(json.dumps(
            [{"Number": "L1", "Meaning": "wine"}, {"Meaning": "king"}, {"Meaning": "god"}]), encoding="utf-8")
        with pytest.raises(ValueError, match="Number"):          # else every such entry pools under "None"
            ms.competitor_domains(SimpleNamespace(file="toy_roots.json"), tmp_path)


# --- the command ---

CLI_CORPUS = {
    "d1": _doc("Tablet", "KA-NA-SI", "VIN", "1"),
    "d2": _doc("Tablet", "MA-RU-KU", "VIR", "2"),
    "d3": _doc("Tablet", "KU-NI-SU", "GRA", "3"),          # a gold-set word
    "d4": _doc("Clay vessel", "DA-ME"),
}


@pytest.fixture
def cli_run(engine, tmp_path, monkeypatch, capsys):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps(CLI_CORPUS), encoding="utf-8")
    monkeypatch.setattr(cli, "CORPUS", corpus)
    prereg = tmp_path / "prereg.md"
    prereg.write_text("signed\n", encoding="utf-8")

    def run(*extra: str, prereg_arg: bool = True, full_index: bool = True,
            index: Path | None = None) -> tuple[int, dict | None, str]:
        argv = ["--stat", "rank", "--n", "99", "--index", str(index or engine.index.path), *extra]
        if full_index:
            argv.append("--full-index")
        if prereg_arg:
            argv += ["--prereg", str(prereg)]
        rc = cli.main(argv)
        out, err = capsys.readouterr()
        return rc, (json.loads(out) if rc == 0 else None), err
    run.prereg = prereg
    return run


class TestRefusals:
    """Before any file is read: unit tests."""

    def test_no_pre_registration_no_run(self, tmp_path):
        assert cli.main(["--stat", "rank"]) == 5
        assert cli.main(["--stat", "rank", "--prereg", str(tmp_path / "missing.md")]) == 5

    def test_no_test_reaches_the_live_corpus(self):
        assert cli.CORPUS.read_text(encoding="utf-8") == "{}"         # conftest's stand-in

    def test_count_needs_tau(self, tmp_path):
        with pytest.raises(SystemExit) as e:
            cli.main(["--stat", "count", "--prereg", str(tmp_path / "p.md")])
        assert e.value.code == 2

    @pytest.mark.parametrize("cap", [[], ["--cap", "0"], ["--cap", "-1"]])
    def test_cap_needs_a_positive_cap(self, tmp_path, cap):
        with pytest.raises(SystemExit) as e:
            cli.main(["--stat", "cap", *cap, "--prereg", str(tmp_path / "p.md")])
        assert e.value.code == 2


class TestStrata:
    WORDS = ("KA-NA-SI", "DA-ME", "MA-RU-KU", "JA-SA-SA-RA-ME")

    def test_none_is_one_stratum(self):
        assert cli.strata_of(list(self.WORDS), set(), "none") is None

    def test_source_length_and_both(self):
        words, logo = list(self.WORDS), {"KA-NA-SI", "DA-ME"}
        assert cli.strata_of(words, logo, "source") == ["logogram", "logogram", "document", "document"]
        assert cli.strata_of(words, logo, "length") == ["3", "2", "3", "5"]
        assert cli.strata_of(words, logo, "source-length") == ["logogram 3", "logogram 2", "document 3",
                                                              "document 5"]

    def test_length_strata_are_the_power_study_shapes(self):
        words = ["A-B-C-D-E", "A-B-C-D-E-F", "A-B-C-D-E-F-G-H-I-J-K-L-M-N-O-P"]       # as calibrated: 5 or more
        assert cli.strata_of(words, set(), "length") == ["5", "5", "5"]
        assert cli.strata_of(words, set(), "source-length") == ["document 5"] * 3


def _rivals(d: Path, gloss: bool = True) -> Path:
    for s in COMPETITORS:
        rows = [{"Number": "R1", "Consonantal_Root": "k-n-s", **({"Meaning": "wine"} if gloss else {})},
                {"Number": "R2", "Consonantal_Root": "m-r-k", **({"Meaning": "king"} if gloss else {})}]
        (d / s.file).write_text(json.dumps(rows), encoding="utf-8")
    return d


class TestCli:
    pytestmark = SHORESH

    def test_gold_words_are_set_aside_and_counted(self, cli_run):
        rc, out, _ = cli_run()
        assert rc == 0
        assert out["words"] == 2 and out["gold_set_aside"] == 1
        assert out["sha256"]["gold"] == cli._sha256(cli.GOLD)

    def test_gold_run_keeps_them(self, cli_run):
        _, out, _ = cli_run("--gold-run")
        assert out["words"] == 3 and out["gold_set_aside"] == 0 and out["sha256"]["gold"] is None

    def test_all_adds_document_anchored_words(self, cli_run):
        assert cli_run("--set", "all")[1]["words"] == 3

    def test_the_report_is_stamped_and_seeded(self, cli_run):
        _, out, _ = cli_run()
        assert out["sha256"]["prereg"] == cli._sha256(cli_run.prereg)
        assert out["sha256"]["corpus"] == cli._sha256(cli.CORPUS)
        assert out["sha256"]["tagger"] == sg.TAGGER_SHA256
        assert out["semitic"]["n"] == 99 and out["semitic"]["seed"] == cli.SEED
        assert out["semitic"]["words_with_a_match"] == 2
        assert cli_run()[1] == out

    def test_a_word_with_an_unmapped_sign_is_listed_never_shortened(self, cli_run, monkeypatch, tmp_path):
        corpus = tmp_path / "unmapped.json"
        corpus.write_text(json.dumps({**CLI_CORPUS, "d5": _doc("Tablet", "*999-KA", "VIN", "1")}), encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", corpus)
        rc, out, _ = cli_run()
        assert rc == 0
        assert out["words"] == 2 and out["unmapped"] == ["*999-KA"]

    @pytest.mark.parametrize("mode, expected", [("none", None), ("length", ["3", "3"]),
                                                ("source", ["logogram", "logogram"]), ("fine", ["3|3|1", "3|3|1"])])
    def test_the_strata_reach_the_shuffle(self, cli_run, monkeypatch, mode, expected):
        seen = []
        real = cli.ms.shuffle_test

        def spy(D, assign, stat, n, seed, strata=None):
            seen.append(strata)
            return real(D, assign, stat, n, seed, strata)
        monkeypatch.setattr(cli.ms, "shuffle_test", spy)
        rc, out, _ = cli_run("--strata", mode)
        assert rc == 0 and out["strata"] == mode and seen == [expected]

    def test_fine_strata_split_a_sign_count_and_fold_a_lone_word(self, cli_run, monkeypatch, tmp_path):
        """A-NA-SI's skeleton is two consonants long, so it stands alone and falls back to its sign count."""
        corpus = tmp_path / "anasi.json"
        corpus.write_text(json.dumps({**CLI_CORPUS, "d5": _doc("Tablet", "A-NA-SI", "VIN", "1")}), encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", corpus)
        seen = []
        real = cli.ms.shuffle_test

        def spy(D, assign, stat, n, seed, strata=None):
            seen.append(strata)
            return real(D, assign, stat, n, seed, strata)
        monkeypatch.setattr(cli.ms, "shuffle_test", spy)
        rc, _, _ = cli_run("--strata", "fine")
        assert rc == 0 and seen == [["3", "3|3|1", "3|3|1"]]

    def test_conventional_values_list_a_value_beyond_linear_b_as_unmapped(self, cli_run, monkeypatch, tmp_path):
        corpus = tmp_path / "s306.json"
        corpus.write_text(json.dumps({**CLI_CORPUS, "d5": _doc("Tablet", "KU-*306-NU", "VIN", "1")}), encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", corpus)
        rc, out, _ = cli_run()
        assert rc == 0 and out["sign_values"] == "all" and out["words"] == 3 and out["unmapped"] == []
        rc, out, _ = cli_run("--conventional-values")
        assert rc == 0 and out["sign_values"] == "conventional"
        assert out["words"] == 2 and out["unmapped"] == ["KU-*306-NU"]

    def test_the_gold_guard_reads_in_the_run_s_mode(self, cli_run, monkeypatch):
        seen, real = [], cli.gold_guard
        monkeypatch.setattr(cli, "gold_guard", lambda path, **kw: seen.append(kw) or real(path, **kw))
        assert cli_run()[0] == 0 and cli_run("--conventional-values")[0] == 0
        assert seen == [{"conventional": False}, {"conventional": True}]

    def test_the_capped_sum_is_the_statistic_asked_for(self, cli_run, monkeypatch):
        seen = []
        real = cli.ms.shuffle_test

        def spy(D, assign, stat, n, seed, strata=None):
            seen.append(stat(D, assign) == pytest.approx(ms.t_cap(D, assign, 1.5)) and stat([[3.0]], [0]) == -1.5)
            return real(D, assign, stat, n, seed, strata)
        monkeypatch.setattr(cli.ms, "shuffle_test", spy)
        rc, out, _ = cli_run("--stat", "cap", "--cap", "1.5")
        assert rc == 0 and seen == [True] and out["stat"] == "cap" and out["cap"] == 1.5
        assert -2 * 1.5 <= out["semitic"]["observed"] <= 0

    def test_competitors_run_on_the_same_words(self, cli_run, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "RIVALS", _rivals(tmp_path))
        rc, out, _ = cli_run("--competitors")
        assert rc == 0
        assert set(out["competitors"]) == {"luwian", "egyptian", "hurrian"}
        for t in out["competitors"].values():
            assert t["n"] == out["semitic"]["n"] and t["words_with_a_match"] >= 1

    def test_the_shipped_rival_files_carry_no_glosses_so_the_arm_stops(self, cli_run):
        rc, _, err = cli_run("--competitors")
        assert rc == 2 and "gloss" in err

    def test_rival_files_without_glosses_stop_with_exit_2(self, cli_run, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "RIVALS", _rivals(tmp_path, gloss=False))
        rc, _, err = cli_run("--competitors")
        assert rc == 2 and "gloss" in err

    def test_a_missing_rival_file_stops_with_exit_2(self, cli_run, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "RIVALS", tmp_path)
        rc, _, err = cli_run("--competitors")
        assert rc == 2 and err.startswith("stopped: ") and "is not in this checkout" in err     # AGENTS.md's form

    def test_a_corrupt_rival_file_stops_with_exit_2(self, cli_run, monkeypatch, tmp_path):
        d = tmp_path / "rivals"                     # apart from the corpus, so the file corrupted is a rival file
        d.mkdir()
        next(_rivals(d).glob("*.json")).write_text("{bad", encoding="utf-8")
        monkeypatch.setattr(cli, "RIVALS", d)
        assert cli_run("--competitors")[0] == 2

    @pytest.mark.parametrize("corpus", [[1, 2], {"d1": "KA-NA-SI"}, {"d1": {"transliteratedWords": None}},
                                        {"d1": {"transliteratedWords": "KA"}}, {"d1": {"transliteratedWords": [1]}}])
    def test_a_corpus_of_the_wrong_shape_stops_with_exit_4(self, cli_run, monkeypatch, tmp_path, corpus):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(corpus), encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", path)
        assert cli_run()[0] == 4

    def test_an_unreadable_gold_set_stops_with_exit_3(self, cli_run, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "GOLD", tmp_path / "missing.json")
        assert cli_run()[0] == 3
        assert cli_run("--gold-run", full_index=False)[0] == 3       # the A4 list is read from it too

    def test_a_file_that_is_not_an_index_stops_with_exit_2(self, cli_run, tmp_path):
        bad = tmp_path / "bad.sqlite"
        bad.write_bytes(b"not sqlite")
        assert cli_run(index=bad)[0] == 2
        assert cli_run("--allow-stale", index=bad)[0] == 2

    def test_an_index_changed_while_loading_stops_with_exit_2(self, cli_run, engine, monkeypatch, tmp_path):
        copy = tmp_path / "index.sqlite"
        copy.write_bytes(engine.index.path.read_bytes())
        load = RootIndex.load

        def changing(path, **kw):
            idx = load(path, **kw)
            with open(copy, "ab") as f:
                f.write(b"\0")
            return idx
        monkeypatch.setattr(cli.RootIndex, "load", staticmethod(changing))
        rc, _, err = cli_run(index=copy)
        assert rc == 2 and "changed" in err


# --- additive scores and the power simulation ---

class TestScores:
    def test_rank_and_count_rows_sum_to_the_statistics(self):
        rng = random.Random(4)
        D = [[rng.choice([0.0, 0.3, 0.7, INF]) for _ in range(4)] for _ in range(25)]
        assign = [rng.randrange(4) for _ in range(25)]
        assert sum(ms.rank_row(D[i])[a] for i, a in enumerate(assign)) == pytest.approx(ms.t_rank(D, assign))
        assert sum(ms.count_row(D[i], 0.3)[a] for i, a in enumerate(assign)) == ms.t_count(D, assign, 0.3)
        assert sum(ms.cap_row(D[i], 1.0)[a] for i, a in enumerate(assign)) == pytest.approx(ms.t_cap(D, assign, 1.0))


class TestKsUniform:
    def test_an_even_grid_is_uniform(self):
        d, p = ms.ks_uniform([(i + 0.5) / 200 for i in range(200)])
        assert d == pytest.approx(0.0025) and p > 0.99

    def test_p_values_piled_near_zero_are_not(self):
        d, p = ms.ks_uniform([0.01 * (i % 10 + 1) for i in range(200)])
        assert d >= 0.85 and p < 1e-6

    def test_p_values_piled_near_one_are_not(self):
        d, p = ms.ks_uniform([1 - 0.01 * (i % 10) for i in range(200)])
        assert d >= 0.85 and p < 1e-6

    def test_the_kolmogorov_tail_at_known_points(self):
        """Q(λ) = 2 Σ (−1)^(j−1) e^(−2 j² λ²): 0.2700 at λ = 1, 0.0500 at λ = 1.3581 (the 5% critical value)."""
        assert ms.kolmogorov_tail(1.0) == pytest.approx(0.2700, abs=1e-4)
        assert ms.kolmogorov_tail(1.3581) == pytest.approx(0.0500, abs=1e-4)
        assert ms.kolmogorov_tail(0.0) == 1.0

    def test_empty_is_refused(self):
        with pytest.raises(ValueError, match="no p-values"):
            ms.ks_uniform([])


def _null_pool(rng, slots, contexts, size=20):
    return [[[rng.choice([0.0, 0.3, 0.6, 1.0, INF]) for _ in range(contexts)] for _ in range(size)] for _ in slots]


SCORERS = {"rank": ms.rank_row, "count_0.3": lambda r: ms.count_row(r, 0.3)}


class TestSimulate:
    def test_with_nothing_planted_detection_is_near_alpha(self):
        rng = random.Random(5)
        slots = [i % 4 for i in range(40)]
        out = ms.simulate(slots, _null_pool(rng, slots, 4), {}, k=0, runs=300, n_perm=99, seed=1,
                          scorers=SCORERS)
        for name in SCORERS:
            assert out[name]["power"] <= 0.1
            assert out[name]["planted"] == 0

    def test_planted_words_near_their_own_context_are_detected(self):
        rng = random.Random(6)
        slots = [i % 4 for i in range(40)]
        plants = {c: [[0.0 if j == c else 1.0 for j in range(4)]] * 10 for c in range(4)}
        out = ms.simulate(slots, _null_pool(rng, slots, 4), plants, k=20, runs=100, n_perm=99, seed=2,
                          scorers=SCORERS)
        for name in SCORERS:
            assert out[name]["power"] >= 0.9
            assert out[name]["planted"] == 20

    def test_only_slots_whose_context_has_plants_take_one(self):
        rng = random.Random(7)
        slots = [0] * 10 + [1] * 30
        plants = {0: [[0.0, 1.0]] * 10}
        out = ms.simulate(slots, _null_pool(rng, slots, 2), plants, k=25, runs=5, n_perm=19, seed=3,
                          scorers={"rank": ms.rank_row})
        assert out["rank"]["planted"] == 10

    def test_the_seed_fixes_the_result(self):
        rng = random.Random(8)
        slots = [i % 3 for i in range(30)]
        pool = _null_pool(rng, slots, 3)
        plants = {c: [[0.0 if j == c else 0.6 for j in range(3)]] for c in range(3)}
        a = ms.simulate(slots, pool, plants, k=5, runs=50, n_perm=49, seed=9, scorers=SCORERS)
        assert a == ms.simulate(slots, pool, plants, k=5, runs=50, n_perm=49, seed=9, scorers=SCORERS)

    def test_plants_follow_each_slot_s_own_pool_key(self):
        rng = random.Random(12)
        slots = [0] * 20
        keys = ["short"] * 10 + ["long"] * 10                 # e.g. (context, length): plants match the slot's shape
        plants = {"short": [[0.0]] * 10}
        out = ms.simulate(slots, _null_pool(rng, slots, 1), plants, k=15, runs=5, n_perm=19, seed=1,
                          scorers={"rank": ms.rank_row}, plant_of=keys)
        assert out["rank"]["planted"] == 10

    def test_a_plant_fills_at_most_one_slot_a_run(self):
        """A word list holds each word once: two plants for ten slots of their key plant two, not ten."""
        rng = random.Random(15)
        slots = [0] * 10
        out = ms.simulate(slots, _null_pool(rng, slots, 1), {0: [[0.0], [0.0]]}, k=10, runs=5, n_perm=19, seed=1,
                          scorers={"rank": ms.rank_row})
        assert out["rank"]["planted"] == 2
        assert (out["rank"]["planted_min"], out["rank"]["planted_max"]) == (2, 2)

    def test_one_word_in_two_pools_is_planted_once(self):
        rng = random.Random(16)
        slots = [0, 0, 1, 1]
        pool, plants = _null_pool(rng, slots, 2), {0: [[0.0, 1.0]], 1: [[1.0, 0.0]]}
        kw = {"k": 4, "runs": 5, "n_perm": 19, "seed": 1, "scorers": {"rank": ms.rank_row}}
        assert ms.simulate(slots, pool, plants, **kw)["rank"]["planted"] == 2          # a plant per pool
        assert ms.simulate(slots, pool, plants, plant_ids={0: ["w"], 1: ["w"]}, **kw)["rank"]["planted"] == 1

    def test_a_spent_pool_leaves_its_slots_null(self):
        """Pool a holds one plant for five slots, b five for five: at k = 8 every run plants a once and b five times,
        six in all, and the other four a slots keep their null rows."""
        rng = random.Random(17)
        slots, keys = [0] * 10, ["a"] * 5 + ["b"] * 5
        out = ms.simulate(slots, _null_pool(rng, slots, 1), {"a": [[0.0]], "b": [[0.0]] * 5}, k=8, runs=20,
                          n_perm=19, seed=2, scorers={"rank": ms.rank_row}, plant_of=keys)
        assert (out["rank"]["planted_min"], out["rank"]["planted_max"]) == (6, 6)

    def test_the_planted_count_reports_its_range_over_runs(self):
        """Slot a may take x or y, slot b only x: when a takes x, b is spent, so a run plants one or two."""
        rng = random.Random(18)
        out = ms.simulate([0, 0], _null_pool(rng, [0, 0], 1), {"a": [[0.0], [0.0]], "b": [[0.0]]}, k=2, runs=60,
                          n_perm=9, seed=3, scorers={"rank": ms.rank_row}, plant_of=["a", "b"],
                          plant_ids={"a": ["x", "y"], "b": ["x"]})["rank"]
        assert (out["planted_min"], out["planted_max"]) == (1, 2) and 1 < out["planted"] < 2

    def test_null_draws_use_each_decoy_once_until_the_pool_is_spent(self):
        draws = ms.null_draws([5, 2], runs=5, rng=random.Random(4))
        assert len(draws) == 5 and all(len(d) == 2 for d in draws)
        assert sorted(d[0] for d in draws) == [0, 1, 2, 3, 4]
        assert sorted(Counter(d[1] for d in draws).values()) == [2, 3]          # spent, then reused evenly
        with pytest.raises(ValueError):
            ms.null_draws([3, 0], runs=1, rng=random.Random(4))

    def test_fresh_null_scores_every_decoy_once(self):
        """30 decoys a slot over 30 runs: drawn fresh, every decoy enters once; drawn with replacement, some never do."""
        slots = [0, 0, 1, 1]
        pool = [[[s * 100.0 + j, j / 10] for j in range(30)] for s in range(4)]           # every row distinct

        def scored(fresh):
            seen = set()

            def scorer(row):
                seen.add(tuple(row))
                return ms.rank_row(row)
            ms.simulate(slots, pool, {}, k=0, runs=30, n_perm=9, seed=5, scorers={"rank": scorer},
                        fresh_null=fresh)
            return len(seen)
        assert scored(True) == 4 * 30
        assert scored(False) < 4 * 30

    def test_plant_ids_must_name_every_plant(self):
        with pytest.raises(ValueError):
            ms.simulate([0, 0], [[[0.0]], [[0.0]]], {0: [[0.0], [0.1]]}, k=1, runs=1, n_perm=9, seed=1,
                        scorers={"rank": ms.rank_row}, plant_ids={0: ["w"]})

    def test_length_strata_remove_a_breadth_confound(self):
        """Short words sit in the broad context and are nearer it; long words are near nothing. Nothing is planted:
        the unstratified shuffle fires on shape alone, the length-stratified one does not."""
        rng = random.Random(13)
        slots, strata, pool = [], [], []
        for i in range(40):
            short = i % 2 == 0
            slots.append(0 if short else rng.randrange(2))
            strata.append("2" if short else "4")
            pool.append([[0.0, rng.choice([0.6, 1.0])]] if short else [[INF, INF]])
        kw = {"k": 0, "runs": 40, "n_perm": 99, "seed": 5, "scorers": {"rank": ms.rank_row}}
        assert ms.simulate(slots, pool, {}, **kw)["rank"]["power"] >= 0.9
        assert ms.simulate(slots, pool, {}, strata=strata, **kw)["rank"]["power"] <= 0.1

    def test_keep_p_returns_every_run_s_p(self):
        rng = random.Random(14)
        slots = [i % 3 for i in range(30)]
        out = ms.simulate(slots, _null_pool(rng, slots, 3), {}, k=0, runs=25, n_perm=19, seed=6,
                          scorers={"rank": ms.rank_row}, keep_p=True)
        ps = out["rank"]["p"]
        assert len(ps) == 25 and all(0.05 <= p <= 1.0 for p in ps)
        assert out["rank"]["power"] == round(sum(p < 0.05 for p in ps) / 25, 4)

    def test_rows_built_afresh_on_each_access_score_as_stored_rows(self):
        """A pool may hand out a new row object each time; scores follow the row, not the object's id."""
        class Fresh:
            def __init__(self, rows):
                self.rows = rows

            def __len__(self):
                return len(self.rows)

            def __getitem__(self, j):
                return list(self.rows[j])
        rng = random.Random(10)
        slots = [i % 3 for i in range(30)]
        pool = _null_pool(rng, slots, 3)
        plants = {c: [[0.0 if j == c else rng.choice([0.3, 0.6]) for j in range(3)] for _ in range(5)]
                  for c in range(3)}
        kw = {"k": 8, "runs": 150, "n_perm": 49, "seed": 4, "scorers": SCORERS}
        assert (ms.simulate(slots, [Fresh(p) for p in pool], {c: Fresh(v) for c, v in plants.items()}, **kw)
                == ms.simulate(slots, pool, plants, **kw))
