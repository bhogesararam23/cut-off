"""Attacks that must fail: path traversal, other origins, other methods, leaking errors."""

import pytest
from fastapi.testclient import TestClient

from conftest import EVENT, ORIGIN
from main import create_app, parse_origins

BASE = f"/api/events/{EVENT}"

# every way we could think of to name a file outside the event folder
ATTACKS = [
    "../secret.json", "../../secret.json", "../../../secret.json", "..%2fsecret.json", "..%2Fsecret.json",
    "%2e%2e/secret.json", "%2e%2e%2fsecret.json", "%2E%2E%2Fsecret.json", "..%252fsecret.json", "%252e%252e%252fsecret.json",
    "....//secret.json", "..;/secret.json", "..\\secret.json", "..%5csecret.json", "%5c..%5csecret.json",
    "..%c0%afsecret.json", "%c0%ae%c0%ae/secret.json", "%ef%bc%8e%ef%bc%8e/secret.json", "..%00/secret.json",
    "event.json%00.png", "stats.json%00", "/etc/passwd", "%2fetc%2fpasswd", "C:%5CWindows%5Cwin.ini", "C:/Windows/win.ini",
    "file:///etc/passwd", "~/.env", ".env", ".git/config", "..", ".", "%2e", "%2e%2e", "./stats.json", "stats.json/",
    "a" * 5000 + ".png", "%", "%zz", "stats.json?x=../../secret.json",
]

TEMPLATES = [
    "/static/" + EVENT + "/{a}",
    "/static/{a}/stats.json",
    "/api/events/{a}",
    "/api/events/{a}/stats",
    "/api/events/{a}/landslides",
    BASE + "/landslides/{a}",
    BASE + "/communities/{a}/route",
]


# The HTTP client itself resolves bare dot segments before sending (".." becomes the parent path), so what
# reaches the server for these is an ordinary, legitimate URL. They are only checked for leaking secrets.
CLIENT_NORMALISED = {"..", ".", "./stats.json", "stats.json/", "%2e", "%2e%2e"}
QUERY_FORMS = {"stats.json?x=../../secret.json"}


@pytest.mark.parametrize("template", TEMPLATES)
@pytest.mark.parametrize("attack", ATTACKS)
def test_traversal_attempts_never_reach_files_outside_the_event_folder(tree_client, template, attack):
    r = tree_client.get(template.format(a=attack))
    assert "TOP-SECRET" not in r.text and "root:" not in r.text and "[fonts]" not in r.text
    if attack in CLIENT_NORMALISED or attack in QUERY_FORMS:
        return
    assert r.status_code == 404, (template, attack, r.status_code)


@pytest.mark.parametrize("path", [
    f"/static/{EVENT}/..%2f..%2fsecret.json", f"/static/..%2fdata/{EVENT}/stats.json", "/static/%2e%2e/%2e%2e/secret.json",
    f"/static/{EVENT}/%2e%2e/root-secret.json", "/api/events/%2e%2e%2fdata", "/api/events/..%2fsecret",
])
def test_the_documented_attack_forms_return_404(tree_client, path):
    r = tree_client.get(path)
    assert r.status_code == 404 and "TOP-SECRET" not in r.text


def test_secrets_next_to_the_data_are_still_unreachable_by_name(tree_client):
    for name in ("root-secret.json", "secret.json", "passwd"):
        for path in (f"/static/{EVENT}/{name}", f"/static/data/{name}", f"/api/events/{name}"):
            assert tree_client.get(path).status_code == 404


# ---- other origins ----

def test_listed_origin_is_allowed(client):
    r = client.get(f"{BASE}/stats", headers={"Origin": ORIGIN})
    assert r.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-credentials" not in r.headers
    assert "vary" in r.headers and "origin" in r.headers["vary"].lower()


@pytest.mark.parametrize("origin", [
    "https://evil.example", "http://localhost:5173.evil.example", "https://cut-off.example.com.evil.example",
    "http://cut-off.example.com", "null", "https://sub.cut-off.example.com", "*",
])
def test_unlisted_origins_get_no_cors_headers(client, origin):
    r = client.get(f"{BASE}/stats", headers={"Origin": origin})
    assert r.status_code == 200                                    # the data is public; the browser just may not read it
    assert "access-control-allow-origin" not in r.headers


