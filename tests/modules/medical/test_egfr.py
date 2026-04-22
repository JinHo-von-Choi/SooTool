"""Tests for eGFR calculator (CKD-EPI 2021)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.medical  # noqa: F401
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_VALID_STAGES = {"G1", "G2", "G3a", "G3b", "G4", "G5"}


class TestEGFR:
    def test_egfr_male_30_cr_1(self) -> None:
        """30yo male, creatinine=1.0 -> high eGFR, stage G1 or G2."""
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.0",
            age=30,
            sex="male",
        )
        egfr = Decimal(result["egfr"])
        assert egfr > Decimal("60")
        assert result["stage"] in {"G1", "G2"}
        assert "trace" in result

    def test_egfr_female_65_cr_1_5(self) -> None:
        """65yo female, creatinine=1.5 -> stage G3a roughly (eGFR 45-60)."""
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.5",
            age=65,
            sex="female",
        )
        stage = result["stage"]
        # CKD-EPI 2021 for 65yo female cr=1.5 gives approximately 37-43 -> G3b
        assert stage in {"G3a", "G3b"}

    def test_egfr_stage_g5_very_high_creatinine(self) -> None:
        """Very high creatinine -> G5."""
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="8.0",
            age=60,
            sex="male",
        )
        egfr = Decimal(result["egfr"])
        assert egfr < Decimal("15")
        assert result["stage"] == "G5"

    def test_egfr_valid_stage_enum(self) -> None:
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.2",
            age=45,
            sex="female",
        )
        assert result["stage"] in _VALID_STAGES

    def test_egfr_race_non_black_accepted(self) -> None:
        """race parameter accepted but CKD-EPI 2021 does not use it."""
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.0",
            age=40,
            sex="male",
            race="non_black",
        )
        assert "egfr" in result

    def test_egfr_one_decimal_place(self) -> None:
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.0",
            age=40,
            sex="male",
        )
        egfr_str = result["egfr"]
        parts = egfr_str.split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 1

    def test_egfr_invalid_sex_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.egfr",
                creatinine_mg_dl="1.0",
                age=40,
                sex="other",
            )

    def test_egfr_zero_creatinine_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.egfr",
                creatinine_mg_dl="0",
                age=40,
                sex="male",
            )

    def test_egfr_trace_structure(self) -> None:
        result = REGISTRY.invoke(
            "medical.egfr",
            creatinine_mg_dl="1.0",
            age=40,
            sex="male",
        )
        assert result["trace"]["tool"] == "medical.egfr"
