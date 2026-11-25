"""Kernel J: Zero-Curation Automated Dictionary Audit of Pre-Linguistic Anchors.

Eliminates researcher degrees of freedom in synset curation by extracting EVERY matching
headword automatically from independent open JSONL dictionaries (Akkadian, Ugaritic,
Hebrew, Greek LSJ, Anatolian, Hurrian, Egyptian) using fixed English concept regexes on
the `meaning` field alone—zero hand-picked words, zero project-lexicon inputs.

Scores each language by marginal log-likelihood over all auto-extracted candidates
(naturally penalizing bloated synsets via 1/|C|), calibrated on Linear B (must identify
Greek and reject Semitic) and tested against 5,000–10,000 consonant-series grid permutations.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402
import lid              # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
CONTACT_DIR = Path(
    os.environ.get("KAPHTOR_CONTACT_DIR", str(HERE.parents[1] / "data/contact"))
)
LSJ_GLOSSES = Path(
    os.environ.get("KAPHTOR_LSJ_GLOSSES_JSONL", str(HERE.parents[1] / "data/share-alike/greek/lsj_glosses.jsonl"))
)
SUMERIAN_LEX = Path(
    os.environ.get(
        "KAPHTOR_SUMERIAN_LEXICON_JSONL",
        str(HERE.parents[1] / "data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl"),
    )
)
CONSONANT_SERIES = ("D", "J", "K", "M", "N", "P", "Q", "R", "S", "T", "W", "Z")
Word = tuple[tuple[str, str], ...]

# Pure English (+ German for TLA Egyptian) concept regexes applied identically to every dictionary's `meaning` field.
CONCEPT_PATTERNS: dict[str, re.Pattern] = {
    "TOTAL": re.compile(r"\b(total|all|whole|entirety|sum|altogether|so much|so many|gesamt|summe|alle)\b", re.I),
    "DEFICIT": re.compile(r"\b(deficit|owe|debt|missing|shortfall|lack|lacking|finished|complete|end|schuld|mangel|fehlbetrag)\b", re.I),
    "BOWL": re.compile(r"\b(bowl|basin|dish|cup|goblet|chalice|schale|becken|becher|napf)\b", re.I),
    "JAR": re.compile(r"\b(jar|pitcher|amphora|jug|flask|vessel|pot|urn|krug|gefäß|topf|flasche)\b", re.I),
    "WHEAT": re.compile(r"\b(wheat|emmer|grain|barley|corn|cereal|spelt|weizen|gerste|getreide|korn)\b", re.I),
    "TRIPOD": re.compile(r"\b(tripod|three-footed|cauldron|dreifuß|kessel)\b", re.I),
    "SWORD": re.compile(r"\b(sword|dagger|blade|schwert|dolch|klinge)\b", re.I),
    "WOOL": re.compile(r"\b(wool|fleece|cloth|linen|garment|textile|fabric|weave|wolle|tuch|leinen|gewand)\b", re.I),
    "OIL": re.compile(r"\b(oil|olive|fat|unguent|salve|grease|anoint|öl|salbe|fett)\b", re.I),
    "WINE": re.compile(r"\b(wine|must|vineyard|grape|raisin|vine|wein|most|traube)\b", re.I),
}

# Zero-curation commodity-qualifier regexes for Kernel F ligature acrophony audit
LIGATURE_PATTERNS: dict[str, re.Pattern] = {
    "OIL": re.compile(r"\b(oil|olive|anoint|anointing|unguent|salve|fragrant|aromatic|scented|sage|rose|honey|libation|good|fine|pure|öl|salböl)\b", re.I),
    "GRAIN": re.compile(r"\b(grain|wheat|emmer|barley|flour|seed|meal|cereal|spelt|threshed|weizen|gerste|getreide|mehl)\b", re.I),
    "WINE": re.compile(r"\b(wine|must|spiced|fermented|sweet|vintage|wein|most)\b", re.I),
    "TEXTILE": re.compile(r"\b(cloth|linen|garment|wool|fabric|textile|tunic|robe|woven|folded|tuch|leinen|gewand|wolle)\b", re.I),
}

LB_LIGATURES: list[tuple[str, str]] = [
    ("PA", "OIL"), ("WE", "OIL"), ("A", "OIL"),
    ("PE", "GRAIN"), ("TE", "TEXTILE"), ("PU", "TEXTILE"),
]

LA_LIGATURES: list[tuple[str, str]] = [
    ("KU", "GRAIN"), ("PA", "GRAIN"), ("QE", "GRAIN"),
    ("KI", "OIL"), ("MI", "OIL"), ("DI", "OIL"), ("TA", "OIL"), ("NE", "OIL"), ("RI", "OIL"),
    ("RA", "WINE"),
]

# Linear B calibration anchors (strictly pre-linguistic meanings)
LB_ANCHORS: list[tuple[str, str]] = [
    ("TO-SO", "TOTAL"),
    ("O-PE-RO", "DEFICIT"),
    ("TI-RI-PO", "TRIPOD"),
    ("A-PI-PO-RE-WE", "JAR"),
    ("PA-KA-NA", "SWORD"),
    ("SI-TO", "WHEAT"),
]

# Expanded Linear B calibration anchors (n=9: adds DI-PA, WO-NO, E-RA-WO)
LB_ANCHORS_EXT9: list[tuple[str, str]] = LB_ANCHORS + [
    ("DI-PA", "BOWL"),
    ("WO-NO", "WINE"),
    ("E-RA-WO", "OIL"),
]

# Linear A pre-linguistic anchors (signed baseline n=8: 6 shared with Kernel D plus PO-TO-KU-RO and KA-PA)
LA_ANCHORS: list[tuple[str, str]] = [
    ("KU-RO", "TOTAL"),
    ("KI-RO", "DEFICIT"),
    ("PO-TO-KU-RO", "TOTAL"),
    ("A-KA-NU", "BOWL"),
    ("KA-PA", "BOWL"),
    ("SU-PU", "JAR"),
    ("KA-DI", "JAR"),
    ("KU-NI-SU", "WHEAT"),
]

# Deduplicated baseline (n=7: drops PO-TO-KU-RO so KU-RO is never double-counted)
LA_DEDUP_7: list[tuple[str, str]] = [x for x in LA_ANCHORS if x[0] != "PO-TO-KU-RO"]

# Tier 1a — Purest strict-LB pictographic + arithmetic inventory (n=9, deduplicated):
# 100% strict signs-a5-proposed.json (zero PA3 folding, zero PA-RA header inference, zero MA+RU monogram);
# adds PA-TA-QE (HT 31 *402-VS drawing) and DA-RO-PA (HT 38 *403-VS drawing, UNTRANSLATED blind inclusion).
LA_DEDUP_9: list[tuple[str, str]] = LA_DEDUP_7 + [
    ("PA-TA-QE", "BOWL"),
    ("DA-RO-PA", "JAR"),
]

# Tier 1b — Strict-LB extended with Kernel D's PA-RA (HT 128a header) & MA+RU (A558/LANA wool monogram) (n=11):
# Note: MA+RU is a ligatured wool monogram (distinct from HT 117a syllabic PN MA-RU), and PA-RA is a tablet
# heading above GRA entries rather than a ligature; all four additions are K-series-free.
LA_DEDUP_11: list[tuple[str, str]] = LA_DEDUP_9 + [
    ("PA-RA", "WHEAT"),
    ("MA-RU", "WOOL"),
]

# Tier 2a — Full HT 31 + HT 38 literal vessel drawings + arithmetic + KU-NI-SU (n=12, deduplicated):
# Sensitivity tier folding GORILA doublet AB 56 (PA3 -> PA, kept opaque in signs-a5-proposed.json §15 ruling 3)
# on HT 31's three literal vessel drawings (QA-PA3, KA-RO-PA3, SU-PA3-RA); excludes PA-RA & MA+RU.
LA_DEDUP_12: list[tuple[str, str]] = LA_DEDUP_9 + [
    ("QA-PA₃", "BOWL"),
    ("KA-RO-PA₃", "JAR"),
    ("SU-PA₃-RA", "BOWL"),
]

# Tier 2b — Full extended sensitivity tier (n=14: Tier 1b + HT 31 PA3 doublet vessel drawings).
LA_DEDUP_14: list[tuple[str, str]] = LA_DEDUP_11 + [
    ("QA-PA₃", "BOWL"),
    ("KA-RO-PA₃", "JAR"),
    ("SU-PA₃-RA", "BOWL"),
]

# Strictly K-series-free subset of Tier 1b (n=5: tests consonant-grid p_perm survival without K-series signs)
LA_DROPK_5: list[tuple[str, str]] = [
    ("SU-PU", "JAR"),
    ("PA-TA-QE", "BOWL"),
    ("DA-RO-PA", "JAR"),
    ("PA-RA", "WHEAT"),
    ("MA-RU", "WOOL"),
]


def _normalize_doublet(word: str) -> str:
    """Fold GORILA doublet AB 56 (PA3 -> PA) for Tier 2 sensitivity runs only (opaque in signs-a5-proposed.json)."""
    return word.replace("₃", "")


def _vocalize_egyptian(raw: str) -> list[str] | None:
    """Map consonantal Middle Egyptian transliteration into CV segments via neutral schwa insertion."""
    s = raw.lower().strip()
    if not s or len(s) < 2:
        return None
    segs: list[str] = []
    for ch in s:
        if ch in ("a", "e", "i", "o", "u"):
            segs.append(ch)
        elif ch in ("ꜣ", "3", "ꜥ", "ʾ", "ʿ"):
            segs.append("a")
        elif ch in ("ỉ", "j", "y"):
            segs.append("i")
        elif ch == "w":
            segs.append("u")
        elif ch.isalpha():
            if segs and segs[-1] not in ("a", "e", "i", "o", "u"):
                segs.append("a")
            segs.append(ch)
    if segs and segs[-1] not in ("a", "e", "i", "o", "u"):
        segs.append("a")
    return segs if len(segs) >= 2 else None


def _word_to_cv_keys(
    rec: dict,
    lang: str,
    tables: r.Tables,
    signs: set,
) -> Word | None:
    """Render a dictionary headword to CV sign keys using only its dictionary form."""
    if lang == "greek":
        lb_key = rec.get("lb_key")
        if lb_key:
            w = lid.lsj_keys(lb_key)
            if w and len(w) >= 2:
                return w
        norm = rec.get("normalized") or ""
        segs = lid.norm_segments(norm)
    elif lang == "egyptian":
        raw = rec.get("transliteration_unicode") or rec.get("normalized") or ""
        raw = re.split(r"[,;/(\s.]+", str(raw).strip())[0]
        segs = _vocalize_egyptian(raw)
    else:
        raw = rec.get("vocalization") or rec.get("normalized") or rec.get("form_original") or ""
        # Strip parenthetical notes, keep primary single word
        raw = re.split(r"[,;/(\s]+", str(raw).strip())[0]
        segs = lid.norm_segments(raw)

    if not segs or len(segs) < 2:
        return None
    arm_key = "luwian" if lang == "anatolian" else lang
    w = r.word(segs, arm_key, tables, "omission") or r.word(segs, arm_key, tables, "plene")
    if not w or len(w) < 2:
        return None
    if not all(k in signs for k in w):
        return None
    return tuple(w)


def _gloss_specificity(meaning: str, pat: re.Pattern) -> tuple[int, int]:
    """Rank shorter/more direct glosses first when capping synsets (purely length-based, language-blind)."""
    m = pat.search(meaning)
    pos = m.start() if m else 9999
    return (pos, len(meaning))


def extract_auto_synsets(
    tables: r.Tables,
    signs: set,
    max_per_concept: int | None = 40,
    patterns: dict[str, re.Pattern] | None = None,
    acrophone_only: bool = False,
) -> tuple[dict[str, dict[str, list[Word]]], dict[str, dict[str, int]]]:
    """Automatically extract concept synsets from independent JSONL lexica with zero human selection."""
    pats = patterns or CONCEPT_PATTERNS
    greek_path = CONTACT_DIR / "greek_lexicon.jsonl"
    if not greek_path.is_file():
        greek_path = LSJ_GLOSSES
    sources: dict[str, list[Path]] = {
        "semitic": [
            CONTACT_DIR / "akkadian_lexicon.jsonl",
            CONTACT_DIR / "ugaritic_lexicon.jsonl",
            CONTACT_DIR / "hebrew_lexicon.jsonl",
        ],
        "greek": [greek_path],
        "sumerian": [SUMERIAN_LEX],
        "anatolian": [CONTACT_DIR / "anatolian_lexicon.jsonl"],
        "hurrian": [CONTACT_DIR / "hurrian_lexicon.jsonl"],
        "egyptian": [CONTACT_DIR / "egyptian_lexicon.jsonl"],
    }
    # Keep only languages that have at least one present lexicon file
    active_sources = {
        lang: [p for p in paths if p.is_file()]
        for lang, paths in sources.items()
    }
    active_sources = {lang: paths for lang, paths in active_sources.items() if paths}

    # Collect (specificity_key, cv_word) per (concept, lang)
    raw_hits: dict[str, dict[str, dict[Word, tuple[int, int]]]] = {
        c: {l: {} for l in active_sources} for c in pats
    }

    for lang, paths in active_sources.items():
        for p in paths:
            with p.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    meaning = str(rec.get("meaning") or "")
                    if not meaning:
                        continue
                    matched_concepts = [c for c, pat in pats.items() if pat.search(meaning)]
                    if not matched_concepts:
                        continue
                    w = _word_to_cv_keys(rec, lang, tables, signs)
                    if not w:
                        continue
                    key_w: Word = (w[0],) if acrophone_only else w
                    for c in matched_concepts:
                        spec = _gloss_specificity(meaning, pats[c])
                        prev = raw_hits[c][lang].get(key_w)
                        if prev is None or spec < prev:
                            raw_hits[c][lang][key_w] = spec

    synsets: dict[str, dict[str, list[Word]]] = {}
    counts: dict[str, dict[str, int]] = {}
    for c in pats:
        synsets[c] = {}
        counts[c] = {}
        for lang in active_sources:
            ordered = sorted(raw_hits[c][lang].items(), key=lambda kv: (kv[1], kv[0]))
            words = [w for w, _ in ordered]
            counts[c][lang] = len(words)
            if max_per_concept is not None:
                words = words[:max_per_concept]
            synsets[c][lang] = words
    return synsets, counts


def _score_one_anchor(w: Word, cands: list[Word], beta: float = 6.0) -> float:
    if not cands:
        return -beta
    dists = [ad.cv_distance(w, c) for c in cands]
    mx = max(-beta * d for d in dists)
    return mx + math.log(sum(math.exp(-beta * d - mx) for d in dists) / len(dists))


def score_anchors(
    anchors: list[tuple[Word, str]],
    synsets: dict[str, dict[str, list[Word]]],
    lang: str,
    beta: float = 6.0,
) -> float:
    return sum(_score_one_anchor(w, synsets[concept][lang], beta=beta) for w, concept in anchors)


def exact_concept_shuffle(
    parsed: list[tuple[Word, str]],
    synsets: dict[str, dict[str, list[Word]]],
    lang: str,
    beta: float = 6.0,
    n_mc: int = 10000,
    seed: int = 20261123,
) -> dict:
    """Permutation test over assignments of concept labels to anchor words.

    Tests semantic specificity independently of consonant-grid permutations: keeps real sign
    values fixed and shuffles which concept (TOTAL, DEFICIT, BOWL, JAR, WHEAT, WOOL, ...) maps
    to which word. Enumerates all distinct labelings exactly when len(parsed) <= 8; uses
    deterministic Monte Carlo (n_mc draws) when len(parsed) > 8. Skips subsets with < 12
    distinct labelings (e.g., ARITH_2 where 2! = 2).
    """
    concepts = [c for _, c in parsed]
    uniq_c = sorted(set(concepts))
    if len(uniq_c) < 2:
        return {"n_concept_perms": 1, "concept_null_mean": None, "concept_null_sd": None, "z_concept": None, "p_concept": None}

    # Pre-compute score matrix M[word_idx][concept]
    mat = [
        {c: _score_one_anchor(w, synsets[c][lang], beta=beta) for c in uniq_c}
        for w, _ in parsed
    ]
    obs = sum(mat[i][concepts[i]] for i in range(len(parsed)))

    if len(parsed) <= 8:
        distinct_perms = sorted(set(itertools.permutations(concepts)))
        n_cp = len(distinct_perms)
        if n_cp < 12:
            return {"n_concept_perms": n_cp, "concept_null_mean": None, "concept_null_sd": None, "z_concept": None, "p_concept": None}
        nulls = [sum(mat[i][perm[i]] for i in range(len(parsed))) for perm in distinct_perms]
        mu = sum(nulls) / n_cp
        sd = math.sqrt(sum((x - mu) ** 2 for x in nulls) / n_cp)
        z = (obs - mu) / sd if sd > 0 else 0.0
        ge = sum(1 for x in nulls if x >= obs - 1e-12)
        p = ge / n_cp
        return {
            "n_concept_perms": n_cp,
            "concept_null_mean": round(mu, 4),
            "concept_null_sd": round(sd, 4),
            "z_concept": round(z, 3),
            "p_concept": round(p, 5),
        }

    rng = random.Random(seed)
    buf = list(concepts)
    nulls = []
    for _ in range(n_mc):
        rng.shuffle(buf)
        nulls.append(sum(mat[i][buf[i]] for i in range(len(parsed))))
    mu = sum(nulls) / n_mc
    sd = math.sqrt(sum((x - mu) ** 2 for x in nulls) / n_mc)
    z = (obs - mu) / sd if sd > 0 else 0.0
    ge = sum(1 for x in nulls if x >= obs - 1e-12)
    p = (ge + 1) / (n_mc + 1)
    return {
        "n_concept_perms": n_mc,
        "concept_null_mean": round(mu, 4),
        "concept_null_sd": round(sd, 4),
        "z_concept": round(z, 3),
        "p_concept": round(p, 5),
    }


def run_battery(
    raw_anchors: list[tuple[str, str]],
    synsets: dict[str, dict[str, list[Word]]],
    sign_table: dict,
    n_perm: int = 5000,
    seed: int = 20261123,
    beta: float = 6.0,
) -> dict:
    parsed = [(tuple(a.keys(_normalize_doublet(w), sign_table)), c) for w, c in raw_anchors]
    first_c = next(iter(synsets))
    langs = tuple(
        l for l in ("semitic", "greek", "sumerian", "anatolian", "hurrian", "egyptian")
        if l in synsets[first_c]
    )
    rng = random.Random(seed)
    perms: list[dict[str, str]] = []
    for _ in range(n_perm):
        shuf = list(CONSONANT_SERIES)
        rng.shuffle(shuf)
        perms.append(dict(zip(CONSONANT_SERIES, shuf)))

    def _perm_word(w: Word, pm: dict[str, str]) -> Word:
        return tuple((pm.get(c, c), v) for c, v in w)

    res: dict[str, dict] = {}
    for lang in langs:
        obs = score_anchors(parsed, synsets, lang, beta=beta)
        nulls = [
            score_anchors([(_perm_word(w, pm), c) for w, c in parsed], synsets, lang, beta=beta)
            for pm in perms
        ]
        mu = sum(nulls) / len(nulls)
        sd = math.sqrt(sum((x - mu) ** 2 for x in nulls) / len(nulls))
        z = (obs - mu) / sd if sd > 0 else 0.0
        ge = sum(1 for x in nulls if x >= obs - 1e-12)
        p = (ge + 1) / (n_perm + 1)
        c_res = exact_concept_shuffle(parsed, synsets, lang, beta=beta, n_mc=max(n_perm, 10000), seed=seed)
        res[lang] = {
            "ll": round(obs, 4),
            "null_mean": round(mu, 4),
            "null_sd": round(sd, 4),
            "z_perm": round(z, 3),
            "p_perm": round(p, 5),
            **c_res,
        }
    ranked = sorted(res.items(), key=lambda kv: -kv[1]["ll"])
    return {
        "n_anchors": len(raw_anchors),
        "winner": ranked[0][0],
        "runner_up": ranked[1][0],
        "delta_ll": round(ranked[0][1]["ll"] - ranked[1][1]["ll"], 4),
        "languages": res,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Kernel J: Zero-Curation Automated Dictionary Audit.")
    ap.add_argument("--cap", type=int, default=40, help="Max auto-extracted candidates per concept/lang (0=uncapped)")
    ap.add_argument("--n-perm", type=int, default=5000)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--ligatures", action="store_true", help="Run zero-curation audit on Kernel F commodity ligatures")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tables, signs = r.load_tables(), lid.sign_keys()
    sign_table = a.load_signs()
    cap = None if args.cap <= 0 else args.cap

    if args.ligatures:
        lig_syn, lig_counts = extract_auto_synsets(
            tables, signs, max_per_concept=cap, patterns=LIGATURE_PATTERNS, acrophone_only=True
        )
        cal_lb = run_battery(LB_LIGATURES, lig_syn, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out_l: dict = {
            "mode": "ligatures",
            "cap": cap,
            "beta": args.beta,
            "n_perm": args.n_perm,
            "synset_raw_counts": lig_counts,
            "calibration_linear_b": cal_lb,
        }
        if SIGNATURE.exists():
            out_l["linear_a_ligatures"] = run_battery(
                LA_LIGATURES, lig_syn, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta
            )
        if args.json:
            print(json.dumps(out_l, indent=2))
            return 0
        print(f"=== Kernel J (--ligatures): Zero-Curation Ligature Audit (cap={cap}, n_perm={args.n_perm}) ===")
        for c, by_l in lig_counts.items():
            print(f"  {c:<8} " + "  ".join(f"{l}={n}" for l, n in by_l.items()))
        for label in ("calibration_linear_b", "linear_a_ligatures"):
            if label not in out_l:
                continue
            b = out_l[label]
            print(f"\n--- {label} (n={b['n_anchors']}, winner={b['winner']}, ΔLL={b['delta_ll']:+.3f}) ---")
            for l, d in sorted(b["languages"].items(), key=lambda kv: -kv[1]["ll"]):
                c_str = (
                    f"  Z_concept={d['z_concept']:+6.2f} p_concept={d['p_concept']:.5f} (n={d['n_concept_perms']})"
                    if d["p_concept"] is not None
                    else ""
                )
                print(f"  {l:<12} LL={d['ll']:+8.3f}  null={d['null_mean']:+8.3f}±{d['null_sd']:.3f}  Z={d['z_perm']:+6.2f}  p={d['p_perm']:.5f}{c_str}")
        return 0

    synsets, counts = extract_auto_synsets(tables, signs, max_per_concept=cap)

    cal_lb = run_battery(LB_ANCHORS, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
    cal_lb_ext9 = run_battery(LB_ANCHORS_EXT9, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
    out: dict = {
        "cap": cap,
        "beta": args.beta,
        "n_perm": args.n_perm,
        "seed": args.seed,
        "synset_raw_counts": counts,
        "calibration_linear_b": cal_lb,
        "calibration_linear_b_ext9": cal_lb_ext9,
    }
    if SIGNATURE.exists():
        out["linear_a_full_8"] = run_battery(LA_ANCHORS, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dedup_7"] = run_battery(LA_DEDUP_7, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dedup_9"] = run_battery(LA_DEDUP_9, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dedup_12"] = run_battery(LA_DEDUP_12, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dedup_11"] = run_battery(LA_DEDUP_11, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dedup_14"] = run_battery(LA_DEDUP_14, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        out["linear_a_dropk_5"] = run_battery(LA_DROPK_5, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        no_loans = [x for x in LA_ANCHORS if x[0] not in ("A-KA-NU", "KU-NI-SU", "KA-DI")]
        out["linear_a_no_loans_5"] = run_battery(no_loans, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)
        arith = [x for x in LA_ANCHORS if x[0] in ("KU-RO", "KI-RO")]
        out["linear_a_arith_2"] = run_battery(arith, synsets, sign_table, n_perm=args.n_perm, seed=args.seed, beta=args.beta)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"=== Kernel J: Zero-Curation Automated Dictionary Audit (cap={cap}, beta={args.beta}, n_perm={args.n_perm}) ===")
    print("Raw auto-extracted candidate counts per concept:")
    for c, by_l in counts.items():
        print(f"  {c:<8} " + "  ".join(f"{l}={n}" for l, n in by_l.items()))
    for label in (
        "calibration_linear_b",
        "calibration_linear_b_ext9",
        "linear_a_full_8",
        "linear_a_dedup_7",
        "linear_a_dedup_9",
        "linear_a_dedup_12",
        "linear_a_dedup_11",
        "linear_a_dedup_14",
        "linear_a_dropk_5",
        "linear_a_no_loans_5",
        "linear_a_arith_2",
    ):
        if label not in out:
            continue
        b = out[label]
        print(f"\n--- {label} (n={b['n_anchors']}, winner={b['winner']}, ΔLL={b['delta_ll']:+.3f}) ---")
        for l, d in sorted(b["languages"].items(), key=lambda kv: -kv[1]["ll"]):
            c_str = (
                f"  Z_concept={d['z_concept']:+6.2f} p_concept={d['p_concept']:.5f} (n={d['n_concept_perms']})"
                if d["p_concept"] is not None
                else ""
            )
            print(f"  {l:<12} LL={d['ll']:+8.3f}  null={d['null_mean']:+8.3f}±{d['null_sd']:.3f}  Z={d['z_perm']:+6.2f}  p={d['p_perm']:.5f}{c_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
