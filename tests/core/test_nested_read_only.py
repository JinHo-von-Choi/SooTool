from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from sootool import server
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY, ToolRegistry

_WRITE_ITEM_ARGS = {
    "domain": "tax", "name": "kr_income", "year": 2026, "yaml_content": "policy_version: 1\n",
}


@pytest.fixture(autouse=True)
def _admin_mode(tmp_path: Path, monkeypatch) -> Path:
    """관리자 모드를 켠 상태에서도 중첩 호출이 쓰기 도구를 실행하지 못함을 확인하기 위한 환경."""
    server._load_modules()
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_DRAFT_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    return tmp_path


def _nothing_was_written(root: Path) -> bool:
    return not any(p.is_file() for p in root.rglob("*"))


def test_invoke_read_only_runs_read_only_tools():
    assert REGISTRY.invoke_read_only("core.add", operands=["1", "2"])["result"] == "3"


def test_invoke_read_only_refuses_write_tools():
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke_read_only("sootool.policy_propose", **_WRITE_ITEM_ARGS)


def test_invoke_read_only_keeps_unknown_tool_key_error():
    with pytest.raises(KeyError):
        REGISTRY.invoke_read_only("no.such_tool")


def test_invoke_read_only_on_a_private_registry():
    r = ToolRegistry()

    @r.tool(namespace="t", name="reader")
    def _reader() -> dict[str, Any]:
        return {"result": "ok"}

    @r.tool(namespace="t", name="writer", read_only=False)
    def _writer() -> dict[str, Any]:
        return {"result": "wrote"}

    assert r.invoke_read_only("t.reader")["result"] == "ok"
    with pytest.raises(InvalidInputError):
        r.invoke_read_only("t.writer")


def test_batch_refuses_write_tool_items(_admin_mode):
    out = REGISTRY.invoke(
        "core.batch",
        items=[
            {"id": "w", "tool": "sootool.policy_propose", "args": _WRITE_ITEM_ARGS},
            {"id": "r", "tool": "core.add", "args": {"operands": ["1", "2"]}},
        ],
    )
    by_id = {item["id"]: item for item in out["results"]}
    assert by_id["w"]["status"] == "error"
    assert by_id["r"]["status"] == "ok"
    assert _nothing_was_written(_admin_mode)


def test_pipeline_refuses_write_tool_steps(_admin_mode):
    out = REGISTRY.invoke(
        "core.pipeline",
        steps=[{"id": "w", "tool": "sootool.policy_propose", "args": _WRITE_ITEM_ARGS}],
    )
    assert out["status"] != "ok"
    assert _nothing_was_written(_admin_mode)


def test_lean_call_cannot_reach_write_tools_through_batch(_admin_mode):
    lean = server.build_server(profile="lean")
    result = asyncio.run(lean.call_tool(
        "sootool.call",
        {"name": "core.batch", "arguments": {"items": [
            {"id": "w", "tool": "sootool.policy_rollback",
             "args": {"domain": "tax", "name": "kr_income", "year": 2026}},
        ]}},
    ))
    out = result.structured_content
    assert out["count_error"] == 1
    assert out["count_ok"] == 0
    assert _nothing_was_written(_admin_mode)


# --- 중첩 호출의 요청 컨텍스트 전파 ---

def test_batch_items_inherit_the_stateless_request_context():
    from sootool.core.request_context import request_context
    from sootool.skill_guide.session_state import STORE

    before = STORE.session_count()
    with request_context(stateless=True):
        out = REGISTRY.invoke(
            "core.batch", items=[{"id": "a", "tool": "core.add", "args": {"operands": ["1", "2"]}}],
        )
    inner_meta = out["results"][0]["result"]["_meta"]
    assert "session_stats" not in inner_meta
    assert STORE.session_count() == before


def test_pipeline_steps_inherit_the_request_locale_and_scopes():
    from sootool.core.request_context import (
        REQUEST_LOCALE,
        REQUEST_SCOPES,
        SCOPE_READ,
        request_context,
    )

    seen: dict[str, object] = {}

    r = ToolRegistry()

    @r.tool(namespace="t", name="probe")
    def _probe() -> dict[str, Any]:
        seen["locale"] = REQUEST_LOCALE.get()
        seen["scopes"] = REQUEST_SCOPES.get()
        return {"result": "ok"}

    from sootool.core.pipeline import PipelineExecutor

    with request_context(locale="en", scopes=frozenset({SCOPE_READ})):
        PipelineExecutor(registry=r).run(steps=[{"id": "s", "tool": "t.probe", "args": {}}])
    assert seen == {"locale": "en", "scopes": frozenset({SCOPE_READ})}
