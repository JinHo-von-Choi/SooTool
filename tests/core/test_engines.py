from __future__ import annotations

import ast

import pytest

from sootool import server
from sootool.core.engines import (
    COMPOSITE,
    DECIMAL,
    ENGINES,
    FLOAT64,
    MPMATH,
    NONE,
    _imported_roots,
    engine_of,
)
from sootool.core.registry import REGISTRY


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def _entry(name: str):
    return next(e for e in REGISTRY.list() if e.full_name == name)


def test_every_tool_has_a_known_engine():
    unknown = [e.full_name for e in REGISTRY.list() if engine_of(e) not in ENGINES]
    assert not unknown, unknown


@pytest.mark.parametrize(
    ("tool", "expected"),
    [
        ("core.add", DECIMAL),
        ("tax.progressive", DECIMAL),
        ("finance.loan_schedule", DECIMAL),
        ("core.calc", MPMATH),
        ("symbolic.solve", MPMATH),
        ("stats.ci_mean", FLOAT64),
        ("finance.var_historical", FLOAT64),
        ("geometry.matrix_inverse", FLOAT64),
        ("core.batch", COMPOSITE),
        ("core.pipeline", COMPOSITE),
        ("sootool.verify_receipt", COMPOSITE),
        ("sootool.policy_list", NONE),
        ("sootool.skill_guide", NONE),
    ],
)
def test_representative_classification(tool, expected):
    assert engine_of(_entry(tool)) == expected


def test_policy_tools_are_all_classified_as_non_numeric():
    for entry in REGISTRY.list():
        if entry.full_name.startswith("sootool.policy_"):
            assert engine_of(entry) == NONE, entry.full_name


def test_import_scan_sees_lazy_module_and_nested_imports():
    tree = ast.parse(
        "import numpy as np\n"
        "stats = lazy_module('scipy.stats')\n"
        "def f():\n"
        "    import mpmath\n"
    )
    assert _imported_roots(tree) == {"numpy", "scipy", "mpmath"}


def test_response_meta_reports_engine():
    out = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert out["_meta"]["engine"] == DECIMAL
    out = REGISTRY.invoke("stats.ci_mean", values=["1", "2", "3"])
    assert out["_meta"]["engine"] == FLOAT64


def test_engine_is_not_part_of_result_hash():
    from sootool.core.audit import result_hash

    out = REGISTRY.invoke("core.add", operands=["1", "2"])
    assert result_hash(out) == out["_meta"]["integrity"]["result_hash"]


def test_describe_reports_engine():
    from sootool.core.catalog import describe_tool

    assert describe_tool(_entry("stats.ci_mean"))["engine"] == FLOAT64
