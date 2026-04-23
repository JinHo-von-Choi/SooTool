"""Practical examples for skill_guide."""
from __future__ import annotations

from typing import Any

_EXAMPLES_KO: list[dict[str, Any]] = [
    {
        "request": "500만원에서 부가세 분리해줘",
        "tool_call": {
            "tool": "accounting.vat_extract",
            "args": {"vat_inclusive": "5000000", "rate": "0.1"},
        },
        "expected_output": {
            "supply": "4545454",
            "vat": "454546",
            "trace": {"formula": "supply=floor(inclusive/(1+rate)), vat=inclusive-supply"},
        },
    },
    {
        "request": "2024년 종합소득세 계산해줘 (과세표준 8000만원)",
        "tool_call": {
            "tool": "tax.kr_income",
            "args": {"taxable_income": "80000000", "year": 2024},
        },
        "expected_output": {
            "tax": "...",
            "trace": {"policy_version": "kr_income_2024", "formula": "progressive brackets"},
        },
    },
    {
        "request": "대출 3개 조건 비교해줘 (이자율 각각 3.5%, 4.0%, 4.5%, 원금 3억, 30년)",
        "tool_call": {
            "tool": "core.batch",
            "args": {
                "items": [
                    {"id": "loan_35", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.035", "months": 360}},
                    {"id": "loan_40", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.040", "months": 360}},
                    {"id": "loan_45", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.045", "months": 360}},
                ]
            },
        },
        "expected_output": {
            "results": [
                {"id": "loan_35", "status": "ok"},
                {"id": "loan_40", "status": "ok"},
                {"id": "loan_45", "status": "ok"},
            ]
        },
    },
    {
        "request": "월급 350만원 → 연봉 → 소득세 → 실수령액 계산해줘",
        "tool_call": {
            "tool": "core.pipeline",
            "args": {
                "steps": [
                    {"id": "annual", "tool": "core.mul", "args": {"operands": ["3500000", "12"]}},
                    {"id": "tax", "tool": "tax.kr_income", "args": {"taxable_income": "${annual.result}", "year": 2024}},
                    {"id": "net", "tool": "core.sub", "args": {"a": "${annual.result}", "b": "${tax.tax}"}},
                ]
            },
        },
        "expected_output": {"steps": [{"id": "annual"}, {"id": "tax"}, {"id": "net"}]},
    },
    {
        "request": "2026년 월급 350만원(식대 20만원 포함) 세후 실수령액 알려줘",
        "tool_call": {
            "tool": "payroll.kr_salary",
            "args": {"monthly_salary": "3500000", "year": 2026, "meal_allowance": "200000"},
        },
        "expected_output": {
            "gross":  "3500000",
            "net":    "...",
            "insurances": {"national_pension": "...", "health_insurance": "...", "long_term_care": "..."},
            "trace":  {"tool": "payroll.kr_salary"},
        },
    },
    {
        "request": "저항 220Ω에 12V 인가 시 전류와 소비전력 계산",
        "tool_call": {
            "tool": "core.batch",
            "args": {
                "items": [
                    {"id": "ohm",   "tool": "engineering.electrical_ohm",   "args": {"voltage": "12", "resistance": "220"}},
                    {"id": "power", "tool": "engineering.electrical_power", "args": {"voltage": "12", "resistance": "220"}},
                ]
            },
        },
        "expected_output": {
            "results": [{"id": "ohm", "status": "ok"}, {"id": "power", "status": "ok"}],
        },
    },
]

_EXAMPLES_EN: list[dict[str, Any]] = [
    {
        "request": "Separate VAT from KRW 5,000,000",
        "tool_call": {
            "tool": "accounting.vat_extract",
            "args": {"vat_inclusive": "5000000", "rate": "0.1"},
        },
        "expected_output": {
            "supply": "4545454",
            "vat": "454546",
            "trace": {"formula": "supply=floor(inclusive/(1+rate)), vat=inclusive-supply"},
        },
    },
    {
        "request": "Calculate 2024 Korean income tax for taxable income KRW 80,000,000",
        "tool_call": {
            "tool": "tax.kr_income",
            "args": {"taxable_income": "80000000", "year": 2024},
        },
        "expected_output": {
            "tax": "...",
            "trace": {"policy_version": "kr_income_2024"},
        },
    },
    {
        "request": "Compare 3 loan options (rates 3.5%, 4.0%, 4.5%, principal 300M KRW, 30 years)",
        "tool_call": {
            "tool": "core.batch",
            "args": {
                "items": [
                    {"id": "loan_35", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.035", "months": 360}},
                    {"id": "loan_40", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.040", "months": 360}},
                    {"id": "loan_45", "tool": "finance.loan_schedule", "args": {"principal": "300000000", "annual_rate": "0.045", "months": 360}},
                ]
            },
        },
        "expected_output": {
            "results": [
                {"id": "loan_35", "status": "ok"},
                {"id": "loan_40", "status": "ok"},
                {"id": "loan_45", "status": "ok"},
            ]
        },
    },
    {
        "request": "Monthly salary 3.5M KRW -> annual -> income tax -> net pay",
        "tool_call": {
            "tool": "core.pipeline",
            "args": {
                "steps": [
                    {"id": "annual", "tool": "core.mul", "args": {"operands": ["3500000", "12"]}},
                    {"id": "tax", "tool": "tax.kr_income", "args": {"taxable_income": "${annual.result}", "year": 2024}},
                    {"id": "net", "tool": "core.sub", "args": {"a": "${annual.result}", "b": "${tax.tax}"}},
                ]
            },
        },
        "expected_output": {"steps": [{"id": "annual"}, {"id": "tax"}, {"id": "net"}]},
    },
    {
        "request": "Korean monthly take-home pay for 3.5M KRW gross (200k meal allowance) in 2026",
        "tool_call": {
            "tool": "payroll.kr_salary",
            "args": {"monthly_salary": "3500000", "year": 2026, "meal_allowance": "200000"},
        },
        "expected_output": {
            "gross":  "3500000",
            "net":    "...",
            "insurances": {"national_pension": "...", "health_insurance": "...", "long_term_care": "..."},
            "trace":  {"tool": "payroll.kr_salary"},
        },
    },
    {
        "request": "Current and power dissipation for 12V across a 220 ohm resistor",
        "tool_call": {
            "tool": "core.batch",
            "args": {
                "items": [
                    {"id": "ohm",   "tool": "engineering.electrical_ohm",   "args": {"voltage": "12", "resistance": "220"}},
                    {"id": "power", "tool": "engineering.electrical_power", "args": {"voltage": "12", "resistance": "220"}},
                ]
            },
        },
        "expected_output": {
            "results": [{"id": "ohm", "status": "ok"}, {"id": "power", "status": "ok"}],
        },
    },
]


def get_examples(locale: str = "ko") -> list[dict[str, Any]]:
    """Return practical examples for the given locale."""
    if locale == "en":
        return _EXAMPLES_EN
    return _EXAMPLES_KO
