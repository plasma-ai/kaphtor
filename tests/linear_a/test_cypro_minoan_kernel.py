"""CI guard tests for models/cypro-minoan-kernel/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
KERNEL_DIR = REPO / "models" / "cypro-minoan-kernel"
LEDGER_PATH = KERNEL_DIR / "runs" / "cm-kernel-2026-11-25.json"

if str(KERNEL_DIR) not in sys.path:
    sys.path.insert(0, str(KERNEL_DIR))

import cm_kernel


@pytest.mark.data
def test_cypro_minoan_kernel_ledger_matches_shipped_inputs() -> None:
    """Pinned run ledger must match SHA-256 hashes of all shipped kaphtor input files."""
    assert LEDGER_PATH.exists(), f"Missing pinned run ledger: {LEDGER_PATH}"
    assert cm_kernel.main(["check", "--ledger", str(LEDGER_PATH)]) == 0


@pytest.mark.data
def test_cypro_minoan_kernel_t3_firewall_and_counts() -> None:
    """Kernel manifest must never touch Linear A data and must match audited Amathus IG XV 1 counts."""
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert ledger["manifest"]["t5_compliant"] is True
    for info in ledger["manifest"]["inputs"].values():
        assert "linear-a" not in info["path"]
    assert ledger["corpora_counts"]["ec_amathus_confirmed_types"] == 92
    assert ledger["corpora_counts"]["ec_amathus_undotted_types"] == 66
    # Orthographic glide laws must hold strongly in shipped data (positive exact p-values)
    pan = ledger["kernel_cm_o_glides"]["pan_cm"]
    assert 0.0 < pan["ci_jv_enrichment_p_vs_non_i"] < 1e-6
    assert 0.0 < pan["cu_wv_enrichment_p_vs_non_u"] < 1e-4
    # Suffix containment must significantly beat position-preserving syllable-shuffled null
    assert ledger["kernel_cm_b_stems"]["p_suffix"] <= 0.01
    # Verify deterministic alphabetical tie-breaking in top_productive_suffixes
    items = list(ledger["kernel_cm_b_stems"]["top_productive_suffixes"].items())
    assert items == sorted(items, key=lambda kv: (-kv[1], kv[0]))
