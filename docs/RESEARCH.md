# Research notes — GEMS geothermal-fault submission

Status date: 2026-10-20 (UTC). **No candidate has been validated on real data.** The competition
rasters, the official metric text, and the GEMSDOE pages are all unreachable from the build sandbox
(see [SOURCES](SOURCES.md)). Everything below is one of three kinds, labelled in the text:

- **[CHECKED]** computed or read here, with a reference.
- **[PRIOR]** a reasoned expectation, not measured. It must not be written as a score.
- **[UNVERIFIED]** a claim we could not check against an official source.

Budget used on real data: **0 of 3 experiments**, **0 submission slots**. The synthetic checks
below are pipeline self-tests, not protocol experiments.

---

## 1. Why did the GEMSDOE32 submission (`h33-h33-2-b2-…-zeros`, 0.2778) score highest?

### 1.1 What we know
- [CHECKED] The brief lists it as the best per-site score (0.2778). The next highest listed are 0.2750 (GEMSDOE36) and 0.2710 (GEMSDOE28). See `data/user_reported_scores.csv`.
- [CHECKED] The GEMSDOE32 page is unreachable here, so **we cannot read its method, parameters, or output**. Anything about how it was built is [UNVERIFIED].
- [UNVERIFIED] The name suggests a family `h33`, a variant `2`, and a `zeros` suffix. We read the suffix as "something was set to zero" and cannot say what.

### 1.2 Leading explanation (metric geometry, testable)
Under α=0.2 and β=0.8 the metric weights missed faults (FN) four times as heavily as false alarms (FP). The 300 m triangular tolerance gives partial credit to predictions that are close to a fault. Together these reward **broad, high-recall maps placed along fault-prone corridors** more than sharp, precise traces. [PRIOR for the leaderboard, CHECKED for the metric behaviour in §1.3.]

### 1.3 Metric geometry on synthetic fault geometry [CHECKED — our metric implementation, synthetic 400×400 network with 12 random lines, 100 m cells]

| Prediction | Pooled DTI (our definition) |
|---|---|
| Exact fault trace | 1.000 |
| Trace dilated by 1 px (100 m band) | 0.963 |
| Trace shifted 200 m | 0.774 |
| Gaussian blur, σ=200 m, max-normalized | 0.711 |
| Trace shifted 600 m | 0.424 |
| Constant 0.1 everywhere | 0.132 |
| **All ones (predict "fault" everywhere)** | **0.244** |
| All zeros | 0.000 |

Read this table as a statement about the metric, not about the leaderboard. Two things follow:
1. Position matters less than the metric's raw precision suggests: a 200 m miss still keeps about three quarters of the score.
2. A map that predicts everything is not worthless under this weighting.

### 1.4 The coverage floor (closed form, [CHECKED] by unit test)
For the all-ones map, with `a` = total tolerance coverage over the scoring domain and `N` = domain pixels:
`DTI_ones = a / (a + 0.2 (N − a))`. The all-ones map therefore beats a target score `x` exactly when
**mean coverage `a/N ≥ 0.2x / (1 − 0.8x)`**:

