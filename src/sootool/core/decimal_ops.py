from __future__ import annotations

from decimal import Decimal, getcontext

getcontext().prec = 50
Number = Decimal | int | str


def D(value: Number | float, *, allow_float: bool = False) -> Decimal:
    if isinstance(value, float):
        if not allow_float:
            raise TypeError(
                "float 입력 금지: 정밀도 손실 위험. 문자열로 전달하거나 allow_float=True 명시."
            )
        return Decimal(str(value))
    return Decimal(value)


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
        raise ZeroDivisionError("분모가 0")
    return a / b


def power(base: Decimal, exponent: int) -> Decimal:
    return base ** exponent
