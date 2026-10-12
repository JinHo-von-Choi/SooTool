"""Tests for geometry area tools."""
from __future__ import annotations

import concurrent.futures
import math
from decimal import ROUND_UP, Decimal, Inexact, localcontext

import pytest

import sootool.modules.geometry  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.modules.geometry.area import area_rectangle, area_triangle


def _circle(radius: str) -> dict:
    return REGISTRY.invoke("geometry.area_circle", radius=radius)


def _triangle(base: str, height: str) -> dict:
    return REGISTRY.invoke("geometry.area_triangle", base=base, height=height)


def _rectangle(width: str, height: str) -> dict:
    return REGISTRY.invoke("geometry.area_rectangle", width=width, height=height)


def _polygon(vertices: list) -> dict:
    return REGISTRY.invoke("geometry.area_polygon", vertices=vertices)


class TestAreaCircle:
    def test_area_circle_r5(self) -> None:
        result = _circle("5")
        area = Decimal(result["area"])
        # π*25 ≈ 78.5398...
        assert abs(area - Decimal("78.5398")) < Decimal("0.0001")

    def test_area_circle_r1(self) -> None:
        result = _circle("1")
        area = Decimal(result["area"])
        assert abs(area - Decimal(str(math.pi))) < Decimal("1E-10")

    def test_area_circle_r0(self) -> None:
        result = _circle("0")
        assert Decimal(result["area"]) == Decimal("0")

    def test_area_circle_r10(self) -> None:
        result = _circle("10")
        area = Decimal(result["area"])
        # π*100 ≈ 314.1592...
        assert abs(area - Decimal("314.1592")) < Decimal("0.0001")

    def test_area_circle_trace_present(self) -> None:
        result = _circle("5")
        assert "trace" in result
        assert result["trace"]["tool"] == "geometry.area_circle"

    def test_area_circle_negative_radius_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _circle("-1")

    def test_area_circle_invalid_input(self) -> None:
        with pytest.raises(InvalidInputError):
            _circle("abc")


class TestAreaTriangle:
    @pytest.mark.parametrize(("base", "height", "expected"), [
        ("0", "0", "0"),
        ("5", "-0", "0"),
        ("1", "1", "0.5"),
        ("1E-40", "1E-40", "5E-81"),
        ("1E+40", "1E+40", "5E+79"),
    ])
    def test_boundaries(self, base: str, height: str, expected: str) -> None:
        assert Decimal(_triangle(base, height)["area"]) == Decimal(expected)

    @pytest.mark.parametrize("field", ["base", "height"])
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "abc", 0.1])
    def test_invalid_dimensions(self, field: str, value: object) -> None:
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("geometry.area_triangle", **{"base": "2", "height": "3", field: value})

    def test_exact_half_product_beyond_default_precision(self) -> None:
        base = "123456789012345678901234567890123456789012345678901234567891"
        result = _triangle(base, "9")
        product = int(base) * 9
        expected = f"{product // 2}.5"
        assert result["area"] == expected
        assert result["trace"]["output"] == {"area": expected}

    def test_independent_of_caller_decimal_context(self) -> None:
        with localcontext() as context:
            context.prec = 3
            context.rounding = ROUND_UP
            context.Emax = 5
            context.Emin = -5
            context.traps[Inexact] = True
            context.clear_flags()
            result = area_triangle("123456.789", "0.987654321")
            assert result["area"] == "60966.3155563176345"
            assert context.prec == 3
            assert context.rounding == ROUND_UP
            assert context.Emax == 5
            assert context.Emin == -5
            assert context.traps[Inexact]
            assert not any(context.flags.values())

    @pytest.mark.parametrize(("base", "height"), [
        ("1E+999999", "100"),
        ("1E-999999", "1E-100"),
    ])
    def test_unrepresentable_area_raises_domain_error(self, base: str, height: str) -> None:
        with pytest.raises(InvalidInputError, match="Decimal"):
            _triangle(base, height)

    def test_area_triangle_3_4(self) -> None:
        # (3 * 4) / 2 = 6
        result = _triangle("3", "4")
        assert result["area"] == "6"

    def test_area_triangle_half_base_half(self) -> None:
        result = _triangle("1", "2")
        assert result["area"] == "1"

    def test_area_triangle_decimal_values(self) -> None:
        result = _triangle("2.5", "4")
        assert Decimal(result["area"]) == Decimal("5")

    def test_area_triangle_zero_height(self) -> None:
        result = _triangle("5", "0")
        assert Decimal(result["area"]) == Decimal("0")

    def test_area_triangle_trace_present(self) -> None:
        result = _triangle("3", "4")
        assert result["trace"]["tool"] == "geometry.area_triangle"

    def test_area_triangle_negative_base_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _triangle("-1", "4")

    def test_area_triangle_negative_height_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _triangle("3", "-1")


