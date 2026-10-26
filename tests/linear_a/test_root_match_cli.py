"""Tests for tools/linear_a/root_match.py, the report-only Shoresh command, and tools.core.root_match.bh_q. Every
index is built in tmp_path; the command is called in-process and must write nothing."""
from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import pytest
import test_root_match as trm  # the shared records and corpus words; pytest puts this folder on the path
from shoresh_inputs import SHORESH

from tools.core import competitors as cp
from tools.core import root_match as rm
from tools.core import semantic_gate as sg
from tools.core.phonetics import LUWIAN_DISTANCES
from tools.core.root_index import RootIndex, write_index
from tools.linear_a import root_match as cli
from tools.linear_a.validation.root_match_phase0 import GOLD_SECTIONS

pytestmark = SHORESH

SYNTHETIC_GOLD = "TO-ZE-PU"     # a made-up sign group, in no section of the real gold set and no reading twin of one


@pytest.fixture
def synthetic_gold(tmp_path, monkeypatch) -> Path:
    """A gold file whose every section holds one made-up word: no test takes a number on a real gold word (A14)."""
    path = tmp_path / "gold.json"
    path.write_text(json.dumps({s: [{"word": SYNTHETIC_GOLD}] for s in GOLD_SECTIONS}), encoding="utf-8")
    monkeypatch.setattr(cli, "GOLD", path)
    return path


@pytest.fixture
def built(tmp_path) -> tuple[Path, Path]:
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(tmp_path / "x.sqlite", roots, lexica=())
    return roots, tmp_path / "x.sqlite"


def _run(index_path: Path, words: list[str], exclusions=None, **kw):
    opts = {"n": 30, "seed": rm.SEED, "families": "ABC", "names": False, "top": 5, "breadth": True,
            "corpus_words": trm.CORPUS, "contexts": sg.Contexts({})}   # A18: no attested context, never the live corpus
    opts.update(kw)
    return cli.run(words, index=RootIndex.load(index_path), exclusions=exclusions, **opts)


class TestBH:
    def test_known_values_and_untested_words(self):
        q = rm.bh_q([0.01, 0.04, 0.03, 0.2, None])
        assert q[4] is None and q[3] == 0.2
        assert q[0] == pytest.approx(0.04) and q[1] == pytest.approx(0.16 / 3) and q[2] == pytest.approx(0.16 / 3)

    def test_q_is_monotone_in_p_and_never_below_it(self):
        ps = [0.5, 0.001, 0.02, 0.02, 0.9, 0.049]
        q = rm.bh_q(ps)
        order = sorted(range(len(ps)), key=lambda i: ps[i])
        assert all(q[a] <= q[b] for a, b in pairwise(order))
        assert all(qq >= p for p, qq in zip(ps, q)) and max(q) <= 1


class TestRun:
    def test_batch_gets_q_and_a_single_word_does_not(self, built):
        _, index = built
        one = _run(index, ["KA-NA-SI"])
        assert "bh_q" not in one["results"][0]
        two = _run(index, ["KA-NA-SI", "MA-RA-KU"])
        assert [r["bh_q"] for r in two["results"]] == rm.bh_q([r["p_max"] for r in two["results"]])

    def test_unmapped_word_is_reported_and_the_batch_goes_on(self, built):
        _, index = built
        out = _run(index, ["KA-A303-SI", "KA-NA-SI"])
        assert "unmapped sign A303" in out["results"][0]["error"]
        assert out["results"][1]["verdict"] in {"PHONOLOGICAL_ONLY", "NO_SIGNAL"}
        assert "bh_q" not in out["results"][0]

    def test_key_set_is_named_and_exclusions_apply(self, built):
        _, index = built
        full = _run(index, ["KA-NA-SI"])
        assert full["key_set"] == "full (secondary)"
        primary = _run(index, ["KA-NA-SI"], exclusions={"1": "campaign_addition"})
        assert primary["key_set"] == "primary (A4: 1 Numbers out)"
        assert "1" not in {h["number"] for h in primary["results"][0]["clusters"]}

    def test_render_carries_the_verdict_the_a1_note_and_the_footer(self, built):
        _, index = built
        text = cli.render(_run(index, ["KA-NA-SI"]))
        assert "PHONOLOGICAL_ONLY" in text and "(not in p_max)" in text and "Enters at SPECULATIVE." in text
        assert "semantic: no semantic evidence (0 of 0 attestations with a known context)" in text   # A18

    def test_render_carries_the_semantic_gate(self, built):
        _, index = built
        ctx = sg.Contexts({"X1": {"support": "Stone vessel", "transliteratedWords": ["KA-NA-SI"]}})
        r = _run(index, ["KA-NA-SI"], contexts=ctx)["results"][0]
        assert r["semantic"]["context"] == ["deity", "ritual_cultic"] and r["semantic"]["attestations"] == 1
        assert "semantic: context deity, ritual_cultic (1 of 1 attestations)" in cli.render(
            {"index": "x", "index_checked": True, "key_set": "k", "n": 30, "seed": 1, "results": [r]})

    def test_semantic_lines(self):
        base = {"context": ["food_drink"], "attestations": 2, "known": 1, "fitting": 1, "d_star": None,
                "families": {}, "p_max": None, "deciding_family": None}
        assert cli._semantic_lines({}) == []
        assert cli._semantic_lines(base)[-1] == "  semantic: no fitting cluster retrieved, so no d*_sem and no CONVERGENT"
        full = {**base, "d_star": 0.3, "p_max": 0.004, "deciding_family": "B",
                "families": {"A": {"p": 0.2, "in_p_max": False}, "B": {"p": 0.004, "in_p_max": True}}}
        assert cli._semantic_lines(full) == [
            "  semantic: context food_drink (1 of 2 attestations); 1 retrieved clusters fit",
            "  semantic: d*_sem=0.3  p_max_sem=0.004 (B)  A: p=0.2 (not in p_max)  B: p=0.004"]

    def test_run_passes_the_contexts_to_the_engine(self, built, monkeypatch):
        _, index = built
        monkeypatch.setattr(rm, "load_corpus", lambda: (_ for _ in ()).throw(AssertionError("live corpus read")))
        _run(index, ["KA-NA-SI"])                                   # the given contexts, never the live corpus

    def test_the_domains_are_read_in_the_parent_before_a_pool_forks(self, built):
        _run(built[1], ["KA-NA-SI"])
        assert cli._RUN["engine"]._cluster_domains is not None and cli._RUN["engine"]._contexts is not None


