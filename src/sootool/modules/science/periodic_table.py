"""IUPAC 2021 standard atomic weights for common elements.

Source: IUPAC 2021 Table of Standard Atomic Weights
(https://iupac.org/what-we-do/periodic-table-of-elements/)

Values are the conventional standard atomic weights in g/mol.
For elements with a range (e.g., H, C, N, O), the conventional value is used.

27 common elements included per spec.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

from decimal import Decimal

# Standard atomic weights from IUPAC 2021.
# Keys are element symbols (case-sensitive canonical form, e.g. "Ca" not "ca").
ATOMIC_MASS: dict[str, str] = {
    "H":  "1.008",
    "He": "4.002602",
    "Li": "6.94",
    "Be": "9.0121831",
    "B":  "10.81",
    "C":  "12.011",
    "N":  "14.007",
    "O":  "15.999",
    "F":  "18.998403163",
    "Ne": "20.1797",
    "Na": "22.98976928",
    "Mg": "24.305",
    "Al": "26.9815384",
    "Si": "28.085",
    "P":  "30.973761998",
    "S":  "32.06",
    "Cl": "35.45",
    "Ar": "39.948",
    "K":  "39.0983",
    "Ca": "40.078",
    "Fe": "55.845",
    "Cu": "63.546",
    "Zn": "65.38",
    "Ag": "107.8682",
    "Au": "196.966570",
    "Hg": "200.592",
    "Pb": "207.2",
}

# Pre-parsed Decimal values (immutable after module load)
ATOMIC_MASS_DECIMAL: dict[str, Decimal] = {
    sym: Decimal(mass) for sym, mass in ATOMIC_MASS.items()
}
