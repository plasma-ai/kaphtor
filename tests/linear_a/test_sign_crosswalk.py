"""tools/core/sign_crosswalk.py: sign labels from corpus, SigLA, crop manifest and lineara boxes -> registry codes.

The unit tests build a Crosswalk from inline rows. The `data` tests read data/linear-a/sign-registry.json and
sign_crosswalk_overrides.json, read-only; the lineara test is `maintainer`, run only with a lashon-ha-kretan checkout.
"""
import json
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.sign_crosswalk import OVERRIDES_PATH, Crosswalk, base_code, default_crosswalk, is_klasma
from tools.paths import LINEAR_A_DATA

REGISTRY_PATH = LINEAR_A_DATA / "sign-registry.json"
NEEDS_REGISTRY = pytest.mark.skipif(not REGISTRY_PATH.exists(), reason="sign-registry.json is not in this checkout")

REGISTRY = [
    {"ab_number": "AB08", "name": "a", "unicode_glyph": "\U00010607"},
    {"ab_number": "A701", "name": "A", "unicode_glyph": "\U00010740"},
    {"ab_number": "AB56", "name": "", "unicode_glyph": "\U00010630"},
    {"ab_number": "AB21F", "name": "OVISf", "unicode_glyph": "\U00010610"},
    {"ab_number": "AB120", "name": "GRA", "unicode_glyph": "\U00010648"},
    {"ab_number": "AB120B", "name": "GRA", "unicode_glyph": None},
    {"ab_number": "A301", "name": "", "unicode_glyph": "\U00010655"},
    {"ab_number": "A411VAS", "name": "vessel ideogram (VAS series)", "unicode_glyph": None},
    {"ab_number": "A411VASB", "name": "vessel ideogram (VAS series)", "unicode_glyph": None},
    {"ab_number": "A709-2", "name": "L2", "unicode_glyph": "\U00010749"},
    {"ab_number": "AB302", "name": "OLE", "unicode_glyph": None},
    {"ab_number": "AB67", "name": "ki", "unicode_glyph": "\U00010641"},
    {"ab_number": "A1000", "name": "SUS+SI+RE", "unicode_glyph": None},
    {"ab_number": "AB131", "name": "VIN", "unicode_glyph": None},
    {"ab_number": "A188", "name": "", "unicode_glyph": None},
    {"ab_number": "AB86", "name": "", "unicode_glyph": None},
    {"ab_number": "AB122", "name": "OLIV", "unicode_glyph": None},
    {"ab_number": "A406VAS", "name": "vessel ideogram (VAS series)", "unicode_glyph": None},
    {"ab_number": "AB16", "name": "qa₂", "unicode_glyph": None},
]
LINEARA = [
    ("\U00010607", "A"),
    ("\U00010630", "PA₃"),
    ("\U00010101", "*900"),
    ("\U00010641", "KI"),
]


@pytest.mark.parametrize("label, codes, kind", [
    ("*411", ("A411VAS",), "sign"),                    # bare vessel number
    ("SUS+SI+RE", ("A1000",), "sign"),                 # registry name that is itself a ligature
    ("AB131/VINA", ("AB131",), "sign"),                # alternatives: the resolvable half
    ("QA2", ("AB16",), "sign"),                        # digit for subscript
    ("'*188'", ("A188",), "sign"),                     # stray quotes
    ("*OLIV", ("AB122",), "sign"),                     # star on a Latin logogram
    ("*406VAS+KE", ("A406VAS", "?"), "ligature"),      # VAS suffix inside a ligature, KE unknown here
    ("*86+'*188'", ("AB86", "A188"), "ligature"),
])
def test_residue_rules(cw, label, codes, kind):
    r = cw.resolve(label)
    assert (r.codes, r.kind) == (codes, kind)


def test_ambiguous_label_lists_every_candidate():
    pairs = LINEARA + [("\U00010740", "A")]          # lineara gives AB08 and fraction A701 the label A
    cw = Crosswalk(REGISTRY, pairs, overrides={})
    r = cw.resolve("A")
    assert r.ambiguous and set(r.alternatives) == {("AB08",), ("A701",)}
    assert r.codes == r.alternatives[0]


def test_unambiguous_has_single_alternative(cw):
    assert cw.resolve("AB8").alternatives == (("AB08",),)


# -- codes, glyph checks and stand-ins ----------------------------------------------

def test_registry_codes_resolve_to_themselves(cw):
    for code in ("A709-2", "A411VASB", "AB120B", "AB21F"):
        assert cw.resolve(code).codes == (code,), code


def test_sigla_variant_digit_form(cw):
    assert cw.resolve("A709-2").codes == ("A709-2",)
    assert cw.resolve("A7092").codes == ("A709-2",)


