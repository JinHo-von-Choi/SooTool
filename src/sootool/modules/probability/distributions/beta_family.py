"""Beta family tools: beta and F.
"""
from __future__ import annotations

from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY
from sootool.modules.probability.distributions._common import (
    DistributionResult,
    _dist_result,
    _parse_float,
    _parse_quantile,
    _validate_nonneg_float,
    _validate_positive_float,
    stats,
)


@REGISTRY.tool(
    namespace="probability",
    name="beta_pdf",
    description="베타분포의 확률밀도 f(x; α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값은 1 을 넘을 수 있고 확률이 아니다.",
    version="1.0.0",
)
def beta_pdf(x: str, alpha: str, beta: str) -> DistributionResult:
    x_f     = _parse_float(x,     "x")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    if x_f < 0.0 or x_f > 1.0:
        raise DomainConstraintError(f"x={x}은(는) [0, 1] 구간이어야 합니다.")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.pdf(x_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_pdf",
        "f(x; α, β) = x^(α-1) * (1-x)^(β-1) / B(α, β)",
        "pdf",
        {"x": x, "alpha": alpha, "beta": beta},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="beta_cdf",
    description="베타분포의 누적확률 P(X ≤ x) = I_x(α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. alpha 와 beta 를 서로 바꾸면 결과가 달라진다.",
    version="1.0.0",
)
def beta_cdf(x: str, alpha: str, beta: str) -> DistributionResult:
    x_f     = _parse_float(x,     "x")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    if x_f < 0.0 or x_f > 1.0:
        raise DomainConstraintError(f"x={x}은(는) [0, 1] 구간이어야 합니다.")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.cdf(x_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_cdf",
        "P(X ≤ x) = I_x(α, β)",
        "cdf",
        {"x": x, "alpha": alpha, "beta": beta},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="beta_ppf",
    description="베타분포의 분위수를 구한다. q 는 0 초과 1 미만, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. q 가 0 또는 1 이면 오류이며 결과는 [0, 1] 구간의 값이다.",
    version="1.0.0",
)
def beta_ppf(q: str, alpha: str, beta: str) -> DistributionResult:
    q_f     = _parse_quantile(q,  "q")
    alpha_f = _parse_float(alpha, "alpha")
    beta_f  = _parse_float(beta,  "beta")
    _validate_positive_float(alpha_f, "alpha", alpha)
    _validate_positive_float(beta_f,  "beta",  beta)
    val = float(stats.beta.ppf(q_f, a=alpha_f, b=beta_f))
    return _dist_result(
        "probability.beta_ppf",
        "x = I⁻¹_q(α, β)",
        "ppf",
        {"q": q, "alpha": alpha, "beta": beta},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="f_pdf",
    description="F 분포의 확률밀도를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. dfn 과 dfd 를 바꾸면 결과가 달라진다.",
    version="1.0.0",
)
def f_pdf(x: str, dfn: str, dfd: str) -> DistributionResult:
    x_f   = _parse_float(x,   "x")
    dfn_f = _parse_float(dfn, "dfn")
    dfd_f = _parse_float(dfd, "dfd")
    _validate_nonneg_float(x_f,        "x",   x)
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.pdf(x_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_pdf",
        "f(x; d1, d2) = √((d1 x)^d1 d2^d2 / ((d1 x + d2)^(d1+d2))) / (x B(d1/2, d2/2))",
        "pdf",
        {"x": x, "dfn": dfn, "dfd": dfd},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="f_cdf",
    description="F 분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 검정의 p 값은 1 에서 이 값을 뺀 오른쪽 꼬리다.",
    version="1.0.0",
)
def f_cdf(x: str, dfn: str, dfd: str) -> DistributionResult:
    x_f   = _parse_float(x,   "x")
    dfn_f = _parse_float(dfn, "dfn")
    dfd_f = _parse_float(dfd, "dfd")
    _validate_nonneg_float(x_f,        "x",   x)
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.cdf(x_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_cdf",
        "P(X ≤ x) = I_{d1 x/(d1 x + d2)}(d1/2, d2/2)",
        "cdf",
        {"x": x, "dfn": dfn, "dfd": dfd},
        val,
    )


@REGISTRY.tool(
    namespace="probability",
    name="f_ppf",
    description="F 분포의 분위수를 구한다. q 는 0 초과 1 미만, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 유의수준 α 의 임계값은 q 에 1-α 를 넣는다.",
    version="1.0.0",
)
def f_ppf(q: str, dfn: str, dfd: str) -> DistributionResult:
    q_f   = _parse_quantile(q, "q")
    dfn_f = _parse_float(dfn,  "dfn")
    dfd_f = _parse_float(dfd,  "dfd")
    _validate_positive_float(dfn_f,    "dfn", dfn)
    _validate_positive_float(dfd_f,    "dfd", dfd)
    val = float(stats.f.ppf(q_f, dfn=dfn_f, dfd=dfd_f))
    return _dist_result(
        "probability.f_ppf",
        "x = F⁻¹(q; d1, d2)",
        "ppf",
        {"q": q, "dfn": dfn, "dfd": dfd},
        val,
    )
