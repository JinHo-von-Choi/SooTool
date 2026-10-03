"""Body measurement calculators: BMI and BSA.

Author: 최진호
Date: 2026-04-22

Sources:
  - WHO BMI classification (https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight)
  - Du Bois D, Du Bois EF. A formula to estimate the approximate surface area
    if height and weight be known. Arch Intern Med. 1916;17:863-871.
  - Mosteller RD. Simplified calculation of body-surface area.
    N Engl J Med. 1987;317(17):1098.
"""
from __future__ import annotations

from decimal import Decimal

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply

# WHO BMI category cutoffs (lower-bound inclusive)
_BMI_CATEGORIES: list[tuple[Decimal, str]] = [
    (D("40"),   "obese_3"),
    (D("35"),   "obese_2"),
    (D("30"),   "obese_1"),
    (D("25"),   "overweight"),
    (D("18.5"), "normal"),
    (D("0"),    "underweight"),
]


class MedicalBmiResult(TracedResult):
    bmi:      str
    category: str


class MedicalBsaResult(TracedResult):
    bsa_m2: str


def _bmi_category(bmi: Decimal) -> str:
    for threshold, label in _BMI_CATEGORIES:
        if bmi >= threshold:
            return label
    return "underweight"


@REGISTRY.tool(
    namespace="medical",
    name="bmi",
    description=(
        "체질량지수(BMI)를 계산하고 WHO 기준으로 분류한다. "
        "BMI = weight_kg / height_m^2, 입력은 미터와 킬로그램의 Decimal 문자열, "
        "결과는 소수 2자리 HALF_EVEN 반올림. 분류는 underweight(<18.5), normal(<25), "
        "overweight(<30), obese_1(<35), obese_2(<40), obese_3(40 이상)이며 반올림한 값으로 판정한다. "
        "신장을 cm 단위로 넣으면 결과가 100배 이상 어긋난다."
    ),
    version="1.0.0",
)
def medical_bmi(
    height_m:  str,
    weight_kg: str,
) -> MedicalBmiResult:
    """Calculate BMI and WHO classification.

    Args:
        height_m:  신장 (미터, Decimal string)
        weight_kg: 체중 (킬로그램, Decimal string)

    Returns:
        {bmi: str (소수점 2자리, HALF_EVEN), category: str, trace}
    """
    trace = CalcTrace(
        tool="medical.bmi",
        formula="bmi = weight_kg / height_m^2",
    )

    h = D(height_m)
    w = D(weight_kg)

    if h <= Decimal("0"):
        raise InvalidInputError("height_m은 0보다 커야 합니다.")
    if w <= Decimal("0"):
        raise InvalidInputError("weight_kg은 0보다 커야 합니다.")

    trace.input("height_m",  height_m)
    trace.input("weight_kg", weight_kg)

    bmi_raw  = w / (h * h)
    bmi      = round_apply(bmi_raw, 2, RoundingPolicy.HALF_EVEN)
    category = _bmi_category(bmi)

    trace.step("bmi_raw",  str(bmi_raw))
    trace.step("category", category)
    trace.output(str(bmi))

    return {
        "bmi":      str(bmi),
        "category": category,
        "trace":    trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="medical",
    name="bsa",
    description=(
        "체표면적(BSA)을 m² 단위로 계산한다. 입력은 신장 cm, 체중 kg의 Decimal 문자열, "
        "결과는 소수 4자리 HALF_EVEN 반올림. method=dubois(기본)는 0.007184 * h^0.725 * w^0.425, "
        "method=mosteller는 sqrt(h*w/3600). 항암제 용량 산정 등에 쓰며, "
        "신장을 m 단위로 넣으면 결과가 크게 어긋난다. 비정수 지수는 float64로 계산한다."
    ),
    version="1.0.0",
)
def medical_bsa(
    height_cm: str,
    weight_kg: str,
    method:    str = "dubois",
) -> MedicalBsaResult:
    """Calculate Body Surface Area.

    Args:
        height_cm: 신장 (센티미터, Decimal string)
        weight_kg: 체중 (킬로그램, Decimal string)
        method:    계산법 ("dubois" | "mosteller")

    Returns:
        {bsa_m2: str (소수점 4자리), trace}
    """
    trace = CalcTrace(
        tool="medical.bsa",
        formula=(
            "dubois: 0.007184 * h^0.725 * w^0.425; "
            "mosteller: sqrt(h*w/3600)"
        ),
    )

    valid_methods = {"dubois", "mosteller"}
    if method not in valid_methods:
        raise InvalidInputError(f"method는 {valid_methods} 중 하나여야 합니다.")

    h = D(height_cm)
    w = D(weight_kg)

    if h <= Decimal("0"):
        raise InvalidInputError("height_cm은 0보다 커야 합니다.")
    if w <= Decimal("0"):
        raise InvalidInputError("weight_kg은 0보다 커야 합니다.")

    trace.input("height_cm", height_cm)
    trace.input("weight_kg", weight_kg)
    trace.input("method",    method)

    if method == "dubois":
        # Use mpmath for non-integer exponents to ensure precision
        h_f = float(h)
        w_f = float(w)
        bsa_f   = 0.007184 * (h_f ** 0.725) * (w_f ** 0.425)
        bsa_raw = D(str(bsa_f), allow_float=True)
        trace.step("formula_used", "0.007184 * h^0.725 * w^0.425")
    else:
        # Mosteller: sqrt(h*w/3600)
        hw_ratio = h * w / D("3600")
        bsa_f    = float(mpmath.sqrt(float(hw_ratio)))
        bsa_raw  = D(str(bsa_f), allow_float=True)
        trace.step("formula_used", "sqrt(h*w/3600)")

    bsa = round_apply(bsa_raw, 4, RoundingPolicy.HALF_EVEN)

    trace.step("bsa_raw", str(bsa_raw))
    trace.output(str(bsa))

    return {
        "bsa_m2": str(bsa),
        "trace":  trace.to_dict(),
    }
