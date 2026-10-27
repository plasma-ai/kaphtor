"""Tests for tools/core/semantic_gate.py: the context map, the document-type table and the frozen tagger (§3.1, A10,
A18). Synthetic corpora only, except the read-only check that every shipped support string is mapped."""
from __future__ import annotations

import json

import pytest

from tools.core import semantic_gate as sg
from tools.paths import LINEAR_A_DATA

CORPUS = LINEAR_A_DATA / "corpus.json"

RITUAL = frozenset({"ritual_cultic", "deity"})
POTTERY = frozenset({"pottery_vessel", "food_drink"})


def _doc(support: str, *tokens: str) -> dict:
    return {"support": support, "transliteratedWords": list(tokens)}


class TestMap:
    def test_every_mapped_domain_is_a_tagger_domain(self):
        domains = set(sg.tagger().DOMAIN_KEYWORDS)
        assert set().union(*sg.LOGOGRAM_DOMAINS.values()) <= domains
        assert set().union(*(d for d in sg.SUPPORT_DOMAINS.values() if d)) <= domains

    def test_the_logogram_map_is_the_one_ruled(self):
        """Pinned row by row (A18, A19): the map changes only by an amendment."""
        assert sg.LOGOGRAM_DOMAINS == {
            "GRA": {"agriculture", "food_drink"}, "CYP": {"flora", "food_drink"},
            "OLE": {"food_drink", "agriculture"}, "VIR": {"administrative", "kinship"},
            "VIN": {"food_drink", "agriculture"}, "OLIV": {"flora", "food_drink", "agriculture"},
            "*21M": {"fauna"}, "*21F": {"fauna"}, "*22F": {"fauna"}, "*22M": {"fauna"}, "*23M": {"fauna"},
            "HIDE": {"fauna", "textile"}, "*131B": {"food_drink"}, "*131C": {"food_drink"},
            "*118": {"metrology", "metallurgy"}, "NI": {"flora", "food_drink"}}
        assert sg.NUMBER_REQUIRED == {"*118", "NI"}
        assert sg.SPELLINGS == {"*OLIV": "OLIV", "VINb": "*131B", "VINc": "*131C"}
        assert sg.LAYOUT == {"\n", "𐄁"}

    def test_the_document_type_table_is_the_one_ruled(self):
        ritual = ["Stone vessel", "Stone-vessel fragment", "Stone object", "Metal object", "ivory object",
                  "Bronze bowl", "Silver pin", "Triton", "Stone ladle (HM 1545)",
                  "Fragment of a locally made limestone bowl or krater", "Serpentine cylindrical jar; HM 2479 + HM 2480",
                  "Square red-orange serpentine libation table (HM 5317)", "Square serpentine libation-table fragment",
                  "Stone libation table fragment", "Fragmentary circular serpentine libation table"]
        pottery = ["Clay vessel", "clay vessel", "Painted clay vessel", "Pithoid jar", "Inked inscription",
                   "Clay chalice rim (two nonjoining fragments); painted inscription"]
        unknown = ["Tablet", "Lames (short thin tablet)", "3-sided bar", "4-sided bar", "Roundel", "Nodule", "Sealing",
                   "Architecture", "Graffito", "Grave stele fragment", "Clay reel", "Clay larnax fragment",
                   "Loom weight", "Label", "Amygdaloid stone seal", "Clay spindle whorl", "Unspecified object", ""]
        assert sg.SUPPORT_DOMAINS == {**{s: RITUAL for s in ritual}, **{s: POTTERY for s in pottery},
                                      **{s: None for s in unknown}}

    @pytest.mark.parametrize("support, domains", [
        ("Stone vessel", RITUAL), ("Silver pin", RITUAL), ("Triton", RITUAL), ("Bronze bowl", RITUAL),
        ("Clay vessel", POTTERY), ("clay vessel", POTTERY), ("Pithoid jar", POTTERY), ("Inked inscription", POTTERY),
        ("Painted clay vessel", POTTERY), ("Tablet", None), ("Nodule", None), ("Clay larnax fragment", None),
        ("Loom weight", None), ("", None)])
    def test_document_types(self, support, domains):
        assert sg.SUPPORT_DOMAINS[support] == domains

    @pytest.mark.data
    @pytest.mark.skipif(not CORPUS.exists(), reason="corpus.json is not in this checkout")
    def test_every_shipped_support_is_mapped(self):
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))   # read only
        assert {d.get("support", "") for d in corpus.values()} <= set(sg.SUPPORT_DOMAINS)

    def test_an_unmapped_support_is_unknown(self):
        assert sg.Contexts({"X1": _doc("Bone plaque", "KA-PA", "𐄁")}).context("KA-PA") is None


