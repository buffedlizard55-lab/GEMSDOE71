import numpy as np

from gems import holdout
from gems.features import distance_to_visible_faults, oof_distance_map


def test_folds_partition_segments_and_masks_are_clean(synth):
    _, _, _, labels = synth
    study = np.ones(labels.shape, bool)
    folds = holdout.make_folds(labels, study, n_folds=4, buffer_m=300)
    union = np.zeros_like(labels)
    for f in folds:
        union |= f.withheld
        assert not (f.visible_faults & f.withheld).any(), "visible and withheld overlap"
        assert not (f.domain & f.visible_faults).any(), "visible faults leaked into scoring domain"
        assert not (f.train_pixels & f.withheld).any(), "withheld pixels used for training"
        assert not (f.train_pixels & f.buffer).any(), "buffer pixels used for training"
        assert not (f.train_pixels & f.stripe).any(), "scoring stripe used for training"
        assert not (f.domain & ~f.stripe).any(), "domain outside stripe"
        assert f.withheld.sum() > 0
    assert (union == labels).all(), "every fault pixel must be withheld in exactly one fold"
    for a in range(len(folds)):
        for b in range(a + 1, len(folds)):
            assert not (folds[a].withheld & folds[b].withheld).any()


def test_distance_feature_ignores_withheld_faults(synth):
    _, _, _, labels = synth
    study = np.ones(labels.shape, bool)
    f = holdout.make_folds(labels, study, n_folds=4, buffer_m=0)[0]
    d = distance_to_visible_faults(f.visible_faults)
    # On a withheld fault pixel the distance must be > 0 because that pixel is not visible.
    if f.withheld.any():
        assert d[f.withheld].min() > 0


def test_leakage_canary_flags_leak_and_passes_noise(tmp_path):
    rng = np.random.default_rng(3)
    y = rng.random((100, 100)) < 0.05
    leak = y.astype(np.float32) + rng.normal(0, 0.01, y.shape).astype(np.float32)
    noise = rng.normal(0, 1, y.shape).astype(np.float32)
    F = np.stack([leak, noise], axis=-1)
    dom = np.ones(y.shape, bool)
    rows = {r["feature"]: r for r in holdout.leakage_canary(F, ["leak", "noise"], y, dom)}
    assert rows["leak"]["flag"] == "LEAKAGE-REVIEW"
    assert rows["noise"]["flag"] == "ok"


def test_training_pixels_never_copy_their_own_label(synth):
    """Regression: training positives must not get distance 0 from their own visible fault."""
    _, _, _, labels = synth
    study = np.ones(labels.shape, bool)
    for f in holdout.make_folds(labels, study, n_folds=4, buffer_m=0):
        d = oof_distance_map(f.visible_faults, f.stripe_index, f.index)
        train_pos = f.visible_faults & f.train_pixels
        assert train_pos.any()
        assert d[train_pos].min() > 0, "a training pixel sees its own fault -> label copy"
