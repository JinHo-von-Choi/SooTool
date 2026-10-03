"""MCP 경계: 입력 숫자 허용과 오류 계약.

도구 함수를 MCP 에 노출할 때 두 가지를 보장한다.

1. 입력: 문자열 숫자를 받는 파라미터가 JSON 숫자(정수, 부동소수)로 오더라도 문자열로 바꿔
   받는다. LLM 은 숫자를 JSON number 로 보내는 경우가 많다. 부동소수는 클라이언트가 보낸
   배정밀도 값의 최단 왕복 표기(repr)로 변환하므로, 배정밀도를 넘는 자릿수가 필요하면 처음부터
   문자열로 보내야 한다. 입력 스키마(JSON Schema)는 여전히 string 으로 광고한다.
2. 오류: 모든 도구 오류를 ``{"error": {"code", "message", "retryable", ...}}`` 구조의
   ``isError`` 결과로 돌려준다. 예기치 못한 예외는 내부 오류 코드로 변환하고 상세는 로그에만 남긴다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import contextvars
import functools
import inspect
import logging
import math
import types
import typing
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp.types import CallToolResult, InputRequiredResult, TextContent
from pydantic import BeforeValidator, ValidationError, ValidationInfo

from sootool.core.errors import InvalidArgumentsError, SooToolError, UnknownToolError

log = logging.getLogger("sootool.boundary")

INTERNAL_ERROR_CODE = "internal_error"
_INTERNAL_MESSAGE   = "계산 중 예기치 않은 오류가 발생했습니다."


_COERCED_FLOATS: contextvars.ContextVar[list[dict[str, str]] | None] = contextvars.ContextVar(
    "sootool_coerced_floats", default=None,
)


def _number_to_str(value: Any, info: ValidationInfo) -> Any:
    """JSON 숫자를 문자열 숫자로 바꾼다. 그 밖의 값은 그대로 두어 검증 단계가 판단하게 한다.

    부동소수는 배정밀도 표기(repr)로 바뀌어 원래 의도한 자릿수와 다를 수 있으므로, 호출 단위로 변환
    기록을 남겨 응답의 ``_meta.input_coerced`` 로 알린다.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        converted = repr(value)
        record = _COERCED_FLOATS.get()
        if record is not None:
            record.append({"argument": info.field_name or "", "from": "float", "as": converted})
        return converted
    return value


_NUMERIC_STR = Annotated[str, BeforeValidator(_number_to_str)]


def _coercible(tp: Any) -> Any:
    """타입 안의 모든 ``str`` 을 숫자 허용 문자열로 바꾼다(list, dict 값, Optional 포함)."""
    if tp is str:
        return _NUMERIC_STR
    origin = typing.get_origin(tp)
    args   = typing.get_args(tp)
    if origin is None or origin is Annotated or not args:
        return tp
    if origin is list:
        return types.GenericAlias(list, (_coercible(args[0]),))
    if origin is dict and len(args) == 2:
        return types.GenericAlias(dict, (args[0], _coercible(args[1])))
    if origin is typing.Union or origin is types.UnionType:
        return typing.Union[tuple(_coercible(a) for a in args)]  # noqa: UP007
    return tp


def coerced_signature(fn: Callable[..., Any], base: inspect.Signature | None = None) -> inspect.Signature:
    """``fn`` 의 시그니처에서 문자열 파라미터를 숫자 허용으로 바꾼 시그니처를 만든다.

    ``base`` 가 있으면 그 시그니처(예: 정책 공통 인자를 더한 노출 시그니처)를 바탕으로 한다.
    타입 힌트는 ``fn`` 에서 해석하며, 힌트가 없는 파라미터는 ``base`` 의 주석을 그대로 쓴다.
    """
    signature = base if base is not None else inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:  # noqa: BLE001
        log.debug("type hints unresolved for %s; numeric coercion skipped", fn, exc_info=True)
        return signature
    parameters = [
        p.replace(annotation=_coercible(hints.get(p.name, p.annotation)))
        for p in signature.parameters.values()
    ]
    return signature.replace(
        parameters=parameters,
        return_annotation=hints.get("return", signature.return_annotation),
    )


