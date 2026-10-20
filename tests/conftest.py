import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CRS = "EPSG:32611"
RES = 100.0
H, W = 120, 160


def _segments(rng, n=8):
    """Synthetic fault traces: 2-px-wide straight lines. SYNTHETIC, not GEMS data.

    Segment centres are stratified across columns so every holdout stripe contains a segment.
    """
    mask = np.zeros((H, W), dtype=bool)
    yy, xx = np.mgrid[0:H, 0:W]
    for i in range(n):
        x0 = (i + rng.uniform(0.2, 0.8)) / n * W
        y0 = rng.uniform(0, H)
        ang = rng.uniform(0, np.pi)
        ux, uy = np.cos(ang), np.sin(ang)
        # distance from each pixel to the infinite line through (x0, y0)
        dist = np.abs((xx - x0) * uy - (yy - y0) * ux)
        seg_len = (np.abs((xx - x0) * ux + (yy - y0) * uy) < rng.uniform(15, 35))
        mask |= (dist < 1.0) & seg_len
    return mask


def make_synthetic(tmp_path, seed=0, leak=False):
    rng = np.random.default_rng(seed)
    labels = _segments(rng)
    yy, xx = np.mgrid[0:H, 0:W]
    # Weak, physically-motivated-looking signal: smooth response near faults + noise.
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(~labels) * RES
    signal = np.exp(-dist / 300.0)
    bands = [signal + rng.normal(0, 0.3, (H, W)) for _ in range(3)]
    bands += [rng.normal(0, 1, (H, W)) for _ in range(3)]
    if leak:
        bands.append(labels.astype(float) + rng.normal(0, 0.01, (H, W)))
    feat = np.stack(bands).astype(np.float32)
    feat[:, :5, :5] = -3.4028234663852886e38  # nodata corner -> study area excludes it
    transform = from_origin(500000.0, 4000000.0, RES, RES)
    feat_path = tmp_path / "features.tif"
    with rasterio.open(feat_path, "w", driver="GTiff", height=H, width=W, count=feat.shape[0],
                       dtype="float32", crs=CRS, transform=transform, nodata=-3.4028234663852886e38) as dst:
        for i in range(feat.shape[0]):
            dst.write(feat[i], i + 1)
            dst.update_tags(i + 1, description=f"synthetic band {i + 1}")
    lab = labels.astype(np.int32)
    lab_path = tmp_path / "labels.tif"
    with rasterio.open(lab_path, "w", driver="GTiff", height=H, width=W, count=1, dtype="int32",
                       crs=CRS, transform=transform, nodata=-1) as dst:
        dst.write(lab, 1)
    tmpl_path = tmp_path / "template.tif"
    with rasterio.open(tmpl_path, "w", driver="GTiff", height=H, width=W, count=1, dtype="float32",
                       crs=CRS, transform=transform) as dst:
        dst.write(np.zeros((H, W), dtype=np.float32), 1)
    return feat_path, lab_path, tmpl_path, labels


@pytest.fixture
def synth(tmp_path):
    return make_synthetic(tmp_path)
