"""Extended unit conversions: energy, pressure, data size, small-time units.

내부 자료형 (ADR-008):
- 에너지/압력/작은 시간 단위: pint 기반 (Decimal non-int type) → Decimal 문자열.
- 데이터 크기: Decimal 정수 연산 (SI: 10^3 단계, IEC: 2^10 단계).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.units import _UREG


class MagnitudeUnitResult(TracedResult):
    magnitude: str
    unit:      str


class EnergyConvertResult(MagnitudeUnitResult):
    pass


class PressureConvertResult(MagnitudeUnitResult):
    pass


class DataSizeConvertResult(MagnitudeUnitResult):
    pass


class TimeSmallConvertResult(MagnitudeUnitResult):
    pass


# ---------------------------------------------------------------------------
# Energy conversion factors (to Joule)
# ---------------------------------------------------------------------------
_ENERGY_TO_J: dict[str, Decimal] = {
    "J":    D("1"),
    "kJ":   D("1000"),
    "cal":  D("4.184"),            # thermochemical calorie
    "kcal": D("4184"),
    "eV":   D("1.602176634E-19"),
    "BTU":  D("1055.05585262"),
    "Wh":   D("3600"),
    "kWh":  D("3600000"),
}


@REGISTRY.tool(
    namespace="units",
    name="energy_convert",
    description=(
        "에너지 단위를 J 기준 Decimal 계수로 변환한다. 지원 단위는 J, kJ, cal, kcal, eV, BTU, Wh, kWh 이며 "
        "대소문자를 구분하고 magnitude 는 Decimal 문자열이다. cal 은 열화학 칼로리(4.184 J)이고 "
        "결과는 magnitude 와 unit 이다. 목록에 없는 단위(MJ, 국제표 칼로리 등)는 오류이다."
    ),
    version="1.0.0",
)
def energy_convert(
    magnitude: str,
    from_unit: str,
    to_unit:   str,
) -> EnergyConvertResult:
    trace = CalcTrace(
        tool="units.energy_convert",
        formula="result = magnitude * factor(from→J) / factor(to→J)",
    )
    if from_unit not in _ENERGY_TO_J:
        raise InvalidInputError(f"지원하지 않는 from_unit: {from_unit!r}. 지원: {sorted(_ENERGY_TO_J)}")
    if to_unit not in _ENERGY_TO_J:
        raise InvalidInputError(f"지원하지 않는 to_unit: {to_unit!r}. 지원: {sorted(_ENERGY_TO_J)}")

    try:
        m = D(magnitude)
    except Exception as exc:
        raise InvalidInputError(f"magnitude는 Decimal 문자열이어야 합니다: {magnitude!r}") from exc

    trace.input("magnitude", magnitude)
    trace.input("from_unit", from_unit)
    trace.input("to_unit",   to_unit)

    j_value = m * _ENERGY_TO_J[from_unit]
    out     = j_value / _ENERGY_TO_J[to_unit]
    out_str = str(out)
    trace.step("joules",     str(j_value))
    trace.step("result",     out_str)
    trace.output({"magnitude": out_str, "unit": to_unit})

    return {"magnitude": out_str, "unit": to_unit, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Pressure conversion factors (to Pascal)
# ---------------------------------------------------------------------------
_PRESSURE_TO_PA: dict[str, Decimal] = {
    "Pa":   D("1"),
    "kPa":  D("1000"),
    "MPa":  D("1000000"),
    "atm":  D("101325"),
    "bar":  D("100000"),
    "mbar": D("100"),
    "psi":  D("6894.757293168361"),
    "mmHg": D("133.322387415"),
    "torr": D("133.322368421"),
}


@REGISTRY.tool(
    namespace="units",
    name="pressure_convert",
    description=(
        "압력 단위를 Pa 기준 Decimal 계수로 변환한다. 지원 단위는 Pa, kPa, MPa, atm, bar, mbar, psi, mmHg, torr 이며 "
        "대소문자를 구분하고 magnitude 는 Decimal 문자열이다. 단순 배율 변환이라 게이지압과 절대압의 "
        "차이는 반영하지 않는다. 결과는 magnitude 와 unit 이다."
    ),
    version="1.0.0",
)
def pressure_convert(
    magnitude: str,
    from_unit: str,
    to_unit:   str,
) -> PressureConvertResult:
    trace = CalcTrace(
        tool="units.pressure_convert",
        formula="result = magnitude * factor(from→Pa) / factor(to→Pa)",
    )
    if from_unit not in _PRESSURE_TO_PA:
        raise InvalidInputError(f"지원하지 않는 from_unit: {from_unit!r}. 지원: {sorted(_PRESSURE_TO_PA)}")
    if to_unit not in _PRESSURE_TO_PA:
        raise InvalidInputError(f"지원하지 않는 to_unit: {to_unit!r}. 지원: {sorted(_PRESSURE_TO_PA)}")

    try:
        m = D(magnitude)
    except Exception as exc:
        raise InvalidInputError(f"magnitude는 Decimal 문자열이어야 합니다: {magnitude!r}") from exc

    trace.input("magnitude", magnitude)
    trace.input("from_unit", from_unit)
    trace.input("to_unit",   to_unit)

    pa = m * _PRESSURE_TO_PA[from_unit]
    out = pa / _PRESSURE_TO_PA[to_unit]
    out_str = str(out)
    trace.step("pascals", str(pa))
    trace.step("result", out_str)
    trace.output({"magnitude": out_str, "unit": to_unit})

    return {"magnitude": out_str, "unit": to_unit, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Data size conversion (SI vs IEC)
# ---------------------------------------------------------------------------
_SI_DATA_TO_BYTES: dict[str, Decimal] = {
    "b":  D("1") / D("8"),   # bit
    "B":  D("1"),
    "kB": D("1000"),
    "MB": D("1000000"),
    "GB": D("10")**9,
    "TB": D("10")**12,
    "PB": D("10")**15,
}

_IEC_DATA_TO_BYTES: dict[str, Decimal] = {
    "B":   D("1"),
    "KiB": D("1024"),
    "MiB": D("1024")**2,
    "GiB": D("1024")**3,
    "TiB": D("1024")**4,
    "PiB": D("1024")**5,
}


@REGISTRY.tool(
    namespace="units",
    name="data_size_convert",
    description=(
        "데이터 크기 단위를 바이트 기준으로 변환한다. mode 'si'(b, B, kB, MB, GB, TB, PB, 1000 배, b 는 비트, 기본)와 "
        "'iec'(B, KiB, MiB, GiB, TiB, PiB, 1024 배)는 각 표의 단위만, 'mixed' 는 두 표를 함께 허용한다. "
        "magnitude 는 0 이상 Decimal 문자열이고 단위는 대소문자를 구분한다(KB 는 오류, kB 만 유효)."
    ),
    version="1.0.0",
)
def data_size_convert(
    magnitude: str,
    from_unit: str,
    to_unit:   str,
    mode:      str = "si",
) -> DataSizeConvertResult:
    trace = CalcTrace(
        tool="units.data_size_convert",
        formula="result_bytes = magnitude * factor(from→B); result = result_bytes / factor(to→B)",
    )
    if mode == "si":
        table = _SI_DATA_TO_BYTES
    elif mode == "iec":
        table = _IEC_DATA_TO_BYTES
    elif mode == "mixed":
        # Accept either table
        table = {**_SI_DATA_TO_BYTES, **_IEC_DATA_TO_BYTES}
    else:
        raise InvalidInputError(f"mode는 'si'|'iec'|'mixed' 여야 합니다: {mode!r}")

    if from_unit not in table:
        raise InvalidInputError(
            f"지원하지 않는 from_unit: {from_unit!r} (mode={mode}). 지원: {sorted(table)}"
        )
    if to_unit not in table:
        raise InvalidInputError(
            f"지원하지 않는 to_unit: {to_unit!r} (mode={mode}). 지원: {sorted(table)}"
        )

    try:
        m = D(magnitude)
    except Exception as exc:
        raise InvalidInputError(f"magnitude는 Decimal 문자열이어야 합니다: {magnitude!r}") from exc

    if m < D("0"):
        raise DomainConstraintError("데이터 크기는 음수일 수 없습니다.")

    trace.input("magnitude", magnitude)
    trace.input("from_unit", from_unit)
    trace.input("to_unit",   to_unit)
    trace.input("mode",      mode)

    bytes_val = m * table[from_unit]
    out = bytes_val / table[to_unit]
    out_str = str(out)
    trace.step("bytes", str(bytes_val))
    trace.step("result", out_str)
    trace.output({"magnitude": out_str, "unit": to_unit})

    return {"magnitude": out_str, "unit": to_unit, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# Small-time unit conversion via pint
# ---------------------------------------------------------------------------
_TIME_UNITS = frozenset(["s", "ms", "us", "ns", "ps", "min", "hour", "day"])
# pint understands all of these.


@REGISTRY.tool(
    namespace="units",
    name="time_small_convert",
    description=(
        "짧은 시간 단위 s, ms, us, ns, ps, min, hour, day 사이를 pint 로 변환한다. magnitude 는 Decimal 문자열이고 "
        "단위는 대소문자를 구분하며 1 day 는 86400 s 이다. 월과 연은 길이가 일정하지 않아 지원하지 않으므로 "
        "날짜 간격에는 datetime.diff 를 쓴다."
    ),
    version="1.0.0",
)
def time_small_convert(
    magnitude: str,
    from_unit: str,
    to_unit:   str,
) -> TimeSmallConvertResult:
    trace = CalcTrace(
        tool="units.time_small_convert",
        formula="quantity = magnitude [from]; result = quantity.to(to_unit)",
    )
    if from_unit not in _TIME_UNITS:
        raise InvalidInputError(f"지원하지 않는 from_unit: {from_unit!r}. 지원: {sorted(_TIME_UNITS)}")
    if to_unit not in _TIME_UNITS:
        raise InvalidInputError(f"지원하지 않는 to_unit: {to_unit!r}. 지원: {sorted(_TIME_UNITS)}")

    try:
        m = D(magnitude)
    except Exception as exc:
        raise InvalidInputError(f"magnitude는 Decimal 문자열이어야 합니다: {magnitude!r}") from exc

    trace.input("magnitude", magnitude)
    trace.input("from_unit", from_unit)
    trace.input("to_unit",   to_unit)

    try:
        q   = _UREG.Quantity(m, from_unit)
        out = q.to(to_unit)
    except Exception as exc:
        raise InvalidInputError(
            f"시간 단위 변환 실패: {from_unit!r} → {to_unit!r}: {exc}"
        ) from exc

    out_str = str(out.magnitude)
    trace.step("result", out_str)
    trace.output({"magnitude": out_str, "unit": to_unit})

    return {"magnitude": out_str, "unit": to_unit, "trace": trace.to_dict()}
