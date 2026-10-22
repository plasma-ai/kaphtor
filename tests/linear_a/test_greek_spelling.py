"""Tests for lib/greek_spelling.py — greek_to_lb and lb_token_to_key.

Regression coverage for the --greek route normalizer bug: attested LB
tokens were rendered through the Linear A sign table, which silently
dropped syllables it did not know (ai, nwa, dwo, jo, wo, qo...) and
mis-valued doublets, so lb_key matching missed or mis-scored forms.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.greek_spelling import greek_to_lb, lb_token_to_key


class TestGreekToLB:
    def test_known_forms(self):
        cases = {
            "khrusos": "kuruso",
            "khalkos": "kako",
            "tripos": "tiripo",
            "elephas": "erepa",
            "sperma": "pema",
            "wanax": "wanaka",
        }
        for src, want in cases.items():
            assert greek_to_lb(src) == want, src

    def test_hyphenated_output(self):
        assert greek_to_lb("khrusos", hyphens=True) == "ku-ru-so"


class TestLBTokenToKey:
    def test_plain_token(self):
        assert lb_token_to_key("ku-ru-so") == "kuruso"

    def test_shared_space_with_greek_to_lb(self):
        # Both sides of a comparison must land in one phoneme space.
        assert lb_token_to_key("ku-ru-so") == greek_to_lb("khrusos")
        assert lb_token_to_key("ka-ko") == greek_to_lb("khalkos")
        assert lb_token_to_key("ti-ri-po") == greek_to_lb("tripos")

    def test_pa2_not_dropped(self):
        # Regression: doublet subscripts were dropped by the LA table path.
        assert lb_token_to_key("ku-ru-su-pa2") == "kurusupa"

    def test_subscript_unicode(self):
        assert lb_token_to_key("ku-ru-su-pa₂") == "kurusupa"

    def test_a2_renders_h_unwritten(self):
        assert lb_token_to_key("a2-te-ro") == "atero"

    def test_a3_glide_drop_matches_greek_side(self):
        # a3 = ai; the same glide-drop rule as greek_to_lb applies, so
        # a3-ka-sa-ma and the folded Greek both surface without the glide.
        assert lb_token_to_key("a3-ka-sa-ma") == "akasama"

    def test_e_ra3_wo_matches_elaiwon(self):
        assert lb_token_to_key("e-ra3-wo") == greek_to_lb("elaiwon")

    def test_lb_only_plain_signs(self):
        # jo/wo/qo/zo/qi are absent from the Linear A table and were
        # silently dropped (nwa-ni-jo collapsed to "ni", dwo-jo to "").
        assert lb_token_to_key("dwo-jo") == "dwoio"
        assert lb_token_to_key("nwa-ni-jo") == "nwaniio"
        assert lb_token_to_key("qo-u-ko-ro") == "qoukoro"
        assert lb_token_to_key("wo-ka") == "woka"

    def test_complex_signs(self):
        assert lb_token_to_key("pte-re-wa") == "pterewa"
        assert lb_token_to_key("pu2-te-re") == "putere"
        assert lb_token_to_key("o-pe-ro2") == "operio"

    def test_untransliterated_sign_refuses(self):
        # Open signs must refuse the whole token, never a partial render.
        assert lb_token_to_key("*34-ke-u") is None
        assert lb_token_to_key("*56-ra-ku-ja") is None
        assert lb_token_to_key("ma-*79") is None

    def test_lacuna_refuses(self):
        assert lb_token_to_key("ko-•-ro") is None

    def test_edge_damage_brackets_stripped(self):
        # Edge-broken tokens render on their visible signs; whether a
        # broken token should be scored at all is the caller's gate.
        assert lb_token_to_key("]ra-wo") == "rawo"
        assert lb_token_to_key("ke[") == "ke"

    def test_empty_and_garbage(self):
        assert lb_token_to_key("") is None
        assert lb_token_to_key("VIR") is None
        assert lb_token_to_key("]") is None
