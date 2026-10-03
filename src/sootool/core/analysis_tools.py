"""분석 도구: 역산(core.solve_for), 시나리오 비교(core.compare), 설명(core.explain).

세 도구 모두 다른 읽기 전용 도구를 이름으로 실행해 결과를 가공하며, 가공은 결정적 Decimal 연산과
문자열 조립뿐이다. 하위 호출 결과의 ``_meta`` 는 호출 이력에 따라 달라지므로 결과에서 뺀다. 하위 도구가 계산한
수치는 바꾸지 않는다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, TypedDict

from sootool.core.audit import CalcTrace
from sootool.core.catalog import bind_call_arguments, resolve_tool
from sootool.core.decimal_ops import D
from sootool.core.engines import FLOAT64, engine_of
from sootool.core.errors import InvalidInputError
from sootool.core.limits import ensure_max
from sootool.core.receipts import NON_REPLAYABLE_TOOLS
from sootool.core.registry import REGISTRY, ToolEntry
from sootool.core.result_types import Citation, TracedResult
from sootool.core.solver import bisect

_ANALYSIS_TOOLS = frozenset({"core.solve_for", "core.compare", "core.explain"})
_FORBIDDEN_TARGETS = NON_REPLAYABLE_TOOLS | _ANALYSIS_TOOLS
_VALUE_PREVIEW_CHARS = 300


def _target_entry(tool: str) -> ToolEntry:
    entry = resolve_tool(REGISTRY, tool)
    if entry.full_name in _FORBIDDEN_TARGETS or not entry.read_only:
        raise InvalidInputError(f"{entry.full_name} 은(는) 분석 도구의 대상 도구로 쓸 수 없습니다.")
    return entry


def _run(entry: ToolEntry, arguments: dict[str, Any]) -> dict[str, Any]:
    """대상 도구를 실행하고 ``_meta`` 를 뺀 결과를 반환한다."""
    kwargs = bind_call_arguments(entry, arguments)
    result = REGISTRY.invoke_read_only(entry.full_name, **kwargs)
    if not isinstance(result, dict):
        raise InvalidInputError(f"{entry.full_name} 은(는) 분석 도구가 읽을 수 있는 결과를 내지 않습니다.")
    return {k: v for k, v in result.items() if k != "_meta"}


def _extract(result: dict[str, Any], path: str) -> Any:
    """``a.b.0.c`` 형태의 경로로 결과 안의 값을 읽는다."""
    node: Any = result
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            available = sorted(result) if isinstance(result, dict) else []
            raise InvalidInputError(
                f"필드 {path!r} 를 결과에서 찾을 수 없습니다. 최상위 필드: {available}"
            )
    return node


def _number(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise InvalidInputError(f"{label} 은(는) 숫자 값이 아닙니다: {value!r}")
    if isinstance(value, (int, str, Decimal)):
        return D(value)
    raise InvalidInputError(f"{label} 은(는) 숫자 값이 아닙니다: {value!r}")


def _plain(value: Decimal) -> str:
    """지수 표기 없이 Decimal 을 문자열로 만든다."""
    return format(value.normalize(), "f") if value != 0 else "0"


# ---------------------------------------------------------------------------
# core.solve_for
# ---------------------------------------------------------------------------

class SolveBracket(TypedDict):
    lower: str
    upper: str


class SolveForResult(TracedResult):
    solution:    str
    achieved:    str
    residual:    str
    converged:   bool
    iterations:  int
    evaluations: int
    bracket:     SolveBracket
    at_solution: dict[str, Any]


@REGISTRY.tool(
    namespace="core",
    name="solve_for",
    description=(
        "역산: 읽기 전용 도구 tool 의 결과 필드 target_field 가 target 이 되도록 숫자 문자열 입력 variable 을 "
        "[lower, upper] 에서 이분법(Decimal)으로 찾는다. 예: 세후 월급에서 세전 월급 구하기. "
        "구간 양 끝의 함수값 부호가 달라야 하며 단계별 함수는 가장 가까운 해와 residual 을 반환한다. "
        "잔차가 tolerance(기본 0.5) 이내면 converged 가 true 이고 max_iter(기본 100)는 최대 200이다."
    ),
    version="1.0.0",
)
def solve_for(
    tool:         str,
    arguments:    dict[str, Any],
    variable:     str,
    target_field: str,
    target:       str,
    lower:        str,
    upper:        str,
    tolerance:    str  = "0.5",
    max_iter:     int  = 100,
    integer:      bool = False,
) -> SolveForResult:
    trace = CalcTrace(
        tool="core.solve_for",
        formula="find x in [lower, upper] such that tool(variable=x)[target_field] = target (bisection)",
    )
    entry = _target_entry(tool)
    ensure_max("SOLVER_EVALUATIONS", max_iter, "max_iter")
    if max_iter < 1:
        raise InvalidInputError("max_iter 는 1 이상이어야 합니다.")
    if variable not in entry.exposed_signature().parameters:
        raise InvalidInputError(f"{entry.full_name} 에 파라미터 {variable!r} 가 없습니다.")

    target_d    = _number(target, "target")
    lower_d     = _number(lower, "lower")
    upper_d     = _number(upper, "upper")
    tolerance_d = abs(_number(tolerance, "tolerance"))

    def evaluate(x: Decimal) -> Decimal:
        value = _extract(_run(entry, {**arguments, variable: _plain(x)}), target_field)
        return _number(value, f"{target_field} 값") - target_d

    result = bisect(evaluate, lower_d, upper_d, tolerance=tolerance_d, max_iter=max_iter, integer=integer)
    solution = _plain(result.x)
    at_solution = _run(entry, {**arguments, variable: solution})
    achieved = _number(_extract(at_solution, target_field), f"{target_field} 값")

    trace.input("tool", entry.full_name)
    trace.input("variable", variable)
    trace.input("target_field", target_field)
    trace.input("target", target)
    trace.input("bracket", [lower, upper])
    trace.input("integer", integer)
    for step in result.steps:
        trace.step("iteration", {"n": step.iteration, "x": _plain(step.x), "f": _plain(step.value)})
    trace.output(solution)

    return {
        "solution":    solution,
        "achieved":    _plain(achieved),
        "residual":    _plain(result.value),
        "converged":   result.converged,
        "iterations":  result.iterations,
        "evaluations": result.evaluations,
        "bracket":     {"lower": _plain(result.lower), "upper": _plain(result.upper)},
        "at_solution": at_solution,
        "trace":       trace.to_dict(),
    }


# ---------------------------------------------------------------------------
# core.compare
# ---------------------------------------------------------------------------

class CompareRow(TypedDict):
    name:              str
    arguments:         dict[str, Any]
    values:            dict[str, Any]
    delta_vs_baseline: dict[str, str | None]


class CompareResult(TracedResult):
    tool:      str
    baseline:  dict[str, Any]
    scenarios: list[CompareRow]


@REGISTRY.tool(
    namespace="core",
    name="compare",
    description=(
        "시나리오 비교: 읽기 전용 도구 tool 을 base_arguments 로 실행한 기준안과, 각 시나리오의 arguments 로 덮어쓴 "
        "실행을 비교한다. fields 는 결과에서 비교할 필드 경로 목록(예: tax, breakdown.0.rate). 숫자 필드는 기준안 대비 "
        "차이(delta_vs_baseline)를, 숫자가 아닌 필드는 null 을 반환한다. 시나리오는 이름이 겹치지 않게 최대 50개까지 받는다."
    ),
    version="1.0.0",
)
def compare(
    tool:           str,
    base_arguments: dict[str, Any],
    scenarios:      list[dict[str, Any]],
    fields:         list[str],
) -> CompareResult:
    trace = CalcTrace(tool="core.compare", formula="values(scenario) and values(scenario) - values(baseline)")
    entry = _target_entry(tool)
    ensure_max("SCENARIOS", len(scenarios), "scenarios")
    if not scenarios:
        raise InvalidInputError("scenarios 는 비어 있지 않은 목록이어야 합니다.")
    if not fields:
        raise InvalidInputError("fields 는 비어 있지 않은 목록이어야 합니다.")

    def values_of(arguments: dict[str, Any]) -> dict[str, Any]:
        result = _run(entry, arguments)
        return {path: _extract(result, path) for path in fields}

    baseline = values_of(base_arguments)

    rows: list[CompareRow] = []
    names: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict) or not isinstance(scenario.get("name"), str) or not scenario["name"]:
            raise InvalidInputError(f"scenarios[{index}] 에는 비어 있지 않은 name 이 필요합니다.")
        if scenario["name"] in names:
            raise InvalidInputError(f"시나리오 이름이 중복됩니다: {scenario['name']!r}")
        names.add(scenario["name"])
        overrides = scenario.get("arguments", {})
        if not isinstance(overrides, dict):
            raise InvalidInputError(f"scenarios[{index}].arguments 는 객체여야 합니다.")
        values = values_of({**base_arguments, **overrides})
        delta: dict[str, str | None] = {}
        for path, value in values.items():
            try:
                delta[path] = _plain(_number(value, path) - _number(baseline[path], path))
            except InvalidInputError:
                delta[path] = None
        rows.append({"name": scenario["name"], "arguments": overrides, "values": values, "delta_vs_baseline": delta})

    trace.input("tool", entry.full_name)
    trace.input("fields", fields)
    trace.input("scenario_count", len(scenarios))
    trace.output({"baseline": baseline, "scenarios": [r["name"] for r in rows]})
    return {"tool": entry.full_name, "baseline": baseline, "scenarios": rows, "trace": trace.to_dict()}


# ---------------------------------------------------------------------------
# core.explain
# ---------------------------------------------------------------------------

_LABELS: dict[str, dict[str, Any]] = {
    "ko": {
        "tool": "도구", "formula": "수식", "inputs": "입력", "steps": "계산 단계", "output": "결과",
        "policy": "적용 정책", "current": "현재", "citation": "근거", "engine_float": "참고: 이 도구는 배정밀도(float64) 근사 결과를 냅니다.",
        "status": {"enacted": "확정", "proposed": "개정안(확정 전)", "superseded": "교체된 이전 버전"},
        "period": "시행",
    },
    "en": {
        "tool": "Tool", "formula": "Formula", "inputs": "Inputs", "steps": "Steps", "output": "Result",
        "policy": "Policy", "current": "present", "citation": "Basis", "engine_float": "Note: this tool returns IEEE 754 double precision approximations.",
        "status": {"enacted": "enacted", "proposed": "proposed (not enacted)", "superseded": "superseded version"},
        "period": "effective",
    },
}


def _preview(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    return text if len(text) <= _VALUE_PREVIEW_CHARS else text[: _VALUE_PREVIEW_CHARS - 1] + "…"


class Explanation(TypedDict):
    summary:   str
    lines:     list[str]
    citations: list[Citation]


class ExplainResult(TracedResult):
    summary:   str
    lines:     list[str]
    citations: list[Citation]
    result:    dict[str, Any]
    lang:      str


def render_explanation(tool: str, response: dict[str, Any], engine: str, lang: str) -> Explanation:
    """응답의 trace 와 정책 메타데이터를 평문 설명으로 직렬화한다. 수치는 바꾸지 않는다."""
    text      = _LABELS[lang]
    raw_trace = response.get("trace")
    trace: dict[str, Any] = raw_trace if isinstance(raw_trace, dict) else {}
    lines     = [f"{text['tool']}: {tool}"]
    if trace.get("formula"):
        lines.append(f"{text['formula']}: {trace['formula']}")
    if trace.get("inputs"):
        lines.append(f"{text['inputs']}:")
        lines.extend(f"  {key} = {_preview(value)}" for key, value in trace["inputs"].items())
    if trace.get("steps"):
        lines.append(f"{text['steps']}:")
        lines.extend(
            f"  {index}. {step.get('label', '')}: {_preview(step.get('value'))}"
            for index, step in enumerate(trace["steps"], start=1)
        )
    if "output" in trace:
        lines.append(f"{text['output']}: {_preview(trace['output'])}")

    citations: list[Citation] = []
    status = response.get("policy_status")
    if status:
        end = response.get("policy_effective_to") or text["current"]
        lines.append(
            f"{text['policy']}: {text['status'].get(status, status)}, "
            f"{text['period']} {response.get('policy_effective_date', '')}~{end}"
        )
        citations = list(response.get("policy_citations") or [])
        for citation in citations:
            parts = [str(citation.get("law", "")), str(citation.get("article", ""))]
            url   = f" ({citation['url']})" if citation.get("url") else ""
            lines.append(f"{text['citation']}: {' '.join(p for p in parts if p)}{url}")
    if engine == FLOAT64:
        lines.append(text["engine_float"])
    return {"summary": "\n".join(lines), "lines": lines, "citations": citations}


@REGISTRY.tool(
    namespace="core",
    name="explain",
    description=(
        "설명 모드: 읽기 전용 도구 tool 을 arguments 로 실행하고, 수식, 입력, 계산 단계, 결과, 적용 정책(상태, 시행 기간)과 "
        "근거 조문을 평문(lang: ko 또는 en)으로 풀어 반환한다. 수치는 도구 결과 그대로이며 설명은 trace 를 서술할 뿐이다. "
        "긴 값은 300자에서 줄여 보이고 원본은 result 에 있다."
    ),
    version="1.0.0",
)
def explain(tool: str, arguments: dict[str, Any], lang: str = "ko") -> ExplainResult:
    trace = CalcTrace(tool="core.explain", formula="render(trace(tool(arguments)))")
    if lang not in _LABELS:
        raise InvalidInputError(f"lang 은 {sorted(_LABELS)} 중 하나여야 합니다: {lang!r}")
    entry    = _target_entry(tool)
    response = _run(entry, arguments)
    rendered = render_explanation(entry.full_name, response, engine_of(entry), lang)

    trace.input("tool", entry.full_name)
    trace.input("lang", lang)
    trace.output(rendered["summary"])
    return {
        "summary":   rendered["summary"],
        "lines":     rendered["lines"],
        "citations": rendered["citations"],
        "result":    response,
        "lang":      lang,
        "trace":     trace.to_dict(),
    }
