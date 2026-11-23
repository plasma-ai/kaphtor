"""Kernel H: Structurally-Gated Personnel Roster Onomastics (Zero Dictionary Peeking).

Extracts putative personal names purely by tablet syntax: undamaged >=3-sign syllabic words
immediately followed by the numeral "1" on Linear A administrative tablets (e.g. HT 117a, HT 85a,
HT 29, HT 103).

Compares those structurally-identified name slots against size-equalized, forward-spelled
Bronze Age onomastica (Amorite/Mari Gelb vs. Mycenaean Linear B Knossos/Pylos names vs.
Hittite/Hurrian TLHdig) under strict Linear B sign values + 1,000 consonant-series permutations.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
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
CORPUS_PATH = Path(
    os.environ.get("KAPHTOR_CORPUS_JSON", str(HERE.parents[1] / "data/linear-a/corpus.json"))
)
ORACC_LEVANT_NAMES = Path(
    os.environ.get(
        "KAPHTOR_ORACC_LEVANT_NAMES",
        str(HERE.parents[1] / "data/share-alike/oracc-levant/name_occurrences.jsonl"),
    )
)
KASSITE_NAMES = Path(
    os.environ.get(
        "KAPHTOR_KASSITE_NAMES",
        str(HERE.parents[1] / "data/ane/kassite-concordances/entries.jsonl"),
    )
)
# Optional override: private Amorite/Mari name list (used when set and present)
AMORITE_PATH = Path(os.environ.get("KAPHTOR_AMORITE_ONOMASTICON", ""))
Word = tuple[tuple[str, str], ...]


def extract_structural_roster_names(corpus_path: Path = CORPUS_PATH) -> list[Word]:
    """Undamaged >=3-sign words immediately followed by numeral '1' on administrative tablets."""
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    sign_table = a.load_signs()
    valid_signs = {k for k in sign_table.values() if isinstance(k, tuple)}
    out: list[Word] = []
    seen: set[Word] = set()
    for doc_id, rec in sorted(raw.items()):
        if any(tag in doc_id for tag in ("Za", "Zb", "Zc", "Zf", "Zg")):
            continue
        tw = rec.get("transliteratedWords") or []
        for i in range(len(tw) - 1):
            tok, nxt = tw[i], tw[i + 1]
            if str(nxt).strip() != "1":
                continue
            if not isinstance(tok, str) or any(ch in tok for ch in "[]?*+0123456789/\\· "):
                continue
            w = a.keys(tok, sign_table)
            if len(w) >= 3 and lid.valid(w, valid_signs) and w not in seen:
                seen.add(w)
                out.append(w)
    return out


def load_oracc_levant_names(tables: r.Tables, signs: set, max_n: int = 1500) -> list[Word]:
    """Shipped LBA Levant Semitic personal/royal names (Ugarit, Amarna, Alalakh; CC BY-SA 3.0)."""
    out: list[Word] = []
    seen: set[Word] = set()
    with open(ORACC_LEVANT_NAMES, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("damaged") or row.get("qpn_pos") not in ("PN", "RN"):
                continue
            form = str(row.get("normalized_form") or row.get("name") or "")
            if not form or "OR" in form:
                continue
            segs = lid.norm_segments(form.lower())
            if not segs:
                continue
            w = r.word(segs, "akkadian", tables, "plene")
            w = lid.glide(w, signs) if w else None
            if w and len(w) >= 3 and lid.valid(w, signs) and w not in seen:
                seen.add(w)
                out.append(w)
                if len(out) >= max_n:
                    break
    return out


def load_kassite_names(tables: r.Tables, signs: set, max_n: int = 1500) -> list[Word]:
    """Shipped Kassite-period personal names (Clay/Hinke/Radau/King concordances; Public Domain)."""
    out: list[Word] = []
    seen: set[Word] = set()
    with open(KASSITE_NAMES, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") != "person":
                continue
            form = str(row.get("normalized_key") or row.get("headword") or "")
            if not form or "(" in form or "?" in form:
                continue
            segs = lid.norm_segments(form.lower())
            if not segs:
                continue
            w = r.word(segs, "akkadian", tables, "plene")
            w = lid.glide(w, signs) if w else None
            if w and len(w) >= 3 and lid.valid(w, signs) and w not in seen:
                seen.add(w)
                out.append(w)
                if len(out) >= max_n:
                    break
    return out


def load_amorite_names(tables: r.Tables, signs: set, max_n: int = 1200) -> list[Word]:
    if not AMORITE_PATH or not AMORITE_PATH.is_file():
        return []
    out: list[Word] = []
    seen: set[Word] = set()
    with open(AMORITE_PATH, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            form = row.get("normalized") or row.get("name") or row.get("headword") or ""
            segs = lid.norm_segments(str(form).lower())
            if not segs:
                continue
            w = r.word(segs, "akkadian", tables, "plene")
            w = lid.glide(w, signs) if w else None
            if w and len(w) >= 3 and lid.valid(w, signs) and w not in seen:
                seen.add(w)
                out.append(w)
                if len(out) >= max_n:
                    break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-perm", type=int, default=500)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt missing.", file=sys.stderr)
        return 2

    t0 = time.time()
    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)

    roster_names = extract_structural_roster_names()
    levant_sem = load_oracc_levant_names(tables, signs, max_n=1500)
    kassite = load_kassite_names(tables, signs, max_n=1500)
    amorite = load_amorite_names(tables, signs, max_n=1200)

    # Rival >=3-sign lexical/onomastic pools (equalized to same type count)
    lb_docs, _ = lid.linear_b_docs(signs)
    mycenaean = sorted({w for _, ws in lb_docs for w in ws if len(w) >= 3})
    hur_docs, _ = lid.written_docs(lid.segment_docs("hurrian"), "hurrian", "plene", tables, signs)
    hurrian = sorted({w for _, ws in hur_docs for w in ws if len(w) >= 3})
    hit_docs, _ = lid.written_docs(lid.segment_docs("hittite"), "hittite", "plene", tables, signs)
    anatolian = sorted({w for _, ws in hit_docs for w in ws if len(w) >= 3})

    pools: dict[str, list[Word]] = {
        "levant_semitic": levant_sem,
        "kassite": kassite,
        "mycenaean_lb": mycenaean,
        "hurrian": hurrian,
        "anatolian": anatolian,
    }
    target_arm = "levant_semitic"
    if amorite:
        pools["amorite_semitic"] = amorite
        target_arm = "amorite_semitic"

    budget = min(len(v) for v in pools.values())
    rng = random.Random(20261122)
    models = {k: lid.Model(rng.sample(v, budget), 3, alphabet) for k, v in pools.items()}

    obs = {k: lid.bits_per_sign([m], roster_names) for k, m in models.items()}
    winner = min(obs, key=obs.get)
    obs_margin = min(v for k, v in obs.items() if k != target_arm) - obs[target_arm]

    prng = random.Random(20261122)
    pmargins = []
    ge = 0
    for _ in range(args.n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        prng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        pw = [ad.permute_word(w, mp) for w in roster_names]
        pf = {k: lid.bits_per_sign([m], pw) for k, m in models.items()}
        pm = min(v for k, v in pf.items() if k != target_arm) - pf[target_arm]
        pmargins.append(pm)
        if pm >= obs_margin - 1e-12:
            ge += 1
    mean = sum(pmargins) / len(pmargins)
    sd = math.sqrt(sum((x - mean) ** 2 for x in pmargins) / len(pmargins)) or 1e-9
    z = (obs_margin - mean) / sd
    p = (1 + ge) / (args.n_perm + 1)

    rec = {
        "n_roster_names": len(roster_names),
        "budget_per_arm": budget,
        "n_perm": args.n_perm,
        "target_arm": target_arm,
        "winner": winner,
        "bits": {k: round(v, 4) for k, v in obs.items()},
        "margin_obs": round(obs_margin, 4),
        "perm_mean": round(mean, 4),
        "z_perm": round(z, 3),
        "p_perm": round(p, 5),
        "seconds": round(time.time() - t0, 1),
    }
    if args.json:
        print(json.dumps(rec, indent=2))
        return 0

    print(f"=== Kernel H: Structurally-Gated Roster Onomastics (n={len(roster_names)} roster names, budget={budget}/arm, B={args.n_perm}, {rec['seconds']}s) ===")
    print(f"  winner={winner} | bits={{ {', '.join(f'{k}: {v:.4f}' for k,v in obs.items())} }}")
    print(f"  M({target_arm})={obs_margin:+.4f} | perm_mean={mean:+.4f} | Z_perm={z:+.2f} | p_perm={p:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
