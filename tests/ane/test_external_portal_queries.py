import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    path = ROOT / "tools" / "ane" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_deaps_search_parser_preserves_record_identity_and_does_not_paginate():
    deaps = load_script("query_deaps")
    source = """
    <div id='paging_info'>Displaying <b>all 2</b> objects</div>
    <div class='card mb-3' data-map-value='11076'>
      <h2><a href="/text_objects/11076">Cairo squeeze</a></h2>
      <div class='pb-2 fw-bold'>Dedicatory Inscription</div>
      <span class="unicode" dir="rtl">ברזמדנא זנה</span>
    <div class='card mb-3' data-map-value='11086'>
      <h2><a href="/text_objects/11086">Cairo stone</a></h2>
      <div class='pb-2 fw-bold'>Dedicatory Inscription</div>
    <div class='row'><div class='col' id='paging'>
    """
    result = deaps.parse_search_results(source, 1)
    assert result["total_objects"] == 2
    assert result["shown_on_page"] == 2
    assert result["pagination_followed"] is False
    assert result["records"][0]["object_id"] == 11076
    assert result["records"][0]["text_excerpt"] == "ברזמדנא זנה"


def test_deaps_record_parser_keeps_metadata_and_public_text_blocks():
    deaps = load_script("query_deaps")
    source = """
    <h1 class='d-inline-block'>Cairo EM JdE 36448</h1>
    <div class='fs 6'>Dedicatory Inscription</div>
    <h2 id='metadata'>Metadata</h2><dl class='row'>
      <dt>Language</dt><dd>Aramaic</dd><dt>Script</dt><dd>Aramaic</dd>
    </dl>
    <div aria-label='Text Editions' id='text_grid'>
      <div class='grid-text ed1' dir='rtl' lang='oar'>
        <button class="unicode btn">ברזמדנא</button>
        <button class="unicode btn">זנה</button>
      </div>
      <div class='grid-text ed1' dir='ltr' lang='en'>This shrine</div>
    <div aria-label='Word Information'></div>
    <span data-text-target='citation'>Moore, &#39;Cairo&#39;, DEAPS.</span>
    """
    row = deaps.parse_record(source, 11076)
    assert row["metadata"] == {"Language": "Aramaic", "Script": "Aramaic"}
    assert row["text_blocks"][0]["text"] == "ברזמדנא זנה"
    assert row["text_blocks"][1]["text"] == "This shrine"
    assert row["citation"] == "Moore, 'Cairo', DEAPS."


def test_elephantine_search_and_object_parsers_preserve_rights_fields():
    elephantine = load_script("query_elephantine")
    search = """
    <span>1 Results of 10745 Data Sets</span>
    <tr><td><a href="../texts/view.php?t=309606">text</a></td>
      <td><a href="object.php?o=309606">St. Cairo EM JdE 36448</a></td>
      <td>Shrine Dedicatory Inscription</td><td>Short summary</td></tr>
    """
    results = elephantine.parse_search_results(search)
    assert results["total_results"] == 1
    assert results["pagination_followed"] is False
    assert results["records"][0]["text_id"] == 309606

    record = """
    <h1>&nbsp;</h1><h1>St. Cairo EM JdE 36448</h1>
    <p>TEI-XML-File: https://example.invalid/309606.tei.xml</p>
    <tr><td class="zelle">Language, Primary</td><td class="zelle">Aramaic, Imperial</td></tr>
    <tr><td class="zelle">Dataset License</td><td class="zelle">CC BY-NC-SA 4.0</td></tr>
    <tr><td class="zelle">Data set citation</td><td class="zelle">Data set 309606.</td></tr>
    """
    parsed = elephantine.parse_object(record, 309606)
    assert parsed["dataset_license"] == "CC BY-NC-SA 4.0"
    assert parsed["dataset_citation"] == "Data set 309606."
    assert parsed["tei_url"].endswith("309606.tei.xml")


def test_elephantine_text_parser_exposes_but_does_not_fetch_tei():
    elephantine = load_script("query_elephantine")
    source = """
    <td><strong>St. Cairo EM JdE 36448</strong>
      <a>(More information about the Object)</a></td>
    <tr><td class="zelle">Publication No.</td><td class="zelle">TAD D.17.1</td></tr>
    <tr><td class="zelle">Modern Title</td><td class="zelle">Shrine inscription</td></tr>
    <ab xml:lang="Armi arc"><lb n="1"/>ברזמדנא זנה<lb n="2"/>רב חילא</ab>
    <ab xml:lang="Latn en"><lb n="1"/>This shrine<lb n="2"/>the chief</ab>
    <td class="zelle">TEI-XML-File</td><td class="zelle">https://example.invalid/309606.tei.xml</td>
    """
    parsed = elephantine.parse_text(source, 309606)
    assert parsed["publication_number"] == "TAD D.17.1"
    assert parsed["text_blocks"][0]["text"] == "ברזמדנא זנה\nרב חילא"
    assert parsed["tei_url"].endswith("309606.tei.xml")


def test_rsti_parser_preserves_uuid_properties_items_and_license():
    rsti = load_script("query_rsti")
    uuid = "98ef62eb-5eea-4b82-83a9-ff52cfef76f1"
    payload = f"""<?xml version="1.0"?>
    <result><ochre><metadata/><spatialUnit uuid="{uuid}" publicationDateTime="2025-06-10">
      <availability><license target="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA</license></availability>
      <context displayPath="RSTI/Ugarit/Acropolis"/>
      <identification><label>RS 1.001</label></identification>
      <description>Tablet, Alphabetic Ugaritic</description>
      <observations><observation><properties>
        <property><label>Museum Number</label><value>M8214</value></property>
        <property><label>Associated text</label><value uuid="de32293f-9b4b-435e-bf02-c4894863035b">RS 1.001</value></property>
      </properties></observation></observations>
      <items><text uuid="de32293f-9b4b-435e-bf02-c4894863035b"><identification><label>RS 1.001</label></identification></text></items>
    </spatialUnit></ochre></result>""".encode()
    parsed = rsti.parse_response(payload, uuid)
    assert parsed["label"] == "RS 1.001"
    assert parsed["license"]["label"] == "CC BY-NC-SA"
    assert parsed["properties"][1]["value_attributes"]["uuid"].startswith("de322")
    assert parsed["items"][0]["label"] == "RS 1.001"

    wrapper = {"response": parsed, "scope_note": "One response."}
    filtered = rsti.filter_immediate_items(wrapper, "RS 1.001")
    assert filtered["response"]["item_count"] == 1
    assert filtered["response"]["unfiltered_item_count"] == 1
    assert "filtered locally" in filtered["scope_note"]


@pytest.mark.parametrize("script_name", ["query_deaps", "query_elephantine", "query_rsti"])
def test_new_portal_clients_refuse_unfiltered_calls(script_name, monkeypatch):
    module = load_script(script_name)
    monkeypatch.setattr(sys, "argv", [f"{script_name}.py"])
    with pytest.raises(SystemExit):
        module.main()


@pytest.mark.parametrize("script_name,argv", [
    ("query_deaps", ["query_deaps.py", "TAD", "--delay", "0.5"]),
    ("query_elephantine", ["query_elephantine.py", "309606", "--delay", "0.5"]),
    ("query_rsti", ["query_rsti.py", "98ef62eb-5eea-4b82-83a9-ff52cfef76f1", "--delay", "0.5"]),
])
def test_new_portal_clients_refuse_subsecond_requests(script_name, argv, monkeypatch):
    module = load_script(script_name)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit):
        module.main()
