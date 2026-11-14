"""A synthetic scene for the validation protocol: 20 landslide patches with graded drops (-5 to -9 dB) and three
"wet ground" decoys on forest (-2 dB). Any threshold from -2.5 to -4.5 dB separates them perfectly, so tuning has an answer."""

from __future__ import annotations

import numpy as np
from affine import Affine
from pyproj import Transformer

import synth
from synth import LAT0, LON0, N, UTM, _power, _write

PATCH_PX = 16                    # native 10 m pixels: a 160 m square
DROPS = [-5.0 - 4.0 * k / 19 for k in range(20)]
PATCHES = [(40 + 70 * (k % 5), 40 + 70 * (k // 5)) for k in range(20)]            # (col, row) of the top-left corner
TRAPS = [(350, 40), (350, 160), (350, 280)]                                        # 40 x 40 px decoys, clear of the patches
TRAP_PX = 40
TRAP_DROP = -2.0


def _lonlat(transform: Affine, col: float, row: float) -> tuple[float, float]:
    x, y = transform * (col, row)
    lon, lat = Transformer.from_crs(UTM, 4326, always_xy=True).transform(x, y)
    return round(lon, 6), round(lat, 6)


def build(root):
    """Rasters + config (single pair) + points.csv text. Returns (cfg, csv_text)."""
    cfg = synth.build(root)                                    # DEM, bbox and the standard files
    cfg["pairs"] = cfg["pairs"][:1]
    cfg["detect"] = dict(cfg["detect"], threshold_db=-1.5)       # a starting value that flags the decoys
    rng = np.random.default_rng(11)
    x0, y0 = Transformer.from_crs(4326, UTM, always_xy=True).transform(LON0, LAT0)
    transform = Affine(10, 0, x0, 0, -10, y0)
    flat = np.full((N, N), -12.0)
    after = flat.copy()
    for (c, r), drop in zip(PATCHES, DROPS):
        after[r:r + PATCH_PX, c:c + PATCH_PX] += drop
    for c, r in TRAPS:
        after[r:r + TRAP_PX, c:c + TRAP_PX] += TRAP_DROP
    raw = root / "data" / "raw"
    _write(raw / "t141_before.tif", _power(rng, flat), transform, UTM)
    _write(raw / "t141_after.tif", _power(rng, after), transform, UTM)

    rows = ["id,lon,lat,label,size,notes"]
    sizes = ["small", "medium", "large"]
    for k, (c, r) in enumerate(PATCHES):
        lon, lat = _lonlat(transform, c + PATCH_PX / 2, r + PATCH_PX / 2)
        rows.append(f"L{k + 1:03d},{lon},{lat},landslide,{sizes[k % 3]},")
    n = 0
    for c, r in TRAPS:                                          # 4 forest points inside each decoy
        for dc, dr in ((10, 10), (30, 10), (10, 30), (30, 30)):
            n += 1
            lon, lat = _lonlat(transform, c + dc, r + dr)
            rows.append(f"F{n:03d},{lon},{lat},forest,,")
    for k in range(12):                                         # 12 on stable forest, away from every patch and decoy
        n += 1
        lon, lat = _lonlat(transform, 60 + 25 * k, 360)
        rows.append(f"F{n:03d},{lon},{lat},forest,,")
    return cfg, "\n".join(rows) + "\n"
