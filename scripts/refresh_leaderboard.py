#!/usr/bin/env python3
"""Try to refresh the public leaderboard snapshot. Fail closed.

This sandbox's shell can reach GitHub and PyPI, not drivendata.org. A failed
fetch must not overwrite docs/data/feed.json with invented rows.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "docs" / "data" / "feed.json"
URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=20) as resp:
            body = resp.read(200)
            code = resp.status
    except Exception as exc:
        print(json.dumps({
            "refreshed": False,
            "url": URL,
            "error": f"{type(exc).__name__}: {exc}",
            "feed_left_unchanged": str(FEED),
            "note": "No rows were invented. The committed snapshot remains the last successful transcription.",
        }, indent=2))
        return 1
    print(json.dumps({
        "refreshed": False,
        "http_status": code,
        "bytes_peeked": len(body),
        "note": "HTTP succeeded but this script does not parse a client-rendered leaderboard. Leaving the committed snapshot unchanged rather than guessing rows.",
    }, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
