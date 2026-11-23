"""Kernel C: Corpus-Derived Liturgical Lexical Cohesion (KERNEL-SPECS.md §4).

Mechanically builds size-locked (exact top-K, default K=300) liturgical/cultic CV vocabularies for
Hebrew (OSHB Psalms/Leviticus vs. narrative prose via Dirichlet log-odds), Syriac (Ephrem hymns),
Anatolian (TLHdig), Hurrian (TLHdig/eCUT), Akkadian (ORACC), and Greek (Diodorus) strictly from the
`train` split (excluding any chapter present in calibration controls).

Scores any prayer inscription (controls or, once signed and gated, IO Za 2) under strict Linear B
sign values against each size-locked top-K set AND against B random consonant-series permutations of
the Linear B grid.

Linear A mode (--run-linear-a) is refused unless SIGNATURE.txt exists and calibration passes.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402
import lid              # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
CONTROLS_V3 = Path(
    os.environ.get(
        "KAPHTOR_CONTROLS_V3",
        str(HERE.parents[1] / "ioza2-adjudication/protocol-d/controls/controls_v3.jsonl"),
    )
)
Word = tuple[tuple[str, str], ...]

HEB_LIT_BOOKS = ("Ps", "Lev", "Lam", "Joel", "Hab", "Song")
HEB_PROSE_BOOKS = ("Gen", "Exod", "Josh", "Judg", "1Sam", "2Sam", "1Kgs", "2Kgs", "Esth", "Ruth")

# IO Za 2 under strict Linear B values (*301 stays opaque)
IO_ZA_2_STRICT = [
    "A-TA-I-*301-WA-JA",
    "JA-DI-KI-TU",
    "JA-SA-SA-RA-ME",
    "U-NA-KA-NA-SI",
    "I-PI-NA-MA",
    "SI-RU-TE",
    "TA-NA-RA-TE-U-TI-NU",
]


def dirichlet_log_odds(
    fg_counts: collections.Counter,
    bg_counts: collections.Counter,
    alpha: float = 0.05,
) -> dict[Word, float]:
    """Monroe et al. (2008) informative Dirichlet log-odds z-score for fg vs. bg."""
    vocab = set(fg_counts) | set(bg_counts)
    n_fg = sum(fg_counts.values())
    n_bg = sum(bg_counts.values())
    a0 = alpha * len(vocab)
    scores: dict[Word, float] = {}
    for w in vocab:
        c1 = fg_counts.get(w, 0)
        c2 = bg_counts.get(w, 0)
        if c1 < 2:
            continue
        p1 = (c1 + alpha) / (n_fg + a0 - c1 - alpha)
        p2 = (c2 + alpha) / (n_bg + a0 - c2 - alpha)
        delta = math.log(p1) - math.log(p2)
        var = 1.0 / (c1 + alpha) + 1.0 / (c2 + alpha)
        scores[w] = delta / math.sqrt(var)
    return scores


def _bucket_vocab(vocab: list[Word]) -> dict[int, list[Word]]:
    buckets: dict[int, list[Word]] = collections.defaultdict(list)
    for v in vocab:
        buckets[len(v)].append(v)
    return dict(buckets)


def word_match_cost(
    w: Word,
    vocab: list[Word],
    max_strip_pre: int = 1,
    max_strip_suf: int = 1,
    strip_penalty: float = 0.10,
    tau: float = 0.35,
    buckets: dict[int, list[Word]] | None = None,
    vocab_set: set[Word] | None = None,
    dist_cache: dict[tuple[Word, Word], float] | None = None,
) -> float:
    """Minimum CV alignment cost of `w` (or affix-stripped stem of len >= 2) against `vocab`."""
    candidates: list[tuple[Word, float]] = [(w, 0.0)]
    n = len(w)
    for pre in range(max_strip_pre + 1):
        for suf in range(max_strip_suf + 1):
            if pre == 0 and suf == 0:
                continue
            if n - pre - suf >= 2:
                candidates.append((w[pre : n - suf], strip_penalty * (pre + suf)))
    best = tau  # anything >= tau contributes 0 to score_prayer
    if vocab_set is None:
        vocab_set = set(vocab)
    # Exact-match fast path
    for cand, pen in candidates:
        if pen < best and cand in vocab_set:
            best = pen
            if best <= 1e-9:
                return 0.0
    if buckets is None:
        buckets = _bucket_vocab(vocab)
    for cand, pen in candidates:
        if pen >= best:
            continue
        clen = len(cand)
        for vlen, vlist in buckets.items():
            if abs(clen - vlen) * 0.75 / max(clen, vlen) + pen >= best:
                continue
            for v in vlist:
                if dist_cache is not None:
                    key = (cand, v)
                    d0 = dist_cache.get(key)
                    if d0 is None:
                        d0 = ad.cv_distance(cand, v)
                        dist_cache[key] = d0
                else:
                    d0 = ad.cv_distance(cand, v)
                d = d0 + pen
                if d < best:
                    best = d
                    if best <= 1e-9:
                        return 0.0
    return min(best, 1.0)


def score_prayer(
    words: list[Word],
    vocab: list[Word],
    tau: float = 0.35,
    max_strip_pre: int = 1,
    max_strip_suf: int = 1,
    buckets: dict[int, list[Word]] | None = None,
    vocab_set: set[Word] | None = None,
    dist_cache: dict[tuple[Word, Word], float] | None = None,
) -> float:
    """Mean liturgical cohesion score in [0, 1] over undamaged words in a prayer."""
    usable = [w for w in words if len(w) >= 2]
    if not usable:
        return 0.0
    if buckets is None:
        buckets = _bucket_vocab(vocab)
    if vocab_set is None:
        vocab_set = set(vocab)
    total = 0.0
    for w in usable:
        c = word_match_cost(
            w,
            vocab,
            max_strip_pre=max_strip_pre,
            max_strip_suf=max_strip_suf,
            tau=tau,
            buckets=buckets,
            vocab_set=vocab_set,
            dist_cache=dist_cache,
        )
        if c < tau:
            total += 1.0 - c / tau
    return total / len(usable)


def perm_z_score(
    words: list[Word],
    vocab: list[Word],
    n_perm: int = 500,
    seed: int = 20261122,
    tau: float = 0.35,
) -> dict:
    """Score `words` against `vocab` and `n_perm` consonant-series grid permutations."""
    buckets = _bucket_vocab(vocab)
    vocab_set = set(vocab)
    dist_cache: dict[tuple[Word, Word], float] = {}
    obs = score_prayer(words, vocab, tau=tau, buckets=buckets, vocab_set=vocab_set, dist_cache=dist_cache)
    rng = random.Random(seed)
    vals = []
    ge = 0
    for _ in range(n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        pw = [ad.permute_word(w, mp) for w in words]
        s = score_prayer(pw, vocab, tau=tau, buckets=buckets, vocab_set=vocab_set, dist_cache=dist_cache)
        vals.append(s)
        if s >= obs - 1e-12:
            ge += 1
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    sd = math.sqrt(var) if var > 1e-12 else 1e-9
    return {
        "score": round(obs, 4),
        "perm_mean": round(mean, 4),
        "z_perm": round((obs - mean) / sd, 3),
        "p_perm": round((1 + ge) / (n_perm + 1), 5),
    }


def _control_hebrew_chapters(controls: list[dict]) -> set[str]:
    """Extract OSHB chapter prefixes present in controls_v3 so Hebrew training is 100% disjoint."""
    chaps = set()
    for row in controls:
        if row.get("language") == "hebrew":
            cl = str(row.get("cluster") or "")
            if cl:
                chaps.add(cl.replace(" ", "."))
            cid = str(row.get("id") or "")
            # e.g. D3-H1-heb-Psalms143.1a -> extract chapter
            if "heb-" in cid:
                ref = cid.split("heb-", 1)[1].split(".")[0]
                chaps.add(ref)
    return chaps


def build_size_locked_lexicons(
    k_top: int = 300,
    conv: str = "plene",
    exclude_heb_refs: set[str] | None = None,
) -> dict[str, list[Word]]:
    """Build exact size-K liturgical vocabularies from train splits only."""
    tables, signs = r.load_tables(), lid.sign_keys()
    excl = exclude_heb_refs or set()

    lexicons: dict[str, list[Word]] = {}

    # 1. Hebrew liturgical (Dirichlet log-odds: Psalms/Leviticus/etc. vs. narrative prose)
    heb_seg = lid.segment_docs("hebrew")
    heb_docs, _ = lid.written_docs(heb_seg, "hebrew", conv, tables, signs)
    fg, bg = collections.Counter(), collections.Counter()
    for doc_id, words in lid.select(heb_docs, "train"):
        if any(e and e in doc_id for e in excl):
            continue
        book = doc_id.split(".", 1)[0]
        if book in HEB_LIT_BOOKS:
            fg.update(words)
        elif book in HEB_PROSE_BOOKS:
            bg.update(words)
    z_heb = dirichlet_log_odds(fg, bg)
    ranked_heb = sorted(z_heb.items(), key=lambda kv: (-kv[1], kv[0]))
    lexicons["hebrew_lit"] = [w for w, _ in ranked_heb[:k_top]]

    # 2. Akkadian (ORACC CC0 Old/Standard Babylonian, train split, top-K by frequency)
    akk_seg = lid.segment_docs("akkadian")
    akk_docs, _ = lid.written_docs(akk_seg, "akkadian", conv, tables, signs)
    c_akk = collections.Counter(w for _, ws in lid.select(akk_docs, "train") for w in ws)
    if len(c_akk) >= k_top:
        lexicons["akkadian_lit"] = [w for w, _ in c_akk.most_common(k_top)]

    # 2b. Syriac (optional Ephrem hymns when KAPHTOR_ANE_DIR holds aramaic_texts.jsonl)
    syr_seg = lid.segment_docs("syriac")
    if syr_seg:
        syr_docs, _ = lid.written_docs(syr_seg, "syriac", conv, tables, signs)
        c_syr = collections.Counter(w for _, ws in lid.select(syr_docs, "train") for w in ws)
        if len(c_syr) >= k_top:
            lexicons["syriac_lit"] = [w for w, _ in c_syr.most_common(k_top)]

    # 3. Anatolian (Hittite + Luwian CTH rituals/texts, train split, top-K)
    c_ana = collections.Counter()
    for lang in ("hittite", "luwian"):
        seg = lid.segment_docs(lang)
        docs, _ = lid.written_docs(seg, lang, conv, tables, signs)
        c_ana.update(w for _, ws in lid.select(docs, "train") for w in ws)
    lexicons["anatolian_lit"] = [w for w, _ in c_ana.most_common(k_top)]

    # 4. Hurrian (Hurrian + Urartian rituals/texts, train split, top-K)
    c_hur = collections.Counter()
    for lang in ("hurrian", "urartian"):
        seg = lid.segment_docs(lang)
        docs, _ = lid.written_docs(seg, lang, conv, tables, signs)
        c_hur.update(w for _, ws in lid.select(docs, "train") for w in ws)
    lexicons["hurrian_lit"] = [w for w, _ in c_hur.most_common(k_top)]

    # 5. Greek (Diodorus train split, top-K)
    dio_docs, _ = lid.diodorus_docs(signs)
    c_grk = collections.Counter(w for _, ws in lid.select(dio_docs, "train") for w in ws)
    lexicons["greek_lit"] = [w for w, _ in c_grk.most_common(k_top)]

    # Verify exact size lock
    for name, vs in lexicons.items():
        assert len(vs) == k_top, f"{name} has {len(vs)} != {k_top}"
    return lexicons


def run_calibration(k_top: int = 300, n_perm: int = 400, conv: str = "plene") -> dict:
    t0 = time.time()
    controls = [json.loads(line) for line in CONTROLS_V3.read_text(encoding="utf-8").splitlines() if line.strip()]
    excl = _control_hebrew_chapters(controls)
    lexicons = build_size_locked_lexicons(k_top=k_top, conv=conv, exclude_heb_refs=excl)
    sign_table = a.load_signs()

    # Evaluate on Hebrew prayers vs. Hebrew prose vs. non-Semitic controls
    by_class: dict[str, list[dict]] = collections.defaultdict(list)
    for row in controls:
        cls = row["class"]
        words = [a.keys(w, sign_table) for w in row.get("la_canonical", [])]
        scores = {}
        for arm, vocab in lexicons.items():
            scores[arm] = perm_z_score(words, vocab, n_perm=n_perm, seed=20261122)
        winner = max(lexicons, key=lambda arm: scores[arm]["z_perm"])
        by_class[cls].append({"id": row["id"], "winner": winner, "scores": scores})

    summary = {}
    for cls, items in sorted(by_class.items()):
        heb_zs = [it["scores"]["hebrew_lit"]["z_perm"] for it in items]
        heb_wins = sum(it["winner"] == "hebrew_lit" for it in items)
        p_sig = sum(it["scores"]["hebrew_lit"]["p_perm"] <= 0.05 for it in items)
        summary[cls] = {
            "n": len(items),
            "mean_z_hebrew_lit": round(sum(heb_zs) / len(heb_zs), 3),
            "hebrew_lit_wins": heb_wins,
            "p_le_05_hebrew_lit": p_sig,
        }
    return {
        "k_top": k_top,
        "conv": conv,
        "n_perm": n_perm,
        "seconds": round(time.time() - t0, 1),
        "summary": summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--run-linear-a", action="store_true")
    ap.add_argument("--k-top", type=int, default=300)
    ap.add_argument("--n-perm", type=int, default=400)
    ap.add_argument("--conv", choices=("plene", "omission"), default="plene")
    args = ap.parse_args()

    if args.calibrate or (not args.run_linear_a and CONTROLS_V3.is_file()):
        if not CONTROLS_V3.is_file():
            print(f"MISSING: {CONTROLS_V3} (set KAPHTOR_CONTROLS_V3 to run Protocol D calibration).", file=sys.stderr)
            return 2
        res = run_calibration(k_top=args.k_top, n_perm=args.n_perm, conv=args.conv)
        out_path = HERE / "runs" / f"pilot-liturgy-c-{args.conv}.json"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"=== Kernel C Calibration (K={args.k_top}, {args.conv}, B={args.n_perm}) in {res['seconds']}s ===")
        for cls, s in res["summary"].items():
            print(
                f"  {cls:22s} | n={s['n']:2d} | mean_Z(heb_lit)={s['mean_z_hebrew_lit']:+6.2f} "
                f"| heb_wins={s['hebrew_lit_wins']:2d}/{s['n']:2d} | p<=0.05: {s['p_le_05_hebrew_lit']:2d}/{s['n']:2d}"
            )

    if args.run_linear_a:
        if not SIGNATURE.is_file():
            print("REFUSED: SIGNATURE.txt not found beside pre-registration.", file=sys.stderr)
            return 2
        sign_table = a.load_signs()
        words = [a.keys(w, sign_table) for w in IO_ZA_2_STRICT]
        lexicons = build_size_locked_lexicons(k_top=args.k_top, conv=args.conv)
        print(f"\n=== Kernel C Target: IO Za 2 (strict LB values, K={args.k_top}, B={args.n_perm}) ===")
        for arm, vocab in lexicons.items():
            s = perm_z_score(words, vocab, n_perm=args.n_perm, seed=20261122)
            print(f"  {arm:14s} | score={s['score']:.4f} | Z_perm={s['z_perm']:+6.2f} | p_perm={s['p_perm']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
