"""SooTool 라이브러리 인터페이스(코드 실행 환경용).

MCP 서버를 거치지 않고 같은 도구를 파이썬 함수처럼 호출한다. 결과는 MCP 응답과 같은 구조(결과 필드, trace,
영수증 ``_meta.integrity``)이고 도구가 선언한 TypedDict 로 타입이 붙는다. 오류는 ``SooToolError`` 계열 예외로
발생한다.

    from sootool.sdk import tax, payroll, core

    out = tax.kr_income(taxable_income=50_000_000, year=2026)
    out["tax"]                           # "6240000"
    out["_meta"]["integrity"]["input_hash"]

네임스페이스는 처음 쓸 때 해당 도메인만 불러오므로 가져오는 비용이 작다(mcp 패키지를 가져오지 않는다).
숫자 인자는 문자열 숫자, 정수, Decimal 을 받고 부동소수는 배정밀도 표기로 바뀌며 ``_meta.input_coerced`` 에
기록된다. 정적 타입 검사를 위한 스텁은 ``scripts/gen_sdk_stubs.py`` 가 레지스트리에서 생성한다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import inspect
import types
import typing
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sootool.core.coerce import number_to_str
from sootool.core.registry import REGISTRY, ToolEntry
from sootool.runtime import NAMESPACE_MODULES, _register_core_tools, load_namespace

__all__ = ["Namespace", "Tool", "namespaces"]

if TYPE_CHECKING:
    # 정적 타입 검사기와 편집기에는 생성된 타입 선언을 보여 준다(런타임에는 가져오지 않는다).
    from sootool.sdk._typed import (
        accounting as accounting,
    )
    from sootool.sdk._typed import (
        core as core,
    )
    from sootool.sdk._typed import (
        crypto as crypto,
    )
    from sootool.sdk._typed import (
        datetime as datetime,
    )
    from sootool.sdk._typed import (
        engineering as engineering,
    )
    from sootool.sdk._typed import (
        finance as finance,
    )
    from sootool.sdk._typed import (
        geometry as geometry,
    )
    from sootool.sdk._typed import (
        math as math,
    )
    from sootool.sdk._typed import (
        medical as medical,
    )
    from sootool.sdk._typed import (
        payroll as payroll,
    )
    from sootool.sdk._typed import (
        pm as pm,
    )
    from sootool.sdk._typed import (
        probability as probability,
    )
    from sootool.sdk._typed import (
        realestate as realestate,
    )
    from sootool.sdk._typed import (
        science as science,
    )
    from sootool.sdk._typed import (
        sootool as sootool,
    )
    from sootool.sdk._typed import (
        stats as stats,
    )
    from sootool.sdk._typed import (
        symbolic as symbolic,
    )
    from sootool.sdk._typed import (
        tax as tax,
    )
    from sootool.sdk._typed import (
        tax_us as tax_us,
    )
    from sootool.sdk._typed import (
        units as units,
    )


def _coerce(value: Any, argument: str, coerced: list[dict[str, str]]) -> Any:
    """인자 안의 모든 숫자(리스트, 딕셔너리 값 포함)를 문자열 숫자로 바꾼다."""
    if isinstance(value, list):
        return [_coerce(item, argument, coerced) for item in value]
    if isinstance(value, dict):
        return {key: _coerce(item, argument, coerced) for key, item in value.items()}
    converted, from_float = number_to_str(value)
    if from_float:
        coerced.append({"argument": argument, "from": "float", "as": converted})
    return converted


def _wants_str(annotation: Any) -> bool:
    """파라미터가 문자열 숫자를 받는 자리인지 판정한다(str, list[str], dict[키, str], str | None)."""
    if annotation is str:
        return True
    origin = typing.get_origin(annotation)
    args   = typing.get_args(annotation)
    if origin is list and args:
        return _wants_str(args[0])
    if origin is dict and len(args) == 2:
        return _wants_str(args[1])
    if origin is typing.Union or origin is types.UnionType:
        numeric = any(a in (int, float, Decimal) for a in args)
        return not numeric and any(_wants_str(a) for a in args)
    return False


class Tool:
    """등록된 도구 하나를 감싼 호출 가능 객체. 시그니처와 설명은 도구 정의에서 가져온다."""

    def __init__(self, entry: ToolEntry) -> None:
        self._entry = entry
        self.__name__ = entry.name
        self.__qualname__ = entry.full_name
        self.__doc__ = entry.description
        self.__signature__ = entry.exposed_signature()
        try:
            hints = typing.get_type_hints(entry.fn)
        except Exception:  # noqa: BLE001
            hints = {}
        self._string_params = {
            name for name, parameter in self.__signature__.parameters.items()
            if _wants_str(hints.get(name, parameter.annotation))
        }

    @property
    def full_name(self) -> str:
        return self._entry.full_name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        bound = self.__signature__.bind(*args, **kwargs)
        coerced: list[dict[str, str]] = []
        arguments = {
            name: _coerce(value, name, coerced) if name in self._string_params else value
            for name, value in bound.arguments.items()
        }
        result = REGISTRY.invoke(self._entry.full_name, **arguments)
        if coerced and isinstance(result, dict):
            meta = dict(result.get("_meta") or {})
            meta["input_coerced"] = coerced
            result = {**result, "_meta": meta}
        return result

    def __repr__(self) -> str:
        return f"<sootool tool {self._entry.full_name}{inspect.signature(self)}>"


class Namespace:
    """도메인 하나의 도구 모음. 속성 접근으로 도구를 찾는다."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            _register_core_tools()
            load_namespace(self._name)
            self._loaded = True

    def _tools(self) -> dict[str, ToolEntry]:
        self._ensure_loaded()
        return {e.name: e for e in REGISTRY.list() if e.namespace == self._name}

    def __getattr__(self, tool: str) -> Tool:
        if tool.startswith("_"):
            raise AttributeError(tool)
        entries = self._tools()
        if tool not in entries:
            raise AttributeError(f"{self._name}.{tool} 도구가 없습니다. 사용 가능: {', '.join(sorted(entries))}")
        return Tool(entries[tool])

    def __dir__(self) -> list[str]:
        return sorted(self._tools())

    def __repr__(self) -> str:
        return f"<sootool namespace {self._name}>"


_NAMESPACES: dict[str, Namespace] = {}


def namespaces() -> list[str]:
    """사용할 수 있는 네임스페이스 이름."""
    return sorted(NAMESPACE_MODULES)


def __getattr__(name: str) -> Namespace:
    if name not in NAMESPACE_MODULES:
        raise AttributeError(f"sootool.sdk 에 {name!r} 네임스페이스가 없습니다. 사용 가능: {', '.join(namespaces())}")
    return _NAMESPACES.setdefault(name, Namespace(name))


def __dir__() -> list[str]:
    return [*__all__, *namespaces()]
