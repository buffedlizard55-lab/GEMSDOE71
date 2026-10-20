"""Feature engineering and physical hypothesis surfaces for GEMSDOE71.

Every fold-invariant physical transform reads strictly from the cached sanitized bands in
``.cache/bands/`` (prepared by ``scripts/prepare_data.py``). Every catalogue-derived feature
(crack-tip stress concentration, relay corridor, and catalogue-flank distance collar) is
computed strictly from the ``visible_faults`` mask supplied by the caller so that withheld
holdout segments are never leaked.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.ndimage import (
    binary_closing,
    distance_transform_edt,
    gaussian_filter,
    laplace,
)
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
BANDS_DIR = ROOT / ".cache" / "bands"
EXT_DIR = ROOT / ".cache" / "external"

OFFICIAL_BAND_MAP = {
    "mag_anom": "01_mag_anom.npy",
    "rtp": "02_rtp.npy",
    "tmi_hg": "03_tmi_hg.npy",
    "geod_2ndinv": "04_geod_2ndinv.npy",
    "iso_grav_anom_slope": "05_iso_grav_anom_slope.npy",
    "tc": "06_tc.npy",
    "geod_shearrate": "07_geod_shearrate.npy",
    "geod_dilaterate": "08_geod_dilaterate.npy",
    "tmi_vg": "09_tmi_vg.npy",
    "deq_n100a15": "10_deq_n100a15.npy",
    "iso_grav_anom_vg": "11_iso_grav_anom_vg.npy",
    "det_elev": "12_det_elev.npy",
    "iso_grav_anom": "13_iso_grav_anom.npy",
    "tmi": "14_tmi.npy",
    "depth_to_base_surf": "15_depth_to_base_surf.npy",
    "ieq_n100a15": "16_ieq_n100a15.npy",
    "cond_surf": "17_cond_surf.npy",
    "iso_grav_anom_hg": "18_iso_grav_anom_hg.npy",
    "det_elev_slope": "19_det_elev_slope.npy",
}


def load_footprint() -> np.ndarray:
    return np.load(BANDS_DIR / "_footprint.npy")


def load_catalogue() -> np.ndarray:
    return np.load(BANDS_DIR / "_labels.npy")


def load_sgmc() -> np.ndarray:
    return np.load(BANDS_DIR / "_sgmc.npy")


def load_band(name: str, fill_median: bool = True) -> np.ndarray:
    """Load a sanitized float32 band from .cache/bands/."""
    fname = OFFICIAL_BAND_MAP.get(name, f"{name}.npy")
    path = BANDS_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Cached band not found: {path}. Run `python scripts/prepare_data.py`.")
    arr = np.load(path).astype(np.float32)
    if fill_median:
        finite = np.isfinite(arr)
        med = float(np.median(arr[finite])) if finite.any() else 0.0
        arr = np.where(finite, arr, med).astype(np.float32)
    return arr


def robust_zpos(arr: np.ndarray, foot: np.ndarray, clip_max: float = 6.0) -> np.ndarray:
    """Robust positive z-score normalized to [0, 1] inside ``foot`` using median and MAD."""
    vals = arr[foot & np.isfinite(arr)]
    if vals.size == 0:
        return np.zeros(arr.shape, dtype=np.float32)
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    if mad < 1e-9:
        mad = float(np.std(vals)) or 1.0
    z = np.clip((np.nan_to_num(arr, nan=med) - med) / mad, 0.0, clip_max) / clip_max
    z[~foot] = 0.0
    return z.astype(np.float32)


def hessian_ridge(arr: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Frangi/Sato-style largest negative principal curvature (ridge crest response)."""
    axx = gaussian_filter(arr, sigma=sigma, order=(0, 2), mode="nearest")
    ayy = gaussian_filter(arr, sigma=sigma, order=(2, 0), mode="nearest")
    axy = gaussian_filter(arr, sigma=sigma, order=(1, 1), mode="nearest")
    rad = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy * axy, 0.0))
    l1 = (axx + ayy) * 0.5 + rad
    l2 = (axx + ayy) * 0.5 - rad
    big = np.where(np.abs(l1) >= np.abs(l2), l1, l2)
    return np.maximum(-big, 0.0).astype(np.float32)


