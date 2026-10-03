"""한국 세무·노무 공식 계산 예시 재현 시험.

kr_official_examples.yaml 의 각 시나리오를 REGISTRY.invoke 로 실행하고, 지정한 출력 필드를
공식 출처(국세청, 국가법령정보센터, 행정안전부, 고용노동부 등)에 실린 계산 결과와 비교한다.
시나리오 하나가 pytest 케이스 하나이며, 통과 수를 전체 수로 나눈 값이 재현율이다.

기대값은 출처에 적힌 숫자 그대로이고, 출처의 기준 연도와 도구에 넘기는 year 가 같아야 한다.
현행과 다른 가정(옛 세율, 정책이 없는 연도)의 예시는 excluded 절에 사유와 함께 둔다.

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pytest
import yaml

import sootool.modules.payroll  # noqa: F401
import sootool.modules.realestate  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.registry import REGISTRY

_DATA_PATH = Path(__file__).with_name("kr_official_examples.yaml")
_DATA: dict[str, Any] = yaml.safe_load(_DATA_PATH.read_text(encoding="utf-8"))
_SCENARIOS: list[dict[str, Any]] = _DATA["scenarios"]
_EXCLUDED: list[dict[str, Any]] = _DATA.get("excluded") or []

_MIN_SCENARIOS = 40
_SOURCE_KEYS = ("title", "url", "base_year", "quote")


def _resolve(result: Any, path: str) -> Any:
    """점(.)으로 구분한 경로를 따라 결과 dict 의 값을 꺼낸다. 정수 조각은 리스트 색인으로 본다."""
    node = result
    for part in path.split("."):
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict):
            if part not in node:
                raise KeyError(f"출력에 '{path}' 경로가 없습니다(멈춘 조각: {part})")
            node = node[part]
        else:
            raise KeyError(f"'{path}' 경로의 '{part}' 앞 값이 dict 나 list 가 아닙니다")
    return node


def _as_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _matches(actual: Any, expected: Any, display_unit: Decimal | None) -> bool:
    """숫자는 Decimal 값으로, 그 밖의 값은 그대로 비교한다.

    출처가 금액을 표시 단위(예: 0.1만원)로만 적은 시나리오는 display_unit 을 두고,
    실제값이 기대값에서 그 단위 미만으로 떨어져 있으면 같은 값으로 본다.
    """
    if isinstance(expected, bool) or expected is None:
        return actual is expected
    expected_dec = _as_decimal(expected)
    actual_dec = _as_decimal(actual)
    if expected_dec is not None and actual_dec is not None:
        if display_unit is not None:
            return abs(actual_dec - expected_dec) < display_unit
        return actual_dec == expected_dec
    return bool(actual == expected)


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[s["id"] for s in _SCENARIOS])
def test_official_example(scenario: dict[str, Any]) -> None:
    result = REGISTRY.invoke(scenario["tool"], **scenario["inputs"])
    unit = scenario.get("display_unit")
    display_unit = Decimal(str(unit)) if unit is not None else None

    mismatches: list[str] = []
    for path, expected in scenario["expected"].items():
        actual = _resolve(result, path)
        if not _matches(actual, expected, display_unit):
            mismatches.append(f"{path}: 기대 {expected!r}, 실제 {actual!r}")

    assert not mismatches, (
        f"[{scenario['area']}] {scenario['tool']} 공식 예시와 다릅니다 "
        f"({scenario['source']['url']}):\n  " + "\n  ".join(mismatches)
    )


class TestScenarioSetIntegrity:
    """시나리오 세트 자체의 형식 검사. 도구를 호출하지 않는다."""

    def test_minimum_scenario_count(self) -> None:
        assert len(_SCENARIOS) >= _MIN_SCENARIOS

    def test_ids_unique_across_sections(self) -> None:
        ids = [s["id"] for s in _SCENARIOS] + [e["id"] for e in _EXCLUDED]
        assert len(ids) == len(set(ids))

    def test_every_scenario_cites_official_source(self) -> None:
        for s in _SCENARIOS:
            source = s["source"]
            missing = [k for k in _SOURCE_KEYS if not source.get(k)]
            assert not missing, f"{s['id']}: source 누락 {missing}"
            assert str(source["url"]).startswith("https://"), s["id"]
            assert s["expected"], f"{s['id']}: expected 가 비었습니다"

    def test_tool_year_matches_source_year(self) -> None:
        for s in _SCENARIOS:
            year = s["inputs"].get("year")
            if year is not None:
                assert year == s["source"]["base_year"], s["id"]

    def test_tools_are_registered(self) -> None:
        for s in _SCENARIOS:
            assert s["tool"] in REGISTRY._tools, s["id"]

    def test_excluded_entries_state_reason_and_source(self) -> None:
        for e in _EXCLUDED:
            assert e.get("reason"), e["id"]
            assert str(e["source"]["url"]).startswith("https://"), e["id"]
            assert e["source"].get("base_year"), e["id"]
