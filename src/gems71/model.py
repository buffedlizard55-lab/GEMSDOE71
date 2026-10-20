"""Model synthesis, ablations, deterministic NMS dot emitter, and multi-domain holdout evaluation for Lane H71."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage as ndi

from gems57 import evaluate_holdout as EH57
from gems57 import metric as M57


def emit_thinned(surf2d: np.ndarray, domain: np.ndarray, k_dots: int, nms_size: int = 3) -> np.ndarray:
    """Emit crisp {0.0, 1.0} dots at 2D non-maximum-suppressed local peaks within domain."""
    yy, xx = np.indices(surf2d.shape, dtype=np.float32)
    s_pert = np.where(domain, surf2d + 1e-7 * ((yy * 0.6180339 + xx * 0.4142135) % 1.0), -1.0)
    lmax = ndi.maximum_filter(s_pert, size=nms_size)
    peaks = domain & (s_pert == lmax) & (s_pert > 0)
    vals = s_pert[peaks]
    out = np.zeros_like(surf2d, dtype=np.float32)
    if len(vals) == 0:
        return out
    if len(vals) <= k_dots:
        out[peaks] = 1.0
    else:
        thr = np.partition(vals, len(vals) - k_dots)[len(vals) - k_dots]
        out[peaks & (s_pert >= thr)] = 1.0
    return out


def build_physical_surfaces(
    X_fp: np.ndarray,
    feature_names: list[str],
    cult_fp: np.ndarray,
    fp: np.ndarray,
    seed: int = 71,
) -> dict[str, np.ndarray]:
    """Construct 2D physical score surfaces for H71-A and all ablation/baseline arms."""
    H, W = fp.shape
    idx = {n: i for i, n in enumerate(feature_names)}

    def get_col(name: str) -> np.ndarray:
        return X_fp[:, idx[name]].astype(np.float32)

    def to_2d(v_fp: np.ndarray) -> np.ndarray:
        out = np.zeros((H, W), dtype=np.float32)
        out[fp] = v_fp
        return out

    # 1. Baseline 100 m topogeophys (only 100 m training_features topo & gravity/magnetic bands)
    score_base100 = (
        0.30 * get_col("det_slope")
        + 0.20 * get_col("det_elev")
        + 0.20 * get_col("grav_iso")
        + 0.15 * get_col("grav_slope")
        + 0.15 * get_col("tmi_hg")
    )

    # 2. H71-B ablation: Gallardo-Meju cross-gradient structural concordance
    score_h71b = (
        0.35 * get_col("crossgrad_grav_base")
        + 0.25 * get_col("crossgrad_grav_mag")
        + 0.20 * get_col("depth_base_inv")
        + 0.10 * get_col("grav_iso")
        + 0.10 * get_col("tc_abs")
    )

    # 3. H71-C ablation: Crustal strain-rate dilatation/shear + seismicity + 10 m topo
    score_h71c = (
        0.45 * get_col("transtensional_idx")
        + 0.30 * get_col("topo_curv_ridge")
        + 0.25 * get_col("slope_p90")
    )

    # 4. H71-D ablation: Hydrothermal demagnetization + K/Th alteration + GDR 1391 vents
    score_h71d = (
        0.25 * get_col("hydro_demag_trough")
        + 0.20 * get_col("rad_alteration_edge")
        + 0.15 * get_col("clay_cap_cond_edge")
        + 0.15 * get_col("vent_comp")
        + 0.15 * get_col("vent_paleo")
        + 0.10 * get_col("vent_2m")
    )

    # 5. H71-A physical core: Hydrothermal-Structural Conduit & Alteration-Demagnetization Convergence
    hydro_gate = (
        0.25 * get_col("vent_comp")
        + 0.25 * get_col("hydro_demag_trough")
        + 0.25 * get_col("rad_alteration_edge")
        + 0.15 * get_col("clay_cap_cond_edge")
        + 0.10 * get_col("vent_paleo")
    )
    struct_conduit = (
        0.15 * get_col("scarp_dipole")
        + 0.15 * get_col("scarp_facing_net")
        + 0.19 * get_col("topo_curv_ridge")
        + 0.15 * get_col("slope_p90")
        + 0.11 * get_col("det_slope")
        + 0.08 * get_col("depth_base_inv")
        + 0.04 * get_col("tc_abs")
        + 0.08 * get_col("crossgrad_grav_base")
        + 0.05 * get_col("transtensional_idx")
    )
    score_h71a_phys = (
        struct_conduit * (1.0 + 0.40 * hydro_gate)
        + 0.10 * hydro_gate * get_col("transtensional_idx")
    ) * np.where(cult_fp, 0.35, 1.0)

    rng = np.random.default_rng(seed)
    score_rand = rng.random(int(fp.sum()), dtype=np.float32)

    return {
        "random_control": to_2d(score_rand),
        "baseline_100m_topogeophys": to_2d(score_base100),
        "h71b_crossgrad_ablation": to_2d(score_h71b),
        "h71c_strain_seis_ablation": to_2d(score_h71c),
        "h71d_hydro_alteration_ablation": to_2d(score_h71d),
        "h71a_phys_only_ablation": to_2d(score_h71a_phys),
        "hydro_gate_2d": to_2d(hydro_gate),
    }


def compute_relay_prior(d_ref: np.ndarray, hydro_2d: np.ndarray) -> np.ndarray:
    """Compute hydrothermal-gated damage-zone relay prior strictly from visible-fault distance d_ref."""
    return (np.where(d_ref > 2.0, np.exp(-(d_ref - 2.0) / 18.0), 0.0) * (0.5 + 0.5 * hydro_2d)).astype(np.float32)


def run_holdout_and_sgmc_experiments(
    surfaces: dict[str, np.ndarray],
    fp: np.ndarray,
    cat: np.ndarray,
    d_cat: np.ndarray,
    sgmc_off: np.ndarray,
    vent_corridor_fp: np.ndarray,
    relief_10m_fp: np.ndarray,
    folds20: list[dict[str, Any]],
    h33_champion: np.ndarray,
    w_relay: float = 0.28,
    k_fold: int = 10500,
    k_sub: int = 38800,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    """Run 4-quadrant spatially blocked hide-and-recover evaluation + SGMC off-catalogue benchmark."""
    H, W = fp.shape
    phys_h71a_2d = surfaces["h71a_phys_only_ablation"]
    hydro_2d = surfaces["hydro_gate_2d"]
    arm_names = [
        "random_control",
        "baseline_100m_topogeophys",
        "h71b_crossgrad_ablation",
        "h71c_strain_seis_ablation",
        "h71d_hydro_alteration_ablation",
        "h71a_phys_only_ablation",
        "h71a_full_conduit_synthesis",
        "h33_2_b2_champion",
    ]

    # Secondary sub-domain masks:
    # (a) Off-range-front intrabasin & piedmont floor (relief_10m <= 75th percentile of footprint)
    off_rf_2d = np.zeros((H, W), dtype=bool)
    off_rf_2d[fp] = relief_10m_fp <= float(np.quantile(relief_10m_fp, 0.75))
    # (b) Geothermal vent & paleo-sinter upflow corridor (within 8 km of GDR 1391 thermal features)
    vent_dom_2d = np.zeros((H, W), dtype=bool)
    vent_dom_2d[fp] = vent_corridor_fp

    terms_full = {k: None for k in arm_names}
    terms_off_rf = {k: None for k in arm_names}
    terms_vent = {k: None for k in arm_names}
    per_fold_details: dict[str, dict[str, Any]] = {k: {} for k in arm_names}
    relay_oof_2d = np.zeros((H, W), dtype=np.float32)

    for f in folds20:
        fname = f["fold"]
        d_vis = ndi.distance_transform_edt(~f["visible"]).astype(np.float32)
        dom_emit = fp & f["region"] & (~f["masked_known"]) & (d_vis > 2.0)
        relay_prior = compute_relay_prior(d_vis, hydro_2d)
        relay_oof_2d[fp & f["region"] & (~f["masked_known"])] = relay_prior[fp & f["region"] & (~f["masked_known"])]

        s_h71a_fold = phys_h71a_2d * (1.0 + w_relay * relay_prior)
        preds_fold = {}
        for k in arm_names:
            if k == "h71a_full_conduit_synthesis":
                preds_fold[k] = emit_thinned(s_h71a_fold, dom_emit, k_fold, nms_size=3)
            elif k == "h33_2_b2_champion":
                preds_fold[k] = h33_champion
            else:
                preds_fold[k] = emit_thinned(surfaces[k], dom_emit, k_fold, nms_size=3)

            res_f, t_f = EH57.evaluate(preds_fold[k], f, fp)
            terms_full[k] = t_f if terms_full[k] is None else (terms_full[k] + t_f)
            per_fold_details[k][fname] = {
                "dti": round(float(res_f["dti"]), 6),
                "tpw": round(float(res_f["tpw"]), 3),
                "fpw": round(float(res_f["fpw"]), 3),
                "fnw": round(float(res_f["fnw"]), 3),
                "n_truth": int(res_f["n_truth"]),
                "n_emitted": int(res_f["n_emitted"]),
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": EH57.VERSION,
            }

            _, t_rf = EH57.evaluate(preds_fold[k], f, off_rf_2d)
            terms_off_rf[k] = t_rf if terms_off_rf[k] is None else (terms_off_rf[k] + t_rf)

            _, t_vt = EH57.evaluate(preds_fold[k], f, vent_dom_2d)
            terms_vent[k] = t_vt if terms_vent[k] is None else (terms_vent[k] + t_vt)

    summary_full = EH57.pooled_summary(terms_full, draws=1000, seed=520810, candidate="h71a_full_conduit_synthesis")
    summary_off_rf = EH57.pooled_summary(terms_off_rf, draws=1000, seed=520810, candidate="h71a_full_conduit_synthesis")
    summary_vent = EH57.pooled_summary(terms_vent, draws=1000, seed=520810, candidate="h71a_full_conduit_synthesis")

    # Build final submission surface & dots on full footprint (d_cat > 2.0 collar)
    relay_sub = compute_relay_prior(d_cat, hydro_2d)
    s_sub_raw = phys_h71a_2d * (1.0 + w_relay * relay_sub)
    s_sub_norm = np.zeros((H, W), dtype=np.float32)
    v_fp = s_sub_raw[fp]
    s_sub_norm[fp] = np.clip((v_fp - v_fp.min()) / (v_fp.max() - v_fp.min() + 1e-12), 0.0, 1.0)
    pred_sub = emit_thinned(s_sub_norm, fp & (d_cat > 2.0), k_sub, nms_size=3)

    # Off-catalogue USGS SGMC fault evaluation (n_pos = 62,122 off-catalogue fault pixels > 300 m from catalogue)
    sgmc_valid = fp & (~cat)
    sgmc_results = {}
    for k in arm_names:
        if k == "h71a_full_conduit_synthesis":
            p_eval_38800 = pred_sub
            p_eval_37654 = emit_thinned(s_sub_norm, fp & (d_cat > 2.0), 37654, nms_size=3)
            r38 = M57.dti_exact(p_eval_38800, sgmc_off, valid=sgmc_valid)
            r37 = M57.dti_exact(p_eval_37654, sgmc_off, valid=sgmc_valid)
            sgmc_results[k] = {
                "dti_at_k38800": round(float(r38["dti"]), 6),
                "dti_at_k37654_equal_budget": round(float(r37["dti"]), 6),
                "tpw": round(float(r38["tp"]), 3),
                "fpw": round(float(r38["fp"]), 3),
                "fnw": round(float(r38["fn"]), 3),
                "n_truth": int(r38["n_truth"]),
                "n_emitted": int((p_eval_38800 > 0).sum()),
                "evidence_class": "HOLDOUT-DTI (USGS-SGMC-OFF-CATALOGUE-DIAGNOSTIC)",
            }
        elif k == "h33_2_b2_champion":
            rh = M57.dti_exact(h33_champion, sgmc_off, valid=sgmc_valid)
            sgmc_results[k] = {
                "dti_at_k38800": round(float(rh["dti"]), 6),
                "dti_at_k37654_equal_budget": round(float(rh["dti"]), 6),
                "tpw": round(float(rh["tp"]), 3),
                "fpw": round(float(rh["fp"]), 3),
                "fnw": round(float(rh["fn"]), 3),
                "n_truth": int(rh["n_truth"]),
                "n_emitted": int((h33_champion > 0).sum()),
                "evidence_class": "HOLDOUT-DTI (USGS-SGMC-OFF-CATALOGUE-DIAGNOSTIC)",
            }
        else:
            p_arm = emit_thinned(surfaces[k], fp & (d_cat > 2.0), k_sub, nms_size=3)
            ra = M57.dti_exact(p_arm, sgmc_off, valid=sgmc_valid)
            sgmc_results[k] = {
                "dti_at_k38800": round(float(ra["dti"]), 6),
                "tpw": round(float(ra["tp"]), 3),
                "fpw": round(float(ra["fp"]), 3),
                "fnw": round(float(ra["fn"]), 3),
                "n_truth": int(ra["n_truth"]),
                "n_emitted": int((p_arm > 0).sum()),
                "evidence_class": "HOLDOUT-DTI (USGS-SGMC-OFF-CATALOGUE-DIAGNOSTIC)",
            }

    experiment_summary = {
        "evaluator_version": EH57.VERSION,
        "evidence_class": "HOLDOUT-DTI",
        "holdout_instrument": "4-quadrant spatially blocked buffered component draw (seed=20, hide_frac=0.20, buffer_px=3)",
        "withheld_positive_pixels_full_domain": int(summary_full["scores"]["h71a_full_conduit_synthesis"]["withheld_positive_pixels"]),
        "withheld_positive_pixels_off_range_front_domain": int(summary_off_rf["scores"]["h71a_full_conduit_synthesis"]["withheld_positive_pixels"]),
        "withheld_positive_pixels_geothermal_vent_domain": int(summary_vent["scores"]["h71a_full_conduit_synthesis"]["withheld_positive_pixels"]),
        "full_domain_pooled_summary": summary_full,
        "off_range_front_domain_pooled_summary": summary_off_rf,
        "geothermal_vent_corridor_pooled_summary": summary_vent,
        "per_fold_breakdown": per_fold_details,
        "usgs_sgmc_off_catalogue_benchmark": sgmc_results,
    }
    return experiment_summary, s_sub_norm, pred_sub, relay_oof_2d
