#!/usr/bin/env python3
"""Generate publication-grade scientific figures for the GEMSDOE71 GitHub Pages site."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def make_fig1_collinearity():
    e0 = json.load(open(ROOT / "evidence" / "e0_forensic_02778.json"))
    fit = e0["four_point_collinearity_inversion"]
    ladder = fit["ladder"]
    T_w = fit["implied_weighted_true_positive_T_w"]
    C_G = fit["implied_constant_denominator_C_G"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), dpi=140)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#334155")

    n_grid = np.linspace(34000, 45500, 200)
    s_curve = T_w / (0.2 * n_grid + C_G)
    ax1.plot(n_grid, s_curve, color="#38bdf8", lw=2.2, label=f"Constant-Recall Tversky Curve\n$S(N_P) = {T_w:.1f} / (0.2 N_P + {C_G:.1f})$")

    pts_n = [r["dots"] for r in ladder]
    pts_s = [r["owner_reported_dti"] for r in ladder]
    labels = [
        "GEMSDOE25 (B=0)\n44,090 dots: 0.2600",
        "GEMSDOE28 (B=1px)\n40,199 dots: 0.2708",
        "GEMSDOE36 (B=2px+infill)\n38,854 dots: 0.2750",
        "GEMSDOE32 H33-2-B2 (B=2px)\n37,654 dots: 0.2778",
    ]
    colors = ["#94a3b8", "#fbbf24", "#f97316", "#22c55e"]
    for x, y, lbl, c in zip(pts_n, pts_s, labels, colors):
        ax1.scatter([x], [y], color=c, s=80, zorder=5, edgecolors="#0f172a", linewidth=1.2)
        dx = -280 if x > 41000 else 220
        dy = 0.0014 if y < 0.276 else -0.0028
        ha = "right" if x > 41000 else "left"
        ax1.annotate(lbl, (x, y), xytext=(x + dx, y + dy), color="#f8fafc", fontsize=8.2, ha=ha,
                     arrowprops=dict(arrowstyle="->", color="#64748b", lw=0.8))

    ax1.set_title("A. 4-Point Constant-Recall Collinearity ($r = 0.999261$)", color="#f8fafc", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Emitted Positive Pixels ($N_P$)", color="#e2e8f0", fontsize=9.5)
    ax1.set_ylabel("ORGANIZER-CONFIRMED / Owner-Reported DTI", color="#e2e8f0", fontsize=9.5)
    ax1.grid(True, color="#334155", linestyle="--", alpha=0.5)
    ax1.legend(loc="lower left", facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8.5)

    # Panel B: Linearized 1/S vs N_P
    inv_s = [1.0 / y for y in pts_s]
    inv_curve = (0.2 * n_grid + C_G) / T_w
    ax2.plot(n_grid, inv_curve, color="#a855f7", lw=2.2, label=f"Linear Fit: $1/S = (0.2/T_w) N_P + C_G/T_w$\nMax DTI residual = $0.00039$")
    for x, y, c in zip(pts_n, inv_s, colors):
        ax2.scatter([x], [y], color=c, s=80, zorder=5, edgecolors="#0f172a", linewidth=1.2)
    ax2.set_title("B. Exact Reciprocal Linearization ($1 / \\mathrm{DTI}$ vs $N_P$)", color="#f8fafc", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Emitted Positive Pixels ($N_P$)", color="#e2e8f0", fontsize=9.5)
    ax2.set_ylabel("Reciprocal Score ($1 / \\mathrm{DTI}$)", color="#e2e8f0", fontsize=9.5)
    ax2.grid(True, color="#334155", linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left", facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(ASSETS / "fig1_collinearity_02778.svg", format="svg")
    plt.close(fig)


def make_fig2_holdout():
    e2 = json.load(open(ROOT / "evidence" / "e2_holdout_comparison.json"))
    scores = e2["pooled_summary"]["scores"]
    per_fold = e2["per_fold_scores"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), dpi=140)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#cbd5e1", labelsize=8.8)
        for spine in ax.spines.values():
            spine.set_color("#334155")

    arms = [
        ("H71A_DPST_HDT", "H71-A: DPST-HDT\n(Promoted Top Candidate)", "#22c55e"),
        ("H71C_Kostrov_Riedel", "H71-C: Kostrov-Riedel\nStrain/Seismic Ratio", "#38bdf8"),
        ("H71B_ASTR_Tilt", "H71-B: Analytic Signal\n& Salem Tilt Contact", "#a855f7"),
        ("H71A_NoTip_Ablation", "H71-A Ablation:\nNo Visible Crack-Tip", "#f59e0b"),
        ("Baseline_TopoScarp", "Baseline Control:\nTopographic Scarp Only", "#94a3b8"),
    ]
    y_pos = np.arange(len(arms))[::-1]
    vals = [scores[k]["dti"] for k, _, _ in arms]
    lows = [scores[k]["dti"] - scores[k]["ci95"][0] for k, _, _ in arms]
    highs = [scores[k]["ci95"][1] - scores[k]["dti"] for k, _, _ in arms]
    colors = [c for _, _, c in arms]
    names = [lbl for _, lbl, _ in arms]

    ax1.barh(y_pos, vals, xerr=[lows, highs], color=colors, alpha=0.88, height=0.58,
             error_kw=dict(ecolor="#f8fafc", lw=1.4, capsize=4))
    for y, v in zip(y_pos, vals):
        ax1.text(v + 0.001, y - 0.18, f"{v:.5f}", color="#f8fafc", fontsize=8.5, fontweight="bold")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, color="#f8fafc", fontsize=8.5)
    ax1.set_xlim(0, 0.072)
    ax1.set_xlabel("Pooled Spatially-Blocked HOLDOUT-DTI (gems57-pooled-hide-v2, 22,893 withheld px)", color="#e2e8f0", fontsize=9)
    ax1.set_title("A. 5-Arm Pooled HOLDOUT-DTI & 95% Spatial Bootstrap CIs", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax1.grid(True, axis="x", color="#334155", linestyle="--", alpha=0.5)

    # Panel B: Per-fold comparison H71-A vs Baseline_TopoScarp & H71-A NoTip
    folds = list(per_fold["H71A_DPST_HDT"].keys())
    x = np.arange(len(folds))
    w = 0.26
    ax2.bar(x - w, [per_fold["H71A_DPST_HDT"][f]["dti"] for f in folds], width=w, color="#22c55e", label="H71-A (DPST-HDT)")
    ax2.bar(x, [per_fold["H71A_NoTip_Ablation"][f]["dti"] for f in folds], width=w, color="#f59e0b", label="H71-A No-Tip Ablation")
    ax2.bar(x + w, [per_fold["Baseline_TopoScarp"][f]["dti"] for f in folds], width=w, color="#94a3b8", label="Baseline TopoScarp")
    ax2.set_xticks(x)
    ax2.set_xticklabels(folds, rotation=25, color="#e2e8f0")
    ax2.set_ylabel("Per-Fold HOLDOUT-DTI", color="#e2e8f0", fontsize=9)
    ax2.set_title("B. Per-Fold Consistency: H71-A Beats Baseline in 8/8 Folds", color="#f8fafc", fontsize=10.5, fontweight="bold")
    ax2.grid(True, axis="y", color="#334155", linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left", facecolor="#0f172a", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=8.5)

    fig.tight_layout()
    fig.savefig(ASSETS / "fig2_holdout_ablation.svg", format="svg")
    plt.close(fig)


def make_fig3_spatial_preview():
    card = json.load(open(ROOT / "evidence" / "run_card.json"))
    zeros_path = ROOT / card["raster"]["primary_zeros_tif"]
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & fp
    with rasterio.open(zeros_path) as ds:
        emitted = (ds.read(1) > 0.5) & fp
    with rasterio.open(ROOT / ".cache" / "registry_rasters" / "GEMSDOE32__h33-2-b2-zeros__c55bafc4.tif") as ds:
        h33 = (ds.read(1) > 0.5) & fp

    # Downsample 6x for clean visual density overview
    step = 6
    H, W = fp.shape
    h_s, w_s = H // step, W // step
    fp_s = fp[:h_s * step, :w_s * step].reshape(h_s, step, w_s, step).any(axis=(1, 3))
    cat_s = cat[:h_s * step, :w_s * step].reshape(h_s, step, w_s, step).mean(axis=(1, 3))
    em_s = emitted[:h_s * step, :w_s * step].reshape(h_s, step, w_s, step).mean(axis=(1, 3))
    h33_s = h33[:h_s * step, :w_s * step].reshape(h_s, step, w_s, step).mean(axis=(1, 3))

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8), dpi=130)
    fig.patch.set_facecolor("#0f172a")
    titles = [
        "A. Mapped Fault Catalogue\n(60,988 px in 5,167,373-px Footprint)",
        "B. GEMSDOE32 H33-2-B2 (0.2778)\n(37,654 dots, B=2.0 px, s=2.83 px)",
        "C. GEMSDOE71 H71-A DPST-HDT\n(35,500 dots, B=2.5 px, s=3.25 px)",
    ]
    cmaps = ["YlOrRd", "Blues", "Greens"]
    arrays = [cat_s, h33_s, em_s]
    vmaxs = [0.18, 0.08, 0.08]

    for ax, title, arr, cmap, vm in zip(axes, titles, arrays, cmaps, vmaxs):
        ax.set_facecolor("#090d16")
        disp = np.where(fp_s, arr, np.nan)
        ax.imshow(disp, cmap=cmap, vmin=0.0, vmax=vm, interpolation="nearest")
        ax.set_title(title, color="#f8fafc", fontsize=10, fontweight="bold")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#334155")

    fig.tight_layout()
    fig.savefig(ASSETS / "fig3_spatial_preview.png", format="png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    make_fig1_collinearity()
    make_fig2_holdout()
    make_fig3_spatial_preview()
    print("Generated fig1_collinearity_02778.svg, fig2_holdout_ablation.svg, fig3_spatial_preview.png")
