"""VAT (부가가치세) tools: extract and add."""
from __future__ import annotations

from decimal import Decimal

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D, add, div, mul, sub
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.core.rounding import RoundingPolicy, apply


class VatExtractResult(TracedResult):
    net: str
    vat: str


class VatAddResult(TracedResult):
    gross: str
    vat:   str


def _parse_policy(rounding: str) -> RoundingPolicy:
    try:
        return RoundingPolicy(rounding)
    except ValueError as exc:
        raise InvalidInputError(f"유효하지 않은 반올림 정책: {rounding!r}") from exc


@REGISTRY.tool(
    namespace="accounting",
    name="vat_extract",
    description=(
        "공급대가(부가세 포함 금액)에서 공급가액과 부가세를 역산한다. 공급가액 = gross / (1 + rate)를 정수 자리로 "
        "rounding(기본 DOWN, 절사) 처리하고 부가세 = gross - 공급가액. rate 기본 0.1, 금액은 Decimal 문자열. "
        "공급가액에서 공급대가를 구하는 순방향 계산에는 vat_add 를 쓴다."
    ),
    version="1.0.0",
)
def vat_extract(
    gross: str,
    rate: str = "0.1",
    rounding: str = "DOWN",
) -> VatExtractResult:
    """Extract net (공급가액) and VAT from gross (공급대가).

    Formula: net = floor(gross / (1 + rate)), vat = gross - net

    The Korean standard (국세청 부가가치세법 시행령) uses truncation (DOWN rounding)
    when computing the net from a gross-inclusive price.

    Args:
        gross:    공급대가 (Decimal string)
        rate:     VAT 세율, 기본 0.1
        rounding: 반올림 정책 (한국 표준: DOWN)

    Returns:
        {net, vat, trace}
    """
    trace = CalcTrace(
        tool="accounting.vat_extract",
        formula="net = gross / (1 + rate) [rounding]; vat = gross - net",
    )
    policy = _parse_policy(rounding)

    gross_d = D(gross)
    rate_d  = D(rate)

    if rate_d <= Decimal("0"):
        raise InvalidInputError("rate는 0 초과여야 합니다.")
    if gross_d < Decimal("0"):
        raise InvalidInputError("gross는 0 이상이어야 합니다.")

    trace.input("gross",    gross)
    trace.input("rate",     rate)
    trace.input("rounding", rounding)

    divisor = add(Decimal("1"), rate_d)
    net_raw = div(gross_d, divisor)
    net     = apply(net_raw, 0, policy)
    vat     = sub(gross_d, net)

    trace.step("divisor", str(divisor))
    trace.step("net_raw", str(net_raw))
    trace.step("net",     str(net))
    trace.step("vat",     str(vat))
    trace.output({"net": str(net), "vat": str(vat)})

    return {
        "net":   str(net),
        "vat":   str(vat),
        "trace": trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="accounting",
    name="vat_add",
    description=(
        "공급가액에 부가세를 더해 공급대가를 계산한다. 부가세 = 공급가액 x rate(기본 0.1)를 정수 자리로 "
        "rounding 처리하며 기본은 HALF_EVEN 으로 vat_extract 의 기본(DOWN)과 다르다. 금액은 Decimal 문자열. "
        "공급대가에서 공급가액을 구하려면 vat_extract 를 쓴다."
    ),
    version="1.0.0",
)
def vat_add(
    net: str,
    rate: str = "0.1",
    rounding: str = "HALF_EVEN",
) -> VatAddResult:
    """Add VAT to net to compute gross.

    Formula: vat = net * rate (rounded), gross = net + vat

    Args:
        net:      공급가액 (Decimal string)
        rate:     VAT 세율, 기본 0.1
        rounding: 반올림 정책

    Returns:
        {gross, vat, trace}
    """
    trace = CalcTrace(
        tool="accounting.vat_add",
        formula="vat = net * rate [rounding]; gross = net + vat",
    )
    policy = _parse_policy(rounding)

    net_d  = D(net)
    rate_d = D(rate)

    if rate_d <= Decimal("0"):
        raise InvalidInputError("rate는 0 초과여야 합니다.")
    if net_d < Decimal("0"):
        raise InvalidInputError("net은 0 이상이어야 합니다.")

    trace.input("net",      net)
    trace.input("rate",     rate)
    trace.input("rounding", rounding)

    vat_raw = mul(net_d, rate_d)
    vat     = apply(vat_raw, 0, policy)
    gross   = add(net_d, vat)

    trace.step("vat_raw", str(vat_raw))
    trace.step("vat",     str(vat))
    trace.step("gross",   str(gross))
    trace.output({"gross": str(gross), "vat": str(vat)})

    return {
        "gross": str(gross),
        "vat":   str(vat),
        "trace": trace.to_dict(),
    }
