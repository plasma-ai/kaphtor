"""Kernel D: Pre-Linguistic Semantic Anchors with Bounded Synsets & Grid-Permutation Null (KERNEL-SPECS.md §5).

Tests whether words whose meanings are fixed BEFORE any language is named (by arithmetic summation or
direct pictographic/logogram adjacency) match one candidate language better than rivals AND better than
10,000 random consonant-series permutations of the Linear B syllabary grid.

Calibration Gate (--calibrate):
  Runs ONLY on Linear B's own pre-linguistic anchors (to-so, o-pe-ro, ti-ri-po, di-pa, si-to, wo-no).
  Must identify Linear B as Greek at p_perm <= 0.01 and reject Semitic, Anatolian, and Hurrian.

Linear A mode (--run-linear-a) is refused unless SIGNATURE.txt exists and calibration passes.

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
Word = tuple[tuple[str, str], ...]


def glide(word: Word, signs: set) -> Word:
    out = [word[0]]
    for key in word[1:]:
        series = {"i": "J", "u": "W"}.get(out[-1][1]) if key[0] == "" else None
        out.append((series, key[1]) if series and (series, key[1]) in signs else key)
    return tuple(out)


# ---- Pre-registered bounded synsets (max 6 core attested Bronze Age / early lexemes per slot per language) ----
# Every entry is a phoneme-segment tuple for c_render.word, with standard dictionary provenance.

SYNSETS: dict[str, dict[str, list[tuple[str, tuple[str, ...], str]]]] = {
    "TOTAL": {
        "semitic": [
            ("kullu", ("k", "u", "l", "u"), "Ug. kl /kull-/, Akk. kullatu, Heb. kol"),
            ("gamru", ("g", "a", "m", "r", "u"), "Akk. gamru 'total'"),
            ("napḫaru", ("n", "a", "p", "ḫ", "a", "r", "u"), "Akk. napḫaru 'total'"),
            ("gabbu", ("g", "a", "b", "u"), "Akk. gabbu 'all, total'"),
        ],
        "greek": [
            ("tosos", ("t", "o", "s", "o", "s"), "Myc. to-so, Gk. τόσος 'so much, total'"),
            ("pas", ("p", "a", "s"), "Gk. πᾶς 'all'"),
            ("holos", ("h", "o", "l", "o", "s"), "Gk. ὅλος 'whole'"),
            ("sumpas", ("s", "u", "m", "p", "a", "s"), "Gk. σύμπας 'all together'"),
        ],
        "anatolian": [
            ("humant", ("ḫ", "u", "m", "a", "n", "t", "a"), "Hitt. ḫūmant- 'all, whole'"),
            ("tanima", ("t", "a", "n", "i", "m", "a"), "Luw. tanima- 'all, every'"),
            ("punata", ("p", "u", "n", "a", "t", "a"), "Luw. punata- 'all'"),
            ("dapian", ("t", "a", "p", "i", "a", "n"), "Hitt. dapi- 'entire'"),
        ],
        "hurrian": [
            ("sua", ("š", "u", "a"), "Hurr. šu-a 'all'"),
            ("sue", ("š", "u", "e"), "Hurr. šu-e 'all'"),
            ("heiarunna", ("ḫ", "e", "i", "a", "r", "u", "n", "a"), "Hurr. ḫeiarunna 'all'"),
            ("tubi", ("t", "u", "p", "i"), "Hurr. tup- 'sum/full'"),
        ],
    },
    "DEFICIT": {
        "semitic": [
            ("kilu", ("k", "i", "l", "u"), "Aram. klʾ 'withhold', Akk. kalû 'withhold deliveries'"),
            ("ḫisru", ("ḫ", "i", "s", "r", "u"), "Heb. ḥesrōn, Ug. ḫsr 'lack, deficit'"),
            ("maṭu", ("m", "a", "ṭ", "u"), "Akk. maṭû 'be lacking, deficit'"),
            ("riḫtu", ("r", "i", "ḫ", "t", "u"), "Akk. rīḫtu 'remainder, balance'"),
        ],
        "greek": [
            ("ophelos", ("o", "p", "e", "l", "o", "s"), "Myc. o-pe-ro 'debt, deficit'"),
            ("leimma", ("l", "e", "i", "m", "a"), "Gk. λεῖμμα 'remnant'"),
            ("endeia", ("e", "n", "d", "e", "i", "a"), "Gk. ἔνδεια 'lack'"),
            ("loipos", ("l", "o", "i", "p", "o", "s"), "Gk. λοιπός 'remaining'"),
        ],
        "anatolian": [
            ("karus", ("k", "a", "r", "u", "s"), "Hitt. karuš- 'fall short'"),
            ("impa", ("i", "m", "p", "a"), "Hitt. impa- 'burden, obligation'"),
            ("tarku", ("t", "a", "r", "k", "u"), "Hitt./Luw. residue/debt"),
            ("kappi", ("k", "a", "p", "i"), "Hitt. kappi- 'small, short'"),
        ],
        "hurrian": [
            ("kiri", ("k", "i", "r", "i"), "Hurr. kir- 'release/owe'"),
            ("niri", ("n", "i", "r", "i"), "Hurr. nir- 'less'"),
            ("tadi", ("t", "a", "t", "i"), "Hurr. tat-"),
            ("ari", ("a", "r", "i"), "Hurr. ar- 'give/due'"),
        ],
    },
    "VESSEL_CUP": {
        "semitic": [
            ("aganu", ("ʾ", "a", "g", "a", "n", "u"), "Ug. ʾagn, Heb. ʾaggān, Akk. agannu 'bowl'"),
            ("suppu", ("s", "u", "p", "u"), "Ebla zu-bù, Ug. sp, Mari sappu 'bowl'"),
            ("qabu", ("q", "a", "b", "u"), "Heb. qab, Akk. qû 'measuring cup'"),
            ("karpatu", ("k", "a", "r", "p", "a", "t", "u"), "Akk. karpatu, Ug. krpn 'pot, cup'"),
            ("kadu", ("k", "a", "d", "u"), "Ug. kd, Heb. kad 'jar'"),
            ("kasu", ("k", "a", "s", "u"), "Ug. ks, Heb. kōs, Akk. kāsu 'cup'"),
        ],
        "greek": [
            ("depas", ("d", "e", "p", "a", "s"), "Myc. di-pa, Gk. δέπας 'cup, vessel'"),
            ("tripos", ("t", "r", "i", "p", "o", "s"), "Myc. ti-ri-po, Gk. τρίπους 'tripod cauldron'"),
            ("krater", ("k", "r", "a", "t", "e", "r"), "Gk. κρατήρ 'mixing bowl'"),
            ("kulix", ("k", "u", "l", "i", "k", "s"), "Gk. κύλιξ 'cup'"),
            ("phiale", ("p", "i", "a", "l", "e"), "Gk. φιάλη 'shallow bowl'"),
            ("amphoreus", ("a", "m", "p", "o", "r", "e", "u", "s"), "Myc. a-pi-po-re-we 'amphora'"),
        ],
        "anatolian": [
            ("huppar", ("ḫ", "u", "p", "a", "r"), "Hitt. ḫuppar- 'bowl, tureen'"),
            ("tapišana", ("t", "a", "p", "i", "š", "a", "n", "a"), "Hitt. tapišana- 'vessel'"),
            ("ishuzzi", ("i", "š", "ḫ", "u", "z", "i"), "Hitt. vessel/jar"),
            ("palhi", ("p", "a", "l", "ḫ", "i"), "Hitt. palḫi- 'cauldron'"),
            ("kukup", ("k", "u", "k", "u", "p", "i"), "Hitt. kukup- 'jug'"),
            ("zaluwani", ("z", "a", "l", "u", "w", "a", "n", "i"), "Hitt. zaluwani- 'plate/bowl'"),
        ],
        "hurrian": [
            ("kazi", ("k", "a", "z", "i"), "Hurr. kazi 'cup'"),
            ("hupri", ("ḫ", "u", "p", "r", "i"), "Hurr. ḫupri 'vessel, pot'"),
            ("zallu", ("z", "a", "l", "u"), "Hurr. zallu 'bowl'"),
            ("turi", ("t", "u", "r", "i"), "Hurr. vessel"),
            ("šahri", ("š", "a", "ḫ", "r", "i"), "Hurr. šaḫri 'vessel'"),
            ("amumi", ("a", "m", "u", "m", "i"), "Hurr. vessel"),
        ],
    },
    "GRAIN": {
        "semitic": [
            ("kunišu", ("k", "u", "n", "i", "š", "u"), "Akk./Nuzi kunīšu 'emmer wheat'"),
            ("barru", ("b", "a", "r", "u"), "Heb. bār, Ar. burr 'threshed grain, wheat'"),
            ("ḥiṭṭatu", ("ḥ", "i", "ṭ", "a", "t", "u"), "Ug. ḥṭt, Heb. ḥiṭṭāh 'wheat'"),
            ("šeʾu", ("š", "e", "ʾ", "u"), "Akk. šeʾu 'barley, grain'"),
            ("daganu", ("d", "a", "g", "a", "n", "u"), "Heb. dāgān, Ug. dgn 'grain'"),
        ],
        "greek": [
            ("sitos", ("s", "i", "t", "o", "s"), "Myc. si-to, Gk. σῖτος 'grain'"),
            ("kritha", ("k", "r", "i", "t", "a"), "Gk. κριθή 'barley'"),
            ("puros", ("p", "u", "r", "o", "s"), "Gk. πυρός 'wheat'"),
            ("zeia", ("z", "e", "i", "a"), "Gk. ζειά 'emmer'"),
            ("karpos", ("k", "a", "r", "p", "o", "s"), "Gk. καρπός 'produce'"),
        ],
        "anatolian": [
            ("halki", ("ḫ", "a", "l", "k", "i"), "Hitt. ḫalki- 'grain, barley'"),
            ("kant", ("k", "a", "n", "t", "a"), "Hitt. kant- 'einkorn wheat'"),
            ("zizza", ("z", "i", "z", "a"), "Hitt. zizza- 'emmer'"),
            ("šeppit", ("š", "e", "p", "i", "t"), "Hitt. šeppit- 'grain'"),
            ("ewan", ("e", "w", "a", "n"), "Hitt. ewan- 'barley'"),
        ],
        "hurrian": [
            ("kade", ("k", "a", "t", "e"), "Hurr. kade 'barley, grain'"),
            ("šari", ("š", "a", "r", "i"), "Hurr. grain"),
            ("hini", ("ḫ", "i", "n", "i"), "Hurr. grain/flour"),
            ("tali", ("t", "a", "l", "i"), "Hurr. grain/produce"),
            ("amari", ("a", "m", "a", "r", "i"), "Hurr. cereal"),
        ],
    },
    "WINE": {
        "semitic": [
            ("yaynu", ("y", "a", "y", "n", "u"), "Ug. yn, Heb. yayin 'wine'"),
            ("tirošu", ("t", "i", "r", "o", "š", "u"), "Ug. trṯ, Heb. tîrōš 'must, wine'"),
            ("ḫamru", ("ḫ", "a", "m", "r", "u"), "Ug. ḫmr, Aram. ḥamar 'wine'"),
            ("karanu", ("k", "a", "r", "a", "n", "u"), "Akk. karānu 'wine'"),
        ],
        "greek": [
            ("woinos", ("w", "o", "i", "n", "o", "s"), "Myc. wo-no, Gk. οἶνος 'wine'"),
            ("methu", ("m", "e", "t", "u"), "Gk. μέθυ 'wine'"),
            ("gleukos", ("g", "l", "e", "u", "k", "o", "s"), "Gk. γλεῦκος 'sweet wine'"),
            ("oinos", ("o", "i", "n", "o", "s"), "Gk. οἶνος 'wine'"),
        ],
        "anatolian": [
            ("wiyana", ("w", "i", "y", "a", "n", "a"), "Hitt. wiyana-, Luw. maddu-/wiyana- 'wine'"),
            ("maddu", ("m", "a", "d", "u"), "Luw. maddu- 'wine'"),
            ("marnuwan", ("m", "a", "r", "n", "u", "w", "a", "n"), "Hitt. fermented drink"),
            ("walhi", ("w", "a", "l", "ḫ", "i"), "Hitt. walḫi- 'beverage'"),
        ],
        "hurrian": [
            ("taršu", ("t", "a", "r", "š", "u"), "Hurr. beverage"),
            ("šiye", ("š", "i", "y", "e"), "Hurr. šiye 'water/drink'"),
            ("kuri", ("k", "u", "r", "i"), "Hurr. drink"),
            ("madi", ("m", "a", "t", "i"), "Hurr. drink"),
        ],
    },
}

# Calibration target: Linear B pre-linguistic anchors (meaning fixed by arithmetic/ideograms)
LINEAR_B_ANCHORS: list[tuple[str, str]] = [
    ("TO-SO", "TOTAL"),
    ("O-PE-RO", "DEFICIT"),
    ("TI-RI-PO", "VESSEL_CUP"),
    ("DI-PA", "VESSEL_CUP"),
    ("SI-TO", "GRAIN"),
    ("WO-NO", "WINE"),
]

# Linear A pre-linguistic anchors (meaning fixed by arithmetic/logograms BEFORE any Semitic reading)
# Only secure Linear B sign values used in primary mode (PA3 -> opaque in strict mode, or tested in secondary).
LINEAR_A_ANCHORS_STRICT: list[tuple[str, str]] = [
    ("KU-RO", "TOTAL"),
    ("KI-RO", "DEFICIT"),
    ("A-KA-NU", "VESSEL_CUP"),
    ("SU-PU", "VESSEL_CUP"),
    ("PA-TA-QE", "VESSEL_CUP"),
    ("KA-DI", "VESSEL_CUP"),
    ("KU-NI-SU", "GRAIN"),
    ("PA-RA", "GRAIN"),
]


def cv_distance(x: Word, y: Word) -> float:
    """Normalized CV edit distance in [0, 1] between two sign-key words.

    - Exact (series, vowel) match: 0.0
    - Same consonant series, different vowel: 0.35 (dead-vowel / vocalization shift)
    - Different consonant series, same vowel: 0.85
    - Different series & vowel: 1.0
    - Insertion/deletion: 0.75
    """
    m, n = len(x), len(y)
    if m == 0 and n == 0:
        return 0.0
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        dp[i][0] = 0.75 * i
    for j in range(1, n + 1):
        dp[0][j] = 0.75 * j
    for i in range(1, m + 1):
        xi = x[i - 1]
        for j in range(1, n + 1):
            yj = y[j - 1]
            if xi == yj:
                sub = 0.0
            elif isinstance(xi, tuple) and isinstance(yj, tuple):
                if xi[0] == yj[0]:
                    sub = 0.35
                elif xi[1] == yj[1]:
                    sub = 0.85
                else:
                    sub = 1.0
            else:
                sub = 1.0
            dp[i][j] = min(dp[i - 1][j] + 0.75, dp[i][j - 1] + 0.75, dp[i - 1][j - 1] + sub)
    return dp[m][n] / max(m, n)


def spell_synsets(tables: r.Tables, signs: set) -> dict[str, dict[str, list[tuple[str, list[Word]]]]]:
    """Forward-spell every bounded synset entry under both omission and plene + glide rule."""
    spelled: dict[str, dict[str, list[tuple[str, list[Word]]]]] = {}
    for concept, by_lang in SYNSETS.items():
        spelled[concept] = {}
        for lang, entries in by_lang.items():
            arm_key = "luwian" if lang == "anatolian" else lang
            items = []
            for label, segs, _ in entries:
                forms: list[Word] = []
                for conv in r.CONVENTIONS:
                    w = r.word(segs, arm_key, tables, conv)
                    if w:
                        w = glide(w, signs)
                        if w not in forms:
                            forms.append(w)
                if forms:
                    items.append((label, forms))
            spelled[concept][lang] = items
    return spelled


def score_anchors(
    anchor_words: list[tuple[Word, str]],
    spelled: dict,
    lang: str,
    beta: float = 6.0,
) -> tuple[float, list[dict]]:
    """Bayesian marginal log-likelihood over bounded synsets (log-mean-exp penalizes extra synonyms)."""
    total_ll = 0.0
    details = []
    for w, concept in anchor_words:
        entries = spelled[concept][lang]
        dists = []
        best_label, best_d = "", 1.0
        for label, forms in entries:
            d = min(cv_distance(w, f) for f in forms)
            dists.append(d)
            if d < best_d:
                best_d, best_label = d, label
        # Log-mean-exp marginal likelihood
        max_neg = max(-beta * d for d in dists)
        lme = max_neg + math.log(sum(math.exp(-beta * d - max_neg) for d in dists) / len(dists))
        total_ll += lme
        details.append({"concept": concept, "best_match": best_label, "best_dist": round(best_d, 3), "ll": round(lme, 3)})
    return total_ll, details


def permute_word(w: Word, mapping: dict[str, str]) -> Word:
    return tuple((mapping.get(k[0], k[0]), k[1]) if isinstance(k, tuple) else k for k in w)


def run_battery(
    anchors: list[tuple[str, str]],
    tables: r.Tables,
    sign_table: dict,
    signs: set,
    n_perm: int = 10000,
    seed: int = 20261122,
    beta: float = 6.0,
) -> dict:
    spelled = spell_synsets(tables, signs)
    parsed = [(a.keys(form, sign_table), concept) for form, concept in anchors]
    langs = ("semitic", "greek", "anatolian", "hurrian")

    observed = {}
    details = {}
    for lang in langs:
        ll, det = score_anchors(parsed, spelled, lang, beta=beta)
        observed[lang] = ll
        details[lang] = det

    # 10,000 random consonant-series grid permutations (vowels fixed)
    rng = random.Random(seed)
    perm_scores = {lang: [] for lang in langs}
    ge_counts = {lang: 0 for lang in langs}
    for _ in range(n_perm):
        shuf = list(CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(CONSONANT_SERIES, shuf))
        p_anchors = [(permute_word(w, mp), c) for w, c in parsed]
        for lang in langs:
            ll, _ = score_anchors(p_anchors, spelled, lang, beta=beta)
            perm_scores[lang].append(ll)
            if ll >= observed[lang] - 1e-12:
                ge_counts[lang] += 1

    summary = {}
    for lang in langs:
        arr = perm_scores[lang]
        mean = sum(arr) / len(arr)
        var = sum((x - mean) ** 2 for x in arr) / len(arr)
        sd = math.sqrt(var) if var > 0 else 1e-9
        z = (observed[lang] - mean) / sd
        p = (1 + ge_counts[lang]) / (n_perm + 1)
        summary[lang] = {
            "ll": round(observed[lang], 4),
            "perm_mean": round(mean, 4),
            "perm_sd": round(sd, 4),
            "z_perm": round(z, 3),
            "p_perm": round(p, 5),
            "details": details[lang],
        }
    winner = max(langs, key=lambda l: summary[l]["z_perm"])
    return {"winner": winner, "n_perm": n_perm, "seed": seed, "beta": beta, "languages": summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true", help="Run calibration gate on Linear B anchors only")
    ap.add_argument("--run-linear-a", action="store_true", help="Run on Linear A anchors (requires SIGNATURE.txt)")
    ap.add_argument("--n-perm", type=int, default=10000)
    args = ap.parse_args()

    tables = r.load_tables()
    sign_table = a.load_signs()
    signs = {k for k in sign_table.values() if isinstance(k, tuple)}

    cal = run_battery(LINEAR_B_ANCHORS, tables, sign_table, signs, n_perm=args.n_perm)
    runner_up_ll = max(cal["languages"][l]["ll"] for l in ("semitic", "anatolian", "hurrian"))
    runner_up_z = max(cal["languages"][l]["z_perm"] for l in ("semitic", "anatolian", "hurrian"))
    ll_margin = cal["languages"]["greek"]["ll"] - runner_up_ll
    z_margin = cal["languages"]["greek"]["z_perm"] - runner_up_z
    cal_pass = (
        cal["winner"] == "greek"
        and cal["languages"]["greek"]["p_perm"] <= 0.001
        and ll_margin >= 5.0
        and z_margin >= 2.0
    )
    print(
        f"=== Kernel D Calibration (Linear B Anchors, B={args.n_perm}) "
        f"| PASS={cal_pass} | dLL={ll_margin:+.2f} | dZ={z_margin:+.2f} ==="
    )
    for lang, s in cal["languages"].items():
        print(f"  {lang:10s} | LL={s['ll']:8.3f} | Z_perm={s['z_perm']:+6.2f} | p_perm={s['p_perm']:.5f}")

    if args.run_linear_a:
        if not SIGNATURE.is_file():
            print("REFUSED: SIGNATURE.txt not found beside pre-registration.", file=sys.stderr)
            return 2
        if not cal_pass:
            print("REFUSED: Calibration gate failed.", file=sys.stderr)
            return 3
        la = run_battery(LINEAR_A_ANCHORS_STRICT, tables, sign_table, signs, n_perm=args.n_perm)
        print(f"\n=== Kernel D Target (Linear A Strict Anchors, B={args.n_perm}) | winner={la['winner']} ===")
        for lang, s in la["languages"].items():
            print(f"  {lang:10s} | LL={s['ll']:8.3f} | Z_perm={s['z_perm']:+6.2f} | p_perm={s['p_perm']:.5f}")
    return 0 if cal_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
