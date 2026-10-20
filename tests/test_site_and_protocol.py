"""Pass 2 & Pass 3 verification tests: HTML link integrity, download accessibility,
Parallel-Run Protocol compliance, and README prompt storage.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_all_html_pages_and_local_links_resolve():
    expected_pages = [
        "index.html",
        "executive-summary.html",
        "forensic-02778.html",
        "hypotheses-and-ablation.html",
        "uniqueness-and-leakage.html",
        "limitations-and-sources.html",
    ]
    for page in expected_pages:
        p = DOCS / page
        assert p.exists(), f"Missing HTML page: {p}"
        text = p.read_text()
        assert len(text) > 2000

        # Check all href and src attributes
        targets = re.findall(r'(?:href|src)="([^"]+)"', text)
        assert len(targets) > 5
        for t in targets:
            if t.startswith(("http://", "https://", "#")):
                continue
            clean = t.split("#")[0]
            target_path = DOCS / clean
            assert target_path.exists(), f"Broken link in {page}: {t} -> {target_path}"
            assert target_path.stat().st_size > 0, f"Empty linked asset: {target_path}"


def test_top_of_site_download_and_status_prominence():
    card = json.loads((ROOT / "evidence" / "run_card.json").read_text())
    tif_name = card["raster"]["primary_zeros_tif"].split("/")[-1]
    zip_name = card["raster"]["zip_archive"].split("/")[-1]
    sub_name = card["submission"]["name"]
    sub_note = card["submission"]["note"]
    assert len(sub_note) <= 140

    for page in ("index.html", "executive-summary.html"):
        text = (DOCS / page).read_text()
        # Must appear in the first 3500 characters (very beginning of the site)
        head_chunk = text[:4500]
        assert "OK TO DOWNLOAD AND SUBMIT" in head_chunk
        assert f"downloads/{tif_name}" in head_chunk
        assert f"downloads/{zip_name}" in head_chunk
        assert sub_name in head_chunk
        assert sub_note in head_chunk


def test_readme_contains_standing_prompt_and_deliverable_links():
    readme = (ROOT / "README.md").read_text()
    assert "OK TO DOWNLOAD AND SUBMIT" in readme
    assert "PARALLEL-RUN PROTOCOL" in readme
    assert "Predicted values must be in range [0, 1]" in readme
    assert "gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif" in readme
    assert "HOLDOUT-DTI" in readme
    assert "ORGANIZER-CONFIRMED" in readme


def test_run_card_completeness():
    card = json.loads((DOCS / "run_card.json").read_text())
    required_keys = [
        "hypothesis",
        "mechanism",
        "named_non_fault_process_that_could_mimic_it",
        "holdout_dti",
        "leakage_canary",
        "correlation_and_overlap_vs_registry",
        "raster",
        "validator_output",
        "submission",
        "experiments_used",
        "verdict",
    ]
    for k in required_keys:
        assert k in card, f"Missing key in run_card.json: {k}"
    assert card["verdict"] == "promote"
    assert card["experiments_used"] == 3
    assert card["validator_output"]["all_checks_passed"] is True
    assert card["validator_output"]["upstream_nan_validator_passed"] is True
    assert card["validator_output"]["values_in_0_1"] is True
    assert card["validator_output"]["no_nan_inside_footprint"] is True
    assert card["validator_output"]["crs_shape_transform_match"] is True
