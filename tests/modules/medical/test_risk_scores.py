"""Tests for medical risk scores: CHA2DS2-VASc, HAS-BLED, Framingham."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.medical  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


class TestCHA2DS2VASc:
    def test_zero_score(self) -> None:
        r = REGISTRY.invoke(
            "medical.cha2ds2_vasc",
            age=40, female=False, chf=False, hypertension=False,
            diabetes=False, stroke_or_tia=False, vascular_disease=False,
        )
        assert r["score"] == 0
        assert r["risk_level"] == "low"

    def test_maximum_score(self) -> None:
        r = REGISTRY.invoke(
            "medical.cha2ds2_vasc",
            age=80, female=True, chf=True, hypertension=True,
            diabetes=True, stroke_or_tia=True, vascular_disease=True,
        )
        # 1+1+2+1+2+1+1 = 9
        assert r["score"] == 9
        assert r["risk_level"] == "high"

    def test_age_65_to_74_one_point(self) -> None:
        r = REGISTRY.invoke(
            "medical.cha2ds2_vasc",
            age=70, female=False,
        )
        assert r["score"] == 1

    def test_age_gte_75_two_points(self) -> None:
        r = REGISTRY.invoke(
            "medical.cha2ds2_vasc",
            age=76, female=False,
        )
        assert r["score"] == 2


class TestHASBLED:
    def test_zero(self) -> None:
        flags = {k: False for k in [
            "hypertension", "abnormal_renal", "abnormal_liver", "stroke",
            "bleeding_history", "labile_inr", "elderly", "drugs", "alcohol",
        ]}
        r = REGISTRY.invoke("medical.has_bled", **flags)
        assert r["score"] == 0
        assert r["risk_level"] == "low"

    def test_all_positive(self) -> None:
        flags = {k: True for k in [
            "hypertension", "abnormal_renal", "abnormal_liver", "stroke",
            "bleeding_history", "labile_inr", "elderly", "drugs", "alcohol",
        ]}
        r = REGISTRY.invoke("medical.has_bled", **flags)
        assert r["score"] == 9
        assert r["risk_level"] == "high"

    def test_high_risk_threshold(self) -> None:
        flags = {k: False for k in [
            "hypertension", "abnormal_renal", "abnormal_liver", "stroke",
            "bleeding_history", "labile_inr", "elderly", "drugs", "alcohol",
        ]}
        flags["hypertension"] = True
        flags["stroke"] = True
        flags["elderly"] = True
        r = REGISTRY.invoke("medical.has_bled", **flags)
        assert r["score"] == 3
        assert r["risk_level"] == "high"


class TestFramingham:
    def test_healthy_male_low_risk(self) -> None:
        r = REGISTRY.invoke(
            "medical.framingham_cvd_10y",
            sex="male", age=40, total_chol="180", hdl="60", sbp="110",
            treated_htn=False, smoker=False, diabetes=False,
        )
        risk = Decimal(r["risk"])
        assert Decimal("0") <= risk <= Decimal("0.05")

    def test_high_risk_male(self) -> None:
        r = REGISTRY.invoke(
            "medical.framingham_cvd_10y",
            sex="male", age=70, total_chol="260", hdl="35", sbp="160",
            treated_htn=True, smoker=True, diabetes=True,
        )
        risk = Decimal(r["risk"])
        # 해당 프로파일은 10년 일반 CVD 위험 ≥ 0.4
        assert risk > Decimal("0.3")

    def test_invalid_sex_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke(
                "medical.framingham_cvd_10y",
                sex="other", age=55, total_chol="200", hdl="50", sbp="125",
                treated_htn=False, smoker=False, diabetes=False,
            )

    def test_age_outside_range_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke(
                "medical.framingham_cvd_10y",
                sex="male", age=80, total_chol="200", hdl="50", sbp="125",
                treated_htn=False, smoker=False, diabetes=False,
            )


class TestBatchRaceFree:
    def test_cha_race_free(self) -> None:
        baseline = REGISTRY.invoke(
            "medical.cha2ds2_vasc",
            age=70, female=True, hypertension=True,
        )["score"]

        def run() -> int:
            r = REGISTRY.invoke(
                "medical.cha2ds2_vasc",
                age=70, female=True, hypertension=True,
            )
            return r["score"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            results = [f.result() for f in [ex.submit(run) for _ in range(100)]]
        for r in results:
            assert r == baseline
