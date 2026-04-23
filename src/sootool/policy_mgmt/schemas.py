"""Domain-specific pydantic schemas for policy YAML validation.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

class PolicyHeader(BaseModel):
    sha256: str
    effective_date: str
    notice_no: str
    source_url: str
    year: int | None = None


# ---------------------------------------------------------------------------
# Tax — income / capital gains / withholding
# ---------------------------------------------------------------------------

class TaxBracket(BaseModel):
    upper: Decimal | None
    rate: Decimal

    @field_validator("rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError(f"rate must be between 0 and 1, got {v}")
        return v


class TaxBracketsData(BaseModel):
    brackets: list[TaxBracket]

    @model_validator(mode="after")
    def brackets_monotone(self) -> TaxBracketsData:
        brackets = self.brackets
        if not brackets:
            raise ValueError("brackets must not be empty")
        for i, b in enumerate(brackets[:-1]):
            if b.upper is None:
                raise ValueError(f"Only the last bracket may have upper=None (bracket index {i})")
        if brackets[-1].upper is not None:
            raise ValueError("Last bracket must have upper=None")
        # Check monotone increasing upper values
        uppers = [b.upper for b in brackets[:-1]]
        for i in range(len(uppers) - 1):
            if uppers[i] is not None and uppers[i + 1] is not None:
                if uppers[i] >= uppers[i + 1]:  # type: ignore[operator]
                    raise ValueError(
                        f"bracket upper values must be strictly increasing: "
                        f"index {i} ({uppers[i]}) >= index {i+1} ({uppers[i+1]})"
                    )
        return self


class KrIncomePolicyData(BaseModel):
    brackets: list[TaxBracket]

    @model_validator(mode="after")
    def validate_brackets(self) -> KrIncomePolicyData:
        TaxBracketsData(brackets=self.brackets)
        return self


class HoldingPeriodEntry(BaseModel):
    holding_years_min: int
    holding_years_max: int | None
    rate: Decimal

    @field_validator("rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError(f"rate must be between 0 and 1, got {v}")
        return v


class KrCapitalGainsPolicyData(BaseModel):
    general: list[HoldingPeriodEntry]
    one_house: list[HoldingPeriodEntry]
    income_tax_brackets: list[TaxBracket]

    @model_validator(mode="after")
    def validate_income_brackets(self) -> KrCapitalGainsPolicyData:
        TaxBracketsData(brackets=self.income_tax_brackets)
        return self


class KrWithholdingPolicyData(BaseModel):
    """Withholding tax policy — flexible structure accepted."""
    pass


# ---------------------------------------------------------------------------
# Realestate
# ---------------------------------------------------------------------------

class HouseBracket(BaseModel):
    upper: Decimal | None
    rate: Decimal

    @field_validator("rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") <= v <= Decimal("1")):
            raise ValueError(f"rate must be between 0 and 1, got {v}")
        return v


class MultiHouseSurcharge(BaseModel):
    two_houses_non_regulated: Decimal
    two_houses_regulated: Decimal
    three_plus: Decimal


class HouseRates(BaseModel):
    brackets: list[HouseBracket]
    multi_house_surcharge: MultiHouseSurcharge


class Surcharges(BaseModel):
    rural_special: Decimal
    local_edu: Decimal


class KrAcquisitionPolicyData(BaseModel):
    house: HouseRates
    surcharges: Surcharges


class LtvRates(BaseModel):
    regulated_first_house: Decimal
    regulated_multi_house: Decimal
    non_regulated_first_house: Decimal
    non_regulated_multi_house: Decimal


class DtiRates(BaseModel):
    regulated: Decimal
    non_regulated: Decimal


class KrDsrLtvPolicyData(BaseModel):
    dsr_cap: Decimal
    ltv: LtvRates
    dti: DtiRates


# ---------------------------------------------------------------------------
# Domain schema registry
# ---------------------------------------------------------------------------

_DOMAIN_SCHEMAS: dict[str, dict[str, type[BaseModel]]] = {
    "tax": {
        "kr_income":      KrIncomePolicyData,
        "kr_capital_gains": KrCapitalGainsPolicyData,
        "kr_withholding": KrWithholdingPolicyData,
    },
    "realestate": {
        "kr_acquisition": KrAcquisitionPolicyData,
        "kr_dsr_ltv":     KrDsrLtvPolicyData,
    },
}


def get_domain_schema(domain: str, name: str) -> type[BaseModel] | None:
    """Return the pydantic model class for the given domain/name, or None if unknown."""
    return _DOMAIN_SCHEMAS.get(domain, {}).get(name)