class TestSemanticInputs:
    """The semantic gate's inputs: data/linear-a/corpus.json stamped from the bytes parsed, the tagger checked in the parent,
    and the index unchanged until its Meanings are read (§7.1, A18)."""

    def _corpus(self, tmp_path, monkeypatch, docs: dict) -> Path:
        path = tmp_path / "corpus.json"
        path.write_text(json.dumps(docs), encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", path)
        return path

    def test_the_report_stamps_the_corpus_it_read(self, built, tmp_path, monkeypatch, capsys):
        import hashlib
        path = self._corpus(tmp_path, monkeypatch,
                            {"X1": {"support": "Tablet", "transliteratedWords": ["MA-RU-KU", "VIR", "3"]}})
        assert cli.main(["MA-RU-KU", "--index", str(built[1]), "--full-index", "--n", "10", "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["corpus_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert report["tagger_sha256"] == sg.TAGGER_SHA256
        assert report["results"][0]["semantic"]["context"] == ["administrative", "kinship"]   # these very bytes

    def test_a_sweep_stamps_the_corpus_too(self, built, tmp_path, monkeypatch, capsys):
        self._corpus(tmp_path, monkeypatch, {})
        unread = tmp_path / "unread.json"
        unread.write_text(json.dumps({"entries": [{"word": "KA-NA-SI"}]}), encoding="utf-8")
        monkeypatch.setattr(cli, "UNREAD", unread)
        assert cli.main(["--sweep", "unread", "--index", str(built[1]), "--full-index", "--n", "10", "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["sweep"]["corpus_sha256"] == report["corpus_sha256"] and report["corpus_sha256"]

    def test_an_unreadable_corpus_exits_4(self, built, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(cli, "CORPUS", tmp_path / "missing.json")
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), "--full-index", "--n", "10"]) == 4
        assert "corpus" in capsys.readouterr().err
        (tmp_path / "bad.json").write_text("{", encoding="utf-8")
        monkeypatch.setattr(cli, "CORPUS", tmp_path / "bad.json")
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), "--full-index", "--n", "10"]) == 4

    def test_a_changed_tagger_exits_4_before_any_word(self, built, tmp_path, monkeypatch, capsys):
        self._corpus(tmp_path, monkeypatch, {})
        copy = tmp_path / "tag_semantic_fields.py"
        copy.write_bytes(sg.TAGGER.read_bytes() + b"\n# edited\n")
        monkeypatch.setattr(sg, "TAGGER", copy)
        sg.tagger.cache_clear()
        try:
            assert cli.main(["KA-NA-SI", "--index", str(built[1]), "--full-index", "--n", "10"]) == 4
            err = capsys.readouterr()
            assert "A18" in err.err and err.out == ""
        finally:
            sg.tagger.cache_clear()

    def test_an_index_changed_before_its_meanings_are_read_exits_2(self, built, tmp_path, monkeypatch, capsys):
        self._corpus(tmp_path, monkeypatch, {})
        shas = iter(["a", "a", "b"])                               # before the load, after it, after the Meanings
        monkeypatch.setattr(cli, "_sha256", lambda p: next(shas))
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), "--full-index", "--n", "10"]) == 2
        captured = capsys.readouterr()
        assert "changed" in captured.err and captured.out == ""


