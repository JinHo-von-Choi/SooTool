"""Medical risk score calculators: CHA2DS2-VASc, HAS-BLED, Framingham 10-year CVD.

내부 자료형 (ADR-008):
- 점수 계산: 정수 합 (bool → int).
- Framingham 회귀: 내부 float64 (지수·로그), 결과 float64 → Decimal 문자열.

출처:
- Lip GYH et al. CHA2DS2-VASc (Chest 2010;137:263).
- Pisters R et al. HAS-BLED (Chest 2010;138:1093).
- D'Agostino RB et al. Framingham General CVD Risk (Circulation 2008;117:743).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import math
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _require_int(value: int, name: str, lo: int | None = None, hi: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInputError(f"{name}은(는) 정수여야 합니다: {value!r}")
    if lo is not None and value < lo:
        raise DomainConstraintError(f"{name}={value}은(는) {lo} 이상이어야 합니다.")
    if hi is not None and value > hi:
        raise DomainConstraintError(f"{name}={value}은(는) {hi} 이하여야 합니다.")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInputError(f"{name}은(는) bool이어야 합니다: {value!r}")
    return value


@REGISTRY.tool(
    namespace="medical",
    name="cha2ds2_vasc",
    description=(
        "CHA2DS2-VASc 점수: 심방세동 환자의 뇌졸중 위험도. "
        "C=울혈성심부전, H=고혈압, A2=75세이상(2점), D=당뇨, S2=뇌졸중/TIA(2점), "
        "V=혈관질환, A=65-74세, Sc=여성. 총 0-9점."
    ),
    version="1.0.0",
)
def cha2ds2_vasc(
    age:                  int,
    female:               bool,
    chf:                  bool = False,
    hypertension:         bool = False,
    diabetes:             bool = False,
    stroke_or_tia:        bool = False,
    vascular_disease:     bool = False,
) -> dict[str, Any]:
    """Compute CHA2DS2-VASc score."""
    trace = CalcTrace(
        tool="medical.cha2ds2_vasc",
        formula="CHF+HTN+2*(Age≥75)+DM+2*Stroke+Vasc+(Age 65-74)+Female",
    )
    a = _require_int(age, "age", lo=0, hi=130)
    f = _require_bool(female, "female")
    c = _require_bool(chf, "chf")
    h = _require_bool(hypertension, "hypertension")
    dm = _require_bool(diabetes, "diabetes")
    s = _require_bool(stroke_or_tia, "stroke_or_tia")
    v = _require_bool(vascular_disease, "vascular_disease")

    age_pts = 2 if a >= 75 else (1 if a >= 65 else 0)
    score = int(c) + int(h) + age_pts + int(dm) + 2 * int(s) + int(v) + int(f)

    trace.input("age", a)
    trace.input("female", f)
    trace.input("chf", c)
    trace.input("hypertension", h)
    trace.input("diabetes", dm)
    trace.input("stroke_or_tia", s)
    trace.input("vascular_disease", v)
    trace.step("age_points", age_pts)
    trace.step("score", score)
    trace.output({"score": score})

    return {
        "score":       score,
        "risk_level":  "low" if score == 0 else ("moderate" if score == 1 else "high"),
        "trace":       trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="medical",
    name="has_bled",
    description=(
        "HAS-BLED 점수: 항응고 치료 환자의 주요 출혈 위험도. "
        "H=고혈압, A=간/신장기능장애(각1), S=뇌졸중, B=출혈력, L=불안정 INR, "
        "E=노인(>65), D=약물/음주(각1). 총 0-9점."
    ),
    version="1.0.0",
)
def has_bled(
    hypertension:        bool,
    abnormal_renal:      bool,
    abnormal_liver:      bool,
    stroke:              bool,
    bleeding_history:    bool,
    labile_inr:          bool,
    elderly:             bool,
    drugs:               bool,
    alcohol:             bool,
) -> dict[str, Any]:
    """Compute HAS-BLED score."""
    trace = CalcTrace(
        tool="medical.has_bled",
        formula="H + (renal + liver) + S + B + L + E + (drugs + alcohol)",
    )
    flags = {
        "hypertension":     hypertension,
        "abnormal_renal":   abnormal_renal,
        "abnormal_liver":   abnormal_liver,
        "stroke":           stroke,
        "bleeding_history": bleeding_history,
        "labile_inr":       labile_inr,
        "elderly":          elderly,
        "drugs":            drugs,
        "alcohol":          alcohol,
    }
    for k, v in flags.items():
        _require_bool(v, k)
        trace.input(k, v)

    score = sum(int(v) for v in flags.values())
    trace.step("score", score)
    trace.output({"score": score})

    return {
        "score":      score,
        "risk_level": "low" if score <= 2 else "high",
        "trace":      trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# Framingham General 10-year CVD risk (D'Agostino 2008, simplified)
# ---------------------------------------------------------------------------
#
# Score = 1 - S0(t)^exp(βX - meanβX)
# Coefficients from Table 2 (D'Agostino 2008), general CVD 10-year model.

_FRAMINGHAM_COEF = {
    "male": {
        "ln_age":          3.06117,
        "ln_total_chol":   1.12370,
        "ln_hdl":         -0.93263,
        "ln_sbp_untreated": 1.93303,
        "ln_sbp_treated":   1.99881,
        "smoker":          0.65451,
        "diabetes":        0.57367,
        "S0":              0.88936,
        "mean_beta_x":    23.9802,
    },
    "female": {
        "ln_age":          2.32888,
        "ln_total_chol":   1.20904,
        "ln_hdl":         -0.70833,
        "ln_sbp_untreated": 2.76157,
        "ln_sbp_treated":   2.82263,
        "smoker":          0.52873,
        "diabetes":        0.69154,
        "S0":              0.95012,
        "mean_beta_x":    26.1931,
    },
}


@REGISTRY.tool(
    namespace="medical",
    name="framingham_cvd_10y",
    description=(
        "Framingham 일반 10년 심혈관질환 위험도 (D'Agostino 2008). "
        "sex=male|female, age(30-74), total_chol/hdl(mg/dL), sbp(mmHg), "
        "treated_htn, smoker, diabetes. 반환: 10년 발생 확률 (0-1)."
    ),
    version="1.0.0",
)
def framingham_cvd_10y(
    sex:             str,
    age:             int,
    total_chol:      str,
    hdl:             str,
    sbp:             str,
    treated_htn:     bool,
    smoker:          bool,
    diabetes:        bool,
) -> dict[str, Any]:
    """Compute 10-year general CVD risk (probability)."""
    trace = CalcTrace(
        tool="medical.framingham_cvd_10y",
        formula="Risk = 1 - S0^exp(Σ β_i X_i - mean β X)",
    )
    if sex not in ("male", "female"):
        raise InvalidInputError(f"sex는 'male'|'female' 여야 합니다: {sex!r}")
    _require_int(age, "age", lo=30, hi=74)
    _require_bool(treated_htn, "treated_htn")
    _require_bool(smoker, "smoker")
    _require_bool(diabetes, "diabetes")

    try:
        tc  = decimal_to_float64(D(total_chol))
        hd  = decimal_to_float64(D(hdl))
        sbp_f = decimal_to_float64(D(sbp))
    except Exception as exc:
        raise InvalidInputError("total_chol, hdl, sbp는 Decimal 문자열이어야 합니다.") from exc

    for n, v in (("total_chol", tc), ("hdl", hd), ("sbp", sbp_f)):
        if v <= 0.0:
            raise DomainConstraintError(f"{n}은(는) 양수여야 합니다.")

    c = _FRAMINGHAM_COEF[sex]

    ln_age   = math.log(float(age))
    ln_tc    = math.log(tc)
    ln_hdl   = math.log(hd)
    ln_sbp   = math.log(sbp_f)

    beta_sbp = c["ln_sbp_treated"] if treated_htn else c["ln_sbp_untreated"]
    beta_x = (
        c["ln_age"] * ln_age
        + c["ln_total_chol"] * ln_tc
        + c["ln_hdl"] * ln_hdl
        + beta_sbp * ln_sbp
        + c["smoker"] * int(smoker)
        + c["diabetes"] * int(diabetes)
    )
    risk = 1.0 - c["S0"] ** math.exp(beta_x - c["mean_beta_x"])
    risk = max(0.0, min(1.0, risk))
    risk_str = float64_to_decimal_str(risk, digits=10)

    trace.input("sex",         sex)
    trace.input("age",         age)
    trace.input("total_chol",  total_chol)
    trace.input("hdl",         hdl)
    trace.input("sbp",         sbp)
    trace.input("treated_htn", treated_htn)
    trace.input("smoker",      smoker)
    trace.input("diabetes",    diabetes)
    trace.step("beta_x",          float64_to_decimal_str(beta_x, digits=10))
    trace.step("risk_probability", risk_str)
    trace.output({"risk": risk_str})

    return {
        "risk":        risk_str,
        "risk_pct":    float64_to_decimal_str(risk * 100.0, digits=8),
        "trace":       trace.to_dict(),
    }
