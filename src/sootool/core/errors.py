class SooToolError(Exception):
    pass


class InvalidInputError(SooToolError):
    pass


class DomainConstraintError(SooToolError):
    pass


class PrecisionLossError(SooToolError):
    pass


class UnsafeDirectoryError(SooToolError):
    """정책·초안·감사 로그 저장 디렉터리가 안전하지 않음(심볼릭 링크, 타인 소유, 비디렉터리)."""


class InputLimitError(DomainConstraintError):
    """도구 입력이 호출 단위 한도를 초과함.

    attributes:
        field:    한도가 적용된 입력 이름.
        limit:    허용 상한.
        observed: 실제 입력값.
    """

    def __init__(self, field: str, limit: int, observed: int) -> None:
        self.field    = field
        self.limit    = limit
        self.observed = observed
        super().__init__(f"{field}: {observed} 이(가) 한도 {limit} 을(를) 초과합니다.")


class InvalidExpressionError(SooToolError):
    """core.calc: ast.parse 실패 또는 문법 오류.

    attributes:
        message:  사람이 읽을 에러 메시지.
        location: (line, column) 또는 None.
    """

    def __init__(self, message: str, location: tuple[int, int] | None = None) -> None:
        self.message  = message
        self.location = location
        if location is None:
            super().__init__(message)
        else:
            super().__init__(f"{message} (line {location[0]}, col {location[1]})")


class DisallowedOperationError(SooToolError):
    """core.calc: 화이트리스트 위반 노드·연산자·함수 참조."""

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


class UndefinedVariableError(SooToolError):
    """core.calc: 변수 딕셔너리에 존재하지 않는 Name 참조."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"undefined variable: {name!r}")


class ExpressionTooComplexError(SooToolError):
    """core.calc: 노드 상한 또는 표현식 문자열 상한 초과."""

    def __init__(self, reason: str, limit: int, observed: int) -> None:
        self.reason   = reason
        self.limit    = limit
        self.observed = observed
        super().__init__(f"{reason}: {observed} exceeds limit {limit}")