class TestMain:
    def test_stale_index_is_refused_unless_allowed(self, built, capsys):
        roots, index = built
        roots.write_text(json.dumps(trm.RECORDS[:2], ensure_ascii=False), encoding="utf-8")
        assert cli.main(["KA-NA-SI", "--index", str(index), "--full-index", "--n", "10", "--families", "AC"]) == 2
        assert "--allow-stale" in capsys.readouterr().err
        code = cli.main(["KA-NA-SI", "--index", str(index), "--full-index", "--n", "10", "--families", "AC",
                         "--allow-stale", "--json"])
        assert code == 0 and json.loads(capsys.readouterr().out)["index_checked"] is False

    def test_json_and_exit_status(self, built, capsys):
        _, index = built
        assert cli.main(["KA-NA-SI", "--index", str(index), "--full-index", "--n", "10", "--families", "AC",
                         "--json"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["index_checked"] is True and report["results"][0]["footer"] == "Enters at SPECULATIVE."
        assert report["key_set"] == "full (secondary)" and report["n"] == 10 and report["families"] == "AC"
        assert report["gold_run"] is False
        assert cli.main(["KA-A303", "--index", str(index), "--full-index", "--n", "10", "--families", "AC"]) == 1

    def test_words_from_a_file(self, built, tmp_path, capsys):
        _, index = built
        f = tmp_path / "words.txt"
        f.write_text("KA-NA-SI\n\nMA-RA-KU\n", encoding="utf-8")
        cli.main(["--file", str(f), "--index", str(index), "--full-index", "--n", "10", "--families", "AC",
                  "--json"])
        assert [r["word"] for r in json.loads(capsys.readouterr().out)["results"]] == ["KA-NA-SI", "MA-RA-KU"]

    @pytest.mark.parametrize("argv", [[], ["KA-NA-SI", "--families", "AD"], ["KA-NA-SI", "--families", ""]])
    def test_bad_arguments(self, argv):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert e.value.code == 2

    def test_writes_nothing(self, built, capsys):
        _, index = built
        before = sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in index.parent.iterdir())
        cli.main(["KA-NA-SI", "--index", str(index), "--full-index", "--n", "10", "--families", "AC"])
        capsys.readouterr()
        assert sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in index.parent.iterdir()) == before


class TestCompetitors:
    ARGS = ("--full-index", "--n", "10", "--families", "AC", "--json")

    def test_on_by_default_with_all_three(self, built, capsys):
        _, index = built
        assert cli.main(["KA-NA-SI", "--index", str(index), *self.ARGS]) == 0
        report = json.loads(capsys.readouterr().out)
        assert list(report["competitors"]) == ["luwian", "egyptian", "hurrian"] and all(report["competitors"].values())
        r = report["results"][0]
        assert list(r["competitors"]) == ["luwian", "egyptian", "hurrian"] and "semitic_specific" in r
        text = cli.render(report)
        assert "competitor hurrian: d*=" in text and "Semitic-specific:" in text

    def test_switched_off(self, built, capsys):
        _, index = built
        assert cli.main(["KA-NA-SI", "--index", str(index), *self.ARGS, "--no-competitors"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["competitors"] == {} and report["results"][0]["competitors"] == {}
        assert "competitor null (§2) not run" in report["results"][0]["notes"]
        assert "Semitic-specific" not in cli.render(report)

    def test_names_reach_the_competitors(self, built, capsys, monkeypatch):
        _, index = built
        seen = []
        monkeypatch.setattr(cli, "competitor_spaces", lambda names: seen.append(names) or [])
        cli.main(["KA-NA-SI", "--index", str(index), *self.ARGS, "--names"])
        cli.main(["KA-NA-SI", "--index", str(index), *self.ARGS])
        capsys.readouterr()
        assert seen == [True, False]

    def test_a_missing_rival_file_stops_with_2_and_names_it(self, built, capsys, monkeypatch):
        monkeypatch.setattr(cp, "COMPETITORS", [cp.Spec("absent", "absent_roots.json", LUWIAN_DISTANCES)])
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), *self.ARGS]) == 2
        captured = capsys.readouterr()
        assert captured.out == "" and "absent_roots.json is not in this checkout" in captured.err
        assert "--no-competitors" in captured.err


