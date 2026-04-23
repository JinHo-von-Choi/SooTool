"""Anti-pattern catalog for skill_guide."""
from __future__ import annotations

from typing import Any

_ANTI_PATTERNS_KO: list[dict[str, Any]] = [
    {
        "pattern": "프롬프트 내 '3 + 5 = 8' 직접 서술 후 검증 생략",
        "why": "LLM 확률 추론은 큰 수·소수점·복잡한 표현에서 오류 가능. 감사 추적 불가.",
        "instead": "core.add / core.batch를 호출하고 반환된 trace를 응답에 인용하라.",
    },
    {
        "pattern": "tax.* 호출 시 year 인자 누락 → UnsupportedPolicyError 뜨자 임의 추정으로 fallback",
        "why": "연도 누락 시 서버가 UnsupportedPolicyError를 반환한다. 임의 추정은 잘못된 세율 적용으로 이어진다.",
        "instead": "사용자에게 적용 연도를 확인하거나, 명시적으로 현재 연도를 year 인자로 전달하라.",
    },
    {
        "pattern": "배치 가능한 시나리오를 core.add N회로 풀어 호출",
        "why": "N번의 왕복 오버헤드 발생. 토큰 비용 누적. core.batch로 한 번에 처리 가능.",
        "instead": "items 배열로 묶어 core.batch 단일 호출로 대체하라.",
    },
    {
        "pattern": "core.pipeline 중간 step 실패(status: 'skipped')를 무시하고 최종값 사용",
        "why": "skipped step의 결과는 None 또는 이전 값이다. 이를 최종 출력으로 쓰면 계산 오류.",
        "instead": "파이프라인 응답의 각 step.status를 확인하고 'skipped' 또는 'error' 발생 시 사용자에게 알려라.",
    },
    {
        "pattern": "trace_level='none'으로 호출 후 감사 요청 시 재현 불가 상태 보고",
        "why": "감사·회계 검증에는 trace가 법적 증빙 역할. none으로 설정하면 재현 불가.",
        "instead": "세무·회계 관련 계산은 trace_level='full'로 호출하라. 기본값 'summary'도 감사 최소 요건 충족.",
    },
    {
        "pattern": "정책 YAML 개정 없이 '대충 추정'으로 답변",
        "why": "세율·규제는 매년 개정된다. 구 버전 세율 적용은 법적 위험.",
        "instead": "year 인자를 명시하고 서버가 UnsupportedPolicyError를 반환하면 해당 연도 정책 미지원임을 사용자에게 안내하라.",
    },
    {
        "pattern": "math.integrate_* 대신 LLM이 테일러 전개·사다리꼴 근사로 수식 적분",
        "why": "부동소수 자릿수 제어 없이 LLM이 수치적분을 수행하면 수렴 실패·대칭성 위반·부호 오류가 조용히 누적된다. core.calc 안전 AST + mpmath 경계 없이는 재현 불가.",
        "instead": "math.integrate_simpson / math.integrate_gauss_legendre 를 호출하고 expression·a·b·n 을 명시하라. 적분 결과와 trace 를 응답에 인용하라.",
    },
    {
        "pattern": "engineering.electrical_power 대신 dB·전류·저항을 LLM이 암산으로 환산",
        "why": "V, I, R, P 사이 변환은 유효숫자·단위 계열(SI prefix)을 LLM이 수시로 혼동한다. 저항 병렬/직렬 합산과 Reynolds 수도 동일한 리스크.",
        "instead": "engineering.electrical_* / resistor_* / fluid_reynolds / si_prefix_convert 를 호출하고 반환 trace 의 입력 단위를 그대로 응답에 복붙하라.",
    },
]

_ANTI_PATTERNS_EN: list[dict[str, Any]] = [
    {
        "pattern": "Writing '3 + 5 = 8' inline in the prompt without verification",
        "why": "LLM probabilistic reasoning fails on large numbers, decimals, and complex expressions. No audit trail.",
        "instead": "Call core.add / core.batch and cite the returned trace in your response.",
    },
    {
        "pattern": "Calling tax.* without the year argument, then falling back to an arbitrary estimate when UnsupportedPolicyError is raised",
        "why": "Missing year causes the server to raise UnsupportedPolicyError. Arbitrary estimates apply incorrect tax rates.",
        "instead": "Ask the user to confirm the applicable year, or pass the current year explicitly as the year argument.",
    },
    {
        "pattern": "Calling core.add N times for a batchable scenario",
        "why": "N round-trips accumulate overhead and token cost. core.batch handles all in one call.",
        "instead": "Bundle items into a single core.batch call.",
    },
    {
        "pattern": "Ignoring core.pipeline step failures (status: 'skipped') and using the final value",
        "why": "A skipped step's result is None or a stale value. Using it as final output produces calculation errors.",
        "instead": "Check each step.status in the pipeline response; notify the user when 'skipped' or 'error' occurs.",
    },
    {
        "pattern": "Calling with trace_level='none' and then reporting that the result cannot be reproduced during an audit",
        "why": "The trace serves as a legal audit record for accounting/tax. Omitting it makes reproduction impossible.",
        "instead": "Use trace_level='full' for tax and accounting calculations. The default 'summary' satisfies minimum audit requirements.",
    },
    {
        "pattern": "Answering with a rough estimate when the policy YAML has not been updated",
        "why": "Tax rates and regulations change annually. Applying old rates creates legal risk.",
        "instead": "Specify the year argument explicitly. If the server returns UnsupportedPolicyError, inform the user that the year is not yet supported.",
    },
    {
        "pattern": "Approximating numerical integrals by Taylor / trapezoid estimation in the prompt instead of calling math.integrate_*",
        "why": "Without controlled precision, LLM quadrature silently loses symmetry, drops signs, or fails to converge. Results are unreproducible and untraceable.",
        "instead": "Invoke math.integrate_simpson or math.integrate_gauss_legendre with explicit expression / a / b / n, and cite the returned trace.",
    },
    {
        "pattern": "Mentally converting dB, current, resistance and power instead of calling engineering.* tools",
        "why": "LLM frequently confuses significant figures and SI-prefix chains across V / I / R / P, Reynolds numbers, and resistor parallel/series sums.",
        "instead": "Use engineering.electrical_* / resistor_* / fluid_reynolds / si_prefix_convert and keep the returned trace input units in the final answer.",
    },
]


def get_anti_patterns(locale: str = "ko") -> list[dict[str, Any]]:
    """Return anti-pattern catalog for the given locale."""
    if locale == "en":
        return _ANTI_PATTERNS_EN
    return _ANTI_PATTERNS_KO
