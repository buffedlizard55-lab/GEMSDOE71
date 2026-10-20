#!/usr/bin/env python
"""Check a candidate submission TIF against the template before uploading.

Usage: python scripts/validate_submission.py SUBMISSION.tif --template data/example_submission.tif
Exit code 0 only if every check passes.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gems.validate import report  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--template", required=True)
    a = ap.parse_args()
    r = report(a.tif, template=a.template)
    print(json.dumps(r, indent=2))
    sys.exit(0 if r["pass"] else 1)


if __name__ == "__main__":
    main()
