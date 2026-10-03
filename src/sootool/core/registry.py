from __future__ import annotations

import contextlib
import functools
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sootool.core.errors import InvalidInputError
from sootool.core.limits import validate_argument_sizes
from sootool.core.policy_context import policy_context

log = logging.getLogger("sootool.core.registry")

PostProcessor = Callable[[dict[str, Any], str], dict[str, Any]]


@functools.cache
def _signature(fn: Callable[..., Any]) -> inspect.Signature:
    return inspect.signature(fn)


def _with_defaults(fn: Callable[..., Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    """기본값을 채운 호출 인자 사본을 반환한다.

    기본값을 생략한 호출과 명시한 호출, 직접 호출과 MCP 호출이 같은 integrity 입력 해시를
    갖도록 정규화한다. 바인딩이 불가능한 인자는 그대로 두며, 실제 호출 단계에서 TypeError 로
    드러난다.
    """
    try:
        bound = _signature(fn).bind(**kwargs)
    except TypeError:
        return dict(kwargs)
    bound.apply_defaults()
    return dict(bound.arguments)


# 정책 기반 도구가 도구 함수의 파라미터 외에 공통으로 받는 호출 인자.
POLICY_ARGUMENTS = ("as_of", "include_proposed")

POLICY_PARAMETERS: tuple[inspect.Parameter, ...] = (
    inspect.Parameter("as_of", inspect.Parameter.KEYWORD_ONLY, default=None, annotation=str | None),
    inspect.Parameter("include_proposed", inspect.Parameter.KEYWORD_ONLY, default=False, annotation=bool),
)


def _parse_policy_arguments(as_of: Any, include_proposed: Any) -> tuple[date | None, bool]:
    if isinstance(include_proposed, bool):
        proposed = include_proposed
    else:
        raise InvalidInputError(f"include_proposed 는 true 또는 false 여야 합니다: {include_proposed!r}")
    if as_of is None:
        return None, proposed
    if isinstance(as_of, date):
        return as_of, proposed
    if not isinstance(as_of, str):
        raise InvalidInputError(f"as_of 는 YYYY-MM-DD 형식의 날짜 문자열이어야 합니다: {as_of!r}")
    try:
        return date.fromisoformat(as_of), proposed
    except ValueError as exc:
        raise InvalidInputError(f"as_of 는 YYYY-MM-DD 형식의 날짜 문자열이어야 합니다: {as_of!r}") from exc


@dataclass
class ToolEntry:
    namespace:   str
    name:        str
    description: str
    fn:          Callable[..., Any]
    version:     str                = "1.0.0"
    deprecated:  dict[str, Any] | None = None
    read_only:   bool               = True
    destructive: bool               = False
    idempotent:  bool               = True
    policy:      bool               = False

    @property
    def full_name(self) -> str:
        return f"{self.namespace}.{self.name}"

    @property
    def public_description(self) -> str:
        """도구 목록에 노출하는 설명. 폐기 예고된 도구는 앞에 대체 도구와 제거 예정 버전을 붙인다."""
        if not self.deprecated:
            return self.description
        replacement = self.deprecated.get("replacement")
        remove_in   = self.deprecated.get("remove_in")
        notice = "[폐기 예정"
        if replacement:
            notice += f", 대체: {replacement}"
        if remove_in:
            notice += f", 제거 예정: {remove_in}"
        return f"{notice}] {self.description}"

    def exposed_signature(self) -> inspect.Signature:
        """호출자가 보는 시그니처. 정책 기반 도구는 ``as_of``, ``include_proposed`` 를 더한다."""
        signature = inspect.signature(self.fn)
        if not self.policy:
            return signature
        return signature.replace(parameters=[*signature.parameters.values(), *POLICY_PARAMETERS])


class ToolRegistry:
    def __init__(self) -> None:
        self._tools:           dict[str, ToolEntry]  = {}
        self._post_processors: list[PostProcessor]   = []

    def tool(
        self,
        *,
        namespace:   str,
        name:        str,
        description: str       = "",
        version:     str       = "1.0.0",
        deprecated:  dict[str, Any] | None = None,
        read_only:   bool      = True,
        destructive: bool      = False,
        idempotent:  bool      = True,
        policy:      bool      = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            entry = ToolEntry(
                namespace=namespace,
                name=name,
                description=description,
                fn=fn,
                version=version,
                deprecated=deprecated,
                read_only=read_only,
                destructive=destructive,
                idempotent=idempotent,
                policy=policy,
            )
            if entry.full_name in self._tools:
                raise ValueError(f"도구 중복 등록: {entry.full_name}")
            self._tools[entry.full_name] = entry
            return fn

        return deco

    def list(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def register_post_processor(self, fn: PostProcessor) -> None:
        """Register a post-processor applied to every invoke() result.

        Post-processors are called only when the result is a dict containing
        a "trace" key (ADR-011: result/trace are never modified; processors
        must write exclusively to _meta).

        Signature: fn(response: dict, tool_name: str) -> dict
        """
        self._post_processors.append(fn)

    def invoke_read_only(self, full_name: str, **kwargs: Any) -> Any:
        """읽기 전용으로 선언된 도구만 실행한다.

        다른 도구를 이름으로 호출하는 도구(core.batch, core.pipeline)가 쓰기 도구를 우회 실행하지
        못하게 하는 경계다. 이 경계가 있어 두 도구의 readOnlyHint 선언이 사실과 일치한다.
        """
        entry = self._tools.get(full_name)
        if entry is None:
            raise KeyError(full_name)
        if not entry.read_only:
            raise InvalidInputError(
                f"{full_name} 은(는) 읽기 전용이 아니어서 다른 도구 안에서 실행할 수 없습니다."
            )
        return self.invoke(full_name, **kwargs)

    def invoke(self, full_name: str, **kwargs: Any) -> Any:
        if full_name not in self._tools:
            raise KeyError(full_name)
        entry = self._tools[full_name]
        validate_argument_sizes(kwargs)

        # 정책 기반 도구의 공통 인자(as_of, include_proposed)는 도구 함수에 넘기지 않고 호출 범위의
        # 정책 해석 컨텍스트로 설정한다. 지정하지 않으면 바깥 호출의 컨텍스트를 그대로 상속한다.
        policy_inputs: dict[str, Any] = {}
        scope: contextlib.AbstractContextManager[None] = contextlib.nullcontext()
        if entry.policy:
            raw_as_of   = kwargs.pop("as_of", None)
            raw_include = kwargs.pop("include_proposed", False)
            policy_inputs = {"as_of": raw_as_of, "include_proposed": raw_include}
            as_of, include_proposed = _parse_policy_arguments(raw_as_of, raw_include)
            if raw_as_of is not None or raw_include:
                scope = policy_context(as_of=as_of, include_proposed=include_proposed)

        # Capture the inputs for the integrity stamp before the tool runs and
        # restore the previous context on exit. Stack-style save/restore is
        # required because batch/pipeline tools recursively invoke() other
        # tools, a naive reset would clobber the outer frame's context.
        from sootool.core.audit import _INTEGRITY_CTX, set_current_inputs
        prev_inputs = _INTEGRITY_CTX.inputs
        prev_policy = _INTEGRITY_CTX.policy_meta
        set_current_inputs({**_with_defaults(entry.fn, kwargs), **policy_inputs})
        # Each nested call starts with a fresh policy slot; the previous
        # frame's policy is restored in the finally block below.
        _INTEGRITY_CTX.policy_meta = None
        try:
            with scope:
                result = entry.fn(**kwargs)
            if isinstance(result, dict) and "trace" in result:
                for proc in self._post_processors:
                    try:
                        result = proc(result, full_name)
                    except Exception:
                        log.warning(
                            "Post-processor %s failed for %s", proc, full_name, exc_info=True
                        )
            return result
        finally:
            _INTEGRITY_CTX.inputs = prev_inputs
            _INTEGRITY_CTX.policy_meta = prev_policy


REGISTRY = ToolRegistry()
