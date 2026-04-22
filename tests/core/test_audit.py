from decimal import Decimal
from sootool.core.audit import CalcTrace

def test_trace_records_inputs_and_output():
    t = CalcTrace(tool="finance.npv", formula="sum(cf/(1+r)^t)")
    t.input("rate", Decimal("0.05"))
    t.input("cashflows", [Decimal("-100"), Decimal("60"), Decimal("60")])
    t.step("discount_year_1", Decimal("57.14"))
    t.step("discount_year_2", Decimal("54.42"))
    t.output(Decimal("11.56"))
    data = t.to_dict()
    assert data["tool"] == "finance.npv"
    assert data["formula"] == "sum(cf/(1+r)^t)"
    assert data["inputs"]["rate"] == "0.05"
    assert data["output"] == "11.56"
    assert len(data["steps"]) == 2

def test_trace_serializes_decimal_as_string():
    t = CalcTrace(tool="t")
    t.output(Decimal("3.14"))
    assert t.to_dict()["output"] == "3.14"
