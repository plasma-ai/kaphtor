"""`build_sigla_db.py`: the Marshal reader, SigLA's signs and words, the corpus keys, the build contract, and (data)
the shipped `sigla_db.json` reproduced from the shipped `database.js`.

The unit tests write a small database.js inline, in SigLA's own encoding, and build into tmp_path. Nothing here
writes to data/.
"""
import json
import struct

import pytest

from tools.linear_a import build_sigla_db as b
from tools.paths import LINEAR_A_DATA

# --- a small OCaml Marshal encoder: lists are tag-0 blocks, {"t", "f"} other tags ---------------------------------

def enc(x) -> bytes:
    if isinstance(x, int):
        return bytes([0x40 + x]) if 0 <= x < 64 else b"\x02" + struct.pack(">i", x)
    if isinstance(x, str):
        raw = x.encode("utf-8")
        return (bytes([0x20 + len(raw)]) if len(raw) < 32 else bytes([0x09, len(raw)])) + raw
    tag, fields = (x["t"], x["f"]) if isinstance(x, dict) else (0, x)
    if len(fields) < 8:
        head = bytes([0x80 | (len(fields) << 4) | tag])
    else:
        head = b"\x08" + struct.pack(">I", len(fields) << 10 | tag)
    return head + b"".join(enc(f) for f in fields)


def objects(x) -> int:
    """How many objects the reader files in its table for `x`: each string and each non-empty block."""
    if isinstance(x, int):
        return 0
    if isinstance(x, str):
        return 1
    fields = x["f"] if isinstance(x, dict) else x
    return (1 if fields else 0) + sum(objects(f) for f in fields)


def marshal(value, body: bytes | None = None, nobj: int | None = None) -> bytes:
    body = enc(value) if body is None else body
    nobj = objects(value) if nobj is None else nobj
    return struct.pack(">IIIII", 0x8495A6BE, len(body), nobj, 0, 0) + body


def database_js(value) -> str:
    """A database.js whose `data` line holds `value`, written as SigLA writes it ('"\\\\NNN…"')."""
    digits = "".join(f"\\\\{byte:03d}" for byte in marshal(value))
    return f"/* Signs */\nvar signs = '\"\"';\nvar data = '\"{digits}\"';\n"


def sign(series, number, value=None, index=0, name=None):
    """A SigLA sign record of nine fields: series, number, [[value, index]], reference, [name], four more."""
    return [series, number, [[value, index]] if value else [], ["HT 1/1"], [name] if name else 0, 0, 0, 0, 0]


def occurrence(position, reading, role, doubt, erased, hidden):
    """SigLA's eight occurrence fields: 0, reading, position, [role, doubt], erased, 0, hidden, geometry.

    role None is a sign inside a word ([index, word] in SigLA's data); else 0 logogram, 1 fraction, 2 transaction
    sign, 3 unknown."""
    return [0, reading, position, [[0, 0] if role is None else role, doubt], erased, 0, hidden, 0]


def read(position, s, variant=(), certain=1, role=None, doubt=0, erased=0, hidden=0):
    return occurrence(position, [[s, list(variant)], certain], role, doubt, erased, hidden)


def unread(position, kind=0, role=None, doubt=0, erased=0):
    return occurrence(position, kind, role, doubt, erased, 0)


def word(*positions, flag=(0, 0)):
    node = 0
    for p in reversed(positions):
        node = [[0, 0, p], node]
    return [0, node, list(flag), 0]


def meta(support="Tablet", site="Haghia Triada", period="LM IB", url=None, seals=()):
    return [support, 0, site, 0, 0, 0, 0, [period], [url] if url else 0, list(seals)]


def document(occurrences, words, **kw):
    return [[meta(**kw), 0, list(words), 0, list(occurrences)]]


def corpus_map(docs: dict):
    """An OCaml Map of the documents, as a right-leaning chain of [left, key, value, right, height] nodes."""
    node = 0
    for key in sorted(docs, reverse=True):
        node = [0, key, docs[key], node, 1]
    return [node]


HT_25A = document(
    [read(1, sign("AB", 79)), read(2, sign("AB", 65, "ju")), read(3, sign("AB", 29, "pu", ["2"])),
     unread(4), read(5, sign("AB", 21, "qi", name="OVIS"), variant=["f"], certain=0),
     read(6, sign("A", 707, name="J"), role=1), read(7, sign("AB", 30, "ni", name="FIC"), role=0, erased=1),
     read(8, sign("A", 330), role=3, hidden=1), unread(9, role=3, doubt=1, erased=1)],
    [word(1, 2, 3), word(4, 5, flag=(2, 0))],
    url="https://cefael.efa.gr/detail.php?site_id=1&ce=abc123&sp=80",
    seals=[[5, ["CMS II,6 no. 159"], ["bull"], 0]],
)


