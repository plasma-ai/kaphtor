#!/usr/bin/env python3
"""Deterministic, zero-LLM Cypro-Minoan Kernels CM-I (Morphology) & CM-H (Clay-Ball Onomastics).

Runs strictly on shipped kaphtor datasets (zero external folders, zero Linear A leakage):
  - data/ane/cypro-minoan/{catalogue,translations,lexicon}.json
  - data/ane/ig-xv-1-cypriot/records.jsonl (Amathus Eteocypriot & Cypriot Syllabic Greek controls)
  - data/share-alike/{anatolian,cuneiform,greek,hebrew,latin,linear-b,oracc-levant}/
  - data/ane/kassite-concordances/entries.jsonl

Kernels:
  - CM-I1: 7-family multi-language rival-exclusion bound-affix margin permutation (cypriot_plene & omission)
  - CM-I2: 8-way size-matched (N=90 confirmed / N=64 undotted) word-final discriminative model
           pitting Amathus IG XV 1 Eteocypriot against all 7 vocalized ancient language families
  - CM-H:  7-way size-equalized clay-ball roster onomastics (calibrated on CM 3 RASH Atab 004)
           plus acrophonic initial-vs-final test on isolated single-sign clay-ball suffixes

Usage:
    python3 models/cypro-minoan-kernel/cm_kernel_ih.py manifest
    python3 models/cypro-minoan-kernel/cm_kernel_ih.py run [--perms 2000] [--out PATH]
    python3 models/cypro-minoan-kernel/cm_kernel_ih.py check --ledger runs/cm-kernel-ih-2026-11-25.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True

KERNEL_DIR = Path(__file__).resolve().parent
if str(KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(KERNEL_DIR))

import cm_kernel as ck

REPO = Path(__file__).resolve().parents[2]
CM_DIR = REPO / "data" / "ane" / "cypro-minoan"
IG_PATH = REPO / "data" / "ane" / "ig-xv-1-cypriot" / "records.jsonl"
LB_PATH = REPO / "data" / "share-alike" / "linear-b" / "linear_b_tokens.jsonl"
SHARE_DIR = REPO / "data" / "share-alike"
KASSITE_PATH = REPO / "data" / "ane" / "kassite-concordances" / "entries.jsonl"

VOWELS = ("a", "e", "i", "o", "u")
VSET = frozenset(VOWELS)
# Cypriot / Cypro-Minoan 11 consonant series (distinguishes l vs r; merges voicing/aspiration)
CM_SERIES = ("j", "k", "l", "m", "n", "p", "r", "s", "t", "w", "z")
CSET = frozenset(CM_SERIES)
ALPHABET: list[tuple[str, str]] = [("", v) for v in VOWELS] + [(c, v) for c in CM_SERIES for v in VOWELS]

Key = tuple[str, str]
Word = tuple[Key, ...]

GRK_MAP = {
    "α": "a", "ε": "e", "η": "e", "ι": "i", "ο": "o", "ω": "o", "υ": "u",
    "β": "p", "π": "p", "φ": "p",
    "γ": "k", "κ": "k", "χ": "k",
    "δ": "t", "τ": "t", "θ": "t",
    "ζ": "z", "ξ": "ks", "ψ": "ps",
    "λ": "l", "μ": "m", "ν": "n", "ρ": "r", "σ": "s", "ς": "s",
}

HEB_CONS = {
    "א": "", "ע": "", "ה": "", "ח": "k",
    "ב": "p", "פ": "p", "ף": "p",
    "ג": "k", "כ": "k", "ך": "k", "ק": "k",
    "ד": "t", "ט": "t", "ת": "t",
    "ו": "w", "י": "j",
    "ז": "z", "צ": "z", "ץ": "z",
    "ס": "s", "ש": "s",
    "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ר": "r",
}
HEB_VOW = {
    "\u05b7": "a", "\u05b8": "a", "\u05b2": "a",
    "\u05b5": "e", "\u05b6": "e", "\u05b1": "e",
    "\u05b4": "i",
    "\u05b9": "o", "\u05ba": "o", "\u05b3": "o",
    "\u05bb": "u",
}

LAT_CONS = {
    "b": "p", "p": "p", "f": "p", "v": "w", "w": "w",
    "c": "k", "k": "k", "g": "k", "q": "k", "h": "", "ḫ": "k", "ḥ": "k", "x": "ks",
    "d": "t", "t": "t", "ṭ": "t", "ṯ": "t", "ḏ": "t", "þ": "t",
    "z": "z", "ṣ": "z", "ẓ": "z",
    "s": "s", "š": "s", "ś": "s",
    "l": "l", "m": "m", "n": "n", "ŋ": "n", "ĝ": "n", "r": "r", "y": "j", "j": "j",
}


def _strip_accents_keep_sem(s: str) -> str:
    out = []
    for ch in s:
        if ch in "šśḫḥṭṣṯḏẓŋĝ":
            out.append(ch)
        else:
            decomp = unicodedata.normalize("NFD", ch)
            out.append("".join(c for c in decomp if unicodedata.category(c) != "Mn"))
    return "".join(out)


def phonemes_to_cm_cv(segs: list[str], mode: str = "cypriot_plene") -> Word | None:
    """Render phoneme sequence into Cypriot 11-series CV tuples with automatic -Ci-jV-/-Cu-wV- glides."""
    if not segs:
        return None
    syls: list[Key] = []
    i = 0
    n = len(segs)
    while i < n:
        s = segs[i]
        if s in VSET:
            if syls and syls[-1][1] == "i":
                syls.append(("j", s))
            elif syls and syls[-1][1] == "u":
                syls.append(("w", s))
            else:
                syls.append(("", s))
            i += 1
        elif s in CSET:
            if i + 1 < n and segs[i + 1] in VSET:
                syls.append((s, segs[i + 1]))
                i += 2
            else:
                if mode == "cypriot_plene":
                    nxt_v = None
                    for k in range(i + 1, min(i + 3, n)):
                        if segs[k] in VSET:
                            nxt_v = segs[k]
                            break
                    syls.append((s, nxt_v if nxt_v is not None else "e"))
                i += 1
        else:
            i += 1
    return tuple(syls) if len(syls) >= 2 else None


def latin_cuneiform_to_segs(word: str) -> list[str]:
    w = _strip_accents_keep_sem(word.lower())
    w = re.sub(r"[^a-zšśḫḥṭṣṯḏẓŋĝ]", "", w)
    segs: list[str] = []
    for ch in w:
        if ch in VSET:
            if not segs or segs[-1] != ch:
                segs.append(ch)
        elif ch in LAT_CONS:
            for m in LAT_CONS[ch]:
                if m in CSET and (not segs or segs[-1] != m):
                    segs.append(m)
    return segs


def greek_to_segs(word: str) -> list[str]:
    w = "".join(c for c in unicodedata.normalize("NFD", word.lower()) if unicodedata.category(c) != "Mn")
    segs: list[str] = []
    for ch in w:
        mapped = GRK_MAP.get(ch)
        if not mapped:
            continue
        for c in mapped:
            if (c in VSET or c in CSET) and (not segs or segs[-1] != c):
                segs.append(c)
    return segs


def _has_heb_vowel_before_next_cons(s: str, start: int) -> bool:
    """Return True iff a Hebrew vowel mark occurs before the next Hebrew consonant."""
    for k in range(start, len(s)):
        if s[k] in HEB_CONS:
            return False
        if s[k] in HEB_VOW:
            return True
    return False


def hebrew_to_segs(surface: str) -> list[str]:
    """Convert vocalized OSHB Hebrew surface to phoneme segments, handling matres lectionis (ו/י) cleanly."""
    s = surface.replace("/", "")
    segs: list[str] = []
    n = len(s)
    for idx, ch in enumerate(s):
        if ch in HEB_CONS:
            # Mater lectionis: holam male (ו + \u05b9/\u05ba) or true shuruq (ו + \u05bc with no vowel before next cons)
            if ch == "ו" and idx + 1 < n:
                if s[idx + 1] in ("\u05b9", "\u05ba"):
                    continue
                if s[idx + 1] == "\u05bc" and not _has_heb_vowel_before_next_cons(s, idx + 2):
                    continue
            # Mater lectionis: yod after hireq/tsere/segol with no vowel before the next consonant -> long vowel, no 'j'
            if ch == "י" and segs and segs[-1] in ("i", "e"):
                if not _has_heb_vowel_before_next_cons(s, idx + 1):
                    continue
            m = HEB_CONS[ch]
            if m:
                segs.append(m)
        elif ch in HEB_VOW:
            v = HEB_VOW[ch]
            if not segs or segs[-1] != v:
                segs.append(v)
        elif ch == "\u05bc" and idx > 0 and s[idx - 1] == "ו" and not _has_heb_vowel_before_next_cons(s, idx + 1):
            if not segs or segs[-1] != "u":
                segs.append("u")
    return segs


def str_tuple_to_word(w: tuple[str, ...]) -> Word | None:
    if len(w) < 2 or not all(1 <= len(s) <= 2 for s in w):
        return None
    keys = [ck.split_cv(s) for s in w]
    if all((c == "" or c in CSET) and v in VSET for c, v in keys):
        return tuple(keys)
    return None


def parse_ig_cypriot_greek(ig_path: Path = IG_PATH) -> list[Word]:
    """Parse unbroken Cypriot Syllabic Greek L >= 2 word types from IG XV 1 as an in-script calibration gate."""
    words: set[Word] = set()
    for line in ig_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        for ed in rec.get("editions") or []:
            lbl = (ed.get("language_label") or "").lower()
            if "greek" not in lbl or "eteo" in lbl:
                continue
            if (ed.get("script_label") or "").lower() != "cypriot syllabic":
                continue
            joined = ck._split_glued_linebreaks(ed.get("text") or "")
            toks = [t for t in re.split(r"[\s·•:∣|]+", joined) if t]
            for i, tok in enumerate(toks):
                if (i > 0 and toks[i - 1].endswith("]")) or (i + 1 < len(toks) and toks[i + 1].startswith("[")):
                    continue
                tc = tok.strip(",;()<>")
                if not tc or tc.isdigit() or any(ch in tc for ch in ".[]?…*‒"):
                    continue
                if tc.startswith("-") or tc.endswith("-"):
                    continue
                parts = [ck.norm_syl(p) for p in tc.split("-") if p.strip()]
                if len(parts) >= 2 and all(
                    re.fullmatch(r"[a-z]{1,2}", p) and p[-1] in VSET and (len(p) == 1 or p[0] in CSET)
                    for p in parts
                ):
                    w = str_tuple_to_word(tuple(parts))
                    if w:
                        words.add(w)
    return sorted(words)


def load_vocalized_families(
    mode: str = "cypriot_plene",
    cap: int = 2500,
    seed: int = 20261125,
    share_dir: Path = SHARE_DIR,
) -> dict[str, list[Word]]:
    """Load the 7 shipped vocalized ancient language families rendered into Cypriot 11-series CV space."""
    fams: dict[str, set[Word]] = collections.defaultdict(set)

    # 1. Greek (Perseus Diodorus Books 1-5 inflected prose)
    for line in (share_dir / "greek" / "diodorus_1_5.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        txt = json.loads(line).get("text") or ""
        for tok in re.findall(r"[α-ωΑ-Ωά-ώΆ-Ώἀ-ῼ]+", txt):
            w = phonemes_to_cm_cv(greek_to_segs(tok), mode=mode)
            if w:
                fams["greek"].add(w)

    # 2. Semitic: 50/50 balanced OSHB Hebrew + ORACC Akkadian
    heb_set: set[Word] = set()
    for line in (share_dir / "hebrew" / "oshb_words.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        w = phonemes_to_cm_cv(hebrew_to_segs(json.loads(line).get("surface") or ""), mode=mode)
        if w:
            heb_set.add(w)
    akk_set: set[Word] = set()
    for line in (share_dir / "cuneiform" / "oracc_akkadian.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        for tok in json.loads(line).get("tokens") or []:
            norm = tok.get("norm") or ""
            if norm and norm != "X":
                w = phonemes_to_cm_cv(latin_cuneiform_to_segs(norm), mode=mode)
                if w:
                    akk_set.add(w)

    # 3. Anatolian (Hittite/Luwian), Hurrian, Hattic (TLHdig)
    for line in (share_dir / "anatolian" / "tlhdig_docs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        lg = row.get("language") or ""
        fam = (
            "anatolian"
            if lg in ("Hit", "Luw")
            else ("hurrian" if lg == "Hur" else ("hattic" if lg in ("Hat", "Hattian") else None))
        )
        if not fam:
            continue
        for tok in row.get("words") or []:
            if not tok or tok.isupper():
                continue
            w = phonemes_to_cm_cv(latin_cuneiform_to_segs(tok), mode=mode)
            if w:
                fams[fam].add(w)

    # 4. Sumerian (ORACC): strictly lowercase phonetic forms (reject ORACC morphological gloss codes)
    sux_clean_re = re.compile(r"^[a-zšŋĝḫṭṣāēīōūâêîôû-]+$")
    for line in (share_dir / "cuneiform" / "oracc_sumerian.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        for tok in json.loads(line).get("tokens") or []:
            norm = (tok.get("norm") or "").strip()
            if norm and sux_clean_re.fullmatch(norm):
                w = phonemes_to_cm_cv(latin_cuneiform_to_segs(norm), mode=mode)
                if w:
                    fams["sumerian"].add(w)

    # 5. Latin (LatInfLexi): deduplicate unique clean alphabetic forms across all 816k rows first (zero multiplicity/DEF bias)
    lat_orth_re = re.compile(r'"orth_form"\s*:\s*"([A-Za-z]+)"')
    lat_orths: set[str] = set()
    with (share_dir / "latin" / "latinf_forms.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            m = lat_orth_re.search(line)
            if m:
                lat_orths.add(m.group(1).lower())
    for orth in sorted(lat_orths):
        w = phonemes_to_cm_cv(latin_cuneiform_to_segs(orth), mode=mode)
        if w:
            fams["latin"].add(w)

    rng = random.Random(seed)
    out: dict[str, list[Word]] = {}
    heb_l, akk_l = sorted(heb_set), sorted(akk_set)
    half = cap // 2
    sem_s = set(rng.sample(heb_l, min(half, len(heb_l)))) | set(rng.sample(akk_l, min(cap - half, len(akk_l))))
    out["semitic"] = sorted(sem_s)
    for fam in sorted(fams):
        lst = sorted(fams[fam])
        out[fam] = sorted(rng.sample(lst, cap)) if len(lst) > cap else lst
    return out


def extract_bound_affixes(words: list[Word]) -> dict:
    """Extract strict one-sided morphological affixes from distinct L >= 2 word types."""
    types = sorted({w for w in words if len(w) >= 2})
    tset = set(types)
    n_pre = 0
    n_suf = 0
    pre_keys: list[Key] = []
    suf_keys: list[Key] = []
    seen: set[tuple[Word, Word]] = set()
    for w in types:
        for alen in (1, 2):
            if len(w) - alen < 2:
                continue
            if w[alen:] in tset and (w[alen:], w) not in seen:
                seen.add((w[alen:], w))
                n_pre += 1
                pre_keys.append(w[0])
            if w[:-alen] in tset and (w[:-alen], w) not in seen:
                seen.add((w[:-alen], w))
                n_suf += 1
                suf_keys.append(w[-1])
    by_t3: dict[Word, list[Word]] = collections.defaultdict(list)
    by_h3: dict[Word, list[Word]] = collections.defaultdict(list)
    for w in types:
        if len(w) >= 4:
            by_t3[w[1:]].append(w)
            by_h3[w[:-1]].append(w)
    for key in sorted(by_t3):
        grp = by_t3[key]
        if 2 <= len(grp) <= 8:
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    if (grp[i], grp[j]) not in seen:
                        seen.add((grp[i], grp[j]))
                        n_pre += 1
                        pre_keys.extend([grp[i][0], grp[j][0]])
    for key in sorted(by_h3):
        grp = by_h3[key]
        if 2 <= len(grp) <= 8:
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    if (grp[i], grp[j]) not in seen:
                        seen.add((grp[i], grp[j]))
                        n_suf += 1
                        suf_keys.extend([grp[i][-1], grp[j][-1]])
    return {
        "n_pre": n_pre,
        "n_suf": n_suf,
        "pre_rate": round(n_pre / (n_pre + n_suf), 4) if (n_pre + n_suf) else 0.0,
        "pre_cv": dict(sorted(collections.Counter(pre_keys).items())),
        "suf_cv": dict(sorted(collections.Counter(suf_keys).items())),
        "n_pre_cv": len(pre_keys),
        "n_suf_cv": len(suf_keys),
    }


class BoundAffixModel:
    """Dirichlet-smoothed polarity + bound CV-sign affix model over Cypriot 11-series alphabet."""

    def __init__(self, feats: dict, alpha: float = 0.5):
        n_pre, n_suf = feats["n_pre"], feats["n_suf"]
        self.p_pre = (n_pre + 1.0) / (n_pre + n_suf + 2.0)
        self.p_suf = 1.0 - self.p_pre
        v = len(ALPHABET)
        self.pre_d = {k: (feats["pre_cv"].get(k, 0) + alpha) / (feats["n_pre_cv"] + alpha * v) for k in ALPHABET}
        self.suf_d = {k: (feats["suf_cv"].get(k, 0) + alpha) / (feats["n_suf_cv"] + alpha * v) for k in ALPHABET}
        self.fl_pre = alpha / (feats["n_pre_cv"] + alpha * v)
        self.fl_suf = alpha / (feats["n_suf_cv"] + alpha * v)

    def score(self, feats: dict, perm: dict[str, str] | None = None) -> tuple[float, float]:
        ll_pol = feats["n_pre"] * math.log(self.p_pre) + feats["n_suf"] * math.log(self.p_suf)
        ll_cv = 0.0
        for (c, v), cnt in feats["pre_cv"].items():
            mk = (perm.get(c, c), v) if perm else (c, v)
            ll_cv += cnt * math.log(self.pre_d.get(mk, self.fl_pre))
        for (c, v), cnt in feats["suf_cv"].items():
            mk = (perm.get(c, c), v) if perm else (c, v)
            ll_cv += cnt * math.log(self.suf_d.get(mk, self.fl_suf))
        return ll_pol, ll_cv


def _make_series_perms(n_perm: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    perms = []
    for _ in range(n_perm):
        sh = list(CM_SERIES)
        rng.shuffle(sh)
        perms.append(dict(zip(CM_SERIES, sh)))
    return perms


def eval_kernel_i1(
    words: list[Word],
    models: dict[str, BoundAffixModel],
    perms: list[dict[str, str]],
) -> dict:
    """Kernel CM-I1: 7-family bound-affix discriminative margin permutation."""
    feats = extract_bound_affixes(words)
    n_perm = len(perms)
    obs_j: dict[str, float] = {}
    null_j: dict[str, list[float]] = {}
    for fam in sorted(models):
        m = models[fam]
        lp, lc = m.score(feats)
        obs_j[fam] = lp + lc
        null_j[fam] = [lp + m.score(feats, p)[1] for p in perms]

    fams = sorted(models)
    fam_out: dict[str, dict] = {}
    for fam in fams:
        om = obs_j[fam] - max(obs_j[r] for r in fams if r != fam)
        nm = [null_j[fam][i] - max(null_j[r][i] for r in fams if r != fam) for i in range(n_perm)]
        mu = sum(nm) / n_perm
        sd = math.sqrt(max(sum((x - mu) ** 2 for x in nm) / n_perm, 1e-12))
        pm = (sum(1 for x in nm if x >= om - 1e-12) + 1) / (n_perm + 1)
        fam_out[fam] = {
            "ll_joint": round(obs_j[fam], 3),
            "margin_obs": round(om, 3),
            "z_margin": round((om - mu) / sd, 2),
            "p_margin": round(pm, 5),
        }
    ranked = sorted(fams, key=lambda f: (-obs_j[f], f))
    return {
        "n_types": len(words),
        "n_pre": feats["n_pre"],
        "n_suf": feats["n_suf"],
        "pre_rate": feats["pre_rate"],
        "winner": ranked[0],
        "winner_margin": fam_out[ranked[0]]["margin_obs"],
        "winner_p_margin": fam_out[ranked[0]]["p_margin"],
        "families": fam_out,
    }


def _end1_dist(words: list[Word], alpha: float = 0.5) -> dict[Key, float]:
    cnt = collections.Counter(w[-1] for w in words if len(w) >= 2)
    tot = sum(cnt.values())
    v = len(ALPHABET)
    return {k: (cnt.get(k, 0) + alpha) / (tot + alpha * v) for k in ALPHABET}


def build_i2_log_dists(
    fam_words: dict[str, list[Word]],
    ec_words: list[Word],
    draws: int = 200,
    seed: int = 20261125,
) -> dict[str, dict[Key, float]]:
    """Size-equalize every arm to len(ec_words) using unbiased expected log-probabilities mean_d(log P_d).

    Averaging in log-probability space avoids Jensen's inequality bias (averaging raw probabilities
    before log erases sampling zeros for large arms and unfairly boosts them against single-sample EC).
    """
    n_ec = len(ec_words)
    rng = random.Random(seed)
    ec_d = _end1_dist(ec_words, alpha=0.5)
    log_dists: dict[str, dict[Key, float]] = {"amathus_ec": {k: math.log(ec_d[k]) for k in ALPHABET}}
    for fam in sorted(fam_words):
        fw = fam_words[fam]
        acc: dict[Key, float] = {k: 0.0 for k in ALPHABET}
        for _ in range(draws):
            sub = rng.sample(fw, min(n_ec, len(fw)))
            d = _end1_dist(sub, alpha=0.5)
            for k in ALPHABET:
                acc[k] += math.log(d[k]) / draws
        log_dists[fam] = acc
    return log_dists


def eval_kernel_i2(
    words: list[Word],
    log_dists: dict[str, dict[Key, float]],
    perms: list[dict[str, str]],
) -> dict:
    """Kernel CM-I2: 8-way size-matched word-final discriminative margin permutation (incl. Amathus EC)."""
    end_c = dict(sorted(collections.Counter(w[-1] for w in words if len(w) >= 2).items()))
    n_perm = len(perms)

    def score_ld(ld: dict[Key, float], perm: dict[str, str] | None = None) -> float:
        s = 0.0
        for (c, v), cnt in end_c.items():
            if c and c not in CSET:
                continue
            mk = (perm.get(c, c), v) if perm else (c, v)
            s += cnt * ld[mk]
        return s

    fams = sorted(log_dists)
    obs = {f: score_ld(log_dists[f]) for f in fams}
    nulls = {f: [score_ld(log_dists[f], p) for p in perms] for f in fams}
    fam_out: dict[str, dict] = {}
    for fam in fams:
        om = obs[fam] - max(obs[r] for r in fams if r != fam)
        nm = [nulls[fam][i] - max(nulls[r][i] for r in fams if r != fam) for i in range(n_perm)]
        mu = sum(nm) / n_perm
        sd = math.sqrt(max(sum((x - mu) ** 2 for x in nm) / n_perm, 1e-12))
        pm = (sum(1 for x in nm if x >= om - 1e-12) + 1) / (n_perm + 1)
        fam_out[fam] = {
            "ll": round(obs[fam], 3),
            "margin_obs": round(om, 3),
            "z_margin": round((om - mu) / sd, 2),
            "p_margin": round(pm, 5),
        }
    ranked = sorted(fams, key=lambda f: (-obs[f], f))
    return {
        "n_types": len(words),
        "winner": ranked[0],
        "winner_margin": fam_out[ranked[0]]["margin_obs"],
        "winner_p_margin": fam_out[ranked[0]]["p_margin"],
        "amathus_ec_margin": fam_out["amathus_ec"]["margin_obs"],
        "amathus_ec_p_margin": fam_out["amathus_ec"]["p_margin"],
        "families": fam_out,
    }


def _witten_bell_scorer(words: list[Word]):
    u: collections.Counter[Key] = collections.Counter()
    b: collections.Counter[tuple[Key, Key]] = collections.Counter()
    b_ctx: collections.Counter[Key] = collections.Counter()
    b_types: dict[Key, set[Key]] = collections.defaultdict(set)
    bos: Key = ("<BOS>", "")
    eos: Key = ("<EOS>", "")
    for w in words:
        seq = (bos, *w, eos)
        for i in range(1, len(seq)):
            u[seq[i]] += 1
            b[(seq[i - 1], seq[i])] += 1
            b_ctx[seq[i - 1]] += 1
            b_types[seq[i - 1]].add(seq[i])
    tot_u = sum(u.values())
    v = len(ALPHABET) + 1

    def bits(w: Word, perm: dict[str, str] | None = None) -> float:
        mw = tuple((perm.get(c, c), vw) for c, vw in w) if perm else w
        seq = (bos, *mw, eos)
        tot = 0.0
        for i in range(1, len(seq)):
            p1 = (u[seq[i]] + 0.5) / (tot_u + 0.5 * v)
            ctx = seq[i - 1]
            c_ctx = b_ctx[ctx]
            if c_ctx > 0:
                lam = c_ctx / (c_ctx + len(b_types[ctx]))
                p2 = lam * (b[(ctx, seq[i])] / c_ctx) + (1.0 - lam) * p1
            else:
                p2 = p1
            tot += -math.log2(p2)
        return tot / (len(w) + 1)

    return bits


def load_onomastic_pools(
    ec_l2: list[Word],
    cgk: list[Word],
    lb: list[Word],
    fams_plene: dict[str, list[Word]],
    share_dir: Path = SHARE_DIR,
    kassite_path: Path = KASSITE_PATH,
) -> dict[str, list[Word]]:
    lev: set[Word] = set()
    for line in (share_dir / "oracc-levant" / "name_occurrences.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("damaged") or row.get("qpn_pos") not in ("PN", "RN"):
            continue
        form = str(row.get("normalized_form") or row.get("name") or "")
        if not form or "OR" in form:
            continue
        w = phonemes_to_cm_cv(latin_cuneiform_to_segs(form), mode="cypriot_plene")
        if w:
            lev.add(w)

    kas: set[Word] = set()
    for line in kassite_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("kind") != "person":
            continue
        form = str(row.get("normalized_key") or row.get("headword") or "")
        if not form or "(" in form or "?" in form:
            continue
        w = phonemes_to_cm_cv(latin_cuneiform_to_segs(form), mode="cypriot_plene")
        if w:
            kas.add(w)

    return {
        "amathus_ec": sorted(ec_l2),
        "anatolian": sorted(fams_plene["anatolian"]),
        "cypriot_greek": sorted(cgk),
        "hurrian": sorted(fams_plene["hurrian"]),
        "kassite": sorted(kas),
        "levant_semitic": sorted(lev),
        "mycenaean_lb": sorted(lb),
    }


def run_kernel_h_clay_balls(
    pools: dict[str, list[Word]],
    cm1_words: list[Word],
    cm_dir: Path = CM_DIR,
    n_perm: int = 1000,
    seed: int = 20261125,
) -> dict:
    """Kernel CM-H: 7-way size-equalized clay-ball onomastics + acrophony test."""
    n_target = len(pools["amathus_ec"])
    scorers = {}
    for idx, fam in enumerate(sorted(pools)):
        words = pools[fam]
        rng_f = random.Random(seed + 500 + idx)
        if len(words) <= n_target:
            models = [_witten_bell_scorer(words)]
        else:
            models = [_witten_bell_scorer(rng_f.sample(words, n_target)) for _ in range(10)]

        def make_scorer(ms):
            def _sc(target: list[Word], perm: dict[str, str] | None = None) -> float:
                return sum(sum(m(w, perm) for w in target) / len(target) for m in ms) / len(ms)
            return _sc

        scorers[fam] = make_scorer(models)

    cat = json.loads((cm_dir / "catalogue.json").read_text(encoding="utf-8"))
    tr = json.loads((cm_dir / "translations.json").read_text(encoding="utf-8"))["translations"]
    seq1, seq2, iso, rash004 = [], [], [], []
    for sig, rec in sorted(tr.items()):
        if sig == "RASH Atab 004":
            for w in rec["words"]:
                vals = [ck.norm_syl(v) for v in (w.get("values") or [])]
                if len(vals) >= 3:
                    kw = str_tuple_to_word(tuple(vals))
                    if kw:
                        rash004.append(kw)
        if cat[sig].get("type_code") != "Abou":
            continue
        ws = rec["words"]
        if ws and ws[0].get("values"):
            v1 = [ck.norm_syl(v) for v in ws[0]["values"]]
            kw = str_tuple_to_word(tuple(v1))
            if kw:
                seq1.append(kw)
        if len(ws) == 2 and ws[1].get("values"):
            v2 = [ck.norm_syl(v) for v in ws[1]["values"]]
            if len(v2) == 1 and re.fullmatch(r"[a-z]{1,2}", v2[0]) and v2[0][-1] in VSET:
                c, v = ck.split_cv(v2[0])
                if c == "" or c in CSET:
                    iso.append((c, v))
            elif len(v2) >= 2:
                kw = str_tuple_to_word(tuple(v2))
                if kw:
                    seq2.append(kw)

    perms = _make_series_perms(n_perm, seed + 808)
    arm_results = {}
    for key, target in (
        ("ctrl_rash_atab_004_cm3", rash004),
        ("cm1_clay_ball_seq1", seq1),
        ("cm1_clay_ball_seq2", seq2),
    ):
        obs_raw = {f: scorers[f](target) for f in sorted(scorers)}
        ranked = sorted(obs_raw.items(), key=lambda kv: (kv[1], kv[0]))
        w1 = ranked[0][0]
        obs_m = ranked[1][1] - ranked[0][1]
        ge = 0
        for p in perms:
            ps = {f: scorers[f](target, p) for f in sorted(scorers)}
            pm = min(v for f, v in ps.items() if f != w1) - ps[w1]
            if pm >= obs_m - 1e-12:
                ge += 1
        arm_results[key] = {
            "n_words": len(target),
            "winner": w1,
            "margin_bits": round(obs_m, 4),
            "p_margin_perm": round((ge + 1) / (n_perm + 1), 5),
            "bits_per_sign": {f: round(v, 4) for f, v in sorted(obs_raw.items())},
        }

    # Acrophonic test on the 19 isolated single signs on multi | single clay balls
    init_c = collections.Counter(w[0] for w in cm1_words)
    fin_c = collections.Counter(w[-1] for w in cm1_words)
    med_c = collections.Counter(s for w in cm1_words for s in w[1:-1])

    def ll_pos(seq: list[Key], pool: collections.Counter[Key]) -> float:
        tot = sum(pool.values())
        v = len(ALPHABET)
        return sum(math.log((pool.get(k, 0) + 0.5) / (tot + 0.5 * v)) for k in seq)

    ll_init = ll_pos(iso, init_c)
    ll_med = ll_pos(iso, med_c)
    ll_fin = ll_pos(iso, fin_c)
    obs_dll = ll_init - ll_fin

    rng_a = random.Random(seed + 909)
    all_cm1 = [s for w in cm1_words for s in w]
    fin_cm1 = [w[-1] for w in cm1_words]
    n_boot = 5000
    ge_all = 0
    ge_fin = 0
    for _ in range(n_boot):
        d1 = rng_a.choices(all_cm1, k=len(iso))
        if ll_pos(d1, init_c) - ll_pos(d1, fin_c) >= obs_dll - 1e-12:
            ge_all += 1
        d2 = rng_a.choices(fin_cm1, k=len(iso))
        if ll_pos(d2, init_c) - ll_pos(d2, fin_c) >= obs_dll - 1e-12:
            ge_fin += 1

    iso_set = set(iso)
    s2_inits = [w[0] for w in seq2]
    hits_s2 = sum(1 for x in s2_inits if x in iso_set)
    p_base = sum(1 for w in cm1_words if w[0] in iso_set) / max(len(cm1_words), 1)
    p_binom_s2 = sum(
        math.comb(len(s2_inits), k) * (p_base ** k) * ((1.0 - p_base) ** (len(s2_inits) - k))
        for k in range(hits_s2, len(s2_inits) + 1)
    )

    return {
        "size_equalized_budget": n_target,
        "onomastics": arm_results,
        "acrophony": {
            "n_isolated_signs": len(iso),
            "n_distinct_isolated_signs": len(iso_set),
            "ll_initial": round(ll_init, 3),
            "ll_medial": round(ll_med, 3),
            "ll_final": round(ll_fin, 3),
            "delta_ll_init_minus_fin": round(obs_dll, 3),
            "p_vs_final_pool": round((ge_fin + 1) / (n_boot + 1), 5),
            "p_vs_all_positions_pool": round((ge_all + 1) / (n_boot + 1), 5),
            "seq2_initial_overlap": hits_s2,
            "seq2_total": len(s2_inits),
            "cm1_init_baseline_rate": round(p_base, 4),
            "p_binom_seq2_overlap": round(p_binom_s2, 5),
        },
    }


def build_manifest(
    cm_dir: Path = CM_DIR,
    ig_path: Path = IG_PATH,
    share_dir: Path = SHARE_DIR,
    kassite_path: Path = KASSITE_PATH,
) -> dict:
    files = {
        "cm_catalogue": cm_dir / "catalogue.json",
        "cm_translations": cm_dir / "translations.json",
        "cm_lexicon": cm_dir / "lexicon.json",
        "ig_xv_1": ig_path,
        "tlhdig_anatolian": share_dir / "anatolian" / "tlhdig_docs.jsonl",
        "oracc_akkadian": share_dir / "cuneiform" / "oracc_akkadian.jsonl",
        "oracc_sumerian": share_dir / "cuneiform" / "oracc_sumerian.jsonl",
        "diodorus_greek": share_dir / "greek" / "diodorus_1_5.jsonl",
        "oshb_hebrew": share_dir / "hebrew" / "oshb_words.jsonl",
        "latinf_latin": share_dir / "latin" / "latinf_forms.jsonl",
        "linear_b_damos": share_dir / "linear-b" / "linear_b_tokens.jsonl",
        "oracc_levant_names": share_dir / "oracc-levant" / "name_occurrences.jsonl",
        "kassite_names": kassite_path,
    }
    return {
        "schema_version": 1,
        "firewall": "Cypro-Minoan only: reads zero data/linear-a/ files and zero models/language-id-kernel/ modules.",
        "t5_compliant": True,
        "inputs": {
            name: {"path": str(p.relative_to(REPO)), "sha256": ck.sha256_file(p), "bytes": p.stat().st_size}
            for name, p in sorted(files.items())
        },
    }


def run_suite_ih(
    n_perm_i: int = 2000,
    n_perm_h: int = 1000,
    seed: int = 20261125,
    cm_dir: Path = CM_DIR,
    ig_path: Path = IG_PATH,
    share_dir: Path = SHARE_DIR,
    kassite_path: Path = KASSITE_PATH,
) -> dict:
    cgk = parse_ig_cypriot_greek(ig_path)
    lb = [w for raw in ck.load_linear_b_types(share_dir / "linear-b" / "linear_b_tokens.jsonl") if (w := str_tuple_to_word(raw))]
    ec_conf = [w for raw in ck.parse_ig_amathus(ig_path, exclude_dotted=False) if len(raw) >= 2 and (w := str_tuple_to_word(raw))]
    ec_undot = [w for raw in ck.parse_ig_amathus(ig_path, exclude_dotted=True) if len(raw) >= 2 and (w := str_tuple_to_word(raw))]

    cm_val = {k: [w for raw in v if (w := str_tuple_to_word(raw))] for k, v in ck.load_cm_word_types(cm_dir, "valerio").items()}
    cm_dav = {k: [w for raw in v if (w := str_tuple_to_word(raw))] for k, v in ck.load_cm_word_types(cm_dir, "davis").items()}
    cm_hoc = {k: [w for raw in v if (w := str_tuple_to_word(raw))] for k, v in ck.load_cm_word_types(cm_dir, "hochymin").items()}

    perms_i = _make_series_perms(n_perm_i, seed)
    i_modes: dict[str, dict] = {}
    fams_plene_cache: dict[str, list[Word]] = {}

    for m_idx, mode in enumerate(("cypriot_plene", "omission")):
        fams = load_vocalized_families(mode=mode, cap=2500, seed=seed, share_dir=share_dir)
        if mode == "cypriot_plene":
            fams_plene_cache = fams
        models_i1 = {fam: BoundAffixModel(extract_bound_affixes(ws)) for fam, ws in sorted(fams.items())}
        dists_i2_conf = build_i2_log_dists(fams, ec_conf, draws=200, seed=seed + 100 + m_idx)
        dists_i2_undot = build_i2_log_dists(fams, ec_undot, draws=200, seed=seed + 200 + m_idx)

        targets_i1 = {
            "calib_cypriot_greek_ig_xv_1": cgk,
            "calib_damos_linear_b": lb,
            "cm12_valerio_emended": cm_val["CM 1+2"],
            "cm12_davis_unsplit": cm_dav["CM 1+2"],
            "cm12_hochymin_unsplit": cm_hoc["CM 1+2"],
            "cm2_only_valerio": cm_val["CM 2"],
            "cm3_ugarit_control": cm_val["CM 3"],
        }
        targets_i2 = {
            **targets_i1,
            "cm1_only_valerio": cm_val["CM 1"],
        }
        i_modes[mode] = {
            "train_counts": {fam: len(ws) for fam, ws in sorted(fams.items())},
            "kernel_cm_i1_rival_exclusion": {
                k: eval_kernel_i1(ws, models_i1, perms_i) for k, ws in targets_i1.items()
            },
            "kernel_cm_i2_amathus_confirmed_8way": {
                k: eval_kernel_i2(ws, dists_i2_conf, perms_i) for k, ws in targets_i2.items()
            },
            "kernel_cm_i2_amathus_undotted_8way": {
                k: eval_kernel_i2(ws, dists_i2_undot, perms_i)
                for k, ws in (
                    ("calib_cypriot_greek_ig_xv_1", cgk),
                    ("cm12_valerio_emended", cm_val["CM 1+2"]),
                    ("cm12_davis_unsplit", cm_dav["CM 1+2"]),
                    ("cm12_hochymin_unsplit", cm_hoc["CM 1+2"]),
                    ("cm3_ugarit_control", cm_val["CM 3"]),
                )
            },
        }

    pools_h = load_onomastic_pools(ec_conf, cgk, lb, fams_plene_cache, share_dir=share_dir, kassite_path=kassite_path)
    kernel_h = run_kernel_h_clay_balls(pools_h, cm_val["CM 1"], cm_dir=cm_dir, n_perm=n_perm_h, seed=seed)

    return {
        "schema_version": 1,
        "seed": seed,
        "permutations_i": n_perm_i,
        "permutations_h": n_perm_h,
        "note_egyptian": "TLA/ORAEC Egyptian is consonantal (unvocalized) and omitted from vocalized CV models to avoid synthetic vowel insertion.",
        "manifest": build_manifest(cm_dir, ig_path, share_dir, kassite_path),
        "corpora_counts": {
            "ig_cypriot_greek_l2": len(cgk),
            "ig_amathus_ec_confirmed_l2": len(ec_conf),
            "ig_amathus_ec_undotted_l2": len(ec_undot),
            "linear_b_clean_l2": len(lb),
            "cm_valerio_l2": {k: len(v) for k, v in sorted(cm_val.items())},
        },
        "kernel_cm_i": i_modes,
        "kernel_cm_h_clay_balls": kernel_h,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Cypro-Minoan Kernels CM-I and CM-H.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest", help="Print SHA-256 manifest of shipped inputs.")
    p_run = sub.add_parser("run", help="Run CM-I1, CM-I2, and CM-H.")
    p_run.add_argument("--perms-i", type=int, default=2000)
    p_run.add_argument("--perms-h", type=int, default=1000)
    p_run.add_argument("--seed", type=int, default=20261125)
    p_run.add_argument("--out", type=Path, default=None)
    p_chk = sub.add_parser("check", help="Verify a pinned run ledger against current shipped inputs.")
    p_chk.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.cmd == "manifest":
        print(json.dumps(build_manifest(), indent=2))
        return 0
    if args.cmd == "run":
        res = run_suite_ih(n_perm_i=args.perms_i, n_perm_h=args.perms_h, seed=args.seed)
        text = json.dumps(res, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(text)
        return 0
    if args.cmd == "check":
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        cur = build_manifest()
        if ledger["manifest"]["inputs"] != cur["inputs"]:
            print("STALE: shipped input SHA-256 mismatch against ledger", file=sys.stderr)
            return 1
        print(f"OK: {args.ledger.name} matches all {len(cur['inputs'])} shipped input SHA-256 pins")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
