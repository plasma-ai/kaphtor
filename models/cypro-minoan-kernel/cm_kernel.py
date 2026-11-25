#!/usr/bin/env python3
"""Deterministic, zero-LLM Cypro-Minoan statistical kernel suite (T5-compliant).

Runs strictly on shipped kaphtor datasets (zero external folders, zero Linear A leakage):
  - data/ane/cypro-minoan/{catalogue,translations,lexicon,onomasticon,grammar_hypotheses,grid,MANIFEST}.json
  - data/ane/ig-xv-1-cypriot/records.jsonl (Amathus-only Eteocypriot parts; Golgoi/Kurion/Marion separated)
  - data/share-alike/linear-b/linear_b_tokens.jsonl (DAMOS Mycenaean Greek negative control)

Kernels:
  - CM-G: Subcorpus & IG XV 1 Amathus word-final / bigram continuity (V-vs-CV + vowel-preserving nulls)
  - CM-E: Decoy-calibrated IG XV 1 Amathus lexical, C-skeleton & 3-regime 013/008 alignment + controls
  - CM-O: Orthographic glide-rule (-Ci-jV-, -Cu-wV-) enrichment & bare-vowel positional laws
  - CM-B: Unsupervised stem-extension productivity calibrated against syllable-shuffled null lexica

Usage:
    python3 models/cypro-minoan-kernel/cm_kernel.py manifest
    python3 models/cypro-minoan-kernel/cm_kernel.py run [--perms 2000] [--lb-draws 20] [--out PATH]
    python3 models/cypro-minoan-kernel/cm_kernel.py check --ledger runs/cm-kernel-2026-11-25.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CM_DIR = REPO / "data" / "ane" / "cypro-minoan"
IG_PATH = REPO / "data" / "ane" / "ig-xv-1-cypriot" / "records.jsonl"
LB_PATH = REPO / "data" / "share-alike" / "linear-b" / "linear_b_tokens.jsonl"

VOWELS = ("a", "e", "i", "o", "u")
J_GLIDES = frozenset({"ja", "je", "ji", "jo", "ju"})
W_GLIDES = frozenset({"wa", "we", "wi", "wo", "wu"})
TENTATIVE_AMATHUS_IG = frozenset({"IG XV 1, 12"})


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_syl(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().replace("₂", "").replace("₃", "").replace("š", "s").strip()
    if s in ("ya", "ye", "yi", "yo", "yu"):
        s = "j" + s[1:]
    return s


def has_underdot(tok: str) -> bool:
    return "\u0323" in unicodedata.normalize("NFD", tok)


def split_cv(syl: str) -> tuple[str, str]:
    if len(syl) == 1:
        return ("", syl)
    return (syl[0], syl[1])


def is_pure_vowel(syl: str) -> bool:
    return len(syl) == 1 and syl in VOWELS


def _split_glued_linebreaks(text: str) -> str:
    """Restore word boundaries where IG XV 1 EpiDoc <lb/> tags were stripped without spaces.

    In Cypriot syllabic transliteration, syllables within a word are strictly joined by '-'.
    Accordingly:
      1. 'vacat' / 'vac.' glued after a syllable terminates the line.
      2. Hyphens followed by arrows or spaces ('a- pi-ma', 'tu-ka- ←i-...') join wrapped syllables.
      3. '..' glued to a letter without '-' marks a stripped line break beside a lacuna.
      4. A syllable vowel (+ optional combining underdot) directly followed by another letter
         with no intervening '-' marks a stripped line break between two words.
    """
    t = unicodedata.normalize("NFD", text)
    t = re.sub(r"vacat\b[^←→|]*", " ", t)
    t = re.sub(r"vac\.[^←→|]*", " ", t)
    t = re.sub(r"-\s*[←→]+\s*", "-", t)
    t = re.sub(r"-\s+", "-", t)
    t = re.sub(r"[←→\u2003]+", " ", t)
    t = re.sub(r"([a-z]\u0323?)(\.\.)", r"\1 \2", t)
    t = re.sub(r"(\.\.)([a-z])", r"\1 \2", t)
    t = re.sub(r"([aeiou]\u0323?)(?=[a-z])", r"\1 ", t)
    return unicodedata.normalize("NFC", t)


def parse_ig_amathus(
    ig_path: Path = IG_PATH,
    exclude_dotted: bool = False,
) -> list[tuple[str, ...]]:
    """Parse strictly unbroken, line-wrap-joined Amathus Eteocypriot word types from IG XV 1 records.jsonl.

    Yields exactly 92 confirmed non-doubtful word types (66 strictly undotted) matching the audited
    IG XV 1 Amathus filter:
      - Amathus-only (excludes Kurion, Marion, unprovenanced IG XV 1, 16)
      - Excludes tentative attribution (IG XV 1, 12) and direction-doubtful parts ('←?' / '→?')
      - Rejects lacuna-adjacent fragments (immediately next to '[' or ']') and optional underdotted tokens
    """
    words: set[tuple[str, ...]] = set()
    for line in ig_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("place") != "Amathus":
            continue
        desig = rec.get("designation") or ""
        if desig in TENTATIVE_AMATHUS_IG:
            continue
        for ed in rec.get("editions") or []:
            if "eteocypriot" not in (ed.get("language_label") or "").lower():
                continue
            if ed.get("language_label_basis") == "tentative":
                continue
            raw_text = ed.get("text") or ""
            if "←?" in raw_text or "→?" in raw_text:
                continue
            joined = _split_glued_linebreaks(raw_text)
            raw_toks = [t for t in re.split(r"[\s·•:∣|]+", joined) if t]
            for i, tok in enumerate(raw_toks):
                prev_t = raw_toks[i - 1] if i > 0 else ""
                next_t = raw_toks[i + 1] if i + 1 < len(raw_toks) else ""
                if prev_t.endswith("]") or next_t.startswith("["):
                    continue
                tok_c = tok.strip(",;()<>")
                if not tok_c or tok_c.isdigit():
                    continue
                if any(ch in tok_c for ch in ".[]?…*‒") or tok_c.startswith("-") or tok_c.endswith("-"):
                    continue
                if exclude_dotted and has_underdot(tok_c):
                    continue
                parts = [norm_syl(p) for p in tok_c.split("-") if p.strip()]
                if parts and all(re.fullmatch(r"[a-z]{1,2}", p) and p[-1] in VOWELS for p in parts):
                    words.add(tuple(parts))
    return sorted(words)


def load_cm_word_types(
    cm_dir: Path = CM_DIR,
    regime: str = "valerio",
) -> dict[str, list[tuple[str, ...]]]:
    """Load attested L >= 2 read word types per subcorpus from shipped lexicon.json + translations.json.

    Excludes synthetic paradigm_stem rows so every type is a genuinely attested read word.
    Unassigned-subcorpus entries (subcorpora == ['null'], 9 entries) are omitted from subcorpus buckets.
    regime:
      - 'valerio':  shipped Valério-emended readings (008=na, 013=to in CM 1; 013->008=na in CM 2)
      - 'davis':    unsplit 013=na, 008=to on CM 1+CM 3 entries (CM 2-only emended 008 stays na)
      - 'hochymin': unsplit 013=to, 008=na (reverts CM 2-only emended 008 back to 013=to; does not
                    revert the 6 CM 1 Valério-emended 008->013 entries)
    """
    lex = json.loads((cm_dir / "lexicon.json").read_text(encoding="utf-8"))
    sv_raw = json.loads((cm_dir / "translations.json").read_text(encoding="utf-8"))["sign_values"]
    sv = {k: norm_syl(v["value"]) for k, v in sv_raw.items()}

    buckets: dict[str, set[tuple[str, ...]]] = {
        "CM 1": set(),
        "CM 2": set(),
        "CM 3": set(),
        "CM 1+2": set(),
    }
    for e in lex["entries"]:
        if e["entry_kind"] == "paradigm_stem":
            continue
        signs = e["cypro_minoan"].split("-")
        if len(signs) < 2 or not all(s in sv for s in signs):
            continue
        subs = set(e.get("subcorpora") or [])
        is_cm2_only = "CM 2" in subs and "CM 1" not in subs
        if regime == "valerio":
            syls = tuple(norm_syl(p) for p in e["values"].split("-"))
        elif regime == "davis":
            syls = tuple(
                ("na" if s == "013" else ("to" if s == "008" else sv[s]))
                if not is_cm2_only
                else sv[s]
                for s in signs
            )
        elif regime == "hochymin":
            syls = tuple(
                "to" if (is_cm2_only and s == "008") else sv[s]
                for s in signs
            )
        else:
            raise ValueError(f"Unknown regime {regime!r}")

        if not all(re.fullmatch(r"[a-z]{1,2}", x) and x[-1] in VOWELS for x in syls):
            continue
        for sub in ("CM 1", "CM 2", "CM 3"):
            if sub in subs:
                buckets[sub].add(syls)
        if subs & {"CM 1", "CM 2"}:
            buckets["CM 1+2"].add(syls)

    return {k: sorted(v) for k, v in buckets.items()}


def load_linear_b_types(lb_path: Path = LB_PATH) -> list[tuple[str, ...]]:
    """Load clean DAMOS Linear B syllabic L >= 2 word types mapped to Cypriot-like voiceless series (d->t, q->k)."""
    words: set[tuple[str, ...]] = set()
    for line in lb_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("token_type") != "syllabic" or rec.get("editorial_status") != "clean":
            continue
        tok = (rec.get("token_normalized") or "").strip().lstrip("'")
        if any(ch in tok for ch in "[]?*+."):
            continue
        parts = [norm_syl(p) for p in tok.split("-") if p.strip()]
        if len(parts) >= 2 and all(re.fullmatch(r"[a-z]{1,2}", p) and p[-1] in VOWELS for p in parts):
            normed = []
            for p in parts:
                if len(p) == 2 and p[0] == "d":
                    p = "t" + p[1]
                elif len(p) == 2 and p[0] == "q":
                    p = "k" + p[1]
                normed.append(p)
            words.add(tuple(normed))
    return sorted(words)


def _cosine(c1: collections.Counter[str], c2: collections.Counter[str]) -> float:
    keys = set(c1) & set(c2)
    num = sum(c1[k] * c2[k] for k in keys)
    d1 = math.sqrt(sum(v * v for v in c1.values()))
    d2 = math.sqrt(sum(v * v for v in c2.values()))
    return num / (d1 * d2) if d1 and d2 else 0.0


def _perm_map(vocab: list[str], rng: random.Random, mode: str) -> dict[str, str]:
    """Generate a syllable bijection under 'unr', 'vpres', or 'vcv' (V-vs-CV + vowel-preserving)."""
    if mode == "unr":
        shuffled = vocab[:]
        rng.shuffle(shuffled)
        return dict(zip(vocab, shuffled))
    groups: dict[tuple, list[str]] = collections.defaultdict(list)
    for s in vocab:
        if mode == "vpres":
            groups[(split_cv(s)[1],)].append(s)
        elif mode == "vcv":
            groups[(is_pure_vowel(s), split_cv(s)[1])].append(s)
        else:
            raise ValueError(f"Unknown mode {mode!r}")
    out: dict[str, str] = {}
    for g in groups.values():
        sh = g[:]
        rng.shuffle(sh)
        out.update(zip(g, sh))
    return out


def _align_metrics(cm_words: list[tuple[str, ...]], ec_words: list[tuple[str, ...]]) -> dict:
    ec_l2 = {w for w in ec_words if len(w) >= 2}
    ec_l3 = {w for w in ec_words if len(w) >= 3}
    ec_suf2 = {w[-2:] for w in ec_l3}
    ec_pre2 = {w[:2] for w in ec_l3}
    ec_end1 = collections.Counter(w[-1] for w in ec_l2)
    ec_bi = {(a, b) for w in ec_l2 for a, b in zip(w, w[1:])}
    ec_csk: dict[tuple[str, ...], list[tuple[str, ...]]] = collections.defaultdict(list)
    for w in ec_l3:
        ec_csk[tuple(split_cv(x)[0] for x in w)].append(w)

    cm_l2 = [w for w in cm_words if len(w) >= 2]
    cm_l3 = [w for w in cm_words if len(w) >= 3]
    cm_suf2 = {w[-2:] for w in cm_l3}
    cm_pre2 = {w[:2] for w in cm_l3}
    cm_end1 = collections.Counter(w[-1] for w in cm_l2)
    cm_bi = {(a, b) for w in cm_l2 for a, b in zip(w, w[1:])}

    exact2 = sorted("-".join(w) for w in cm_l2 if w in ec_l2)
    csk_forms = []
    csk_stems = set()
    for w in cm_l3:
        cs = tuple(split_cv(x)[0] for x in w)
        hits = [
            ew
            for ew in ec_csk.get(cs, [])
            if sum(1 for a, b in zip(w, ew) if split_cv(a)[1] == split_cv(b)[1]) >= 2
        ]
        if hits:
            csk_forms.append("-".join(w))
            csk_stems.add(w[:2])

    return {
        "n_cm_l2": len(cm_l2),
        "n_cm_l3": len(cm_l3),
        "exact_l2": len(exact2),
        "exact_l2_words": exact2,
        "csk_stems_l3": len(csk_stems),
        "csk_forms_l3": len(csk_forms),
        "csk_forms_words": sorted(csk_forms),
        "shared_suf2": len(cm_suf2 & ec_suf2),
        "shared_suf2_list": sorted("-".join(x) for x in (cm_suf2 & ec_suf2)),
        "shared_pre2": len(cm_pre2 & ec_pre2),
        "shared_bi": len(cm_bi & ec_bi),
        "end1_cos": round(_cosine(cm_end1, ec_end1), 4),
    }


def calibrate_alignment(
    cm_words: list[tuple[str, ...]],
    ec_words: list[tuple[str, ...]],
    n_perm: int = 2000,
    seed: int = 20261125,
) -> dict:
    """Calibrate all alignment & continuity metrics against B permutations of CM's alphabet under vcv and unr nulls."""
    obs = _align_metrics(cm_words, ec_words)
    vocab = sorted({s for w in cm_words for s in w})
    keys = ("exact_l2", "csk_stems_l3", "csk_forms_l3", "shared_suf2", "shared_pre2", "shared_bi", "end1_cos")
    pvals: dict[str, dict[str, float]] = {}
    zscores: dict[str, dict[str, float]] = {}

    for mode in ("unr", "vcv"):
        rng = random.Random(seed if mode == "vcv" else seed + 17)
        ge = collections.Counter()
        sums = collections.Counter()
        sq = collections.Counter()
        for _ in range(n_perm):
            pm = _perm_map(vocab, rng, mode)
            cm_p = [tuple(pm[s] for s in w) for w in cm_words]
            m = _align_metrics(cm_p, ec_words)
            for k in keys:
                val = m[k]
                sums[k] += val
                sq[k] += val * val
                if val >= obs[k] - 1e-12:
                    ge[k] += 1
        pvals[mode] = {k: round((ge[k] + 1) / (n_perm + 1), 5) for k in keys}
        zscores[mode] = {}
        for k in keys:
            mu = sums[k] / n_perm
            var = max(sq[k] / n_perm - mu * mu, 1e-12)
            zscores[mode][k] = round((obs[k] - mu) / math.sqrt(var), 2)

    return {"observed": obs, "p": pvals, "z": zscores}


