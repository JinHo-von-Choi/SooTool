"""정책 기반 도구의 선언(policy=True)이 실제 정책 사용과 일치하는지 구조로 검사한다."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from sootool import server
from sootool.core.registry import POLICY_ARGUMENTS, REGISTRY

_MODULES_DIR = Path(server.__file__).resolve().parent / "modules"
_ADMIN_POLICY_TOOLS = {"sootool.policy_get", "sootool.policy_export"}


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def _tools_using_policies() -> set[str]:
    """모듈 소스에서 정책 로더를 직접·간접으로 쓰는 도구(위임 포함)를 AST 로 찾는다."""
    found: set[str] = set()
    for path in sorted(_MODULES_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "policy_load" not in source and "REGISTRY.invoke" not in source and "payroll_kr_salary" not in source:
            continue
        functions = {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        calls = {
            name: {
                (n.func.id if isinstance(n.func, ast.Name) else n.func.attr)
                for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
            }
            for name, fn in functions.items()
        }
        uses = {name for name, called in calls.items() if "policy_load" in called}
        changed = True
        while changed:
            changed = False
            for name, called in calls.items():
                if name not in uses and called & uses:
                    uses.add(name)
                    changed = True
        for name, fn in functions.items():
            delegates = bool(calls[name] & {"invoke", "payroll_kr_salary"})
            if name not in uses and not delegates:
                continue
            for decorator in fn.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "tool"
                ):
                    keywords = {k.arg: k.value for k in decorator.keywords}
                    found.add(f"{keywords['namespace'].value}.{keywords['name'].value}")  # type: ignore[attr-defined]
    return found


def test_every_tool_that_loads_a_policy_is_declared_policy_aware():
    flagged = {e.full_name for e in REGISTRY.list() if e.policy}
    used    = _tools_using_policies()
    assert used - flagged == set(), f"정책을 쓰지만 policy=True 가 없는 도구: {sorted(used - flagged)}"


def test_only_policy_using_tools_and_the_admin_readers_are_flagged():
    flagged = {e.full_name for e in REGISTRY.list() if e.policy}
    assert flagged - _tools_using_policies() == _ADMIN_POLICY_TOOLS


def test_every_policy_aware_tool_takes_a_year():
    for entry in REGISTRY.list():
        if entry.policy:
            assert "year" in inspect.signature(entry.fn).parameters, entry.full_name


def test_policy_arguments_are_exposed_only_on_policy_aware_tools():
    for entry in REGISTRY.list():
        exposed = set(entry.exposed_signature().parameters)
        has_policy_args = set(POLICY_ARGUMENTS) <= exposed
        assert has_policy_args == entry.policy, entry.full_name


def test_tool_functions_do_not_declare_the_policy_arguments_themselves():
    """공통 인자는 레지스트리가 처리한다. 함수가 같은 이름을 선언하면 충돌한다."""
    for entry in REGISTRY.list():
        if entry.policy:
            assert not set(POLICY_ARGUMENTS) & set(inspect.signature(entry.fn).parameters), entry.full_name


def test_describe_lists_the_policy_arguments():
    from sootool.core.catalog import describe_tool

    entry  = next(e for e in REGISTRY.list() if e.full_name == "tax.kr_income")
    names  = [p["name"] for p in describe_tool(entry)["parameters"]]
    assert names[-2:] == ["as_of", "include_proposed"]
