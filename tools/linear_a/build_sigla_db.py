#!/usr/bin/env python3
"""Build data/linear-a/sigla_db.json from SigLA's own database (data/linear-a/sigla/database.js).

SigLA (sigla.phis.me; Salgarella and Castellan) ships its whole corpus as two OCaml Marshal blobs in database.js.
This decodes the `data` blob into one record per document: metadata, every sign position (reading, SigLA's
certainty flag, role with its doubt flag, erasure flag, hidden flag; unread positions kept), and SigLA's own word
division with its per-word flag pair. Positions SigLA leaves unread stay unread, and its word groups stand as SigLA
sets them. Each sign keeps SigLA's code, its value with the index as a subscript (AB29 pu₂), its name (AB30
FIC, A707 J), its variant tag (AB21 f) and a sign_id written as sigla-sign-map.json writes its ab_number (AB21F,
A709-2); ids the map writes otherwise (vessel signs, A402VAS) do not join it. Left out: the image geometry of each
position, and the sign record's reference field.

Each document is matched to its corpus.json record (corpus_key), read-only from corpus.json, with hand-set
matches in sigla/corpus_key_overrides.json. The CEFAEL session token (ce=…) is dropped from edition links.

Read-only on the sources. Before replacing sigla_db.json the old file is copied into --backups (default
tools.paths.BACKUPS, outside the repository) under a name that cannot already exist, and the build refuses to drop
a document the old file holds, or to shrink one's positions or words, unless --allow-drop. No network, no model.

    uv run tools/linear_a/build_sigla_db.py --dry-run   # decode and report; write nothing
    uv run tools/linear_a/build_sigla_db.py             # write data/linear-a/sigla_db.json

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import BACKUPS, LINEAR_A_DATA, NotInCheckout, require

SOURCE_NAME = "sigla/database.js"
OVERRIDES_NAME = "sigla/corpus_key_overrides.json"
OUT_NAME = "sigla_db.json"
SOURCE_LABEL = "data/linear-a/sigla/database.js"

sys.setrecursionlimit(100000)


# --- OCaml Marshal reader -------------------------------------------------------------------------------------

def blob(text: str, var: str) -> bytes:
    """The bytes of the `var <var> = '"\\\\NNN…"'` line of database.js."""
    line = next((l for l in text.split("\n") if l.startswith(f"var {var} = ")), None)
    if line is None:
        raise ValueError(f"no `var {var} = ` line in the source")
    body = line[line.index("'") + 1 : line.rindex("'")]
    if not (body[0] == '"' and body[-1] == '"'):
        raise ValueError(f"unexpected {var} literal")
    if not re.fullmatch(r"(?:\\\\\d{3})*", body[1:-1]):
        raise ValueError(f"{var} literal holds something other than \\\\ddd byte escapes")
    return bytes(int(d) for d in re.findall(r"\\\\(\d{3})", body))


class Reader:
    """A reader for the OCaml Marshal format: blocks become lists (tag 0) or {"t": tag, "f": fields}."""

    def __init__(self, b: bytes):
        magic, self.dlen, self.nobj, _, _ = struct.unpack(">IIIII", b[:20])
        if magic != 0x8495A6BE:
            raise ValueError(f"bad Marshal magic {magic:#x}")
        self.b, self.p, self.tab = b, 20, []

    def finish(self):
        """Raise unless the whole stream was read and the object count matches the header."""
        if self.p != len(self.b) or self.p != 20 + self.dlen:
            raise ValueError(f"Marshal stream: read {self.p} of {len(self.b)} bytes (header says {20 + self.dlen})")
        if len(self.tab) != self.nobj:
            raise ValueError(f"Marshal stream: {len(self.tab)} objects, header says {self.nobj}")

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def take(self, n, fmt):
        v = struct.unpack(fmt, self.b[self.p : self.p + n])[0]; self.p += n; return v

    def string(self, n):
        raw = self.b[self.p : self.p + n]; self.p += n
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("latin-1")
        self.tab.append(s)
        return s

    def block(self, tag, size):
        if size == 0:
            return {"t": tag, "f": []} if tag else []
        obj = [] if tag == 0 else {"t": tag, "f": []}
        self.tab.append(obj)
        fields = obj if tag == 0 else obj["f"]
        for _ in range(size):
            fields.append(self.read())
        return obj

    def read(self):
        c = self.u8()
        if c >= 0x80:
            return self.block(c & 0xF, (c >> 4) & 0x7)
        if c >= 0x40:
            return c & 0x3F
        if c >= 0x20:
            return self.string(c & 0x1F)
        if c == 0x00: return self.take(1, ">b")
        if c == 0x01: return self.take(2, ">h")
        if c == 0x02: return self.take(4, ">i")
        if c == 0x03: return self.take(8, ">q")
        if c in (0x04, 0x05, 0x06):
            n = {0x04: 1, 0x05: 2, 0x06: 4}[c]
            off = int.from_bytes(self.b[self.p : self.p + n], "big"); self.p += n
            return self.tab[len(self.tab) - off]
        if c == 0x08:
            h = self.take(4, ">I")
            return self.block(h & 0xFF, h >> 10)
        if c == 0x13:
            h = self.take(8, ">Q")
            return self.block(h & 0xFF, h >> 10)
        if c == 0x09: return self.string(self.u8())
        if c == 0x0A: return self.string(self.take(4, ">I"))
        if c in (0x0B, 0x0C):
            v = self.take(8, ">d" if c == 0x0B else "<d"); self.tab.append(v); return v
        if c in (0x0D, 0x0E, 0x0F, 0x07):
            n = self.u8() if c in (0x0D, 0x0E) else self.take(4, ">I")
            fmt = ">d" if c in (0x0D, 0x0F) else "<d"
            arr = [self.take(8, fmt) for _ in range(n)]
            self.tab.append(arr); return arr
        raise ValueError(f"unsupported Marshal code {c:#x} at {self.p - 1}")


# --- SigLA records ----------------------------------------------------------------------------------------------

def _walk(n, out):
    """OCaml Map node [left, key, value, right, height] -> out[key] = value."""
    if isinstance(n, list) and len(n) == 5 and isinstance(n[1], str):
        _walk(n[0], out)
        out[n[1]] = n[2]
        _walk(n[3], out)


SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _sign(p, variant) -> dict:
    """A sign record [series, number, [[value, index]], [reference], [name], ...] and its variant tags -> one sign.

    phon keeps SigLA's value index as a subscript (AB29 pu₂); name is SigLA's name for the sign, a logogram's
    abbreviation or a fraction's letter (AB30 FIC, A707 J); variant is SigLA's tag (AB21 f, A709 2); sign_id is written in the sign map's form (AB21F, A709-2; AB numbers two
    digits)."""
    ph = p[2][0] if isinstance(p[2], list) and p[2] else None
    name = p[4][0] if isinstance(p[4], list) and p[4] else None
    phon = None
    if ph is not None:
        value, index = (ph[0], ph[1]) if isinstance(ph, list) else (ph, 0)
        if isinstance(index, list):
            index = index[0] if index else None
        phon = str(value) + (str(index).translate(SUBSCRIPT) if index not in (0, None) else "")
    tags = [str(t) for t in variant] if isinstance(variant, list) else []
    num = f"{int(p[1]):02d}" if p[0] == "AB" and str(p[1]).isdigit() else str(p[1])
    sign_id = f"{p[0]}{num}" + "".join(f"-{t}" if t.isdigit() else t.upper() for t in tags)
    return {"code": f"{p[0]}{p[1]}", "phon": phon, "name": name, "variant": "".join(tags) or None,
            "sign_id": sign_id}


def _signs(pat) -> list[dict]:
    """A reading [sign, variant tags] -> its signs in order, [{code, phon, variant, sign_id}]."""
    if isinstance(pat, list) and len(pat) == 2 and isinstance(pat[0], list) and len(pat[0]) == 9:
        return [_sign(pat[0], pat[1])]
    found = []

    def collect(p):
        if isinstance(p, list) and len(p) == 9 and isinstance(p[0], str):
            found.append(_sign(p, None))
        elif isinstance(p, list):
            for x in p:
                collect(x)
        elif isinstance(p, dict):
            for x in p["f"]:
                collect(x)
    collect(pat)
    return found


# Occurrence field 3 is [role, doubt]: a block [index, word] for a sign inside a word, which SigLA's pages call a
# syllabogram, else a constant; doubt 1 is SigLA's "?" on the role ("Unknown?").
ROLES = {0: "logogram", 1: "fraction", 2: "transaction_sign", 3: "unknown"}


def _occurrence(o) -> dict:
    r, pos = o[1], o[2]
    role, doubt = o[3]
    flags = {
        "role": "syllabogram" if isinstance(role, list) else ROLES[role],
        "role_certain": not doubt,
        "erased": bool(o[4]),
        "hidden": bool(o[6]),
    }
    if r in (0, 1):
        return {"position": pos, "read": False, "signs": [], "certain": None, **flags, "sigla_kind": r}
    return {"position": pos, "read": True, "signs": _signs(r[0]), "certain": bool(r[1]), **flags,
            "sigla_kind": None}


def _label(occ: dict) -> str:
    """Display form: a syllabogram's phonetic value upper-cased (code when it has none); any other role its code, a
    logogram's with SigLA's name (AB30/FIC); [?] unread; (?) after an uncertain reading; ligatures joined by +."""
    if not occ["read"]:
        return "[?]"
    if occ["role"] == "syllabogram":
        parts = [(s["phon"].upper() if s["phon"] else s["code"]) for s in occ["signs"]]
    else:
        parts = [s["code"] + (f"/{s['name']}" if occ["role"] == "logogram" and s["name"] else "")
                 for s in occ["signs"]]
    lab = "+".join(parts)
    return lab if occ["certain"] else f"{lab}(?)"


def _strip_session(url: str) -> str:
    """Drop the CEFAEL session token (ce=…), a per-visit id that SigLA's edition links carry."""
    if not isinstance(url, str):
        return url
    return re.sub(r"[?&]$", "", re.sub(r"([?&])ce=[^&]*&?", r"\1", url))