| Target score | Required mean coverage |
|---|---|
| 0.2778 (GEMSDOE32) | ≥ 0.0714 |
| 0.3195 (brief's "highest") | ≥ 0.0858 |
| 0.4413 (brief's "highest") | ≥ 0.1364 |

**Consequence [PRIOR until measured]:** if the real fault network covers roughly 7% of the scoring domain under the 300 m tolerance, a trivial map reaches 0.2778. This is the most important check we can run first, and it needs only the labels. `scripts/run_holdout.py` reports it automatically as `trivial_baselines`.

### 1.5 Can we beat 0.2778?
- **Not demonstrated.** Nothing here has been scored on real data, so no claim of beating 0.2778 is made.
- **The bar is higher than 0.2778.** A submission must beat the trivial all-ones baseline on the same holdout, by a margin whose 95% CI excludes the baseline. Otherwise a high leaderboard number says more about coverage than about discovery.
- **We will not submit a coverage-maximising map as a discovery.** It would score on the metric but would not be a geological result. We report it as a control.

---

## 2. Candidate hypotheses (ranked)

All use layers from the reference notebook's verified band list (see [FLAGS](FLAGS.md) F1–F2 for band-index issues). "Missing from catalogue" means the feature targets faults the USGS/INGENIOUS catalogue cannot contain.

| Rank | Hypothesis | Layers | Physical signature | Why it could catch a catalogue-missing fault | How it differs from the reference | Main non-fault mimic | Cost | Status |
|---|---|---|---|---|---|---|---|---|
| **1** | **H1 — Catalogue-incompleteness correction (positive-unlabeled learning).** Treat catalogue traces as labelled positives and everything else as *unlabelled*, not negative. Estimate the probability that an unlabelled pixel is a missing fault. | Catalogue labels; Band 6 (tilt), Band 3 (THD), Band 15 (basement depth) | Linear magnetic ridge with no mapped trace | Directly models the "missing from catalogue" class instead of calling it negative | Reference labels all non-catalogue pixels 0 (cell 12, `y_train`) | Catalogue-sampling bias: faults get mapped where roads and surveys are dense, so the model learns survey geography | Low | **Top candidate.** Not validated. Gate below. |
| 2 | **H3 — Concealed-fault coincidence index.** Multiply normalised gravity-gradient, basement-step, and magnetic-lineament maps; high values mark places where three independent fields agree. | Band 18 (horizontal gradient), Band 5 (slope), Band 15 (depth to basement), Band 6 (tilt) | Gravity-gradient maximum coincident with a basement step and magnetic lineament | Faults under basin fill have no surface trace, so they cannot be in a surface-mapped catalogue | Multi-physics coincidence instead of learned per-channel filters | Depositional basin margin with no fault (onlap); isostatic residual error near ranges | Medium | Contrarian bet. Not validated. |
| 3 | **H2 — Multi-scale structural ridge coherence.** Hessian ridge detection on RTP, then keep ridges whose orientation is coherent within a 1–3 km structure-tensor window. | Band 2 (RTP), Band 9 (vertical gradient), Band 6 (tilt) | Coherent linear magnetic ridges | Buried or weakly magnetised faults show as coherent lineaments without a scarp | Explicit orientation coherence, not learned convolution | Airborne flight-line striping; dikes; shallow basalt flows | Low–medium | Not validated. Ridge filters are common, so less contrarian. |
| 4 | **H4 — Geodetic strain discontinuity.** Lateral jumps in strain-rate fields, using the gradient direction rather than magnitude. | Band 4 (second invariant), Band 7 (shear), Band 8 (dilatation) | Strain discontinuity aligned with strike | Aseismic creep and slip with no surface expression | Uses discontinuity direction, not magnitude | GNSS/InSAR coverage seams and interpolation edges; plate-scale strain. Needs a coverage-mask control | Low | Not validated. Blocked until a coverage mask is available (see §4). |
| 5 | **H5 — Seismicity alignments.** Azimuthal alignment of earthquakes. | Band 10 (distance to earthquake), Band 16 (intensity/density) | Clusters of epicentres aligned along a plane | Aftershock planes can mark unmapped faults | Would need raw epicentres | Earthquake clustering without a single plane | — | **Not viable yet.** The bands are pre-aggregated. Raw USGS ComCat is blocked here, and the meaning of the "azimuth parameters" in the band description is [UNVERIFIED]. |

### 2.1 Gate before any submission slot is spent
1. Holdout DTI (`run_holdout`, HOLDOUT-DTI label) with its 95% CI.
2. The all-ones baseline on the same holdout. The candidate's CI lower bound must exceed that baseline.
3. Canary: no single feature above AUC 0.90 (`LEAKAGE-REVIEW` flag); if one is flagged, the candidate is blocked until a human clears it.
4. Correlation and overlap against any other registry raster, when those rasters are reachable (currently not).
5. Validator pass on the written TIF (`scripts/validate_submission.py`).

---

## 3. What the pipeline does and does not do

Implemented and tested here:
- Hide-and-recover folds: whole fault segments withheld by spatial stripe; buffer excluded from training; catalogue features built from visible faults only; visible faults removed from the scoring domain pixel-exactly.
- Out-of-fold catalogue distance (fixes a label copy found during this session, F11).
- Pooled soft Tversky/DTI with a triangular tolerance, a fold-level bootstrap CI, a leakage canary, and the all-ones baseline.
- Submission writer that refuses NaN and out-of-range values, matches the template's CRS, shape and transform, and re-reads the file to verify it.

Not implemented or not validated:
- Any real-data result. The data is not present.
- A U-Net. The reference notebook uses one; we use a gradient-boosting baseline so the pipeline runs on CPU. The U-Net is the next model to add once a GPU and the data are available.
- Threshold selection. We output probabilities. Whether thresholding helps under this metric is an open experiment.

---

## 4. Metric definition used (ASSUMED)

Documented in `gems/metric.py`. Summary: `TP = Σ p·Tt`, `FP = Σ p·(1−Tt)`, `FN = Σ t·(1−Pc)`, where `Tt` is the truth dilated by the triangular kernel and `Pc` is the prediction dilated the same way. With zero tolerance it reduces to standard Tversky (unit test). **If GEMS_96647.pdf defines it differently, change `metric.py` once and re-run every holdout.** Do not keep a private copy.

---

## 5. Data sources — what is needed, and what is verified

| Need | Candidate | Status | Note |
|---|---|---|---|
| Labels, features, submission grid | DrivenData data tab; Dropbox mirrors in the brief | BLOCKED here | Required for everything. See `scripts/download_competition_data.sh`. |
| Metric text | GEMS_96647.pdf | BLOCKED here | Needed to confirm §4. |
| Independent fault catalogue | GEM Global Active Faults DB (GitHub) | VERIFIED accessible, CC-BY-SA-4.0 | **Not independent for US**: traces come from USGS Hazfaults 2014 and UCERF3. Useful only for global-scale checks. |
| Survey coverage (for H1 covariate) | USGS GeoDAWN survey extent | BLOCKED here | Needed to control the H1 mimic. |
| Seismicity (for H5) | USGS ComCat FDSN API | BLOCKED here | Obtainable? **Unverified.** Must be checked from an unrestricted machine. |
| Regional geology | Nevada Bureau of Mines and Geology (NBMG) | BLOCKED here | https://www.nbmg.unr.edu/ returned HTTP 000 from the sandbox. Contents unchecked. |
| Quaternary fault catalogue (USGS) | USGS Quaternary Fault and Fold Database | **Name only, URL not verified** | Probably the lineage of the competition catalogue. Check before use. |

---

## 6. What others may be overlooking [PRIOR]

- The **metric**: coverage and tolerance (§1). [UNVERIFIED] Other entries may well be high-recall maps; we cannot inspect their rasters from here. Our edge, if any, comes from calibrating against the trivial baseline and reporting that honestly.
- The **label**: catalogue faults are presence-only. PU learning (H1) is standard in other fields but is not what the reference does.
- **Concealed faults** (H3): a catalogue of mapped traces cannot contain them, so any method limited to mapped traces is blind to them.
- **Survey geography** as a confounder (H1 mimic). It is easy to learn and easy to miss.

---

## 7. Next steps (in order)

1. Place the data in `data/` on an unrestricted machine (`scripts/download_competition_data.sh` for the public links; DrivenData files by hand).
2. `python scripts/prepare_data.py` — resolves names, checks CRS/shape/band count, writes `data/manifest.json`.
3. Read GEMS_96647.pdf and update `gems/metric.py` if the definition differs (§4).
4. `python scripts/run_holdout.py` — record the all-ones baseline and the canary before anything else.
5. Only then run H1 as the first experiment, against the gate in §2.1.
