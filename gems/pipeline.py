"""End-to-end steps shared by scripts/ and tests/. Nothing here downloads data."""
from __future__ import annotations

import numpy as np

from . import config
from .features import build_feature_matrix, load_feature_stack, minmax_normalize, oof_distance_map, study_area
from .holdout import leakage_canary, make_folds
from .metric import bootstrap_ci, pooled_dti, soft_counts
from .model import fit_predict


def load_labels(path) -> np.ndarray:
    """Binary fault mask. Reference rule: values >= 1 are faults; nodata (-1) is not."""
    import rasterio

    with rasterio.open(path) as src:
        arr = src.read(1)
        nd = src.nodata
    mask = arr >= 1
    if nd is not None:
        mask &= arr != nd
    return mask


def run_holdout(features_path, labels_path, n_folds=config.DEFAULT_FOLDS, buffer_m=config.DEFAULT_BUFFER_M,
                seed=config.DEFAULT_SEED, n_boot=2000, model_fn=None) -> dict:
    """Hide-and-recover evaluation. Returns a JSON-serialisable result labelled HOLDOUT-DTI."""
    raw, band_names = load_feature_stack(features_path)
    labels = load_labels(labels_path)
    if raw.shape[:2] != labels.shape:
        raise ValueError(f"feature shape {raw.shape[:2]} != label shape {labels.shape}")
    study = study_area(raw)
    Xn = minmax_normalize(raw)
    del raw
    folds = make_folds(labels, study, n_folds=n_folds, buffer_m=buffer_m)
    fit = model_fn or (lambda F, y, tr, pr: fit_predict(F, y, tr, pr, seed=seed))

    counts, per_fold = [], []
    canary: dict[str, list[float]] = {}
    feature_names = None
    for f in folds:
        F, fnames = build_feature_matrix(Xn, oof_distance_map(f.visible_faults, f.stripe_index, f.index))
        feature_names = fnames
        # The model sees visible labels only: withheld pixels are masked out of the label raster.
        pred = fit(F, f.visible_faults, f.train_pixels, f.domain)
        c = soft_counts(pred, labels & ~f.visible_faults, f.domain)
        counts.append(c)
        per_fold.append({"fold": f.index,
                         "withheld_fault_px_total": int(f.withheld.sum()),
                         "withheld_fault_px_in_scoring_stripe": int((f.withheld & f.stripe).sum()),
                         "domain_px": int(f.domain.sum()),
                         **{k: round(v, 3) for k, v in c.items()},
                         "dti_fold": round(pooled_dti([c]), 4)})
        if f.domain.any():
            for row in leakage_canary(F, fnames, labels & ~f.visible_faults, f.domain, seed=seed):
                canary.setdefault(row["feature"], []).append(row["auc"])
        del F

    # Conservative canary: a feature is flagged if ANY fold shows |AUC - 0.5| beyond the limit.
    canary_out = []
    for key, aucs in canary.items():
        finite = [a for a in aucs if np.isfinite(a)]
        strengths = [max(a, 1 - a) for a in finite]
        flag = "LEAKAGE-REVIEW" if any(s > config.LEAKAGE_AUC_LIMIT for s in strengths) else "ok"
        if not finite:
            flag = "insufficient"
        canary_out.append({"feature": key,
                           "auc_per_fold": [round(a, 4) if np.isfinite(a) else None for a in aucs],
                           "max_strength": round(max(strengths), 4) if strengths else None,
                           "flag": flag})

    # Mandatory trivial baseline on the SAME holdout domains: predict 1 everywhere in the domain.
    ones_counts = []
    for f in folds:
        ones = f.domain.astype(np.float32)
        ones_counts.append(soft_counts(ones, labels & ~f.visible_faults, f.domain))
    a = sum(c["TP"] for c in ones_counts)                 # sum of tolerance coverage over domains
    N = sum(int(f.domain.sum()) for f in folds)
    baselines = {
        "all_ones_pooled_dti": round(pooled_dti(ones_counts), 4),
        "all_ones_mean_coverage": round(a / N, 4) if N else None,
        "note": ("All-ones beats a pooled DTI x iff mean coverage >= 0.2x/(1-0.8x). "
                 "Any model must beat this trivial map to show skill."),
    }

    dti = pooled_dti(counts)
    lo, hi = bootstrap_ci(counts, n_boot=n_boot, seed=seed)
    n_pos = int(sum(f.withheld.sum() for f in folds))
    n_scored_pos = int(sum(c["n_truth_px"] for c in counts))
    return {
        "label": "HOLDOUT-DTI",
        "evaluator_version": config.EVALUATOR_VERSION,
        "metric": {"alpha": config.TVERSKY_ALPHA, "beta": config.TVERSKY_BETA,
                   "tolerance_m": config.TOLERANCE_M, "definition": "see gems/metric.py (ASSUMED)"},
        "n_folds": len(folds), "buffer_m": buffer_m, "seed": seed,
        "withheld_positive_px": n_pos,
        "scored_positive_px": n_scored_pos,
        "pooled_dti": round(dti, 4),
        "dti_ci95": [round(lo, 4), round(hi, 4)],
        "ci_method": f"fold-level percentile bootstrap, n_boot={n_boot}",
        "per_fold": per_fold,
        "trivial_baselines": baselines,
        "leakage_canary": canary_out,
        "features": feature_names,
        "band_descriptions": band_names,
    }


def predict_full(features_path, labels_path, n_folds=config.DEFAULT_FOLDS, buffer_m=config.DEFAULT_BUFFER_M,
                 seed=config.DEFAULT_SEED) -> np.ndarray:
    """Cross-fitted submission map: each spatial stripe is predicted by a model that never saw that
    stripe's faults (same fold machinery as the holdout). Output is float32 in [0, 1], 0 off-footprint.

    OPEN QUESTION (flagged): whether the competition scores the full map or only unknown faults.
    Known faults inside a stripe are predicted here from features, not copied from labels.
    """
    raw, _ = load_feature_stack(features_path)
    labels = load_labels(labels_path)
    study = study_area(raw)
    Xn = minmax_normalize(raw)
    del raw
    out = np.zeros(labels.shape, dtype=np.float32)
    for f in make_folds(labels, study, n_folds=n_folds, buffer_m=buffer_m):
        F, _ = build_feature_matrix(Xn, oof_distance_map(f.visible_faults, f.stripe_index, f.index))
        target = f.stripe & study
        pred = fit_predict(F, f.visible_faults, f.train_pixels, target, seed=seed)
        out[target] = pred[target]
        del F, pred  # free the ~1 GB feature matrix before the next fold allocates its own
    return out