def _meta(m: list) -> dict:
    def opt(x):
        return x if x not in (0, None) else None
    seals = []
    if isinstance(m[9], list):
        for s in m[9]:
            seals.append({
                "cms": s[1][0] if s[1] else None,
                "motif": s[2][0] if s[2] else None,
                "count": s[0],
                "arachne_url": s[3][0] if isinstance(s[3], list) and s[3] else None,
            })
    return {
        "support": m[0],
        "site": m[2],
        "dimensions_cm": opt(m[6])[0] if opt(m[6]) else None,
        "period": (m[7][0] or None) if isinstance(m[7], list) and m[7] else None,
        "edition_url": _strip_session(m[8][0]) if isinstance(m[8], list) and m[8] else None,
        "seals": seals,
    }


def corpus_id(sigla_id: str) -> str:
    """'HT 25a' -> 'HT25a': the SigLA id with spaces removed (not always a corpus.json key; see corpus_keys)."""
    return sigla_id.replace(" ", "")


def _norm(key: str) -> str:
    return re.sub(r"[\s`<>]", "", key).lower()


def corpus_keys(sigla_ids, corpus: dict, overrides: dict) -> dict:
    """SigLA id -> (corpus.json key or None, how it was matched), the first rule that holds:

    sigla_id: one corpus.json record's sigla.id names this document. override: sigla/corpus_key_overrides.json.
    key: the id with spaces removed is a corpus.json key. face: the id less a face suffix (a, b, α, β, γ, -latus)
    is one corpus.json key.
    """
    by_block = {}
    for k, v in corpus.items():
        sid = v.get("sigla", {}).get("id") if isinstance(v.get("sigla"), dict) else None
        if sid:
            by_block.setdefault(sid, []).append(k)
    by_norm = {}
    for k in corpus:
        by_norm.setdefault(_norm(k), []).append(k)
    out = {}
    for sid in sigla_ids:
        if len(by_block.get(sid, [])) == 1:
            out[sid] = (by_block[sid][0], "sigla_id")
        elif sid in overrides:
            out[sid] = (overrides[sid], "override")
        elif corpus_id(sid) in corpus:
            out[sid] = (corpus_id(sid), "key")
        else:
            base = re.sub(r"(-latus|[abαβγ])(>?)$", r"\2", sid)
            hits = by_norm.get(_norm(base), []) if base != sid else []
            out[sid] = (hits[0], "face") if len(hits) == 1 else (None, None)
    return out


