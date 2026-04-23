"""bench/cases.yaml 구조·기대값 검증 (FB-M3).

작성자: 최진호
작성일: 2026-04-24

이 테스트는 LLM API 를 호출하지 않는다. CI 에서 결정론적으로 실행 가능한
항목만 검증한다.

- cases.yaml 을 yaml.safe_load 로 파싱 가능해야 한다.
- cases 길이는 정확히 20 이어야 하며 id 는 unique 해야 한다.
- 각 케이스는 필수 필드(id, prompt, tool_call, expected_decimal_string,
  category, difficulty)를 보유한다.
- tool_call.tool 은 REGISTRY 에 등록된 tool 이어야 한다.
- expected_decimal_string 은 Decimal 로 파싱 가능해야 한다.
- REGISTRY.invoke 결과의 해당 field 가 expected_decimal_string 과 일치해야 한다
  (SooTool Decimal ground truth invariant).
- 카테고리 분포는 플랜(FB-M3) 명세와 일치한다:
  한국 소득세 8, 부가세 3, 복리 2, 확률 2 + 통계 1 = 3, 공학 2, 양도세 2 = 20.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from sootool.core.registry import REGISTRY
from sootool.server import _load_modules


_CASES_PATH = Path(__file__).resolve().parents[2] / "bench" / "cases.yaml"

_REQUIRED_FIELDS = (
    "id",
    "prompt",
    "tool_call",
    "expected_decimal_string",
    "category",
    "difficulty",
)

_EXPECTED_CATEGORY_COUNTS = {
    "tax_korea":         8,
    "vat":               3,
    "finance_compound":  2,
    "probability":       2,
    "stats":             1,
    "engineering_ac":    2,
    "tax_korea_capgain": 2,
}


@pytest.fixture(scope="module")
def cases_doc() -> dict:
    _load_modules()
    return yaml.safe_load(_CASES_PATH.read_text(encoding="utf-8"))


def test_cases_yaml_loads(cases_doc: dict) -> None:
    """yaml.safe_load 성공 + 최상위 cases 키 존재."""
    assert isinstance(cases_doc, dict)
    assert "cases" in cases_doc
    assert isinstance(cases_doc["cases"], list)


def test_cases_count_is_twenty(cases_doc: dict) -> None:
    assert len(cases_doc["cases"]) == 20


def test_cases_ids_unique(cases_doc: dict) -> None:
    ids = [c["id"] for c in cases_doc["cases"]]
    assert len(ids) == len(set(ids)), f"중복 id 존재: {ids}"


def test_cases_required_fields(cases_doc: dict) -> None:
    for c in cases_doc["cases"]:
        for f in _REQUIRED_FIELDS:
            assert f in c, f"case {c.get('id')}: 필수 필드 누락 {f!r}"
        tc = c["tool_call"]
        for f in ("tool", "args", "field"):
            assert f in tc, f"case {c['id']}: tool_call.{f} 누락"


def test_expected_decimal_parses(cases_doc: dict) -> None:
    for c in cases_doc["cases"]:
        Decimal(c["expected_decimal_string"])  # raises InvalidOperation if bad


def test_tool_registered(cases_doc: dict) -> None:
    registered = {e.full_name for e in REGISTRY.list()}
    for c in cases_doc["cases"]:
        tool = c["tool_call"]["tool"]
        assert tool in registered, f"case {c['id']}: 미등록 도구 {tool}"


def test_sootool_ground_truth(cases_doc: dict) -> None:
    """REGISTRY.invoke 결과가 expected_decimal_string 과 정확히 일치."""
    mismatches: list[str] = []
    for c in cases_doc["cases"]:
        tc = c["tool_call"]
        resp = REGISTRY.invoke(tc["tool"], **tc["args"])
        actual = str(resp[tc["field"]])
        if actual != c["expected_decimal_string"]:
            mismatches.append(
                f"{c['id']}: expected={c['expected_decimal_string']!r} actual={actual!r}"
            )
    assert not mismatches, "ground truth 불일치:\n" + "\n".join(mismatches)


def test_category_distribution(cases_doc: dict) -> None:
    counts: dict[str, int] = {}
    for c in cases_doc["cases"]:
        counts[c["category"]] = counts.get(c["category"], 0) + 1
    assert counts == _EXPECTED_CATEGORY_COUNTS, (
        f"카테고리 분포 불일치: 실측={counts}"
    )


def test_difficulty_values(cases_doc: dict) -> None:
    allowed = {"easy", "medium", "hard"}
    for c in cases_doc["cases"]:
        assert c["difficulty"] in allowed, (
            f"case {c['id']}: difficulty={c['difficulty']!r} 는 허용되지 않음"
        )
