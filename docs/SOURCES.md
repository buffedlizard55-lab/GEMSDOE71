# Sources — verified, partially verified, or blocked

Every claim in this repo should trace to a row here. **Status is what this sandbox could actually
check** (date: 2026-10-20 UTC). The sandbox egress allowlist is `github.com`, `api.github.com`,
`codeload.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. Everything else
returned HTTP `000` (blocked). Raw check results: [`data/link_check.csv`](data/link_check.csv).

Legend: **VERIFIED** = read or executed here · **BLOCKED** = not reachable from here, needs manual
review from an unrestricted machine · **USER-PROVIDED** = taken from the project brief, not checked.

## A. Competition and official documents

| # | Source | URL | Status here | What was checked / what is needed |
|---|---|---|---|---|
| A1 | DrivenData competition page | https://www.drivendata.org/competitions/306/competition-doe-gems/ | BLOCKED (000) | Rules and the data page. Brief says data requires login. |
| A2 | Problem description (page 967) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | BLOCKED (000) | Needed to confirm the metric text. |
| A3 | About page (page 968) | https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ | BLOCKED (000) | — |
| A4 | Data download tab | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ | BLOCKED (000) | Login-gated per brief. Files: `labels.tif`, `training_features.tif`, `sample_submission.tif`, `1m_DEM_links.csv`. |
| A5 | Leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | BLOCKED (000) | Needed to resolve the conflicting "current high score" values (see FLAGS F6). |
| A6 | GEMS scoring/problem PDF (GEMS_96647) | https://docs.nlr.gov/docs/fy26osti/96647.pdf | BLOCKED (000) | **Authoritative metric text.** Our Tversky/tolerance definition is ASSUMED until this is read. Also mirrored (USER-PROVIDED) at the Dropbox link in A9. |
| A7 | USGS GeoDAWN airborne magnetic/radiometric data | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | BLOCKED (000) | Origin of magnetic/radiometric bands. Needed to confirm band provenance. |
| A8 | INGENIOUS project (GBCGE) | https://gbcge.org/current-projects/ingenious/ | BLOCKED (000) | Fault catalogue provenance. |
| A9 | Dropbox mirrors from the brief (5 files) | see `scripts/download_competition_data.sh` | BLOCKED (000) | `example_submission.tif`, `existing_faults.tif`, `gems-geodawn-numerical-features.tif`, `GEMS_96647.pdf`, `Digital-elevation-model-links-JSON.pdf`. Downloaded only on an unrestricted machine. |
| A10 | EPSG:32611 definition | https://epsg.io/32611 | BLOCKED (000) | **Checked instead against PROJ's bundled database via pyproj 3.7.2 (PROJ 9.5.1): `WGS 84 / UTM zone 11N`.** VERIFIED offline. |
| A11 | Tversky index (background) | https://en.wikipedia.org/wiki/Tversky_index | BLOCKED (000) | Formula verified from the PyPI source of `segmentation-models-pytorch` 0.3.4 instead (see B3). |
| A12 | GEMS data submission on OpenEI GDR (per brief); USGS ComCat seismicity API | https://gdr.openei.org/submissions/1391 ; https://earthquake.usgs.gov/fdsnws/event/1/version | BLOCKED (000) | Needed for any seismicity-derived hypothesis. **Not yet obtainable from this sandbox — must be checked from an unrestricted machine before H4 is viable.** |
| A13 | NBMG Nevada geology | https://www.nbmg.unr.edu/ | BLOCKED (000) | Not used yet. Candidate regional geology/fault source; needs manual check. |

## B. Verified here (reachable through GitHub or PyPI)

| # | Source | URL | Status | What was checked |
|---|---|---|---|---|
| B1 | GEMS reference solution (DrivenData) | https://github.com/drivendataorg/gems-prize-reference-solution | VERIFIED | Cloned at commit `aebe92f` ("initial commit"). Read `unet-mc-cv-reference-solution.ipynb` (all 21 cells, outputs) and `pyproject.toml`. Source of: grid 3730×3292, 100 m, EPSG:32611, 19 bands, label rule `>=1`, Tversky(alpha=0.2, beta=0.8). Irregularities listed in FLAGS. |
| B2 | GEM Global Active Faults DB | https://github.com/GEMScienceTools/gem-global-active-faults | VERIFIED | Cloned at commit `56816508` (2021-06-24). License **CC-BY-SA-4.0** (GitHub API). 13,696 LineString features in `gem_active_faults_harmonized.geojson`. US entries are labelled `USGS Hazfaults 2014` (129 in the Nevada box) or `UCERF3` (70). **Not an independent catalogue for US faults.** Citation in its README: Styron & Pagani (2020), *Earthquake Spectra* 36(1_suppl), doi:10.1177/8755293020944182. |
| B3 | segmentation-models-pytorch 0.3.4 (PyPI) | https://pypi.org/project/segmentation-models-pytorch/ | VERIFIED | `losses/_functional.py::soft_tversky_score`: `TP/(TP + alpha*FP + beta*FN)` with `FP = sum(p*(1-t))`, `FN = sum((1-p)*t)`. Same as our `gems/metric.py` at zero tolerance (unit-tested). |
| B4 | pyproj 3.7.2 / PROJ 9.5.1 | https://pypi.org/project/pyproj/ | VERIFIED | `CRS.from_epsg(32611).name == "WGS 84 / UTM zone 11N"`. |
| B5 | rasterio 1.4.4, scikit-learn, scipy, pytest | PyPI | VERIFIED (installed) | Used by the pipeline and tests. |
| B6 | Brief's GEMSDOE site list (github.io) | https://buffedlizard55-lab.github.io/… | BLOCKED | Every GEMSDOE site returned 000. **We could not read the GEMSDOE32 page, so its method is unverified** (see RESEARCH §1). |

## C. Data gaps that block validation

1. Labels and features (DrivenData login) → nothing can be scored on real data yet.
2. Competition metric text (GEMS_96647.pdf) → the tolerance-Tversky definition is assumed.
3. Submission grid (`sample_submission.tif` / `example_submission.tif`) → needed for the exact geotransform.
4. Seismicity catalogue (USGS ComCat) → needed for H4; obtainability unverified from here.