def decode(text: str) -> dict:
    """SigLA's `data` blob -> {sigla_id: record}; corpus_key and corpus_match are filled by build()."""
    r = Reader(blob(text, "data"))
    v = r.read()
    r.finish()
    raw = {}
    _walk(v[0], raw)
    docs = {}
    for doc_id, val in raw.items():
        rec = val[0]
        occs = {o[2]: _occurrence(o) for o in rec[4]}
        words = []
        in_word = set()
        for w in rec[2]:
            ps, node = [], w[1]
            while isinstance(node, list) and len(node) == 2:
                ps.append(node[0][2])
                node = node[1]
            in_word.update(ps)
            words.append({"positions": ps, "text": "-".join(_label(occs[p]) for p in ps if p in occs),
                          "sigla_word_flag": w[2]})
        docs[doc_id] = {
            "sigla_id": doc_id,
            "corpus_id": corpus_id(doc_id),
            "corpus_key": None,
            "corpus_match": None,
            **_meta(rec[0]),
            "positions": [occs[p] for p in sorted(occs)],
            "words": words,
            "outside_words": [p for p in sorted(occs) if p not in in_word],
        }
    return docs


DESCRIPTION = (
    "SigLA's own corpus, decoded from its database.js (data/linear-a/sigla/database.js): per document the "
    "metadata, every sign position with SigLA's reading and certainty flag (unread positions kept, read false), "
    "its role (syllabogram, logogram, fraction, transaction_sign, unknown) with SigLA's doubt on the role "
    "(role_certain), and whether SigLA marks it erased or leaves it off its document page (hidden); and SigLA's "
    "word division, each word with SigLA's unlabelled flag pair (sigla_word_flag). Each sign keeps SigLA's code, "
    "value with its index (AB29 pu₂), name (AB30 FIC, A707 J), variant tag and a sign_id in the sign map's form "
    "(AB21F). `text` forms: a syllabogram's phonetic value upper-cased, [?] unread, (?) an uncertain reading. Image "
    "geometry is left out. corpus_key is the corpus.json record the document belongs to (corpus_match says how it "
    "was found: sigla_id, override, key, face)."
)


