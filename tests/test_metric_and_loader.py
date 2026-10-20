"""Local checks that do not need the competition mirrors, plus one mirror check if present."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import metric
from gems71.conduits import FORBIDDEN_COLUMNS, bresenham, utm_to_rowcol


def test_kernel_endpoints():
    assert metric.kernel(0) == 1
    assert metric.kernel(3) == 0
    assert abs(float(metric.kernel(1.5)) - 0.5) < 1e-12


def test_dti_matches_bruteforce():
    rng = np.random.default_rng(7)
    pred = np.zeros((12, 12))
    truth = np.zeros((12, 12), bool)
    pred[rng.integers(0, 12, 8), rng.integers(0, 12, 8)] = rng.random(8)
    truth[rng.integers(0, 12, 5), rng.integers(0, 12, 5)] = True
    a = metric.dti_exact(pred, truth)
    b = metric.dti_bruteforce(pred, truth)
    assert abs(a["dti"] - b["dti"]) < 1e-9
    assert abs(a["tp"] - b["tp"]) < 1e-9
    assert abs(a["fp"] - b["fp"]) < 1e-9


def test_published_identity_weights():
    # Problem page worked example: TPw=3.00, FPw=1.89, FNw=2.00, displayed as 0.60.
    # The displayed value is rounded. Exact arithmetic is 3 / (3 + 0.2*1.89 + 0.8*2).
    dti = metric.dti_from_components(3.0, 1.89, 2.0)
    exact = 3.0 / (3.0 + 0.2 * 1.89 + 0.8 * 2.0)
    assert abs(dti - exact) < 1e-12
    assert abs(dti - 0.60) < 0.005


def test_transform_roundtrip():
    row, col = utm_to_rowcol([243350.0 + 250.0], [4508550.0 - 350.0])
    assert abs(col[0] - 2.5) < 1e-9
    assert abs(row[0] - 3.5) < 1e-9


def test_bresenham_endpoints():
    pts = bresenham(0, 0, 0, 4)
    assert pts[0] == (0, 0) and pts[-1] == (0, 4)
    assert len(pts) == 5


def test_forbidden_columns_constant():
    assert "dist_known_fault_px" in FORBIDDEN_COLUMNS


def test_champion_distance_is_not_double_complemented():
    # IR-71-DIST-01: ndi_distance(~cat) measured the complement and wrote 0 m.
    source = (ROOT / "scripts" / "run_h71.py").read_text()
    assert "ndi_distance(~cat)" not in source
    assert "ndi_distance(cat)" in source


def test_note_fits_the_portal_limit():
    import json
    reg = json.loads((ROOT / "registry" / "preregistration-h71.json").read_text())
    assert len(reg["submission_note"]) <= 140