def error_payload(exc: BaseException) -> dict[str, Any]:
    """예외를 오류 계약 구조로 변환한다. SooToolError 가 아니면 내부 오류로 취급한다."""
    if isinstance(exc, SooToolError):
        return exc.to_payload()
    return {
        "code":      INTERNAL_ERROR_CODE,
        "message":   _INTERNAL_MESSAGE,
        "retryable": False,
        "details":   {"type": type(exc).__name__},
    }


def error_result(exc: BaseException) -> CallToolResult:
    """오류 계약 구조를 담은 isError 결과를 만든다."""
    payload = error_payload(exc)
    return CallToolResult(
        content=[TextContent(type="text", text=f"[{payload['code']}] {payload['message']}")],
        structured_content={"error": payload},
        is_error=True,
    )


def _with_input_coerced(result: Any) -> Any:
    """이 호출에서 부동소수가 문자열로 바뀌었다면 ``_meta.input_coerced`` 로 알린다."""
    coerced = _COERCED_FLOATS.get()
    if not coerced or not isinstance(result, dict):
        return result
    meta = dict(result.get("_meta") or {})
    meta["input_coerced"] = [dict(item) for item in coerced]
    return {**result, "_meta": meta}


def with_error_contract(
    fn:         Callable[..., Any],
    call:       Callable[..., Any] | None = None,
    *,
    coerce:     bool                      = True,
    signature:  inspect.Signature | None  = None,
) -> Callable[..., Any]:
    """``fn`` 의 시그니처로 노출되는 호출자를 만든다.

    ``call`` 이 있으면 그것을 실제 실행에 쓴다(예: REGISTRY.invoke 경유). 실행 중 발생한 예외는
    오류 계약 결과로 변환한다. 입력 숫자 허용은 ``coerce`` 로 끌 수 있다. ``signature`` 로 노출
    시그니처를 지정할 수 있다(기본은 ``fn`` 의 시그니처).
    """
    target = call if call is not None else fn

    @functools.wraps(fn)
    def bound(**kwargs: Any) -> Any:
        try:
            return _with_input_coerced(target(**kwargs))
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, SooToolError):
                log.exception("unexpected error in tool %s", getattr(fn, "__name__", fn))
            return error_result(exc)

    bound.__signature__ = (  # type: ignore[attr-defined]
        coerced_signature(fn, signature) if coerce else (signature or inspect.signature(fn))
    )
    return bound


def _validation_problems(exc: ValidationError) -> list[dict[str, str]]:
    """pydantic 오류에서 필드 경로와 메시지만 추린다. 거부된 입력값은 되돌려주지 않는다."""
    return [
        {"field": ".".join(str(part) for part in err["loc"]) or "(root)", "message": err["msg"]}
        for err in exc.errors()
    ]


class SooToolServer(MCPServer):
    """오류 계약을 서버 경계 전체에 적용하는 MCPServer.

    도구 함수 안에서 난 오류는 ``with_error_contract`` 가 변환한다. 이 클래스는 함수에 닿기 전에
    SDK 가 거부하는 경우(알 수 없는 도구, 필수 인자 누락과 타입 오류)를 같은 형식으로 돌려준다.
    선언되지 않은 인자는 SDK 가 조용히 버리므로 여기서 거부한다. 오타 난 선택 인자(예: 반올림
    정책)가 무시되어 기본값으로 계산되는 일을 막기 위해서다.
    """

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
    ) -> CallToolResult | InputRequiredResult:
        token = _COERCED_FLOATS.set([])
        try:
            return await self._call_tool(name, arguments, context)
        finally:
            _COERCED_FLOATS.reset(token)

    async def _call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Any,
    ) -> CallToolResult | InputRequiredResult:
        tool = self._tool_manager.get_tool(name)
        if tool is not None:
            declared = set(tool.parameters.get("properties", {}))
            unexpected = sorted(set(arguments) - declared)
            if unexpected:
                return error_result(InvalidArgumentsError([
                    {"field": key, "message": "Unexpected argument"} for key in unexpected
                ]))
        try:
            return await super().call_tool(name, arguments, context)
        except UnexpectedToolError:
            raise
        except ToolError as exc:
            cause = exc.__cause__
            if isinstance(cause, ValidationError):
                return error_result(InvalidArgumentsError(_validation_problems(cause)))
            if tool is None:
                return error_result(UnknownToolError(name))
            raise
