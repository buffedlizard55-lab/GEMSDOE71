"""Hide-and-recover holdout.

Protocol implemented here (per the project brief):
1. Fault segments = 8-connected components of the positive label mask.
2. Segments are assigned to K spatial stripes by centroid column (blocked, not random pixels).
3. Fold k withholds every segment in stripe k (whole segments, pixel-exact).
4. A buffer of `buffer_m` around withheld segments is excluded from TRAINING pixels.
5. Catalogue-derived features for fold k use only the visible faults (labels minus withheld).
6. Visible faults are excluded from the scoring domain pixel-exactly, so credit cannot come
   from reproducing known faults.
7. The scoring domain for fold k = stripe k  AND  study area  AND  NOT visible fault.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from . import config


@dataclass
class Fold:
    index: int
    withheld: np.ndarray        # bool, withheld fault pixels
    visible_faults: np.ndarray  # bool, catalogue faults usable as features / training labels
    buffer: np.ndarray          # bool, excluded from training
    stripe: np.ndarray          # bool, spatial stripe (scoring region before masking)
    domain: np.ndarray          # bool, scoring domain
    train_pixels: np.ndarray    # bool, pixels allowed as training samples
    stripe_index: np.ndarray    # int, stripe id per pixel (for out-of-fold catalogue features)


def label_segments(labels: np.ndarray) -> tuple[np.ndarray, int]:
    """Label 8-connected fault segments. Returns (segment_id array, n_segments)."""
    seg, n = ndimage.label(labels.astype(bool), structure=np.ones((3, 3), dtype=int))
    return seg, int(n)


def make_folds(labels: np.ndarray, study: np.ndarray, n_folds: int = config.DEFAULT_FOLDS,
               buffer_m: float = config.DEFAULT_BUFFER_M, res_m: float = config.EXPECTED_RES_M) -> list[Fold]:
    seg, n_seg = label_segments(labels)
    if n_seg < n_folds:
        raise ValueError(f"need at least {n_folds} fault segments, found {n_seg}")
    H, W = labels.shape
    # Centroid column of each segment decides its stripe.
    cols = np.arange(W)
    stripe_edges = np.linspace(0, W, n_folds + 1)
    seg_ids = np.arange(1, n_seg + 1)
    centroids_x = np.array(ndimage.center_of_mass(labels.astype(bool), seg, seg_ids))[:, 1]
    seg_fold = np.clip(np.searchsorted(stripe_edges, centroids_x, side="right") - 1, 0, n_folds - 1)
    empty = [k for k in range(n_folds) if not (seg_fold == k).any()]
    if empty:
        raise ValueError(f"stripes {empty} contain no fault segment centroids; use fewer folds or another layout")
    col_fold = np.clip(np.searchsorted(stripe_edges, cols, side="right") - 1, 0, n_folds - 1)
    stripe_of_px = np.broadcast_to(col_fold[None, :], (H, W))

    folds: list[Fold] = []
    for k in range(n_folds):
        withheld_ids = seg_ids[seg_fold == k]
        withheld = np.isin(seg, withheld_ids)
        visible = labels.astype(bool) & ~withheld
        if buffer_m > 0 and withheld.any():
            near = ndimage.distance_transform_edt(~withheld, sampling=res_m) <= buffer_m
        else:
            near = withheld.copy()
        buffer = near & ~withheld
        stripe = stripe_of_px == k
        domain = stripe & study & ~visible
        train_pixels = study & ~stripe & ~near
        folds.append(Fold(index=k, withheld=withheld, visible_faults=visible, buffer=buffer,
                          stripe=stripe, domain=domain, train_pixels=train_pixels,
                          stripe_index=stripe_of_px))
    return folds


def leakage_canary(features: np.ndarray, names: list[str], labels: np.ndarray, domain: np.ndarray,
                   max_samples: int = 200_000, seed: int = 0) -> list[dict]:
    """Single-feature AUC on the holdout domain. |AUC-0.5| giving >0.90 is flagged."""
    from sklearn.metrics import roc_auc_score

    idx = np.flatnonzero(domain.ravel())
    if idx.size == 0 or labels.ravel()[idx].min() == labels.ravel()[idx].max():
        return [{"feature": n, "auc": float("nan"), "flag": "no-both-classes"} for n in names]
    rng = np.random.default_rng(seed)
    if idx.size > max_samples:
        idx = rng.choice(idx, max_samples, replace=False)
    y = labels.ravel()[idx].astype(int)
    out = []
    F = features.reshape(-1, features.shape[-1])
    for j, name in enumerate(names):
        x = F[idx, j].astype(np.float64)
        ok = np.isfinite(x)
        if ok.sum() < 10 or len(np.unique(y[ok])) < 2:
            out.append({"feature": name, "auc": float("nan"), "flag": "insufficient"})
            continue
        auc = float(roc_auc_score(y[ok], x[ok]))
        strength = max(auc, 1 - auc)
        flag = "LEAKAGE-REVIEW" if strength > config.LEAKAGE_AUC_LIMIT else "ok"
        out.append({"feature": name, "auc": round(auc, 4), "flag": flag})
    return out
