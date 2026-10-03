"""도구별 계산 엔진(정확도 등급) 분류.

도구가 정의된 모듈의 임포트를 정적으로 분석해 가장 거친 수치 엔진을 도구의 등급으로 삼는다.

- decimal: Decimal 정수·십진 산술만 사용한다. 반올림은 호출에 지정한 정책을 따른다.
- mpmath:  임의 정밀도(mpmath 작업 자릿수) 연산을 사용한다.
- float64: numpy, scipy, statsmodels 등 IEEE 754 배정밀도 연산을 거친다. 결과는 근사값이다.
- composite: 다른 도구를 실행해 결과를 묶는 도구. 각 하위 결과가 자신의 등급을 갖는다.
- none: 수치 계산 도구가 아니다(정책 관리, 가이드).

도구가 정의된 모듈의 직접 임포트로 분류하므로 모듈 안의 일부 경로만 float 을 쓰더라도 해당
모듈의 모든 도구는 float64 로 표기한다(과대 표기 쪽으로 기운 보수적 분류). 다른 모듈에 계산을
위임하는 도구는 ``_OVERRIDES`` 에 명시한다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import ast
import functools
import importlib.util
from pathlib import Path
from typing import Final

from sootool.core.registry import ToolEntry

DECIMAL: Final = "decimal"
MPMATH:  Final = "mpmath"
FLOAT64: Final = "float64"

COMPOSITE: Final = "composite"
NONE:      Final = "none"

ENGINES: Final = (DECIMAL, MPMATH, FLOAT64, COMPOSITE, NONE)

_OVERRIDES: Final = {
    "core.calc":              MPMATH,
    "core.batch":             COMPOSITE,
    "core.pipeline":          COMPOSITE,
    "core.pipeline_resume":   COMPOSITE,
    "core.solve_for":         COMPOSITE,
    "core.compare":           COMPOSITE,
    "core.explain":           COMPOSITE,
    "symbolic.solve":         MPMATH,
    "symbolic.diff":          MPMATH,
    "sootool.verify_receipt": COMPOSITE,
    "sootool.skill_guide":    NONE,
    "sootool.policy_list":     NONE,
    "sootool.policy_get":      NONE,
    "sootool.policy_history":  NONE,
    "sootool.policy_diff":     NONE,
    "sootool.policy_validate": NONE,
    "sootool.policy_propose":  NONE,
    "sootool.policy_activate": NONE,
    "sootool.policy_rollback": NONE,
    "sootool.policy_export":   NONE,
    "sootool.policy_import":   NONE,
}

_FLOAT_PACKAGES: Final = frozenset({"numpy", "scipy", "statsmodels", "numpy_financial"})
_MP_PACKAGES:    Final = frozenset({"mpmath", "sympy"})


def _root(name: str) -> str:
    return name.split(".", 1)[0]


def _imported_roots(tree: ast.AST) -> set[str]:
    """import 문과 ``lazy_module("pkg.sub")`` 호출에서 최상위 패키지 이름을 모은다."""
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(_root(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(_root(node.module))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "lazy_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            roots.add(_root(node.args[0].value))
    return roots


@functools.cache
def _engine_of_module(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    if spec is None or not spec.origin or not spec.origin.endswith(".py"):
        return DECIMAL
    tree  = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    roots = _imported_roots(tree)
    if roots & _FLOAT_PACKAGES:
        return FLOAT64
    if roots & _MP_PACKAGES:
        return MPMATH
    return DECIMAL


def engine_of(entry: ToolEntry) -> str:
    """도구의 엔진 등급을 반환한다. 명시 지정이 없으면 정의 모듈의 임포트로 분류한다."""
    return _OVERRIDES.get(entry.full_name) or _engine_of_module(entry.fn.__module__)
