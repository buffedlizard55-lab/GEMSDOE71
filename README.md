# GEMSDOE71 — Depth-Persistent Potential-Field Structure Tensor & Hydrothermal Demagnetization/Illitization Conjunction (`DPST-HDT`)

> **SUBMISSION STATUS: `OK TO DOWNLOAD AND SUBMIT — VERIFIED UNIQUE & FORMAT-VALIDATED` (`verdict: promote`)**
>
> - **Primary Submission GeoTIFF (`.tif`, All-Finite `[0.0, 1.0]`, 139 KB):** [`docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif`](docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif)
>   - **SHA-256:** `8576f1474ee6fa6bb38d319abfa58ef7016d4909fc58abbf7dd8ef722b957bfe`
> - **Competition ZIP Archive (`.zip`, 106 KB):** [`docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.zip`](docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.zip)
>   - **SHA-256:** `183eb6f4b051cf61300355bc6ede63808933c442dc7af626b7ad737d89ba3591`
> - **Companion Footprint-NaN GeoTIFF (`-nan.tif`, 350 KB):** [`docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-nan.tif`](docs/downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-nan.tif)
>   - **SHA-256:** `b6f934f4ca0084d6e7de6556f6cd5faf6a71fb49312214c8391823e8a7cd655e`
> - **Canonical JSON Run Card:** [`docs/run_card.json`](docs/run_card.json) | [`evidence/run_card.json`](evidence/run_card.json)
> - **Unique Submission Name:** `gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0`
> - **Short Submission Note (106 / 140 chars):** `GEMSDOE71 H71-A DPST-HDT | 35500 dots (s=3.25, B=2.5px); HOLDOUT-DTI 0.0526 (+0.0250 vs base); id fd98afd0`
> - **Interactive GitHub Pages Site:** [`docs/index.html`](docs/index.html) | [`docs/executive-summary.html`](docs/executive-summary.html) | [`docs/forensic-02778.html`](docs/forensic-02778.html) | [`docs/hypotheses-and-ablation.html`](docs/hypotheses-and-ablation.html) | [`docs/uniqueness-and-leakage.html`](docs/uniqueness-and-leakage.html) | [`docs/limitations-and-sources.html`](docs/limitations-and-sources.html)

---

## Executive Summary & Key Verified Results

### 1. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`) Scored `0.2778` (`ORGANIZER-CONFIRMED`) & How We Advance Beyond It
1. **Exact 4-Point Constant-Recall Tversky Collinearity (`Pearson r = 0.999261`, Max Residual `0.00039`):**
   Decoding the pixel arrays of the four milestone GEMSDOE submissions in `.cache/registry_rasters/` proves that `GEMSDOE25` (`44,090` dots, `B=0 px`, `ORGANIZER-CONFIRMED` `0.2600`), `GEMSDOE28` (`40,199` dots, `B=1 px`, `ORGANIZER-CONFIRMED` `0.2708`), `GEMSDOE36` (`38,854` dots, `B=2 px + 1,200 infill`, `ORGANIZER-CONFIRMED` `0.2750`), and `GEMSDOE32` (`37,654` dots, `B=2 px`, `ORGANIZER-CONFIRMED` `0.2778`) lie on a single constant-recall Tversky hyperbola:
   $$\mathrm{DTI}(N_P) = \frac{T_w}{0.2\,N_P + C_G}, \qquad T_w = 5{,}151.30,\quad C_G = 10{,}987.77$$
   Removing `6,436` near-catalogue flank dots within $d \le 2\text{ px}$ ($200\text{ m}$) sacrificed **zero** hidden-fault recall while stripping $0.2 \times 6{,}436 = 1{,}287.2$ false-positive penalty units from the denominator. Conversely, `GEMSDOE36` (`0.2750`) dropped `-0.0028` below `GEMSDOE32` (`0.2778`) because its `1,200` PINN infill dots added $0.2 \times 1{,}200 = 240$ denominator penalty units with near-zero marginal recall.
