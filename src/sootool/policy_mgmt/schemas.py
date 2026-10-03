"""Domain-specific pydantic schemas for policy YAML validation.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
# Tax, income / capital gains / withholding
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


def _unit_rate(v: Decimal) -> Decimal:
    if not (Decimal("0") <= v <= Decimal("1")):
        raise ValueError(f"rate must be between 0 and 1, got {v}")
    return v


class ShortTermRates(BaseModel):
    under_1y: Decimal
    under_2y: Decimal

    @field_validator("under_1y", "under_2y")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class ShortTermRateTable(BaseModel):
    housing:       ShortTermRates
    presale_right: ShortTermRates
    land_building: ShortTermRates


class OneHouseExemption(BaseModel):
    sale_price_threshold:                             Decimal
    min_holding_years:                                int
    min_residence_years_if_acquired_in_regulated_area: int


class SurchargeExclusion(BaseModel):
    min_holding_years: int
    transfer_until:    date


class SurchargeRelief(BaseModel):
    min_holding_years: int
    two_houses:        Decimal
    three_plus:        Decimal

    @field_validator("two_houses", "three_plus")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class CapitalGainsMultiHouseSurcharge(BaseModel):
    two_houses: Decimal
    three_plus: Decimal
    exclusion:  SurchargeExclusion | None = None
    relief:     SurchargeRelief | None = None

    @field_validator("two_houses", "three_plus")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class LongResidenceBasicDeduction(BaseModel):
    amount:              Decimal
    min_residence_years: int
    max_sale_price:      Decimal


class KrCapitalGainsPolicyData(BaseModel):
    general:                       list[HoldingPeriodEntry]
    one_house_holding:             list[HoldingPeriodEntry]
    one_house_residence:           list[HoldingPeriodEntry]
    one_house_min_residence_years: int
    one_house_exemption:           OneHouseExemption
    basic_deduction:               Decimal
    short_term_rates:              ShortTermRateTable
    presale_right_rate:            Decimal
    unregistered_rate:             Decimal
    non_business_land_surcharge:   Decimal
    multi_house_surcharge:         CapitalGainsMultiHouseSurcharge
    income_tax_brackets:           list[TaxBracket]
    basic_deduction_long_residence_one_house: LongResidenceBasicDeduction | None = None

    @field_validator("presale_right_rate", "unregistered_rate", "non_business_land_surcharge")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)

    @model_validator(mode="after")
    def validate_income_brackets(self) -> KrCapitalGainsPolicyData:
        TaxBracketsData(brackets=self.income_tax_brackets)
        return self


class LaborDeductionBracket(BaseModel):
    upper:  Decimal | None
    rate:   Decimal
    offset: Decimal

    @field_validator("rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class SimpleTaxAboveUpper(BaseModel):
    over_k:  int
    upper_k: int | None
    add:     Decimal
    factor:  Decimal
    rate:    Decimal

    @field_validator("factor", "rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class SimpleTaxRounding(BaseModel):
    decimals: int
    mode:     str

    @field_validator("mode")
    @classmethod
    def known_mode(cls, v: str) -> str:
        allowed = {"HALF_EVEN", "HALF_UP", "DOWN", "UP", "FLOOR", "CEIL"}
        if v not in allowed:
            raise ValueError(f"mode must be one of {sorted(allowed)}, got {v!r}")
        return v


class SimpleTaxTable(BaseModel):
    """근로소득 간이세액표 (소득세법 시행령 별표 2)."""

    salary_unit_krw:      int
    max_family:           int
    rows:                 list[tuple[int, int, list[int]]]
    at_upper_salary_k:    int
    at_upper:             list[int]
    above_upper:          list[SimpleTaxAboveUpper]
    above_upper_rounding: SimpleTaxRounding

    @model_validator(mode="after")
    def table_shape(self) -> SimpleTaxTable:
        if self.max_family < 2:
            raise ValueError("max_family must be at least 2")
        if not self.rows:
            raise ValueError("rows must not be empty")
        for i, (lower, upper, taxes) in enumerate(self.rows):
            if lower >= upper:
                raise ValueError(f"rows[{i}]: lower {lower} must be below upper {upper}")
            if len(taxes) != self.max_family:
                raise ValueError(f"rows[{i}]: expected {self.max_family} tax values, got {len(taxes)}")
            if any(t < 0 for t in taxes):
                raise ValueError(f"rows[{i}]: tax values must not be negative")
            if i > 0 and self.rows[i - 1][1] != lower:
                raise ValueError(f"rows[{i}]: lower {lower} must equal previous upper {self.rows[i - 1][1]}")
        if self.rows[-1][1] != self.at_upper_salary_k:
            raise ValueError("last row upper must equal at_upper_salary_k")
        if len(self.at_upper) != self.max_family:
            raise ValueError(f"at_upper must have {self.max_family} values")
        if not self.above_upper or self.above_upper[0].over_k != self.at_upper_salary_k:
            raise ValueError("above_upper must start at at_upper_salary_k")
        for i, segment in enumerate(self.above_upper[:-1]):
            if segment.upper_k is None or segment.upper_k != self.above_upper[i + 1].over_k:
                raise ValueError(f"above_upper[{i}]: upper_k must equal the next over_k")
        if self.above_upper[-1].upper_k is not None:
            raise ValueError("last above_upper segment must have upper_k=None")
        return self


class ChildReduction(BaseModel):
    age_min:            int
    age_max:            int
    one:                Decimal
    two:                Decimal
    per_child_over_two: Decimal


class FamilyOverMax(BaseModel):
    floor_zero: bool


class KrWithholdingPolicyData(BaseModel):
    """근로소득 원천징수 정책: 간이세액표와 상여·연말정산이 함께 쓰는 공제·세율."""

    labor_income_deduction_brackets: list[LaborDeductionBracket]
    labor_income_deduction_cap:      Decimal | None = None
    personal_deduction:              Decimal
    brackets:                        list[TaxBracket]
    simple_tax_table:                SimpleTaxTable
    child_reduction_monthly:         ChildReduction
    family_over_max:                 FamilyOverMax

    @model_validator(mode="after")
    def validate_brackets(self) -> KrWithholdingPolicyData:
        TaxBracketsData(brackets=self.brackets)
        return self


# ---------------------------------------------------------------------------
# Realestate
# ---------------------------------------------------------------------------

def _check_unit_rate(v: Decimal | None) -> Decimal | None:
    if v is not None and not (Decimal("0") <= v <= Decimal("1")):
        raise ValueError(f"rate must be between 0 and 1, got {v}")
    return v


class RateFormula(BaseModel):
    """산식 세율: (가액 × slope_numerator / slope_denominator + intercept_pct) / 100."""
    slope_numerator: Decimal
    slope_denominator: Decimal
    intercept_pct: Decimal
    round_decimals: int


class HouseBracket(BaseModel):
    upper: Decimal | None
    rate: Decimal | None = None
    rate_formula: RateFormula | None = None

    @field_validator("rate")
    @classmethod
    def rate_range(cls, v: Decimal | None) -> Decimal | None:
        return _check_unit_rate(v)

    @model_validator(mode="after")
    def rate_or_formula(self) -> HouseBracket:
        if (self.rate is None) == (self.rate_formula is None):
            raise ValueError("each bracket needs exactly one of rate or rate_formula")
        return self


class MultiHouseSurcharge(BaseModel):
    """중과세율(표준세율 대체). None 은 중과 없음."""
    two_houses_non_regulated: Decimal | None = None
    two_houses_regulated: Decimal
    three_houses_non_regulated: Decimal | None = None
    three_plus: Decimal
    four_plus_non_regulated: Decimal | None = None
    corporate: Decimal | None = None

    @field_validator(
        "two_houses_non_regulated", "two_houses_regulated", "three_houses_non_regulated",
        "three_plus", "four_plus_non_regulated", "corporate",
    )
    @classmethod
    def rate_range(cls, v: Decimal | None) -> Decimal | None:
        return _check_unit_rate(v)


class HouseRates(BaseModel):
    brackets: list[HouseBracket]
    multi_house_surcharge: MultiHouseSurcharge


class HeavySurcharge(BaseModel):
    rate: Decimal
    rural_special: Decimal
    local_edu: Decimal


class Surcharges(BaseModel):
    rural_special: Decimal
    local_edu: Decimal | None = None
    local_edu_ratio_of_rate: Decimal | None = None
    heavy: list[HeavySurcharge] = []

    @model_validator(mode="after")
    def local_edu_present(self) -> Surcharges:
        if self.local_edu is None and self.local_edu_ratio_of_rate is None:
            raise ValueError("one of local_edu or local_edu_ratio_of_rate is required")
        return self


class KrAcquisitionPolicyData(BaseModel):
    house: HouseRates
    surcharges: Surcharges


class LtvRates(BaseModel):
    regulated_first_house: Decimal
    regulated_multi_house: Decimal
    non_regulated_first_house: Decimal
    non_regulated_multi_house: Decimal
    capital_non_regulated_multi_house: Decimal | None = None
    first_time_buyer_capital_or_regulated: Decimal | None = None
    first_time_buyer_other: Decimal | None = None
    first_time_buyer_loan_cap: Decimal | None = None


class DtiRates(BaseModel):
    regulated: Decimal
    non_regulated: Decimal
    non_capital: Decimal | None = None


class LoanAmountCap(BaseModel):
    upper: Decimal | None
    cap: Decimal


class StressDsr(BaseModel):
    floor_rate: Decimal
    capital_or_regulated_mortgage_floor: Decimal
    non_capital_mortgage_floor: Decimal | None = None


class KrDsrLtvPolicyData(BaseModel):
    dsr_cap: Decimal
    dsr_cap_nonbank: Decimal | None = None
    stress_dsr: StressDsr | None = None
    ltv: LtvRates
    mortgage_amount_cap_capital_or_regulated: list[LoanAmountCap] = []
    dti: DtiRates


# ---------------------------------------------------------------------------
# Payroll: 4대보험
# ---------------------------------------------------------------------------

class NationalPensionRates(BaseModel):
    employee_rate: Decimal
    employer_rate: Decimal
    base_min_monthly: Decimal
    base_max_monthly: Decimal
    base_truncation_unit: Decimal = Decimal("1")

    @field_validator("employee_rate", "employer_rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)

    @model_validator(mode="after")
    def bounds_ordered(self) -> NationalPensionRates:
        if not (Decimal("0") < self.base_min_monthly <= self.base_max_monthly):
            raise ValueError("national_pension requires 0 < base_min_monthly <= base_max_monthly")
        if self.base_truncation_unit <= 0:
            raise ValueError("base_truncation_unit must be positive")
        return self


class HealthInsuranceRates(BaseModel):
    employee_rate: Decimal
    employer_rate: Decimal
    long_term_care_rate_of_health: Decimal
    premium_min_monthly_total: Decimal | None = None
    premium_max_monthly_total: Decimal | None = None

    @field_validator("employee_rate", "employer_rate", "long_term_care_rate_of_health")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)

    @model_validator(mode="after")
    def bounds_ordered(self) -> HealthInsuranceRates:
        if self.employee_rate + self.employer_rate <= 0:
            raise ValueError("health_insurance employee_rate + employer_rate must be positive")
        lo, hi = self.premium_min_monthly_total, self.premium_max_monthly_total
        if lo is not None and hi is not None and not (Decimal("0") <= lo <= hi):
            raise ValueError("health_insurance requires 0 <= premium_min_monthly_total <= premium_max_monthly_total")
        return self


class EmployeeRate(BaseModel):
    employee_rate: Decimal

    @field_validator("employee_rate")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class LocalIncomeTaxRate(BaseModel):
    rate_of_income_tax: Decimal

    @field_validator("rate_of_income_tax")
    @classmethod
    def rate_range(cls, v: Decimal) -> Decimal:
        return _unit_rate(v)


class NonTaxableCaps(BaseModel):
    meal_monthly_cap: Decimal


class KrFourInsurancePolicyData(BaseModel):
    national_pension: NationalPensionRates
    health_insurance: HealthInsuranceRates
    employment_insurance: EmployeeRate
    industrial_accident: EmployeeRate
    local_income_tax: LocalIncomeTaxRate
    non_taxable: NonTaxableCaps
    income_tax: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Domain schema registry
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 구조 스키마: 나머지 정책 문서의 data 가 갖춰야 할 키와 값의 종류. 같은 정책의 모든 버전 파일이 공통으로
# 가진 키를 필수로 하고, 선언하지 않은 키는 허용한다(값의 법적 정합성은 시험과 조문 인용으로 다룬다).
# ---------------------------------------------------------------------------

class KrHealthIncomePremiumPolicyData(BaseModel):
    """payroll/kr_health_income_premium 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    evaluation_rates: dict[str, Any]
    financial_income_exclusion_max: Decimal
    income_premium_max_monthly: Decimal
    non_salary_income_threshold_annual: Decimal
    settlement_installment: dict[str, Any]


