"""Slope, aspect and the shadow/layover mask from a DEM.

The DEM must already be on the radar grid: north-up, in a metric coordinate system.
Angles are in degrees. Aspect is the compass direction the slope faces (downhill), clockwise from north.
"""

from __future__ import annotations

import numpy as np

# Satellite heading (direction of travel) used when the file metadata does not give one.
DEFAULT_HEADINGS = {"ascending": 350.0, "descending": 190.0}


def slope_aspect(dem: np.ndarray, pixel_x_m: float, pixel_y_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (slope_deg, aspect_deg). Flat ground has aspect 0 and slope 0."""
    z = np.asarray(dem, dtype="float64")
    d_row, d_col = np.gradient(z, pixel_y_m, pixel_x_m)   # rows increase southwards, columns eastwards
    dz_east, dz_north = d_col, -d_row
    slope = np.degrees(np.arctan(np.hypot(dz_east, dz_north)))
    aspect = np.degrees(np.arctan2(-dz_east, -dz_north)) % 360.0   # downhill direction
    return slope.astype("float32"), aspect.astype("float32")


def look_azimuth(direction: str, heading_deg: float | None = None) -> float:
    """Compass direction the radar looks towards. NISAR looks to the right of its heading."""
    if heading_deg is None:
        if direction not in DEFAULT_HEADINGS:
            raise ValueError(f"direction must be 'ascending' or 'descending', got {direction!r}")
        heading_deg = DEFAULT_HEADINGS[direction]
    return (heading_deg + 90.0) % 360.0


def shadow_layover(slope_deg: np.ndarray, aspect_deg: np.ndarray, look_az_deg: float,
                   incidence_deg: float) -> np.ndarray:
    """True where the radar cannot see the ground properly (layover, shadow, or no DEM).

    Slope in the range plane: s = atan(tan(slope) * -cos(aspect - look_azimuth)).
    Layover when s >= incidence; shadow when s <= -(90 - incidence).
    """
    s_r = np.degrees(np.arctan(np.tan(np.radians(slope_deg)) * -np.cos(np.radians(aspect_deg - look_az_deg))))
    layover = s_r >= incidence_deg
    shadow = s_r <= -(90.0 - incidence_deg)
    no_data = ~np.isfinite(slope_deg) | ~np.isfinite(aspect_deg)
    return layover | shadow | no_data
