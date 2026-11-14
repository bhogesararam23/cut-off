"""Cut roads and places for the study area out of an OpenStreetMap extract (.osm.pbf).

The extract is untrusted input: it is only opened with the maintained GDAL reader, never executed or unpacked.
Output files are plain lon/lat GeoJSON in the shape access.py reads: roads (osm_id, name, highway) and
places (osm_id, name, place, population).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROAD_CLASSES = ("trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "track")
PLACE_CLASSES = ("town", "village", "hamlet")
NAME_MAX = 120
TAG_RE = re.compile(r'"((?:[^"\\]|\\.)*)"=>"((?:[^"\\]|\\.)*)"')


def parse_other_tags(text: str | None) -> dict[str, str]:
    """GDAL's OSM reader keeps rare tags in one hstore-style string: "key"=>"value","key2"=>"value2"."""
    if not text:
        return {}
    return {k.replace('\\"', '"'): v.replace('\\"', '"') for k, v in TAG_RE.findall(text)}


def clean_name(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value[:NAME_MAX] or None


def population(tags: dict[str, str]) -> int | None:
    digits = re.sub(r"[^0-9]", "", tags.get("population", ""))
    return int(digits) if digits and len(digits) <= 9 else None


def _feature(geom: dict, props: dict) -> dict:
    return {"type": "Feature", "properties": props, "geometry": geom}


def extract(pbf: Path, bbox: tuple[float, float, float, float], out_dir: Path) -> dict:
    """Write roads.geojson and places.geojson for bbox = (west, south, east, north). Returns counts."""
    import shapely
    from pyogrio import read_dataframe

    pbf, out_dir = Path(pbf), Path(out_dir)
    if not pbf.is_file():
        raise FileNotFoundError(f"OpenStreetMap extract not found: {pbf}")
    out_dir.mkdir(parents=True, exist_ok=True)

    roads = read_dataframe(pbf, layer="lines", bbox=bbox, where="highway IN (" + ",".join(f"'{c}'" for c in ROAD_CLASSES) + ")")
    road_feats = []
    for _, r in roads.iterrows():
        if r.geometry is None or r.geometry.is_empty:
            continue
        road_feats.append(_feature(json.loads(shapely.to_geojson(shapely.set_precision(r.geometry, 1e-6))),
                                   {"osm_id": str(r["osm_id"]), "name": clean_name(r["name"]), "highway": r["highway"]}))

    places = read_dataframe(pbf, layer="points", bbox=bbox, where="place IN (" + ",".join(f"'{c}'" for c in PLACE_CLASSES) + ")")
    place_feats = []
    for _, r in places.iterrows():
        name = clean_name(r["name"])
        if not name or r.geometry is None:
            continue
        place_feats.append(_feature(json.loads(shapely.to_geojson(shapely.set_precision(r.geometry, 1e-6))),
                                    {"osm_id": str(r["osm_id"]), "name": name, "place": r["place"],
                                     "population": population(parse_other_tags(r.get("other_tags")))}))

    for name, feats in (("roads.geojson", road_feats), ("places.geojson", place_feats)):
        (out_dir / name).write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                                               separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    by_class = {c: sum(f["properties"]["highway"] == c for f in road_feats) for c in ROAD_CLASSES}
    by_place = {c: sum(f["properties"]["place"] == c for f in place_feats) for c in PLACE_CLASSES}
    return {"roads": len(road_feats), "roads_by_class": by_class, "places": len(place_feats), "places_by_class": by_place,
            "places_with_population": sum(f["properties"]["population"] is not None for f in place_feats)}