def test_preflight(client):
    ok = client.options(f"{BASE}/stats", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == ORIGIN
    assert ok.headers["access-control-allow-methods"] == "GET"
    for method in ("POST", "DELETE", "PUT"):
        bad = client.options(f"{BASE}/stats", headers={"Origin": ORIGIN, "Access-Control-Request-Method": method})
        assert bad.status_code == 400
    other = client.options(f"{BASE}/stats", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert other.status_code == 400 and "access-control-allow-origin" not in other.headers


def test_errors_carry_cors_headers_too(client):
    r = client.get(f"{BASE}/nope", headers={"Origin": ORIGIN})
    assert r.status_code == 404 and r.headers["access-control-allow-origin"] == ORIGIN


def test_origin_settings():
    assert parse_origins(None) == ["http://localhost:5173"]
    assert parse_origins("  ") == ["http://localhost:5173"]
    assert parse_origins("https://a.example/, http://localhost:5173") == ["https://a.example", "http://localhost:5173"]
    for bad in ("*", "https://*.example.com", "example.com", "https://a.example,*", "ftp://a.example", "javascript:alert(1)"):
        with pytest.raises(ValueError):
            parse_origins(bad)


# ---- only GET ----

PATHS = ["/api/health", "/api/events", BASE, f"{BASE}/stats", f"{BASE}/landslides", f"{BASE}/landslides/L0001",
         f"{BASE}/communities/x/route", f"/static/{EVENT}/hv_change_t141d.png"]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete", "head", "options", "trace"])
def test_only_get_is_answered(client, path, method):
    r = client.request(method.upper(), path)
    assert r.status_code == 405, (method, path, r.status_code)


def test_nothing_is_written(tree, tree_client):
    before = sorted((p.name, p.stat().st_size) for p in (tree / EVENT).iterdir())
    for path in PATHS:
        tree_client.post(path, json={"a": 1})
        tree_client.put(path, content=b"x")
        tree_client.delete(path)
    assert sorted((p.name, p.stat().st_size) for p in (tree / EVENT).iterdir()) == before


# ---- no leaks ----

def test_a_damaged_file_gives_a_generic_error_not_a_trace(tree, tree_client):
    (tree / EVENT / "landslides.geojson").write_text('{"type": "FeatureCollection", "features": [{"oops": 1}]}', encoding="utf-8")
    (tree / EVENT / "roads.geojson").write_text("{not json", encoding="utf-8")
    for path in (f"{BASE}/landslides", f"{BASE}/roads", f"{BASE}/landslides/L0001"):
        r = tree_client.get(path)
        assert r.status_code == 500 and r.json() == {"detail": "internal error"}
        for leak in ("Traceback", "ValidationError", "pydantic", str(tree), "oops", "line 1"):
            assert leak not in r.text


def test_an_unexpected_crash_is_generic_too(tree):
    app = create_app(data_dir=tree)

    def boom(*_a, **_k):
        raise RuntimeError("secret internal detail at C:\\private\\path")

    app.state  # noqa: B018
    import main as main_module
    store_cls = main_module.DataStore
    original = store_cls.load_json
    store_cls.load_json = boom
    try:
        r = TestClient(app, raise_server_exceptions=False).get(f"{BASE}/stats")
    finally:
        store_cls.load_json = original
    assert r.status_code == 500 and r.json() == {"detail": "internal error"}
    assert "secret internal detail" not in r.text and "private" not in r.text


def test_the_app_is_not_in_debug_mode(client):
    assert client.app.debug is False


def test_safety_headers_on_every_kind_of_response(client):
    for path in (f"{BASE}/stats", f"/static/{EVENT}/hv_change_t141d.png", f"{BASE}/nope", f"{BASE}/roads?status=x"):
        r = client.get(path)
        assert r.headers["x-content-type-options"] == "nosniff", path
        assert r.headers["referrer-policy"] == "no-referrer"


def test_validation_errors_do_not_echo_the_input(client):
    r = client.get(f"{BASE}/landslides", params={"min_area_m2": "<script>alert(1)</script>"})
    assert r.status_code == 422 and "script" not in r.text


def test_absurd_inputs_do_not_crash(client):
    assert client.get("/static/" + EVENT + "/" + "a" * 60_000 + ".png").status_code in (404, 414)
    assert client.get(f"{BASE}/landslides", params={"min_area_m2": "9" * 400}).status_code == 422
    assert client.get(f"{BASE}/roads", params={"status": "blocked," * 5000}).status_code == 422
