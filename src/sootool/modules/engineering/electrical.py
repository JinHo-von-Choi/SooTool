"""Electrical engineering tools: Ohm's law, power equations, resistor networks."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_ZERO = Decimal("0")


def _d_or_none(v: str | None) -> Decimal | None:
    return D(v) if v is not None else None


def _sqrt_decimal(x: Decimal) -> Decimal:
    """Newton-Raphson square root for Decimal."""
    if x < _ZERO:
        raise InvalidInputError("제곱근의 피연산자는 0 이상이어야 합니다.")
    if x == _ZERO:
        return _ZERO
    # Use Python float as initial guess then refine
    guess = Decimal(str(float(x) ** 0.5))
    two   = Decimal("2")
    for _ in range(30):
        next_g = (guess + div(x, guess)) / two
        if abs(next_g - guess) < Decimal("1E-40"):
            break
        guess = next_g
    return guess


@REGISTRY.tool(
    namespace="engineering",
    name="electrical_ohm",
    description="Ohm's law: V=IR. Provide exactly 2 of {voltage, current, resistance}.",
    version="1.0.0",
)
def electrical_ohm(
    voltage:    str | None = None,
    current:    str | None = None,
    resistance: str | None = None,
) -> dict[str, Any]:
    """Compute the missing Ohm's law variable (V = I × R).

    Exactly two of the three parameters must be provided. The third is
    computed from the others.

    Args:
        voltage:    Voltage in Volts (Decimal string), or None.
        current:    Current in Amperes (Decimal string), or None.
        resistance: Resistance in Ohms (Decimal string), or None.

    Returns:
        {voltage: str, current: str, resistance: str, trace}

    Raises:
        InvalidInputError: If not exactly 2 values are given, or any value
            is non-positive where required.
    """
    trace = CalcTrace(tool="engineering.electrical_ohm", formula="V = I × R")

    given = {k: v for k, v in [("voltage", voltage), ("current", current), ("resistance", resistance)] if v is not None}
    if len(given) != 2:
        raise InvalidInputError(
            f"정확히 2개의 값을 입력해야 합니다. 현재 {len(given)}개 입력됨: {list(given.keys())}"
        )

    trace.input("given", list(given.keys()))

    v_d = _d_or_none(voltage)
    i_d = _d_or_none(current)
    r_d = _d_or_none(resistance)

    if voltage is None:
        # V = I * R
        assert i_d is not None and r_d is not None
        if i_d <= _ZERO:
            raise InvalidInputError("current는 0 초과여야 합니다.")
        if r_d <= _ZERO:
            raise InvalidInputError("resistance는 0 초과여야 합니다.")
        v_d = mul(i_d, r_d)
        trace.step("V = I × R", str(v_d))

    elif current is None:
        # I = V / R
        assert v_d is not None and r_d is not None
        if v_d < _ZERO:
            raise InvalidInputError("voltage는 0 이상이어야 합니다.")
        if r_d <= _ZERO:
            raise InvalidInputError("resistance는 0 초과여야 합니다.")
        i_d = div(v_d, r_d)
        trace.step("I = V / R", str(i_d))

    else:
        # R = V / I
        assert v_d is not None and i_d is not None
        if v_d < _ZERO:
            raise InvalidInputError("voltage는 0 이상이어야 합니다.")
        if i_d <= _ZERO:
            raise InvalidInputError("current는 0 초과여야 합니다.")
        r_d = div(v_d, i_d)
        trace.step("R = V / I", str(r_d))

    trace.output({"voltage": str(v_d), "current": str(i_d), "resistance": str(r_d)})

    return {
        "voltage":    str(v_d),
        "current":    str(i_d),
        "resistance": str(r_d),
        "trace":      trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="electrical_power",
    description="Power equations: P=VI=I²R=V²/R. Provide exactly 2 of {power, voltage, current, resistance}.",
    version="1.0.0",
)
def electrical_power(
    power:      str | None = None,
    voltage:    str | None = None,
    current:    str | None = None,
    resistance: str | None = None,
) -> dict[str, Any]:
    """Compute missing power/electrical variables from two given values.

    Supported equation sets (exactly 2 values required):
      - P, V      → I = P/V,  R = V²/P
      - P, I      → V = P/I,  R = P/I²
      - P, R      → I = √(P/R), V = √(P*R)
      - V, I      → P = V*I,  R = V/I
      - V, R      → P = V²/R, I = V/R
      - I, R      → P = I²*R, V = I*R

    Args:
        power:      Power in Watts (Decimal string), or None.
        voltage:    Voltage in Volts (Decimal string), or None.
        current:    Current in Amperes (Decimal string), or None.
        resistance: Resistance in Ohms (Decimal string), or None.

    Returns:
        {power: str, voltage: str, current: str, resistance: str, trace}

    Raises:
        InvalidInputError: If not exactly 2 compatible values are given.
    """
    trace = CalcTrace(tool="engineering.electrical_power", formula="P=VI=I²R=V²/R")

    given = {k: v for k, v in [("power", power), ("voltage", voltage), ("current", current), ("resistance", resistance)] if v is not None}
    if len(given) != 2:
        raise InvalidInputError(
            f"정확히 2개의 값을 입력해야 합니다. 현재 {len(given)}개 입력됨: {list(given.keys())}"
        )

    keys = frozenset(given.keys())
    trace.input("given", list(given.keys()))

    p_d = _d_or_none(power)
    v_d = _d_or_none(voltage)
    i_d = _d_or_none(current)
    r_d = _d_or_none(resistance)

    if keys == frozenset({"voltage", "current"}):
        # P = V * I, R = V / I
        assert v_d is not None and i_d is not None
        p_d = mul(v_d, i_d)
        r_d = div(v_d, i_d)
        trace.step("P = V × I", str(p_d))
        trace.step("R = V / I", str(r_d))

    elif keys == frozenset({"voltage", "resistance"}):
        # P = V² / R, I = V / R
        assert v_d is not None and r_d is not None
        p_d = div(mul(v_d, v_d), r_d)
        i_d = div(v_d, r_d)
        trace.step("P = V² / R", str(p_d))
        trace.step("I = V / R", str(i_d))

    elif keys == frozenset({"current", "resistance"}):
        # P = I² * R, V = I * R
        assert i_d is not None and r_d is not None
        p_d = mul(mul(i_d, i_d), r_d)
        v_d = mul(i_d, r_d)
        trace.step("P = I² × R", str(p_d))
        trace.step("V = I × R", str(v_d))

    elif keys == frozenset({"power", "voltage"}):
        # I = P / V, R = V² / P
        assert p_d is not None and v_d is not None
        i_d = div(p_d, v_d)
        r_d = div(mul(v_d, v_d), p_d)
        trace.step("I = P / V", str(i_d))
        trace.step("R = V² / P", str(r_d))

    elif keys == frozenset({"power", "current"}):
        # V = P / I, R = P / I²
        assert p_d is not None and i_d is not None
        v_d = div(p_d, i_d)
        r_d = div(p_d, mul(i_d, i_d))
        trace.step("V = P / I", str(v_d))
        trace.step("R = P / I²", str(r_d))

    elif keys == frozenset({"power", "resistance"}):
        # I = √(P/R), V = √(P*R)
        assert p_d is not None and r_d is not None
        pr_ratio   = div(p_d, r_d)
        pr_product = mul(p_d, r_d)
        i_d = _sqrt_decimal(pr_ratio)
        v_d = _sqrt_decimal(pr_product)
        trace.step("I = √(P/R)", str(i_d))
        trace.step("V = √(P×R)", str(v_d))

    else:
        raise InvalidInputError(f"지원하지 않는 입력 조합: {list(given.keys())}")

    trace.output({"power": str(p_d), "voltage": str(v_d), "current": str(i_d), "resistance": str(r_d)})

    return {
        "power":      str(p_d),
        "voltage":    str(v_d),
        "current":    str(i_d),
        "resistance": str(r_d),
        "trace":      trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="resistor_series",
    description="Total resistance of resistors in series: R_total = ΣRᵢ.",
    version="1.0.0",
)
def resistor_series(resistors: list[str]) -> dict[str, Any]:
    """Compute total resistance for resistors connected in series.

    Formula: R_total = R₁ + R₂ + … + Rₙ

    Args:
        resistors: List of resistance values as Decimal strings (all > 0).

    Returns:
        {total: str, trace}

    Raises:
        InvalidInputError: If fewer than 1 resistor given or any value ≤ 0.
    """
    trace = CalcTrace(tool="engineering.resistor_series", formula="R_total = ΣRᵢ")

    if not resistors:
        raise InvalidInputError("resistors 리스트는 최소 1개 이상이어야 합니다.")

    values = [D(r) for r in resistors]
    for i, v in enumerate(values):
        if v <= _ZERO:
            raise InvalidInputError(f"resistors[{i}]는 0 초과여야 합니다. 입력값: {resistors[i]!r}")

    trace.input("resistors", resistors)

    total = add(*values)
    trace.step("total", str(total))
    trace.output(str(total))

    return {
        "total": str(total),
        "trace": trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="resistor_parallel",
    description="Total resistance of resistors in parallel: 1/R_total = Σ(1/Rᵢ).",
    version="1.0.0",
)
def resistor_parallel(resistors: list[str]) -> dict[str, Any]:
    """Compute total resistance for resistors connected in parallel.

    Formula: 1/R_total = 1/R₁ + 1/R₂ + … + 1/Rₙ

    Args:
        resistors: List of resistance values as Decimal strings (all > 0).

    Returns:
        {total: str, trace}

    Raises:
        InvalidInputError: If fewer than 1 resistor given or any value ≤ 0.
    """
    trace = CalcTrace(tool="engineering.resistor_parallel", formula="1/R_total = Σ(1/Rᵢ)")

    if not resistors:
        raise InvalidInputError("resistors 리스트는 최소 1개 이상이어야 합니다.")

    values = [D(r) for r in resistors]
    for i, v in enumerate(values):
        if v <= _ZERO:
            raise InvalidInputError(f"resistors[{i}]는 0 초과여야 합니다. 입력값: {resistors[i]!r}")

    trace.input("resistors", resistors)

    reciprocal_sum = add(*[div(Decimal("1"), v) for v in values])
    total          = div(Decimal("1"), reciprocal_sum)

    trace.step("sum_of_reciprocals", str(reciprocal_sum))
    trace.step("total", str(total))
    trace.output(str(total))

    return {
        "total": str(total),
        "trace": trace.to_dict(),
    }
