# Irregularities flagged for manual review

Each flag states what was seen, where, and why it matters. Nothing here is fixed silently.
"Verified" means read directly from the source named; "Unverified" means it could not be checked here.

## F1 — Reference notebook: label band printed with a stale loop variable (VERIFIED)
- **Where:** `unet-mc-cv-reference-solution.ipynb`, cell 6. Code prints `f"Band {i}: ..."` where `i` is left over from cell 5's loop; cell 6 actually reads `src.tags(1)`.
- **Seen:** the cell 6 output says `Band 19: Fault locations ...`.
- **Why it matters:** the label raster is a single band. The "Band 19" text is a bug, not a fact about the file. Do not treat it as evidence about band layout.

## F2 — Reference notebook: "elevation (channel 4)" is not elevation (VERIFIED)
- **Where:** cell 12 (`make_patches`): `np.isnan(X_patches[ii, jj, 0, :, :, 4])` with the comment "containing elevation (channel 4)".
- **Seen:** channel index 4 (0-based) is **Band 5**, "Isostatic gravity anomaly slope". Elevation bands are **Band 12** (Detrended elevation, index 11) and **Band 19** (Detrended elevation slope, index 18).
- **Why it matters:** the patch-validity filter uses the wrong channel. Patches are kept or dropped based on gravity NaNs, not elevation NaNs.

## F3 — Reference notebook: filename mismatch with the brief's Dropbox file (VERIFIED against the brief text)
- **Where:** cell 2 expects `data/numeric_features.tif` and `data/labels.tif`. The brief's Dropbox file is `gems-geodawn-numerical-features.tif`; the brief lists `existing_faults.tif`, not `labels.tif`.
- **Why it matters:** we cannot tell from names whether `existing_faults.tif` is the same raster as DrivenData's `labels.tif`. `scripts/prepare_data.py` accepts either name and writes a note. **Confirm by checking the raster values and CRS before trusting any result.**

## F4 — Reference notebook: checkpoint selected on the TEST split (VERIFIED)
- **Where:** cell 16. `best_model` is chosen by lowest `test_losses`, and those test losses come from the same test patches that are then predicted and written out.
- **Why it matters:** this is selection on the evaluation data, so any score from that protocol is optimistic. `gems/pipeline.py::run_holdout` does no checkpoint selection: the baseline is a gradient-boosting model with fixed hyperparameters and `early_stopping=False`, so nothing is chosen on the scored domain. Keep this distinction in every write-up.

## F5 — Reference notebook: averaging denominator does not match the number of predictions (VERIFIED)
- **Where:** cell 16. `y_out[...] += test_preds[ii] / MC` runs only for iterations in which a patch was in the test set (about half of them, since `test_proportion=0.5`). Dividing by `MC=5` regardless means each pixel is scaled by roughly `k/5`, where `k` is its number of test appearances.
- **Why it matters:** output values are biased toward 0 and differ between pixels. This does not change rankings within one pixel, but it does change thresholds and any cross-region comparison.

## F6 — Brief: conflicting "current high score" values (VERIFIED as internal inconsistency)
- **Seen in the brief:** 0.4413, 0.3774, and 0.3195 are each described as the current GEMSDOE high score. The highest per-site score actually listed is **0.2778** (GEMSDOE32). See `docs/data/user_reported_scores.csv`.
- **Why it matters:** we cannot tell which number is the organizer-confirmed leaderboard value. The leaderboard page (A5) is blocked from this sandbox.

## F7 — Brief: "Predicted values must be in range [0, 1]" failures (USER-PROVIDED, cause UNVERIFIED)
- **Seen:** the user's upload failed with this message.
- **Likely causes (to check against the actual file):** NaN or nodata values inside the footprint; raw logits or unnormalized scores above 1; a non-zero nodata tag such as `-3.4e38` or `-1`.
- **What we do:** `gems/submission.py` refuses to write any file with NaN/inf or values outside [0, 1], and `scripts/validate_submission.py` checks a file before upload.

## F8 — Brief: site-level entries with missing names or scores (VERIFIED against the brief text)
- GEMSDOE67 has a name with no score. GEMSDOE68, 69, 70, 71 and 72 have a URL with no name and no score. Recorded as `INCOMPLETE` in the CSV.
- GEMSDOE32's score is listed twice in the brief (same value). Deduplicated in the CSV.

## F9 — Metric definition is ASSUMED (UNVERIFIED)
- **Where:** `gems/metric.py`. The brief gives alpha=0.2, beta=0.8 and a 300 m triangular kernel but not the exact pixel-level formula. Our soft-counting definition is documented in the file and in RESEARCH §4. **Must be checked against GEMS_96647.pdf (blocked from here).**
- **Why it matters:** under this definition a trivial all-ones map can reach about 0.24 on a sparse synthetic network (RESEARCH §1.3). If the official scorer differs, the baseline numbers differ too.

## F10 — Catalogue independence (VERIFIED for GEM DB; UNVERIFIED for competition catalogue)
- **Seen:** every US trace in the GEM GAF-DB inside the Nevada box comes from `USGS Hazfaults 2014` or `UCERF3` (see SOURCES B2).
- **Why it matters:** a "missing faults" hypothesis checked against GEM GAF-DB is checked against the same USGS lineage, so it does not test independence. Overlap with the competition's catalogue is unknown until the data is placed.

## F11 — Pipeline issues found and fixed in this session (VERIFIED)
1. First synthetic run gave pooled DTI **0.000** because the catalogue-distance feature copied the label for training pixels (distance 0 on their own fault). Fixed with out-of-fold distance maps; regression test `test_training_pixels_never_copy_their_own_label`.
2. Full-size run (3730×3292, 19 bands) was killed for memory (exit −9). Fixed with chunked prediction, in-place normalization and freeing per-fold matrices. Measured peak RSS after the fix: about 3.7 GB on synthetic data (`docs/run_cards`).
3. Canary reported raw feature names rather than the names used in the model. Fixed.

## F12 — Lane check for the parallel-run protocol was NOT RUN (BLOCKED)
- The protocol requires rank correlation and dot overlap against other registry rasters. Those rasters are on GEMSDOE sites that returned 000. **No correlation or overlap check has been done.** Any submission from this repo must not be treated as lane-checked.
