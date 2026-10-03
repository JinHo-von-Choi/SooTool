"""미국 FICA 급여세와 자영업세 계산 (tax_us.fica).

근로자 모드(employee):
  OASDI 6.2% (IRC 3101(a)) 와 고용주 OASDI 6.2% (IRC 3111(a)) 는 고용주별 연간 임금 중
  사회보장 기준액(Social Security Act 230)까지에 부과한다(IRC 3121(a)(1)).
  Medicare(HI) 1.45% 는 근로자·고용주 각각 전액에 부과한다(IRC 3101(b)(1), 3111(b)).
  추가 Medicare 0.9% (IRC 3101(b)(2)) 는 근로자만 부담한다.
    - 원천징수: 해당 고용주가 지급한 임금 중 200,000 달러 초과분(IRC 3102(f)(1)).
    - 신고 시 정산: 신고 유형별 임계값(공동 250,000, 부부 개별 125,000, 그 밖 200,000)을
      넘는 Medicare 임금 합계분(Form 8959 Part I). filing_status 를 줄 때만 계산한다.

자영업 모드(self_employed, Schedule SE Part I 일반 방식):
  순자영업소득 = 순이익 x (1 - (12.4% + 2.9%) / 2) = 순이익 x 92.35% (IRC 1402(a)(12)).
  400 달러 미만이면 자영업 소득이 없다(IRC 1402(b)(2)).
  OASDI 12.4% 는 (기준액 - 같은 해 사회보장 임금) 한도까지(IRC 1401(a), 1402(b)(1)),
  HI 2.9% 는 전액(IRC 1401(b)(1)). 자영업세의 50% 는 소득공제(IRC 164(f), Schedule SE line 13).
  추가 Medicare 0.9% 는 신고 유형별 임계값을 Medicare 임금만큼 줄인(0 미만 불가) 금액을
  넘는 자영업 소득에 부과한다(IRC 1401(b)(2), Form 8959 Part II).

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any, NotRequired, TypedDict, cast

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import PolicyResult
from sootool.core.rounding import apply as round_apply
from sootool.modules.tax.progressive import _parse_rounding
from sootool.policy_mgmt.loader import load as policy_load
from sootool.policy_mgmt.trace_ext import enrich_response

_ZERO  = Decimal("0")
_HALF  = Decimal("0.5")
_MODES = frozenset({"employee", "self_employed"})

_Rounder = Callable[[Decimal], Decimal]
_Policy  = dict[str, dict[str, Any]]


class FicaShare(TypedDict):
    """근로자 또는 고용주 한쪽의 FICA 부담액."""

    social_security_tax:     str
    medicare_tax:            str
    additional_medicare_tax: str
    total:                   str


class FicaResult(PolicyResult):
    mode:                      str
    filing_status:             str | None
    social_security_wage_base: str
    employee:                                  NotRequired[FicaShare]
    employer:                                  NotRequired[FicaShare]
    social_security_taxable_wages:             NotRequired[str]
    medicare_wages:                            NotRequired[str]
    additional_medicare_withholding_threshold: NotRequired[str]
    additional_medicare_withholding_base:      NotRequired[str]
    additional_medicare_filing_threshold:      NotRequired[str]
    additional_medicare_liability_base:        NotRequired[str]
    additional_medicare_liability:             NotRequired[str]
    net_earnings:                              NotRequired[str]
    below_minimum:                             NotRequired[bool]
    social_security_taxable_earnings:          NotRequired[str]
    social_security_tax:                       NotRequired[str]
    medicare_tax:                              NotRequired[str]
    self_employment_tax:                       NotRequired[str]
    self_employment_tax_deduction:             NotRequired[str]
    additional_medicare_tax:                   NotRequired[str]
    self_employment_total:                     NotRequired[str]


def _amount(name: str, value: str, *, allow_negative: bool = False) -> Decimal:
    """금액 입력을 유한한 Decimal 로 바꾸고 필요하면 음수를 거부한다."""
    amount = D(value)
    if not amount.is_finite():
        raise InvalidInputError(f"{name}는 유한한 숫자여야 합니다.")
    if not allow_negative and amount < _ZERO:
        raise InvalidInputError(f"{name}는 0 이상이어야 합니다.")
    return amount


def _excess(amount: Decimal, threshold: Decimal) -> Decimal:
    """임계값을 넘는 부분. 넘지 않으면 0."""
    return max(amount - threshold, _ZERO)


def _filing_threshold(data: _Policy, filing_status: str) -> Decimal:
    """신고 유형별 추가 Medicare 임계값(IRC 3101(b)(2), 1401(b)(2)(A))."""
    thresholds = data["additional_medicare"]["filing_thresholds"]
    if filing_status not in thresholds:
        raise InvalidInputError(
            f"유효하지 않은 filing_status: '{filing_status}'. 허용값: {sorted(thresholds)}"
        )
    return D(str(thresholds[filing_status]))


@REGISTRY.tool(
    namespace="tax_us",
    name="fica",
    description=(
        "미국 FICA 급여세(IRC 3101, 3111) 근로자·고용주 부담분과 자영업세 SECA(IRC 1401, "
        "순이익의 92.35%)를 과세연도 정책으로 계산한다. 금액은 USD 연간 합계 문자열, 세목별로 "
        "decimals 자리 반올림(기본 HALF_UP 2자리). 추가 Medicare 0.9%는 고용주 원천징수"
        "(20만 달러 초과)와 filing_status 별 신고 정산(25만/12.5만/20만)을 나눠 낸다. "
        "사회보장 기준액은 고용주 한 곳 기준이며 복수 고용주 초과징수 환급, 선택적 계산법, "
        "RRTA, 배우자 자영업 소득 합산은 다루지 않는다. 오용 예: 급여 1회분을 연간 임금으로 넣기."
    ),
    version="1.0.0",
    policy=True,
)
def tax_us_fica(
    year:                 int,
    mode:                 str        = "employee",
    wages:                str        = "0",
    net_profit:           str        = "0",
    filing_status:        str | None = None,
    other_medicare_wages: str        = "0",
    rounding:             str        = "HALF_UP",
    decimals:             int        = 2,
) -> FicaResult:
    """미국 FICA(근로자·고용주) 또는 SECA(자영업) 세액을 계산한다.

    Args:
        year:                 과세연도(2025, 2026). 임금은 지급 연도, 자영업 소득은 과세연도 개시 연도 기준.
        mode:                 "employee"(근로자·고용주 FICA) 또는 "self_employed"(Schedule SE).
        wages:                USD. employee 모드는 이 고용주가 그 해 지급한 FICA 과세 임금 연간 합계.
                              self_employed 모드는 본인의 W-2 사회보장·Medicare 임금(기준액과 추가
                              Medicare 임계값을 줄이는 데만 쓰며 그 임금의 FICA 는 계산하지 않는다).
        net_profit:           USD. self_employed 모드의 순이익(Schedule SE line 3, 음수 허용).
        filing_status:        single/married_joint/married_separate/head_of_household/
                              qualifying_surviving_spouse. employee 모드는 선택(주면 신고 정산액 계산),
                              self_employed 모드는 필수.
        other_medicare_wages: USD. Form 8959 에 합산하지만 wages 에 없는 Medicare 임금
                              (다른 고용주 임금, 공동 신고 배우자 임금).
        rounding:             반올림 정책(기본 HALF_UP). 세목별로 적용한다.
        decimals:             소수 자리수(기본 2, 센트).
    """
    trace = CalcTrace(
        tool="tax_us.fica",
        formula=(
            "employee: OASDI = rate * min(wages, base) (근로자·고용주 각각); HI = rate * wages; "
            "추가 Medicare 원천징수 = 0.009 * max(wages - 200000, 0); "
            "신고 정산 = 0.009 * max(wages + other_medicare_wages - threshold(filing_status), 0). "
            "self_employed: NE = net_profit * (1 - (0.124 + 0.029) / 2) (net_profit > 0); NE < 400 이면 0; "
            "OASDI = 0.124 * min(NE, max(base - wages, 0)); HI = 0.029 * NE; 공제 = 50% * (OASDI + HI); "
            "추가 Medicare = 0.009 * max(NE - max(threshold - wages - other_medicare_wages, 0), 0)"
        ),
    )

    if mode not in _MODES:
        raise InvalidInputError(f"mode는 {sorted(_MODES)} 중 하나여야 합니다. 입력: '{mode}'")
    if decimals < 0:
        raise InvalidInputError("decimals는 0 이상이어야 합니다.")
    policy       = _parse_rounding(rounding)
    wages_d      = _amount("wages", wages)
    other_d      = _amount("other_medicare_wages", other_medicare_wages)
    net_profit_d = _amount("net_profit", net_profit, allow_negative=True)
    if mode == "employee" and net_profit_d != _ZERO:
        raise InvalidInputError("net_profit은 mode='self_employed' 일 때만 씁니다.")
    if mode == "employee" and filing_status is None and other_d != _ZERO:
        raise InvalidInputError("other_medicare_wages는 filing_status를 줄 때만 신고 정산에 씁니다.")
    if mode == "self_employed" and filing_status is None:
        raise InvalidInputError(
            "self_employed 모드는 추가 Medicare 임계값을 정하기 위해 filing_status가 필요합니다."
        )

    policy_doc = policy_load("tax_us", "fica", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]
    base       = D(str(data["social_security"]["wage_base"]))
    add_rate   = D(str(data["additional_medicare"]["rate"]))
    threshold  = None if filing_status is None else _filing_threshold(data, filing_status)

    trace.input("year",                 year)
    trace.input("mode",                 mode)
    trace.input("wages",                wages)
    trace.input("net_profit",           net_profit)
    trace.input("filing_status",        filing_status)
    trace.input("other_medicare_wages", other_medicare_wages)
    trace.input("policy_version",       pv)
    trace.step("social_security_wage_base", str(base))

    def rnd(value: Decimal) -> Decimal:
        return round_apply(value, decimals, policy)

    resp: dict[str, object] = {
        "mode":                      mode,
        "filing_status":             filing_status,
        "social_security_wage_base": str(base),
    }
    if threshold is not None and mode == "self_employed":
        resp.update(_self_employed(data, wages_d, other_d, net_profit_d, threshold, add_rate, base, rnd, trace))
    else:
        resp.update(_employee(data, wages_d, other_d, threshold, add_rate, base, rnd, trace))

    resp["policy_version"] = pv
    resp["trace"]          = trace.to_dict()
    return cast(FicaResult, enrich_response(resp, policy_doc))


def _employee(
    data:      _Policy,
    wages:     Decimal,
    other:     Decimal,
    threshold: Decimal | None,
    add_rate:  Decimal,
    base:      Decimal,
    rnd:       _Rounder,
    trace:     CalcTrace,
) -> dict[str, object]:
    ss_cfg   = data["social_security"]
    med_cfg  = data["medicare"]
    withhold = D(str(data["additional_medicare"]["withholding_threshold"]))

    ss_wages      = min(wages, base)
    withhold_base = _excess(wages, withhold)

    ee_ss  = rnd(ss_wages * D(str(ss_cfg["employee_rate"])))
    ee_med = rnd(wages * D(str(med_cfg["employee_rate"])))
    ee_add = rnd(withhold_base * add_rate)
    er_ss  = rnd(ss_wages * D(str(ss_cfg["employer_rate"])))
    er_med = rnd(wages * D(str(med_cfg["employer_rate"])))

    employee: FicaShare = {
        "social_security_tax":     str(ee_ss),
        "medicare_tax":            str(ee_med),
        "additional_medicare_tax": str(ee_add),
        "total":                   str(ee_ss + ee_med + ee_add),
    }
    employer: FicaShare = {
        "social_security_tax":     str(er_ss),
        "medicare_tax":            str(er_med),
        "additional_medicare_tax": str(rnd(_ZERO)),
        "total":                   str(er_ss + er_med),
    }
    trace.step("social_security_taxable_wages",        str(ss_wages))
    trace.step("additional_medicare_withholding_base", str(withhold_base))
    trace.step("employee",                             employee)
    trace.step("employer",                             employer)

    out: dict[str, object] = {
        "employee":                                  employee,
        "employer":                                  employer,
        "social_security_taxable_wages":             str(ss_wages),
        "medicare_wages":                            str(wages),
        "additional_medicare_withholding_threshold": str(withhold),
        "additional_medicare_withholding_base":      str(withhold_base),
    }
    if threshold is not None:
        liability_base = _excess(wages + other, threshold)
        liability      = rnd(liability_base * add_rate)
        trace.step("additional_medicare_filing_threshold", str(threshold))
        trace.step("additional_medicare_liability_base",   str(liability_base))
        trace.step("additional_medicare_liability",        str(liability))
        out["additional_medicare_filing_threshold"] = str(threshold)
        out["additional_medicare_liability_base"]   = str(liability_base)
        out["additional_medicare_liability"]        = str(liability)
    trace.output(employee["total"])
    return out


def _self_employed(
    data:       _Policy,
    wages:      Decimal,
    other:      Decimal,
    net_profit: Decimal,
    threshold:  Decimal,
    add_rate:   Decimal,
    base:       Decimal,
    rnd:        _Rounder,
    trace:      CalcTrace,
) -> dict[str, object]:
    ss_rate  = D(str(data["social_security"]["self_employment_rate"]))
    med_rate = D(str(data["medicare"]["self_employment_rate"]))
    minimum  = D(str(data["self_employment"]["minimum_net_earnings"]))

    factor       = Decimal("1") - (ss_rate + med_rate) * _HALF
    net_earnings = net_profit * factor if net_profit > _ZERO else net_profit
    below_min    = net_earnings < minimum
    se_income    = _ZERO if below_min else net_earnings

    ss_room     = max(base - wages, _ZERO)
    ss_earnings = min(se_income, ss_room)
    ss_tax      = rnd(ss_earnings * ss_rate)
    med_tax     = rnd(se_income * med_rate)
    se_tax      = ss_tax + med_tax
    deduction   = rnd(se_tax * _HALF)

    reduced_threshold = max(threshold - wages - other, _ZERO)
    add_base          = _excess(se_income, reduced_threshold)
    add_tax           = rnd(add_base * add_rate)
    total             = se_tax + add_tax

    trace.step("net_earnings_factor",                  str(factor))
    trace.step("net_earnings",                         str(net_earnings))
    trace.step("below_minimum",                        below_min)
    trace.step("social_security_room",                 str(ss_room))
    trace.step("social_security_taxable_earnings",     str(ss_earnings))
    trace.step("self_employment_tax",                  str(se_tax))
    trace.step("additional_medicare_filing_threshold", str(reduced_threshold))
    trace.step("additional_medicare_liability_base",   str(add_base))
    trace.output(str(total))

    return {
        "net_earnings":                         str(net_earnings),
        "below_minimum":                        below_min,
        "social_security_taxable_earnings":     str(ss_earnings),
        "social_security_tax":                  str(ss_tax),
        "medicare_tax":                         str(med_tax),
        "self_employment_tax":                  str(se_tax),
        "self_employment_tax_deduction":        str(deduction),
        "additional_medicare_filing_threshold": str(reduced_threshold),
        "additional_medicare_liability_base":   str(add_base),
        "additional_medicare_tax":              str(add_tax),
        "self_employment_total":                str(total),
    }