class TestContext:
    def test_the_logogram_immediately_after_gives_its_domains_and_overrides_the_document(self):
        ctx = sg.Contexts({"X1": _doc("Stone vessel", "KA-PA", "VIN", "5")})
        assert ctx.context("KA-PA") == {"food_drink", "agriculture"}

    def test_ligatures_pool_with_their_base(self):
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", "OLE+KI", "3")}).context("KA-PA") == {"food_drink",
                                                                                                 "agriculture"}

    def test_without_a_logogram_the_document_type_counts(self):
        ctx = sg.Contexts({"X1": _doc("Stone vessel", "KA-PA", "—", "VIN"), "X2": _doc("Tablet", "DA-ME", "TE", "4"),
                           "X3": _doc("Tablet", "SI-RU", "NI", "KU")})
        assert ctx.context("KA-PA") == RITUAL                  # a dash is no layout token: no adjacent logogram
        assert ctx.context("DA-ME") is None                     # a single syllabogram is no logogram; tablets unknown
        assert ctx.context("SI-RU") is None                     # NI with no number after is the syllable

    def test_line_breaks_and_dividers_are_skipped(self):
        """A19: layout between a word and the next token is skipped."""
        ctx = sg.Contexts({"X1": _doc("Stone vessel", "KA-PA", "\n", "VIN", "5"),
                           "X2": _doc("Tablet", "DA-ME", "𐄁", "\n", "GRA", "3"),
                           "X3": _doc("Tablet", "SI-RU", "\n", "NI", "2")})
        assert ctx.context("KA-PA") == sg.LOGOGRAM_DOMAINS["VIN"]
        assert ctx.context("DA-ME") == sg.LOGOGRAM_DOMAINS["GRA"]
        assert ctx.context("SI-RU") == sg.LOGOGRAM_DOMAINS["NI"]
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", "\n")}).context("KA-PA") is None     # layout, then the end

    def test_spelling_variants_count_as_their_sign(self):
        """A19: *OLIV as OLIV, VINb and VINc as *131B and *131C, ligatures included."""
        for spelling, sign in [("*OLIV+TU", "OLIV"), ("VINb+WI", "*131B"), ("VINc", "*131C")]:
            ctx = sg.Contexts({"X1": _doc("Tablet", "KA-PA", spelling, "4")})
            assert ctx.context("KA-PA") == sg.LOGOGRAM_DOMAINS[sign], spelling

    def test_a_fused_logogram_is_read_after_its_word(self):
        """A19: X-VIN reads as X VIN; the logogram's domains override the document type."""
        ctx = sg.Contexts({"X1": _doc("Stone vessel", "KA-PA-VIN", "5"), "X2": _doc("Tablet", "DA-ME-VIR+KA"),
                           "X3": _doc("Tablet", "SI-RU-*21F", "1"), "X4": _doc("Tablet", "TU-*OLIV")})
        assert ctx.context("KA-PA") == sg.LOGOGRAM_DOMAINS["VIN"]
        assert ctx.attestations("KA-PA-VIN") == (0, 0)
        assert ctx.context("DA-ME") == sg.LOGOGRAM_DOMAINS["VIR"]
        assert ctx.context("SI-RU") == {"fauna"}
        assert ctx.attestations("TU") == (0, 0)                # a one-sign remainder is no word

    @pytest.mark.parametrize("sign", ["*118", "NI"])
    def test_a_fused_118_or_ni_stays_part_of_the_word(self, sign):
        ctx = sg.Contexts({"X1": _doc("Stone vessel", f"KA-PA-{sign}", "5")})
        assert ctx.context(f"KA-PA-{sign}") == RITUAL and ctx.attestations("KA-PA") == (0, 0)

    @pytest.mark.parametrize("sign", ["*118+KU", "NI+A"])
    def test_a_ligature_of_118_or_ni_needs_a_number_too(self, sign):
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", sign, "KU")}).context("KA-PA") is None
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", sign, "3")}).context("KA-PA") == \
            sg.LOGOGRAM_DOMAINS[sign.split("+")[0]]

    def test_the_logogram_before_a_word_never_counts(self):
        assert sg.Contexts({"X1": _doc("Tablet", "VIN", "KA-PA", "5")}).context("KA-PA") is None
        assert sg.Contexts({"X1": _doc("Tablet", "VIN", "KA-PA")}).context("KA-PA") is None      # last token

    @pytest.mark.parametrize("sign", ["*118", "NI"])
    def test_118_and_ni_need_a_number_after(self, sign):
        with_number = sg.Contexts({"X1": _doc("Tablet", "KA-PA", sign, "¹⁄₂")}).context("KA-PA")
        assert with_number == sg.LOGOGRAM_DOMAINS[sign]
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", sign, "KU")}).context("KA-PA") is None
        assert sg.Contexts({"X1": _doc("Tablet", "KA-PA", sign)}).context("KA-PA") is None    # last token

    def test_attestations_unite_and_unknown_ones_add_nothing(self):
        ctx = sg.Contexts({"X1": _doc("Tablet", "KA-PA", "VIN", "5"), "X2": _doc("Stone vessel", "KA-PA"),
                           "X3": _doc("Nodule", "KA-PA")})
        assert ctx.context("KA-PA") == {"food_drink", "agriculture"} | RITUAL
        assert ctx.attestations("KA-PA") == (3, 2)             # (attestations, with a known context)

    def test_a_word_with_no_known_context_or_no_attestation_has_no_evidence(self):
        ctx = sg.Contexts({"X1": _doc("Nodule", "KA-PA")})
        assert ctx.context("KA-PA") is None and ctx.context("SI-KI-NE") is None
        assert ctx.attestations("SI-KI-NE") == (0, 0)

    def test_spellings_compare_canonically(self):
        ctx = sg.Contexts({"X1": _doc("Stone vessel", "ka-ra₂-pa")})
        assert ctx.context("KA-RA2-PA") == RITUAL == ctx.context("KA-RA₂-PA")


