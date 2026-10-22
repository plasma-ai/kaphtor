"""The data guard in conftest.py: each case runs a small pytest session against its own data folder (KAPHTOR_DATA)
with the guard as that session's conftest, and checks the session's exit status and report. Every write happens
under tmp_path.
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = Path(__file__).with_name("conftest.py")


@pytest.fixture
def run(pytester, tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "linear-a").mkdir(parents=True)
    (data / "linear-a" / "lexicon.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("KAPHTOR_DATA", str(data))
    monkeypatch.setenv("PYTHONPATH", str(REPO))
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))

    def go(body: str):
        pytester.makepyfile(test_inner="import os\nfrom pathlib import Path\nDATA = Path(os.environ['KAPHTOR_DATA'])\n\n"
                                       "def test_inner():\n" + "".join(f"    {ln}\n" for ln in body.splitlines()))
        return pytester.runpytest_subprocess("-p", "no:cacheprovider")
    return data, go


def test_a_clean_run_passes(run):
    _, go = run
    assert go("assert (DATA / 'linear-a' / 'lexicon.json').read_text() == '{}'").ret == 0


@pytest.mark.parametrize("name, body", [
    ("added", "(DATA / 'linear-a' / 'probe.txt').write_text('x')"),
    ("changed", "(DATA / 'linear-a' / 'lexicon.json').write_text('{\"a\": 1}')"),
    ("removed", "(DATA / 'linear-a' / 'lexicon.json').unlink()"),
    ("same size, mtime put back", ("p = DATA / 'linear-a' / 'lexicon.json'\nst = p.stat()\np.write_text('[]')\n"
                                   "os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))")),
    ("broken symlink", "(DATA / 'linear-a' / 'link').symlink_to(DATA / 'nowhere')"),
])
def test_a_change_under_data_fails_the_run_and_is_named(run, name, body):
    _, go = run
    result = go(body)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, name
    result.stdout.fnmatch_lines(["*data/ changed during the run*", "*linear-a*"])


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions, not as root")
def test_an_unreadable_folder_fails_the_run_and_is_named(run):
    data, go = run
    locked = data / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        result = go("pass")
    finally:
        locked.chmod(0o755)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*cannot read*locked*"])
