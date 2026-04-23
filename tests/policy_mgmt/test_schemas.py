"""Tests for domain-specific pydantic schemas.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from sootool.policy_mgmt.schemas import (
    KrDsrLtvPolicyData,
    KrIncomePolicyData,
    TaxBracket,
    TaxBracketsData,
    get_domain_schema,
)


def test_tax_brackets_valid() -> None:
    brackets = [
        {"upper": "14000000", "rate": "0.06"},
        {"upper": None, "rate": "0.15"},
    ]
    data = TaxBracketsData(brackets=[TaxBracket(**b) for b in brackets])
    assert len(data.brackets) == 2


def test_tax_brackets_last_must_be_none() -> None:
    brackets = [
        {"upper": "14000000", "rate": "0.06"},
        {"upper": "50000000", "rate": "0.15"},
    ]
    with pytest.raises(ValueError):
        TaxBracketsData(brackets=[TaxBracket(**b) for b in brackets])


def test_tax_brackets_non_last_cannot_be_none() -> None:
    brackets = [
        {"upper": None, "rate": "0.06"},
        {"upper": None, "rate": "0.15"},
    ]
    with pytest.raises(ValueError):
        TaxBracketsData(brackets=[TaxBracket(**b) for b in brackets])


def test_tax_brackets_must_be_monotone() -> None:
    brackets = [
        {"upper": "50000000", "rate": "0.15"},
        {"upper": "14000000", "rate": "0.06"},
        {"upper": None, "rate": "0.35"},
    ]
    with pytest.raises(ValueError):
        TaxBracketsData(brackets=[TaxBracket(**b) for b in brackets])


def test_rate_range_violation() -> None:
    with pytest.raises(ValueError):
        TaxBracket(upper=None, rate=Decimal("1.5"))


def test_kr_income_policy_valid() -> None:
    data = {
        "brackets": [
            {"upper": 14000000, "rate": "0.06"},
            {"upper": None, "rate": "0.15"},
        ]
    }
    KrIncomePolicyData.model_validate(data)


def test_kr_dsr_ltv_valid() -> None:
    data = {
        "dsr_cap": "0.40",
        "ltv": {
            "regulated_first_house":    "0.50",
            "regulated_multi_house":    "0.00",
            "non_regulated_first_house": "0.70",
            "non_regulated_multi_house": "0.60",
        },
        "dti": {
            "regulated":     "0.40",
            "non_regulated": "0.60",
        },
    }
    KrDsrLtvPolicyData.model_validate(data)


def test_get_domain_schema_known() -> None:
    cls = get_domain_schema("tax", "kr_income")
    assert cls is KrIncomePolicyData


def test_get_domain_schema_unknown() -> None:
    cls = get_domain_schema("tax", "nonexistent_policy")
    assert cls is None
