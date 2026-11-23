"""The development-part pilot of the language-identification test (PREREGISTRATION-DRAFT.md §5 to §7).

Reads the training and development parts of the known-language texts, and nothing of Linear A but the sizes in
Protocol C's pool-shape.json. Trains every arm, cuts each test language's development part into pseudo-corpora of
Linear A's shape, scores them under the own, sister and absent conditions, and writes one new record under runs/.
A pilot decides nothing.

    uv run python pilot.py --k 10 --draws 5

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

import lid
from lid import ct, r

sys.path.insert(0, str(lid.HERE / "render"))
import c_pseudo  # noqa: E402  (Protocol C's cut into pseudo-corpora; read, never edited)

PC = lid.HERE.parents[1] / "ioza2-adjudication/protocol-c"
POOL = PC / "controls/pool-shape.json"
SKILLS = {"linear-a-decipherment": Path.home() / ".claude/skills/linear-a-decipherment",
          "ancient-near-east-research": Path.home() / ".claude/skills/ancient-near-east-research"}
INPUTS = [ct.OSHB, lid.QURAN, ct.TLHDIG, ct.LINEAR_B, lid.LSJ, ct.EUPT, lid.TRACES, lid.LATIN, lid.ARAMAIC,
          lid.DIODORUS, POOL,
          *sorted({lid.ORACC_DIR / name for name, _ in lid.ORACC.values()}), lid.HERE / "render/series.json",
          lid.HERE / "render/series-a5-proposed.json", lid.HERE / "render/signs-a5-proposed.json",
          lid.HERE / "lid.py", lid.HERE / "pilot.py", lid.HERE / "PREREGISTRATION-DRAFT.md"]
# Every member of an arm is a test language; the Boğazköy Akkadian is a test text and trains nothing.
TEST_LANGUAGES = tuple(m for members in lid.ARMS.values() for m in members if m != "lsj") + ("akkadian_bo",)
# The sister condition: the text's own language is taken out of its family arm, where the arm has another member.
SISTERS = {m: arm for arm, members in lid.ARMS.items() if len(members) > 1 for m in members}
SEED = 20261122
MIN_ARM = 800


def hashes() -> dict:
    return {str(p): lid.sha256(p) for p in INPUTS}


def commit(path: Path) -> str:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def flat(docs) -> list:
    return [w for _, words in docs for w in words]


def corpora(words: list, sizes: list, n_types: int, k: int) -> list[dict]:
    """K pseudo-corpora of Linear A's shape, or one short corpus when the text holds too few distinct words."""
    if len(set(words)) < n_types:
        return [{"words": words, "short": True, "overlaps": False}]
    # A corpus cut after the text has run out and started again repeats earlier words: it is no new sample and
    # is left out, so a small text gives fewer than K corpora.
    return [{"words": [w for _, w in c["tokens"]], "short": False, "overlaps": False}
            for c in c_pseudo.cut(words, sizes, n_types, k=k, seed=SEED) if not c["overlaps"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--draws", type=int, default=5)
    ap.add_argument("--orders", type=int, nargs="+", default=[2, 3])
    ap.add_argument("--tier", choices=("full", "three"), default="full",
                    help="three: e with i and o with u, in every source and in the alphabet")
    args = ap.parse_args()
    began, before = time.time(), hashes()
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    sizes, n_types = pool["document_sizes"], pool["test_types"]
    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)

    train: dict = {}                                         # (language, convention) -> training-part words
    dev: dict = {}                                           # (language, convention) -> development-part words
    counts: dict = {}
    for language in TEST_LANGUAGES:
        if language == "diodorus":                           # spelled by the Greek speller, one convention
            continue
        seg = lid.segment_docs(language)
        for conv in r.CONVENTIONS:
            docs, n = lid.written_docs(seg, language, conv, tables, signs)
            train[language, conv] = flat(lid.select(docs, "train"))
            dev[language, conv] = flat(lid.select(docs, "dev"))
            counts[f"{language}/{conv}"] = {**n, "train_types": len(set(train[language, conv])),
                                            "dev_words": len(dev[language, conv]),
                                            "dev_types": len(set(dev[language, conv]))}
    lb_docs, n = lid.linear_b_docs(signs)
    dev["greek", "written"] = flat(lid.select(lb_docs, "dev"))
    counts["greek/written"] = {**n, "dev_words": len(dev["greek", "written"]),
                               "dev_types": len(set(dev["greek", "written"]))}
    lsj, n = lid.lsj_words(signs)
    counts["lsj"] = {**n, "types": len(set(lsj))}
    dio_docs, n = lid.diodorus_docs(signs)
    train["diodorus", "lb"] = flat(lid.select(dio_docs, "train"))
    dev["diodorus", "written"] = flat(lid.select(dio_docs, "dev"))
    counts["diodorus/lb"] = {**n, "train_types": len(set(train["diodorus", "lb"])),
                             "dev_types": len(set(dev["diodorus", "written"]))}
    if args.tier == "three":                                 # after validity, so both tiers hold the same words
        train = {k: [lid.three_vowels(w) for w in v] for k, v in train.items()}
        dev = {k: [lid.three_vowels(w) for w in v] for k, v in dev.items()}
        lsj = [lid.three_vowels(w) for w in lsj]
        alphabet = sorted({lid.three_vowels((k,))[0] for k in signs})

    def members(arm: str, conv: str, without: str | None = None) -> dict:
        if arm == "greek":
            both = {"lsj": lsj, "diodorus": train["diodorus", "lb"]}
            return {m: words for m, words in both.items() if m != without}
        return {m: train[m, conv] for m in lid.ARMS[arm] if m != without}

    # §6: a family that holds fewer than MIN_ARM training types is no arm; its texts stay as test texts of a
    # language outside every arm. T is set by the arms that remain. A family arm without one member (the sister
    # condition) draws up to T from what its other members hold; what each holds is recorded.
    held = {arm: min(lid.holds(members(arm, conv)) for conv in r.CONVENTIONS) for arm in lid.ARMS}
    arms = [arm for arm in lid.ARMS if held[arm] >= MIN_ARM]
    counts["arms_hold"] = held
    counts["no_arm_too_small"] = [arm for arm in lid.ARMS if arm not in arms]
    variants = [(arm, None) for arm in arms] + [(arm, language) for language, arm in SISTERS.items() if arm in arms]
    smallest = min(held[arm] for arm in arms)
    total = 1000 if smallest >= 1000 else smallest // 100 * 100
    counts["sister_arms_hold"] = {f"{arm} without {without}/{conv}": lid.holds(members(arm, conv, without))
                                  for arm, without in variants if without for conv in r.CONVENTIONS}
    if total < 100:
        print(f"the smallest arm holds {smallest} training types: too few to train on", file=sys.stderr)
        return 1

    results = {}
    for order in args.orders:
        models = {}                                         # (arm, without, convention) -> the draws' models
        for arm, without in variants:
            for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
                models[arm, without, conv] = [
                    lid.Model(lid.draw(members(arm, conv, without), total, SEED + j), order, alphabet)
                    for j in range(args.draws)]

        def fit(words, arm, without=None):
            return min(lid.bits_per_sign(ms, words) for (a_, w_, _), ms in models.items()
                       if a_ == arm and w_ == without)

        rows = []
        for (language, conv), words in dev.items():
            own_arm = lid.ARM_OF[language]
            for j, c in enumerate(corpora(words, sizes, n_types, args.k)):
                full = {arm: fit(c["words"], arm) for arm in arms}
                row = {"language": language, "convention": conv, "corpus": j, "short": c["short"],
                       "overlaps": c["overlaps"], "types": len(set(c["words"])), "bits": full,
                       "first": min(full, key=full.get),
                       "own": lid.margin(full, own_arm) if own_arm in arms else None,
                       "semitic": lid.margin(full, "semitic"), "greek": lid.margin(full, "greek")}
                if own_arm not in ("semitic",):
                    row["semitic_absent"] = lid.margin(full, "semitic", absent=(own_arm,))
                if own_arm not in ("greek",):
                    row["greek_absent"] = lid.margin(full, "greek", absent=(own_arm,))
                if language in SISTERS and own_arm in arms:  # akkadian_bo trains nothing: its own run is its sister run
                    sister = {**full, own_arm: fit(c["words"], own_arm, language)}
                    row["sister_bits"] = sister[own_arm]
                    row["sister_first"] = min(sister, key=sister.get)
                    row["sister"] = lid.margin(sister, own_arm)
                rows.append(row)
        results[str(order)] = {"rows": rows, "summary": summarise(rows)}

    after = hashes()
    if after != before:
        print("an input changed during the run; no record is written", file=sys.stderr)
        return 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = lid.HERE / "runs" / f"pilot-dev-{args.tier}-{stamp}.json"
    out.parent.mkdir(exist_ok=True)
    record = {"kind": "pilot, development part; decides nothing", "tier": args.tier, "seed": SEED, "k": args.k, "draws": args.draws,
              "training_types_per_arm": total, "n_types": n_types, "counts": counts,
              "commits": {name: commit(path) for name, path in SKILLS.items()}, "sha256": before,
              "seconds": round(time.time() - began, 1), "results": results}
    with open(out, "x", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1)
    print(out)
    for order, res in results.items():
        print(f"order {order}")
        print(json.dumps(res["summary"], ensure_ascii=False, indent=1))
    return 0


def summarise(rows: list) -> dict:
    """Per convention of the test text: the thresholds, the gate's shares, and who fits each language best."""
    out = {}
    for conv in sorted({row["convention"] for row in rows} - {"written"}):
        use = [row for row in rows if row["convention"] in (conv, "written")]
        not_semitic = [row for row in use if lid.ARM_OF[row["language"]] != "semitic"]
        not_greek = [row for row in use if lid.ARM_OF[row["language"]] != "greek"]
        theta_s = lid.threshold([m for row in not_semitic for m in (row["semitic"], row["semitic_absent"])])
        theta_g = lid.threshold([m for row in not_greek for m in (row["greek"], row["greek_absent"])])

        def of(language):
            return [row for row in use if row["language"] == language]

        s = {"theta_semitic": round(theta_s, 4), "theta_greek": round(theta_g, 4),
             "theta_semitic_set_by": max(not_semitic, key=lambda row: max(row["semitic"], row["semitic_absent"]))["language"],
             "G1_greek_as_greek": lid.power([row["greek"] for row in of("greek")], theta_g) if of("greek") else None,
             "G2_hebrew_own": lid.power([row["semitic"] for row in of("hebrew")], theta_s),
             "G3_sister_above_theta": {m: lid.power([row["sister"] for row in of(m)], theta_s)
                                       for m in lid.ARMS["semitic"] if of(m)},
             "by_language": {}}
        for language in sorted({row["language"] for row in use}):
            got = of(language)
            entry = {"corpora": len(got), "short": sum(row["short"] for row in got),
                     "right_arm_first": sum(row["first"] == lid.ARM_OF[language] for row in got),
                     "mean_own_margin": (round(sum(row["own"] for row in got) / len(got), 4)
                                         if got[0]["own"] is not None else None),
                     "mean_semitic_margin": round(sum(row["semitic"] for row in got) / len(got), 4)}
            if "sister" in got[0]:
                entry["right_arm_first_as_sister"] = sum(row["sister_first"] == lid.ARM_OF[language] for row in got)
                entry["mean_sister_margin"] = round(sum(row["sister"] for row in got) / len(got), 4)
            s["by_language"][language] = entry
        out[conv] = s
    return out


if __name__ == "__main__":
    raise SystemExit(main())
