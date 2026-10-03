"""core.calc AST 평가기.
"""
from __future__ import annotations

import ast
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Any

import mpmath

from sootool.core.calc._rules import (
    _ALLOWED_CONSTANTS,
    _TRANSCENDENTAL_FUNCTIONS,
)
from sootool.core.calc._validate import (
    _location_of,
)
from sootool.core.calc._values import (
    _constant_value,
    _is_integer_decimal,
    _literal_to_decimal,
    _to_mpf,
    _variable_value,
)
from sootool.core.cast import mpmath_to_decimal
from sootool.core.errors import (
    DisallowedOperationError,
    DomainConstraintError,
)


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
