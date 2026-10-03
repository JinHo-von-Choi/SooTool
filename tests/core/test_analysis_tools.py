from __future__ import annotations

from decimal import Decimal

import pytest

from sootool import server
from sootool.core.errors import InvalidInputError, SolverBracketError
from sootool.core.registry import REGISTRY


@pytest.fixture(scope="module", autouse=True)
def _loaded() -> None:
    server._load_modules()


_LOAN = {"principal": "10000000", "annual_rate": "0.05", "months": 12}


# --- core.solve_for ---

def test_solve_for_inverts_a_tool_result():
    forward = REGISTRY.invoke("finance.fv", present_value="1000", rate="0.05", periods=10)
    out = REGISTRY.invoke(
        "core.solve_for", tool="finance.fv", arguments={"rate": "0.05", "periods": 10},
        variable="present_value", target_field="fv", target=forward["fv"], lower="1", upper="100000", tolerance="0.001",
    )
    assert out["converged"] is True
    assert abs(Decimal(out["solution"]) - Decimal("1000")) < Decimal("0.01")
    assert Decimal(out["achieved"]) == Decimal(out["at_solution"]["fv"])


def test_solve_for_integer_mode_over_a_step_function():
    out = REGISTRY.invoke(
        "core.solve_for", tool="payroll.kr_salary", arguments={"year": 2026}, variable="monthly_salary",
        target_field="net", target="3000000", lower="3000000", upper="9000000", integer=True,
    )
    assert out["converged"] is True
    assert Decimal(out["achieved"]) == Decimal("3000000")


def test_solve_for_reports_a_missing_sign_change():
    with pytest.raises(SolverBracketError):
        REGISTRY.invoke(
            "core.solve_for", tool="finance.fv", arguments={"rate": "0.05", "periods": 10},
            variable="present_value", target_field="fv", target="1", lower="1000", upper="2000",
        )


def test_solve_for_rejects_unknown_variable_field_and_forbidden_targets():
    base = {"tool": "finance.fv", "arguments": {"rate": "0.05", "periods": 10}, "target": "1", "lower": "1", "upper": "5"}
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.solve_for", variable="nope", target_field="fv", **base)
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.solve_for", variable="present_value", target_field="no.such.field", **base)
    for forbidden in ("core.batch", "core.solve_for", "sootool.policy_activate", "core.explain"):
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("core.solve_for", **{**base, "tool": forbidden}, variable="present_value", target_field="fv")


def test_solve_for_is_deterministic_and_replay_verifiable():
    args = dict(
        tool="finance.fv", arguments={"rate": "0.05", "periods": 10}, variable="present_value", target_field="fv",
        target="2000", lower="1", upper="100000", tolerance="0.001",
    )
    first  = REGISTRY.invoke("core.solve_for", **args)
    second = REGISTRY.invoke("core.solve_for", **args)
    assert first["_meta"]["integrity"]["result_hash"] == second["_meta"]["integrity"]["result_hash"]
    verified = REGISTRY.invoke(
        "sootool.verify_receipt", tool="core.solve_for", arguments=args, receipt=first["_meta"]["integrity"],
    )
    assert verified["valid"] is True