# --- the reader -------------------------------------------------------------------------------------------------

def test_the_reader_reads_blocks_strings_ints_and_shared_references():
    body = bytes([0x80 | (3 << 4)]) + enc("ab") + bytes([0x04, 1]) + enc(70)
    r = b.Reader(marshal(None, body, nobj=2))
    assert r.read() == ["ab", "ab", 70]
    r.finish()
    assert b.Reader(marshal({"t": 2, "f": [1, "x"]})).read() == {"t": 2, "f": [1, "x"]}


def test_the_reader_reads_every_wider_code():
    s300 = "s" * 300
    body = b"\x08" + struct.pack(">I", 8 << 10) + b"".join([   # block of eight fields, four-byte header
        b"\x00" + struct.pack(">b", -5),            # int8
        b"\x01" + struct.pack(">h", -300),          # int16
        b"\x02" + struct.pack(">i", 70000),         # int32
        b"\x09" + bytes([40]) + b"x" * 40,          # string, one-byte length
        b"\x0A" + struct.pack(">I", 300) + s300.encode(),  # string, four-byte length
        b"\x0C" + struct.pack("<d", 1.5),           # double, little-endian
        b"\x05" + struct.pack(">H", 3),             # shared reference, two-byte offset: the 40-x string
        b"\x13" + struct.pack(">Q", 1 << 10) + enc(7),  # block, eight-byte header
    ])
    r = b.Reader(marshal(None, body, nobj=5))
    assert r.read() == [-5, -300, 70000, "x" * 40, s300, 1.5, "x" * 40, [7]]
    r.finish()


def test_the_reader_refuses_a_stream_it_does_not_finish_or_whose_count_is_off():
    r = b.Reader(marshal(None, enc([1, "a"]) + enc(2), nobj=2))
    r.read()
    with pytest.raises(ValueError, match="read .* bytes"):
        r.finish()
    r = b.Reader(marshal([1, "a"], nobj=5))
    r.read()
    with pytest.raises(ValueError, match="objects, header says 5"):
        r.finish()


def test_the_reader_refuses_another_magic():
    with pytest.raises(ValueError, match="magic"):
        b.Reader(b"\x00" * 20 + enc(1)).read()


def test_blob_reads_the_named_line():
    text = database_js([1, "z"])
    assert b.Reader(b.blob(text, "data")).read() == [1, "z"]
    with pytest.raises(ValueError, match="var nope"):
        b.blob(text, "nope")


def test_blob_refuses_a_literal_with_anything_but_byte_escapes():
    text = database_js([1, "z"]).replace("\\\\132", "\\\\132x", 1)   # after the magic's first byte
    assert text != database_js([1, "z"])
    with pytest.raises(ValueError, match="byte escapes"):
        b.blob(text, "data")


# --- signs ------------------------------------------------------------------------------------------------------

def test_a_value_index_is_kept_as_a_subscript():
    assert b._sign(sign("AB", 76, "ra", ["2"]), [])["phon"] == "ra₂"
    assert b._sign(sign("AB", 60, "ra"), [])["phon"] == "ra"


def test_a_variant_is_kept_and_the_sign_id_joins_the_sign_map():
    assert b._sign(sign("AB", 21, "qi", name="OVIS"), ["f"]) == {
        "code": "AB21", "phon": "qi", "name": "OVIS", "variant": "f", "sign_id": "AB21F"}
    assert b._sign(sign("A", 709), ["2"])["sign_id"] == "A709-2"
    assert b._sign(sign("AB", 8, "a"), [])["sign_id"] == "AB08"
    assert b._sign(sign("AB", 120), [])["phon"] is None


def test_the_session_token_is_dropped_from_an_edition_link():
    assert b._strip_session("https://x/d.php?site_id=1&ce=abc&sp=80") == "https://x/d.php?site_id=1&sp=80"
    assert b._strip_session("https://x/d.php?ce=abc") == "https://x/d.php"
    assert b._strip_session(None) is None


# --- documents --------------------------------------------------------------------------------------------------

