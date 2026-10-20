import numpy as np
import pytest

from gems import metric


def _binary_tversky(pred, truth, alpha=0.2, beta=0.8):
    tp = np.sum(pred * truth)
    fp = np.sum(pred * (1 - truth))
    fn = np.sum((1 - pred) * truth)
    return tp / (tp + alpha * fp + beta * fn)


def test_zero_tolerance_equals_standard_tversky():
    rng = np.random.default_rng(1)
    truth = rng.random((30, 40)) < 0.1
    pred = (rng.random((30, 40)) < 0.2).astype(float)
    dom = np.ones_like(truth, dtype=bool)
    c = metric.soft_counts(pred, truth, dom, tol_m=0.0)
    assert metric.pooled_dti([c]) == pytest.approx(_binary_tversky(pred, truth.astype(float)), abs=1e-12)


def test_perfect_prediction_scores_one_and_empty_scores_zero():
    truth = np.zeros((20, 20), bool)
    truth[10, 2:18] = True
    dom = np.ones_like(truth)
    assert metric.pooled_dti([metric.soft_counts(truth.astype(float), truth, dom)]) == pytest.approx(1.0, abs=1e-9)
    assert metric.pooled_dti([metric.soft_counts(np.zeros((20, 20)), truth, dom)]) == 0.0


def test_shift_inside_tolerance_gets_analytic_credit():
    # Vertical truth line of 60 px; prediction shifted 2 px (200 m) east.
    # Triangular weight w(200 m)=1/3 with 300 m tolerance -> DTI = 1/3 exactly in the interior.
    truth = np.zeros((80, 80), bool)
    truth[10:70, 40] = True
    pred = np.zeros((80, 80))
    pred[10:70, 42] = 1.0
    dom = np.ones_like(truth)
    dti = metric.pooled_dti([metric.soft_counts(pred, truth, dom)])
    assert dti == pytest.approx(1 / 3, abs=0.02)


def test_shift_outside_tolerance_gets_no_credit():
    truth = np.zeros((80, 80), bool)
    truth[10:70, 40] = True
    pred = np.zeros((80, 80))
    pred[10:70, 46] = 1.0  # 600 m away
    dom = np.ones_like(truth)
    assert metric.pooled_dti([metric.soft_counts(pred, truth, dom)]) == pytest.approx(0.0, abs=1e-9)


def test_domain_excludes_outside_pixels():
    truth = np.zeros((20, 20), bool)
    truth[5, 5] = True
    pred = np.zeros((20, 20))
    pred[5, 5] = 1.0
    dom = np.zeros_like(truth)
    dom[:, :10] = True
    c = metric.soft_counts(pred, truth, dom, tol_m=0)
    assert c["n_truth_px"] == 1 and c["TP"] == 1.0
    dom[5, 5] = False
    c = metric.soft_counts(pred, truth, dom, tol_m=0)
    assert c["n_truth_px"] == 0


def test_bootstrap_ci_brackets_point_estimate_for_constant_counts():
    counts = [{"TP": 5.0, "FP": 5.0, "FN": 5.0, "n_truth_px": 5} for _ in range(4)]
    lo, hi = metric.bootstrap_ci(counts, n_boot=200, seed=0)
    assert lo == pytest.approx(metric.pooled_dti(counts), abs=1e-9)
    assert hi == pytest.approx(metric.pooled_dti(counts), abs=1e-9)


def test_all_ones_dti_matches_closed_form():
    """All-ones map: DTI = a / (a + alpha*(N - a)), a = sum of tolerance coverage over the domain."""
    rng = np.random.default_rng(4)
    truth = rng.random((60, 60)) < 0.03
    dom = np.ones_like(truth)
    c = metric.soft_counts(np.ones((60, 60)), truth, dom)
    a = c["TP"]
    N = dom.sum()
    expected = a / (a + 0.2 * (N - a))
    assert metric.pooled_dti([c]) == pytest.approx(expected, abs=1e-9)
