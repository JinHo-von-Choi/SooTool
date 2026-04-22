"""Tests for geometry vector tools: dot, cross, norm."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.geometry  # noqa: F401
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY


def _dot(a: list[str], b: list[str]) -> dict:
    return REGISTRY.invoke("geometry.vector_dot", a=a, b=b)


def _cross(a: list[str], b: list[str]) -> dict:
    return REGISTRY.invoke("geometry.vector_cross", a=a, b=b)


def _norm(v: list[str], p: int = 2) -> dict:
    return REGISTRY.invoke("geometry.vector_norm", v=v, p=p)


class TestVectorDot:
    def test_dot_1_2_3_4_5_6(self) -> None:
        # [1,2,3]·[4,5,6] = 4+10+18 = 32
        result = _dot(["1", "2", "3"], ["4", "5", "6"])
        assert result["result"] == "32"

    def test_dot_unit_vectors(self) -> None:
        # [1,0,0]·[0,1,0] = 0 (orthogonal)
        result = _dot(["1", "0", "0"], ["0", "1", "0"])
        assert Decimal(result["result"]) == Decimal("0")

    def test_dot_parallel_vectors(self) -> None:
        # [1,0]·[2,0] = 2
        result = _dot(["1", "0"], ["2", "0"])
        assert Decimal(result["result"]) == Decimal("2")

    def test_dot_decimal_values(self) -> None:
        # [1.5, 2.5]·[2, 4] = 3 + 10 = 13
        result = _dot(["1.5", "2.5"], ["2", "4"])
        assert Decimal(result["result"]) == Decimal("13")

    def test_dot_negative_values(self) -> None:
        # [-1, 2]·[3, -4] = -3 - 8 = -11
        result = _dot(["-1", "2"], ["3", "-4"])
        assert Decimal(result["result"]) == Decimal("-11")

    def test_dot_single_element(self) -> None:
        result = _dot(["5"], ["3"])
        assert Decimal(result["result"]) == Decimal("15")

    def test_dot_trace(self) -> None:
        result = _dot(["1", "2"], ["3", "4"])
        assert result["trace"]["tool"] == "geometry.vector_dot"

    def test_dot_length_mismatch_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _dot(["1", "2", "3"], ["1", "2"])

    def test_dot_empty_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _dot([], [])

    # Property: a·b == b·a (commutativity)
    def test_dot_commutative(self) -> None:
        a = ["1", "2", "3"]
        b = ["4", "5", "6"]
        assert _dot(a, b)["result"] == _dot(b, a)["result"]


class TestVectorCross:
    def test_cross_unit_x_unit_y(self) -> None:
        # [1,0,0] × [0,1,0] = [0,0,1]
        result = _cross(["1", "0", "0"], ["0", "1", "0"])
        r = result["result"]
        assert Decimal(r[0]) == Decimal("0")
        assert Decimal(r[1]) == Decimal("0")
        assert Decimal(r[2]) == Decimal("1")

    def test_cross_unit_y_unit_z(self) -> None:
        # [0,1,0] × [0,0,1] = [1,0,0]
        result = _cross(["0", "1", "0"], ["0", "0", "1"])
        r = result["result"]
        assert Decimal(r[0]) == Decimal("1")
        assert Decimal(r[1]) == Decimal("0")
        assert Decimal(r[2]) == Decimal("0")

    def test_cross_unit_z_unit_x(self) -> None:
        # [0,0,1] × [1,0,0] = [0,1,0]
        result = _cross(["0", "0", "1"], ["1", "0", "0"])
        r = result["result"]
        assert Decimal(r[0]) == Decimal("0")
        assert Decimal(r[1]) == Decimal("1")
        assert Decimal(r[2]) == Decimal("0")

    def test_cross_anti_commutative(self) -> None:
        # a × b = -(b × a)
        a = ["1", "2", "3"]
        b = ["4", "5", "6"]
        ab = _cross(a, b)["result"]
        ba = _cross(b, a)["result"]
        for ab_i, ba_i in zip(ab, ba, strict=True):
            assert Decimal(ab_i) == -Decimal(ba_i)

    def test_cross_parallel_vectors_zero(self) -> None:
        # [1,0,0] × [2,0,0] = [0,0,0]
        result = _cross(["1", "0", "0"], ["2", "0", "0"])
        r = result["result"]
        assert all(Decimal(v) == Decimal("0") for v in r)

    def test_cross_general_values(self) -> None:
        # [1,2,3] × [4,5,6] = [2*6-3*5, 3*4-1*6, 1*5-2*4] = [-3, 6, -3]
        result = _cross(["1", "2", "3"], ["4", "5", "6"])
        r = result["result"]
        assert Decimal(r[0]) == Decimal("-3")
        assert Decimal(r[1]) == Decimal("6")
        assert Decimal(r[2]) == Decimal("-3")

    def test_cross_wrong_dimension_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _cross(["1", "2"], ["3", "4"])

    def test_cross_trace(self) -> None:
        result = _cross(["1", "0", "0"], ["0", "1", "0"])
        assert result["trace"]["tool"] == "geometry.vector_cross"


class TestVectorNorm:
    def test_norm_l2_3_4(self) -> None:
        # √(9+16) = √25 = 5
        result = _norm(["3", "4"])
        assert abs(Decimal(result["result"]) - Decimal("5")) < Decimal("1E-10")

    def test_norm_l2_1_0_0(self) -> None:
        # √1 = 1
        result = _norm(["1", "0", "0"])
        assert abs(Decimal(result["result"]) - Decimal("1")) < Decimal("1E-10")

    def test_norm_l1(self) -> None:
        # L1: |3| + |4| = 7
        result = _norm(["3", "4"], p=1)
        assert abs(Decimal(result["result"]) - Decimal("7")) < Decimal("1E-10")

    def test_norm_linf_approximation(self) -> None:
        # L-infinity approximated by large p: max(3, 4) = 4
        # Use p=1000 as approximation — should be very close to 4
        result = _norm(["3", "4"], p=1000)
        assert abs(Decimal(result["result"]) - Decimal("4")) < Decimal("0.01")

    def test_norm_zero_vector(self) -> None:
        result = _norm(["0", "0", "0"])
        assert abs(Decimal(result["result"]) - Decimal("0")) < Decimal("1E-10")

    def test_norm_single_element(self) -> None:
        result = _norm(["5"])
        assert abs(Decimal(result["result"]) - Decimal("5")) < Decimal("1E-10")

    def test_norm_negative_elements(self) -> None:
        # L2 of [-3, 4] = 5
        result = _norm(["-3", "4"])
        assert abs(Decimal(result["result"]) - Decimal("5")) < Decimal("1E-10")

    def test_norm_trace(self) -> None:
        result = _norm(["3", "4"])
        assert result["trace"]["tool"] == "geometry.vector_norm"

    def test_norm_invalid_p_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _norm(["1", "2"], p=0)

    def test_norm_empty_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _norm([])

    # Property: norm(s*v) == |s| * norm(v)
    def test_norm_scaling(self) -> None:
        v = ["3", "4"]
        norm_v = Decimal(_norm(v)["result"])
        # scale by 2: norm([6,8]) should be 2 * norm([3,4]) = 10
        norm_2v = Decimal(_norm(["6", "8"])["result"])
        assert abs(norm_2v - 2 * norm_v) < Decimal("1E-10")
