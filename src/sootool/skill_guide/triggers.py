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
    {
        "signal": '"음력", "설날", "추석", "절기", "24절기" 포함',
        "tool": "datetime.solar_to_lunar / datetime.lunar_to_solar / datetime.lunar_holiday / datetime.solar_terms",
        "reason": "KASI 조견표 기반 음력↔양력 정밀 변환 — 연도별 윤달 자동 반영",
    },
    {
        "signal": '"회계연도", "fiscal year", "과세기간", "월급 정산일" 포함',
        "tool": "datetime.fiscal_year / datetime.fiscal_quarter / datetime.tax_period_kr / datetime.payroll_period",
        "reason": "국가별 FY 경계 (KR/US/JP/UK) + 급여/과세 기간 정확 계산",
    },
    {
        "signal": '"수치적분", "simpson", "가우스", "스플라인", "푸리에" 포함',
        "tool": "math.integrate_simpson / math.integrate_gauss_legendre / math.interpolate_* / math.fft",
        "reason": "core.calc 안전 AST + mpmath/numpy 수치해석 - LLM 직접 적분 오류 방지",
    },
    {
        "signal": '"CHA2DS2-VASc", "HAS-BLED", "Framingham", "QT 보정" 포함',
        "tool": "medical.cha2ds2_vasc / medical.has_bled / medical.framingham_cvd_10y / medical.qtc_*",
        "reason": "임상 결정 지원 - 공인 점수표 및 보정식 (Bazett/Fridericia/Framingham/Hodges)",
    },
    {
        "signal": '"Nernst", "전기분해", "패러데이", "스넬", "브래그", "렌즈" 포함',
        "tool": "science.nernst / science.faraday_electrolysis / science.snell_law / science.bragg / science.thin_lens",
        "reason": "물리·화학 공식 Decimal 경계 계산 — 삼각/로그는 mpmath",
    },
    {
        "signal": '"에너지 단위", "압력 단위", "MB/MiB", "ms/us/ns" 포함',
        "tool": "units.energy_convert / units.pressure_convert / units.data_size_convert / units.time_small_convert",
        "reason": "단위 전용 변환 테이블 (J/cal/eV, Pa/atm/psi, SI/IEC, ms~ps)",
    },
    {
        "signal": '"Earned Schedule", "SPI(t)", "일정 몬테카를로" 포함',
        "tool": "pm.earned_schedule / pm.monte_carlo_schedule",
        "reason": "시간 기반 일정 성과 지표 + PERT-Beta 몬테카를로 (결정론 seed)",
    },
    {
        "signal": '"확장 유클리드", "CRT", "중국인의 나머지", "오일러 phi", "카마이클" 포함',
        "tool": "crypto.egcd / crypto.crt / crypto.euler_totient / crypto.carmichael_lambda",
        "reason": "정수 이론 정확 계산 (암호·모듈러 필수 빌딩블록)",
    },
    {
        "signal": '"월급", "실수령", "4대보험", "급여명세", "세후 월급" 포함',
        "tool": "payroll.kr_salary",
        "reason": "4대보험(국민연금·건강·장기요양·고용)과 간이 소득세를 연도별 정책 YAML 기반으로 일괄 공제 — LLM 수치 계산 금지",
    },
    {
        "signal": '"저항", "옴의 법칙", "레이놀즈수", "SI 접두사", "병렬 저항" 포함',
        "tool": "engineering.electrical_ohm / engineering.resistor_parallel / engineering.fluid_reynolds / engineering.si_prefix_convert",
        "reason": "공학 결정론 공식 — 단위·유효숫자 보존, LLM 암산 대체",
    },
    {
        "signal": '"DSR", "DTI", "LTV", "주담대 한도", "전세자금대출" 포함',
        "tool": "realestate.kr_dsr / realestate.kr_dti / realestate.kr_ltv",
        "reason": "감독규정 고시 기반 한도 계산 — 연도별 YAML 정책 고정",
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
    {
        "signal": '"lunar", "Seollal", "Chuseok", "solar term", "24 solar terms"',
        "tool": "datetime.solar_to_lunar / datetime.lunar_to_solar / datetime.lunar_holiday / datetime.solar_terms",
        "reason": "KASI-aligned lunar↔solar conversions with leap-month awareness",
    },
    {
        "signal": '"fiscal year", "quarter boundary", "tax period", "payroll period"',
        "tool": "datetime.fiscal_year / datetime.fiscal_quarter / datetime.tax_period_kr / datetime.payroll_period",
        "reason": "Country-specific FY boundaries (KR/US/JP/UK) + payroll/tax windows",
    },
    {
        "signal": '"numerical integration", "Simpson", "Gauss-Legendre", "spline", "FFT"',
        "tool": "math.integrate_simpson / math.integrate_gauss_legendre / math.interpolate_* / math.fft",
        "reason": "core.calc safe AST + mpmath/numpy numerical analysis — avoid LLM integration errors",
    },
    {
        "signal": '"CHA2DS2-VASc", "HAS-BLED", "Framingham", "QT correction"',
        "tool": "medical.cha2ds2_vasc / medical.has_bled / medical.framingham_cvd_10y / medical.qtc_*",
        "reason": "Clinical decision support - validated scores and correction formulas",
    },
    {
        "signal": '"Nernst", "electrolysis", "Faraday", "Snell", "Bragg", "lens"',
        "tool": "science.nernst / science.faraday_electrolysis / science.snell_law / science.bragg / science.thin_lens",
        "reason": "Physics/chemistry formulas with Decimal boundary and mpmath transcendentals",
    },
    {
        "signal": '"energy units", "pressure units", "MB/MiB", "ms/us/ns"',
        "tool": "units.energy_convert / units.pressure_convert / units.data_size_convert / units.time_small_convert",
        "reason": "Domain-specific conversion tables (J/cal/eV, Pa/atm/psi, SI/IEC, ms~ps)",
    },
    {
        "signal": '"Earned Schedule", "SPI(t)", "schedule Monte Carlo"',
        "tool": "pm.earned_schedule / pm.monte_carlo_schedule",
        "reason": "Time-based schedule metrics + deterministic PERT-Beta Monte Carlo",
    },
    {
        "signal": '"extended Euclidean", "CRT", "Chinese Remainder", "Euler totient", "Carmichael"',
        "tool": "crypto.egcd / crypto.crt / crypto.euler_totient / crypto.carmichael_lambda",
        "reason": "Exact integer number theory (cryptographic building blocks)",
    },
    {
        "signal": '"monthly salary", "net pay", "Korean 4 insurances", "payroll", "take-home"',
        "tool": "payroll.kr_salary",
        "reason": "Applies per-year 4-insurance YAML (pension, health, LTC, employment) plus simplified income tax — never compute by hand",
    },
    {
        "signal": '"resistor", "Ohm\'s law", "Reynolds number", "SI prefix", "parallel resistor"',
        "tool": "engineering.electrical_ohm / engineering.resistor_parallel / engineering.fluid_reynolds / engineering.si_prefix_convert",
        "reason": "Deterministic engineering formulas with unit and significant-figure preservation",
    },
    {
        "signal": '"DSR", "DTI", "LTV", "mortgage cap", "loan-to-value"',
        "tool": "realestate.kr_dsr / realestate.kr_dti / realestate.kr_ltv",
        "reason": "Regulatory-notice-based limits pinned to per-year YAML policies",
    },
]


def get_triggers(locale: str = "ko") -> list[dict[str, Any]]:
    """Return trigger table for the given locale."""
    if locale == "en":
        return _TRIGGERS_EN
    return _TRIGGERS_KO
