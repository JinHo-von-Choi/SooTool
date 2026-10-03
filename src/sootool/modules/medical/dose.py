"""Weight-based drug dose calculator.

Author: 최진호
Date: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply


class MedicalDoseWeightBasedResult(TracedResult):
    dose:   str
    unit:   str
    capped: bool


@REGISTRY.tool(
    namespace="medical",
    name="dose_weight_based",
    description=(
        "체중 기반 약물 용량을 계산한다. dose = weight_kg * dose_per_kg, "
        "max_dose를 주면 초과 시 max_dose로 제한하고 capped=true를 돌려준다. "
        "입력은 kg과 kg당 용량의 Decimal 문자열(0 이상), 결과는 소수 4자리 HALF_EVEN 반올림 후 "
        "후행 0을 제거한 고정소수점 문자열. unit은 표시용 문자열이며 환산하지 않는다. "
        "단위가 다른 dose_per_kg와 max_dose를 섞으면 안 된다."
    ),
    version="1.0.0",
)
def medical_dose_weight_based(
    weight_kg:    str,
    dose_per_kg:  str,
    max_dose:     str | None = None,
    unit:         str        = "mg",
) -> MedicalDoseWeightBasedResult:
    """Calculate weight-based dose with optional ceiling.

    Args:
        weight_kg:   체중 (킬로그램, Decimal string)
        dose_per_kg: kg당 용량 (Decimal string)
        max_dose:    최대 허용 용량 (Decimal string, optional)
        unit:        용량 단위 (기본 "mg")

    Returns:
        {dose: str, unit: str, capped: bool, trace}
    """
    trace = CalcTrace(
        tool="medical.dose_weight_based",
        formula="dose = min(weight_kg * dose_per_kg, max_dose)",
    )

    w   = D(weight_kg)
    dpk = D(dose_per_kg)

    if w < Decimal("0"):
        raise InvalidInputError("weight_kg은 0 이상이어야 합니다.")
    if dpk < Decimal("0"):
        raise InvalidInputError("dose_per_kg은 0 이상이어야 합니다.")

    trace.input("weight_kg",   weight_kg)
    trace.input("dose_per_kg", dose_per_kg)
    trace.input("max_dose",    max_dose)
    trace.input("unit",        unit)

    raw_dose = w * dpk
    trace.step("raw_dose", str(raw_dose))

    capped = False
    dose   = raw_dose

    if max_dose is not None:
        max_d = D(max_dose)
        if max_d < Decimal("0"):
            raise InvalidInputError("max_dose는 0 이상이어야 합니다.")
        if raw_dose > max_d:
            dose   = max_d
            capped = True
            trace.step("cap_applied", str(max_d))

    dose_rounded = round_apply(dose, 4, RoundingPolicy.HALF_EVEN)
    # Strip trailing zeros while avoiding scientific notation
    normalized = dose_rounded.normalize()
    # Convert to fixed-point string (avoids "3.5E+2" etc.)
    dose_str = format(normalized, "f")

    trace.step("capped", str(capped))
    trace.output(dose_str)

    return {
        "dose":   dose_str,
        "unit":   unit,
        "capped": capped,
        "trace":  trace.to_dict(),
    }