class TestGoldGuard:
    """No engine number on a gold-set word before the gold run (§6): the guard refuses before the index loads."""

    ARGS = ("--full-index", "--n", "10", "--families", "AC")

    def test_gold_keys_cover_every_section_and_the_lexicon_spelling(self):
        data = json.loads(cli.GOLD.read_text(encoding="utf-8"))
        keys = cli.gold_sign_groups(cli.GOLD)
        for section in ("positives", "negatives", "controls", "lb_negatives", "lb_loans", "lb_shuffles", "excluded"):
            assert data[section] and all(cli.sign_group_key(r["word"]) in keys for r in data[section])
        assert ("PI", "QI", "TE") in keys and ("PI", "*34", "TE") in keys

    @pytest.mark.parametrize("word", ["KU-RO", "ku-ro", "A-PA3", " A-PA₃ ", "PI-QI-TE"])
    def test_gold_word_is_refused_before_the_index_loads(self, tmp_path, capsys, word):
        absent = tmp_path / "absent.sqlite"
        assert cli.main([word, "--index", str(absent), *self.ARGS, "--json"]) == 3
        out = capsys.readouterr()
        assert out.out == "" and "refused" in out.err and word.strip() in out.err

    def test_one_gold_word_refuses_the_whole_batch(self, built, capsys):
        _, index = built
        assert cli.main(["KA-NA-SI", "KU-RO", "--index", str(index), *self.ARGS]) == 3
        out = capsys.readouterr()
        assert out.out == "" and "KU-RO" in out.err and "KA-NA-SI" not in out.err

    def test_gold_run_lifts_the_guard_and_says_so(self, built, capsys, synthetic_gold):
        _, index = built
        assert cli.main([SYNTHETIC_GOLD, "--index", str(index), *self.ARGS, "--json", "--no-competitors"]) == 3
        capsys.readouterr()
        assert cli.main([SYNTHETIC_GOLD, "--index", str(index), *self.ARGS, "--json", "--no-competitors",
                         "--gold-run"]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["gold_run"] is True and report["results"][0]["word"] == SYNTHETIC_GOLD
        assert "GOLD RUN" in cli.render(report) and "GOLD RUN" not in cli.render({**report, "gold_run": False})

    @pytest.mark.parametrize("content", [None, "{not json"])
    def test_unreadable_gold_set_refuses(self, built, capsys, monkeypatch, tmp_path, content):
        _, index = built
        gold = tmp_path / "gold.json"
        if content is not None:
            gold.write_text(content, encoding="utf-8")
        monkeypatch.setattr(cli, "GOLD", gold)
        assert cli.main(["KA-NA-SI", "--index", str(index), *self.ARGS]) == 3
        out = capsys.readouterr()
        assert out.out == "" and "gold set unreadable" in out.err


EXPLAIN_RECORDS = [{"Number": "7", "Proto-Semitic": "*ḏakar-", "Meaning": "'male'",
                    "Analogues": {"Aramaic": "dkr 'male' (DJBA, 341)", "Hebrew": "zākār 'male' (HALOT, 271)"}},
                   {"Number": "8", "Proto-Semitic": "*zVkr-", "Meaning": "'to remember'", "Analogues": {}}]
EXPLAIN_LEXICON = [
    {"id": "p7", "language": "Phoenician", "root": "zkr", "normalized": "zkr", "meaning": "male",
     "semitic_roots_ref": ["7"]},                                                            # fk: joins 7
    {"id": "p8", "language": "Phoenician", "root": "zkr", "normalized": "zkr", "meaning": "Zakar", "pos": "DN",
     "semitic_roots_ref": ["7"]},                                                            # onomastic
    {"id": "p9", "language": "Phoenician", "root": "zkr", "normalized": "zkr", "meaning": "to remember"},
    {"id": "p10", "language": "Phoenician", "root": "zkr", "normalized": "zkr", "meaning": "male, man"},
]


@pytest.fixture
def explain_index(tmp_path, monkeypatch) -> Path:
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(EXPLAIN_RECORDS, ensure_ascii=False), encoding="utf-8")
    lexica = (trm._lex("phoenician", trm._jsonl(tmp_path / "p.jsonl", EXPLAIN_LEXICON)),)
    write_index(tmp_path / "x.sqlite", roots, lexica)
    monkeypatch.setattr(rm, "_correspondences", lambda: trm.TABLE)        # the synthetic sound-law table
    return tmp_path / "x.sqlite"


class TestIndexRecord:
    def test_headword_meaning_and_analogues_with_their_citations(self, explain_index):
        rec = cli.index_record(RootIndex.load(explain_index), "7")
        assert (rec["number"], rec["ps"], rec["meaning"]) == ("7", "*ḏakar-", "'male'")
        assert rec["analogues"] == [{"language": "Aramaic", "branch": "Aramaic", "text": "dkr 'male' (DJBA, 341)"},
                                    {"language": "Hebrew", "branch": "Hebrew", "text": "zākār 'male' (HALOT, 271)"}]

    def test_rows_are_the_records_own(self, explain_index):
        assert cli.index_record(RootIndex.load(explain_index), "8")["analogues"] == []

    def test_unknown_number_is_none(self, explain_index):
        assert cli.index_record(RootIndex.load(explain_index), "999") is None


