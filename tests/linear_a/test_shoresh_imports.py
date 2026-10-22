"""The Shoresh modules load and run from this repository alone: each is imported in an isolated interpreter (-I -S:
no environment, no site-packages) with only the repository on its path, and no module is loaded from outside it or
the standard library. The semantic
gate's frozen tagger is checked against the hash A18 froze. No data is read; nothing writes.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.core import semantic_gate

PROBE = """
import json, sys, sysconfig
sys.path.insert(0, {root!r})
import tools.core.{module} as m
{calls}
stdlib = sysconfig.get_paths()["stdlib"]
outside = sorted(f for f in (getattr(mod, "__file__", None) for mod in list(sys.modules.values()))
                 if f and not f.startswith({root!r}) and not f.startswith(stdlib))
print(json.dumps({{"result": result, "outside": outside}}))
"""

CALLS = {
    # KAPHTOR_DATA is empty: the correspondence table is absent, so it is recorded missing, and building an index
    # or reading the table names it.
    "root_index": """
from pathlib import Path
from tools.paths import CACHE, NotInCheckout
from tools.core.semitic_root_schema import _correspondences
def refused(call):
    try:
        call()
    except NotInCheckout as e:
        return str(e).split(' is not')[0]
table = m.KEY_LOGIC_FILES[0]
result = [m.shadow_key(('š', 'm', 'ʿ'))[0], m.shadow_key(('ʾ', 'm', 'r'))[0], table.name,
          m._key_logic_hashes()[m._portable(table)], m.DEFAULT_INDEX == CACHE / 'root_index.sqlite',
          refused(lambda: m.write_index(Path('index.sqlite'), m.DEFAULT_ROOTS)), Path('index.sqlite').exists(),
          refused(_correspondences)]""",
    "semantic_gate": "result = [m.tagger().classify(\"a ship's oar\"), list(m._key('a-pa₃'))]",
    "root_match": ("result = [list(m.phonemes('ʾṯr')), m.word_signs('KU-PA₃-NU'), list(m.sign_decomposition('PA₃')),"
                   " sorted(m.GEMINABLE_STOPS)]"),
    "competitors": """
from tools.paths import NotInCheckout
try:
    m.load(m.COMPETITORS[0])
    missing = None
except NotInCheckout as e:
    missing = str(e).split(' is not')[0]
result = [list(m.key_of({'Consonantal_Root': 'ka-ta-bu', 'Meaning': 'write'})), m.is_name({'Meaning': 'Baal (DN)'}),
          missing]""",
}
# The private originals' values on the same calls.
EXPECTED = {
    "root_index": ["SM", "MR", "semitic_correspondences.json", "missing", True, "semitic_correspondences.json", False,
                   "semitic_correspondences.json"],
    "semantic_gate": [["maritime"], ["A", "PA3"]],
    "root_match": [["ʾ", "ṯ", "r"], ["KU", "PA₃", "NU"], ["b", "a"], ["b", "d", "k", "p", "q", "t"]],
    "competitors": [["k", "t", "b"], True, "luwian_roots.json"],
}


@pytest.mark.parametrize("module", sorted(CALLS))
def test_the_module_runs_from_the_repository_alone(module, tmp_path):
    probe = PROBE.format(root=str(ROOT), module=module, calls=CALLS[module])
    done = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", probe], cwd=tmp_path, capture_output=True, text=True,
                          timeout=120, env={"PYTHONDONTWRITEBYTECODE": "1", "KAPHTOR_DATA": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)
    assert out["outside"] == []
    assert out["result"] == EXPECTED[module]


def test_the_frozen_tagger_is_the_one_a18_froze():
    assert hashlib.sha256(semantic_gate.TAGGER.read_bytes()).hexdigest() == semantic_gate.TAGGER_SHA256
    assert semantic_gate.TAGGER.is_relative_to(ROOT)


def test_a_changed_tagger_is_refused(tmp_path, monkeypatch):
    changed = tmp_path / "tag_semantic_fields.py"
    changed.write_bytes(semantic_gate.TAGGER.read_bytes() + b"\n")
    monkeypatch.setattr(semantic_gate, "TAGGER", changed)
    semantic_gate.tagger.cache_clear()
    try:
        with pytest.raises(semantic_gate.TaggerChanged):
            semantic_gate.tagger()
    finally:
        semantic_gate.tagger.cache_clear()
