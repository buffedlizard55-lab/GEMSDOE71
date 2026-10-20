#!/usr/bin/env python
"""Train on all labels, predict the study area, and write a validated GeoTIFF to submissions/.

A written file is a CANDIDATE only. Choosing one for a weekly slot is a separate step.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gems import config, pipeline, submission  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(ROOT / "data" / "numeric_features.tif"))
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.tif"))
    ap.add_argument("--template", default=str(ROOT / "data" / "example_submission.tif"))
    ap.add_argument("--name", required=True, help="3-64 chars: letters, digits, . _ -")
    ap.add_argument("--note", required=True, help="at most 140 characters")
    ap.add_argument("--holdout-json", help="optional runs/holdout_*.json to embed in the sidecar")
    ap.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    a = ap.parse_args()
    extra = {}
    if a.holdout_json:
        h = json.loads(Path(a.holdout_json).read_text())
        extra["holdout"] = {k: h[k] for k in ("label", "pooled_dti", "dti_ci95", "n_folds",
                                              "withheld_positive_px", "evaluator_version")}
    pred = pipeline.predict_full(a.features, a.labels, seed=a.seed)
    out = ROOT / "submissions" / f"{a.name}.tif"
    man = submission.write_submission(pred, a.template, out, a.name, a.note, extra=extra)
    print(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
