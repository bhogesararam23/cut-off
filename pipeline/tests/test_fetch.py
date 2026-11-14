from types import SimpleNamespace

from cutoff.fetch import bbox_wkt, format_table, list_granules, summarise


def fake(**props):
    return SimpleNamespace(properties=props)


def test_bbox_wkt_is_a_closed_ring():
    assert bbox_wkt([-81.0, 7.3, -80.3, 8.0]) == "POLYGON((-81.0 7.3,-80.3 7.3,-80.3 8.0,-81.0 8.0,-81.0 7.3))"


def test_summary_sorts_and_tolerates_missing_fields():
    rows = summarise([
        fake(fileID="B", startTime="2026-10-09T23:53:35Z", pathNumber=141, frameNumber=85, flightDirection="DESCENDING", bytes=1),
        fake(fileID="A", startTime="2026-09-27T23:53:35Z", pathNumber=141, frameNumber=85, flightDirection="DESCENDING"),
        fake(),
    ])
    assert [r["name"] for r in rows if r["name"]] == ["A", "B"] and any(r["name"] is None for r in rows)
    assert "granule" in format_table(rows) and format_table([]) == "no granules found"


def test_list_granules_passes_box_and_dates_and_downloads_nothing():
    calls = []

    def search(**kw):
        calls.append(kw)
        return [fake(fileID="G", startTime="t", pathNumber=1, frameNumber=2, flightDirection="ASCENDING")]

    rows = list_granules([-81.0, 7.3, -80.3, 8.0], "2026-09-01", "2026-10-31", search=search)
    assert calls[0]["intersectsWith"].startswith("POLYGON((-81.0 7.3") and calls[0]["start"] == "2026-09-01"
    assert rows[0]["name"] == "G"
