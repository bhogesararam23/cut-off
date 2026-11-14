"""Every endpoint serves exactly what is in the files, with the documented filters and errors."""

import json

import pytest

from conftest import EVENT, read_file

BASE = f"/api/events/{EVENT}"
RANK = {"low": 1, "medium": 2, "high": 3}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "version": "0.1.0"}


def test_events_list(client, mock_dir):
    r = client.get("/api/events")
    assert r.status_code == 200
    ev = read_file(mock_dir, "event.json")
    assert r.json() == [{"event_id": ev["event_id"], "name": ev["name"], "time_utc": ev["time_utc"], "bbox": ev["bbox"], "mock": ev["mock"]}]


@pytest.mark.parametrize("path,file", [
    (BASE, "event.json"), (f"{BASE}/stats", "stats.json"), (f"{BASE}/timeseries", "timeseries.json"),
    (f"{BASE}/timeline", "timeline.json"), (f"{BASE}/unknown", "unknown.geojson"), (f"{BASE}/roads", "roads.geojson"),
    (f"{BASE}/communities", "communities.geojson"), (f"{BASE}/landslides", "landslides.geojson"),
])
def test_endpoints_serve_the_file_unchanged(client, mock_dir, path, file):
    r = client.get(path)
    assert r.status_code == 200
    assert r.json() == read_file(mock_dir, file)


def test_pairs_have_absolute_image_urls_that_work(client, mock_dir):
    r = client.get(f"{BASE}/pairs")
    assert r.status_code == 200
    disk = read_file(mock_dir, "pairs.json")
    pairs = r.json()
    assert [p["id"] for p in pairs] == [p["id"] for p in disk]
    for p, d in zip(pairs, disk):
        for key in ("before_png", "after_png", "change_png"):
            assert p[key] == f"http://testserver/static/{EVENT}/{d[key]}"
        assert {k: v for k, v in p.items() if not k.endswith("_png")} == {k: v for k, v in d.items() if not k.endswith("_png")}
    img = client.get(pairs[0]["change_png"].replace("http://testserver", ""))
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_public_url_setting_is_used_for_image_links(mock_dir):
    from fastapi.testclient import TestClient
    from main import create_app

    c = TestClient(create_app(data_dir=mock_dir, public_url="https://api.example.com/"))
    assert c.get(f"{BASE}/pairs").json()[0]["before_png"].startswith(f"https://api.example.com/static/{EVENT}/hv_")