class KrLaborPayPolicyData(BaseModel):
    """payroll/kr_labor_pay 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    amount_rounding: dict[str, Any]
    holiday_daily_limit_hours: Decimal
    monthly_hours: dict[str, Any]
    night_window: dict[str, Any]
    premium_rates: dict[str, Any]
    small_workplace_max_employees: Decimal
    weekly_holiday: dict[str, Any]


class KrMinimumWagePolicyData(BaseModel):
    """payroll/kr_minimum_wage 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    hourly_minimum_wage: Decimal
    inclusion: dict[str, Any]
    notice_monthly_amount: Decimal
    notice_monthly_hours: Decimal
    probation: dict[str, Any]


class KrNationalPensionBenefitPolicyData(BaseModel):
    """payroll/kr_national_pension_benefit 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    a_value: Decimal
    deferral_increment_per_month: Decimal
    deferral_max_months: Decimal
    deferral_ratios: list[Any]
    dependent_annual: dict[str, Any]
    early_max_months: Decimal
    early_reduction_per_month: Decimal
    extension_rate_per_year: Decimal
    full_benefit_months: Decimal
    minimum_months: Decimal
    monthly_truncation_unit: Decimal
    partial_base_ratio: Decimal
    partial_increment_per_year: Decimal
    proportional_constants: list[Any]
    revaluation_rates: dict[str, Any]


class KrSeverancePolicyData(BaseModel):
    """payroll/kr_severance 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    converted_salary_deduction_brackets: list[Any]
    service_deduction_brackets: list[Any]
    tax_brackets: list[Any]


