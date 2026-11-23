"""Kernel F: Pre-Linguistic Commodity Ligature & Adjunct Acrophony (10,000 consonant-grid perms).

Tests whether syllabic adjuncts written directly on pictographically fixed commodity logograms
(GRA+*, OLE+*, VIN+*) match the initial CV syllable (acrophone) of bounded, equal-size commodity
qualifier synsets in Semitic vs. Greek, Anatolian, and Hurrian.

Calibration Gate (--calibrate):
  Runs on Linear B's own commodity ligatures (OLE+PA, OLE+WE, OLE+A, TELA+TE, TELA+PU, GRA+PE)
  and must identify Linear B as Greek at p_perm <= 0.01 while rejecting Semitic, Anatolian, Hurrian.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import c_align as a  # noqa: E402
import c_render as r  # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
CONSONANT_SERIES = ("D", "J", "K", "M", "N", "P", "Q", "R", "S", "T", "W", "Z")
Key = tuple[str, str]

# Bounded commodity-qualifier synsets (max 6 attested Bronze Age qualifiers/types per commodity per language)
COMMODITY_SYNSETS: dict[str, dict[str, list[tuple[str, tuple[str, ...], str]]]] = {
    "OIL": {
        "semitic": [
            ("ṭābu", ("ṭ", "a", "b", "u"), "Ug. šmn ṭb, Ebla sa-ma-nu-um da-bù 'good oil'"),
            ("mišḥā", ("m", "i", "š", "ḥ", "a"), "Heb. šemen ham-mišḥā, Ug. mšḥ 'anointing oil'"),
            ("dišpu", ("d", "i", "š", "p", "u"), "Akk. dišpu 'honey(ed oil)'"),
            ("neseku", ("n", "e", "s", "e", "k", "u"), "Heb. nesek, Ug. nsk 'libation oil'"),
            ("riqqu", ("r", "i", "q", "u"), "Akk. riqqu, Ug. rqḥ 'aromatic oil'"),
            ("kīnu", ("k", "i", "n", "u"), "Akk. kīnu 'standard/regular oil'"),
        ],
        "greek": [
            ("pakowen", ("p", "a", "k", "o", "w", "e"), "Myc. OLE+PA pa-ko-we 'sage-scented oil'"),
            ("wearepe", ("w", "e", "a", "r", "e", "p", "e"), "Myc. OLE+WE we-a-re-pe 'anointing oil'"),
            ("aloipha", ("a", "l", "o", "i", "p", "a"), "Myc. OLE+A a-re-pa 'unguent/salve'"),
            ("kuperon", ("k", "u", "p", "e", "r", "o"), "Myc. ku-pa-ro 'cyperus-scented'"),
            ("wodo", ("w", "o", "d", "o"), "Myc. wo-do-we 'rose-scented oil'"),
            ("elaion", ("e", "l", "a", "i", "o", "n"), "Gk. ἔλαιον 'olive oil'"),
        ],
        "anatolian": [
            ("sani", ("s", "a", "n", "i"), "Hitt. šani- 'fine/pure oil'"),
            ("hulali", ("ḫ", "u", "l", "a", "l", "i"), "Hitt. oil qualifier"),
            ("huppar", ("ḫ", "u", "p", "a", "r"), "Hitt. vessel/oil"),
            ("lazzai", ("l", "a", "z", "a", "i"), "Hitt. lazzi- 'good'"),
            ("parkui", ("p", "a", "r", "k", "u", "i"), "Hitt. parkui- 'pure'"),
            ("waršula", ("w", "a", "r", "š", "u", "l", "a"), "Hitt. waršula- 'fragrant'"),
        ],
        "hurrian": [
            ("šehali", ("š", "e", "ḫ", "a", "l", "i"), "Hurr. šeḫali 'pure'"),
            ("niri", ("n", "i", "r", "i"), "Hurr. niri 'good'"),
            ("pahi", ("p", "a", "ḫ", "i"), "Hurr. aromatic/head"),
            ("turi", ("t", "u", "r", "i"), "Hurr. qualifier"),
            ("ahri", ("a", "ḫ", "r", "i"), "Hurr. aḫri 'incense/fragrance'"),
            ("keldi", ("k", "e", "l", "t", "i"), "Hurr. keldi 'well-being/offering'"),
        ],
    },
    "GRAIN": {
        "semitic": [
            ("kunīšu", ("k", "u", "n", "i", "š", "u"), "Akk./Nuzi kunīšu 'emmer wheat'"),
            ("parīsu", ("p", "a", "r", "i", "s", "u"), "Akk. parīsu, Ug. prs 'half-gur grain measure'"),
            ("qemāḥu", ("q", "e", "m", "a", "ḥ", "u"), "Heb. qemaḥ, Ug. qmḥ, Akk. qēmu 'flour'"),
            ("barru", ("b", "a", "r", "u"), "Heb. bār, Ar. burr 'threshed grain'"),
            ("ḥiṭṭatu", ("ḥ", "i", "ṭ", "a", "t", "u"), "Ug. ḥṭt, Heb. ḥiṭṭāh 'wheat'"),
            ("šeʾu", ("š", "e", "ʾ", "u"), "Akk. šeʾu 'barley'"),
        ],
        "greek": [
            ("pema", ("p", "e", "m", "a"), "Myc. GRA+PE pe-mo/pe-ma 'seed grain'"),
            ("sitos", ("s", "i", "t", "o", "s"), "Myc. si-to 'grain'"),
            ("kritha", ("k", "r", "i", "t", "a"), "Gk. κριθή 'barley'"),
            ("puros", ("p", "u", "r", "o", "s"), "Gk. πυρός 'wheat'"),
            ("aleuron", ("a", "l", "e", "u", "r", "o", "n"), "Gk. ἄλευρον 'wheat flour'"),
            ("zeia", ("z", "e", "i", "a"), "Gk. ζειά 'emmer'"),
        ],
        "anatolian": [
            ("halki", ("ḫ", "a", "l", "k", "i"), "Hitt. ḫalki- 'barley/grain'"),
            ("kant", ("k", "a", "n", "t", "a"), "Hitt. kant- 'einkorn wheat'"),
            ("zizza", ("z", "i", "z", "a"), "Hitt. zizza- 'emmer'"),
            ("memal", ("m", "e", "m", "a", "l"), "Hitt. memal 'groats/meal'"),
            ("šeppit", ("š", "e", "p", "i", "t"), "Hitt. šeppit- 'grain'"),
            ("ewan", ("e", "w", "a", "n"), "Hitt. ewan- 'barley'"),
        ],
        "hurrian": [
            ("kade", ("k", "a", "t", "e"), "Hurr. kade 'barley'"),
            ("hini", ("ḫ", "i", "n", "i"), "Hurr. grain/flour"),
            ("šari", ("š", "a", "r", "i"), "Hurr. grain"),
            ("tali", ("t", "a", "l", "i"), "Hurr. produce"),
            ("amari", ("a", "m", "a", "r", "i"), "Hurr. cereal"),
            ("zizi", ("z", "i", "z", "i"), "Hurr. grain"),
        ],
    },
    "WINE": {
        "semitic": [
            ("raqḥu", ("r", "a", "q", "ḥ", "u"), "Heb. yayin hāreqaḥ 'spiced wine'"),
            ("ṭābu", ("ṭ", "a", "b", "u"), "Ug. yn ṭb 'good wine'"),
            ("ḥamru", ("ḥ", "a", "m", "r", "u"), "Ug. ḫmr 'fermented wine'"),
            ("kadu", ("k", "a", "d", "u"), "Ug. kd yn 'jar of wine'"),
        ],
        "greek": [
            ("woinos", ("w", "o", "i", "n", "o", "s"), "Myc. wo-no 'wine'"),
            ("methu", ("m", "e", "t", "u"), "Gk. μέθυ 'wine'"),
            ("gleukos", ("g", "l", "e", "u", "k", "o", "s"), "Gk. γλεῦκος 'sweet wine'"),
            ("deuka", ("d", "e", "u", "k", "a"), "Myc. de-re-u-ko 'new wine'"),
        ],
        "anatolian": [
            ("wiyana", ("w", "i", "y", "a", "n", "a"), "Hitt. wiyana- 'wine'"),
            ("maddu", ("m", "a", "d", "u"), "Luw. maddu- 'wine'"),
            ("marnuwan", ("m", "a", "r", "n", "u", "w", "a", "n"), "Hitt. fermented drink"),
            ("walhi", ("w", "a", "l", "ḫ", "i"), "Hitt. walḫi- 'beverage'"),
        ],
        "hurrian": [
            ("taršu", ("t", "a", "r", "š", "u"), "Hurr. beverage"),
            ("šiye", ("š", "i", "y", "e"), "Hurr. drink"),
            ("kuri", ("k", "u", "r", "i"), "Hurr. drink"),
            ("madi", ("m", "a", "t", "i"), "Hurr. drink"),
        ],
    },
    "TEXTILE": {
        "semitic": [
            ("kitānu", ("k", "i", "t", "a", "n", "u"), "Akk. kitû, Ug. ktn 'linen'"),
            ("ṣubātu", ("ṣ", "u", "b", "a", "t", "u"), "Akk. ṣubātu 'garment'"),
            ("buṣu", ("b", "u", "ṣ", "u"), "Heb. būṣ 'fine linen'"),
            ("labūšu", ("l", "a", "b", "u", "š", "u"), "Ug. lbš, Akk. lubūšu 'garment'"),
        ],
        "greek": [
            ("tepa", ("t", "e", "p", "a"), "Myc. TELA+TE te-pa 'heavy cloth'"),
            ("pukata", ("p", "u", "k", "a", "t", "a"), "Myc. TELA+PU pu-ka-ta-ri-ja 'folded cloth'"),
            ("pako", ("p", "a", "k", "o"), "Myc. pa-we-a 'cloths'"),
            ("kito", ("k", "i", "t", "o"), "Myc. ki-to 'tunic'"),
        ],
        "anatolian": [
            ("tug", ("t", "u", "k", "a"), "Hitt. cloth"),
            ("kureššar", ("k", "u", "r", "e", "š", "a", "r"), "Hitt. kureššar 'fabric'"),
            ("hulana", ("ḫ", "u", "l", "a", "n", "a"), "Hitt. ḫulana- 'wool'"),
            ("kariulli", ("k", "a", "r", "i", "u", "l", "i"), "Hitt. garment"),
        ],
        "hurrian": [
            ("tabri", ("t", "a", "p", "r", "i"), "Hurr. cloth"),
            ("ziani", ("z", "i", "a", "n", "i"), "Hurr. textile"),
            ("kubi", ("k", "u", "p", "i"), "Hurr. garment"),
            ("šari", ("š", "a", "r", "i"), "Hurr. fabric"),
        ],
    },
}

# Linear B calibration ligatures (strictly Greek acrophones)
LINEAR_B_LIGATURES: list[tuple[str, str]] = [
    ("PA", "OIL"),      # OLE+PA pa-ko-we
    ("WE", "OIL"),      # OLE+WE we-a-re-pe
    ("A", "OIL"),       # OLE+A a-re-pa
    ("PE", "GRAIN"),    # GRA+PE pe-mo
    ("TE", "TEXTILE"),  # TELA+TE te-pa
    ("PU", "TEXTILE"),  # TELA+PU pu-ka-ta-ri-ja
]

# Linear A strict commodity ligatures (Ya Diktu App. C.5; only secure Linear B adjunct signs)
LINEAR_A_LIGATURES: list[tuple[str, str]] = [
    ("KU", "GRAIN"),    # GRA+KU
    ("PA", "GRAIN"),    # GRA+PA
    ("QE", "GRAIN"),    # GRA+QE
    ("KI", "OIL"),      # OLE+KI
    ("MI", "OIL"),      # OLE+MI
    ("DI", "OIL"),      # OLE+DI
    ("TA", "OIL"),      # OLE+TA
    ("NE", "OIL"),      # OLE+NE
    ("RI", "OIL"),      # OLE+RI
    ("RA", "WINE"),     # VIN+RA
]


def syll_distance(x: Key, y: Key) -> float:
    if x == y:
        return 0.0
    if x[0] == y[0]:
        return 0.35
    if x[1] == y[1]:
        return 0.85
    return 1.0


def build_acrophones(tables: r.Tables) -> dict[str, dict[str, list[Key]]]:
    out: dict[str, dict[str, list[Key]]] = {}
    for comm, by_lang in COMMODITY_SYNSETS.items():
        out[comm] = {}
        for lang, entries in by_lang.items():
            arm_key = "luwian" if lang == "anatolian" else lang
            keys: list[Key] = []
            for _, segs, _ in entries:
                w = r.word(segs, arm_key, tables, "plene") or r.word(segs, arm_key, tables, "omission")
                if w:
                    keys.append(w[0])
            out[comm][lang] = keys
    return out


def score_ligatures(ligs: list[tuple[Key, str]], acros: dict, lang: str, beta: float = 6.0) -> float:
    ll = 0.0
    for k, comm in ligs:
        cands = acros[comm][lang]
        dists = [syll_distance(k, c) for c in cands]
        mx = max(-beta * d for d in dists)
        ll += mx + math.log(sum(math.exp(-beta * d - mx) for d in dists) / len(dists))
    return ll


def run_battery(
    ligatures: list[tuple[str, str]],
    tables: r.Tables,
    sign_table: dict,
    n_perm: int = 10000,
    seed: int = 20261122,
    beta: float = 6.0,
) -> dict:
    acros = build_acrophones(tables)
    parsed = [(a.keys(adj, sign_table)[0], comm) for adj, comm in ligatures]
    langs = ("semitic", "greek", "anatolian", "hurrian")
    obs = {lang: score_ligatures(parsed, acros, lang, beta=beta) for lang in langs}

    rng = random.Random(seed)
    perm_lls = {lang: [] for lang in langs}
    ge = {lang: 0 for lang in langs}
    for _ in range(n_perm):
        shuf = list(CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(CONSONANT_SERIES, shuf))
        pligs = [((mp.get(k[0], k[0]), k[1]), comm) for k, comm in parsed]
        for lang in langs:
            ll = score_ligatures(pligs, acros, lang, beta=beta)
            perm_lls[lang].append(ll)
            if ll >= obs[lang] - 1e-12:
                ge[lang] += 1

    summary = {}
    for lang in langs:
        arr = perm_lls[lang]
        mean = sum(arr) / len(arr)
        sd = math.sqrt(sum((x - mean) ** 2 for x in arr) / len(arr)) or 1e-9
        summary[lang] = {
            "ll": round(obs[lang], 4),
            "z_perm": round((obs[lang] - mean) / sd, 3),
            "p_perm": round((1 + ge[lang]) / (n_perm + 1), 5),
        }
    winner = max(langs, key=lambda l: summary[l]["z_perm"])
    return {"winner": winner, "n_perm": n_perm, "languages": summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--run-linear-a", action="store_true")
    ap.add_argument("--n-perm", type=int, default=10000)
    args = ap.parse_args()

    tables = r.load_tables()
    sign_table = a.load_signs()
    cal = run_battery(LINEAR_B_LIGATURES, tables, sign_table, n_perm=args.n_perm)
    runner_ll = max(cal["languages"][l]["ll"] for l in ("semitic", "anatolian", "hurrian"))
    cal_pass = cal["winner"] == "greek" and cal["languages"]["greek"]["p_perm"] <= 0.01 and (cal["languages"]["greek"]["ll"] - runner_ll) >= 3.0
    print(f"=== Kernel F Calibration (Linear B Ligatures, B={args.n_perm}) | PASS={cal_pass} ===")
    for lang, s in cal["languages"].items():
        print(f"  {lang:10s} | LL={s['ll']:8.3f} | Z_perm={s['z_perm']:+6.2f} | p_perm={s['p_perm']:.5f}")

    if args.run_linear_a:
        if not SIGNATURE.is_file() or not cal_pass:
            print("REFUSED: requires SIGNATURE.txt and passing calibration.", file=sys.stderr)
            return 2
        la = run_battery(LINEAR_A_LIGATURES, tables, sign_table, n_perm=args.n_perm)
        print(f"\n=== Kernel F Target (Linear A Commodity Ligatures, B={args.n_perm}) | winner={la['winner']} ===")
        for lang, s in la["languages"].items():
            print(f"  {lang:10s} | LL={s['ll']:8.3f} | Z_perm={s['z_perm']:+6.2f} | p_perm={s['p_perm']:.5f}")
    return 0 if cal_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
