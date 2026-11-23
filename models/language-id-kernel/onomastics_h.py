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
# the Amorite name list (amorite_onomasticon.jsonl): not shipped; name its path in KAPHTOR_AMORITE_ONOMASTICON
AMORITE_PATH = Path(os.environ.get("KAPHTOR_AMORITE_ONOMASTICON", "amorite_onomasticon.jsonl"))
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
            if not isinstance(tok, str) or any(ch in tok for ch in "[]?*+0123456789/\· "):
                continue
            w = a.keys(tok, sign_table)
            if len(w) >= 3 and lid.valid(w, valid_signs) and w not in seen:
                seen.add(w)
                out.append(w)
    return out


def load_amorite_names(tables: r.Tables, signs: set, max_n: int = 1200) -> list[Word]:
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
    args = ap.parse_args()
    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt missing.", file=sys.stderr)
        return 2

    t0 = time.time()
    tables, signs = r.load_tables(), lid.sign_keys()
    alphabet = sorted(signs)

    roster_names = extract_structural_roster_names()
    amorite = load_amorite_names(tables, signs, max_n=1200)

    # Rival >=3-sign lexical/onomastic pools (equalized to same type count)
    lb_docs, _ = lid.linear_b_docs(signs)
    mycenaean = sorted({w for _, ws in lb_docs for w in ws if len(w) >= 3})
    hur_docs, _ = lid.written_docs(lid.segment_docs("hurrian"), "hurrian", "plene", tables, signs)
    hurrian = sorted({w for _, ws in hur_docs for w in ws if len(w) >= 3})
    hit_docs, _ = lid.written_docs(lid.segment_docs("hittite"), "hittite", "plene", tables, signs)
    anatolian = sorted({w for _, ws in hit_docs for w in ws if len(w) >= 3})

    pools = {"amorite_semitic": amorite, "mycenaean_lb": mycenaean, "hurrian": hurrian, "anatolian": anatolian}
    budget = min(len(v) for v in pools.values())
    rng = random.Random(20261122)
    models = {k: lid.Model(rng.sample(v, budget), 3, alphabet) for k, v in pools.items()}

    obs = {k: lid.bits_per_sign([m], roster_names) for k, m in models.items()}
    winner = min(obs, key=obs.get)
    obs_margin = min(v for k, v in obs.items() if k != "amorite_semitic") - obs["amorite_semitic"]

    prng = random.Random(20261122)
    pmargins = []
    ge = 0
    for _ in range(args.n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        prng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        pw = [ad.permute_word(w, mp) for w in roster_names]
        pf = {k: lid.bits_per_sign([m], pw) for k, m in models.items()}
        pm = min(v for k, v in pf.items() if k != "amorite_semitic") - pf["amorite_semitic"]
        pmargins.append(pm)
        if pm >= obs_margin - 1e-12:
            ge += 1
    mean = sum(pmargins) / len(pmargins)
    sd = math.sqrt(sum((x - mean) ** 2 for x in pmargins) / len(pmargins)) or 1e-9
    z = (obs_margin - mean) / sd
    p = (1 + ge) / (args.n_perm + 1)

    print(f"=== Kernel H: Structurally-Gated Roster Onomastics (n={len(roster_names)} roster names, budget={budget}/arm, B={args.n_perm}, {round(time.time()-t0,1)}s) ===")
    print(f"  winner={winner} | bits={{ {', '.join(f'{k}: {v:.4f}' for k,v in obs.items())} }}")
    print(f"  M(amorite_semitic)={obs_margin:+.4f} | perm_mean={mean:+.4f} | Z_perm={z:+.2f} | p_perm={p:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