def test_decode_keeps_unread_positions_word_division_and_signs_outside_words():
    doc = b.decode(database_js(corpus_map({"HT 25a": HT_25A})))["HT 25a"]
    assert [w["text"] for w in doc["words"]] == ["AB79-JU-PU₂", "[?]-QI(?)"]
    assert [w["sigla_word_flag"] for w in doc["words"]] == [[0, 0], [2, 0]]
    assert doc["outside_words"] == [6, 7, 8, 9]
    unread_position = doc["positions"][3]
    assert unread_position == {"position": 4, "read": False, "signs": [], "certain": None, "role": "syllabogram",
                               "role_certain": True, "erased": False, "hidden": False, "sigla_kind": 0}
    assert doc["positions"][4]["certain"] is False and doc["positions"][4]["signs"][0]["sign_id"] == "AB21F"
    assert doc["edition_url"] == "https://cefael.efa.gr/detail.php?site_id=1&sp=80"
    assert doc["seals"] == [{"cms": "CMS II,6 no. 159", "motif": "bull", "count": 5, "arachne_url": None}]
    assert (doc["corpus_id"], doc["site"], doc["support"], doc["period"]) == ("HT25a", "Haghia Triada", "Tablet", "LM IB")


def test_each_position_keeps_sigla_s_role_its_doubt_erasure_and_hidden_flags():
    doc = b.decode(database_js(corpus_map({"HT 25a": HT_25A})))["HT 25a"]
    flags = {p["position"]: (p["role"], p["role_certain"], p["erased"], p["hidden"]) for p in doc["positions"]}
    assert flags == {1: ("syllabogram", True, False, False), 2: ("syllabogram", True, False, False),
                     3: ("syllabogram", True, False, False), 4: ("syllabogram", True, False, False),
                     5: ("syllabogram", True, False, False), 6: ("fraction", True, False, False),
                     7: ("logogram", True, True, False), 8: ("unknown", True, False, True),
                     9: ("unknown", False, True, False)}


def test_a_label_gives_a_syllabogram_its_value_and_any_other_role_its_code():
    doc = b.decode(database_js(corpus_map({"HT 25a": HT_25A})))["HT 25a"]
    labels = {p["position"]: b._label(p) for p in doc["positions"]}
    assert labels == {1: "AB79", 2: "JU", 3: "PU₂", 4: "[?]", 5: "QI(?)", 6: "A707", 7: "AB30/FIC", 8: "A330",
                      9: "[?]"}


def test_an_empty_period_is_null():
    doc = b.decode(database_js(corpus_map({"PS Za 2": document([read(1, sign("AB", 1, "da"))], [word(1)],
                                                                period="")})))["PS Za 2"]
    assert doc["period"] is None


def test_corpus_keys_take_the_first_rule_that_holds():
    corpus = {"HT25a": {"sigla": {"id": "HT 25a"}}, "HT123+124a": {}, "KH5": {}, "HTWa1019": {},
              "A1": {"sigla": {"id": "Z 1"}}, "A2": {"sigla": {"id": "Z 1"}}}
    ids = ["HT 25a", "HT 123a", "KH 5", "HT Wa 1019α", "Z 1", "QQ 9"]
    assert b.corpus_keys(ids, corpus, {"HT 123a": "HT123+124a"}) == {
        "HT 25a": ("HT25a", "sigla_id"), "HT 123a": ("HT123+124a", "override"), "KH 5": ("KH5", "key"),
        "HT Wa 1019α": ("HTWa1019", "face"), "Z 1": (None, None), "QQ 9": (None, None)}


# --- the build --------------------------------------------------------------------------------------------------

@pytest.fixture
def data(tmp_path):
    root = tmp_path / "linear-a"
    (root / "sigla").mkdir(parents=True)
    (root / "sigla" / "database.js").write_text(
        database_js(corpus_map({"HT 25a": HT_25A, "HT 25b": document([read(1, sign("AB", 1, "da"))], [word(1)])})),
        encoding="utf-8")
    (root / "sigla" / "corpus_key_overrides.json").write_text('{"overrides": {}}', encoding="utf-8")
    corpus = {"HT25a": {"sigla": {"id": "HT 25a"}}, "HT25b": {}}
    (root / "corpus.json").write_text(json.dumps(corpus), encoding="utf-8")
    return root


def run(data, tmp_path, *extra):
    return b.main(["--data", str(data), "--backups", str(tmp_path / "backups"), *extra])


