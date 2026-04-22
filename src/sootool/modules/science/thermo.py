"""Science thermodynamics tool: ideal_gas (PV = nRT).

내부 자료형 (ADR-008):
- 입력: Decimal 문자열 (정확히 3개의 변수 제공, 1개 계산).
- 연산: Decimal.
- R = 8.314462618 J/(mol·K) (NIST 2018 CODATA).

PV = nRT  →  단위: P [Pa], V [m³], n [mol], T [K]

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY

# NIST 2018 CODATA: R = 8.314462618 J mol⁻¹ K⁻¹
_R = D("8.314462618")
_VARS = ("pressure", "volume", "moles", "temperature")


def _parse_optional(value: str | None, name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) 유효한 숫자 문자열이어야 합니다: {value!r}") from exc


@REGISTRY.tool(
    namespace="science",
    name="ideal_gas",
    description=(
        "이상 기체 법칙: PV = nRT. "
        "P [Pa], V [m³], n [mol], T [K] 중 3개 제공 시 나머지 계산. "
        "R = 8.314462618 J/(mol·K) (NIST 2018 CODATA). 전 구간 Decimal."
    ),
    version="1.0.0",
)
def ideal_gas(
    pressure:    str | None = None,
    volume:      str | None = None,
    moles:       str | None = None,
    temperature: str | None = None,
) -> dict[str, Any]:
    """Compute the missing variable in the ideal gas law PV = nRT.

    Exactly 3 of the 4 variables must be provided; the remaining one is computed.

    Args:
        pressure:    P in Pascals [Pa] (Decimal string or None).
        volume:      V in cubic metres [m³] (Decimal string or None).
        moles:       n in moles [mol] (Decimal string or None).
        temperature: T in Kelvin [K] (Decimal string or None).

    Returns:
        {pressure: str, volume: str, moles: str, temperature: str, trace}

    Raises:
        DomainConstraintError: If not exactly 3 variables are given, or computed value is negative.
        InvalidInputError:     On non-numeric inputs.
    """
    trace = CalcTrace(
        tool="science.ideal_gas",
        formula="PV = nRT  (R = 8.314462618 J/(mol·K))",
    )

    raw_vals: dict[str, str | None] = {
        "pressure":    pressure,
        "volume":      volume,
        "moles":       moles,
        "temperature": temperature,
    }

    parsed: dict[str, Decimal | None] = {
        k: _parse_optional(v, k) for k, v in raw_vals.items()
    }

    given_count = sum(1 for v in parsed.values() if v is not None)
    if given_count != 3:
        raise DomainConstraintError(
            f"정확히 3개의 변수를 제공해야 합니다 (주어진 개수: {given_count}). "
            "None으로 설정된 변수 1개가 계산됩니다."
        )

    # Identify the unknown variable
    unknown = next(k for k, v in parsed.items() if v is None)

    for k, v in parsed.items():
        if v is not None:
            trace.input(k, str(v))
    trace.step("unknown", unknown)
    trace.step("R", str(_R))

    P = parsed["pressure"]
    V = parsed["volume"]
    n = parsed["moles"]
    T = parsed["temperature"]

    if unknown == "pressure":
        # P = nRT / V
        if V == D("0"):
            raise DomainConstraintError("volume이 0이면 pressure를 계산할 수 없습니다.")
        P = (n * _R * T) / V  # type: ignore[operator]
        if P < D("0"):
            raise DomainConstraintError(f"계산된 pressure가 음수입니다: {P}")

    elif unknown == "volume":
        # V = nRT / P
        if P == D("0"):
            raise DomainConstraintError("pressure가 0이면 volume을 계산할 수 없습니다.")
        V = (n * _R * T) / P  # type: ignore[operator]
        if V < D("0"):
            raise DomainConstraintError(f"계산된 volume이 음수입니다: {V}")

    elif unknown == "moles":
        # n = PV / (RT)
        if T == D("0"):
            raise DomainConstraintError("temperature가 0K이면 moles를 계산할 수 없습니다.")
        n = (P * V) / (_R * T)  # type: ignore[operator]
        if n < D("0"):
            raise DomainConstraintError(f"계산된 moles가 음수입니다: {n}")

    elif unknown == "temperature":
        # T = PV / (nR)
        if n == D("0"):
            raise DomainConstraintError("moles가 0이면 temperature를 계산할 수 없습니다.")
        T = (P * V) / (n * _R)  # type: ignore[operator]
        if T < D("0"):
            raise DomainConstraintError(f"계산된 temperature가 음수입니다: {T}")

    trace.step("computed value", str(locals().get({"pressure": "P", "volume": "V", "moles": "n", "temperature": "T"}[unknown])))

    result = {
        "pressure":    str(P),
        "volume":      str(V),
        "moles":       str(n),
        "temperature": str(T),
    }
    trace.output(result)

    return {**result, "trace": trace.to_dict()}
