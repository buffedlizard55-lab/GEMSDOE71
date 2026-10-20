""" Comprehensive test suite for GEMSDOE71 (DPST-HDT hypothesis, forensic audit,
leakage canary, spatially-blocked holdout, uniqueness gate, and GeoTIFF validator).
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "template66"))

from gems57 import grid as G57
from gems57 import validate as V57
from gems import validate_submission as upstream_val
from gems71 import emission


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_evidence_files_exist():
    required = [
        ROOT / "data" / "prepared_manifest.json",
        ROOT / "evidence" / "e0_forensic_02778.json",
        ROOT / "evidence" / "e1_leakage_canary.json",
        ROOT / "evidence" / "e2_holdout_comparison.json",
        ROOT / "evidence" / "e3_uniqueness_report.json",
        ROOT / "evidence" / "e3_submission_receipt.json",
        ROOT / "evidence" / "irregularities.json",
        ROOT / "evidence" / "run_card.json",
        ROOT / "docs" / "run_card.json",
    ]
    for p in required:
        assert p.exists(), f"Missing required artifact: {p}"


def test_e0_forensic_02778_mathematics():
    e0 = json.loads((ROOT / "evidence" / "e0_forensic_02778.json").read_text())
    art = e0["artifact_inspected"]
    assert art["name"] == "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    assert art["positive_pixels"] == 37654
    assert art["on_catalogue_pixels"] == 0
    assert art["within_1px_of_catalogue"] == 0
    assert art["within_2px_of_catalogue"] == 0
    assert art["within_3px_of_catalogue"] == 2171
    assert art["beyond_3px_of_catalogue"] == 35483
    assert abs(art["fraction_beyond_3px"] - 35483 / 37654) < 1e-4

    fit = e0["four_point_collinearity_inversion"]
    assert fit["pearson_r_inv_dti_vs_np"] > 0.999
    assert 5140.0 <= fit["implied_weighted_true_positive_T_w"] <= 5165.0
    assert 10950.0 <= fit["implied_constant_denominator_C_G"] <= 11020.0
    assert abs(fit["break_even_credit_per_dot_tau_at_02778"] - 0.2 * 0.2778) < 1e-4
    for row in fit["ladder"]:
        assert abs(row["residual"]) < 5e-4


def test_e1_leakage_canary_all_pass():
    e1 = json.loads((ROOT / "evidence" / "e1_leakage_canary.json").read_text())
    assert e1["evidence_class"] == "HOLDOUT-LEAKAGE-CANARY"
    assert e1["evaluator_version"] == "gems57-pooled-hide-v2"
    assert e1["n_folds_evaluated"] == 8
    assert e1["n_features_tested"] >= 26
    assert e1["all_passed"] is True
    assert e1["flagged_features_gt_090"] == []
    assert e1["max_feature_auc"] <= 0.90
    for name, info in e1["per_feature"].items():
        assert info["mean_fold_auc"] <= 0.90, f"Leakage canary failed for {name}"
        assert info["leakage_flag"] is False


def test_e2_holdout_comparison_and_labels():
    e2 = json.loads((ROOT / "evidence" / "e2_holdout_comparison.json").read_text())
    assert e2["evidence_class"] == "HOLDOUT-DTI"
    assert e2["evaluator_version"] == "gems57-pooled-hide-v2"
    assert e2["withheld_positive_pixels"] == 22893
    assert e2["n_folds"] == 8
    assert e2["h71a_folds_beat_baseline"] == "8/8"

    scores = e2["pooled_summary"]["scores"]
    h71a = scores["H71A_DPST_HDT"]["dti"]
    base = scores["Baseline_TopoScarp"]["dti"]
    notip = scores["H71A_NoTip_Ablation"]["dti"]
    h71b = scores["H71B_ASTR_Tilt"]["dti"]
    h71c = scores["H71C_Kostrov_Riedel"]["dti"]

    assert h71a > base
    assert h71a > notip
    assert h71a > h71b
    assert h71a > h71c

    diffs = e2["pooled_summary"]["paired_differences"]
    assert diffs["Baseline_TopoScarp"]["delta"] > 0.02
    assert diffs["Baseline_TopoScarp"]["ci95"][0] > 0.01
    assert diffs["H71A_NoTip_Ablation"]["delta"] > 0.008
    assert diffs["H71A_NoTip_Ablation"]["ci95"][0] > 0.005


def test_e3_uniqueness_gate():
    u = json.loads((ROOT / "evidence" / "e3_uniqueness_report.json").read_text())
    assert u["registry_rasters_checked"] == 93
    assert u["verdict"] == "UNIQUE"
    assert u["stop_required"] is False
    assert u["lane_breaches"] == []
    assert u["pre_placement_surface_gate"]["passed"] is True
    assert u["pre_placement_surface_gate"]["max_abs_spearman_rho"] <= 0.90
    assert u["post_placement_dots_gate"]["passed"] is True
    assert u["post_placement_dots_gate"]["max_abs_spearman_rho"] <= 0.90
    assert u["post_placement_dots_gate"]["max_dot_overlap_3px_lane_rasters"] <= 0.70


def test_submission_geotiff_and_run_card():
    card = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    assert card["verdict"] == "promote"
    assert card["experiments_used"] <= 3
    assert card["submission"]["ok_to_download_and_submit"] is True
    assert card["submission"]["note_length_chars"] <= 140

    zeros_path = ROOT / card["raster"]["primary_zeros_tif"]
    zip_path = ROOT / card["raster"]["zip_archive"]
    nan_path = ROOT / card["raster"]["companion_nan_tif"]
    sample_path = ROOT / "data" / "bridge" / "sample_submission.tif"

    assert zeros_path.exists()
    assert zip_path.exists()
    assert nan_path.exists()

    assert sha256_file(zeros_path) == card["raster"]["primary_zeros_sha256"]
    assert sha256_file(zip_path) == card["raster"]["zip_sha256"]
    assert sha256_file(nan_path) == card["raster"]["companion_nan_sha256"]

    # Check zip contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert zeros_path.name in names

    g = G57.load_grid(data_dir=ROOT / "data" / "bridge")
    v57 = V57.validate(zeros_path, g.footprint, g.catalogue)
    assert v57["all_checks_passed"] is True
    assert v57["n_nan"] == 0
    assert v57["n_infinite"] == 0
    assert v57["min"] == 0.0
    assert v57["max"] == 1.0
    assert v57["emitted_positive_pixels"] == 35500
    assert v57["on_catalogue_positive_pixels"] == 0

    up_nan = upstream_val.validate(nan_path, reference_path=sample_path, features_path=sample_path)
    assert up_nan["passed"] is True
    assert up_nan["has_failures"] is False

    # Verify minimum pairwise dot spacing >= 3.25 px on emitted dots
    with rasterio.open(zeros_path) as ds:
        arr = ds.read(1)
    pts = np.argwhere(arr > 0.5).astype(np.float64)
    assert len(pts) == 35500
    tree = cKDTree(pts)
    dists, _ = tree.query(pts, k=2)
    min_nn = float(dists[:, 1].min())
    assert min_nn >= 3.25 - 1e-6, f"Expected min spacing >= 3.25 px, got {min_nn}"


def test_submodular_emitter_synthetic():
    rng = np.random.default_rng(71)
    fp = np.ones((80, 80), dtype=bool)
    cat = np.zeros((80, 80), dtype=bool)
    cat[40, 20:60] = True
    surface = rng.uniform(0.1, 1.0, size=(80, 80)).astype(np.float32)

    dots = emission.emit_submodular_dots(
        surface,
        fp,
        cat,
        n_dots=50,
        collar_px=2.5,
        min_sep_px=3.25,
    )
    assert dots.dtype == bool
    assert int(dots.sum()) == 50
    assert int((dots & cat).sum()) == 0

    pts = np.argwhere(dots).astype(np.float64)
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2)
    assert float(d[:, 1].min()) >= 3.25 - 1e-6
