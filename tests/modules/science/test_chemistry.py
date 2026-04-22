"""Tests for science chemistry tools: molar_mass, stoichiometry."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.science  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _mm(formula: str) -> dict:
    return REGISTRY.invoke("science.molar_mass", formula=formula)


def _stoich(
    reactants: list[dict],
    products: list[dict],
    coefficients: dict,
) -> dict:
    return REGISTRY.invoke(
        "science.stoichiometry",
        reactants=reactants,
        products=products,
        coefficients=coefficients,
    )


class TestMolarMass:
    def test_molar_mass_water(self) -> None:
        """H2O: H=1.008*2 + O=15.999 = 18.015."""
        r = _mm("H2O")
        mm = Decimal(r["molar_mass"])
        expected = Decimal("1.008") * 2 + Decimal("15.999")
        assert abs(mm - expected) < Decimal("0.001")
        assert r["composition"] == {"H": 2, "O": 1}

    def test_molar_mass_parens_ca_oh2(self) -> None:
        """Ca(OH)2: Ca=40.078 + 2*(O=15.999+H=1.008) = 40.078 + 34.014 = 74.092."""
        r = _mm("Ca(OH)2")
        mm = Decimal(r["molar_mass"])
        expected = Decimal("40.078") + 2 * (Decimal("15.999") + Decimal("1.008"))
        assert abs(mm - expected) < Decimal("0.01")
        assert r["composition"]["Ca"] == 1
        assert r["composition"]["O"] == 2
        assert r["composition"]["H"] == 2

    def test_molar_mass_hydrate_cuso4_5h2o(self) -> None:
        """CuSO4.5H2O: Cu=63.546+S=32.06+O=4*15.999+5*(2*1.008+15.999)."""
        r = _mm("CuSO4.5H2O")
        mm = Decimal(r["molar_mass"])
        # CuSO4: 63.546 + 32.06 + 4*15.999 = 159.602
        # 5*H2O: 5*(2*1.008+15.999) = 5*18.015 = 90.075
        # Total: 249.677
        assert abs(mm - Decimal("249.677")) < Decimal("0.1")
        assert r["composition"]["Cu"] == 1
        assert r["composition"]["S"] == 1
        assert r["composition"]["O"] == 9  # 4 + 5
        assert r["composition"]["H"] == 10  # 5*2

    def test_molar_mass_simple_element(self) -> None:
        """Fe single element."""
        r = _mm("Fe")
        mm = Decimal(r["molar_mass"])
        assert abs(mm - Decimal("55.845")) < Decimal("0.001")

    def test_molar_mass_sodium_chloride(self) -> None:
        """NaCl: Na=22.98976928 + Cl=35.45."""
        r = _mm("NaCl")
        mm = Decimal(r["molar_mass"])
        expected = Decimal("22.98976928") + Decimal("35.45")
        assert abs(mm - expected) < Decimal("0.001")

    def test_molar_mass_nested_parens(self) -> None:
        """Al2(SO4)3: 2*Al + 3*(S+4*O)."""
        r = _mm("Al2(SO4)3")
        mm = Decimal(r["molar_mass"])
        expected = (
            Decimal("26.9815384") * 2
            + (Decimal("32.06") + 4 * Decimal("15.999")) * 3
        )
        assert abs(mm - expected) < Decimal("0.01")

    def test_molar_mass_unknown_element_raises(self) -> None:
        with pytest.raises(DomainConstraintError, match="알 수 없는 원소"):
            _mm("Xy3")

    def test_molar_mass_empty_formula_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _mm("")

    def test_molar_mass_invalid_chars_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _mm("H2@O")

    def test_molar_mass_trace(self) -> None:
        r = _mm("H2O")
        assert "trace" in r
        assert r["trace"]["tool"] == "science.molar_mass"


class TestStoichiometry:
    def test_stoich_2h2_o2_2h2o_mass_based(self) -> None:
        """2H2 + O2 -> 2H2O: given 4g H2 and excess O2 -> ~36g H2O."""
        # Molar mass H2 = 2*1.008 = 2.016 g/mol
        # 4g H2 = 4/2.016 ≈ 1.984 mol H2
        # Coefficient H2=2, so scale = 1.984/2 ≈ 0.992
        # H2O: 2 * 0.992 = 1.984 mol H2O
        # mass H2O ≈ 1.984 * 18.015 ≈ 35.73g  (close to 36g theoretical)
        r = _stoich(
            reactants=[
                {"formula": "H2",  "mass": "4"},
                {"formula": "O2",  "mass": "100"},  # excess
            ],
            products=[{"formula": "H2O"}],
            coefficients={"H2": 2, "O2": 1, "H2O": 2},
        )
        h2o_mass = Decimal(r["masses"]["H2O"])
        # Should be approximately 35.73g (H2 is the limiting reagent when O2 is excess)
        assert abs(h2o_mass - Decimal("35.73")) < Decimal("0.5")

    def test_stoich_limiting_reagent_h2_limiting(self) -> None:
        """2H2 + O2 -> 2H2O: given 2 mol H2, 2 mol O2 -> H2 is limiting."""
        r = _stoich(
            reactants=[
                {"formula": "H2", "moles": "2"},
                {"formula": "O2", "moles": "2"},
            ],
            products=[{"formula": "H2O"}],
            coefficients={"H2": 2, "O2": 1, "H2O": 2},
        )
        assert r["limiting_reagent"] == "H2"
        # H2: scale = 2/2 = 1, O2: scale = 2/1 = 2 => H2 is limiting
        h2o_moles = Decimal(r["moles"]["H2O"])
        # scale = 1, H2O coeff = 2 => 2 mol H2O
        assert abs(h2o_moles - Decimal("2")) < Decimal("1E-6")

    def test_stoich_moles_based(self) -> None:
        """N2 + 3H2 -> 2NH3: given 1 mol N2, 6 mol H2."""
        r = _stoich(
            reactants=[
                {"formula": "N2", "moles": "1"},
                {"formula": "H2", "moles": "6"},
            ],
            products=[{"formula": "N2"}, {"formula": "H2"}, {"formula": "NH3"}],
            coefficients={"N2": 1, "H2": 3, "NH3": 2},
        )
        # N2: scale = 1/1 = 1; H2: scale = 6/3 = 2 => N2 limiting
        assert r["limiting_reagent"] == "N2"
        nh3_moles = Decimal(r["moles"]["NH3"])
        # scale=1, NH3 coeff=2 => 2 mol NH3
        assert abs(nh3_moles - Decimal("2")) < Decimal("1E-6")

    def test_stoich_missing_mass_and_moles_raises(self) -> None:
        with pytest.raises(InvalidInputError, match="mass 또는 moles"):
            _stoich(
                reactants=[{"formula": "H2"}],
                products=[{"formula": "H2O"}],
                coefficients={"H2": 2, "O2": 1, "H2O": 2},
            )

    def test_stoich_formula_not_in_coefficients_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _stoich(
                reactants=[{"formula": "CO2", "moles": "1"}],
                products=[{"formula": "CO"}],
                coefficients={"H2": 2, "O2": 1},
            )

    def test_stoich_empty_reactants_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _stoich([], [{"formula": "H2O"}], {"H2O": 1})

    def test_stoich_trace(self) -> None:
        r = _stoich(
            reactants=[{"formula": "H2", "moles": "1"}, {"formula": "O2", "moles": "1"}],
            products=[{"formula": "H2O"}],
            coefficients={"H2": 2, "O2": 1, "H2O": 2},
        )
        assert "trace" in r
        assert r["trace"]["tool"] == "science.stoichiometry"


class TestScienceBatchRaceFree:
    def test_science_batch_race_free(self) -> None:
        expected_mm = _mm("H2O")["molar_mass"]

        def run() -> str:
            return _mm("H2O")["molar_mass"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected_mm, "Race condition in molar_mass"
