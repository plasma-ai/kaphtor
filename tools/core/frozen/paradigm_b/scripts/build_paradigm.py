#!/usr/bin/env python3
"""Build data/paradigm/<arm>.json: the morphological inventories of option B
(PROTOCOL-B §4) and the attested inflected forms used by selftest_b.py.

Every morpheme is hand-encoded from a grammar of its language and cites it.
The blindness rule (§4.1) is enforced mechanically: an entry whose id,
function, citation or note mentions a Linear A form, a lexicon.json headword,
"Linear A", "Minoan" or "Ya Diktu" aborts the build. Parity (§4.2): every
rival arm's morpheme count and one-sign count must lie within 1.5× of the
headline `cs` inventory or the build exits 3.

Phonemic notation: one Latin string per morpheme, tokenized by
vendor/phonetics._tokenize_phonemes and grouped into (C, V) segments by
render_la.tokens_to_segments; a consonant not followed by a vowel is a bare
coda ("at" = (None,a),(t,None); "kum" = (k,u),(m,None)). Vowel length is not
written (the syllabary does not mark it).

Run: IOZA2_PREFREEZE=1 uv run python scripts/build_paradigm.py
Attribution: di Mino.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import paths  # noqa: E402
import render_la  # noqa: E402

OUT_DIR = paths.DATA / "paradigm"
ATTRIBUTION = "di Mino"
PARITY = 1.5                 # distinct realizations (PROTOCOL-B §4.2)
PARITY_ONE_SIGN_CAP = 2.0    # one-sign realizations: reported, hard cap only

INNOV_T_OBJ = "archaic_t_object_suffix"
INNOV_ENERGIC_POST = "energic_after_object"

# languages by branch (PROTOCOL-B §2)
NWS = {"ugaritic", "hebrew", "phoenician", "amarna", "amorite", "aramaic"}
ARABIC = {"arabic", "safaitic", "hismaic", "dadanitic"}
ASA = {"sabaic", "qatabanic", "minaic"}


def M(id, position, phon, function, attested, cite, *, cost=0.0, innovation=None, note=None, vowels="attested"):
    """One morpheme row. ``position`` is the 1-based order class on its side."""
    return dict(id=id, position=position, phon=phon, function=function,
                attested_in=sorted(set(attested)), citations=cite if isinstance(cite, list) else [cite],
                cost=cost, innovation_id=innovation, note=note, vowel_status=vowels)


# ===========================================================================
# CENTRAL SEMITIC (headline arm `cs`; `nws_floor` = the NWS-attested subset)
# ===========================================================================

CS_PREFIX_CLASSES = ["proclitic particle", "person prefix", "stem prefix"]
CS_SUFFIX_CLASSES = ["gender/derivation", "case/number/verbal ending", "state (mimation/nunation)",
                     "energic", "pronominal", "enclitic", "energic after pronominal (priced)"]

UG = "ugaritic"
HB = "hebrew"
AR = "arabic"
SF = "safaitic"
AM = "amorite"
SB = "sabaic"
PH = "phoenician"
AA = "amarna"
AC = "aramaic"

CS_PREFIXES = [
    # class 1 — proclitic particles
    M("cs_p_wa", 1, "wa", "conjunction 'and'", [UG, HB, AR, SF, SB],
      ["Tropper 2000 §83.11", "Huehnergard 2012 §…conjunctions", "Al-Jallad 2019 (wa-)", "Beeston 1984 (w-)"]),
    M("cs_p_u", 1, "u", "conjunction 'and', allomorph û- before labials and shewa", [HB],
      ["Joüon–Muraoka 2006 §104c"]),
    M("cs_p_pa", 1, "pa", "conjunction 'and then, so' (Ug. p, Ar. fa-, Saf. f)", [UG, AR, SF, SB],
      ["Tropper 2000 §83.12", "Huehnergard 2019: 67 (*pa)", "Al-Jallad 2015 (f)", "Beeston 1984 (f-)"]),
    M("cs_p_la", 1, "la", "asseverative / precative la=; negative lā; preposition la-", [UG, HB, AR, AM],
      ["Tropper 2000 §85.2", "Huehnergard 1983", "Huffmon 1965: 78–80 (la-yaqtul)", "Al-Jallad 2019 (la-)"]),
    M("cs_p_li", 1, "li", "preposition 'to, for'", [UG, HB, AR, SF, SB],
      ["Tropper 2000 §82.11", "Al-Jallad 2015 (l)", "Beeston 1984 (l-)"]),
    M("cs_p_bi", 1, "bi", "preposition 'in, with'", [UG, HB, AR, SF, SB],
      ["Tropper 2000 §82.12", "Al-Jallad 2015 (b-)", "Beeston 1984 (b-)"]),
    M("cs_p_ka", 1, "ka", "preposition 'like'", [UG, HB, AR, AM],
      ["Tropper 2000 §82.13", "Huffmon 1965: 102 (ka/ki)"]),
    M("cs_p_ki", 1, "ki", "subordinator / emphatic kī 'that, indeed'", [UG, HB],
      ["Tropper 2000 §83.24", "Joüon–Muraoka 2006 §157"]),
    M("cs_p_ya", 1, "ya", "vocative particle yā 'O'", [UG, AR],
      ["Tropper 2000 §84.2", "Al-Jallad 2019 (yā)"]),
    M("cs_p_ha", 1, "ha", "article ha- (Heb.), h- (Safaitic); Safaitic vocative h", [HB, SF],
      ["Joüon–Muraoka 2006 §35", "Al-Jallad 2015 (h- article; h vocative)"]),
    M("cs_p_al", 1, "ʾal", "prohibitive ʾal + jussive", [UG, HB],
      ["Tropper 2000 §87.3", "Huehnergard 2019: 68"]),
    M("cs_p_hal", 1, "hal", "presentative hal/han 'behold'; Ar. hal (interrogative)", [UG, HB, AR],
      ["Tropper 2000 §81.4 (hl)", "Huehnergard 2019: 68 (*han/*hal)"]),
    # class 2 — person prefixes of the prefix conjugation
    M("cs_pp_a", 2, "ʾa", "1cs person prefix", [UG, HB, AR, SF, SB, AM],
      ["Tropper 2000 §73.222", "Huehnergard 2019: 62–63", "Huffmon 1965: 66"]),
    M("cs_pp_ta", 2, "ta", "2ms / 3fs person prefix", [UG, HB, AR, SF, SB, AM],
      ["Tropper 2000 §73.222", "Huehnergard 2019: 62–63", "Huffmon 1965: 85"]),
    M("cs_pp_ya", 2, "ya", "3ms person prefix", [UG, HB, AR, SF, SB, AM],
      ["Tropper 2000 §73.222", "Huehnergard 2019: 62–63", "Huffmon 1965: 63–65"]),
    M("cs_pp_na", 2, "na", "1cp person prefix", [UG, HB, AR, SF, SB],
      ["Tropper 2000 §73.222", "Huehnergard 2019: 62–63"]),
    M("cs_pp_i", 2, "ʾi", "1cs prefix, i-grade (Barth–Ginsberg, a-theme verbs)", [UG, HB, AM],
      ["Tropper 2000 §73.242", "Lipiński 1997 §40.21", "Huffmon 1965: 63"]),
    M("cs_pp_ti", 2, "ti", "2ms / 3fs prefix, i-grade", [UG, HB, AM],
      ["Tropper 2000 §73.242", "Lipiński 1997 §40.21"]),
    M("cs_pp_yi", 2, "yi", "3ms prefix, i-grade", [UG, HB, AM],
      ["Tropper 2000 §73.242", "Lipiński 1997 §40.21", "Huffmon 1965: 63 (Emar/Amorite yi-)"]),
    M("cs_pp_ni", 2, "ni", "1cp prefix, i-grade", [UG, HB],
      ["Tropper 2000 §73.242"]),
    M("cs_pp_u", 2, "ʾu", "1cs prefix, u-grade (D, Š, internal passive)", [UG, AR, AM],
      ["Tropper 2000 §74.412", "Huehnergard 2019: 64–65", "Huffmon 1965: 75 (yuqtal)"]),
    M("cs_pp_tu", 2, "tu", "2ms / 3fs prefix, u-grade", [UG, AR],
      ["Tropper 2000 §74.412", "Huehnergard 2019: 64–65"]),
    M("cs_pp_yu", 2, "yu", "3ms prefix, u-grade", [UG, AR, AM],
      ["Tropper 2000 §74.412", "Huehnergard 2019: 64–65", "Huffmon 1965: 75"]),
    M("cs_pp_nu", 2, "nu", "1cp prefix, u-grade", [UG, AR],
      ["Tropper 2000 §74.412"]),
    # class 3 — stem prefixes
    M("cs_s_n", 3, "n", "N-stem prefix in the prefix conjugation (unassimilated in Ar. yanfaʿilu; assimilated in Ug./Heb.)",
      [AR, UG, HB], ["Al-Jallad 2019 (stem VII)", "Tropper 2000 §74.32", "Huehnergard 2019: 64"]),
    M("cs_s_na", 3, "na", "N-stem prefix, suffix conjugation and participle (naqtala)", [UG],
      ["Tropper 2000 §74.32"]),
    M("cs_s_ni", 3, "ni", "N-stem prefix, suffix conjugation (Heb. niqṭal)", [HB],
      ["Joüon–Muraoka 2006 §51"]),
    M("cs_s_in", 3, "ʾin", "N-stem with prosthetic vowel, suffix conjugation (Ar. ʾinfaʿala)", [AR],
      ["Al-Jallad 2019 (stem VII)"]),
    M("cs_s_ta", 3, "ta", "prefixed t-stem (Ug. tD, Ar. V/VI, Sab. t-); also nominal ta- (taqtīl)", [UG, AR, SB],
      ["Tropper 2000 §74.43", "Al-Jallad 2019 (stems V–VI)", "Beeston 1984 (t-stems)"]),
    M("cs_s_hit", 3, "hit", "Heb. hitpaʿel prefix", [HB], ["Joüon–Muraoka 2006 §53"]),
    M("cs_s_i", 3, "ʾi", "prosthetic vowel of t-stems and N-stems (Ug. Gt ʾiqtatil; Ar. VII–X)", [UG, AR],
      ["Tropper 2000 §74.23", "Al-Jallad 2019 (stems VII–X)"]),
    M("cs_s_sha", 3, "ša", "Š causative prefix", [UG, AA],
      ["Tropper 2000 §74.62", "Rainey 1996 II (Š-stem)"]),
    M("cs_s_ha", 3, "ha", "h-causative prefix (Heb. hifʿil, Aram. hafʿel, Sab. h-)", [HB, AC, SB],
      ["Joüon–Muraoka 2006 §54", "Beeston 1984 (h-causative)"]),
    M("cs_s_a", 3, "ʾa", "ʾ-causative prefix (Ar. IV ʾafʿala, Aram. ʾafʿel)", [AR, AC],
      ["Al-Jallad 2019 (stem IV)"]),
    M("cs_s_shta", 3, "šta", "Št causative-reflexive prefix", [UG], ["Tropper 2000 §74.64"]),
    M("cs_s_ista", 3, "ʾista", "Ar. X ʾistafʿala prefix", [AR], ["Al-Jallad 2019 (stem X)"]),
    M("cs_s_ma", 3, "ma", "nominal prefix ma- (maqtal-)", [UG, HB, AR, SB, AM],
      ["Tropper 2000 §51.45", "Huffmon 1965: 98 (ma-prefix nouns)"]),
    M("cs_s_mi", 3, "mi", "nominal prefix mi- (miqtal-)", [UG, HB, AR], ["Tropper 2000 §51.45"]),
    M("cs_s_mu", 3, "mu", "participle prefix mu- of the derived stems", [UG, AR, SB],
      ["Tropper 2000 §74.4 (muqattilu)", "Al-Jallad 2019 (participles)"]),
    # Sabaic-only
    M("cs_s_sa", 3, "sa", "s¹-causative prefix (Qatabanic, Minaic; Sabaic h-)", ["qatabanic", "minaic"],
      ["Beeston 1984 (causative s¹-)"], note="sabaic_only"),
]

CS_SUFFIXES = [
    # class 1 — gender / derivation
    M("cs_g_at", 1, "at", "feminine -at-", [UG, HB, AR, SF, SB, AM],
      ["Tropper 2000 §54.111", "Huehnergard 2019: 60–61", "Al-Jallad 2015 (-t)"]),
    M("cs_g_t", 1, "t", "feminine -t (bound state; 3fs suffix conjugation after vowel)", [UG, HB, AR, SF, SB],
      ["Tropper 2000 §52.5", "Al-Jallad 2015 (-t)"]),
    M("cs_g_ut", 1, "ut", "abstract -ūt", [HB, AC, AR],
      ["Joüon–Muraoka 2006 §88Mj", "Al-Jallad 2019 (-ūt)"]),
    M("cs_g_an", 1, "an", "-ān augmentative / hypocoristic / adjectival", [UG, HB, AR, AM],
      ["Tropper 2000 §51.46", "Huffmon 1965: 135 (-ān)"]),
    M("cs_g_iy", 1, "iy", "nisbe -iyy-", [UG, HB, AR, SF],
      ["Tropper 2000 §51.43", "Al-Jallad 2019 (nisba)"]),
    # class 2 — case / number / verbal endings
    M("cs_c_u", 2, "u", "nominative -u; indicative -u; 3mp -ū; nom. pl. -ū; locative -u", [UG, AR, AM],
      ["Tropper 2000 §54.1, §73.2", "Huehnergard 2019: 60", "Huffmon 1965: 105"]),
    M("cs_c_i", 2, "i", "genitive -i; 2fs -ī; oblique pl. -ī; 1cs possessive -ī", [UG, AR, AM],
      ["Tropper 2000 §54.1", "Huehnergard 2019: 60", "Huffmon 1965: 106"]),
    M("cs_c_a", 2, "a", "accusative -a; volitive -a; 3ms suffix conjugation -a; dual nom. -ā; 3fp -ā", [UG, AR, AM],
      ["Tropper 2000 §54.1, §73.2", "Huehnergard 2019: 60, 63"]),
    M("cs_c_e", 2, "e", "dual oblique -ē", [UG], ["Tropper 2000 §53.22"]),
    M("cs_c_ay", 2, "ay", "dual oblique -ay(na) (PS *-ay-na, Ar. -ayni)", [AR, HB],
      ["Huehnergard 2019: 60–61", "Al-Jallad 2019 (dual)"]),
    M("cs_c_una", 2, "una", "masc. pl. nom. -ūna; 3mp/2mp indicative -ūna", [UG, AR],
      ["Tropper 2000 §53.31, §73.222", "Al-Jallad 2019 (-ūna)"]),
    M("cs_c_ina", 2, "ina", "masc. pl. oblique -īna; 2fs indicative -īna", [UG, AR],
      ["Tropper 2000 §53.31, §73.222"]),
    M("cs_c_ana", 2, "ana", "dual indicative -āna", [UG], ["Tropper 2000 §73.223"]),
    M("cs_c_ani", 2, "ani", "dual nominative -āni", [AR], ["Al-Jallad 2019 (dual)"]),
    M("cs_c_ayna", 2, "ayna", "dual oblique -ayna", [AR], ["Al-Jallad 2019 (dual)"]),
    M("cs_c_na", 2, "na", "fem. pl. -na; 1cp suffix conjugation -nā", [UG, AR, HB],
      ["Tropper 2000 §73.223, §73.3", "Al-Jallad 2019 (suffix conjugation)"]),
    M("cs_c_ta", 2, "ta", "2ms suffix conjugation -ta", [UG, AR, AM, HB],
      ["Tropper 2000 §73.3", "Huffmon 1965: 91"]),
    M("cs_c_ti", 2, "ti", "2fs suffix conjugation -ti; 1cs -ti (Amorite)", [UG, AR, AM],
      ["Tropper 2000 §73.3", "Huffmon 1965: 91"]),
    M("cs_c_tu", 2, "tu", "1cs suffix conjugation -tu", [UG, AR],
      ["Tropper 2000 §73.3 (-tū?)", "Al-Jallad 2019 (-tu)"]),
    M("cs_c_tumu", 2, "tumu", "2mp suffix conjugation -tumū", [UG], ["Tropper 2000 §73.3"]),
    M("cs_c_tum", 2, "tum", "2mp suffix conjugation -tum", [AR, HB], ["Al-Jallad 2019 (suffix conjugation)"]),
    M("cs_c_aha", 2, "aha", "directive -ah(a)", [UG, HB], ["Tropper 2000 §54.3", "Joüon–Muraoka 2006 §93c"]),
    M("cs_c_w", 2, "w", "3mp suffix conjugation -w", [SB], ["Beeston 1984 (suffix conjugation)"], note="sabaic_only"),
    # class 3 — state
    M("cs_st_m", 3, "m", "mimation -m after a short case vowel", [UG, AM, SB],
      ["Tropper 2000 §53.31", "Huehnergard 2019: 59–61", "Huffmon 1965: 95"]),
    M("cs_st_n", 3, "n", "nunation -n after a short case vowel; Sab. postposed definite -n", [AR, SB],
      ["Al-Jallad 2019 (tanwīn)", "Beeston 1984 (-n)"]),
    M("cs_st_ma", 3, "ma", "nonbound -ma after long vowels (dual, masc. pl.)", [UG], ["Tropper 2000 §53.31, §54.121"]),
    M("cs_st_mi", 3, "mi", "nonbound -mi after long vowels (dual)", [UG], ["Tropper 2000 §53.22"]),
    # class 4 — energic
    M("cs_e_n", 4, "n", "energic -n after a vowel (yaqtulu-n)", [UG, AR],
      ["Tropper 2000 §73.6", "Al-Jallad 2019 (energic)"]),
    M("cs_e_an", 4, "an", "energic -an", [UG, AR, AA],
      ["Tropper 2000 §73.6", "Rainey 1996 II: 234–44", "Al-Jallad 2019 (energic)"]),
    M("cs_e_anna", 4, "anna", "energic -anna", [UG, AR],
      ["Tropper 2000 §73.6", "Al-Jallad 2019 (energic)"]),
    # class 5 — pronominal suffixes
    M("cs_pr_i", 5, "i", "1cs possessive -ī", [UG, HB, AR], ["Tropper 2000 §41.2"]),
    M("cs_pr_ya", 5, "ya", "1cs -ya (after vowels)", [UG, AR], ["Tropper 2000 §41.2", "Al-Jallad 2019 (-ya)"]),
    M("cs_pr_ni", 5, "ni", "1cs object -nī", [UG, HB, AR], ["Tropper 2000 §41.2"]),
    M("cs_pr_ka", 5, "ka", "2ms -ka", [UG, HB, AR, SF], ["Tropper 2000 §41.2", "Al-Jallad 2015 (-k)"]),
    M("cs_pr_ki", 5, "ki", "2fs -ki", [UG, HB, AR], ["Tropper 2000 §41.2"]),
    M("cs_pr_hu", 5, "hu", "3ms -hū", [UG, AR, SF, SB], ["Tropper 2000 §41.2", "Al-Jallad 2015 (-h)", "Beeston 1984 (-hw)"]),
    M("cs_pr_ha", 5, "ha", "3fs -hā", [UG, AR, SF], ["Tropper 2000 §41.2"]),
    M("cs_pr_na", 5, "na", "1cp -nā", [UG, HB, AR], ["Tropper 2000 §41.2"]),
    M("cs_pr_kumu", 5, "kumu", "2mp -kumū", [UG], ["Tropper 2000 §41.2"]),
    M("cs_pr_kum", 5, "kum", "2mp -kum", [AR, HB, SF], ["Al-Jallad 2019 (pronominal suffixes)"]),
    M("cs_pr_humu", 5, "humu", "3mp -humū", [UG, SB], ["Tropper 2000 §41.2", "Beeston 1984 (-hmw)"]),
    M("cs_pr_hum", 5, "hum", "3mp -hum", [AR, SF], ["Al-Jallad 2019 (pronominal suffixes)", "Al-Jallad 2015 (-hm)"]),
    M("cs_pr_s", 5, "s", "3ms -s¹ (Sabaic)", [SB], ["Beeston 1984 (-s¹)"], note="sabaic_only"),
    M("cs_pr_ti_arch", 5, "ti", "archaic *-t- object suffix (2nd person), unattested in Central Semitic", [],
      ["Lipiński 1997 §36"], cost=0.40, innovation=INNOV_T_OBJ),
    M("cs_pr_ta_arch", 5, "ta", "archaic *-t- object suffix (2nd person), unattested in Central Semitic", [],
      ["Lipiński 1997 §36"], cost=0.40, innovation=INNOV_T_OBJ),
    # class 6 — enclitic particles
    M("cs_en_ma", 6, "ma", "enclitic -ma (focus)", [UG, AR], ["Tropper 2000 §89.2", "Huehnergard 2019: 68 (*=ma)"]),
    M("cs_en_mi", 6, "mi", "enclitic -mi", [UG, AM], ["Tropper 2000 §89.2", "Huffmon 1965: 102 (-mi)"]),
    M("cs_en_m", 6, "m", "enclitic -m", [UG], ["Tropper 2000 §89.2"]),
    M("cs_en_na", 6, "na", "enclitic -na (topicalizing)", [UG], ["Tropper 2000 §89.3"]),
    M("cs_en_n", 6, "n", "enclitic -n", [UG], ["Tropper 2000 §89.3"]),
    # class 7 (ext only) — energic after the pronominal suffix
    M("cs_ep_n", 7, "n", "energic -n placed after the object suffix (reverses the attested order)", [],
      ["Huehnergard 2012 §IV.D.4", "Rainey 1996 II: 234–44"], cost=0.40, innovation=INNOV_ENERGIC_POST),
    M("cs_ep_an", 7, "an", "energic -an after the object suffix", [],
      ["Huehnergard 2012 §IV.D.4"], cost=0.40, innovation=INNOV_ENERGIC_POST),
    M("cs_ep_anna", 7, "anna", "energic -anna after the object suffix", [],
      ["Huehnergard 2012 §IV.D.4"], cost=0.40, innovation=INNOV_ENERGIC_POST),
]

# attested inflected forms: (id, language, prefixes, stem, suffixes, surface, citation)
CS_FORMS = [
    ("ug_yamluku", UG, ["cs_pp_ya"], "mluk", ["cs_c_u"], "yamluku", "Tropper 2000 §73.222"),
    ("ug_tamluku", UG, ["cs_pp_ta"], "mluk", ["cs_c_u"], "tamluku", "Tropper 2000 §73.222"),
    ("ug_amluku", UG, ["cs_pp_a"], "mluk", ["cs_c_u"], "ʾamluku", "Tropper 2000 §73.222"),
    ("ug_namluku", UG, ["cs_pp_na"], "mluk", ["cs_c_u"], "namluku", "Tropper 2000 §73.222"),
    ("ug_yamlukuna", UG, ["cs_pp_ya"], "mluk", ["cs_c_una"], "yamlukūna", "Tropper 2000 §73.222"),
    ("ug_tamlukina", UG, ["cs_pp_ta"], "mluk", ["cs_c_ina"], "tamlukīna", "Tropper 2000 §73.222"),
    ("ug_yamlukan", UG, ["cs_pp_ya"], "mluk", ["cs_e_an"], "yamlukan", "Tropper 2000 §73.6"),
    ("ug_yamlukanna", UG, ["cs_pp_ya"], "mluk", ["cs_e_anna"], "yamlukanna", "Tropper 2000 §73.6"),
    ("ug_yamlukun", UG, ["cs_pp_ya"], "mluk", ["cs_c_u", "cs_e_n"], "yamlukun", "Tropper 2000 §73.6"),
    ("ug_malaka", UG, [], "malak", ["cs_c_a"], "malaka", "Tropper 2000 §73.3"),
    ("ug_malakat", UG, [], "malak", ["cs_g_at"], "malakat", "Tropper 2000 §73.3"),
    ("ug_malakta", UG, [], "malak", ["cs_c_ta"], "malaktā", "Tropper 2000 §73.3"),
    ("ug_malakti", UG, [], "malak", ["cs_c_ti"], "malaktī", "Tropper 2000 §73.3"),
    ("ug_malakna", UG, [], "malak", ["cs_c_na"], "malaknā", "Tropper 2000 §73.3"),
    ("ug_malaktumu", UG, [], "malak", ["cs_c_tumu"], "malaktumū", "Tropper 2000 §73.3"),
    ("ug_malku", UG, [], "malk", ["cs_c_u"], "malku", "Tropper 2000 §54.1"),
    ("ug_malki", UG, [], "malk", ["cs_c_i"], "malki", "Tropper 2000 §54.1"),
    ("ug_malka", UG, [], "malk", ["cs_c_a"], "malka", "Tropper 2000 §54.1"),
    ("ug_malkatu", UG, [], "malk", ["cs_g_at", "cs_c_u"], "malkatu", "Tropper 2000 §54.111"),
    ("ug_malkuma", UG, [], "malk", ["cs_c_u", "cs_st_ma"], "malkūma", "Tropper 2000 §53.31"),
    ("ug_malkima", UG, [], "malk", ["cs_c_i", "cs_st_ma"], "malkīma", "Tropper 2000 §53.31"),
    ("ug_malkami", UG, [], "malk", ["cs_c_a", "cs_st_mi"], "malkāmi", "Tropper 2000 §53.22"),
    ("ug_malkemi", UG, [], "malk", ["cs_c_e", "cs_st_mi"], "malkēmi", "Tropper 2000 §53.22"),
    ("ug_malkuka", UG, [], "malk", ["cs_c_u", "cs_pr_ka"], "malkuka", "Tropper 2000 §41.2"),
    ("ug_malkuhu", UG, [], "malk", ["cs_c_u", "cs_pr_hu"], "malkuhū", "Tropper 2000 §41.2"),
    ("ug_malkiya", UG, [], "malk", ["cs_c_i", "cs_pr_ya"], "malkiya", "Tropper 2000 §41.2"),
    ("ug_malkuhumu", UG, [], "malk", ["cs_c_u", "cs_pr_humu"], "malkuhumū", "Tropper 2000 §41.2"),
    ("ug_yamlukuni", UG, ["cs_pp_ya"], "mluk", ["cs_c_u", "cs_pr_ni"], "yamlukunī", "Tropper 2000 §41.2"),
    ("ug_yasalhimu", UG, ["cs_pp_ya", "cs_s_sha"], "lḥim", ["cs_c_u"], "yašalḥimu", "Tropper 2000 §74.62"),
    ("ug_tistahwiyu", UG, ["cs_pp_ti", "cs_s_shta"], "ḥwiy", ["cs_c_u"], "tištaḥwiyu", "Tropper 2000 §74.64"),
    ("ug_naqtala", UG, ["cs_s_na"], "qtal", ["cs_c_a"], "naqtala", "Tropper 2000 §74.32"),
    ("ug_taqattala", UG, ["cs_s_ta"], "qattal", ["cs_c_a"], "taqattala", "Tropper 2000 §74.43"),
    ("ug_muqattilu", UG, ["cs_s_mu"], "qattil", ["cs_c_u"], "muqattilu", "Tropper 2000 §74.4"),
    ("ug_maqtalu", UG, ["cs_s_ma"], "qtal", ["cs_c_u"], "maqtalu", "Tropper 2000 §51.45"),
    ("ug_wamalku", UG, ["cs_p_wa"], "malk", ["cs_c_u"], "wamalku", "Tropper 2000 §83.11"),
    ("ug_layamluk", UG, ["cs_p_la", "cs_pp_ya"], "mluk", [], "layamluk", "Tropper 2000 §85.2"),
    ("ug_limalki", UG, ["cs_p_li"], "malk", ["cs_c_i"], "limalki", "Tropper 2000 §82.11"),
    ("ug_bimalki", UG, ["cs_p_bi"], "malk", ["cs_c_i"], "bimalki", "Tropper 2000 §82.12"),
    ("ug_yabaslu", UG, ["cs_p_ya"], "baʿl", ["cs_c_u"], "yabaʿlu", "Tropper 2000 §84.2 (y bʿl)"),
    ("ug_alyamluk", UG, ["cs_p_al", "cs_pp_ya"], "mluk", [], "ʾalyamluk", "Tropper 2000 §87.3"),
    ("ug_ugaritiyyu", UG, [], "ʾugarit", ["cs_g_iy", "cs_c_u"], "ʾugaritiyu", "Tropper 2000 §51.43"),
    ("ug_salmanu", UG, [], "šalm", ["cs_g_an", "cs_c_u"], "šalmānu", "Tropper 2000 §51.46"),
    ("hb_malkut", HB, [], "malk", ["cs_g_ut"], "malkūt", "Joüon–Muraoka 2006 §88Mj"),
    ("ug_malkukumu", UG, [], "malk", ["cs_c_u", "cs_pr_kumu"], "malkukumū", "Tropper 2000 §41.2"),
    ("ug_binama", UG, [], "bin", ["cs_c_a", "cs_en_ma"], "binama", "Tropper 2000 §89.2"),
    ("ar_kataba", AR, [], "katab", ["cs_c_a"], "kataba", "Al-Jallad 2019 (suffix conjugation)"),
    ("ar_yaktubu", AR, ["cs_pp_ya"], "ktub", ["cs_c_u"], "yaktubu", "Al-Jallad 2019 (prefix conjugation)"),
    ("ar_katabtu", AR, [], "katab", ["cs_c_tu"], "katabtu", "Al-Jallad 2019 (suffix conjugation)"),
    ("ar_kitabun", AR, [], "kitab", ["cs_c_u", "cs_st_n"], "kitābun", "Al-Jallad 2019 (tanwīn)"),
    ("ar_istaqbala", AR, ["cs_s_ista"], "qbal", ["cs_c_a"], "ʾistaqbala", "Al-Jallad 2019 (stem X)"),
    ("ar_infatala", AR, ["cs_s_in"], "fatal", ["cs_c_a"], "ʾinfatala", "Al-Jallad 2019 (stem VII)"),
    ("ar_yanfatilu", AR, ["cs_pp_ya", "cs_s_n"], "fatil", ["cs_c_u"], "yanfatilu", "Al-Jallad 2019 (stem VII)"),
    ("ar_yukattibu", AR, ["cs_pp_yu"], "kattib", ["cs_c_u"], "yukattibu", "Al-Jallad 2019 (stem II)"),
    ("ar_katabtum", AR, [], "katab", ["cs_c_tum"], "katabtum", "Al-Jallad 2019 (suffix conjugation)"),
    ("ar_kitabuhum", AR, [], "kitab", ["cs_c_u", "cs_pr_hum"], "kitābuhum", "Al-Jallad 2019 (pronominal suffixes)"),
    ("ar_malikayni", AR, [], "malik", ["cs_c_ayna"], "malikayna", "Al-Jallad 2019 (dual)"),
    ("sf_yawir", SF, ["cs_pp_ya"], "ʿwir", [], "yaʿwir", "OCIANA AAEK 253 (yʿwr); Al-Jallad 2015 (prefix conjugation)"),
    ("sf_wagama", SF, [], "wagam", ["cs_c_a"], "wagama", "OCIANA AAEK 130 (wgm); Al-Jallad 2015 (suffix conjugation)"),
    ("sf_gayrat", SF, [], "ġayr", ["cs_g_at"], "ġayrat", "OCIANA AAEK 141 (ġyrt); Al-Jallad 2015 (feminine -t)"),
    ("sf_halat", SF, ["cs_p_ha"], "lat", [], "halat", "OCIANA AAEK 51 (h lt); Al-Jallad 2015 (vocative h)"),
    ("sf_ahuhu", SF, [], "ʾaḫ", ["cs_c_u", "cs_pr_hu"], "ʾaḫuhu", "OCIANA AAEK 139 (ʾḫ -h); Al-Jallad 2015 (-h)"),
    # Sabaic (with-Sabaic variant only)
    ("sb_yfln", SB, ["cs_pp_ya"], "fʿal", ["cs_e_n"], "yafʿaln", "Beeston 1984 (yfʿln); sabaic_dictionary.jsonl"),
    ("sb_hfl", SB, ["cs_s_ha"], "fʿal", [], "hafʿal", "Beeston 1984 (h-causative)"),
    ("sb_sfl", SB, ["cs_s_sa"], "fʿal", [], "safʿal", "Beeston 1984 (s¹-causative, Qatabanic/Minaic)"),
    ("sb_flw", SB, [], "faʿal", ["cs_c_w"], "faʿalw", "Beeston 1984 (3mp -w)"),
    ("sb_bytn", SB, [], "bayt", ["cs_st_n"], "baytn", "Beeston 1984 (postposed -n)"),
    ("sb_byths", SB, [], "bayt", ["cs_pr_s"], "bayts", "Beeston 1984 (-s¹)"),
]

# ===========================================================================
# LUWIAN
# ===========================================================================

LU = "luwian"
LUW_PREFIX_CLASSES = ["sentence-initial connector + clitic chain"]
LUW_SUFFIX_CLASSES = ["derivational", "case/number", "verbal ending", "Wackernagel clitic"]

LUW_PREFIXES = [
    M("luw_p_a", 1, "a", "sentence-initial connector a-", [LU], ["Payne 2014 §… particles", "Melchert 2003"]),
    M("luw_p_awa", 1, "awa", "connector a- + quotative =wa", [LU], ["Payne 2014 (a-wa/i)"]),
    M("luw_p_pa", 1, "pa", "contrastive connector pa-", [LU], ["Payne 2014 (pa-)"]),
    M("luw_p_wa", 1, "wa", "quotative particle wa- on the first word", [LU], ["Payne 2014 (=wa)"]),
]

LUW_SUFFIXES = [
    # class 1 derivational
    M("luw_d_asa", 1, "asa", "possessive/toponymic -assa-", [LU], ["Melchert 2003", "Payne 2014 (-assa/i-)"]),
    M("luw_d_asi", 1, "asi", "possessive adjective -assi-", [LU], ["Melchert 2003", "Payne 2014 (-assa/i-)"]),
    M("luw_d_ali", 1, "ali", "denominative -alli-", [LU], ["Melchert 1993 (-alli-)"]),
    M("luw_d_wani", 1, "wani", "gentilic -wanni-", [LU], ["Melchert 1993 (-wanni-)"]),
    M("luw_d_ahi", 1, "aḫi", "abstract -ahi(t)-", [LU], ["Melchert 1993 (-ahit-)"]),
    M("luw_d_anza", 1, "anza", "participle -anza", [LU], ["Melchert 1993 (-anza)"]),
    M("luw_d_ant", 1, "ant", "participial -ant-", [LU], ["Melchert 1993 (-ant-)"]),
    M("luw_d_iya", 1, "iya", "adjective -iya-", [LU], ["Melchert 1993 (-iya-)"]),
    M("luw_d_ami", 1, "ami", "deverbative -(a)mmi-", [LU], ["Melchert 1993 (-(a)mma/i-)"]),
    M("luw_d_ana", 1, "ana", "relational -anna/i-", [LU], ["Melchert 1993 (-anna/i-)"]),
    M("luw_d_atar", 1, "atar", "abstract -atar", [LU], ["Melchert 1993 (-atar)"]),
    M("luw_d_ala", 1, "ala", "agent -ala-", [LU], ["Melchert 1993 (-ala-)"]),
    M("luw_d_ahit", 1, "aḫit", "abstract -ahit-", [LU], ["Melchert 1993 (-ahit-)"]),
    # class 2 case/number
    M("luw_c_s", 2, "s", "nom. sg. common -s", [LU], ["Payne 2014 §… nouns", "Melchert 2003"]),
    M("luw_c_n", 2, "n", "acc. sg. common / nom.-acc. sg. neuter -n", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_i", 2, "i", "dat.-loc. sg. -i", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_ati", 2, "ati", "abl.-instr. -ati", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_as", 2, "as", "gen. sg. -as (archaic)", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_nzi", 2, "nzi", "nom. pl. common -nzi", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_nz", 2, "nz", "acc. pl. common -nz", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_c_a", 2, "a", "nom.-acc. pl. neuter / collective -a", [LU], ["Melchert 1993"]),
    M("luw_c_us", 2, "us", "u-stem nom. sg. -us", [LU], ["Melchert 1993 (u-stems)"]),
    M("luw_c_un", 2, "un", "u-stem acc. sg. -un", [LU], ["Melchert 1993 (u-stems)"]),
    M("luw_c_unzi", 2, "unzi", "u-stem nom. pl. -unzi", [LU], ["Melchert 1993 (u-stems)"]),
    M("luw_c_za", 2, "za", "neuter nom.-acc. particle -za/-sa", [LU], ["Melchert 1993 (-sa/-za)"]),
    M("luw_c_anza", 2, "anza", "dat. pl. -anza", [LU], ["Payne 2014"]),
    # class 3 verbal endings
    M("luw_v_wi", 3, "wi", "1sg pres. -wi", [LU], ["Payne 2014 §… verbs", "Melchert 2003"]),
    M("luw_v_si", 3, "si", "2sg pres. -si", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ti", 3, "ti", "3sg pres. -ti", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_i", 3, "i", "3sg pres. -i (ḫi-conjugation)", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_mina", 3, "mina", "1pl pres. -mina", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_tani", 3, "tani", "2pl pres. -tani", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_nti", 3, "nti", "3pl pres. -nti", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ha", 3, "ḫa", "1sg pret. -ḫa", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ta", 3, "ta", "2sg/3sg pret. -ta", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_nta", 3, "nta", "3pl pret. -nta", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_tu", 3, "tu", "3sg impv. -tu", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ntu", 3, "ntu", "3pl impv. -ntu", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ru", 3, "ru", "2sg impv. medio-passive -ru", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_taru", 3, "taru", "3sg impv. medio-passive -taru", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_hari", 3, "ḫari", "1sg medio-passive -ḫari", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_tari", 3, "tari", "2/3sg medio-passive -tari", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ari", 3, "ari", "3sg medio-passive -ari", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_ntari", 3, "ntari", "3pl medio-passive -ntari", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_una", 3, "una", "infinitive -una", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_man", 3, "man", "supine -man", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_v_tanu", 3, "tanu", "2pl impv. -tanu", [LU], ["Payne 2014", "Melchert 2003"]),
    # class 4 Wackernagel clitics (attached to the first word of the clause)
    M("luw_k_wa", 4, "wa", "quotative =wa", [LU], ["Payne 2014 §… clitics", "Melchert 2003"]),
    M("luw_k_pa", 4, "pa", "contrastive =pa", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_ha", 4, "ḫa", "'and also' =ḫa", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_ta", 4, "ta", "local particle =tta/=ta", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_mu", 4, "mu", "1sg dat. =mu", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_ti", 4, "ti", "2sg dat. / reflexive =ti", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_si", 4, "si", "3sg poss. =si", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_an", 4, "an", "3sg acc. =an", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_ata", 4, "ata", "3sg dat. / neuter =ata", [LU], ["Payne 2014", "Melchert 1993"]),
    M("luw_k_du", 4, "du", "3sg dat. =du/=tu", [LU], ["Melchert 1993"]),
    M("luw_k_mi", 4, "mi", "1sg poss. =mi", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_za", 4, "za", "reflexive =za", [LU], ["Payne 2014", "Melchert 2003"]),
    M("luw_k_sa", 4, "sa", "neuter resumptive =sa", [LU], ["Melchert 1993"]),
    M("luw_k_as", 4, "as", "3sg nom. / 3pl acc. =as", [LU], ["Melchert 1993"]),
    M("luw_k_mas", 4, "mas", "3pl dat. =(m)mas", [LU], ["Melchert 1993"]),
    M("luw_k_manza", 4, "manza", "1sg reflexive =manza", [LU], ["Payne 2014"]),
    M("luw_k_anza", 4, "anza", "3sg abl. =anza", [LU], ["Payne 2014"]),
]

LUW_FORMS = [
    ("lu_masanas", LU, [], "masana", ["luw_c_s"], "masanas", "Payne 2014 (massana- 'god', nom. sg.)"),
    ("lu_masanan", LU, [], "masana", ["luw_c_n"], "masanan", "Payne 2014 (acc. sg.)"),
    ("lu_masani", LU, [], "masana", ["luw_c_i"], "masanai", "Payne 2014 (dat.-loc.)"),
    ("lu_masanati", LU, [], "masan", ["luw_c_ati"], "masanati", "Payne 2014 (abl.-instr. -ati; KARATEPE 1)"),
    ("lu_masaninzi", LU, [], "masani", ["luw_c_nzi"], "masaninzi", "Payne 2014 (nom. pl. -nzi)"),
    ("lu_masaninz", LU, [], "masani", ["luw_c_nz"], "masaninz", "Payne 2014 (acc. pl. -nz)"),
    ("lu_masanasis", LU, [], "masan", ["luw_d_asi", "luw_c_s"], "masanasis", "Melchert 2003 (massanassi- 'divine')"),
    ("lu_tarhuntas", LU, [], "tarhunt", ["luw_c_as"], "tarhuntas", "Payne 2014 (gen. -as)"),
    ("lu_tarhuntiyas", LU, [], "tarhunt", ["luw_d_iya", "luw_c_s"], "tarhuntiyas", "Melchert 1993 (-iya-)"),
    ("lu_tarhunzanza", LU, [], "tarhunz", ["luw_d_anza"], "tarhunzanza", "Melchert 1993 (-anza)"),
    ("lu_pipisati", LU, [], "pipisa", ["luw_v_ti"], "pipisati", "Payne 2014 (3sg pres. -ti)"),
    ("lu_piyata", LU, [], "piya", ["luw_v_ta"], "piyata", "Payne 2014 (3sg pret. -ta)"),
    ("lu_piyanta", LU, [], "piya", ["luw_v_nta"], "piyanta", "Payne 2014 (3pl pret. -nta)"),
    ("lu_piyatu", LU, [], "piya", ["luw_v_tu"], "piyatu", "Payne 2014 (3sg impv. -tu)"),
    ("lu_iziha", LU, [], "izi", ["luw_v_ha"], "iziḫa", "Payne 2014, KARATEPE 1 (i-zi-i-ha 'I made')"),
    ("lu_tamaha", LU, [], "tama", ["luw_v_ha"], "tamaḫa", "Payne 2014, KARATEPE 1 (ta-ma-ha 'I built')"),
    ("lu_asata", LU, [], "asa", ["luw_v_ta"], "asata", "Payne 2014 (asa- 'sit', pret.)"),
    ("lu_azuna", LU, [], "az", ["luw_v_una"], "azuna", "Payne 2014 (infinitive -una)"),
    ("lu_iyaman", LU, [], "iya", ["luw_v_man"], "iyaman", "Payne 2014 (supine -man)"),
    ("lu_hantawatis", LU, [], "hantawati", ["luw_c_s"], "hantawatis", "Payne 2014 (hantawati- 'king')"),
    ("lu_hantawatin", LU, [], "hantawati", ["luw_c_n"], "hantawatin", "Payne 2014"),
    ("lu_hantawatalis", LU, [], "hantawat", ["luw_d_ali", "luw_c_s"], "hantawatalis", "Melchert 1993 (-alli-)"),
    ("lu_zas", LU, [], "za", ["luw_c_s"], "zas", "Payne 2014 (demonstrative za-)"),
    ("lu_zan", LU, [], "za", ["luw_c_n"], "zan", "Payne 2014"),
    ("lu_apas", LU, [], "apa", ["luw_c_s"], "apas", "Payne 2014 (apa- 'that')"),
    ("lu_apanzi", LU, [], "apa", ["luw_c_nzi"], "apanzi", "Payne 2014"),
    ("lu_kwis", LU, [], "kwi", ["luw_c_s"], "kwis", "Payne 2014 (relative kwi-)"),
    ("lu_amun", LU, [], "amu", ["luw_c_n"], "amun", "Payne 2014 (1sg pronoun)"),
    ("lu_warpi", LU, [], "warp", ["luw_c_i"], "warpi", "Melchert 2003 (i-mutation)"),
    ("lu_tiyamahi", LU, [], "tiyam", ["luw_d_ahi"], "tiyamaḫi", "Melchert 1993 (-ahi(t)-)"),
    ("lu_lukawanis", LU, [], "luka", ["luw_d_wani", "luw_c_s"], "lukawanis", "Melchert 1993 (-wanni-)"),
    ("lu_tarhuntasas", LU, [], "tarhunt", ["luw_d_asa", "luw_c_s"], "tarhuntasas", "Payne 2014 (-assa-)"),
    ("lu_hantawatatar", LU, [], "hantawat", ["luw_d_atar"], "hantawatatar", "Melchert 1993 (-atar)"),
    ("lu_azari", LU, [], "az", ["luw_v_ari"], "azari", "Payne 2014 (medio-passive -ari)"),
    ("lu_azantari", LU, [], "aza", ["luw_v_ntari"], "azantari", "Payne 2014 (-ntari)"),
    ("lu_asaru", LU, [], "asa", ["luw_v_ru"], "asaru", "Payne 2014 (impv. medio-passive -ru)"),
    ("lu_tarhuntimi", LU, [], "tarhunti", ["luw_k_mi"], "tarhuntimi", "Payne 2014 (=mi)"),
    ("lu_apasha", LU, [], "apa", ["luw_c_s", "luw_k_ha"], "apasḫa", "Payne 2014 (=ḫa)"),
    ("lu_apanpa", LU, [], "apa", ["luw_c_n", "luw_k_pa"], "apanpa", "Payne 2014 (=pa)"),
    ("lu_azantu", LU, [], "aza", ["luw_v_ntu"], "azantu", "Payne 2014 (3pl impv. -ntu)"),
    ("lu_wanatis", LU, [], "wanati", ["luw_c_s"], "wanatis", "Payne 2014 (wanati- 'woman')"),
    ("lu_masanawa", LU, [], "masana", ["luw_k_wa"], "masanawa", "Payne 2014 (=wa on the first word)"),
]

# ===========================================================================
# HURRIAN
# ===========================================================================

HU = "hurrian"
HUR_PREFIX_CLASSES = []
HUR_SUFFIX_CLASSES = ["derivational / root complement", "tense", "valence / mood", "possessive", "plural",
                      "article", "case", "article (Suffixaufnahme)", "case (Suffixaufnahme)",
                      "agreement / enclitic pronoun", "sentence enclitic / negation"]

HUR_PREFIXES: list[dict] = []

HUR_SUFFIXES = [
    # class 1
    M("hur_d_uhe", 1, "uḫe", "gentilic -(u)ḫe", [HU], ["Laroche 1980; Wegner 2007 §… Derivation"]),
    M("hur_d_ubhi", 1, "ubḫi", "adjectival -ubḫi", [HU], ["Laroche 1980"]),
    M("hur_d_ushi", 1, "usḫi", "instrument noun -usḫi", [HU], ["Laroche 1980"]),
    M("hur_d_ugari", 1, "ugari", "abstract -ugari", [HU], ["Laroche 1980"]),
    M("hur_d_uhli", 1, "uḫli", "agent -uḫli", [HU], ["Laroche 1980"]),
    M("hur_d_an", 1, "an", "root complement -an-", [HU], ["Wegner 2007 (Wurzelerweiterungen)"]),
    M("hur_d_ol", 1, "ol", "desiderative / root complement -ol-", [HU], ["Wegner 2007"]),
    M("hur_d_ost", 2, "ošt", "past -ošt-", [HU], ["Wegner 2007 (Tempus)"]),
    M("hur_d_ast", 1, "ast", "intensive -ast-", [HU], ["Laroche 1980"]),
    M("hur_d_ug", 1, "ug", "root complement -ug-", [HU], ["Wegner 2007"]),
    M("hur_d_ill", 1, "ill", "optative -ill-", [HU], ["Wegner 2007 (Modus)"]),
    M("hur_d_du", 1, "du", "causative/derivational -du-", [HU], ["Wegner 2007", "EA 24 un-du-mann-i-n"]),
    M("hur_d_mann", 1, "mann", "desiderative -mann-", [HU], ["Wegner 2007", "EA 24"]),
    M("hur_d_ui", 1, "ui", "passive-reflexive -ui-", [HU], ["Laroche 1980"]),
    # class 2
    M("hur_v_a", 3, "a", "intransitive valence / 3sg pret. -a", [HU], ["Wegner 2007 (Valenz)", "Laroche 1980"]),
    M("hur_v_i", 3, "i", "transitive valence -i-", [HU], ["Wegner 2007 (Valenz)"]),
    M("hur_v_o", 3, "o", "valence -o-", [HU], ["Wegner 2007"]),
    M("hur_v_oz", 2, "oz", "past -ož-", [HU], ["Wegner 2007 (Tempus)"]),
    M("hur_v_ed", 2, "ed", "future -ed-", [HU], ["Wegner 2007 (Tempus)", "Laroche 1980"]),
    M("hur_v_et", 2, "et", "future -et- (class B)", [HU], ["Laroche 1980"]),
    M("hur_v_us", 2, "us", "preterite -us- (class A)", [HU], ["Laroche 1980"]),
    M("hur_v_ust", 2, "ust", "preterite -ust- (class B)", [HU], ["Laroche 1980"]),
    M("hur_v_amb", 3, "amb", "intransitive -am(b)-", [HU], ["Laroche 1980", "Wegner 2007"]),
    M("hur_v_umma", 3, "umma", "infinitive -umma", [HU], ["Laroche 1980"]),
    M("hur_v_um", 3, "um", "infinitive -um", [HU], ["Laroche 1980"]),
    # class 3 possessive
    M("hur_ps_we", 4, "we", "1sg possessive -we/-ffe", [HU], ["Laroche 1980", "Wegner 2007 (Possessivsuffixe)"]),
    M("hur_ps_iffe", 4, "iffe", "1sg possessive -iffe", [HU], ["Wegner 2007 (Possessivsuffixe)"]),
    M("hur_ps_b", 4, "b", "2sg possessive -b/-v", [HU], ["Laroche 1980"]),
    M("hur_ps_ya", 4, "ya", "3sg possessive -(y)a", [HU], ["Laroche 1980"]),
    M("hur_ps_wwas", 4, "wwaš", "1pl possessive -wwaš", [HU], ["Laroche 1980"]),
    M("hur_ps_yas", 4, "yaš", "3pl possessive -yaš", [HU], ["Laroche 1980"]),
    # class 4 plural
    M("hur_pl_as", 5, "aš", "plural -aš-", [HU], ["Wegner 2007 (Numerus)"]),
    M("hur_pl_ast", 5, "ašt", "plural -ašt-", [HU], ["Wegner 2007 (Numerus)"]),
    # class 5 article
    M("hur_ar_ne", 6, "ne", "article / anaphoric -ne", [HU], ["Wegner 2007 (Artikel)", "EA 24"]),
    M("hur_ar_ni", 6, "ni", "article -ni", [HU], ["Wegner 2007 (Artikel)"]),
    M("hur_ar_na", 6, "na", "article plural -na", [HU], ["Wegner 2007 (Artikel)"]),
    # class 6 case
    M("hur_c_se", 7, "še", "ergative -še", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_s", 7, "š", "ergative -š", [HU], ["Wegner 2007 (Kasus)", "EA 24"]),
    M("hur_c_we", 7, "we", "genitive -we", [HU], ["Wegner 2007 (Kasus)", "EA 24"]),
    M("hur_c_wa", 7, "wa", "dative -wa", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_da", 7, "da", "directive -da", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_dan", 7, "dan", "ablative -dan", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_ae", 7, "ae", "instrumental / essive -ae", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_os", 7, "oš", "equative -oš", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_ra", 7, "ra", "associative -ra", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_ura", 7, "ura", "comitative -ura", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_a", 7, "a", "allative / locative -a", [HU], ["Wegner 2007 (Kasus)"]),
    M("hur_c_se_pl", 7, "se", "plural genitive -se", [HU], ["Laroche 1980"]),
    M("hur_c_sa", 7, "sa", "plural dative -sa", [HU], ["Laroche 1980"]),
    M("hur_c_sta", 7, "sta", "plural directive -sta", [HU], ["Laroche 1980"]),
    # class 7/8 Suffixaufnahme (article + case copied from the head)
    M("hur_ar2_ne", 8, "ne", "article resumed after a genitive (Suffixaufnahme)", [HU], ["Wegner 2007 (Suffixaufnahme)", "EA 24"]),
    M("hur_c2_s", 9, "š", "ergative copied from the head", [HU], ["Wegner 2007 (Suffixaufnahme)", "EA 24"]),
    M("hur_c2_wa", 9, "wa", "dative copied from the head", [HU], ["Wegner 2007 (Suffixaufnahme)"]),
    M("hur_c2_da", 9, "da", "directive copied from the head", [HU], ["Wegner 2007 (Suffixaufnahme)"]),
    # class 9 agreement / enclitic pronouns
    M("hur_ag_b", 10, "b", "3sg intransitive agreement -b", [HU], ["Wegner 2007 (Verbalmorphologie)"]),
    M("hur_ag_m", 10, "m", "3sg agreement -m", [HU], ["Wegner 2007"]),
    M("hur_ag_a", 10, "a", "3sg absolutive -a", [HU], ["Laroche 1980"]),
    M("hur_ag_ya", 10, "ya", "3sg present -ya", [HU], ["Laroche 1980"]),
    M("hur_ag_au", 10, "au", "1sg -au", [HU], ["Laroche 1980"]),
    M("hur_ag_iu", 10, "iu", "2sg present -iu", [HU], ["Laroche 1980"]),
    M("hur_ag_u", 10, "u", "2sg preterite -u", [HU], ["Laroche 1980"]),
    M("hur_ag_tilla", 10, "tilla", "1pl -tilla", [HU], ["Laroche 1980"]),
    M("hur_ag_lla", 10, "lla", "3pl -lla", [HU], ["Laroche 1980", "Wegner 2007"]),
    M("hur_ag_tta", 10, "tta", "1sg absolutive clitic -tta", [HU], ["Wegner 2007 (Enklitika)"]),
    M("hur_ag_mma", 10, "mma", "2sg absolutive clitic -mma", [HU], ["Wegner 2007 (Enklitika)"]),
    M("hur_ag_nna", 10, "nna", "3sg absolutive clitic -nna", [HU], ["Wegner 2007 (Enklitika)"]),
    M("hur_ag_n", 10, "n", "3sg absolutive -n", [HU], ["EA 24 un-du-mann-i-n"]),
    M("hur_ag_l", 10, "l", "3pl -l(la)", [HU], ["Wegner 2007"]),
    # class 10 sentence enclitics / negation
    M("hur_en_ma", 11, "ma", "connective -ma", [HU], ["Wegner 2007 (Satzpartikeln)"]),
    M("hur_en_man", 11, "man", "connective -mān", [HU], ["EA 24", "Wegner 2007"]),
    M("hur_en_an", 11, "an", "connective -an", [HU], ["Wegner 2007"]),
    M("hur_en_wa", 11, "wa", "negation -wa", [HU], ["Wegner 2007 (Negation)", "EA 24 tān-a-wa"]),
    M("hur_en_ki", 11, "ki", "assertive negation -ki", [HU], ["Laroche 1980"]),
    M("hur_en_mma", 11, "mma", "connective -mma", [HU], ["Wegner 2007"]),
]

HUR_FORMS = [
    ("hu_enne", HU, [], "eni", ["hur_ar_ne"], "enine", "Wegner 2007 (eni 'god' + article)"),
    ("hu_simigene", HU, [], "šimige", ["hur_ar_ne"], "šimigene", "EA 24 (Šimige-ne)"),
    ("hu_sauskane", HU, [], "šauška", ["hur_ar_ne"], "šauškane", "EA 24 (Šauška-ne)"),
    ("hu_ninuawene", HU, [], "ninua", ["hur_c_we", "hur_ar2_ne"], "ninuawene", "EA 24 (Ninua-we-ne)"),
    ("hu_tessubwenes", HU, [], "tešub", ["hur_c_we", "hur_ar2_ne", "hur_c2_s"], "tešubweneš", "EA 24 (Teššub-we-ne-š)"),
    ("hu_ewrines", HU, [], "ewri", ["hur_ar_ne", "hur_c_s"], "ewrineš", "EA 24 (ewri-ne-š)"),
    ("hu_enast", HU, [], "en", ["hur_pl_ast"], "enašt", "Wegner 2007 (plural -ašt-)"),
    ("hu_eniwa", HU, [], "eni", ["hur_c_wa"], "eniwa", "Wegner 2007 (dative)"),
    ("hu_enida", HU, [], "eni", ["hur_c_da"], "enida", "Wegner 2007 (directive)"),
    ("hu_enidan", HU, [], "eni", ["hur_c_dan"], "enidan", "Wegner 2007 (ablative)"),
    ("hu_eniura", HU, [], "eni", ["hur_c_ura"], "eniura", "Wegner 2007 (comitative)"),
    ("hu_enios", HU, [], "eni", ["hur_c_os"], "enioš", "Wegner 2007 (equative)"),
    ("hu_tadiwe", HU, [], "tadi", ["hur_c_we"], "tadiwe", "Wegner 2007 (genitive)"),
    ("hu_tadiae", HU, [], "tadi", ["hur_c_ae"], "tadiae", "Wegner 2007 (instrumental)"),
    ("hu_tadira", HU, [], "tadi", ["hur_c_ra"], "tadira", "Wegner 2007 (associative)"),
    ("hu_senaiffe", HU, [], "šena", ["hur_ps_iffe"], "šenaiffe", "Wegner 2007 (šena-iffe 'my brother')"),
    ("hu_attaiffe", HU, [], "attai", ["hur_ps_iffe"], "attaiffe", "Wegner 2007 (attai-ffe 'my father')"),
    ("hu_enniyas", HU, [], "eni", ["hur_ps_ya", "hur_c_s"], "eniyaš", "Laroche 1980 (3sg poss. + erg.)"),
    ("hu_tiwena", HU, [], "tiwe", ["hur_ar_na"], "tiwena", "Wegner 2007 (tiwe-na 'the words')"),
    ("hu_pahia", HU, [], "paḫ", ["hur_v_i", "hur_ag_a"], "paḫia", "Wegner 2007 (paḫ- 'build')"),
    ("hu_pahiosta", HU, [], "paḫ", ["hur_d_ost", "hur_v_i", "hur_ag_a"], "paḫoštia", "Wegner 2007 (past -ošt-)"),
    ("hu_pahiawa", HU, [], "paḫ", ["hur_v_i", "hur_ag_a", "hur_en_wa"], "paḫiawa", "Wegner 2007 (negation -wa)"),
    ("hu_unab", HU, [], "un", ["hur_v_a", "hur_ag_b"], "unab", "Wegner 2007 (un- 'come', 3sg intr.)"),
    ("hu_undumannin", HU, [], "un", ["hur_d_du", "hur_v_i", "hur_ag_n"], "undui n", "EA 24 (un-du-mann-i-n)"),
    ("hu_tanawa", HU, [], "tan", ["hur_v_a", "hur_en_wa"], "tanawa", "EA 24 (tān-a-wa)"),
    ("hu_akkaduhe", HU, [], "akkad", ["hur_d_uhe"], "akkaduḫe", "Laroche 1980 (Akkad-uḫe)"),
    ("hu_ahrushi", HU, [], "aḫr", ["hur_d_ushi"], "aḫrusḫi", "Laroche 1980 (aḫr-usḫi 'censer')"),
    ("hu_tadugari", HU, [], "tad", ["hur_d_ugari"], "tadugari", "Laroche 1980 (tad-ugari)"),
    ("hu_unumma", HU, [], "un", ["hur_v_umma"], "unumma", "Laroche 1980 (infinitive -umma)"),
    ("hu_tadau", HU, [], "tad", ["hur_ag_au"], "tadau", "Laroche 1980 (1sg -au)"),
    ("hu_tadiu", HU, [], "tad", ["hur_ag_iu"], "tadiu", "Laroche 1980 (2sg -iu)"),
    ("hu_tadatilla", HU, [], "tad", ["hur_v_a", "hur_ag_tilla"], "tadatilla", "Laroche 1980 (1pl -tilla)"),
    ("hu_eniwenes", HU, [], "eni", ["hur_c_we", "hur_ar2_ne", "hur_c2_s"], "eniweneš", "Wegner 2007 (Suffixaufnahme)"),
    ("hu_enastines", HU, [], "en", ["hur_pl_ast", "hur_ar_ni", "hur_c_s"], "enaštiniš", "Wegner 2007 (enašt-i-ne-š)"),
    ("hu_tadiawwas", HU, [], "tadi", ["hur_ps_wwas"], "tadiwwaš", "Laroche 1980 (1pl poss.)"),
    ("hu_tadozi", HU, [], "tad", ["hur_v_oz", "hur_v_i"], "tadozi", "Wegner 2007 (past -ož- before the valence vowel)"),
    ("hu_tadastab", HU, [], "tad", ["hur_d_ast", "hur_v_a", "hur_ag_b"], "tadastab", "Laroche 1980 (intensive -ast-)"),
    ("hu_tadilla", HU, [], "tad", ["hur_v_i", "hur_ag_lla"], "tadilla", "Laroche 1980 (3pl -lla)"),
    ("hu_tadinna", HU, [], "tad", ["hur_v_i", "hur_ag_nna"], "tadinna", "Wegner 2007 (3sg abs. clitic)"),
    ("hu_enise", HU, [], "eni", ["hur_c_se"], "eniše", "Wegner 2007 (ergative -še)"),
    ("hu_tadiman", HU, [], "tadi", ["hur_en_man"], "tadiman", "EA 24 (-mān)"),
]

# ===========================================================================
# EGYPTIAN (Middle Egyptian; affix vowels per Loprieno 1995 §4 where
# reconstructed, else the Egyptological /e/ filler, flagged)
# ===========================================================================

EG = "egyptian"
EGY_PREFIX_CLASSES = ["proclitic particle / article", "derivational prefix"]
EGY_SUFFIX_CLASSES = ["gender / number / nisbe", "verbal morpheme", "suffix pronoun",
                      "dependent pronoun (enclitic)", "enclitic particle / postnominal determiner"]

EGY_PREFIXES = [
    M("egy_p_iw", 1, "ʾiw", "particle jw", [EG], ["Allen 2014 §10.3"], vowels="filler"),
    M("egy_p_in", 1, "ʾin", "agent marker / particle jn", [EG], ["Allen 2014 §14.9"], vowels="filler"),
    M("egy_p_mek", 1, "mek", "particle mk 'behold'", [EG], ["Allen 2014 §16.6"], vowels="filler"),
    M("egy_p_ne", 1, "ne", "negation n", [EG], ["Allen 2014 §11.5"], vowels="filler"),
    M("egy_p_nen", 1, "nen", "negation nn", [EG], ["Allen 2014 §11.5"], vowels="filler"),
    M("egy_p_pa", 1, "pa", "article pꜣ", [EG], ["Allen 2014 §5.10"]),
    M("egy_p_ta", 1, "ta", "article tꜣ", [EG], ["Allen 2014 §5.10"]),
    M("egy_p_na", 1, "na", "article nꜣ", [EG], ["Allen 2014 §5.10"]),
    M("egy_p_n_prep", 1, "n", "preposition / indirect-genitive n 'to, for, of' (written unseparated)", [EG], ["Allen 2014 §8.2"]),
    M("egy_p_r_prep", 1, "r", "preposition r 'to, toward' (written unseparated)", [EG], ["Allen 2014 §8.2"]),
    M("egy_p_s", 2, "s", "causative prefix s-", [EG], ["Allen 2014 §13.3"]),
    M("egy_p_m", 2, "m", "locative/instrumental noun prefix m-", [EG], ["Allen 2014 §4.5"]),
    M("egy_p_tw", 2, "tuw", "passive prefix tw-", [EG], ["Allen 2014 §19.3"], vowels="filler"),
]

EGY_SUFFIXES = [
    # class 1
    M("egy_g_at", 1, "at", "feminine -t (*-at)", [EG], ["Allen 2014 §4.2", "Loprieno 1995 §4.4"]),
    M("egy_g_t", 1, "t", "feminine -t after a vowel-final stem", [EG], ["Allen 2014 §4.2"]),
    M("egy_g_aw", 1, "aw", "masc. plural -w (*-aw)", [EG], ["Allen 2014 §4.4", "Loprieno 1995 §4.4"]),
    M("egy_g_wat", 1, "wat", "fem. plural / abstract -wt", [EG], ["Allen 2014 §4.4"]),
    M("egy_g_uway", 1, "uway", "masc. dual -wj", [EG], ["Allen 2014 §4.4", "Loprieno 1995 §4.4"]),
    M("egy_g_tay", 1, "tay", "fem. dual -tj", [EG], ["Allen 2014 §4.4"]),
    M("egy_g_i", 1, "i", "nisbe -j (*-i)", [EG], ["Allen 2014 §6.1", "Loprieno 1995 §4.4"]),
    M("egy_g_ti", 1, "ti", "fem. nisbe -tj", [EG], ["Allen 2014 §6.1"]),
    # class 2 verbal
    M("egy_v_n", 2, "n", "sḏm.n.f perfect -n-", [EG], ["Allen 2014 §18.2"]),
    M("egy_v_t", 2, "t", "sḏm.t.f -t-", [EG], ["Allen 2014 §22.3"]),
    M("egy_v_tuw", 2, "tuw", "passive -tw", [EG], ["Allen 2014 §19.3"], vowels="filler"),
    M("egy_v_in", 2, "in", "sḏm.jn.f -jn-", [EG], ["Allen 2014 §22.1"], vowels="filler"),
    M("egy_v_har", 2, "ḫar", "sḏm.ḫr.f -ḫr-", [EG], ["Allen 2014 §22.1"], vowels="filler"),
    M("egy_v_ka", 2, "ka", "sḏm.kꜣ.f -kꜣ-", [EG], ["Allen 2014 §22.1"]),
    M("egy_v_ku", 2, "ku", "stative 1sg -kw", [EG], ["Allen 2014 §17.2", "Loprieno 1995 §4.6"]),
    M("egy_v_ti", 2, "ti", "stative 2sg / 3fs -tj", [EG], ["Allen 2014 §17.2"]),
    M("egy_v_u", 2, "u", "stative 3ms -w", [EG], ["Allen 2014 §17.2"]),
    M("egy_v_win", 2, "win", "stative 1pl -wjn", [EG], ["Allen 2014 §17.2"], vowels="filler"),
    M("egy_v_tiwni", 2, "tiwni", "stative 2pl -tjwnj", [EG], ["Allen 2014 §17.2"], vowels="filler"),
    M("egy_v_w", 2, "w", "stative 3pl / plural participle -w", [EG], ["Allen 2014 §17.2"]),
    # class 3 suffix pronouns
    M("egy_s_i", 3, "i", "1sg .j", [EG], ["Allen 2014 §5.3", "Loprieno 1995 §4.6"]),
    M("egy_s_ak", 3, "ak", "2ms .k", [EG], ["Allen 2014 §5.3", "Loprieno 1995 §4.6"]),
    M("egy_s_at", 3, "aṯ", "2fs .ṯ", [EG], ["Allen 2014 §5.3"]),
    M("egy_s_af", 3, "af", "3ms .f", [EG], ["Allen 2014 §5.3", "Loprieno 1995 §4.6"]),
    M("egy_s_as", 3, "as", "3fs .s", [EG], ["Allen 2014 §5.3", "Loprieno 1995 §4.6"]),
    M("egy_s_an", 3, "an", "1pl .n", [EG], ["Allen 2014 §5.3"]),
    M("egy_s_tan", 3, "ṯan", "2pl .ṯn", [EG], ["Allen 2014 §5.3"], vowels="filler"),
    M("egy_s_san", 3, "san", "3pl .sn", [EG], ["Allen 2014 §5.3", "Loprieno 1995 §4.6"]),
    M("egy_s_st", 3, "sat", "3pl / neuter .st", [EG], ["Allen 2014 §5.3"], vowels="filler"),
    # class 4 dependent pronouns (enclitic to the verb or particle)
    M("egy_dp_wi", 4, "wi", "1sg wj", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_tu", 4, "ṯu", "2ms ṯw", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_tn", 4, "ṯen", "2fs / 2pl ṯn", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_su", 4, "su", "3ms sw", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_si", 4, "si", "3fs sj", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_sen", 4, "sen", "3pl sn", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_st", 4, "set", "neuter st", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    M("egy_dp_n", 4, "en", "1pl n", [EG], ["Allen 2014 §5.4"], vowels="filler"),
    # class 5 enclitic particles and postnominal determiners
    M("egy_e_is", 5, "is", "enclitic js", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_rf", 5, "ref", "enclitic rf", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_hm", 5, "ḥem", "enclitic ḥm", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_grt", 5, "geret", "enclitic grt", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_tr", 5, "ter", "enclitic tr", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_a", 5, "a", "enclitic ꜣ", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_wnnt", 5, "wenet", "enclitic wnnt", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_swt", 5, "sewet", "enclitic swt", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_ms", 5, "mes", "enclitic ms", [EG], ["Allen 2014 §16.7"], vowels="filler"),
    M("egy_e_pn", 5, "pen", "demonstrative pn", [EG], ["Allen 2014 §5.8"], vowels="filler"),
    M("egy_e_tn", 5, "ten", "demonstrative tn", [EG], ["Allen 2014 §5.8"], vowels="filler"),
    M("egy_e_nn", 5, "nen", "demonstrative nn", [EG], ["Allen 2014 §5.8"], vowels="filler"),
    M("egy_e_pf", 5, "pef", "demonstrative pf", [EG], ["Allen 2014 §5.8"], vowels="filler"),
    M("egy_e_tf", 5, "tef", "demonstrative tf", [EG], ["Allen 2014 §5.8"], vowels="filler"),
    M("egy_e_nb", 5, "neb", "quantifier nb 'every'", [EG], ["Allen 2014 §6.4"], vowels="filler"),
]

EGY_FORMS = [
    ("eg_senat", EG, [], "sen", ["egy_g_at"], "senat", "Allen 2014 §4.2 (sn.t 'sister')"),
    ("eg_senaw", EG, [], "sen", ["egy_g_aw"], "senaw", "Allen 2014 §4.4 (sn.w 'brothers')"),
    ("eg_senuway", EG, [], "sen", ["egy_g_uway"], "senuway", "Allen 2014 §4.4 (sn.wj)"),
    ("eg_senwat", EG, [], "sen", ["egy_g_wat"], "senwat", "Allen 2014 §4.4 (sn.wt)"),
    ("eg_neteraw", EG, [], "neṯer", ["egy_g_aw"], "neṯeraw", "Allen 2014 §4.4 (nṯr.w 'gods')"),
    ("eg_kemeti", EG, [], "kemet", ["egy_g_i"], "kemeti", "Allen 2014 §6.1 (kmt.j 'Egyptian')"),
    ("eg_kemetti", EG, [], "kemet", ["egy_g_ti"], "kemetti", "Allen 2014 §6.1 (kmt.tj)"),
    ("eg_sedemaf", EG, [], "seḏem", ["egy_s_af"], "seḏemaf", "Allen 2014 §5.3 (sḏm.f)"),
    ("eg_sedemas", EG, [], "seḏem", ["egy_s_as"], "seḏemas", "Allen 2014 §5.3 (sḏm.s)"),
    ("eg_sedemi", EG, [], "seḏem", ["egy_s_i"], "seḏemi", "Allen 2014 §5.3 (sḏm.j)"),
    ("eg_sedemak", EG, [], "seḏem", ["egy_s_ak"], "seḏemak", "Allen 2014 §5.3 (sḏm.k)"),
    ("eg_sedemat", EG, [], "seḏem", ["egy_s_at"], "seḏemaṯ", "Allen 2014 §5.3 (sḏm.ṯ)"),
    ("eg_sedemsan", EG, [], "seḏem", ["egy_s_san"], "seḏemsan", "Allen 2014 §5.3 (sḏm.sn)"),
    ("eg_sedeman", EG, [], "seḏem", ["egy_s_an"], "seḏeman", "Allen 2014 §5.3 (sḏm.n)"),
    ("eg_sedemtan", EG, [], "seḏem", ["egy_s_tan"], "seḏemṯan", "Allen 2014 §5.3 (sḏm.ṯn)"),
    ("eg_sedemnaf", EG, [], "seḏem", ["egy_v_n", "egy_s_af"], "seḏemnaf", "Allen 2014 §18.2 (sḏm.n.f)"),
    ("eg_sedemtuw", EG, [], "seḏem", ["egy_v_tuw"], "seḏemtuw", "Allen 2014 §19.3 (sḏm.tw)"),
    ("eg_sedeminaf", EG, [], "seḏem", ["egy_v_in", "egy_s_af"], "seḏeminaf", "Allen 2014 §22.1 (sḏm.jn.f)"),
    ("eg_sedemharaf", EG, [], "seḏem", ["egy_v_har", "egy_s_af"], "seḏemḫaraf", "Allen 2014 §22.1 (sḏm.ḫr.f)"),
    ("eg_sedemkaf", EG, [], "seḏem", ["egy_v_ka", "egy_s_af"], "seḏemkaaf", "Allen 2014 §22.1 (sḏm.kꜣ.f)"),
    ("eg_sedemku", EG, [], "seḏem", ["egy_v_ku"], "seḏemku", "Allen 2014 §17.2 (stative 1sg)"),
    ("eg_sedemti", EG, [], "seḏem", ["egy_v_ti"], "seḏemti", "Allen 2014 §17.2 (stative -tj)"),
    ("eg_sedemu", EG, [], "seḏem", ["egy_v_u"], "seḏemu", "Allen 2014 §17.2 (stative 3ms)"),
    ("eg_sedemwin", EG, [], "seḏem", ["egy_v_win"], "seḏemwin", "Allen 2014 §17.2 (stative 1pl)"),
    ("eg_sedemtaf", EG, [], "seḏem", ["egy_v_t", "egy_s_af"], "seḏemtaf", "Allen 2014 §22.3 (sḏm.t.f)"),
    ("eg_semen", EG, ["egy_p_s"], "men", [], "smen", "Allen 2014 §13.3 (s-mn 'establish')"),
    ("eg_seanh", EG, ["egy_p_s"], "ʿanḫ", [], "sʿanḫ", "Allen 2014 §13.3 (s-ʿnḫ)"),
    ("eg_mehat", EG, ["egy_p_m"], "ḫa", ["egy_g_at"], "mḫaat", "Allen 2014 §4.5 (m-ḫꜣ.t 'scales')"),
    ("eg_tuwsedem", EG, ["egy_p_tw"], "seḏem", [], "tuwseḏem", "Allen 2014 §19.3 (tw-sḏm)"),
    ("eg_para", EG, ["egy_p_pa"], "raʿ", [], "paraʿ", "Allen 2014 §5.10 (pꜣ-rʿ)"),
    ("eg_tanet", EG, ["egy_p_ta"], "net", [], "tanet", "Allen 2014 §5.10 (tꜣ-nt)"),
    ("eg_naneter", EG, ["egy_p_na"], "neṯer", [], "naneṯer", "Allen 2014 §5.10 (nꜣ-nṯr)"),
    ("eg_senpen", EG, [], "sen", ["egy_e_pn"], "senpen", "Allen 2014 §5.8 (sn pn)"),
    ("eg_senatten", EG, [], "sen", ["egy_g_at", "egy_e_tn"], "senatten", "Allen 2014 §5.8 (sn.t tn)"),
    ("eg_senneb", EG, [], "sen", ["egy_e_nb"], "senneb", "Allen 2014 §6.4 (sn nb)"),
    ("eg_sedemafref", EG, [], "seḏem", ["egy_s_af", "egy_e_rf"], "seḏemafref", "Allen 2014 §16.7 (sḏm.f rf)"),
    ("eg_sedemafis", EG, [], "seḏem", ["egy_s_af", "egy_e_is"], "seḏemafis", "Allen 2014 §16.7 (sḏm.f js)"),
    ("eg_sedemafsu", EG, [], "seḏem", ["egy_s_af", "egy_dp_su"], "seḏemafsu", "Allen 2014 §5.4 (sḏm.f sw)"),
    ("eg_sedemnafsu", EG, [], "seḏem", ["egy_v_n", "egy_s_af", "egy_dp_su"], "seḏemnafsu", "Allen 2014 §5.4 (sḏm.n.f sw)"),
    ("eg_iwsedem", EG, ["egy_p_iw"], "seḏem", [], "ʾiwseḏem", "Allen 2014 §10.3 (jw sḏm)"),
    ("eg_nesedemaf", EG, ["egy_p_ne"], "seḏem", ["egy_s_af"], "neseḏemaf", "Allen 2014 §11.5 (n sḏm.f)"),
    ("eg_meksu", EG, ["egy_p_mek"], "su", [], "meksu", "Allen 2014 §16.6 (mk sw)"),
]

# ===========================================================================
# assembly
# ===========================================================================

ARMS = {
    "cs": dict(prefix_classes=CS_PREFIX_CLASSES, suffix_classes=CS_SUFFIX_CLASSES,
               prefixes=CS_PREFIXES, suffixes=CS_SUFFIXES, forms=CS_FORMS,
               languages=sorted(NWS | ARABIC), languages_sabaic=sorted(NWS | ARABIC | ASA)),
    "luwian": dict(prefix_classes=LUW_PREFIX_CLASSES, suffix_classes=LUW_SUFFIX_CLASSES,
                   prefixes=LUW_PREFIXES, suffixes=LUW_SUFFIXES, forms=LUW_FORMS, languages=[LU]),
    "hurrian": dict(prefix_classes=HUR_PREFIX_CLASSES, suffix_classes=HUR_SUFFIX_CLASSES,
                    prefixes=HUR_PREFIXES, suffixes=HUR_SUFFIXES, forms=HUR_FORMS, languages=[HU]),
    "egyptian": dict(prefix_classes=EGY_PREFIX_CLASSES, suffix_classes=EGY_SUFFIX_CLASSES,
                     prefixes=EGY_PREFIXES, suffixes=EGY_SUFFIXES, forms=EGY_FORMS, languages=[EG]),
}

FORBIDDEN = ("linear a", "minoan", "ya diktu", "libation formula", "peak sanctuary")


def phon_segments(s: str, arm: str = "cs") -> list[list]:
    from common import paradigm
    return [[c, v] for c, v in paradigm.segs(s, arm)]


def family_needles() -> set[str]:
    fam = paths.load_data("formula_family.json")
    needles: set[str] = set()
    for insc in fam["inscriptions"]:
        for t in insc["tokens"]:
            if "-" in t["linear_a"]:
                needles.add(t["linear_a"].lower())
        for ws in insc["slots"].values():
            for w in ws:
                if "-" in w:
                    needles.add(w.lower())
    lex = paths.load_snapshot("lexicon.json")
    entries = lex.get("entries", lex) if isinstance(lex, dict) else lex
    if isinstance(entries, dict):
        entries = list(entries.values()) if not all(isinstance(v, str) for v in entries.values()) else []
    for e in entries:
        if isinstance(e, dict):
            w = e.get("word") or e.get("linear_a") or ""
            if isinstance(w, str) and "-" in w:
                needles.add(w.lower())
    return needles


def _mentions(text: str, needle: str) -> bool:
    """Whole-form match: the hyphenated Linear A form bounded by non-sign characters."""
    return re.search(r"(?<![\w*])" + re.escape(needle) + r"(?![\w*])", text) is not None


def check_blind(arm: str, rows: list[dict], forms: list[tuple], needles: set[str]) -> None:
    for r in rows:
        text = " ".join([r["id"], r["function"], " ".join(r["citations"]), r.get("note") or ""]).lower()
        for f in FORBIDDEN:
            if f in text:
                sys.exit(f"[blindness] {arm}:{r['id']} mentions {f!r}")
        for n in needles:
            if _mentions(text, n):
                sys.exit(f"[blindness] {arm}:{r['id']} mentions the Linear A form {n!r}")
    for f in forms:
        text = " ".join([f[0], f[6]]).lower()
        for x in FORBIDDEN:
            if x in text:
                sys.exit(f"[blindness] {arm} form {f[0]} mentions {x!r}")
        for n in needles:
            if _mentions(text, n):
                sys.exit(f"[blindness] {arm} form {f[0]} mentions the Linear A form {n!r}")


def one_sign(row: dict, kind: str, arm: str) -> bool:
    segs = render_la.fuse_segments([(p[0], p[1]) for p in row["phonemic"]])
    if kind == "suffix":
        r = render_la.render_segments(segs, arm, prev_vowel="a", word_final=True)
        # a bare initial vowel fuses with the stem-final consonant: count the rest
        n = len(r) - (1 if segs and segs[0][0] is None else 0)
        return n <= 1
    r = render_la.render_segments(segs, arm, next_vowel="a", word_final=False)
    return len(r) <= 1


def build_arm(arm: str, spec: dict, needles: set[str], stamp: str) -> dict:
    rows = []
    for kind, lst in (("prefix", spec["prefixes"]), ("suffix", spec["suffixes"])):
        for r in lst:
            row = dict(r)
            row["kind"] = kind
            row["phonemic"] = phon_segments(row.pop("phon"), arm)
            row["sabaic_only"] = (row.get("note") == "sabaic_only")
            if arm == "cs":
                langs = set(row["attested_in"])
                row["branches"] = sorted({b for b, s in (("nws", NWS), ("arabic", ARABIC), ("asa", ASA)) if langs & s})
            rows.append(row)
    check_blind(arm, rows, spec["forms"], needles)
    forms = [dict(id=f[0], language=f[1], prefixes=f[2], stem=f[3], suffixes=f[4], surface=f[5], citation=f[6])
             for f in spec["forms"]]
    ids = {r["id"] for r in rows}
    for f in forms:
        for mid in f["prefixes"] + f["suffixes"]:
            if mid not in ids:
                sys.exit(f"{arm}: form {f['id']} cites unknown morpheme {mid}")
    headline = [r for r in rows if r["cost"] == 0 and not r["sabaic_only"]]
    distinct = {(r["kind"], tuple(map(tuple, r["phonemic"]))) for r in headline}
    one = {(r["kind"], tuple(map(tuple, r["phonemic"]))) for r in headline if one_sign(r, r["kind"], arm)}
    counts = dict(total=len(rows), headline=len(headline), distinct_headline=len(distinct),
                  one_sign_headline=len(one),
                  priced=sum(r["cost"] > 0 for r in rows), sabaic_only=sum(r["sabaic_only"] for r in rows),
                  prefix=sum(r["kind"] == "prefix" for r in headline),
                  suffix=sum(r["kind"] == "suffix" for r in headline))
    return {
        "_meta": {"built_by": "scripts/build_paradigm.py", "built_at": stamp,
                  "inputs": {"data/formula_family.json": paths.sha256(paths.DATA / "formula_family.json")},
                  "attribution": ATTRIBUTION, "protocol": "PROTOCOL-B.md §4",
                  "blindness_rule": "no entry mentions a Linear A form, a lexicon.json headword, "
                                    "'Linear A', 'Minoan' or 'Ya Diktu' (checked mechanically at build)",
                  "citation_status": "section numbers marked '(topic)' are to be verified against the "
                                     "cited grammar before REPORT-B cites them; records for Al-Jallad 2015, "
                                     "Beeston 1984, Joüon–Muraoka 2006, Huffmon 1965, Payne 2014, Melchert 1993/2003, "
                                     "Wegner 2007, Laroche 1980, Allen 2014, Loprieno 1995 to be added to "
                                     "sources/sources_database.json"},
        "arm": arm,
        "languages": spec["languages"],
        "languages_with_sabaic": spec.get("languages_sabaic", spec["languages"]),
        "classes": {"prefix": spec["prefix_classes"], "suffix": spec["suffix_classes"]},
        "morphemes": rows,
        "attested_forms": forms,
        "counts": counts,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    needles = family_needles()
    built = {arm: build_arm(arm, spec, needles, stamp) for arm, spec in ARMS.items()}
    # nws_floor: the NWS-attested subset of cs (cost-0, branch includes nws)
    floor = json.loads(json.dumps(built["cs"]))
    floor["arm"] = "nws_floor"
    floor["morphemes"] = [r for r in floor["morphemes"] if r["cost"] == 0 and "nws" in r.get("branches", [])]
    floor["attested_forms"] = [f for f in floor["attested_forms"] if f["language"] in NWS]
    floor["languages"] = sorted(NWS)
    fl_head = floor["morphemes"]
    floor["counts"] = dict(total=len(fl_head), headline=len(fl_head),
                           distinct_headline=len({(r["kind"], tuple(map(tuple, r["phonemic"]))) for r in fl_head}),
                           one_sign_headline=len({(r["kind"], tuple(map(tuple, r["phonemic"]))) for r in fl_head if one_sign(r, r["kind"], "nws_floor")}),
                           priced=0, sabaic_only=0,
                           prefix=sum(r["kind"] == "prefix" for r in fl_head),
                           suffix=sum(r["kind"] == "suffix" for r in fl_head))
    built["nws_floor"] = floor

    print("arm         total headline distinct one-sign prefix suffix priced sabaic_only forms")
    for arm, d in built.items():
        c = d["counts"]
        print(f"{arm:<11} {c['total']:>5} {c['headline']:>8} {c['distinct_headline']:>8} {c['one_sign_headline']:>8} "
              f"{c['prefix']:>6} {c['suffix']:>6} {c['priced']:>6} {c['sabaic_only']:>11} {len(d['attested_forms']):>5}")
    # parity (§4.2): rivals vs cs on distinct headline count and one-sign count
    cs = built["cs"]["counts"]
    bad = []
    for arm in ("luwian", "hurrian", "egyptian"):
        c = built[arm]["counts"]
        for key, cap in (("distinct_headline", PARITY), ("one_sign_headline", PARITY_ONE_SIGN_CAP)):
            ratio = max(cs[key], c[key]) / max(1, min(cs[key], c[key]))
            built[arm]["counts"][f"ratio_{key}_vs_cs"] = round(ratio, 3)
            if ratio > cap:
                bad.append(f"{arm} {key}: cs {cs[key]} vs {c[key]} (ratio {ratio:.2f} > {cap})")
    if bad:
        print("PARITY VIOLATION:\n  " + "\n  ".join(bad))
        return 3
    for arm, d in built.items():
        (OUT_DIR / f"{arm}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(built)} inventories to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
