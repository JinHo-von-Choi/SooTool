from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sootool.middleware.cors import build_cors_middleware


def _ok(request: Request) -> PlainTextResponse:  # noqa: ARG001
    return PlainTextResponse("ok")


def _make_app(origins: list[str]) -> TestClient:
    app = Starlette(routes=[Route("/", _ok, methods=["GET", "POST", "OPTIONS"])])
    wrapped = build_cors_middleware(app, origins)
    return TestClient(wrapped, raise_server_exceptions=True)


def test_no_origins_no_cors_headers() -> None:
    client = _make_app([])
    resp = client.get("/", headers={"Origin": "https://example.com"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers


def test_allowed_origin_returns_header() -> None:
    client = _make_app(["https://example.com"])
    resp = client.get("/", headers={"Origin": "https://example.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://example.com"


def test_disallowed_origin_no_cors_header() -> None:
    client = _make_app(["https://allowed.com"])
    resp = client.get("/", headers={"Origin": "https://evil.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") != "https://evil.com"


def test_preflight_allowed_origin() -> None:
    client = _make_app(["https://example.com"])
    resp = client.options(
        "/",
        headers={
            "Origin":                          "https://example.com",
            "Access-Control-Request-Method":   "POST",
            "Access-Control-Request-Headers":  "content-type",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") == "https://example.com"


def test_preflight_disallowed_origin() -> None:
    client = _make_app(["https://allowed.com"])
    resp = client.options(
        "/",
        headers={
            "Origin":                        "https://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "https://evil.com"