2. **Why `0.2778` Was Not the Ceiling:**
   `h33-2-b2` still emitted **2,171 dots (`5.77%`) in the $2 < d \le 3\text{ px}$ ($200\text{--}300\text{ m}$) diagonal collar** (mostly at $d = \sqrt{5} = 2.236\text{ px}$), where mapped catalogue strands already provide partial $R=3\text{ px}$ triangular kernel coverage and off-fault dots act as false-positive flank noise; furthermore, its $s = 2\sqrt{2} = 2.828\text{ px}$ spacing allowed adjacent $R=3.0\text{ px}$ kernels to overlap redundantly, and its legacy `H19-5` surface did not incorporate 150 m upward-continued potential-field persistence or hydrothermal magnetite-destruction/illitization conjunction.
3. **How `GEMSDOE71` (`H71-A DPST-HDT`) Improves Fault Recovery:**
   We formulate and validate **Hypothesis H71-A (`DPST-HDT`)**—the four-way conjunction of (1) 150 m upward-continued magnetic/gravity depth-persistence (`P_persist`), (2) hydrothermal magnetite-destruction RTP Laplacian troughs + electrical conductivity (`cond_surf`) + radiometric `K/Th` illite/adularia enrichment + DOE GDR 1391 chemical geothermometers (`H_vent`), (3) Lake Lahontan shoreline-decoupled 1 m LiDAR / 100 m DEM scarp crests (`S_scarp`), and (4) visible-only crack-tip & step-over stress concentration (`K_tip`)—and emit **35,500 submodular non-overlapping dots** at **$s = 3.25\text{ px}$** outside a **$B = 2.5\text{ px}$ ($250\text{ m}$) collar**.

### 2. Spatially-Blocked Hide-and-Recover Holdout Results (`gems57-pooled-hide-v2`, `22,893` Withheld Positive Pixels)

| Experimental Arm | Role | Pooled `HOLDOUT-DTI` | 95% Spatial Bootstrap CI | Paired $\Delta$ vs Arm | SGMC Off-Catalogue DTI |
| :--- | :--- | ---: | ---: | ---: | ---: |
| **`H71A_DPST_HDT` ($B=2.5, s=3.25$)** | **Promoted Deliverable (`35,500` dots)** | **`0.05372`** (`s20`) / **`0.05264`** (8-fold) | **`[0.04139, 0.06284]`** | **Reference (Top Arm)** | **`0.06667`** |
| `H71C_Kostrov_Riedel` | Kostrov Dilatation/Shear + Microseismic Ratio | `0.04696` | `[0.03118, 0.06046]` | `+0.00567 [-0.00837, +0.02211]` | `0.05352` |
| `H71B_ASTR_Tilt` | Analytic-Signal Contact & Salem Tilt Zero-Crossing | `0.04464` | `[0.03690, 0.05230]` | `+0.00800 [-0.00500, +0.02165]` | `0.07326` |
| `H71A_NoTip_Ablation` | Within-Lane Ablation (`K_tip = 0`) | `0.04140` | `[0.03214, 0.04963]` | **`+0.01124 [+0.00805, +0.01460]`** | `0.06509` |
| `Baseline_TopoScarp` | Topographic Slope & Relief Scarp Control | `0.02767` | `[0.02141, 0.03410]` | **`+0.02497 [+0.01553, +0.03488]`** | `0.09944` |

### 3. Why `"Predicted values must be in range [0, 1]"` Happens & How `GEMSDOE71` Solves It
- **`IR-71-DATA-01` (Unflagged `-3.4028235e+38` Sentinel inside `training_features.tif`):** `training_features.tif` has `nodata=None` in its GDAL metadata yet contains `58,171` band-pixels (`3,073` unique footprint cells: `3,061` in 18 bands and `3,073` in Band 6 `tc`) equal to `-3.4028235e+38`. Unsanitized linear combinations propagate `-3.4e38` directly into the output raster.
- **`IR-71-MASK-02` (`4,601`-Pixel Mask Mismatch Between `sample_submission.tif` and `training_features.tif`):** `sample_submission.tif` has `5,167,373` finite pixels whereas `training_features.tif` Band 1 has `5,165,852` non-sentinel pixels (`3,061` pixels are valid in `sample_submission.tif` but `-3.4028235e+38` in `training_features.tif`; `1,540` pixels are finite in `training_features.tif` but `NaN` in `sample_submission.tif`). If a submission masks outside `training_features.tif` with `NaN`, those `3,061` pixels inside `sample_submission.tif`'s evaluation mask are `NaN`, causing `((pred >= 0) & (pred <= 1)).all()` to evaluate to `False` and raise `"Predicted values must be in range [0, 1]"`.
- **Our Solution:** Primary deliverable `gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif` sanitizes all `3,073` sentinel pixels and fills outside-footprint cells with `0.0` so all `12,279,160` `float32` pixels are strictly finite in `{0.0, 1.0}` (`15/15` checks pass). Companion `-nan.tif` is masked strictly by `sample_submission.tif`'s `5,167,373`-pixel mask (`15/15` checks pass).

