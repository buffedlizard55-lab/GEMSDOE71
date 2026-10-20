#!/usr/bin/env python
"""Run the hide-and-recover holdout (HOLDOUT-DTI) and write runs/holdout_<utc>.json."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gems import config, pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(ROOT / "data" / "numeric_features.tif"))
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.tif"))
    ap.add_argument("--folds", type=int, default=config.DEFAULT_FOLDS)
    ap.add_argument("--buffer-m", type=float, default=config.DEFAULT_BUFFER_M)
    ap.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    ap.add_argument("--n-boot", type=int, default=2000)
    a = ap.parse_args()
    res = pipeline.run_holdout(a.features, a.labels, n_folds=a.folds, buffer_m=a.buffer_m,
                               seed=a.seed, n_boot=a.n_boot)
    out = ROOT / "runs" / f"holdout_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in ("label", "pooled_dti", "dti_ci95", "n_folds",
                                          "withheld_positive_px", "scored_positive_px")}, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
