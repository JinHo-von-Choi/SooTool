"""Tests for geometry matrix tools: multiply, determinant, inverse, solve."""
from __future__ import annotations

from decimal import Decimal

import pytest

import sootool.modules.geometry  # noqa: F401
from sootool.core.errors import DomainConstraintError
from sootool.core.registry import REGISTRY


def _mul(A: list, B: list) -> dict:
    return REGISTRY.invoke("geometry.matrix_multiply", A=A, B=B)


def _det(M: list) -> dict:
    return REGISTRY.invoke("geometry.matrix_determinant", M=M)


def _inv(M: list) -> dict:
    return REGISTRY.invoke("geometry.matrix_inverse", M=M)


def _solve(A: list, b: list) -> dict:
    return REGISTRY.invoke("geometry.matrix_solve", A=A, b=b)


class TestMatrixMultiply:
    def test_multiply_2x2_identity(self) -> None:
        A    = [["1", "2"], ["3", "4"]]
        iden = [["1", "0"], ["0", "1"]]
        result = _mul(A, iden)
        R = result["result"]
        assert R[0] == ["1", "2"]
        assert R[1] == ["3", "4"]

    def test_multiply_2x2(self) -> None:
        # [[1,2],[3,4]] @ [[5,6],[7,8]]
        # = [[1*5+2*7, 1*6+2*8], [3*5+4*7, 3*6+4*8]]
        # = [[19, 22], [43, 50]]
        A = [["1", "2"], ["3", "4"]]
        B = [["5", "6"], ["7", "8"]]
        result = _mul(A, B)
        R = result["result"]
        assert Decimal(R[0][0]) == Decimal("19")
        assert Decimal(R[0][1]) == Decimal("22")
        assert Decimal(R[1][0]) == Decimal("43")
        assert Decimal(R[1][1]) == Decimal("50")

    def test_multiply_non_square(self) -> None:
        # 2x3 @ 3x2 = 2x2
        A = [["1", "0", "1"], ["2", "1", "0"]]
        B = [["1", "2"], ["3", "4"], ["5", "6"]]
        result = _mul(A, B)
        R = result["result"]
        # Row 0: [1+0+5, 2+0+6] = [6, 8]
        # Row 1: [2+3+0, 4+4+0] = [5, 8]
        assert Decimal(R[0][0]) == Decimal("6")
        assert Decimal(R[0][1]) == Decimal("8")
        assert Decimal(R[1][0]) == Decimal("5")
        assert Decimal(R[1][1]) == Decimal("8")

    def test_multiply_1x1(self) -> None:
        result = _mul([["3"]], [["7"]])
        assert Decimal(result["result"][0][0]) == Decimal("21")

    def test_multiply_dimension_mismatch_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _mul([["1", "2"], ["3", "4"]], [["1", "0", "0"]])

    def test_multiply_trace(self) -> None:
        result = _mul([["1"]], [["1"]])
        assert result["trace"]["tool"] == "geometry.matrix_multiply"

    # Property: (A@B) ≠ (B@A) in general (non-commutative)
    def test_multiply_non_commutative(self) -> None:
        A = [["1", "2"], ["3", "4"]]
        B = [["5", "6"], ["7", "8"]]
        ab = _mul(A, B)["result"]
        ba = _mul(B, A)["result"]
        # At least one element should differ
        assert any(
            Decimal(ab[i][j]) != Decimal(ba[i][j])
            for i in range(2)
            for j in range(2)
        )