def run_kernel_o_glides(cm_dir: Path = CM_DIR) -> dict:
    """Kernel CM-O: Empirical orthographic glide (-Ci-jV-, -Cu-wV-) and bare-vowel final-rate laws."""
    tr = json.loads((cm_dir / "translations.json").read_text(encoding="utf-8"))["translations"]
    cat = json.loads((cm_dir / "catalogue.json").read_text(encoding="utf-8"))

    def binom_ge(k: int, n: int, p: float) -> float:
        return sum(math.comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i)) for i in range(k, n + 1))

    out = {}
    for scope, sub_filter in (("pan_cm", None), ("cm2_only", {"CM 2"})):
        nf = collections.Counter()
        bj = collections.Counter()
        bw = collections.Counter()
        v_tot, v_fin, cv_tot, cv_fin = 0, 0, 0, 0
        for sig, rec in tr.items():
            sub = cat[sig].get("subcorpus")
            if sub_filter and sub not in sub_filter:
                continue
            for w in rec["words"]:
                vals = [norm_syl(v) for v in (w.get("values") or [])]
                if len(vals) < 2:
                    continue
                for i, syl in enumerate(vals):
                    if not re.fullmatch(r"[a-z]{1,2}", syl) or syl[-1] not in VOWELS:
                        continue
                    if is_pure_vowel(syl):
                        v_tot += 1
                        if i == len(vals) - 1:
                            v_fin += 1
                    else:
                        cv_tot += 1
                        if i == len(vals) - 1:
                            cv_fin += 1
                    if i + 1 < len(vals):
                        nxt = vals[i + 1]
                        if re.fullmatch(r"[a-z]{1,2}", nxt) and nxt[-1] in VOWELS:
                            v = split_cv(syl)[1]
                            nf[v] += 1
                            if nxt in J_GLIDES:
                                bj[v] += 1
                            if nxt in W_GLIDES:
                                bw[v] += 1

        tot_nf = sum(nf.values()) or 1
        base_j = sum(bj.values()) / tot_nf
        base_w = sum(bw.values()) / tot_nf
        # Non-i rate for jV and non-u rate for wV
        non_i_nf = sum(nf[v] for v in VOWELS if v != "i") or 1
        non_i_j = sum(bj[v] for v in VOWELS if v != "i") / non_i_nf
        non_u_nf = sum(nf[v] for v in VOWELS if v != "u") or 1
        non_u_w = sum(bw[v] for v in VOWELS if v != "u") / non_u_nf
        p_j_exact = binom_ge(bj["i"], nf["i"], max(non_i_j, 1e-6))
        p_w_exact = binom_ge(bw["u"], nf["u"], max(non_u_w, 1e-6))

        out[scope] = {
            "by_vowel": {
                v: {
                    "non_final": nf[v],
                    "before_jV": bj[v],
                    "p_j": round(bj[v] / max(nf[v], 1), 4),
                    "before_wV": bw[v],
                    "p_w": round(bw[v] / max(nf[v], 1), 4),
                }
                for v in VOWELS
            },
            "ci_jv_enrichment_p_vs_non_i": float(f"{p_j_exact:.4e}"),
            "cu_wv_enrichment_p_vs_non_u": float(f"{p_w_exact:.4e}"),
            "base_j_rate": round(base_j, 4),
            "base_w_rate": round(base_w, 4),
            "bare_vowel_final_rate": round(v_fin / max(v_tot, 1), 4),
            "cv_final_rate": round(cv_fin / max(cv_tot, 1), 4),
        }
    return out


