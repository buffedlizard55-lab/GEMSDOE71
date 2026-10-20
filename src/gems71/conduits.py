"""Discharge-conduit lineaments for the GeoDAWN grid.

No function in this module reads a distance-to-catalogue column. Callers that
need a catalogue mask pass a boolean raster they computed themselves from the
published fault grid.
"""

from __future__ import annotations

import csv
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

FORBIDDEN_COLUMNS = (
    "dist_known_fault_px",
    "dist_known_fault",
    "distance_to_fault",
    "dist_fault",
)

# Deposit types that are discharge or hydrothermal products, not lake-shore tufa
# and not undifferentiated silica-cemented sediment.
PALEO_KEEP_EXACT = {
    "Travertine",
    "Sinter",
    "Sinter and silicified zone",
    "Alteration",
    "Explosion craters",
    "Sulfur",
    "Sulfate crust",
    "Hydrothermally altered deposits",
    "Silicified fault breccia",
    "Calcite-qtz veins",
    "Silica vein",
    "Argillic alteration",
    "Travertine?",
}
PALEO_DROP_SUBSTR = ("tufa", "silica-cemented sand", "silica-cemented mud")


def _fnum(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.upper() == "NULL" or text.lower() == "nan":
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    if not math.isfinite(out):
        return None
    return out


def assert_columns_unused(fieldnames: list[str], used: set[str]) -> None:
    leaked = [c for c in fieldnames if c in FORBIDDEN_COLUMNS and c in used]
    if leaked:
        raise RuntimeError(f"refusing to use label-derived columns: {leaked}")
    present = [c for c in fieldnames if c in FORBIDDEN_COLUMNS]
    if present and present[0] in used:
        raise RuntimeError("label-derived column was used")


@dataclass
class PointSet:
    row: np.ndarray
    col: np.ndarray
    weight: np.ndarray
    anchor: np.ndarray
    kind: np.ndarray
    counts: dict


def utm_to_rowcol(easting: np.ndarray, northing: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Inverse of the pinned EPSG:32611 100 m geotransform.

    x = 243350 + col * 100, y = 4508550 - row * 100.
    """
    col = (np.asarray(easting, dtype=np.float64) - 243350.0) / 100.0
    row = (4508550.0 - np.asarray(northing, dtype=np.float64)) / 100.0
    return row, col


def _inside(row: np.ndarray, col: np.ndarray, shape: tuple[int, int], footprint: np.ndarray):
    rr = np.rint(row).astype(np.int32)
    cc = np.rint(col).astype(np.int32)
    ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
    ok[ok] &= footprint[rr[ok], cc[ok]]
    return rr, cc, ok


def load_discharge_points(
    wellspring_csv: Path,
    paleo_zip: Path,
    vents_csv: Path,
    probes_xlsx: Path | None,
    footprint: np.ndarray,
    *,
    probe_dab_min: float = 2.0,
    geotherm_anchor: float = 120.0,
) -> PointSet:
    """Load discharge seeds. ``dist_known_fault_px`` is never read into an array."""
    shape = footprint.shape
    rows, cols, weights, anchors, kinds = [], [], [], [], []
    counts = {
        "wellspring_rows": 0,
        "springs_used": 0,
        "wells_used": 0,
        "wells_anchor": 0,
        "paleo_rows": 0,
        "paleo_used": 0,
        "paleo_dropped_tufa_or_sand": 0,
        "paleo_outside": 0,
        "vents_rows": 0,
        "vents_used": 0,
        "probes_rows": 0,
        "probes_used": 0,
        "forbidden_columns_present": [],
        "forbidden_columns_used": [],
    }

    with Path(wellspring_csv).open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        forbidden = [c for c in fields if c in FORBIDDEN_COLUMNS]
        counts["forbidden_columns_present"] = forbidden
        used = {"layer", "thermalclass", "row", "col", "temp_c",
                "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
        if set(forbidden) & used:
            raise RuntimeError("wellspring loader requested a label-derived column")
        for rec in reader:
            counts["wellspring_rows"] += 1
            r = _fnum(rec.get("row"))
            c = _fnum(rec.get("col"))
            if r is None or c is None:
                continue
            layer = (rec.get("layer") or "").lower()
            thermal = (rec.get("thermalclass") or "").strip().lower()
            temp = _fnum(rec.get("temp_c"))
            geos = [
                _fnum(rec.get("geothermquartz_c")),
                _fnum(rec.get("geothermchalc_c")),
                _fnum(rec.get("geothermcat_c")),
            ]
            geo_max = max([g for g in geos if g is not None], default=None)
            is_spring = "spring" in layer
            is_well = "well" in layer and not is_spring
            hot = thermal.startswith("hot") or (temp is not None and temp >= 50.0)
            warm = thermal.startswith("warm") or (
                temp is not None and temp >= (30.0 if is_spring else 40.0)
            )
            if is_spring and hot:
                w, kind, anchor = 3.0, "spring_hot", True
            elif is_spring and warm:
                w, kind, anchor = 2.0, "spring_warm", True
            elif is_spring and geo_max is not None and geo_max >= geotherm_anchor:
                w, kind, anchor = 2.0, "spring_geo", True
            elif is_well and hot:
                w, kind = 1.5, "well_hot"
                anchor = geo_max is not None and geo_max >= geotherm_anchor
            elif is_well and (warm or (geo_max is not None and geo_max >= geotherm_anchor)):
                w, kind = 0.8, "well_warm"
                anchor = geo_max is not None and geo_max >= geotherm_anchor
            else:
                continue
            if anchor and is_well:
                counts["wells_anchor"] += 1
            rr, cc, ok = _inside(np.array([r]), np.array([c]), shape, footprint)
            if not ok[0]:
                continue
            rows.append(int(rr[0]))
            cols.append(int(cc[0]))
            weights.append(w)
            anchors.append(anchor)
            kinds.append(kind)
            counts["springs_used" if is_spring else "wells_used"] += 1

    with zipfile.ZipFile(paleo_zip) as zf:
        text = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
    paleo_fields = next(csv.reader([text.splitlines()[0]]))
    if any(c in FORBIDDEN_COLUMNS for c in paleo_fields):
        raise RuntimeError("unexpected label column in paleo table")
    from rasterio.warp import transform as rio_transform

    paleo_recs = list(csv.DictReader(text.splitlines()))
    keep_lon, keep_lat, keep_w = [], [], []
    for rec in paleo_recs:
        counts["paleo_rows"] += 1
        dtype = (rec.get("Deposit_type") or "").strip()
        low = dtype.lower()
        if any(s in low for s in PALEO_DROP_SUBSTR) or dtype not in PALEO_KEEP_EXACT:
            if "tufa" in low or "silica-cemented" in low:
                counts["paleo_dropped_tufa_or_sand"] += 1
            continue
        lon = _fnum(rec.get("Long_deg_NAD83"))
        lat = _fnum(rec.get("Lat_deg_NAD83"))
        if lon is None or lat is None:
            continue
        keep_lon.append(lon)
        keep_lat.append(lat)
        keep_w.append(2.5 if dtype in {"Sinter", "Travertine", "Sinter and silicified zone", "Travertine?"} else 1.5)
    if keep_lon:
        east, north = rio_transform("EPSG:4269", "EPSG:32611", keep_lon, keep_lat)
        row_f, col_f = utm_to_rowcol(east, north)
        rr, cc, ok = _inside(row_f, col_f, shape, footprint)
        counts["paleo_outside"] = int((~ok).sum())
        for i in np.flatnonzero(ok):
            rows.append(int(rr[i]))
            cols.append(int(cc[i]))
            weights.append(keep_w[i])
            anchors.append(True)
            kinds.append("paleo")
            counts["paleo_used"] += 1

    with Path(vents_csv).open(newline="") as fh:
        reader = csv.DictReader(fh)
        fields = list(reader.fieldnames or [])
        if "dist_known_fault_px" in fields:
            counts["forbidden_columns_present"].append("vents.dist_known_fault_px")
        for rec in reader:
            counts["vents_rows"] += 1
            r = _fnum(rec.get("row"))
            c = _fnum(rec.get("col"))
            if r is None or c is None:
                continue
            rr, cc, ok = _inside(np.array([r]), np.array([c]), shape, footprint)
            if not ok[0]:
                continue
            rows.append(int(rr[0]))
            cols.append(int(cc[0]))
            weights.append(0.5)
            anchors.append(True)
            kinds.append("vent")
            counts["vents_used"] += 1

    if probes_xlsx is not None and Path(probes_xlsx).is_file():
        import openpyxl

        wb = openpyxl.load_workbook(probes_xlsx, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        header = None
        for rec in ws.iter_rows(values_only=True):
            if header is None:
                header = [str(c) if c is not None else "" for c in rec]
                if any(c in FORBIDDEN_COLUMNS for c in header):
                    raise RuntimeError("unexpected label column in 2 m probe table")
                continue
            counts["probes_rows"] += 1
            data = {header[i]: rec[i] for i in range(min(len(header), len(rec)))}
            dab = _fnum(data.get("2mDAB"))
            east = _fnum(data.get("UTM_E_n83z11n"))
            north = _fnum(data.get("UTM_N_n83z11n"))
            if dab is None or east is None or north is None or dab < probe_dab_min:
                continue
            row_f, col_f = utm_to_rowcol([east], [north])
            rr, cc, ok = _inside(row_f, col_f, shape, footprint)
            if not ok[0]:
                continue
            rows.append(int(rr[0]))
            cols.append(int(cc[0]))
            weights.append(1.5)
            anchors.append(True)
            kinds.append("probe")
            counts["probes_used"] += 1
        wb.close()
    else:
        counts["probes_missing"] = True

    if not rows:
        return PointSet(
            row=np.zeros(0, np.int32), col=np.zeros(0, np.int32),
            weight=np.zeros(0, np.float64), anchor=np.zeros(0, bool),
            kind=np.zeros(0, dtype="U16"), counts=counts,
        )
    return PointSet(
        row=np.asarray(rows, np.int32),
        col=np.asarray(cols, np.int32),
        weight=np.asarray(weights, np.float64),
        anchor=np.asarray(anchors, bool),
        kind=np.asarray(kinds),
        counts=counts,
    )


def verify_wellspring_grid(wellspring_csv: Path, footprint: np.ndarray, n: int = 200) -> dict:
    """Check that published row/col match the pinned geotransform within 1 px."""
    mismatches = 0
    checked = 0
    max_err = 0.0
    with Path(wellspring_csv).open(newline="") as fh:
        for rec in csv.DictReader(fh):
            east, north = _fnum(rec.get("utm_x")), _fnum(rec.get("utm_y"))
            r, c = _fnum(rec.get("row")), _fnum(rec.get("col"))
            if None in (east, north, r, c):
                continue
            rr, cc = utm_to_rowcol([east], [north])
            err = max(abs(rr[0] - r), abs(cc[0] - c))
            max_err = max(max_err, float(err))
            if err > 1.0:
                mismatches += 1
            checked += 1
            if checked >= n:
                break
    return {"checked": checked, "mismatches_gt_1px": mismatches, "max_abs_err_px": max_err}


@dataclass
class Axis:
    y0: float
    x0: float
    y1: float
    x1: float
    quality: float
    n_points: int
    rms: float
    ratio: float


def fit_axes(points: PointSet, *, radius_px: float = 60.0, min_points: int = 3,
             min_span_px: float = 15.0, min_ratio: float = 3.5,
             max_rms_px: float = 3.5) -> list[Axis]:
    """Local weighted PCA axes. Wells-only neighbourhoods are rejected."""
    if points.row.size < min_points:
        return []
    # Aggregate identical cells so a borehole cluster is one sample, not a fake line.
    key = points.row.astype(np.int64) * 100_000 + points.col.astype(np.int64)
    uniq, inv = np.unique(key, return_inverse=True)
    n = uniq.size
    w = np.bincount(inv, weights=points.weight, minlength=n).astype(np.float64)
    anchor = np.zeros(n, bool)
    np.maximum.at(anchor, inv, points.anchor)
    row = (uniq // 100_000).astype(np.float64)
    col = (uniq % 100_000).astype(np.float64)
    xy = np.column_stack([row, col])
    tree = cKDTree(xy)
    axes: list[Axis] = []
    # Visit heavier cells first; cap the search so a 20k-cell cloud stays cheap.
    order = np.argsort(-w)
    if order.size > 8000:
        order = order[:8000]
    for i in order:
        if w[i] <= 0:
            continue
        neigh = tree.query_ball_point(xy[i], radius_px)
        if len(neigh) < min_points:
            continue
        neigh = np.asarray(neigh, np.int32)
        if not anchor[neigh].any():
            continue
        pts = xy[neigh]
        ww = w[neigh]
        ww = ww / ww.sum()
        centroid = (pts * ww[:, None]).sum(axis=0)
        delta = pts - centroid
        cov = (delta * ww[:, None]).T @ delta
        evals, evecs = np.linalg.eigh(cov)
        if evals[1] <= 1e-8:
            continue
        ratio = float(evals[1] / max(evals[0], 1e-8))
        if ratio < min_ratio:
            continue
        axis = evecs[:, 1]
        proj = delta @ axis
        span = float(proj.max() - proj.min())
        if span < min_span_px:
            continue
        perp = delta @ evecs[:, 0]
        rms = float(np.sqrt(np.average(perp * perp, weights=ww)))
        if rms > max_rms_px:
            continue
        quality = float(w[neigh].sum()) * min(ratio / 8.0, 1.5) * max(0.0, 1.0 - rms / max_rms_px)
        p0 = centroid + float(proj.min()) * axis
        p1 = centroid + float(proj.max()) * axis
        axes.append(Axis(float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1]),
                         quality, int(len(neigh)), rms, ratio))
    return axes


def bresenham(y0: float, x0: float, y1: float, x1: float) -> list[tuple[int, int]]:
    y, x = int(round(y0)), int(round(x0))
    y1i, x1i = int(round(y1)), int(round(x1))
    dy, dx = abs(y1i - y), abs(x1i - x)
    sy = 1 if y < y1i else -1
    sx = 1 if x < x1i else -1
    err = dx - dy
    pts = []
    for _ in range(dx + dy + 2):
        pts.append((y, x))
        if y == y1i and x == x1i:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return pts


def rasterize_axes(axes: list[Axis], shape: tuple[int, int], footprint: np.ndarray,
                   hg: np.ndarray | None = None, hg_min: float | None = None,
                   extend_px: int = 0) -> np.ndarray:
    """Max-quality trace. Optional magnetic gate and along-strike extension."""
    out = np.zeros(shape, np.float32)
    h, w = shape
    for ax in axes:
        pts = bresenham(ax.y0, ax.x0, ax.y1, ax.x1)
        if extend_px and hg is not None and hg_min is not None:
            direction = np.array([ax.y1 - ax.y0, ax.x1 - ax.x0], np.float64)
            norm = float(np.hypot(direction[0], direction[1]))
            if norm > 0:
                direction /= norm
                for sign, origin in ((1.0, (ax.y1, ax.x1)), (-1.0, (ax.y0, ax.x0))):
                    for step in range(1, extend_px + 1):
                        yy = int(round(origin[0] + sign * step * direction[0]))
                        xx = int(round(origin[1] + sign * step * direction[1]))
                        if not (0 <= yy < h and 0 <= xx < w):
                            break
                        val = hg[yy, xx]
                        if not np.isfinite(val) or val < hg_min:
                            break
                        pts.append((yy, xx))
        q = np.float32(ax.quality)
        for y, x in pts:
            if not (0 <= y < h and 0 <= x < w) or not footprint[y, x]:
                continue
            if hg is not None and hg_min is not None:
                val = hg[y, x]
                if not np.isfinite(val) or val < hg_min:
                    continue
            if q > out[y, x]:
                out[y, x] = q
    return out


def horizontal_gradient(code: np.ndarray) -> np.ndarray:
    """Gradient magnitude of a monotonic uint8 code. 0 is treated as nodata."""
    valid = code > 0
    t = code.astype(np.float32)
    gy = np.zeros(t.shape, np.float32)
    gx = np.zeros(t.shape, np.float32)
    gy[1:-1, :] = (t[2:, :] - t[:-2, :]) * 0.5
    gx[:, 1:-1] = (t[:, 2:] - t[:, :-2]) * 0.5
    hg = np.hypot(gy, gx)
    neighbor_ok = ndi.binary_erosion(valid, iterations=1)
    hg = np.where(neighbor_ok, hg, np.nan)
    return hg


def normalize_surface(trace: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Rank-normalize positive trace pixels into (0, 1]. Zeros stay zero."""
    out = np.zeros(trace.shape, np.float32)
    pos = footprint & (trace > 0)
    n = int(pos.sum())
    if n == 0:
        return out
    order = np.argsort(trace[pos], kind="mergesort")
    ranks = np.empty(n, np.float32)
    ranks[order] = (np.arange(1, n + 1, dtype=np.float32) / n)
    out[pos] = ranks
    return out


def nms_emit(surface: np.ndarray, allowed: np.ndarray, budget: int,
             radius_px: float = 3.0) -> np.ndarray:
    """Greedy Euclidean NMS. ``allowed`` is the only mask (footprint minus catalogue)."""
    pred = np.zeros(surface.shape, np.float32)
    yy, xx = np.nonzero(allowed & (surface > 0))
    if yy.size == 0 or budget <= 0:
        return pred
    score = surface[yy, xx]
    order = np.argsort(-score, kind="mergesort")
    r = int(math.floor(radius_px))
    offsets = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
               if dy * dy + dx * dx < radius_px * radius_px]
    taken = np.zeros(surface.shape, bool)
    h, w = surface.shape
    kept = 0
    for i in order:
        y = int(yy[i])
        x = int(xx[i])
        if taken[y, x]:
            continue
        pred[y, x] = 1.0
        kept += 1
        for dy, dx in offsets:
            yy2, xx2 = y + dy, x + dx
            if 0 <= yy2 < h and 0 <= xx2 < w:
                taken[yy2, xx2] = True
        if kept >= budget:
            break
    return pred


def density(points_row, points_col, shape, sigma_px: float = 3.0) -> np.ndarray:
    img = np.zeros(shape, np.float32)
    if len(points_row) == 0:
        return img
    np.add.at(img, (points_row, points_col), 1.0)
    return ndi.gaussian_filter(img, sigma=sigma_px, mode="constant")
