"""Development-split experiment testing Fix 1 (unpooled per-language models + sign-count parity).

Reads ONLY the training and development splits via lid.select(..., "train"/"dev").
Never reads the gate split or any Linear A word. Does not modify lid.py or pilot.py.

Compares four configurations at order 3 (5 draws, k=10, seed 20261122):
  1. baseline       : pooled family arms, equal word-type count (T=800)
  2. pooled_signs   : pooled family arms, equal total sign count (S)
  3. unpooled_types : per-language models (min over family members), equal word-type count (T=800)
  4. unpooled_signs : per-language models (min over family members), equal total sign count (S)
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import lid
import pilot
from lid import r


def draw_by_signs(members: dict, target_signs: int, seed: int) -> list:
    """Draw distinct word types in equal sign shares across members until ~target_signs."""
    types = {name: sorted(set(words)) for name, words in members.items()}
    out: list = []
    left_signs, waiting = target_signs, len(types)
    for name in sorted(types, key=lambda n: (sum(len(w) + 1 for w in types[n]), n)):
        pool = list(types[name])
        random.Random(f"{seed}:{name}").shuffle(pool)
        quota = left_signs // waiting
        taken, acc = [], 0
        for w in pool:
            s = len(w) + 1
            if acc + s > quota and taken:
                break
            taken.append(w)
            acc += s
        out.extend(taken)
        left_signs -= acc
        waiting -= 1
    return out


def member_signs(words: list) -> int:
    return sum(len(w) + 1 for w in set(words))


def run_experiment(k: int = 10, draws: int = 5, order: int = 3) -> dict:
    t0 = time.time()
    pool = json.loads(pilot.POOL.read_text(encoding="utf-8"))
    sizes, n_types = pool["document_sizes"], pool["test_types"]
    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)

    train: dict = {}
    dev: dict = {}
    for language in pilot.TEST_LANGUAGES:
        if language == "diodorus":
            continue
        seg = lid.segment_docs(language)
        for conv in r.CONVENTIONS:
            docs, _ = lid.written_docs(seg, language, conv, tables, signs)
            train[language, conv] = pilot.flat(lid.select(docs, "train"))
            dev[language, conv] = pilot.flat(lid.select(docs, "dev"))

    lb_docs, _ = lid.linear_b_docs(signs)
    dev["greek", "written"] = pilot.flat(lid.select(lb_docs, "dev"))
    lsj, _ = lid.lsj_words(signs)
    dio_docs, _ = lid.diodorus_docs(signs)
    train["diodorus", "lb"] = pilot.flat(lid.select(dio_docs, "train"))
    dev["diodorus", "written"] = pilot.flat(lid.select(dio_docs, "dev"))

    def members(arm: str, conv: str, without: str | None = None) -> dict:
        if arm == "greek":
            both = {"lsj": lsj, "diodorus": train["diodorus", "lb"]}
            return {m: words for m, words in both.items() if m != without}
        return {m: train[m, conv] for m in lid.ARMS[arm] if m != without}

    held = {arm: min(lid.holds(members(arm, conv)) for conv in r.CONVENTIONS) for arm in lid.ARMS}
    arms = [arm for arm in lid.ARMS if held[arm] >= pilot.MIN_ARM]
    smallest_types = min(held[arm] for arm in arms)
    total_types = 1000 if smallest_types >= 1000 else smallest_types // 100 * 100

    # Sign budget: smallest arm's total distinct-type signs, rounded down to nearest 100
    held_signs = {
        arm: min(sum(member_signs(ws) for ws in members(arm, conv).values()) for conv in r.CONVENTIONS)
        for arm in arms
    }
    smallest_signs = min(held_signs.values())
    total_signs = (smallest_signs // 100) * 100

    # Pre-cut dev pseudo-corpora once so all 4 modes see identical test sets
    dev_corpora = {}
    for (language, conv), words in dev.items():
        dev_corpora[language, conv] = pilot.corpora(words, sizes, n_types, k)

    variants = [(arm, None) for arm in arms] + [
        (arm, language) for language, arm in pilot.SISTERS.items() if arm in arms
    ]

    # Build individual member models for unpooled modes
    # Only include members that hold at least MIN_ARM types (or all members with >= 200 types? Let's use >= 200 so ugaritic/luwian/aramaic still participate, capped at budget)
    all_members = {}
    for arm in arms:
        for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
            for m, ws in members(arm, conv).items():
                all_members[arm, m, conv] = ws

    modes = ["baseline", "pooled_signs", "unpooled_types", "unpooled_signs"]
    out_summary = {
        "total_types": total_types,
        "total_signs": total_signs,
        "held_signs": held_signs,
        "modes": {},
    }

    for mode in modes:
        if mode in ("baseline", "pooled_signs"):
            models = {}
            for arm, without in variants:
                for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
                    mems = members(arm, conv, without)
                    if mode == "baseline":
                        models[arm, without, conv] = [
                            lid.Model(lid.draw(mems, total_types, pilot.SEED + j), order, alphabet)
                            for j in range(draws)
                        ]
                    else:
                        models[arm, without, conv] = [
                            lid.Model(draw_by_signs(mems, total_signs, pilot.SEED + j), order, alphabet)
                            for j in range(draws)
                        ]

            def fit_fn(words, arm, without=None):
                return min(
                    lid.bits_per_sign(ms, words)
                    for (a_, w_, _), ms in models.items()
                    if a_ == arm and w_ == without
                )
        else:
            # Per-member models
            m_models = {}
            for (arm, m, conv), ws in all_members.items():
                if mode == "unpooled_types":
                    m_models[arm, m, conv] = [
                        lid.Model(lid.draw({m: ws}, total_types, pilot.SEED + j), order, alphabet)
                        for j in range(draws)
                    ]
                else:
                    m_models[arm, m, conv] = [
                        lid.Model(draw_by_signs({m: ws}, total_signs, pilot.SEED + j), order, alphabet)
                        for j in range(draws)
                    ]

            def fit_fn(words, arm, without=None):
                return min(
                    lid.bits_per_sign(ms, words)
                    for (a_, m_, _), ms in m_models.items()
                    if a_ == arm and m_ != without
                )

        rows = []
        for (language, conv), corps in dev_corpora.items():
            own_arm = lid.ARM_OF[language]
            for j, c in enumerate(corps):
                full = {arm: fit_fn(c["words"], arm) for arm in arms}
                row = {
                    "language": language,
                    "convention": conv,
                    "corpus": j,
                    "short": c["short"],
                    "overlaps": c["overlaps"],
                    "types": len(set(c["words"])),
                    "bits": full,
                    "first": min(full, key=full.get),
                    "own": lid.margin(full, own_arm) if own_arm in arms else None,
                    "semitic": lid.margin(full, "semitic"),
                    "greek": lid.margin(full, "greek"),
                }
                if own_arm != "semitic":
                    row["semitic_absent"] = lid.margin(full, "semitic", absent=(own_arm,))
                if own_arm != "greek":
                    row["greek_absent"] = lid.margin(full, "greek", absent=(own_arm,))
                if language in pilot.SISTERS and own_arm in arms:
                    sister = {**full, own_arm: fit_fn(c["words"], own_arm, language)}
                    row["sister_bits"] = sister[own_arm]
                    row["sister_first"] = min(sister, key=sister.get)
                    row["sister"] = lid.margin(sister, own_arm)
                rows.append(row)

        summary = pilot.summarise(rows)
        # Also record top-3 outside margins for Semitic to see outlier behavior
        for conv in ("omission", "plene"):
            use = [row for row in rows if row["convention"] in (conv, "written")]
            not_sem = [row for row in use if lid.ARM_OF[row["language"]] != "semitic"]
            top_out = sorted(
                ((max(row["semitic"], row["semitic_absent"]), row["language"], row["corpus"]) for row in not_sem),
                reverse=True,
            )[:5]
            summary[conv]["top5_outside_semitic"] = [(round(v, 4), l, c) for v, l, c in top_out]
        out_summary["modes"][mode] = summary

    out_summary["seconds"] = round(time.time() - t0, 1)
    return out_summary


if __name__ == "__main__":
    res = run_experiment()
    out_path = lid.HERE / "runs" / "pilot-fix1-comparison.json"
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} in {res['seconds']}s (T={res['total_types']}, S={res['total_signs']})")
    for mode, summ in res["modes"].items():
        print(f"\n=== {mode} ===")
        for conv in ("omission", "plene"):
            s = summ[conv]
            g3 = s["G3_sister_above_theta"]
            print(
                f"  {conv:8s} | theta_S={s['theta_semitic']:.4f} ({s['theta_semitic_set_by']}) "
                f"| theta_G={s['theta_greek']:.4f} | G1={s['G1_greek_as_greek']} "
                f"| G3: heb={g3.get('hebrew')} ara={g3.get('arabic')} syr={g3.get('syriac')} "
                f"uga={g3.get('ugaritic')} geez={g3.get('geez')} akk={g3.get('akkadian')}"
            )
            print(f"           | top5_outside={s['top5_outside_semitic']}")
