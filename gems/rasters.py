"""Raster I/O helpers with explicit format checks."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio

from . import config


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def format_problems(path: str | Path, *, expect_shape=config.EXPECTED_SHAPE,
                    expect_crs=config.EXPECTED_CRS, expect_res=config.EXPECTED_RES_M) -> list[str]:
    """Return a list of human-readable format problems (empty list = OK)."""
    problems: list[str] = []
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_string() != expect_crs:
            problems.append(f"CRS is {src.crs}, expected {expect_crs}")
        if expect_shape is not None and (src.height, src.width) != tuple(expect_shape):
            problems.append(f"shape is {(src.height, src.width)}, expected {tuple(expect_shape)}")
        if expect_res is not None and (abs(src.res[0] - expect_res) > 1e-6 or abs(src.res[1] - expect_res) > 1e-6):
            problems.append(f"resolution is {src.res}, expected {expect_res} m")
    return problems


def read_band(path: str | Path, band: int = 1) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        arr = src.read(band)
        meta = {"nodata": src.nodata, "transform": src.transform, "crs": src.crs,
                "shape": (src.height, src.width), "dtype": src.dtypes[band - 1]}
    return arr, meta