class KrYearendDeductionsPolicyData(BaseModel):
    """payroll/kr_yearend_deductions 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    donation: dict[str, Any]
    education: dict[str, Any]
    housing_loan_interest: dict[str, Any]
    medical: dict[str, Any]


class KrComprehensivePolicyData(BaseModel):
    """realestate/kr_comprehensive 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    base_deduction: dict[str, Any]
    burden_cap_ratio: Decimal
    corporate_rates: dict[str, Any]
    fair_market_ratio: Decimal
    multi_bracket_min_house_count: Decimal
    multi_house_brackets: list[Any]
    one_house_brackets: list[Any]
    one_house_credit: dict[str, Any]
    property_tax_credit: dict[str, Any]
    rural_special_rate: Decimal


class KrLocalPropertyPolicyData(BaseModel):
    """realestate/kr_local_property 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    acquisition_brackets: list[Any]
    acquisition_coefficient: dict[str, Any]
    fair_market_ratio: Decimal
    one_house_fair_market_ratio: list[Any]
    one_house_special: dict[str, Any]
    property_brackets: list[Any]
    property_coefficient: dict[str, Any]
    surcharges: dict[str, Any]
    urban_area_applicable: dict[str, Any]


class KrPropertyTaxPolicyData(BaseModel):
    """realestate/kr_property_tax 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: list[Any]
    fair_market_ratio: Decimal
    one_house_fair_market_ratio: list[Any]
    one_house_special: dict[str, Any]
    surcharges: dict[str, Any]
    tax_base_cap_rate: Decimal


