"""Geometry matrix tools: multiply, determinant, inverse, solve."""
from __future__ import annotations

from decimal import Decimal

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.limits import ensure_max
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult


def _parse_matrix(M: list[list[str]], name: str) -> list[list[Decimal]]:
    """Parse a matrix of string values to Decimal."""
    if isinstance(M, list):
        ensure_max("MATRIX_DIM", len(M), f"{name}.rows")
        for row in M:
            if isinstance(row, list):
                ensure_max("MATRIX_DIM", len(row), f"{name}.columns")
    try:
        result = []
        for row in M:
            result.append([D(str(v)) for v in row])
        return result
    except Exception as exc:
        raise InvalidInputError(f"{name} 변환 오류: {exc}") from exc


def _validate_square(M: list[list[Decimal]], name: str) -> int:
    n = len(M)
    if n == 0:
        raise DomainConstraintError(f"{name} 은(는) 비어있을 수 없습니다.")
    for i, row in enumerate(M):
        if len(row) != n:
            raise DomainConstraintError(
                f"{name}[{i}] 행 길이({len(row)})가 행렬 크기({n})와 다릅니다. 정방행렬이 아닙니다."
            )
    return n


def _decimal_matrix_to_float(M: list[list[Decimal]]) -> np.ndarray:
    return np.array([[float(v) for v in row] for row in M], dtype=np.float64)


def _float_matrix_to_str(M: np.ndarray) -> list[list[str]]:
    return [[str(D(repr(v))) for v in row] for row in M]


class MatrixMultiplyResult(TracedResult):
    result: list[list[str]]


@REGISTRY.tool(
    namespace="geometry",
    name="matrix_multiply",
    description=(
        "행렬 곱 A @ B 를 Decimal 로 계산한다. "
        "A 는 m×k, B 는 k×n 의 Decimal 문자열 2차원 리스트이며 A 의 열 수와 B 의 행 수가 같아야 한다. "
        "행과 열은 각각 200 이하. float 를 거치지 않아 반올림 오차가 없다. "
        "행렬 곱은 교환법칙이 성립하지 않으므로 A @ B 와 B @ A 는 다르다."
    ),
    version="1.0.0",
)
def matrix_multiply(A: list[list[str]], B: list[list[str]]) -> MatrixMultiplyResult:
    """Compute matrix multiplication A @ B using Decimal arithmetic.

    Args:
        A: m×k matrix as list of lists of Decimal strings.
        B: k×n matrix as list of lists of Decimal strings.

    Returns:
        {result: list[list[str]], trace}
    """
    trace = CalcTrace(tool="geometry.matrix_multiply", formula="C[i][j] = Σ A[i][k] * B[k][j]")
    trace.input("A", A)
    trace.input("B", B)

    am = _parse_matrix(A, "A")
    bm = _parse_matrix(B, "B")

    rows_a = len(am)
    if rows_a == 0:
        raise DomainConstraintError("A 는 비어있을 수 없습니다.")
    cols_a = len(am[0])

    rows_b = len(bm)
    if rows_b == 0:
        raise DomainConstraintError("B 는 비어있을 수 없습니다.")
    cols_b = len(bm[0])

    if cols_a != rows_b:
        raise DomainConstraintError(
            f"행렬 차원 불일치: A({rows_a}×{cols_a}) @ B({rows_b}×{cols_b}). "
            f"A의 열 수({cols_a})와 B의 행 수({rows_b})가 같아야 합니다."
        )

    # Decimal loop multiplication for precision
    result: list[list[Decimal]] = [
        [
            sum(
                (am[i][k] * bm[k][j] for k in range(cols_a)),
                D("0"),
            )
            for j in range(cols_b)
        ]
        for i in range(rows_a)
    ]

    result_str = [[str(v) for v in row] for row in result]

    trace.step("shape", f"({rows_a}×{cols_b})")
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


class MatrixDeterminantResult(TracedResult):
    result: str