def test_solve_for_respects_the_evaluation_limit(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_SOLVER_EVALUATIONS", "5")
    with pytest.raises(Exception) as info:
        REGISTRY.invoke(
            "core.solve_for", tool="finance.fv", arguments={"rate": "0.05", "periods": 10}, variable="present_value",
            target_field="fv", target="2000", lower="1", upper="100000", max_iter=6,
        )
    assert info.value.to_payload()["code"] == "input_limit"


# --- payroll.kr_gross_from_net ---

@pytest.mark.parametrize("net", ["2000000", "3000000", "5000000"])
def test_gross_from_net_is_the_smallest_salary_reaching_the_target(net):
    out = REGISTRY.invoke("payroll.kr_gross_from_net", net_monthly=net, year=2026)
    gross = int(out["gross"])
    assert Decimal(out["achieved_net"]) >= Decimal(net)
    below = REGISTRY.invoke("payroll.kr_salary", monthly_salary=str(gross - 1), year=2026)
    assert Decimal(below["net"]) < Decimal(net)
    assert out["residual"] == str(Decimal(out["achieved_net"]) - Decimal(net))
    assert out["salary"]["net"] == out["achieved_net"]


def test_gross_from_net_follows_the_policy_arguments():
    june    = REGISTRY.invoke("payroll.kr_gross_from_net", net_monthly="3000000", year=2026, as_of="2026-06-15")
    early   = REGISTRY.invoke("payroll.kr_gross_from_net", net_monthly="3000000", year=2026, as_of="2026-06-01")
    august  = REGISTRY.invoke("payroll.kr_gross_from_net", net_monthly="3000000", year=2026, as_of="2026-08-01")
    assert june["gross"] == early["gross"]
    assert early["policy_effective_date"] == "2026-01-01"
    assert august["policy_effective_date"] == "2026-07-01"
    assert early["_meta"]["integrity"]["input_hash"] != june["_meta"]["integrity"]["input_hash"]


def test_gross_from_net_rejects_non_positive_targets():
    with pytest.raises(Exception) as info:
        REGISTRY.invoke("payroll.kr_gross_from_net", net_monthly="0", year=2026)
    assert info.value.to_payload()["code"] == "domain_constraint"


# --- core.compare ---

def test_compare_reports_values_and_deltas_against_the_baseline():
    out = REGISTRY.invoke(
        "core.compare", tool="finance.loan_schedule", base_arguments=_LOAN, fields=["monthly_payment"],
        scenarios=[
            {"name": "24개월", "arguments": {"months": 24}},
            {"name": "금리 3%", "arguments": {"annual_rate": "0.03"}},
        ],
    )
    baseline = Decimal(out["baseline"]["monthly_payment"])
    rows = {r["name"]: r for r in out["scenarios"]}
    assert Decimal(rows["24개월"]["values"]["monthly_payment"]) < baseline
    assert Decimal(rows["24개월"]["delta_vs_baseline"]["monthly_payment"]) == (
        Decimal(rows["24개월"]["values"]["monthly_payment"]) - baseline
    )
    assert Decimal(rows["금리 3%"]["delta_vs_baseline"]["monthly_payment"]) < 0
    assert [r["name"] for r in out["scenarios"]] == ["24개월", "금리 3%"]


def test_compare_non_numeric_fields_have_no_delta():
    out = REGISTRY.invoke(
        "core.compare", tool="finance.loan_schedule", base_arguments=_LOAN, fields=["trace.tool"],
        scenarios=[{"name": "a", "arguments": {"months": 6}}],
    )
    assert out["scenarios"][0]["values"]["trace.tool"] == "finance.loan_schedule"
    assert out["scenarios"][0]["delta_vs_baseline"]["trace.tool"] is None


def test_compare_validates_its_inputs():
    base = dict(tool="finance.loan_schedule", base_arguments=_LOAN, fields=["monthly_payment"])
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.compare", scenarios=[], **base)
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.compare", scenarios=[{"arguments": {}}], **base)
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.compare", scenarios=[{"name": "a"}, {"name": "a"}], **base)
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.compare", tool=base["tool"], base_arguments=_LOAN, fields=[], scenarios=[{"name": "a"}])
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.compare", scenarios=[{"name": "a"}], **{**base, "fields": ["missing.field"]})


def test_compare_enforces_the_scenario_limit(monkeypatch):
    monkeypatch.setenv("SOOTOOL_LIMIT_SCENARIOS", "2")
    with pytest.raises(Exception) as info:
        REGISTRY.invoke(
            "core.compare", tool="finance.loan_schedule", base_arguments=_LOAN, fields=["monthly_payment"],
            scenarios=[{"name": str(i), "arguments": {"months": 6 + i}} for i in range(3)],
        )
    assert info.value.to_payload()["code"] == "input_limit"


def test_compare_with_policy_as_of_per_scenario():
    out = REGISTRY.invoke(
        "core.compare", tool="tax.kr_income", base_arguments={"taxable_income": "50000000", "year": 2026},
        fields=["tax", "policy_effective_date"],
        scenarios=[{"name": "as_of 6월", "arguments": {"as_of": "2026-06-01"}}],
    )
    assert out["scenarios"][0]["values"]["tax"] == out["baseline"]["tax"]
    assert out["scenarios"][0]["values"]["policy_effective_date"] == "2026-01-01"


# --- core.explain ---

def test_explain_renders_formula_inputs_steps_result_and_policy_basis():
    out = REGISTRY.invoke("core.explain", tool="tax.kr_income", arguments={"taxable_income": "50000000", "year": 2026})
    text = out["summary"]
    assert "도구: tax.kr_income" in text
    assert "taxable_income" in text and "50000000" in text
    assert "결과: " in text
    assert "적용 정책: 확정, 시행 2026-01-01~현재" in text
    assert out["result"]["tax"] == "6240000"
    assert out["lines"][0] == "도구: tax.kr_income"


def test_explain_does_not_change_the_numbers():
    direct = REGISTRY.invoke("tax.kr_income", taxable_income="50000000", year=2026)
    out    = REGISTRY.invoke("core.explain", tool="tax.kr_income", arguments={"taxable_income": "50000000", "year": 2026})
    assert out["result"]["tax"] == direct["tax"]
    assert out["result"]["trace"] == direct["trace"]


def test_explain_in_english_and_unknown_language():
    out = REGISTRY.invoke("core.explain", tool="core.add", arguments={"operands": ["1", "2"]}, lang="en")
    assert out["summary"].startswith("Tool: core.add")
    assert "Result:" in out["summary"]
    with pytest.raises(InvalidInputError):
        REGISTRY.invoke("core.explain", tool="core.add", arguments={"operands": ["1"]}, lang="fr")


def test_explain_notes_float64_engines():
    out = REGISTRY.invoke("core.explain", tool="stats.ci_mean", arguments={"values": ["1", "2", "3"]})
    assert "배정밀도(float64)" in out["summary"]


def test_explain_cites_the_legal_basis_when_the_policy_has_citations():
    out = REGISTRY.invoke("core.explain", tool="tax.kr_income", arguments={"taxable_income": "1000000", "year": 2026})
    assert out["citations"] == [] or all("law" in c for c in out["citations"])


def test_analysis_tools_are_read_only_composites():
    from sootool.core.engines import COMPOSITE, engine_of

    for name in ("core.solve_for", "core.compare", "core.explain"):
        entry = next(e for e in REGISTRY.list() if e.full_name == name)
        assert entry.read_only is True
        assert engine_of(entry) == COMPOSITE
