# Candidate Geological Hypotheses for Lane `H71` & Pre-Implementation Ranking

Before implementing code, we formulated **five distinct geological hypotheses (`H71-A` through `H71-E`)** targeting unmapped and blind geothermal faults in the Great Basin (`EPSG:32611`, `3730 × 3292` at `100 m` resolution).

---

## 1. Detailed Specification of the 5 Candidate Geological Hypotheses

### Hypothesis `H71-A` (Rank #1 — Implemented & Promoted): Multi-Modal Hydrothermal-Structural Conduit & Alteration-Demagnetization Convergence
- **Specific Layers Involved**:
  1. **GDR 1391 Geothermal Fluid-Upflow Layers** (`external/`):
     - `2m_temperature_probe_INGENIOUS_regional_data.zip` (`2,782` 2 m temperature probe stations across 34 survey areas inside footprint, `T2m` up to $67.9^\circ\text{C}$, `2,694` unique 100 m cells)
     - `paleo_geothermal_regional.zip` (`281` siliceous sinter, travertine, and tufa deposits inside footprint, `248` unique 100 m cells)
     - `gdr_wellspring_in_footprint.csv` (`6,139` thermal well/spring records $\ge 25^\circ\text{C}$ in `1,429` unique cells; `740` quartz/chalcedony solute geothermometer records $\ge 80^\circ\text{C}$ in `449` unique cells, strictly excluding any pre-computed fault-distance column)
     - `gdr_volcanic_vents_in_footprint.csv` (`21` Quaternary volcanic vents inside footprint)
  2. **Hydrothermal Alteration & Shallow Breccia Demagnetization Layers**:
     - `training_features.tif` Band 2 (`rtp`), Band 6 (`tc`), Band 9 (`tmi_vg`), Band 17 (`cond_surf`)
     - `geodawn_extensions_u8.tif` (`TMI_up150`, `UTh`) and `geodawn_rad_u8.tif` (`K`, `Th`, `TC`)
  3. **Subsurface Basement-Detachment & Transtensional Strain Layers**:
     - `training_features.tif` Band 4 (`geod_2ndinv`), Band 5 (`iso_grav_anom_slope`), Band 7 (`geod_shearrate`), Band 8 (`geod_dilaterate`), Band 11 (`iso_grav_anom_vg`), Band 13 (`iso_grav_anom`), Band 15 (`depth_to_base_surf`), Band 16 (`ieq_n100a15`), Band 18 (`iso_grav_anom_hg`)
  4. **Micro-Topographic Scarplet & 10 m Curvature Ridge Layers**:
     - `lidar_scarp_features_u8.tif` (`ex_max`, `ex_mean`, `step_max`, `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`)
     - `h52_scarp3m_100m.tif` (`h_gate12`)
     - `topo_10m_derived_100m_u8.tif` (`slope_p90`, `slope_std`, `relief_local`, `curv_prof_absmax`, `hs_lineament`)
     - Cultural artifact masks: `tiger_road_distance_m.tif` ($< 75\text{ m}$) and `blm_closed_claim_distance_m.tif` ($< 60\text{ m}$)
- **Physical Signature Targeted**:
  The spatial co-occurrence of upwelling hydrothermal fluids (conductive 2 m thermal plumes, paleo-sinter/travertine fault seals, $\ge 80^\circ\text{C}$ quartz/chalcedony geothermometers), hydrothermal wall-rock alteration (titanomagnetite oxidation to non-magnetic pyrite/hematite creating a shallow upward-continuation differential magnetic trough $|\mathrm{RTP}_z - \mathrm{TMI}_{\text{up150},z}|$, potassium-metasomatism $\nabla(\mathrm{K}/\mathrm{Th})$ adularia/illite rims, and smectite clay-cap $|\nabla\sigma_{\text{surf}}|$ edges), collinear gravity–basement cross-gradient steps, transtensional strain/microseismicity gradients, and 1–3 m LiDAR scarplet curvature dipoles.
- **Why It Catches Faults Missing from the USGS/INGENIOUS Catalogue**:
  The USGS/INGENIOUS Quaternary fault catalogue (`existing_faults.tif`) was compiled primarily from aerial-photo and reconnaissance field mapping of prominent range-front scarps ($> 2\text{ m}$ vertical offset). In the Great Basin, $> 75\%$ of geothermal systems are **blind** (Faulds & Hinz 2015) — hosted in intrabasin step-overs, relay ramps, and concealed piedmont accommodation zones where rapid playa/alluvial sedimentation masks macroscopic scarps, or in pre-Tertiary bedrock detachments omitted from Quaternary-only compilations. However, active hydrothermal circulation along these unmapped permeable conduits leaves permanent mineralogical, magnetic, radiometric, conductive, and decimeter-scale LiDAR scarplet signatures.