class KrSubscriptionPolicyData(BaseModel):
    """realestate/kr_subscription 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    dependents: dict[str, Any]
    homeless_period: dict[str, Any]
    max_total_points: Decimal
    savings_period: dict[str, Any]
    spouse_savings: dict[str, Any]


class KrComprehensiveIncomePolicyData(BaseModel):
    """tax/kr_comprehensive_income 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    additional_deduction: dict[str, Any]
    child_tax_credit: dict[str, Any]
    dividend_gross_up_rate: Decimal
    financial_income_threshold: Decimal
    financial_withholding_rate: Decimal
    other_income_deemed_expense_rate: Decimal
    other_income_separate_threshold: Decimal
    other_income_withholding_rate: Decimal
    standard_tax_credit_non_wage: dict[str, Any]


class KrCorporatePolicyData(BaseModel):
    """tax/kr_corporate 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: list[Any]
    minimum_tax: dict[str, Any]
    small_rental_brackets: list[Any]


class KrEitcPolicyData(BaseModel):
    """tax/kr_eitc 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    business_adjustment_rates: dict[str, Any]
    calculation_table: list[Any]
    dual_earner_min_each: Decimal
    earnings_excluded_industries: list[Any]
    household_types: dict[str, Any]
    late_application_rate: Decimal
    minimum_award: dict[str, Any]
    property_limit: Decimal
    property_reduction_rate: Decimal
    property_reduction_threshold: Decimal