class TestAreaRectangle:
    @pytest.mark.parametrize(("width", "height", "expected"), [
        ("0", "0", "0"),
        ("5", "-0", "0"),
        ("1E-40", "1E-40", "1E-80"),
        ("1E+40", "1E+40", "1E+80"),
    ])
    def test_boundaries(self, width: str, height: str, expected: str) -> None:
        assert Decimal(_rectangle(width, height)["area"]) == Decimal(expected)

    @pytest.mark.parametrize("field", ["width", "height"])
    @pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "abc", 0.1])
    def test_invalid_dimensions(self, field: str, value: object) -> None:
        inputs = {"width": "2", "height": "3", field: value}
        with pytest.raises(InvalidInputError):
            REGISTRY.invoke("geometry.area_rectangle", **inputs)

    @pytest.mark.parametrize("field", ["width", "height"])
    def test_negative_dimension(self, field: str) -> None:
        with pytest.raises(DomainConstraintError):
            REGISTRY.invoke("geometry.area_rectangle", **{"width": "2", "height": "3", field: "-0.001"})

    def test_exact_product_beyond_default_precision(self) -> None:
        width = "123456789012345678901234567890123456789012345678901234567890"
        result = _rectangle(width, "9")
        expected = str(int(width) * 9)
        assert result["area"] == expected
        assert result["trace"]["output"] == {"area": expected}

    def test_independent_of_caller_decimal_context(self) -> None:
        with localcontext() as context:
            context.prec = 3
            context.rounding = ROUND_UP
            context.Emax = 5
            context.Emin = -5
            context.traps[Inexact] = True
            context.clear_flags()
            result = area_rectangle("123456.789", "0.987654321")
            assert result["area"] == "121932.631112635269"
            assert context.prec == 3
            assert context.rounding == ROUND_UP
            assert context.Emax == 5
            assert context.Emin == -5
            assert context.traps[Inexact]
            assert not any(context.flags.values())

    @pytest.mark.parametrize(("width", "height"), [
        ("1E+999999", "10"),
        ("1E-999999", "1E-100"),
    ])
    def test_unrepresentable_product_raises_domain_error(self, width: str, height: str) -> None:
        with pytest.raises(InvalidInputError, match="Decimal"):
            _rectangle(width, height)

    def test_area_rectangle_3_4(self) -> None:
        result = _rectangle("3", "4")
        assert result["area"] == "12"

    def test_area_rectangle_decimal(self) -> None:
        result = _rectangle("2.5", "3.5")
        assert Decimal(result["area"]) == Decimal("8.75")

    def test_area_rectangle_unit(self) -> None:
        result = _rectangle("1", "1")
        assert result["area"] == "1"

    def test_area_rectangle_zero(self) -> None:
        result = _rectangle("0", "5")
        assert Decimal(result["area"]) == Decimal("0")

    def test_area_rectangle_trace(self) -> None:
        result = _rectangle("3", "4")
        assert result["trace"]["tool"] == "geometry.area_rectangle"

    def test_area_rectangle_negative_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _rectangle("-1", "4")


