#!/usr/bin/env python3
"""Apply the post-run corrections that must be in the published card.

IR-71-DIST-01 inverted the catalogue mask in the first forensics write.
The corrected distances were remeasured from the same bytes and are merged
here. This script does not rescore the candidate and does not change the verdict.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems57.grid import TRANSFORM, HEIGHT, WIDTH, EPSG  # noqa: E402

CARD = ROOT / "evidence" / "run_card.json"
FIX = Path("/tmp/fix_forensics.json")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    card = json.loads(CARD.read_text())
    fix = json.loads(FIX.read_text())
    champ = card["champion_forensics"]
    dist = fix["champion_distance_m"]
    champ["min_distance_to_catalogue_m"] = dist["min"]
    champ["median_distance_to_catalogue_m"] = dist["median"]
    champ["fraction_within_300m"] = dist["fraction_within_300m"]
    champ["dots_on_catalogue"] = dist["dots_on_catalogue"]
    champ["distance_method"] = dist["method"]
    champ["void_first_write"] = (
        "The first card write reported min distance 0 m. That call complemented the "
        "catalogue twice. It is void. The numbers in this object were remeasured."
    )
    card["champion_forensics"] = champ
    card["ours_vs_champion_3px_overlap"] = fix["ours_vs_champion_3px_overlap"]
    card["ours_distance_to_catalogue_m"] = fix["ours_distance_m"]
    card["off_catalogue_incumbent_diagnostic"] = {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": "gems57-pooled-hide-v2",
        "role": "diagnostic, not the preregistered gate",
        "why": (
            "The preregistered incumbent was the maximum HOLDOUT-DTI among all local "
            "registry rasters. That maximum is a file that is positive on every catalogue "
            "pixel, so its false-negative count on withheld catalogue segments is zero. "
            "It is not a discovery analogue. This diagnostic restricts the comparison to "
            "registry rasters with zero positive pixels on the published catalogue."
        ),
        "top": fix["off_catalogue_incumbent_top"],
        "candidate_still_below": True,
    }
    card["irregularities"] = [
        "IR-71-DIST-01",
        "IR-71-INCUMBENT-01",
        "IR-71-UNIQ-01",
        "IR-71-SAMPLE-01",
        "IR-71-MIRROR-01",
        "IR-71-LANE-01",
        "IR-71-TEMPLATE-UNIQ-01",
    ]

    # NaN-outside twin. Inside-footprint bytes match the zeros file. Not the upload.
    zeros = ROOT / "docs" / "downloads" / card["filename"]
    with rasterio.open(zeros) as src:
        a = src.read(1)
        profile = src.profile
    fp = np.isfinite(a)  # zeros file is all finite; footprint is the non-requirement here
    # Reconstruct footprint from the bridge sample so outside cells become NaN.
    sample = Path("/tmp/template60/data/bridge/sample_submission.tif")
    with rasterio.open(sample) as src:
        sample_a = src.read(1)
        if src.crs.to_epsg() != EPSG or src.shape != (HEIGHT, WIDTH):
            raise SystemExit("sample grid changed")
        if tuple(src.transform)[:6] != tuple(TRANSFORM)[:6]:
            raise SystemExit("sample transform changed")
    footprint = np.isfinite(sample_a)
    if not np.array_equal(a[~footprint], np.zeros((~footprint).sum(), np.float32)):
        raise SystemExit("zeros file is not zero outside the footprint")
    nan_arr = a.astype(np.float32).copy()
    nan_arr[~footprint] = np.nan
    if not np.array_equal(nan_arr[footprint], a[footprint]):
        raise SystemExit("nan twin changed inside-footprint values")
    nan_name = card["filename"].replace("-zeros.tif", "-nan.tif")
    nan_path = ROOT / "docs" / "downloads" / nan_name
    profile.update(dtype="float32", count=1, compress="lzw", nodata=None, tiled=False)
    # Write nodata=NaN explicitly.
    with rasterio.open(nan_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH, count=1,
                       dtype="float32", crs=f"EPSG:{EPSG}", transform=TRANSFORM,
                       nodata=float("nan"), compress="lzw") as dst:
        dst.write(nan_arr, 1)
        dst.set_band_description(1, "predicted_new_fault_probability")
    with rasterio.open(nan_path) as src:
        b = src.read(1)
        nan_meta = {
            "filename": nan_name,
            "sha256": sha256_file(nan_path),
            "role": "official-wording alternate; NOT the upload",
            "crs": str(src.crs),
            "shape": [src.height, src.width],
            "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata_is_nan": bool(src.nodata is not None and np.isnan(src.nodata)),
            "nan_pixels": int(np.isnan(b).sum()),
            "inside_matches_zeros_file": bool(np.array_equal(b[footprint], a[footprint])),
            "outside_all_nan": bool(np.isnan(b[~footprint]).all()),
            "inside_min": float(np.nanmin(b[footprint])),
            "inside_max": float(np.nanmax(b[footprint])),
            "do_not_upload": True,
            "why": (
                "The problem page says data outside the bounds is null or NaN. A previous "
                "upload from this project family was rejected with 'Predicted values must be "
                "in range [0, 1]'. This twin follows the page. The -zeros file is the one "
                "that cannot contain a nodata sentinel. Neither file is cleared for a slot."
            ),
        }
    card["nan_twin"] = nan_meta
    CARD.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (ROOT / "evidence" / "h71_champion_forensics.json").write_text(
        json.dumps(card["champion_forensics"], indent=2) + "\n")
    print("patched", nan_name, nan_meta["sha256"][:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
