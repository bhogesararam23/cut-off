"""List NISAR granules over the study box with asf_search. Listing only: nothing is downloaded."""

from __future__ import annotations

from typing import Any, Callable


def bbox_wkt(bbox: list[float]) -> str:
    w, s, e, n = bbox
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def summarise(results: Any) -> list[dict]:
    """One plain row per granule from asf_search results (missing fields become None)."""
    rows = []
    for r in results:
        p = r.properties
        rows.append({
            "name": p.get("fileID") or p.get("sceneName"),
            "start": p.get("startTime"),
            "track": p.get("pathNumber"),
            "frame": p.get("frameNumber"),
            "direction": p.get("flightDirection"),
            "size_mb": p.get("bytes") if isinstance(p.get("bytes"), (int, float)) else p.get("fileSize"),
        })
    return sorted(rows, key=lambda x: (str(x["track"]), str(x["start"])))


def list_granules(bbox: list[float], start: str, end: str, max_results: int = 200,
                  search: Callable[..., Any] | None = None) -> list[dict]:
    """Search ASF for NISAR L2 GCOV granules that intersect the box. `search` can be replaced in tests."""
    if search is None:
        import asf_search as asf

        def search(**kw):  # noqa: E306
            return asf.geo_search(dataset=asf.DATASET.NISAR, processingLevel="GCOV", **kw)

    return summarise(search(intersectsWith=bbox_wkt(bbox), start=start, end=end, maxResults=max_results))


def format_table(rows: list[dict]) -> str:
    if not rows:
        return "no granules found"
    lines = [f"{'track':>5} {'dir':<10} {'frame':>5}  {'start (UTC)':<22} granule"]
    for r in rows:
        lines.append(f"{str(r['track']):>5} {str(r['direction']):<10} {str(r['frame']):>5}  {str(r['start']):<22} {r['name']}")
    return "\n".join(lines)