def test_alternative_with_variant_letter_picks_the_variant():
    reg = REGISTRY + [{"ab_number": "AB21", "name": "qi", "unicode_glyph": None},
                      {"ab_number": "AB131A", "name": "VIN", "unicode_glyph": None}]
    cw = Crosswalk(reg, LINEARA, overrides={})
    assert cw.resolve("AB21/OVISF").codes == ("AB21F",)
    r = cw.resolve("AB131/VINA")
    assert r.codes == ("AB131A",) and not r.ambiguous


def test_label_glyph_conflict_is_flagged(cw):
    r = cw.resolve("KI", glyph="\U00010607")          # label KI, glyph A (AB08)
    assert r.codes == ("AB08",) and r.ambiguous
    assert r.alternatives[0] == ("AB08",) and ("AB67",) in r.alternatives
    assert "label/glyph disagree" in r.note


def test_label_agreeing_with_glyph_is_not_flagged(cw):
    r = cw.resolve("KI", glyph="\U00010641")
    assert not r.ambiguous and r.note == ""


def test_stand_in_glyph_is_ambiguous():
    # lineara draws two different GORILA signs with one Unicode glyph (MA+RU and *560 both as A559).
    reg = REGISTRY + [{"ab_number": "A559", "name": "MA+RU", "unicode_glyph": "\U000106E2"},
                      {"ab_number": "A560", "name": "", "unicode_glyph": None}]
    pairs = LINEARA + [("\U000106E2", "MA+RU"), ("\U000106E2", "*560")]
    cw = Crosswalk(reg, pairs, overrides={})
    r = cw.resolve("MA+RU", glyph="\U000106E2")
    assert r.ambiguous and set(r.alternatives) >= {("A559",), ("A560",)}


def test_base_and_its_own_variant_are_not_a_conflict_or_stand_in():
    glyph = "\U00010677"
    reg = REGISTRY + [{"ab_number": "AB131A", "name": "VIN", "unicode_glyph": glyph}]
    cw = Crosswalk(reg, LINEARA + [(glyph, "VIN"), (glyph, "VINa")], overrides={})
    r = cw.resolve("VIN", glyph=glyph)
    assert r.codes == ("AB131A",) and not r.ambiguous


def test_klasma_glyph_stand_ins_resolve_in_fraction_context():
    glyph = "\U00010743"                     # a klasmatogram lineara also labels E
    reg = REGISTRY + [{"ab_number": "AB38", "name": "e", "unicode_glyph": "\U00010621"},
                      {"ab_number": "A704", "name": "E", "unicode_glyph": glyph}]
    cw = Crosswalk(reg, LINEARA + [(glyph, "E"), (glyph, "¹⁄₄")], overrides={})
    r = cw.resolve("¹⁄₄", glyph=glyph, token_class="fraction")
    assert r.codes == ("A704",) and not r.ambiguous


def test_sign_fraction_name_collision_flagged_without_class(cw):
    r = cw.resolve("A")
    assert r.codes == ("AB08",) and r.ambiguous and ("A701",) in r.alternatives


def test_fraction_class_never_falls_back_to_a_syllable(cw):
    assert cw.resolve("KI", token_class="fraction").kind == "unresolved"


def test_ligature_lost_component_survives_the_glyph_route(cw):
    r = cw.resolve("OLE+[?]", glyph="\U00010641")    # glyph alone would say a plain sign
    assert r.kind == "ligature" and r.codes[-1] == "?"


@pytest.mark.parametrize("code, base", [
    ("AB131A", "AB131"), ("A309A", "A309"), ("A411VASB", "A411VAS"), ("A411VAS", "A411VAS"),
    ("A709-2", "A709-2"), ("AB08", "AB08"),
])
def test_base_code(code, base):
    assert base_code(code) == base


def test_composite_glyph_named_with_a_lost_slot_is_complete():
    # lineara names the whole GORILA composite A510 "QA2+[?]+PU": the glyph is the complete sign.
    glyph = "\U000106C2"
    reg = REGISTRY + [{"ab_number": "A510", "name": "", "unicode_glyph": glyph}]
    cw = Crosswalk(reg, LINEARA + [(glyph, "QA2+[?]+PU")], overrides={})
    r = cw.resolve("QA2+[?]+PU", glyph=glyph)
    assert r.codes == ("A510",) and r.kind == "sign"


