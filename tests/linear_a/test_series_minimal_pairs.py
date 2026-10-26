"""series_minimal_pairs: pairs counted only across one CV sign with the same vowel and once per distinct word,
damaged and non-syllabic words left out, a shuffle that keeps every slot's series counts, a planted alternation found
and a planted separation found short, the +1 correction and the ranking of pairs the null never makes, the command's
outputs, refusals and exits, and (data) the shipped corpus's D-T pairs."""
import hashlib
import json
import random
from collections import Counter, defaultdict

import pytest

from tools.core.corpus_utils import load_corpus
from tools.linear_a.analysis import series_minimal_pairs as smp


def _words(*forms):
    return [smp.parse(w) for w in forms]


def _corpus(tmp_path, *words):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"A1": {"transliteratedWords": list(words)}}), encoding="utf-8")
    return path


@pytest.mark.unit
def test_a_plain_syllable_parses_and_other_signs_stay_whole():
    assert smp.parse("KU-DA-TA₂-*301-A") == [("K", "U"), ("D", "A"), (None, "TA₂"), (None, "*301"), (None, "A")]


@pytest.mark.unit
def test_pairs_need_one_differing_syllable_with_the_same_vowel():
    counts = smp.count_pairs(_words("KU-DA", "KU-TA", "KU-RA", "KU-TI", "KU-DA-NI", "SU-TA", "SI-RA"))
    assert counts == Counter({("D", "T"): 1, ("D", "R"): 1, ("R", "T"): 1, ("K", "S"): 1})
    assert smp.count_pairs(_words("KU-DA", "KU-DA")) == Counter()


@pytest.mark.unit
def test_copies_a_shuffle_makes_count_once():
    assert smp.count_pairs(_words("KU-DA", "KU-DA", "KU-TA")) == Counter({("D", "T"): 1})


@pytest.mark.unit
def test_a_fixed_sign_never_forms_a_pair():
    assert smp.count_pairs(_words("KU-TA", "KU-TA₂", "KU-A", "KU-DA")) == Counter({("D", "T"): 1})


@pytest.mark.unit
def test_examples_name_the_words_of_each_pair():
    examples = defaultdict(list)
    smp.count_pairs(_words("KU-DA", "MA-RI", "KU-TA"), examples)
    assert examples[("D", "T")] == [(0, 2)]


@pytest.mark.unit
def test_damaged_single_sign_and_non_syllabic_words_are_left_out():
    corpus = {"A1": {"transliteratedWords": ["KU-DA", "[KU-TA", "KU-RA]", "KU-?", "DA", "\n", "KU-DA", "PU-VIN",
                                             "MA+RU-ME", "DI-𐄉-TI-DU", "TA-NA-I-*301-(TI/E)", "*402-VS-PA-TA-QE",
                                             "AU-RE-TE", "RO-A559-A534C", "NWA-*21F"]},
              "A2": {"transliteratedWords": ["KU-DA"]}}
    assert smp.word_types(corpus) == {"AU-RE-TE": ["A1"], "KU-DA": ["A1", "A2"], "NWA-*21F": ["A1"],
                                      "RO-A559-A534C": ["A1"]}


@pytest.mark.unit
def test_slot_classes_key_on_length_position_and_vowel():
    assert smp.slot_classes(_words("KU-DA", "MA-TA-*301", "SI-TA")) == {
        (2, 0, "U"): [0], (2, 1, "A"): [0, 2], (3, 0, "A"): [1], (3, 1, "A"): [1], (2, 0, "I"): [2]}


@pytest.mark.unit
def test_the_shuffle_keeps_each_slots_series_counts_and_the_fixed_signs():
    words = _words("KU-DA-*301", "MA-TA-*301", "NI-RA-*301", "KU-DA", "SA-TI", "PA₃-NA")
    slots = smp.slot_classes(words)
    for seed in range(20):
        out = smp.shuffled(words, slots, random.Random(seed))
        for (length, i, vowel), holders in slots.items():
            assert Counter(out[k][i] for k in holders) == Counter(words[k][i] for k in holders)
        assert [[s for s in w if s[0] is None] for w in out] == [[s for s in w if s[0] is None] for w in words]


@pytest.mark.unit
def test_a_planted_alternation_stands_out_and_a_planted_separation_falls_short():
    stems = [f"*3{n:02d}" for n in range(20)]                    # fixed first signs: only the second slot shuffles
    planted = {f"{stem}-{s}A": ["X"] for stem in stems[:10] for s in "DT"}
    apart = {f"{stem}-{s}A": ["X"] for stem in stems[:10] for s in "DR"}
    apart.update({f"{stem}-{s}A": ["X"] for stem in stems[10:] for s in "TN"})
    hit = smp.run(planted, 300, 1)["focus"]
    miss = smp.run(apart, 300, 1)["focus"]
    assert hit["observed"] == 10 and hit["p_upper"] < 0.05     # every stem split D/T: 2^10 / C(20,10) ≈ 0.0055
    assert hit["ratio"] > 1 and hit["p_lower"] == 1.0
    assert miss["observed"] == 0 and miss["ratio"] == 0       # null mean 20 × 2 × 10/40 × 10/39 ≈ 2.56
    assert 2 < miss["null_mean"] < 3.2 and miss["p_lower"] < 0.2


