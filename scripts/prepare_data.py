#!/usr/bin/env python
"""Locate and check the GEMS inputs in data/, then write data/manifest.json.

Looks for files under the names the organisers and the reference notebook use. Reports every
format problem and exits non-zero if any required input is missing or fails a check.
Nothing is downloaded here.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gems import config  # noqa: E402
from gems.rasters import format_problems, sha256_file  # noqa: E402

DATA = ROOT / "data"
CANDIDATES = {
    # role: (search order, expected band count or None)
    "features": (["numeric_features.tif", "gems-geodawn-numerical-features.tif"], config.N_FEATURE_BANDS),
    "labels": (["labels.tif", "existing_faults.tif"], 1),
    "template": (["sample_submission.tif", "example_submission.tif"], 1),
}


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    problems, found = [], {}
    for role, (names, nbands) in CANDIDATES.items():
        path = next((DATA / n for n in names if (DATA / n).exists()), None)
        if path is None:
            problems.append(f"{role}: none of {names} found in data/")
            continue
        found[role] = path
        probs = format_problems(path, expect_shape=config.EXPECTED_SHAPE if role != "template" else None)
        import rasterio
        with rasterio.open(path) as src:
            if nbands is not None and src.count != nbands:
                probs.append(f"band count {src.count}, expected {nbands}")
        for p in probs:
            problems.append(f"{role} ({path.name}): {p}")
    manifest = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "roles": {r: {"file": p.name, "sha256": sha256_file(p)} for r, p in found.items()},
        "problems": problems,
        "note": ("labels.tif (DrivenData) and existing_faults.tif (Dropbox) are both accepted as 'labels' "
                 "for now; confirm which one is the fault label raster before trusting results."),
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for p in problems:
        print("PROBLEM:", p)
    print("roles found:", {r: p.name for r, p in found.items()})
    print("manifest: data/manifest.json")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
