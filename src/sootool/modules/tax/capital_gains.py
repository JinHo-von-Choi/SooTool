"""Korean capital gains tax (양도소득세) calculator with LTCT deduction.

Author: 최진호
Date: 2026-04-22

장기보유특별공제 (Long-Term Capital Tax Deduction):
  - 일반 부동산: 3년 보유 시 6%, 이후 1년당 2% 추가, 최대 30% (15년)
  - 1세대1주택: 보유+거주 요건 충족 시, 최대 80% (10년 이상)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.audit       import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors      import InvalidInputError
from sootool.core.registry    import REGISTRY
from sootool.core.rounding    import RoundingPolicy
from sootool.modules.tax.progressive import _calc_progressive
from sootool.policies import load as policy_load


def _lookup_ltct_rate(
    holding_years: int,
    table:         list[dict[str, Any]],
) -> Decimal:
    """Look up the LTCT deduction rate from the policy table."""
    for entry in table:
        min_y = entry["holding_years_min"]
        max_y = entry["holding_years_max"]  # None means no upper limit

        if holding_years < min_y:
            continue
        if max_y is None or holding_years <= max_y:
            return D(str(entry["rate"]))

    return Decimal("0")


@REGISTRY.tool(
    namespace="tax",
    name="capital_gains_kr",
    description=(
        "한국 양도소득세 계산 (장기보유특별공제 포함). "
        "소득세법 제95조 기준."
    ),
    version="1.0.0",
)
def tax_capital_gains_kr(
    acquisition_price: str,
    sale_price:        str,
    holding_years:     int,
    is_one_house:      bool,
    year:              int,
    decimals:          int = 0,
) -> dict[str, Any]:
    """Calculate Korean capital gains tax with LTCT special deduction.

    Args:
        acquisition_price: 취득가액 (Decimal string, 원)
        sale_price:        양도가액 (Decimal string, 원)
        holding_years:     보유 기간 (년, 정수)
        is_one_house:      1세대1주택 여부
        year:              과세연도
        decimals:          소수점 자리수 (기본 0)

    Returns:
        {gain, ltct_deduction, taxable_gain, tax, policy_version, trace}
    """
    trace = CalcTrace(
        tool="tax.capital_gains_kr",
        formula=(
            "gain = sale - acquisition; "
            "ltct_deduction = gain * ltct_rate; "
            "taxable_gain = gain - ltct_deduction; "
            "tax = 누진세율 적용(taxable_gain)"
        ),
    )

    acq  = D(acquisition_price)
    sale = D(sale_price)

    if acq < Decimal("0"):
        raise InvalidInputError("acquisition_price는 0 이상이어야 합니다.")
    if sale < Decimal("0"):
        raise InvalidInputError("sale_price는 0 이상이어야 합니다.")
    if holding_years < 0:
        raise InvalidInputError("holding_years는 0 이상이어야 합니다.")

    policy_doc = policy_load("tax", "kr_capital_gains", year)
    data       = policy_doc["data"]
    pv         = policy_doc["policy_version"]

    table_key = "one_house" if is_one_house else "general"
    ltct_table = data[table_key]
    brackets   = data["income_tax_brackets"]

    trace.input("acquisition_price", acquisition_price)
    trace.input("sale_price",        sale_price)
    trace.input("holding_years",     holding_years)
    trace.input("is_one_house",      is_one_house)
    trace.input("year",              year)

    gain = sale - acq

    if gain <= Decimal("0"):
        trace.step("gain",            str(gain))
        trace.step("ltct_deduction",  "0")
        trace.step("taxable_gain",    "0")
        trace.output("0")
        return {
            "gain":            str(gain),
            "ltct_deduction":  "0",
            "taxable_gain":    "0",
            "tax":             "0",
            "policy_version":  pv,
            "trace":           trace.to_dict(),
        }

    ltct_rate   = _lookup_ltct_rate(holding_years, ltct_table)
    ltct_deduct = gain * ltct_rate
    taxable     = gain - ltct_deduct

    if taxable < Decimal("0"):
        taxable = Decimal("0")

    tax, _, _, _ = _calc_progressive(taxable, brackets, RoundingPolicy.HALF_UP, decimals)

    trace.step("gain",           str(gain))
    trace.step("ltct_rate",      str(ltct_rate))
    trace.step("ltct_deduction", str(ltct_deduct))
    trace.step("taxable_gain",   str(taxable))
    trace.output(str(tax))

    return {
        "gain":            str(gain),
        "ltct_deduction":  str(ltct_deduct),
        "taxable_gain":    str(taxable),
        "tax":             str(tax),
        "policy_version":  pv,
        "trace":           trace.to_dict(),
    }
