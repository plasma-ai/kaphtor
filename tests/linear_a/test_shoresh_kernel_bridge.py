"""Unit tests for Shoresh Amendment A25 (tools/core/shoresh_kernel_bridge.py)."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.core import shoresh_kernel_bridge as skb


def test_extracts_kober_trios_and_pairs():
    words = [
        "SA-RU", "SA-RO", "SA-RA2",
        "PA3-NI", "PA3-NI-NA", "PA3-NI-WI",
        "PI-TO",
    ]
    clusters = skb.extract_kober_clusters(words)
    assert len(clusters) == 2
    assert set(clusters[0]) == {"PA3-NI", "PA3-NI-NA", "PA3-NI-WI"}
    assert set(clusters[1]) == {"SA-RA2", "SA-RO", "SA-RU"}


def test_annotates_anchors_liturgy_and_clusters():
    a_kuro = skb.annotate_word("KU-RO")
    assert "KERNEL_D_ANCHORED" in a_kuro["flags"]
    assert a_kuro["anchor"]["concept"] == "TOTAL"

    a_sirute = skb.annotate_word("SI-RU-TE", corpus_words=["SI-RU", "SI-RU-TE", "SI-RU-TI"])
    assert "KERNEL_C_LITURGICAL" in a_sirute["flags"]
    assert "KOBER_TRIO" in a_sirute["flags"]
    assert a_sirute["liturgical"]["io_za_2_slot"] == 6


def test_enrich_result_preserves_existing_keys():
    base = {"word": "KU-RO", "verdict": "UNINFORMATIVE", "d_star": 0.0}
    enriched = skb.enrich_result(base)
    assert enriched["verdict"] == "UNINFORMATIVE"
    assert enriched["kernel_bridge"]["anchor"]["concept"] == "TOTAL"
    assert math.isclose(skb.couple_cluster_z([2.0, 2.0, 2.0]), 2.0 * math.sqrt(3.0), rel_tol=1e-4)


def test_isolated_stdlib_import():
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); import tools.core.shoresh_kernel_bridge as m; assert 'KU-RO' in m.ANCHOR_SLOTS"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
