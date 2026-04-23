"""Trigger table data for skill_guide — maps detection signals to tools."""
from __future__ import annotations

from typing import Any

_TRIGGERS_KO: list[dict[str, Any]] = [
    {
        "signal": "숫자 두 개 이상 사칙연산",
        "tool": "core.add / core.sub / core.mul / core.div 또는 core.batch",
        "reason": "확률 추론 회피 — LLM 직접 산수는 오차 발생 가능",
    },
    {
        "signal": '"세액", "소득세", "양도세", "취득세" 포함',
        "tool": "tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax",
        "reason": "세율표 버전 고정 — 연도별 정책 YAML 사용",
    },
    {
        "signal": '"부가세", "공급가액" 포함',
        "tool": "accounting.vat_extract / accounting.vat_add",
        "reason": "DOWN 반올림 법정 표준 준수",
    },
    {
        "signal": '"현재가치", "NPV", "IRR", "할인율" 포함',
        "tool": "finance.pv / finance.fv / finance.npv / finance.irr",
        "reason": "Decimal 복리 정확도 — float 오차 누적 방지",
    },
    {
        "signal": '"감가상각", "정액법", "정률법" 포함',
        "tool": "accounting.depreciation_straight_line / accounting.depreciation_declining_balance",
        "reason": "기말 잔존가 처리 및 HALF_EVEN 반올림 표준",
    },
    {
        "signal": '"영업일", "공휴일 제외" 포함',
        "tool": "datetime.add_business_days / datetime.count_business_days",
        "reason": "holidays 라이브러리 기반 법정 공휴일 정확 반영",
    },
    {
        "signal": '"t-검정", "신뢰구간", "p-value" 포함',
        "tool": "stats.ttest_one_sample / stats.ttest_two_sample / stats.ci_mean",
        "reason": "scipy 기반 수치 안정성",
    },
    {
        "signal": "확률·분포 PDF/CDF 계산 요청",
        "tool": "probability.normal_pdf / probability.normal_cdf / probability.binomial_pmf 등",
        "reason": "수치 안정성 및 재현 가능한 결과",
    },
    {
        "signal": "행렬·벡터 연산 요청",
        "tool": "geometry.matrix_multiply / geometry.matrix_inverse / geometry.vector_dot 등",
        "reason": "numpy 기반 수치 연산",
    },
    {
        "signal": "단위 변환 요청",
        "tool": "units.convert / units.temperature",
        "reason": "pint 라이브러리 기반 단위 체계",
    },
    {
        "signal": "통화 환산 요청",
        "tool": "units.fx_convert / units.fx_triangulate",
        "reason": "삼각 환산 지원",
    },
    {
        "signal": "복수 시나리오 비교 요청",
        "tool": "core.batch",
        "reason": "왕복 비용 절감 — N개 독립 연산 병렬 실행",
    },
    {
        "signal": "이전 계산 결과를 다음 계산 입력으로 사용",
        "tool": "core.pipeline",
        "reason": "결정론 체인 보장 — 수동 중계 오류 방지",
    },
    {
        "signal": '"채권 수익률", "듀레이션" 포함',
        "tool": "finance.bond_ytm / finance.bond_duration",
        "reason": "Macaulay·Modified Duration 구분 계산",
    },
    {
        "signal": '"옵션 가격", "그릭스", "블랙숄즈" 포함',
        "tool": "finance.black_scholes",
        "reason": "mpmath 고정밀 계산",
    },
    {
        "signal": '"세법 개정", "고시문", "세율 변경" 포함',
        "tool": "sootool.policy_propose / sootool.policy_activate",
        "reason": "정책 YAML 갱신 워크플로우 — validate → propose → activate 순서 준수",
    },
    {
        "signal": '"정책 롤백", "이전 세율", "원상 복구" 포함',
        "tool": "sootool.policy_rollback",
        "reason": "override 정책 제거 후 패키지 기본값 복원 — 감사 로그 자동 기록",
    },
]

_TRIGGERS_EN: list[dict[str, Any]] = [
    {
        "signal": "Two or more numbers with arithmetic operations",
        "tool": "core.add / core.sub / core.mul / core.div or core.batch",
        "reason": "Avoid probabilistic reasoning — LLM direct arithmetic may produce errors",
    },
    {
        "signal": '"income tax", "capital gains tax", "acquisition tax"',
        "tool": "tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax",
        "reason": "Policy version pinning — uses per-year YAML",
    },
    {
        "signal": '"VAT", "supply amount", "tax-inclusive price"',
        "tool": "accounting.vat_extract / accounting.vat_add",
        "reason": "DOWN rounding as required by law",
    },
    {
        "signal": '"present value", "NPV", "IRR", "discount rate"',
        "tool": "finance.pv / finance.fv / finance.npv / finance.irr",
        "reason": "Decimal compound interest precision — prevents float drift",
    },
    {
        "signal": '"depreciation", "straight-line", "declining balance"',
        "tool": "accounting.depreciation_straight_line / accounting.depreciation_declining_balance",
        "reason": "Period-end salvage handling and HALF_EVEN rounding standard",
    },
    {
        "signal": '"business days", "excluding holidays"',
        "tool": "datetime.add_business_days / datetime.count_business_days",
        "reason": "Accurate statutory holidays via holidays library",
    },
    {
        "signal": '"t-test", "confidence interval", "p-value"',
        "tool": "stats.ttest_one_sample / stats.ttest_two_sample / stats.ci_mean",
        "reason": "scipy-based numerical stability",
    },
    {
        "signal": "Probability / distribution PDF/CDF computation",
        "tool": "probability.normal_pdf / probability.normal_cdf / probability.binomial_pmf etc.",
        "reason": "Numerical stability and reproducible results",
    },
    {
        "signal": "Matrix / vector operations",
        "tool": "geometry.matrix_multiply / geometry.matrix_inverse / geometry.vector_dot etc.",
        "reason": "numpy-based numerical computation",
    },
    {
        "signal": "Unit conversion request",
        "tool": "units.convert / units.temperature",
        "reason": "pint library unit system",
    },
    {
        "signal": "Currency conversion request",
        "tool": "units.fx_convert / units.fx_triangulate",
        "reason": "Triangulation support",
    },
    {
        "signal": "Multiple scenario comparison",
        "tool": "core.batch",
        "reason": "Reduce round-trips — N independent operations in parallel",
    },
    {
        "signal": "Previous result fed into next calculation",
        "tool": "core.pipeline",
        "reason": "Determinism chain guarantee — prevents manual relay errors",
    },
    {
        "signal": '"bond yield", "duration"',
        "tool": "finance.bond_ytm / finance.bond_duration",
        "reason": "Macaulay vs Modified Duration distinction",
    },
    {
        "signal": '"option price", "Greeks", "Black-Scholes"',
        "tool": "finance.black_scholes",
        "reason": "mpmath high-precision computation",
    },
    {
        "signal": '"tax law amendment", "official notice", "gazette", "rate change"',
        "tool": "sootool.policy_propose / sootool.policy_activate",
        "reason": "Policy YAML update workflow — validate → propose → activate sequence",
    },
    {
        "signal": '"policy rollback", "previous rate", "revert policy"',
        "tool": "sootool.policy_rollback",
        "reason": "Remove override and restore package default — audit log auto-recorded",
    },
]


def get_triggers(locale: str = "ko") -> list[dict[str, Any]]:
    """Return trigger table for the given locale."""
    if locale == "en":
        return _TRIGGERS_EN
    return _TRIGGERS_KO
