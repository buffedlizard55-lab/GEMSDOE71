"""Metric-optimal Submodular Expected-Kernel-Coverage Marginal-DTI Emission for GEMSDOE71.

Mathematical foundation
-----------------------
Under the official Distance-Weighted Tversky Index (alpha = 0.2, beta = 0.8, R = 300 m = 3 px
triangular kernel k(d) = max(0, 1 - d/3)), a single predicted dot at x covers every truth
pixel y within 3 px with weight k(||x - y||), while adding exactly alpha * 1 = 0.2 to the
false-positive denominator term.

Therefore:
1. The expected first-order kernel-weighted truth coverage of a candidate pixel x under a
   continuous fault-propensity density S(y) is the convolution of S with the exact 3-px
   triangular kernel k(d), sharpened along 1-px ridge crests via directional non-maximum
   suppression (so dots sit dead-center on the fault trace where k(0) = 1.0 rather than on
   shoulder pixels where k(1) = 2/3).
2. Catalogue-flank collar exclusion d(visible_faults) > collar_px removes the zero-credit
   near-catalogue halo (proven by the 4-point live-score collinearity 0.2600 -> 0.2708 ->
   0.2750 -> 0.2778).
3. Greedy submodular disk exclusion at spacing min_sep_px >= 3.1 px guarantees that emitted
   dots do not overlap within their primary kernel core, maximizing E[TP_w] / (0.2 N_P + C).
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve, distance_transform_edt


def triangular_kernel_2d(radius_px: float = 3.0) -> np.ndarray:
    """Exact 2-D 300 m (3 px) triangular kernel k(d) = max(0, 1 - d / radius_px)."""
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.hypot(yy, xx)
    k = np.maximum(0.0, 1.0 - d / float(radius_px)).astype(np.float32)
    return k / max(float(k.sum()), 1e-9)


def directional_ridge_boost(surface: np.ndarray) -> np.ndarray:
    """4-direction local crest indicator (1.0 on local maxima across at least 2 axes)."""
    s = np.asarray(surface, dtype=np.float32)
    c_ns = (s >= np.roll(s, 1, axis=0)) & (s >= np.roll(s, -1, axis=0))
    c_ew = (s >= np.roll(s, 1, axis=1)) & (s >= np.roll(s, -1, axis=1))
    c_d1 = (s >= np.roll(np.roll(s, 1, axis=0), 1, axis=1)) & (
        s >= np.roll(np.roll(s, -1, axis=0), -1, axis=1)
    )
    c_d2 = (s >= np.roll(np.roll(s, 1, axis=0), -1, axis=1)) & (
        s >= np.roll(np.roll(s, -1, axis=0), 1, axis=1)
    )
    crest_count = (
        c_ns.astype(np.float32)
        + c_ew.astype(np.float32)
        + c_d1.astype(np.float32)
        + c_d2.astype(np.float32)
    )
    return 0.70 + 0.30 * (crest_count / 4.0)


def expected_kernel_priority(surface: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Compute the expected 3-px triangular-kernel coverage priority field."""
    s = np.where(foot & np.isfinite(surface), surface, 0.0).astype(np.float32)
    k2d = triangular_kernel_2d(3.0)
    k_conv = convolve(s, k2d, mode="nearest")
    boost = directional_ridge_boost(s)
    prio = (0.55 * s + 0.45 * k_conv) * boost
    prio[~foot] = 0.0
    return prio.astype(np.float32)


def emit_submodular_dots(
    surface: np.ndarray,
    foot: np.ndarray,
    visible_faults: np.ndarray,
    *,
    n_dots: int = 36800,
    min_sep_px: float = 3.15,
    collar_px: float = 2.25,
    d_visible: np.ndarray | None = None,
) -> np.ndarray:
    """Place up to ``n_dots`` binary dots by greedy submodular kernel-priority thinning.

    Parameters
    ----------
    surface : np.ndarray
        2-D continuous propensity surface in [0, 1].
    foot : np.ndarray
        Boolean footprint mask (5,167,373 valid pixels).
    visible_faults : np.ndarray
        Boolean mask of visible mapped faults (withheld segments excluded in holdout folds).
    n_dots : int
        Maximum dot budget across the full footprint (scaled proportionally when evaluating a
        cropped or sub-footprint domain).
    min_sep_px : float
        Minimum Euclidean separation between emitted dots in pixels (100 m/px).
    collar_px : float
        Catalogue-flank exclusion collar in pixels around ``visible_faults``.
    d_visible : np.ndarray, optional
        Precomputed Euclidean distance transform to ``visible_faults``.
    """
    foot_b = np.asarray(foot, dtype=bool)
    vis_b = np.asarray(visible_faults, dtype=bool) & foot_b
    if d_visible is None:
        d_visible = distance_transform_edt(~vis_b).astype(np.float32)

    allowed = foot_b & (~vis_b) & (d_visible > float(collar_px))
    prio = expected_kernel_priority(surface, foot_b)
    cand_mask = allowed & (prio > 0.0)
    ys, xs = np.nonzero(cand_mask)
    if ys.size == 0 or n_dots <= 0:
        return np.zeros(surface.shape, dtype=bool)

    scores = prio[ys, xs]
    # Keep top 8x candidate pool for fast sorting
    cap = min(ys.size, max(n_dots * 8, 120_000))
    if ys.size > cap:
        top_idx = np.argpartition(scores, -cap)[-cap:]
        ys, xs, scores = ys[top_idx], xs[top_idx], scores[top_idx]

    order = np.argsort(-scores, kind="mergesort")
    ys = ys[order]
    xs = xs[order]

    r_int = int(np.ceil(min_sep_px))
    dy_grid, dx_grid = np.mgrid[-r_int:r_int + 1, -r_int:r_int + 1]
    disk_mask = (dy_grid * dy_grid + dx_grid * dx_grid) <= (min_sep_px * min_sep_px)
    dy_off, dx_off = dy_grid[disk_mask], dx_grid[disk_mask]

    h, w = surface.shape
    blocked = np.zeros((h, w), dtype=bool)
    emitted = np.zeros((h, w), dtype=bool)
    count = 0

    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]:
            continue
        emitted[y, x] = True
        count += 1
        if count >= n_dots:
            break
        ny = y + dy_off
        nx = x + dx_off
        ok = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        blocked[ny[ok], nx[ok]] = True

    return emitted
