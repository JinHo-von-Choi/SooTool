"""플레이북 예시가 실제로 실행되는지 검증한다.

모든 플레이북(한국어, 영어)에 대해 (1) 단계의 도구가 등록되어 있고 인자 이름이 도구 시그니처에 있는지,
(2) 정책 관리를 제외한 플레이북은 자리표시자에 표본 값을 채워 ``core.pipeline`` 으로 끝까지 실행되는지 확인한다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import copy
import inspect
import json
import re
from typing import Any

import pytest

from sootool import server
from sootool.core.registry import REGISTRY
from sootool.skill_guide.examples import get_examples
from sootool.skill_guide.playbooks import get_playbooks

_SAMPLE: dict[str, Any] = {
    # 급여
    "월급": "3000000", "monthly": "3000000", "gross": "3000000", "연도": 2026, "year": 2026,
    "식대": "200000", "meal": "200000",
    # 부가세
    "금액1": "11000", "금액2": "22000", "amount1": "11000", "amount2": "22000",
    # 대출
    "원금": "100000000", "principal": "100000000",
    "이자율A": "0.04", "이자율B": "0.05", "이자율C": "0.06", "rate_a": "0.04", "rate_b": "0.05", "rate_c": "0.06",
    "기간": 12, "term": 12, "n": 10,
    # NPV, 채권
    "r": "0.05", "현금흐름": ["-1000", "300", "400", "500"], "cashflows": ["-1000", "300", "400", "500"],
    "액면가": "1000", "face": "1000", "시장가": "950", "price": "950", "쿠폰율": "0.05", "coupon": "0.05",
    "이자지급횟수": 2, "freq": 2,
    # 통계
    "A그룹 데이터": ["1", "2", "3", "4", "5"], "data_a": ["1", "2", "3", "4", "5"],
    "B그룹 데이터": ["2", "3", "4", "5", "7"], "data_b": ["2", "3", "4", "5", "7"],
    # 의료
    "체중": "70", "kg": "70", "mg/kg": "5", "상한": "400", "ceiling": "400",
    "QT ms": "400", "RR ms": "800", "나이": 70, "age": 70, "bool": True,
    # 수학
    "f(t) 표현식": "100*exp(-0.05*t)", "f(t) expression": "100*exp(-0.05*t)", "T": "10",
    "할인율": "0.05", "rate": "0.05",
    "샘플링된 현금흐름 리스트": ["100", "95", "90", "86"], "sampled cash flows": ["100", "95", "90", "86"],
    # 전기
    "V": "12", "R": "6", "R1": "10", "R2": "20", "R3": "30",
}
_PLACEHOLDER = re.compile(r"<([^<>]+)>")
_POLICY_TOOL_PREFIX = "sootool.policy_"


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def _all_playbooks() -> list[tuple[str, dict[str, Any]]]:
    return [(f"{loc}:{pb['id']}", pb) for loc in ("ko", "en") for pb in get_playbooks(loc)]


def _fill(node: Any) -> Any:
    if isinstance(node, str):
        match = _PLACEHOLDER.fullmatch(node)
        if match:
            key = match.group(1)
            assert key in _SAMPLE, f"표본 값이 없는 자리표시자: <{key}>"
            return copy.deepcopy(_SAMPLE[key])
        return _PLACEHOLDER.sub(lambda m: str(_SAMPLE[m.group(1)]), node)
    if isinstance(node, dict):
        return {k: _fill(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v) for v in node]
    return node


def _tool_calls(step: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    calls = [(step["tool"], step.get("args", {}))]
    if step["tool"] == "core.batch":
        for item in step["args"].get("items", []):
            calls.append((item["tool"], item.get("args", {})))
    return calls


@pytest.mark.parametrize(("name", "playbook"), _all_playbooks(), ids=[n for n, _ in _all_playbooks()])
def test_playbook_steps_use_registered_tools_and_declared_arguments(name, playbook):
    entries = {e.full_name: e for e in REGISTRY.list()}
    for step in playbook["steps"]:
        for tool, args in _tool_calls(step):
            assert tool in entries, f"{name}: 등록되지 않은 도구 {tool}"
            declared = set(entries[tool].exposed_signature().parameters)
            unknown = sorted(set(args) - declared)
            assert not unknown, f"{name}: {tool} 에 없는 인자 {unknown}"
            required = {
                p.name for p in entries[tool].exposed_signature().parameters.values()
                if p.default is inspect.Parameter.empty
            }
            missing = sorted(required - set(args))
            assert not missing, f"{name}: {tool} 필수 인자 누락 {missing}"


@pytest.mark.parametrize(
    ("name", "playbook"),
    [(n, p) for n, p in _all_playbooks() if not any(s["tool"].startswith(_POLICY_TOOL_PREFIX) for s in p["steps"])],
    ids=[n for n, p in _all_playbooks() if not any(s["tool"].startswith(_POLICY_TOOL_PREFIX) for s in p["steps"])],
)
def test_playbook_runs_end_to_end(name, playbook):
    steps  = _fill(playbook["steps"])
    result = REGISTRY.invoke("core.pipeline", steps=steps)
    failed = {
        step_id: info.get("error")
        for step_id, info in result["steps"].items()
        if info["status"] != "ok"
    }
    assert result["status"] == "ok", f"{name}: {json.dumps(failed, ensure_ascii=False, default=str)[:600]}"


def _all_examples() -> list[tuple[str, dict[str, Any]]]:
    return [(f"{loc}:{i}:{ex['tool_call']['tool']}", ex) for loc in ("ko", "en") for i, ex in enumerate(get_examples(loc))]


_NUMERIC = re.compile(r"-?\d+(\.\d+)?")


@pytest.mark.parametrize(("name", "example"), _all_examples(), ids=[n for n, _ in _all_examples()])
def test_example_tool_call_runs_and_matches_its_expected_numbers(name, example):
    call   = example["tool_call"]
    entry  = {e.full_name: e for e in REGISTRY.list()}[call["tool"]]
    unknown = sorted(set(call["args"]) - set(entry.exposed_signature().parameters))
    assert not unknown, f"{name}: 도구에 없는 인자 {unknown}"
    result = REGISTRY.invoke(call["tool"], **call["args"])
    if call["tool"] == "core.pipeline":
        assert result["status"] == "ok", f"{name}: {json.dumps(result['steps'], ensure_ascii=False, default=str)[:500]}"
    if call["tool"] == "core.batch":
        failed = [item for item in result["results"] if item["status"] != "ok"]
        assert not failed, f"{name}: {json.dumps(failed, ensure_ascii=False, default=str)[:500]}"
    for key, expected in example.get("expected_output", {}).items():
        if isinstance(expected, str) and _NUMERIC.fullmatch(expected):
            assert str(result[key]) == expected, f"{name}: {key} 기대 {expected}, 실제 {result[key]}"
