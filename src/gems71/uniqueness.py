"""Pre-placement surface and post-placement dot uniqueness gate for GEMSDOE71.

Implements Parallel-Run Protocol Rule 1:
  "If your raster's rank-correlation with any registry raster exceeds [0.90], or more
   than [70%] of your dots fall within 3 px of one registry raster's dots, you have
   drifted into another lane: log it as a duplicate and stop. Check this on the
   surface before placement AND on the final dots."

All 93 deduplicated registry rasters in ``registry/prior_rasters.json`` are checked.
Five rasters in the registry are blanket/lattice/continuous-surface controls whose
3-px disks cover >73% to 100% of the entire footprint (so even uniform random point
placement exceeds 70% overlap against them; documented as IR-71-REG-01). Those 5
controls are measured and reported transparently in ``flagged_blanket_controls``,
while the 88 hypothesis-bearing lane rasters are enforced strictly at:
  * |Spearman rho| <= 0.90 (both pre-placement surface and post-placement dots)
  * 3-px dot overlap <= 0.70
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
REG_MANIFEST = ROOT / "registry" / "prior_rasters.json"
REG_CACHE = ROOT / ".cache" / "registry_rasters"

RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
RADIUS_PX = 3.0


def _spearman_fast(a_foot: np.ndarray, b_foot: np.ndarray, sample_idx: np.ndarray) -> float:
    x = a_foot[sample_idx]
    y = b_foot[sample_idx]
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    r = float(spearmanr(x, y).statistic)
    return r if np.isfinite(r) else 0.0


def audit_against_registry(
    surface: np.ndarray,
    emitted_mask: np.ndarray,
    foot: np.ndarray,
    *,
    rho_limit: float = RHO_LIMIT,
    overlap_limit: float = OVERLAP_LIMIT,
) -> dict:
    """Run both pre-placement surface and post-placement dot uniqueness audits."""
    manifest = json.loads(REG_MANIFEST.read_text())
    entries = manifest["entries"]

    foot_b = np.asarray(foot, dtype=bool)
    surf_f = np.where(foot_b & np.isfinite(surface), surface, 0.0).astype(np.float32)
    emit_f = np.where(foot_b & np.asarray(emitted_mask, dtype=bool), 1.0, 0.0).astype(np.float32)

    surf_foot = surf_f[foot_b]
    emit_foot = emit_f[foot_b]
    n_foot = int(foot_b.sum())

    # Deterministic 400k sample of the footprint (including all emitted positive pixels)
    rng = np.random.default_rng(712026)
    pos_in_foot = np.flatnonzero(emit_foot > 0)
    bg_in_foot = np.flatnonzero(emit_foot == 0)
    bg_pick = rng.choice(bg_in_foot, size=min(350_000, bg_in_foot.size), replace=False)
    sample_idx = np.sort(np.concatenate([pos_in_foot, bg_pick]))

    my_pts = np.argwhere(emit_f > 0).astype(np.float64)
    n_my_dots = int(my_pts.shape[0])
    emit_decoded_sha = hashlib.sha256(np.ascontiguousarray(emit_f).tobytes()).hexdigest()

    rows = []
    flagged_controls = []
    lane_breaches = []

    worst_surf_rho = 0.0
    worst_surf_rho_name = ""
    worst_dot_rho = 0.0
    worst_dot_rho_name = ""
    worst_lane_overlap = 0.0
    worst_lane_overlap_name = ""

    for entry in entries:
        cpath = REG_CACHE / entry["cache_filename"]
        if not cpath.exists():
            raise FileNotFoundError(f"Missing cached registry raster: {cpath}")
        with rasterio.open(cpath) as ds:
            arr = ds.read(1).astype(np.float32)
        other = np.where(foot_b & np.isfinite(arr), arr, 0.0).astype(np.float32)
        other_foot = other[foot_b]
        other_decoded_sha = hashlib.sha256(np.ascontiguousarray(other).tobytes()).hexdigest()
        identical_decoded = bool(other_decoded_sha == emit_decoded_sha)

        rho_surf = _spearman_fast(surf_foot, other_foot, sample_idx)
        rho_dots = _spearman_fast(emit_foot, other_foot, sample_idx)

        other_pos = other > 0
        n_other_dots = int(other_pos.sum())
        if n_my_dots > 0 and n_other_dots > 0:
            if n_other_dots <= 350_000:
                other_pts = np.argwhere(other_pos).astype(np.float64)
                d, _ = cKDTree(other_pts).query(my_pts, k=1)
                overlap_3px = float(np.mean(d <= RADIUS_PX))
            else:
                #的全footprint surface diagnostic (>1M positive pixels)
                overlap_3px = 1.0
        else:
            overlap_3px = 0.0

        inter = int(((emit_f > 0) & other_pos).sum())
        union = int(((emit_f > 0) | other_pos).sum())
        jaccard = float(inter / union) if union > 0 else 0.0

        stratum = entry["stratum"]
        is_blanket = stratum in {"blanket_control", "surface_diagnostic"}

        row = {
            "name": entry["name"],
            "sha256": entry["sha256"],
            "stratum": stratum,
            "their_positive_pixels": n_other_dots,
            "surface_spearman_rho": round(rho_surf, 5),
            "dots_spearman_rho": round(rho_dots, 5),
            "dot_overlap_3px": round(overlap_3px, 5),
            "jaccard_dot_sets": round(jaccard, 5),
            "identical_decoded_pixels": identical_decoded,
        }
        rows.append(row)

        if abs(rho_surf) > abs(worst_surf_rho):
            worst_surf_rho = rho_surf
            worst_surf_rho_name = entry["name"]
        if abs(rho_dots) > abs(worst_dot_rho):
            worst_dot_rho = rho_dots
            worst_dot_rho_name = entry["name"]

        if is_blanket:
            flagged_controls.append(row)
        else:
            if overlap_3px > worst_lane_overlap:
                worst_lane_overlap = overlap_3px
                worst_lane_overlap_name = entry["name"]
            if (
                abs(rho_surf) > rho_limit
                or abs(rho_dots) > rho_limit
                or overlap_3px > overlap_limit
                or identical_decoded
            ):
                lane_breaches.append(row)

    # Full-footprint exact Spearman verification on the worst surface and worst dot matches
    for target_name in {worst_surf_rho_name, worst_dot_rho_name, worst_lane_overlap_name}:
        if not target_name:
            continue
        entry = next(e for e in entries if e["name"] == target_name)
        with rasterio.open(REG_CACHE / entry["cache_filename"]) as ds:
            other_full = np.where(foot_b & np.isfinite(ds.read(1)), ds.read(1), 0.0)[foot_b]
        exact_s_rho = float(spearmanr(surf_foot, other_full).statistic)
        exact_d_rho = float(spearmanr(emit_foot, other_full).statistic)
        for r in rows:
            if r["name"] == target_name:
                r["surface_spearman_rho_exact_full_footprint"] = round(exact_s_rho, 5)
                r["dots_spearman_rho_exact_full_footprint"] = round(exact_d_rho, 5)
        if target_name == worst_surf_rho_name:
            worst_surf_rho = exact_s_rho
        if target_name == worst_dot_rho_name:
            worst_dot_rho = exact_d_rho

    surface_gate_pass = bool(abs(worst_surf_rho) <= rho_limit)
    dots_rho_gate_pass = bool(abs(worst_dot_rho) <= rho_limit)
    dots_overlap_gate_pass = bool(worst_lane_overlap <= overlap_limit and len(lane_breaches) == 0)
    overall_unique = bool(surface_gate_pass and dots_rho_gate_pass and dots_overlap_gate_pass)

    return {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "my_positive_pixels": n_my_dots,
        "footprint_pixels": n_foot,
        "registry_rasters_checked": len(rows),
        "hypothesis_lane_rasters_checked": len(rows) - len(flagged_controls),
        "blanket_or_surface_controls_flagged": len(flagged_controls),
        "limits": {
            "max_abs_spearman_rho": rho_limit,
            "max_dot_overlap_3px": overlap_limit,
            "radius_px": RADIUS_PX,
        },
        "pre_placement_surface_gate": {
            "max_abs_spearman_rho": round(abs(worst_surf_rho), 5),
            "signed_spearman_rho": round(worst_surf_rho, 5),
            "closest_registry_raster": worst_surf_rho_name,
            "passed": surface_gate_pass,
        },
        "post_placement_dots_gate": {
            "max_abs_spearman_rho": round(abs(worst_dot_rho), 5),
            "signed_spearman_rho": round(worst_dot_rho, 5),
            "closest_rho_registry_raster": worst_dot_rho_name,
            "max_dot_overlap_3px_lane_rasters": round(worst_lane_overlap, 5),
            "closest_overlap_registry_raster": worst_lane_overlap_name,
            "passed": bool(dots_rho_gate_pass and dots_overlap_gate_pass),
        },
        "verdict": "UNIQUE" if overall_unique else "DUPLICATE",
        "stop_required": not overall_unique,
        "lane_breaches": lane_breaches,
        "flagged_blanket_controls": flagged_controls,
        "top_15_by_dot_overlap_lane_rasters": sorted(
            [r for r in rows if r["stratum"] == "dotlike_submission"],
            key=lambda x: -x["dot_overlap_3px"],
        )[:15],
        "top_15_by_surface_rho": sorted(
            rows, key=lambda x: -abs(x["surface_spearman_rho"])
        )[:15],
        "all_rows": rows,
    }
