from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sootool.middleware.auth import AuthMiddleware, BearerTokenValidator


def _ok(request: Request) -> PlainTextResponse:  # noqa: ARG001
    return PlainTextResponse("ok")


_DEFAULT_TOKEN = "secret"  # noqa: S105


def _make_app(token: str | None = _DEFAULT_TOKEN) -> TestClient:
    app = Starlette(routes=[Route("/", _ok), Route("/healthz", _ok)])
    validators = [BearerTokenValidator(token)] if token else []
    wrapped = AuthMiddleware(app, validators)
    return TestClient(wrapped, raise_server_exceptions=True)


def test_no_token_configured_passes_through() -> None:
    client = _make_app(token=None)
    assert client.get("/").status_code == 200


def test_missing_auth_header_returns_401() -> None:
    client = _make_app()
    resp = client.get("/")
    assert resp.status_code == 401


def test_wrong_token_returns_401() -> None:
    client = _make_app()
    resp = client.get("/", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


def test_correct_token_returns_200() -> None:
    client = _make_app()
    resp = client.get("/", headers={"Authorization": f"Bearer {_DEFAULT_TOKEN}"})
    assert resp.status_code == 200


def test_healthz_skips_auth() -> None:
    client = _make_app()
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_malformed_auth_header_returns_401() -> None:
    client = _make_app()
    resp = client.get("/", headers={"Authorization": "Token secret"})
    assert resp.status_code == 401
