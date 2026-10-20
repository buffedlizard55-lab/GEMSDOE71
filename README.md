# GEMSDOE71

Read this file before changing the lane, the metric, or the submission file.

**Verdict: negative. Not OK to submit.** The audit GeoTIFF is downloadable from [`docs/index.html`](docs/index.html). It is not cleared for a DrivenData weekly slot. `slots_used` is 0.

| | |
|---|---|
| File | `docs/downloads/gemsdoe71-h71-ventconduit-20261020T200548Z-9dc1668b-zeros.tif` |
| sha256 | `c5c63e82a1f788fe2c30463a08b4e72d8c477ce3154d9727033bb40efa01a4d2` |
| Name | `GEMSDOE71-H71-vent-conduit` |
| Note (116 chars) | `GEMSDOE71 H71 vent-conduit; sinter/spring axes x mag-edge; NMS3 off-catalogue; local checks only; no organiser score` |
| HOLDOUT-DTI | 0.001538, 95% CI [0.000219, 0.003261], evaluator `gems57-pooled-hide-v2`, 11,321 withheld positives |
| Organizer score | none |

## Standing prompt

This is the project prompt. Later sessions start here.

Generate a unique, obviously downloadable DOE GEMS (DrivenData competition 306) submission GeoTIFF for this repository. It must be submittable without the portal error “Predicted values must be in range [0, 1]”. Give it a unique name and a note of at most 140 characters. Explain why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is listed at 0.2778, and whether a higher score is possible, then use that explanation to build a submission unlike prior GEMSDOE rasters.

Also required:

- A GitHub Pages site with a clean UI and links to the official sources.
- The download, and a clear statement of whether the file is OK to submit, at the top of the site.
- An executive-summary subpage with the exact steps to submit on DrivenData.
- This prompt, in this README.
- Three to five geological hypotheses that have not already been tried, ranked by expected distance-weighted Tversky against cost.
- Holdout-validate the top hypothesis before any weekly slot is spent.
- One JSON run card.
- A pull request merged to `main`.
- Do not pick or spend a real submission slot.

Parallel-run protocol, which binds this checkout:

- One lane. Do not enter a lane another session already owns.
- If rank-correlation with any registry raster exceeds 0.90, or more than 70% of dots lie within 3 pixels of one registry raster, log a duplicate and stop. Check the surface before placement and check the final dots.
- Reuse the template’s cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Holdout means hide-and-recover whole fault segments, with a buffer. Catalogue features come only from visible faults. Mask visible faults pixel-exactly. Pooled DTI uses α = 0.2, β = 0.8, and a 300 m triangular kernel.
- Fix shared tools once in the template. Do not keep a private fork.
- Label every number HOLDOUT-DTI (evaluator version, withheld-positive count, 95% interval) or ORGANIZER-CONFIRMED (a submission-page receipt). Never write a projection as a score.
- Leakage canary: score each feature alone on the holdout. AUC above 0.90 is leakage until proven otherwise.
- End with one JSON run card: hypothesis, mechanism, named non-fault mimic, holdout DTI and interval, correlation and overlap against the registry, raster sha256, validator result (no NaN inside the footprint, values in [0, 1], CRS, shape, and transform match), submission name, note of at most 140 characters, and a promote or negative verdict. A negative is a deliverable.
- Stop after 3 experiments or 2 hours. Do not pick submissions.

Other constraints that came with the prompt:

- Values must be in [0, 1]. A previous download failed the portal with “Predicted values must be in range [0, 1]”.
- The file must be unique, not a copy of a previous submission.
- No DrivenData login. Use free official public sources only. No manual input. Verify line by line. Do not invent numbers. Flag irregularities and give links for manual review.
- Work through three passes: implement, review and fix, then re-check against this prompt.
- Stay on the session branch. Merge to `main` only through a pull request.

The prompt referred to “the single method paragraph below.” No separate method paragraph was in the text delivered to this session. That gap is IR-71-LANE-01. The lane was taken from the scientific instruction in the same prompt: geothermal-vent evidence for faults the catalogue missed, not a copy of an existing raster. It was frozen in `registry/preregistration-h71.json` before any score was computed.

## What this checkout found

H71 tested whether sinter, travertine, and spring-cluster axes, confirmed by a magnetic edge, mark catalogue-missed faults. They do not, on this holdout. The winner of the three preregistered experiments does not beat a mass-matched random draw. The file is a valid, unique, finite `[0, 1]` GeoTIFF, and it is still a negative.

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is an owner-reported public score of 0.2778 from the GEMSDOE32 site, not an organizer receipt held here. On the shared evaluator it scores about 0.0037. The official public board, fetched 2026-10-20, has rank 1 at 0.4413, so a higher organizer score than 0.2778 exists. This file is not evidence that this lane can reach it. The argument, the algebra, and the links are on the [method page](docs/method.html).

## Pages

- [Audit page](docs/index.html) — verdict and download.
- [How to submit](docs/executive-summary.html) — portal steps. Do not use them on this file.
- [Why 0.2778](docs/method.html)
- [Hypotheses](docs/hypotheses.html)
- [Sources](docs/sources.html)
- [Irregularities](docs/irregularities.html)
- [Run card](docs/data/run-card.json)

## Reproduce the published card

Do not retune `registry/preregistration-h71.json`. Do not spend a slot.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python tests/test_metric_and_loader.py
python scripts/publish_corrections.py   # needs /tmp/fix_forensics.json from the remeasurement
python scripts/build_site.py
python scripts/refresh_leaderboard.py   # fail-closed; does not invent rows
```

The experiment runner is `scripts/run_h71.py`. It already ran. Re-running it spends hours and does not change the frozen verdict. The 19-band feature stack was not available in this sandbox; the canary that needed it was skipped and is labeled that way in the card.

Shared evaluator: [60GEMSDOE](https://github.com/buffedlizard55-lab/60GEMSDOE) commit `b99591ee`, vendored byte-identically into `src/gems57`. Hashes are in `docs/template-provenance.json`.