def test_lost_slot_label_whose_glyph_is_the_surviving_part_stays_partial():
    # lineara labels the VIR glyph "VIR+[?]" as well: that glyph is the surviving part, not a composite.
    glyph = "\U00010647"
    reg = REGISTRY + [{"ab_number": "AB100", "name": "VIR", "unicode_glyph": glyph}]
    cw = Crosswalk(reg, LINEARA + [(glyph, "VIR"), (glyph, "VIR+[?]")], overrides={})
    r = cw.resolve("VIR+[?]", glyph=glyph)
    assert r.kind == "ligature" and r.codes == ("AB100", "?")


def test_unresolved_label_is_no_evidence_of_conflict():
    glyph = "\U00010647"
    reg = REGISTRY + [{"ab_number": "AB180", "name": "", "unicode_glyph": glyph}]
    r = Crosswalk(reg, LINEARA, overrides={}).resolve("HIDE+[?]", glyph=glyph)   # HIDE is no registry name
    assert r.codes == ("AB180", "?") and "disagree" not in r.note


def test_composite_glyph_against_component_label_is_its_own_note():
    glyph = "\U000106C3"
    reg = REGISTRY + [{"ab_number": "A638", "name": "", "unicode_glyph": glyph},
                      {"ab_number": "A307", "name": "", "unicode_glyph": None}]
    cw = Crosswalk(reg, LINEARA, overrides={})
    r = cw.resolve("*307+*307", glyph=glyph)
    assert r.codes == ("A638",) and "composite glyph against component label" in r.note
    assert "label/glyph disagree" not in r.note


def test_lost_component_ligature_still_checks_its_label():
    r = Crosswalk(REGISTRY, LINEARA, overrides={}).resolve("KI+[?]", glyph="\U00010607")   # glyph AB08, label KI
    assert r.codes == ("AB08", "?") and "label/glyph disagree" in r.note


def test_ligature_component_ambiguity_is_a_note_not_a_flag(cw):
    r = cw.resolve("A+KI")
    assert not r.ambiguous


def test_override_matches_without_underdot():
    cw = Crosswalk(REGISTRY, LINEARA, overrides={"*301": {"kind": "sign", "codes": ["AB67"]}})
    assert cw.resolve("*301̣").codes == ("AB67",)


def test_combining_underdot_is_stripped_and_noted(cw):
    r = cw.resolve("*301̣")
    assert r.codes == ("A301",) and "dotted" in r.note


def test_rendered_fraction_without_glyph(cw):
    r = cw.resolve("≈¹⁄₄")
    assert (r.kind, r.codes) == ("fraction", ()) and "1/4" in r.note


@pytest.fixture
def cw():
    return Crosswalk(REGISTRY, LINEARA, overrides={})


def test_glyph_route_wins(cw):
    r = cw.resolve("PA₃", glyph="\U00010630")
    assert (r.kind, r.codes, r.rule) == ("sign", ("AB56",), "glyph")


def test_glyph_with_damage_mark_is_stripped(cw):
    assert cw.resolve("A", glyph="\U00010607\U0001076B").codes == ("AB08",)


@pytest.mark.parametrize("label, code", [
    ("AB8", "AB08"), ("AB08", "AB08"), ("AB120b", "AB120B"),
    ("A411b", "A411VASB"), ("A411", "A411VAS"), ("A7092", "A709-2"),
])
def test_code_normalisation(cw, label, code):
    r = cw.resolve(label)
    assert (r.codes, r.rule) == ((code,), "code")


@pytest.mark.parametrize("label, code", [("*21F", "AB21F"), ("*301", "A301"), ("*411-VS", "A411VAS")])
def test_star_forms(cw, label, code):
    assert cw.resolve(label).codes == (code,)


def test_lineara_label_bridges_unnamed_registry_sign(cw):
    r = cw.resolve("PA₃")
    assert (r.codes, r.rule) == (("AB56",), "lineara_label")


def test_lineara_divider_label(cw):
    r = cw.resolve("*900")
    assert (r.kind, r.codes) == ("divider", ())


def test_name_collision_follows_token_class(cw):
    assert cw.resolve("A").codes == ("AB08",)
    assert cw.resolve("A", token_class="fraction").codes == ("A701",)


def test_base_sign_beats_lettered_variant(cw):
    r = cw.resolve("GRA")
    assert r.codes == ("AB120",) and not r.ambiguous


def test_ligature_components(cw):
    r = cw.resolve("OLE+KI")
    assert (r.kind, r.codes, r.rule) == ("ligature", ("AB302", "AB67"), "ligature")


def test_ligature_with_unknown_component(cw):
    r = cw.resolve("OLE+?")
    assert r.kind == "ligature" and r.codes == ("AB302", "?")


@pytest.mark.parametrize("label, kind", [("5", "numeral"), ("[?]", "lacuna"), ("\U00010101", "divider")])
def test_structural_classes(cw, label, kind):
    assert cw.resolve(label).kind == kind


