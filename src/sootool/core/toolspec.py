"""도구 메타데이터의 단일 조회 지점.

도구 정의(``ToolEntry``)와 거기서 파생되는 값(엔진, 정확도 등급, 별칭, 결과 타입 이름, 파라미터)을 한 구조로
묶는다. 검색 설명(``describe``), 문서 목록 생성, SDK 타입 선언이 같은 값을 쓰게 해 서로 어긋나지 않게 한다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Final

from sootool.core.engines import COMPOSITE, DECIMAL, FLOAT64, MPMATH, NONE, engine_of
from sootool.core.registry import ToolEntry
from sootool.core.result_types import declared_result_type
from sootool.core.tool_aliases import ALIASES

# 엔진별 정확도 등급. exact 는 Decimal 로 정확히 계산, high_precision 은 지정 자릿수(기본 50)의 임의 정밀도,
# approximate 는 float64 근사, depends_on_children 은 호출한 도구에 따르며, not_numeric 은 수치 계산이 아니다.
EXACTNESS: Final[dict[str, str]] = {
    DECIMAL:   "exact",
    MPMATH:    "high_precision",
    FLOAT64:   "approximate",
    COMPOSITE: "depends_on_children",
    NONE:      "not_numeric",
}


# 도구가 처음 들어간 버전. 표에 없는 도구는 0.1.0 부터 있었다. 새 도구를 추가할 때 이 표에 한 줄을 더한다.
BASELINE_VERSION: Final = "0.1.0"
SINCE: Final[dict[str, str]] = {
    "sootool.verify_receipt":               "0.2.0",
    "core.solve_for":                       "0.2.0",
    "core.compare":                         "0.2.0",
    "core.explain":                         "0.2.0",
    "finance.cagr":                         "0.2.0",
    "payroll.kr_gross_from_net":            "0.2.0",
    "tax_us.fica":                          "0.2.0",
    "tax.kr_eitc":                          "0.2.0",
    "tax.kr_securities_transaction":        "0.2.0",
    "tax.kr_pension_income":                "0.2.0",
    "tax.kr_vehicle_tax":                   "0.2.0",
    "tax.kr_registration_license_tax":      "0.2.0",
    "tax.kr_comprehensive_income_tax":      "0.2.0",
    "realestate.kr_subscription_score":     "0.2.0",
    "payroll.kr_overtime_pay":              "0.2.0",
    "payroll.kr_weekly_holiday_pay":        "0.2.0",
    "payroll.kr_minimum_wage_check":        "0.2.0",
    "payroll.kr_national_pension_benefit":  "0.2.0",
    "payroll.kr_health_income_premium":     "0.2.0",
}

# 비용 등급: light 는 상수 시간 계산, heavy 는 반복, 시뮬레이션, 기호 계산, 다건 실행으로 시간이 입력 크기에 따라 늘어난다.
HEAVY_TOOLS: Final = frozenset({
    "core.batch", "core.pipeline", "core.pipeline_resume", "core.solve_for", "core.compare",
    "pm.monte_carlo_schedule", "stats.bootstrap_ci", "symbolic.solve", "symbolic.diff",
    "finance.irr", "finance.bond_ytm", "finance.loan_schedule", "math.fft", "math.ifft",
    "probability.factorial", "probability.nCr", "probability.nPr", "crypto.is_prime", "crypto.modpow",
})

# 네임스페이스별 분류 태그(검색, 문서 분류용).
NAMESPACE_TAGS: Final[dict[str, tuple[str, ...]]] = {
    "accounting": ("finance", "accounting"), "core": ("arithmetic", "meta"), "crypto": ("math", "number-theory"),
    "datetime": ("date", "calendar"), "engineering": ("engineering", "science"), "finance": ("finance",),
    "geometry": ("math", "geometry"), "math": ("math", "numerical"), "medical": ("medical", "clinical"),
    "payroll": ("labor", "tax", "korea"), "pm": ("project-management",), "probability": ("statistics", "probability"),
    "realestate": ("real-estate", "tax", "korea"), "science": ("science",), "sootool": ("meta", "policy"),
    "stats": ("statistics",), "symbolic": ("math", "symbolic"), "tax": ("tax", "korea"), "tax_us": ("tax", "us"),
    "units": ("units", "conversion"),
}


@dataclass(frozen=True)
class ParameterSpec:
    name:     str
    type:     str
    required: bool
    default:  Any = None


@dataclass(frozen=True)
class ToolSpec:
    full_name:   str
    namespace:   str
    name:        str
    description: str
    version:     str
    read_only:   bool
    destructive: bool
    idempotent:  bool
    policy:      bool
    deprecated:  dict[str, Any] | None
    engine:      str
    exactness:   str
    result_type: str | None
    since:       str
    cost:        str
    tags:        tuple[str, ...]
    aliases:     tuple[str, ...]
    parameters:  tuple[ParameterSpec, ...]


def _tags(entry: ToolEntry) -> tuple[str, ...]:
    tags = list(NAMESPACE_TAGS.get(entry.namespace, ()))
    if entry.policy:
        tags.append("policy")
    if not entry.read_only:
        tags.append("admin")
    return tuple(dict.fromkeys(tags))


def tool_spec(entry: ToolEntry) -> ToolSpec:
    """도구 정의에서 모든 파생 메타데이터를 모아 반환한다."""
    engine   = engine_of(entry)
    declared = declared_result_type(entry.fn)
    parameters = tuple(
        ParameterSpec(
            name     = p.name,
            type     = "" if p.annotation is inspect.Parameter.empty else str(p.annotation),
            required = p.default is inspect.Parameter.empty,
            default  = None if p.default is inspect.Parameter.empty else p.default,
        )
        for p in entry.exposed_signature().parameters.values()
    )
    return ToolSpec(
        full_name   = entry.full_name,
        namespace   = entry.namespace,
        name        = entry.name,
        description = entry.description,
        version     = entry.version,
        read_only   = entry.read_only,
        destructive = entry.destructive,
        idempotent  = entry.idempotent,
        policy      = entry.policy,
        deprecated  = entry.deprecated,
        engine      = engine,
        exactness   = EXACTNESS[engine],
        result_type = None if declared is None else getattr(declared, "__name__", str(declared)),
        since       = SINCE.get(entry.full_name, BASELINE_VERSION),
        cost        = "heavy" if entry.full_name in HEAVY_TOOLS else "light",
        tags        = _tags(entry),
        aliases     = ALIASES.get(entry.full_name, ()),
        parameters  = parameters,
    )
