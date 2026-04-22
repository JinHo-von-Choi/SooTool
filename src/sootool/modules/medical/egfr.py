"""eGFR calculator using CKD-EPI 2021 equation.

Author: 최진호
Date: 2026-04-22

Source:
  Inker LA, et al. New Creatinine- and Cystatin C-Based Equations to Estimate GFR
  without Race. N Engl J Med. 2021;385(19):1737-1749.
  CKD-EPI 2021 (race-free creatinine equation).

CKD staging per KDIGO 2012 Clinical Practice Guideline:
  G1: eGFR >= 90
  G2: 60 <= eGFR < 90
  G3a: 45 <= eGFR < 60
  G3b: 30 <= eGFR < 45
  G4: 15 <= eGFR < 30
  G5: eGFR < 15
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import mpmath

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.rounding import RoundingPolicy, apply as round_apply

# CKD-EPI 2021 race-free creatinine equation coefficients
# eGFR = 142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200)
#         * 0.9938^age * [1.012 if female]
_COEFF_KAPPA_FEMALE = 0.7
_COEFF_KAPPA_MALE   = 0.9
_COEFF_ALPHA_FEMALE = -0.241
_COEFF_ALPHA_MALE   = -0.302
_COEFF_BASE         = 142.0
_COEFF_MAX_EXP      = -1.200
_COEFF_AGE_BASE     = 0.9938
_COEFF_SEX_FEMALE   = 1.012


def _ckd_epi_2021(creatinine: float, age: int, sex: str) -> float:
    """Compute eGFR using CKD-EPI 2021 (race-free) creatinine equation."""
    if sex == "female":
        kappa = _COEFF_KAPPA_FEMALE
        alpha = _COEFF_ALPHA_FEMALE
    else:
        kappa = _COEFF_KAPPA_MALE
        alpha = _COEFF_ALPHA_MALE

    ratio = creatinine / kappa

    min_ratio = min(ratio, 1.0)
    max_ratio = max(ratio, 1.0)

    egfr = (
        _COEFF_BASE
        * (min_ratio ** alpha)
        * (max_ratio ** _COEFF_MAX_EXP)
        * (_COEFF_AGE_BASE ** age)
    )

    if sex == "female":
        egfr *= _COEFF_SEX_FEMALE

    return egfr


def _ckd_stage(egfr: Decimal) -> str:
    """Map eGFR to KDIGO 2012 CKD stage."""
    if egfr >= D("90"):
        return "G1"
    if egfr >= D("60"):
        return "G2"
    if egfr >= D("45"):
        return "G3a"
    if egfr >= D("30"):
        return "G3b"
    if egfr >= D("15"):
        return "G4"
    return "G5"


@REGISTRY.tool(
    namespace="medical",
    name="egfr",
    description=(
        "eGFR 계산 (CKD-EPI 2021, race-free). "
        "KDIGO 2012 기준 CKD stage 반환. "
        "단위: mL/min/1.73m²."
    ),
    version="1.0.0",
)
def medical_egfr(
    creatinine_mg_dl: str,
    age:              int,
    sex:              str,
    race:             str = "non_black",
) -> dict[str, Any]:
    """Calculate eGFR and CKD stage.

    Args:
        creatinine_mg_dl: 혈청 크레아티닌 (mg/dL, Decimal string)
        age:              나이 (정수, 년)
        sex:              성별 ("male" | "female")
        race:             인종 (CKD-EPI 2021 race-free 방정식이므로 무시됨)

    Returns:
        {egfr: str (소수점 1자리), stage: str, trace}
    """
    trace = CalcTrace(
        tool="medical.egfr",
        formula=(
            "CKD-EPI 2021 (race-free): "
            "142 * min(Scr/kappa,1)^alpha * max(Scr/kappa,1)^-1.2 "
            "* 0.9938^age [* 1.012 if female]"
        ),
    )

    valid_sex = {"male", "female"}
    if sex not in valid_sex:
        raise InvalidInputError(f"sex는 {valid_sex} 중 하나여야 합니다.")

    cr = D(creatinine_mg_dl)
    if cr <= Decimal("0"):
        raise InvalidInputError("creatinine_mg_dl은 0보다 커야 합니다.")
    if age <= 0:
        raise InvalidInputError("age는 0보다 커야 합니다.")

    trace.input("creatinine_mg_dl", creatinine_mg_dl)
    trace.input("age",              age)
    trace.input("sex",              sex)
    trace.input("race",             f"{race} (CKD-EPI 2021에서는 race 계수 미사용)")

    egfr_f   = _ckd_epi_2021(float(cr), age, sex)
    egfr_raw = D(str(egfr_f), allow_float=True)
    egfr     = round_apply(egfr_raw, 1, RoundingPolicy.HALF_EVEN)
    stage    = _ckd_stage(egfr)

    trace.step("egfr_raw", str(egfr_raw))
    trace.step("stage",    stage)
    trace.output(str(egfr))

    return {
        "egfr":  str(egfr),
        "stage": stage,
        "trace": trace.to_dict(),
    }
