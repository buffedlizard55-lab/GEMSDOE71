#!/usr/bin/env python3
"""Prepare, sanitize, and audit the competition rasters and cached feature stack for GEMSDOE71.

Reads:
  * .cache/training_features.tif (19 float32 official bands)
  * data/bridge/labels.tif & existing_faults.tif
  * data/bridge/sample_submission.tif
  * .cache/external/lidar_scarp_features_u8.tif (12 uint8 bands)
  * .cache/external/geodawn_rad_u8.tif (4 uint8 bands: K, Th, U, TC)
  * .cache/external/geodawn_extensions_u8.tif (4 uint8 bands: ThK, UK, UTh, TMI_up150)
  * data/external/derived_sgmc_faults_100m_u8.tif

Sanitizes nodata sentinels (-3.4028235e+38), writes fast per-band .npy arrays to .cache/bands/,
and writes data/prepared_manifest.json.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
BANDS_DIR = CACHE_DIR / "bands"

BASE_NAMES = [
    "mag_anom",
    "rtp",
    "tmi_hg",
    "geod_2ndinv",
    "iso_grav_anom_slope",
    "tc",
    "geod_shearrate",
    "geod_dilaterate",
    "tmi_vg",
    "deq_n100a15",
    "iso_grav_anom_vg",
    "det_elev",
    "iso_grav_anom",
    "tmi",
    "depth_to_base_surf",
    "ieq_n100a15",
    "cond_surf",
    "iso_grav_anom_hg",
    "det_elev_slope",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare() -> dict:
    BANDS_DIR.mkdir(parents=True, exist_ok=True)

    feat_path = CACHE_DIR / "training_features.tif"
    lab_path = ROOT / "data" / "bridge" / "labels.tif"
    exist_path = ROOT / "data" / "bridge" / "existing_faults.tif"
    tmpl_path = ROOT / "data" / "bridge" / "sample_submission.tif"
    lidar_path = CACHE_DIR / "external" / "lidar_scarp_features_u8.tif"
    rad_path = CACHE_DIR / "external" / "geodawn_rad_u8.tif"
    ext_path = CACHE_DIR / "external" / "geodawn_extensions_u8.tif"
    sgmc_path = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"

    for p in (feat_path, lab_path, exist_path, tmpl_path, lidar_path, rad_path, ext_path, sgmc_path):
        if not p.exists():
            raise FileNotFoundError(
                f"Missing required file {p}. Run `bash scripts/download_competition_data.sh` first."
            )

    with rasterio.open(tmpl_path) as tmpl:
        epsg = tmpl.crs.to_epsg()
        if epsg != 32611:
            raise ValueError(f"Expected EPSG:32611, got {tmpl.crs}")
        shape_hw = (tmpl.height, tmpl.width)
        if shape_hw != (3730, 3292):
            raise ValueError(f"Expected shape (3730, 3292), got {shape_hw}")
        transform_tuple = tuple(float(v) for v in tmpl.transform)[:6]
        foot_arr = tmpl.read(1)
        foot = np.isfinite(foot_arr)
        tmpl_ones_on_foot = int((foot_arr[foot] == 1.0).sum())

    with rasterio.open(lab_path) as lab_src:
        lab_raw = lab_src.read(1)
        lab = (lab_raw == 1) & foot

    with rasterio.open(sgmc_path) as sgmc_src:
        sgmc = (sgmc_src.read(1) > 0) & foot

    np.save(BANDS_DIR / "_footprint.npy", foot)
    np.save(BANDS_DIR / "_labels.npy", lab)
    np.save(BANDS_DIR / "_sgmc.npy", sgmc)

    band_stats = []
    total_sentinel_in_foot = 0
    any_sentinel_in_foot = np.zeros(shape_hw, dtype=bool)

    with rasterio.open(feat_path) as feat_src:
        if (feat_src.height, feat_src.width) != shape_hw:
            raise ValueError("training_features.tif shape mismatch")
        for idx, bname in enumerate(BASE_NAMES, 1):
            arr = feat_src.read(idx).astype(np.float32)
            is_sentinel = (~np.isfinite(arr)) | (arr < -1e38)
            sentinel_in_foot = int(np.sum(is_sentinel & foot))
            total_sentinel_in_foot += sentinel_in_foot
            any_sentinel_in_foot |= is_sentinel & foot

            arr[is_sentinel] = np.nan
            arr[~foot] = np.nan
            np.save(BANDS_DIR / f"{idx:02d}_{bname}.npy", arr)

            valid_vals = arr[foot & np.isfinite(arr)]
            band_stats.append(
                {
                    "index": idx,
                    "name": bname,
                    "source": "training_features.tif",
                    "description": feat_src.descriptions[idx - 1],
                    "finite_in_footprint": int(valid_vals.size),
                    "sentinel_in_footprint": sentinel_in_foot,
                    "min": float(np.min(valid_vals)),
                    "p05": float(np.percentile(valid_vals, 5)),
                    "median": float(np.median(valid_vals)),
                    "p95": float(np.percentile(valid_vals, 95)),
                    "max": float(np.max(valid_vals)),
                }
            )

    external_stats = []
    for ext_file, prefix in (
        (lidar_path, "lidar"),
        (rad_path, "rad"),
        (ext_path, "ext"),
    ):
        with rasterio.open(ext_file) as src:
            for b_idx in range(1, src.count + 1):
                bdesc = src.descriptions[b_idx - 1] or f"b{b_idx}"
                raw_u8 = src.read(b_idx)
                if bdesc == "valid":
                    val = (raw_u8 > 0).astype(np.float32)
                    val[~foot] = np.nan
                else:
                    val = np.where(raw_u8 > 0, (raw_u8.astype(np.float32) - 1.0) / 254.0, np.nan)
                    val[~foot] = np.nan
                cname = f"{prefix}_{bdesc}"
                np.save(BANDS_DIR / f"{cname}.npy", val.astype(np.float32))
                v = val[foot & np.isfinite(val)]
                external_stats.append(
                    {
                        "name": cname,
                        "source": ext_file.name,
                        "band": b_idx,
                        "finite_in_footprint": int(v.size),
                        "median": float(np.median(v)) if v.size else 0.0,
                        "p95": float(np.percentile(v, 95)) if v.size else 0.0,
                    }
                )

    manifest = {
        "schema_version": 1,
        "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grid": {
            "epsg": epsg,
            "height": shape_hw[0],
            "width": shape_hw[1],
            "total_cells": int(shape_hw[0] * shape_hw[1]),
            "transform": list(transform_tuple),
            "pixel_size_m": [100.0, 100.0],
        },
        "counts": {
            "footprint_valid_pixels": int(foot.sum()),
            "outside_footprint_pixels": int((~foot).sum()),
            "positive_catalogue_label_pixels": int(lab.sum()),
            "sgmc_positive_in_footprint_pixels": int(sgmc.sum()),
            "sample_submission_ones_in_footprint": tmpl_ones_on_foot,
            "negative_in_footprint_pixels": int(foot.sum() - lab.sum()),
            "total_sentinel_band_pixels_inside_footprint": total_sentinel_in_foot,
            "unique_footprint_pixels_with_any_sentinel": int(any_sentinel_in_foot.sum()),
        },
        "source_hashes": {
            "training_features.tif": sha256_file(feat_path),
            "labels.tif": sha256_file(lab_path),
            "existing_faults.tif": sha256_file(exist_path),
            "sample_submission.tif": sha256_file(tmpl_path),
            "lidar_scarp_features_u8.tif": sha256_file(lidar_path),
            "geodawn_rad_u8.tif": sha256_file(rad_path),
            "geodawn_extensions_u8.tif": sha256_file(ext_path),
            "derived_sgmc_faults_100m_u8.tif": sha256_file(sgmc_path),
        },
        "bands": band_stats,
        "external_channels": external_stats,
    }

    out_path = ROOT / "data" / "prepared_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    manifest = prepare()
    print(
        f"[GEMSDOE71] Prepared {len(manifest['bands'])} official bands + "
        f"{len(manifest['external_channels'])} external channels | "
        f"Footprint={manifest['counts']['footprint_valid_pixels']:,} px | "
        f"Catalogue positives={manifest['counts']['positive_catalogue_label_pixels']:,} px | "
        f"Sanitized {manifest['counts']['total_sentinel_band_pixels_inside_footprint']:,} sentinel band-pixels."
    )


if __name__ == "__main__":
    main()