def test_editorial_brackets_are_ignored(cw):
    assert cw.resolve("[KI]").codes == ("AB67",)


def test_unresolved_is_never_guessed(cw):
    r = cw.resolve("N800")
    assert (r.kind, r.codes, r.rule) == ("unresolved", (), "none")


def test_override_wins(tmp_path):
    cw = Crosswalk(REGISTRY, LINEARA, overrides={"N800": {"kind": "sign", "codes": ["AB67"], "note": "test"}})
    r = cw.resolve("N800")
    assert (r.codes, r.rule, r.note) == (("AB67",), "override", "test")


def test_override_naming_an_unknown_code_raises():
    with pytest.raises(ValueError):
        Crosswalk(REGISTRY, LINEARA, overrides={"X": {"kind": "sign", "codes": ["NOPE"]}})


@pytest.mark.parametrize("code, klasma", [
    ("A701", True), ("A709-2", True), ("A713", True), ("A726", True), ("A732", True),
    ("A805", False), ("A501", False), ("AB08", False), ("A7", False),
])
def test_every_700_series_code_is_a_klasma(code, klasma):
    assert is_klasma(code) is klasma


def test_jE_in_fraction_context_is_the_klasmatogram():
    cw = Crosswalk(REGISTRY + [{"ab_number": "AB46", "name": "je", "unicode_glyph": None},
                               {"ab_number": "A732", "name": "JE", "unicode_glyph": "\U00010755",
                                "components": ["A707", "A704"]}], [])
    r = cw.resolve("JE", token_class="fraction")
    assert (r.kind, r.codes) == ("fraction", ("A732",))
    assert cw.resolve("JE", token_class="single_sign").codes == ("AB46",)


def test_components_come_from_the_registry_row():
    cw = Crosswalk(REGISTRY + [{"ab_number": "A717", "name": "DD", "unicode_glyph": None,
                                "components": ["A703", "A703"]}], [])
    assert cw.components("A717") == ("A703", "A703")
    assert cw.components("AB08") == ()
    assert cw.components("NOPE") == ()


def test_lashon_dir_comes_only_from_the_environment(monkeypatch, tmp_path):
    from tools.core import sign_crosswalk
    monkeypatch.delenv("LASHON_HA_KRETAN_DIR", raising=False)
    assert sign_crosswalk.lashon_dir() is None
    monkeypatch.setenv("LASHON_HA_KRETAN_DIR", str(tmp_path))
    assert sign_crosswalk.lashon_dir() == tmp_path


# -- real files, read-only ------------------------------------------------------------

@pytest.mark.data
@pytest.mark.skipif(not OVERRIDES_PATH.exists(), reason="sign_crosswalk_overrides.json is not in this checkout")
def test_overrides_file_is_valid_json():
    data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    assert isinstance(data.get("overrides"), dict)


@pytest.mark.data
@NEEDS_REGISTRY
def test_real_registry_cases():
    cw = default_crosswalk()
    assert cw.resolve("AB8").codes == ("AB08",)
    assert cw.resolve("A411b").codes == ("A411VASB",)
    assert cw.resolve("A7092").codes == ("A709-2",)
    assert cw.resolve("*21F").codes == ("AB21F",)


@pytest.mark.data
@NEEDS_REGISTRY
def test_real_registry_unicode_rows():
    cw = default_crosswalk()
    assert cw.resolve("*404-VS").codes == ("A404VAS",)
    assert cw.resolve("*405-VS").codes == ("A405VAS",)
    assert cw.resolve("*800").codes == ("A800",)
    assert cw.resolve("*806").codes == ("A806",)
    assert (cw.resolve("A711").kind, cw.resolve("A711").codes) == ("fraction", ("A711",))
    assert cw.components("A717") == ("A703", "A703")
    assert cw.components("A732") == ("A707", "A704")


@pytest.mark.data
@NEEDS_REGISTRY
def test_real_registry_covers_every_linear_a_code_point():
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["signs"]
    have = {s["rendering"]["unicode"] for s in registry if s.get("rendering", {}).get("unicode")}
    named = {f"U+{cp:X}" for cp in range(0x10600, 0x10780) if unicodedata.name(chr(cp), "")}
    assert named <= have, sorted(named - have)


@pytest.mark.maintainer
@NEEDS_REGISTRY
def test_real_lineara_bridge():
    cw = default_crosswalk()
    if not cw.has_lineara:
        pytest.skip("lashon-ha-kretan ideograms.js not present")
    assert cw.resolve("PA₃").codes == ("AB56",)
    assert cw.resolve("*900").kind == "divider"