class TestExplain:
    def test_clusters_carry_the_record_and_its_joined_lexemes(self, explain_index):
        h = next(c for c in _run(explain_index, ["ZA-KA-RA"], explained=True)["results"][0]["clusters"]
                 if c["number"] == "7")
        assert h["record"] == {"number": "7", "ps": "*ḏakar-", "meaning": "'male'", "analogues": [
            {"language": "Aramaic", "branch": "Aramaic", "text": "dkr 'male' (DJBA, 341)"},
            {"language": "Hebrew", "branch": "Hebrew", "text": "zākār 'male' (HALOT, 271)"}]}
        assert [(x["id"], x["basis"]) for x in h["joined"]] == [("phoenician:p10", "root_key_exact"),
                                                                 ("phoenician:p7", "fk")]
        assert h["sound_laws"]["profile"] == ["A", "C"]

    def test_a_link_without_gloss_overlap_does_not_join(self, explain_index):
        index = RootIndex.load(explain_index)
        assert ("7", "root_key_exact", False) in index.links["phoenician:p9"]          # linked to 7, not joined
        clusters = _run(explain_index, ["ZA-KA-RA"], explained=True)["results"][0]["clusters"]
        joined = {c["number"]: [x["id"] for x in c["joined"]] for c in clusters}
        assert joined == {"7": ["phoenician:p10", "phoenician:p7"], "8": ["phoenician:p9"]}
        assert all(c["record"]["number"] == c["number"] for c in clusters) and len(clusters) == 2

    def test_names_add_the_onomastic_lexeme(self, explain_index):
        def ids(**kw):
            h = next(c for c in _run(explain_index, ["ZA-KA-RA"], explained=True, **kw)["results"][0]["clusters"]
                     if c["number"] == "7")
            return {x["id"] for x in h["joined"]}
        assert ids(names=True) - ids() == {"phoenician:p8"}

    def test_off_by_default(self, explain_index):
        h = _run(explain_index, ["ZA-KA-RA"])["results"][0]["clusters"][0]
        assert "record" not in h and "joined" not in h and "sound laws vs" not in cli.render(
            _run(explain_index, ["ZA-KA-RA"]))

    def test_render(self, explain_index):
        text = cli.render(_run(explain_index, ["ZA-KA-RA"], explained=True))
        assert "*ḏakar- 'male'" in text and "Hebrew (Hebrew): zākār 'male' (HALOT, 271)" in text
        assert "joined phoenician:p7 zkr 'male' (fk)" in text
        assert "sound laws vs *ḏakar- (ḏ-k-r): *ḏ:z diagnostic (A, C); *k:k not diagnostic; *r:r not diagnostic" in text
        assert "profile: A, C" in text

    def test_render_edge_cases(self):
        base = {"record": None, "joined": [], "sound_laws": None}
        assert cli._explained(base) == ["           (record not in the index)",
                                        "           sound laws: not computed (no PS headword)"]
        sl = {"headword": "*x-", "radicals": "ṯ-ḏ", "profile": [], "positions": [
            {"ps": "*ṯ", "la": "s", "status": "diagnostic", "consistent": ["A"], "uncertain": ["A"]},
            {"ps": "*ḏ", "la": "d", "status": "diagnostic", "consistent": ["B"], "uncertain": []}]}
        lines = cli._explained({**base, "sound_laws": sl})
        assert lines[-2].endswith("*ṯ:s diagnostic (A?); *ḏ:d diagnostic (B)")
        assert lines[-1] == "           profile: none (the diagnostic radicals disagree)"
        none = cli._explained({**base, "sound_laws": {**sl, "profile": None, "positions": []}})
        assert none[-2].endswith(": —") and none[-1] == "           profile: — (no diagnostic radical)"

    def test_main_flag(self, explain_index, capsys):
        args = ["ZA-KA-RA", "--index", str(explain_index), "--full-index", "--n", "10", "--families", "AC",
                "--no-competitors", "--json"]
        assert cli.main([*args, "--explain"]) == 0
        assert "record" in json.loads(capsys.readouterr().out)["results"][0]["clusters"][0]
        assert cli.main(args) == 0
        assert "record" not in json.loads(capsys.readouterr().out)["results"][0]["clusters"][0]


COGNATE_LEXICON = EXPLAIN_LEXICON + [
    {"id": "p11", "language": "Phoenician", "root": "zkrn", "normalized": "zkrn", "meaning": "memorial"},  # reduced
    {"id": "p12", "language": "Phoenician", "root": "zkt", "normalized": "zkt", "meaning": "a measure"},   # no link
    {"id": "p13", "language": "Phoenician", "root": "zkt", "normalized": "zkt", "meaning": "Zakat", "pos": "PN"},
]