def test_the_build_writes_the_file_and_names_its_source(data, tmp_path):
    assert run(data, tmp_path) == 0
    out = json.loads((data / "sigla_db.json").read_text(encoding="utf-8"))
    assert out["source"]["file"] == "data/linear-a/sigla/database.js" and "fetched" not in out["source"]
    assert out["stats"] == {"documents": 2, "positions": 10, "unread": 2, "uncertain": 1, "words": 3,
                            "corpus_keyed": 2,
                            "roles": {"syllabogram": 6, "logogram": 1, "fraction": 1, "transaction_sign": 0,
                                      "unknown": 2},
                            "role_doubted": 1, "erased": 2, "hidden": 1}
    assert out["documents"]["HT 25b"]["corpus_match"] == "key"
    assert not (tmp_path / "backups").exists()
    assert (data / "sigla_db.json").stat().st_mode & 0o777 == 0o644


def test_a_dry_run_writes_nothing(data, tmp_path):
    assert run(data, tmp_path, "--dry-run") == 0
    assert not (data / "sigla_db.json").exists()


def test_a_rebuild_backs_up_the_old_file_outside_the_data(data, tmp_path):
    run(data, tmp_path)
    first = (data / "sigla_db.json").read_bytes()
    assert run(data, tmp_path) == 0
    (backup,) = (tmp_path / "backups").iterdir()
    assert backup.read_bytes() == first and backup.name.startswith("sigla_db.json.bak-")
    assert sorted(p.name for p in data.iterdir()) == ["corpus.json", "sigla", "sigla_db.json"]


def test_the_build_refuses_to_drop_a_document_or_shrink_one(data, tmp_path):
    run(data, tmp_path)
    old = json.loads((data / "sigla_db.json").read_text(encoding="utf-8"))
    old["documents"]["HT 99"] = {"positions": [], "words": []}
    old["documents"]["HT 25b"]["words"].append({"positions": [], "text": ""})
    (data / "sigla_db.json").write_text(json.dumps(old), encoding="utf-8")
    assert run(data, tmp_path) == 2
    assert json.loads((data / "sigla_db.json").read_text(encoding="utf-8")) == old
    assert run(data, tmp_path, "--allow-drop") == 0
    assert "HT 99" not in json.loads((data / "sigla_db.json").read_text(encoding="utf-8"))["documents"]


def test_a_missing_source_is_named(tmp_path, capsys):
    assert b.main(["--data", str(tmp_path), "--dry-run"]) == 2
    assert "sigla/database.js is not in this checkout" in capsys.readouterr().err


# --- the shipped file -------------------------------------------------------------------------------------------

@pytest.mark.data
def test_the_shipped_file_is_what_the_builder_makes_of_the_shipped_source():
    source = (LINEAR_A_DATA / "sigla" / "database.js").read_bytes()
    corpus = json.loads((LINEAR_A_DATA / "corpus.json").read_text(encoding="utf-8"))
    overrides = json.loads((LINEAR_A_DATA / "sigla" / "corpus_key_overrides.json").read_text(encoding="utf-8"))
    shipped = json.loads((LINEAR_A_DATA / "sigla_db.json").read_text(encoding="utf-8"))
    built = b.build(source, corpus, overrides["overrides"])
    assert shipped["source"] == built["source"]
    assert shipped["stats"] == built["stats"]
    assert shipped == built


@pytest.mark.data
def test_the_shipped_file_reads_known_positions_as_sigla_shows_them():
    docs = json.loads((LINEAR_A_DATA / "sigla_db.json").read_text(encoding="utf-8"))["documents"]

    def at(doc, position):
        return next(p for p in docs[doc]["positions"] if p["position"] == position)

    ht84 = at("HT 84", 1)                       # QI-JA-DU: AB21 with SigLA's variant f
    assert (ht84["role"], ht84["signs"][0]["sign_id"], b._label(ht84)) == ("syllabogram", "AB21F", "QI")
    assert [w["text"] for w in docs["HT 84"]["words"]][:3] == ["QI-JA-DU", "[?]", "NU-TI"]
    arkh = at("ARKH 1a", 3)                     # a logogram that also carries a phonetic value
    assert (arkh["role"], arkh["signs"][0]["phon"], b._label(arkh)) == ("logogram", "qa", "AB16")
    kh8 = at("KH 8", 10)                        # SigLA: AB30/FIC, Erasure (Logogram)
    assert (kh8["role"], kh8["erased"], b._label(kh8)) == ("logogram", True, "AB30/FIC")
    assert at("HT 13", 6)["role"] == "transaction_sign"
    ht22 = at("HT 22", 3)                       # off SigLA's HT 22 page, which shows positions 1-2
    assert (ht22["role"], ht22["hidden"]) == ("unknown", True)
    ht115 = at("HT 115a", 37)                   # SigLA: Erasure (Unknown?)
    assert (ht115["read"], ht115["role"], ht115["role_certain"], ht115["erased"]) == (False, "unknown", False, True)
