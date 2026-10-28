import bz2
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT =Path(__file__).resolve().parents[2]


def load_script(name):
    path = ROOT / "tools" / "ane" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def features(htid="mdp.39015008689583"):
    return {
        "htid": htid,
        "metadata": {
            "title": "Die Personennamen der Texte aus Ugarit.",
            "contributor": {"name": "Gröndahl, Frauke."},
            "pubDate": 1967,
            "accessRights": "ic",
        },
        "features": {
            "pageCount": 3,
            "pages": [
                {"seq": "00000001", "header": None, "body": None, "footer": None},
                {"seq": "00000112", "header": None, "footer": None,
                 "body": {"tokenPosCount": {"awldn": {"UNK": 1}, "Gott": {"NN": 2}}}},
                {"seq": "00000137", "header": {"tokenPosCount": {"123": {"CD": 1}}}, "footer": None,
                 "body": {"tokenPosCount": {"b'ldn": {"UNK": 2, "NN": 1}, "bldn": {"UNK": 1}}}},
            ],
        },
    }


def test_stubbytree_path_takes_every_third_character_of_the_clean_id():
    ht = load_script("query_hathitrust")
    assert ht.ef_relative_path("mdp.39015008689583") == "mdp/31088/mdp.39015008689583.json.bz2"
    # Both paths answered 206 on data.analytics.hathitrust.org (2026-10-28).
    assert ht.ef_relative_path("nc01.ark:/13960/t2v41mn4r") == (
        "nc01/a+30214/nc01.ark+=13960=t2v41mn4r.json.bz2"
    )
    assert ht.ef_relative_path("miun.adx6300.0001.001") == (
        "miun/a600,1/miun.adx6300,0001,001.json.bz2"
    )


def test_search_sums_pos_counts_skips_blank_pages_and_applies_offset():
    ht = load_script("query_hathitrust")
    hits = ht.search(features(), re.compile("ldn", re.IGNORECASE), 14)
    assert [h["seq"] for h in hits] == [112, 137]
    assert [h["printed_page"] for h in hits] == [98, 123]
    assert hits[1]["tokens"] == {"b'ldn": 3, "bldn": 1}


def test_search_reads_header_and_footer_tokens_and_leaves_pages_unnumbered_without_offset():
    ht = load_script("query_hathitrust")
    hits = ht.search(features(), re.compile("^123$"), None)
    assert hits == [{"seq": 137, "printed_page": None, "tokens": {"123": 1}}]


def test_catalog_items_keep_rights_and_holder():
    ht = load_script("query_hathitrust")
    payload = json.dumps({"records": {}, "items": [{
        "htid": "mdp.39015008689583", "rightsCode": "ic",
        "usRightsString": "Limited (search-only)", "orig": "University of Michigan", "enumcron": False,
    }]}).encode()
    assert ht.parse_catalog(payload) == [{
        "htid": "mdp.39015008689583", "rights": "ic", "us_rights": "Limited (search-only)",
        "holder": "University of Michigan", "enumeration": "",
    }]


def test_local_features_file_is_read_without_a_request_and_must_match_the_volume(tmp_path, monkeypatch):
    ht = load_script("query_hathitrust")
    monkeypatch.setattr(ht, "request_bytes", lambda *a, **k: pytest.fail("network request"))
    path = tmp_path / "ef.json.bz2"
    path.write_bytes(bz2.compress(json.dumps(features()).encode()))
    data, origin = ht.load_features("mdp.39015008689583", path, False, 1.5)
    assert origin["network_request_count"] == 0
    assert data["htid"] == "mdp.39015008689583"
    with pytest.raises(RuntimeError, match="not 'mdp.1'"):
        ht.load_features("mdp.1", path, False, 1.5)


@pytest.mark.parametrize("argv", [
    ["query_hathitrust.py", "mdp.39015008689583"],
    ["query_hathitrust.py", "mdp.39015008689583", "ldn", "--delay", "0.5"],
    ["query_hathitrust.py", "not an id", "ldn"],
])
def test_refuses_whole_volume_dumps_subsecond_requests_and_bad_ids(argv, monkeypatch):
    ht = load_script("query_hathitrust")
    monkeypatch.setattr(ht, "request_bytes", lambda *a, **k: pytest.fail("network request"))
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit):
        ht.main()
