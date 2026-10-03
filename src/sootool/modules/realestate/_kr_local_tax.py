"""취득세·재산세 공통 산식 (지방세법 제11조제1항제8호, 제110조, 제111조의2).

Author: 최진호
Date: 2026-10-03

취득세(acquisition_tax, kr_local_property)와 재산세(kr_property_tax, kr_local_property)가
같은 법정 산식을 쓰므로 한곳에 둔다.

- 주택 유상취득 표준세율: 구간별 단일 세율 또는 산식 세율(``rate_formula``).
  6억 초과 9억 이하 구간은 (취득당시가액 × 2/3억원 - 3) × 1/100 이며
  소수점 이하 다섯째자리에서 반올림하여 넷째자리까지 계산한다.
- 재산세 공정시장가액비율: 일반 주택 비율, 1세대 1주택은 시가표준액 구간별 비율.
- 재산세 1세대 1주택 특례세율: 시가표준액 상한 이하에서만 적용.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sootool.core.decimal_ops import D
from sootool.core.rounding import RoundingPolicy
from sootool.core.rounding import apply as round_apply


def acquisition_standard_rate(price: Decimal, brackets: list[dict[str, Any]]) -> Decimal:
    """취득가액이 속한 구간의 표준세율을 반환한다. 구간 경계는 상한 포함이다.

    구간에 ``rate_formula`` 가 있으면 산식으로 계산한다.
    rate = (price × slope_numerator / slope_denominator + intercept_pct) / 100,
    소수점 이하 ``round_decimals`` 자리까지 반올림.
    """
    for bracket in brackets:
        upper = bracket.get("upper")
        if upper is None or price <= D(str(upper)):
            return _bracket_rate(price, bracket)
    return _bracket_rate(price, brackets[-1])


def _bracket_rate(price: Decimal, bracket: dict[str, Any]) -> Decimal:
    formula = bracket.get("rate_formula")
    if formula:
        slope     = D(str(formula["slope_numerator"])) / D(str(formula["slope_denominator"]))
        intercept = D(str(formula["intercept_pct"]))
        raw       = (price * slope + intercept) / Decimal("100")
        return round_apply(raw, int(formula["round_decimals"]), RoundingPolicy.HALF_UP)
    return D(str(bracket["rate"]))


def lookup_upper_table(value: Decimal, table: list[dict[str, Any]], field: str) -> Decimal:
    """상한 포함 구간표(``upper``)에서 값이 속한 구간의 ``field`` 를 반환한다."""
    for row in table:
        upper = row.get("upper")
        if upper is None or value <= D(str(upper)):
            return D(str(row[field]))
    return D(str(table[-1][field]))


def property_fair_market_ratio(
    published_price: Decimal,
    data:            dict[str, Any],
    is_one_house:    bool,
) -> Decimal:
    """재산세 공정시장가액비율. 1세대 1주택 구간표가 있으면 시가표준액 구간별 비율을 쓴다."""
    one_house_table = data.get("one_house_fair_market_ratio")
    if is_one_house and one_house_table:
        return lookup_upper_table(published_price, one_house_table, "ratio")
    return D(str(data["fair_market_ratio"]))


def property_special_brackets(
    published_price: Decimal,
    data:            dict[str, Any],
    is_one_house:    bool,
) -> list[dict[str, Any]] | None:
    """1세대 1주택 특례세율 구간표. 적용 대상이 아니면 None."""
    special = data.get("one_house_special")
    if not (is_one_house and special):
        return None
    if published_price > D(str(special["max_published_price"])):
        return None
    brackets: list[dict[str, Any]] = special["brackets"]
    return brackets


def property_tax_base(
    published_price:            Decimal,
    fair_market_ratio:          Decimal,
    prior_year_published_price: Decimal | None,
    cap_rate:                   Decimal | None,
) -> tuple[Decimal, Decimal | None]:
    """주택 재산세 과세표준과 과세표준상한액(지방세법 제110조제3항)을 계산한다.

    과세표준상한액 = 직전 연도 시가표준액 × 해당 연도 공정시장가액비율
                    + 해당 연도 과세표준 × 과세표준상한율.
    직전 연도 시가표준액이나 상한율이 없으면 상한을 적용하지 않는다.
    """
    base = published_price * fair_market_ratio
    if prior_year_published_price is None or cap_rate is None:
        return base, None
    cap = prior_year_published_price * fair_market_ratio + base * cap_rate
    return min(base, cap), cap
