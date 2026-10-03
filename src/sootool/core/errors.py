"""SooTool 오류 계층과 기계가 읽을 수 있는 오류 계약.

모든 도구 오류는 ``SooToolError`` 의 하위 클래스이며 고유한 ``code`` 를 갖는다. MCP 경계는
오류를 ``{"error": {"code", "message", "retryable", ...}}`` 구조로 변환한다. 일부 클래스는
기존 호출자의 호환을 위해 표준 예외(ZeroDivisionError, TypeError, decimal.InvalidOperation)도
함께 상속한다.
"""
from __future__ import annotations

import decimal
from typing import Any, ClassVar


class SooToolError(Exception):
    """모든 SooTool 도구 오류의 기반 클래스."""

    code:      ClassVar[str]  = "tool_error"
    retryable: ClassVar[bool] = False

    field: str | None = None

    def details(self) -> dict[str, Any]:
        """오류 코드별 부가 정보. 하위 클래스가 재정의한다."""
        return {}

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code":      self.code,
            "message":   str(self),
            "retryable": self.retryable,
        }
        if self.field:
            payload["field"] = self.field
        details = self.details()
        if details:
            payload["details"] = details
        return payload


class InvalidInputError(SooToolError):
    """입력 형식이나 값이 올바르지 않다."""

    code = "invalid_input"


class InvalidArgumentsError(InvalidInputError):
    """도구 인자가 입력 스키마 검증(필수 인자, 타입)을 통과하지 못했다."""

    code = "invalid_arguments"

    def __init__(self, problems: list[dict[str, str]]) -> None:
        self.problems = problems
        summary = "; ".join(f"{p['field']}: {p['message']}" for p in problems) or "unknown"
        super().__init__(f"인자 검증 실패: {summary}")

    def details(self) -> dict[str, Any]:
        return {"problems": self.problems}


class UnknownToolError(InvalidInputError):
    """등록되지 않은 도구 이름으로 호출했다."""

    code = "unknown_tool"

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"알 수 없는 도구입니다: {name!r}. sootool.search 로 도구를 찾을 수 있습니다.")

    def details(self) -> dict[str, Any]:
        return {"name": self.name}


class InvalidNumberError(InvalidInputError, decimal.InvalidOperation):
    """숫자 문자열이 아닌 값이 들어왔다."""

    code = "invalid_number"


class FloatInputError(InvalidInputError, TypeError):
    """부동소수점 입력은 정밀도 손실 위험으로 거부한다."""

    code = "float_input"


class DomainConstraintError(SooToolError):
    """입력은 형식상 올바르지만 도메인 제약(범위, 부호, 정의역)을 위반한다."""

    code = "domain_constraint"


class DivisionByZeroError(DomainConstraintError, ZeroDivisionError):
    """분모가 0 이다."""

    code = "division_by_zero"


class PrecisionLossError(SooToolError):
    code = "precision_loss"


class UnsafeDirectoryError(SooToolError):
    """정책·초안·감사 로그 저장 디렉터리가 안전하지 않음(심볼릭 링크, 타인 소유, 비디렉터리)."""

    code = "unsafe_directory"


class ToolTimeoutError(SooToolError):
    """호출 시간 예산을 초과했다."""

    code      = "timeout"
    retryable = True

    def __init__(self, tool: str, seconds: float) -> None:
        self.tool    = tool
        self.seconds = seconds
        super().__init__(f"{tool} 이(가) 호출 시간 예산 {seconds:g}초를 초과했습니다.")

    def details(self) -> dict[str, Any]:
        return {"tool": self.tool, "seconds": self.seconds}


class SolverBracketError(DomainConstraintError):
    """근 찾기 구간이 올바르지 않거나 양 끝의 함수값 부호가 같아 해가 보장되지 않는다."""

    code = "no_sign_change"

    def __init__(self, message: str, lower: Any, upper: Any, f_lower: Any, f_upper: Any) -> None:
        self.lower   = lower
        self.upper   = upper
        self.f_lower = f_lower
        self.f_upper = f_upper
        super().__init__(message)

    def details(self) -> dict[str, Any]:
        return {
            "lower": str(self.lower), "upper": str(self.upper),
            "f_lower": None if self.f_lower is None else str(self.f_lower),
            "f_upper": None if self.f_upper is None else str(self.f_upper),
        }


class PolicyFormatError(SooToolError, ValueError):
    """정책 YAML 의 필수 필드 누락이나 값 형식 오류."""

    code = "policy_format"


