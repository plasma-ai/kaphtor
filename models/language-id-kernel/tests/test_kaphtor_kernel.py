"""Unit tests for kaphtor_kernel.py (manifest, theta_95, Stouffer Z, and SIGNATURE.txt safety gate)."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import kaphtor_kernel as kk


def test_percentile_and_stouffer():
    assert math.isclose(kk.percentile([0.1, 0.2, 0.3, 0.4, 0.5], 0.95), 0.48)
    assert math.isclose(kk.stouffer_z([3.0, 3.0, 3.0]), 3.0 * math.sqrt(3.0))


def test_manifest_covers_core_files():
    m = kk.build_manifest()
    assert any(k.endswith("kaphtor_kernel.py") for k in m)
    assert any(k.endswith("kober_b.py") for k in m)
    assert any(k.endswith("anchors_d.py") for k in m)
    assert all(len(v) == 64 for v in m.values())


def test_run_refuses_without_signature(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(kk, "SIGNATURE", tmp_path / "NO_SIGNATURE.txt")
    rc = kk.cmd_run(n_perm_d=10, n_perm_ab=2, n_perm_c=2, draws=1)
    assert rc == 2


def test_cli_manifest_and_calibrate_smoke():
    proc = subprocess.run(
        [sys.executable, str(kk.HERE / "kaphtor_kernel.py"), "calibrate", "--n-perm", "1000"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PASS=True" in proc.stdout
