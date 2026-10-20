# PhD-Level Autopsy: Why & How `h33-h33-2-b2` (`GEMSDOE32`) Scored `0.2778` (`ORGANIZER-CONFIRMED`) — and How Lane `H71` Surpasses It

## 1. Forensic Identification of the `0.2778` (`ORGANIZER-CONFIRMED`) Champion Artifact

| Attribute | Verified Value |
|---|---|
| **Submission Identifier** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` |
| **Source Repository & Lane** | `buffedlizard55-lab/GEMSDOE32` (Lane `H33`, branch family derived from `H19-5`) |
| **Canonical File Path** | `submissions/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` |
| **SHA-256 Checksum** | `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` |
| **Twin `-nan.tif` SHA-256** | `785334e70da2c09fa9d1c71dd6c0c8eb22ccba1f113d59013d95620c1ca6387c` |
| **Organizer Score** | **`0.2778` (`ORGANIZER-CONFIRMED`, owner submission ledger)** |
| **Grid Geometry** | `3730 rows × 3292 cols` (`12,279,160` total pixels), `EPSG:32611`, `100 m` resolution, `5,167,373` valid footprint pixels |
| **Value Distribution** | Strictly binary `{0.0, 1.0}` (`float32`), `37,654` positive pixels (`0.7287%` of valid footprint), `0.0` outside footprint |
| **300 m Kernel Coverage** | `525,356` valid footprint pixels within $3\text{ px}$ ($300\text{ m}$) of a placed dot (`10.167%` of valid footprint) |
| **Distance from Mapped Catalogue** | `0` dots at $d_{\text{cat}} \le 2\text{ px}$ ($200\text{ m}$); `6,298` dots in $2 < d_{\text{cat}} \le 3\text{ px}$; `10,165` dots in $3 < d_{\text{cat}} \le 5\text{ px}$; `21,191` dots at $d_{\text{cat}} > 5\text{ px}$ |

---

## 2. Mathematical Mechanics of the Distance-Tolerant IoU (DTI) Metric

Let $\Omega \subset \{1,\dots,3730\} \times \{1,\dots,3292\}$ denote the active evaluation domain (`valid & ~known_faults`), let $T \subset \Omega$ denote the set of hidden ground-truth fault pixels ($N_T = |T|$), and let $P: \Omega \to [0, 1]$ denote the submitted prediction field.

Define the $300\text{ m}$ ($R = 3\text{ px}$) radial triangular distance-decay kernel:
$$K(\Delta r, \Delta c) = \max\left(0,\, 1 - \frac{\sqrt{\Delta r^2 + \Delta c^2}}{3}\right), \qquad \sqrt{\Delta r^2 + \Delta c^2} \le 3.$$

In the official `metric.max_cover` / `metric.dti_exact` implementation:
1. **Truth-to-Prediction Cover ($c_t$)**: Each hidden truth pixel $t \in T$ receives credit equal to the **pointwise maximum** kernel-weighted prediction within its $300\text{ m}$ disk:
   $$c_t(P) = \max_{x \in \Omega:\, \|x - t\|_2 \le 3} P(x)\, K(x - t) \in [0, 1].$$
2. **Prediction-to-Truth Proximity ($q_x$)**: Each predicted pixel $x \in \Omega$ is credited according to its proximity to the nearest hidden truth pixel:
   $$q_x(T) = \max_{t \in T:\, \|x - t\|_2 \le 3} K(x - t) \in [0, 1].$$
3. **Weighted Confusion Terms & DTI Objective ($\alpha = 0.2,\ \beta = 0.8$)**:
   $$\mathrm{TP}_w(P) = \sum_{t \in T} c_t(P), \qquad \mathrm{FN}_w(P) = \sum_{t \in T} \bigl(1 - c_t(P)\bigr) = N_T - \mathrm{TP}_w(P), \qquad \mathrm{FP}_w(P) = \sum_{x \in \Omega} P(x)\bigl(1 - q_x(T)\bigr),$$
   $$\mathrm{DTI}(P) = \frac{\mathrm{TP}_w(P)}{\mathrm{TP}_w(P) + \alpha\,\mathrm{FP}_w(P) + \beta\,\mathrm{FN}_w(P)} = \frac{\mathrm{TP}_w(P)}{\beta N_T + (1-\beta)\,\mathrm{TP}_w(P) + \alpha\,\mathrm{FP}_w(P)}.$$

### Theorem 1 (Sub-Optimality of Soft Fractional Probabilities)
Suppose a set of isolated candidate dot locations $S \subset \Omega$ is emitted with constant amplitude $p \in (0, 1]$. Because both $c_t(p\mathbf{1}_S) = p\,c_t(\mathbf{1}_S)$ and $\mathrm{FP}_w(p\mathbf{1}_S) = p\,\mathrm{FP}_w(\mathbf{1}_S)$ scale linearly with $p$, the DTI score is:
$$\mathrm{DTI}(p\mathbf{1}_S) = \frac{p\,\mathrm{TP}_w(\mathbf{1}_S)}{\beta N_T + p\bigl[(1-\beta)\mathrm{TP}_w(\mathbf{1}_S) + \alpha\,\mathrm{FP}_w(\mathbf{1}_S)\bigr]}.$$
Differentiating with respect to $p$:
$$\frac{\partial\,\mathrm{DTI}(p\mathbf{1}_S)}{\partial p} = \frac{\beta N_T\,\mathrm{TP}_w(\mathbf{1}_S)}{\bigl(\beta N_T + p[(1-\beta)\mathrm{TP}_w(\mathbf{1}_S) + \alpha\,\mathrm{FP}_w(\mathbf{1}_S)]\bigr)^2} > 0 \quad \forall p \in (0, 1].$$
**Consequence**: Any submission that emits soft calibrated probabilities $p \in (0.05, 0.40)$ suffers a severe analytical penalty because the $\beta N_T = 0.8 N_T$ term in the denominator does not shrink with $p$. For any fixed support $S$, crisp binary emission $P(x) \in \{0.0, 1.0\}$ strictly maximizes DTI.

### Theorem 2 (Submodularity of $\max$-Kernel Coverage & Why Dense Ridges Fail)
Because $c_t(P) = \max_{\|x-t\|_2 \le 3} P(x)K(x-t)$ uses the **pointwise $\max$ operator** rather than a sum, placing a second dot $x_2$ adjacent to $x_1$ (`100 m` apart) yields near-zero marginal gain $\Delta\mathrm{TP}_w \approx 0$ (since $x_1$ already covers its $7\times 7$ neighborhood with kernel weights $1.00, 0.67, 0.53, 0.33$), while paying the **full additive false-positive penalty** $\Delta\mathrm{FP}_w = 1 - q_{x_2} \approx 1$.
Specifically, adding a crisp dot $x \notin S$ increases $\mathrm{DTI}(S)$ if and only if its marginal net kernel cover $\Delta\mathrm{TP}_w(x \mid S) = \sum_{t \in T} \max(0,\, K(x-t) - c_t(\mathbf{1}_S))$ satisfies:
$$\frac{\Delta\mathrm{TP}_w(x \mid S)}{\Delta\mathrm{FP}_w(x) - (1-\beta)\Delta\mathrm{TP}_w(x \mid S)} > \frac{\alpha\,\mathrm{DTI}(S)}{1 - (1-\beta)\mathrm{DTI}(S)} \approx 0.2\,\mathrm{DTI}(S).$$
At $\mathrm{DTI} \approx 0.2778$, the break-even threshold is only $\approx 0.0556$ net truth-pixel cover per emitted dot — **provided the dot's $300\text{ m}$ disk is not already covered by a neighbor**. Enforcing minimum inter-dot spacing ($d \ge 2.8\text{–}3.0\text{ px}$) eliminates intra-cluster kernel cannibalization and multiplies the effective area covered per unit $\mathrm{FP}_w$ by $\approx 4.2\times$.

---

## 3. Step-by-Step Empirical Progression to `0.2778` (`ORGANIZER-CONFIRMED`)

The owner's organizer-confirmed leaderboard ledger documents the exact causal chain from early continuous/ridge submissions to `h33-h33-2-b2`:

| Step | Submission / Milestone | Score (`ORGANIZER-CONFIRMED`) | Causal Modification & Physical/Mathematical Mechanism |
|---|---|---|---|
| **1** | `H17` (`GEMSDOE24`) — Multi-scale LiDAR scarp + 10 m topo + geophysics + cultural masks | **`0.1922`** | Replaced 100 m raw DEM with 1–3 m USGS 3DEP LiDAR scarplet geometry (`step_max`, `lapneg_max`, `lappos_max`, `upface_max`, `downface_max`), 10 m USGS curvature/slope, GeoDAWN radiometrics/aeromagnetics, and TIGER road / BLM mining-claim cultural suppression. Emitted as connected 1 px wide ridge chains. |
| **2** | `H19-5` (`GEMSDOE26`) — Corridor-anisotropic directional continuity + structural tip priors | **`0.2477`** (`+0.0555`) | Added 500 m strike-aligned directional continuity filtering along local fault/scarp azimuth and structural fault-tip / relay-ramp priors, plus crisp binary `{0, 1}` thresholding (Theorem 1). Still emitted contiguous 1 px wide lines (`55,660` positive pixels). |
| **3** | `H31-1` (`GEMSDOE30`) — Poisson-disk blue-noise spatial thinning ($d = 3.0\text{ px}$) | **`0.2600`** (`+0.0123`) | Decimated contiguous `H19-5` ridge chains into isolated blue-noise dots (`35,147` dots) separated by $d \ge 3.0\text{ px}$ ($300\text{ m}$), eliminating intra-ridge $\max$-kernel redundancy (Theorem 2). |
| **4** | `H33` (`GEMSDOE31`/`32`) — Tighter blue-noise packing ($d = 2.8\text{ px}$) | **`0.2708`** (`+0.0108`) | Reduced blue-noise inhibition radius from $3.0\text{ px}$ to $2.8\text{ px}$ ($\sqrt{8}\approx 2.828\text{ px}$), eliminating diagonal dead-zones where a fault trace passing between two $3.0\text{ px}$-spaced dots dropped to kernel weight $0.53$. |
| **5** | `h33-h33-2-b2` (`GEMSDOE32`) — Known-fault halo exclusion ($d_{\text{cat}} \le 2\text{ px}$) | **`0.2778`** (`+0.0070`) | Zeroed out all dots within $d_{\text{cat}} \le 2\text{ px}$ ($200\text{ m}$) of `existing_faults.tif` (`37,654` surviving dots). Even if the organizer masks `existing_faults.tif` pixel-exactly ($r=0$), dots placed at $d_{\text{cat}} \in \{1, 2\}\text{ px}$ waste $45\text{–}70\%$ of their $300\text{ m}$ kernel disk overlapping already-mapped fault pixels rather than unmapped fault extensions. |

---

## 4. Why `h33-h33-2-b2` Scores `0.003699` on Buffered Hide-and-Recover Holdout (`folds20`) vs `0.095386` on Off-Catalogue USGS SGMC Faults

A critical diagnostic finding arises when we evaluate the pre-computed `h33-h33-2-b2` GeoTIFF on our two complementary validation instruments:
1. **On the Canonical Buffered Hide-and-Recover Holdout (`gems57-pooled-hide-v3-se`, `11,321` withheld positive pixels across 4 spatial quadrants)**:
   - `h33-h33-2-b2` scores **`0.003699` (`HOLDOUT-DTI`, `95% CI [0.003006, 0.004392]`)**.
   - **Why?** Because `h33-h33-2-b2` is a static pre-computed submission GeoTIFF whose $d_{\text{cat}} \le 2\text{ px}$ ($200\text{ m}$) exclusion collar was carved around the **entire** `existing_faults.tif` catalogue — *including* the 20% of fault segments that `buffered_component_draw` withholds as `truth`! Consequently, `h33-h33-2-b2` deliberately excavated a $200\text{ m}$ void directly on top of every withheld holdout fault segment.
2. **On the Independent Off-Catalogue USGS SGMC Fault Benchmark (`derived_sgmc_faults_100m_u8.tif` at $d_{\text{cat}} > 3\text{ px}$, `62,122` truth pixels)**:
   - `h33-h33-2-b2` scores **`0.095386` (`HOLDOUT-DTI`, USGS-SGMC-OFF-CATALOGUE-DIAGNOSTIC)**.
   - Here, because the evaluation targets are real USGS State Geologic Map Compilation bedrock/intrabasin faults that are absent from `existing_faults.tif` ($d_{\text{cat}} > 300\text{ m}$), `h33-h33-2-b2`'s catalogue collar does not artificially zero out its predictions.

---

## 5. Three Geological Blind Spots of `h33-h33-2-b2` — and How Lane `H71` Beats It on Both Instruments

Why is `h33-h33-2-b2` still Sub-Optimal, and how do we generate a genuinely distinct submission (`H71-A`) that beats it?

1. **Blind Spot 1 — Purely Geomorphic / Distance-Decay Bias (Zero Direct Geothermal Fluid-Flow Evidence)**:
   - `h33-h33-2-b2` was selected entirely by LiDAR/topographic scarp amplitude and distance to mapped Quaternary faults. In the Great Basin, however, **>75% of known geothermal systems are "blind"** (Faulds & Hinz 2015) — concealed beneath Quaternaryplaya, lacustrine, or alluvial-fan sediments where surface fault scarps are eroded or sub-decimeter, yet upwelling thermal fluids leave unmistakable **conductive thermal anomalies (`2m_temperature_probe`), siliceous sinter/travertine deposits (`paleo_geothermal`), thermal springs/geothermometer plumes (`gdr_wellspring`), shallow breccia magnetite destruction (`rtp - TMI_up150`), and potassium-metasomatism (`K/Th`)**.
2. **Blind Spot 2 — Lack of Cross-Gradient Basement-Detachment Concordance**:
   - Where unmapped faults cut pre-Tertiary basement or volcanic bedrock (`derived_sgmc_faults_100m_u8.tif`), 1–3 m LiDAR scarplet extractors tuned for alluvial fault scarps lose sensitivity or fire on non-tectonic talus slopes. Combining **Gallardo-Meju (2003) collinear cross-gradient concordance** ($\nabla g_{\text{iso}} \cdot \nabla z_{\text{base}}$ and $\nabla g_{\text{iso}} \cdot \nabla\mathrm{RTP}$) with 10 m profile curvature and hydrothermal alteration isolates true faulted basement steps.
3. **Blind Spot 3 — Sub-Optimal Support Allocation Across Relay Zones vs Unmapped Bedrock Ranges**:
   - By coupling our **26 physical-hydrothermal-geomorphic channels** with a **fold-proper hydrothermal-gated damage-zone relay prior** (`vis_relay_hydro_prior`, derived strictly from `fold['visible']` during holdout and from `existing_faults.tif` at submission time outside the $d \le 2\text{ px}$ collar) and emitting `38,800` non-maximum-suppressed ($d \ge 3\text{ px}$) crisp `{0.0, 1.0}` dots:
     - On the **4-quadrant buffered hide-and-recover holdout (`gems57-pooled-hide-v3-se`, `11,321` withheld positives)**, `H71-A` achieves **`0.073036` (`95% CI [0.058155, 0.088277]`)**, beating `h33-h33-2-b2` (`0.003699`), `random_control` (`0.046595`), `baseline_100m_topogeophys` (`0.026602`), and every single-family ablation (`H71-B` `0.057960`, `H71-C` `0.047954`, `H71-D` `0.044230`, `H71-A-phys-only` `0.060341`) by **`> 2 SE` (`beats_two_se = True` across all 7 controls)**!
     - On the **independent off-catalogue USGS SGMC fault benchmark (`62,122` off-catalogue positives)**, `H71-A` (`38,800` dots) achieves **`0.096616`**, surpassing `h33-h33-2-b2` (`0.095386`) while maintaining a maximum pre-placement surface Spearman correlation of **`0.1046 <= 0.90`** and maximum discrete 3-px dot overlap of **`0.4687 <= 0.70`** across all 108 registry rasters.
