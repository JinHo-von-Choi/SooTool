from __future__ import annotations

import pytest

from sootool import server
from sootool.core.catalog import (
    bind_call_arguments,
    describe_tool,
    resolve_tool,
    search_tools,
)
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


def test_exact_name_ranks_first():
    hits = search_tools(REGISTRY, "core.add")
    assert hits[0]["name"] == "core.add"


def test_search_matches_description_text():
    names = [h["name"] for h in search_tools(REGISTRY, "정액법 감가상각")]
    assert "accounting.depreciation_straight_line" in names


def test_search_matches_tool_name_tokens():
    names = [h["name"] for h in search_tools(REGISTRY, "loan schedule")]
    assert "finance.loan_schedule" in names[:3]


def test_search_is_deterministic():
    first  = search_tools(REGISTRY, "tax income", limit=20)
    second = search_tools(REGISTRY, "tax income", limit=20)
    assert first == second
    scores = [h["score"] for h in first]
    assert scores == sorted(scores, reverse=True)


def test_search_namespace_filter():
    hits = search_tools(REGISTRY, "tax", limit=50, namespace="tax_us")
    assert hits
    assert all(h["name"].startswith("tax_us.") for h in hits)


def test_search_limit_is_enforced():
    assert len(search_tools(REGISTRY, "calculate probability", limit=3)) <= 3


def test_search_without_match_returns_empty_list():
    assert search_tools(REGISTRY, "zzzzqqqq") == []


@pytest.mark.parametrize("query", ["", "   "])
def test_search_rejects_blank_query(query):
    with pytest.raises(InvalidInputError):
        search_tools(REGISTRY, query)


@pytest.mark.parametrize("limit", [0, 51, True])
def test_search_rejects_out_of_range_limit(limit):
    with pytest.raises(InvalidInputError):
        search_tools(REGISTRY, "tax", limit=limit)


def test_describe_lists_parameters_with_defaults():
    info   = describe_tool(resolve_tool(REGISTRY, "finance.loan_schedule"))
    params = {p["name"]: p for p in info["parameters"]}
    assert params["principal"]["required"] is True
    assert params["method"]["required"] is False
    assert params["method"]["default"] == "EQUAL_PAYMENT"
    assert info["read_only"] is True


def test_describe_marks_policy_write_tools():
    info = describe_tool(resolve_tool(REGISTRY, "sootool.policy_activate"))
    assert info["read_only"] is False
    assert info["destructive"] is True


def test_resolve_unknown_tool_suggests_candidates():
    with pytest.raises(InvalidInputError) as info:
        resolve_tool(REGISTRY, "finance.loan")
    assert "finance.loan_schedule" in str(info.value)


def test_bind_rejects_unknown_and_missing_arguments():
    entry = resolve_tool(REGISTRY, "core.sub")
    with pytest.raises(InvalidInputError):
        bind_call_arguments(entry, {"a": "1"})
    with pytest.raises(InvalidInputError):
        bind_call_arguments(entry, {"a": "1", "b": "2", "c": "3"})
    assert bind_call_arguments(entry, {"a": "1", "b": "2"}) == {"a": "1", "b": "2"}