@pytest.mark.unit
def test_p_values_carry_the_plus_one_and_a_pair_the_null_never_makes_ranks_first(monkeypatch):
    monkeypatch.setattr(smp, "shuffled", lambda words, slots, rng: _words("MI-RA", "SO-NA"))
    result = smp.run({w: ["X"] for w in ("KU-DA", "KU-TA", "MI-RA", "SO-NA")}, 9, 0)
    focus = result["focus"]
    assert (focus["observed"], focus["null_mean"], focus["p_upper"], focus["p_lower"]) == (1, 0, 0.1, 1.0)
    assert focus["ratio"] is None and focus["rank_by_ratio"] == 1
    assert result["all_pairs"] == {"observed": 1, "null_mean": 0.0}


@pytest.mark.unit
def test_the_same_seed_gives_the_same_result():
    found = {w: ["X"] for w in ("KU-DA", "KU-TA", "MA-RI", "MA-NI", "SI-DU", "SI-TU", "PA-RA")}
    assert smp.run(found, 50, 7) == smp.run(found, 50, 7)


@pytest.mark.unit
def test_the_command_writes_both_files_and_reads_the_focus_either_way_round(tmp_path, monkeypatch, capsys):
    corpus = _corpus(tmp_path, "KU-DA", "KU-TA", "SI-DU", "SI-TU")
    monkeypatch.setattr(smp, "CORPUS_PATH", corpus)
    out = tmp_path / "out"
    assert smp.main(["--out", str(out), "--focus", "t-d", "--permutations", "5", "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["focus"]["pair"] == "D-T" and printed["focus"]["observed"] == 2
    assert [p["words"] for p in printed["focus_pairs"]] == [["KU-DA", "KU-TA"], ["SI-DU", "SI-TU"]]
    written = json.loads((out / "minimal_pairs.json").read_text(encoding="utf-8"))
    assert written["corpus_sha256"] == hashlib.sha256(corpus.read_bytes()).hexdigest()
    assert written["focus"] == printed["focus"]
    assert "| D-T |" in (out / "minimal_pairs.md").read_text(encoding="utf-8")


@pytest.mark.unit
@pytest.mark.parametrize("focus", ["D-D", "D", "DA-T", "A-T", "D-T-K"])
def test_a_bad_focus_is_refused(tmp_path, monkeypatch, focus):
    monkeypatch.setattr(smp, "CORPUS_PATH", tmp_path / "absent.json")
    with pytest.raises(SystemExit) as stop:
        smp.main(["--out", str(tmp_path / "out"), "--focus", focus])
    assert stop.value.code == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.unit
def test_an_existing_output_is_never_written_over(tmp_path, monkeypatch, capsys):
    (tmp_path / "minimal_pairs.md").write_text("kept", encoding="utf-8")
    monkeypatch.setattr(smp, "CORPUS_PATH", tmp_path / "absent.json")     # read, it would stop with exit 2
    assert smp.main(["--out", str(tmp_path), "--permutations", "1"]) == 1
    assert (tmp_path / "minimal_pairs.md").read_text(encoding="utf-8") == "kept"
    assert not (tmp_path / "minimal_pairs.json").exists()
    assert "refused" in capsys.readouterr().err


@pytest.mark.unit
def test_an_out_that_is_a_file_is_refused_before_the_run(tmp_path, monkeypatch, capsys):
    (tmp_path / "out").write_text("kept", encoding="utf-8")
    monkeypatch.setattr(smp, "CORPUS_PATH", tmp_path / "absent.json")
    assert smp.main(["--out", str(tmp_path / "out"), "--permutations", "1"]) == 1
    assert (tmp_path / "out").read_text(encoding="utf-8") == "kept"
    assert "refused" in capsys.readouterr().err


@pytest.mark.unit
def test_an_out_inside_data_is_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(smp, "DATA", tmp_path / "data")
    monkeypatch.setattr(smp, "CORPUS_PATH", tmp_path / "absent.json")
    assert smp.main(["--out", str(tmp_path / "data" / "linear-a"), "--permutations", "1"]) == 1
    assert not (tmp_path / "data").exists()
    assert "refused" in capsys.readouterr().err


@pytest.mark.unit
def test_a_missing_corpus_stops_with_exit_2(tmp_path, monkeypatch):
    monkeypatch.setattr(smp, "CORPUS_PATH", tmp_path / "absent.json")
    assert smp.main(["--out", str(tmp_path / "out"), "--permutations", "1"]) == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.data
def test_the_shipped_corpus_has_five_d_t_pairs():
    result = smp.run(smp.word_types(load_corpus()), 1, smp.DEFAULT_SEED)
    assert [p["words"] for p in result["focus_pairs"]] == [
        ["DA-RA", "TA-RA"], ["I-DI", "I-TI"], ["KA-DI", "KA-TI"], ["KU-DA", "KU-TA"], ["SI-DU", "SI-TU"]]