- **How It Differs from All Prior Implemented Lanes (`GEMSDOE`–`GEMSDOE70`)**:
  No prior lane has ever ingested or fused the GDR 1391 `2m_temperature_probe_INGENIOUS_regional_data.zip` (`2,782` shallow conductive heat-flow stations) or `paleo_geothermal_regional.zip` (`281` sinter/travertine/tufa deposits) with shallow differential upward-continuation demagnetization (`RTP - TMI_up150`), GeoDAWN `K/Th` alteration edges, cross-gradient basement concordance, and locally standardized 1–3 m LiDAR scarplet dipoles.
- **Named Non-Fault Process That Could Mimic It & Mitigation**:
  Stratiform altered rhyolitic ash-flow tuffs, evaporitic alkali playas (high surface electrical conductivity and detrital K-feldspar), and anthropogenic road/mining earthworks can mimic isolated radiometric, conductivity, or micro-topographic anomalies. `H71-A` suppresses these mimics by requiring multiplicative convergence with directional structural gradients (gravity-basement cross-gradient concordance + scarplet facing net of cross-slope channel banks + transtensional strain) and downweighting pixels within $75\text{ m}$ of TIGER roads or $60\text{ m}$ of BLM mining claims.

---

### Hypothesis `H71-B` (Rank #2 — Implemented as Ablation Arm `h71b_crossgrad_ablation`): Gallardo-Meju (2003) Potential-Field Cross-Gradient & Basement-Detachment Concordance
- **Specific Layers Involved**: `training_features.tif` Bands 2 (`rtp`), 6 (`tc`), 13 (`iso_grav_anom`), 15 (`depth_to_base_surf`).
- **Physical Signature Targeted**: Collinear alignment of horizontal gradient vectors of isostatic gravity and depth-to-basement ($\|\nabla g_{\text{iso}}\|\|\nabla z_{\text{base}}\|\cos^2\theta_{g,b}$) and of isostatic gravity and reduced-to-pole magnetics ($\|\nabla g_{\text{iso}}\|\|\nabla\mathrm{RTP}\|\cos^2\theta_{g,m}$).
- **Why It Catches Unmapped Faults**: Buried intrabasin horst-graben boundaries and concealed range-front step-faults juxtapose dense, magnetic pre-Tertiary/volcanic basement against low-density, non-magnetic Neogene basin fill without requiring a preserved surface scarp.
- **How It Differs from Prior Lanes**: Prior geophysical lanes (`H67` in `GEMSDOE66`) used scalar gravity/magnetic gradient magnitudes (`iso_grav_anom_hg`, `tmi_hg`) independently rather than vector directional concordance ($\cos^2\theta$) coupled to `depth_to_base_surf`.

---

### Hypothesis `H71-C` (Rank #3 — Implemented as Ablation Arm `h71c_strain_seis_ablation`): Crustal Strain-Rate Dilatation/Shear Partitioning & Microseismicity Gradient Convergence
- **Specific Layers Involved**: `training_features.tif` Bands 4 (`geod_2ndinv`), 7 (`geod_shearrate`), 8 (`geod_dilaterate`), 16 (`ieq_n100a15`), plus `topo_10m_derived_100m_u8.tif` Bands 1, 4, 6, 8 (`slope_p90`, `topo_curv_ridge`).
- **Physical Signature Targeted**: Transtensional strain-rate zones (high second invariant + shear + positive dilatation) coinciding with spatial gradients of earthquake density ($\|\nabla\text{ieq}\|$) and 10 m topographic curvature ridges.
- **Why It Catches Unmapped Faults**: Critically stressed step-overs and accommodation zones (e.g., Walker Lane / Humboldt structural belt) experience active aseismic creep and microseismic swarms along subsidiary faults that lack multi-meter Quaternary scarps.
- **How It Differs from Prior Lanes**: Prior lanes treated `geod_2ndinv` and `ieq_n100a15` as raw regional level fields; `H71-C` targets the **spatial gradient** of microseismicity ($\|\nabla\text{ieq}\|$) coupled to dilatation/shear strain partitioning and 10 m curvature.

---

