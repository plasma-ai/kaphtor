"""Unit checks on tools/linear_a/analysis/: no data folder is read; outputs land in tmp folders."""
import json
import sys

from tools.linear_a.analysis import gordon_morphology_overlay as gmo
from tools.linear_a.analysis import lb_roc_calibration as lrc


def test_strip_digits_drops_sign_subscripts():
    assert gmo.canonical_word("KI-RE-TA₂", strip_digits=True) == "KI-RE-TA"
    assert gmo.canonical_word("PU₂-RA₂", strip_digits=True) == "PU-RA"


def test_without_strip_digits_the_subscript_stays():
    assert gmo.canonical_word("KI-RE-TA₂") == "KI-RE-TA2"


def test_a_subscripted_final_matches_the_template_through_the_stripped_form():
    assert not gmo.template_match("A-DU-NI₂", "an_gentilic_name")
    assert gmo.template_match("A-DU-NE₂", "an_gentilic_name")   # a made-up sign: only the stripped form ends -NE


def _features(path):
    rows = [{"label": 1, "numeric_follower_rate": v} for v in (0.6, 0.8, 0.9)]
    rows += [{"label": 0, "numeric_follower_rate": v} for v in (0.1, 0.2)]
    path.write_text(json.dumps({"metadata": {"features": ["numeric_follower_rate"]}, "features": rows}),
                    encoding="utf-8")
    return path


def test_a_separating_feature_calibrates_at_the_boundary():
    values = [(0.6, 1), (0.8, 1), (0.9, 1), (0.1, 0), (0.2, 0)]
    result, _ = lrc.calibrate_feature(values, "numeric_follower_rate", "gte", 3, 2)
    assert result["auc"] == 1.0
    assert (result["threshold"], result["tpr"], result["fpr"]) == (0.6, 1.0, 0.0)


def test_a_rerun_backs_up_the_thresholds_it_replaces(monkeypatch, tmp_path):
    out, backups = tmp_path / "thresholds.json", tmp_path / "backups"
    backup = lrc.backup_existing
    monkeypatch.setattr(lrc, "backup_existing", lambda path: backup(path, backups))
    monkeypatch.setattr(sys, "argv", ["lb_roc_calibration", "--input", str(_features(tmp_path / "f.json")),
                                      "--output", str(out)])
    assert lrc.main() == 0
    first = out.read_text(encoding="utf-8")
    assert not backups.exists()
    assert lrc.main() == 0
    assert [p.read_text(encoding="utf-8") for p in backups.iterdir()] == [first]


def test_a_missing_feature_file_stops_with_exit_2(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["lb_roc_calibration", "--input", str(tmp_path / "absent.json"),
                                      "--output", str(tmp_path / "out.json")])
    assert lrc.main() == 2
    assert not (tmp_path / "out.json").exists()
