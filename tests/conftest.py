"""No test may write into the data folder.

The session records every entry under DATA before the first test and again after the last: its size, its mtime and
its ctime, read with lstat so a symlink counts as itself. ctime moves on any write and cannot be set back, so a rewrite
that keeps a file's size and restores its mtime is still seen. An entry added, changed or removed fails the run, and
so does a folder the guard cannot read; the report names each. Another process writing into data/ during the run
fails it too, which is why the report says what changed, not who changed it. A test that writes uses `tmp_path`.

A test marked neither `data` nor `maintainer` is marked `unit` here, so `-m unit` selects what runs on a fresh clone.

No test reaches past this machine. A socket connection or a name lookup for any host but this one fails the test
that made it and names the address; the failure is raised past a client's own `except Exception`. Loopback stays
open. A test of a remote client stubs its request.
"""
import ipaddress
import os
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.paths import DATA

_before: dict = {}
_unreadable: list = []


def _data_entries() -> dict:
    """(size, mtime, ctime) for every entry under DATA, symlinks included; unreadable folders go to `_unreadable`."""
    entries = {}
    for root, dirs, names in os.walk(DATA, onerror=lambda error: _unreadable.append(error.filename)):
        for name in names + [d for d in dirs if os.path.islink(os.path.join(root, d))]:
            if name == ".DS_Store":
                continue
            path = os.path.join(root, name)
            st = os.lstat(path)
            entries[path] = (st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    return entries


_connect, _connect_ex, _getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo


def _local(host) -> bool:
    if host in (None, "", "localhost"):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def _blocked(where) -> None:
    pytest.fail(f"network blocked: a test reached for {where!r}; stub the request instead", pytrace=False)


def _guarded_connect(self, address):
    if isinstance(address, tuple) and not _local(address[0]):
        _blocked(address)
    return _connect(self, address)


def _guarded_connect_ex(self, address):
    if isinstance(address, tuple) and not _local(address[0]):
        _blocked(address)
    return _connect_ex(self, address)


def _guarded_getaddrinfo(host, *args, **kwargs):
    if not _local(host if not isinstance(host, bytes) else host.decode()):
        try:
            ipaddress.ip_address(str(host))  # a literal address needs no lookup; its connect is checked
        except ValueError:
            _blocked(host)
    return _getaddrinfo(host, *args, **kwargs)


def pytest_configure(config):
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo


def pytest_collection_modifyitems(items):
    for item in items:
        if not (item.get_closest_marker("data") or item.get_closest_marker("maintainer")):
            item.add_marker(pytest.mark.unit)


def pytest_sessionstart(session):
    if DATA.exists():
        _before.update(_data_entries())


def pytest_sessionfinish(session, exitstatus):
    if not DATA.exists() and not _before:
        return
    after = _data_entries()
    changed = sorted(path for path in _before.keys() | after.keys() if _before.get(path) != after.get(path))
    lines = [f"data/ changed during the run ({DATA}):"] + [f"  {path}" for path in changed] if changed else []
    lines += [f"cannot read {path}, so data/ cannot be checked" for path in sorted(set(_unreadable))]
    if not lines:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    for line in lines:
        if reporter:
            reporter.write_line(line, red=True)
        else:
            print(line, file=sys.stderr)
    session.exitstatus = pytest.ExitCode.TESTS_FAILED
