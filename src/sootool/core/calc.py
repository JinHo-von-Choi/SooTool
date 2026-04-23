"""
core/calc.py — AST 기반 안전 수식 평가기.

ADR-017 (core.calc 보안 경계) 구현.

설계:
- ast.parse(mode="eval") + NodeVisitor 화이트리스트로 허용 노드만 통과.
- 순수 정수 사칙·모듈러·정수 지수 Pow는 Decimal 직접 연산.
- 초월 함수와 비정수 지수 Pow는 mpmath.mp.dps 로컬 컨텍스트로 계산 후
  core.cast.mpmath_to_decimal 을 경유해 Decimal 문자열로 복귀(ADR-008).
- Python eval/exec/compile 미사용. AST 평가만 수행.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import ast
import os
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Any

import mpmath

from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import (
    DisallowedOperationError,
    DomainConstraintError,
    ExpressionTooComplexError,
    InvalidExpressionError,
    UndefinedVariableError,
)

# ----------------------------------------------------------------------------
# 화이트리스트 정의
# ----------------------------------------------------------------------------

_ALLOWED_NODE_TYPES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Call,
    ast.Tuple,    # Call 인자 위치에서만; 부모 컨텍스트에서 추가 검증
    ast.Load,     # ast.Name.ctx 에 자동으로 붙는 컨텍스트 노드
)

# operator·unaryop 노드는 BinOp/UnaryOp 가 부모에서 검사한다. ast.walk 에서
# 독립 노드로 등장하므로 화이트리스트 단계에서 스킵해야 한다.
_OPERATOR_PARENT_NODES: tuple[type[ast.AST], ...] = (
    ast.operator,
    ast.unaryop,
    ast.cmpop,     # Compare 노드가 차단되면 cmpop 도 도달하지 않지만 안전망
    ast.boolop,    # BoolOp 이 차단되므로 도달하지 않지만 안전망
    ast.expr_context,  # Load/Store/Del 의 상위. Load 는 별도로 허용
)

_ALLOWED_BINOP_TYPES: tuple[type[ast.AST], ...] = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.FloorDiv,
)

_ALLOWED_UNARYOP_TYPES: tuple[type[ast.AST], ...] = (
    ast.USub,
    ast.UAdd,
)

_ALLOWED_FUNCTIONS: frozenset[str] = frozenset({
    "sqrt", "abs",  "floor", "ceil", "round",
    "log",  "log10", "log2", "ln",   "exp",
    "sin",  "cos",  "tan",   "asin", "acos", "atan", "atan2",
    "pow",
})

_ALLOWED_CONSTANTS: frozenset[str] = frozenset({"pi", "e", "tau"})

# 초월 함수는 mpmath 경유. 순수 Decimal 연산이 불가능한 함수 집합.
_TRANSCENDENTAL_FUNCTIONS: frozenset[str] = frozenset({
    "sqrt", "log", "log10", "log2", "ln", "exp",
    "sin",  "cos", "tan",   "asin", "acos", "atan", "atan2",
})

# 명시적 차단 노드 — 에러 메시지를 구체화하기 위해 별도 테이블 유지.
_EXPLICITLY_DENIED: dict[type[ast.AST], str] = {
    ast.Attribute:     "attribute access",
    ast.Subscript:     "subscript access",
    ast.Lambda:        "lambda expression",
    ast.GeneratorExp:  "generator expression",
    ast.ListComp:      "list comprehension",
    ast.DictComp:      "dict comprehension",
    ast.SetComp:       "set comprehension",
    ast.BoolOp:        "boolean operator",
    ast.Compare:       "comparison operator",
    ast.IfExp:         "conditional expression",
    ast.NamedExpr:     "walrus operator",
    ast.JoinedStr:     "f-string",
    ast.FormattedValue: "f-string value",
    ast.Starred:       "star argument",
    ast.List:          "list literal",
    ast.Set:           "set literal",
    ast.Dict:          "dict literal",
    ast.Await:         "await",
    ast.Yield:         "yield",
    ast.YieldFrom:     "yield from",
}


# ----------------------------------------------------------------------------
# 환경변수 기반 복잡도 상한
# ----------------------------------------------------------------------------

_DEFAULT_MAX_NODES    = 300
_DEFAULT_MAX_EXPR_LEN = 3000


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _max_nodes() -> int:
    return _env_int("SOOTOOL_CALC_MAX_NODES", _DEFAULT_MAX_NODES)


def _max_expr_len() -> int:
    return _env_int("SOOTOOL_CALC_MAX_EXPR_LEN", _DEFAULT_MAX_EXPR_LEN)


# ----------------------------------------------------------------------------
# 파서 / 검증
# ----------------------------------------------------------------------------

def _parse(expression: str) -> ast.Expression:
    limit = _max_expr_len()
    if len(expression) > limit:
        raise ExpressionTooComplexError(
            reason   = "expression string too long",
            limit    = limit,
            observed = len(expression),
        )
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        loc: tuple[int, int] | None = None
        if exc.lineno is not None and exc.offset is not None:
            loc = (exc.lineno, exc.offset)
        raise InvalidExpressionError(exc.msg or "syntax error", location=loc) from exc
    assert isinstance(tree, ast.Expression)
    return tree


def _count_and_validate(tree: ast.Expression) -> dict[str, int]:
    """단일 순회로 노드 개수와 화이트리스트 준수 여부를 검증한다.

    returns:
        노드 종류별 카운트 dict (trace.parsed_ast_summary 용).
    raises:
        ExpressionTooComplexError, DisallowedOperationError.
    """
    node_limit = _max_nodes()
    counts:    dict[str, int] = {}
    total:     int            = 0

    for node in ast.walk(tree):
        # operator·unaryop 등은 BinOp/UnaryOp 에서 이미 검사하므로 스킵한다.
        if isinstance(node, _OPERATOR_PARENT_NODES) and not isinstance(node, ast.Load):
            continue

        total += 1
        if total > node_limit:
            raise ExpressionTooComplexError(
                reason   = "too many AST nodes",
                limit    = node_limit,
                observed = total,
            )

        kind = type(node).__name__
        counts[kind] = counts.get(kind, 0) + 1

        if type(node) in _EXPLICITLY_DENIED:
            raise DisallowedOperationError(
                node_kind = kind,
                detail    = _EXPLICITLY_DENIED[type(node)],
                location  = _location_of(node),
            )

        if isinstance(node, _ALLOWED_NODE_TYPES):
            if isinstance(node, ast.BinOp):
                if not isinstance(node.op, _ALLOWED_BINOP_TYPES):
                    raise DisallowedOperationError(
                        node_kind = type(node.op).__name__,
                        detail    = "binary operator",
                        location  = _location_of(node),
                    )
            elif isinstance(node, ast.UnaryOp):
                if not isinstance(node.op, _ALLOWED_UNARYOP_TYPES):
                    raise DisallowedOperationError(
                        node_kind = type(node.op).__name__,
                        detail    = "unary operator",
                        location  = _location_of(node),
                    )
            elif isinstance(node, ast.Call):
                _validate_call(node)
            elif isinstance(node, ast.Constant):
                _validate_constant(node)
            elif isinstance(node, ast.Tuple):
                # Tuple 은 Call 의 인자 위치에서만 정당함. 부모 컨텍스트 검사는
                # _validate_call 에서 처리되므로 여기서는 AST 단독으로는 허용된
                # 상태로 남겨둔다. 평가 단계에서 Tuple 값이 직접 결과가 되는
                # 경로는 존재하지 않는다(최상위는 Expression.body 단일 노드).
                continue
            continue

        raise DisallowedOperationError(
            node_kind = kind,
            detail    = "node type not permitted",
            location  = _location_of(node),
        )

    return counts


def _validate_call(node: ast.Call) -> None:
    if not isinstance(node.func, ast.Name):
        raise DisallowedOperationError(
            node_kind = type(node.func).__name__,
            detail    = "callable must be a bare function name",
            location  = _location_of(node),
        )
    name = node.func.id
    if name not in _ALLOWED_FUNCTIONS:
        raise DisallowedOperationError(
            node_kind = "Call",
            detail    = f"function {name!r} is not whitelisted",
            location  = _location_of(node),
        )
    if node.keywords:
        raise DisallowedOperationError(
            node_kind = "Call",
            detail    = "keyword arguments are not permitted",
            location  = _location_of(node),
        )


def _validate_constant(node: ast.Constant) -> None:
    value = node.value
    if isinstance(value, bool):
        # bool 은 int 의 하위 타입이므로 명시적으로 차단한다.
        raise DisallowedOperationError(
            node_kind = "Constant",
            detail    = "boolean constants are not permitted",
            location  = _location_of(node),
        )
    if isinstance(value, (int, float)):
        return
    raise DisallowedOperationError(
        node_kind = "Constant",
        detail    = f"constant of type {type(value).__name__} not permitted",
        location  = _location_of(node),
    )


def _location_of(node: ast.AST) -> tuple[int, int] | None:
    line = getattr(node, "lineno", None)
    col  = getattr(node, "col_offset", None)
    if line is None or col is None:
        return None
    return (int(line), int(col))


# ----------------------------------------------------------------------------
# 평가기
# ----------------------------------------------------------------------------

_MPMATH_CONSTANTS: dict[str, Any] = {
    # 각 상수는 평가 시점 mpmath.mp.dps 로 생성된다.
}


def _constant_value(name: str) -> Any:
    if name == "pi":
        return mpmath.mp.pi
    if name == "e":
        return mpmath.mp.e
    if name == "tau":
        return 2 * mpmath.mp.pi
    raise UndefinedVariableError(name)


def _variable_value(name: str, variables: dict[str, str]) -> Decimal:
    raw = variables.get(name)
    if raw is None:
        raise UndefinedVariableError(name)
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise DomainConstraintError(
            f"variable {name!r} is not a valid Decimal string: {raw!r}",
        ) from exc


def _literal_to_decimal(value: int | float) -> Decimal:
    if isinstance(value, float):
        # float 누수를 막기 위해 문자열 경유.
        return Decimal(repr(value))
    return Decimal(value)


def _is_integer_decimal(x: Decimal) -> bool:
    return x == x.to_integral_value()


def _to_mpf(x: Decimal | Any) -> Any:
    if isinstance(x, Decimal):
        return mpmath.mpf(str(x))
    return x


class _Evaluator:
    """재귀 하강 평가기. 각 노드에서 Decimal 또는 mpmath 값 반환.

    반환 타입은 `Decimal | mpmath.mpf` 두 가지. 혼합 시 최종 결과에서 Decimal
    문자열로 통일된다.
    """

    def __init__(
        self,
        variables:   dict[str, str],
        precision:   int,
        steps:       list[dict[str, Any]],
        record_full: bool,
    ) -> None:
        self.variables   = variables
        self.precision   = precision
        self.steps       = steps
        self.record_full = record_full

    # -- 디스패치 ------------------------------------------------------------

    def evaluate(self, node: ast.AST) -> Decimal | Any:
        if isinstance(node, ast.Expression):
            return self.evaluate(node.body)
        if isinstance(node, ast.Constant):
            value = node.value
            # _validate_constant 에서 int/float 외 모두 차단되므로 이 지점에선
            # int 또는 float 만 도달한다. mypy narrowing 을 위한 assert.
            assert isinstance(value, (int, float)) and not isinstance(value, bool)
            return _literal_to_decimal(value)
        if isinstance(node, ast.Name):
            return self._eval_name(node)
        if isinstance(node, ast.UnaryOp):
            return self._eval_unary(node)
        if isinstance(node, ast.BinOp):
            return self._eval_binop(node)
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        raise DisallowedOperationError(
            node_kind = type(node).__name__,
            detail    = "unreachable: node passed whitelist but not handled",
            location  = _location_of(node),
        )

    # -- Name / Constant ------------------------------------------------------

    def _eval_name(self, node: ast.Name) -> Decimal | Any:
        name = node.id
        if name in _ALLOWED_CONSTANTS:
            return _constant_value(name)
        return _variable_value(name, self.variables)

    # -- UnaryOp --------------------------------------------------------------

    def _eval_unary(self, node: ast.UnaryOp) -> Decimal | Any:
        operand = self.evaluate(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        # USub
        if isinstance(operand, Decimal):
            return -operand
        return -operand

    # -- BinOp ----------------------------------------------------------------

    def _eval_binop(self, node: ast.BinOp) -> Decimal | Any:
        left  = self.evaluate(node.left)
        right = self.evaluate(node.right)
        op    = node.op

        # 한 쪽이 mpmath 값이면 양쪽 모두 mpmath 로 승격해 계산한다.
        if not isinstance(left, Decimal) or not isinstance(right, Decimal):
            with mpmath.workdps(self.precision):
                lm = _to_mpf(left)
                rm = _to_mpf(right)
                value = self._apply_binop_mp(op, lm, rm, node)
            self._record(f"{self._op_symbol(op)}", value)
            return value

        # 양쪽 Decimal. Pow 지수가 정수가 아니면 mpmath 경로로 전환.
        if isinstance(op, ast.Pow) and not _is_integer_decimal(right):
            with mpmath.workdps(self.precision):
                value = mpmath.power(mpmath.mpf(str(left)), mpmath.mpf(str(right)))
            self._record("**", value)
            return value

        result = self._apply_binop_decimal(op, left, right, node)
        self._record(self._op_symbol(op), result)
        return result

    def _apply_binop_decimal(
        self,
        op:    ast.operator,
        left:  Decimal,
        right: Decimal,
        node:  ast.BinOp,
    ) -> Decimal:
        try:
            if isinstance(op, ast.Add):
                return left + right
            if isinstance(op, ast.Sub):
                return left - right
            if isinstance(op, ast.Mult):
                return left * right
            if isinstance(op, ast.Div):
                if right == 0:
                    raise DomainConstraintError("division by zero")
                return left / right
            if isinstance(op, ast.Mod):
                if right == 0:
                    raise DomainConstraintError("modulo by zero")
                return left % right
            if isinstance(op, ast.FloorDiv):
                if right == 0:
                    raise DomainConstraintError("floor division by zero")
                return left // right
            if isinstance(op, ast.Pow):
                # 정수 지수만 여기로 유입된다.
                exponent = int(right)
                return left ** exponent
        except DivisionByZero as exc:
            raise DomainConstraintError("division by zero") from exc
        except InvalidOperation as exc:
            raise DomainConstraintError(str(exc) or "invalid Decimal operation") from exc
        raise DisallowedOperationError(
            node_kind = type(op).__name__,
            detail    = "unreachable binary operator",
            location  = _location_of(node),
        )

    def _apply_binop_mp(
        self,
        op:    ast.operator,
        left:  Any,
        right: Any,
        node:  ast.BinOp,
    ) -> Any:
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            if right == 0:
                raise DomainConstraintError("division by zero")
            return left / right
        if isinstance(op, ast.Mod):
            if right == 0:
                raise DomainConstraintError("modulo by zero")
            return mpmath.fmod(left, right)
        if isinstance(op, ast.FloorDiv):
            if right == 0:
                raise DomainConstraintError("floor division by zero")
            return mpmath.floor(left / right)
        if isinstance(op, ast.Pow):
            return mpmath.power(left, right)
        raise DisallowedOperationError(
            node_kind = type(op).__name__,
            detail    = "unreachable mpmath binary operator",
            location  = _location_of(node),
        )

    @staticmethod
    def _op_symbol(op: ast.operator) -> str:
        return {
            ast.Add:      "+",
            ast.Sub:      "-",
            ast.Mult:     "*",
            ast.Div:      "/",
            ast.Mod:      "%",
            ast.FloorDiv: "//",
            ast.Pow:      "**",
        }.get(type(op), type(op).__name__)

    # -- Call ------------------------------------------------------------------

    def _eval_call(self, node: ast.Call) -> Decimal | Any:
        assert isinstance(node.func, ast.Name)
        name = node.func.id
        args = [self.evaluate(a) for a in node.args]

        if name in _TRANSCENDENTAL_FUNCTIONS:
            with mpmath.workdps(self.precision):
                mp_args = [_to_mpf(a) for a in args]
                value   = self._call_mpmath(name, mp_args, node)
            self._record(f"{name}(..)", value)
            return value

        result = self._call_decimal(name, args, node)
        self._record(f"{name}(..)", result)
        return result

    def _call_mpmath(self, name: str, args: list[Any], node: ast.Call) -> Any:
        if name == "sqrt":
            self._require_arity(name, args, 1, node)
            if args[0] < 0:
                raise DomainConstraintError("sqrt of negative number")
            return mpmath.sqrt(args[0])
        if name == "exp":
            self._require_arity(name, args, 1, node)
            return mpmath.exp(args[0])
        if name == "log":
            if len(args) == 1:
                if args[0] <= 0:
                    raise DomainConstraintError("log of non-positive number")
                return mpmath.log(args[0])
            if len(args) == 2:
                if args[0] <= 0 or args[1] <= 0 or args[1] == 1:
                    raise DomainConstraintError("log: invalid arguments")
                return mpmath.log(args[0], args[1])
            raise DisallowedOperationError(
                node_kind = "Call",
                detail    = f"log expects 1 or 2 args, got {len(args)}",
                location  = _location_of(node),
            )
        if name == "ln":
            self._require_arity(name, args, 1, node)
            if args[0] <= 0:
                raise DomainConstraintError("ln of non-positive number")
            return mpmath.log(args[0])
        if name == "log10":
            self._require_arity(name, args, 1, node)
            if args[0] <= 0:
                raise DomainConstraintError("log10 of non-positive number")
            return mpmath.log10(args[0])
        if name == "log2":
            self._require_arity(name, args, 1, node)
            if args[0] <= 0:
                raise DomainConstraintError("log2 of non-positive number")
            return mpmath.log(args[0], 2)
        if name == "sin":
            self._require_arity(name, args, 1, node)
            return mpmath.sin(args[0])
        if name == "cos":
            self._require_arity(name, args, 1, node)
            return mpmath.cos(args[0])
        if name == "tan":
            self._require_arity(name, args, 1, node)
            return mpmath.tan(args[0])
        if name == "asin":
            self._require_arity(name, args, 1, node)
            if args[0] < -1 or args[0] > 1:
                raise DomainConstraintError("asin domain: [-1, 1]")
            return mpmath.asin(args[0])
        if name == "acos":
            self._require_arity(name, args, 1, node)
            if args[0] < -1 or args[0] > 1:
                raise DomainConstraintError("acos domain: [-1, 1]")
            return mpmath.acos(args[0])
        if name == "atan":
            self._require_arity(name, args, 1, node)
            return mpmath.atan(args[0])
        if name == "atan2":
            self._require_arity(name, args, 2, node)
            return mpmath.atan2(args[0], args[1])
        raise DisallowedOperationError(
            node_kind = "Call",
            detail    = f"unreachable transcendental function {name!r}",
            location  = _location_of(node),
        )

    def _call_decimal(
        self,
        name: str,
        args: list[Any],
        node: ast.Call,
    ) -> Decimal | Any:
        if name == "abs":
            self._require_arity(name, args, 1, node)
            if isinstance(args[0], Decimal):
                return abs(args[0])
            with mpmath.workdps(self.precision):
                return mpmath.fabs(args[0])
        if name == "floor":
            self._require_arity(name, args, 1, node)
            if isinstance(args[0], Decimal):
                return args[0].to_integral_value(rounding="ROUND_FLOOR")
            with mpmath.workdps(self.precision):
                return mpmath.floor(args[0])
        if name == "ceil":
            self._require_arity(name, args, 1, node)
            if isinstance(args[0], Decimal):
                return args[0].to_integral_value(rounding="ROUND_CEILING")
            with mpmath.workdps(self.precision):
                return mpmath.ceil(args[0])
        if name == "round":
            if len(args) not in (1, 2):
                raise DisallowedOperationError(
                    node_kind = "Call",
                    detail    = f"round expects 1 or 2 args, got {len(args)}",
                    location  = _location_of(node),
                )
            ndigits = 0
            if len(args) == 2:
                ndigits_dec = args[1] if isinstance(args[1], Decimal) else Decimal(str(args[1]))
                if not _is_integer_decimal(ndigits_dec):
                    raise DomainConstraintError("round ndigits must be integer")
                ndigits = int(ndigits_dec)
            value = args[0] if isinstance(args[0], Decimal) else mpmath_to_decimal(
                args[0], digits=self.precision,
            )
            quantizer = Decimal(10) ** (-ndigits)
            return value.quantize(quantizer, rounding="ROUND_HALF_EVEN")
        if name == "pow":
            self._require_arity(name, args, 2, node)
            base, exponent = args[0], args[1]
            if (
                isinstance(base, Decimal)
                and isinstance(exponent, Decimal)
                and _is_integer_decimal(exponent)
            ):
                return base ** int(exponent)
            with mpmath.workdps(self.precision):
                return mpmath.power(_to_mpf(base), _to_mpf(exponent))
        raise DisallowedOperationError(
            node_kind = "Call",
            detail    = f"unreachable decimal function {name!r}",
            location  = _location_of(node),
        )

    @staticmethod
    def _require_arity(
        name:     str,
        args:     list[Any],
        expected: int,
        node:     ast.Call,
    ) -> None:
        if len(args) != expected:
            raise DisallowedOperationError(
                node_kind = "Call",
                detail    = f"{name} expects {expected} arg(s), got {len(args)}",
                location  = _location_of(node),
            )

    # -- trace 기록 -----------------------------------------------------------

    def _record(self, label: str, value: Any) -> None:
        if not self.record_full:
            return
        if isinstance(value, Decimal):
            rendered = str(value)
        else:
            with mpmath.workdps(self.precision):
                rendered = str(mpmath_to_decimal(value, digits=self.precision))
        self.steps.append({"label": label, "value": rendered})


# ----------------------------------------------------------------------------
# 공개 API
# ----------------------------------------------------------------------------

def _normalize_result(value: Any, precision: int) -> str:
    if isinstance(value, Decimal):
        return str(value)
    with mpmath.workdps(precision):
        return str(mpmath_to_decimal(value, digits=precision))


def calc(
    expression:  str,
    variables:   dict[str, str] | None = None,
    precision:   int                   = 50,
    trace_level: str                   = "summary",
) -> dict[str, Any]:
    """AST 기반 안전 수식 평가기.

    args:
        expression:  평가할 수식 문자열.
        variables:   이름 → Decimal 문자열 바인딩. None 이면 상수·숫자 리터럴만 사용.
        precision:   mpmath 작업 정밀도(십진 자릿수). 기본 50. 1 이상이어야 함.
        trace_level: 'summary' / 'full' / 'none'. server.py 의 _apply_trace_level 에서
                     후처리되므로 본 함수는 full 이든 summary 든 동일 trace 를 반환하되,
                     full 일 때만 evaluation_steps 를 채운다.
    returns:
        {"result": Decimal 문자열, "trace": {...}}
    """
    if not isinstance(expression, str):
        raise InvalidExpressionError("expression must be a string")
    if not isinstance(precision, int) or precision < 1:
        raise DomainConstraintError("precision must be a positive integer")

    bindings: dict[str, str] = dict(variables) if variables else {}
    for k, v in bindings.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise DomainConstraintError(
                "variables must map str → str (Decimal string)",
            )

    tree   = _parse(expression)
    counts = _count_and_validate(tree)

    steps: list[dict[str, Any]] = []
    evaluator = _Evaluator(
        variables   = bindings,
        precision   = precision,
        steps       = steps,
        record_full = trace_level == "full",
    )
    value  = evaluator.evaluate(tree)
    output = _normalize_result(value, precision)

    trace: dict[str, Any] = {
        "tool":                "core.calc",
        "formula":             expression,
        "inputs": {
            "expression": expression,
            "variables":  dict(bindings),
            "precision":  precision,
        },
        "steps":               steps,
        "output":              output,
        "parsed_ast_summary":  counts,
    }

    return {"result": output, "trace": trace}
