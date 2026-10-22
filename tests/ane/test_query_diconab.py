import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script():
    path = ROOT / "tools" / "ane" / "query_diconab.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def test_diconab_search_parser_preserves_occurrence_and_record_identity():
    diconab = load_script()
    source = """
    <div class="my-4"><strong>83</strong> word occurrences found</div>
    <a class="page-link" href="/words/attestations?ag=1&amp;p=3">3</a>
    <tr class="border border-start-0 border-end-0">
      <th>1.</th>
      <td><span class="fs-5 fw-bold text-nowrap">{mlk}</span> –
          <span class="text-muted small">Subst. sg. construct</span></td>
      <td><a href="/inscriptions/3287">record</a>
          <span class="fw-bold text-nowrap small">ARIth 1</span></td>
      <td class="col text-end">ʾl-</td>
      <td class="col ps-1"><mark title="word position (from the beginning): 6">mlk</mark></td>
    </tr>
    """
    result = diconab.parse_search_results(source, 1)
    assert result["total_occurrences"] == 83
    assert result["shown_on_page"] == 1
    assert result["available_pages_reported"] == 3
    assert result["pagination_followed"] is False
    assert result["automatic_pagination_followed"] is False
    assert result["explicit_page_requested"] is False
    assert result["occurrences"][0] == {
        "form": "{mlk}",
        "category": "Subst. sg. construct",
        "inscription_id": "3287",
        "siglum": "ARIth 1",
        "word_position": 6,
        "left_context": "ʾl-",
        "right_context": "mlk",
        "record_url": "https://diconab.huma-num.fr/inscriptions/3287",
    }


def test_diconab_record_parser_extracts_citation_without_embedded_html():
    diconab = load_script()
    source = """
    <h2 class="display-6 fw-bold border-bottom"><i></i> ARIth 1
      <nav></nav></h2>
    <a data-copy-content="Nehmé, “ARIth 1”, in &lt;em&gt;DiCoNab&lt;/em&gt;, 2026,
       &lt;a href=&quot;https://diconab.huma-num.fr/inscriptions/3287&quot;&gt;record&lt;/a&gt;"></a>
    <a href="/sites/1271"><strong>Site north-west of Eilat</strong>, Sinai (Egypt)</a>
    <div class="col fs-5 mb-1 "><div class="fw-bold"><span>Language of text</span></div>
      <div>Undetermined</div></div>
    <div class="col fs-5 mb-1 "><div class="fw-bold"><span>Commentary</span></div>
      <div>Long narrative material must not be cached.</div></div>
    <div class="fw-bold">Reading and translation</div>
    <div class="fst-italic">ʾnh ʿdyw b{r}<br>tʿlbh ʾlmlk</div>
    <div class="arabic">ا ن ه</div>
    <strong>last change</strong>: 21/04/2026 - 15:29:28<br>
    <strong>created on</strong>: 19/04/2026 - 14:58:28
    """
    record = diconab.parse_record(source, 3287)
    assert record["siglum"] == "ARIth 1"
    assert record["site"] == "Site north-west of Eilat, Sinai (Egypt)"
    assert record["metadata"]["Language of text"] == "Undetermined"
    assert "Commentary" not in record["metadata"]
    assert record["transliteration_display"] == "ʾnh ʿdyw b{r} tʿlbh ʾlmlk"
    assert "<em>" not in record["citation"]
    assert record["last_change"] == "21/04/2026 - 15:29:28"


def test_diconab_cli_defaults_are_conservative():
    diconab = load_script()
    parser = diconab.build_parser()
    args = parser.parse_args(["mlk", "--delay", "1"])
    assert args.query == "mlk"
    assert args.match == "exact"
    assert diconab.MIN_DELAY == 1.0


def test_diconab_cli_refuses_unfiltered_and_subsecond_requests(monkeypatch):
    diconab = load_script()
    monkeypatch.setattr(sys, "argv", ["query_diconab.py"])
    with pytest.raises(SystemExit):
        diconab.main()
    monkeypatch.setattr(sys, "argv", ["query_diconab.py", "mlk", "--delay", "0.5"])
    with pytest.raises(SystemExit):
        diconab.main()


def test_diconab_search_parser_accepts_genuine_zero_and_rejects_interstitial():
    diconab = load_script()
    zero = '<div class="my-4"><strong>0</strong> word occurrences found</div>'
    result = diconab.parse_search_results(zero, 1)
    assert result["total_occurrences"] == 0
    assert result["occurrences"] == []
    with pytest.raises(RuntimeError, match="result-count marker not found"):
        diconab.parse_search_results("<html><h1>Maintenance</h1></html>", 1)


def test_diconab_request_bytes_throttles_every_live_call(monkeypatch):
    diconab = load_script()
    delays = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"ok"

    class Client:
        def open(self, _request, timeout):
            assert timeout == 60
            return Response()

    monkeypatch.setattr(diconab, "throttle_live_request", delays.append)
    assert diconab.request_bytes(Client(), "https://example.invalid", delay=2.0) == b"ok"
    assert delays == [2.0]


def test_diconab_explicit_page_request_is_auditable(monkeypatch, tmp_path):
    diconab = load_script()
    monkeypatch.setattr(diconab, "CACHE", tmp_path)
    monkeypatch.setattr(diconab, "RATE_LIMIT_STATE", tmp_path / ".last-live-request")
    monkeypatch.setattr(diconab, "opener", object)
    calls = []
    form = b'''<select name="word_attestation_filter_form[fbEntityField]"></select>
      <input name="word_attestation_filter_form[_token]" value="token">'''
    results = b'<div class="my-4"><strong>0</strong> word occurrences found</div>'

    def fake_request(_client, url, *, data=None, ajax=False, accept="", delay=0):
        calls.append({"url": url, "data": data, "ajax": ajax, "delay": delay})
        return form if len(calls) == 1 else results

    monkeypatch.setattr(diconab, "request_bytes", fake_request)
    wrapper = diconab.search("missing", "word", "exact", 3, 2.0, False)
    assert len(calls) == 3
    assert all(call["delay"] == 2.0 for call in calls)
    assert calls[-1]["url"].endswith("?ag=1&p=3")
    assert wrapper["response"]["explicit_page_requested"] is True
    assert wrapper["response"]["automatic_pagination_followed"] is False
    assert "form submission returned page 1" in wrapper["scope_note"]
