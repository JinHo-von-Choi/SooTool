"""숫자 입력을 문자열 숫자로 바꾸는 규칙(MCP 경계와 SDK 가 공유한다).

도구는 숫자를 Decimal 문자열로 받는다. 호출자가 정수, Decimal, 부동소수를 넘기면 문자열로 바꾼다. 부동소수는
배정밀도 값의 최단 왕복 표기(repr)로 바뀌어 의도한 자릿수와 다를 수 있으므로 변환 여부를 함께 알린다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any


def number_to_str(value: Any) -> tuple[Any, bool]:
    """(변환된 값, 부동소수에서 변환됐는지)를 반환한다. 숫자가 아닌 값은 그대로 둔다."""
    if isinstance(value, bool):
        return value, False
    if isinstance(value, (int, Decimal)):
        return str(value), False
    if isinstance(value, float) and math.isfinite(value):
        return repr(value), True
    return value, False
