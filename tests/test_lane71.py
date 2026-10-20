"""Automated verification test suite for GEMSDOE71 Lane H71."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from gems import validate_submission as V_GEMS  # noqa: E402
from gems57 import validate as V57  # noqa: E402
from gems71 import SUBMISSION_ID, SUBMISSION_NOTE  # noqa: E402


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_submission_files_and_validators() -> None:
    sub_dir = REPO_ROOT / "submissions"
    docs_sub_dir = REPO_ROOT / "docs" / "submissions"
    template_path = REPO_ROOT / "data" / "bridge" / "sample_submission.tif"
    cat_path = REPO_ROOT / "data" / "bridge" / "existing_faults.tif"

    zeros_tif = sub_dir / f"{SUBMISSION_ID}-zeros.tif"
    nan_tif = sub_dir / f"{SUBMISSION_ID}-nan.tif"
    zip_file = sub_dir / f"{SUBMISSION_ID}-zeros.tif.zip"
    surf_tif = sub_dir / f"{SUBMISSION_ID}-surface-zeros.tif"

    assert zeros_tif.is_file()
    assert nan_tif.is_file()
    assert zip_file.is_file()
    assert surf_tif.is_file()

    # Check docs/submissions mirrors match byte-for-byte
    assert _sha256(zeros_tif) == _sha256(docs_sub_dir / zeros_tif.name)
    assert _sha256(nan_tif) == _sha256(docs_sub_dir / nan_tif.name)
    assert _sha256(zip_file) == _sha256(docs_sub_dir / zip_file.name)

    with rasterio.open(template_path) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(cat_path) as ds:
        cat = (ds.read(1) > 0) & fp

    # Check primary -zeros.tif has zero NaNs anywhere and lies strictly in [0, 1]
    with rasterio.open(zeros_tif) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
        assert np.isfinite(arr).all(), "Primary -zeros.tif must have zero NaN/Inf cells anywhere"
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert int((arr > 0).sum()) == 38800
        assert int((arr[cat] > 0).sum()) == 0

    v_gems = V_GEMS.validate(
        zeros_tif,
        reference_path=template_path,
        features_path=template_path,
        outside_policy="either",
    )
    assert v_gems["passed"] is True
    assert v_gems["has_failures"] is False

    v57 = V57.validate(zeros_tif, footprint=fp, catalogue=cat)
    assert v57["all_checks_passed"] is True


def test_leakage_canary_and_holdout_evidence() -> None:
    e1 = json.loads((REPO_ROOT / "evidence" / "e1_feature_leakage_canary.json").read_text())
    canary = e1["leakage_canary"]
    assert canary["all_features_pass"] is True
    assert canary["n_features_tested"] == 27
    assert canary["max_physical_holdout_auc_directional"] <= 0.90
    assert canary["max_overall_holdout_auc_directional"] <= 0.90
    for f in canary["features"]:
        assert f["holdout_auc_directional"] <= 0.90
        assert f["sgmc_off_catalogue_auc_directional"] <= 0.90
        assert f["canary_pass"] is True

    e2 = json.loads((REPO_ROOT / "evidence" / "e2_holdout_ablation_and_sgmc.json").read_text())
    assert e2["evidence_class"] == "HOLDOUT-DTI"
    assert e2["evaluator_version"] == "gems57-pooled-hide-v3-se"
    assert e2["withheld_positive_pixels_full_domain"] == 11321

    full_scores = e2["full_domain_pooled_summary"]["scores"]
    full_diffs = e2["full_domain_pooled_summary"]["paired_differences"]
    assert full_scores["h71a_full_conduit_synthesis"]["dti"] > 0.070
    assert len(full_diffs) == 7
    for arm, diff in full_diffs.items():
        assert diff["delta"] > 0.0, f"H71-A must beat {arm}"
        assert diff["beats_two_se"] is True, f"H71-A must beat {arm} by > 2 SE"

    sgmc = e2["usgs_sgmc_off_catalogue_benchmark"]
    assert (
        sgmc["h71a_full_conduit_synthesis"]["dti_at_k38800"]
        > sgmc["h33_2_b2_champion"]["dti_at_k38800"]
    )


def test_uniqueness_and_run_card() -> None:
    e3 = json.loads((REPO_ROOT / "evidence" / "e3_uniqueness_and_validation.json").read_text())
    u = e3["uniqueness_audit"]
    assert u["n_registry_rasters_checked"] == 108
    assert u["max_abs_spearman_pre_placement_surface"] <= 0.90
    assert u["max_abs_spearman_final_dots"] <= 0.90
    assert u["max_3px_overlap_symmetric_discrete_detectors"] <= 0.70
    assert u["max_3px_overlap_directed_discrete_detectors"] <= 0.70
    assert u["max_3px_overlap_symmetric_all_including_lattices"] <= 0.70
    assert u["uniqueness_gate_passed"] is True

    card = json.loads((REPO_ROOT / "evidence" / "run_card.json").read_text())
    assert card["verdict"] == "promote"
    assert card["ok_to_download_and_submit"] is True
    assert len(card["submission_note"]) <= 140
    assert card["submission_note"] == SUBMISSION_NOTE
    assert card["validator_output"]["no_nan_in_footprint"] is True
    assert card["validator_output"]["values_in_0_1"] is True
    assert card["validator_output"]["crs_matches_epsg32611"] is True
    assert card["validator_output"]["shape_matches_3292x3730"] is True
    assert card["validator_output"]["transform_matches_template"] is True


def test_readme_and_github_pages_site() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    assert "PARALLEL-RUN PROTOCOL (read before writing any code):" in readme
    assert "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros" in readme
    assert f"{SUBMISSION_ID}-zeros.tif" in readme

    for page in ("docs/index.html", "docs/executive-summary.html", "index.html", "executive-summary.html"):
        html = (REPO_ROOT / page).read_text()
        assert f"submissions/{SUBMISSION_ID}-zeros.tif" in html
        assert SUBMISSION_NOTE in html
        assert "PROMOTE" in html
