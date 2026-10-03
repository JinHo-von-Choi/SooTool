"""Tests for tax.kr_withholding_simple tool (근로소득 간이세액표).

Author: 최진호
Date: 2026-04-22
Modified: 2026-10-03

기대값은 소득세법 시행령 [별표 2] <개정 2026. 2. 27.> 본표와 하단 산식, 제3호·제4호에서 직접 옮겼다.
"""
from __future__ import annotations

from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest
import yaml

import sootool.modules.tax  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.tax.kr_withholding import (
    _calc_labor_income_deduction,
    monthly_withholding_tax,
)
from sootool.policies import UnsupportedPolicyError

_POLICY_DIR = Path(__file__).resolve().parents[3] / "src" / "sootool" / "policies" / "tax"
_MARCH_FILE = _POLICY_DIR / "kr_withholding_2026@2026-03-01.yaml"
_JAN_FILE   = _POLICY_DIR / "kr_withholding_2026.yaml"


def call_withholding(**kwargs):
    return REGISTRY.invoke("tax.kr_withholding_simple", **kwargs)


def tax_of(salary: str, dependents: int = 1, children: int = 0, **extra) -> int:
    result = call_withholding(
        monthly_salary=salary, dependents=dependents, children_8_20=children, year=2026, **extra,
    )
    return int(result["withheld_tax"])