@pytest.fixture
def cognates_index(tmp_path, monkeypatch) -> Path:
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(EXPLAIN_RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(tmp_path / "x.sqlite", roots, (trm._lex("phoenician", trm._jsonl(tmp_path / "p.jsonl", COGNATE_LEXICON)),))
    monkeypatch.setattr(rm, "_correspondences", lambda: trm.TABLE)
    return tmp_path / "x.sqlite"


class TestPossibleCognates:
    """§8 (A17): a link that does not join is shown as "possible cognate of N"; a lexeme with no link, as unlinked.
    Display only."""

    @staticmethod
    def _possible(report) -> dict[str, list[tuple[str, str]]]:
        return {c["number"]: [(x["id"], x["basis"]) for x in c["possible"]] for c in report["results"][0]["clusters"]}

    def test_links_that_do_not_join_are_possible_cognates(self, cognates_index):
        report = _run(cognates_index, ["ZA-KA-RA"], explained=True)
        assert self._possible(report) == {
            "7": [("phoenician:p9", "root_key_exact"), ("phoenician:p11", "root_key_reduced")],
            "8": [("phoenician:p10", "root_key_exact"), ("phoenician:p7", "root_key_exact"),
                  ("phoenician:p11", "root_key_reduced")]}
        joined = {c["number"]: [x["id"] for x in c["joined"]] for c in report["results"][0]["clusters"]}
        assert joined == {"7": ["phoenician:p10", "phoenician:p7"], "8": ["phoenician:p9"]}   # unchanged

    def test_onomastic_ones_only_with_names(self, cognates_index):
        plain = self._possible(_run(cognates_index, ["ZA-KA-RA"], explained=True))
        named = self._possible(_run(cognates_index, ["ZA-KA-RA"], explained=True, names=True))
        assert set(named["8"]) - set(plain["8"]) == {("phoenician:p8", "root_key_exact")}

    def test_an_unlinked_lexeme_at_or_under_d_star_is_shown_and_never_counted(self, cognates_index):
        r = _run(cognates_index, ["ZA-KA-TA"], explained=True)["results"][0]
        assert r["d_star"] > 0                                                  # p12 sits at 0 and is no cluster
        assert [(x["id"], x["distance"]) for x in r["unlinked"]] == [("phoenician:p12", 0.0)]
        assert all(c["number"] in {"7", "8"} for c in r["clusters"])
        plain = _run(cognates_index, ["ZA-KA-TA"])["results"][0]
        assert (plain["d_star"], plain["p_max"], plain["verdict"]) == (r["d_star"], r["p_max"], r["verdict"])

    def test_an_unlinked_lexeme_beyond_d_star_is_not_shown(self, cognates_index):
        assert _run(cognates_index, ["ZA-KA-RA"], explained=True)["results"][0]["unlinked"] == []   # d* = 0

    def test_at_d_exactly_counts_and_onomastic_ones_need_names(self, cognates_index):
        index = RootIndex.load(cognates_index)
        d = rm._q(rm.distance(("z", "k", "r"), ("z", "k", "t")))
        assert d > 0
        assert rm.Shoresh(index).unlinked_near("ZA-KA-RA", d) == [(d, "phoenician:p12")]
        assert rm.Shoresh(index, names=True).unlinked_near("ZA-KA-RA", d) == [(d, "phoenician:p12"),
                                                                              (d, "phoenician:p13")]
        assert rm.Shoresh(index).unlinked_near("ZA-KA-RA", rm.INF) == []

    def test_off_by_default(self, cognates_index):
        r = _run(cognates_index, ["ZA-KA-TA"])["results"][0]
        assert "unlinked" not in r and all("possible" not in c for c in r["clusters"])

    def test_render_lists_the_first_ones_and_counts_the_rest(self, cognates_index):
        text = cli.render(_run(cognates_index, ["ZA-KA-TA"], explained=True))
        assert "possible cognate of 7: phoenician:p9 zkr 'to remember' (root_key_exact)" in text
        assert "unlinked phoenician:p12 zkt 'a measure' d=0" in text
        many = [{"id": f"x:{i}", "form": "zkr", "meaning": "m", "basis": "root_key_reduced"} for i in range(11)]
        lines = cli._explained({"number": "7", "record": None, "joined": [], "possible": many, "sound_laws": None})
        shown = [ln for ln in lines if "possible cognate of 7" in ln]
        assert len(shown) == cli.SHOWN and lines[1 + cli.SHOWN].strip() == f"… {11 - cli.SHOWN} more possible cognates"


SWEEP_WORDS = ["MA-RA-KU", SYNTHETIC_GOLD, "KA-A303", "KA-NA-SI", "DA-ME"]   # SYNTHETIC_GOLD: the gold-set word


@pytest.fixture
def unread(tmp_path, monkeypatch, synthetic_gold) -> Path:
    path = tmp_path / "unread_words.json"
    path.write_text(json.dumps({"entries": [{"word": w} for w in SWEEP_WORDS]}), encoding="utf-8")
    monkeypatch.setattr(cli, "UNREAD", path)
    return path


class TestSweep:
    ARGS = ("--sweep", "unread", "--full-index", "--n", "30", "--families", "AC", "--no-competitors", "--json")

    def _sweep(self, index, capsys, *extra):
        code = cli.main([*self.ARGS, "--index", str(index), *extra])
        return code, json.loads(capsys.readouterr().out)

    def test_gold_words_are_set_aside_and_counted(self, built, unread, capsys):
        code, report = self._sweep(built[1], capsys)
        assert code == 1                                                      # KA-A303 is unmapped
        assert SYNTHETIC_GOLD not in {r["word"] for r in report["results"]}
        s = report["sweep"]
        assert (s["listed"], s["skipped_gold"], len(report["results"])) == (5, 1, 4)

    def test_stamped_with_the_word_list_and_the_index(self, built, unread, capsys):
        import hashlib
        _, report = self._sweep(built[1], capsys)
        assert report["sweep"]["sha256"] == hashlib.sha256(unread.read_bytes()).hexdigest()
        assert report["sweep"]["index_sha256"] == hashlib.sha256(built[1].read_bytes()).hexdigest()
        assert report["sweep"]["source"] == "data/linear-a/unread_words.json"

    def test_ranked_by_q_with_unmapped_words_last(self, built, unread, capsys):
        _, report = self._sweep(built[1], capsys)
        rows = report["results"]
        assert "error" in rows[-1] and rows[-1]["word"] == "KA-A303"
        qs = [r["bh_q"] for r in rows if "error" not in r and r["p_max"] is not None]
        assert qs == sorted(qs) and len(qs) >= 2
        assert all(len(r["clusters"]) <= 1 for r in rows if "error" not in r)      # one cluster per word

    def test_gold_run_queries_the_gold_word(self, built, unread, capsys):
        _, report = self._sweep(built[1], capsys, "--gold-run")
        assert report["sweep"]["skipped_gold"] == 0 and SYNTHETIC_GOLD in {r["word"] for r in report["results"]}

    def test_a_missing_word_list_stops_with_5_and_names_it(self, built, capsys, monkeypatch, tmp_path):
        monkeypatch.setattr(cli, "UNREAD", tmp_path / "unread_words.json")
        assert cli.main([*self.ARGS, "--index", str(built[1])]) == 5
        captured = capsys.readouterr()
        assert captured.out == "" and "unread_words.json is not in this checkout" in captured.err

    @pytest.mark.parametrize("argv", [["KA-NA-SI", "--sweep", "unread"], ["--sweep", "unread", "--workers", "0"],
                                      ["--sweep", "all"]])
    def test_bad_arguments(self, argv, unread):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert e.value.code == 2

    def test_workers_equal_a_serial_run(self, built):
        words = ["KA-NA-SI", "MA-RA-KU", "DA-ME", "KA-A303"]
        serial = _run(built[1], words)
        forked = _run(built[1], words, workers=2)
        assert forked["results"] == serial["results"]

    def test_one_cluster_per_word_even_where_more_match(self, explain_index, tmp_path, monkeypatch, capsys):
        path = tmp_path / "u.json"
        path.write_text(json.dumps({"entries": [{"word": "ZA-KA-RA"}]}), encoding="utf-8")
        monkeypatch.setattr(cli, "UNREAD", path)
        assert len(_run(explain_index, ["ZA-KA-RA"])["results"][0]["clusters"]) == 2      # 7 and 8 both match
        _, report = self._sweep(explain_index, capsys)
        assert len(report["results"][0]["clusters"]) == 1

    def test_workers_and_top_reach_the_run_and_the_table(self, built, unread, capsys, monkeypatch):
        seen = []
        real = cli.run
        monkeypatch.setattr(cli, "run", lambda *a, **kw: seen.append(kw["workers"]) or real(*a, **kw))
        cli.main(["--sweep", "unread", "--full-index", "--n", "10", "--families", "AC", "--no-competitors",
                  "--index", str(built[1]), "--workers", "3", "--top", "1"])
        out = capsys.readouterr().out
        assert seen == [3]
        assert len([ln for ln in out.splitlines() if ln[:4].strip().isdigit()]) == 1 and "… 3 more" in out

    def test_ranked_order(self):
        rows = [{"word": "Z", "error": "x"}, {"word": "B", "p_max": 0.2, "bh_q": 0.4},
                {"word": "C", "p_max": None}, {"word": "A", "p_max": 0.01, "bh_q": 0.04},
                {"word": "D", "p_max": 0.3, "bh_q": 0.4}]
        assert [r["word"] for r in cli.ranked(rows)] == ["A", "B", "D", "C", "Z"]

    def test_render_shows_the_top_rows(self, built, unread, capsys):
        _, report = self._sweep(built[1], capsys)
        text = cli.render(report, 2)
        assert "5 listed, 1 gold-set words skipped, 4 queried" in text
        assert "… 2 more (--top, or --json for all)" in text and "SPECULATIVE" in text
        assert len([ln for ln in text.splitlines() if ln[:4].strip().isdigit()]) == 2

    def test_top_zero_shows_every_row(self, built, unread, capsys):
        _, report = self._sweep(built[1], capsys)
        text = cli.render(report, 0)
        assert len([ln for ln in text.splitlines() if ln[:4].strip().isdigit()]) == 4 and "more" not in text

    def test_stamped_with_the_bytes_it_read(self, built, unread, capsys, monkeypatch):
        import hashlib
        before = hashlib.sha256(unread.read_bytes()).hexdigest()
        real = cli.run

        def rewriting(*a, **kw):          # another session dual-writes the list while the sweep runs
            unread.write_text(json.dumps({"entries": [{"word": "DA-ME"}]}), encoding="utf-8")
            return real(*a, **kw)
        monkeypatch.setattr(cli, "run", rewriting)
        _, report = self._sweep(built[1], capsys)
        assert report["sweep"]["sha256"] == before and report["sweep"]["listed"] == 5

    def test_every_sweep_word_gold_queries_nothing(self, built, tmp_path, monkeypatch, capsys, synthetic_gold):
        path = tmp_path / "all_gold.json"
        path.write_text(json.dumps({"entries": [{"word": SYNTHETIC_GOLD}, {"word": SYNTHETIC_GOLD.lower()}]}),
                        encoding="utf-8")
        monkeypatch.setattr(cli, "UNREAD", path)
        code, report = self._sweep(built[1], capsys)
        assert code == 0 and report["results"] == [] and report["sweep"]["skipped_gold"] == 2


class TestGuardByReading:
    """A14 by reading: a spelling the engine reads as a gold word is held back with it."""
    ARGS = ("--full-index", "--n", "10", "--families", "AC", "--no-competitors", "--json")

    @pytest.mark.parametrize("word", ["KU2-RO", "KU-RO9", "KU-RO٢", "KU₂-RO", "KU-*310-SU", "ku-*310-su"])
    def test_a_reading_twin_of_a_gold_word_is_refused(self, tmp_path, capsys, word):
        assert cli.main([word, "--index", str(tmp_path / "absent.sqlite"), *self.ARGS]) == 3
        assert "refused" in capsys.readouterr().err

    def test_a_sweep_sets_a_reading_twin_aside(self, built, tmp_path, monkeypatch, capsys, synthetic_gold):
        path = tmp_path / "u.json"
        path.write_text(json.dumps({"entries": [{"word": "TO2-ZE-PU"}, {"word": "KA-NA-SI"}]}), encoding="utf-8")
        monkeypatch.setattr(cli, "UNREAD", path)
        assert cli.main(["--sweep", "unread", "--index", str(built[1]), *self.ARGS]) == 0
        report = json.loads(capsys.readouterr().out)
        assert [r["word"] for r in report["results"]] == ["KA-NA-SI"] and report["sweep"]["skipped_gold"] == 1

    @pytest.mark.parametrize("content", ["{}", '{"positives": []}', "[]", '{"positives": [{"word": "KU-RO"}]}'])
    def test_a_gold_file_of_the_wrong_shape_refuses(self, built, capsys, monkeypatch, tmp_path, content):
        gold = tmp_path / "gold.json"
        gold.write_text(content, encoding="utf-8")
        monkeypatch.setattr(cli, "GOLD", gold)
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), *self.ARGS]) == 3
        assert "gold set unreadable" in capsys.readouterr().err


