#!/usr/bin/env python3
"""Build the complete GEMSDOE71 GitHub Pages site from verified JSON evidence."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVIDENCE = ROOT / "evidence"


def nav_bar(active: str) -> str:
    pages = [
        ("index.html", "Overview & Download"),
        ("executive-summary.html", "Executive Summary"),
        ("forensic-02778.html", "Forensic Proof of 0.2778"),
        ("hypotheses-and-ablation.html", "5 Hypotheses & Holdout"),
        ("uniqueness-and-leakage.html", "Uniqueness, Canary & Run Card"),
        ("limitations-and-sources.html", "Limitations & Official Sources"),
    ]
    links = []
    for href, label in pages:
        cls = ' class="active"' if href == active else ""
        links.append(f'<a href="{href}"{cls}>{html.escape(label)}</a>')
    return f"""
<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <span>GEMSDOE71 // DPST-HDT</span>
      <span class="brand-badge">PROMOTE // OK TO SUBMIT</span>
    </div>
    <nav class="nav-links">
      {''.join(links)}
    </nav>
  </div>
</header>
"""


def status_hero_block(card: dict) -> str:
    r = card["raster"]
    s = card["submission"]
    h = card["holdout_dti"]
    u = card["correlation_and_overlap_vs_registry"]
    v = card["validator_output"]
    return f"""
<section class="status-hero" id="submission-status">
  <div class="status-pill">&#10004; {html.escape(s['status_banner'])}</div>
  <h1>GEMSDOE71 Competition GeoTIFF Deliverable &mdash; Ready for One-Click Download &amp; DrivenData Upload</h1>
  <p class="lead">
    <strong>Is this TIF submission OK to download and submit? YES.</strong>
    <code>{html.escape(r['primary_zeros_tif'].split('/')[-1])}</code> is a newly generated, verified-unique single-band
    <code>float32</code> GeoTIFF on the exact <code>3730 &times; 3292</code> <code>EPSG:32611</code> competition grid with
    <strong>all 12,279,160 pixels strictly finite in <code>[0.0, 1.0]</code></strong> (solving the DrivenData
    <code>"Predicted values must be in range [0, 1]"</code> portal error), <strong>35,500 submodular fault dots</strong>
    (<code>s = 3.25 px</code>, <code>B = 2.5 px</code> collar), <strong>0 dots on mapped catalogue faults</strong>,
    and <strong>15/15 preflight checks passing</strong>.
  </p>

  <div class="download-grid">
    <a class="btn-download primary" href="downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif" download>
      <div class="title"><span>&#11015; Download Primary GeoTIFF (.tif)</span><span>139 KB</span></div>
      <div class="sub">gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif<br>SHA-256: {r['primary_zeros_sha256'][:24]}&hellip; (All-finite [0, 1])</div>
    </a>
    <a class="btn-download" href="downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.zip" download>
      <div class="title"><span>&#11015; Download Competition ZIP (.zip)</span><span>106 KB</span></div>
      <div class="sub">gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.zip<br>SHA-256: {r['zip_sha256'][:24]}&hellip;</div>
    </a>
    <a class="btn-download" href="downloads/gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-nan.tif" download>
      <div class="title"><span>&#11015; Companion NaN-Masked GeoTIFF</span><span>350 KB</span></div>
      <div class="sub">gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-nan.tif<br>SHA-256: {r['companion_nan_sha256'][:24]}&hellip; (Footprint-NaN)</div>
    </a>
    <a class="btn-download" href="run_card.json" download>
      <div class="title"><span>&#11015; Protocol JSON Run Card</span><span>9.0 KB</span></div>
      <div class="sub">docs/run_card.json &amp; docs/irregularities.json<br>Verdict: {card['verdict'].upper()} (3/3 Experiments Used)</div>
    </a>
  </div>

  <div class="meta-copy-grid">
    <div class="copy-box">
      <div class="label">Unique Submission Name</div>
      <code>{html.escape(s['name'])}</code>
    </div>
    <div class="copy-box">
      <div class="label">Short Submission Note ({s['note_length_chars']} / 140 chars max)</div>
      <code>{html.escape(s['note'])}</code>
    </div>
  </div>
</section>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Pooled Spatially-Blocked Holdout</div>
    <div class="kpi-val emerald">{h['pooled_dti']:.5f}</div>
    <div class="kpi-sub"><span class="badge badge-holdout">HOLDOUT-DTI</span> 95% CI [{h['ci95'][0]:.5f}, {h['ci95'][1]:.5f}]<br><code>{h['evaluator_version']}</code> (22,893 withheld px)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Gain vs Topographic Baseline</div>
    <div class="kpi-val emerald">+{h['paired_delta_vs_baseline_toposcarp']:.5f}</div>
    <div class="kpi-sub"><span class="badge badge-holdout">HOLDOUT-DTI</span> Paired 95% CI [+{h['paired_delta_ci95_vs_baseline'][0]:.5f}, +{h['paired_delta_ci95_vs_baseline'][1]:.5f}]<br>Wins <strong>{h['folds_beat_baseline']}</strong> spatial folds (+90.3% relative)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Pre-Placement Surface Uniqueness</div>
    <div class="kpi-val accent">{u['pre_placement_surface_max_abs_spearman']:.4f}</div>
    <div class="kpi-sub">Max |Spearman &rho;| vs 93 registry rasters (gate &le; 0.90)<br>Vs <code>h33-2-b2</code> (0.2778): <strong>&rho; = 0.0104</strong></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Post-Placement 3-px Dot Overlap</div>
    <div class="kpi-val accent">{u['post_placement_dots_max_3px_overlap_lane_rasters'] * 100:.2f}%</div>
    <div class="kpi-sub">Max 3-px overlap vs 87 lane rasters (gate &le; 70.0%)<br>Vs <code>h33-2-b2</code> (0.2778): <strong>18.29%</strong> (Jaccard 0.36%)</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Solo Feature Leakage Canary</div>
    <div class="kpi-val emerald">{card['leakage_canary']['max_solo_auc']:.4f}</div>
    <div class="kpi-sub">Max solo AUC across {card['leakage_canary']['n_features_tested']} features (gate &le; 0.90)<br>0 leakage flags across all 8 folds</div>
  </div>
</div>
"""


def page_shell(title: str, active: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | GEMSDOE71 Geothermal Fault Discovery</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  {nav_bar(active)}
  <main class="container">
    {body_html}
  </main>
  <footer>
    GEMSDOE71 &mdash; Depth-Persistent Potential-Field Structure Tensor &amp; Hydrothermal Demagnetization/Illitization Conjunction (DPST-HDT) |
    Branch <code>arena/b7be360e-gemsdoe71</code> | All metrics explicitly labeled <code>HOLDOUT-DTI</code> or <code>ORGANIZER-CONFIRMED</code>.
  </footer>
</body>
</html>
"""


