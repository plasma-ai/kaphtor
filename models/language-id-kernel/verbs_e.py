"""Kernel E: Verbal-Frame Forward Model (Prefix + Suffix Edge Distribution on >=4-Sign Words).

Trains a Witten-Bell edge-frame model P_L(pre_1, pre_2, suf_1, suf_2) on equal budgets of
forward-spelled >=4-sign words (using OSHB HV* finite verbs for Hebrew, plus sister Semitic
corpora vs. Greek, Anatolian, Hurrian, and Latin).

Calibration Gate:
  Held-out dev-split >=4-sign finite Hebrew verbs vs. dev-split Greek/Hittite/Hurrian/Latin.

Target (requires SIGNATURE.txt):
  All undamaged >=4-sign words on non-administrative Linear A supports (Za, Zb, Zc, Zf, Zg)
  under strict Linear B sign values, tested against 1,000 consonant-series grid permutations.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402
import c_texts as ct    # noqa: E402
import lid              # noqa: E402

import os
SIGNATURE = HERE / "SIGNATURE.txt"
CORPUS_PATH = Path(
    os.environ.get("KAPHTOR_CORPUS_JSON", str(HERE.parents[1] / "data/linear-a/corpus.json"))
)
Word = tuple[tuple[str, str], ...]


class EdgeFrameModel:
    """Witten-Bell model over word-edge verbal frames: (pre1, pre2, suf1, suf2)."""

    def __init__(self, words: list[Word], alphabet: list):
        self.v = len(alphabet)
        self.c_p1 = collections.Counter()
        self.c_p2 = collections.Counter()
        self.c_s1 = collections.Counter()
        self.c_s2 = collections.Counter()
        self.c_p2_given_p1: dict = collections.defaultdict(collections.Counter)
        self.c_s2_given_s1: dict = collections.defaultdict(collections.Counter)
        for w in words:
            if len(w) < 4:
                continue
            p1, p2, s2, s1 = w[0], w[1], w[-2], w[-1]
            self.c_p1[p1] += 1
            self.c_p2[p2] += 1
            self.c_s1[s1] += 1
            self.c_s2[s2] += 1
            self.c_p2_given_p1[p1][p2] += 1
            self.c_s2_given_s1[s1][s2] += 1
        self.n = sum(self.c_p1.values())

    def _wb(self, counter: collections.Counter, total: int, sym, p_bo: float) -> float:
        if not total:
            return p_bo
        t = len(counter)
        return (counter.get(sym, 0) + t * p_bo) / (total + t)

    def log2(self, w: Word) -> float:
        if len(w) < 4:
            return 0.0
        p0 = 1.0 / self.v
        p1, p2, s2, s1 = w[0], w[1], w[-2], w[-1]
        pr_p1 = self._wb(self.c_p1, self.n, p1, p0)
        pr_p2_uni = self._wb(self.c_p2, self.n, p2, p0)
        c2 = self.c_p2_given_p1.get(p1)
        pr_p2 = self._wb(c2, sum(c2.values()), p2, pr_p2_uni) if c2 else pr_p2_uni

        pr_s1 = self._wb(self.c_s1, self.n, s1, p0)
        pr_s2_uni = self._wb(self.c_s2, self.n, s2, p0)
        cs2 = self.c_s2_given_s1.get(s1)
        pr_s2 = self._wb(cs2, sum(cs2.values()), s2, pr_s2_uni) if cs2 else pr_s2_uni
        return math.log2(pr_p1) + math.log2(pr_p2) + math.log2(pr_s1) + math.log2(pr_s2)

    def bits_per_word(self, words: list[Word]) -> float:
        usable = [w for w in words if len(w) >= 4]
        if not usable:
            return 0.0
        return -sum(self.log2(w) for w in usable) / len(usable)


def hebrew_verb_docs(conv: str, tables: r.Tables, signs: set) -> list[tuple[str, list[Word]]]:
    """OSHB finite verbs only (morphology starting with HV), grouped by chapter."""
    docs: dict[str, list] = collections.OrderedDict()
    for row in ct._rows(ct.OSHB):
        morph = str(row.get("morphology") or "")
        if morph.startswith("HV"):
            doc = lid._hebrew_doc(row["reference"])
            docs.setdefault(doc, []).append(ct.hebrew_segments(row["surface"]))
    written, _ = lid.written_docs(list(docs.items()), "hebrew", conv, tables, signs)
    return [(d, [w for w in ws if len(w) >= 4]) for d, ws in written if any(len(w) >= 4 for w in ws)]


def load_linear_a_votive_long(corpus_path: Path = CORPUS_PATH) -> list[Word]:
    """Undamaged >=4-sign words on non-administrative Linear A supports (Za/Zb/Zc/Zf/Zg), strict LB values."""
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    sign_table = a.load_signs()
    valid_signs = {k for k in sign_table.values() if isinstance(k, tuple)}
    out: list[Word] = []
    seen: set[Word] = set()
    for doc_id, rec in sorted(raw.items()):
        if not any(tag in doc_id for tag in ("Za", "Zb", "Zc", "Zf", "Zg")):
            continue
        for tok in rec.get("transliteratedWords") or []:
            if not isinstance(tok, str) or any(ch in tok for ch in "[]?*+0123456789/\· "):
                continue
            w = a.keys(tok, sign_table)
            if len(w) >= 4 and lid.valid(w, valid_signs) and w not in seen:
                seen.add(w)
                out.append(w)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--conv", choices=("plene", "omission"), default="plene")
    args = ap.parse_args()
    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt missing.", file=sys.stderr)
        return 2

    t0 = time.time()
    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)

    # Train equal-size >=4-sign verbal/long-word edge models across 5 arms
    heb_v = hebrew_verb_docs(args.conv, tables, signs)
    train_sets: dict[str, list[Word]] = {
        "semitic_verbs": sorted({w for _, ws in lid.select(heb_v, "train") for w in ws}),
    }
    dev_sets: dict[str, list[Word]] = {
        "semitic_verbs": sorted({w for _, ws in lid.select(heb_v, "dev") for w in ws}),
    }
    for arm, lang in (("greek", "diodorus"), ("anatolian", "hittite"), ("hurrian", "hurrian"), ("latin", "latin")):
        if lang == "diodorus":
            docs, _ = lid.diodorus_docs(signs)
        else:
            docs, _ = lid.written_docs(lid.segment_docs(lang), lang, args.conv, tables, signs)
        train_sets[arm] = sorted({w for _, ws in lid.select(docs, "train") for w in ws if len(w) >= 4})
        dev_sets[arm] = sorted({w for _, ws in lid.select(docs, "dev") for w in ws if len(w) >= 4})

    budget = min(len(v) for v in train_sets.values())
    rng = random.Random(20261122)
    models = {
        arm: EdgeFrameModel(rng.sample(ws, budget), alphabet)
        for arm, ws in train_sets.items()
    }

    # Calibration check on dev sets (100 random >=4-sign words per language)
    print(f"=== Kernel E Calibration (budget={budget} >=4-sign types/arm, {args.conv}) ===")
    cal_ok = True
    for arm, dws in dev_sets.items():
        sample = random.Random(f"cal:{arm}").sample(dws, min(80, len(dws)))
        fits = {m: round(mod.bits_per_word(sample), 3) for m, mod in models.items()}
        win = min(fits, key=fits.get)
        if win != arm:
            cal_ok = False
        print(f"  dev {arm:14s} -> winner={win:14s} | fits={fits}")

    # Target: Linear A non-administrative >=4-sign words + consonant-grid permutation
    la_long = load_linear_a_votive_long()
    obs_fits = {m: mod.bits_per_word(la_long) for m, mod in models.items()}
    obs_win = min(obs_fits, key=obs_fits.get)
    obs_margin = min(v for k, v in obs_fits.items() if k != "semitic_verbs") - obs_fits["semitic_verbs"]

    prng = random.Random(20261122)
    pmargins = []
    ge = 0
    for _ in range(args.n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        prng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        pw = [ad.permute_word(w, mp) for w in la_long]
        pf = {m: mod.bits_per_word(pw) for m, mod in models.items()}
        pm = min(v for k, v in pf.items() if k != "semitic_verbs") - pf["semitic_verbs"]
        pmargins.append(pm)
        if pm >= obs_margin - 1e-12:
            ge += 1
    mean = sum(pmargins) / len(pmargins)
    sd = math.sqrt(sum((x - mean) ** 2 for x in pmargins) / len(pmargins)) or 1e-9
    z = (obs_margin - mean) / sd
    p = (1 + ge) / (args.n_perm + 1)

    print(f"\n=== Kernel E Target: Linear A Votive >=4-sign words (n={len(la_long)}, B={args.n_perm}, {round(time.time()-t0,1)}s) ===")
    print(f"  cal_ok={cal_ok} | winner={obs_win} | fits={{ {', '.join(f'{k}: {v:.3f}' for k,v in obs_fits.items())} }}")
    print(f"  M(semitic_verbs)={obs_margin:+.4f} | perm_mean={mean:+.4f} | Z_perm={z:+.2f} | p_perm={p:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