def run_kernel_b_stem_productivity(
    cm_words: list[tuple[str, ...]],
    n_perm: int = 1000,
    seed: int = 20261125,
) -> dict:
    """Kernel CM-B: Unsupervised 1-syllable suffix/prefix containment pairs calibrated against
    a position-preserving (initial / medial / final) length-matched syllable-shuffle null."""
    def count_extensions(words: list[tuple[str, ...]]) -> tuple[int, int, dict[str, int]]:
        wset = set(words)
        suf_pairs = 0
        pre_pairs = 0
        suf_counts: collections.Counter[str] = collections.Counter()
        for w in sorted(wset):
            if len(w) >= 3:
                if w[:-1] in wset:
                    suf_pairs += 1
                    suf_counts[w[-1]] += 1
                if w[1:] in wset:
                    pre_pairs += 1
        top_sorted = sorted(suf_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        return suf_pairs, pre_pairs, dict(top_sorted)

    obs_suf, obs_pre, top_sufs = count_extensions(cm_words)
    rng = random.Random(seed + 99)
    # Position-preserving syllable shuffle: keep word-initial, word-medial, and word-final
    # pools separate so bare-vowel initial bias does not deflate null suffix expectations.
    init_pool = [w[0] for w in cm_words]
    med_pool = [s for w in cm_words for s in w[1:-1]]
    fin_pool = [w[-1] for w in cm_words]
    lengths = [len(w) for w in cm_words]
    ge_suf, ge_pre = 0, 0
    sum_suf, sum_pre = 0.0, 0.0
    for _ in range(n_perm):
        sh_i = init_pool[:]
        sh_m = med_pool[:]
        sh_f = fin_pool[:]
        rng.shuffle(sh_i)
        rng.shuffle(sh_m)
        rng.shuffle(sh_f)
        null_words = []
        m_idx = 0
        for wi, L in enumerate(lengths):
            med_len = L - 2
            med = sh_m[m_idx:m_idx + med_len]
            m_idx += med_len
            null_words.append((sh_i[wi], *med, sh_f[wi]))
        ns, np_ = count_extensions(null_words)[:2]
        sum_suf += ns
        sum_pre += np_
        if ns >= obs_suf:
            ge_suf += 1
        if np_ >= obs_pre:
            ge_pre += 1

    return {
        "n_word_types": len(cm_words),
        "null_model": "position_preserving_init_med_fin_shuffle",
        "suffix_extension_pairs": obs_suf,
        "null_suffix_mean": round(sum_suf / n_perm, 2),
        "p_suffix": round((ge_suf + 1) / (n_perm + 1), 5),
        "prefix_extension_pairs": obs_pre,
        "null_prefix_mean": round(sum_pre / n_perm, 2),
        "p_prefix": round((ge_pre + 1) / (n_perm + 1), 5),
        "top_productive_suffixes": top_sufs,
    }


def build_manifest(cm_dir: Path = CM_DIR, ig_path: Path = IG_PATH, lb_path: Path = LB_PATH) -> dict:
    files = {
        "cm_catalogue": cm_dir / "catalogue.json",
        "cm_translations": cm_dir / "translations.json",
        "cm_lexicon": cm_dir / "lexicon.json",
        "cm_onomasticon": cm_dir / "onomasticon.json",
        "cm_grammar": cm_dir / "grammar_hypotheses.json",
        "cm_grid": cm_dir / "grid.json",
        "ig_xv_1": ig_path,
        "linear_b_damos": lb_path,
    }
    return {
        "schema_version": 1,
        "firewall": "Cypro-Minoan only: reads zero Linear A lexicon/translations/sign_values files.",
        "t5_compliant": True,
        "inputs": {
            name: {"path": str(p.relative_to(REPO)), "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for name, p in files.items()
        },
    }


def run_suite(
    n_perm: int = 2000,
    lb_draws: int = 20,
    seed: int = 20261125,
    cm_dir: Path = CM_DIR,
    ig_path: Path = IG_PATH,
    lb_path: Path = LB_PATH,
) -> dict:
    ec_conf = parse_ig_amathus(ig_path, exclude_dotted=False)
    ec_undot = parse_ig_amathus(ig_path, exclude_dotted=True)
    cm_val = load_cm_word_types(cm_dir, regime="valerio")
    cm_dav = load_cm_word_types(cm_dir, regime="davis")
    cm_hoc = load_cm_word_types(cm_dir, regime="hochymin")
    lb_all = load_linear_b_types(lb_path)

    # Kernel CM-G & CM-E: primary Valério, Undotted EC, Davis, HoChyMin, CM 3 control, and Linear B draws
    kernel_g_subcorpora = {
        sub: calibrate_alignment(cm_val[sub], ec_conf, n_perm=n_perm, seed=seed + i * 31)
        for i, sub in enumerate(("CM 1", "CM 2", "CM 1+2", "CM 3"))
    }
    kernel_e_regimes = {
        "valerio_vs_confirmed_ec": kernel_g_subcorpora["CM 1+2"],
        "valerio_vs_undotted_ec": calibrate_alignment(cm_val["CM 1+2"], ec_undot, n_perm=n_perm, seed=seed + 201),
        "davis_unsplit_vs_confirmed_ec": calibrate_alignment(cm_dav["CM 1+2"], ec_conf, n_perm=n_perm, seed=seed + 301),
        "hochymin_unsplit_vs_confirmed_ec": calibrate_alignment(
            cm_hoc["CM 1+2"], ec_conf, n_perm=n_perm, seed=seed + 401
        ),
        "cm3_ugarit_control": kernel_g_subcorpora["CM 3"],
    }

    # Size-matched DAMOS Linear B Greek negative control draws
    n_target = len(cm_val["CM 1+2"])
    rng = random.Random(seed + 777)
    lb_exact, lb_csk, lb_suf2, lb_pre2, lb_end1 = [], [], [], [], []
    lb_p_suf2, lb_p_csk, lb_p_end1 = [], [], []
    for d_i in range(lb_draws):
        draw = rng.sample(lb_all, min(n_target, len(lb_all)))
        m = _align_metrics(draw, ec_conf)
        lb_exact.append(m["exact_l2"])
        lb_csk.append(m["csk_stems_l3"])
        lb_suf2.append(m["shared_suf2"])
        lb_pre2.append(m["shared_pre2"])
        lb_end1.append(m["end1_cos"])
        if d_i < min(5, lb_draws):
            cal = calibrate_alignment(draw, ec_conf, n_perm=min(500, n_perm), seed=seed + 900 + d_i)
            lb_p_suf2.append(cal["p"]["vcv"]["shared_suf2"])
            lb_p_csk.append(cal["p"]["vcv"]["csk_stems_l3"])
            lb_p_end1.append(cal["p"]["vcv"]["end1_cos"])

    def _mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 3) if xs else 0.0

    def _med(xs: list[float]) -> float:
        s = sorted(xs)
        return round(s[len(s) // 2], 4) if s else 1.0

    lb_control = {
        "n_draws": lb_draws,
        "sample_size": n_target,
        "exact_l2_mean": _mean(lb_exact),
        "csk_stems_l3_mean": _mean(lb_csk),
        "shared_suf2_mean": _mean(lb_suf2),
        "shared_pre2_mean": _mean(lb_pre2),
        "end1_cos_mean": _mean(lb_end1),
        "calibrated_draws": len(lb_p_suf2),
        "median_p_vcv_suf2": _med(lb_p_suf2),
        "median_p_vcv_csk_stems": _med(lb_p_csk),
        "median_p_vcv_end1_cos": _med(lb_p_end1),
    }

    kernel_o = run_kernel_o_glides(cm_dir)
    kernel_b = run_kernel_b_stem_productivity(cm_val["CM 1+2"], n_perm=min(1000, n_perm), seed=seed)

    return {
        "schema_version": 1,
        "seed": seed,
        "permutations": n_perm,
        "manifest": build_manifest(cm_dir, ig_path, lb_path),
        "corpora_counts": {
            "ec_amathus_confirmed_types": len(ec_conf),
            "ec_amathus_undotted_types": len(ec_undot),
            "cm_valerio_types_l2": {k: len(v) for k, v in cm_val.items()},
            "linear_b_clean_types_l2": len(lb_all),
        },
        "kernel_cm_g_subcorpora": kernel_g_subcorpora,
        "kernel_cm_e_regimes": kernel_e_regimes,
        "linear_b_negative_control": lb_control,
        "kernel_cm_o_glides": kernel_o,
        "kernel_cm_b_stems": kernel_b,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Cypro-Minoan statistical kernel suite.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest", help="Print SHA-256 manifest of shipped inputs.")
    p_run = sub.add_parser("run", help="Run all 4 Cypro-Minoan kernels.")
    p_run.add_argument("--perms", type=int, default=2000)
    p_run.add_argument("--lb-draws", type=int, default=20)
    p_run.add_argument("--seed", type=int, default=20261125)
    p_run.add_argument("--out", type=Path, default=None)
    p_chk = sub.add_parser("check", help="Verify a pinned run ledger against current shipped inputs.")
    p_chk.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.cmd == "manifest":
        print(json.dumps(build_manifest(), indent=2))
        return 0
    if args.cmd == "run":
        res = run_suite(n_perm=args.perms, lb_draws=args.lb_draws, seed=args.seed)
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
