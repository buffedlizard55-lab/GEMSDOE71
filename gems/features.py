"""Feature stack and catalogue-derived features.

Catalogue rule (hide-and-recover): every feature that uses the fault catalogue is computed from
the *visible* faults only. See gems/holdout.py for how the visible set is built per fold.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

from . import config


def load_feature_stack(path: str | Path) -> tuple[np.ndarray, list[str]]:
    """Read all bands into one contiguous (H, W, C) float32 array. Nodata becomes NaN.

    Bands are written into a preallocated array one at a time to keep peak memory low
    (the full GEMS stack is ~0.9 GB as float32). Returns the stack and band descriptions.
    """
    with rasterio.open(path) as src:
        H, W, C = src.height, src.width, src.count
        out = np.empty((H, W, C), dtype=np.float32)
        names = []
        for i in range(1, C + 1):
            band = src.read(i).astype(np.float32, copy=False)
            if src.nodata is not None:
                band[band == np.float32(src.nodata)] = np.nan
            band[band < config.NODATA_FLOOR] = np.nan
            out[:, :, i - 1] = band
            names.append(src.tags(i).get("description", f"band{i}"))
            del band
    return out, names


def minmax_normalize(X: np.ndarray) -> np.ndarray:
    """Per-channel min-max to [0, 1] using finite values (same rule as the reference notebook).

    Only feature min/max are used (no labels), so this does not leak fault labels.
    Works in place on the float32 stack to avoid a second full copy.
    """
    lo = np.nanmin(X, axis=(0, 1)).astype(np.float32)
    hi = np.nanmax(X, axis=(0, 1)).astype(np.float32)
    span = np.where(hi - lo > 0, hi - lo, 1.0).astype(np.float32)
    X -= lo
    X /= span
    return X


def study_area(X: np.ndarray) -> np.ndarray:
    """Footprint = pixels with at least one finite feature value."""
    return np.isfinite(X).any(axis=-1)


def distance_to_visible_faults(visible_mask: np.ndarray, res_m: float = config.EXPECTED_RES_M) -> np.ndarray:
    """Euclidean distance (m) from each pixel to the nearest VISIBLE fault pixel.

    If there are no visible faults the distance is set to a large constant so the feature
    carries no spurious information.
    """
    if not visible_mask.any():
        return np.full(visible_mask.shape, 1e6, dtype=np.float32)
    d = ndimage.distance_transform_edt(~visible_mask, sampling=res_m)
    return d.astype(np.float32)


def oof_distance_map(visible_faults: np.ndarray, stripe_index: np.ndarray, scoring_stripe: int,
                     res_m: float = config.EXPECTED_RES_M) -> np.ndarray:
    """Catalogue distance feature for one fold WITHOUT label copying.

    - Pixels in the scoring stripe: distance to ALL visible faults (what the holdout can know).
    - Pixels in any other (training) stripe j: distance to visible faults OUTSIDE stripe j.
      Without this, a training pixel on a visible fault has distance 0 and the model learns
      "distance 0 == fault", which is a label copy and predicts ~0 on unseen faults.
    """
    out = distance_to_visible_faults(visible_faults, res_m).copy()
    # stripes depend only on the column, so one row of the broadcast array lists them all
    for j in np.unique(stripe_index[0]):
        if j == scoring_stripe:
            continue
        m = stripe_index == j
        out[m] = distance_to_visible_faults(visible_faults & ~m, res_m)[m]
    return out


def build_feature_matrix(X_norm: np.ndarray, dist_m: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Append the catalogue-derived distance channel. One allocation; NaN -> 0 in place."""
    H, W, C = X_norm.shape
    stacked = np.empty((H, W, C + 1), dtype=np.float32)
    stacked[..., :C] = X_norm
    stacked[..., C] = dist_m
    np.nan_to_num(stacked, copy=False, nan=0.0)
    names = [f"f{i:02d}" for i in range(C)] + ["cat_dist_visible_m"]
    return stacked, names
