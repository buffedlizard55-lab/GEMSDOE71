"""Standalone checks for any candidate GeoTIFF (organiser data or a submission)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from . import config
from .rasters import sha256_file


def report(path, template=None, expect_crs=config.EXPECTED_CRS) -> dict:
    """Return a dict of checks. 'pass' is True only if every check passes."""
    checks = {}
    with rasterio.open(path) as s:
        arr = s.read(1).astype(np.float64) if s.count >= 1 else None
        checks["bands"] = s.count
        checks["dtype"] = s.dtypes[0]
        checks["nodata_tag"] = s.nodata
        checks["crs"] = s.crs.to_string() if s.crs else None
        checks["crs_ok"] = (s.crs is not None and s.crs.to_string() == expect_crs)
        checks["shape"] = [s.height, s.width]
        checks["transform"] = list(s.transform)[:6]
        if template is not None:
            with rasterio.open(template) as t:
                checks["template_crs_match"] = s.crs == t.crs
                checks["template_transform_match"] = s.transform == t.transform
                checks["template_shape_match"] = (s.height, s.width) == (t.height, t.width)
    finite = np.isfinite(arr)
    checks["nan_or_inf_count"] = int((~finite).sum())
    vals = arr[finite]
    checks["min"] = float(vals.min()) if vals.size else None
    checks["max"] = float(vals.max()) if vals.size else None
    checks["in_unit_interval"] = bool(vals.size and vals.min() >= 0 and vals.max() <= 1)
    checks["sha256"] = sha256_file(path)
    checks["file"] = str(Path(path).name)
    keys = [k for k in checks if k.endswith("_ok") or k.endswith("_match")]
    checks["pass"] = (checks["bands"] == 1 and checks["nan_or_inf_count"] == 0
                      and checks["in_unit_interval"] and all(checks[k] for k in keys))
    return checks
