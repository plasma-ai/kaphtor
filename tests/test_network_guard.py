"""The network guard in conftest.py: no test reaches past this machine.

Each case runs a small pytest session with the guard as its conftest. A connection or a name lookup for any host but
this one fails the test that made it, and names the address, even inside a client's own `except Exception`. Loopback
stays open. Nothing here reaches the network: 192.0.2.1 is a documentation address, and the guard stops the
connection before it is attempted.
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = Path(__file__).with_name("conftest.py")


@pytest.fixture
def go(pytester, tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("KAPHTOR_DATA", str(data))
    monkeypatch.setenv("PYTHONPATH", str(REPO))
    pytester.makeconftest(GUARD.read_text(encoding="utf-8"))

    def run(body: str):
        pytester.makepyfile(test_inner="import socket\nimport urllib.request\n\n"
                                       "def test_inner():\n" + "".join(f"    {ln}\n" for ln in body.splitlines()))
        return pytester.runpytest_subprocess("-p", "no:cacheprovider")
    return run


@pytest.mark.parametrize("name, body", [
    ("socket", "socket.create_connection(('192.0.2.1', 80), timeout=0.5)"),
    ("swallowed by the caller", ("try:\n    socket.create_connection(('192.0.2.1', 80), timeout=0.5)\n"
                                 "except Exception:\n    pass")),
    ("urllib", "try:\n    urllib.request.urlopen('http://192.0.2.1/', timeout=0.5)\nexcept Exception:\n    pass"),
])
def test_a_connection_off_this_machine_fails_the_test_and_names_the_address(go, name, body):
    result = go(body)
    assert result.ret == pytest.ExitCode.TESTS_FAILED, name
    result.stdout.fnmatch_lines(["*network blocked*192.0.2.1*"])


def test_a_name_lookup_off_this_machine_fails_before_any_query(go):
    result = go("try:\n    socket.getaddrinfo('example.org', 443)\nexcept Exception:\n    pass")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*network blocked*example.org*"])


def test_loopback_stays_open(go):
    body = ("server = socket.socket()\nserver.bind(('127.0.0.1', 0))\nserver.listen(1)\n"
            "client = socket.create_connection(server.getsockname(), timeout=2)\n"
            "client.close()\nserver.close()\nsocket.getaddrinfo('localhost', 80)")
    assert go(body).ret == pytest.ExitCode.OK
