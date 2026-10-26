"""Tests for tools/linear_a/validation/root_match_phase0.py: the pure functions behind the gold sets and baselines,
and the fixture-writing guarantees. No subcommand runs; every fixture path points into tmp_path."""
from __future__ import annotations

import json
import random
import subprocess

import pytest
from shoresh_inputs import SHORESH

from tools.linear_a.validation import root_match_phase0 as h


class TestRootParsing:
    @pytest.mark.parametrize("root, keys", [
        ("k-n-s", [("k", "n", "s")]),
        ("q-y-n / q-n-y", [("q", "y", "n"), ("q", "n", "y")]),
        ("√k-n-s?", [("k", "n", "s")]),
        ("to gather", []), ("k-n-s (Heb.)", []), ("k-n-s2", []), ("k-", []), (None, []), ("", []),
    ])
    def test_parse_lexicon_root(self, root, keys):
        assert h.parse_lexicon_root(root) == keys

    def test_unparsed_alternatives_are_reported(self):
        unparsed: list[str] = []
        assert h.parse_lexicon_root("k-n-s / to gather", unparsed) == [("k", "n", "s")]
        assert unparsed == ["to gather"]

    @pytest.mark.parametrize("g", ["ʾ", "ʿ", "ḥ", "ḫ", "h"])
    def test_fold_gutturals(self, g):
        assert h.fold_gutturals((g, "b")) == ("b",)


def _m(root: str, d: float) -> dict:
    return {"root": root, "distance": d}


class TestRanks:
    def test_recovery_rank(self):
        ms = [_m("*ḥ-b-r", 0.0), _m("*x-y-z", 0.1), _m("*ʾ-b-r", 0.2)]
        assert h.recovery_rank([("ʾ", "b", "r")], ms) == (3, 1)
        assert h.recovery_rank([("q", "q", "q")], ms) == (None, None)
        assert h.recovery_rank([("b", "r")], [{"distance": 0}]) == (None, None)      # no root key: no crash

    def test_expected_rank_is_tie_aware(self):
        ms = [_m("*a-b-c", 0.0), _m("*k-n-s", 0.0), _m("*m-l-k", 0.0), _m("*z-z-z", 0.5)]
        er, truncated = h.expected_rank([("k", "n", "s")], ms)
        assert er == pytest.approx(2.0) and not truncated          # tie of 3, one gold: (3 + 1) / 2
        er, _ = h.expected_rank([("k", "n", "s"), ("m", "l", "k")], ms)
        assert er == pytest.approx(4 / 3)                          # two gold in the tie: (3 + 1) / 3
        assert h.expected_rank([("k", "n", "s")], ms[:3])[1]       # list ends in the tie group: truncated
        assert h.expected_rank([("q", "q", "q")], ms) == (None, False)


class TestStatistics:
    def test_auc(self):
        assert h._auc([0.0, 0.1], [0.5, 0.9]) == 1.0
        assert h._auc([0.5, 0.9], [0.0, 0.1]) == 0.0
        assert h._auc([0.3], [0.3]) == 0.5
        assert h._auc([float("inf")], [float("inf")]) == 0.5
        with pytest.raises(ValueError, match="both classes"):
            h._auc([0.1], [])

    def test_bootstrap_is_seeded_and_brackets_the_estimate(self):
        a, b = [0.0, 0.1, 0.2, 0.4], [0.3, 0.5, 0.6, 0.9]
        r1, r2 = h._bootstrap(h._auc, a, b, n=500), h._bootstrap(h._auc, a, b, n=500)
        assert r1 == r2 and r1["ci95"][0] <= r1["estimate"] <= r1["ci95"][1]


class TestSkeletonsAndDecoys:
    pytestmark = SHORESH        # the sign registry, the sign values and the lexicon

    def test_loud_skeleton_reports_unmapped_signs(self):
        assert h.loud_skeleton("KU-NI-SU") == ("kns", [])
        skel, unmapped = h.loud_skeleton("PI-QI-TE")
        assert unmapped == ["QI"] and skel == "pt"                  # extract_skeleton would return "pt" silently

    def test_lexicon_spelling_maps_to_corpus_signs(self):
        assert h.corpus_spelling("PI-QI-TE") == "PI-*34-TE"
        assert h.loud_skeleton(h.corpus_spelling("SI-DU-QI-KU-MI")) == ("sdqkm", [])
        assert h.corpus_spelling("KU-NI-SU") == "KU-NI-SU"
        assert h.lexicon_sign_aliases() == {"QI": "*34"}

    def test_lexicon_alias_needs_its_resolution_summary_entry(self, monkeypatch):
        monkeypatch.setattr(h, "_resolution_pairs", lambda: {"*301=NA"})
        with pytest.raises(SystemExit, match=r"\*34=QI"):
            h.lexicon_sign_aliases()

    def test_shuffle_never_repeats_the_source_skeleton(self):
        rng = random.Random(1)
        for word in ("A-KA-NU", "KU-NI-SU", "JA-DI-KI-TU"):
            s = h.shuffle_new_skeleton(rng, word)
            assert s and h.extract_skeleton(s) != h.extract_skeleton(word)
        assert h.shuffle_new_skeleton(rng, "KU-KU") is None

    def test_fabrication_is_position_and_length_matched(self):
        words = ["KU-NI-SU", "KU-RO", "A-KA-NU", "SA-RA-ME", "DA-MA-TE", "I-DA-MA-TE", "PA-JA-RE", "TI-TI-KU"]
        tables = h.position_tables(words)
        rng = random.Random(3)
        fab = h.fabricate(rng, 3, 3, tables, set(words))
        assert fab and fab not in words and h._skel_len(fab) == 3 and h._ocp_ok(fab)
        signs = fab.split("-")
        assert signs[0] in tables["initial"][0] and signs[-1] in tables["final"][0]
        assert h.fabricate(rng, 2, 5, tables, set(words), tries=50) is None   # impossible: None, never a near miss

    def test_ocp(self):
        assert h._ocp_ok("KU-NI-SU") and not h._ocp_ok("TI-TI-KU")

    def test_campaign_signs_come_from_the_resolution_summary(self):
        signs = h.campaign_signs()
        assert {"PA₃", "PA3", "*301", "*34", "QI", "ZU"} <= signs and "KU" not in signs

    def test_proposed_values_are_campaign_signs(self, tmp_path, monkeypatch):
        summary = {"phonemic": ["AU=/aw/"], "proposed": {"phonemic": [{"entry": "*34=QI", "tier": "CANDIDATE"}]}}
        (tmp_path / "sign_values.json").write_text(json.dumps({"resolution_summary": summary}), encoding="utf-8")
        monkeypatch.setattr(h, "DATA_DIR", tmp_path)
        assert {"AU", "*34", "QI"} <= h.campaign_signs()
        assert h.lexicon_sign_aliases() == {"QI": "*34"}


