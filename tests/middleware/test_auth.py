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


# --- 인증 범위 ---

def _scope_probe_app() -> tuple[Starlette, list[frozenset[str] | None]]:
    from sootool.core.request_context import REQUEST_SCOPES

    seen: list[frozenset[str] | None] = []

    async def probe(request: Request) -> PlainTextResponse:  # noqa: ARG001
        seen.append(REQUEST_SCOPES.get())
        return PlainTextResponse("ok")

    return Starlette(routes=[Route("/", probe)]), seen


def test_matching_token_grants_its_scopes_to_the_downstream_handler() -> None:
    from sootool.core.request_context import SCOPE_POLICY_WRITE, SCOPE_READ

    app, seen = _scope_probe_app()
    validators = [
        BearerTokenValidator("read-token", frozenset({SCOPE_READ})),
        BearerTokenValidator("admin-token", frozenset({SCOPE_READ, SCOPE_POLICY_WRITE})),
    ]
    client = TestClient(AuthMiddleware(app, validators))
    client.get("/", headers={"Authorization": "Bearer read-token"})
    client.get("/", headers={"Authorization": "Bearer admin-token"})
    assert seen == [frozenset({SCOPE_READ}), frozenset({SCOPE_READ, SCOPE_POLICY_WRITE})]


def test_scopes_do_not_leak_to_the_next_request() -> None:
    from sootool.core.request_context import REQUEST_SCOPES

    app, _ = _scope_probe_app()
    client = TestClient(AuthMiddleware(app, [BearerTokenValidator("t")]))
    client.get("/", headers={"Authorization": "Bearer t"})
    assert REQUEST_SCOPES.get() is None


def test_without_validators_no_scope_restriction_is_applied() -> None:
    app, seen = _scope_probe_app()
    TestClient(AuthMiddleware(app, [])).get("/")
    assert seen == [None]


def test_default_validator_scope_is_read_only() -> None:
    from sootool.core.request_context import SCOPE_READ

    assert BearerTokenValidator("x").scopes == frozenset({SCOPE_READ})
