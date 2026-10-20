"""Submission writer + validator.

Enforces the rules behind the portal error "Predicted values must be in range [0, 1]":
no NaN/inf, every value in [0, 1], single band, same CRS/transform/shape as the template.
The writer never silently clips: out-of-range values raise an error so the cause is visible.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from .rasters import sha256_file

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
NOTE_MAX = 140


def validate_array(arr: np.ndarray, template_shape: tuple[int, int]) -> list[str]:
    errs = []
    if arr.ndim != 2:
        errs.append(f"array must be 2-D, got {arr.ndim}-D")
        return errs
    if tuple(arr.shape) != tuple(template_shape):
        errs.append(f"shape {arr.shape} != template {tuple(template_shape)}")
    if not np.isfinite(arr).all():
        errs.append(f"{int((~np.isfinite(arr)).sum())} non-finite values (NaN/inf)")
    finite = arr[np.isfinite(arr)]
    if finite.size and (finite.min() < 0.0 or finite.max() > 1.0):
        errs.append(f"values outside [0, 1]: min={finite.min():.6g}, max={finite.max():.6g}")
    return errs


def validate_name_note(name: str, note: str) -> list[str]:
    errs = []
    if not NAME_RE.match(name or ""):
        errs.append("name must be 3-64 chars of letters, digits, '.', '_' or '-'")
    if note is None or len(note) > NOTE_MAX:
        errs.append(f"note must be at most {NOTE_MAX} characters")
    return errs


def default_name(prefix: str, digest: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{digest[:8]}"


def verify_file(path, template_path) -> list[str]:
    """Re-open the written file and compare it with the template and the value rules."""
    errs = []
    with rasterio.open(template_path) as t, rasterio.open(path) as s:
        if s.count != 1:
            errs.append(f"band count {s.count}, expected 1")
        if s.crs != t.crs:
            errs.append(f"CRS {s.crs} != template {t.crs}")
        if s.transform != t.transform:
            errs.append(f"transform {s.transform} != template {t.transform}")
        if (s.height, s.width) != (t.height, t.width):
            errs.append(f"shape {(s.height, s.width)} != template {(t.height, t.width)}")
        if s.nodata is not None:
            errs.append(f"nodata is set to {s.nodata}; writer should leave it unset")
        arr = s.read(1)
    errs += validate_array(arr, (t.height, t.width))
    return errs


def write_submission(arr: np.ndarray, template_path, out_path, name: str, note: str,
                     extra: dict | None = None) -> dict:
    """Write a float32 GeoTIFF on the template grid, verify it, and write a JSON sidecar."""
    out_path = Path(out_path)
    with rasterio.open(template_path) as t:
        shape, crs, transform = (t.height, t.width), t.crs, t.transform
    errs = validate_array(arr, shape) + validate_name_note(name, note)
    if errs:
        raise ValueError("refusing to write submission: " + "; ".join(errs))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = arr.astype(np.float32)
    with rasterio.open(out_path, "w", driver="GTiff", height=shape[0], width=shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=None, compress="deflate") as dst:
        dst.write(data, 1)
        dst.update_tags(gems_name=name, gems_note=note)
    errs = verify_file(out_path, template_path)
    digest = sha256_file(out_path)
    manifest = {"name": name, "note": note, "file": out_path.name, "sha256": digest,
                "shape": list(shape), "crs": crs.to_string(), "verified": not errs,
                "verify_errors": errs, "created_utc": datetime.now(timezone.utc).isoformat(),
                **(extra or {})}
    out_path.with_suffix(out_path.suffix + ".json").write_text(json.dumps(manifest, indent=2))
    if errs:
        raise ValueError("written file failed verification: " + "; ".join(errs))
    return manifest