class TestClusters:
    def test_meaning_and_joined_glosses_unite(self):
        doms = sg.cluster_domains({"7": "'wine; vineyard'", "8": "'to remember'"}, {"8": ["temple offering"]})
        assert doms["7"] >= {"food_drink"} and doms["8"] == set(sg.tagger().classify("temple offering"))
        assert doms["8"]

    def test_a_cluster_with_no_tagged_word_never_fits(self):
        doms = sg.cluster_domains({"9": "'to remember'"}, {})
        assert doms["9"] == frozenset() and not sg.fits(doms["9"], {"food_drink"})

    def test_fit_is_a_shared_domain(self):
        assert sg.fits(frozenset({"fauna", "body"}), frozenset({"fauna"}))
        assert not sg.fits(frozenset({"fauna"}), frozenset({"flora"}))


class TestFrozenTagger:
    def test_the_tagger_is_the_one_a18_froze(self):
        assert sg.tagger().classify("grain and wine") == ["agriculture", "food_drink"]

    def test_a_changed_tagger_is_refused(self, tmp_path, monkeypatch):
        copy = tmp_path / "tag_semantic_fields.py"
        copy.write_bytes(sg.TAGGER.read_bytes() + b"\n# edited\n")
        monkeypatch.setattr(sg, "TAGGER", copy)
        sg.tagger.cache_clear()
        try:
            with pytest.raises(sg.TaggerChanged, match="A18"):
                sg.tagger()
        finally:
            sg.tagger.cache_clear()
