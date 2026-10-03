"""dB conversion, resistor color code and op-amp gain tools.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D, div, mul
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.engineering.electrical_ac._common import (
    _MP_DPS,
    _ONE,
    _OUT_DIG,
    _ZERO,
)

_DB_MODES = frozenset(
    {"v_to_db", "p_to_db", "db_to_v", "db_to_p", "np_to_db", "db_to_np",
     "w_to_dbm", "dbm_to_w"}
)


@REGISTRY.tool(
    namespace="engineering",
    name="db_convert",
    description=(
        "dB·Np·dBm 상호 변환. modes: v_to_db (20log10 비), p_to_db (10log10), "
        "db_to_v, db_to_p, np_to_db, db_to_np, w_to_dbm, dbm_to_w."
    ),
    version="1.0.0",
)
def db_convert(mode: str, value: str, reference: str = "1") -> dict[str, Any]:
    """Convert between linear quantities and decibel/neper scales.

    Args:
        mode:      변환 모드 (위 설명 참조)
        value:     입력 값 (Decimal string)
        reference: 기준값 (Decimal string). v_to_db/p_to_db에서 비율 분모로 사용.

    Returns:
        {result, trace}
    """
    trace = CalcTrace(tool="engineering.db_convert", formula="")
    if mode not in _DB_MODES:
        raise InvalidInputError(f"mode는 {sorted(_DB_MODES)} 중 하나여야 합니다. 입력: {mode!r}")

    trace.input("mode", mode)
    trace.input("value", value)
    trace.input("reference", reference)

    v_d   = D(value)
    ref_d = D(reference)

    with mpmath.workdps(_MP_DPS):
        v_mp   = mpmath.mpf(str(v_d))
        ref_mp = mpmath.mpf(str(ref_d))
        ten    = mpmath.mpf("10")
        twenty = mpmath.mpf("20")

        if mode == "v_to_db":
            if v_mp <= 0 or ref_mp <= 0:
                raise InvalidInputError("v_to_db는 양수 비율이 필요합니다.")
            trace.formula = "dB = 20 log10(V/V_ref)"
            result = twenty * mpmath.log10(v_mp / ref_mp)

        elif mode == "p_to_db":
            if v_mp <= 0 or ref_mp <= 0:
                raise InvalidInputError("p_to_db는 양수 비율이 필요합니다.")
            trace.formula = "dB = 10 log10(P/P_ref)"
            result = ten * mpmath.log10(v_mp / ref_mp)

        elif mode == "db_to_v":
            trace.formula = "V/V_ref = 10^(dB/20)"
            result = mpmath.power(ten, v_mp / twenty)

        elif mode == "db_to_p":
            trace.formula = "P/P_ref = 10^(dB/10)"
            result = mpmath.power(ten, v_mp / ten)

        elif mode == "np_to_db":
            trace.formula = "dB = Np × (20 / ln(10))"
            result = v_mp * (twenty / mpmath.log(ten))

        elif mode == "db_to_np":
            trace.formula = "Np = dB × (ln(10) / 20)"
            result = v_mp * (mpmath.log(ten) / twenty)

        elif mode == "w_to_dbm":
            if v_mp <= 0:
                raise InvalidInputError("w_to_dbm은 양수 전력이 필요합니다.")
            trace.formula = "dBm = 10 log10(P_W / 1 mW)"
            result = ten * mpmath.log10(v_mp / mpmath.mpf("0.001"))

        else:  # dbm_to_w
            trace.formula = "P_W = 10^(dBm/10) × 1 mW"
            result = mpmath.power(ten, v_mp / ten) * mpmath.mpf("0.001")

        result_dec = mpmath_to_decimal(result, digits=_OUT_DIG)

    trace.step("result", str(result_dec))
    trace.output(str(result_dec))

    return {"result": str(result_dec), "trace": trace.to_dict()}


_COLOR_DIGITS: dict[str, int] = {
    "black":   0,
    "brown":   1,
    "red":     2,
    "orange":  3,
    "yellow":  4,
    "green":   5,
    "blue":    6,
    "violet":  7,
    "gray":    8,
    "white":   9,
}


_COLOR_MULTIPLIER: dict[str, Decimal] = {
    "black":   Decimal("1"),
    "brown":   Decimal("10"),
    "red":     Decimal("100"),
    "orange":  Decimal("1000"),
    "yellow":  Decimal("10000"),
    "green":   Decimal("100000"),
    "blue":    Decimal("1000000"),
    "violet":  Decimal("10000000"),
    "gray":    Decimal("100000000"),
    "white":   Decimal("1000000000"),
    "gold":    Decimal("0.1"),
    "silver":  Decimal("0.01"),
}


_COLOR_TOLERANCE: dict[str, Decimal] = {
    "brown":   Decimal("1"),
    "red":     Decimal("2"),
    "green":   Decimal("0.5"),
    "blue":    Decimal("0.25"),
    "violet":  Decimal("0.1"),
    "gray":    Decimal("0.05"),
    "gold":    Decimal("5"),
    "silver":  Decimal("10"),
}


@REGISTRY.tool(
    namespace="engineering",
    name="resistor_color_code",
    description=(
        "저항기 4밴드 또는 5밴드 컬러코드 해독. "
        "4밴드: [digit1, digit2, multiplier, tolerance], "
        "5밴드: [digit1, digit2, digit3, multiplier, tolerance]."
    ),
    version="1.0.0",
)
def resistor_color_code(bands: list[str]) -> dict[str, Any]:
    """Decode a 4-band or 5-band resistor color code."""
    trace = CalcTrace(
        tool="engineering.resistor_color_code",
        formula="R = (digits × 10^multiplier_index) ± tolerance%",
    )
    trace.input("bands", bands)

    if len(bands) not in (4, 5):
        raise InvalidInputError("bands는 4개 또는 5개여야 합니다.")
    bands_lower = [b.lower().strip() for b in bands]

    digit_count = 2 if len(bands_lower) == 4 else 3
    digit_bands = bands_lower[:digit_count]
    multiplier_band = bands_lower[digit_count]
    tolerance_band  = bands_lower[digit_count + 1]

    digits = 0
    for i, band in enumerate(digit_bands):
        if band not in _COLOR_DIGITS:
            raise InvalidInputError(f"자릿수 밴드 {i} 색상이 유효하지 않습니다: {band!r}")
        digits = digits * 10 + _COLOR_DIGITS[band]

    if multiplier_band not in _COLOR_MULTIPLIER:
        raise InvalidInputError(f"승수 밴드 색상이 유효하지 않습니다: {multiplier_band!r}")
    if tolerance_band not in _COLOR_TOLERANCE:
        raise InvalidInputError(
            f"허용오차 밴드 색상이 유효하지 않습니다: {tolerance_band!r}"
        )

    multiplier = _COLOR_MULTIPLIER[multiplier_band]
    tolerance  = _COLOR_TOLERANCE[tolerance_band]
    resistance = mul(Decimal(digits), multiplier)

    trace.step("digits",     str(digits))
    trace.step("multiplier", str(multiplier))
    trace.step("tolerance",  str(tolerance))
    trace.step("resistance", str(resistance))
    trace.output({
        "resistance_ohm": str(resistance),
        "tolerance_pct":  str(tolerance),
    })

    return {
        "resistance_ohm": str(resistance),
        "tolerance_pct":  str(tolerance),
        "trace":          trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="engineering",
    name="opamp_gain",
    description=(
        "Op-amp 기본 이득. configuration='inverting' (-Rf/Rin) "
        "또는 'non_inverting' (1 + Rf/Rin)."
    ),
    version="1.0.0",
)
def opamp_gain(
    feedback_resistance: str,
    input_resistance:    str,
    configuration:       str = "inverting",
) -> dict[str, Any]:
    """Compute ideal op-amp closed-loop voltage gain."""
    trace = CalcTrace(tool="engineering.opamp_gain", formula="")
    if configuration not in ("inverting", "non_inverting"):
        raise InvalidInputError(
            "configuration은 'inverting' 또는 'non_inverting'이어야 합니다."
        )
    rf_d = D(feedback_resistance)
    rin_d = D(input_resistance)
    if rf_d <= _ZERO or rin_d <= _ZERO:
        raise InvalidInputError("두 저항 모두 0 초과여야 합니다.")

    trace.input("feedback_resistance", feedback_resistance)
    trace.input("input_resistance",    input_resistance)
    trace.input("configuration",       configuration)

    if configuration == "inverting":
        trace.formula = "A = -Rf / Rin"
        gain = -div(rf_d, rin_d)
    else:
        trace.formula = "A = 1 + Rf / Rin"
        gain = _ONE + div(rf_d, rin_d)

    trace.step("gain", str(gain))
    trace.output(str(gain))

    return {"gain": str(gain), "trace": trace.to_dict()}
