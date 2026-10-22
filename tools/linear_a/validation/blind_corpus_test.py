#!/usr/bin/env python3
"""Blind Corpus Test — locked-lexicon out-of-sample reading of untranslated inscriptions.

Report-only. Reads the frozen partition (data/linear-a/blind-corpus-partition.json,
pre-registered before any scoring run; its `locked_tag` names the lock) and scores
every untranslated substantive inscription under two symmetric arms:

  NWS arm     locked lexicon roots + semitic_roots + Amorite + Ugaritic contact DBs,
              SEMITIC_DISTANCES, guttural transparency
  Luwian arm  luwian_roots + Anatolian contact DB, LUWIAN_DISTANCES,
              guttural transparency (parity with the existing null_model_audit)

Composite score per inscription: S = 0.5*LMR + 0.3*GC + 0.2*CF
  LMR  share of scorable word-tokens (skeleton >= 2 consonants) with a DB match
       at weighted distance <= 0.3
  GC   share of adjacent scored-token pairs whose inferred roles are compatible
       under tools/core/phrase_grammar.ROLE_COMPATIBILITY
  CF   share of role-assigned tokens whose role fits the document type
       (administrative vs votive, from the corpus `support` field)

Null models (both arms):
  A  sign-value permutation — permute consonant assignments across syllabograms,
     keep every lookup mechanism identical (the selection-aware null)
  B  skeleton permutation — shuffle the corpus consonant pool, preserve lengths
  C  token shuffle — permute token order across inscriptions (targets GC/CF)

Matching uses a hash-neighborhood matcher (exact + guttural-stripped DB variants +
single/double cheap substitutions within budget) whose agreement with the exact
weighted-Levenshtein DP is measured per arm by --selftest.

Outputs go to --out, else the user cache (`CACHE/linear-a/blind-corpus/`).

Usage:
  uv run tools/linear_a/validation/blind_corpus_test.py --selftest
  uv run tools/linear_a/validation/blind_corpus_test.py --score
  uv run tools/linear_a/validation/blind_corpus_test.py --full [--iterations 1000] [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core.phonetics import (
    LUWIAN_DISTANCES,
    SEMITIC_DISTANCES,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from ...core.phrase_grammar import ROLE_COMPATIBILITY, PhraseGrammar
from ...core.semitic_root_schema import roots_records
from ...core.skeleton import SIGN_DECOMPOSITION, _lookup_sign
from ...paths import CACHE, CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
PARTITION_PATH = DATA_DIR / "blind-corpus-partition.json"
OUT_ROOT = CACHE / "linear-a" / "blind-corpus"


def _read_json(path: Path, name: str):
    return json.loads(require(path, name).read_text(encoding="utf-8"))


def _read_jsonl(name: str):
    with require(CONTACT_DATA / name, name).open(encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)

MATCH_BUDGET = 0.3  # pre-registered primary threshold (raw weighted distance)
SENSITIVITY_BUDGET = 0.5  # pre-registered secondary threshold
WEIGHTS = {"LMR": 0.5, "GC": 0.3, "CF": 0.2}
MIN_SKELETON = 2  # tokens with fewer consonants are unscorable by skeleton method
GUTTURALS = ("ʔ", "ʿ", "ʾ", "h", "ḥ", "ḫ")  # mirrors phonetics.GUTTURAL_PHONEMES (NWS-relevant subset)
MAX_GUTTURAL_STRIP = 3

ADMIN_SUPPORTS = {"Tablet", "Nodule", "Roundel", "Lames (short thin tablet)",
                  "Sealing", "4-sided bar"}
VOTIVE_SUPPORTS = {"Stone vessel", "Clay vessel", "Metal object", "Stone object",
                   "Architecture", "Inked inscription"}
EXPECTED_ROLES = {
    "administrative": {"PERSONAL_NAME", "TOPONYM", "COMMODITY_LABEL",
                       "ACCOUNTING_TOTAL", "QUANTITY_OR_MEASURE"},
    "votive": {"PERSONAL_NAME", "TOPONYM", "CULTIC_RECIPIENT", "VERB_ACTION"},
}

_GRAMMAR = PhraseGrammar({}, [])  # meanings-only role inference

NAME_DOMAINS = ("name", "onomastic")
TOPONYM_DOMAINS = ("toponym",)
DEITY_DOMAINS = ("deity", "divine", "theonym")
COMMODITY_DOMAINS = ("commodity",)


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_partition() -> dict:
    return _read_json(PARTITION_PATH, "blind-corpus-partition.json")


def load_corpus_tokens() -> dict[str, dict]:
    """Return {inscription_id: {tokens: [...], support: str}} for all inscriptions."""
    corpus = _read_json(DATA_DIR / "corpus.json", "corpus.json")
    word_re = re.compile(r"^[A-Z*].*-")
    docs = {}
    for cid, e in corpus.items():
        toks = [w.strip() for w in (e.get("transliteratedWords") or [])
                if word_re.match(w.strip()) and w.strip() not in ("\n", "𐄁")]
        docs[cid] = {"tokens": toks, "support": e.get("support", "")}
    return docs


def syllabic_signs(token: str) -> list[str]:
    """Leading run of resolvable syllabograms (drops fused ideogram tails like -OLIV)."""
    signs = []
    for comp in token.split("-"):
        if _lookup_sign(comp):
            signs.append(comp)
        else:
            break
    return signs


def token_skeleton(signs: list[str], cons_map: dict[str, str | None]) -> tuple[str, ...]:
    cons = []
    for s in signs:
        upper = s.upper().translate(str.maketrans("₂₃₄₅", "2345"))
        key = upper if upper in cons_map else re.sub(r"\d+$", "", upper)
        c = cons_map.get(key)
        if c:
            cons.append(c)
    return tuple(_tokenize_phonemes("".join(cons)))


def base_consonant_map() -> dict[str, str | None]:
    return {sign: decomp[0] for sign, decomp in SIGN_DECOMPOSITION.items()}


# ---------------------------------------------------------------------------
# DB arms
# ---------------------------------------------------------------------------

def _devowel(form: str) -> tuple[str, ...]:
    """Consonantal skeleton of a romanized DB key, as canonical phoneme tuple."""
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    cons = "".join(ch for ch in form if ch.lower() not in vowels
                   and ch not in "*-_ ()[]0123456789.,'\"")
    return tuple(_tokenize_phonemes(cons))


def _role_for(meaning: str, domains: list[str]) -> str | None:
    dom = " ".join(domains).lower()
    if any(d in dom for d in NAME_DOMAINS):
        return "PERSONAL_NAME"
    if any(d in dom for d in TOPONYM_DOMAINS):
        return "TOPONYM"
    if any(d in dom for d in DEITY_DOMAINS):
        return "CULTIC_RECIPIENT"
    if any(d in dom for d in COMMODITY_DOMAINS):
        return "COMMODITY_LABEL"
    return _GRAMMAR.infer_semantic_category(meaning or "")


def _add(db: dict, skel: tuple[str, ...], source: str, ref: str,
         meaning: str, role: str | None) -> None:
    if len(skel) < MIN_SKELETON or len(skel) > 6:
        return
    db[skel].append((source, ref, meaning, role))


def build_nws_db() -> dict[tuple[str, ...], list]:
    db: dict[tuple[str, ...], list] = defaultdict(list)
    lex = _read_json(DATA_DIR / "lexicon.json", "lexicon.json")
    entries = lex.get("entries", lex)
    for e in entries:
        if not isinstance(e, dict) or e.get("confidence") == "REJECTED":
            continue
        root = (e.get("root") or "").replace("-", "")
        if root:
            role = _role_for(e.get("meaning", ""), [e.get("semantic_field", "")])
            _add(db, tuple(_tokenize_phonemes(root)), "lexicon",
                 e.get("word", ""), e.get("meaning", ""), role)
    roots = roots_records(_read_json(SEMITIC_ROOTS_DATA / "semitic_roots.json", "semitic_roots.json"))
    for r in roots:
        skel = _devowel(str(r.get("Proto-Semitic", "")).split(",")[0].split(" ")[0])
        meaning = str(r.get("Meaning", "")).strip("'\"")
        _add(db, skel, "proto_semitic", str(r.get("Proto-Semitic", "")), meaning,
             _role_for(meaning, []))
    for fname, source in (("amorite_onomasticon.jsonl", "amorite"),
                          ("ugaritic_lexicon.jsonl", "ugaritic")):
        for e in _read_jsonl(fname):
            meaning = e.get("meaning", "")
            doms = e.get("semantic_domain") or []
            role = _role_for(meaning, doms if isinstance(doms, list) else [str(doms)])
            seen = set()
            for key in e.get("match_keys", []):
                skel = _devowel(key)
                if skel in seen:
                    continue
                seen.add(skel)
                _add(db, skel, source, e.get("id", ""), meaning, role)
    return db


def build_luwian_db() -> dict[tuple[str, ...], list]:
    db: dict[tuple[str, ...], list] = defaultdict(list)
    roots = _read_json(DATA_DIR / "luwian_roots.json", "luwian_roots.json")
    for r in roots:
        skel = _devowel(str(r.get("Consonantal_Root", "")))
        meaning = str(r.get("Meaning", "")).strip("'\"")
        _add(db, skel, "proto_luwian", str(r.get("Proto-Luwian", "")), meaning,
             _role_for(meaning, []))
    for e in _read_jsonl("anatolian_lexicon.jsonl"):
        meaning = e.get("meaning", "")
        doms = e.get("semantic_domain") or []
        role = _role_for(meaning, doms if isinstance(doms, list) else [str(doms)])
        seen = set()
        for key in e.get("match_keys", []):
            skel = _devowel(key)
            if skel in seen:
                continue
            seen.add(skel)
            _add(db, skel, "anatolian", e.get("id", ""), meaning, role)
    return db


# ---------------------------------------------------------------------------
# Hash-neighborhood matcher
# ---------------------------------------------------------------------------

class Arm:
    """One language arm: guttural-stripped DB index + cheap-substitution table."""

    def __init__(self, name: str, db: dict[tuple[str, ...], list],
                 distances: dict[tuple[str, str], float]):
        self.name = name
        self.db = db
        self.distances = distances
        # DB-side: stripped-variant index (root gutturals removed at 0.1 each)
        self.index: dict[tuple[str, ...], list] = defaultdict(list)
        for skel in db:
            gut_pos = [i for i, p in enumerate(skel) if p in GUTTURALS]
            for k in range(min(len(gut_pos), MAX_GUTTURAL_STRIP) + 1):
                for combo in itertools.combinations(gut_pos, k):
                    stripped = tuple(p for i, p in enumerate(skel) if i not in combo)
                    if stripped:
                        cost = 0.1 * k
                        self.index[stripped].append((cost, skel))
        # Query-side: cheap substitution partners (both orders), built to the
        # largest budget any caller uses; per-call budgets filter at generation.
        # The matcher generates at most double substitutions — a conservative
        # approximation of full DP (triple 0.1-subs totalling 0.3 are missed).
        self.cheap: dict[str, list[tuple[str, float]]] = defaultdict(list)
        max_budget = max(MATCH_BUDGET, SENSITIVITY_BUDGET)
        for (a, b), c in distances.items():
            if c <= max_budget:
                self.cheap[a].append((b, c))
                self.cheap[b].append((a, c))

    def _variants(self, skel: tuple[str, ...], budget: float):
        yield skel, 0.0
        n = len(skel)
        for i in range(n):
            for b, c in self.cheap.get(skel[i], ()):
                if c > budget:
                    continue
                v1 = skel[:i] + (b,) + skel[i + 1:]
                yield v1, c
                for j in range(i + 1, n):
                    for b2, c2 in self.cheap.get(skel[j], ()):
                        if c + c2 <= budget:
                            yield v1[:j] + (b2,) + v1[j + 1:], c + c2

    def best_match(self, skel: tuple[str, ...], budget: float = MATCH_BUDGET):
        """Return (cost, source, ref, meaning, role) or None."""
        best = None
        seen: dict[tuple[str, ...], float] = {}
        for variant, sub_cost in self._variants(skel, budget):
            prev = seen.get(variant)
            if prev is not None and prev <= sub_cost:
                continue
            seen[variant] = sub_cost
            for strip_cost, orig in self.index.get(variant, ()):
                total = sub_cost + strip_cost
                if total <= budget and (best is None or total < best[0]):
                    entry = self.db[orig][0]
                    best = (total, *entry)
        return best


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def doc_type(support: str) -> str | None:
    if support in ADMIN_SUPPORTS:
        return "administrative"
    if support in VOTIVE_SUPPORTS:
        return "votive"
    return None


def roles_compatible(a: str, b: str) -> bool:
    return b in ROLE_COMPATIBILITY.get(a, set()) or a in ROLE_COMPATIBILITY.get(b, set())


def score_inscription(tokens: list[str], support: str, arm: Arm,
                      cons_map: dict, budget: float = MATCH_BUDGET) -> dict:
    scorable, matches, roles = [], [], []
    for tok in tokens:
        signs = syllabic_signs(tok)
        skel = token_skeleton(signs, cons_map)
        if len(skel) < MIN_SKELETON:
            continue
        scorable.append(tok)
        m = arm.best_match(skel, budget)
        matches.append(m)
        roles.append(m[4] if m else None)
    n = len(scorable)
    if n == 0:
        return {"scorable": 0, "LMR": 0.0, "GC": 0.0, "CF": 0.0, "S": 0.0,
                "matches": []}
    lmr = sum(1 for m in matches if m) / n
    pairs = [(roles[i], roles[i + 1]) for i in range(n - 1)
             if roles[i] and roles[i + 1]]
    gc = (sum(1 for a, b in pairs if roles_compatible(a, b)) / len(pairs)
          if pairs else 0.0)
    dt = doc_type(support)
    assigned = [r for r in roles if r]
    cf = (sum(1 for r in assigned if r in EXPECTED_ROLES.get(dt, set())) / len(assigned)
          if (assigned and dt) else 0.0)
    s = WEIGHTS["LMR"] * lmr + WEIGHTS["GC"] * gc + WEIGHTS["CF"] * cf
    detail = [{"token": t,
               "match": None if not m else
               {"d": round(m[0], 3), "source": m[1], "ref": m[2],
                "meaning": m[3][:100], "role": m[4]}}
              for t, m in zip(scorable, matches)]
    return {"scorable": n, "LMR": lmr, "GC": gc, "CF": cf, "S": s,
            "matches": detail}


def score_set(ids: list[str], docs: dict, arm: Arm, cons_map: dict,
              budget: float = MATCH_BUDGET) -> dict[str, dict]:
    out = {}
    for cid in ids:
        d = docs.get(cid)
        if d:
            out[cid] = score_inscription(d["tokens"], d["support"], arm,
                                         cons_map, budget)
    return out


def mean_S(scores: dict[str, dict]) -> float:
    vals = [s["S"] for s in scores.values() if s["scorable"] > 0]
    return statistics.mean(vals) if vals else 0.0


def mean_LMR(scores: dict[str, dict]) -> float:
    vals = [s["LMR"] for s in scores.values() if s["scorable"] > 0]
    return statistics.mean(vals) if vals else 0.0


# ---------------------------------------------------------------------------
# Null models
# ---------------------------------------------------------------------------

def permuted_cons_map(rng: random.Random) -> dict[str, str | None]:
    """Null A: permute consonant assignments across consonant-bearing signs."""
    cmap = base_consonant_map()
    signs = [s for s, c in cmap.items() if c]
    cons = [cmap[s] for s in signs]
    rng.shuffle(cons)
    for s, c in zip(signs, cons):
        cmap[s] = c
    return cmap


def null_b_docs(docs: dict, ids: list[str], rng: random.Random,
                cons_map: dict) -> dict[str, list[tuple[str, ...]]]:
    """Null B: shuffle the consonant pool across token skeletons, preserving lengths."""
    skels = {}
    pool = []
    for cid in ids:
        row = []
        for tok in docs[cid]["tokens"]:
            skel = token_skeleton(syllabic_signs(tok), cons_map)
            if len(skel) >= MIN_SKELETON:
                row.append(list(skel))
                pool.extend(skel)
        skels[cid] = row
    rng.shuffle(pool)
    it = iter(pool)
    return {cid: [tuple(next(it) for _ in row_skel) for row_skel in rows]
            for cid, rows in ((c, skels[c]) for c in skels)}


def score_skeleton_rows(rows: dict[str, list[tuple[str, ...]]], docs: dict,
                        arm: Arm, budget: float = MATCH_BUDGET) -> float:
    """Mean composite S over pre-extracted skeleton rows (for Nulls B)."""
    vals = []
    for cid, skels in rows.items():
        if not skels:
            continue
        matches = [arm.best_match(sk, budget) for sk in skels]
        roles = [m[4] if m else None for m in matches]
        n = len(skels)
        lmr = sum(1 for m in matches if m) / n
        pairs = [(roles[i], roles[i + 1]) for i in range(n - 1)
                 if roles[i] and roles[i + 1]]
        gc = (sum(1 for a, b in pairs if roles_compatible(a, b)) / len(pairs)
              if pairs else 0.0)
        dt = doc_type(docs[cid]["support"])
        assigned = [r for r in roles if r]
        cf = (sum(1 for r in assigned if r in EXPECTED_ROLES.get(dt, set()))
              / len(assigned) if (assigned and dt) else 0.0)
        vals.append(WEIGHTS["LMR"] * lmr + WEIGHTS["GC"] * gc + WEIGHTS["CF"] * cf)
    return statistics.mean(vals) if vals else 0.0


def null_c_score(ids: list[str], docs: dict, arm: Arm, cons_map: dict,
                 rng: random.Random) -> float:
    """Null C: shuffle scorable tokens across inscriptions, rescore."""
    all_tokens = []
    counts = {}
    for cid in ids:
        toks = [t for t in docs[cid]["tokens"]
                if len(token_skeleton(syllabic_signs(t), cons_map)) >= MIN_SKELETON]
        counts[cid] = len(toks)
        all_tokens.extend(toks)
    rng.shuffle(all_tokens)
    it = iter(all_tokens)
    vals = []
    for cid in ids:
        toks = [next(it) for _ in range(counts[cid])]
        if toks:
            vals.append(score_inscription(toks, docs[cid]["support"], arm,
                                          cons_map)["S"])
    return statistics.mean(vals) if vals else 0.0


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def bootstrap_ci(values: list[float], n_iter: int = 10_000,
                 seed: int = 7) -> tuple[float, float]:
    rng = random.Random(seed)
    if not values:
        return (0.0, 0.0)
    means = sorted(statistics.mean(rng.choices(values, k=len(values)))
                   for _ in range(n_iter))
    return (means[int(0.025 * n_iter)], means[int(0.975 * n_iter)])


def signflip_p(diffs: list[float], n_iter: int = 10_000, seed: int = 11) -> float:
    """Paired permutation (sign-flip) test: H0 mean(diff)=0, one-sided diff>0."""
    rng = random.Random(seed)
    if not diffs:
        return 1.0
    obs = statistics.mean(diffs)
    hits = sum(1 for _ in range(n_iter)
               if statistics.mean(d if rng.random() < 0.5 else -d
                                  for d in diffs) >= obs)
    return (hits + 1) / (n_iter + 1)


def empirical_p(observed: float, null_vals: list[float]) -> tuple[float, float]:
    """One-sided empirical p (observed > null) and Z-score."""
    if not null_vals:
        return 1.0, 0.0
    mu = statistics.mean(null_vals)
    sd = statistics.stdev(null_vals) if len(null_vals) > 1 else 0.0
    p = (sum(1 for v in null_vals if v >= observed) + 1) / (len(null_vals) + 1)
    z = (observed - mu) / sd if sd else 0.0
    return p, z


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    docs = load_corpus_tokens()
    part = load_partition()
    cons_map = base_consonant_map()
    print("Building arms...")
    nws = Arm("nws", build_nws_db(), SEMITIC_DISTANCES)
    luw = Arm("luwian", build_luwian_db(), LUWIAN_DISTANCES)
    print(f"  NWS db skeletons: {len(nws.db):,} (index {len(nws.index):,})")
    print(f"  Luwian db skeletons: {len(luw.db):,} (index {len(luw.index):,})")
    failures = 0

    # 1. Matcher agreement vs exact DP, per arm
    rng = random.Random(42)
    for arm in (nws, luw):
        db_skels = list(arm.db.keys())
        sample_tokens = []
        for cid in rng.sample(part["clean"] + part["discussed"],
                              min(30, len(part["clean"] + part["discussed"]))):
            for tok in docs[cid]["tokens"]:
                sk = token_skeleton(syllabic_signs(tok), cons_map)
                if len(sk) >= MIN_SKELETON:
                    sample_tokens.append(sk)
        sample_tokens = sample_tokens[:40]
        agree = disagree = 0
        for sk in sample_tokens:
            fast = arm.best_match(sk)
            fast_hit = fast is not None
            # exact DP over length-bucketed DB
            dp_hit = False
            s1 = "".join(sk)
            for dbsk in db_skels:
                if abs(len(dbsk) - len(sk)) > 3:
                    continue
                d = weighted_levenshtein(s1, "".join(dbsk), arm.distances,
                                         guttural_transparent=True)
                if d <= MATCH_BUDGET:
                    dp_hit = True
                    break
            if fast_hit == dp_hit:
                agree += 1
            else:
                disagree += 1
        rate = agree / max(agree + disagree, 1)
        status = "OK" if rate >= 0.9 else "FAIL"
        if rate < 0.9:
            failures += 1
        print(f"  [{status}] {arm.name} matcher agreement vs DP: "
              f"{rate:.2%} ({agree}/{agree + disagree})")

    # 2. Positive controls: translated inscriptions should outscore Null-A sample
    translated = _read_json(DATA_DIR / "translations.json", "translations.json")["translations"]
    trans_ids = [cid for cid in translated if cid in docs
                 and len(docs[cid]["tokens"]) >= 2][:30]
    ctrl = mean_S(score_set(trans_ids, docs, nws, cons_map))
    rng2 = random.Random(1)
    null_sample = [mean_S(score_set(trans_ids, docs, nws, permuted_cons_map(rng2)))
                   for _ in range(5)]
    null_mean = statistics.mean(null_sample)
    ok = ctrl > null_mean
    if not ok:
        failures += 1
    print(f"  [{'OK' if ok else 'FAIL'}] positive control: translated mean S "
          f"{ctrl:.3f} > Null-A sample mean {null_mean:.3f}")

    # 3. Determinism
    a = mean_S(score_set(part["clean"][:10], docs, nws, cons_map))
    b = mean_S(score_set(part["clean"][:10], docs, nws, cons_map))
    ok = abs(a - b) < 1e-12
    if not ok:
        failures += 1
    print(f"  [{'OK' if ok else 'FAIL'}] determinism: {a:.6f} == {b:.6f}")

    print(f"\nSelftest: {'PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


# ---------------------------------------------------------------------------
# Main runs
# ---------------------------------------------------------------------------

def run(full: bool, iterations: int, out_dir: Path | None) -> None:
    t0 = datetime.now().astimezone()
    part = load_partition()
    docs = load_corpus_tokens()
    cons_map = base_consonant_map()
    arms = {"nws": Arm("nws", build_nws_db(), SEMITIC_DISTANCES),
            "luwian": Arm("luwian", build_luwian_db(), LUWIAN_DISTANCES)}

    translated = _read_json(DATA_DIR / "translations.json", "translations.json")["translations"]
    trans_ids = [cid for cid in translated if cid in docs
                 and len(docs[cid]["tokens"]) >= 2]
    partitions = {"clean": part["clean"], "listed": part["listed"],
                  "discussed": part["discussed"],
                  "translated_control": trans_ids}

    ts = t0.strftime("%Y%m%d-%H%M%S")
    out = out_dir or (OUT_ROOT / ts)
    out.mkdir(parents=True, exist_ok=True)

    observed: dict[str, dict] = {}
    per_insc_rows = []
    for pname, ids in partitions.items():
        observed[pname] = {}
        for aname, arm in arms.items():
            scores = score_set(ids, docs, arm, cons_map)
            scores_05 = score_set(ids, docs, arm, cons_map, SENSITIVITY_BUDGET)
            svals = [s["S"] for s in scores.values() if s["scorable"] > 0]
            observed[pname][aname] = {
                "n": len(svals),
                "mean_S": mean_S(scores),
                "mean_LMR": mean_LMR(scores),
                "mean_GC": statistics.mean([s["GC"] for s in scores.values()
                                            if s["scorable"] > 0] or [0.0]),
                "mean_CF": statistics.mean([s["CF"] for s in scores.values()
                                            if s["scorable"] > 0] or [0.0]),
                "mean_LMR_d05": mean_LMR(scores_05),
                "ci_S": bootstrap_ci(svals),
            }
            for cid, s in scores.items():
                per_insc_rows.append({"id": cid, "partition": pname, "arm": aname,
                                      **{k: s[k] for k in
                                         ("scorable", "LMR", "GC", "CF", "S")},
                                      "matches": s["matches"]})
        # paired NWS-vs-Luwian on this partition
        nws_s = score_set(ids, docs, arms["nws"], cons_map)
        luw_s = score_set(ids, docs, arms["luwian"], cons_map)
        diffs = [nws_s[c]["S"] - luw_s[c]["S"] for c in nws_s
                 if nws_s[c]["scorable"] > 0]
        observed[pname]["paired"] = {
            "mean_diff_S": statistics.mean(diffs) if diffs else 0.0,
            "p_signflip_nws_gt_luw": signflip_p(diffs),
        }
        print(f"[{pname}] NWS S={observed[pname]['nws']['mean_S']:.3f} "
              f"LMR={observed[pname]['nws']['mean_LMR']:.3f} | "
              f"Luwian S={observed[pname]['luwian']['mean_S']:.3f} "
              f"LMR={observed[pname]['luwian']['mean_LMR']:.3f} | "
              f"diff p={observed[pname]['paired']['p_signflip_nws_gt_luw']:.4f}")

    nulls: dict[str, dict] = {}
    if full:
        rng = random.Random(2026)
        primary_ids = part["clean"]
        for aname, arm in arms.items():
            na, nb, nc = [], [], []
            for i in range(iterations):
                cm = permuted_cons_map(rng)
                na.append(mean_S(score_set(primary_ids, docs, arm, cm)))
                rows = null_b_docs(docs, primary_ids, rng, cons_map)
                nb.append(score_skeleton_rows(rows, docs, arm))
                nc.append(null_c_score(primary_ids, docs, arm, cons_map, rng))
                if (i + 1) % 50 == 0:
                    print(f"  [{aname}] null iteration {i + 1}/{iterations}", flush=True)
            obs = observed["clean"][aname]["mean_S"]
            nulls[aname] = {}
            for label, vals in (("A_sign_permutation", na),
                                ("B_skeleton_permutation", nb),
                                ("C_token_shuffle", nc)):
                p, z = empirical_p(obs, vals)
                nulls[aname][label] = {"mean": statistics.mean(vals),
                                       "sd": statistics.stdev(vals),
                                       "p": p, "z": z, "n_iter": len(vals)}
                print(f"[{aname}] Null {label}: mean={statistics.mean(vals):.3f} "
                      f"obs={obs:.3f} z={z:.2f} p={p:.4f}")
            # lift = observed LMR / null-A LMR baseline (DB-size normalization)
            lmr_null = [mean_LMR(score_set(primary_ids, docs, arm,
                                           permuted_cons_map(rng)))
                        for _ in range(min(iterations, 200))]
            nulls[aname]["LMR_lift"] = {
                "observed_LMR": observed["clean"][aname]["mean_LMR"],
                "null_A_LMR_mean": statistics.mean(lmr_null),
                "lift": (observed["clean"][aname]["mean_LMR"]
                         / statistics.mean(lmr_null)) if statistics.mean(lmr_null)
                        else float("inf"),
            }

    provenance = {
        "locked_tag": part["locked_tag"],
        "run_started": t0.isoformat(),
        "run_finished": datetime.now().astimezone().isoformat(),
        "iterations": iterations if full else 0,
        "weights": WEIGHTS,
        "match_budget": MATCH_BUDGET,
        "lexicon_md5": hashlib.md5((DATA_DIR / "lexicon.json").read_bytes()).hexdigest(),
        "corpus_md5": hashlib.md5((DATA_DIR / "corpus.json").read_bytes()).hexdigest(),
    }
    (out / "summary.json").write_text(json.dumps(
        {"provenance": provenance, "observed": observed, "nulls": nulls},
        indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    with open(out / "per_inscription.jsonl", "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in per_insc_rows)
    print(f"\nWrote {out}/summary.json and per_inscription.jsonl "
          f"({datetime.now().astimezone() - t0})")


def threshold_sweep(iterations: int = 200, out_dir: Path | None = None) -> None:
    """POST-HOC DIAGNOSTIC (labeled as such — not the pre-registered primary).

    The pre-registered budget 0.3 saturates the NWS arm (LMR ~0.9 under ANY
    sign mapping), leaving the primary test without power. This sweep asks
    where, if anywhere, the true sign-value mapping carries information:
    exact matches (d=0) and near-exact (d<=0.1, one root guttural) escape
    saturation. Also runs a no-names NWS variant (Amorite/onomastic
    personal-name entries excluded) to separate name-list inflation from
    core-vocabulary signal.
    """
    part = load_partition()
    docs = load_corpus_tokens()
    cons_map = base_consonant_map()
    ids = part["clean"]

    nws_db = build_nws_db()
    nws_db_nonames = {k: [e for e in v if not (e[3] == "PERSONAL_NAME"
                                               and e[0] in ("amorite",))]
                      for k, v in nws_db.items()}
    nws_db_nonames = {k: v for k, v in nws_db_nonames.items() if v}
    arms = {
        "nws": Arm("nws", nws_db, SEMITIC_DISTANCES),
        "nws_nonames": Arm("nws_nonames", nws_db_nonames, SEMITIC_DISTANCES),
        "luwian": Arm("luwian", build_luwian_db(), LUWIAN_DISTANCES),
    }
    print(f"{'arm':<13} {'budget':>6} {'obs_LMR':>8} {'nullA_LMR':>10} "
          f"{'z':>6} {'p':>8}")
    results = []
    for aname, arm in arms.items():
        for budget in (0.0, 0.1, 0.2, 0.3):
            obs = mean_LMR(score_set(ids, docs, arm, cons_map, budget))
            rng = random.Random(2027)
            null_vals = [mean_LMR(score_set(ids, docs, arm,
                                            permuted_cons_map(rng), budget))
                         for _ in range(iterations)]
            p, z = empirical_p(obs, null_vals)
            print(f"{aname:<13} {budget:>6.1f} {obs:>8.3f} "
                  f"{statistics.mean(null_vals):>10.3f} {z:>6.2f} {p:>8.4f}",
                  flush=True)
            results.append({"arm": aname, "budget": budget, "obs_LMR": obs,
                            "null_mean": statistics.mean(null_vals),
                            "null_sd": statistics.stdev(null_vals),
                            "z": z, "p": p, "n_iter": iterations})
    out = (out_dir or OUT_ROOT) / "threshold_sweep.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"note": "POST-HOC diagnostic: saturation analysis after the "
                 "pre-registered budget 0.3 showed ceiling effects "
                 "(NWS LMR ~0.9 under any sign mapping)",
         "results": results}, indent=1), encoding="utf-8")
    print(f"Wrote {out}")


def main() -> int:
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--score", action="store_true",
                    help="observed scores only (no nulls)")
    ap.add_argument("--full", action="store_true",
                    help="observed + null models + lift")
    ap.add_argument("--sweep", action="store_true",
                    help="post-hoc threshold sweep diagnostic")
    ap.add_argument("--iterations", type=int, default=1000)
    ap.add_argument("--quick", action="store_true", help="150 null iterations")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.selftest:
        return 1 if selftest() else 0
    if args.sweep:
        threshold_sweep(min(args.iterations, 200), args.out)
        return 0
    iters = 150 if args.quick else args.iterations
    run(full=args.full, iterations=iters, out_dir=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