def build(source: bytes, corpus: dict, overrides: dict) -> dict:
    """The whole sigla_db.json object for a database.js, a corpus and the overrides."""
    docs = decode(source.decode("utf-8"))
    for sid, (key, how) in corpus_keys(docs, corpus, overrides).items():
        docs[sid]["corpus_key"], docs[sid]["corpus_match"] = key, how
    positions = [p for d in docs.values() for p in d["positions"]]
    return {
        "description": DESCRIPTION,
        "source": {"file": SOURCE_LABEL, "sha256": hashlib.sha256(source).hexdigest(), "site": "https://sigla.phis.me"},
        "stats": {
            "documents": len(docs),
            "positions": len(positions),
            "unread": sum(1 for p in positions if not p["read"]),
            "uncertain": sum(1 for p in positions if p["read"] and not p["certain"]),
            "words": sum(len(d["words"]) for d in docs.values()),
            "corpus_keyed": sum(1 for d in docs.values() if d["corpus_key"]),
            "roles": {r: sum(1 for p in positions if p["role"] == r) for r in ("syllabogram", *ROLES.values())},
            "role_doubted": sum(1 for p in positions if not p["role_certain"]),
            "erased": sum(1 for p in positions if p["erased"]),
            "hidden": sum(1 for p in positions if p["hidden"]),
        },
        "documents": dict(sorted(docs.items())),
    }


