from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sootool.middleware.request_id import REQUEST_ID_HEADER, RequestIDMiddleware


def _echo(request: Request) -> PlainTextResponse:
    rid = getattr(request.state, "request_id", "")
    return PlainTextResponse(rid)


def _make_app() -> TestClient:
    app = Starlette(routes=[Route("/", _echo)])
    wrapped = RequestIDMiddleware(app)
    return TestClient(wrapped, raise_server_exceptions=True)


def test_generates_request_id_when_absent() -> None:
    client = _make_app()
    resp = client.get("/")
    assert resp.status_code == 200
    rid = resp.headers.get(REQUEST_ID_HEADER)
    assert rid and len(rid) == 36


def test_echoes_existing_request_id() -> None:
    client = _make_app()
    custom = "my-request-id-123"
    resp = client.get("/", headers={REQUEST_ID_HEADER: custom})
    assert resp.headers.get(REQUEST_ID_HEADER) == custom
    assert resp.text == custom


def test_response_header_set() -> None:
    client = _make_app()
    resp = client.get("/")
    assert REQUEST_ID_HEADER in resp.headers
