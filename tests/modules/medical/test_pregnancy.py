"""Tests for pregnancy gestational age calculator."""
from __future__ import annotations

import pytest

import sootool.modules.medical  # noqa: F401
import sootool.server  # noqa: F401  — registers core.batch
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY


class TestPregnancyWeeks:
    def test_pregnancy_week_20(self) -> None:
        """LMP exactly 20 weeks ago -> weeks=20, days=0, trimester=2."""
        from datetime import date, timedelta
        lmp = date.today() - timedelta(weeks=20)
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date=str(lmp),
        )
        assert result["weeks"] == 20
        assert result["days"] == 0
        assert result["trimester"] == 2
        assert "edd" in result
        assert "trace" in result

    def test_pregnancy_week_8_trimester_1(self) -> None:
        """8 weeks -> trimester 1."""
        from datetime import date, timedelta
        lmp = date.today() - timedelta(weeks=8)
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date=str(lmp),
        )
        assert result["weeks"] == 8
        assert result["trimester"] == 1

    def test_pregnancy_week_30_trimester_3(self) -> None:
        """30 weeks -> trimester 3."""
        from datetime import date, timedelta
        lmp = date.today() - timedelta(weeks=30)
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date=str(lmp),
        )
        assert result["weeks"] == 30
        assert result["trimester"] == 3

    def test_pregnancy_edd(self) -> None:
        """LMP=2025-10-01 -> EDD=2026-07-08 (280 days later)."""
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date="2025-10-01",
            reference_date="2025-10-15",
        )
        assert result["edd"] == "2026-07-08"

    def test_pregnancy_42_weeks_clamp(self) -> None:
        """LMP 50 weeks ago -> clamped to 42 weeks max."""
        from datetime import date, timedelta
        lmp = date.today() - timedelta(weeks=50)
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date=str(lmp),
        )
        assert result["weeks"] == 42
        assert result["days"] == 0

    def test_pregnancy_reference_date_explicit(self) -> None:
        """Explicit reference date gives reproducible result."""
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date="2026-01-01",
            reference_date="2026-05-08",
        )
        # 2026-01-01 to 2026-05-08 = 127 days = 18 weeks 1 day
        assert result["weeks"] == 18
        assert result["days"] == 1

    def test_pregnancy_lmp_after_reference_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.pregnancy_weeks",
                lmp_date="2026-06-01",
                reference_date="2026-01-01",
            )

    def test_pregnancy_invalid_date_format_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.pregnancy_weeks",
                lmp_date="01/01/2026",
            )

    def test_pregnancy_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "medical.pregnancy_weeks",
            lmp_date="2026-01-01",
            reference_date="2026-03-01",
        )
        trace = result["trace"]
        assert trace["tool"] == "medical.pregnancy_weeks"
        assert "inputs" in trace

    def test_medical_batch_race_free(self) -> None:
        """Multiple medical tools in batch -> deterministic results."""
        items = [
            {
                "tool":  "medical.bmi",
                "args":  {"height_m": "1.75", "weight_kg": "70"},
                "id":    "bmi1",
            },
            {
                "tool":  "medical.dose_weight_based",
                "args":  {"weight_kg": "70", "dose_per_kg": "5"},
                "id":    "dose1",
            },
        ]
        batch_result = REGISTRY.invoke(
            "core.batch",
            items=items,
            deterministic=True,
        )
        results_map = {r["id"]: r for r in batch_result["results"]}
        assert results_map["bmi1"]["result"]["bmi"] == "22.86"
        assert results_map["dose1"]["result"]["dose"] == "350"