class TestAreaPolygon:
    @pytest.mark.parametrize("reverse", [False, True])
    def test_small_square_at_large_coordinates(self, reverse: bool) -> None:
        low = "1000000000000000000000000000000"
        high = "1000000000000000000000000000001"
        vertices = [[low, low], [high, low], [high, high], [low, high]]
        if reverse:
            vertices.reverse()

        result = _polygon(vertices)

        assert Decimal(result["area"]) == Decimal("1")
        assert result["trace"]["output"] == {"area": result["area"]}

    def test_fractional_area_at_large_coordinates(self) -> None:
        result = _polygon([
            ["1000000000000000000000000000000.000", "-1000000000000000000000000000000.00"],
            ["1000000000000000000000000000000.125", "-1000000000000000000000000000000.00"],
            ["1000000000000000000000000000000.000", "-999999999999999999999999999999.75"],
        ])

        assert Decimal(result["area"]) == Decimal("0.015625")

    @pytest.mark.parametrize("vertices", [
        [["0", "0"], ["1", "1"], ["2", "2"]],
        [["1", "1"], ["1", "1"], ["1", "1"]],
        [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"], ["0", "0"]],
    ])
    def test_degenerate_and_closed_boundaries(self, vertices: list[list[str]]) -> None:
        expected = "1" if len(vertices) == 5 else "0"
        assert Decimal(_polygon(vertices)["area"]) == Decimal(expected)

    @pytest.mark.parametrize("coordinate", ["NaN", "sNaN", "Infinity", "-Infinity", "abc"])
    @pytest.mark.parametrize("axis", [0, 1])
    def test_invalid_coordinates_raise(self, coordinate: str, axis: int) -> None:
        vertices = [["0", "0"], ["1", "0"], ["0", "1"]]
        vertices[1][axis] = coordinate
        with pytest.raises(InvalidInputError):
            _polygon(vertices)

    @pytest.mark.parametrize("vertex", [[], ["1"], ["1", "2", "3"]])
    def test_vertex_requires_exactly_two_coordinates(self, vertex: list[str]) -> None:
        with pytest.raises(InvalidInputError):
            _polygon([["0", "0"], vertex, ["0", "1"]])

    def test_polygon_unit_square(self) -> None:
        # [[0,0],[1,0],[1,1],[0,1]] → area = 1
        vertices = [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"]]
        result = _polygon(vertices)
        assert Decimal(result["area"]) == Decimal("1")

    def test_polygon_2x2_square(self) -> None:
        vertices = [["0", "0"], ["2", "0"], ["2", "2"], ["0", "2"]]
        result = _polygon(vertices)
        assert Decimal(result["area"]) == Decimal("4")

    def test_polygon_right_triangle(self) -> None:
        # Triangle with vertices (0,0), (3,0), (0,4) → area = 6
        vertices = [["0", "0"], ["3", "0"], ["0", "4"]]
        result = _polygon(vertices)
        assert Decimal(result["area"]) == Decimal("6")

    def test_polygon_pentagon(self) -> None:
        # Regular-ish pentagon, just check it returns positive area
        vertices = [
            ["0", "2"], ["2", "0"], ["3", "2"],
            ["2", "4"], ["0", "4"],
        ]
        result = _polygon(vertices)
        assert Decimal(result["area"]) > Decimal("0")

    def test_polygon_clockwise_same_as_ccw(self) -> None:
        # Shoelace should return absolute value regardless of winding
        ccw = [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"]]
        cw  = [["0", "0"], ["0", "1"], ["1", "1"], ["1", "0"]]
        assert _polygon(ccw)["area"] == _polygon(cw)["area"]

    def test_polygon_too_few_vertices_raises(self) -> None:
        with pytest.raises(DomainConstraintError):
            _polygon([["0", "0"], ["1", "0"]])

    def test_polygon_trace(self) -> None:
        vertices = [["0", "0"], ["1", "0"], ["1", "1"], ["0", "1"]]
        result = _polygon(vertices)
        assert result["trace"]["tool"] == "geometry.area_polygon"

    # Property: area invariant under vertex rotation
    def test_polygon_rotation_invariant(self) -> None:
        v = [["0", "0"], ["4", "0"], ["4", "3"], ["0", "3"]]
        area_base = _polygon(v)["area"]
        # Rotate vertices by 1
        rotated = v[1:] + v[:1]
        assert _polygon(rotated)["area"] == area_base

    def test_geometry_batch_race_free(self) -> None:
        """100 parallel area_polygon calls must return identical results."""
        vertices = [["0", "0"], ["3", "0"], ["3", "4"], ["0", "4"]]

        def call(_: int) -> str:
            return _polygon(vertices)["area"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            results = list(ex.map(call, range(100)))

        assert all(r == results[0] for r in results), "Race condition detected"