class KrGiftPolicyData(BaseModel):
    """tax/kr_gift 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: list[Any]
    deduction_lookback_years: Decimal
    filing_credit_rate: Decimal
    generation_skip_surcharge: dict[str, Any]
    marriage_birth_deduction: Decimal
    relationship_deduction: dict[str, Any]


class KrInheritancePolicyData(BaseModel):
    """tax/kr_inheritance 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: list[Any]
    deductions: dict[str, Any]
    filing_credit_rate: Decimal
    generation_skip_surcharge: dict[str, Any]
    pre_gift_limit_threshold: Decimal


class KrPensionIncomePolicyData(BaseModel):
    """tax/kr_pension_income 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    deferred_retirement_ratios: list[Any]
    lifetime_annuity_rate: Decimal
    local_income_tax_ratio: Decimal
    non_pension_withdrawal_rate: Decimal
    pension_income_deduction: dict[str, Any]
    pension_receipt_min_age: Decimal
    private_pension_age_rates: list[Any]
    separate_taxation_option_rate: Decimal
    separate_taxation_threshold: Decimal


class KrRegistrationLicenseTaxPolicyData(BaseModel):
    """tax/kr_registration_license_tax 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    local_education_tax_rate: Decimal
    other_registration_flat: Decimal
    real_estate_rates: dict[str, Any]
    rounding_unit: Decimal


class KrSecuritiesTransactionPolicyData(BaseModel):
    """tax/kr_securities_transaction 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    markets: dict[str, Any]
    statutory_rate: Decimal


class KrSimplifiedVatPolicyData(BaseModel):
    """tax/kr_simplified_vat 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    card_sales_credit: dict[str, Any]
    input_credit_rate: Decimal
    nonpayment_threshold: Decimal
    restricted_threshold_amount: Decimal
    threshold_amount: Decimal
    value_added_rates: dict[str, Any]
    vat_rate: Decimal


