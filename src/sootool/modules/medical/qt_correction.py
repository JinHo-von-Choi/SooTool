"""QT interval correction formulas: Bazett, Fridericia, Framingham, Hodges.

내부 자료형 (ADR-008):
- 입력 QT, RR (초 또는 밀리초) 는 Decimal 문자열.
- 비정수 지수(0.5, 1/3)는 mpmath 경유, 경계에서 Decimal 문자열로 복귀.
- Hodges 공식의 HR(심박수) 계산에서는 HR = 60 / RR (bpm).

출처:
- Bazett HC. Heart 1920;7:353.
- Fridericia LS. Acta Med Scand 1920;53:469.
- Sagie A et al. Framingham QTc. Am J Cardiol 1992;70:797.
- Hodges M. J Cardiovasc Electrophysiol 1983.

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import threading
from decimal import Decimal

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.cast import mpmath_to_decimal
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_MPDPS = 40


class QtcResult(TracedResult):
    qtc:  str
    unit: str


class QtcHodgesResult(QtcResult):
    hr_bpm: str
_MP_LOCK = threading.Lock()


def _parse_positive(value: str, name: str) -> Decimal:
    try:
        v = D(value)
    except Exception as exc:
        raise InvalidInputError(f"{name}은(는) Decimal 문자열이어야 합니다: {value!r}") from exc
    if v <= D("0"):
        raise DomainConstraintError(f"{name}은(는) 양수여야 합니다: {value}")
    return v


def _to_seconds(qt: Decimal, rr: Decimal, unit: str) -> tuple[Decimal, Decimal]:
    if unit == "s":
        return qt, rr
    if unit == "ms":
        return qt / D("1000"), rr / D("1000")
    raise InvalidInputError(f"unit는 'ms'|'s' 여야 합니다: {unit!r}")


@REGISTRY.tool(
    namespace="medical",
    name="qtc_bazett",
    description=(
        "Bazett 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / sqrt(RR). "
        "qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 결과 단위도 같다. "
        "내부는 mpmath 40자리로 계산해 유효숫자 20자리 문자열로 돌려준다(반올림 소수 자릿수 고정 없음). "
        "빠른 심박(RR 짧음)에서는 과대 보정되므로 그 구간엔 Fridericia를 고려한다."
    ),
    version="1.0.0",
)
def qtc_bazett(qt: str, rr: str, unit: str = "ms") -> QtcResult:
    trace = CalcTrace(tool="medical.qtc_bazett", formula="QTc = QT / sqrt(RR)")
    qt_d = _parse_positive(qt, "qt")
    rr_d = _parse_positive(rr, "rr")
    qt_s, rr_s = _to_seconds(qt_d, rr_d, unit)

    trace.input("qt", qt)
    trace.input("rr", rr)
    trace.input("unit", unit)

    with _MP_LOCK, mpmath.workdps(_MPDPS):
        qtc_s_mpf = mpmath.mpf(str(qt_s)) / mpmath.sqrt(mpmath.mpf(str(rr_s)))
        qtc_s_dec = mpmath_to_decimal(qtc_s_mpf, digits=20)
    qtc_out = qtc_s_dec if unit == "s" else qtc_s_dec * D("1000")
    qtc_str = str(qtc_out)

    trace.step("qtc", qtc_str)
    trace.output({"qtc": qtc_str, "unit": unit})

    return {"qtc": qtc_str, "unit": unit, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="medical",
    name="qtc_fridericia",
    description=(
        "Fridericia 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / RR^(1/3). "
        "qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 결과 단위도 같다. "
        "내부는 mpmath 40자리로 계산해 유효숫자 20자리 문자열로 돌려준다. "
        "RR을 심박수(bpm)로 넣으면 안 된다. RR은 R-R 간격 시간이다."
    ),
    version="1.0.0",
)
def qtc_fridericia(qt: str, rr: str, unit: str = "ms") -> QtcResult:
    trace = CalcTrace(tool="medical.qtc_fridericia", formula="QTc = QT / RR^(1/3)")
    qt_d = _parse_positive(qt, "qt")
    rr_d = _parse_positive(rr, "rr")
    qt_s, rr_s = _to_seconds(qt_d, rr_d, unit)

    trace.input("qt", qt)
    trace.input("rr", rr)
    trace.input("unit", unit)

    with _MP_LOCK, mpmath.workdps(_MPDPS):
        rr_cbrt   = mpmath.cbrt(mpmath.mpf(str(rr_s)))
        qtc_s_mpf = mpmath.mpf(str(qt_s)) / rr_cbrt
        qtc_s_dec = mpmath_to_decimal(qtc_s_mpf, digits=20)
    qtc_out = qtc_s_dec if unit == "s" else qtc_s_dec * D("1000")
    qtc_str = str(qtc_out)

    trace.step("qtc", qtc_str)
    trace.output({"qtc": qtc_str, "unit": unit})

    return {"qtc": qtc_str, "unit": unit, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="medical",
    name="qtc_framingham",
    description=(
        "Framingham 선형 공식으로 QT 간격을 보정한다. QTc = QT + 0.154 * (1 - RR_초). "
        "qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, "
        "내부에서 초로 환산해 계산한 뒤 입력 단위로 돌려준다. Decimal 정확 연산이며 반올림하지 않는다. "
        "RR을 심박수(bpm)로 넣으면 안 된다."
    ),
    version="1.0.0",
)
def qtc_framingham(qt: str, rr: str, unit: str = "ms") -> QtcResult:
    trace = CalcTrace(
        tool="medical.qtc_framingham",
        formula="QTc_s = QT_s + 0.154 * (1 - RR_s)",
    )
    qt_d = _parse_positive(qt, "qt")
    rr_d = _parse_positive(rr, "rr")
    qt_s, rr_s = _to_seconds(qt_d, rr_d, unit)

    trace.input("qt", qt)
    trace.input("rr", rr)
    trace.input("unit", unit)

    qtc_s = qt_s + D("0.154") * (D("1") - rr_s)
    qtc_out = qtc_s if unit == "s" else qtc_s * D("1000")
    qtc_str = str(qtc_out)

    trace.step("qtc", qtc_str)
    trace.output({"qtc": qtc_str, "unit": unit})

    return {"qtc": qtc_str, "unit": unit, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="medical",
    name="qtc_hodges",
    description=(
        "Hodges 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc_ms = QT_ms + 1.75 * (HR - 60), HR = 60 / RR_초. "
        "qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, "
        "결과는 입력 단위로 돌려주며 계산에 쓴 심박수 hr_bpm도 함께 반환한다. Decimal 연산이며 반올림하지 않는다. "
        "RR 대신 심박수를 넣으면 안 된다."
    ),
    version="1.0.0",
)
def qtc_hodges(qt: str, rr: str, unit: str = "ms") -> QtcHodgesResult:
    trace = CalcTrace(
        tool="medical.qtc_hodges",
        formula="QTc_ms = QT_ms + 1.75 * (HR - 60), HR = 60 / RR_s",
    )
    qt_d = _parse_positive(qt, "qt")
    rr_d = _parse_positive(rr, "rr")
    qt_s, rr_s = _to_seconds(qt_d, rr_d, unit)

    trace.input("qt", qt)
    trace.input("rr", rr)
    trace.input("unit", unit)

    hr    = D("60") / rr_s
    qt_ms = qt_s * D("1000")
    qtc_ms = qt_ms + D("1.75") * (hr - D("60"))
    qtc_out = qtc_ms if unit == "ms" else qtc_ms / D("1000")
    qtc_str = str(qtc_out)

    trace.step("hr_bpm", str(hr))
    trace.step("qtc",    qtc_str)
    trace.output({"qtc": qtc_str, "unit": unit, "hr_bpm": str(hr)})

    return {"qtc": qtc_str, "unit": unit, "hr_bpm": str(hr), "trace": trace.to_dict()}