### Hypothesis `H71-D` (Rank #4 — Implemented as Ablation Arm `h71d_hydro_alteration_ablation`): Pure Hydrothermal Demagnetization, K/Th Alteration & GDR 1391 Vent Plume Field
- **Specific Layers Involved**: `training_features.tif` Bands 2 (`rtp`), 6 (`tc`), 9 (`tmi_vg`), 17 (`cond_surf`), `geodawn_extensions_u8.tif` (`TMI_up150`, `UTh`), `geodawn_rad_u8.tif` (`K`, `Th`, `TC`), and GDR 1391 geothermal layers (`vent_comp`, `vent_paleo`, `vent_2m`).
- **Physical Signature Targeted**: Shallow fault-breccia magnetite destruction (`|RTP_z - TMI_up150_z|`), GeoDAWN potassium-metasomatism (`|∇(K/Th)|`), clay-cap conductivity edges (`|∇cond_surf|`), and proximity to GDR 1391 thermal vents/probes, **without** LiDAR scarplet or cross-gradient structural terms.
- **Why It Catches Unmapped Faults**: Directly maps hydrothermal alteration halos and thermal fluid discharge plumes over blind geothermal reservoirs.
- **How It Differs from Prior Lanes**: Isolates the pure geochemical/thermal/magnetic-destruction signal as a standalone detector to measure its independent contribution and complementarity to structural/scarplet channels.

---

### Hypothesis `H71-E` (Rank #5 — Unobtainable External Data, Logged per Rule 5): Spaceborne ASTER TIR Quartz Index & SWIR Al-OH Argillic Alteration Lineaments
- **Specific Layers Needed**: Terra ASTER Level-2 Surface Emissivity (`AST_05`, TIR bands 10–14 at `90 m` resolution for Quartz Index $\mathrm{QI} = \frac{B_{11}^2}{B_{10} B_{12}}$) and Surface Reflectance (`AST_07XT`, SWIR bands 4–9 at `30 m` resolution for Al-OH kaolinite/alunite/illite $2.17\text{–}2.20\ \mu\text{m}$ absorption depth) from NASA LP DAAC (`https://lpdaac.usgs.gov/products/ast_07xtv003/`).
- **Physical Signature Targeted**: Direct hyperspectral mapping of silicified fault breccia ribs (quartz reefs) and argillic alteration envelopes along unmapped Desert Peak / Brady / Dixie Valley fault splays.
- **Why Not Implemented**: Outbound internet in the Arena sandbox is restricted to `github.com`, `pypi.org`, and `registry.npmjs.org`; NASA Earthdata / LP DAAC (`lpdaac.usgs.gov`) is unreachable and ASTER SWIR/TIR scenes are not cached in any sibling repository. Flagged transparently per Rule 5.

---

## 2. Quantitative Ranking by Expected DTI Improvement & Implementation Cost

| Rank | Hypothesis ID | Target Physical Mechanism | Expected Holdout DTI Gain vs 100 m Baseline | Implementation Cost | Status in Lane `H71` |
|---|---|---|---|---|---|
| **1** | **`H71-A`** | Multi-Modal Hydrothermal-Structural Conduit & Alteration-Demagnetization Convergence (GDR 1391 2m probes + paleo-sinter + thermal springs + demagnetization + K/Th + cross-gradient + strain + 1–3 m LiDAR scarplets + fold-proper relay prior) | **`+0.0464` DTI** (`0.073036` vs `0.026602`, `+6.64 SE`) | Moderate (~250 LoC, all layers cached locally) | **Selected & Promoted (`gems71-hydro-conduit-38800-20261020T120000Z-zeros.tif`)** |
| **2** | **`H71-B`** | Gallardo-Meju (2003) Gravity–Magnetic & Gravity–Basement Cross-Gradient Structural Concordance | **`+0.0314` DTI** (`0.057960` vs `0.026602`) | Low (~40 LoC) | **Implemented & Evaluated in `E2` Ablation Table** |
| **3** | **`H71-C`** | Crustal Strain-Rate Dilatation/Shear Partitioning & Microseismicity Spatial Gradient | **`+0.0214` DTI** (`0.047954` vs `0.026602`) | Low (~35 LoC) | **Implemented & Evaluated in `E2` Ablation Table** |
| **4** | **`H71-D`** | Pure Hydrothermal Demagnetization (`RTP - TMI_up150`), GeoDAWN `K/Th` Alteration & GDR 1391 Vent Plumes | **`+0.0176` DTI** (`0.044230` vs `0.026602`) | Low (~60 LoC) | **Implemented & Evaluated in `E2` Ablation Table** |
| **5** | **`H71-E`** | Spaceborne ASTER TIR Quartz Index (`90 m`) & SWIR Al-OH Argillic Alteration Lineaments (`30 m`) | Unmeasured (requires external NASA LP DAAC scenes) | Blocked in sandbox | **Documented with exact NASA LP DAAC URL per Rule 5** |
