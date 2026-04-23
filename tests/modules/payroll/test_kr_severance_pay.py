"""Tests for payroll.kr_severance_pay."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.payroll  # noqa: F401
import sootool.modules.tax  # noqa: F401
from sootool.core.batch import BatchExecutor
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


def call(**kwargs):
    return REGISTRY.invoke("payroll.kr_severance_pay", **kwargs)


class TestKrSeverancePayBasic:
    def test_100m_10years(self):
        r = call(severance_amount="100000000", service_years="10", year=2026)
        assert Decimal(r["severance"])         == Decimal("100000000")
        assert Decimal(r["service_deduction"]) == Decimal("15000000")
        assert Decimal(r["converted_salary"])  == Decimal("102000000")
        assert Decimal(r["tax"])               == Decimal("3875000")

    def test_short_service_5years_raises_no_error(self):
        r = call(severance_amount="30000000", service_years="5", year=2026)
        assert Decimal(r["service_deduction"]) == Decimal("5000000")
        assert Decimal(r["tax"]) > Decimal("0")

    def test_long_service_25years(self):
        r = call(severance_amount="500000000", service_years="25", year=2026)
        # 25년: 20년까지 4000만 + 5년 * 300만 = 5500만
        assert Decimal(r["service_deduction"]) == Decimal("55000000")
        assert Decimal(r["tax"]) > Decimal("0")

    def test_non_taxable_reduces_base(self):
        r = call(
            severance_amount="50000000", service_years="10", year=2026,
            non_taxable="10000000",
        )
        assert Decimal(r["taxable_severance"]) == Decimal("40000000")

    def test_trace_and_policy_version(self):
        r = call(severance_amount="30000000", service_years="3", year=2026)
        assert r["trace"]["tool"] == "payroll.kr_severance_pay"
        assert r["policy_version"]["year"] == 2026
        assert "sha256" in r["policy_version"]
        assert r["policy_source"] == "package"


class TestKrSeverancePayValidation:
    def test_negative_severance_raises(self):
        with pytest.raises(InvalidInputError):
            call(severance_amount="-1", service_years="5", year=2026)

    def test_zero_years_raises(self):
        with pytest.raises(InvalidInputError):
            call(severance_amount="10000000", service_years="0", year=2026)

    def test_negative_years_raises(self):
        with pytest.raises(InvalidInputError):
            call(severance_amount="10000000", service_years="-1", year=2026)

    def test_non_taxable_exceeds_raises(self):
        with pytest.raises(InvalidInputError):
            call(
                severance_amount="5000000", service_years="5", year=2026,
                non_taxable="6000000",
            )

    def test_small_severance_under_deduction_yields_zero_tax(self):
        # 3년, 300만원 — 근속공제 300만 → taxable 0
        r = call(severance_amount="3000000", service_years="3", year=2026)
        assert Decimal(r["tax"]) == Decimal("0")


class TestKrSeverancePayBatch:
    def test_batch_race_free(self):
        executor = BatchExecutor(registry=REGISTRY, max_workers=16, deterministic=True)
        items = [
            {
                "id":   f"sev-{i}",
                "tool": "payroll.kr_severance_pay",
                "args": {
                    "severance_amount": "50000000",
                    "service_years":    "7",
                    "year":             2026,
                },
            }
            for i in range(100)
        ]
        response = executor.run(items)
        assert response["status"] == "all_ok"
        results = [r["result"] for r in response["results"]]
        first = results[0]
        for r in results[1:]:
            assert r["tax"] == first["tax"]