class PolicyNotInEffectError(SooToolError):
    """요청한 시점(as_of)에 시행 중인 정책 버전이 없다."""

    code = "policy_not_in_effect"

    def __init__(self, domain: str, key: str, year: int, as_of: str, periods: list[dict[str, Any]]) -> None:
        self.domain  = domain
        self.key     = key
        self.year    = year
        self.as_of   = as_of
        self.periods = periods
        listing = ", ".join(f"{p['effective_from']}~{p['effective_to'] or '현재'}({p['status']})" for p in periods)
        super().__init__(
            f"정책 '{domain}/{key}' {year}년 버전 중 {as_of} 에 시행 중인 것이 없습니다. 시행 기간: {listing or '없음'}"
        )

    def details(self) -> dict[str, Any]:
        return {
            "domain": self.domain, "key": self.key, "year": self.year,
            "as_of": self.as_of, "periods": self.periods,
        }


class PolicyNotEnactedError(SooToolError):
    """정책은 있지만 아직 확정(enacted)되지 않은 개정안(proposed)뿐이다."""

    code = "policy_not_enacted"

    def __init__(self, domain: str, key: str, year: int) -> None:
        self.domain = domain
        self.key    = key
        self.year   = year
        super().__init__(
            f"정책 '{domain}/{key}' {year}년 버전은 확정 전 개정안(proposed)입니다. "
            "개정안 기준으로 계산하려면 include_proposed=true 를 지정하세요. 결과에는 legal_status=proposed 가 표기됩니다."
        )

    def details(self) -> dict[str, Any]:
        return {"domain": self.domain, "key": self.key, "year": self.year}


class InputLimitError(DomainConstraintError):
    """도구 입력이 호출 단위 한도를 초과함.

    attributes:
        field:    한도가 적용된 입력 이름.
        limit:    허용 상한.
        observed: 실제 입력값.
    """

    code = "input_limit"

    def __init__(self, field: str, limit: int, observed: int) -> None:
        self.field    = field
        self.limit    = limit
        self.observed = observed
        super().__init__(f"{field}: {observed} 이(가) 한도 {limit} 을(를) 초과합니다.")

    def details(self) -> dict[str, Any]:
        return {"limit": self.limit, "observed": self.observed}


class InvalidExpressionError(SooToolError):
    """core.calc: ast.parse 실패 또는 문법 오류.

    attributes:
        message:  사람이 읽을 에러 메시지.
        location: (line, column) 또는 None.
    """

    code = "invalid_expression"

    def __init__(self, message: str, location: tuple[int, int] | None = None) -> None:
        self.message  = message
        self.location = location
        if location is None:
            super().__init__(message)
        else:
            super().__init__(f"{message} (line {location[0]}, col {location[1]})")

    def details(self) -> dict[str, Any]:
        return {"line": self.location[0], "column": self.location[1]} if self.location else {}


class DisallowedOperationError(SooToolError):
    """core.calc: 화이트리스트 위반 노드·연산자·함수 참조."""

    code = "disallowed_operation"

    def __init__(
        self,
        node_kind:  str,
        detail:     str                         = "",
        location:   tuple[int, int] | None      = None,
    ) -> None:
        self.node_kind = node_kind
        self.detail    = detail
        self.location  = location
        loc_part       = ""
        if location is not None:
            loc_part = f" (line {location[0]}, col {location[1]})"
        detail_part = f": {detail}" if detail else ""
        super().__init__(f"disallowed {node_kind}{detail_part}{loc_part}")

    def details(self) -> dict[str, Any]:
        return {"node_kind": self.node_kind}


class UndefinedVariableError(SooToolError):
    """core.calc: 변수 딕셔너리에 존재하지 않는 Name 참조."""

    code = "undefined_variable"

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"undefined variable: {name!r}")

    def details(self) -> dict[str, Any]:
        return {"name": self.name}


class ExpressionTooComplexError(SooToolError):
    """core.calc: 노드 상한 또는 표현식 문자열 상한 초과."""

    code = "expression_too_complex"

    def __init__(self, reason: str, limit: int, observed: int) -> None:
        self.reason   = reason
        self.limit    = limit
        self.observed = observed
        super().__init__(f"{reason}: {observed} exceeds limit {limit}")

    def details(self) -> dict[str, Any]:
        return {"reason": self.reason, "limit": self.limit, "observed": self.observed}
