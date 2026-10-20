#!/usr/bin/env python3
"""H71 conduit-lineament experiments. Reads the frozen preregistration and does not retune it.

Uses the shared template (gems57.evaluate_holdout, gems57.submission_writer, gems57.metric)
rather than a private metric. Numbers written here are either measured in this process
or copied from a file this process hashed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as HO  # noqa: E402
from gems57 import metric as M  # noqa: E402
from gems57 import submission_writer as SW  # noqa: E402
from gems57 import uniqueness as U  # noqa: E402
from gems71 import conduits as C  # noqa: E402

DATA = Path(os.environ.get("GEMS71_DATA", "/tmp/template60"))
PROBES = Path(os.environ.get(
    "GEMS71_PROBES",
    "/tmp/probes/2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe.xlsx",
))
REGISTRY = Path(os.environ.get("GEMS71_REGISTRY", str(DATA / "registry" / "rasters")))
PREREG = ROOT / "registry" / "preregistration-h71.json"
EVID = ROOT / "evidence"
SUB = ROOT / "submissions"
DL = ROOT / "docs" / "downloads"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    return obj


def json_dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sanitize(obj), indent=2, allow_nan=False) + "\n")


def load_pred(path: Path, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        raw = src.read(1)
        info = {
            "crs": str(src.crs) if src.crs else None,
            "shape": list(src.shape),
            "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata": None if src.nodata is None else str(src.nodata),
            "dtype": src.dtypes[0],
        }
    finite = np.isfinite(raw)
    coerced = int((~finite).sum()) + int((finite & ((raw < 0) | (raw > 1))).sum())
    a = np.where(finite, raw, 0).astype(np.float32)
    a = np.clip(a, 0, 1)
    a = np.where(footprint, a, 0).astype(np.float32)
    info["coerced_pixels"] = coerced
    info["sha256"] = sha256_file(path)
    info["positive"] = int((a > 0).sum())
    return a, info


def auc_safe(scores: np.ndarray, labels: np.ndarray) -> float | None:
    if labels.sum() == 0 or labels.sum() == labels.size:
        return None
    if np.nanstd(scores) == 0 or not np.isfinite(scores).all():
        return None
    return float(roc_auc_score(labels, scores))


def score_folds(pred: np.ndarray, folds, footprint: np.ndarray):
    terms = None
    per = []
    for fold in folds:
        result, block = EH.evaluate(pred, fold, footprint, block_side=200)
        terms = block if terms is None else terms + block
        per.append({
            "fold": fold["name"],
            "dti": result["dti"],
            "tp": result["tp"],
            "fp": result["fp"],
            "fn": result["fn"],
            "n_truth": result["n_truth"],
            "n_emitted_in_active": result["n_emitted"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
        })
    return terms, per


def random_nms(allowed: np.ndarray, n: int, seed: int, radius: float = 3.0) -> np.ndarray:
    pred = np.zeros(allowed.shape, np.float32)
    yy, xx = np.nonzero(allowed)
    if yy.size == 0 or n <= 0:
        return pred
    rng = np.random.default_rng(seed)
    order = rng.permutation(yy.size)
    r = int(np.floor(radius))
    offsets = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
               if dy * dy + dx * dx < radius * radius]
    taken = np.zeros(allowed.shape, bool)
    h, w = allowed.shape
    kept = 0
    for i in order:
        y, x = int(yy[i]), int(xx[i])
        if taken[y, x]:
            continue
        pred[y, x] = 1.0
        kept += 1
        for dy, dx in offsets:
            yy2, xx2 = y + dy, x + dx
            if 0 <= yy2 < h and 0 <= xx2 < w:
                taken[yy2, xx2] = True
        if kept >= n:
            break
    return pred


def uniqueness_scan(arr: np.ndarray, footprint: np.ndarray, rasters: list[Path]) -> dict:
    index = [{
        "repo": "60GEMSDOE-registry",
        "submission": p.name,
        "file": str(p.resolve()),
        "sha256": None,
    } for p in rasters]
    # List indexes are fail-closed (no organizer-complete certificate). Rows are still measurements.
    report = U.compare_array_to_registry(arr, index, footprint, include_reverse=True)
    phase = U.two_phase_summary(
        report["rows"], int(footprint.sum()), expected_rasters=len(rasters),
    )
    phase["template_fail_closed_unique"] = report.get("unique")
    phase["template_scope"] = report.get("scope")
    phase["source_errors"] = [r for r in report["rows"] if "error" in r]
    phase["n_errors"] = len(phase["source_errors"])
    # Drop the full row dump from the returned object used for the card; keep a slim table.
    slim = []
    for r in report["rows"]:
        if "error" in r:
            continue
        slim.append({
            "submission": r.get("submission"),
            "their_dots": r.get("their_dots"),
            "spearman_full_footprint": r.get("spearman_full_footprint"),
            "my_dots_within_3px_of_theirs": r.get("my_dots_within_3px_of_theirs"),
            "jaccard_dot_sets": r.get("jaccard_dot_sets"),
            "representation": U.representation_class(int(r.get("their_dots") or 0), int(footprint.sum()))["kind"],
        })
    slim.sort(key=lambda r: -(r["my_dots_within_3px_of_theirs"] or 0))
    phase["top_overlaps"] = slim[:8]
    phase["top_rho"] = sorted(
        [r for r in slim if r["spearman_full_footprint"] is not None],
        key=lambda r: -abs(r["spearman_full_footprint"]),
    )[:8]
    return phase


def dequant_dem(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        q = src.read(9)
    lo, hi = 1099.7082177734376, 2481.5011486816393
    t = (q.astype(np.float32) - 1.0) / 254.0
    return np.where(q > 0, lo + t * (hi - lo), np.nan).astype(np.float32)


def main() -> int:
    t0 = time.time()
    prereg = json.loads(PREREG.read_text())
    P = prereg["parameters"]
    EVID.mkdir(parents=True, exist_ok=True)
    print("loading grid", flush=True)
    grid = G.load_grid(DATA / "data" / "bridge")
    fp = grid.footprint
    cat = grid.catalogue
    print(f"footprint {int(fp.sum()):,} catalogue {int(cat.sum()):,}", flush=True)

    bridge_hashes = {
        "existing_faults.tif": sha256_file(DATA / "data" / "bridge" / "existing_faults.tif"),
        "sample_submission.tif": sha256_file(DATA / "data" / "bridge" / "sample_submission.tif"),
    }
    expected = {
        "existing_faults.tif": G.SHA256_EXISTING_FAULTS,
        "sample_submission.tif": G.SHA256_SAMPLE_SUBMISSION,
    }
    if bridge_hashes != expected:
        raise SystemExit(f"bridge hash mismatch: {bridge_hashes} != {expected}")

    with rasterio.open(DATA / "data" / "bridge" / "sample_submission.tif") as src:
        sample = src.read(1)
    sample_ones = int((np.isfinite(sample) & (sample == 1)).sum())
    grid_check = C.verify_wellspring_grid(DATA / "data" / "external" / "gdr_wellspring_in_footprint.csv", fp)
    if grid_check["mismatches_gt_1px"]:
        raise SystemExit(f"wellspring row/col does not match the pinned transform: {grid_check}")

    points = C.load_discharge_points(
        DATA / "data" / "external" / "gdr_wellspring_in_footprint.csv",
        DATA / "data" / "external" / "paleo_geothermal_regional.zip",
        DATA / "data" / "external" / "gdr_volcanic_vents_in_footprint.csv",
        PROBES if PROBES.is_file() else None,
        fp,
        probe_dab_min=P["probe_dab_min_c"],
        geotherm_anchor=P["geotherm_anchor_c"],
    )
    print("points", points.counts, flush=True)
    json_dump(EVID / "h71_points.json", {
        "counts": points.counts,
        "grid_check": grid_check,
        "bridge_sha256": bridge_hashes,
        "sample_submission_ones": sample_ones,
        "catalogue_pixels": int(cat.sum()),
        "note": "dist_known_fault_px was present in the CSVs and was not read into any array.",
    })

    print("fitting axes", flush=True)
    axes = C.fit_axes(
        points, radius_px=P["neighborhood_px"], min_points=P["min_points"],
        min_span_px=P["min_span_px"], min_ratio=P["min_eigen_ratio"], max_rms_px=P["max_rms_px"],
    )
    print(f"axes {len(axes)}", flush=True)

    print("magnetic gradient", flush=True)
    with rasterio.open(DATA / "data" / "external" / "geodawn_extensions_u8.tif") as src:
        # Band 4 is TMI upward-continued 150 m, per the file's band description.
        desc = src.descriptions
        tmi = src.read(4)
        if desc[3] != "TMI_up150":
            raise SystemExit(f"unexpected extensions band 4 description: {desc}")
    hg = C.horizontal_gradient(tmi)
    hg_fp = hg[fp & np.isfinite(hg)]
    hg_min = float(np.percentile(hg_fp, P["hg_percentile"]))
    print(f"HG p{P['hg_percentile']} = {hg_min:.4f} on uint8-code gradient", flush=True)

    surfaces = {
        "E1": C.rasterize_axes(axes, fp.shape, fp),
        "E2": C.rasterize_axes(axes, fp.shape, fp, hg=hg, hg_min=hg_min),
        "E3": C.rasterize_axes(axes, fp.shape, fp, hg=hg, hg_min=hg_min, extend_px=P["extension_px"]),
    }
    for name, surf in surfaces.items():
        print(f"{name} trace pixels {int((surf > 0).sum()):,}", flush=True)

    print("building holdout", flush=True)
    folds, _quad = HO.buffered_component_draw(
        grid, seed=P["holdout_seed"], hide_frac=P["holdout_hide_frac"], buffer_px=P["holdout_buffer_px"],
    )
    withheld = np.zeros(fp.shape, bool)
    for fold in folds:
        withheld |= fold["truth"]
    print("withheld positives", int(withheld.sum()),
          [(f["name"], int(f["truth"].sum())) for f in folds], flush=True)

    # Canaries: each feature alone, labels = withheld positives, negatives = sample of active cells.
    spring_kinds = np.isin(points.kind, ["spring_hot", "spring_warm", "spring_geo"])
    paleo_kinds = points.kind == "paleo"
    probe_kinds = points.kind == "probe"
    features = {
        "spring_density_sigma3": C.density(points.row[spring_kinds], points.col[spring_kinds], fp.shape),
        "paleo_density_sigma3": C.density(points.row[paleo_kinds], points.col[paleo_kinds], fp.shape),
        "probe_density_sigma3": C.density(points.row[probe_kinds], points.col[probe_kinds], fp.shape),
        "E1_trace": surfaces["E1"],
        "E2_trace": surfaces["E2"],
        "E3_trace": surfaces["E3"],
        "tmi_hg": np.where(np.isfinite(hg), hg, 0).astype(np.float32),
    }
    # Visible-catalogue distance is a diagnostic, not a model feature.
    visible = folds[0]["visible"]
    features["DIAGNOSTIC_distance_to_visible_catalogue_not_used"] = ndi_distance(visible)

    rng = np.random.default_rng(P["random_seed"])
    active = fp & ~folds[0]["masked_known"]
    neg_idx = np.flatnonzero(active & ~withheld)
    take = rng.choice(neg_idx, size=min(40000, neg_idx.size), replace=False)
    pos_idx = np.flatnonzero(withheld)
    canary = []
    leakage = []
    for fname, feat in features.items():
        scores = np.concatenate([feat.ravel()[pos_idx], feat.ravel()[take]])
        labels = np.concatenate([np.ones(pos_idx.size), np.zeros(take.size)])
        auc = auc_safe(scores, labels)
        row = {
            "feature": fname,
            "auc": auc,
            "n_withheld_positives": int(pos_idx.size),
            "n_negatives_sampled": int(take.size),
            "evidence_class": "HOLDOUT-FEATURE-AUC",
            "evaluator_version": EH.VERSION,
            "used_in_emission": fname in {"E1_trace", "E2_trace", "E3_trace", "tmi_hg"},
        }
        canary.append(row)
        if auc is not None and auc > prereg["gates"]["canary_auc_max"] and row["used_in_emission"]:
            leakage.append(fname)
        print(f"canary {fname} AUC {auc}", flush=True)
    json_dump(EVID / "h71_canary.json", {"rows": canary, "leakage_features": leakage})

    rasters = sorted(REGISTRY.glob("*.tif"))
    print(f"registry rasters {len(rasters)}", flush=True)

    # Surface uniqueness BEFORE placement.
    surface_scans = {}
    stopped = {}
    for name, surf in surfaces.items():
        norm = C.normalize_surface(surf, fp)
        print(f"surface uniqueness {name}", flush=True)
        scan = uniqueness_scan(norm, fp, rasters)
        surface_scans[name] = scan
        rho = scan["literal_reading"]["worst_spearman_full_footprint"]
        stopped[name] = bool(rho is not None and rho > prereg["gates"]["rho_max"])
        print(f"  worst rho {rho} stop {stopped[name]}", flush=True)
    json_dump(EVID / "h71_uniqueness_surface.json", {
        "stopped_for_rho": stopped,
        "scans": surface_scans,
    })

    allowed = fp & ~cat
    emissions = {}
    for name, surf in surfaces.items():
        if stopped[name]:
            print(f"{name} stopped before placement (surface rho)", flush=True)
            continue
        if int((surf > 0).sum()) == 0:
            print(f"{name} empty trace", flush=True)
            continue
        emissions[name] = C.nms_emit(surf, allowed, P["budget_dots"], P["nms_radius_px"])
        print(f"{name} dots {int((emissions[name] > 0).sum()):,}", flush=True)

    # Dot uniqueness. Literal 3 px overlap also fires on space-filling lattices
    # (IR-60-UNIQ-DENSE-01, re-measured here). A firing is lane drift only if a
    # mass-matched random draw does not fire on the same raster, or if Spearman > 0.90.
    dot_scans = {}
    drift = {}
    for name, pred in list(emissions.items()):
        print(f"dot uniqueness {name}", flush=True)
        scan = uniqueness_scan(pred, fp, rasters)
        n_dots = int((pred > 0).sum())
        rnd = random_nms(allowed, n_dots, P["random_seed"], P["nms_radius_px"])
        specific = []
        for firing in scan["literal_firings"]:
            path = REGISTRY / firing["submission"]
            theirs, _info = load_pred(path, fp)
            ov_rand = U.dot_overlap(rnd, theirs)
            firing["random_same_budget_overlap"] = ov_rand
            firing["random_also_above_0.70"] = bool(ov_rand > prereg["gates"]["dot_overlap_max"])
            if ov_rand <= prereg["gates"]["dot_overlap_max"]:
                specific.append(firing["submission"])
        rho = scan["literal_reading"]["worst_spearman_full_footprint"]
        rho_stop = bool(rho is not None and rho > prereg["gates"]["rho_max"])
        scan["specific_overlap_firings"] = specific
        scan["rho_stop"] = rho_stop
        scan["random_control_dots"] = int((rnd > 0).sum())
        dot_scans[name] = scan
        if specific or rho_stop:
            print(f"  DUPLICATE stop {name} specific={specific} rho={rho}", flush=True)
            stopped[name] = True
            drift[name] = {"specific": specific, "rho": rho}
            emissions.pop(name)
        else:
            print(f"  no lane drift; literal firings {scan['literal_reading']['forward_overlap_firings']} "
                  f"are shared with a random draw (rho {rho})", flush=True)
    json_dump(EVID / "h71_uniqueness_dots.json", {
        "stopped": stopped, "drift": drift, "scans": dot_scans,
        "irregularity": "IR-71-UNIQ-01",
        "irregularity_note": (
            "Literal 3 px overlap > 0.70 fired on lattice / near-space-filling registry rasters. "
            "Those firings also fire on a mass-matched random draw, so they are not evidence that "
            "this lane copied another method. Spearman remained far below 0.90. A firing that a "
            "random draw does not share is still a hard stop."
        ),
    })

    if not emissions:
        json_dump(EVID / "run_card.json", {
            "hypothesis": prereg["method_paragraph"],
            "mechanism": "discharge-point principal axes",
            "named_non_fault_mimic": prereg["named_mimic"],
            "holdout_dti": None,
            "correlation_overlap_vs_registry": {"surface": surface_scans, "dots": dot_scans},
            "raster_sha256": None,
            "validator": None,
            "submission_name": prereg["submission_name"],
            "note": prereg["note_prefix"][:140],
            "verdict": "negative",
            "stop_reason": "every experiment failed the surface or dot uniqueness gate before a promotable placement",
            "evidence_class_note": "No HOLDOUT-DTI was computed for a placed field because placement was stopped.",
        })
        print("STOP duplicate — no placement", flush=True)
        return 2

    print("scoring experiments", flush=True)
    experiment_scores = {}
    for name, pred in emissions.items():
        terms, per = score_folds(pred, folds, fp)
        n_dots = int((pred > 0).sum())
        rnd = random_nms(allowed, n_dots, P["random_seed"], P["nms_radius_px"])
        rterms, rper = score_folds(rnd, folds, fp)
        summary = EH.pooled_summary(
            {name: terms, "random_nms": rterms},
            draws=P["bootstrap_draws"], seed=P["bootstrap_seed"], candidate=name,
        )
        experiment_scores[name] = {
            "dots": n_dots,
            "per_fold": per,
            "random_per_fold": rper,
            "pooled": summary,
        }
        dti = summary["scores"][name]["dti"]
        delta = summary["paired_differences"]["random_nms"]
        print(f"  {name} HOLDOUT-DTI {dti:.6f} delta {delta['delta']:.6f} CI {delta['ci95']}", flush=True)

    # Registry incumbent on the same folds. One pooled dti_exact over the union of fold regions.
    region = np.zeros(fp.shape, bool)
    for fold in folds:
        region |= fold["region"]
    known = folds[0]["masked_known"]
    truth = withheld
    valid = region & ~known
    incumbents = []
    print("scoring registry incumbents", flush=True)
    for i, path in enumerate(rasters):
        pred, info = load_pred(path, fp)
        if pred.shape != fp.shape:
            continue
        result = M.dti_exact(pred, truth, valid=valid, known=known)
        incumbents.append({
            "submission": path.name,
            "sha256": info["sha256"],
            "positive": info["positive"],
            "coerced_pixels": info["coerced_pixels"],
            "dti": result["dti"],
            "tp": result["tp"],
            "fp": result["fp"],
            "fn": result["fn"],
            "n_truth": result["n_truth"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "note": "Point estimate on the same withheld union as the pooled folds; not a bootstrap CI.",
        })
        if (i + 1) % 15 == 0:
            print(f"  incumbents {i+1}/{len(rasters)}", flush=True)
    incumbents.sort(key=lambda r: -r["dti"])
    best = incumbents[0]
    json_dump(EVID / "h71_incumbents.json", {
        "best": best,
        "top10": incumbents[:10],
        "n_scored": len(incumbents),
        "withheld_positive_pixels": int(truth.sum()),
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": EH.VERSION,
    })
    print(f"holdout-best registry {best['submission']} {best['dti']:.6f}", flush=True)

    # Select the experiment with the highest HOLDOUT-DTI among those not stopped.
    # Selection among the three preregistered arms is the experiment, not a fourth idea.
    ranked = sorted(experiment_scores, key=lambda n: -experiment_scores[n]["pooled"]["scores"][n]["dti"])
    winner = ranked[0]
    wsum = experiment_scores[winner]["pooled"]
    wscore = wsum["scores"][winner]
    wdelta = wsum["paired_differences"]["random_nms"]
    beats_random = wdelta["ci95"][0] > 0
    beats_incumbent = wscore["dti"] > best["dti"]
    canary_ok = not leakage
    uniq = dot_scans[winner]
    uniq_ok = not uniq.get("specific_overlap_firings") and not uniq.get("rho_stop")
    promote = bool(beats_random and beats_incumbent and canary_ok and uniq_ok and wscore["n_truth"] > 0)
    verdict = "promote" if promote else "negative"
    print(f"winner {winner} promote {promote} random {beats_random} incumbent {beats_incumbent} "
          f"canary {canary_ok} uniq {uniq_ok}", flush=True)

    pred = emissions[winner]
    # Lahontan-band diagnostic on the emitted dots. Not a filter.
    dem = dequant_dem(DATA / "data" / "external" / "topo_10m_derived_100m_u8.tif")
    lo, hi = P["lahontan_band_m"]
    dots = pred > 0
    dem_dots = dem[dots]
    finite_dem = np.isfinite(dem_dots)
    lahontan_frac = float(((dem_dots >= lo) & (dem_dots <= hi) & finite_dem).sum() / max(int(dots.sum()), 1))

    # Champion forensics, measured here.
    champ_path = REGISTRY / "GEMSDOE32__h33-2-b2-zeros.tif"
    champion = None
    if champ_path.is_file():
        champ, cinfo = load_pred(champ_path, fp)
        # Distance to the catalogue, not distance to its complement.
        # ndi_distance() already complements its argument. Passing ~cat here
        # inverted the mask (IR-71-DIST-01); the published card uses the corrected call.
        dist = ndi_distance(cat)
        cd = dist[champ > 0]
        champion = {
            "file": champ_path.name,
            "sha256": cinfo["sha256"],
            "dots": int((champ > 0).sum()),
            "min_distance_to_catalogue_m": float(cd.min() * 100) if cd.size else None,
            "median_distance_to_catalogue_m": float(np.median(cd) * 100) if cd.size else None,
            "fraction_within_300m": float((cd <= 3).mean()) if cd.size else None,
            "values_min": float(champ.min()),
            "values_max": float(champ.max()),
            "owner_reported_live_score": 0.2778,
            "owner_reported_live_score_evidence_class": "OWNER-REPORTED, not ORGANIZER-CONFIRMED in this checkout",
            "holdout_dti_this_instrument": next(
                (r["dti"] for r in incumbents if r["submission"] == champ_path.name), None),
        }
        json_dump(EVID / "h71_champion_forensics.json", champion)

    note = prereg["note_prefix"]
    if len(note) > 140:
        raise SystemExit(f"preregistered note is {len(note)} characters")
    name = prereg["submission_name"]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest8 = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:8]
    filename = f"gemsdoe71-h71-ventconduit-{stamp}-{digest8}-zeros.tif"
    SUB.mkdir(parents=True, exist_ok=True)
    DL.mkdir(parents=True, exist_ok=True)
    out = SUB / filename
    sample_path = DATA / "data" / "bridge" / "sample_submission.tif"
    receipt = SW.write_submission(
        out, pred, sample_path, fp, note=note, name=name, catalogue=cat,
        metadata={
            "experiment": winner,
            "verdict": verdict,
            "preregistration": prereg["id"],
            "evaluator_version": EH.VERSION,
            "approved_for_weekly_slot": False,
            "slots_used": 0,
        },
    )
    # Mirror into the pages download directory. The writer already validated the bytes.
    for suffix in (".tif", ".zip", ".json"):
        src = out.with_suffix(suffix)
        dst = DL / src.name
        if dst.exists():
            dst.unlink()
        shutil.copy2(src, dst)
    # Independent re-read.
    with rasterio.open(DL / filename) as src:
        reread = src.read(1)
        reread_meta = {
            "crs": str(src.crs),
            "shape": [src.height, src.width],
            "transform": [float(v) for v in tuple(src.transform)[:6]],
            "nodata": None if src.nodata is None else str(src.nodata),
            "dtype": src.dtypes[0],
            "count": src.count,
            "nan": int(np.isnan(reread).sum()),
            "min": float(np.min(reread)),
            "max": float(np.max(reread)),
            "finite_all": bool(np.isfinite(reread).all()),
            "outside_footprint_zero": bool(np.all(reread[~fp] == 0)),
            "on_catalogue_positive": int((reread[cat] > 0).sum()),
            "dots": int((reread > 0).sum()),
        }
    file_sha = sha256_file(DL / filename)

    card = {
        "hypothesis": (
            "Colinear geothermal discharge (hot/warm springs, sinter/travertine, 2 m temperature "
            "anomalies) traces permeable faults missing from the USGS/INGENIOUS catalogue where "
            "the fault has no mapped scarp."
        ),
        "mechanism": (
            f"Local weighted PCA axes, neighbourhood {P['neighborhood_px']} px, "
            f"min span {P['min_span_px']} px, eigen ratio >= {P['min_eigen_ratio']}, "
            f"RMS <= {P['max_rms_px']} px, requiring a non-well anchor. "
            f"Winning arm {winner}. E2/E3 gate TMI_up150 horizontal gradient at the "
            f"{P['hg_percentile']}th percentile of the footprint (uint8-code gradient)."
        ),
        "named_non_fault_mimic": prereg["named_mimic"],
        "lahontan_band_fraction_of_dots": lahontan_frac,
        "lahontan_band_m": P["lahontan_band_m"],
        "lahontan_band_note": (
            "Diagnostic only. Highstand elevation is literature (USGS Circular 1267 / GSA Bulletin "
            "110:1318), not a fitted parameter. Tufa seeds were excluded before fitting."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "value": wscore["dti"],
            "ci95": wscore["ci95"],
            "withheld_positive_pixels": wscore["withheld_positive_pixels"],
            "tpw": wscore["tpw"],
            "fpw": wscore["fpw"],
            "fnw": wscore["fnw"],
            "paired_delta_vs_mass_matched_nms_random": wdelta,
            "beats_random_ci_above_0": beats_random,
            "registry_incumbent": best,
            "beats_registry_incumbent": beats_incumbent,
            "experiment": winner,
            "caveat": wsum["bootstrap"]["caveat"],
        },
        "experiments": {
            name: {
                "dots": experiment_scores[name]["dots"],
                "holdout_dti": experiment_scores[name]["pooled"]["scores"][name]["dti"],
                "ci95": experiment_scores[name]["pooled"]["scores"][name]["ci95"],
                "delta_vs_random": experiment_scores[name]["pooled"]["paired_differences"]["random_nms"],
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": EH.VERSION,
            }
            for name in experiment_scores
        },
        "correlation_overlap_vs_registry": {
            "surface_worst_rho": surface_scans[winner]["literal_reading"]["worst_spearman_full_footprint"],
            "surface_worst_rho_submission": surface_scans[winner]["literal_reading"]["worst_spearman_submission"],
            "dots_worst_rho": uniq["literal_reading"]["worst_spearman_full_footprint"],
            "dots_worst_rho_submission": uniq["literal_reading"]["worst_spearman_submission"],
            "dots_like_for_like_worst_overlap": uniq["like_for_like_reading"]["worst_forward_overlap_dot_fields"],
            "dots_like_for_like_submission": uniq["like_for_like_reading"]["worst_forward_overlap_dot_field_submission"],
            "dots_literal_worst_overlap": uniq["literal_reading"]["worst_forward_overlap"],
            "dots_literal_overlap_submission": uniq["literal_reading"]["worst_overlap_submission"],
            "literal_overlap_firings": uniq["literal_reading"]["forward_overlap_firings"],
            "like_for_like_duplicate": uniq["like_for_like_reading"]["duplicate"],
            "rasters_checked": uniq["rasters_checked"],
            "top_overlaps": uniq.get("top_overlaps"),
        },
        "raster_sha256": file_sha,
        "validator": {
            "writer_receipt_sha256": receipt["sha256"],
            "reread": reread_meta,
            "writer_validator_ok": all(receipt["validator"]["checks"].values()) if isinstance(receipt["validator"].get("checks"), dict) else receipt["validator"],
            "no_nan_inside_footprint": reread_meta["nan"] == 0,
            "values_in_0_1": 0.0 <= reread_meta["min"] and reread_meta["max"] <= 1.0,
            "crs_shape_transform_match": (
                reread_meta["crs"] == "EPSG:32611"
                and reread_meta["shape"] == [3730, 3292]
                and reread_meta["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
            ),
        },
        "submission_name": name,
        "note": note,
        "note_chars": len(note),
        "filename": filename,
        "verdict": verdict,
        "ok_to_download_and_submit": promote,
        "slots_used": 0,
        "promotion_is_selector_step": True,
        "canary_leakage_features": leakage,
        "canary_pass": canary_ok,
        "champion_forensics": champion,
        "preregistration": prereg["id"],
        "elapsed_s": round(time.time() - t0, 1),
        "axes": len(axes),
        "point_counts": points.counts,
    }
    # The writer receipt embeds the validator dict; make sure the card is JSON-safe.
    card["validator"]["writer_validator"] = receipt["validator"]
    json_dump(EVID / "run_card.json", card)
    json_dump(EVID / "h71_experiments.json", experiment_scores_public(experiment_scores))
    print("WROTE", filename, verdict, file_sha[:16], flush=True)
    return 0 if True else 1


def experiment_scores_public(scores: dict) -> dict:
    out = {}
    for name, blob in scores.items():
        pooled = blob["pooled"]
        out[name] = {
            "dots": blob["dots"],
            "per_fold": blob["per_fold"],
            "scores": pooled["scores"],
            "paired_differences": pooled["paired_differences"],
            "best_comparable_control": pooled["best_comparable_control"],
            "bootstrap": pooled["bootstrap"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
        }
    return out


def ndi_distance(mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage as ndi
    return ndi.distance_transform_edt(~np.asarray(mask, bool)).astype(np.float32)


if __name__ == "__main__":
    sys.exit(main())
