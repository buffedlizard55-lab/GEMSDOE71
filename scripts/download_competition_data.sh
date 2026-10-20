#!/usr/bin/env bash
# Download the GEMS data files that the organisers link publicly (Dropbox links from the brief).
#
# Files that the brief says REQUIRE DrivenData login (labels.tif, training_features.tif,
# sample_submission.tif, 1m_DEM_links.csv) are NOT downloaded by this script. Place them in data/
# yourself; scripts/prepare_data.py will detect them.
#
# Dropbox links are used exactly as provided in the brief, with dl=1 for a direct download.
# Each download is checked: a TIFF must start with the TIFF magic bytes, not an HTML login page.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
mkdir -p data/docs

fetch() {  # fetch <url> <dest> <kind: tif|pdf|any>
  local url="$1" dest="$2" kind="$3"
  echo "-> $dest"
  if ! curl -fL --retry 3 --max-time 900 -sS -o "$dest.part" "$url"; then
    echo "   FAILED: network/HTTP error (is dropbox.com reachable from this machine?)"; rm -f "$dest.part"; return 1
  fi
  local magic; magic=$(head -c 4 "$dest.part" | od -An -tx1 | tr -d ' \n')
  case "$kind" in
    tif) case "$magic" in 49492a00|4d4d002a) ;; *) echo "   FAILED: not a TIFF (got magic $magic)"; rm -f "$dest.part"; return 1;; esac ;;
    pdf) [ "$(head -c 4 "$dest.part")" = "%PDF" ] || { echo "   FAILED: not a PDF"; rm -f "$dest.part"; return 1; } ;;
  esac
  mv "$dest.part" "$dest"
  echo "   ok ($(wc -c < "$dest") bytes)"
}

status=0
fetch 'https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=1' data/example_submission.tif tif || status=1
fetch 'https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=1' data/existing_faults.tif tif || status=1
fetch 'https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=1' data/gems-geodawn-numerical-features.tif tif || status=1
fetch 'https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=1' data/docs/GEMS_96647.pdf pdf || status=1
fetch 'https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=1' data/docs/Digital-elevation-model-links-JSON.pdf pdf || status=1

echo
echo "DrivenData login required (not attempted here). Place these in data/ manually if you have access:"
echo "  labels.tif  training_features.tif  sample_submission.tif  1m_DEM_links.csv"
echo "  https://www.drivendata.org/competitions/306/competition-doe-gems/data/"
echo
echo "Next: python scripts/prepare_data.py"
exit $status
