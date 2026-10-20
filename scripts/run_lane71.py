#!/usr/bin/env python3
"""CLI entrypoint for GEMSDOE71 Lane H71 3-experiment pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from gems71.pipeline import run_all  # noqa: E402


def main() -> int:
    card = run_all(REPO_ROOT)
    print(json.dumps(card, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
