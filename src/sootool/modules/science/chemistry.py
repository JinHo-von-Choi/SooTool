"""Science chemistry tools: molar_mass, stoichiometry.

내부 자료형 (ADR-008):
- 화학식 파싱: 정수 계수 (원소 개수는 항상 자연수).
- molar_mass: 원자량은 Decimal, 결과 Decimal.
- stoichiometry: Decimal 몰수 및 질량 계산.

화학식 파싱 규칙:
- 대소문자 구분 (Ca, C, Cl 등).
- 중첩 괄호 지원: Ca(OH)2, Al2(SO4)3.
- 수화물 표기: CuSO4.5H2O (점 '.'으로 구분).
- 알려지지 않은 원소: DomainConstraintError.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sootool.core.audit import CalcTrace
from sootool.core.decimal_ops import D
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult
from sootool.modules.science.periodic_table import ATOMIC_MASS_DECIMAL


class MolarMassResult(TracedResult):
    molar_mass:  str
    composition: dict[str, int]


class StoichiometryResult(TracedResult):
    moles:            dict[str, str]
    masses:           dict[str, str]
    limiting_reagent: str


def _parse_formula(formula: str) -> dict[str, int]:
    """Parse a chemical formula string into element -> count mapping.

    Supports:
    - Simple formulas: H2O, NaCl, Fe
    - Parentheses: Ca(OH)2, Al2(SO4)3
    - Hydrates with '.': CuSO4.5H2O

    Returns:
        dict mapping element symbol -> total atom count.

    Raises:
        InvalidInputError:     On malformed formula.
        DomainConstraintError: On unknown element symbol.
    """
    if not formula:
        raise InvalidInputError("화학식이 비어 있습니다.")

    # Handle hydrates: split on '.' and recurse, scaling by coefficient
    if "." in formula:
        parts = formula.split(".", 1)
        lhs   = parts[0]
        rhs   = parts[1]
        # rhs may start with a number (e.g. "5H2O")
        match = re.match(r"^(\d*)(.+)$", rhs)
        if not match:
            raise InvalidInputError(f"수화물 형식이 올바르지 않습니다: {formula!r}")
        hydrate_coeff = int(match.group(1)) if match.group(1) else 1
        hydrate_form  = match.group(2)

        lhs_counts  = _parse_formula(lhs)
        rhs_counts  = _parse_formula(hydrate_form)
        result: dict[str, int] = dict(lhs_counts)
        for elem, cnt in rhs_counts.items():
            result[elem] = result.get(elem, 0) + cnt * hydrate_coeff
        return result

    return _parse_formula_simple(formula)


def _parse_formula_simple(formula: str) -> dict[str, int]:
    """Parse a formula without '.' hydrate notation, supporting parentheses."""
    tokens = _tokenize(formula)
    counts, _ = _parse_tokens(tokens, 0)
    return counts


def _tokenize(formula: str) -> list[str]:
    """Tokenize a chemical formula into elements, digits, and parentheses."""
    token_pattern = re.compile(r"[A-Z][a-z]?|\d+|[()]")
    tokens = token_pattern.findall(formula)
    # Verify the formula is fully consumed
    reconstructed = "".join(tokens)
    if reconstructed != formula:
        bad = re.sub(r"[A-Z][a-z]?|\d+|[()]", "", formula)
        raise InvalidInputError(f"화학식에 인식할 수 없는 문자가 있습니다: {bad!r} in {formula!r}")
    return tokens


def _parse_tokens(
    tokens: list[str],
    pos: int,
) -> tuple[dict[str, int], int]:
    """Recursively parse token list into element counts.

    Returns:
        (counts_dict, next_position)
    """
    counts: dict[str, int] = {}

    while pos < len(tokens):
        tok = tokens[pos]

        if tok == "(":
            # Parse inside parentheses
            inner, pos = _parse_tokens(tokens, pos + 1)
            # Expect closing ')'
            if pos >= len(tokens) or tokens[pos] != ")":
                raise InvalidInputError("괄호가 맞지 않습니다: ')' 누락.")
            pos += 1
            # Optional multiplier after ')'
            mult = 1
            if pos < len(tokens) and tokens[pos].isdigit():
                mult = int(tokens[pos])
                pos += 1
            for elem, cnt in inner.items():
                counts[elem] = counts.get(elem, 0) + cnt * mult

        elif tok == ")":
            # Return to caller which handles ')'
            break

        elif re.match(r"^[A-Z]", tok):
            # Element symbol, validate and parse count
            elem = tok
            pos += 1
            count = 1
            if pos < len(tokens) and tokens[pos].isdigit():
                count = int(tokens[pos])
                pos += 1
            if elem not in ATOMIC_MASS_DECIMAL:
                raise DomainConstraintError(
                    f"알 수 없는 원소 기호: {elem!r}. "
                    f"지원 원소: {sorted(ATOMIC_MASS_DECIMAL.keys())}"
                )
            counts[elem] = counts.get(elem, 0) + count

        else:
            # Standalone digit or unexpected token
            raise InvalidInputError(f"화학식 파싱 오류: 예상치 못한 토큰 {tok!r}")

    return counts, pos


@REGISTRY.tool(
    namespace="science",
    name="molar_mass",
    description=(
        "화학식으로 몰질량(g/mol)을 계산하고 원소별 원자 수(composition)를 돌려준다. "
        "원소 기호는 대소문자를 구분하며 괄호 Ca(OH)2, 수화물 CuSO4.5H2O 표기를 지원한다. "
        "IUPAC 2021 관례값 원자량을 Decimal로 합산하며 반올림하지 않는다. "
        "H~Pb 사이 일반 원소 27종만 지원하고 그 밖의 원소와 이온 전하 표기는 오류다."
    ),
    version="1.0.0",
)
def molar_mass(formula: str) -> MolarMassResult:
    """Compute the molar mass of a chemical compound.

    Args:
        formula: Chemical formula string (e.g. "H2O", "Ca(OH)2", "CuSO4.5H2O").

    Returns:
        {molar_mass: str (g/mol), composition: dict[element, count], trace}

    Raises:
        DomainConstraintError: On unknown element.
        InvalidInputError:     On malformed formula.
    """
    trace = CalcTrace(
        tool="science.molar_mass",
        formula="M = Σ (count_i * atomic_mass_i)",
    )
    trace.input("formula", formula)

    composition = _parse_formula(formula.strip())
    trace.step("composition", composition)

    total_mass = D("0")
    for elem, count in composition.items():
        mass = ATOMIC_MASS_DECIMAL[elem]
        contribution = mass * Decimal(count)
        total_mass += contribution
        trace.step(f"{elem}: {count} × {mass}", str(contribution))

    trace.step("molar_mass", str(total_mass))
    trace.output({"molar_mass": str(total_mass), "composition": composition})

    return {
        "molar_mass":  str(total_mass),
        "composition": composition,
        "trace":       trace.to_dict(),
    }


@REGISTRY.tool(
    namespace="science",
    name="stoichiometry",
    description=(
        "균형 맞춘 반응식 계수로 한계 반응물을 찾고 각 물질의 몰수(mol)와 질량(g)을 계산한다. "
        "reactants는 {formula, mass(g) 또는 moles} 목록, products는 {formula} 목록, coefficients는 {화학식: 정수 계수}이며 "
        "수치는 Decimal 문자열이다. 몰질량은 molar_mass 와 같은 원자량을 쓰고 반올림하지 않는다. "
        "계수가 균형 상태가 아니면 결과가 틀리며 수율이나 불순물은 반영하지 않는다."
    ),
    version="1.0.0",
)
def stoichiometry(
    reactants: list[dict[str, Any]],
    products: list[dict[str, Any]],
    coefficients: dict[str, int],
) -> StoichiometryResult:
    """Compute stoichiometric amounts given a balanced equation.

    Args:
        reactants:    List of {formula: str, mass?: str (g), moles?: str}.
                      Provide either mass or moles for each reactant.
        products:     List of {formula: str}, formulas for which to compute amounts.
        coefficients: Balanced equation coefficients for all species
                      (reactants and products), e.g. {"H2": 2, "O2": 1, "H2O": 2}.

    Returns:
        {moles: dict[formula, str], masses: dict[formula, str],
         limiting_reagent: str, trace}

    Raises:
        InvalidInputError:     On missing mass/moles or invalid numbers.
        DomainConstraintError: On unknown formulas not in coefficients.
    """
    trace = CalcTrace(
        tool="science.stoichiometry",
        formula="moles = given_moles / coeff; product_moles = scale * product_coeff",
    )

    if not reactants:
        raise InvalidInputError("reactants 목록이 비어 있습니다.")
    if not products:
        raise InvalidInputError("products 목록이 비어 있습니다.")

    trace.input("reactants",    [r.get("formula") for r in reactants])
    trace.input("products",     [p.get("formula") for p in products])
    trace.input("coefficients", coefficients)

    # Parse molar masses for all formulas
    def get_molar(f: str) -> Decimal:
        return Decimal(molar_mass(f)["molar_mass"])

    # Convert each reactant input to moles
    reactant_moles: dict[str, Decimal] = {}

    for r in reactants:
        form = str(r.get("formula", ""))
        if not form:
            raise InvalidInputError("reactant formula가 비어 있습니다.")
        if form not in coefficients:
            raise DomainConstraintError(
                f"반응물 {form!r}이(가) coefficients에 없습니다."
            )
        if "moles" in r and r["moles"] is not None:
            try:
                mol = D(str(r["moles"]))
            except Exception as exc:
                raise InvalidInputError(f"{form} moles 파싱 오류: {r['moles']!r}") from exc
        elif "mass" in r and r["mass"] is not None:
            try:
                mass_g = D(str(r["mass"]))
            except Exception as exc:
                raise InvalidInputError(f"{form} mass 파싱 오류: {r['mass']!r}") from exc
            mol = mass_g / get_molar(form)
        else:
            raise InvalidInputError(f"reactant {form!r}에 mass 또는 moles가 필요합니다.")

        if mol < D("0"):
            raise DomainConstraintError(f"{form}의 mol({mol})은 음수가 될 수 없습니다.")

        reactant_moles[form] = mol
        trace.step(f"{form} moles", str(mol))

    # Find the limiting reagent: reactant with minimum moles / coefficient
    scale_factors: dict[str, Decimal] = {}
    for form, mol in reactant_moles.items():
        coeff = Decimal(str(coefficients[form]))
        if coeff <= D("0"):
            raise DomainConstraintError(f"{form}의 coefficient는 양수여야 합니다: {coeff}")
        scale_factors[form] = mol / coeff

    limiting_reagent = min(scale_factors, key=lambda f: scale_factors[f])
    scale = scale_factors[limiting_reagent]
    trace.step("limiting_reagent", limiting_reagent)
    trace.step("scale_factor",     str(scale))

    # Compute moles and masses for all species
    all_formulas = list(reactant_moles.keys()) + [p["formula"] for p in products]
    result_moles: dict[str, str] = {}
    result_masses: dict[str, str] = {}

    for form in all_formulas:
        if form not in coefficients:
            raise DomainConstraintError(f"{form!r}이(가) coefficients에 없습니다.")
        coeff = Decimal(str(coefficients[form]))
        mol   = scale * coeff
        mass  = mol * get_molar(form)
        result_moles[form]  = str(mol)
        result_masses[form] = str(mass)
        trace.step(f"{form} product moles", str(mol))
        trace.step(f"{form} product mass",  str(mass))

    trace.output({
        "limiting_reagent": limiting_reagent,
        "moles":  result_moles,
        "masses": result_masses,
    })

    return {
        "moles":            result_moles,
        "masses":           result_masses,
        "limiting_reagent": limiting_reagent,
        "trace":            trace.to_dict(),
    }