def structure_tensor_coherence(arr: np.ndarray, sigma_grad: float = 1.5,
                               sigma_int: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Return (coherence in [0, 1], dominant strike angle in radians) of ``arr``."""
    sm = gaussian_filter(arr, sigma=sigma_grad, mode="nearest")
    gy, gx = np.gradient(sm)
    jxx = gaussian_filter(gx * gx, sigma=sigma_int, mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma=sigma_int, mode="nearest")
    jxy = gaussian_filter(gx * gy, sigma=sigma_int, mode="nearest")
    tr = jxx + jyy + 1e-12
    diff = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    coh = np.clip(diff / tr, 0.0, 1.0).astype(np.float32)
    # Strike is perpendicular to gradient eigenvector
    grad_angle = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    strike = (grad_angle + 0.5 * np.pi) % np.pi
    return coh, strike.astype(np.float32)


def compute_gdr_geothermometer_idw(foot: np.ndarray) -> np.ndarray:
    """IDW surface of GDR 1391 spring-chemistry reservoir geothermometer temperature (>110 C).

    Uses ONLY the measured chemical geothermometer columns (geothermquartz_c,
    geothermchalc_c, geothermcat_c) and temp_c from gdr_wellspring_in_footprint.csv.
    Never reads dist_known_fault_px (which is label-derived).
    """
    csv_path = EXT_DIR / "gdr_wellspring_in_footprint.csv"
    shape = foot.shape
    if not csv_path.exists():
        return np.zeros(shape, dtype=np.float32)

    pts_rc = []
    temps = []
    with csv_path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                r = float(row.get("row", ""))
                c = float(row.get("col", ""))
            except ValueError:
                continue
            if not (0 <= r < shape[0] and 0 <= c < shape[1]):
                continue
            vals = []
            for col_name in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c", "temp_c"):
                raw = row.get(col_name, "")
                try:
                    v = float(raw)
                    if np.isfinite(v) and 20.0 <= v <= 380.0:
                        vals.append(v)
                except ValueError:
                    pass
            if vals:
                t_max = max(vals)
                if t_max >= 90.0:
                    pts_rc.append((r, c))
                    temps.append(t_max - 70.0)
    if not pts_rc:
        return np.zeros(shape, dtype=np.float32)

    pts = np.asarray(pts_rc, dtype=np.float64)
    vals = np.asarray(temps, dtype=np.float64)
    tree = cKDTree(pts)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    grid_pts = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float64)
    out_flat = np.zeros(grid_pts.shape[0], dtype=np.float32)
    step = 500_000
    k = min(6, len(pts))
    for s in range(0, grid_pts.shape[0], step):
        d, idx = tree.query(grid_pts[s:s + step], k=k)
        if d.ndim == 1:
            d = d[:, None]
            idx = idx[:, None]
        w = 1.0 / (1.0 + (d / 18.0) ** 2)
        out_flat[s:s + step] = ((w * vals[idx]).sum(axis=1) / (w.sum(axis=1) + 1e-12)).astype(np.float32)
    surf = gaussian_filter(out_flat.reshape(shape), sigma=2.5)
    return robust_zpos(surf, foot)


def compute_fold_invariant_components(foot: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the fold-invariant physical components for H71-A, H71-B, H71-C, and baselines."""
    # 1. Load required bands
    rtp = load_band("rtp")
    tmi_hg = load_band("tmi_hg")
    tmi_vg = load_band("tmi_vg")
    tc = load_band("tc")
    iso_grav_hg = load_band("iso_grav_anom_hg")
    iso_grav_vg = load_band("iso_grav_anom_vg")
    iso_grav_slope = load_band("iso_grav_anom_slope")
    depth_base = load_band("depth_to_base_surf")
    cond_surf = load_band("cond_surf")
    det_elev = load_band("det_elev")
    det_elev_slope = load_band("det_elev_slope")
    geod_2ndinv = load_band("geod_2ndinv")
    geod_shear = load_band("geod_shearrate")
    geod_dilat = load_band("geod_dilaterate")
    ieq = load_band("ieq_n100a15")
    deq = load_band("deq_n100a15")

    tmi_up150 = load_band("ext_TMI_up150")
    ext_thk = load_band("ext_ThK")
    rad_k = load_band("rad_K")
    rad_th = load_band("rad_Th")

    lidar_step = load_band("lidar_step_max", fill_median=False)
    lidar_cross = load_band("lidar_cross_max", fill_median=False)
    lidar_coh = load_band("lidar_coh100", fill_median=False)
    lidar_valid = load_band("lidar_valid", fill_median=False) > 0.5

    # --- Component 1: Upward-Continued Potential-Field Depth-Persistence (P_persist) ---
    # Gradient of 150 m upward-continued TMI vs surface tmi_hg + gravity HG + basement inflection
    gy_u150, gx_u150 = np.gradient(gaussian_filter(tmi_up150, sigma=1.5))
    grad_u150 = np.hypot(gy_u150, gx_u150)
    z_u150 = robust_zpos(grad_u150, foot)
    z_tmi_hg = robust_zpos(tmi_hg, foot)
    # Cross-altitude persistence: geometric mean rewards structures present at surface AND +150m
    mag_persist = np.sqrt(z_u150 * z_tmi_hg)

    gy_db, gx_db = np.gradient(gaussian_filter(depth_base, sigma=1.8))
    z_db_grad = robust_zpos(np.hypot(gy_db, gx_db), foot)
    z_grav_hg = robust_zpos(iso_grav_hg, foot)
    z_grav_slope = robust_zpos(iso_grav_slope, foot)
    grav_ridge = robust_zpos(hessian_ridge(iso_grav_hg, sigma=2.0), foot)

    P_persist = (
        0.34 * mag_persist
        + 0.28 * z_grav_hg
        + 0.20 * grav_ridge
        + 0.18 * np.sqrt(z_grav_slope * z_db_grad)
    ).astype(np.float32)
    P_persist[~foot] = 0.0

    # --- Component 2: Hydrothermal Magnetite-Destruction & K-Metasomatism Conduit (H_vent) ---
    # Magnetite destruction creates a positive Laplacian trough (d2(rtp) > 0) inside low RTP
    rtp_smooth = gaussian_filter(rtp, sigma=2.0)
    mag_trough = robust_zpos(laplace(rtp_smooth), foot)
    # Electrical conductivity gradient & high-conductivity clay-cap margin
    gy_c, gx_c = np.gradient(gaussian_filter(cond_surf, sigma=1.5))
    z_cond_edge = robust_zpos(np.hypot(gy_c, gx_c), foot)
    z_cond_high = robust_zpos(cond_surf, foot)
    # Radiometric K/Th enrichment (illite/adularia alteration halo)
    k_over_th = np.clip(rad_k / (rad_th + 0.08), 0.0, 10.0)
    inv_thk = 1.0 - np.clip(ext_thk, 0.0, 1.0)
    z_k_enrich = 0.55 * robust_zpos(k_over_th, foot) + 0.45 * robust_zpos(inv_thk, foot)
    # GDR 1391 geothermometer reservoir temperature prior
    z_geotherm = compute_gdr_geothermometer_idw(foot)

    H_vent = (
        0.32 * mag_trough
        + 0.26 * (0.6 * z_cond_edge + 0.4 * z_cond_high)
        + 0.24 * z_k_enrich
        + 0.18 * z_geotherm
    ).astype(np.float32)
    H_vent[~foot] = 0.0

    # --- Component 3: Shoreline-Decoupled Multi-Scale Scarp Crest (S_scarp) ---
    # Multi-scale Hessian ridge on det_elev + det_elev_slope + 1m LiDAR scarp where valid
    ridge_s15 = robust_zpos(hessian_ridge(det_elev, sigma=1.5), foot)
    ridge_s30 = robust_zpos(hessian_ridge(det_elev, sigma=3.0), foot)
    z_slope = robust_zpos(det_elev_slope, foot)
    coh_elev, strike_elev = structure_tensor_coherence(det_elev_slope, sigma_grad=1.2, sigma_int=2.8)

    lidar_comp = np.zeros(foot.shape, dtype=np.float32)
    if lidar_valid.any():
        l_raw = (
            0.45 * np.nan_to_num(lidar_step, nan=0.0)
            + 0.35 * np.nan_to_num(lidar_cross, nan=0.0)
            + 0.20 * np.nan_to_num(lidar_coh, nan=0.0)
        )
        lidar_comp = robust_zpos(l_raw, foot & lidar_valid)

    raw_scarp = (
        0.35 * ridge_s15
        + 0.25 * ridge_s30
        + 0.22 * (z_slope * coh_elev)
        + 0.18 * np.where(lidar_valid, lidar_comp, 0.5 * (ridge_s15 + z_slope))
    )
    # Pluvial Lake Lahontan Shoreline Suppressor:
    # Low-relief basin-margin contour lines with near-zero potential-field basement support
    # are penalized by up to 45% unless backed by P_persist or H_vent.
    low_elev_basin = (det_elev < np.percentile(det_elev[foot], 35)) & (P_persist < 0.18) & (H_vent < 0.18)
    shoreline_gate = np.where(low_elev_basin, 0.55, 1.0).astype(np.float32)
    S_scarp = (raw_scarp * shoreline_gate).astype(np.float32)
    S_scarp[~foot] = 0.0

    # --- H71-B Comparator: Salem Analytic-Signal Tilt-Contact Ratio (ASTR-Tilt) ---
    # Tilt derivative zero-crossing sharpness + horizontal gradient of tilt + gravity contact ratio
    gy_tc, gx_tc = np.gradient(gaussian_filter(tc, sigma=1.5))
    z_tilt_grad = robust_zpos(np.hypot(gy_tc, gx_tc), foot)
    tc_med = float(np.median(tc[foot]))
    tc_zero_prox = np.exp(-((tc - tc_med) / 6.5) ** 2).astype(np.float32)
    grav_as = np.hypot(iso_grav_hg, iso_grav_vg) + 1e-6
    grav_contact = robust_zpos(iso_grav_hg / grav_as, foot)
    mag_as = np.hypot(tmi_hg, tmi_vg) + 1e-6
    mag_contact = robust_zpos(tmi_hg / mag_as, foot)
    H71_B_surface = (
        0.38 * (z_tilt_grad * tc_zero_prox)
        + 0.32 * grav_contact * z_grav_hg
        + 0.30 * mag_contact * z_u150
    ).astype(np.float32)
    H71_B_surface[~foot] = 0.0

    # --- H71-C Comparator: Kostrov Transtensional Strain-Rate & Microseismic Riedel (Kostrov-Riedel) ---
    kostrov_ratio = robust_zpos(geod_dilat / (geod_2ndinv + 1.0), foot)
    z_shear = robust_zpos(geod_shear, foot)
    z_2ndinv = robust_zpos(geod_2ndinv, foot)
    seismic_rate = robust_zpos(ieq / (deq + 5.0), foot)
    H71_C_surface = (
        0.35 * np.sqrt(z_shear * kostrov_ratio)
        + 0.30 * seismic_rate
        + 0.20 * z_2ndinv
        + 0.15 * S_scarp
    ).astype(np.float32)
    H71_C_surface[~foot] = 0.0

    # --- Baseline Comparator: Single-Layer Topographic Scarp Ridge ---
    Baseline_topo = (0.55 * ridge_s15 + 0.45 * z_slope).astype(np.float32)
    Baseline_topo[~foot] = 0.0

    return {
        "P_persist": P_persist,
        "H_vent": H_vent,
        "S_scarp": S_scarp,
        "H71_B_surface": H71_B_surface,
        "H71_C_surface": H71_C_surface,
        "Baseline_topo": Baseline_topo,
        "strike_elev": strike_elev,
        "z_shear": z_shear,
        "kostrov_ratio": kostrov_ratio,
        "seismic_rate": seismic_rate,
    }


def compute_visible_tip_stress(visible_faults: np.ndarray, foot: np.ndarray,
                               z_shear: np.ndarray, kostrov_ratio: np.ndarray,
                               seismic_rate: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute (K_tip, d_visible) strictly from the ``visible_faults`` mask.

    1. Finds 8-connected fault terminations (1 neighbour) and branch junctions (>=3 neighbours)
       of ``visible_faults`` (morphologically closed by 1 px to heal 1-px raster gaps).
    2. Propagates a fracture-mechanics crack-tip process-zone field (decaying as (1 + d/8)^(-0.5)
       outside the 2-px catalogue collar, peaking in the 3..18 px step-over / splay zone),
       modulated by local transtensional geodetic strain and microseismic density.
    3. Returns (K_tip, d_visible) where d_visible is the Euclidean distance transform to
       ``visible_faults``.
    """
    vis = np.asarray(visible_faults, dtype=bool) & foot
    d_vis = distance_transform_edt(~vis).astype(np.float32)

    closed = binary_closing(vis, structure=np.ones((3, 3), dtype=bool), iterations=1)
    nbrs = np.zeros(closed.shape, dtype=np.int16)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nbrs += np.roll(np.roll(closed, dr, axis=0), dc, axis=1)
    tips = closed & (nbrs == 1)
    junctions = closed & (nbrs >= 3)

    if tips.any():
        d_tip = distance_transform_edt(~tips).astype(np.float32)
        tip_field = np.power(1.0 + d_tip / 8.0, -0.65).astype(np.float32)
    else:
        tip_field = np.zeros(foot.shape, dtype=np.float32)

    if junctions.any():
        d_jnc = distance_transform_edt(~junctions).astype(np.float32)
        jnc_field = np.power(1.0 + d_jnc / 10.0, -0.65).astype(np.float32)
    else:
        jnc_field = np.zeros(foot.shape, dtype=np.float32)

    # Off-catalogue relay/splay band (peaks at 3..22 px from visible traces)
    relay_envelope = np.exp(-((d_vis - 8.5) / 14.0) ** 2).astype(np.float32)
    strain_mod = 0.50 + 0.25 * z_shear + 0.15 * kostrov_ratio + 0.10 * seismic_rate
    raw_k = (0.52 * tip_field + 0.28 * jnc_field + 0.20 * relay_envelope) * strain_mod
    K_tip = robust_zpos(raw_k, foot)
    K_tip[~foot] = 0.0
    return K_tip, d_vis


def compose_h71a_surface(comp: dict[str, np.ndarray], visible_faults: np.ndarray,
                         foot: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Compose the H71-A (DPST-HDT) continuous propensity surface in [0, 1] inside ``foot``.

    Combines:
      * P_persist (32%): Upward-continued potential-field depth-persistence
      * S_scarp   (30%): Shoreline-decoupled multi-scale scarp crest
      * H_vent    (22%): Hydrothermal magnetite-destruction & K-metasomatism conduit
      * K_tip(V)  (16%): Visible-only crack-tip & step-over process-zone stress concentration
    Plus a multiplicative synergistic boost where >=2 independent physical regimes corroborate.
    """
    K_tip, d_vis = compute_visible_tip_stress(
        visible_faults,
        foot,
        comp["z_shear"],
        comp["kostrov_ratio"],
        comp["seismic_rate"],
    )
    P = comp["P_persist"]
    S = comp["S_scarp"]
    H = comp["H_vent"]

    linear = 0.32 * P + 0.30 * S + 0.22 * H + 0.16 * K_tip
    # Multi-physics corroboration synergy: geometric conjunction across subsurface + surface + thermal
    synergy = np.sqrt(np.maximum(P * S, 0.0)) * 0.18 + np.sqrt(np.maximum(P * H, 0.0)) * 0.14 + np.sqrt(np.maximum(S * K_tip, 0.0)) * 0.12
    raw = linear + synergy
    raw[~foot] = 0.0
    vmax = float(raw[foot].max()) if foot.any() else 1.0
    surf = (raw / max(vmax, 1e-9)).astype(np.float32)
    surf[~foot] = 0.0
    return np.clip(surf, 0.0, 1.0), {"K_tip": K_tip, "d_vis": d_vis}
