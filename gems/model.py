"""Baseline pixel classifier (CPU). A placeholder for the U-Net reference model, not a leaderboard candidate.

Training pixels are subsampled (all positives, negatives capped at NEG_PER_POS per positive)
to keep CPU training tractable. Output is a calibrated-ish probability in [0, 1].
"""
from __future__ import annotations

import numpy as np

NEG_PER_POS = 10
MAX_TRAIN = 400_000
PREDICT_CHUNK = 1_000_000  # rows per predict call; avoids copying the whole stripe (~1 GB at GEMS size)


def fit_predict(F: np.ndarray, labels: np.ndarray, train_mask: np.ndarray, predict_mask: np.ndarray,
                seed: int = 0) -> np.ndarray:
    """Fit on train_mask pixels, return (H, W) float32 probabilities on predict_mask (0 elsewhere)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    H, W, C = F.shape
    Ff = F.reshape(-1, C)
    yf = labels.reshape(-1).astype(np.int8)
    rng = np.random.default_rng(seed)
    tr = np.flatnonzero(train_mask.reshape(-1))
    pos = tr[yf[tr] == 1]
    neg = tr[yf[tr] == 0]
    if pos.size == 0:
        raise ValueError("no positive training pixels; cannot fit")
    n_neg = min(neg.size, NEG_PER_POS * pos.size, max(0, MAX_TRAIN - pos.size))
    neg = rng.choice(neg, n_neg, replace=False) if n_neg < neg.size else neg
    idx = np.concatenate([pos, neg])
    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, early_stopping=False, random_state=seed)
    clf.fit(Ff[idx], yf[idx])
    out = np.zeros(H * W, dtype=np.float32)
    pr = np.flatnonzero(predict_mask.reshape(-1))
    for s in range(0, pr.size, PREDICT_CHUNK):
        rows = pr[s:s + PREDICT_CHUNK]
        out[rows] = clf.predict_proba(Ff[rows])[:, 1].astype(np.float32)
    return out.reshape(H, W)
