#!/usr/bin/env python3
"""Verify SHA-256 checksums of all core and external GEMS datasets in .cache/gems_data/."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / ".cache" / "gems_data"

EXPECTED_SHA256 = {
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "external/h52_scarp3m_100m.tif": "b5e53d67c3a7d3d1ca44ae04ae1e84d8574857da3fcd5e34ba47276d6c04b923",
    "external/topo_10m_derived_100m_u8.tif": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
    "external/geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
    "external/geodawn_extensions_u8.tif": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
    "external/derived_sgmc_faults_100m_u8.tif": "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    "external/tiger_road_distance_m.tif": "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988",
    "external/blm_closed_claim_distance_m.tif": "a88356423c03fc8b6510a84f77cee2b1d38c4ccbd7761bc95c1ca8332a2e166a",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    results = {}
    for rel, exp in EXPECTED_SHA256.items():
        p = DATA_DIR / rel
        if not p.exists():
            print(f"MISSING: {p}", file=sys.stderr)
            return 1
        actual = sha256(p)
        ok = actual == exp
        results[rel] = {"sha256": actual, "expected": exp, "ok": ok}
        if not ok:
            print(f"MISMATCH on {rel}: got {actual}, expected {exp}", file=sys.stderr)
            return 1
    print(json.dumps({"all_verified": True, "files": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