def _data(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["data"]


class TestTableLookup:
    def test_3010k_family_1(self):
        """3,000천원 이상 3,020천원 미만, 가족 1명: 74,350원."""
        assert tax_of("3010000", 1) == 74350

    def test_3010k_family_2(self):
        assert tax_of("3010000", 2) == 56850

    def test_3010k_family_4(self):
        assert tax_of("3010000", 4) == 26690

    def test_3000k_boundary_is_lower_inclusive(self):
        """3,000천원은 3,000~3,020 행, 2,999,999원은 2,990~3,000 행(73,060원)."""
        assert tax_of("3000000", 1) == 74350
        assert tax_of("2999999", 1) == 73060

    def test_row_lookup_truncates_below_thousand_won(self):
        """3,019,999원은 3,019천원으로 같은 행, 3,020,000원은 다음 행(76,060원)."""
        assert tax_of("3019999", 1) == 74350
        assert tax_of("3020000", 1) == 76060

    def test_770k_boundary_and_below(self):
        assert tax_of("769999", 1) == 0
        assert tax_of("770000", 1) == 0
        assert tax_of("0", 1) == 0

    def test_first_positive_row(self):
        """1,060천원 이상 1,065천원 미만, 가족 1명: 1,040원. 바로 아래 행은 0원."""
        assert tax_of("1060000", 1) == 1040
        assert tax_of("1059999", 1) == 0

    def test_reference_rows(self):
        assert tax_of("2005000", 1) == 19520
        assert tax_of("5010000", 1) == 335470
        assert tax_of("7010000", 1) == 732700

    def test_trace_records_row(self):
        result = call_withholding(monthly_salary="3010000", dependents=1, year=2026)
        assert result["lookup"]["method"] == "table_row"
        assert result["lookup"]["row"] == {"lower_k": 3000, "upper_k": 3020}
        steps = {s["label"]: s["value"] for s in result["trace"]["steps"]}
        assert steps["table_row"] == {"lower_k": 3000, "upper_k": 3020}
        assert steps["table_tax"] == "74350"


class TestUpperRows:
    def test_exactly_10000k(self):
        assert tax_of("10000000", 1) == 1507400
        assert tax_of("10000000", 11) == 960840

    def test_last_table_row_below_10000k(self):
        assert tax_of("9999999", 1) == 1503990

    def test_14000k_first_segment_end(self):
        """1,507,400 + 4,000,000 x 98% x 35% + 25,000 = 2,904,400."""
        assert tax_of("14000000", 1) == 2904400

    def test_20000k_second_segment(self):
        """1,507,400 + 1,397,000 + 6,000,000 x 98% x 38% = 5,138,800."""
        assert tax_of("20000000", 1) == 5138800

    def test_20000k_family_3(self):
        """1,200,840 + 1,397,000 + 6,000,000 x 98% x 38% = 4,832,240."""
        assert tax_of("20000000", 3) == 4832240

    def test_100000k_last_segment(self):
        """1,507,400 + 31,034,600 + 13,000,000 x 45% = 38,392,000."""
        assert tax_of("100000000", 1) == 38392000

    def test_fraction_below_won_is_dropped(self):
        """10,000,001원: 1,532,400.343원 산출, 원 미만 버림."""
        assert tax_of("10000001", 1) == 1532400

    def test_segment_boundaries_are_continuous(self):
        """14,000천원 경계 양쪽 세액 차이는 1원 미만 산식 증분뿐이다."""
        at  = tax_of("14000000", 1)
        nxt = tax_of("14000001", 1)
        assert 0 <= nxt - at <= 1


class TestFamilyAndChildren:
    def test_family_12_and_13(self):
        """5,000~5,020 행: 10명 106,600, 11명 87,850. 12명 69,100, 13명 50,350 (별표 2 제4호)."""
        assert tax_of("5010000", 12) == 69100
        assert tax_of("5010000", 13) == 50350

    def test_family_over_max_never_negative(self):
        """3,000~3,020 행: 11명 0원, 10명 3,600원. 12명 산식 결과가 음수이면 0원."""
        assert tax_of("3010000", 12) == 0

    def test_child_reductions_after_march(self):
        """5,000~5,020 행 가족 4명 219,100원에서 20,830 / 45,830 / 45,830+33,330 / 45,830+2x33,330 차감."""
        assert tax_of("5010000", 4, 0) == 219100
        assert tax_of("5010000", 4, 1) == 198270
        assert tax_of("5010000", 4, 2) == 173270
        assert tax_of("5010000", 5, 3) == 200350 - (45830 + 33330)
        assert tax_of("5010000", 5, 4) == 200350 - (45830 + 2 * 33330)

    def test_child_reduction_floor_zero(self):
        """3,000~3,020 행 가족 3명 31,940원: 자녀 1명 11,110원, 2명은 음수라 0원."""
        assert tax_of("3010000", 3, 1) == 11110
        assert tax_of("3010000", 3, 2) == 0

    def test_child_reduction_before_march(self):
        """2026.2.28.까지 원천징수분은 2024.2.29. 개정 별표 2: 12,500 / 29,160 / +25,000원."""
        assert tax_of("5010000", 4, 1, as_of="2026-02-01") == 206600
        assert tax_of("5010000", 4, 2, as_of="2026-02-01") == 189940
        assert tax_of("5010000", 5, 3, as_of="2026-02-01") == 200350 - (29160 + 25000)

    def test_default_version_is_march(self):
        result = call_withholding(monthly_salary="5010000", dependents=4, children_8_20=1, year=2026)
        assert result["policy_effective_date"] == "2026-03-01"
        assert result["withheld_tax"] == "198270"

    def test_children_exceeding_family_raises(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="3000000", dependents=2, children_8_20=2, year=2026)

    def test_negative_children_raises(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="3000000", dependents=2, children_8_20=-1, year=2026)


class TestPublicFunction:
    def test_monthly_withholding_tax_matches_table(self):
        data = _data(_MARCH_FILE)
        assert monthly_withholding_tax(Decimal("3010000"), 2, 0, data) == Decimal("56850")
        assert monthly_withholding_tax(Decimal("5010000"), 4, 1, data) == Decimal("198270")

    def test_labor_income_deduction_brackets(self):
        """소득세법 제47조제1항: 총급여 3,000만원 → 750만 + 1,500만 x 15% = 975만원."""
        data = _data(_MARCH_FILE)
        assert _calc_labor_income_deduction(Decimal("30000000"), data["labor_income_deduction_brackets"]) == Decimal("9750000")

    def test_labor_income_deduction_cap(self):
        """같은 항 단서: 공제액 2천만원 한도. 총급여 5억원이면 1,475만 + 4억 x 2% = 2,275만원 → 2천만원."""
        data = _data(_MARCH_FILE)
        brackets = data["labor_income_deduction_brackets"]
        cap      = Decimal(str(data["labor_income_deduction_cap"]))
        assert _calc_labor_income_deduction(Decimal("500000000"), brackets) == Decimal("22750000")
        assert _calc_labor_income_deduction(Decimal("500000000"), brackets, cap) == Decimal("20000000")
        assert _calc_labor_income_deduction(Decimal("30000000"), brackets, cap) == Decimal("9750000")


class TestTableStructure:
    @pytest.mark.parametrize("path", [_JAN_FILE, _MARCH_FILE])
    def test_rows_are_contiguous_and_complete(self, path):
        table = _data(path)["simple_tax_table"]
        rows  = table["rows"]
        assert rows[0][0] == 770
        assert rows[-1][1] == table["at_upper_salary_k"] == 10000
        assert len(rows) == 646
        for prev, cur in pairwise(rows):
            assert prev[1] == cur[0]
        for lower, upper, taxes in rows:
            assert lower < upper
            assert len(taxes) == table["max_family"] == 11

    @pytest.mark.parametrize("path", [_JAN_FILE, _MARCH_FILE])
    def test_monotone_in_salary_and_family(self, path):
        table = _data(path)["simple_tax_table"]
        rows  = [r[2] for r in table["rows"]] + [table["at_upper"]]
        for prev, cur in pairwise(rows):
            assert all(a <= b for a, b in zip(prev, cur, strict=True))
        for taxes in rows:
            assert all(a >= b for a, b in pairwise(taxes))

    def test_above_upper_segments_are_continuous(self):
        """각 구간 끝의 가산액이 다음 구간의 가산액과 같다 (1,397,000 / 6,610,600 / 7,394,600 / 13,394,600 / 31,034,600)."""
        segments = _data(_MARCH_FILE)["simple_tax_table"]["above_upper"]
        for seg, nxt in pairwise(segments):
            span = Decimal(seg["upper_k"] - seg["over_k"]) * 1000
            end  = Decimal(str(seg["add"])) + span * Decimal(str(seg["factor"])) * Decimal(str(seg["rate"]))
            assert end == Decimal(str(nxt["add"]))

    def test_versions_share_the_same_main_table(self):
        jan, mar = _data(_JAN_FILE), _data(_MARCH_FILE)
        assert jan["simple_tax_table"] == mar["simple_tax_table"]
        assert jan["child_reduction_monthly"]["one"] == 12500
        assert mar["child_reduction_monthly"]["one"] == 20830


class TestValidation:
    def test_returns_policy_version(self):
        result = call_withholding(monthly_salary="5000000", dependents=1, year=2026)
        assert result["policy_version"]["year"] == 2026

    def test_invalid_negative_salary(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="-1", dependents=1, year=2026)

    def test_invalid_zero_dependents(self):
        with pytest.raises(InvalidInputError):
            call_withholding(monthly_salary="3000000", dependents=0, year=2026)

    def test_unsupported_year(self):
        with pytest.raises(UnsupportedPolicyError):
            call_withholding(monthly_salary="3000000", dependents=1, year=2099)