def test_landslide_filters(client, mock_dir):
    disk = read_file(mock_dir, "landslides.geojson")["features"]
    for level in ("low", "medium", "high"):
        r = client.get(f"{BASE}/landslides", params={"min_confidence": level})
        want = [f for f in disk if RANK[f["properties"]["confidence"]] >= RANK[level]]
        assert r.status_code == 200 and r.json()["features"] == want
    areas = sorted(f["properties"]["area_m2"] for f in disk)
    cut = areas[len(areas) // 2]
    r = client.get(f"{BASE}/landslides", params={"min_area_m2": cut})
    assert r.json()["features"] == [f for f in disk if f["properties"]["area_m2"] >= cut]
    both = client.get(f"{BASE}/landslides", params={"min_confidence": "high", "min_area_m2": cut}).json()["features"]
    assert both == [f for f in disk if f["properties"]["confidence"] == "high" and f["properties"]["area_m2"] >= cut]
    assert client.get(f"{BASE}/landslides", params={"min_area_m2": 1e9}).json() == {"type": "FeatureCollection", "features": []}


def test_road_and_community_filters(client, mock_dir):
    roads = read_file(mock_dir, "roads.geojson")["features"]
    r = client.get(f"{BASE}/roads", params={"status": "blocked,at_risk"})
    assert r.json()["features"] == [f for f in roads if f["properties"]["status"] in ("blocked", "at_risk")]
    assert {f["properties"]["status"] for f in client.get(f"{BASE}/roads?status=clear").json()["features"]} == {"clear"}
    comms = read_file(mock_dir, "communities.geojson")["features"]
    r = client.get(f"{BASE}/communities", params={"status": "cut_off"})
    assert r.json()["features"] == [f for f in comms if f["properties"]["status"] == "cut_off"] and r.json()["features"]


@pytest.mark.parametrize("url", [
    f"{BASE}/landslides?min_confidence=extreme", f"{BASE}/landslides?min_confidence=", f"{BASE}/landslides?min_confidence=HIGH",
    f"{BASE}/landslides?min_area_m2=-1", f"{BASE}/landslides?min_area_m2=abc", f"{BASE}/landslides?min_area_m2=1e12",
    f"{BASE}/landslides?min_area_m2=nan", f"{BASE}/landslides?min_area_m2=inf",
    f"{BASE}/roads?status=bogus", f"{BASE}/roads?status=blocked,bogus", f"{BASE}/roads?status=", f"{BASE}/roads?status=blocked,,clear",
    f"{BASE}/roads?status=" + "blocked," * 20, f"{BASE}/communities?status=blocked", f"{BASE}/communities?status=cut_off;drop",
])
def test_bad_query_values_are_422_without_echoing_input(client, url):
    r = client.get(url)
    assert r.status_code == 422
    assert r.json() == {"detail": "invalid query value"}


def test_one_landslide(client, mock_dir):
    first = read_file(mock_dir, "landslides.geojson")["features"][0]
    r = client.get(f"{BASE}/landslides/{first['properties']['id']}")
    assert r.status_code == 200 and r.json() == first


@pytest.mark.parametrize("path", [
    f"{BASE}/landslides/L9999", f"{BASE}/landslides/l0001", f"{BASE}/communities/12345/route", f"{BASE}/communities/none/route",
])
def test_missing_features_are_404(client, path):
    r = client.get(path)
    assert r.status_code == 404 and r.json() == {"detail": "feature not found"}


def test_unknown_event_is_404_everywhere(client):
    for suffix in ("", "/pairs", "/landslides", "/landslides/L0001", "/unknown", "/roads", "/communities",
                   "/communities/1/route", "/stats", "/timeseries", "/timeline"):
        r = client.get(f"/api/events/other-event{suffix}")
        assert r.status_code == 404 and r.json() == {"detail": "event not found"}, suffix
    assert client.get("/static/other-event/a.png").json() == {"detail": "event not found"}


def test_community_route(tree, tree_client):
    path = tree / EVENT / "communities.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["features"][0]["properties"]["osm_id"] = "node-1"
    path.write_text(json.dumps(data), encoding="utf-8")
    p = data["features"][0]["properties"]
    r = tree_client.get(f"{BASE}/communities/node-1/route")
    assert r.status_code == 200
    assert r.json() == {"status": p["status"], "reason": p["reason"], "nearest_hub": p["nearest_hub"]}


def test_static_files(client):
    ok = client.get(f"/static/{EVENT}/hv_change_t141d.png")
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    js = client.get(f"/static/{EVENT}/stats.json")
    assert js.status_code == 200 and js.headers["content-type"] == "application/json"
    geo = client.get(f"/static/{EVENT}/landslides.geojson")
    assert geo.status_code == 200 and geo.headers["content-type"].startswith("application/geo+json")
    for bad in ("nope.png", "hv_change_t141d.txt", "README", "HV_change_t141d.png"):
        assert client.get(f"/static/{EVENT}/{bad}").status_code == 404


def test_missing_file_in_an_existing_event(tree, tree_client):
    (tree / EVENT / "timeseries.json").unlink()
    r = tree_client.get(f"{BASE}/timeseries")
    assert r.status_code == 404 and r.json() == {"detail": "data not found"}


def test_event_list_skips_unusable_events(tree, tree_client):
    (tree / "broken-one").mkdir()
    (tree / "broken-one" / "event.json").write_text('{"event_id": 1}', encoding="utf-8")
    (tree / "no-event-file").mkdir()
    assert [e["event_id"] for e in tree_client.get("/api/events").json()] == [EVENT]


def test_responses_are_cached_for_five_minutes(client):
    r = client.get(f"{BASE}/stats")
    assert r.headers["cache-control"] == "public, max-age=300"
    assert client.get(f"{BASE}/nope").headers["cache-control"] == "no-store"


def test_edited_files_are_picked_up(tree, tree_client):
    first = tree_client.get(f"{BASE}/stats").json()
    path = tree / EVENT / "stats.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["landslides"] = first["landslides"] + 1000
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    assert tree_client.get(f"{BASE}/stats").json()["landslides"] == first["landslides"] + 1000


def test_docs_list_every_endpoint(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/health", "/api/events", "/api/events/{event_id}", "/api/events/{event_id}/pairs", "/api/events/{event_id}/landslides",
        "/api/events/{event_id}/landslides/{landslide_id}", "/api/events/{event_id}/unknown", "/api/events/{event_id}/roads",
        "/api/events/{event_id}/communities", "/api/events/{event_id}/communities/{osm_id}/route", "/api/events/{event_id}/stats",
        "/api/events/{event_id}/timeseries", "/api/events/{event_id}/timeline", "/static/{event_id}/{file_name}",
    }
    assert set(spec) == expected
    assert all(set(methods) == {"get"} for methods in spec.values())