class TestMatrixDeterminant:
    def test_det_1x1(self) -> None:
        result = _det([["5"]])
        assert Decimal(result["result"]) == Decimal("5")

    def test_det_2x2(self) -> None:
        # [[a,b],[c,d]] → ad - bc = 1*4 - 2*3 = -2
        result = _det([["1", "2"], ["3", "4"]])
        assert Decimal(result["result"]) == Decimal("-2")

    def test_det_2x2_identity(self) -> None:
        result = _det([["1", "0"], ["0", "1"]])
        assert Decimal(result["result"]) == Decimal("1")

    def test_det_3x3(self) -> None:
        # [[1,2,3],[4,5,6],[7,8,9]] → 0 (rows are linearly dependent)
        result = _det([["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
        assert abs(Decimal(result["result"])) < Decimal("1E-10")

    def test_det_3x3_nonzero(self) -> None:
        # [[1,0,0],[0,2,0],[0,0,3]] → 6
        result = _det([["1", "0", "0"], ["0", "2", "0"], ["0", "0", "3"]])
        assert abs(Decimal(result["result"]) - Decimal("6")) < Decimal("1E-10")

    def test_det_4x4_numpy(self) -> None:
        # 4x4 diagonal matrix: det = product of diagonal = 1*2*3*4 = 24
        M = [
            ["1", "0", "0", "0"],
            ["0", "2", "0", "0"],
            ["0", "0", "3", "0"],
            ["0", "0", "0", "4"],
        ]
        result = _det(M)
        assert abs(Decimal(result["result"]) - Decimal("24")) < Decimal("0.001")

    def test_det_trace(self) -> None:
        result = _det([["1", "0"], ["0", "1"]])
        assert result["trace"]["tool"] == "geometry.matrix_determinant"

    def test_det_non_square_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _det([["1", "2", "3"], ["4", "5", "6"]])


class TestMatrixInverse:
    def test_inverse_2x2_identity(self) -> None:
        result = _inv([["1", "0"], ["0", "1"]])
        R = result["result"]
        assert abs(float(R[0][0]) - 1.0) < 1e-10
        assert abs(float(R[0][1]) - 0.0) < 1e-10

    def test_inverse_2x2(self) -> None:
        # inv([[2,1],[5,3]]) = [[3,-1],[-5,2]]
        result = _inv([["2", "1"], ["5", "3"]])
        R = result["result"]
        assert abs(float(R[0][0]) - 3.0) < 1e-10
        assert abs(float(R[0][1]) + 1.0) < 1e-10
        assert abs(float(R[1][0]) + 5.0) < 1e-10
        assert abs(float(R[1][1]) - 2.0) < 1e-10

    def test_inverse_roundtrip(self) -> None:
        """inv(M) @ M should equal I within float64 tolerance."""
        M_str = [["2", "1"], ["5", "3"]]
        inv_result = _inv(M_str)
        inv_rows = inv_result["result"]

        M_np    = [[float(v) for v in row] for row in M_str]
        inv_np  = [[float(v) for v in row] for row in inv_rows]

        product = [[sum(inv_np[i][k] * M_np[k][j]
                        for k in range(2))
                    for j in range(2)]
                   for i in range(2)]

        # Should be close to identity
        assert abs(product[0][0] - 1.0) < 1e-10
        assert abs(product[0][1] - 0.0) < 1e-10
        assert abs(product[1][0] - 0.0) < 1e-10
        assert abs(product[1][1] - 1.0) < 1e-10

    def test_inverse_singular_raises(self) -> None:
        # Singular matrix has no inverse
        with pytest.raises(DomainConstraintError):
            _inv([["1", "2"], ["2", "4"]])

    def test_inverse_trace(self) -> None:
        result = _inv([["1", "0"], ["0", "1"]])
        assert result["trace"]["tool"] == "geometry.matrix_inverse"

    # Property: det(inv(M)) = 1/det(M)
    def test_inverse_det_relation(self) -> None:
        M = [["2", "1"], ["5", "3"]]
        det_m   = float(_det(M)["result"])                  # det = 1
        inv_r   = _inv(M)["result"]
        det_inv = float(_det(inv_r)["result"])               # det(inv) should be 1 too
        assert abs(det_m * det_inv - 1.0) < 1e-10


class TestMatrixSolve:
    def test_solve_2x2_known(self) -> None:
        # 2x + y = 1, 5x + 3y = 2 → x=1, y=-1
        A = [["2", "1"], ["5", "3"]]
        b = ["1", "2"]
        result = _solve(A, b)
        x = result["x"]
        assert abs(float(x[0]) - 1.0) < 1e-10
        assert abs(float(x[1]) + 1.0) < 1e-10

    def test_solve_3x3(self) -> None:
        # [[1,0,0],[0,1,0],[0,0,1]] * [1,2,3] = [1,2,3]
        A = [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]]
        b = ["1", "2", "3"]
        result = _solve(A, b)
        x = result["x"]
        assert abs(float(x[0]) - 1.0) < 1e-10
        assert abs(float(x[1]) - 2.0) < 1e-10
        assert abs(float(x[2]) - 3.0) < 1e-10

    def test_solve_verification(self) -> None:
        """Verify A @ x ≈ b."""
        A  = [["2", "1"], ["5", "3"]]
        b  = ["4", "7"]
        x  = [float(v) for v in _solve(A, b)["x"]]
        Af = [[float(v) for v in row] for row in A]
        bf = [float(v) for v in b]

        for i in range(len(bf)):
            dot = sum(Af[i][j] * x[j] for j in range(len(x)))
            assert abs(dot - bf[i]) < 1e-10

    def test_solve_singular_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _solve([["1", "2"], ["2", "4"]], ["1", "2"])

    def test_solve_size_mismatch_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _solve([["1", "0"], ["0", "1"]], ["1", "2", "3"])

    def test_solve_trace(self) -> None:
        result = _solve([["1", "0"], ["0", "1"]], ["3", "4"])
        assert result["trace"]["tool"] == "geometry.matrix_solve"
