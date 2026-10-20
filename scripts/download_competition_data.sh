#!/usr/bin/env bash
# Restore and SHA-256 verify the competition rasters and external layers from
# the owner-pinned GitHub mirrors (registry/data_manifest.json).
# Works inside the Arena sandbox via `gh api` (only github.com / api.github.com needed).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="${GEMS_CACHE_DIR:-/tmp/gems_cache}"
mkdir -p "$CACHE_DIR/external" "$ROOT/data/bridge" "$ROOT/data/external"
ln -sfn "$CACHE_DIR" "$ROOT/.cache"

PY="${PYTHON_BIN:-/home/user/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

"$PY" - "$ROOT" "$CACHE_DIR" <<'PYEOF'
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
cache_dir = Path(sys.argv[2])
manifest = json.loads((root / "registry" / "data_manifest.json").read_text())

WANT_IDS = {
    "training_features",
    "labels",
    "existing_faults",
    "sample_submission",
    "ext_lidar_scarp_features_u8",
    "ext_geodawn_rad_u8",
    "ext_geodawn_extensions_u8",
    "ext_derived_sgmc_faults_100m_u8",
    "ext_gdr_wellspring_in_footprint",
    "ext_gdr_qfaults_traces",
    "ext_gdr_volcanic_vents_in_footprint",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gh_raw(repo: str, ref: str, path: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=fh,
            check=True,
        )


for item in manifest["files"]:
    fid = item["id"]
    if fid not in WANT_IDS:
        continue
    target = cache_dir / item["dest"]
    if target.exists() and sha256(target) == item["sha256"]:
        print(f"[ok cached] {fid:35s} -> {target.name} (sha256={item['sha256'][:12]}...)")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if "parts" in item:
            chunks = []
            for idx, part in enumerate(item["parts"]):
                cpath = cache_dir / f"_part_{fid}_{idx:03d}"
                print(f"[fetch part {idx+1}/{len(item['parts'])}] {fid} <- {part}", flush=True)
                gh_raw(item["repo"], item["ref"], part, cpath)
                chunks.append(cpath)
            with target.open("wb") as out:
                for cpath in chunks:
                    out.write(cpath.read_bytes())
            for cpath in chunks:
                cpath.unlink()
        else:
            print(f"[fetch] {fid} <- {item['repo']}:{item['path']}", flush=True)
            gh_raw(item["repo"], item["ref"], item["path"], target)
        got = sha256(target)
        if got != item["sha256"]:
            target.unlink(missing_ok=True)
            raise RuntimeError(f"SHA-256 mismatch for {fid}: expected {item['sha256']}, got {got}")
        print(f"[ok fetched] {fid:35s} -> {target.name} ({target.stat().st_size:,} bytes)")

# Mirror small core bridge files into data/bridge and data/external for template tools
for name in ("labels.tif", "existing_faults.tif", "sample_submission.tif"):
    src = cache_dir / name
    dst = root / "data" / "bridge" / name
    if not dst.exists() or sha256(dst) != sha256(src):
        shutil.copy2(src, dst)

sgmc_src = cache_dir / "external" / "derived_sgmc_faults_100m_u8.tif"
sgmc_dst = root / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
if not sgmc_dst.exists() or sha256(sgmc_dst) != sha256(sgmc_src):
    shutil.copy2(sgmc_src, sgmc_dst)

print("[DONE] All competition rasters and external layers verified by SHA-256.")
PYEOF