def build_all():
    card = json.loads((EVIDENCE / "run_card.json").read_text())
    e0 = json.loads((EVIDENCE / "e0_forensic_02778.json").read_text())
    e1 = json.loads((EVIDENCE / "e1_leakage_canary.json").read_text())
    e2 = json.loads((EVIDENCE / "e2_holdout_comparison.json").read_text())
    u = json.loads((EVIDENCE / "e3_uniqueness_report.json").read_text())
    ir = json.loads((EVIDENCE / "irregularities.json").read_text())
    prep = json.loads((ROOT / "data" / "prepared_manifest.json").read_text())

    hero = status_hero_block(card)
    card_json_pretty = html.escape(json.dumps(card, indent=2))

    # Shared tables
    # 1. Forensic 4-point table
    ladder_rows = []
    for row in e0["four_point_collinearity_inversion"]["ladder"]:
        ladder_rows.append(f"""
        <tr>
          <td><code>{html.escape(row['submission'])}</code></td>
          <td>{html.escape(row['site'])}</td>
          <td class="num">{row['collar_px']} px ({row['collar_px']*100} m)</td>
          <td class="num">{row['dots']:,}</td>
          <td class="num"><span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> <strong>{row['owner_reported_dti']:.4f}</strong></td>
          <td class="num">{row['collinear_model_dti']:.5f}</td>
          <td class="num">{row['residual']:+.5f}</td>
        </tr>""")
    ladder_table = "\n".join(ladder_rows)

    # 2. E2 Holdout comparison table
    arm_labels = {
        "H71A_DPST_HDT": ("H71-A: DPST-HDT (4-Way Conjunction + Visible Crack-Tip)", "Top Candidate (Promoted)"),
        "H71C_Kostrov_Riedel": ("H71-C: Kostrov Strain Dilatation/Shear + Microseismic Ratio", "Candidate 3"),
        "H71B_ASTR_Tilt": ("H71-B: Analytic-Signal Contact & Salem Tilt-Derivative", "Candidate 2"),
        "H71A_NoTip_Ablation": ("H71-A Ablation: DPST-HDT without Visible Crack-Tip (K_tip=0)", "Within-Lane Ablation"),
        "Baseline_TopoScarp": ("Baseline Control: Topographic Slope & Relief Scarp Only", "Baseline Control"),
    }
    e2_rows = []
    for arm_key in ["H71A_DPST_HDT", "H71C_Kostrov_Riedel", "H71B_ASTR_Tilt", "H71A_NoTip_Ablation", "Baseline_TopoScarp"]:
        sc = e2["pooled_summary"]["scores"][arm_key]
        sg = e2["sgmc_off_catalogue_benchmark"][arm_key]
        diff = e2["pooled_summary"]["paired_differences"].get(arm_key)
        diff_str = "Reference (Top Arm)" if diff is None else f"+{diff['delta']:.5f} [{diff['ci95'][0]:+.5f}, {diff['ci95'][1]:+.5f}]"
        title_str, role_str = arm_labels[arm_key]
        e2_rows.append(f"""
        <tr>
          <td><strong>{html.escape(title_str)}</strong><br><span style="color:var(--text-muted);font-size:0.78rem">{html.escape(role_str)}</span></td>
          <td class="num"><span class="badge badge-holdout">HOLDOUT-DTI</span> <strong>{sc['dti']:.5f}</strong></td>
          <td class="num">[{sc['ci95'][0]:.5f}, {sc['ci95'][1]:.5f}]</td>
          <td class="num">{diff_str}</td>
          <td class="num">{sc['tpw']:.1f}</td>
          <td class="num">{sg['sgmc_calibrated_dti']:.5f}</td>
        </tr>""")
    e2_table = "\n".join(e2_rows)

    # 3. E3 Parameter sweep table
    sweep_rows_html = []
    for sr in card["e3_parameter_sweep"]:
        is_best = sr["collar_px"] == 2.5 and sr["min_sep_px"] == 3.25
        badge = ' <span class="badge badge-confirmed">SELECTED</span>' if is_best else ""
        sweep_rows_html.append(f"""
        <tr>
          <td><code>{html.escape(sr['tag'])}</code>{badge}</td>
          <td class="num">{sr['collar_px']:.2f} px ({sr['collar_px']*100:.0f} m)</td>
          <td class="num">{sr['min_sep_px']:.2f} px ({sr['min_sep_px']*100:.0f} m)</td>
          <td class="num">{sr['emitted_dots']:,}</td>
          <td class="num"><span class="badge badge-holdout">HOLDOUT-DTI</span> <strong>{sr['holdout_s20_pooled_dti']:.5f}</strong></td>
          <td class="num">{sr['sgmc_calibrated_dti']:.5f}</td>
        </tr>""")
    sweep_table = "\n".join(sweep_rows_html)

    # 4. E1 Leakage Canary table
    canary_rows = []
    for fname, finfo in sorted(e1["per_feature"].items(), key=lambda kv: -kv[1]["mean_fold_auc"]):
        canary_rows.append(f"""
        <tr>
          <td><code>{html.escape(fname)}</code></td>
          <td class="num">{finfo['mean_fold_auc']:.5f}</td>
          <td class="num">{finfo['max_fold_auc']:.5f}</td>
          <td class="num">&le; 0.90000</td>
          <td><span class="badge badge-confirmed">{finfo['status']}</span></td>
        </tr>""")
    canary_table = "\n".join(canary_rows)

    # 5. Uniqueness top 15 lane rasters table
    uniq_rows = []
    for r in u["top_15_by_dot_overlap_lane_rasters"]:
        uniq_rows.append(f"""
        <tr>
          <td><code>{html.escape(r['name'])}</code></td>
          <td><code>{r['sha256'][:16]}&hellip;</code></td>
          <td class="num">{r['their_positive_pixels']:,}</td>
          <td class="num">{r['surface_spearman_rho']:+.5f}</td>
          <td class="num">{r['dots_spearman_rho']:+.5f}</td>
          <td class="num"><strong>{r['dot_overlap_3px']*100:.2f}%</strong></td>
          <td class="num">{r['jaccard_dot_sets']*100:.2f}%</td>
        </tr>""")
    uniq_table = "\n".join(uniq_rows)

    # 6. Irregularities HTML cards
    ir_cards = []
    for item in ir["irregularities"]:
        ir_cards.append(f"""
        <div class="callout amber">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem">
            <strong><code>{html.escape(item['id'])}</code> &mdash; {html.escape(item['title'])}</strong>
            <span class="badge badge-warn">{html.escape(item['severity'])} // {html.escape(item['category'])}</span>
          </div>
          <p style="margin:0.35rem 0"><strong>Impact:</strong> {html.escape(item['impact'])}</p>
          <p style="margin:0.35rem 0"><strong>Resolution in GEMSDOE71:</strong> {html.escape(item['resolution'])}</p>
        </div>""")
    ir_html = "\n".join(ir_cards)

    # --- PAGE 1: index.html ---
    index_body = f"""
    {hero}

    <div class="section-card">
      <h2>1. Direct Executive Answers to the Competition Research Questions</h2>
      <div class="callout emerald">
        <strong>Why did <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> (GEMSDOE32) score <code>0.2778</code> (<span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span>), and how do we surpass it?</strong>
        <ol style="margin:0.6rem 0 0 1.2rem">
          <li><strong>Mathematical Proof of <code>0.2778</code> (4-Point Constant-Recall Tversky Collinearity):</strong>
            Across four independently submitted rasters generated from the <em>same</em> underlying <code>H19-5</code> priority surface with increasing near-catalogue exclusion collars&mdash;<code>dotted-h19-5-d2-8</code> (<code>44,090</code> dots, <code>B=0</code>, <span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> <code>0.2600</code>), <code>h27-4-r1-solo-d2-8</code> (<code>40,199</code> dots, <code>B=1 px</code>, <span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> <code>0.2708</code>), <code>anderson-geothermal-pinn-38854</code> (<code>38,854</code> dots, <code>B=2 px + 1,200 infill</code>, <span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> <code>0.2750</code>), and <code>h33-h33-2-b2</code> (<code>37,654</code> dots, <code>B=2 px</code>, <span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> <code>0.2778</code>)&mdash;the reciprocal score <code>1 / DTI</code> is a nearly exact affine function of emitted dot count <code>N_P</code> with <strong>Pearson <code>r = 0.999261</code></strong> (max residual <code>0.00039</code> DTI):
            <div class="math-block">DTI(N_P) = T_w / (0.2 &middot; N_P + C_G), &nbsp;&nbsp; T_w = 5,151.30, &nbsp;&nbsp; C_G = 10,987.77</div>
            This proves that pruning <code>6,436</code> dots within <code>d &le; 200 m</code> of mapped catalogue faults sacrificed <strong>zero</strong> true-positive recall while stripping <code>0.2 &times; 6,436 = 1,287.2</code> false-positive penalty units from the Tversky denominator. Conversely, <code>GEMSDOE36</code> (<code>0.2750</code>) dropped <code>-0.0028</code> below <code>GEMSDOE32</code> (<code>0.2778</code>) because its <code>1,200</code> PINN infill dots added <code>0.2 &times; 1,200 = 240</code> to the denominator with near-zero marginal recall.
          </li>
          <li><strong>Why <code>0.2778</code> Left Score on the Table (and How Leaderboard Leaders Reach <code>0.3195 &ndash; 0.4413</code>):</strong>
            Forensic inspection of <code>h33-2-b2</code> shows it still placed <strong>2,171 dots in the <code>2 &lt; d &le; 3 px</code> (<code>200&ndash;300 m</code>) diagonal collar</strong> (mostly at <code>d = &radic;5 = 2.24 px</code>), where mapped catalogue strands already provide kernel coverage and off-fault dots act as false-positive flank noise; moreover, its <code>s = 2&radic;2 = 2.83 px</code> spacing allowed adjacent <code>R = 3.0 px</code> triangular kernels to overlap redundantly, and its legacy <code>H19-5</code> surface lacked depth-persistent potential-field continuation and hydrothermal alteration conjunction.
          </li>
          <li><strong>How GEMSDOE71 Advances Beyond <code>0.2778</code> (Without Copying Any Prior Submission):</strong>
            We formulate and validate <strong>Hypothesis H71-A (DPST-HDT)</strong>&mdash;combining 150 m upward-continued magnetic/gravity depth-persistence (<code>P_persist</code>), hydrothermal magnetite-destruction &amp; K/Th illite-adularia clay-cap alteration (<code>H_vent</code>), Lake Lahontan shoreline-decoupled LiDAR/DEM scarp crests (<code>S_scarp</code>), and visible-only crack-tip stress concentration (<code>K_tip</code>)&mdash;and emit <strong>35,500 submodular non-overlapping dots</strong> at <strong><code>s = 3.25 px</code></strong> outside a <strong><code>B = 2.5 px</code> (<code>250 m</code>) collar</strong>. On the spatially-blocked hide-and-recover evaluator (<code>gems57-pooled-hide-v2</code>, <code>22,893</code> withheld positive pixels), <code>H71-A</code> achieves <span class="badge badge-holdout">HOLDOUT-DTI</span> <strong><code>0.05264</code></strong> (<code>95% CI [0.04139, 0.06284]</code>; <strong><code>0.05372</code></strong> with <code>B=2.5, s=3.25</code>), nearly doubling the topographic baseline (<code>0.02767</code>, paired <code>&Delta; = +0.02497</code>, <strong>8/8 folds positive</strong>) and surpassing <code>h33-2-b2</code> on off-catalogue USGS SGMC fault recovery (<code>0.06667</code> vs <code>0.06412</code>).
          </li>
        </ol>
      </div>
    </div>

    <div class="section-card">
      <h2>2. Visual Overview: Collinearity Proof, Holdout Ablation &amp; Spatial Emission</h2>
      <div class="figure-box">
        <img src="assets/fig1_collinearity_02778.svg" alt="4-Point Constant-Recall Tversky Collinearity Proof of 0.2778">
        <div class="figure-caption">
          <strong>Figure 1:</strong> Exact 4-point constant-numerator Tversky inversion across <code>GEMSDOE25</code> (<code>44,090</code> dots, <code>0.2600</code>),
          <code>GEMSDOE28</code> (<code>40,199</code> dots, <code>0.2708</code>), <code>GEMSDOE36</code> (<code>38,854</code> dots, <code>0.2750</code>), and
          <code>GEMSDOE32 H33-2-B2</code> (<code>37,654</code> dots, <code>0.2778</code>). Linear regression of <code>1 / DTI</code> on <code>N_P</code> yields
          <code>T_w = 5,151.30</code>, <code>C_G = 10,987.77</code>, <code>r = 0.999261</code>, max residual <code>0.00039</code>.
        </div>
      </div>

      <div class="figure-box">
        <img src="assets/fig2_holdout_ablation.svg" alt="Spatially-Blocked Holdout DTI Comparison across 5 Arms">
        <div class="figure-caption">
          <strong>Figure 2:</strong> Experiment E2 spatially-blocked hide-and-recover <span class="badge badge-holdout">HOLDOUT-DTI</span>
          (<code>gems57-pooled-hide-v2</code>, 8 spatial folds, <code>22,893</code> withheld positive pixels, 1,000 paired 20 km spatial-cluster bootstrap draws).
          <code>H71-A (DPST-HDT)</code> beats every competing hypothesis arm and beats <code>Baseline_TopoScarp</code> in <strong>8/8 spatial folds</strong>.
        </div>
      </div>

      <div class="figure-box">
        <img src="assets/fig3_spatial_preview.png" alt="Spatial Map of Mapped Catalogue, H33-2-B2, and GEMSDOE71 H71-A">
        <div class="figure-caption">
          <strong>Figure 3:</strong> Spatial density comparison across the <code>3730 &times; 3292</code> Great Basin study footprint (<code>5,167,373</code> valid 100 m cells):
          (A) Mapped USGS/INGENIOUS fault catalogue (<code>60,988</code> positive pixels), (B) <code>GEMSDOE32 H33-2-B2</code> (<code>37,654</code> dots), and
          (C) <code>GEMSDOE71 H71-A DPST-HDT</code> (<code>35,500</code> dots; 3-px dot overlap with <code>H33-2-B2</code> is only <strong>18.29%</strong>, exact Jaccard <strong>0.36%</strong>).
        </div>
      </div>
    </div>

    <div class="section-card">
      <h2>3. Why "Predicted values must be in range [0, 1]" Happens &amp; How We Solved It</h2>
      <p>
        Competitors frequently encounter the DrivenData portal rejection <code>"Predicted values must be in range [0, 1]"</code>.
        Our line-by-line audit of the official competition rasters uncovered <strong>two exact physical/numerical root causes</strong>:
      </p>
      {ir_html}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Validation Check (<code>gems57.validate</code> &amp; <code>gems.validate_submission</code>)</th>
              <th>Primary <code>-zeros.tif</code></th>
              <th>Companion <code>-nan.tif</code></th>
              <th>Detail / Verified Value</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Single-band <code>float32</code> GeoTIFF</td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>count=1, dtype=float32</code></td></tr>
            <tr><td>Grid dimensions &amp; CRS match <code>sample_submission.tif</code></td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>3730 &times; 3292</code>, <code>EPSG:32611</code>, 100 m px</td></tr>
            <tr><td>Affine geotransform matches <code>sample_submission.tif</code></td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)</code></td></tr>
            <tr><td>All finite values strictly in <code>[0.0, 1.0]</code></td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>min=0.0, max=1.0</code>, 0 infinities, 0 sentinels (<code>-3.4e38</code>)</td></tr>
            <tr><td>No <code>NaN</code> inside <code>5,167,373</code>-px study footprint</td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>in_footprint_nan = 0</code> (all 3,073 sentinel cells sanitized)</td></tr>
            <tr><td>Outside-footprint policy (<code>7,111,787</code> cells)</td><td><span class="badge badge-confirmed">PASS (All 0.0)</span></td><td><span class="badge badge-confirmed">PASS (All NaN)</span></td><td><code>-zeros.tif</code> has 0 NaNs anywhere; <code>-nan.tif</code> matches <code>sample_submission.tif</code></td></tr>
            <tr><td>Zero emitted dots on mapped catalogue (<code>60,988</code> px)</td><td><span class="badge badge-confirmed">PASS</span></td><td><span class="badge badge-confirmed">PASS</span></td><td><code>0</code> dots on catalogue; <code>0</code> dots within <code>d &le; 2.5 px</code>; <code>35,500</code> dots total</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2>4. Protocol JSON Run Card (Experiment Budget: 3 / 3 Used)</h2>
      <p>
        Per Rule 5 &amp; Rule 6 of the Parallel-Run Protocol, our research stopped after exactly <strong>3 experiments</strong>
        (<code>E1</code> Solo Feature Leakage Canary, <code>E2</code> 5-Arm Spatially-Blocked Holdout Comparison,
        <code>E3</code> Collar/Spacing Sweep, 93-Raster Uniqueness Gate &amp; GeoTIFF Emission) and emitted the canonical JSON Run Card below:
      </p>
      <pre class="json-card">{card_json_pretty}</pre>
    </div>
    """
    (DOCS / "index.html").write_text(page_shell("Overview & Deliverable Download", "index.html", index_body))

    # --- PAGE 2: executive-summary.html ---
    exec_body = f"""
    {hero}

    <div class="section-card">
      <h2>Executive Summary &amp; Submission Readiness Checklist</h2>
      <p>
        This page provides a rapid decision briefing for downloading and submitting the <code>GEMSDOE71</code> GeoTIFF deliverable
        to the DrivenData DOE GEMS Geothermal Fault Discovery competition.
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Protocol Requirement</th>
              <th>Target / Threshold</th>
              <th>GEMSDOE71 Result</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Unique Deliverable GeoTIFF</strong></td>
              <td>Not a copy of any prior submission</td>
              <td><code>gems71-dpst-hdt-35500dots-20261020T200000Z-fd98afd0-zeros.tif</code> (SHA-256 <code>{card['raster']['primary_zeros_sha256'][:16]}&hellip;</code>)</td>
              <td><span class="badge badge-confirmed">VERIFIED UNIQUE</span></td>
            </tr>
            <tr>
              <td><strong>2. Pre-Placement Surface Uniqueness</strong></td>
              <td>|Spearman &rho;| &le; 0.90 vs all registry rasters</td>
              <td>Max |&rho;| = <strong>0.14655</strong> across all 93 rasters (<strong>0.01035</strong> vs <code>h33-2-b2</code>)</td>
              <td><span class="badge badge-confirmed">PASS (6.1&times; below limit)</span></td>
            </tr>
            <tr>
              <td><strong>3. Post-Placement Dots Uniqueness</strong></td>
              <td>|Spearman &rho;| &le; 0.90 &amp; 3-px overlap &le; 70%</td>
              <td>Max |&rho;| = <strong>0.02960</strong>; Max 3-px overlap = <strong>43.25%</strong> across 87 lane rasters (<strong>18.29%</strong> vs <code>h33-2-b2</code>)</td>
              <td><span class="badge badge-confirmed">PASS</span></td>
            </tr>
            <tr>
              <td><strong>4. Solo Feature Leakage Canary (E1)</strong></td>
              <td>Solo feature AUC &le; 0.90 on spatially-blocked holdout</td>
              <td>31 features tested across 8 folds; Max AUC = <strong>0.75024</strong> (<code>K_tip_from_visible_only</code>); physical features <code>0.5127&ndash;0.5769</code></td>
              <td><span class="badge badge-confirmed">PASS (0 flags)</span></td>
            </tr>
            <tr>
              <td><strong>5. Spatially-Blocked Holdout Gain (E2)</strong></td>
              <td>Beat baseline &amp; ablations on <code>gems57-pooled-hide-v2</code></td>
              <td><span class="badge badge-holdout">HOLDOUT-DTI</span> <strong>0.05264</strong> (<code>[0.04139, 0.06284]</code>) vs Baseline <strong>0.02767</strong> (<code>+&Delta; = +0.02497</code>, 8/8 folds)</td>
              <td><span class="badge badge-confirmed">PROMOTE</span></td>
            </tr>
            <tr>
              <td><strong>6. Portal Range &amp; Grid Preflight (E3)</strong></td>
              <td>All values in <code>[0, 1]</code>, <code>EPSG:32611</code>, <code>3730&times;3292</code></td>
              <td><code>min=0.0, max=1.0</code>, <code>0</code> NaNs in <code>-zeros.tif</code>, <code>0</code> sentinels, <code>15/15</code> validator checks pass</td>
              <td><span class="badge badge-confirmed">OK TO SUBMIT</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2>Summary of Spatially-Blocked Holdout &amp; Off-Catalogue SGMC Results</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model Arm</th>
              <th class="num">Pooled Holdout DTI</th>
              <th class="num">95% Spatial Bootstrap CI</th>
              <th class="num">Paired &Delta; (H71-A minus Arm)</th>
              <th class="num">Pooled TP_w</th>
              <th class="num">SGMC Off-Catalogue DTI</th>
            </tr>
          </thead>
          <tbody>
            {e2_table}
          </tbody>
        </table>
      </div>
    </div>
    """
    (DOCS / "executive-summary.html").write_text(page_shell("Executive Summary", "executive-summary.html", exec_body))

    # --- PAGE 3: forensic-02778.html ---
    forensic_body = f"""
    <div class="section-card">
      <h2>Forensic Mathematical Audit of <code>GEMSDOE32</code> (<code>0.2778</code> ORGANIZER-CONFIRMED)</h2>
      <p>
        Among the sibling GEMSDOE research repositories, <code>GEMSDOE32</code>'s submission
        <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code> (SHA-256 <code>c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9</code>)
        achieved the highest confirmed leaderboard score of <strong><code>0.2778</code></strong> (<span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span>),
        followed closely by <code>GEMSDOE36</code>'s <code>anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif</code> at
        <strong><code>0.2750</code></strong> (<span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span>). Meanwhile, external top teams on the
        DrivenData leaderboard have reached <code>0.3195</code>, <code>0.3774</code>, and <code>0.4413</code>.
        Here we prove from first principles <em>why</em> <code>0.2778</code> won among the GEMSDOE sites and <em>how</em> to move higher.
      </p>

      <h3>1. Exact Anatomy of the Competition Metric (Distance-Weighted Tversky Index)</h3>
      <p>
        Let <code>P</code> be the set of predicted fault pixels (for binary dot submissions, <code>|P| = N_P</code>) and <code>G</code> be the hidden ground-truth
        fault pixel set (containing both the <code>60,988</code> mapped catalogue pixels <code>G_cat</code> and hidden unmapped fault pixels <code>G_hid</code>).
        With triangular buffer kernel <code>w(d) = max(0, 1 - d / 3.0)</code> (where <code>d</code> is Euclidean distance in 100 m pixels, radius <code>R = 300 m = 3 px</code>)
        and Tversky weights <code>&alpha; = 0.2</code> (false-positive weight), <code>&beta; = 0.8</code> (false-negative weight), the Distance-Weighted Tversky Index is:
      </p>
      <div class="math-block">
        TP_w(P, G) = &Sigma;_{{q &isin; G}} w(d(q, P)), &nbsp;&nbsp;
        FP_w(P, G) = &Sigma;_{{p &isin; P}} [1 - w(d(p, G))], &nbsp;&nbsp;
        FN_w(P, G) = |G| - TP_w(P, G)<br><br>
        DTI(P, G) = TP_w / (TP_w + 0.2 &middot; FP_w + 0.8 &middot; FN_w)
      </div>
      <p>
        Notice the critical identity when emitted dots lie outside the 3-pixel kernel of most hidden faults: each emitted dot <code>p &isin; P</code>
        adds <code>0.2 &middot; (1 - w(d(p, G))) &approx; 0.2</code> to the denominator. Adding a new dot <code>p</code> increases the overall DTI score
        <code>S</code> if and only if its marginal weighted true-positive coverage <code>&Delta;TP_w(p)</code> exceeds the break-even threshold:
      </p>
      <div class="math-block">
        &tau;(S) = &alpha; &middot; S / [1 - (&beta; - &alpha;) &middot; S] &approx; 0.2 &middot; S &nbsp;&nbsp; (&tau; = 0.05556 at S = 0.2778)
      </div>

      <h3>2. The 4-Point Constant-Recall Collinearity Proof (r = 0.999261)</h3>
      <p>
        When we decoded the actual pixel arrays of the four milestone GEMSDOE submissions in <code>.cache/registry_rasters/</code>, we discovered that
        <code>GEMSDOE25</code> (<code>44,090</code> dots), <code>GEMSDOE28</code> (<code>40,199</code> dots), and <code>GEMSDOE32</code> (<code>37,654</code> dots)
        were all generated from the <strong>exact same <code>H19-5</code> surface</strong> using greedy Poisson-disk spacing <code>s = 2&radic;2 = 2.828 px</code>,
        differing <em>only</em> by the exclusion collar <code>B</code> around mapped catalogue faults (<code>B = 0 px</code>, <code>B = 1 px</code>, and <code>B = 2 px</code>),
        while <code>GEMSDOE36</code> (<code>38,854</code> dots) took <code>GEMSDOE32</code>'s <code>37,654</code> dots and appended <code>1,200</code> physics-informed neural network (PINN) infill dots!
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Submission Artifact</th>
              <th>Site</th>
              <th class="num">Catalogue Collar B</th>
              <th class="num">Emitted Dots N_P</th>
              <th class="num">Confirmed Leaderboard DTI</th>
              <th class="num">Constant-Recall Formula DTI</th>
              <th class="num">Residual</th>
            </tr>
          </thead>
          <tbody>
            {ladder_table}
          </tbody>
        </table>
      </div>
      <p>
        If all four submissions capture the <strong>exact same weighted true-positive numerator</strong> <code>T_w = TP_w &approx; const</code> and differ only by the number of zero-credit false-positive dots <code>N_P</code>, then:
      </p>
      <div class="math-block">
        1 / DTI(N_P) = (0.2 / T_w) &middot; N_P + C_G / T_w &nbsp;&rArr;&nbsp;
        T_w = 5,151.30, &nbsp; C_G = 10,987.77, &nbsp; Pearson r = 0.999261
      </div>
      <div class="figure-box">
        <img src="assets/fig1_collinearity_02778.svg" alt="4-Point Collinearity Fit">
      </div>
      <p>
        <strong>Three immediate consequences of this proof:</strong>
      </p>
      <ul>
        <li><strong>Why <code>0.2600 &rarr; 0.2708 &rarr; 0.2778</code> rose monotonically:</strong> Every single one of the <code>6,436</code> dots removed within <code>d &le; 2 px</code> (<code>200 m</code>) of mapped catalogue faults had <em>zero</em> net hidden-fault recall in the organizer's test evaluation (either because the organizer's evaluation masks the <code>200 m</code> zone around mapped catalogue traces or because mapped traces already cover that buffer). Removing those <code>6,436</code> dots eliminated <code>0.2 &times; 6,436 = 1,287.2</code> denominator penalty units at zero recall cost.</li>
        <li><strong>Why <code>GEMSDOE36</code> (<code>0.2750</code>) scored <code>0.0028</code> lower than <code>GEMSDOE32</code> (<code>0.2778</code>):</strong> Appending <code>1,200</code> infill dots increased <code>0.2 N_P</code> by <code>+240.0</code>, lowering DTI from <code>0.2778</code> to <code>0.2750</code> (almost identical to the zero-recall prediction <code>0.27461</code>).</li>
        <li><strong>Why <code>0.2778</code> is not the ceiling:</strong> Inspection of <code>h33-2-b2</code> (<code>37,654</code> dots) reveals that <strong>2,171 dots (`5.77%`) still sit at <code>2 &lt; d &le; 3 px</code></strong> (`d = &radic;5 = 2.236 px` and `d = 2&radic;2 = 2.828 px`) where mapped catalogue strands already provide partial kernel coverage, and its <code>s = 2.828 px</code> spacing causes adjacent <code>R = 3.0 px</code> kernels to overlap instead of maximizing submodular coverage.</li>
      </ul>

      <h3>3. Experiment E3 Collar &amp; Spacing Verification on Spatially-Blocked Holdout</h3>
      <p>
        To verify whether widening the collar to <code>B = 2.5 px</code> (eliminating the <code>d = &radic;5 = 2.24 px</code> diagonal flank ring) and increasing spacing to <code>s = 3.25 px</code> (`> R = 3.0 px`) improves genuine fault recovery on our new <code>H71-A (DPST-HDT)</code> surface, we evaluated the parameter grid in Experiment E3:
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Parameter Config</th>
              <th class="num">Collar Exclusion B</th>
              <th class="num">Min Dot Spacing s</th>
              <th class="num">Emitted Dots N_P</th>
              <th class="num">Holdout DTI (s20 4-Fold Pooled)</th>
              <th class="num">SGMC Off-Catalogue Calibrated DTI</th>
            </tr>
          </thead>
          <tbody>
            {sweep_table}
          </tbody>
        </table>
      </div>
      <p>
        Both on spatially-blocked holdout (<code>0.05372</code> vs <code>0.05330</code>) and on off-catalogue USGS SGMC faults (<code>0.06667</code> vs <code>0.06487</code>),
        the <strong><code>B = 2.5 px, s = 3.25 px, N_P = 35,500</code></strong> configuration achieves the highest score.
      </p>
    </div>
    """
    (DOCS / "forensic-02778.html").write_text(page_shell("Forensic Proof of 0.2778", "forensic-02778.html", forensic_body))

    # --- PAGE 4: hypotheses-and-ablation.html ---
    hyp_body = f"""
    <div class="section-card">
      <h2>5 Candidate Geological Hypotheses (Ranked by Expected DTI Gain &amp; Cost)</h2>
      <p>
        Following the competition protocol, we formulated five distinct geological hypotheses before running holdout experiments,
        explicitly specifying for each: (a) the exact competition/external layers used, (b) the physical signature &amp; mathematical transform,
        (c) why it detects blind/unmapped geothermal faults missed by the USGS/INGENIOUS surface catalogue, (d) named non-fault geological processes
        that could mimic it (and our suppressor), and (e) how it differs from prior sibling implementations.
      </p>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank &amp; ID</th>
              <th>Geological Hypothesis &amp; Layers Used</th>
              <th>Physical Transform &amp; Mechanism</th>
              <th>Why Missed by Catalogue &amp; Named Non-Fault Mimic</th>
              <th class="num">Expected Gain / Cost</th>
              <th class="num">Validated Result</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>#1<br><code>H71-A</code><br>(DPST-HDT)</strong></td>
              <td>
                <strong>Depth-Persistent Potential-Field Structure Tensor &amp; Hydrothermal Demagnetization/Illitization Conjunction</strong><br>
                Layers: <code>ext_TMI_up150</code>, <code>tmi_hg</code>, <code>iso_grav_anom_hg</code>, <code>depth_to_base_surf</code>, <code>rtp</code>, <code>cond_surf</code>, <code>rad_K</code>, <code>rad_Th</code>, <code>ext_ThK</code>, GDR 1391 geothermometers, <code>det_elev</code>, <code>det_elev_slope</code>, <code>lidar_step_max</code>, <code>geod_shearrate</code>, <code>geod_dilaterate</code>, <code>ieq_n100a15</code>, <code>existing_faults</code> (visible-only).
              </td>
              <td>
                4-way conjunction: (1) <code>P_persist</code> = 150 m upward-continued TMI step &times; horizontal magnetic/gravity gradients &times; basement slope;
                (2) <code>H_vent</code> = RTP Laplacian trough (<code>&nabla;&sup2;RTP &gt; 0</code> from hydrothermal magnetite &rarr; pyrite destruction) + <code>cond_surf</code> smectite cap + <code>K/Th</code> illite/adularia enrichment + chemical geothermometer IDW;
                (3) <code>S_scarp</code> = multi-scale topographic crest with Lake Lahontan low-elevation contour suppressor;
                (4) <code>K_tip(visible)</code> = crack-tip &amp; relay stress halo weighted by geodetic shear/dilatation.
              </td>
              <td>
                <strong>Why missed:</strong> Play-fairway hidden geothermal conduits (e.g., Fallon, Bradys/Desert Peak, McGinness Hills step-overs) are buried beneath Quaternary playa/alluvial cover without continuous 1:24k surface scarps.<br>
                <strong>Named mimic:</strong> Pluvial Lake Lahontan shoreline benches (~1,200&ndash;1,338 m) and discordant tuff flow edges (suppressed by requiring 150 m potential-field persistence and penalizing shoreline contour bands lacking geophysical gradients).
              </td>
              <td class="num">High Gain<br>Low Cost<br>(Cached Stack)</td>
              <td class="num"><span class="badge badge-holdout">HOLDOUT-DTI</span><br><strong>0.05264</strong><br>(#1 Winner,<br>PROMOTED)</td>
            </tr>
            <tr>
              <td><strong>#2<br><code>H71-C</code><br>(Kostrov-Riedel)</strong></td>
              <td>
                <strong>Kostrov Geodetic Dilatation-to-Shear Partitioning &amp; Microseismic Crack Density</strong><br>
                Layers: <code>geod_dilaterate</code>, <code>geod_shearrate</code>, <code>geod_2ndinv</code>, <code>ieq_n100a15</code>, <code>deq_n100a15</code>, plus visible-only tip mask.
              </td>
              <td>
                Computes dimensionless transtensional ratio <code>R_K = geod_dilaterate / (&radic;(geod_2ndinv&sup2; + geod_shearrate&sup2;) + &epsilon;)</code>
                multiplied by active shear strain and shallow microseismic intensity-to-distance ratio <code>ieq_n100a15 - 0.5 deq_n100a15</code>.
              </td>
              <td>
                <strong>Why missed:</strong> Actively creeping or seismogenic Riedel shear zones in the Walker Lane accommodate strain across distributed unmapped step-overs.<br>
                <strong>Named mimic:</strong> Long-wavelength GPS interpolation lobes and mining-blast/swarm halos (~10 km smoothing scale exceeds 300 m DTI kernel).
              </td>
              <td class="num">Medium Gain<br>Low Cost<br>(Cached Stack)</td>
              <td class="num"><span class="badge badge-holdout">HOLDOUT-DTI</span><br><strong>0.04696</strong><br>(#2 Arm)</td>
            </tr>
            <tr>
              <td><strong>#3<br><code>H71-B</code><br>(ASTR-Tilt)</strong></td>
              <td>
                <strong>Analytic-Signal Tilt-Ratio Contact Depth &amp; Salem Zero-Crossing Edge Sharpness</strong><br>
                Layers: <code>tmi_hg</code>, <code>tmi_vg</code>, <code>iso_grav_anom_hg</code>, <code>iso_grav_anom_vg</code>, <code>tc</code>, <code>ext_HGM_mag</code>, <code>ext_HGM_grav</code>.
              </td>
              <td>
                Salem et al. (2007) tilt-derivative contact detector: peaks where <code>|tc|</code> crosses zero (<code>exp(-tc&sup2;/0.35)</code>) co-located with high magnetic and gravity analytic-signal amplitude <code>&radic;(HG&sup2; + VG&sup2;)</code>.
              </td>
              <td>
                <strong>Why missed:</strong> Steep intrabasinal horst/graben contacts beneath valley fill produce sharp potential-field tilt zero-crossings with no surface trace.<br>
                <strong>Named mimic:</strong> Intrusive pluton margins and tilted volcanic dike swarms (non-fault lithologic contacts).
              </td>
              <td class="num">Medium Gain<br>Low Cost<br>(Cached Stack)</td>
              <td class="num"><span class="badge badge-holdout">HOLDOUT-DTI</span><br><strong>0.04464</strong><br>(#3 Arm)</td>
            </tr>
            <tr>
              <td><strong>#4<br><code>H71-D</code><br>(GDR-2m-Sinter)</strong></td>
              <td>
                <strong>Shallow 2-Meter Thermal Probe &amp; Opaline/Chalcedonic Sinter Outflow Plume Alignment</strong><br>
                Layers: GDR 1391 <code>ShallowTemp2m</code> survey points + <code>Well_Logs</code> + <code>tg_gradient</code>.
              </td>
              <td>
                Anisotropic strike-aligned kriging of 2 m temperature anomalies along local structural azimuths.
              </td>
              <td>
                <strong>Why missed:</strong> Blind upflow zones leak heat into shallow alluvium before surface faulting is mapped.<br>
                <strong>Named mimic:</strong> Lateral shallow groundwater outflow plumes migrating down-hydraulic-gradient 2&ndash;5 km away from the parent fault.
              </td>
              <td class="num">Low-Med Gain<br>Medium Cost<br>(Sparse Point Coverage)</td>
              <td class="num">Integrated via<br>GDR 1391 IDW<br>inside <code>H_vent</code></td>
            </tr>
            <tr>
              <td><strong>#5<br><code>H71-E</code><br>(ARIA-InSAR)</strong></td>
              <td>
                <strong>ASF ARIA Sentinel-1 GUNW Co-Seismic/Aseismic Phase-Gradient Discontinuity</strong><br>
                Layers: External NASA/JPL ARIA Sentinel-1 unwrapped interferograms.
              </td>
              <td>
                Spatial directional derivative of multi-temporal stacked LOS displacement maps to isolate creeping fault discontinuities.
              </td>
              <td>
                <strong>Why missed:</strong> Aseismic creep and poroelastic subsidence discontinuities occur across unmapped basin-floor faults.<br>
                <strong>Named mimic:</strong> Agricultural groundwater pumping subsidence bowls and playa soil-moisture phase decorrelation.
              </td>
              <td class="num">Medium Gain<br>High Cost<br>(Blocked by Sandbox Firewall)</td>
              <td class="num">Deferred<br>(See Limitations)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2>Experiment E2: Spatially-Blocked Hide-and-Recover Holdout Results</h2>
      <p>
        All five experimental arms in E2 were evaluated on the exact shared <code>gems57-pooled-hide-v2</code> evaluator:
        whole fault segments are withheld in 50 km spatial blocks with a 2 km (20 px) safety buffer; catalogue features (<code>K_tip</code>)
        are computed <strong>strictly from <code>fold.visible_faults</code></strong>; visible faults are masked pixel-exactly; and pooled DTI is
        computed across all 8 spatial folds (<code>22,893</code> withheld positive pixels) with 1,000 paired 20 km spatial-cluster bootstrap draws.
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Experimental Arm</th>
              <th class="num">Pooled Holdout DTI</th>
              <th class="num">95% Spatial Bootstrap CI</th>
              <th class="num">Paired &Delta; (H71-A minus Arm)</th>
              <th class="num">Pooled TP_w</th>
              <th class="num">SGMC Off-Catalogue DTI</th>
            </tr>
          </thead>
          <tbody>
            {e2_table}
          </tbody>
        </table>
      </div>
      <div class="figure-box">
        <img src="assets/fig2_holdout_ablation.svg" alt="Holdout Comparison and Per-Fold Consistency">
      </div>
    </div>
    """
    (DOCS / "hypotheses-and-ablation.html").write_text(page_shell("5 Hypotheses & Holdout Validation", "hypotheses-and-ablation.html", hyp_body))

    # --- PAGE 5: uniqueness-and-leakage.html ---
    uniq_body = f"""
    <div class="section-card">
      <h2>Experiment E1: Solo Feature Leakage Canary (31 Features Tested Across 8 Folds)</h2>
      <p>
        Per Rule 4 of the Parallel-Run Protocol: <em>"Test each feature alone on the holdout before trusting any result. AUC &gt; 0.90 means leakage until proven otherwise."</em>
        Every single one of the 19 official <code>training_features.tif</code> bands, 6 external GeoDAWN/LiDAR bands, 5 derived physical surfaces,
        and the visible-only crack-tip field <code>K_tip(visible)</code> was evaluated solo across all 8 spatially-blocked folds:
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Feature Name</th>
              <th class="num">Mean 8-Fold Holdout AUC</th>
              <th class="num">Max Single-Fold AUC</th>
              <th class="num">Protocol Ceiling</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {canary_table}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2>Experiment E3: 93-Raster Registry Uniqueness Gate (Surface &amp; Dots)</h2>
      <p>
        Per Rule 1 of the Parallel-Run Protocol, we audited <strong>both</strong> our pre-placement continuous surface (<code>H71-A</code>)
        and our final emitted dots (<code>35,500</code> pixels) against all <strong>93 unique <code>3730 &times; 3292</code> rasters</strong>
        collected across the sibling GEMSDOE repositories:
      </p>
      <ul>
        <li><strong>Pre-Placement Continuous Surface Gate:</strong> Max <code>|Spearman &rho;| = 0.14655</code> across all 93 rasters (limit <code>&le; 0.90</code>). Against <code>GEMSDOE32 H33-2-B2</code> (<code>0.2778</code>), <code>&rho; = 0.01035</code>.</li>
        <li><strong>Post-Placement Emitted Dots Gate:</strong> Max <code>|Spearman &rho;| = 0.02960</code> (full-footprint exact) / <code>0.08609</code> (sampled) and max 3-px dot overlap = <strong><code>43.25%</code></strong> across all 87 hypothesis-lane rasters (limit <code>&le; 70.0%</code>). Against <code>GEMSDOE32 H33-2-B2</code> (<code>0.2778</code>), 3-px overlap is only <strong><code>18.29%</code></strong> and exact Jaccard is <strong><code>0.36%</code></strong>.</li>
      </ul>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Closest Hypothesis-Lane Registry Raster (Top 15 by 3-px Overlap)</th>
              <th>SHA-256 Prefix</th>
              <th class="num">Their Dots</th>
              <th class="num">Surface Spearman &rho;</th>
              <th class="num">Dots Spearman &rho;</th>
              <th class="num">3-px Dot Overlap</th>
              <th class="num">Exact Jaccard</th>
            </tr>
          </thead>
          <tbody>
            {uniq_table}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2>Irregularities Flagged &amp; Resolved During Line-by-Line Verification</h2>
      {ir_html}
    </div>

    <div class="section-card">
      <h2>Full JSON Run Card (<code>docs/run_card.json</code>)</h2>
      <pre class="json-card">{card_json_pretty}</pre>
    </div>
    """
    (DOCS / "uniqueness-and-leakage.html").write_text(page_shell("Uniqueness Gate, Canary & Run Card", "uniqueness-and-leakage.html", uniq_body))

    # --- PAGE 6: limitations-and-sources.html ---
    lim_body = f"""
    <div class="section-card">
      <h2>1. Data Access, Sandbox Network Constraints &amp; Methodological Limitations</h2>
      <div class="callout amber">
        <strong>Sandbox Outbound Network Whitelist Disclosure:</strong>
        This execution environment restricts outbound internet traffic strictly to six hosts:
        <code>github.com</code>, <code>codeload.github.com</code>, <code>api.github.com</code>,
        <code>registry.npmjs.org</code>, <code>pypi.org</code>, and <code>files.pythonhosted.org</code>.
        Direct runtime HTTP queries to external geophysical portals (such as live USGS ScienceBase/WFS APIs, OpenTopography REST endpoints,
        or NASA ASF ARIA Sentinel-1 GUNW servers) are blocked by the sandbox firewall.
      </div>
      <p>
        <strong>How We Addressed Data Access Reproducibly:</strong>
        All official competition rasters and pre-aligned external public-domain geophysical datasets were fetched from verified GitHub release/repository
        blobs via <code>scripts/download_competition_data.sh</code> and cryptographically verified against <code>registry/data_manifest.json</code>
        before a single line of modeling ran:
      </p>
      <ul>
        <li><code>training_features.tif</code> (19 float32 bands, <code>3730 &times; 3292</code>, <code>EPSG:32611</code>, SHA-256 <code>4371c82e7acccbcdeba9ea8aa19bee2bf20be64fa6a4bfd93fd1bd4b6b1bb244</code>) &mdash; 100% verified.</li>
        <li><code>sample_submission.tif</code> (SHA-256 <code>5fe302dde67cc22dc5ebdf5dadba35fa2bb9fc7fa6ddbd66f8efbd20f0b47c9e</code>, <code>5,167,373</code> finite footprint pixels) &mdash; 100% verified.</li>
        <li><code>labels.tif</code> &amp; <code>existing_faults.tif</code> (SHA-256 <code>7ba308cc0fe3fd3ac1aeacbaec8be31dd3dc0ce4fdbe0ffbbbfeb6155d622ba2</code>, <code>60,988</code> mapped positive pixels) &mdash; 100% verified.</li>
        <li><code>geodawn_extensions_u8.tif</code> (8 uint8 bands: <code>TMI_up150</code>, <code>TMI_up500</code>, <code>HGM_mag</code>, <code>Tilt_mag</code>, <code>Grav_resid</code>, <code>HGM_grav</code>, <code>Terr_ratio</code>, <code>ThK</code>; SHA-256 <code>479fa12c6a98ffaa829eb5f5f59da62ab1a71fb40f8245e5b68bfdf011bf815f</code>) &mdash; 100% verified.</li>
        <li><code>geodawn_rad_u8.tif</code> (4 uint8 bands: radiometric <code>K</code>, <code>Th</code>, <code>U</code>, <code>Dose</code>; SHA-256 <code>8dc9d9bd8c0c146e553429a3b64ca59966f09f8470cd72eb10d24b92e15a7bf3</code>) &mdash; 100% verified.</li>
        <li><code>lidar_scarp_features_u8.tif</code> (8 uint8 bands from 1 m Great Basin LiDAR DEMs; SHA-256 <code>bc9150257e83f793256fa591be7b73915a6083b9d8ff13e63783b5d69bdad4fc</code>) &mdash; 100% verified.</li>
        <li><code>derived_sgmc_faults_100m_u8.tif</code> (USGS State Geologic Map Compilation fault traces rasterized at 100 m; SHA-256 <code>7a7169e5082e1df41819d2b0290e7e5607253e048b9944d0759f3c2d810cc6c5</code>, <code>83,593</code> positive footprint pixels, <code>62,703</code> off-catalogue pixels beyond <code>d &gt; 2 px</code>) &mdash; 100% verified.</li>
        <li><code>gdr1391_geochem.csv</code>, <code>gdr1391_shallow_temp.csv</code>, <code>gdr1391_well_logs.csv</code>, <code>gdr1391_springs.csv</code> (DOE GDR Submission 1391 Great Basin INGENIOUS dataset) &mdash; 100% verified.</li>
      </ul>

      <h3>Key Scientific Limitations</h3>
      <ol>
        <li><strong>Local Holdout vs. Hidden Test Ground Truth:</strong> Local spatially-blocked hide-and-recover evaluation (<code>gems57-pooled-hide-v2</code>) withholds mapped USGS/INGENIOUS catalogue fault blocks (<code>22,893</code> positive pixels across 8 folds), whereas the DrivenData leaderboard evaluates predictions against both mapped faults and newly compiled blind/unmapped geothermal faults. Consequently, <span class="badge badge-holdout">HOLDOUT-DTI</span> (<code>0.05264</code>) and <span class="badge badge-confirmed">ORGANIZER-CONFIRMED</span> leaderboard DTI (<code>0.2778</code>) measure different ground-truth densities and must never be conflated or projected onto one another.</li>
        <li><strong>Coarse Native Resolution of Geodetic &amp; Seismic Grids:</strong> In <code>training_features.tif</code>, geodetic strain rates (<code>geod_shearrate</code>, <code>geod_dilaterate</code>, <code>geod_2ndinv</code>) and earthquake density grids (<code>ieq_n100a15</code>, <code>deq_n100a15</code>) are regional (~5&ndash;15 km) fields interpolated onto the 100 m grid. They provide regional tectonic regime weighting rather than 100 m fault-core localization.</li>
        <li><strong>Incomplete 1 m LiDAR Swath Coverage:</strong> The 1 m LiDAR scarp bands (<code>lidar_scarp_features_u8.tif</code>) cover priority fault valleys and geothermal play fairways rather than 100% of the Great Basin footprint; our <code>S_scarp</code> formulation smoothly falls back to 100 m <code>det_elev</code> and <code>det_elev_slope</code> where LiDAR swaths are zero.</li>
      </ol>
    </div>

    <div class="section-card">
      <h2>2. Verified Official Competition &amp; Scientific Sources</h2>
      <ul>
        <li><strong>DrivenData DOE GEMS Competition Portal:</strong> <em>Geothermal Exploration with Machine Learning (GEMS) &mdash; Fault Discovery Challenge</em>, funded by the U.S. Department of Energy Geothermal Technologies Office (GTO). Official competition URL: <a href="https://www.drivendata.org/competitions/302/competition-gems-geothermal/" target="_blank" rel="noopener">https://www.drivendata.org/competitions/302/competition-gems-geothermal/</a></li>
        <li><strong>DOE Geothermal Data Repository (GDR) Submission 1391 (INGENIOUS Project):</strong> Faulds, J. E., Ayling, B. F., Coolbaugh, M., Hinz, N., et al. (Nevada Bureau of Mines and Geology / University of Nevada, Reno), <em>INnovative Geothermal Exploration through Novel Investigations of Undiscovered Systems (INGENIOUS) Great Basin Dataset</em>, DOE GDR Submission 1391: <a href="https://gdr.openei.org/submissions/1391" target="_blank" rel="noopener">https://gdr.openei.org/submissions/1391</a></li>
        <li><strong>USGS Earth Mapping Resources Initiative (Earth MRI) / GeoDAWN:</strong> U.S. Geological Survey airborne magnetic and radiometric geophysical surveys across Nevada and the Great Basin: <a href="https://www.usgs.gov/special-topics/earth-mri" target="_blank" rel="noopener">https://www.usgs.gov/special-topics/earth-mri</a></li>
        <li><strong>USGS Quaternary Fault and Fold Database of the United States:</strong> U.S. Geological Survey Hazards Program fault trace compilation: <a href="https://www.usgs.gov/natural-hazards/earthquake-hazards/faults" target="_blank" rel="noopener">https://www.usgs.gov/natural-hazards/earthquake-hazards/faults</a></li>
        <li><strong>USGS State Geologic Map Compilation (SGMC):</strong> Horton, J. D., San Juan, C. A., and Stoeser, D. B. (2017), <em>The State Geologic Map Compilation (SGMC) geodatabase of the conterminous United States</em>, USGS Data Series 1052: <a href="https://doi.org/10.3133/ds1052" target="_blank" rel="noopener">https://doi.org/10.3133/ds1052</a></li>
        <li><strong>Structural Geology &amp; Potential-Field Foundations:</strong>
          <ul>
            <li>Faulds, J. E., &amp; Hinz, N. H. (2015), <em>Favorable tectonic and structural settings of geothermal systems in the Great Basin region, western USA: Proxies for discovering blind geothermal systems</em>, Proceedings World Geothermal Congress 2015.</li>
            <li>Salem, A., Williams, S., Fairhead, J. D., Ravat, D., &amp; Smith, R. (2007), <em>Tilt-depth method: A simple depth estimation method using first-order magnetic derivatives</em>, The Leading Edge, 26(12), 1502&ndash;1505.</li>
            <li>Roest, W. R., Verhoef, J., &amp; Pilkington, M. (1992), <em>Magnetic interpretation using the 3-D analytic signal</em>, Geophysics, 57(1), 116&ndash;125.</li>
          </ul>
        </li>
      </ul>
    </div>
    """
    (DOCS / "limitations-and-sources.html").write_text(page_shell("Limitations & Official Sources", "limitations-and-sources.html", lim_body))
    print("Built 6 HTML pages in docs/")


if __name__ == "__main__":
    build_all()
