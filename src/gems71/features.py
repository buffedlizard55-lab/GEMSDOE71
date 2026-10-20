"""Feature construction, GDR 1391 geothermal vent enrichment audit, and single-feature leakage canary for Lane H71."""
from __future__ import annotations

import csv
import gc
import io
import json
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from numpy.lib.format import open_memmap
import rasterio
from rasterio.warp import transform
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

FEATURE_SPECS: list[dict[str, str]] = [
    {"name": "det_elev", "family": "topo_100m", "source": "training_features.tif:band12", "mechanism": "Detrended regional elevation highlighting horst-graben structural relief"},
    {"name": "det_slope", "family": "topo_100m", "source": "training_features.tif:band19", "mechanism": "100 m topographic slope along range-front and intrabasin fault scarps"},
    {"name": "slope_p90", "family": "topo_10m", "source": "topo_10m_derived_100m_u8.tif:band1", "mechanism": "90th-percentile 10 m sub-grid slope capturing narrow bedrock and piedmont scarps"},
    {"name": "relief_10m", "family": "topo_10m", "source": "topo_10m_derived_100m_u8.tif:band5", "mechanism": "Local 10 m sub-grid relief within 100 m cell"},
    {"name": "grav_iso", "family": "gravity_base", "source": "training_features.tif:band13", "mechanism": "Isostatic gravity anomaly delineating dense bedrock blocks vs basin fill"},
    {"name": "grav_slope", "family": "gravity_base", "source": "training_features.tif:band5", "mechanism": "Isostatic gravity slope across basin-bounding normal fault steps"},
    {"name": "grav_hg", "family": "gravity_base", "source": "training_features.tif:band18", "mechanism": "Horizontal gravity gradient magnitude at subsurface density contacts"},
    {"name": "grav_vg", "family": "gravity_base", "source": "training_features.tif:band11", "mechanism": "Absolute vertical gravity gradient over shallow structural ledges"},
    {"name": "depth_base_inv", "family": "gravity_base", "source": "training_features.tif:band15", "mechanism": "Inverted depth-to-pre-Tertiary-basement surface marking shallow structural highs and margins"},
    {"name": "tc_abs", "family": "gravity_base", "source": "training_features.tif:band6", "mechanism": "Terrain correction magnitude tracking steep structural range fronts"},
    {"name": "tmi_hg", "family": "magnetic", "source": "training_features.tif:band3", "mechanism": "Horizontal gradient of total magnetic intensity across juxtaposed volcanic/basement blocks"},
    {"name": "crossgrad_grav_mag", "family": "h71b_crossgrad", "source": "training_features.tif:bands2,13", "mechanism": "Gallardo-Meju (2003) collinear gradient concordance of isostatic gravity and RTP magnetics"},
    {"name": "crossgrad_grav_base", "family": "h71b_crossgrad", "source": "training_features.tif:bands13,15", "mechanism": "Collinear gradient concordance of isostatic gravity and depth-to-basement detachment steps"},
    {"name": "hydro_demag_trough", "family": "h71d_hydrothermal", "source": "training_features.tif:bands2,6,9 + geodawn_extensions_u8.tif:TMI_up150", "mechanism": "Jacobsen (1987) shallow upward-continuation differential demagnetization trough (magnetite->pyrite/hematite)"},
    {"name": "rad_alteration_edge", "family": "h71d_hydrothermal", "source": "geodawn_rad_u8.tif:K,Th,TC + geodawn_extensions_u8.tif:UTh", "mechanism": "GeoDAWN potassium-to-thorium (K/Th) adularia-illite metasomatic gradient and U/Th enrichment"},
    {"name": "clay_cap_cond_edge", "family": "h71d_hydrothermal", "source": "training_features.tif:band17 + GDR1391 vents", "mechanism": "Lateral gradient of surface electrical conductivity (smectite/illite clay cap boundary)"},
    {"name": "vent_comp", "family": "h71d_hydrothermal", "source": "GDR 1391 thermal springs + geothermometers + paleo-sinter + 2m probes + volcanic vents", "mechanism": "Composite hydrothermal upflow proximity field (purely thermal/chemical/mineralogical, zero catalogue input)"},
    {"name": "vent_spring", "family": "h71d_hydrothermal", "source": "gdr_wellspring_in_footprint.csv (T>=25C & quartz/chalc>=80C)", "mechanism": "Thermal spring/well (>=25 C) and solute geothermometer (>=80 C) upflow plume kernel"},
    {"name": "vent_paleo", "family": "h71d_hydrothermal", "source": "paleo_geothermal_regional.zip (sinter/travertine/tufa)", "mechanism": "Quaternary/Tertiary siliceous sinter and travertine fault-seal deposit kernel"},
    {"name": "vent_2m", "family": "h71d_hydrothermal", "source": "2m_temperature_probe_INGENIOUS_regional_data.zip (T2m)", "mechanism": "Shallow 2 m temperature probe conductive thermal anomaly kernel across blind basin playas"},
    {"name": "transtensional_idx", "family": "h71c_strain_seis", "source": "training_features.tif:bands4,7,8,16", "mechanism": "Geodetic 2nd invariant + shear + dilatation strain rate coupled to microseismicity spatial gradient"},
    {"name": "scarp_amp_snr", "family": "lidar_scarplet", "source": "lidar_scarp_features_u8.tif:bands1,2,3 + h52_scarp3m_100m.tif:band2", "mechanism": "Multi-scale 1-3 m LiDAR scarplet step amplitude and multi-scale exceedance SNR"},
    {"name": "scarp_dipole", "family": "lidar_scarplet", "source": "lidar_scarp_features_u8.tif:bands4,5,6,7", "mechanism": "Paired crest/toe Laplacian curvature dipole weighted by synthetic/antithetic facing"},
    {"name": "scarp_facing_net", "family": "lidar_scarplet", "source": "lidar_scarp_features_u8.tif:bands6,7,8", "mechanism": "Synthetic + antithetic scarp facing minus cross-slope fluvial channel bank penalty"},
    {"name": "local_contrast_scarp", "family": "lidar_scarplet", "source": "lidar_scarp_features_u8.tif + 1.5km background filter", "mechanism": "Locally standardized scarplet contrast isolating subtle 0.2-1.0 m intrabasin scarplets on flat basin floors"},
    {"name": "topo_curv_ridge", "family": "topo_10m", "source": "topo_10m_derived_100m_u8.tif:bands1,4,6,8", "mechanism": "10 m profile curvature, slope dispersion, and hillshade lineament ridge detector"},
]


