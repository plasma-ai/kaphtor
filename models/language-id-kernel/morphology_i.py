"""Kernel I: Unsupervised Bound-Affix Morphology & Prefix/Suffix Polarity Kernel.

Extracts strict one-sided morphological affixes from distinct word types in any CV-sign
corpus (stem containment `S` vs `p+S` / `S+s` with `len(S) >= 2`, plus `len(S) >= 3`
single-sided alternations) and scores two orthogonal channels:
  1. Prefix-vs-suffix polarity rate (`ll_pol`).
  2. Bound affix CV-sign identity (`ll_cv` over prefix and suffix CV signs, and
     consonant-only `ll_cons`), tested against consonant-series grid permutations
     (holding vowels fixed so permutation Z measures strictly consonant-specific affix
     identity).

Requires inflected running Greek text via `KAPHTOR_DIODORUS_XML` (not uninflected LSJ
dictionary lemmas) so Greek's inflectional suffix distribution is accurately represented.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import c_render as r         # noqa: E402
import kaphtor_kernel as kk  # noqa: E402
import lid                   # noqa: E402
import pilot                 # noqa: E402

CONSONANT_SERIES = ("D", "J", "K", "M", "N", "P", "Q", "R", "S", "T", "W", "Z")
CSET = set(CONSONANT_SERIES)
SIGNATURE = HERE / "SIGNATURE.txt"
Key = tuple[str, str]


def extract_bound_affixes(words: list[tuple]) -> dict:
    """Extract strict one-sided morphological affixes from distinct word types."""
    types = sorted(set(w for w in words if len(w) >= 2))
    type_set = set(types)
    n_pre = 0
    n_suf = 0
    pre_keys: list[Key] = []
    suf_keys: list[Key] = []
    seen_pairs: set[tuple[tuple, tuple]] = set()

    # 1. Exact stem containment: S vs p+S and S vs S+s
    for w in types:
        lw = len(w)
        for alen in (1, 2):
            if lw - alen < 2:
                continue
            stem_p = w[alen:]
            if stem_p in type_set:
                pair = (stem_p, w)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    n_pre += 1
                    pre_keys.append(w[0])
            stem_s = w[:-alen]
            if stem_s in type_set:
                pair = (stem_s, w)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    n_suf += 1
                    suf_keys.append(w[-1])

    # 2. Strict >=3-sign shared stem with 1-sign single-sided affix alternation
    by_tail3: dict[tuple, list[tuple]] = collections.defaultdict(list)
    by_head3: dict[tuple, list[tuple]] = collections.defaultdict(list)
    for w in types:
        if len(w) >= 4:
            by_tail3[w[1:]].append(w)
            by_head3[w[:-1]].append(w)

    for grp in by_tail3.values():
        if 2 <= len(grp) <= 8:
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    pair = (grp[i], grp[j])
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        n_pre += 1
                        pre_keys.append(grp[i][0])
                        pre_keys.append(grp[j][0])

    for grp in by_head3.values():
        if 2 <= len(grp) <= 8:
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    pair = (grp[i], grp[j])
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        n_suf += 1
                        suf_keys.append(grp[i][-1])
                        suf_keys.append(grp[j][-1])

    pre_cons = [k[0] for k in pre_keys if k[0] in CSET]
    suf_cons = [k[0] for k in suf_keys if k[0] in CSET]
    return {
        "n_transitions": len(seen_pairs),
        "n_pre": n_pre,
        "n_suf": n_suf,
        "pre_rate": n_pre / (n_pre + n_suf) if (n_pre + n_suf) else 0.0,
        "pre_cv_counts": dict(collections.Counter(pre_keys)),
        "suf_cv_counts": dict(collections.Counter(suf_keys)),
        "pre_c_counts": dict(collections.Counter(pre_cons)),
        "suf_c_counts": dict(collections.Counter(suf_cons)),
        "n_pre_cv": len(pre_keys),
        "n_suf_cv": len(suf_keys),
        "n_pre_c": len(pre_cons),
        "n_suf_c": len(suf_cons),
    }


class BoundAffixModel:
    """Dirichlet-smoothed model of polarity + bound CV-sign & consonant-series affixes."""

    def __init__(self, feats: dict, alphabet: list[Key], alpha: float = 0.5):
        self.alphabet = alphabet
        n_pre, n_suf = feats["n_pre"], feats["n_suf"]
        self.p_pre = (n_pre + 1.0) / (n_pre + n_suf + 2.0)
        self.p_suf = 1.0 - self.p_pre
        self.train_n_pre = n_pre
        self.train_n_suf = n_suf

        v = len(alphabet)
        t_pre_cv = feats["n_pre_cv"]
        t_suf_cv = feats["n_suf_cv"]
        self.pre_cv_dist = {
            k: (feats["pre_cv_counts"].get(k, 0) + alpha) / (t_pre_cv + alpha * v)
            for k in alphabet
        }
        self.suf_cv_dist = {
            k: (feats["suf_cv_counts"].get(k, 0) + alpha) / (t_suf_cv + alpha * v)
            for k in alphabet
        }
        self.floor_pre_cv = alpha / (t_pre_cv + alpha * v)
        self.floor_suf_cv = alpha / (t_suf_cv + alpha * v)

        t_pre_c = feats["n_pre_c"]
        t_suf_c = feats["n_suf_c"]
        self.pre_c_dist = {
            c: (feats["pre_c_counts"].get(c, 0) + alpha) / (t_pre_c + alpha * len(CONSONANT_SERIES))
            for c in CONSONANT_SERIES
        }
        self.suf_c_dist = {
            c: (feats["suf_c_counts"].get(c, 0) + alpha) / (t_suf_c + alpha * len(CONSONANT_SERIES))
            for c in CONSONANT_SERIES
        }

    def score_all(self, feats: dict, perm: dict[str, str] | None = None) -> tuple[float, float, float]:
        ll_pol = feats["n_pre"] * math.log(self.p_pre) + feats["n_suf"] * math.log(self.p_suf)
        ll_cv = 0.0
        for (c, v), cnt in feats["pre_cv_counts"].items():
            mk = (perm.get(c, c), v) if perm else (c, v)
            ll_cv += cnt * math.log(self.pre_cv_dist.get(mk, self.floor_pre_cv))
        for (c, v), cnt in feats["suf_cv_counts"].items():
            mk = (perm.get(c, c), v) if perm else (c, v)
            ll_cv += cnt * math.log(self.suf_cv_dist.get(mk, self.floor_suf_cv))

        ll_cons = 0.0
        for c, cnt in feats["pre_c_counts"].items():
            mc = perm[c] if perm else c
            ll_cons += cnt * math.log(self.pre_c_dist[mc])
        for c, cnt in feats["suf_c_counts"].items():
            mc = perm[c] if perm else c
            ll_cons += cnt * math.log(self.suf_c_dist[mc])
        return ll_pol, ll_cv, ll_cons


def _cap_types(words: list[tuple], max_types: int = 2500, seed: int = 20261123) -> list[tuple]:
    types = sorted(set(words))
    if len(types) <= max_types:
        return types
    return random.Random(seed).sample(types, max_types)


def load_family_splits(
    tables: r.Tables,
    signs: set,
    mode: str = "omission",
) -> tuple[dict[str, list[tuple]], dict[str, list[tuple]]]:
    by_lang_train: dict[str, list[tuple]] = {}
    by_lang_dev: dict[str, list[tuple]] = {}
    for language in pilot.TEST_LANGUAGES:
        if language == "diodorus":
            continue
        seg = lid.segment_docs(language)
        docs, _ = lid.written_docs(seg, language, mode, tables, signs)
        by_lang_train[language] = pilot.flat(lid.select(docs, "train"))
        by_lang_dev[language] = pilot.flat(lid.select(docs, "dev"))

    if not lid.DIODORUS.is_file():
        raise SystemExit(
            f"Kernel I requires inflected Greek running text via KAPHTOR_DIODORUS_XML (missing {lid.DIODORUS})."
        )
    dio_docs, _ = lid.diodorus_docs(signs)
    dio_train = pilot.flat(lid.select(dio_docs, "train"))
    dio_dev = pilot.flat(lid.select(dio_docs, "dev"))

    fam_train: dict[str, list[tuple]] = {}
    fam_dev: dict[str, list[tuple]] = {}
    for arm, member_list in lid.ARMS.items():
        if arm == "greek":
            # Strictly inflected running Greek text (no uninflected LSJ lemmas)
            fam_train[arm] = list(dio_train)
            fam_dev[arm] = list(dio_dev)
        else:
            tr_w: list[tuple] = []
            dv_w: list[tuple] = []
            for m in member_list:
                if m in by_lang_train:
                    tr_w.extend(by_lang_train[m])
                    dv_w.extend(by_lang_dev[m])
            if tr_w:
                fam_train[arm] = tr_w
                fam_dev[arm] = dv_w
    return fam_train, fam_dev


def evaluate_corpus(
    words: list[tuple],
    models: dict[str, BoundAffixModel],
    n_perm: int = 5000,
    seed: int = 20261123,
    max_types: int = 2500,
) -> dict:
    words = _cap_types(words, max_types=max_types, seed=seed)
    feats = extract_bound_affixes(words)
    rng = random.Random(seed)
    perms: list[dict[str, str]] = []
    for _ in range(n_perm):
        shuf = list(CONSONANT_SERIES)
        rng.shuffle(shuf)
        perms.append(dict(zip(CONSONANT_SERIES, shuf)))

    results: dict[str, dict] = {}
    null_joint_by_fam: dict[str, list[float]] = {}
    for fam, m in models.items():
        ll_pol, ll_cv, ll_cons = m.score_all(feats)
        null_cv = [m.score_all(feats, p)[1] for p in perms]
        null_joint_by_fam[fam] = [ll_pol + x for x in null_cv]
        mu_cv = sum(null_cv) / len(null_cv)
        sd_cv = math.sqrt(sum((x - mu_cv) ** 2 for x in null_cv) / len(null_cv))
        z_cv = (ll_cv - mu_cv) / sd_cv if sd_cv > 0 else 0.0
        p_cv = (sum(1 for x in null_cv if x >= ll_cv - 1e-12) + 1) / (n_perm + 1)

        null_c = [m.score_all(feats, p)[2] for p in perms]
        mu_c = sum(null_c) / len(null_c)
        sd_c = math.sqrt(sum((x - mu_c) ** 2 for x in null_c) / len(null_c))
        z_c = (ll_cons - mu_c) / sd_c if sd_c > 0 else 0.0
        p_c = (sum(1 for x in null_c if x >= ll_cons - 1e-12) + 1) / (n_perm + 1)

        results[fam] = {
            "ll_pol": round(ll_pol, 3),
            "ll_cv": round(ll_cv, 3),
            "ll_joint_cv": round(ll_pol + ll_cv, 3),
            "z_cv_perm": round(z_cv, 3),
            "p_cv_perm": round(p_cv, 5),
            "ll_cons": round(ll_cons, 3),
            "z_c_perm": round(z_c, 3),
            "p_c_perm": round(p_c, 5),
            "train_pre_rate": round(m.p_pre, 4),
        }

    # Discriminative margin-permutation null: M_L(pi) = LL_L(pi) - max_{R != L} LL_R(pi)
    # Cancels universal cross-linguistic suffix consonants (T, R, M, N, S).
    fams = list(models.keys())
    for fam in fams:
        obs_m = results[fam]["ll_joint_cv"] - max(results[r]["ll_joint_cv"] for r in fams if r != fam)
        null_m = [
            null_joint_by_fam[fam][i] - max(null_joint_by_fam[r][i] for r in fams if r != fam)
            for i in range(n_perm)
        ]
        mu_m = sum(null_m) / n_perm
        sd_m = math.sqrt(sum((x - mu_m) ** 2 for x in null_m) / n_perm)
        z_m = (obs_m - mu_m) / sd_m if sd_m > 0 else 0.0
        p_m = (sum(1 for x in null_m if x >= obs_m - 1e-12) + 1) / (n_perm + 1)
        results[fam]["margin_obs"] = round(obs_m, 3)
        results[fam]["z_margin_perm"] = round(z_m, 3)
        results[fam]["p_margin_perm"] = round(p_m, 5)

    ranked = sorted(results.items(), key=lambda kv: -kv[1]["ll_joint_cv"])
    return {
        "n_types": len(words),
        "n_pre": feats["n_pre"],
        "n_suf": feats["n_suf"],
        "observed_pre_rate": round(feats["pre_rate"], 4),
        "winner_joint_cv": ranked[0][0],
        "delta_ll_joint_cv": round(ranked[0][1]["ll_joint_cv"] - ranked[1][1]["ll_joint_cv"], 3),
        "families": results,
    }


def run_robustness(
    tables: r.Tables,
    signs: set,
    alphabet: list[Key],
    n_perm: int = 2000,
    seeds: tuple[int, ...] = (20261123, 20261124, 20261125, 20261126, 20261127),
) -> dict:
    """Multi-seed × (omission, plene) stability check + votive-vs-admin Linear A split."""
    lb_docs, _ = lid.linear_b_docs(signs)
    lb_words = pilot.flat(lb_docs)
    la_docs, _ = kk.load_linear_a_strict_words()
    la_all = [w for _, ws in la_docs for w in ws]
    votive_series = ("Za", "Zb", "Zc", "Zf", "Zg")
    la_votive = [w for doc_id, ws in la_docs if any(s in doc_id for s in votive_series) for w in ws]
    la_admin = [w for doc_id, ws in la_docs if not any(s in doc_id for s in votive_series) for w in ws]

    sweep: dict[str, dict] = {}
    for mode in ("omission", "plene"):
        fam_train, _ = load_family_splits(tables, signs, mode=mode)
        lb_runs = []
        la_runs = []
        for s in seeds:
            models = {
                fam: BoundAffixModel(extract_bound_affixes(_cap_types(words, seed=s)), alphabet)
                for fam, words in sorted(fam_train.items())
            }
            lb_r = evaluate_corpus(lb_words, models, n_perm=n_perm, seed=s)
            la_r = evaluate_corpus(la_all, models, n_perm=n_perm, seed=s)
            lb_runs.append({
                "seed": s,
                "winner": lb_r["winner_joint_cv"],
                "greek_M": lb_r["families"]["greek"]["margin_obs"],
                "greek_p_M": lb_r["families"]["greek"]["p_margin_perm"],
                "semitic_p_M": lb_r["families"]["semitic"]["p_margin_perm"],
            })
            la_runs.append({
                "seed": s,
                "winner": la_r["winner_joint_cv"],
                "semitic_M": la_r["families"]["semitic"]["margin_obs"],
                "semitic_p_M": la_r["families"]["semitic"]["p_margin_perm"],
                "semitic_p_cv": la_r["families"]["semitic"]["p_cv_perm"],
            })
        # Register split on primary seed
        models0 = {
            fam: BoundAffixModel(extract_bound_affixes(_cap_types(words, seed=seeds[0])), alphabet)
            for fam, words in sorted(fam_train.items())
        }
        vot_r = evaluate_corpus(la_votive, models0, n_perm=n_perm, seed=seeds[0])
        adm_r = evaluate_corpus(la_admin, models0, n_perm=n_perm, seed=seeds[0])
        sweep[mode] = {
            "linear_b_seeds": lb_runs,
            "linear_b_greek_wins": sum(1 for x in lb_runs if x["winner"] == "greek"),
            "linear_a_seeds": la_runs,
            "linear_a_semitic_wins": sum(1 for x in la_runs if x["winner"] == "semitic"),
            "linear_a_mean_M": round(sum(x["semitic_M"] for x in la_runs) / len(la_runs), 2),
            "linear_a_mean_p_M": round(sum(x["semitic_p_M"] for x in la_runs) / len(la_runs), 5),
            "linear_a_votive": {
                "n_types": vot_r["n_types"],
                "pre_rate": vot_r["observed_pre_rate"],
                "n_pre": vot_r["n_pre"],
                "n_suf": vot_r["n_suf"],
                "winner": vot_r["winner_joint_cv"],
                "semitic_M": vot_r["families"]["semitic"]["margin_obs"],
                "semitic_p_M": vot_r["families"]["semitic"]["p_margin_perm"],
            },
            "linear_a_admin": {
                "n_types": adm_r["n_types"],
                "pre_rate": adm_r["observed_pre_rate"],
                "n_pre": adm_r["n_pre"],
                "n_suf": adm_r["n_suf"],
                "winner": adm_r["winner_joint_cv"],
                "semitic_M": adm_r["families"]["semitic"]["margin_obs"],
                "semitic_p_M": adm_r["families"]["semitic"]["p_margin_perm"],
            },
        }
    return sweep


def main() -> int:
    ap = argparse.ArgumentParser(description="Kernel I: Bound Affix Morphology (inflected Greek).")
    ap.add_argument("--mode", choices=("omission", "plene"), default="omission")
    ap.add_argument("--n-perm", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--robustness", action="store_true", help="Run 5-seed x (omission, plene) + votive/admin split")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)
    if args.robustness:
        if not SIGNATURE.exists():
            raise SystemExit(f"Refusing to score Linear A without {SIGNATURE}")
        rob = run_robustness(tables, signs, alphabet, n_perm=min(args.n_perm, 2000))
        if args.json:
            print(json.dumps(rob, indent=2))
            return 0
        for mode, d in rob.items():
            print(f"\n=== Robustness ({mode}) ===")
            print(f"  Linear B Greek wins: {d['linear_b_greek_wins']}/5  p_M={[x['greek_p_M'] for x in d['linear_b_seeds']]}")
            print(f"  Linear A Semitic wins: {d['linear_a_semitic_wins']}/5  mean_M={d['linear_a_mean_M']:+.2f}  mean_p_M={d['linear_a_mean_p_M']:.5f}  p_M={[x['semitic_p_M'] for x in d['linear_a_seeds']]}")
            print(f"  Votive split: {d['linear_a_votive']}")
            print(f"  Admin  split: {d['linear_a_admin']}")
        return 0
    fam_train, fam_dev = load_family_splits(tables, signs, mode=args.mode)
    models = {
        fam: BoundAffixModel(extract_bound_affixes(_cap_types(words)), alphabet)
        for fam, words in sorted(fam_train.items())
    }

    cal_dev = {
        fam: evaluate_corpus(words, models, n_perm=min(args.n_perm, 2000), seed=args.seed)
        for fam, words in sorted(fam_dev.items())
        if words
    }
    lb_docs, _ = lid.linear_b_docs(signs)
    cal_lb = evaluate_corpus(pilot.flat(lb_docs), models, n_perm=args.n_perm, seed=args.seed)

    out: dict = {"mode": args.mode, "n_perm": args.n_perm, "calibration_dev": cal_dev, "calibration_linear_b": cal_lb}
    if SIGNATURE.exists():
        la_docs, _ = kk.load_linear_a_strict_words()
        out["linear_a"] = evaluate_corpus([w for _, ws in la_docs for w in ws], models, n_perm=args.n_perm, seed=args.seed)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"=== Kernel I: Bound Affix Morphology (mode={args.mode}, inflected Greek, n_perm={args.n_perm}) ===")
    print("Trained family prefix rates:")
    for fam, m in sorted(models.items()):
        print(f"  {fam:<12} p_pre={m.p_pre:.3f} (n_pre={m.train_n_pre}, n_suf={m.train_n_suf})")

    print("\n--- Dev-Split Calibration ---")
    for fam, res in cal_dev.items():
        f = res["families"][fam]
        ok = "PASS" if res["winner_joint_cv"] == fam else f"MISS(got {res['winner_joint_cv']})"
        print(f"  dev:{fam:<10} pre_rate={res['observed_pre_rate']:.3f}  win={res['winner_joint_cv']:<10}  Z_cv={f['z_cv_perm']:+6.2f} p_cv={f['p_cv_perm']:.5f}  [{ok}]")

    print(f"\n--- Linear B Gate (n_types={cal_lb['n_types']}, pre_rate={cal_lb['observed_pre_rate']:.3f}, winner={cal_lb['winner_joint_cv']}) ---")
    for fam, d in sorted(cal_lb["families"].items(), key=lambda kv: -kv[1]["ll_joint_cv"]):
        print(f"  {fam:<12} ll_joint={d['ll_joint_cv']:+9.2f}  M={d['margin_obs']:+8.2f} Z_M={d['z_margin_perm']:+6.2f} p_M={d['p_margin_perm']:.5f}  Z_cv={d['z_cv_perm']:+6.2f} p_cv={d['p_cv_perm']:.5f}")

    if "linear_a" in out:
        la = out["linear_a"]
        print(f"\n--- Linear A Target (n_types={la['n_types']}, pre_rate={la['observed_pre_rate']:.3f}, winner={la['winner_joint_cv']}) ---")
        for fam, d in sorted(la["families"].items(), key=lambda kv: -kv[1]["ll_joint_cv"]):
            print(f"  {fam:<12} ll_joint={d['ll_joint_cv']:+9.2f}  M={d['margin_obs']:+8.2f} Z_M={d['z_margin_perm']:+6.2f} p_M={d['p_margin_perm']:.5f}  Z_cv={d['z_cv_perm']:+6.2f} p_cv={d['p_cv_perm']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