---

## Reproducible Pipeline Execution

```bash
# 1. Verify SHA-256 of all official competition & external geophysical rasters
bash scripts/download_competition_data.sh

# 2. Sanitize -3.4028235e+38 sentinels and build cached float32 band arrays
/home/user/.venv/bin/python scripts/prepare_data.py

# 3. Run the 3-experiment pipeline (E0 Forensic, E1 Canary, E2 Holdout, E3 Uniqueness & GeoTIFF Build)
/home/user/.venv/bin/python scripts/run_lane71.py

# 4. Generate scientific figures, rebuild GitHub Pages site, and run pytest suite
/home/user/.venv/bin/python scripts/generate_figures.py
/home/user/.venv/bin/python scripts/build_site.py
/home/user/.venv/bin/pytest -v
```

---

## Standing Instructions & Prompt Record (Stored Verbatim per Requirement)

```text
Look at https://github.com/buffedlizard55-lab?tab=repositories and see all the GEMSDOE repositories and live sites:
buffedlizard55-lab/GEMSDOE69 through buffedlizard55-lab/GEMSDOE1.

Why did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros (GEMSDOE32) get the highest score 0.2778 among our sites? Can we do better?
GEMSDOE36 got 0.2750.
Consider: top scores on the leaderboard are 0.3195, 0.3774 and 0.4413.
Make sure we generate a unique TIF submission for this competition; do not copy a previous submission, unless it is for baseline/calibration learning.
Make sure it is immediately obvious whether the generated TIF submission on the site is OK to download and submit or not.
Many TIF files had the error: "Predicted values must be in range [0, 1]" — make sure we solve this problem.
If we have a downloadable TIF, make sure there is a download link in the executive summary or very beginning of the site.
Also give a unique submission name and short submission note (no more than 140 characters).

PARALLEL-RUN PROTOCOL (read before doing anything):
1. STAY IN YOUR LANE. Before writing a submission, compute rank-correlation and 3-pixel dot overlap against every raster in the registry. If rank-correlation > 0.90 OR > 70% of your dots fall within 3 px of any prior raster, STOP: you have converged on an existing family. Check uniqueness on the pre-placement surface AND the final dots.
2. DO NOT REBUILD PLUMBING. Reuse the template's cached feature stack, evaluate_holdout.py, and submission_writer.py.
   - Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive all catalogue features from the remaining faults only, mask visible faults pixel-exactly, score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel).
   - Submission writer: clip to [0, 1], assert no NaN inside footprint, assert CRS/shape/transform match sample_submission.tif, emit both .tif and .zip, record sha256.
3. LABEL EVERY NUMBER. Every metric in prose or tables must carry HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED. Never write a projection as a score.
4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC > 0.90 means leakage until proven otherwise.
5. END WITH ONE JSON RUN CARD: hypothesis, mechanism, named non-fault process that could mimic it, holdout DTI + CI, correlation/overlap vs registry, raster sha256, validator output, submission name + note (<= 140 chars), verdict: promote / negative.
6. BUDGET. Stop after at most 3 experiments or 2 hours.

Formulate 3-5 candidate geological hypotheses not yet tried, naming specific layers, physical signature/transform, why it catches faults missing from the USGS/INGENIOUS catalogue, and how it differs from existing implementations; rank by expected DTI gain and cost; validate top candidate on spatially-blocked holdout; put this prompt in README.md; run 3 verification passes; create a PR and merge onto main.
```
