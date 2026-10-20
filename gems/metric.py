"""Pooled soft Tversky / DTI with a triangular spatial tolerance.

ASSUMED DEFINITION (verify against the official scoring text, GEMS_96647.pdf, which was not
reachable from the sandbox). With tolerance R (m) and weights w(d) = max(0, 1 - d/R):

  Tt_i = max_j  t_j * w(d_ij)        truth dilated by the triangular kernel (predicted-side credit)
  Pc_j = max_i  p_i * w(d_ij)        prediction dilated by the kernel (truth-side coverage)
  TP = sum_i p_i * Tt_i              predicted mass that lands near a true fault
  FP = sum_i p_i * (1 - Tt_i)        predicted mass far from every true fault
  FN = sum_j t_j * (1 - Pc_j)        true fault pixels not covered by any prediction
  DTI = TP / (TP + alpha*FP + beta*FN)

With R = 0 this is exactly the standard Tversky index on binary masks (checked in tests).
Sums are over the scoring domain only; predictions and truth outside it are ignored.
Pooling = sum TP, FP, FN over folds, then one DTI.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from . import config


def _truth_cover(truth: np.ndarray, res_m: float, tol_m: float) -> np.ndarray:
    """Tt = max(0, 1 - distance_to_nearest_truth / tol). Equals max_j t_j * w(d_ij)."""
    if not truth.any():
        return np.zeros(truth.shape, dtype=np.float64)
    if tol_m <= 0:
        return truth.astype(np.float64)
    d = ndimage.distance_transform_edt(~truth, sampling=res_m)
    return np.clip(1.0 - d / tol_m, 0.0, 1.0)


def _weighted_max_dilate(p: np.ndarray, res_m: float, tol_m: float) -> np.ndarray:
    """Pc_j = max_i p_i * w(d_ij), computed exactly over all offsets within the tolerance."""
    if tol_m <= 0:
        return p.astype(np.float64)
    r = int(math.ceil(tol_m / res_m))
    H, W = p.shape
    pad = np.zeros((H + 2 * r, W + 2 * r), dtype=np.float64)
    pad[r:r + H, r:r + W] = p
    out = np.zeros((H, W), dtype=np.float64)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            d = math.hypot(di * res_m, dj * res_m)
            w = max(0.0, 1.0 - d / tol_m)
            if w <= 0:
                continue
            shifted = pad[r + di:r + di + H, r + dj:r + dj + W]
            np.maximum(out, w * shifted, out=out)
    return out


def soft_counts(pred: np.ndarray, truth: np.ndarray, domain: np.ndarray,
                res_m: float = config.EXPECTED_RES_M, tol_m: float = config.TOLERANCE_M) -> dict:
    """Return TP, FP, FN (floats) for one scoring domain."""
    if pred.shape != truth.shape or pred.shape != domain.shape:
        raise ValueError("pred, truth and domain must share a shape")
    p = np.where(domain, np.clip(np.nan_to_num(pred, nan=0.0), 0.0, 1.0), 0.0).astype(np.float64)
    t = (truth.astype(bool) & domain)
    tt = _truth_cover(t, res_m, tol_m)
    pc = _weighted_max_dilate(p, res_m, tol_m)
    tp = float(np.sum(p * tt * domain))
    fp = float(np.sum(p * (1.0 - tt) * domain))
    fn = float(np.sum(t * (1.0 - pc)))
    return {"TP": tp, "FP": fp, "FN": fn, "n_truth_px": int(t.sum())}


def tversky(tp: float, fp: float, fn: float,
            alpha: float = config.TVERSKY_ALPHA, beta: float = config.TVERSKY_BETA) -> float:
    denom = tp + alpha * fp + beta * fn
    if denom <= 0:
        return 0.0
    return tp / denom


def pooled_dti(counts: list[dict], alpha: float = config.TVERSKY_ALPHA,
               beta: float = config.TVERSKY_BETA) -> float:
    tp = sum(c["TP"] for c in counts)
    fp = sum(c["FP"] for c in counts)
    fn = sum(c["FN"] for c in counts)
    return tversky(tp, fp, fn, alpha, beta)


def bootstrap_ci(counts: list[dict], n_boot: int = 2000, seed: int = 0,
                 alpha: float = config.TVERSKY_ALPHA, beta: float = config.TVERSKY_BETA) -> tuple[float, float]:
    """Percentile 95% CI by resampling folds with replacement (fold-level block bootstrap).

    With only a handful of folds this interval is wide and approximate; report n_folds with it.
    """
    if len(counts) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(counts), len(counts))
        vals.append(pooled_dti([counts[i] for i in idx], alpha, beta))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)