@REGISTRY.tool(
    namespace="geometry",
    name="matrix_determinant",
    description=(
        "정방행렬 M 의 행렬식을 계산한다. "
        "M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). n 이 3 이하면 Decimal 로 정확히 전개하고 n 이 4 이상이면 numpy float64 로 계산해 약 15자리 정밀도만 보장한다. "
        "정방행렬이 아니면 오류이며 n≥4 결과는 근사값임에 유의한다."
    ),
    version="1.0.0",
)
def matrix_determinant(M: list[list[str]]) -> MatrixDeterminantResult:
    """Compute the determinant of a square matrix.

    Uses Decimal cofactor expansion for n ≤ 3, numpy for larger matrices.

    Args:
        M: n×n square matrix as list of lists of Decimal strings.

    Returns:
        {result: str, trace}
    """
    trace = CalcTrace(tool="geometry.matrix_determinant", formula="det(M)")
    trace.input("M", M)

    dm = _parse_matrix(M, "M")
    n  = _validate_square(dm, "M")

    if n == 1:
        det = dm[0][0]
    elif n == 2:
        det = dm[0][0] * dm[1][1] - dm[0][1] * dm[1][0]
    elif n == 3:
        a, b, c = dm[0]
        d, e, f = dm[1]
        g, h, i = dm[2]
        det = (a * (e * i - f * h)
               - b * (d * i - f * g)
               + c * (d * h - e * g))
    else:
        # n > 3: use numpy float64
        np_m = _decimal_matrix_to_float(dm)
        det  = D(repr(float(np.linalg.det(np_m))))

    trace.step("n",   str(n))
    trace.step("det", str(det))
    trace.output({"result": str(det)})

    return {"result": str(det), "trace": trace.to_dict()}


class MatrixInverseResult(TracedResult):
    result: list[list[str]]


@REGISTRY.tool(
    namespace="geometry",
    name="matrix_inverse",
    description=(
        "정방행렬의 역행렬을 numpy.linalg.inv(float64)로 계산한다. "
        "M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). 결과 원소는 float64 repr 문자열이라 '1e-05' 같은 지수 표기가 나올 수 있고 정밀도는 약 15자리다. "
        "특이행렬이면 오류. 연립방정식 해가 목적이면 역행렬을 곱하지 말고 matrix_solve 를 쓴다."
    ),
    version="1.0.0",
)
def matrix_inverse(M: list[list[str]]) -> MatrixInverseResult:
    """Compute the inverse of a square matrix using numpy.linalg.inv.

    Args:
        M: n×n invertible square matrix as list of lists of Decimal strings.

    Returns:
        {result: list[list[str]], trace}
    """
    trace = CalcTrace(tool="geometry.matrix_inverse", formula="M⁻¹ = numpy.linalg.inv(M)")
    trace.input("M", M)

    dm = _parse_matrix(M, "M")
    n  = _validate_square(dm, "M")

    np_m = _decimal_matrix_to_float(dm)

    try:
        inv = np.linalg.inv(np_m)
    except np.linalg.LinAlgError as exc:
        raise DomainConstraintError(f"역행렬이 존재하지 않습니다 (특이행렬): {exc}") from exc

    result_str = [[repr(float(v)) for v in row] for row in inv]

    trace.step("n",   str(n))
    trace.output({"result": result_str})

    return {"result": result_str, "trace": trace.to_dict()}


class MatrixSolveResult(TracedResult):
    x: list[str]


@REGISTRY.tool(
    namespace="geometry",
    name="matrix_solve",
    description=(
        "연립일차방정식 Ax = b 의 해 x 를 numpy.linalg.solve(float64)로 구한다. "
        "A 는 n×n Decimal 문자열 2차원 리스트, b 는 길이 n 리스트. 해는 float64 repr 문자열이며 정밀도는 약 15자리다. "
        "특이행렬이거나 b 의 길이가 n 과 다르면 오류. 비정방(과결정, 부족결정) 시스템은 지원하지 않는다."
    ),
    version="1.0.0",
)
def matrix_solve(A: list[list[str]], b: list[str]) -> MatrixSolveResult:
    """Solve the linear system Ax = b using numpy.linalg.solve.

    Args:
        A: n×n coefficient matrix as list of lists of Decimal strings.
        b: Right-hand side vector of n Decimal strings.

    Returns:
        {x: list[str], trace}
    """
    trace = CalcTrace(tool="geometry.matrix_solve", formula="x = numpy.linalg.solve(A, b)")
    trace.input("A", A)
    trace.input("b", b)

    dm = _parse_matrix(A, "A")
    n  = _validate_square(dm, "A")

    try:
        bv = [D(str(v)) for v in b]
    except Exception as exc:
        raise InvalidInputError(f"b 변환 오류: {exc}") from exc

    if len(bv) != n:
        raise DomainConstraintError(
            f"b 의 길이({len(bv)})가 A 의 크기({n})와 일치하지 않습니다."
        )

    np_a = _decimal_matrix_to_float(dm)
    np_b = np.array([float(v) for v in bv], dtype=np.float64)

    try:
        x_np = np.linalg.solve(np_a, np_b)
    except np.linalg.LinAlgError as exc:
        raise DomainConstraintError(f"선형 시스템이 풀리지 않습니다 (특이행렬): {exc}") from exc

    x_str = [repr(float(v)) for v in x_np]

    trace.step("x", x_str)
    trace.output({"x": x_str})

    return {"x": x_str, "trace": trace.to_dict()}