class KrVehicleTaxPolicyData(BaseModel):
    """tax/kr_vehicle_tax 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    age_reduction: dict[str, Any]
    annual_payment: dict[str, Any]
    local_education_tax_rate: Decimal
    other_passenger_annual: dict[str, Any]
    passenger_cc_rates: dict[str, Any]
    rounding_unit: Decimal


class CapitalGainsPolicyData(BaseModel):
    """tax_us/capital_gains 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    ltcg_brackets: dict[str, Any]
    niit: dict[str, Any]


class FederalIncomePolicyData(BaseModel):
    """tax_us/federal_income 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: dict[str, Any]
    standard_deduction: dict[str, Any]


class FicaPolicyData(BaseModel):
    """tax_us/fica 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    additional_medicare: dict[str, Any]
    medicare: dict[str, Any]
    self_employment: dict[str, Any]
    social_security: dict[str, Any]


class StateTaxCaPolicyData(BaseModel):
    """tax_us/state_tax_ca 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: dict[str, Any]
    has_income_tax: bool
    standard_deduction: dict[str, Any]
    surcharge: dict[str, Any]


class StateTaxNyPolicyData(BaseModel):
    """tax_us/state_tax_ny 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: dict[str, Any]
    has_income_tax: bool
    recapture: dict[str, Any]
    standard_deduction: dict[str, Any]


class StateTaxTxPolicyData(BaseModel):
    """tax_us/state_tax_tx 정책 data 의 구조(필수 키와 값의 종류). 선언하지 않은 키는 허용한다."""

    model_config = ConfigDict(extra="allow")

    brackets: dict[str, Any]
    has_income_tax: bool
    standard_deduction: dict[str, Any]


_DOMAIN_SCHEMAS: dict[str, dict[str, type[BaseModel]]] = {
    "tax": {
        "kr_income":      KrIncomePolicyData,
        "kr_capital_gains": KrCapitalGainsPolicyData,
        "kr_withholding": KrWithholdingPolicyData,
        "kr_comprehensive_income": KrComprehensiveIncomePolicyData,
        "kr_corporate": KrCorporatePolicyData,
        "kr_eitc": KrEitcPolicyData,
        "kr_gift": KrGiftPolicyData,
        "kr_inheritance": KrInheritancePolicyData,
        "kr_pension_income": KrPensionIncomePolicyData,
        "kr_registration_license_tax": KrRegistrationLicenseTaxPolicyData,
        "kr_securities_transaction": KrSecuritiesTransactionPolicyData,
        "kr_simplified_vat": KrSimplifiedVatPolicyData,
        "kr_vehicle_tax": KrVehicleTaxPolicyData,
    },
    "realestate": {
        "kr_acquisition": KrAcquisitionPolicyData,
        "kr_dsr_ltv":     KrDsrLtvPolicyData,
        "kr_comprehensive": KrComprehensivePolicyData,
        "kr_local_property": KrLocalPropertyPolicyData,
        "kr_property_tax": KrPropertyTaxPolicyData,
        "kr_subscription": KrSubscriptionPolicyData,
    },
    "payroll": {
        "kr_4insurance": KrFourInsurancePolicyData,
        "kr_health_income_premium": KrHealthIncomePremiumPolicyData,
        "kr_labor_pay": KrLaborPayPolicyData,
        "kr_minimum_wage": KrMinimumWagePolicyData,
        "kr_national_pension_benefit": KrNationalPensionBenefitPolicyData,
        "kr_severance": KrSeverancePolicyData,
        "kr_yearend_deductions": KrYearendDeductionsPolicyData,
    },
    "tax_us": {
        "capital_gains": CapitalGainsPolicyData,
        "federal_income": FederalIncomePolicyData,
        "fica": FicaPolicyData,
        "state_tax_ca": StateTaxCaPolicyData,
        "state_tax_ny": StateTaxNyPolicyData,
        "state_tax_tx": StateTaxTxPolicyData,
    },
}


def get_domain_schema(domain: str, name: str) -> type[BaseModel] | None:
    """Return the pydantic model class for the given domain/name, or None if unknown."""
    return _DOMAIN_SCHEMAS.get(domain, {}).get(name)