class TestGoldenWords:
    def test_deterministic_sorted_pinned(self, monkeypatch):
        pool = [f"W{i}-A" for i in range(400)] + list(h.PINNED_WORDS)
        monkeypatch.setattr(h, "load_corpus_words", lambda: pool)
        monkeypatch.setattr(h, "extract_skeleton", lambda w: "x")
        a, b = h.golden_words(), h.golden_words()
        assert a == b == sorted(a) and len(a) == h.GOLDEN_SIZE
        assert all(a.count(p) == 1 for p in h.PINNED_WORDS)

    def test_small_pool_and_missing_pins_are_loud(self, monkeypatch, capsys):
        monkeypatch.setattr(h, "load_corpus_words", lambda: ["A-B", "C-D"])
        monkeypatch.setattr(h, "extract_skeleton", lambda w: "x")
        with pytest.raises(ValueError, match="needed"):
            h.golden_words()
        assert "pinned words not in the corpus" in capsys.readouterr().err


class TestFixtureWriting:
    @pytest.fixture
    def tracked(self, tmp_path, monkeypatch):
        inp = tmp_path / "input.json"
        inp.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(h, "tracked_inputs", lambda: [inp, tmp_path / "absent.json"])
        monkeypatch.setattr(h, "REPO", tmp_path)
        return inp

    def test_missing_inputs_are_recorded_and_their_arrival_is_a_change(self, tracked, tmp_path):
        before = h.input_hashes()
        assert before["absent.json"] is None
        (tmp_path / "absent.json").write_text("[]", encoding="utf-8")
        assert h.changed_inputs(before, h.input_hashes()) == ["absent.json"]

    def test_input_change_mid_run_writes_nothing(self, tracked, tmp_path):
        before = h.input_hashes()
        tracked.write_text('{"x": 1}', encoding="utf-8")
        target = tmp_path / "fx.json"
        with pytest.raises(SystemExit, match="NOT written"):
            h.write_fixture(target, {"a": 1}, before)
        assert not target.exists() and not list(tmp_path.glob("*.tmp-*"))

    def test_existing_fixture_is_never_overwritten(self, tracked, tmp_path):
        target = tmp_path / "fx.json"
        target.write_text("original", encoding="utf-8")
        with pytest.raises(SystemExit, match="exists"):
            h._refuse_existing(target)
        with pytest.raises(FileExistsError):
            h.write_fixture(target, {"a": 1}, h.input_hashes())
        assert target.read_text(encoding="utf-8") == "original" and not list(tmp_path.glob("*.tmp-*"))

    def test_written_fixture_is_complete_json_with_provenance(self, tracked, tmp_path):
        target = tmp_path / "fx.json"
        before = h.input_hashes()
        h.write_fixture(target, {"a": 1}, before)
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["a"] == 1 and data["provenance"]["input_sha256"] == before

    def test_nan_is_refused_not_written(self, tracked, tmp_path):
        target = tmp_path / "fx.json"
        with pytest.raises(ValueError):
            h.write_fixture(target, {"a": float("nan")}, h.input_hashes())
        assert not target.exists()

    def test_baseline_refuses_a_gold_set_from_other_inputs(self, tracked, tmp_path):
        gold = tmp_path / "gold.json"
        before = h.input_hashes()
        gold.write_text(json.dumps({"provenance": {"input_sha256": {**before, "input.json": "0" * 64}}}),
                        encoding="utf-8")
        with pytest.raises(SystemExit, match="other inputs"):
            h._read_gold(gold, before)
        gold.write_text(json.dumps({"positives": [], "provenance": {"input_sha256": before}}), encoding="utf-8")
        assert h._read_gold(gold, before)["positives"] == []


class TestLatency:
    def test_failed_cli_call_stops_the_run(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 2, "", "Traceback"))
        with pytest.raises(SystemExit, match="exited 2"):
            h._cli_latency(["KU-RO"])

    def test_missing_rss_stops_the_run(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "0.1 real"))
        with pytest.raises(SystemExit, match="RSS"):
            h._cli_latency(["KU-RO"])
