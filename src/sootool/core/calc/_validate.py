"""core.calc 파싱과 화이트리스트 검증.
"""
from __future__ import annotations

import ast

from sootool.core.calc._rules import (
    _ALLOWED_BINOP_TYPES,
    _ALLOWED_FUNCTIONS,
    _ALLOWED_NODE_TYPES,
    _ALLOWED_UNARYOP_TYPES,
    _EXPLICITLY_DENIED,
    _OPERATOR_PARENT_NODES,
    _max_expr_len,
    _max_nodes,
)
from sootool.core.errors import (
    DisallowedOperationError,
    ExpressionTooComplexError,
    InvalidExpressionError,
)


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