def _grad_mag(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gy, gx = np.gradient(a.astype(np.float32))
    return np.hypot(gx, gy).astype(np.float32), gx.astype(np.float32), gy.astype(np.float32)


def extract_gdr1391_geothermal_layers(data_dir: Path, fp: np.ndarray, aff: Any, crs: Any) -> dict[str, Any]:
    """Parse GDR 1391 point datasets (thermal wells/springs, paleo-sinter/travertine, 2m probes, volcanic vents)."""
    ext = data_dir / "external"
    H, W = fp.shape

    # 1. 2m temperature probes (INGENIOUS regional DBF)
    mask_2m = np.zeros((H, W), dtype=np.float32)
    n_2m_records = 0
    with zipfile.ZipFile(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip") as z:
        dbf = z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
    numrec, lenheader, lenrec = struct.unpack("<4xIHH20x", dbf[:32])
    fields = []
    pos = 32
    while dbf[pos] != 0x0D:
        name = dbf[pos : pos + 11].split(b"\x00")[0].decode("ascii", errors="ignore")
        fields.append((name, chr(dbf[pos + 11]), dbf[pos + 16]))
        pos += 32
    offset = lenheader
    for i in range(numrec):
        rec = dbf[offset + i * lenrec : offset + (i + 1) * lenrec]
        if rec[0] == 0x2A:
            continue
        p = 1
        vals = {}
        for name, _, flen in fields:
            vals[name] = rec[p : p + flen].decode("ascii", errors="ignore").strip()
            p += flen
        try:
            x, y, t2 = float(vals["UTM_E"]), float(vals["UTM_N"]), float(vals["T2m"])
            col, row = ~aff * (x, y)
            ir, ic = int(round(row)), int(round(col))
            if 0 <= ir < H and 0 <= ic < W and fp[ir, ic]:
                n_2m_records += 1
                mask_2m[ir, ic] = max(mask_2m[ir, ic], max(t2 - 15.0, 1.0))
        except Exception:
            pass

    # 2. Paleo-geothermal sinter / travertine / tufa deposits
    mask_paleo = np.zeros((H, W), dtype=np.float32)
    n_paleo_records = 0
    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as z:
        txt = z.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
        rows = list(csv.DictReader(io.StringIO(txt)))
    lons = [float(r["Long_deg_NAD83"]) for r in rows if r["Long_deg_NAD83"]]
    lats = [float(r["Lat_deg_NAD83"]) for r in rows if r["Lat_deg_NAD83"]]
    xs, ys_u = transform("EPSG:4269", crs, lons, lats)
    for x, y in zip(xs, ys_u):
        col, row = ~aff * (x, y)
        ir, ic = int(round(row)), int(round(col))
        if 0 <= ir < H and 0 <= ic < W and fp[ir, ic]:
            n_paleo_records += 1
            mask_paleo[ir, ic] = 1.0

    # 3. Thermal springs/wells (>=25C) and quartz/chalcedony geothermometers (>=80C)
    mask_spring = np.zeros((H, W), dtype=np.float32)
    mask_geotherm = np.zeros((H, W), dtype=np.float32)
    n_spring_records = 0
    n_geotherm_records = 0
    with open(ext / "gdr_wellspring_in_footprint.csv") as f:
        for r in csv.DictReader(f):
            try:
                ir, ic = int(float(r["row"])), int(float(r["col"]))
                if 0 <= ir < H and 0 <= ic < W and fp[ir, ic]:
                    tc_v = float(r["temp_c"]) if r["temp_c"] else 0.0
                    gq = float(r["geothermquartz_c"]) if r["geothermquartz_c"] else 0.0
                    gc_v = float(r["geothermchalc_c"]) if r["geothermchalc_c"] else 0.0
                    if tc_v >= 25.0:
                        n_spring_records += 1
                        mask_spring[ir, ic] = max(mask_spring[ir, ic], min((tc_v - 20.0) / 80.0, 2.0))
                    if max(gq, gc_v) >= 80.0:
                        n_geotherm_records += 1
                        mask_geotherm[ir, ic] = max(mask_geotherm[ir, ic], min((max(gq, gc_v) - 60.0) / 140.0, 2.0))
            except Exception:
                pass

    # 4. Quaternary volcanic vents
    mask_volc = np.zeros((H, W), dtype=np.float32)
    n_volc_records = 0
    with open(ext / "gdr_volcanic_vents_in_footprint.csv") as f:
        for r in csv.DictReader(f):
            try:
                ir, ic = int(float(r["row"])), int(float(r["col"]))
                if 0 <= ir < H and 0 <= ic < W and fp[ir, ic]:
                    n_volc_records += 1
                    mask_volc[ir, ic] = 1.0
            except Exception:
                pass

    d_2m = ndi.distance_transform_edt(mask_2m == 0).astype(np.float32)
    d_paleo = ndi.distance_transform_edt(mask_paleo == 0).astype(np.float32)
    d_spring = ndi.distance_transform_edt(mask_spring == 0).astype(np.float32)
    d_geoth = ndi.distance_transform_edt(mask_geotherm == 0).astype(np.float32)
    d_volc = ndi.distance_transform_edt(mask_volc == 0).astype(np.float32)

    vent_2m = np.exp(-d_2m / 25.0).astype(np.float32)
    vent_paleo = np.exp(-d_paleo / 30.0).astype(np.float32)
    vent_spring = (0.6 * np.exp(-d_spring / 25.0) + 0.4 * np.exp(-d_geoth / 30.0)).astype(np.float32)
    vent_comp = (0.40 * vent_spring + 0.30 * vent_paleo + 0.20 * vent_2m + 0.10 * np.exp(-d_volc / 40.0)).astype(np.float32)
    vent_corridor = fp & ((d_spring <= 80.0) | (d_paleo <= 80.0) | (d_2m <= 80.0))

    stats = {
        "n_2m_probe_stations_in_footprint": int(n_2m_records),
        "n_2m_probe_unique_cells": int((mask_2m > 0).sum()),
        "n_paleo_sinter_travertine_in_footprint": int(n_paleo_records),
        "n_paleo_unique_cells": int((mask_paleo > 0).sum()),
        "n_thermal_wells_springs_ge25C_records": int(n_spring_records),
        "n_thermal_wells_springs_unique_cells": int((mask_spring > 0).sum()),
        "n_geothermometer_ge80C_records": int(n_geotherm_records),
        "n_geothermometer_unique_cells": int((mask_geotherm > 0).sum()),
        "n_volcanic_vents_in_footprint": int(n_volc_records),
        "n_vent_corridor_8km_pixels": int(vent_corridor.sum()),
        "vent_corridor_8km_fraction": float(vent_corridor.sum() / fp.sum()),
    }
    return {
        "vent_comp": vent_comp,
        "vent_spring": vent_spring,
        "vent_paleo": vent_paleo,
        "vent_2m": vent_2m,
        "vent_corridor": vent_corridor,
        "stats": stats,
    }


def ensure_feature_cache(data_dir: Path) -> tuple[np.ndarray, dict[str, np.ndarray], list[str], dict[str, Any]]:
    """Load or build the 26-feature rank-normalized cache on valid footprint pixels."""
    npy_path = data_dir / "h71_X_fp.npy"
    masks_path = data_dir / "h71_masks.npz"
    names_path = data_dir / "h71_feature_names.json"
    vent_stats_path = data_dir / "h71_vent_stats.json"

    with rasterio.open(data_dir / "sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
        aff = ds.transform
        crs = ds.crs
        H, W = ds.height, ds.width

    if npy_path.exists() and masks_path.exists() and names_path.exists():
        X_fp = np.load(npy_path, mmap_mode="r")
        masks_npz = np.load(masks_path)
        masks = {k: masks_npz[k] for k in masks_npz.files}
        fnames = json.loads(names_path.read_text())
        if vent_stats_path.exists():
            vent_stats = json.loads(vent_stats_path.read_text())
        else:
            gdr = extract_gdr1391_geothermal_layers(data_dir, fp, aff, crs)
            vent_stats = gdr["stats"]
            vent_stats_path.write_text(json.dumps(vent_stats, indent=2))
        return X_fp, masks, fnames, vent_stats

    ext = data_dir / "external"
    n_fp = int(fp.sum())
    feature_names = [s["name"] for s in FEATURE_SPECS]
    X_fp = open_memmap(npy_path, mode="w+", dtype=np.float32, shape=(n_fp, len(feature_names)))

    def write_col(idx: int, arr: np.ndarray) -> None:
        v = arr[fp]
        r = rankdata(v, method="average").astype(np.float32)
        X_fp[:, idx] = (r - 1.0) / max(len(r) - 1.0, 1.0)

    gdr = extract_gdr1391_geothermal_layers(data_dir, fp, aff, crs)
    vent_comp = gdr["vent_comp"]
    vent_corridor = gdr["vent_corridor"]
    vent_stats = gdr["stats"]
    vent_stats_path.write_text(json.dumps(vent_stats, indent=2))

    write_col(16, vent_comp)
    write_col(17, gdr["vent_spring"])
    write_col(18, gdr["vent_paleo"])
    write_col(19, gdr["vent_2m"])
    del gdr
    gc.collect()

    with rasterio.open(data_dir / "training_features.tif") as ds:
        def rband(b: int) -> np.ndarray:
            a = ds.read(b).astype(np.float32)
            a[~np.isfinite(a) | (a < -1e30)] = 0.0
            return a

        det_elev = rband(12)
        det_slope = rband(19)
        write_col(0, det_elev); del det_elev
        write_col(1, det_slope); del det_slope

        grav_iso = rband(13)
        grav_slope = rband(5)
        grav_hg = rband(18)
        grav_vg = rband(11)
        depth_base = rband(15)
        write_col(4, grav_iso)
        write_col(5, -grav_slope); del grav_slope
        write_col(6, grav_hg); del grav_hg
        write_col(7, np.abs(grav_vg)); del grav_vg
        write_col(8, -depth_base)

        rtp = rband(2)
        gm_g, gx_g, gy_g = _grad_mag(grav_iso); del grav_iso
        gm_m, gx_m, gy_m = _grad_mag(rtp)
        gm_b, gx_b, gy_b = _grad_mag(depth_base); del depth_base
        dot_gm = (gx_g * gx_m + gy_g * gy_m) / (gm_g * gm_m + 1e-6)
        write_col(11, (np.sqrt(gm_g * gm_m) * (dot_gm * dot_gm)).astype(np.float32))
        del gm_m, gx_m, gy_m, dot_gm
        dot_gb = (gx_g * gx_b + gy_g * gy_b) / (gm_g * gm_b + 1e-6)
        write_col(12, (np.sqrt(gm_g * gm_b) * (dot_gb * dot_gb)).astype(np.float32))
        del gm_g, gx_g, gy_g, gm_b, gx_b, gy_b, dot_gb
        gc.collect()

        tc = rband(6)
        tmi_hg = rband(3)
        tmi_vg = rband(9)
        cond_surf = rband(17)
        write_col(9, -tc)
        write_col(10, tmi_hg); del tmi_hg

        with rasterio.open(ext / "geodawn_extensions_u8.tif") as eds:
            ext_UTh = eds.read(3).astype(np.float32) / 255.0
            tmi_up150 = eds.read(4).astype(np.float32) / 255.0

        rtp_z = (rtp - np.mean(rtp[fp])) / (np.std(rtp[fp]) + 1e-6); del rtp
        up150_z = (tmi_up150 - np.mean(tmi_up150[fp])) / (np.std(tmi_up150[fp]) + 1e-6); del tmi_up150
        hydro_demag = (
            np.abs(rtp_z - up150_z) * (np.abs(tc) / (np.std(tc[fp]) + 1e-6))
            + np.maximum(-tmi_vg / (np.std(tmi_vg[fp]) + 1e-6), 0.0)
        ).astype(np.float32)
        write_col(13, hydro_demag); del rtp_z, up150_z, tc, tmi_vg, hydro_demag

        gm_c, _, _ = _grad_mag(cond_surf); del cond_surf
        write_col(15, (gm_c * (1.0 + vent_comp)).astype(np.float32)); del gm_c, vent_comp
        gc.collect()

        geod_2nd = rband(4)
        geod_shear = rband(7)
        geod_dil = rband(8)
        ieq = rband(16)
        gm_eq, _, _ = _grad_mag(ieq); del ieq
        transtens = (
            (geod_2nd / (np.std(geod_2nd[fp]) + 1e-6))
            + (geod_shear / (np.std(geod_shear[fp]) + 1e-6))
            + 0.5 * (geod_dil / (np.std(geod_dil[fp]) + 1e-6))
            + (gm_eq / (np.std(gm_eq[fp]) + 1e-6))
        ).astype(np.float32)
        write_col(20, transtens); del geod_2nd, geod_shear, geod_dil, gm_eq, transtens
        gc.collect()

    with rasterio.open(ext / "geodawn_rad_u8.tif") as ds:
        rad_K = ds.read(1).astype(np.float32) / 255.0
        rad_Th = ds.read(2).astype(np.float32) / 255.0
        rad_TC = ds.read(4).astype(np.float32) / 255.0
    k_th_ratio = rad_K / (rad_Th + 0.05); del rad_K, rad_Th
    gm_kth, _, _ = _grad_mag(k_th_ratio); del k_th_ratio
    write_col(14, (0.5 * gm_kth + 0.3 * ext_UTh + 0.2 * (1.0 - rad_TC)).astype(np.float32))
    del gm_kth, ext_UTh, rad_TC
    gc.collect()

    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        slope_p90 = ds.read(1).astype(np.float32) / 255.0
        slope_std = ds.read(4).astype(np.float32) / 255.0
        relief_10m = ds.read(5).astype(np.float32) / 255.0
        curv_10m = ds.read(6).astype(np.float32) / 255.0
        hs_lin = ds.read(8).astype(np.float32) / 255.0
    write_col(2, slope_p90)
    write_col(3, relief_10m)
    write_col(25, (0.35 * slope_p90 + 0.25 * slope_std + 0.20 * curv_10m + 0.20 * hs_lin).astype(np.float32))
    relief_10m_fp = relief_10m[fp].copy()
    del slope_p90, slope_std, relief_10m, curv_10m, hs_lin
    gc.collect()

    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        ex_max = ds.read(1).astype(np.float32) / 255.0
        ex_mean = ds.read(2).astype(np.float32) / 255.0
        step_max = ds.read(3).astype(np.float32) / 255.0
        lapneg = ds.read(4).astype(np.float32) / 255.0
        lappos = ds.read(5).astype(np.float32) / 255.0
        downface = ds.read(6).astype(np.float32) / 255.0
        upface = ds.read(7).astype(np.float32) / 255.0
        cross_max = ds.read(8).astype(np.float32) / 255.0
    with rasterio.open(ext / "h52_scarp3m_100m.tif") as ds:
        r3 = ds.read(2)
        h_gate12 = np.where(r3 != -32768, r3.astype(np.float32) / 100.0, 0.0); del r3

    scarp_amp_snr = (0.5 * step_max * np.sqrt(ex_max * ex_mean + 1e-6) + 0.5 * np.abs(h_gate12)).astype(np.float32)
    del ex_max, ex_mean, step_max, h_gate12
    scarp_dipole = (np.sqrt(lapneg * lappos) * (upface + downface)).astype(np.float32)
    del lapneg, lappos
    scarp_facing_net = np.maximum(downface + upface - 0.5 * cross_max, 0.0).astype(np.float32)
    del downface, upface, cross_max
    write_col(21, scarp_amp_snr)
    write_col(22, scarp_dipole)
    write_col(23, scarp_facing_net); del scarp_facing_net

    comb_scarp = scarp_amp_snr + scarp_dipole; del scarp_amp_snr, scarp_dipole
    bg_scarp = ndi.uniform_filter(comb_scarp, size=15)
    write_col(24, (comb_scarp / (bg_scarp + 0.02)).astype(np.float32))
    del comb_scarp, bg_scarp
    gc.collect()

    with rasterio.open(ext / "tiger_road_distance_m.tif") as ds:
        d_road = ds.read(1).astype(np.float32)
    with rasterio.open(ext / "blm_closed_claim_distance_m.tif") as ds:
        d_claim = ds.read(1).astype(np.float32)
    cult_mask = fp & ((d_road < 75.0) | (d_claim < 60.0))
    del d_road, d_claim

    X_fp.flush()
    np.savez_compressed(
        masks_path,
        cult_mask_fp=cult_mask[fp],
        vent_corridor_fp=vent_corridor[fp],
        relief_10m_fp=relief_10m_fp,
    )
    names_path.write_text(json.dumps(feature_names, indent=2))

    X_fp_ro = np.load(npy_path, mmap_mode="r")
    masks_npz = np.load(masks_path)
    masks = {k: masks_npz[k] for k in masks_npz.files}
    return X_fp_ro, masks, feature_names, vent_stats


def run_leakage_canary(
    X_fp: np.ndarray,
    feature_names: list[str],
    fp: np.ndarray,
    folds20: list[dict[str, Any]],
    sgmc_off: np.ndarray,
    d_cat: np.ndarray,
    relay_oof_2d: np.ndarray,
    seed: int = 71,
) -> dict[str, Any]:
    """Evaluate every single feature alone on holdout and SGMC off-catalogue faults.

    Rule 4: Before trusting any result, test each feature alone on holdout.
    A single feature with AUC > 0.90 is leakage until proven otherwise.
    """
    H, W = fp.shape
    fp_idx_map = np.full((H, W), -1, dtype=np.int32)
    fp_idx_map[fp] = np.arange(int(fp.sum()), dtype=np.int32)

    truth_all = np.zeros(int(fp.sum()), dtype=bool)
    eval_all = np.zeros(int(fp.sum()), dtype=bool)
    for f in folds20:
        t_idx = fp_idx_map[f["truth"] & fp & f["region"] & (~f["masked_known"])]
        e_idx = fp_idx_map[fp & f["region"] & (~f["masked_known"])]
        truth_all[t_idx] = True
        eval_all[e_idx] = True

    rng = np.random.default_rng(seed)
    pos_h = np.flatnonzero(truth_all & eval_all)
    neg_h = np.flatnonzero((~truth_all) & eval_all)
    sub_h = np.concatenate([pos_h, rng.choice(neg_h, size=60000, replace=False)])
    yh = truth_all[sub_h]

    sgmc_fp = sgmc_off[fp]
    dcat_fp = d_cat[fp]
    pos_s = np.flatnonzero(sgmc_fp)
    neg_s = np.flatnonzero((dcat_fp > 3.0) & (~sgmc_fp))
    sub_s = np.concatenate([rng.choice(pos_s, size=25000, replace=False), rng.choice(neg_s, size=60000, replace=False)])
    ys = sgmc_fp[sub_s]

    spec_map = {s["name"]: s for s in FEATURE_SPECS}
    rows = []
    for j, name in enumerate(feature_names):
        auc_h = float(roc_auc_score(yh, X_fp[sub_h, j]))
        auc_s = float(roc_auc_score(ys, X_fp[sub_s, j]))
        dir_h = max(auc_h, 1.0 - auc_h)
        dir_s = max(auc_s, 1.0 - auc_s)
        spec = spec_map.get(name, {})
        rows.append(
            {
                "feature_index": j,
                "feature_name": name,
                "family": spec.get("family", "engineered"),
                "source": spec.get("source", ""),
                "mechanism": spec.get("mechanism", ""),
                "holdout_auc_raw": round(auc_h, 6),
                "holdout_auc_directional": round(dir_h, 6),
                "sgmc_off_catalogue_auc_raw": round(auc_s, 6),
                "sgmc_off_catalogue_auc_directional": round(dir_s, 6),
                "uses_catalogue": False,
                "canary_pass": bool(dir_h <= 0.90 and dir_s <= 0.90),
            }
        )

    # Also test the fold-proper visible-catalogue damage-zone relay prior (Rule 2 + Rule 4)
    relay_fp = relay_oof_2d[fp]
    auc_r_h = float(roc_auc_score(yh, relay_fp[sub_h]))
    auc_r_s = float(roc_auc_score(ys, relay_fp[sub_s]))
    dir_r_h = max(auc_r_h, 1.0 - auc_r_h)
    dir_r_s = max(auc_r_s, 1.0 - auc_r_s)
    rows.append(
        {
            "feature_index": len(feature_names),
            "feature_name": "vis_relay_hydro_prior",
            "family": "h71a_fold_proper_relay",
            "source": "fold['visible'] EDT (d_vis > 2 px) * hydro_gate (strictly fold-isolated)",
            "mechanism": "Hydrothermal-gated damage-zone relay continuation derived strictly from remaining visible faults per fold",
            "holdout_auc_raw": round(auc_r_h, 6),
            "holdout_auc_directional": round(dir_r_h, 6),
            "sgmc_off_catalogue_auc_raw": round(auc_r_s, 6),
            "sgmc_off_catalogue_auc_directional": round(dir_r_s, 6),
            "uses_catalogue": True,
            "derived_strictly_from_visible_faults_only": True,
            "canary_pass": bool(dir_r_h <= 0.90 and dir_r_s <= 0.90),
        }
    )

    max_phys_auc = max(r["holdout_auc_directional"] for r in rows if not r["uses_catalogue"])
    max_all_auc = max(r["holdout_auc_directional"] for r in rows)
    max_sgmc_auc = max(r["sgmc_off_catalogue_auc_directional"] for r in rows)
    all_pass = all(r["canary_pass"] for r in rows)
    if not all_pass:
        raise RuntimeError("Leakage canary failed: at least one feature exceeded AUC 0.90")

    return {
        "canary_threshold_auc": 0.90,
        "n_features_tested": len(rows),
        "n_physical_non_catalogue_features": len(feature_names),
        "n_fold_isolated_visible_relay_features": 1,
        "max_physical_holdout_auc_directional": round(max_phys_auc, 6),
        "max_overall_holdout_auc_directional": round(max_all_auc, 6),
        "max_sgmc_off_catalogue_auc_directional": round(max_sgmc_auc, 6),
        "all_features_pass": all_pass,
        "features": rows,
    }