class TestInputs:
    ARGS = ("--full-index", "--n", "10", "--families", "AC", "--no-competitors", "--json")

    def test_a_word_is_queried_in_its_canonical_spelling(self, built, capsys):
        out = []
        for w in ["KA-NA-SI", "ka-na-si", " KA-NA-SI ", "KA--NA-SI"]:
            assert cli.main([w, "--index", str(built[1]), *self.ARGS]) == 0
            out.append(json.loads(capsys.readouterr().out)["results"])
        assert out[1] == out[0] and out[2] == out[0] and out[3] == out[0]

    def test_every_report_is_stamped_with_the_index_and_the_gold_set(self, built, capsys, synthetic_gold):
        import hashlib
        assert cli.main(["KA-NA-SI", "--index", str(built[1]), *self.ARGS]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["index_sha256"] == hashlib.sha256(built[1].read_bytes()).hexdigest()
        assert report["gold_sha256"] == hashlib.sha256(synthetic_gold.read_bytes()).hexdigest()

    def test_a_missing_index_is_reported_not_raised(self, tmp_path, capsys):
        assert cli.main(["KA-NA-SI", "--index", str(tmp_path / "absent.sqlite"), *self.ARGS]) == 2
        assert "absent.sqlite" in capsys.readouterr().err

    @pytest.mark.parametrize("top", ["-1", "-5"])
    def test_a_negative_top_is_refused(self, built, top):
        with pytest.raises(SystemExit) as e:
            cli.main(["KA-NA-SI", "--index", str(built[1]), *self.ARGS, "--top", top])
        assert e.value.code == 2

    def test_explain_never_prints_none(self):
        h = {"record": {"ps": None, "meaning": None, "analogues": []},
             "joined": [{"id": "x1", "form": None, "meaning": None, "basis": "fk"}], "sound_laws": None}
        assert not any("None" in ln for ln in cli._explained(h))


class TestFrozenA4:
    """A17: the primary key set is the gold set's frozen primary_index_exclusions (A4, A13), never recomputed."""
    ARGS = ("--n", "10", "--families", "AC", "--no-competitors", "--json")

    def _gold(self, tmp_path, monkeypatch, exclusions):
        data = {s: [{"word": SYNTHETIC_GOLD}] for s in GOLD_SECTIONS}
        if exclusions is not None:
            data["primary_index_exclusions"] = exclusions
        path = tmp_path / "gold.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(cli, "GOLD", path)

    def test_the_frozen_list_is_read_and_absent_numbers_reported(self, built, capsys, monkeypatch, tmp_path):
        self._gold(tmp_path, monkeypatch, {"2": "campaign_addition", "9999": "no_semitic_reflex"})
        assert cli.main(["MA-RA-KU", "--index", str(built[1]), *self.ARGS]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["key_set"] == "primary (A4: 2 Numbers out)" and report["a4_absent"] == ["9999"]
        assert all(c["number"] != "2" for c in report["results"][0]["clusters"])    # *mVlk- is left out

    def test_a_gold_file_without_the_list_refuses_the_primary_result(self, built, capsys, monkeypatch, tmp_path):
        self._gold(tmp_path, monkeypatch, None)
        assert cli.main(["MA-RA-KU", "--index", str(built[1]), *self.ARGS]) == 3
        assert "primary_index_exclusions" in capsys.readouterr().err
        assert cli.main(["MA-RA-KU", "--index", str(built[1]), "--full-index", *self.ARGS]) == 0


def _die(word: str) -> dict:
    import os
    os._exit(3)                     # a worker killed mid-sweep (OOM, SIGKILL)


class TestPool:
    def test_a_dead_worker_raises_instead_of_hanging(self, built, monkeypatch):
        from concurrent.futures.process import BrokenProcessPool
        monkeypatch.setattr(cli, "_one", _die)
        with pytest.raises(BrokenProcessPool):
            _run(built[1], ["KA-NA-SI", "MA-RA-KU"], workers=2)
