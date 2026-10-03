from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext

from sootool.core.errors import DivisionByZeroError, FloatInputError, InvalidNumberError

getcontext().prec = 50
Number = Decimal | int | str


def D(value: Number | float, *, allow_float: bool = False) -> Decimal:
    """숫자 입력을 Decimal 로 변환한다. 숫자가 아니면 InvalidNumberError 를 낸다."""
    if isinstance(value, float):
        if not allow_float:
            raise FloatInputError(
                "float 입력 금지: 정밀도 손실 위험. 문자열로 전달하거나 allow_float=True 명시."
            )
        return Decimal(str(value))
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise InvalidNumberError(
            f"숫자 문자열이 아닙니다: {value!r}. 쉼표, 단위, 공백 없이 숫자만 전달하세요."
        ) from exc


def add(*operands: Decimal) -> Decimal:
    total = Decimal("0")
    for x in operands:
        total += x
    return total


def sub(a: Decimal, b: Decimal) -> Decimal:
    return a - b


def mul(*operands: Decimal) -> Decimal:
    result = Decimal("1")
    for x in operands:
        result *= x
    return result


def div(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        raise DivisionByZeroError("분모가 0")
    return a / b


def power(base: Decimal, exponent: int) -> Decimal:
    return base ** exponent
