import json

import numpy as np
import pytest
import rasterio

from gems import submission


def test_writer_round_trip_matches_template(synth, tmp_path):
    _, _, tmpl, labels = synth
    arr = np.clip(labels.astype(np.float32) * 0.7 + 0.05, 0, 1)
    out = tmp_path / "out.tif"
    man = submission.write_submission(arr, tmpl, out, name="test-sub-001", note="unit test")
    assert man["verified"] is True
    with rasterio.open(tmpl) as t, rasterio.open(out) as s:
        assert s.crs == t.crs and s.transform == t.transform and s.shape == t.shape
        assert s.nodata is None
        assert s.dtypes[0] == "float32"
        data = s.read(1)
    assert np.isfinite(data).all() and data.min() >= 0 and data.max() <= 1
    side = json.loads((tmp_path / "out.tif.json").read_text())
    assert side["sha256"] == man["sha256"]


def test_writer_refuses_out_of_range_and_nan(synth, tmp_path):
    _, _, tmpl, _ = synth
    bad_hi = np.full((120, 160), 1.5, dtype=np.float32)
    with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
        submission.write_submission(bad_hi, tmpl, tmp_path / "a.tif", name="bad-range-01", note="x")
    bad_nan = np.zeros((120, 160), dtype=np.float32)
    bad_nan[3, 3] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        submission.write_submission(bad_nan, tmpl, tmp_path / "b.tif", name="bad-nan-01", note="x")
    assert not (tmp_path / "a.tif").exists() and not (tmp_path / "b.tif").exists()


def test_writer_refuses_wrong_shape_and_bad_metadata(synth, tmp_path):
    _, _, tmpl, _ = synth
    with pytest.raises(ValueError, match="shape"):
        submission.write_submission(np.zeros((10, 10), np.float32), tmpl, tmp_path / "c.tif",
                                    name="shape-test-01", note="x")
    ok = np.zeros((120, 160), np.float32)
    with pytest.raises(ValueError, match="name"):
        submission.write_submission(ok, tmpl, tmp_path / "d.tif", name="a b", note="x")
    with pytest.raises(ValueError, match="140"):
        submission.write_submission(ok, tmpl, tmp_path / "e.tif", name="ok-name-01", note="x" * 141)
