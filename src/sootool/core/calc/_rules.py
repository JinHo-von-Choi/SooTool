"""core.calc 화이트리스트(허용 노드, 연산자, 함수, 상수)와 한도.
"""
from __future__ import annotations

import ast
import os
from typing import Any

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


# 명시적 차단 노드, 에러 메시지를 구체화하기 위해 별도 테이블 유지.
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


_MPMATH_CONSTANTS: dict[str, Any] = {
    # 각 상수는 평가 시점 mpmath.mp.dps 로 생성된다.
}
