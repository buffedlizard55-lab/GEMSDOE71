import numpy as np
import rasterio

from gems import pipeline, submission


def test_holdout_runs_end_to_end_on_synthetic_rasters(synth):
    feat, lab, tmpl, _ = synth
    res = pipeline.run_holdout(feat, lab, n_folds=4, buffer_m=200, n_boot=100)
    assert res["label"] == "HOLDOUT-DTI"
    assert 0.0 <= res["pooled_dti"] <= 1.0
    lo, hi = res["dti_ci95"]
    assert lo <= hi
    assert res["withheld_positive_px"] > 0
    assert len(res["per_fold"]) == 4
    flags = {r["feature"]: r["flag"] for r in res["leakage_canary"]}
    assert set(flags) == set(res["features"])
    assert res["features"][-1] == "cat_dist_visible_m"


def test_full_prediction_writes_verified_tif_on_template(synth, tmp_path):
    feat, lab, tmpl, _ = synth
    pred = pipeline.predict_full(feat, lab)
    assert pred.shape == (120, 160)
    assert pred.min() >= 0 and pred.max() <= 1 and np.isfinite(pred).all()
    man = submission.write_submission(pred, tmpl, tmp_path / "synthetic_selftest.tif",
                                      name="synthetic-selftest-01", note="SYNTHETIC self-test, not GEMS data")
    assert man["verified"]
    with rasterio.open(tmp_path / "synthetic_selftest.tif") as s:
        assert s.count == 1