def losses(old: dict, new: dict) -> tuple[list[str], list[str]]:
    """Documents the old file holds that the new one drops, and those whose positions or words shrink."""
    dropped = sorted(set(old) - set(new))
    shrunk = sorted(k for k in set(old) & set(new)
                    if len(new[k]["positions"]) < len(old[k].get("positions", []))
                    or len(new[k]["words"]) < len(old[k].get("words", [])))
    return dropped, shrunk


# --- write ------------------------------------------------------------------------------------------------------

def _backup(path: Path, backups: Path) -> Path:
    """Copy `path` into `backups` under a name that cannot already exist (exclusive create; never overwrites)."""
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    dest = backups / f"{path.name}.bak-{stamp}-{os.getpid()}"
    with path.open("rb") as src, dest.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    shutil.copystat(path, dest)
    return dest


def _write(out: dict, target: Path) -> None:
    """Write beside the target, fsync, then rename into place: a failed write leaves the old file intact."""
    target = target.resolve()
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when an input is not in the checkout, or when the build would lose documents."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="decode and report; write nothing")
    ap.add_argument("--allow-drop", action="store_true", help="permit dropping documents the old file holds")
    ap.add_argument("--data", type=Path, default=LINEAR_A_DATA,
                    help="the folder holding corpus.json, sigla/ and sigla_db.json (default: data/linear-a)")
    ap.add_argument("--backups", type=Path, default=BACKUPS, help="where the old sigla_db.json is copied first")
    args = ap.parse_args(argv)

    source = require(args.data / SOURCE_NAME, "sigla/database.js").read_bytes()
    corpus = json.loads(require(args.data / "corpus.json", "corpus.json").read_text(encoding="utf-8"))
    overrides_path = args.data / OVERRIDES_NAME
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))["overrides"] if overrides_path.exists() else {}
    out = build(source, corpus, overrides)
    s = out["stats"]
    print(f"{s['documents']} documents, {s['positions']} positions ({s['unread']} unread, {s['uncertain']} "
          f"uncertain), {s['words']} words; {s['corpus_keyed']} matched to a corpus.json key")
    print("roles: " + ", ".join(f"{r} {n}" for r, n in s["roles"].items())
          + f"; role doubted {s['role_doubted']}; erased {s['erased']}; hidden {s['hidden']}")

    target = args.data / OUT_NAME
    old = json.loads(target.read_text(encoding="utf-8")).get("documents", {}) if target.exists() else {}
    dropped, shrunk = losses(old, out["documents"])
    if (dropped or shrunk) and not args.allow_drop:
        if dropped:
            print(f"refusing: {len(dropped)} documents would be dropped (e.g. {dropped[:5]})", file=sys.stderr)
        if shrunk:
            print(f"refusing: {len(shrunk)} documents would lose positions or words (e.g. {shrunk[:5]})",
                  file=sys.stderr)
        print("pass --allow-drop to accept", file=sys.stderr)
        return 2
    if args.dry_run:
        print("dry run: nothing written")
        return 0
    if target.exists():
        print(f"backup: {_backup(target, args.backups)}")
    _write(out, target)
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
